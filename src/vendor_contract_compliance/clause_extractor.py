"""Explicit heading-based extraction for the synthetic fixture."""
import re

from .models import ContractPage, ExtractedClause

HEADINGS = ("Confidentiality", "Insurance", "Audit Right", "Termination Notice", "Data Protection")


def extract_clauses(pages: list[ContractPage]) -> dict[str, ExtractedClause]:
    clauses: dict[str, ExtractedClause] = {}
    heading_pattern = re.compile(r"^(?:\d+\.\s*)?(" + "|".join(map(re.escape, HEADINGS)) + r")\s*$", re.MULTILINE)
    for page in pages:
        matches = list(heading_pattern.finditer(page.text))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(page.text)
            title = match.group(1)
            body = page.text[match.end():end].strip()
            if body:
                clauses[title] = ExtractedClause(title=title, text=body, page_number=page.page_number)
    return clauses
