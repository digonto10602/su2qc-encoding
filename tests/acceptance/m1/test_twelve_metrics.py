"""M1-T1 — T(eps) table and re-verification of synthesised circuits (prompts/002 §2.8, METHODS §7)."""
import numpy as np
import pytest

import functools

from tests.acceptance._api import api, ross_selinger_band

EPS = (1e-4, 1e-6, 1e-8, 1e-10)


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.twelve:TwelveQubit")()


@pytest.mark.parametrize("kind", ["UE", "UB", "step"])
def test_M1_T1_t_table_and_synth_verify(kind):
    """t_table rows for the eps grid: t_total = t_fixed + sum of pygridsynth T per rotation, each within the
    Ross-Selinger band; |t_qiskit - t_total| <= 10 % of t_total (two gridsynth implementations plus Qiskit's
    optimisation); t_est = t_fixed + 3 n_rot log2(1/eps). The circuit synthesised with pygridsynth at eps = 1e-6
    re-verifies with error <= n_rot eps + 1e-9 and leak <= (n_rot eps)^2 + 1e-12 (triangle inequality; gridsynth
    words are not diagonal)."""
    enc = _enc()
    alpha, beta = 0.37, 0.61
    circ = api("su2plaq.circuits.twelve")
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
        assert r["cx_qiskit"] <= 1.1 * lm["cx"] + 2  # Qiskit's level-3 optimiser should not add CX
    eps = 1e-6
    synth, info = api("su2plaq.metrics.cliffordt:synthesize")(qc, eps)
    assert info["n_rot"] == lm["n_rot"] and set(synth.count_ops()) <= {"cx", "h", "s", "sdg", "t", "tdg", "x", "z"}
    assert info["error_bound_sum"] <= lm["n_rot"] * eps
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    V = enc.target(kind, alpha, beta)
    v = evaluate(synth, enc, V, tol_err=lm["n_rot"] * eps + 1e-9, tol_leak=(lm["n_rot"] * eps) ** 2 + 1e-12)
    assert v.ok, (v.reason, v.op_norm_error, v.max_leak)
    # synthesised T equals the table's rotation T at that eps
    assert synth.count_ops().get("t", 0) + synth.count_ops().get("tdg", 0) == rows[1]["t_total"]
