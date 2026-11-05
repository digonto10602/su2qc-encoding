"""M1-E1, B1..B4, S1 — general circuits of the 12-qubit encoding (prompts/002 §2.6, §4; METHODS §2, §6).
Exact-angle circuits: op-norm error <= 1e-10 where op_norm_error = block error + leak amplitude (prompts/004: leak is
judged as an amplitude, no separate weight tolerance); weight diagnostics (max_leak, dirty_ancilla) <= 1e-20 = (1e-10)^2
(float64 over <= 3e3 gates accumulates ~1e-13 in amplitude, ~1e-26 in weight)."""
import numpy as np
import pytest

import functools

from tests.acceptance._api import api, op_norm_after_phase

ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.twelve:TwelveQubit")()


def _ops(qc):
    return {inst.operation.name for inst in qc.data}


@pytest.mark.parametrize("alpha", [0.37, 0.91])
def test_M1_E1_electric_step(alpha):
    """build_UE(alpha): 4 p gates on the j-qubits (2,5,8,11); exact vs target 'UE' (1e-10); the single-link phase on
    |++>_b (code 0b111) is e^{-3 i alpha / 4} (sign tested, not assumed; Qiskit p(l) = diag(1, e^{il}))."""
    enc = _enc()
    build_UE = api("su2plaq.circuits.twelve:build_UE")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    qc = build_UE(alpha)
    assert qc.num_qubits == 12 and [r.name for r in qc.qregs] == ["d"]
    assert _ops(qc) <= ALLOWED and sum(1 for i in qc.data if i.operation.name in ("p", "rz")) == 4
    lm = api("su2plaq.metrics.logical:logical_metrics")(qc)
    assert lm["cx"] == 0 and lm["n_rot"] == 4 and lm["t_fixed"] == 0
    v = evaluate(qc, enc, enc.target("UE", alpha, None))
    assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20  # prompts/004
    b = run_batch(qc, np.array([0b111], dtype=np.int64))
    assert len(b.keys) == 1 and b.keys[0] == 0b111 and abs(b.amps[0] - np.exp(-0.75j * alpha)) <= 1e-12
    qo = build_UE(alpha, with_outer=True)
    assert qo.num_qubits == 28 and [r.name for r in qo.qregs] == ["d", "o"]
    vo = evaluate(qo, enc, enc.target("UE", alpha, None), method="physical")
    assert vo.ok and vo.outer_bits_read == 0


@pytest.mark.parametrize("beta", [0.4, 1.0, 2.0])
def test_M1_B1_magnetic_inner_block(beta):
    """build_UB(beta) is exact on all 625 inner codes: the 625x625 block (ancillas 0) equals the inner operator
    exp(+i beta (TrW + h.c.)) up to one global phase (1e-10), leak <= 1e-12; only allowed gates; registers as Paulo's."""
    enc = _enc()
    build_UB = api("su2plaq.circuits.twelve:build_UB")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    encoded_block = api("su2plaq.evaluate.sparse_sim:encoded_block")
    inner_target = api("su2plaq.evaluate.evaluator:inner_target")
    qc = build_UB(beta)
    assert [r.name for r in qc.qregs][0] == "d" and qc.qregs[0].size == 12 and "o" not in [r.name for r in qc.qregs]
    assert _ops(qc) <= ALLOWED
    codes = enc.inner_codes()
    batch = run_batch(qc, codes)
    M, leak = encoded_block(batch, codes, len(codes), code_mask=(1 << 12) - 1)
    assert leak.max() <= 1e-12
    V = inner_target(enc, "UB", None, beta)
    assert V.shape == (625, 625)
    assert op_norm_after_phase(M, V) <= 1e-10
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    v = evaluate(qc, enc, enc.target("UB", None, beta))
    assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20  # prompts/004
    # the general circuit uses only macro gates: no native mcrx / cu / mcx; its logical cost is recorded, not fixed here
    lm = api("su2plaq.metrics.logical:logical_metrics")(qc)
    assert lm["ancilla"] == 22 and lm["qubits"] == 34 and lm["n_rot"] >= 3


@functools.lru_cache(maxsize=None)
def _ub_outer():
    enc = _enc()
    build_UB = api("su2plaq.circuits.twelve:build_UB")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    qc = build_UB(0.61, with_outer=True)
    v = evaluate(qc, enc, enc.target("UB", None, 0.61), method="physical", gauss=True)
    return qc, v


def test_M1_B2_physical_states():
    """On the 433 physical states with the outer register present (explicit assembly): error <= 1e-10 including the
    leak amplitude (prompts/004); weight diagnostic max_leak <= 1e-20."""
    enc = _enc()
    ub_outer = _ub_outer()
    qc, v = ub_outer
    assert [r.name for r in qc.qregs][:2] == ["d", "o"]
    assert v.ok and v.method == "physical" and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.n_inputs >= 433


def test_M1_B3_gauss_outputs():
    """Gauss residual of every output state <= 1e-10."""
    enc = _enc()
    ub_outer = _ub_outer()
    _, v = ub_outer
    assert v.gauss_residual <= 1e-10


def test_M1_B4_outer_blind_and_clean():
    """outer_bits_read = 0 (the general circuit never reads the outer register), declared ancillas only (registers d, o,
    then ancillas; Paulo's names p, e, w, g, tmp, h), all returned to |0> (dirty-ancilla weight <= 1e-20 = (1e-10)^2,
    prompts/004: the ancilla leak amplitude is inside op_norm_error <= 1e-10)."""
    enc = _enc()
    ub_outer = _ub_outer()
    qc, v = ub_outer
    assert v.outer_bits_read == 0 and v.n_blocks == 1 and v.dirty_ancilla <= 1e-20 and v.leak_amplitude <= 1e-10
    names = [r.name for r in qc.qregs]
    assert names[:2] == ["d", "o"] and set(names[2:]) == {"p", "e", "w", "g", "tmp", "h"}
    assert qc.num_qubits == 28 + 22
    layout = enc.layout_of(qc)
    assert layout.data == list(range(12)) and layout.outer == list(range(12, 28)) and layout.ancilla == list(range(28, 50))


@pytest.mark.parametrize("order", [1, 2])
def test_M1_S1_step_orders(order):
    """build_step(alpha, beta, order) equals the target 'step' of the same order (1e-10) at the nominal angles and at an
    alternate pair; order 1 = U_B U_E (electric layer first), order 2 = U_E(a/2) U_B U_E(a/2)."""
    enc = _enc()
    build_step = api("su2plaq.circuits.twelve:build_step")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    for alpha, beta in ((0.37, 0.61), (1.70, 1.00)):
        qc = build_step(alpha, beta, order=order)
        assert _ops(qc) <= ALLOWED
        v = evaluate(qc, enc, enc.target("step", alpha, beta, order=order))
        assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20  # prompts/004
    # order mismatch is detected (orders 1 and 2 differ by O(alpha beta) >> 1e-10 at these angles)
    v = evaluate(build_step(0.37, 0.61, order=1), enc, enc.target("step", 0.37, 0.61, order=2))
    assert not v.ok and v.op_norm_error > 1e-3
