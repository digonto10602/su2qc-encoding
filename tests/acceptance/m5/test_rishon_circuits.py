"""M5-E1, B1, S1 — general circuits of the rishon encoding (prompts/200 §2.5, §3 steps 5.6-5.8; METHODS-rishon R6-R7).
Exact-angle circuits: op_norm_error = block error + leak amplitude + pruning bound <= 1e-10 on the 1296 inner codes
(certifies all 38 432 physical states for outer-blind circuits, METHODS-rishon R6 theorem); weights <= 1e-20;
Gauss residual of the sampled outputs <= 1e-10 (prompts/003 rule)."""
import functools

import numpy as np
import pytest

from tests.acceptance._api import api, op_norm_after_phase
from tests.acceptance.m5 import _ref

ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.rishon:RishonEncoding")()


def _ops(qc):
    return {inst.operation.name for inst in qc.data}


def _skeleton(qc):
    return [(inst.operation.name, tuple(qc.find_bit(q).index for q in inst.qubits)) for inst in qc.data]


def _amp(batch, key):
    sel = (batch.keys == key)
    return complex(batch.amps[sel][0]) if sel.any() else 0.0


@pytest.mark.parametrize("alpha", [0.37, 0.91])
def test_M5_E1_electric_step(alpha):
    """build_UE(alpha): registers ['d'] (16 qubits), allowed gates, 4 rotations, <= 8 CX; exact vs the inner target 'UE'
    (1e-10, zero leak); the quartet code of link b picks up e^{-3 i alpha/4} relative to the all-singlet code (sign
    tested, not assumed); with_outer: 48 qubits, no outer bit read; include_outer_electric adds the same phase on an
    outer quartet link (12 rotations, <= 24 CX)."""
    enc = _enc()
    C = api("su2plaq.circuits.rishon")
    Vf = api("su2plaq.rishon.verify")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    lm = api("su2plaq.metrics.logical:logical_metrics")
    qc = C.build_UE(alpha)
    assert qc.num_qubits == 16 and [r.name for r in qc.qregs] == ["d"] and _ops(qc) <= ALLOWED
    m = lm(qc)
    assert m["n_rot"] == 4 and m["cx"] <= 8 and m["t_fixed"] == 0
    v = Vf.verify(qc, enc, "UE", alpha, None)
    assert v.ok and v.certified and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20
    assert v.gauss_residual <= 1e-10 and v.gauss_states == 273
    va, _ = _ref.vac_codes()
    q_b = (va & ~0xF) | _ref.CODES_Q[0]
    b = run_batch(qc, np.array([va, q_b], dtype=np.int64))
    a0 = _amp(b, va)
    a1 = _amp(b, q_b)
    assert abs(a0) >= 1 - 1e-12 and abs(a1 / a0 - np.exp(-0.75j * alpha)) <= 1e-12
    qo = C.build_UE(alpha, with_outer=True)
    assert qo.num_qubits == 48 and [r.name for r in qo.qregs] == ["d", "o"]
    vo = Vf.verify(qo, enc, "UE", alpha, None)
    assert vo.ok and vo.outer_bits_read == 0
    qe = C.build_UE(alpha, with_outer=True, include_outer_electric=True)
    me = lm(qe)
    assert me["n_rot"] == 12 and me["cx"] <= 24
    outer = _ref.outer_near_empty_code()
    k0 = 16                                                     # outer link 0 (o0) at qubits 16..19
    outer_q = (outer & ~(0xF << k0)) | (((0b01 << 0) | (0b01 << 2)) << k0)   # quartet, colour 1 at both ends
    b = run_batch(qe, np.array([va | outer, va | outer_q], dtype=np.int64))
    a0, a1 = _amp(b, va | outer), _amp(b, va | outer_q)
    assert abs(a0) >= 1 - 1e-12 and abs(a1 / a0 - np.exp(-0.75j * alpha)) <= 1e-12
    with pytest.raises(ValueError):
        C.build_UE(alpha, include_outer_electric=True)


