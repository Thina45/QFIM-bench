"""Run the uniform-start hardware campaign on ibm_marrakesh.

Five jobs: r=1, r=2, r=3, r=4, and a repeat of r=2. Predictions must already be in
campaigns/uniform_marrakesh/manifest.json (written with write_campaign_manifest).

    python examples/run_uniform_campaign.py            # dry run: transpile and report only
    python examples/run_uniform_campaign.py --submit   # real submission (uses QPU time)

Requires IBM_QUANTUM_TOKEN in the environment. Counts for each job are saved to
campaigns/uniform_marrakesh/<label>.json as soon as the job returns.
"""

import argparse
import json
from pathlib import Path

from qfim_bench.backends import HardwareBackend
from qfim_bench.circuit import build_grover_circuit

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "campaigns" / "uniform_marrakesh"
MANIFEST = CAMPAIGN / "manifest.json"

PLAN = [("r=1", 1), ("r=2", 2), ("r=3", 3), ("r=4", 4), ("r=2 (repeat)", 2)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submit", action="store_true", help="submit real jobs (default: dry run)")
    args = parser.parse_args()

    hb = HardwareBackend(dry_run=not args.submit, manifest_path=str(MANIFEST))
    for label, r in PLAN:
        qc, info = build_grover_circuit(5, 2, r, initial_state="uniform")
        hb.label = label
        if args.submit:
            result = hb.run(qc, shots=8192)
            out = CAMPAIGN / (label.replace(" ", "_").replace("(", "").replace(")", "").replace("=", "") + ".json")
            out.write_text(json.dumps({"label": label, "r": r, "counts": result.counts,
                                       "theoretical_p": info.theoretical_p}, indent=2), encoding="utf-8")
            emp = sum(c for b, c in result.counts.items() if b.count("1") >= 2) / 8192
            print(f"{label}: empirical {emp:.4f} vs theory {info.theoretical_p:.5f}  -> {out.name}")
        else:
            hb.run(qc, shots=8192)
            rep = hb.last_report
            print(f"{label}: transpiled depth {rep['transpiled_depth']}, gates {rep['transpiled_gates']}, "
                  f"2Q {rep['two_qubit_gates']} | target {rep['target']} | submitted {rep['submitted']}")


if __name__ == "__main__":
    main()
