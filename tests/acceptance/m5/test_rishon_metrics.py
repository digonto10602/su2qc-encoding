"""M5-T1 — T(eps) tables and re-verification of synthesised rishon circuits (prompts/200 §3 step 5.9; METHODS §7;
synthesised tolerances prompts/003-004: op_norm_error and Gauss <= n_rot eps + 1e-9)."""
import functools

import numpy as np
import pytest

from tests.acceptance._api import api, ross_selinger_band

EPS = (1e-4, 1e-6, 1e-8, 1e-10)


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.rishon:RishonEncoding")()


@pytest.mark.parametrize("kind", ["UE", "UB", "step"])
def test_M5_T1_t_table_and_synth_verify(kind):
    """t_table rows for the eps grid: t_total = t_fixed + sum of pygridsynth T per rotation, each in the Ross-Selinger
    band; |t_qiskit - t_total| <= 10 %; t_est formula.  The circuit synthesised at eps = 1e-6 re-verifies through the
    rishon verifier with synth_tolerances(n_rot, eps) (ok and certified; the Gauss sample is judged with the same budget)."""
    enc = _enc()
    alpha, beta = 0.37, 0.61
    C = api("su2plaq.circuits.rishon")
    qc = {"UE": lambda: C.build_UE(alpha), "UB": lambda: C.build_UB(beta), "step": lambda: C.build_step(alpha, beta)}[kind]()
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
    Vf = api("su2plaq.rishon.verify")
    tol = Vf.synth_tolerances(lm["n_rot"], eps)
    assert tol == {"tol_err": lm["n_rot"] * eps + 1e-9, "tol_gauss": lm["n_rot"] * eps + 1e-9}
    a, b = (alpha, None) if kind == "UE" else ((None, beta) if kind == "UB" else (alpha, beta))
    v = Vf.verify(synth, enc, kind, a, b, **tol)
    assert v.ok, (v.reason, v.op_norm_error, v.block_error, v.leak_amplitude, v.gauss_residual)
    assert v.certified and v.leak_amplitude <= tol["tol_err"] and v.gauss_residual <= tol["tol_gauss"] and v.tolerances == tol
    assert synth.count_ops().get("t", 0) + synth.count_ops().get("tdg", 0) == rows[1]["t_total"]
