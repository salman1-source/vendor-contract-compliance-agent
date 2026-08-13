"""End-to-end deterministic audit orchestration (not an AI agent)."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .clause_extractor import extract_clauses
from .models import AuditReport, AuditSummary
from .pdf_extractor import extract_pages
from .policy_loader import load_policies
from .report_builder import write_reports
from .rule_engine import evaluate_rules

DISCLAIMER = "SYNTHETIC DEMONSTRATION ONLY — NOT LEGAL ADVICE. This deterministic report does not approve or reject a contract; an authorized human must make all decisions."


def run_audit(contract: Path, policies_path: Path, output_dir: Path, *, run_at: datetime | None = None) -> AuditReport:
    pages = extract_pages(contract)
    policies = load_policies(policies_path)
    findings = evaluate_rules(extract_clauses(pages), policies)
    counts = Counter(f.status.value for f in findings)
    report = AuditReport(document_name=contract.name, run_at=run_at or datetime.now(timezone.utc),
        policy_versions={p.policy_id: p.version for p in policies},
        summary=AuditSummary(total=len(findings), PASS=counts["PASS"], GAP=counts["GAP"], MISSING=counts["MISSING"], REVIEW=counts["REVIEW"]),
        findings=findings, disclaimer=DISCLAIMER)
    write_reports(report, output_dir)
    return report
