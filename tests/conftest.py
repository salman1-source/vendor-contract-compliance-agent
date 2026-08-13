from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_synthetic_contract import generate


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def contract_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate the PDF in a missing temporary directory; never rely on a tracked binary."""
    path = tmp_path_factory.mktemp("synthetic-contract") / "nested" / "synthetic_vendor_contract.pdf"
    assert not path.parent.exists()
    generate(path)
    assert path.is_file()
    return path