@pytest.mark.parametrize("beta", [0.61, 0.23, 1.0, 2.0])
def test_M5_B1_magnetic_inner_block(beta):
    """build_UB(beta): registers d first, no 'o', allowed gates only; exact on all 1296 inner codes: the simulated block
    (ancillas 0) equals exp(-i beta H_B^in) up to one global phase (1e-10, independent check with run_batch +
    encoded_block), leak weight <= 1e-20; the production verdict agrees (ok, certified, error <= 1e-10, Gauss sample
    <= 1e-10); the gate skeleton does not depend on beta (no fixed-angle tricks)."""
    enc = _enc()
    C = api("su2plaq.circuits.rishon")
    Vf = api("su2plaq.rishon.verify")
    O = api("su2plaq.rishon.operators")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    encoded_block = api("su2plaq.evaluate.sparse_sim:encoded_block")
    qc = C.build_UB(beta)
    names = [r.name for r in qc.qregs]
    assert names[0] == "d" and qc.qregs[0].size == 16 and "o" not in names and _ops(qc) <= ALLOWED
    codes = enc.inner_codes()
    batch = run_batch(qc, codes)
    M, leak = encoded_block(batch, codes, len(codes), code_mask=(1 << 16) - 1)
    assert leak.max() <= 1e-20
    V = O.inner_target("UB", None, beta)
    assert op_norm_after_phase(M, V) <= 1e-10
    v = Vf.verify(qc, enc, "UB", None, beta)
    assert v.ok and v.certified and v.method == "inner_block", (v.reason, v.op_norm_error, v.block_error, v.leak_amplitude, v.gauss_residual)
    assert v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20
    assert v.gauss_residual <= 1e-10 and v.gauss_states == 273 and v.outer_bits_read == 0
    lm = api("su2plaq.metrics.logical:logical_metrics")(qc)
    assert lm["n_rot"] >= 1 and lm["qubits"] == qc.num_qubits
    assert _skeleton(C.build_UB(0.61)) == _skeleton(C.build_UB(0.23))
    frames = C.pair_frames(beta)
    assert len(frames) == 81 and all({"kappa", "pivot", "controls", "frame_gates"} <= set(f) for f in frames)


@functools.lru_cache(maxsize=None)
def _ub_outer():
    enc = _enc()
    C = api("su2plaq.circuits.rishon")
    Vf = api("su2plaq.rishon.verify")
    qc = C.build_UB(0.61, with_outer=True)
    return qc, Vf.verify(qc, enc, "UB", None, 0.61)


def test_M5_B1_physical_with_outer_and_gauss():
    """With the 32-qubit outer register present: registers d, o, then ancillas; no outer bit read; verdict ok with Gauss
    residual <= 1e-10 on the 273 sampled outputs; the explicit physical cross-check on the 17 closed states and the seeded
    sample agrees with the restricted target (1e-10)."""
    enc = _enc()
    Vf = api("su2plaq.rishon.verify")
    qc, v = _ub_outer()
    names = [r.name for r in qc.qregs]
    assert names[:2] == ["d", "o"] and qc.num_qubits >= 48
    lay = enc.layout_of(qc)
    assert lay.data == list(range(16)) and lay.outer == list(range(16, 48)) and lay.ancilla == list(range(48, qc.num_qubits))
    assert v.ok and v.certified and v.outer_bits_read == 0 and v.gauss_residual <= 1e-10 and v.gauss_states == 273
    assert v.op_norm_error <= 1e-10 and v.dirty_ancilla <= 1e-20
    x = Vf.physical_cross_check(qc, enc, "UB", None, 0.61)
    assert x["n_states"] == 273 and x["max_abs_diff"] <= 1e-10


@pytest.mark.parametrize("order", [1, 2])
def test_M5_S1_step_orders(order):
    """build_step(alpha, beta, order) equals the inner target 'step' of the same order (1e-10) at the nominal angles and at
    an alternate pair; order 1 = U_B U_E (electric layer first), order 2 = U_E(a/2) U_B U_E(a/2); the wrong order is
    rejected (the orders differ by O(alpha beta) >> 1e-10)."""
    enc = _enc()
    C = api("su2plaq.circuits.rishon")
    Vf = api("su2plaq.rishon.verify")
    for alpha, beta in ((0.37, 0.61), (1.70, 1.00)):
        qc = C.build_step(alpha, beta, order=order)
        assert _ops(qc) <= ALLOWED
        v = Vf.verify(qc, enc, "step", alpha, beta, order=order)
        assert v.ok and v.certified and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20, (v.reason, v.op_norm_error)
        assert v.gauss_residual <= 1e-10
    v = Vf.verify(C.build_step(0.37, 0.61, order=1), enc, "step", 0.37, 0.61, order=2)
    assert not v.ok and v.op_norm_error > 1e-3
