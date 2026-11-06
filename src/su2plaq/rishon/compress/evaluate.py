"""Rishon evaluator: trial / full mode, worker, cache, synthesised re-verification (prompts/203 section 3.1).  STUBS (step 6.2)."""
from __future__ import annotations

import numpy as np

from su2plaq.rishon.compress._pending import pending


def evaluate_circuit(qc, spec, mode="full", alt_circuits=None, *, program_sha256="", summary="", discoveries=(), t0=None):
    raise pending("evaluate.evaluate_circuit", "6.2")


def evaluate_program(path, spec, mode="full", *, cache=False, root=None):
    raise pending("evaluate.evaluate_program", "6.2")


def trial_states(spec) -> np.ndarray:
    raise pending("evaluate.trial_states", "6.2")


def verify_synthesised(qc, spec, eps=None) -> dict:
    raise pending("evaluate.verify_synthesised", "6.2")


def main(argv=None) -> int:
    """--worker <program> <specs.json> <out.qpy> <meta.json>"""
    raise pending("evaluate.main", "6.2")


if __name__ == "__main__":
    raise SystemExit(main())
