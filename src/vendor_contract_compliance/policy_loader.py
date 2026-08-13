"""Safe YAML policy loading with Pydantic validation."""
from pathlib import Path

import yaml
from pydantic import TypeAdapter, ValidationError

from .models import PolicyRule


def load_policies(policy_path: Path) -> list[PolicyRule]:
    path = policy_path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Policy file does not exist: {policy_path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        policies = TypeAdapter(list[PolicyRule]).validate_python(raw)
    except (yaml.YAMLError, ValidationError) as exc:
        raise ValueError(f"Invalid policy file {policy_path}: {exc}") from exc
    if len(policies) != 5 or len({p.policy_id for p in policies}) != len(policies):
        raise ValueError("Demo policy file must contain exactly five uniquely identified policies")
    return sorted(policies, key=lambda policy: policy.policy_id)
