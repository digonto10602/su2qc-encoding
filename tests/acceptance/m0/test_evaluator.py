"""M0-E3, E4, E5, E6 — evaluator sensitivity on the 12-qubit encoding (prompts/002 §2.7, prompts/004, METHODS §6).
Uses only the codec/physical_vectors/layout_of of TwelveQubit (built in step 0.8) and hand-made circuits; it does
not import su2plaq.circuits. Separations are discrete and large (error 0 vs >= 0.5 / 0.1, leak 1)."""
import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

import functools

from tests.acceptance._api import api


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.twelve:TwelveQubit")()


def _circ(with_outer: bool, n_anc: int = 0) -> tuple[QuantumCircuit, dict]:
    d = QuantumRegister(12, "d")
    regs = [d]
    if with_outer:
        regs.append(QuantumRegister(16, "o"))
    if n_anc:
        regs.append(QuantumRegister(n_anc, "a"))
    qc = QuantumCircuit(*regs)
    return qc, {r.name: r for r in regs}


def test_M0_E3_sensitivity():
    """identity -> ok (error 0, leak 0); X on an ancilla -> leak 1 (not ok); Z on a data j-qubit -> error >= 0.5;
    CX(inner -> outer) -> rejected as writes_outer; CZ(outer, inner) and CX(outer -> inner) -> accepted as valid
    circuits (outer read, not written); x z x z on an ancilla = -1 global phase -> ok."""
    enc = _enc()
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    I = np.eye(433, dtype=complex)
    qc, r = _circ(False)
    v = evaluate(qc, enc, I)
    assert v.ok and v.op_norm_error <= 1e-12 and v.leak_amplitude <= 1e-14 and v.max_leak <= 1e-28  # prompts/004: leak as amplitude; weight = amplitude^2
    assert v.outer_bits_read == 0 and v.method in ("inner_span", "physical") and v.engine == "sparse"
    for method in ("inner_span", "physical"):
        v2 = evaluate(qc, enc, I, method=method)
        assert v2.ok and v2.method == method and v2.op_norm_error <= 1e-12
    qc, r = _circ(False, 1)
    qc.x(r["a"][0])
    v = evaluate(qc, enc, I)
    assert not v.ok and max(v.max_leak, v.dirty_ancilla) >= 1 - 1e-12 and v.reason in ("leak", "dirty_ancilla")
    assert v.leak_amplitude >= 1 - 1e-12 and v.op_norm_error >= v.leak_amplitude  # prompts/004: the leak amplitude is part of the error bound
    qc, r = _circ(False)
    qc.z(r["d"][2])
    v = evaluate(qc, enc, I)
    assert not v.ok and v.op_norm_error >= 0.5 and v.reason == "error"
    qc, r = _circ(True)
    qc.cx(r["d"][2], r["o"][1])
    v = evaluate(qc, enc, I)
    assert not v.ok and v.reason == "writes_outer"
    qc, r = _circ(True)
    qc.cz(r["o"][1], r["d"][2])
    v = evaluate(qc, enc, I)
    assert v.reason != "writes_outer" and v.outer_bits_read == 1 and v.method == "physical"
    qc, r = _circ(True)
    qc.cx(r["o"][1], r["d"][0])
    v = evaluate(qc, enc, I)
    assert v.reason != "writes_outer" and v.outer_bits_read == 1
    qc, r = _circ(False, 1)
    for g in ("x", "z", "x", "z"):
        getattr(qc, g)(r["a"][0])
    v = evaluate(qc, enc, I)
    assert v.ok and abs(v.phase + 1) <= 1e-12


