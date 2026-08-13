"""Real LangGraph StateGraph with a bounded retry edge."""
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from langgraph.graph import END, START, StateGraph
from .agentic_models import AgentState, AgenticRunResult, ReviewerDecision, ToolEvent
from .agentic_report import DISCLAIMER, write_agentic_report
from .agents import OrchestratorAgent, ContractAnalystAgent, ComplianceAnalystAgent, IndependentReviewerAgent

def build_graph(client):
    graph=StateGraph(AgentState)
    graph.add_node("orchestrator",OrchestratorAgent(client)); graph.add_node("contract_analyst",ContractAnalystAgent(client)); graph.add_node("compliance_analyst",ComplianceAnalystAgent(client)); graph.add_node("independent_reviewer",IndependentReviewerAgent(client))
    def report(s):
        s.setdefault("graph_path",[]).append("report_builder"); s["route_status"]="APPROVED"
        now=datetime.now(timezone.utc); s.setdefault("tool_events",[]).append(ToolEvent(tool_name="write_agentic_report",requested_by="report_builder",started_at=now,completed_at=now,success=True,safe_input_summary="validated AgenticRunResult",safe_output_summary="four sanitized report files"))
        result=_result(s); s["final_report_paths"]=write_agentic_report(result,Path(s["output_dir"])); return s
    def failure(s):
        s.setdefault("graph_path",[]).append("controlled_failure"); s["route_status"]="CONTROLLED_FAILURE"
        s.setdefault("reviewer_decision",ReviewerDecision.FAIL); s.setdefault("reviewer_feedback","Retry budget exhausted or safe failure.")
        now=datetime.now(timezone.utc); s.setdefault("tool_events",[]).append(ToolEvent(tool_name="write_agentic_report",requested_by="controlled_failure",started_at=now,completed_at=now,success=True,safe_input_summary="validated partial AgenticRunResult",safe_output_summary="four sanitized failure report files"))
        # Preserve partial evidence in the canonical run artifact.
        result=_result(s); out=Path(s["output_dir"]); out.mkdir(parents=True,exist_ok=True); s["final_report_paths"]=write_agentic_report(result,out); return s
    graph.add_node("report_builder",report); graph.add_node("controlled_failure",failure)
    graph.add_edge(START,"orchestrator"); graph.add_edge("orchestrator","contract_analyst"); graph.add_edge("contract_analyst","compliance_analyst"); graph.add_edge("compliance_analyst","independent_reviewer")
    def route(s):
        if s.get("reviewer_decision")==ReviewerDecision.APPROVE:return "approve"
        if s.get("reviewer_decision")==ReviewerDecision.RETRY and s.get("route_status") != "RETRY_EXHAUSTED":return "retry"
        return "fail"
    graph.add_conditional_edges("independent_reviewer",route,{"approve":"report_builder","retry":"contract_analyst","fail":"controlled_failure"}); graph.add_edge("report_builder",END); graph.add_edge("controlled_failure",END)
    return graph

def _result(s):
    return AgenticRunResult(run_id=s["run_id"],model_name=s["model_name"],client_type=s["client_type"],provider=s["provider"],model=s["model"],plan=s["plan"],graph_path=s["graph_path"],retry_count=min(s["retry_count"],s["max_retries"]),max_retries=s["max_retries"],reviewer_decision=s["reviewer_decision"],reviewer_feedback=s["reviewer_feedback"],findings=s.get("findings",[]),tool_events=s.get("tool_events",[]),agent_events=s.get("agent_events",[]),route_status=s.get("route_status",""),error=s.get("error"),error_code=s.get("error_code"),error_stage=s.get("error_stage"),response_status=s.get("response_status"),incomplete_reason=s.get("incomplete_reason"),disclaimer=DISCLAIMER)

def run_agentic(client, contract:Path, policies:Path, output:Path, max_retries=2):
    initial=AgentState(run_id=str(uuid4()),contract_path=str(contract),policies_path=str(policies),output_dir=str(output),retry_count=0,max_retries=max_retries,tool_events=[],agent_events=[],graph_path=[],model_name=client.model_name,client_type=client.client_type,provider=client.provider,model=client.model_name,route_status="RUNNING",error=None)
    state=build_graph(client).compile().invoke(initial,{"recursion_limit":20})
    return _result(state)
