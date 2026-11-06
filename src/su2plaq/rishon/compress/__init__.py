"""Rishon compression loop (prompts/203 section 3.1).  STUB package (step 6.0): the names exist, the bodies raise
`NotImplementedError("PENDING: ...")`.  Step 6.1 adds the import-time registration
(`from su2plaq.rishon.compress.spec import register; register()`) once `register` is implemented."""
from __future__ import annotations

from su2plaq.rishon.compress._pending import pending

# provenance.EVALUATOR_FILES + the rishon files that decide a verdict (prompts/203 section 3.1); resolved under src/su2plaq
from su2plaq.compress.provenance import EVALUATOR_FILES as _LAPTOP_EVALUATOR_FILES

RISHON_EVALUATOR_FILES: list[str] = list(_LAPTOP_EVALUATOR_FILES) + [
    "encodings/rishon.py", "circuits/rishon.py", "rishon/algebra.py", "rishon/physical.py", "rishon/operators.py",
    "rishon/frames.py", "rishon/verify.py", "rishon/compress/spec.py", "rishon/compress/evaluate.py",
    "rishon/compress/baselines.py",
]


def code_hash() -> str:
    """sha256 over RISHON_EVALUATOR_FILES (provenance.code_hash with the explicit list)."""
    raise pending("code_hash", "6.1")
