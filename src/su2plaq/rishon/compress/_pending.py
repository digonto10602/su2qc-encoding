"""Stub marker for step 6.0 (prompts/203 section 5): every not-yet-built name raises `NotImplementedError("PENDING: ...")`,
so the locked acceptance tests report `PENDING:` (the same word the `tests/acceptance/_api.py` helper uses)."""
from __future__ import annotations


def pending(name: str, step: str) -> NotImplementedError:
    return NotImplementedError(f"PENDING: su2plaq.rishon.compress.{name} is a stub (prompts/203 step {step})")
