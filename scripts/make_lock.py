"""Write requirements-lock.txt: exact versions of qfim-bench's runtime + test dependencies and their
whole dependency closure, taken from the current environment (the one the tests were run in).

    python scripts/make_lock.py
"""

import re
import sys
from importlib import metadata
from pathlib import Path

ROOTS = ["qiskit", "qiskit-aer", "qiskit-ibm-runtime", "numpy", "pandas", "scipy", "mlxtend", "pytest"]


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def closure(roots):
    seen, todo = {}, [norm(r) for r in roots]
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        try:
            dist = metadata.distribution(n)
        except metadata.PackageNotFoundError:
            continue
        seen[n] = dist.version
        for req in dist.requires or []:
            if "extra ==" in req:
                continue
            name = re.split(r"[ ;<>=!~\[(]", req.strip(), maxsplit=1)[0]
            todo.append(norm(name))
    return seen


def main() -> None:
    pins = closure(ROOTS)
    lines = [f"# Exact versions of qfim-bench's dependency closure, from the environment the tests were run in",
             f"# (Python {sys.version.split()[0]}). Regenerate with: python scripts/make_lock.py",
             "# Install: pip install -r requirements-lock.txt && pip install -e . --no-deps"]
    lines += [f"{n}=={v}" for n, v in sorted(pins.items())]
    out = Path(__file__).resolve().parents[1] / "requirements-lock.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(pins)} pins -> {out.name}")


if __name__ == "__main__":
    main()
