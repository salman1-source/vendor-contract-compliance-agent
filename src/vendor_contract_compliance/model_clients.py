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
    def __init__(self, reviewer_decisions=None, model_name="scripted-phase3", invalid_role=None):
        self.model_name, self.invalid_role = model_name, invalid_role
        self.decisions = deque(reviewer_decisions or ["APPROVE"])
    def structured(self, role, schema, context):
        if role == self.invalid_role: return schema.model_validate({"invalid":"redacted"})
        if schema is ExecutionPlan: data = PLAN
        elif schema is ToolRequest: data = {"tool_name": context["tool_name"]}
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
                tool = context["tool_name"]
                response = self._client.responses.create(model=self.model_name, input=f"Role {role}: request only the required tool {tool}.",
                    tools=[{"type":"function","name":tool,"description":"Execute the required deterministic Phase 2 operation.","parameters":{"type":"object","properties":{},"additionalProperties":False},"strict":True}],
                    tool_choice={"type":"function","name":tool}, parallel_tool_calls=False, max_output_tokens=128)
                calls = [item for item in response.output if item.type == "function_call"]
                if response.status != "completed" or len(calls) != 1 or calls[0].name != tool: raise ModelClientError("OpenAI returned an incomplete or invalid tool request")
                return schema(tool_name=tool)
            response = self._client.responses.parse(model=self.model_name,
                input=f"Act as {role}. Return only the requested structured result. Context: {context}",
                text_format=schema, max_output_tokens=512)
            if response.status != "completed" or response.output_parsed is None: raise ModelClientError("OpenAI returned a refusal or incomplete structured response")
            return response.output_parsed
        except (ModelClientError, ValidationError): raise
        except Exception as exc: raise ModelClientError(f"OpenAI request failed safely ({type(exc).__name__})") from None
