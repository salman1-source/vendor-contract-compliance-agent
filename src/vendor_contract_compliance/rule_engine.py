"""Deterministic rules for the five declared synthetic policies."""
import re

from .models import ExtractedClause, Finding, FindingStatus, PolicyRule, Severity

MISSING_EVIDENCE = "Required clause not found after scanning every extracted contract page and declared clause heading."


def _finding(policy: PolicyRule, status: FindingStatus, clause: ExtractedClause | None, reason: str, action: str) -> Finding:
    return Finding(
        finding_id=f"F-{policy.policy_id}", policy_id=policy.policy_id, policy_title=policy.title,
        # Policy severity describes the risk of noncompliance; a satisfied rule has LOW finding severity.
        status=status, severity=Severity.LOW if status == FindingStatus.PASS else policy.severity,
        contract_clause=clause.title if clause else None,
        evidence_text=clause.text if clause else MISSING_EVIDENCE,
        page_number=clause.page_number if clause else None,
        reason=reason, recommended_action=action,
    )


def evaluate_rules(clauses: dict[str, ExtractedClause], policies: list[PolicyRule]) -> list[Finding]:
    findings: list[Finding] = []
    for policy in sorted(policies, key=lambda item: item.policy_id):
        heading = str(policy.parameters["heading"])
        clause = clauses.get(heading)
        if policy.policy_id in {"POL-001", "POL-003"}:
            status = FindingStatus.PASS if clause else FindingStatus.MISSING
            reason = "The required confidentiality heading and obligation were found." if clause else "The required customer audit-right heading was absent from all pages."
            action = "No action required for this deterministic check." if clause else "Add an explicit customer right-to-audit clause for human review."
        elif policy.policy_id == "POL-002":
            if clause is None:
                status, reason, action = FindingStatus.MISSING, "The required insurance clause was absent.", "Add an insurance clause."
            else:
                match = re.search(r"coverage of\s+([\d,]+)\s+SAR\b", clause.text, re.IGNORECASE)
                if not match:
                    status, reason, action = FindingStatus.REVIEW, "Insurance amount could not be deterministically extracted.", "Have a human verify the coverage amount."
                else:
                    actual, required = int(match.group(1).replace(",", "")), int(policy.parameters["minimum_amount"])
                    status = FindingStatus.PASS if actual >= required else FindingStatus.GAP
                    reason = f"Extracted coverage is {actual:,} SAR; policy minimum is {required:,} SAR."
                    action = "No action required." if status == FindingStatus.PASS else f"Increase coverage to at least {required:,} SAR."
        elif policy.policy_id == "POL-004":
            if clause is None:
                status, reason, action = FindingStatus.MISSING, "The required termination notice clause was absent.", "Add a termination notice clause."
            else:
                match = re.search(r"providing\s+(\d+)\s+days written notice\b", clause.text, re.IGNORECASE)
                if not match:
                    status, reason, action = FindingStatus.REVIEW, "Notice days could not be deterministically extracted.", "Have a human verify the notice period."
                else:
                    actual, required = int(match.group(1)), int(policy.parameters["minimum_days"])
                    status = FindingStatus.PASS if actual >= required else FindingStatus.GAP
                    reason = f"Extracted notice is {actual} days; policy minimum is {required} days."
                    action = "No action required." if status == FindingStatus.PASS else f"Revise notice to at least {required} days."
        elif policy.policy_id == "POL-005":
            if clause is None:
                status, reason, action = FindingStatus.MISSING, "The required data protection clause was absent.", "Add a data protection clause."
            else:
                lower = clause.text.lower()
                details = [str(item).lower() for item in policy.parameters["required_details"]]
                missing = [item for item in details if item not in lower]
                status = FindingStatus.PASS if not missing else FindingStatus.REVIEW
                reason = "All declared details were found." if not missing else f"A general obligation exists, but deterministic checks did not find: {', '.join(missing)}. Human review is required; no final legal judgment is made."
                action = "No action required." if not missing else "Have an authorized human review and add incident-notification and data-retention details."
        else:
            raise ValueError(f"Unsupported policy ID: {policy.policy_id}")
        findings.append(_finding(policy, status, clause, reason, action))
    return findings