def test_M0_E4_outer_control_blocks():
    """Entanglement with the controls is an error, not a global phase: p(theta) on an outer j-qubit (phase that depends
    on the outer pattern) -> error > 0.1; cz(outer, data) -> error > 0.1; a genuinely global phase on the whole
    operator is accepted. The 'physical' and 'inner_span' methods agree on an outer-blind diagonal circuit."""
    enc = _enc()
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    I = np.eye(433, dtype=complex)
    qc, r = _circ(True)
    qc.p(0.7, r["o"][1])         # q_j of outer link 0
    v = evaluate(qc, enc, I)
    assert v.reason != "writes_outer" and not v.ok and v.op_norm_error > 0.1
    qc, r = _circ(True)
    qc.cz(r["o"][1], r["d"][2])
    v = evaluate(qc, enc, I)
    assert not v.ok and v.op_norm_error > 0.1
    # an outer-blind diagonal circuit: p on the j-qubit of link b with target = exp(-i alpha H_E) restricted to link b
    basis = enc.basis
    alpha = 0.37
    jb = np.array([lab[0][0] for lab in basis.labels])
    Vb = np.diag(np.exp(-1j * alpha * jb * (jb + 1)))
    qc, r = _circ(True)
    qc.p(-0.75 * alpha, r["d"][2])
    va = evaluate(qc, enc, Vb, method="physical")
    vb = evaluate(qc, enc, Vb, method="inner_span")
    assert va.ok and vb.ok and va.op_norm_error <= 1e-12 and vb.op_norm_error <= 1e-12
    # the same with a global phase e^{i 0.3} applied on every component: ok, phase reported
    qc.global_phase = 0.3
    vc = evaluate(qc, enc, Vb)
    assert vc.ok and abs(vc.phase - np.exp(0.3j)) <= 1e-10


def test_M0_E5_gauss_of_outputs():
    """Gauss residual of the decoded outputs: the exact electric step as p gates (gauge invariant) gives <= 1e-10; a
    code-preserving but gauge-violating gate (swap of q_m' and q_m on link b, i.e. m_L <-> m_R) gives residual > 0.1
    and is reported. The aer_mps engine agrees with the sparse engine on the electric step at 1e-9 and the verdict is
    certified: Aer's MPS contraction is accurate only to ~2e-10 per amplitude (reports/tests/008), so 1e-9 (5x the
    measured engine floor) is the tightest tolerance at which an aer_mps verdict can be certified; the sparse-engine
    assertions stay at 1e-10 (prompts/003 §3). The Gauss tolerance defaults to 1e-10 for exact-angle circuits and the
    verdict records the tolerances it was judged by. prompts/004: there is no separate leak tolerance any more — the
    leak is judged as an amplitude inside `op_norm_error` (= block error + leak amplitude), so `tolerances` has two
    keys and the aer_mps leak amplitude (certified per-physical-state bound from directly contracted weights,
    noise <= 4e-10 measured in reports/research/003) must also be <= 1e-9."""
    enc = _enc()
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    target = api("su2plaq.exact.operators:target")
    alpha = 0.37
    V = target(enc.basis, "UE", alpha=alpha)
    qc, r = _circ(False)
    for q in (2, 5, 8, 11):
        qc.p(-0.75 * alpha, r["d"][q])
    v = evaluate(qc, enc, V, gauss=True)
    assert v.ok and v.op_norm_error <= 1e-10 and v.gauss_residual <= 1e-10
    assert v.certified and v.engine_accuracy == 0.0 and v.tolerances == dict(tol_err=1e-10, tol_gauss=1e-10)  # prompts/004: no tol_leak
    assert v.leak_amplitude <= 1e-10 and v.block_error <= v.op_norm_error
    vm = evaluate(qc, enc, V, gauss=True, engine="aer_mps", tol_err=1e-9, tol_gauss=1e-9)
    assert vm.ok and vm.engine == "aer_mps" and vm.op_norm_error <= 1e-9 and vm.leak_amplitude <= 1e-9 and vm.gauss_residual <= 1e-9
    assert vm.certified and 0.0 < vm.engine_accuracy <= 2e-10 and vm.tolerances == dict(tol_err=1e-9, tol_gauss=1e-9)
    assert vm.max_leak <= vm.leak_amplitude ** 2 + 1e-30  # aer_mps: max_leak is the per-physical-state weight bound, amplitude = its root
    # an aer_mps verdict judged at the exact-angle tolerances is not certified (engine floor above 1e-10 / 1e-12)
    vu = evaluate(qc, enc, V, gauss=True, engine="aer_mps")
    assert vu.engine == "aer_mps" and not vu.certified
    qc, r = _circ(False)
    qc.swap(r["d"][0], r["d"][1])
    v = evaluate(qc, enc, np.eye(433, dtype=complex), gauss=True)
    assert not v.ok and v.leak_amplitude <= 1e-12 and v.gauss_residual > 0.1  # code-preserving: no leak at all (amplitude, prompts/004)


