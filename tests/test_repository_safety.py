import re


def test_repository_has_no_populated_keys_or_real_data(root):
    checked = [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts and p.suffix.lower() in {".py", ".md", ".yaml", ".toml", ".txt", ".example"}]
    content = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in checked)
    assert not re.search(r"(?im)^[A-Z_]*(?:API_KEY|TOKEN|SECRET)[ \t]*=[ \t]*\S+", content)
    assert not re.search(r"(?i)(?:s" + r"k-[A-Za-z0-9]{20,}|BEGIN [A-Z ]+ PRIVATE KEY)", content)
    assert not re.search(r"(?i)[A-Z0-9._%+-]+@(?:gmail|outlook|yahoo)\.[A-Z]{2,}", content)
