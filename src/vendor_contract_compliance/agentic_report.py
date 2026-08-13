import json
from pathlib import Path
from .agentic_models import AgenticRunResult

DISCLAIMER="AI-assisted workflow — deterministic compliance findings — not legal advice."
def write_agentic_report(result: AgenticRunResult, output: Path):
    output.mkdir(parents=True,exist_ok=True)
    paths={"run":output/"agentic_run.json","report":output/"agentic_report.md","tools":output/"tool-events.json","agents":output/"agent-events.json"}
    paths["run"].write_text(json.dumps(result.model_dump(mode="json"),indent=2)+"\n")
    paths["tools"].write_text(json.dumps([x.model_dump(mode="json") for x in result.tool_events],indent=2)+"\n")
    paths["agents"].write_text(json.dumps([x.model_dump(mode="json") for x in result.agent_events],indent=2)+"\n")
    lines=["# Phase 3A Agentic Audit","",f"> {DISCLAIMER}","",f"- Provider: `{result.provider}`",f"- Model: `{result.model}`",f"- Client: `{result.client_type}`",f"- Route: `{' -> '.join(result.graph_path)}`",f"- Retries: {result.retry_count}",f"- Reviewer: **{result.reviewer_decision}**","","## Findings","","| Policy | Status | Severity | Page |","|---|---|---|---|"]
    lines += [f"| {f.policy_id} | {f.status} | {f.severity} | {f.page_number if f.page_number else '—'} |" for f in result.findings]
    paths["report"].write_text("\n".join(lines)+"\n")
    return [str(p) for p in paths.values()]
