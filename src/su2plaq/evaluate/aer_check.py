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


def _prep_all(qc: QuantumCircuit, sim, inputs, save):
    """Aer-native circuits for all inputs; the circuit is transpiled once (not once per input)."""
    base = transpile(qc, sim, optimization_level=0, qubits_initially_zero=False)
    for x in inputs:
        c = _prep(base, x)
        save(c)
        yield c


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
        circs = list(_prep_all(qc, sim, inputs[s0:s0 + chunk], lambda c: c.save_statevector(label="sv")))
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


def _site_tensors(mps, n: int):
    """A_q^s = Gamma_q^s diag(lambda_q) (shape chi_{q-1} x chi_q), list of (A^0, A^1)."""
    gammas, lambdas = mps
    out = []
    for q in range(n):
        g = [np.asarray(x, dtype=np.complex128) for x in gammas[q]]
        if q < len(lambdas):
            lam = np.asarray(lambdas[q], dtype=np.float64)
            g = [x * lam[None, :] for x in g]
        out.append(g)
    return out


def _ancilla_weight(mps, n: int, pinned: list[int]) -> float:
    """DIRECT weight of the output with some qubit of `pinned` set to 1: the disjoint terms 'qubit q is the FIRST pinned qubit
    equal to 1' (earlier pinned qubits 0, all other qubits summed) from prefix / suffix transfer matrices.  A sum of
    non-negative terms: no 1 - <Pi_0> subtraction (prompts/004 §2)."""
    A = _site_tensors(mps, n)
    pin = set(pinned)
    R = [None] * (n + 1)                       # R[q]: environment of sites q..n-1, everything summed
    R[n] = np.ones((1, 1), dtype=np.complex128)
    for q in range(n - 1, -1, -1):
        R[q] = sum(A[q][s].conj() @ R[q + 1] @ A[q][s].T for s in (0, 1))
    L = np.ones((1, 1), dtype=np.complex128)   # left environment, earlier pinned qubits fixed to 0
    w = 0.0
    for q in range(n):
        if q in pin:
            T1 = A[q][1].conj().T @ L @ A[q][1]
            w += float(np.sum(T1 * R[q + 1]).real)
            L = A[q][0].conj().T @ L @ A[q][0]
        else:
            L = A[q][0].conj().T @ L @ A[q][0] + A[q][1].conj().T @ L @ A[q][1]
    return w


def aer_mps_block(qc, inputs: np.ndarray, codes: np.ndarray, code_mask: int, bond_dim: int | None = None) -> tuple[np.ndarray, np.ndarray, dict]:
    """Per-input MPS run (truncation threshold 0, i.e. no deliberate truncation; `bond_dim` caps the bond dimension if
    given).  Accuracy is that of Aer's MPS (~1e-10 vs an exact simulator, see module docstring).

    Returns (M, leak, info).  leak[col] = w_anc[col] + w_inv[col], BOTH computed directly (prompts/004 §2), never as
    1 - sum|M|^2:
      w_anc = weight with some qubit outside `code_mask` set (ancillas, unused outer qubits; first-set decomposition),
      w_inv = sum over the invalid data patterns c (all 2^n_data patterns not in `codes`, every other qubit 0) of |<c|U|i>|^2.
    info = {"max_bond_dim", "seconds", "w_anc", "w_inv", "leak_derived"}; leak_derived = max(0, 1 - sum|M|^2) is the old
    subtraction value, kept as a diagnostic only.  Raises ValueError if n_data (bit length of code_mask) > 16."""
    n = qc.num_qubits
    n_data = int(code_mask).bit_length()
    if n_data > 16:
        raise ValueError(f"aer_mps_block enumerates the invalid data patterns: n_data={n_data} > 16 is not supported")
    inputs = np.asarray(inputs, dtype=np.int64)
    codes, ok = _valid_codes(codes, code_mask)
    invalid = np.setdiff1d(np.arange(2 ** n_data, dtype=np.int64), codes[ok])
    opts = dict(method="matrix_product_state", matrix_product_state_truncation_threshold=0.0, max_memory_mb=200_000_000)
    if bond_dim is not None:
        opts["matrix_product_state_max_bond_dimension"] = int(bond_dim)
    sim = AerSimulator(**opts)
    t0 = time.time()
    M = np.zeros((len(codes), len(inputs)), dtype=np.complex128)
    w_anc = np.zeros(len(inputs))
    w_inv = np.zeros(len(inputs))
    derived = np.zeros(len(inputs))
    max_bond = 1
    pinned = [q for q in range(n) if not (int(code_mask) >> q) & 1]
    circs = _prep_all(qc, sim, inputs, lambda c: c.save_matrix_product_state(label="mps"))
    for col, c in enumerate(circs):
        mps = sim.run(c).result().data()["mps"]
        max_bond = max([max_bond] + [int(np.asarray(l).shape[0]) for l in mps[1]])
        M[ok, col] = _contract(mps, codes[ok], n)
        w_anc[col] = _ancilla_weight(mps, n, pinned)
        w_inv[col] = float(np.sum(np.abs(_contract(mps, invalid, n)) ** 2))
        derived[col] = max(0.0, 1.0 - float(np.sum(np.abs(M[:, col]) ** 2)))
    return M, w_anc + w_inv, {"max_bond_dim": max_bond, "seconds": time.time() - t0, "w_anc": w_anc, "w_inv": w_inv,
                              "leak_derived": derived}
