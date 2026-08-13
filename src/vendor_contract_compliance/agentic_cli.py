import argparse, os, sys
from pathlib import Path
from .agentic_graph import run_agentic
from .model_clients import ModelClientError, OpenAIModelClient, ScriptedModelClient

def safe_dir(value):
    raw=Path(value); root=Path.cwd().resolve(); resolved=raw.resolve()
    if raw.is_absolute() or resolved==root or root not in resolved.parents or (raw.exists() and raw.is_symlink()): raise argparse.ArgumentTypeError("output directory must be a safe relative path inside the current working directory")
    return resolved
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--contract",type=Path,required=True); p.add_argument("--policies",type=Path,required=True); p.add_argument("--output-dir",type=safe_dir,required=True); p.add_argument("--client",choices=["scripted","openai"],default="scripted"); p.add_argument("--scenario",choices=["success","retry","exhaustion"],default="success"); args=p.parse_args(argv)
    try:
        if args.client=="openai": client=OpenAIModelClient()
        else:
            decisions={"success":["APPROVE"],"retry":["RETRY","APPROVE"],"exhaustion":["RETRY","RETRY","RETRY"]}[args.scenario]; client=ScriptedModelClient(decisions)
        result=run_agentic(client,args.contract,args.policies,args.output_dir)
    except (ModelClientError,ValueError,OSError) as exc: print(f"Agentic audit failed: {exc}",file=sys.stderr); return 1
    print(f"Agentic audit: {result.route_status}; reviewer={result.reviewer_decision}; findings={len(result.findings)}; retries={result.retry_count}; client={result.client_type}")
    return 0 if result.route_status=="APPROVED" else 1
if __name__=="__main__": raise SystemExit(main())
