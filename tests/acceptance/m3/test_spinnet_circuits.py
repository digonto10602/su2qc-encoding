"""M3-E1, B1..B3, S1 — general circuits of the spin-network encoding (prompts/100 §3 steps 3.3-3.5; METHODS-spinnet §4).
Exact-angle circuits: op_norm_error = block error + pruning bound + leak amplitude <= 1e-10 (prompts/004), weight
diagnostics <= 1e-20 = (1e-10)^2 (as M1).  Planner measurements (reports/research/100 §4): general circuit 54 CX,
4 rotations, 56 fixed T, 7 ancillas, error ~1e-14 at three angle pairs."""
import functools
from fractions import Fraction

import numpy as np
import pytest

from tests.acceptance._api import api, op_norm_after_phase

ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}
NOMINAL = (0.37, 0.61)


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.spinnet:SpinNet")()


def _ops(qc):
    return {inst.operation.name for inst in qc.data}


def _skeleton(qc):
    return [(inst.operation.name, tuple(qc.find_bit(q).index for q in inst.qubits)) for inst in qc.data]


@pytest.mark.parametrize("alpha", [0.37, 0.91])
def test_M3_E1_electric_step(alpha):
    """build_UE(alpha): one p(-3 alpha/4) on each inner-link qubit 0..3 (register d[8]); exact vs target 'UE' (1e-10);
    the phase of a single j = 1/2 link (code 0b0001, link b) is e^{-3 i alpha/4} (sign tested).  with_outer adds o[8];
    include_outer_electric adds the 8 outer phases and matches the outer-electric target (128 outer blocks read)."""
    enc = _enc()
    build_UE = api("su2plaq.circuits.spinnet:build_UE")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    qc = build_UE(alpha)
    assert qc.num_qubits == 8 and [r.name for r in qc.qregs] == ["d"]
    assert _ops(qc) <= ALLOWED and sum(1 for i in qc.data if i.operation.name in ("p", "rz")) == 4
    assert {qc.find_bit(i.qubits[0]).index for i in qc.data if i.operation.name in ("p", "rz")} == {0, 1, 2, 3}
    lm = api("su2plaq.metrics.logical:logical_metrics")(qc)
    assert lm["cx"] == 0 and lm["n_rot"] == 4 and lm["t_fixed"] == 0
    v = evaluate(qc, enc, enc.target("UE", alpha, None))
    assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20
    b = run_batch(qc, np.array([0b0001], dtype=np.int64))
    assert len(b.keys) == 1 and b.keys[0] == 0b0001 and abs(b.amps[0] - np.exp(-0.75j * alpha)) <= 1e-12
    qo = build_UE(alpha, with_outer=True)
    assert qo.num_qubits == 16 and [r.name for r in qo.qregs] == ["d", "o"]
    vo = evaluate(qo, enc, enc.target("UE", alpha, None), method="physical")
    assert vo.ok and vo.outer_bits_read == 0
    qe = build_UE(alpha, with_outer=True, include_outer_electric=True)
    assert sum(1 for i in qe.data if i.operation.name in ("p", "rz")) == 12
    ve = evaluate(qe, enc, enc.target("UE", alpha, None, include_outer_electric=True), method="physical")
    assert ve.ok and ve.op_norm_error <= 1e-10 and ve.outer_bits_read == 8 and ve.n_blocks == 128
    with pytest.raises(ValueError):
        build_UE(alpha, include_outer_electric=True)


