"""M7-E1, B1..B3, S1, G1 — general circuits of the loop-string-hadron encoding (prompts/400 §1.5-1.6, §3 steps 7.5-7.7;
METHODS-lsh L7).  Exact-angle circuits: op_norm_error = block error + pruning bound + leak amplitude <= 1e-10
(prompts/004), weight diagnostics <= 1e-20 = (1e-10)^2 (as M1, M3).

Planner measurements (scratch/planner/proto_m7_lsh_circuit.py; reports/research/400 §5): U_B = transcoder (per 'in' site
cx, cx, rccx: 20 CX) + the 4-rotation flag walk of the spin-network circuit on the transcoded wires (54 CX) + transcoder
inverse: 94 CX, 4 rotations (-7/2, -1, 3, 3/2) x beta, 88 fixed T, 7 ancillas, depth 87; error 1.4e-14 .. 2.6e-14 at four
beta; step: 94 CX, 8 rotations (order 1) / 12 (order 2), the electric layer sits inside the transcoded frame; stand-alone
U_E: 8 phases, no CX; Gauss residual of all outputs 5e-16."""
import functools
from fractions import Fraction

import numpy as np
import pytest

from tests.acceptance._api import api, op_norm_after_phase

ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}
NOMINAL = (0.37, 0.61)
LINK_B_HALF = 0b100010          # only inner link b at j = 1/2: site c0 = 010 (l_nv), site c1 = 100 (l_vp)


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.lsh:LSH")()


def _ops(qc):
    return {inst.operation.name for inst in qc.data}


def _skeleton(qc):
    return [(inst.operation.name, tuple(qc.find_bit(q).index for q in inst.qubits)) for inst in qc.data]


@pytest.mark.parametrize("alpha", [0.37, 0.91])
def test_M7_E1_electric_step(alpha):
    """build_UE(alpha) on register d[12]: phases only (no CX, at most 8 rotations: the flux of an inner link is the sum of
    two loop-number bits of one site, never both 1), exact vs target 'UE' (1e-10); the code with only link b at j = 1/2
    gets the phase e^{-3 i alpha/4} (sign tested).  with_outer adds o[12] (not read); include_outer_electric adds the
    phases of the 8 outer links (at most 12 more rotations), reads the 12 outer qubits (305 outer-site blocks) and matches
    the outer-electric target."""
    enc = _enc()
    build_UE = api("su2plaq.circuits.lsh:build_UE")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    lmf = api("su2plaq.metrics.logical:logical_metrics")
    qc = build_UE(alpha)
    assert qc.num_qubits == 12 and [r.name for r in qc.qregs] == ["d"] and _ops(qc) <= {"p", "rz"}
    lm = lmf(qc)
    assert lm["cx"] == 0 and 4 <= lm["n_rot"] <= 8 and lm["t_fixed"] == 0 and lm["ancilla"] == 0
    v = evaluate(qc, enc, enc.target("UE", alpha, None))
    assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.gauss_residual <= 1e-10
    assert LINK_B_HALF in set(enc.inner_codes().tolist())
    b = run_batch(qc, np.array([LINK_B_HALF], dtype=np.int64))
    b0 = run_batch(qc, np.array([0], dtype=np.int64))
    assert len(b.keys) == 1 and b.keys[0] == LINK_B_HALF and len(b0.keys) == 1
    assert abs(b.amps[0] / b0.amps[0] - np.exp(-0.75j * alpha)) <= 1e-12
    qo = build_UE(alpha, with_outer=True)
    assert qo.num_qubits == 24 and [r.name for r in qo.qregs] == ["d", "o"]
    vo = evaluate(qo, enc, enc.target("UE", alpha, None), method="physical")
    assert vo.ok and vo.outer_bits_read == 0 and vo.n_inputs == 433
    qe = build_UE(alpha, with_outer=True, include_outer_electric=True)
    assert _ops(qe) <= {"p", "rz"} and lm["n_rot"] + 8 <= lmf(qe)["n_rot"] <= lm["n_rot"] + 12
    ve = evaluate(qe, enc, enc.target("UE", alpha, None, include_outer_electric=True), method="physical")
    assert ve.ok and ve.op_norm_error <= 1e-10 and ve.outer_bits_read == 12 and ve.n_blocks == 305
    with pytest.raises(ValueError):
        build_UE(alpha, include_outer_electric=True)


