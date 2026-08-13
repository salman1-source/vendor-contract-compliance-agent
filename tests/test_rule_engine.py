from vendor_contract_compliance.clause_extractor import extract_clauses
from vendor_contract_compliance.pdf_extractor import extract_pages
from vendor_contract_compliance.policy_loader import load_policies
from vendor_contract_compliance.rule_engine import evaluate_rules

def test_exact_findings_and_stable_order(root, contract_path):
    clauses = extract_clauses(extract_pages(contract_path))
    policies = load_policies(root / "policies/demo_policies.yaml")
    findings = evaluate_rules(clauses, list(reversed(policies)))
    assert policies[0].policy_id == "POL-001" and policies[0].severity.value == "HIGH"
    assert findings[0].status.value == "PASS" and findings[0].severity.value == "LOW"
    assert [(f.policy_id, f.status.value, f.severity.value, f.page_number) for f in findings] == [
        ("POL-001", "PASS", "LOW", 1), ("POL-002", "GAP", "HIGH", 2),
        ("POL-003", "MISSING", "HIGH", None), ("POL-004", "GAP", "MEDIUM", 3),
        ("POL-005", "REVIEW", "MEDIUM", 4),
    ]
    missing = findings[2]
    assert missing.contract_clause is None
    assert "not found after scanning every" in missing.evidence_text
