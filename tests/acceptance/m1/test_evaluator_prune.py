"""M1-V1 — relative cap on the certified pruning bound (prompts/005; METHODS §6).

The sparse engine drops amplitudes below PRUNE_REL x (column max) after every branching gate and certifies the
dropped L2 weight per input column; `dropped_total` is the Frobenius bound on the resulting matrix error and is
already one of the three terms of op_norm_error (prompts/004). The separate `pruning_bound` rejection is only a
safety net that keeps the simulator's share of the error budget negligible: it fires iff
    dropped_total > PRUNE_FRACTION * tol_err,   PRUNE_FRACTION = 1e-2
(Digonto 2026-11-05, reports/tests/020 §C). Exact-angle circuits (tol_err 1e-10) keep the old cap 1e-12;
synthesised circuits get >= 1e-11. The quantity compared is the same `dropped_total` that enters op_norm_error
(not the per-column maximum), and across outer-bit groups it is the MAXIMUM of the per-group Frobenius bounds
(the pruning error is block-diagonal in the outer pattern; prompts/005 §2).
"""
import functools

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from tests.acceptance._api import api


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.twelve:TwelveQubit")()


def _drop_circuit(k: int, delta: float, with_outer: bool) -> QuantumCircuit:
    """k gates u(2 delta, 0, 0) = Ry(2 delta) on d[0]: each creates one amplitude sin(delta) per input column that the
    sparse engine drops (sin(delta) <= PRUNE_REL x column max = 1), so the certified per-column bound is exactly
    k sin(delta) and the Frobenius bound over the 625 inner codes is 25 k sin(delta); the kept amplitude
    cos(delta) = 1.0 in float64, so the circuit itself is the identity to rounding. With with_outer an identity pair
    cz(o[0], d[1]) cz(o[0], d[1]) makes the evaluator read one outer bit -> two outer groups with identical drops."""
    d = QuantumRegister(12, "d")
    regs = [d]
    if with_outer:
        regs.append(QuantumRegister(16, "o"))
    qc = QuantumCircuit(*regs)
    if with_outer:
        qc.cz(regs[1][0], d[1])
        qc.cz(regs[1][0], d[1])
    for _ in range(k):
        qc.u(2 * delta, 0.0, 0.0, d[0])
    return qc


