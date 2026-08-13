"""Audited model boundary for scripted, OpenAI, OpenRouter, and Gemini clients."""
import json
import os
from collections import deque
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .agentic_models import ExecutionPlan, ReviewerResult, ToolRequest

T = TypeVar("T", bound=BaseModel)
SAFE_INCOMPLETE_REASONS = {"max_output_tokens", "content_filter"}
DEFAULT_MODELS = {
    "scripted": "scripted-phase3",
    "openai": "gpt-5.6-luna",
    "openrouter": "openai/gpt-5.6-luna",
    "gemini": "gemini-3.6-flash",
}
SECRET_NAMES = {"openai": "OPENAI_API_KEY", "openrouter": "OPENROUTER_API_KEY", "gemini": "GEMINI_API_KEY"}


class ModelClientError(RuntimeError):
    """A model-boundary error containing diagnostics safe to persist and print."""
    def __init__(self, message, *, safe_code="MODEL_API_ERROR", stage="client",
                 response_status=None, incomplete_reason=None):
        super().__init__(message)
        self.safe_code, self.stage = safe_code, stage
        self.response_status, self.incomplete_reason = response_status, incomplete_reason


class ModelClient(Protocol):
    client_type: str
    provider: str
    model_name: str
    def structured(self, role: str, schema: type[T], context: dict) -> T: ...


PLAN = {"steps": [
    {"step": "Extract page-aware PDF text", "tool": "extract_pdf_pages"},
    {"step": "Extract explicit contract clauses", "tool": "extract_contract_clauses"},
    {"step": "Load validated demo policies", "tool": "load_demo_policies"},
    {"step": "Run immutable deterministic rules", "tool": "run_deterministic_rules"}]}


class ScriptedModelClient:
    client_type = provider = "scripted"
    def __init__(self, reviewer_decisions=None, model_name=DEFAULT_MODELS["scripted"], invalid_role=None,
                 tool_requests=None, plan=None):
        self.model_name, self.invalid_role = model_name, invalid_role
        self.decisions = deque(reviewer_decisions or ["APPROVE"])
        self.tool_requests, self.plan, self.contexts = deque(tool_requests or []), plan or PLAN, []

    def structured(self, role, schema, context):
        self.contexts.append((role, schema, context))
        if role == self.invalid_role:
            return schema.model_validate({"invalid": "redacted"})
        if schema is ExecutionPlan:
            data = self.plan
        elif schema is ToolRequest:
            data = {"tool_name": self.tool_requests.popleft() if self.tool_requests else context["expected_next"]}
        elif schema is ReviewerResult:
            decision = self.decisions.popleft() if self.decisions else "APPROVE"
            data = {"decision": decision, "feedback": "Evidence complete." if decision == "APPROVE" else "Re-run extraction to complete evidence."}
        else:
            raise ModelClientError("Unsupported structured schema")
        return schema.model_validate(data)


def _refused(response):
    return any(getattr(item, "type", None) == "refusal" or
               any(getattr(part, "type", None) == "refusal" for part in (getattr(item, "content", ()) or ()))
               for item in (getattr(response, "output", ()) or ()))


