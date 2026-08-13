#!/usr/bin/env python3
"""Reproducibly generate the non-real Phase 2 PDF fixture."""
from pathlib import Path

import pymupdf

BANNER = "SYNTHETIC DEMONSTRATION DOCUMENT — NOT A REAL CONTRACT"
PAGES = [
    ("1. Confidentiality", "The Supplier shall keep all Customer confidential information confidential and use it only to provide the demonstration services."),
    ("2. Insurance", "The Supplier shall maintain commercial insurance coverage of 1,000,000 SAR."),
    ("3. Termination Notice", "Either party may terminate the demonstration arrangement by providing 15 days written notice."),
    ("4. Data Protection", "The Supplier shall use reasonable safeguards to protect Customer data. No additional operational details are stated in this clause."),
]


def generate(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open()
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    if not font_path.is_file():
        raise FileNotFoundError(f"Required reproducible Unicode font is unavailable: {font_path}")
    metadata = {"title": "Synthetic Vendor Contract", "author": "Phase 2 deterministic fixture", "subject": BANNER}
    document.set_metadata(metadata)
    for page_number, (heading, body) in enumerate(PAGES, start=1):
        page = document.new_page(width=595, height=842)
        page.insert_font(fontname="dejavu", fontfile=str(font_path))
        page.insert_text((50, 55), BANNER, fontsize=9, fontname="dejavu")
        page.insert_text((50, 105), "Synthetic Vendor Services Demonstration", fontsize=18, fontname="helv")
        page.insert_text((50, 155), heading, fontsize=14, fontname="helv")
        page.insert_textbox(pymupdf.Rect(50, 185, 545, 500), body, fontsize=11, fontname="helv")
        page.insert_text((50, 800), f"Synthetic fixture — Page {page_number}", fontsize=9, fontname="helv")
    # Fixed metadata and deterministic object creation make identical inputs byte reproducible.
    document.save(output, garbage=4, deflate=True, clean=True, no_new_id=True)
    document.close()


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[1] / "samples" / "synthetic_vendor_contract.pdf")