def test_M1_V1_pruning_cap_is_relative_to_tol_err():
    """One circuit with certified pruning bound dropped_total = 25 k sin(delta) = 3.125e-11 (k = 250,
    delta = PRUNE_REL/2 = 5e-15; per-column maximum 1.25e-12, i.e. above the old fixed cap 1e-12) and a block error of
    pure float rounding (<= 1e-12), no leak:
      * synth_tolerances(10, 1e-6) (tol_err 1.0001e-5, cap 1.0001e-7): 1e-12 < dropped_total <= cap -> ok, certified
        (the old fixed cap on the per-column maximum rejected this; prompts/005 §1);
      * synth_tolerances(1, 1e-10) (tol_err 1.1e-9, cap 1.1e-11): dropped_total 3.125e-11 > cap but the per-column
        maximum 1.25e-12 < cap -> rejected as `pruning_bound` ONLY if the compared quantity is dropped_total;
        block_error + leak_amplitude <= tol_err, so the cap is the sole reason;
      * exact-angle default (tol_err 1e-10, cap 1e-12): rejected as `pruning_bound` (cap unchanged for exact circuits);
      * the fraction is pinned to 1e-2 within +-20 %: tol_err = 1.2 dropped_total/1e-2 -> ok, 0.8 dropped_total/1e-2 ->
        `pruning_bound`.
    Tolerance on dropped_total: 1e-6 relative to 25 k sin(delta) (the bound is a float64 sum of k identical terms per
    column, sqrt-summed over 625 columns: relative rounding ~ k x 1e-16 = 2.5e-14).
    op_norm_error == block_error + dropped_total + leak_amplitude (1e-15, prompts/004) in every verdict."""
    enc = _enc()
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    synth_tolerances = api("su2plaq.evaluate.evaluator:synth_tolerances")
    frac = api("su2plaq.evaluate.evaluator:PRUNE_FRACTION")
    prune_rel = api("su2plaq.evaluate.sparse_sim:PRUNE_REL")
    assert frac == 1e-2
    I = np.eye(433, dtype=complex)
    k, delta = 250, 0.5 * prune_rel
    expected_total = 25.0 * k * np.sin(delta)
    assert 1e-12 < expected_total, "construction must exceed the old fixed cap (PRUNE_REL changed?)"
    qc = _drop_circuit(k, delta, with_outer=False)

    def check_common(v, tol):
        assert v.engine == "sparse" and v.certified and v.n_blocks == 1 and v.tolerances == tol
        assert abs(v.dropped_total - expected_total) <= 1e-6 * expected_total, (v.dropped_total, expected_total)
        assert v.block_error <= 1e-12 and v.leak_amplitude == 0.0, (v.block_error, v.leak_amplitude)
        assert abs(v.op_norm_error - (v.block_error + v.dropped_total + v.leak_amplitude)) <= 1e-15
        assert v.extra["max_dropped_l2"] <= v.dropped_total

    # accepted: dropped bound in (1e-12, 1e-2 tol_err]
    tol = synth_tolerances(10, 1e-6)
    v = evaluate(qc, enc, I, **tol)
    check_common(v, tol)
    assert v.dropped_total <= frac * tol["tol_err"]
    assert v.ok and v.reason == "ok" and v.failing_inputs == [], (v.reason, v.dropped_total, v.failing_inputs)

    # rejected at a synthesised tolerance whose cap lies between the per-column maximum and the Frobenius bound
    tol = synth_tolerances(1, 1e-10)
    v = evaluate(qc, enc, I, **tol)
    check_common(v, tol)
    assert v.extra["max_dropped_l2"] < frac * tol["tol_err"] < v.dropped_total
    assert v.block_error + v.leak_amplitude <= tol["tol_err"]
    assert not v.ok and v.reason == "pruning_bound", (v.reason, v.dropped_total)
    assert any(name == "dropped_total" and abs(val - v.dropped_total) <= 1e-15 for name, val in v.failing_inputs), v.failing_inputs

    # exact-angle default: cap 1e-2 x 1e-10 = 1e-12, unchanged
    tol = dict(tol_err=1e-10, tol_gauss=1e-10)
    v = evaluate(qc, enc, I)
    check_common(v, tol)
    assert not v.ok and v.reason == "pruning_bound"

    # the fraction itself: +-20 % around the boundary tol_err = dropped_total / 1e-2
    t_hi, t_lo = 1.2 * expected_total / 1e-2, 0.8 * expected_total / 1e-2
    v = evaluate(qc, enc, I, tol_err=t_hi, tol_gauss=t_hi)
    check_common(v, dict(tol_err=t_hi, tol_gauss=t_hi))
    assert v.ok and v.reason == "ok", (v.reason, v.dropped_total, frac * t_hi)
    v = evaluate(qc, enc, I, tol_err=t_lo, tol_gauss=t_lo)
    check_common(v, dict(tol_err=t_lo, tol_gauss=t_lo))
    assert not v.ok and v.reason == "pruning_bound", (v.reason, v.dropped_total, frac * t_lo)


def test_M1_V2_pruning_bound_is_max_over_outer_groups():
    """The same drops with one outer bit read (identity cz pair on o[0]): two outer groups, each simulated once with
    the identical per-group Frobenius bound 25 k sin(delta). The pruning error of the full-register operator is
    block-diagonal in the outer pattern, so its operator norm is the MAXIMUM over groups, not the sum (prompts/005
    §2): dropped_total == 25 k sin(delta) (1e-6 relative), n_blocks == 2, verdict ok at synth_tolerances(10, 1e-6),
    identical dropped_total to the no-outer circuit. A sum over groups (2 x) fails the 1e-6 check."""
    enc = _enc()
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    synth_tolerances = api("su2plaq.evaluate.evaluator:synth_tolerances")
    prune_rel = api("su2plaq.evaluate.sparse_sim:PRUNE_REL")
    I = np.eye(433, dtype=complex)
    k, delta = 250, 0.5 * prune_rel
    expected_total = 25.0 * k * np.sin(delta)
    tol = synth_tolerances(10, 1e-6)
    v = evaluate(_drop_circuit(k, delta, with_outer=True), enc, I, **tol)
    assert v.engine == "sparse" and v.certified and v.outer_bits_read == 1 and v.n_blocks == 2 and v.method == "physical"
    assert abs(v.dropped_total - expected_total) <= 1e-6 * expected_total, (v.dropped_total, expected_total)
    assert v.block_error <= 1e-12 and v.leak_amplitude == 0.0
    assert abs(v.op_norm_error - (v.block_error + v.dropped_total + v.leak_amplitude)) <= 1e-15
    assert v.ok and v.reason == "ok", (v.reason, v.dropped_total)
    v0 = evaluate(_drop_circuit(k, delta, with_outer=False), enc, I, **tol)
    assert abs(v.dropped_total - v0.dropped_total) <= 1e-6 * expected_total
