from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from vendor_contract_compliance.agentic_graph import build_graph, run_agentic
from vendor_contract_compliance.agentic_models import ExecutionPlan, PlanStep, ReviewerResult, ToolRequest
from vendor_contract_compliance.model_clients import ModelClientError, OpenAIModelClient, ScriptedModelClient

EXPECTED=[("POL-001","PASS","LOW",1),("POL-002","GAP","HIGH",2),("POL-003","MISSING","HIGH",None),("POL-004","GAP","MEDIUM",3),("POL-005","REVIEW","MEDIUM",4)]
def run(root,contract_path,tmp_path,decisions): return run_agentic(ScriptedModelClient(decisions),contract_path,root/"policies/demo_policies.yaml",tmp_path)
def test_graph_nodes_edges():
    graph=build_graph(ScriptedModelClient()).compile().get_graph(); nodes=set(graph.nodes); edges={(e.source,e.target) for e in graph.edges}
    assert {"orchestrator","contract_analyst","compliance_analyst","independent_reviewer","report_builder","controlled_failure"} <= nodes
    assert ("__start__","orchestrator") in edges and ("orchestrator","contract_analyst") in edges
def test_success_real_tools_immutable_findings_and_reports(root,contract_path,tmp_path):
    client=ScriptedModelClient(["APPROVE"]); r=run_agentic(client,contract_path,root/"policies/demo_policies.yaml",tmp_path); assert r.route_status=="APPROVED" and len(r.plan.steps)==4
    assert [(f.policy_id,f.status.value,f.severity.value,f.page_number) for f in r.findings]==EXPECTED
    assert [e.tool_name for e in r.tool_events]==["extract_pdf_pages","extract_contract_clauses","load_demo_policies","run_deterministic_rules","write_agentic_report"]
    assert all((tmp_path/n).is_file() for n in ["agentic_run.json","agentic_report.md","tool-events.json","agent-events.json"])
    assert r.findings[2].page_number is None and r.findings[2].contract_clause is None
    reviewer_context=[c for role,schema,c in client.contexts if role=="independent_reviewer"][0]
    assert len(reviewer_context["findings"])==5 and reviewer_context["available_pages"]==[1,2,3,4]
    assert reviewer_context["missing_findings"]==[{"policy_id":"POL-003","page_number":None,"has_clause":False}]
    assert "evidence_text" not in str(reviewer_context) and reviewer_context["tool_events"]
def test_retry_returns_to_contract_then_approves(root,contract_path,tmp_path):
    r=run(root,contract_path,tmp_path,["RETRY","APPROVE"]); assert r.retry_count==1 and r.graph_path.count("contract_analyst")==2 and r.route_status=="APPROVED"
def test_exhaustion_is_bounded(root,contract_path,tmp_path):
    r=run(root,contract_path,tmp_path,["RETRY","RETRY","RETRY"]); assert r.retry_count==2 and r.route_status=="CONTROLLED_FAILURE" and r.graph_path[-1]=="controlled_failure"
def test_tool_failure_controlled(root,contract_path,tmp_path):
    r=run_agentic(ScriptedModelClient(),contract_path,root/"missing.yaml",tmp_path); assert r.route_status=="CONTROLLED_FAILURE" and r.error
def test_invalid_model_output_and_schema_rejected(root,contract_path,tmp_path):
    with pytest.raises(ValidationError): PlanStep(step="",tool="extract_pdf_pages")
    with pytest.raises(ValidationError): ReviewerResult(decision="ALTER",feedback="x")
    r=run_agentic(ScriptedModelClient(invalid_role="independent_reviewer"),contract_path,root/"policies/demo_policies.yaml",tmp_path); assert r.route_status=="CONTROLLED_FAILURE"
def test_openai_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY",raising=False)
    with pytest.raises(ModelClientError,match="not configured"): OpenAIModelClient()

def test_plan_rejects_wrong_tool_order():
    bad={"steps":[{"step":"x","tool":"extract_contract_clauses"},{"step":"x","tool":"extract_pdf_pages"},{"step":"x","tool":"load_demo_policies"},{"step":"x","tool":"run_deterministic_rules"}]}
    with pytest.raises(ValidationError,match="canonical order"): ExecutionPlan.model_validate(bad)