def test_M0_E6_leak_is_judged_as_amplitude():
    """prompts/004 (audit 001 N1, Digonto 2026-11-04): a leaked amplitude delta enters the physical-block error only as
    O(delta^2), so a weight tolerance of 1e-12 let ancilla errors of amplitude 1e-6 pass as 'exact'. The criterion is now
    the combined bound  op_norm_error = ||A - e^{i phi} V||_2 + ||X||_2 <= tol_err  with ||X||_2 = sqrt(lambda_max(X^dag X))
    the operator norm of the out-of-code part of the output on the physical inputs (reports/research/003 §2).
    cry(theta) from the j-qubit of link b onto a fresh ancilla (target identity) leaks amplitude sin(theta/2) on every
    state with j_b = 1/2 and nothing else, so ||X||_2 = sin(theta/2) exactly (X^dag X = sin^2 Pi_{j_b=1/2}); the auditor's
    accepted case theta = 1.9e-6 (leaked amplitude 9.5e-7) must now be rejected, as must theta = 1e-8 (5e-9); theta =
    1e-10 (5e-11, below 1e-10 by a factor 2) is accepted: the threshold is the amplitude 1e-10, not stricter. The same
    construction into an INVALID data code (x; cry(theta, q_j, q_m'); x — rotates 000 -> 001 on j_b = 0 links) is
    rejected too. Tolerance on ||X||_2: 1e-3 relative (float64 on a 433x433 eigenvalue problem gives ~1e-14 absolute;
    1e-3 leaves room for an implementation that bounds rather than computes lambda_max, e.g. the aer_mps route).
    A synthesised-circuit budget judges the same quantity: with synth_tolerances(1, 1e-6) (tol_err 1.001e-6) the
    theta = 1.9e-6 case is a legitimately rounded single rotation and passes. Diagnostics: leak_amplitude^2 >= max_leak
    (operator norm over superpositions >= the largest single-state weight), op_norm_error >= leak_amplitude."""
    enc = _enc()
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    synth_tolerances = api("su2plaq.evaluate.evaluator:synth_tolerances")
    I = np.eye(433, dtype=complex)
    for theta, accepted in ((1.9e-6, False), (1e-8, False), (1e-10, True)):
        qc, r = _circ(False, 1)
        qc.cry(theta, r["d"][2], r["a"][0])
        v = evaluate(qc, enc, I)
        s = np.sin(theta / 2)
        assert abs(v.leak_amplitude - s) <= 1e-3 * s, (theta, v.leak_amplitude, s)
        assert v.leak_amplitude ** 2 >= v.max_leak - 1e-30 and v.op_norm_error >= v.leak_amplitude - 1e-16
        assert v.engine == "sparse" and v.certified and v.tolerances == dict(tol_err=1e-10, tol_gauss=1e-10)
        if accepted:
            assert v.ok and v.reason == "ok", (v.reason, v.op_norm_error)
        else:
            assert not v.ok and v.reason in ("dirty_ancilla", "leak") and v.failing_inputs, (v.reason, v.op_norm_error)
    # the auditor's case under a synthesised budget of one rotation at eps = 1e-6: a correctly rounded rotation passes
    qc, r = _circ(False, 1)
    qc.cry(1.9e-6, r["d"][2], r["a"][0])
    tol = synth_tolerances(1, 1e-6)
    assert tol == dict(tol_err=1e-6 + 1e-9, tol_gauss=1e-6 + 1e-9)
    v = evaluate(qc, enc, I, **tol)
    assert v.ok and v.certified and v.tolerances == tol and abs(v.leak_amplitude - np.sin(0.95e-6)) <= 1e-9
    # leak into an invalid data code (000 -> 001 on links with j_b = 0): same amplitude, rejected
    theta = 1.9e-6
    qc, r = _circ(False)
    qc.x(r["d"][2]); qc.cry(theta, r["d"][2], r["d"][0]); qc.x(r["d"][2])
    v = evaluate(qc, enc, I)
    s = np.sin(theta / 2)
    assert not v.ok and v.reason == "leak" and abs(v.leak_amplitude - s) <= 1e-3 * s and v.dirty_ancilla <= 1e-30
    # op_norm_error is the combined bound: block error + leak amplitude (sparse: exact, dropped_total = 0)
    assert abs(v.op_norm_error - (v.block_error + v.leak_amplitude)) <= 1e-15
