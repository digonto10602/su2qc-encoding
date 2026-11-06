"""Fuzzy plaquette operator on the 8 row qubits (M9; METHODS-fuzzy F2, F5; P Eq. 35, Tex Result 3).

square = sum_{abcd} U_ab(b) U_bc(r) U_dc(t)^dag U_ad(l)^dag, acting on the row spaces only.  Row-register index
``sum_l (2 q1^l + q2^l) 4^l`` with l = b, r, t, l = 0..3 (link b least significant); row-qubit 2l+1 carries q1^l and
2l carries q2^l.
"""
from __future__ import annotations

import numpy as np
from qiskit.quantum_info import SparsePauliOp
from scipy.linalg import expm

from .link import U_link

_COLUMN_BITS = (1, 3, 5, 7)  # q1^l of links b, r, t, l inside the 8-qubit row register


def _k4(Ab, Ar, At, Al):
    return np.kron(np.kron(np.kron(Al, At), Ar), Ab)


def plaquette_row() -> np.ndarray:
    """256x256 matrix of square = sum U_ab(b) U_bc(r) U_dc(t)^dag U_ad(l)^dag on the row qubits."""
    U = [[U_link(a, b) for b in range(2)] for a in range(2)]
    Ud = [[U[a][b].conj().T for b in range(2)] for a in range(2)]
    W = np.zeros((256, 256), complex)
    for a in range(2):
        for b in range(2):
            for c in range(2):
                for d in range(2):
                    W += _k4(U[a][b], U[b][c], Ud[d][c], Ud[a][d])
    return W


def plaquette_pauli() -> SparsePauliOp:
    """Pauli decomposition of ``plaquette_row`` on 8 qubits (qubit 0 least significant), simplified."""
    P = SparsePauliOp.from_operator(plaquette_row())
    return P.simplify(atol=1e-12)


def block_structure() -> dict:
    """Parity-block decomposition (F5).

    With f = q1^b and parities p_k = q1^b xor q1^{l_k} (l_k = r, t, l; p = p_r + 2 p_t + 4 p_l) the operator maps the
    f = 0 states of parity pattern p to the f = 1 states of the same pattern.  Returns {p: dict(rows, cols, D, sing_vals)}
    with ``D = W[rows, cols]`` (16x16; rows = f = 1 indices, cols = f = 0 indices, both ordered by the four q2 bits
    (q2^b, q2^r, q2^t, q2^l) as bits 0..3) and its singular values (descending, length 16).
    """
    W = plaquette_row()
    idx = np.arange(256)
    z = [(idx >> (2 * l + 1)) & 1 for l in range(4)]
    spin = sum(((idx >> (2 * l)) & 1) << l for l in range(4))
    out = {}
    for p in range(8):
        pb = [(p >> k) & 1 for k in range(3)]
        f0 = (z[0] == 0) & (z[1] == pb[0]) & (z[2] == pb[1]) & (z[3] == pb[2])
        f1 = (z[0] == 1) & (z[1] == 1 - pb[0]) & (z[2] == 1 - pb[1]) & (z[3] == 1 - pb[2])
        cols = idx[f0][np.argsort(spin[f0])]
        rows = idx[f1][np.argsort(spin[f1])]
        D = W[np.ix_(rows, cols)]
        sv = np.linalg.svd(D, compute_uv=False)
        out[p] = {"rows": rows, "cols": cols, "D": D, "sing_vals": sv}
    return out


def _commute(p: str, q: str) -> bool:
    return sum(1 for a, b in zip(p, q) if a != "I" and b != "I" and a != b) % 2 == 0


def pauli_clusters() -> list[SparsePauliOp]:
    """Greedy partition of the Pauli strings of the plaquette into mutually commuting clusters (as 8-qubit operators)."""
    P = plaquette_pauli()
    labels = [l for l in P.paulis.to_labels()]
    coeffs = list(P.coeffs)
    clusters: list[list[int]] = []
    for i, lab in enumerate(labels):
        for cl in clusters:
            if all(_commute(lab, labels[j]) for j in cl):
                cl.append(i)
                break
        else:
            clusters.append([i])
    return [SparsePauliOp.from_list([(labels[i], coeffs[i]) for i in cl]) for cl in clusters]


def cluster_product(beta: float, order=None) -> np.ndarray:
    """Greedy commuting-cluster product prod_c exp(2 i beta H_c) (applied in ``order``, default greedy order).

    NOT equal to exp(2 i beta square) (the clusters do not commute with each other); a reported splitting-error row only.
    """
    Hs = [c.to_matrix() for c in pauli_clusters()]
    seq = range(len(Hs)) if order is None else order
    U = np.eye(256, dtype=complex)
    for i in seq:
        U = expm(2j * beta * Hs[i]) @ U
    return U