def test_invalid_model_plan_enters_controlled_failure(root,contract_path,tmp_path):
    bad={"steps":[{"step":"x","tool":"extract_contract_clauses"},{"step":"x","tool":"extract_pdf_pages"},{"step":"x","tool":"load_demo_policies"},{"step":"x","tool":"run_deterministic_rules"}]}
    r=run_agentic(ScriptedModelClient(plan=bad),contract_path,root/"policies/demo_policies.yaml",tmp_path)
    assert r.route_status=="CONTROLLED_FAILURE" and "plan failed schema validation" in r.error

def test_role_tool_allowlist_fails_closed(root,contract_path,tmp_path):
    client=ScriptedModelClient(tool_requests=["load_demo_policies"])
    r=run_agentic(client,contract_path,root/"policies/demo_policies.yaml",tmp_path)
    assert r.route_status=="CONTROLLED_FAILURE" and not r.findings

class FakeResponses:
    def __init__(self, *, parsed=None, status="completed", call_name=None): self.parsed,self.status,self.call_name=parsed,status,call_name; self.kwargs=[]
    def parse(self, **kwargs): self.kwargs.append(kwargs); return SimpleNamespace(status=self.status,output_parsed=self.parsed)
    def create(self, **kwargs):
        self.kwargs.append(kwargs); output=[] if self.call_name is None else [SimpleNamespace(type="function_call",name=self.call_name)]
        return SimpleNamespace(status=self.status,output=output)

def openai_with(fake):
    client=object.__new__(OpenAIModelClient); client.model_name="fake-model"; client._client=SimpleNamespace(responses=fake); return client

def test_fake_openai_structured_plan_parsing():
    plan=ExecutionPlan.model_validate({"steps":[{"step":"pages","tool":"extract_pdf_pages"},{"step":"clauses","tool":"extract_contract_clauses"},{"step":"policies","tool":"load_demo_policies"},{"step":"rules","tool":"run_deterministic_rules"}]})
    fake=FakeResponses(parsed=plan); result=openai_with(fake).structured("orchestrator",ExecutionPlan,{"allowed_tools":"Phase 2 only"})
    assert result==plan and fake.kwargs[0]["text_format"] is ExecutionPlan

def test_fake_openai_strict_function_call_includes_expected_next():
    allowed=["extract_pdf_pages","extract_contract_clauses"]
    fake=FakeResponses(call_name="extract_pdf_pages"); result=openai_with(fake).structured("contract_analyst",ToolRequest,{"allowed_tools":allowed,"expected_next":"extract_pdf_pages"})
    assert result.tool_name=="extract_pdf_pages" and "extract_pdf_pages" in fake.kwargs[0]["input"] and "Request that tool only" in fake.kwargs[0]["input"]
    assert [tool["name"] for tool in fake.kwargs[0]["tools"]]==allowed and fake.kwargs[0]["tool_choice"]=="required"
    assert fake.kwargs[0]["parallel_tool_calls"] is False and all(tool["strict"] is True for tool in fake.kwargs[0]["tools"])

def test_fake_openai_rejects_tool_outside_allowlist():
    rogue=FakeResponses(call_name="load_demo_policies")
    with pytest.raises(ModelClientError,match="allowlist"): openai_with(rogue).structured("contract_analyst",ToolRequest,{"allowed_tools":["extract_pdf_pages"],"expected_next":"extract_pdf_pages"})

def test_fake_openai_rejects_allowed_tool_outside_plan_order():
    fake=FakeResponses(call_name="extract_contract_clauses")
    with pytest.raises(ModelClientError,match="execution plan order"):
        openai_with(fake).structured("contract_analyst",ToolRequest,{"allowed_tools":["extract_pdf_pages","extract_contract_clauses"],"expected_next":"extract_pdf_pages"})

def test_fake_openai_rejects_expected_next_outside_allowlist_without_request():
    fake=FakeResponses(call_name="extract_pdf_pages")
    with pytest.raises(ModelClientError,match="Expected plan tool.*allowlist"):
        openai_with(fake).structured("contract_analyst",ToolRequest,{"allowed_tools":["extract_pdf_pages"],"expected_next":"load_demo_policies"})
    assert fake.kwargs==[]

@pytest.mark.parametrize("status,parsed",[("incomplete",None),("completed",None)])
def test_fake_openai_incomplete_or_refusal(status,parsed):
    with pytest.raises(ModelClientError,match="refusal or incomplete"): openai_with(FakeResponses(status=status,parsed=parsed)).structured("independent_reviewer",ReviewerResult,{})
