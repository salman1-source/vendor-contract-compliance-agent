# Synthetic Vendor Contract Audit Report

- **Document:** `synthetic_vendor_contract.pdf`
- **Run time:** `2026-08-13T08:57:45.239160+00:00`
- **Policy versions:** POL-001=1.0, POL-002=1.0, POL-003=1.0, POL-004=1.0, POL-005=1.0

## Summary

| PASS | GAP | MISSING | REVIEW | Total |
|---:|---:|---:|---:|---:|
| 1 | 2 | 1 | 1 | 5 |

## Findings

### POL-001 — Confidentiality clause required

- **Status / severity:** PASS / LOW
- **Contract clause:** Confidentiality
- **Page:** 1
- **Evidence:** The Supplier shall keep all Customer confidential information confidential and use it only to provide
the demonstration services.
Synthetic fixture · Page 1
- **Reason:** The required confidentiality heading and obligation were found.
- **Recommended action:** No action required for this deterministic check.

### POL-002 — Minimum insurance coverage

- **Status / severity:** GAP / HIGH
- **Contract clause:** Insurance
- **Page:** 2
- **Evidence:** The Supplier shall maintain commercial insurance coverage of 1,000,000 SAR.
Synthetic fixture · Page 2
- **Reason:** Extracted coverage is 1,000,000 SAR; policy minimum is 5,000,000 SAR.
- **Recommended action:** Increase coverage to at least 5,000,000 SAR.

### POL-003 — Customer audit right required

- **Status / severity:** MISSING / HIGH
- **Contract clause:** Not found
- **Page:** Not applicable — clause absent
- **Evidence:** Required clause not found after scanning every extracted contract page and declared clause heading.
- **Reason:** The required customer audit-right heading was absent from all pages.
- **Recommended action:** Add an explicit customer right-to-audit clause for human review.

### POL-004 — Minimum termination notice

- **Status / severity:** GAP / MEDIUM
- **Contract clause:** Termination Notice
- **Page:** 3
- **Evidence:** Either party may terminate the demonstration arrangement by providing 15 days written notice.
Synthetic fixture · Page 3
- **Reason:** Extracted notice is 15 days; policy minimum is 30 days.
- **Recommended action:** Revise notice to at least 30 days.

### POL-005 — Data protection details required

- **Status / severity:** REVIEW / MEDIUM
- **Contract clause:** Data Protection
- **Page:** 4
- **Evidence:** The Supplier shall use reasonable safeguards to protect Customer data. No additional operational
details are stated in this clause.
Synthetic fixture · Page 4
- **Reason:** A general obligation exists, but deterministic checks did not find: incident notification, data retention. Human review is required; no final legal judgment is made.
- **Recommended action:** Have an authorized human review and add incident-notification and data-retention details.

## Disclaimer

SYNTHETIC DEMONSTRATION ONLY — NOT LEGAL ADVICE. This deterministic report does not approve or reject a contract; an authorized human must make all decisions.
