#!/usr/bin/env python3
from pathlib import Path
from vendor_contract_compliance.agentic_graph import build_graph, run_agentic
from vendor_contract_compliance.model_clients import ScriptedModelClient
from generate_synthetic_contract import generate
ROOT=Path(__file__).resolve().parents[1]; pdf=ROOT/"samples/synthetic_vendor_contract.pdf"; generate(pdf); base=ROOT/"evidence/phase3"
for name, decisions in {"mock-success":["APPROVE"],"mock-retry":["RETRY","APPROVE"],"mock-exhaustion":["RETRY","RETRY","RETRY"]}.items(): run_agentic(ScriptedModelClient(decisions),pdf,ROOT/"policies/demo_policies.yaml",base/name)
(base/"graph.mmd").write_text(build_graph(ScriptedModelClient()).compile().get_graph().draw_mermaid().rstrip()+"\n")
