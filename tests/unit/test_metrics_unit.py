"""Unit tests for su2plaq.metrics (own checks)."""
import math

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Operator

from su2plaq.metrics import cliffordt as ct
from su2plaq.metrics import logical as lg


def test_logical_metrics_register_ancilla_and_angles():
    d, o, a = QuantumRegister(3, "d"), QuantumRegister(2, "o"), QuantumRegister(1, "a")
    qc = QuantumCircuit(d, o, a)
    qc.rz(0.3, d[0])
    qc.rz(math.pi / 4, d[1])
    qc.rz(3 * math.pi / 4, d[1])
    qc.rz(math.pi / 2, d[1])
    qc.t(a[0])
    qc.cx(d[0], a[0])
    m = lg.logical_metrics(qc)
    assert m["n_rot"] == 1 and m["t_fixed"] == 3 and m["cx"] == 1 and m["qubits"] == 6 and m["ancilla"] == 1
    assert m["rz_angles"] == [0.3]


def test_lower_rejects_unitary_measure_and_wrapped_mcx():
    qc = QuantumCircuit(1)
    qc.unitary(np.eye(2), [0])
    with pytest.raises(ValueError):
        lg.lower(qc)
    qm = QuantumCircuit(1, 1)
    qm.measure(0, 0)
    with pytest.raises(ValueError):
        lg.lower(qm)
    inner = QuantumCircuit(5)
    inner.mcx([0, 1, 2], 3)
    outer = QuantumCircuit(6)
    outer.append(inner.to_gate(), range(5))
    with pytest.raises(ValueError):
        lg.lower(outer)


@pytest.mark.parametrize("k", range(-8, 9))
def test_exact_words_for_multiples_of_pi_over_4(k):
    th = k * math.pi / 4
    w = ct.pygridsynth_word(th, 1e-6)
    assert ct.word_error(w, th) < 1e-12 and w.count("T") == (k % 2)


def test_word_error_detects_wrong_word():
    assert ct.word_error("HT", 0.37) > 0.1


def test_word_cache_returns_identical_object():
    assert ct.pygridsynth_word(0.37, 1e-4) is ct.pygridsynth_word(0.37, 1e-4)


@pytest.mark.parametrize("eps", [1e-3, 1e-6])
def test_synthesize_reproduces_circuit_up_to_global_phase_and_bound(eps):
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.rz(0.37, 0)
    qc.cx(0, 1)
    qc.rz(-0.55, 1)
    qc.rz(math.pi / 4, 1)
    qc.cp(0.9, 0, 1)
    out, info = ct.synthesize(qc, eps)
    assert set(out.count_ops()) <= {"h", "s", "t", "cx", "sdg", "tdg", "x", "z"}
    U, V = Operator(qc).data, Operator(out).data
    ov = np.trace(V.conj().T @ U)
    err = np.linalg.norm(U - ov / abs(ov) * V, 2)
    assert err <= info["error_bound_sum"] + 1e-9
    assert info["n_rot"] == 5  # rz(0.37), rz(-0.55) and the three rz of cp(0.9)
    assert info["error_bound_sum"] == pytest.approx(info["n_rot"] * eps)
    assert info["error_measured_sum"] == pytest.approx(sum(p["error"] for p in info["per_rotation"])) and 0 < info["error_measured_sum"] <= info["error_bound_sum"]
    assert info["t_rot"] == sum(p["t"] for p in info["per_rotation"] if not p["exact"])


def test_t_table_rows_consistent():
    qc = QuantumCircuit(2)
    qc.cp(0.4, 0, 1)
    qc.t(0)
    rows = ct.t_table(qc, eps_list=(1e-4, 1e-6), qiskit=False)
    m = lg.logical_metrics(qc)
    for r in rows:
        assert r["t_fixed"] == m["t_fixed"] and r["n_rot"] == m["n_rot"] == 3
        assert r["t_total"] == r["t_fixed"] + r["t_rot_pygridsynth"] and r["t_qiskit"] is None
        assert r["t_est"] == pytest.approx(ct.t_estimate(3, m["t_fixed"], r["eps"]))
    rows_q = ct.t_table(qc, eps_list=(1e-4,), qiskit=True)
    assert abs(rows_q[0]["t_qiskit"] - rows_q[0]["t_total"]) <= 6 * 3


