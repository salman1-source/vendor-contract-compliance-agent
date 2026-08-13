"""Four authority-separated Phase 3A agent nodes."""
from datetime import datetime, timezone
from pydantic import ValidationError
from .agentic_models import AgentEvent, ExecutionPlan, ReviewerDecision, ReviewerResult, ToolRequest
from .agentic_tools import clauses, pdf_pages, policies, rules

def _event(state, agent, action):
    state.setdefault("agent_events", []).append(AgentEvent(agent=agent, action=action, occurred_at=datetime.now(timezone.utc)))
    state.setdefault("graph_path", []).append(agent)

class OrchestratorAgent:
    def __init__(self, client): self.client=client
    def __call__(self, state):
        _event(state,"orchestrator","created structured execution plan")
        state["plan"] = self.client.structured("orchestrator",ExecutionPlan,{"allowed_tools":"Phase 2 only"}); return state

class ContractAnalystAgent:
    def __init__(self, client): self.client=client
    def __call__(self, state):
        _event(state,"contract_analyst","requested extraction tools")
        try:
            self.client.structured("contract_analyst",ToolRequest,{"tool_name":"extract_pdf_pages"}); state["pages"]=pdf_pages(state)
            self.client.structured("contract_analyst",ToolRequest,{"tool_name":"extract_contract_clauses"}); state["clauses"]=clauses(state)
        except Exception as exc: state["error"]=f"Contract analysis failed safely ({type(exc).__name__})"; state["route_status"]="FAIL"
        return state

class ComplianceAnalystAgent:
    def __init__(self, client): self.client=client
    def __call__(self, state):
        _event(state,"compliance_analyst","requested deterministic compliance tools")
        if state.get("error"): return state
        try:
            self.client.structured("compliance_analyst",ToolRequest,{"tool_name":"load_demo_policies"}); state["policies"]=policies(state)
            self.client.structured("compliance_analyst",ToolRequest,{"tool_name":"run_deterministic_rules"}); state["findings"]=rules(state)
        except Exception as exc: state["error"]=f"Compliance analysis failed safely ({type(exc).__name__})"; state["route_status"]="FAIL"
        return state

class IndependentReviewerAgent:
    def __init__(self, client): self.client=client
    def __call__(self, state):
        _event(state,"independent_reviewer","reviewed evidence completeness without changing findings")
        if state.get("error"):
            state["reviewer_decision"]=ReviewerDecision.FAIL; state["reviewer_feedback"]="Upstream controlled failure."; return state
        snapshot=[f.model_dump() for f in state.get("findings",[])]
        try: result=self.client.structured("independent_reviewer",ReviewerResult,{"finding_count":len(snapshot),"missing_locations":[f["page_number"] for f in snapshot if str(f["status"])=="MISSING"]})
        except Exception as exc:
            state["error"]=f"Reviewer output failed schema validation ({type(exc).__name__})"; state["reviewer_decision"]=ReviewerDecision.FAIL; state["reviewer_feedback"]="Invalid structured reviewer output."; return state
        if [f.model_dump() for f in state["findings"]] != snapshot: raise RuntimeError("Reviewer cannot modify deterministic findings")
        if result.decision == ReviewerDecision.APPROVE and (len(snapshot)!=5 or any(f["page_number"] is not None for f in snapshot if str(f["status"])=="MISSING")):
            state["error"]="Reviewer approval rejected: incomplete evidence"; state["reviewer_decision"]=ReviewerDecision.FAIL
        else: state["reviewer_decision"]=result.decision
        state["reviewer_feedback"]=result.feedback
        if result.decision == ReviewerDecision.RETRY:
            if state["retry_count"] >= state["max_retries"]: state["route_status"]="RETRY_EXHAUSTED"
            else: state["retry_count"] += 1
        return state
