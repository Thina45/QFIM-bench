"""
config.py — single configuration object for qfim-bench. Every run
parameter lives here; no module downstream of this one should hardcode a
dataset path, item count, threshold, or shot count.

initial_state defaults to "uniform" for the public software release
(see the README "Start state" section). "uniform"
reproduces Eq. (4)'s theoretical success-probability curve exactly on
simulators — this is the claim the package can verify end-to-end without
any hardware run. "ansatz" (the companion paper's actual hardware-circuit
start state) remains fully supported for anyone who wants to reproduce the
paper's own circuit, but it is no longer the default, since its flat,
noiseless-but-still-flat behaviour is not representative of the
Grover-amplification result this package is built to demonstrate and
would otherwise be mistaken for a simulator bug.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QFIMConfig:
    dataset_path: str
    top_k_items: int = 5
    oracle_threshold: int = 2       # Hamming-weight threshold t
    grover_iterations: int | None = 2  # r; None means r_opt = floor(pi/(4 theta)) from the classically known M
    shots: int = 8192
    min_support: float = 0.05       # sigma_min (post-processing threshold)
    alpha: float = 0.1              # post-processing threshold factor
    ansatz_reps: int = 1            # EfficientSU2 repetitions (only used if initial_state="ansatz")
    initial_state: str = "uniform"  # "uniform" (H^n) or "ansatz" (bound EfficientSU2)
    diffusion: str = "matched"      # "matched" (correct for any start) or "hadamard" (mismatched for the ansatz)
    marking: str = "support"        # "support" (data-driven, primary), "cardinality" (v1), or "explicit"
    marked_states: tuple[int, ...] | None = None  # basis-state indices, used only when marking="explicit"
    backend: str = "aer_simulator"  # resolved via backends.get_backend()
    seed: int = 42

    def __post_init__(self):
        if self.top_k_items < 1:
            raise ValueError("top_k_items must be >= 1")
        if not (0 <= self.oracle_threshold <= self.top_k_items):
            raise ValueError("oracle_threshold must be between 0 and top_k_items")
        if self.grover_iterations is not None and self.grover_iterations < 0:
            raise ValueError("grover_iterations must be >= 0 or None")
        if self.shots < 1:
            raise ValueError("shots must be >= 1")
        if not (0 < self.min_support <= 1):
            raise ValueError("min_support must be in (0, 1]")
        if not (0 < self.alpha <= 1):
            raise ValueError("alpha must be in (0, 1]")
        if self.ansatz_reps < 1:
            raise ValueError("ansatz_reps must be >= 1")
        if self.initial_state not in ("uniform", "ansatz"):
            raise ValueError('initial_state must be "uniform" or "ansatz"')
        if self.diffusion not in ("matched", "hadamard"):
            raise ValueError('diffusion must be "matched" or "hadamard"')
        if self.marking not in ("support", "cardinality", "explicit"):
            raise ValueError('marking must be "support", "cardinality" or "explicit"')
        if self.marking == "explicit" and not self.marked_states:
            raise ValueError('marking="explicit" requires marked_states')
