"""EXPLORATORY (not preregistered): per-two-qubit-gate fidelity from the echo circuits.

Model: P_echo = f^g * (1 - 2^-n) + 2^-n, i.e. a fully decohered register returns all-zeros with the
uniform floor 2^-n, and the coherent part decays as f per two-qubit gate (g = transpiled 2Q count of
the echo circuit). So f = ((P - 2^-n) / (1 - 2^-n))^(1/g). The interval is the 95% t-interval of P
across the 5 runs pushed through the same monotone transform; where the lower end of P is at or below
the floor, f has no lower bound (reported as None). Compared with the Grover-curve fits and the
simulator's value. Also tabulates the simulator-minus-hardware shortfall at r=1,2.

    python analysis/echo_fidelity_exploratory.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "results" / "hardware"
SIM_F = 0.9967


def f_from_echo(p: float, n: int, g: float):
    floor = 2.0**-n
    x = (p - floor) / (1 - floor)
    return None if x <= 0 else x ** (1.0 / g)


def main() -> None:
    a = json.loads((HW / "ladder_v2" / "analysis.json").read_text())
    b = json.loads((HW / "ladder_v2b" / "analysis.json").read_text())
    tiers = {3: (a["rows"], a["fit"]["f_per_2q_hw"]), 4: (b["B"]["rows"], b["B"]["fit"]["f"]),
             5: (b["C"]["rows"], b["C"]["fit"]["f"])}
    out = {"status": "EXPLORATORY - not preregistered", "echo": [], "shortfall": []}
    for n, (rows, grover_f) in tiers.items():
        e = next(r for r in rows if r["id"].startswith("echo"))
        g = e["two_qubit_gates"]
        lo, hi = e["t_ci95"]
        rec = {"n": n, "echo_2q_gates": g, "P_echo": e["mean"], "P_ci95": [lo, hi], "floor": 2.0**-n,
               "f_echo": f_from_echo(e["mean"], n, g),
               "f_ci95": [f_from_echo(lo, n, g), f_from_echo(hi, n, g)],
               "f_grover_fit": grover_f, "f_simulator": SIM_F}
        out["echo"].append(rec)
        fe = rec["f_echo"]
        lo_f = rec["f_ci95"][0]
        print(f"n={n}: echo P={e['mean']:.3f} (floor {2.0**-n:.3f}), g={g:.0f}  f_echo={fe:.5f} "
              f"[{'none' if lo_f is None else format(lo_f, '.5f')},{rec['f_ci95'][1]:.5f}]  Grover fit {grover_f:.5f}  sim {SIM_F}")
        for r in rows:
            if r["id"].startswith("ladder") and r["id"].rsplit("_r", 1)[1] in ("1", "2"):
                out["shortfall"].append({"id": r["id"], "simulator_minus_hardware": r["prediction"] - r["mean"],
                                         "prediction": r["prediction"], "hardware": r["mean"]})
    for s in out["shortfall"]:
        print(f"shortfall {s['id']:18s} sim {s['prediction']:.3f} - hw {s['hardware']:.3f} = {s['simulator_minus_hardware']:.3f}")
    vals = [s["simulator_minus_hardware"] for s in out["shortfall"]]
    out["shortfall_range_r1_r2"] = [min(vals), max(vals)]
    r2 = [s["simulator_minus_hardware"] for s in out["shortfall"] if s["id"].endswith("_r2")]
    out["shortfall_range_r2_only"] = [min(r2), max(r2)]
    print(f"shortfall range (r=1,2 all sizes): {min(vals):.3f} to {max(vals):.3f}; r=2 only: {min(r2):.3f} to {max(r2):.3f}")
    (HW / "echo_fidelity_exploratory.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
