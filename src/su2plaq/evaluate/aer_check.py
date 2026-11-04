"""Qiskit-Aer cross-check engines (prompts/002 §2.7, docs/METHODS.md §6).

* `aer_statevector_block`: exact statevector simulation per input, <= 24 qubits (independent check of the sparse
  simulator).
* `aer_mps_block`: matrix-product-state simulation per input, truncation threshold 0 (Aer's own SVD accuracy limits the
  agreement with an exact simulator to ~1e-10, measured 2e-11..6e-11 on a random 8-qubit circuit), Aer's
  statevector-sized memory estimate overridden through `max_memory_mb`; amplitudes of the requested codes are obtained by
  contracting the saved MPS (`save_matrix_product_state`).  `save_amplitudes` is never used with the MPS method
  (Aer 0.17.2 returns zeros).
Both return M[len(codes), n_inputs] with the same code-space semantics as `sparse_sim.encoded_block`.
"""
from __future__ import annotations

import time

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

_MAX_SV_QUBITS = 24


def _prep(qc: QuantumCircuit, x: int) -> QuantumCircuit:
    circ = QuantumCircuit(qc.num_qubits)
    for b in range(qc.num_qubits):
        if (int(x) >> b) & 1:
            circ.x(b)
    circ.compose(qc, qubits=range(qc.num_qubits), inplace=True)
    return circ


def _valid_codes(codes, code_mask):
    codes = np.asarray(codes, dtype=np.int64)
    return codes, (codes & ~np.int64(code_mask)) == 0


def aer_statevector_block(qc, inputs: np.ndarray, codes: np.ndarray, code_mask: int) -> tuple[np.ndarray, np.ndarray]:
    """Same as `sparse_sim.encoded_block` but through qiskit-aer statevector; qc.num_qubits <= 24."""
    n = qc.num_qubits
    if n > _MAX_SV_QUBITS:
        raise ValueError(f"aer statevector check needs <= {_MAX_SV_QUBITS} qubits, got {n}")
    inputs = np.asarray(inputs, dtype=np.int64)
    codes, ok = _valid_codes(codes, code_mask)
    sim = AerSimulator(method="statevector")
    M = np.zeros((len(codes), len(inputs)), dtype=np.complex128)
    leak = np.zeros(len(inputs))
    chunk = max(1, 2 ** 22 // 2 ** n)
    for s0 in range(0, len(inputs), chunk):
        circs = []
        for x in inputs[s0:s0 + chunk]:
            c = _prep(qc, x)
            c.save_statevector(label="sv")
            circs.append(transpile(c, sim, optimization_level=0))
        res = sim.run(circs).result()
        for i in range(len(circs)):
            sv = np.asarray(res.data(i)["sv"], dtype=np.complex128)
            col = s0 + i
            M[ok, col] = sv[codes[ok]]
            mask = np.ones(len(sv), dtype=bool)
            mask[codes[ok]] = False
            leak[col] = float(np.sum(np.abs(sv[mask]) ** 2))
    return M, leak


def _contract(mps, ints: np.ndarray, n: int) -> np.ndarray:
    """Amplitudes <int|MPS> for all `ints` at once; Aer MPS format (list of (G0, G1) per qubit, list of lambdas)."""
    gammas, lambdas = mps
    vec = None
    for q in range(n):
        g0, g1 = (np.asarray(g, dtype=np.complex128) for g in gammas[q])
        bits = ((ints >> q) & 1).astype(bool)
        if vec is None:
            vec = np.where(bits[:, None], g1.reshape(-1, g1.shape[-1])[0][None, :], g0.reshape(-1, g0.shape[-1])[0][None, :])
        else:
            vec = np.where(bits[:, None], vec @ g1, vec @ g0)
        if q < len(lambdas):
            vec = vec * np.asarray(lambdas[q], dtype=np.float64)[None, :]
    return vec[:, 0]


def aer_mps_block(qc, inputs: np.ndarray, codes: np.ndarray, code_mask: int, bond_dim: int | None = None) -> tuple[np.ndarray, np.ndarray, dict]:
    """Per-input MPS run (truncation threshold 0, i.e. no deliberate truncation; `bond_dim` caps the bond dimension if
    given).  Accuracy is that of Aer's MPS (~1e-10 vs an exact simulator, see module docstring).

    Returns (M, leak, {"max_bond_dim", "seconds"}).  The MPS amplitudes are read only on the requested codes, so
    leak is the derived quantity 1 - sum_codes |M|^2 (the saved MPS is normalised); it is NOT the sum of out-of-code
    weights computed directly."""
    n = qc.num_qubits
    inputs = np.asarray(inputs, dtype=np.int64)
    codes, ok = _valid_codes(codes, code_mask)
    opts = dict(method="matrix_product_state", matrix_product_state_truncation_threshold=0.0, max_memory_mb=200_000_000)
    if bond_dim is not None:
        opts["matrix_product_state_max_bond_dimension"] = int(bond_dim)
    sim = AerSimulator(**opts)
    t0 = time.time()
    M = np.zeros((len(codes), len(inputs)), dtype=np.complex128)
    leak = np.zeros(len(inputs))
    max_bond = 1
    for col, x in enumerate(inputs):
        c = _prep(qc, x)
        c.save_matrix_product_state(label="mps")
        mps = sim.run(transpile(c, sim, optimization_level=0)).result().data()["mps"]
        max_bond = max([max_bond] + [int(np.asarray(l).shape[0]) for l in mps[1]])
        M[ok, col] = _contract(mps, codes[ok], n)
        leak[col] = max(0.0, 1.0 - float(np.sum(np.abs(M[:, col]) ** 2)))
    return M, leak, {"max_bond_dim": max_bond, "seconds": time.time() - t0}
