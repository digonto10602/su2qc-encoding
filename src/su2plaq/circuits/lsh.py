"""LSH circuits (prompts/400 section 2). STUB (step 7.0): builders raise NotImplementedError until steps 7.5-7.8.
Register order: d (12), o (12) if with_outer, then ancillas."""
from __future__ import annotations


def _pending(name: str, step: str):
    raise NotImplementedError(f"PENDING: su2plaq.circuits.lsh.{name} is not built yet (prompts/400 step {step})")


def build_UE(alpha, with_outer=False, include_outer_electric=False):
    _pending("build_UE", "7.5")


def build_UB(beta, with_outer=False):
    _pending("build_UB", "7.6")


def build_step(alpha, beta, order=1, with_outer=False):
    _pending("build_step", "7.7")


def wrap_spinnet(sn_qc, with_outer=False):
    _pending("wrap_spinnet", "7.8")
