"""Fuzzy-link operator algebra (M9; METHODS-fuzzy F1-F2; arXiv:2308.05253v4 Eqs. 22, 24-25, 29-30; Tex Eq. (pauli)).

One link carries a 4x4 complex matrix Psi; the 16 basis states are the matrix units |row,col>, row-major, index
``8 q1 + 4 q2 + 2 q3 + q4`` with row = 2 q1 + q2, col = 2 q3 + q4.  Left multiplication Psi -> M Psi is ``kron(M, 1)``,
right multiplication Psi -> Psi M is ``kron(1, M^T)``.  Pauli forms use 4 qubits, little-endian: q_k lives on qubit 4-k,
so the leftmost character of a Qiskit Pauli label is q_1.
"""
from __future__ import annotations

import numpy as np
from qiskit.quantum_info import SparsePauliOp

_I2 = np.eye(2, dtype=complex)
_Z2 = np.zeros((2, 2), dtype=complex)
SIGMA = [np.array([[0, 1], [1, 0]], complex), np.array([[0, -1j], [1j, 0]]), np.array([[1, 0], [0, -1]], complex)]
_I4 = np.eye(4, dtype=complex)

GAMMA0 = 0.5 * np.block([[_Z2, _I2], [_I2, _Z2]]).astype(complex)
GAMMA = [0.5 * np.block([[_Z2, 1j * s], [-1j * s, _Z2]]) for s in SIGMA]
GAMMA5 = np.block([[_I2, _Z2], [_Z2, -_I2]]).astype(complex)
T_R = [0.5 * np.block([[s, _Z2], [_Z2, _Z2]]) for s in SIGMA]  # acts in the upper block
T_L = [0.5 * np.block([[_Z2, _Z2], [_Z2, s]]) for s in SIGMA]  # acts in the lower block


def U_link(a: int, b: int) -> np.ndarray:
    """4x4 matrix U_ab = delta_ab Gamma_0 - i sigma^A_ab Gamma_A (P Eq. 29)."""
    return (1.0 if a == b else 0.0) * GAMMA0 - 1j * sum(SIGMA[A][a, b] * GAMMA[A] for A in range(3))


def lmul(M: np.ndarray) -> np.ndarray:
    """Psi -> M Psi on the 16-dim link space."""
    return np.kron(np.asarray(M, complex), _I4)


def rmul(M: np.ndarray) -> np.ndarray:
    """Psi -> Psi M on the 16-dim link space."""
    return np.kron(_I4, np.asarray(M, complex).T)


def _ad(M: np.ndarray) -> np.ndarray:
    return lmul(M) - rmul(M)


def calT_L(A: int) -> np.ndarray:
    """Left generator Psi -> [T_L^A, Psi] (16x16)."""
    return _ad(T_L[A])


def calT_R(A: int) -> np.ndarray:
    """Right generator Psi -> [T_R^A, Psi] (16x16)."""
    return _ad(T_R[A])


def U_op(a: int, b: int) -> np.ndarray:
    """Link operator calU_ab: Psi -> U_ab Psi (16x16)."""
    return lmul(U_link(a, b))


def casimirs() -> tuple[np.ndarray, np.ndarray]:
    """(C_L, C_R) = (sum_A calT_L^2, sum_A calT_R^2)."""
    CL = sum(calT_L(A) @ calT_L(A) for A in range(3))
    CR = sum(calT_R(A) @ calT_R(A) for A in range(3))
    return CL, CR


def K1() -> np.ndarray:
    """Electric operator calK_1 = C_L + C_R (16x16)."""
    CL, CR = casimirs()
    return CL + CR


def K2() -> np.ndarray:
    """calK_2 = -sum_ab (U_ab Psi U_ab^dag + U_ab^dag Psi U_ab) (16x16)."""
    out = np.zeros((16, 16), complex)
    for a in range(2):
        for b in range(2):
            U = U_link(a, b)
            out += lmul(U) @ rmul(U.conj().T) + lmul(U.conj().T) @ rmul(U)
    return -out


def flavour() -> np.ndarray:
    """F: Psi -> Psi Gamma_5 (= Z on q3)."""
    return rmul(GAMMA5)


def centre() -> np.ndarray:
    """Centre element Z_1 Z_3 (anticommutes with calU_ab, commutes with calK_{1,2})."""
    Z = SIGMA[2]
    return np.kron(np.kron(np.kron(Z, _I2), Z), _I2)


def irreps() -> list[tuple[float, float, int]]:
    """Decomposition into SU(2)_L x SU(2)_R irreps: sorted list of (j_L, j_R, multiplicity)."""
    CL, CR = casimirs()
    # CL, CR commute and are Hermitian: diagonalise a generic combination, then read both Casimirs
    _, V = np.linalg.eigh(CL + np.sqrt(2.0) * CR)
    cl = np.einsum("ij,jk,ki->i", V.conj().T, CL, V).real
    cr = np.einsum("ij,jk,ki->i", V.conj().T, CR, V).real

    def j_of(c):
        return round(float((-1 + np.sqrt(1 + 4 * c)) / 2) * 2) / 2.0

    counts: dict[tuple[float, float], int] = {}
    for a, b in zip(cl, cr):
        key = (j_of(a), j_of(b))
        counts[key] = counts.get(key, 0) + 1
    out = []
    for (jl, jr), n in sorted(counts.items()):
        dim = int(round((2 * jl + 1) * (2 * jr + 1)))
        assert n % dim == 0
        out.append((jl, jr, n // dim))
    return out


# ---- Pauli forms (little-endian: q_k on qubit 4-k; label characters read q1 q2 q3 q4) ----

def pauli_K1() -> SparsePauliOp:
    """K1 = 3/2 - (1/4)(X2X4 - Y2Y4 + Z2Z4)(1 + Z1Z3)."""
    terms = [("IIII", 1.5)]
    for lab, c in (("IXIX", 1.0), ("IYIY", -1.0), ("IZIZ", 1.0), ("ZXZX", 1.0), ("ZYZY", -1.0), ("ZZZZ", 1.0)):
        terms.append((lab, -0.25 * c))
    return SparsePauliOp.from_list(terms)


def pauli_K2() -> SparsePauliOp:
    """K2 = -X1X3 + Y1X2Y3X4 - Y1Y2Y3Y4 + Y1Z2Y3Z4."""
    return SparsePauliOp.from_list([("XIXI", -1.0), ("YXYX", 1.0), ("YYYY", -1.0), ("YZYZ", 1.0)])


def pauli_U(a: int, b: int) -> SparsePauliOp:
    """U_ab = (1/2)[delta_ab X1 + i sigma^A_ab Y1 sigma^A_2] on (q1,q2); q3,q4 untouched."""
    terms = []
    if a == b:
        terms.append(("XIII", 0.5))
    for A, lab in enumerate("XYZ"):
        c = SIGMA[A][a, b]
        if abs(c) > 0:
            terms.append(("Y" + lab + "II", 0.5j * c))
    return SparsePauliOp.from_list(terms, dtype=complex).simplify()
