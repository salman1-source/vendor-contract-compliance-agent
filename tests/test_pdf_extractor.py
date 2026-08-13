from vendor_contract_compliance.clause_extractor import extract_clauses
from vendor_contract_compliance.pdf_extractor import extract_pages

def test_page_text_and_known_clause_locations(contract_path):
    pages = extract_pages(contract_path)
    assert [page.page_number for page in pages] == [1, 2, 3, 4]
    assert all("SYNTHETIC DEMONSTRATION DOCUMENT" in page.text for page in pages)
    clauses = extract_clauses(pages)
    assert {name: clause.page_number for name, clause in clauses.items()} == {
        "Confidentiality": 1, "Insurance": 2, "Termination Notice": 3, "Data Protection": 4
    }
    assert "Audit Right" not in clauses
