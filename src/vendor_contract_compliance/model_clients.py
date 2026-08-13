"""Model boundary: deterministic scripts for tests and OpenAI Responses for manual evidence."""
import os
from collections import deque
from typing import Literal, Protocol, TypeVar
from pydantic import BaseModel, ValidationError
from .agentic_models import ExecutionPlan, ReviewerResult, ToolRequest

T = TypeVar("T", bound=BaseModel)
SafeCode = Literal["OPENAI_INCOMPLETE", "OPENAI_REFUSAL", "OPENAI_INVALID_TOOL_CALL",
                   "OPENAI_SCHEMA_ERROR", "OPENAI_API_ERROR", "OPENAI_PLAN_ERROR"]
SAFE_INCOMPLETE_REASONS = {"max_output_tokens", "content_filter"}

class ModelClientError(RuntimeError):
    """An OpenAI boundary error containing diagnostics safe to persist and print."""
    def __init__(self, message: str, *, safe_code: SafeCode = "OPENAI_API_ERROR",
                 stage: str = "client", response_status: str | None = None,
                 incomplete_reason: str | None = None):
        super().__init__(message)
        self.safe_code = safe_code
        self.stage = stage
        self.response_status = response_status
        self.incomplete_reason = incomplete_reason

def _refused(response) -> bool:
    for item in getattr(response, "output", ()) or ():
        if getattr(item, "type", None) == "refusal":
            return True
        if any(getattr(part, "type", None) == "refusal" for part in (getattr(item, "content", ()) or ())):
            return True
    return False

def _check_response(response, stage: str) -> None:
    status = getattr(response, "status", None)
    if status == "incomplete":
        raw_reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
        reason = raw_reason if raw_reason in SAFE_INCOMPLETE_REASONS else None
        raise ModelClientError("OpenAI returned a refusal or incomplete response", safe_code="OPENAI_INCOMPLETE",
                               stage=stage, response_status="incomplete", incomplete_reason=reason)
    if _refused(response):
        raise ModelClientError("OpenAI response was refused", safe_code="OPENAI_REFUSAL",
                               stage=stage, response_status=status)
    if status != "completed":
        raise ModelClientError("OpenAI response did not complete", safe_code="OPENAI_API_ERROR",
                               stage=stage, response_status=status)

class ModelClient(Protocol):
    client_type: str
    model_name: str
    def structured(self, role: str, schema: type[T], context: dict) -> T: ...

PLAN = {"steps": [
    {"step":"Extract page-aware PDF text", "tool":"extract_pdf_pages"},
    {"step":"Extract explicit contract clauses", "tool":"extract_contract_clauses"},
    {"step":"Load validated demo policies", "tool":"load_demo_policies"},
    {"step":"Run immutable deterministic rules", "tool":"run_deterministic_rules"}]}

class ScriptedModelClient:
    client_type = "scripted"
    def __init__(self, reviewer_decisions=None, model_name="scripted-phase3", invalid_role=None, tool_requests=None, plan=None):
        self.model_name, self.invalid_role = model_name, invalid_role
        self.decisions = deque(reviewer_decisions or ["APPROVE"])
        self.tool_requests = deque(tool_requests or [])
        self.plan = plan or PLAN
        self.contexts = []
    def structured(self, role, schema, context):
        self.contexts.append((role, schema, context))
        if role == self.invalid_role: return schema.model_validate({"invalid":"redacted"})
        if schema is ExecutionPlan: data = self.plan
        elif schema is ToolRequest:
            allowed = context["allowed_tools"]
            data = {"tool_name": self.tool_requests.popleft() if self.tool_requests else context["expected_next"]}
        elif schema is ReviewerResult:
            decision = self.decisions.popleft() if self.decisions else "APPROVE"
            data = {"decision":decision, "feedback":"Evidence complete." if decision == "APPROVE" else "Re-run extraction to complete evidence."}
        else: raise ModelClientError("Unsupported structured schema")
        return schema.model_validate(data)

class OpenAIModelClient:
    client_type = "openai"
    def __init__(self, model_name=None, api_key=None):
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key: raise ModelClientError("OpenAI client is unavailable: key is not configured", stage="configuration")
        from openai import OpenAI
        self.model_name = model_name or os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")
        self._client = OpenAI(api_key=key)
    def structured(self, role, schema, context):
        # Responses structured parsing is used for plans/reviews; tool requests use an
        # equally strict function schema and disable parallel calls.
        try:
            if schema is ToolRequest:
                allowed = context["allowed_tools"]
                expected_next = context["expected_next"]
                if expected_next not in allowed:
                    raise ModelClientError("Expected plan tool is outside the role allowlist", safe_code="OPENAI_INVALID_TOOL_CALL", stage=role)
                instruction = (f"Role {role}: the next tool required by the validated ExecutionPlan is "
                    f"{expected_next}. Request that tool only from the supplied role tools.")
                response = self._client.responses.create(model=self.model_name, input=instruction,
                    tools=[{"type":"function","name":tool,"description":"Execute an allowed deterministic Phase 2 operation.","parameters":{"type":"object","properties":{},"additionalProperties":False},"strict":True} for tool in allowed],
                    tool_choice="required", parallel_tool_calls=False, max_output_tokens=2048,
                    reasoning={"effort":"low"})
                _check_response(response, role)
                calls = [item for item in response.output if item.type == "function_call"]
                if len(calls) != 1: raise ModelClientError("Invalid tool request", safe_code="OPENAI_INVALID_TOOL_CALL", stage=role, response_status=response.status)
                if calls[0].name not in allowed: raise ModelClientError("Tool request is outside the role allowlist", safe_code="OPENAI_INVALID_TOOL_CALL", stage=role, response_status=response.status)
                if calls[0].name != expected_next: raise ModelClientError("Tool request is outside the execution plan order", safe_code="OPENAI_INVALID_TOOL_CALL", stage=role, response_status=response.status)
                request = schema(tool_name=calls[0].name)
                return request
            response = self._client.responses.parse(model=self.model_name,
                input=f"Act as {role}. Return only the requested structured result. Context: {context}",
                text_format=schema, max_output_tokens=2048, reasoning={"effort":"low"})
            _check_response(response, role)
            if response.output_parsed is None: raise ModelClientError("OpenAI returned a refusal or incomplete structured response", safe_code="OPENAI_SCHEMA_ERROR", stage=role, response_status=response.status)
            return response.output_parsed
        except ModelClientError: raise
        except ValidationError as exc: raise ModelClientError("Invalid structured response", safe_code="OPENAI_SCHEMA_ERROR", stage=role) from None
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            detail = f"OpenAI SDK error: {type(exc).__name__}" + (f" (HTTP {status})" if isinstance(status, int) else "")
            raise ModelClientError(detail, safe_code="OPENAI_API_ERROR", stage=role,
                                   response_status=str(status) if isinstance(status, int) else None) from None
