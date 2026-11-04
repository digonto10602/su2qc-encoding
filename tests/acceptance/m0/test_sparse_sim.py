"""M0-E1, E2 — batched sparse simulator vs qiskit-aer statevector and dense Operator (prompts/002 §2.7, METHODS §6).
Tolerance 1e-12: two float64 simulators on <= 70-gate circuits."""
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from tests.acceptance._api import api


def _random_circuit(n: int, n_gates: int, rng: np.random.Generator) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    for _ in range(n_gates):
        g = rng.choice(["h", "cx", "rz", "t", "s", "x", "cz", "ccx", "p", "swap", "cp", "sdg", "tdg", "z"])
        qs = rng.choice(n, size=3, replace=False)
        if g == "h":
            qc.h(int(qs[0]))
        elif g == "cx":
            qc.cx(int(qs[0]), int(qs[1]))
        elif g == "rz":
            qc.rz(float(rng.uniform(-3, 3)), int(qs[0]))
        elif g == "p":
            qc.p(float(rng.uniform(-3, 3)), int(qs[0]))
        elif g == "cp":
            qc.cp(float(rng.uniform(-3, 3)), int(qs[0]), int(qs[1]))
        elif g == "cz":
            qc.cz(int(qs[0]), int(qs[1]))
        elif g == "swap":
            qc.swap(int(qs[0]), int(qs[1]))
        elif g == "ccx":
            qc.ccx(int(qs[0]), int(qs[1]), int(qs[2]))
        else:
            getattr(qc, g)(int(qs[0]))
    return qc


def _dense_from_batch(batch, n_inputs: int) -> np.ndarray:
    out = np.zeros((2 ** batch.n_qubits, n_inputs), complex)
    np.add.at(out, (batch.keys, batch.cols), batch.amps)
    return out


def test_M0_E1_vs_aer(rng):
    """run_batch on a 10-qubit random circuit, 50 seeded basis inputs, vs qiskit-aer statevector: 1e-12."""
    from qiskit_aer import AerSimulator

    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    n = 10
    qc = _random_circuit(n, 60, np.random.default_rng(20261104))
    inputs = np.array(sorted(set(rng.integers(0, 2 ** n, size=50).tolist())), dtype=np.int64)
    batch = run_batch(qc, inputs)
    assert batch.n_qubits == n and batch.keys.dtype == np.int64
    dense = _dense_from_batch(batch, len(inputs))
    sim = AerSimulator(method="statevector")
    for col, x in enumerate(inputs):
        prep = QuantumCircuit(n)
        for b in range(n):
            if (int(x) >> b) & 1:
                prep.x(b)
        prep.compose(qc, inplace=True)
        prep.save_statevector()
        sv = np.asarray(sim.run(prep).result().get_statevector(prep))
        assert np.abs(sv - dense[:, col]).max() <= 1e-12
    # norm preserved
    assert np.abs(np.linalg.norm(dense, axis=0) - 1).max() <= 1e-12


def test_M0_E2_vs_dense_operator(rng):
    """run_batch on a 6-qubit random circuit vs qiskit.quantum_info.Operator columns (1e-12); encoded_block leak and
    code-mask semantics on a hand-made case."""
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    encoded_block = api("su2plaq.evaluate.sparse_sim:encoded_block")
    n = 6
    qc = _random_circuit(n, 40, np.random.default_rng(7))
    inputs = np.arange(2 ** n, dtype=np.int64)
    batch = run_batch(qc, inputs)
    dense = _dense_from_batch(batch, len(inputs))
    U = Operator(qc).data
    assert np.abs(dense - U).max() <= 1e-12
    # encoded_block: 2 data qubits (bits 0,1) + 1 ancilla (bit 2); codes = {0b00, 0b11}; X on the ancilla => leak 1
    qc2 = QuantumCircuit(3)
    qc2.x(2)
    b2 = run_batch(qc2, np.array([0b00, 0b11], dtype=np.int64))
    M, leak = encoded_block(b2, np.array([0b00, 0b11], dtype=np.int64), 2, code_mask=0b011)
    assert M.shape == (2, 2) and np.abs(M).max() <= 1e-14 and np.allclose(leak, [1.0, 1.0])
    # CX(0->1): |00> -> |00> (a code, M[0,0] = 1); |11> -> |01> (bit 1 flipped; not a code) => leak[1] = 1
    qc3 = QuantumCircuit(3)
    qc3.cx(0, 1)
    b3 = run_batch(qc3, np.array([0b00, 0b11], dtype=np.int64))
    M3, leak3 = encoded_block(b3, np.array([0b00, 0b11], dtype=np.int64), 2, code_mask=0b011)
    assert abs(M3[0, 0] - 1) <= 1e-14 and abs(leak3[0]) <= 1e-14 and abs(leak3[1] - 1.0) <= 1e-14
    # the amplitude cap raises a clear exception
    SimCapExceeded = api("su2plaq.evaluate.sparse_sim:SimCapExceeded")
    qh = QuantumCircuit(8)
    for q in range(8):
        qh.h(q)
    with pytest.raises(SimCapExceeded):
        run_batch(qh, np.arange(4, dtype=np.int64), cap=100)
