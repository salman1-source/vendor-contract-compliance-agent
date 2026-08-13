import json
import sys
from types import SimpleNamespace

import pytest

from vendor_contract_compliance.agentic_graph import run_agentic
from vendor_contract_compliance.agentic_models import ExecutionPlan, ToolRequest
from vendor_contract_compliance.model_clients import (
    DEFAULT_MODELS, GeminiModelClient, ModelClientError, OpenAIModelClient,
    OpenRouterModelClient, ScriptedModelClient, create_model_client,
)

EXPECTED=[("POL-001","PASS","LOW",1),("POL-002","GAP","HIGH",2),("POL-003","MISSING","HIGH",None),("POL-004","GAP","MEDIUM",3),("POL-005","REVIEW","MEDIUM",4)]

@pytest.mark.parametrize("name,kind", [("scripted",ScriptedModelClient),("openai",OpenAIModelClient),("openrouter",OpenRouterModelClient),("gemini",GeminiModelClient)])
def test_factory_selection_and_defaults(name, kind):
    options={} if name == "scripted" else {"sdk_client":object()}
    client=create_model_client(name, **options)
    assert isinstance(client,kind) and client.model_name==DEFAULT_MODELS[name] and client.provider==name

@pytest.mark.parametrize("name", ["scripted","openai","openrouter","gemini"])
def test_factory_model_override(name):
    options={} if name == "scripted" else {"sdk_client":object()}
    assert create_model_client(name,"explicit-model",**options).model_name=="explicit-model"

def test_unknown_provider_rejected_before_any_sdk():
    with pytest.raises(ModelClientError,match="Unknown"):
        create_model_client("automatic")

@pytest.mark.parametrize("name,key", [("openai","OPENAI_API_KEY"),("openrouter","OPENROUTER_API_KEY"),("gemini","GEMINI_API_KEY")])
def test_only_selected_key_is_required(monkeypatch,name,key):
    for candidate in ("OPENAI_API_KEY","OPENROUTER_API_KEY","GEMINI_API_KEY"):
        monkeypatch.delenv(candidate,raising=False)
    with pytest.raises(ModelClientError,match=key): create_model_client(name)
    monkeypatch.setenv(key,"fake-selected-key")
    # Injecting a fake SDK proves absent non-selected keys are not consulted and makes no request.
    assert create_model_client(name,sdk_client=object()).provider==name

