"""Audited wrappers around the real deterministic Phase 2 functions."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from .agentic_models import ToolEvent
from .clause_extractor import extract_clauses
from .pdf_extractor import extract_pages
from .policy_loader import load_policies
from .rule_engine import evaluate_rules

def invoke(state, name: str, requested_by: str, fn: Callable):
    start = datetime.now(timezone.utc)
    try:
        value = fn()
        event = ToolEvent(tool_name=name, requested_by=requested_by, started_at=start, completed_at=datetime.now(timezone.utc), success=True,
            safe_input_summary="validated synthetic path or structured objects", safe_output_summary=f"{len(value)} structured records" if hasattr(value, "__len__") else "completed")
        state.setdefault("tool_events", []).append(event); return value
    except Exception as exc:
        state.setdefault("tool_events", []).append(ToolEvent(tool_name=name, requested_by=requested_by, started_at=start, completed_at=datetime.now(timezone.utc), success=False,
            safe_input_summary="validated synthetic path or structured objects", safe_output_summary="no output", error_type=type(exc).__name__))
        raise

def pdf_pages(s): return invoke(s,"extract_pdf_pages","contract_analyst",lambda:extract_pages(Path(s["contract_path"])))
def clauses(s): return invoke(s,"extract_contract_clauses","contract_analyst",lambda:extract_clauses(s["pages"]))
def policies(s): return invoke(s,"load_demo_policies","compliance_analyst",lambda:load_policies(Path(s["policies_path"])))
def rules(s): return invoke(s,"run_deterministic_rules","compliance_analyst",lambda:evaluate_rules(s["clauses"],s["policies"]))
