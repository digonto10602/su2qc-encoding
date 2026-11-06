"""Rishon compression loop (prompts/203 section 3.1).  Importing this package registers the encoding "rishon" with the laptop
machinery (`su2plaq.compress.spec`): `NOMINAL_ANGLES["rishon"]` and the compress view, as two runtime dict inserts (no laptop file
is edited).  Modules: spec, oracle, evaluate (built); baselines, brief, round, run_candidate (later steps: stubs raising
`NotImplementedError("PENDING: ...")`)."""
from __future__ import annotations

import pathlib

# provenance.EVALUATOR_FILES + the rishon files that decide a verdict (prompts/203 section 3.1); resolved under src/su2plaq
from su2plaq.compress import provenance as _provenance
from su2plaq.rishon.compress.spec import register

RISHON_EVALUATOR_FILES: list[str] = list(_provenance.EVALUATOR_FILES) + [
    "encodings/rishon.py", "circuits/rishon.py", "rishon/algebra.py", "rishon/physical.py", "rishon/operators.py",
    "rishon/frames.py", "rishon/verify.py", "rishon/compress/spec.py", "rishon/compress/evaluate.py",
    "rishon/compress/baselines.py",
]

register()      # idempotent side effect on import


def code_hash() -> str:
    """sha256 over RISHON_EVALUATOR_FILES (provenance.code_hash with the explicit list; files that do not exist are skipped)."""
    src = pathlib.Path(_provenance._SRC)
    return _provenance.code_hash([src / f for f in RISHON_EVALUATOR_FILES if (src / f).exists()])
