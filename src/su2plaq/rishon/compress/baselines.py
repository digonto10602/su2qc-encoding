"""Seed circuits and programs of round 0 (prompts/203 section 3.1).  STUBS (step 6.3); `LADDERS` is real."""
from __future__ import annotations

from su2plaq.rishon.compress._pending import pending

LADDERS = ("ccx", "rccx", "mcx")


def general_circuit(spec, ladder: str = "ccx"):
    """circuits.rishon.build_UE/UB/step(..., with_outer=True, ladder=ladder)."""
    raise pending("baselines.general_circuit", "6.3")


def general_program_path(spec, ladder: str = "ccx"):
    raise pending("baselines.general_program_path", "6.3")


def qiskit_l3(spec, seed: int = 12345, window: int = 32):
    raise pending("baselines.qiskit_l3", "6.3")


def qiskit_l3_whole(spec, seed: int = 12345):
    raise pending("baselines.qiskit_l3_whole", "6.3")


def polish(qc, spec):
    raise pending("baselines.polish", "6.3")


def general_polished(spec):
    raise pending("baselines.general_polished", "6.3")


def import_seed(spec, source: str) -> str:
    raise pending("baselines.import_seed", "6.3")
