"""M9-T1 — T(eps) tables and re-verification of synthesised fuzzy circuits (prompts/300 step 9.7; METHODS §7, METHODS-fuzzy F6).
Slow: pygridsynth costs ~0.03 s per rotation and eps (measured, research 300 §5); the plaquette circuit may carry up to 4000 rotations."""
import numpy as np
import pytest

from tests.acceptance._api import ross_selinger_band
from tests.acceptance.m9._fz import NOMINAL, api, op_norm_after_phase

EPS = (1e-4, 1e-6, 1e-8, 1e-10)


def _build(kind):
    circ = api("su2plaq.circuits.fuzzy")
    tg = api("su2plaq.fuzzy.targets")
    alpha, beta = NOMINAL
    k2 = tg.kappa2_of(alpha, 1.0)
    if kind == "UE":
        return circ.link_UE(alpha), tg.UE_link(alpha), "link"
    if kind == "UK":
        return circ.link_UK(k2), tg.UK_link(k2), "link"
    if kind == "UB":
        return circ.build_UB(beta), tg.UB_row(beta), "plaquette"
    return circ.build_step(alpha, beta, kappa2=k2, order=1), None, "step"


@pytest.mark.slow
@pytest.mark.parametrize("kind", ["UE", "UK", "UB", "step"])
def test_M9_T1_t_table_and_synth_verify(kind):
    """t_table rows for the eps grid: t_total = t_fixed + sum of pygridsynth T per rotation within the Ross-Selinger band;
    |t_qiskit - t_total| <= 10 % (two implementations + Qiskit's optimiser); t_est = t_fixed + 3 n_rot log2(1/eps).
    The circuit synthesised at eps = 1e-6 re-verifies with op-norm error (block + leak amplitude) <= n_rot eps + 1e-9
    (prompts/003 §2, 004: triangle inequality over n_rot rotations each within eps; the Gauss residual of outputs shares the
    same budget, measured ratio <= 1 in reports/research/002).  Link circuits and the plaquette block are verified as complete
    unitaries (verify_link / verify_plaquette); the step by verify_step_samples with the same tolerance."""
    qc, V, how = _build(kind)
    lm = api("su2plaq.metrics.logical:logical_metrics")(qc)
    rows = api("su2plaq.metrics.cliffordt:t_table")(qc, EPS)
    assert [r["eps"] for r in rows] == list(EPS)
    for r in rows:
        assert r["t_fixed"] == lm["t_fixed"] and r["n_rot"] == lm["n_rot"]
        assert r["t_total"] == r["t_fixed"] + r["t_rot_pygridsynth"]
        lo, hi = ross_selinger_band(r["eps"])
        assert r["n_rot"] * lo <= r["t_rot_pygridsynth"] <= r["n_rot"] * hi
        assert abs(r["t_est"] - (r["t_fixed"] + 3 * r["n_rot"] * np.log2(1 / r["eps"]))) <= 1e-6
        assert abs(r["t_qiskit"] - r["t_total"]) <= 0.10 * max(r["t_total"], 1)
    eps = 1e-6
    synth, info = api("su2plaq.metrics.cliffordt:synthesize")(qc, eps)
    assert info["n_rot"] == lm["n_rot"] and set(synth.count_ops()) <= {"cx", "h", "s", "sdg", "t", "tdg", "x", "z"}
    assert info["error_bound_sum"] <= lm["n_rot"] * eps
    tol = lm["n_rot"] * eps + 1e-9
    assert api("su2plaq.evaluate.evaluator:synth_tolerances")(lm["n_rot"], eps) == dict(tol_err=tol, tol_gauss=tol)
    if how == "link":
        v = api("su2plaq.fuzzy.verify:verify_link")(synth, V, tol_err=tol)
        assert v.ok and v.op_norm_error <= tol and v.certified and v.tolerances["tol_err"] == tol
    elif how == "plaquette":
        v = api("su2plaq.fuzzy.verify:verify_plaquette")(synth, V, tol_err=tol)
        assert v.ok, (v.reason, v.op_norm_error, v.block_error, v.leak_amplitude)
        assert v.op_norm_error <= tol and v.leak_amplitude <= tol and v.certified
    else:
        tg = api("su2plaq.fuzzy.targets")
        alpha, beta = NOMINAL
        res = api("su2plaq.fuzzy.verify:verify_step_samples")(synth, alpha, beta, tg.kappa2_of(alpha, 1.0), 1, n_random=16, n_phys=4, seed=20261104)
        assert res["err"] <= tol and res["gauss"] <= tol
    assert synth.count_ops().get("t", 0) + synth.count_ops().get("tdg", 0) == rows[1]["t_total"]
