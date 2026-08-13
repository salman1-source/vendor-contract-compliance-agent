"""Strict schemas and shared state for the Phase 3A graph."""
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, TypedDict
from pydantic import Field, model_validator
from .models import ContractPage, ExtractedClause, Finding, PolicyRule, StrictModel

ToolName = Literal["extract_pdf_pages", "extract_contract_clauses", "load_demo_policies", "run_deterministic_rules", "write_agentic_report"]

class PlanStep(StrictModel):
    step: str = Field(min_length=1)
    tool: ToolName

class ExecutionPlan(StrictModel):
    steps: list[PlanStep] = Field(min_length=4)

class ToolRequest(StrictModel):
    tool_name: ToolName

class ReviewerDecision(StrEnum):
    APPROVE = "APPROVE"
    RETRY = "RETRY"
    FAIL = "FAIL"

class ReviewerResult(StrictModel):
    decision: ReviewerDecision
    feedback: str = Field(min_length=1)

class ToolEvent(StrictModel):
    tool_name: ToolName
    requested_by: str
    started_at: datetime
    completed_at: datetime
    success: bool
    safe_input_summary: str
    safe_output_summary: str
    error_type: str | None = None

class AgentEvent(StrictModel):
    agent: str
    action: str
    occurred_at: datetime

class AgenticRunResult(StrictModel):
    run_id: str
    model_name: str
    client_type: Literal["scripted", "openai"]
    plan: ExecutionPlan
    graph_path: list[str]
    retry_count: int = Field(ge=0)
    max_retries: int = Field(ge=0)
    reviewer_decision: ReviewerDecision
    reviewer_feedback: str
    findings: list[Finding]
    tool_events: list[ToolEvent]
    agent_events: list[AgentEvent]
    route_status: str
    error: str | None = None
    disclaimer: str

    @model_validator(mode="after")
    def invariants(self):
        if self.retry_count > self.max_retries:
            raise ValueError("retry_count cannot exceed max_retries")
        if self.reviewer_decision == ReviewerDecision.APPROVE and len(self.findings) != 5:
            raise ValueError("APPROVE requires exactly five findings")
        return self

class AgentState(TypedDict, total=False):
    run_id: str; contract_path: str; policies_path: str; output_dir: str
    plan: ExecutionPlan; current_step: int; pages: list[ContractPage]
    clauses: dict[str, ExtractedClause]; policies: list[PolicyRule]; findings: list[Finding]
    tool_events: list[ToolEvent]; reviewer_decision: ReviewerDecision; reviewer_feedback: str
    retry_count: int; max_retries: int; route_status: str; error: str | None
    final_report_paths: list[str]; model_name: str; client_type: str
    agent_events: list[AgentEvent]; graph_path: list[str]
