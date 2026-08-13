import json, os
import pytest
from pydantic import ValidationError
from vendor_contract_compliance.agentic_graph import build_graph, run_agentic
from vendor_contract_compliance.agentic_models import PlanStep, ReviewerResult
from vendor_contract_compliance.model_clients import ModelClientError, OpenAIModelClient, ScriptedModelClient

EXPECTED=[("POL-001","PASS","LOW",1),("POL-002","GAP","HIGH",2),("POL-003","MISSING","HIGH",None),("POL-004","GAP","MEDIUM",3),("POL-005","REVIEW","MEDIUM",4)]
def run(root,contract_path,tmp_path,decisions): return run_agentic(ScriptedModelClient(decisions),contract_path,root/"policies/demo_policies.yaml",tmp_path)
def test_graph_nodes_edges():
    graph=build_graph(ScriptedModelClient()).compile().get_graph(); nodes=set(graph.nodes); edges={(e.source,e.target) for e in graph.edges}
    assert {"orchestrator","contract_analyst","compliance_analyst","independent_reviewer","report_builder","controlled_failure"} <= nodes
    assert ("__start__","orchestrator") in edges and ("orchestrator","contract_analyst") in edges
def test_success_real_tools_immutable_findings_and_reports(root,contract_path,tmp_path):
    r=run(root,contract_path,tmp_path,["APPROVE"]); assert r.route_status=="APPROVED" and len(r.plan.steps)==4
    assert [(f.policy_id,f.status.value,f.severity.value,f.page_number) for f in r.findings]==EXPECTED
    assert [e.tool_name for e in r.tool_events]==["extract_pdf_pages","extract_contract_clauses","load_demo_policies","run_deterministic_rules","write_agentic_report"]
    assert all((tmp_path/n).is_file() for n in ["agentic_run.json","agentic_report.md","tool-events.json","agent-events.json"])
    assert r.findings[2].page_number is None and r.findings[2].contract_clause is None
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
