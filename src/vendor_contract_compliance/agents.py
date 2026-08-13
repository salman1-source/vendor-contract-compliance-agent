"""Four authority-separated Phase 3A agent nodes."""
from datetime import datetime, timezone
from .agentic_models import AgentEvent, ExecutionPlan, PlanStep, ReviewerDecision, ReviewerResult, ToolRequest
from .agentic_tools import clauses, pdf_pages, policies, rules
from .model_clients import ModelClientError

def _failure(state, exc, fallback, stage):
    if isinstance(exc, ModelClientError):
        state.update(error=str(exc), error_code=exc.safe_code, error_stage=exc.stage,
                     response_status=exc.response_status, incomplete_reason=exc.incomplete_reason)
    else:
        state.update(error=fallback, error_code="MODEL_PLAN_ERROR", error_stage=stage)
    state["route_status"]="FAIL"

def _event(state, agent, action):
    state.setdefault("agent_events", []).append(AgentEvent(agent=agent, action=action, occurred_at=datetime.now(timezone.utc)))
    state.setdefault("graph_path", []).append(agent)

class OrchestratorAgent:
    def __init__(self, client): self.client=client
    def __call__(self, state):
        _event(state,"orchestrator","created structured execution plan")
        try:
            state["plan"] = self.client.structured("orchestrator",ExecutionPlan,{"allowed_tools":["extract_pdf_pages","extract_contract_clauses","load_demo_policies","run_deterministic_rules"]})
        except Exception as exc:
            # A canonical non-executed placeholder keeps controlled-failure reporting typed.
            state["plan"]=ExecutionPlan(steps=[PlanStep(step=name.replace("_"," "),tool=name) for name in ("extract_pdf_pages","extract_contract_clauses","load_demo_policies","run_deterministic_rules")])
            _failure(state,exc,"Orchestrator plan failed schema validation","orchestrator")
        return state

class ContractAnalystAgent:
    def __init__(self, client): self.client=client
    def __call__(self, state):
        _event(state,"contract_analyst","requested extraction tools")
        if state.get("error"): return state
        try:
            handlers={"extract_pdf_pages":lambda: state.__setitem__("pages",pdf_pages(state)),"extract_contract_clauses":lambda: state.__setitem__("clauses",clauses(state))}
            planned=[step.tool for step in state["plan"].steps if step.tool in handlers]
            if planned != list(handlers): raise ValueError("contract plan violates role tool order")
            for expected in planned:
                request=self.client.structured("contract_analyst",ToolRequest,{"allowed_tools":list(handlers),"expected_next":expected})
                if request.tool_name != expected: raise ValueError("contract analyst requested a disallowed or out-of-order tool")
                handlers[request.tool_name]()
        except Exception as exc: _failure(state,exc,"Contract analysis failed safely","contract_analyst")
        return state

class ComplianceAnalystAgent:
    def __init__(self, client): self.client=client
    def __call__(self, state):
        _event(state,"compliance_analyst","requested deterministic compliance tools")
        if state.get("error"): return state
        try:
            handlers={"load_demo_policies":lambda: state.__setitem__("policies",policies(state)),"run_deterministic_rules":lambda: state.__setitem__("findings",rules(state))}
            planned=[step.tool for step in state["plan"].steps if step.tool in handlers]
            if planned != list(handlers): raise ValueError("compliance plan violates role tool order")
            for expected in planned:
                request=self.client.structured("compliance_analyst",ToolRequest,{"allowed_tools":list(handlers),"expected_next":expected})
                if request.tool_name != expected: raise ValueError("compliance analyst requested a disallowed or out-of-order tool")
                handlers[request.tool_name]()
        except Exception as exc: _failure(state,exc,"Compliance analysis failed safely","compliance_analyst")
        return state

class IndependentReviewerAgent:
    def __init__(self, client): self.client=client
    def __call__(self, state):
        _event(state,"independent_reviewer","reviewed evidence completeness without changing findings")
        if state.get("error"):
            state["reviewer_decision"]=ReviewerDecision.FAIL; state["reviewer_feedback"]="Upstream controlled failure."; return state
        snapshot=[f.model_dump() for f in state.get("findings",[])]
        safe_findings=[{"policy_id":f["policy_id"],"status":str(f["status"]),"severity":str(f["severity"]),"page_number":f["page_number"],"clause_present":f["contract_clause"] is not None,"evidence_present":bool(f["evidence_text"])} for f in snapshot]
        context={"findings":safe_findings,"tool_events":[{"tool_name":e.tool_name,"success":e.success} for e in state.get("tool_events",[])],"available_pages":[p.page_number for p in state.get("pages",[])],"missing_findings":[{"policy_id":f["policy_id"],"page_number":f["page_number"],"has_clause":f["contract_clause"] is not None} for f in snapshot if str(f["status"])=="MISSING"],"graph_path":list(state.get("graph_path",[])),"retry_count":state["retry_count"],"max_retries":state["max_retries"]}
        try: result=self.client.structured("independent_reviewer",ReviewerResult,context)
        except Exception as exc:
            _failure(state,exc,"Reviewer output failed safely","independent_reviewer"); state["reviewer_decision"]=ReviewerDecision.FAIL; state["reviewer_feedback"]="Invalid structured reviewer output."; return state
        if [f.model_dump() for f in state["findings"]] != snapshot: raise RuntimeError("Reviewer cannot modify deterministic findings")
        if result.decision == ReviewerDecision.APPROVE and (len(snapshot)!=5 or any(f["page_number"] is not None for f in snapshot if str(f["status"])=="MISSING")):
            state["error"]="Reviewer approval rejected: incomplete evidence"; state["reviewer_decision"]=ReviewerDecision.FAIL
        else: state["reviewer_decision"]=result.decision
        state["reviewer_feedback"]=result.feedback
        if result.decision == ReviewerDecision.RETRY:
            if state["retry_count"] >= state["max_retries"]: state["route_status"]="RETRY_EXHAUSTED"
            else: state["retry_count"] += 1
        return state