@pytest.mark.parametrize("beta", [0.4, 0.61, 1.0, 2.0])
def test_M7_B1_magnetic_inner_block(beta):
    """build_UB(beta) is exact on the 47 inner codes: the 47x47 block (ancillas 0) equals the inner target exp(-i beta K_LSH)
    up to one global phase (1e-10), leak <= 1e-12; registers d[12] then ancillas, no outer register; allowed gates only; the
    gate skeleton does not depend on beta; every rotation angle is a rational multiple of beta with denominator <= 4
    (angle-linear, Lean-certifiable; measured -7/2, -1, 3, 3/2).  Cost sanity (twice the plan's construction: 94 CX,
    4 rotations, 7 ancillas): cx <= 188, 1 <= n_rot <= 16, ancilla <= 16."""
    enc = _enc()
    build_UB = api("su2plaq.circuits.lsh:build_UB")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    encoded_block = api("su2plaq.evaluate.sparse_sim:encoded_block")
    qc = build_UB(beta)
    assert qc.qregs[0].name == "d" and qc.qregs[0].size == 12 and "o" not in [r.name for r in qc.qregs]
    assert _ops(qc) <= ALLOWED
    codes = enc.inner_codes()
    batch = run_batch(qc, codes)
    M, leak = encoded_block(batch, codes, len(codes), code_mask=(1 << 12) - 1)
    assert leak.max() <= 1e-12
    V = enc.inner_target("UB", None, beta)
    assert V.shape == (47, 47) and op_norm_after_phase(M, V) <= 1e-10
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    v = evaluate(qc, enc, enc.target("UB", None, beta))
    assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20
    lm = api("su2plaq.metrics.logical:logical_metrics")(qc)
    assert 1 <= lm["n_rot"] <= 16 and 0 < lm["cx"] <= 188 and lm["ancilla"] <= 16 and lm["qubits"] == 12 + lm["ancilla"]
    for th in lm["rz_angles"]:
        f = Fraction(th / beta).limit_denominator(4)
        assert abs(float(f) * beta - th) <= 1e-9, (th, beta)
    assert _skeleton(qc) == _skeleton(build_UB(beta * 1.7))


@functools.lru_cache(maxsize=None)
def _ub_outer():
    enc = _enc()
    qc = api("su2plaq.circuits.lsh:build_UB")(0.61, with_outer=True)
    v = api("su2plaq.evaluate.evaluator:evaluate")(qc, enc, enc.target("UB", None, 0.61), method="physical", gauss=True)
    return qc, v


def test_M7_B2_physical_states():
    """All 433 physical states with the 12-qubit outer register present (explicit assembly): error <= 1e-10 incl. leak
    amplitude; the outer register is never read (one block: in the (inner | outer) pairing the plaquette needs no
    outer-site information); ancillas declared after d, o; sparse engine, certified."""
    enc = _enc()
    qc, v = _ub_outer()
    assert [r.name for r in qc.qregs][:2] == ["d", "o"] and qc.qregs[0].size == 12 and qc.qregs[1].size == 12
    assert v.ok and v.method == "physical" and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20
    assert v.n_inputs == 433 and v.outer_bits_read == 0 and v.n_blocks == 1
    assert v.engine == "sparse" and v.certified
    layout = enc.layout_of(qc)
    assert layout.data == list(range(12)) and layout.outer == list(range(12, 24)) and layout.ancilla == list(range(24, qc.num_qubits))


def test_M7_B3_gauss_and_clean_ancillas():
    """Gauss residual of every decoded output <= 1e-10 (exact-angle rule; a decoded output that broke the Abelian Gauss law
    on a virtual link would show a residual >= 1/2 times its amplitude); every ancilla returns to |0> (dirty weight
    <= 1e-20); the outer qubits are untouched by any gate."""
    qc, v = _ub_outer()
    assert v.gauss_residual <= 1e-10 and v.dirty_ancilla <= 1e-20 and v.extra["max_span_leak"] <= 1e-12
    touched = {qc.find_bit(q).index for inst in qc.data for q in inst.qubits}
    assert not (touched & set(range(12, 24)))


