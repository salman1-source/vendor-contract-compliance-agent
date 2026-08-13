"""Command-line interface for the deterministic synthetic audit."""
import argparse
import sys
from pathlib import Path

from .pipeline import run_audit


def _safe_output_dir(value: str) -> Path:
    raw = Path(value)
    root = Path.cwd().resolve()
    resolved = raw.resolve()
    if raw.is_absolute() or resolved == root or root not in resolved.parents:
        raise argparse.ArgumentTypeError("output directory must be a relative path inside the current working directory")
    if raw.exists() and raw.is_symlink():
        raise argparse.ArgumentTypeError("output directory cannot be a symbolic link")
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit a synthetic vendor contract with deterministic rules (no AI).")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--policies", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=_safe_output_dir)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = run_audit(args.contract, args.policies, args.output_dir)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Audit failed: {exc}", file=sys.stderr)
        return 1
    summary = report.summary
    print(f"Audit complete: {summary.total} findings (PASS={summary.PASS}, GAP={summary.GAP}, MISSING={summary.MISSING}, REVIEW={summary.REVIEW})")
    print(f"Reports written to: {args.output_dir.relative_to(Path.cwd().resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
