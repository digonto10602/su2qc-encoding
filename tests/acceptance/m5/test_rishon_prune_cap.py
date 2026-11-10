"""M5-V2 — the rishon prune cap (prompts/204 section 3; Digonto's decision 2026-11-10: 10 % of tol_err for this encoding).

Rule.  The certified bound op_norm_error = block_error + leak_amplitude + dropped_total <= tol_err is unchanged and rigorous for
any amount of simulator pruning (prompts/004, prompts/005 section 1-2).  The separate rejection `pruning_bound` (the share of
the budget the sparse engine itself may spend) is, for rishon verdicts only,
    dropped_total > RISHON_PRUNE_FRACTION * tol_err ,   RISHON_PRUNE_FRACTION = 0.1   (shared evaluator: 0.01, untouched).
It is applied inside `su2plaq.rishon.verify.verify` by re-judging a `pruning_bound` verdict of the shared evaluator with the
shared evaluator's own cascade (cap, leak, error, Gauss); every other verdict is passed through.  No shared file changes.

Test circuit: the general U_B(0.61) with relative-phase Toffoli ladders (`ladder="rccx"`): physically exact (block error
3.4e-13) with dropped_total 2.3e-12 measured (reports/tests/204 N1, prompts/203 section 13 E2 table) -- between the two caps
1e-12 and 1e-11 with factors 2.3 and 4.4 of margin.  The threshold itself is pinned at +-10 % around the measured value."""
import functools

import numpy as np
import pytest

from tests.acceptance._api import api

TOL_ERR = 1e-10
BETA = 0.61


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.rishon:RishonEncoding")()


def test_M5_V2_rishon_prune_cap():
    """RISHON_PRUNE_FRACTION == 0.1; the shared constant is still 0.01; the rccx-ladder U_B is `ok` and certified under the
    rishon cap with 1e-12 < dropped_total <= 1e-11 and the full budget op_norm_error <= 1e-10, the shared evaluator's own verdict
    (kept in `inner_verdict`) is `pruning_bound`, and `extra` records the cap; with prune_fraction = 0.01 the old verdict is
    reproduced; the cap sits exactly at prune_fraction * tol_err (0.9 x and 1.1 x the measured bound); a fraction below the
    shared one is refused; the ccx-ladder circuit (dropped 3e-13) is `ok` under both caps."""
    enc = _enc()
    Vf = api("su2plaq.rishon.verify")
    C = api("su2plaq.circuits.rishon")
    frac = api("su2plaq.rishon.verify:RISHON_PRUNE_FRACTION")
    assert frac == 0.1 and api("su2plaq.evaluate.evaluator:PRUNE_FRACTION") == 1e-2
    qc = C.build_UB(BETA, ladder="rccx")
    v = Vf.verify(qc, enc, "UB", None, BETA)
    assert v.ok and v.reason == "ok" and v.certified, (v.reason, v.dropped_total, v.op_norm_error)
    d = v.dropped_total
    assert 1e-12 < d <= frac * TOL_ERR and v.op_norm_error <= TOL_ERR and v.block_error + v.leak_amplitude <= TOL_ERR
    assert abs(v.op_norm_error - (v.block_error + v.leak_amplitude + d)) <= 1e-20
    assert v.gauss_residual <= 1e-10 and v.gauss_states == 273
    assert v.inner_verdict.reason == "pruning_bound" and not v.inner_verdict.ok          # the shared evaluator is unchanged
    assert v.extra["prune_fraction"] == frac and abs(v.extra["prune_cap"] - frac * TOL_ERR) <= 1e-25 and v.extra["laptop_reason"] == "pruning_bound"
    old = Vf.verify(qc, enc, "UB", None, BETA, prune_fraction=1e-2, gauss=False)
    assert not old.ok and old.reason == "pruning_bound" and abs(old.dropped_total - d) <= 1e-18
    assert dict(old.failing_inputs)["prune_cap"] == pytest.approx(1e-12, rel=1e-12)
    lo = Vf.verify(qc, enc, "UB", None, BETA, prune_fraction=0.9 * d / TOL_ERR, gauss=False)
    hi = Vf.verify(qc, enc, "UB", None, BETA, prune_fraction=1.1 * d / TOL_ERR, gauss=False)
    assert (not lo.ok) and lo.reason == "pruning_bound" and hi.ok and hi.reason == "ok"
    with pytest.raises(ValueError):
        Vf.verify(qc, enc, "UB", None, BETA, prune_fraction=1e-3, gauss=False)
    # a genuinely wrong circuit above the shared cap is still rejected, with its true reason
    bad = C.build_UB(BETA + 1e-6, ladder="rccx")
    w = Vf.verify(bad, enc, "UB", None, BETA, gauss=False)
    assert not w.ok and w.reason == "error" and w.op_norm_error > 1e-7
    c = Vf.verify(C.build_UB(BETA), enc, "UB", None, BETA, gauss=False)
    assert c.ok and c.dropped_total <= 1e-12 and c.inner_verdict.ok and c.extra["laptop_reason"] == "ok"
