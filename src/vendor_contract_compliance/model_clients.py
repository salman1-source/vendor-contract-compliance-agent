"""Model boundary: deterministic scripts for tests and OpenAI Responses for manual evidence."""
import os
from collections import deque
from typing import Protocol, TypeVar
from pydantic import BaseModel, ValidationError
from .agentic_models import ExecutionPlan, ReviewerResult, ToolRequest

T = TypeVar("T", bound=BaseModel)
class ModelClientError(RuntimeError): pass

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
        if not key: raise ModelClientError("OpenAI client is unavailable: OPENAI_API_KEY is not configured")
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
                    raise ModelClientError("Expected plan tool is outside the role allowlist")
                instruction = (f"Role {role}: the next tool required by the validated ExecutionPlan is "
                    f"{expected_next}. Request that tool only from the supplied role tools.")
                response = self._client.responses.create(model=self.model_name, input=instruction,
                    tools=[{"type":"function","name":tool,"description":"Execute an allowed deterministic Phase 2 operation.","parameters":{"type":"object","properties":{},"additionalProperties":False},"strict":True} for tool in allowed],
                    tool_choice="required", parallel_tool_calls=False, max_output_tokens=128)
                calls = [item for item in response.output if item.type == "function_call"]
                if response.status != "completed" or len(calls) != 1: raise ModelClientError("OpenAI returned a refusal, incomplete, or invalid tool request")
                if calls[0].name not in allowed: raise ModelClientError("OpenAI requested a tool outside the role allowlist")
                if calls[0].name != expected_next: raise ModelClientError("OpenAI requested an allowed tool outside the execution plan order")
                request = schema(tool_name=calls[0].name)
                return request
            response = self._client.responses.parse(model=self.model_name,
                input=f"Act as {role}. Return only the requested structured result. Context: {context}",
                text_format=schema, max_output_tokens=512)
            if response.status != "completed" or response.output_parsed is None: raise ModelClientError("OpenAI returned a refusal or incomplete structured response")
            return response.output_parsed
        except (ModelClientError, ValidationError): raise
        except Exception as exc: raise ModelClientError(f"OpenAI request failed safely ({type(exc).__name__})") from None
