"""Page-aware PDF text extraction."""
from pathlib import Path

import pymupdf

from .models import ContractPage


def extract_pages(pdf_path: Path) -> list[ContractPage]:
    path = pdf_path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Contract PDF does not exist: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Contract must have a .pdf extension: {pdf_path}")
    try:
        with pymupdf.open(path) as document:
            if not document.is_pdf:
                raise ValueError(f"Contract is not a valid PDF: {pdf_path}")
            return [ContractPage(page_number=i + 1, text=page.get_text().strip()) for i, page in enumerate(document)]
    except pymupdf.FileDataError as exc:
        raise ValueError(f"Unable to read contract PDF: {pdf_path}") from exc
