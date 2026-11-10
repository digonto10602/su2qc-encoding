"""M3-T1 — T(eps) tables and re-verification of the synthesised spin-network circuits on the sparse engine
(prompts/100 §3 step 3.6; METHODS §7, METHODS-spinnet §6).  Same rule as M1-T1: t_total = t_fixed + sum of pygridsynth T,
Ross-Selinger band per rotation, Qiskit CT within 10 %, synthesised circuit at eps = 1e-6 accepted under
synth_tolerances(n_rot, eps) = {tol_err, tol_gauss} = n_rot eps + 1e-9 (prompts/003, 004).  Planner measurements
(reports/research/100 §4): UB 4 rotations, T(1e-6) = 310; step order 1: 8 rotations, 566; synthesised errors 0.25-0.33 of
the budget; the outer-electric row synthesised is `writes_outer` (same as M1, audit 003 N2)."""
import functools

import numpy as np
import pytest

from tests.acceptance._api import api, ross_selinger_band

EPS = (1e-4, 1e-6, 1e-8, 1e-10)


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.spinnet:SpinNet")()


@pytest.mark.parametrize("kind", ["UE", "UB", "step"])
def test_M3_T1_t_table_and_synth_verify(kind):
    """t_table rows for the eps grid; pygridsynth T per rotation within the Ross-Selinger band; |t_qiskit - t_total|
    <= 10 %; t_est = t_fixed + 3 n_rot log2(1/eps); the pygridsynth-synthesised circuit at eps = 1e-6 re-verifies on the
    sparse engine (certified) with op_norm_error and Gauss residual <= n_rot eps + 1e-9."""
    enc = _enc()
    alpha, beta = 0.37, 0.61
    circ = api("su2plaq.circuits.spinnet")
    qc = {"UE": lambda: circ.build_UE(alpha), "UB": lambda: circ.build_UB(beta), "step": lambda: circ.build_step(alpha, beta)}[kind]()
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
        assert r["cx_qiskit"] <= 1.1 * lm["cx"] + 2
    eps = 1e-6
    synth, info = api("su2plaq.metrics.cliffordt:synthesize")(qc, eps)
    assert info["n_rot"] == lm["n_rot"] and set(synth.count_ops()) <= {"cx", "h", "s", "sdg", "t", "tdg", "x", "z"}
    assert info["error_bound_sum"] <= lm["n_rot"] * eps
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    synth_tolerances = api("su2plaq.evaluate.evaluator:synth_tolerances")
    V = enc.target(kind, alpha, beta)
    tol = dict(tol_err=lm["n_rot"] * eps + 1e-9, tol_gauss=lm["n_rot"] * eps + 1e-9)
    assert synth_tolerances(lm["n_rot"], eps) == tol
    v = evaluate(synth, enc, V, **tol)
    assert v.ok, (v.reason, v.op_norm_error, v.block_error, v.leak_amplitude, v.gauss_residual)
    assert v.leak_amplitude <= tol["tol_err"] and v.gauss_residual <= tol["tol_gauss"] and v.engine == "sparse"
    assert v.certified and v.tolerances == tol
    assert synth.count_ops().get("t", 0) + synth.count_ops().get("tdg", 0) == rows[1]["t_total"]
    if kind == "UB":
        # like-for-like with Paulo's 15-qubit circuit at the same per-rotation eps: both 4 rotations; his fixed T = 64
        pq = circ.paulo_circuit()
        prow = api("su2plaq.metrics.cliffordt:t_table")(pq, (eps,), qiskit=False)[0]
        assert prow["n_rot"] == 4 and prow["t_fixed"] == 64 and prow["t_total"] == 64 + prow["t_rot_pygridsynth"]