@pytest.mark.parametrize("order", [1, 2])
def test_M7_S1_step_orders(order):
    """build_step(alpha, beta, order) equals the 'step' target of the same order (1e-10) at the nominal angles and at the
    alternates with the same skeleton; order 1 = U_B U_E (electric layer first), order 2 = U_E(a/2) U_B U_E(a/2).
    Rejected (error > 1e-3): the other order's target, and the target at -beta (as in M3-S1 this pins the circuit to the
    sign gauge of the target; U_B(-beta) is gauge-equivalent, M7-C2).  Rotation count sanity: at most 8 electric phases per
    electric layer on top of the U_B rotations."""
    enc = _enc()
    circ = api("su2plaq.circuits.lsh")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    lmf = api("su2plaq.metrics.logical:logical_metrics")
    skel = None
    for alpha, beta in ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00)):
        qc = circ.build_step(alpha, beta, order=order)
        assert _ops(qc) <= ALLOWED and qc.qregs[0].name == "d" and qc.qregs[0].size == 12
        v = evaluate(qc, enc, enc.target("step", alpha, beta, order=order))
        assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20
        assert v.gauss_residual <= 1e-10
        sk = _skeleton(qc)
        assert skel is None or sk == skel
        skel = sk
    qc = circ.build_step(0.37, 0.61, order=order)
    n_ub = lmf(circ.build_UB(0.61))["n_rot"]
    assert n_ub + 4 * order <= lmf(qc)["n_rot"] <= n_ub + 8 * order and lmf(qc)["cx"] <= 188
    v = evaluate(qc, enc, enc.target("step", 0.37, 0.61, order=3 - order))
    assert not v.ok and v.op_norm_error > 1e-3
    v = evaluate(qc, enc, enc.target("step", 0.37, -0.61, order=order))
    assert not v.ok and v.op_norm_error > 1e-3
    qo = circ.build_step(0.37, 0.61, order=order, with_outer=True)
    vo = evaluate(qo, enc, enc.target("step", 0.37, 0.61, order=order), method="physical")
    assert vo.ok and vo.outer_bits_read == 0 and vo.gauss_residual <= 1e-10 and vo.n_inputs == 433


def test_M7_G1_evaluator_sees_abelian_gauss_law_violations():
    """The unchanged evaluator, fed by the LSH encoding's decode_state, rejects circuits that break the LSH validity rules
    (identity target, 433 inputs, outer register present):
    (a) swap(l_nv, l_vp) on 'in' site 0 breaks the AGL on an inner link -> data code outside the 47 inner codes -> `leak`
        with amplitude 1;
    (b) the site map 001 <-> 110 on 'in' site 0 (ccx, cx, cx, ccx; J = 0 <-> J = 1 with both inner links at 1/2) keeps the
        data inside the 47 inner codes but breaks the AGL on the virtual link -> no leak, span leak 1, Gauss residual >= 1/2;
    (c) x on an ancilla -> `dirty_ancilla`; x on an outer qubit -> `writes_outer`;
    (d) cz(o[0], d[0]) (l_12 of 'out' site 0 with l_pn of 'in' site 0: both 1 on physical states with J_0 = 0) reads one
        outer qubit and changes the operator -> rejected with error 2;
    (e) cz(o[1], d[0]) (l_2v of 'out' site 0 with l_pn of 'in' site 0) is the identity on every physical state, because
        the AGL on the virtual link forbids both bits at once -> accepted (2 blocks, error <= 1e-10): the Abelian Gauss
        law is what makes this gate trivial."""
    from qiskit import QuantumCircuit, QuantumRegister

    enc = _enc()
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    ident = np.eye(433, dtype=np.complex128)

    def circuit(n_anc=0):
        regs = [QuantumRegister(12, "d"), QuantumRegister(12, "o")] + ([QuantumRegister(n_anc, "a")] if n_anc else [])
        return QuantumCircuit(*regs)

    qa = circuit()
    qa.swap(1, 2)
    va = evaluate(qa, enc, ident, method="physical")
    assert not va.ok and va.reason == "leak" and abs(va.leak_amplitude - 1.0) <= 1e-12
    qb = circuit()
    qb.ccx(1, 2, 0)
    qb.cx(0, 1)
    qb.cx(0, 2)
    qb.ccx(1, 2, 0)
    vb = evaluate(qb, enc, ident, method="physical")
    assert not vb.ok and vb.leak_amplitude <= 1e-12 and vb.gauss_residual >= 0.5 - 1e-10
    assert abs(vb.extra["max_span_leak"] - 1.0) <= 1e-12 and vb.op_norm_error >= 1.0 - 1e-12
    qc = circuit(1)
    qc.x(24)
    vc = evaluate(qc, enc, ident, method="physical")
    assert not vc.ok and vc.reason == "dirty_ancilla"
    qw = circuit()
    qw.x(12)
    assert evaluate(qw, enc, ident, method="physical").reason == "writes_outer"
    qd = circuit()
    qd.cz(12, 0)
    vd = evaluate(qd, enc, ident)
    assert not vd.ok and vd.reason == "error" and vd.outer_bits_read == 1 and abs(vd.op_norm_error - 2.0) <= 1e-10
    qe = circuit()
    qe.cz(13, 0)
    ve = evaluate(qe, enc, ident)
    assert ve.ok and ve.outer_bits_read == 1 and ve.n_blocks == 2 and ve.op_norm_error <= 1e-10 and ve.gauss_residual <= 1e-10