@pytest.mark.parametrize("beta", [0.4, 0.61, 1.0, 2.0])
def test_M3_B1_magnetic_inner_block(beta):
    """build_UB(beta) is exact on the 47 inner codes: the 47x47 block (ancillas 0) equals the inner target
    exp(-i beta K) in route-B gauge up to one global phase (1e-10), leak <= 1e-12; registers d[8] then ancillas; allowed
    gates only; the gate skeleton does not depend on beta; every rotation angle is a rational multiple of beta with
    denominator <= 4 (angle-linear, Lean-certifiable: measured angles -7/2, -1, 3, 3/2 x beta); cost sanity: the plan's
    construction (frame + flags + 4-rotation walk) has 54 CX, 4 rotations, 7 ancillas — twice that is the bound."""
    enc = _enc()
    build_UB = api("su2plaq.circuits.spinnet:build_UB")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    encoded_block = api("su2plaq.evaluate.sparse_sim:encoded_block")
    qc = build_UB(beta)
    assert qc.qregs[0].name == "d" and qc.qregs[0].size == 8 and "o" not in [r.name for r in qc.qregs]
    assert _ops(qc) <= ALLOWED
    codes = enc.inner_codes()
    batch = run_batch(qc, codes)
    M, leak = encoded_block(batch, codes, len(codes), code_mask=(1 << 8) - 1)
    assert leak.max() <= 1e-12
    V = enc.inner_target("UB", None, beta)
    assert V.shape == (47, 47) and op_norm_after_phase(M, V) <= 1e-10
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    v = evaluate(qc, enc, enc.target("UB", None, beta))
    assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20
    lm = api("su2plaq.metrics.logical:logical_metrics")(qc)
    assert 1 <= lm["n_rot"] <= 16 and lm["cx"] <= 120 and lm["ancilla"] <= 16 and lm["qubits"] == 8 + lm["ancilla"]
    for th in lm["rz_angles"]:
        f = Fraction(th / beta).limit_denominator(4)
        assert abs(float(f) * beta - th) <= 1e-9, (th, beta)
    assert _skeleton(qc) == _skeleton(build_UB(beta * 1.7))


@functools.lru_cache(maxsize=None)
def _ub_outer():
    enc = _enc()
    build_UB = api("su2plaq.circuits.spinnet:build_UB")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    qc = build_UB(0.61, with_outer=True)
    v = evaluate(qc, enc, enc.target("UB", None, 0.61), method="physical", gauss=True)
    return qc, v


def test_M3_B2_physical_states():
    """All 433 physical states with the outer register present (explicit assembly): error <= 1e-10 incl. leak amplitude;
    the outer register is never read (Paulo's Fig. 2 claim realised: one block), ancillas declared after d, o."""
    enc = _enc()
    qc, v = _ub_outer()
    assert [r.name for r in qc.qregs][:2] == ["d", "o"] and qc.qregs[1].size == 8
    assert v.ok and v.method == "physical" and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20
    assert v.n_inputs == 433 and v.outer_bits_read == 0 and v.n_blocks == 1
    assert v.engine == "sparse" and v.certified
    layout = enc.layout_of(qc)
    assert layout.data == list(range(8)) and layout.outer == list(range(8, 16)) and layout.ancilla == list(range(16, qc.num_qubits))


def test_M3_B3_gauss_and_clean_ancillas():
    """Gauss residual of every decoded output <= 1e-10 (exact-angle rule); every ancilla returns to |0> (dirty weight
    <= 1e-20); the outer qubits are untouched by any gate."""
    enc = _enc()
    qc, v = _ub_outer()
    assert v.gauss_residual <= 1e-10 and v.dirty_ancilla <= 1e-20
    touched = {qc.find_bit(q).index for inst in qc.data for q in inst.qubits}
    assert not (touched & set(range(8, 16)))


@pytest.mark.parametrize("order", [1, 2])
def test_M3_S1_step_orders(order):
    """build_step(alpha, beta, order) equals the route-B 'step' target of the same order (1e-10) at the nominal angles
    and at the alternates with the same skeleton; order 1 = U_B U_E (electric layer first), order 2 = U_E(a/2) U_B
    U_E(a/2).  Rejected (error > 1e-3): the other order's target, and the target at -beta — U_B(-beta) is gauge-equivalent
    to U_B(beta) in this encoding (M3-K1), so this last check pins the circuit to the route-B sign gauge of the target,
    it is not a physics check."""
    enc = _enc()
    build_step = api("su2plaq.circuits.spinnet:build_step")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    skel = None
    for alpha, beta in ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00)):
        qc = build_step(alpha, beta, order=order)
        assert _ops(qc) <= ALLOWED and qc.qregs[0].name == "d"
        v = evaluate(qc, enc, enc.target("step", alpha, beta, order=order))
        assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20
        sk = _skeleton(qc)
        assert skel is None or sk == skel
        skel = sk
    qc = build_step(0.37, 0.61, order=order)
    v = evaluate(qc, enc, enc.target("step", 0.37, 0.61, order=3 - order))
    assert not v.ok and v.op_norm_error > 1e-3
    v = evaluate(qc, enc, enc.target("step", 0.37, -0.61, order=order))
    assert not v.ok and v.op_norm_error > 1e-3
    qo = build_step(0.37, 0.61, order=order, with_outer=True)
    vo = evaluate(qo, enc, enc.target("step", 0.37, 0.61, order=order), method="physical")
    assert vo.ok and vo.outer_bits_read == 0 and vo.gauss_residual <= 1e-10
