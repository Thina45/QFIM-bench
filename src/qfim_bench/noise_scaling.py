"""
noise_scaling.py: a FakeMarrakesh whose error sources are scaled independently.

Used for the noise-sensitivity sweep: does the simulator discriminate weak from strong noise at the
sparse operating point, and which error source drives the loss of amplification?

The scaling acts on the backend's target before the Aer noise model is built from it:

  oneq      multiplies the reported error of every single-qubit gate
  twoq      multiplies the reported error of every two-qubit gate
  readout   multiplies the reported readout (measure) error
  relax     divides T1 and T2 by the factor, so 2 means twice the relaxation rate and 0 switches
            thermal relaxation off

A factor of 1 for all four is the unmodified FakeMarrakesh. Errors are capped below the
fully-depolarising value so every scaled gate stays a valid channel.
"""

from __future__ import annotations

from dataclasses import dataclass

ONEQ_NAMES = {"sx", "x", "rz", "id", "h"}
TWOQ_NAMES = {"cz", "ecr", "cx"}
MAX_ERROR = 0.75  # cap; the fully depolarising one-qubit error is 0.75, two-qubit 0.9375
HUGE_T = 1.0e9    # seconds; relaxation effectively off


@dataclass(frozen=True)
class NoiseScales:
    oneq: float = 1.0
    twoq: float = 1.0
    readout: float = 1.0
    relax: float = 1.0

    @classmethod
    def uniform(cls, s: float) -> "NoiseScales":
        return cls(s, s, s, s)


def scaled_fake_marrakesh(scales: NoiseScales = NoiseScales()):
    """A fresh FakeMarrakesh instance with the given error scalings applied to its target."""
    from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

    backend = FakeMarrakesh()
    target = backend.target

    for name in target.operation_names:
        if name in ("measure",):
            factor = scales.readout
        elif name in ONEQ_NAMES:
            factor = scales.oneq
        elif name in TWOQ_NAMES:
            factor = scales.twoq
        else:
            continue
        for qargs, props in target[name].items():
            if props is not None and props.error is not None:
                props.error = min(MAX_ERROR, props.error * factor)

    if scales.relax != 1.0:
        for qp in target.qubit_properties or []:
            if scales.relax == 0:
                qp.t1, qp.t2 = HUGE_T, HUGE_T
            else:
                if qp.t1 is not None:
                    qp.t1 = qp.t1 / scales.relax
                if qp.t2 is not None:
                    qp.t2 = qp.t2 / scales.relax
    return backend
