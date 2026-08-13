import os
import subprocess
import sys

def run_cli(root, *args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    return subprocess.run([sys.executable, "-m", "vendor_contract_compliance.cli", *args], cwd=root, env=env, text=True, capture_output=True)

def test_cli_success(root, contract_path, tmp_path):
    # pytest temp paths are outside the repository, so use a repository-local disposable directory.
    output = root / ".pytest-cli-output"
    result = run_cli(root, "--contract", str(contract_path), "--policies", "policies/demo_policies.yaml", "--output-dir", output.name)
    try:
        assert result.returncode == 0, result.stderr
        assert "PASS=1, GAP=2, MISSING=1, REVIEW=1" in result.stdout
        assert (output / "findings.json").is_file() and (output / "audit_report.md").is_file()
    finally:
        if output.exists():
            for child in output.iterdir(): child.unlink()
            output.rmdir()

def test_cli_missing_file_and_unsafe_output(root, contract_path):
    missing = run_cli(root, "--contract", "samples/missing.pdf", "--policies", "policies/demo_policies.yaml", "--output-dir", ".pytest-cli-output")
    assert missing.returncode == 1 and "does not exist" in missing.stderr
    unsafe = run_cli(root, "--contract", str(contract_path), "--policies", "policies/demo_policies.yaml", "--output-dir", "../outside")
    assert unsafe.returncode != 0 and "inside the current working directory" in unsafe.stderr
