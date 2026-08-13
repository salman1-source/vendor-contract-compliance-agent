"""Validated data structures shared by the deterministic pipeline."""
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FindingStatus(StrEnum):
    PASS = "PASS"
    GAP = "GAP"
    MISSING = "MISSING"
    REVIEW = "REVIEW"


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ContractPage(StrictModel):
    page_number: int = Field(ge=1)
    text: str


class ExtractedClause(StrictModel):
    title: str
    text: str
    page_number: int = Field(ge=1)


class PolicyRule(StrictModel):
    policy_id: str = Field(pattern=r"^POL-\d{3}$")
    title: str
    description: str
    rule_type: str
    required: bool
    severity: Severity
    parameters: dict[str, Any]
    version: str


class Finding(StrictModel):
    finding_id: str
    policy_id: str
    policy_title: str
    status: FindingStatus
    severity: Severity
    contract_clause: str | None
    evidence_text: str
    page_number: int | None
    reason: str
    recommended_action: str

    @model_validator(mode="after")
    def missing_has_no_location(self) -> "Finding":
        if self.status == FindingStatus.MISSING:
            if self.page_number is not None or self.contract_clause is not None:
                raise ValueError("MISSING findings cannot cite a page or contract clause")
            if "not found" not in self.evidence_text.lower():
                raise ValueError("MISSING evidence must explicitly record the unsuccessful search")
        return self


class AuditSummary(StrictModel):
    total: int
    PASS: int
    GAP: int
    MISSING: int
    REVIEW: int


class AuditReport(StrictModel):
    document_name: str
    run_at: datetime
    policy_versions: dict[str, str]
    summary: AuditSummary
    findings: list[Finding]
    disclaimer: str