class OpenAIModelClient:
    client_type = provider = "openai"
    default_model = DEFAULT_MODELS["openai"]
    secret_name = SECRET_NAMES["openai"]
    base_url = None

    def __init__(self, model_name=None, api_key=None, *, sdk_client=None):
        key = api_key or os.environ.get(self.secret_name)
        if not key and sdk_client is None:
            raise ModelClientError(f"{self.provider} client is unavailable: {self.secret_name} is not configured", stage="configuration")
        self.model_name = model_name or self.default_model
        if sdk_client is not None:
            self._client = sdk_client
        else:
            from openai import OpenAI
            kwargs = {"api_key": key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)

    def _check(self, response, stage):
        status = getattr(response, "status", None)
        prefix = self.provider.upper()
        if status == "incomplete":
            raw = getattr(getattr(response, "incomplete_details", None), "reason", None)
            message = "OpenAI returned a refusal or incomplete response" if self.provider == "openai" else f"{self.provider} returned an incomplete response"
            raise ModelClientError(message, safe_code=f"{prefix}_INCOMPLETE",
                                   stage=stage, response_status="incomplete",
                                   incomplete_reason=raw if raw in SAFE_INCOMPLETE_REASONS else None)
        if _refused(response):
            raise ModelClientError(f"{self.provider} response was refused", safe_code=f"{prefix}_REFUSAL", stage=stage,
                                   response_status=status)
        if status != "completed":
            raise ModelClientError(f"{self.provider} response did not complete", safe_code=f"{prefix}_API_ERROR",
                                   stage=stage, response_status=status)

    def structured(self, role, schema, context):
        prefix = self.provider.upper()
        try:
            if schema is ToolRequest:
                allowed, expected = context["allowed_tools"], context["expected_next"]
                if expected not in allowed:
                    raise ModelClientError("Expected plan tool is outside the role allowlist", safe_code=f"{prefix}_INVALID_TOOL_CALL", stage=role)
                response = self._client.responses.create(
                    model=self.model_name,
                    input=f"Role {role}: the next tool required by the validated ExecutionPlan is {expected}. Request that tool only from the supplied role tools.",
                    tools=[{"type": "function", "name": tool, "description": "Execute an allowed deterministic Phase 2 operation.",
                            "parameters": {"type": "object", "properties": {}, "additionalProperties": False}, "strict": True} for tool in allowed],
                    tool_choice="required", parallel_tool_calls=False, max_output_tokens=2048, reasoning={"effort": "low"})
                self._check(response, role)
                calls = [item for item in response.output if item.type == "function_call"]
                if len(calls) != 1:
                    raise ModelClientError("Invalid tool request", safe_code=f"{prefix}_INVALID_TOOL_CALL", stage=role, response_status=response.status)
                if calls[0].name not in allowed:
                    raise ModelClientError("Tool request is outside the role allowlist", safe_code=f"{prefix}_INVALID_TOOL_CALL", stage=role, response_status=response.status)
                if calls[0].name != expected:
                    raise ModelClientError("Tool request is outside the execution plan order", safe_code=f"{prefix}_INVALID_TOOL_CALL", stage=role, response_status=response.status)
                return schema(tool_name=calls[0].name)
            response = self._client.responses.parse(model=self.model_name,
                input=f"Act as {role}. Return only the requested structured result. Context: {context}",
                text_format=schema, max_output_tokens=2048, reasoning={"effort": "low"})
            self._check(response, role)
            if response.output_parsed is None:
                message = "OpenAI returned a refusal or incomplete structured response" if self.provider == "openai" else f"{self.provider} returned no structured result"
                raise ModelClientError(message, safe_code=f"{prefix}_SCHEMA_ERROR", stage=role,
                                       response_status=response.status)
            return schema.model_validate(response.output_parsed)
        except ModelClientError:
            raise
        except ValidationError:
            raise ModelClientError("Invalid structured response", safe_code=f"{prefix}_SCHEMA_ERROR", stage=role) from None
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            safe_status = str(status) if isinstance(status, int) else None
            detail = ((f"OpenAI SDK error: {type(exc).__name__}" if self.provider == "openai" else f"{self.provider} SDK request failed") +
                      (f" (HTTP {status})" if safe_status else ""))
            raise ModelClientError(detail,
                                   safe_code=f"{prefix}_API_ERROR", stage=role, response_status=safe_status) from None


class OpenRouterModelClient(OpenAIModelClient):
    client_type = provider = "openrouter"
    default_model = DEFAULT_MODELS["openrouter"]
    secret_name = SECRET_NAMES["openrouter"]
    base_url = "https://openrouter.ai/api/v1"


