from datetime import datetime, timezone
import json
from vendor_contract_compliance.pipeline import run_audit

def test_pipeline_writes_reports_and_is_deterministic(root, contract_path, tmp_path):
    fixed = datetime(2026, 8, 13, tzinfo=timezone.utc)
    args = (contract_path, root / "policies/demo_policies.yaml")
    first = run_audit(*args, tmp_path / "one", run_at=fixed)
    second = run_audit(*args, tmp_path / "two", run_at=fixed)
    assert first.model_dump() == second.model_dump()
    assert (tmp_path / "one/findings.json").read_bytes() == (tmp_path / "two/findings.json").read_bytes()
    assert (tmp_path / "one/audit_report.md").read_bytes() == (tmp_path / "two/audit_report.md").read_bytes()
    payload = json.loads((tmp_path / "one/findings.json").read_text())
    assert payload["summary"] == {"total": 5, "PASS": 1, "GAP": 2, "MISSING": 1, "REVIEW": 1}
    assert "NOT LEGAL ADVICE" in (tmp_path / "one/audit_report.md").read_text()
