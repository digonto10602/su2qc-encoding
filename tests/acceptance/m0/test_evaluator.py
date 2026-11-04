"""M0-E3, E4, E5 — evaluator sensitivity on the 12-qubit encoding (prompts/002 §2.7, METHODS §6).
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
    assert v.ok and v.op_norm_error <= 1e-12 and v.max_leak <= 1e-14 and v.dirty_ancilla <= 1e-14
    assert v.outer_bits_read == 0 and v.method in ("inner_span", "physical") and v.engine == "sparse"
    for method in ("inner_span", "physical"):
        v2 = evaluate(qc, enc, I, method=method)
        assert v2.ok and v2.method == method and v2.op_norm_error <= 1e-12
    qc, r = _circ(False, 1)
    qc.x(r["a"][0])
    v = evaluate(qc, enc, I)
    assert not v.ok and max(v.max_leak, v.dirty_ancilla) >= 1 - 1e-12 and v.reason in ("leak", "dirty_ancilla")
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
    and is reported. The aer_mps engine agrees with the sparse engine on the electric step (1e-10)."""
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
    vm = evaluate(qc, enc, V, gauss=True, engine="aer_mps")
    assert vm.ok and vm.engine == "aer_mps" and vm.op_norm_error <= 1e-10 and vm.max_leak <= 1e-12
    qc, r = _circ(False)
    qc.swap(r["d"][0], r["d"][1])
    v = evaluate(qc, enc, np.eye(433, dtype=complex), gauss=True)
    assert not v.ok and v.max_leak <= 1e-12 and v.gauss_residual > 0.1