def test_openrouter_uses_distinct_key_and_base_url(monkeypatch):
    seen={}
    class FakeOpenAI:
        def __init__(self,**kwargs): seen.update(kwargs)
    monkeypatch.setitem(sys.modules,"openai",SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv("OPENAI_API_KEY","wrong-key")
    monkeypatch.setenv("OPENROUTER_API_KEY","router-key")
    client=OpenRouterModelClient()
    assert seen=={"api_key":"router-key","base_url":"https://openrouter.ai/api/v1"}
    assert client.model_name=="openai/gpt-5.6-luna"

def test_gemini_uses_official_google_genai_client(monkeypatch):
    from google import genai
    seen={}
    class FakeClient:
        def __init__(self,**kwargs): seen.update(kwargs)
    monkeypatch.setattr(genai,"Client",FakeClient)
    monkeypatch.setenv("GEMINI_API_KEY","gemini-key")
    GeminiModelClient()
    assert seen=={"api_key":"gemini-key"}

class FakeResponses:
    def __init__(self,response=None,error=None): self.response=response; self.error=error; self.kwargs=[]
    def parse(self,**kwargs):
        self.kwargs.append(kwargs)
        if self.error: raise self.error
        return self.response
    def create(self,**kwargs): return self.parse(**kwargs)

def router_with(fake):
    return OpenRouterModelClient(sdk_client=SimpleNamespace(responses=fake))

def completed(**kwargs):
    defaults={"status":"completed","output":[],"output_parsed":None,"incomplete_details":None}
    defaults.update(kwargs); return SimpleNamespace(**defaults)

def test_openrouter_responses_plan_and_strict_tool_boundary():
    plan=ExecutionPlan.model_validate({"steps":[{"step":"p","tool":"extract_pdf_pages"},{"step":"c","tool":"extract_contract_clauses"},{"step":"l","tool":"load_demo_policies"},{"step":"r","tool":"run_deterministic_rules"}]})
    fake=FakeResponses(completed(output_parsed=plan))
    assert router_with(fake).structured("orchestrator",ExecutionPlan,{})==plan
    call=SimpleNamespace(type="function_call",name="extract_pdf_pages")
    fake=FakeResponses(completed(output=[call]))
    result=router_with(fake).structured("contract_analyst",ToolRequest,{"allowed_tools":["extract_pdf_pages"],"expected_next":"extract_pdf_pages"})
    assert result.tool_name=="extract_pdf_pages" and fake.kwargs[0]["parallel_tool_calls"] is False
    assert fake.kwargs[0]["tools"][0]["strict"] is True

@pytest.mark.parametrize("actual,expected", [("load_demo_policies","extract_pdf_pages"),("extract_contract_clauses","extract_pdf_pages")])
def test_openrouter_rejects_unauthorized_or_out_of_order(actual,expected):
    fake=FakeResponses(completed(output=[SimpleNamespace(type="function_call",name=actual)]))
    with pytest.raises(ModelClientError):
        router_with(fake).structured("contract_analyst",ToolRequest,{"allowed_tools":["extract_pdf_pages","extract_contract_clauses"],"expected_next":expected})

@pytest.mark.parametrize("status",[401,402,429,500])
def test_openrouter_api_diagnostics_are_sanitized(status):
    class Error(Exception): pass
    error=Error("private body"); error.status_code=status; error.headers={"authorization":"private"}
    with pytest.raises(ModelClientError) as caught: router_with(FakeResponses(error=error)).structured("orchestrator",ExecutionPlan,{})
    assert caught.value.response_status==str(status) and "private" not in str(caught.value)

class FakeInteractions:
    def __init__(self,response=None,error=None): self.response=response; self.error=error; self.kwargs=[]
    def create(self,**kwargs):
        self.kwargs.append(kwargs)
        if self.error: raise self.error
        return self.response

def gemini_with(fake): return GeminiModelClient(sdk_client=SimpleNamespace(interactions=fake))

def text_output(value): return SimpleNamespace(type="text",text=value)

def test_gemini_structured_plan_is_stateless_and_disables_reasoning_persistence():
    fake=FakeInteractions(SimpleNamespace(status="completed",outputs=[text_output(json.dumps({"steps":[{"step":"p","tool":"extract_pdf_pages"},{"step":"c","tool":"extract_contract_clauses"},{"step":"l","tool":"load_demo_policies"},{"step":"r","tool":"run_deterministic_rules"}]}))]))
    result=gemini_with(fake).structured("orchestrator",ExecutionPlan,{})
    assert len(result.steps)==4 and fake.kwargs[0]["store"] is False
    assert fake.kwargs[0]["response_mime_type"]=="application/json"
    assert fake.kwargs[0]["generation_config"]["thinking_summaries"]=="none"

def test_gemini_exactly_one_function_and_no_automatic_execution():
    call=SimpleNamespace(type="function_call",name="extract_pdf_pages",arguments={})
    fake=FakeInteractions(SimpleNamespace(status="completed",outputs=[call]))
    result=gemini_with(fake).structured("contract_analyst",ToolRequest,{"allowed_tools":["extract_pdf_pages"],"expected_next":"extract_pdf_pages"})
    assert result.tool_name=="extract_pdf_pages"
    assert fake.kwargs[0]["generation_config"]["tool_choice"]=="any"
    assert "function_responses" not in fake.kwargs[0] and "automatic_function_calling" not in fake.kwargs[0]

@pytest.mark.parametrize("outputs", [[], [SimpleNamespace(type="function_call",name="extract_pdf_pages"),SimpleNamespace(type="function_call",name="extract_pdf_pages")], [SimpleNamespace(type="function_call",name="load_demo_policies")]])
def test_gemini_rejects_missing_multiple_or_unauthorized_functions(outputs):
    fake=FakeInteractions(SimpleNamespace(status="completed",outputs=outputs))
    with pytest.raises(ModelClientError): gemini_with(fake).structured("contract_analyst",ToolRequest,{"allowed_tools":["extract_pdf_pages"],"expected_next":"extract_pdf_pages"})

@pytest.mark.parametrize("response", [SimpleNamespace(status="incomplete",outputs=[]),SimpleNamespace(status="failed",outputs=[text_output("private safety refusal")]),SimpleNamespace(status="completed",outputs=[text_output("not-json")]),SimpleNamespace(status="completed",outputs=[SimpleNamespace(type="thought",text="private reasoning")])])
def test_gemini_incomplete_blocked_malformed_or_thought_only_fails_closed(response):
    with pytest.raises(ModelClientError) as caught: gemini_with(FakeInteractions(response)).structured("orchestrator",ExecutionPlan,{})
    assert "private" not in str(caught.value) and "reasoning" not in str(caught.value)

@pytest.mark.parametrize("status",[400,401,403,429,500])
def test_gemini_api_diagnostics_are_sanitized(status):
    class Error(Exception): pass
    error=Error("private response"); error.status_code=status; error.headers={"private":"header"}
    with pytest.raises(ModelClientError) as caught: gemini_with(FakeInteractions(error=error)).structured("orchestrator",ExecutionPlan,{})
    assert caught.value.response_status==str(status) and "private" not in str(caught.value)

def test_sanitized_result_records_provider_model_and_unchanged_findings(root,contract_path,tmp_path):
    result=run_agentic(ScriptedModelClient(model_name="explicit-script"),contract_path,root/"policies/demo_policies.yaml",tmp_path)
    artifact=json.loads((tmp_path/"agentic_run.json").read_text())
    assert (result.provider,result.model,result.client_type)==("scripted","explicit-script","scripted")
    assert artifact["provider"]=="scripted" and artifact["model"]=="explicit-script"
    assert [(f.policy_id,f.status.value,f.severity.value,f.page_number) for f in result.findings]==EXPECTED

def test_raw_gemini_output_not_persisted_on_failure(root,contract_path,tmp_path):
    secret="raw refusal and thought signature"
    response=SimpleNamespace(status="failed",outputs=[text_output(secret),SimpleNamespace(type="thought",text=secret)])
    run_agentic(gemini_with(FakeInteractions(response)),contract_path,root/"policies/demo_policies.yaml",tmp_path)
    assert secret not in (tmp_path/"agentic_run.json").read_text()

def test_workflow_is_manual_and_explicit(root):
    workflow=(root/".github/workflows/phase3-live-model.yml").read_text()
    assert "workflow_dispatch:" in workflow and "push:" not in workflow and "schedule:" not in workflow
    options=workflow.split("options:",1)[1].split("model:",1)[0]
    assert [line.strip()[2:] for line in options.splitlines() if line.strip().startswith("- ")]==["openai","openrouter","gemini"]
    assert "default: openrouter" in workflow and "if: always()" in workflow
    assert "phase3-${{ inputs.provider }}-sanitized-evidence-attempt-${{ github.run_attempt }}" in workflow
    assert "case \"$SELECTED_PROVIDER\"" in workflow and "Enforce approved result" in workflow
    assert "fallback" not in workflow.lower()
