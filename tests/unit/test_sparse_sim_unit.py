"""Unit tests for su2plaq.evaluate.sparse_sim (own checks)."""
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, random_unitary

from su2plaq.evaluate import sparse_sim as ss


def _dense(batch, n_in):
    out = np.zeros((2 ** batch.n_qubits, n_in), complex)
    np.add.at(out, (batch.keys, batch.cols), batch.amps)
    return out


def test_global_phase_and_unitary_gate():
    qc = QuantumCircuit(3, global_phase=0.7)
    qc.append(random_unitary(4, seed=3), [2, 0])  # two-qubit unitary, non-adjacent qubits
    qc.h(1)
    qc.ccz(0, 1, 2)
    qc.sx(1)
    inputs = np.arange(8, dtype=np.int64)
    assert np.abs(_dense(ss.run_batch(qc, inputs), 8) - Operator(qc).data).max() < 1e-13


def test_ordering_heuristic_matches_plain_order(monkeypatch):
    rng = np.random.default_rng(1)
    qc = QuantumCircuit(5)
    for _ in range(50):
        g = rng.choice(["h", "cx", "t", "ccx", "cp", "swap"])
        qs = [int(q) for q in rng.choice(5, 3, replace=False)]
        if g == "h":
            qc.h(qs[0])
        elif g == "cx":
            qc.cx(qs[0], qs[1])
        elif g == "t":
            qc.t(qs[0])
        elif g == "ccx":
            qc.ccx(*qs)
        elif g == "cp":
            qc.cp(0.3, qs[0], qs[1])
        else:
            qc.swap(qs[0], qs[1])
    inputs = np.arange(32, dtype=np.int64)
    a = _dense(ss.run_batch(qc, inputs), 32)
    monkeypatch.setattr(ss, "_schedule", lambda ops: list(range(len(ops))))
    b = _dense(ss.run_batch(qc, inputs), 32)
    assert np.abs(a - b).max() < 1e-13 and np.abs(a - Operator(qc).data).max() < 1e-13


def test_hh_cancels_exactly_and_support_stays_small():
    qc = QuantumCircuit(1)
    qc.h(0)
    qc.h(0)
    b = ss.run_batch(qc, np.array([0, 1], dtype=np.int64))
    assert len(b.keys) == 2 and np.abs(b.amps - 1).max() < 1e-15


def test_cap_raises_and_does_not_hang():
    qc = QuantumCircuit(20)
    for q in range(20):
        qc.h(q)
    with pytest.raises(ss.SimCapExceeded):
        ss.run_batch(qc, np.array([0], dtype=np.int64), cap=1000)


def test_measure_rejected():
    qc = QuantumCircuit(1, 1)
    qc.measure(0, 0)
    with pytest.raises(ValueError):
        ss.run_batch(qc, np.array([0], dtype=np.int64))


def test_encoded_block_masks_outside_bits():
    qc = QuantumCircuit(3)
    qc.h(2)  # ancilla in superposition: half of the weight leaks
    b = ss.run_batch(qc, np.array([0b01], dtype=np.int64))
    M, leak = ss.encoded_block(b, np.array([0b00, 0b01], dtype=np.int64), 1, code_mask=0b011)
    assert abs(M[1, 0] - 2 ** -0.5) < 1e-15 and abs(leak[0] - 0.5) < 1e-15


# ---------------------------------------------------------------- certified pruning, mcx rejection, Aer engines
from qiskit.quantum_info import Statevector  # noqa: E402


def test_hh_cancellation_has_negligible_certified_bound():
    qc = QuantumCircuit(3)
    for q in range(3):
        qc.h(q)
        qc.h(q)
    b = ss.run_batch(qc, np.array([0, 5], dtype=np.int64))
    assert len(b.keys) == 2 and b.dropped_total <= 1e-15 and np.abs(b.amps - 1).max() < 1e-15


def test_testers_scenario_error_not_hidden():
    """m qubits in |+>, then N tiny Ry on an empty qubit.  With the relative threshold nothing is dropped and the
    result is exact; the certified bound is >= the true error in any case."""
    m, N, theta = 14, 10, 2e-11
    qc = QuantumCircuit(m + 1)
    for q in range(m):
        qc.h(q)
    for _ in range(N):
        qc.ry(theta, m)
    b = ss.run_batch(qc, np.array([0], dtype=np.int64))
    sv = Statevector(qc).data
    err = np.linalg.norm(_dense(b, 1)[:, 0] - sv)
    assert err <= b.dropped_l2[0] + 1e-14
    assert abs(np.sum(np.abs(b.amps[(b.keys >> m) & 1 == 1]) ** 2) ** 0.5 - np.sin(N * theta / 2)) < 1e-12


def test_certified_bound_dominates_true_error_when_pruning_is_forced(monkeypatch):
    monkeypatch.setattr(ss, "PRUNE_REL", 2e-3)  # aggressive threshold to force drops
    rng = np.random.default_rng(5)
    qc = QuantumCircuit(9)
    for q in range(8):
        qc.h(q)
    for _ in range(6):
        qc.ry(float(rng.uniform(0, 0.05)), int(rng.integers(0, 9)))
        qc.cx(int(rng.integers(0, 8)), 8)
        qc.h(int(rng.integers(0, 9)))
    inputs = np.arange(4, dtype=np.int64)
    b = ss.run_batch(qc, inputs)
    exact = Operator(qc).data[:, :4]
    err = np.linalg.norm(_dense(b, 4) - exact, axis=0)
    assert b.dropped_l2.max() > 0 and np.all(err <= b.dropped_l2 * (1 + 1e-9) + 1e-14)
    assert b.dropped_total >= np.linalg.norm(err) - 1e-14


