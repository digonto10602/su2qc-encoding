"""Seed circuits and programs of round 0 (prompts/203 section 3.1).  STUBS (step 6.3) except `LADDERS`, `general_circuit` and
`general_program_path`, which step 6.2 needs (the E1-E3 evaluator tests build their programs from them)."""
from __future__ import annotations

import pathlib

from su2plaq.rishon.compress._pending import pending

LADDERS = ("ccx", "rccx", "mcx")


def general_circuit(spec, ladder: str = "ccx"):
    """circuits.rishon.build_UE/UB/step(..., with_outer=True, ladder=ladder): the reference circuit for the spec's kind, order and
    angles (registers d, o, then the ancilla register).  `ladder` only matters for kinds with U_B."""
    from su2plaq.circuits import rishon as C

    if ladder not in LADDERS:
        raise ValueError(f"ladder must be one of {LADDERS}, got {ladder!r}")
    if spec.kind == "UE":
        return C.build_UE(spec.alpha, with_outer=True)
    if spec.kind == "UB":
        return C.build_UB(spec.beta, with_outer=True, ladder=ladder)
    return C.build_step(spec.alpha, spec.beta, spec.order, with_outer=True, ladder=ladder)


_LADDER_NUMBER = {"ccx": "000", "rccx": "001", "mcx": "002"}


def general_program_path(spec, ladder: str = "ccx") -> pathlib.Path:
    """compress/programs/rishon/seed/000-general[-<kind>].py (ccx), 001-general-rccx[-<kind>].py, 002-general-mcx[-<kind>].py,
    generated on first use by the laptop `program_source` (angle-linear; afterwards the file is immutable)."""
    from su2plaq.compress import baselines as LB
    from su2plaq.compress.spec import ROOT

    if ladder not in LADDERS:
        raise ValueError(f"ladder must be one of {LADDERS}, got {ladder!r}")
    base = "general" if ladder == "ccx" else f"general-{ladder}"
    path = ROOT / "compress" / "programs" / spec.encoding / LB.SEED_FAMILY / f"{_LADDER_NUMBER[ladder]}-{LB._stem(spec, base)}.py"
    if not path.exists():
        style = "" if ladder == "ccx" else f" with {ladder} control ladders"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(LB.program_source(lambda s: general_circuit(s, ladder), spec, summary=f"the reference circuit of the "
                        f"{spec.encoding} encoding ({spec.kind}){style} expressed through the Builder; every angle is a linear "
                        "function of spec.alpha / spec.beta."))
    return path


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
