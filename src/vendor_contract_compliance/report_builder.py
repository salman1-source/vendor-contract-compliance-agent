"""Stable JSON and Markdown report rendering."""
import json
from pathlib import Path

from .models import AuditReport


def write_reports(report: AuditReport, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = output_dir / "findings.json", output_dir / "audit_report.md"
    json_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Synthetic Vendor Contract Audit Report", "", f"- **Document:** `{report.document_name}`", f"- **Run time:** `{report.run_at.isoformat()}`", f"- **Policy versions:** {', '.join(f'{key}={value}' for key, value in report.policy_versions.items())}", "", "## Summary", "", "| PASS | GAP | MISSING | REVIEW | Total |", "|---:|---:|---:|---:|---:|", f"| {report.summary.PASS} | {report.summary.GAP} | {report.summary.MISSING} | {report.summary.REVIEW} | {report.summary.total} |", "", "## Findings", ""]
    for finding in report.findings:
        page = str(finding.page_number) if finding.page_number is not None else "Not applicable — clause absent"
        clause = finding.contract_clause or "Not found"
        lines.extend([f"### {finding.policy_id} — {finding.policy_title}", "", f"- **Status / severity:** {finding.status.value} / {finding.severity.value}", f"- **Contract clause:** {clause}", f"- **Page:** {page}", f"- **Evidence:** {finding.evidence_text}", f"- **Reason:** {finding.reason}", f"- **Recommended action:** {finding.recommended_action}", ""])
    lines.extend(["## Disclaimer", "", report.disclaimer, ""])
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path