@pytest.mark.parametrize("n_ctrl", [3, 4])
def test_native_mcx_with_three_or_more_controls_is_rejected(n_ctrl):
    qc = QuantumCircuit(n_ctrl + 3)  # idle qubits present: Qiskit would silently use them as ancillas
    qc.mcx(list(range(n_ctrl)), n_ctrl)
    with pytest.raises(ValueError, match="mcx"):
        ss.run_batch(qc, np.array([0], dtype=np.int64))


def test_exact_multi_controlled_gates_still_accepted():
    qc = QuantumCircuit(5)
    qc.mcx([0, 1], 2)
    qc.mcp(0.37, [0, 1, 2], 3)
    qc.cswap(0, 1, 2)
    qc.rccx(0, 1, 4)
    qc.append(__import__("qiskit.circuit.library", fromlist=["C3SXGate"]).C3SXGate(), [0, 1, 2, 3])
    inputs = np.arange(32, dtype=np.int64)
    assert np.abs(_dense(ss.run_batch(qc, inputs), 32) - Operator(qc).data).max() < 1e-12


def test_aer_engines_agree_with_sparse():
    from su2plaq.evaluate import aer_check as ac

    rng = np.random.default_rng(2)
    qc = QuantumCircuit(7)
    for _ in range(40):
        g = rng.choice(["h", "cx", "t", "ccx", "rz"])
        q = [int(x) for x in rng.choice(7, 3, replace=False)]
        {"h": lambda: qc.h(q[0]), "cx": lambda: qc.cx(q[0], q[1]), "t": lambda: qc.t(q[0]),
         "ccx": lambda: qc.ccx(*q), "rz": lambda: qc.rz(0.4, q[0])}[g]()
    inputs = np.arange(8, dtype=np.int64)
    codes = np.arange(0, 32, dtype=np.int64)  # code space = low 5 qubits; 2 high qubits are "ancillas"
    mask = 0b11111
    M, leak = ss.encoded_block(ss.run_batch(qc, inputs), codes, 8, mask)
    Ms, ls_ = ac.aer_statevector_block(qc, inputs, codes, mask)
    assert np.abs(M - Ms).max() < 1e-12 and np.abs(leak - ls_).max() < 1e-12
    Mm, lm, info = ac.aer_mps_block(qc, inputs, codes, mask)
    assert np.abs(M - Mm).max() < 1e-9 and np.abs(leak - lm).max() < 1e-9 and info["max_bond_dim"] >= 1


def test_aer_statevector_qubit_limit():
    from su2plaq.evaluate import aer_check as ac

    with pytest.raises(ValueError):
        ac.aer_statevector_block(QuantumCircuit(25), np.array([0]), np.array([0]), 1)


def test_program_order_keeps_decomposed_macros_local():
    """Foreign gates are decomposed in place (not DAG-layer by layer), so 40 independent rccx on one input never hold more
    than a handful of amplitudes (a layer-hoisted order would open 40 Hadamards at once = 2^40)."""
    qc = QuantumCircuit(2 + 40)
    for k in range(40):
        qc.rccx(0, 1, 2 + k)
    b = ss.run_batch(qc, np.array([3], dtype=np.int64), cap=50)
    assert len(b.keys) == 1 and b.keys[0] == 3 | (((1 << 40) - 1) << 2)
    qm = QuantumCircuit(1, 1)
    qm.h(0)
    qm.measure(0, 0)
    with pytest.raises(ValueError):
        ss.run_batch(qm, np.array([0], dtype=np.int64))


def test_decomposition_cache_never_keyed_on_name_alone():
    """Two different custom gates with the same name (QuantumCircuit.to_gate takes the circuit's name) must not share a
    decomposition (audit 1.3: 2-qubit repro was wrong by 0.707)."""
    from qiskit.quantum_info import Operator

    a = QuantumCircuit(2, name="m")
    a.cx(0, 1)
    b = QuantumCircuit(2, name="m")
    b.cz(0, 1)
    q = QuantumCircuit(2)
    q.h(0)
    q.append(a.to_gate(), [0, 1])
    q.append(b.to_gate(), [0, 1])
    got = np.zeros((4, 4), complex)
    batch = ss.run_batch(q, np.arange(4, dtype=np.int64))
    np.add.at(got, (batch.keys, batch.cols), batch.amps)
    assert np.abs(got - Operator(q).data).max() < 1e-12
    assert ss.decomposition_cache_key(a.to_gate()) is None   # custom gate: not cacheable
    from qiskit.circuit.library import CXGate, RZGate

    assert ss.decomposition_cache_key(CXGate()) is not None and ss.decomposition_cache_key(RZGate(0.3)) is not None
    assert ss.decomposition_cache_key(RZGate(0.3)) != ss.decomposition_cache_key(RZGate(0.31))


def test_two_ub_macros_with_the_same_name_are_not_confused():
    from su2plaq.circuits.twelve import build_UB

    qc = QuantumCircuit(34)
    qc.append(build_UB(0.3).to_gate(), range(34))
    qc.append(build_UB(0.31).to_gate(), range(34))
    ref = build_UB(0.61)
    inputs = np.array([0, 0b111, 0b100100100100, 0b111100111000], dtype=np.int64)
    out = []
    for c in (qc, ref):
        b = ss.run_batch(c, inputs)
        d = np.zeros((1 << 12, 4), complex)
        sel = b.keys < (1 << 12)
        np.add.at(d, (b.keys[sel], b.cols[sel]), b.amps[sel])
        out.append(d)
    ov = np.vdot(out[1], out[0])
    assert np.abs(out[0] - ov / abs(ov) * out[1]).max() < 1e-9   # U_B(0.3) U_B(0.31) = U_B(0.61) on the inner codes
