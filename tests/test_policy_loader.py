import pytest
from vendor_contract_compliance.policy_loader import load_policies

def test_loads_five_valid_sorted_policies(root):
    policies = load_policies(root / "policies/demo_policies.yaml")
    assert [p.policy_id for p in policies] == [f"POL-00{i}" for i in range(1, 6)]

def test_rejects_invalid_policy(tmp_path):
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("- policy_id: nope\n  title: incomplete\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid policy"):
        load_policies(invalid)