class GeminiModelClient:
    client_type = provider = "gemini"
    default_model = DEFAULT_MODELS["gemini"]

    def __init__(self, model_name=None, api_key=None, *, sdk_client=None):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key and sdk_client is None:
            raise ModelClientError("gemini client is unavailable: GEMINI_API_KEY is not configured", stage="configuration")
        self.model_name = model_name or self.default_model
        if sdk_client is not None:
            self._client = sdk_client
        else:
            from google import genai
            self._client = genai.Client(api_key=key)

    def structured(self, role, schema, context):
        try:
            common = {"model": self.model_name, "store": False,
                      "generation_config": {"max_output_tokens": 2048, "thinking_level": "low", "thinking_summaries": "none"}}
            if schema is ToolRequest:
                allowed, expected = context["allowed_tools"], context["expected_next"]
                if expected not in allowed:
                    raise ModelClientError("Expected plan function is outside the role allowlist", safe_code="GEMINI_INVALID_TOOL_CALL", stage=role)
                common["generation_config"]["tool_choice"] = "any"
                response = self._client.interactions.create(
                    input=f"Role {role}: request exactly the expected function {expected}; do not execute it.",
                    tools=[{"type": "function", "name": name, "description": "Request an allowed deterministic Phase 2 operation.",
                            "parameters": {"type": "object", "properties": {}, "additionalProperties": False}} for name in allowed], **common)
                self._check(response, role)
                calls = [item for item in (getattr(response, "outputs", None) or []) if getattr(item, "type", None) == "function_call"]
                if len(calls) != 1 or calls[0].name not in allowed or calls[0].name != expected:
                    raise ModelClientError("Invalid, unauthorized, or out-of-order function request", safe_code="GEMINI_INVALID_TOOL_CALL",
                                           stage=role, response_status=getattr(response, "status", None))
                return schema(tool_name=calls[0].name)
            response = self._client.interactions.create(
                input=f"Act as {role}. Return only the requested structured result. Context: {context}",
                response_format=schema.model_json_schema(), response_mime_type="application/json", **common)
            self._check(response, role)
            texts = [item.text for item in (getattr(response, "outputs", None) or []) if getattr(item, "type", None) == "text"]
            if len(texts) != 1:
                raise ModelClientError("Gemini returned no single structured result", safe_code="GEMINI_SCHEMA_ERROR", stage=role)
            return schema.model_validate_json(texts[0])
        except ModelClientError:
            raise
        except (ValidationError, json.JSONDecodeError):
            raise ModelClientError("Invalid structured response", safe_code="GEMINI_SCHEMA_ERROR", stage=role) from None
        except Exception as exc:
            status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            safe_status = str(status) if isinstance(status, int) else None
            raise ModelClientError("gemini SDK request failed" + (f" (HTTP {status})" if safe_status else ""),
                                   safe_code="GEMINI_API_ERROR", stage=role, response_status=safe_status) from None

    @staticmethod
    def _check(response, stage):
        status = getattr(response, "status", None)
        if status == "completed":
            return
        code = "GEMINI_INCOMPLETE" if status == "incomplete" else "GEMINI_API_ERROR"
        raise ModelClientError("Gemini response did not complete", safe_code=code, stage=stage, response_status=status)


def create_model_client(client_type, model_name=None, **kwargs):
    """Create only the explicitly selected provider; never attempts fallback."""
    clients = {"scripted": ScriptedModelClient, "openai": OpenAIModelClient,
               "openrouter": OpenRouterModelClient, "gemini": GeminiModelClient}
    if client_type not in clients:
        raise ModelClientError("Unknown model provider", safe_code="MODEL_CONFIGURATION_ERROR", stage="configuration")
    if client_type == "scripted":
        return clients[client_type](model_name=model_name or DEFAULT_MODELS[client_type], **kwargs)
    return clients[client_type](model_name=model_name, **kwargs)