def test_lower_is_program_order_and_counts_match_whole_circuit_transpile():
    from qiskit import transpile

    qc = QuantumCircuit(5)
    qc.h(0)
    qc.ccx(0, 1, 2)
    qc.rccx(1, 2, 3)
    qc.cp(0.4, 3, 4)
    qc.swap(0, 4)
    qc.ch(1, 0)
    qc.crx(0.3, 2, 3)
    qc.p(0.2, 1)
    low = lg.lower(qc)
    ref = transpile(qc, basis_gates=lg.LOGICAL_BASIS, optimization_level=0, seed_transpiler=lg.SEED, qubits_initially_zero=False)
    assert dict(low.count_ops()) == dict(ref.count_ops())
    U, V = Operator(low).data, Operator(qc).data
    ov = np.trace(V.conj().T @ U)
    assert np.abs(U - ov / abs(ov) * V).max() < 1e-12
    # program order: the opening and closing H of 40 independent rccx are adjacent, not hoisted together
    big = QuantumCircuit(42)
    for k in range(40):
        big.rccx(0, 1, 2 + k)
    lowb = lg.lower(big)
    first_targets = {lowb.find_bit(i.qubits[-1]).index for i in lowb.data[:9]}
    assert len(first_targets) <= 2   # the first 9 gates belong to the first rccx (target qubit 2) only


def test_lower_does_not_confuse_same_named_custom_gates():
    a = QuantumCircuit(2, name="m")
    a.cx(0, 1)
    b = QuantumCircuit(2, name="m")
    b.cz(0, 1)
    q = QuantumCircuit(2)
    q.append(a.to_gate(), [0, 1])
    q.append(b.to_gate(), [0, 1])
    U, V = Operator(lg.lower(q)).data, Operator(q).data
    ov = np.trace(V.conj().T @ U)
    assert np.abs(U - ov / abs(ov) * V).max() < 1e-12


def test_lower_inlines_nested_custom_gates_in_program_order():
    inner = QuantumCircuit(4, name="m")
    for k in range(2):
        inner.rccx(0, 1, 2 + k)
    mid = QuantumCircuit(4, name="m")
    mid.append(inner.to_gate(), range(4))
    mid.t(0)
    top = QuantumCircuit(4)
    top.append(mid.to_gate(), range(4))
    low = lg.lower(top)
    U, V = Operator(low).data, Operator(top).data
    ov = np.trace(V.conj().T @ U)
    assert np.abs(U - ov / abs(ov) * V).max() < 1e-12
    flat = QuantumCircuit(4)
    flat.rccx(0, 1, 2), flat.rccx(0, 1, 3), flat.t(0)
    assert dict(low.count_ops()) == dict(lg.lower(flat).count_ops())


def test_disguised_gates_are_lowered_and_counted_by_content():
    t_as_x = QuantumCircuit(1, name="t")
    t_as_x.x(0)
    cx_as_cz = QuantumCircuit(2, name="cx")
    cx_as_cz.cz(0, 1)
    h_as_s = QuantumCircuit(1, name="h")
    h_as_s.s(0)
    qc = QuantumCircuit(2)
    qc.append(t_as_x.to_gate(), [0])
    qc.append(cx_as_cz.to_gate(), [0, 1])
    qc.append(h_as_s.to_gate(), [1])
    m = lg.logical_metrics(qc)
    assert m["t_fixed"] == 0 and m["n_rot"] == 0
    assert m["cx"] == 1   # a CZ lowers to one CX (+ H), not the 'cx' by name
    ops = dict(lg.lower(qc).count_ops())
    assert ops.get("t", 0) == 0 and ops.get("x", 0) >= 1 and ops.get("s", 0) >= 1
    U, V = Operator(lg.lower(qc)).data, Operator(qc).data
    ov = np.trace(V.conj().T @ U)
    assert np.abs(U - ov / abs(ov) * V).max() < 1e-12
    from qiskit.circuit import Gate

    bad = QuantumCircuit(1)
    bad.append(Gate("t", 1, []), [0])
    with pytest.raises(ValueError, match="no definition"):
        lg.lower(bad)
