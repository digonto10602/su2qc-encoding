"""Import helper for the locked acceptance tests (LOCKED).

`api("su2plaq.exact.physical:physical_basis")` returns the attribute; `api("su2plaq.geometry")` returns the
module. A missing module/attribute fails the calling test with `PENDING: ...` (never a collection error).
Also holds small shared numerics used by several tests (no project imports here).
"""
from __future__ import annotations

import importlib

import numpy as np
import pytest


def api(dotted: str):
    mod_name, _, attr = dotted.partition(":")
    try:
        mod = importlib.import_module(mod_name)
    except ImportError as exc:
        pytest.fail(f"PENDING: cannot import {mod_name}: {exc}", pytrace=False)
    if not attr:
        return mod
    try:
        return getattr(mod, attr)
    except AttributeError:
        pytest.fail(f"PENDING: {mod_name} has no attribute {attr}", pytrace=False)


def op_norm_after_phase(A: np.ndarray, B: np.ndarray) -> float:
    """min over one global phase of ||A - e^{i phi} B||_2 with phi = arg tr(B^dag A)."""
    ov = np.trace(B.conj().T @ A)
    ph = ov / abs(ov) if abs(ov) > 1e-300 else 1.0
    return float(np.linalg.norm(A - ph * B, 2))


def ross_selinger_band(eps: float) -> tuple[float, float]:
    """Acceptance band for the T-count of one rz synthesised to precision eps (METHODS §7)."""
    L = 3 * np.log2(1 / eps)
    return L - 4, L + 3 * np.log2(np.log2(1 / eps)) + 10


# The two closed-plaquette labels of the route-A/route-B basis: ((j_0..j_11), (J_0..J_3)).
CLOSED_VACUUM = ((0.0,) * 12, (0.0,) * 4)
CLOSED_ALLHALF = ((0.5, 0.5, 0.5, 0.5) + (0.0,) * 8, (0.0,) * 4)
