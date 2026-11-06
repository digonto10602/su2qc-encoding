"""One-link rishon algebra: 4 fermionic modes (L1, L2, R1, R2) -> 16x16 complex128 matrices
(prompts/200 §2.1; docs/METHODS-rishon.md R1, R2; BCW hep-th/9704106 Eqs. 4.1-4.6).

Jordan-Wigner, little-endian: mode k is qubit k, c_k = (prod_{m<k} Z_m) sigma^-_k with sigma^- = |0><1|; the
occupation bit 1 means "mode occupied".  Link-local bilinears carry no string outside the link (R2).
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

N_MODES = 4
LINK_QUBITS = ("L1", "L2", "R1", "R2")
CODE_A = 3                      # 0b0011: L1 and L2 occupied (both rishons at the start of the link)
CODE_B = 12                     # 0b1100: R1 and R2 occupied
CODES_Q = (5, 6, 9, 10)         # one rishon at each end

_SIGMA = [
    np.array([[0, 1], [1, 0]], dtype=complex),
    np.array([[0, -1j], [1j, 0]], dtype=complex),
    np.array([[1, 0], [0, -1]], dtype=complex),
]
T_SPIN: list[np.ndarray] = [s / 2 for s in _SIGMA]

_Z = sp.csr_matrix(_SIGMA[2])
_I2 = sp.identity(2, dtype=complex, format="csr")
_SMINUS = sp.csr_matrix(np.array([[0, 1], [0, 0]], dtype=complex))     # |0><1|


def _kron_little_endian(ops: list) -> sp.csr_matrix:
    """ops[q] acts on qubit q; qubit 0 is the least significant tensor factor."""
    out = sp.identity(1, dtype=complex, format="csr")
    for o in ops:
        out = sp.kron(o, out, format="csr")
    return out


def jw_annihilation(k: int, n_modes: int) -> np.ndarray:
    """c_k = (prod_{m<k} Z_m) sigma^-_k on n_modes qubits (dense 2^n x 2^n, complex128)."""
    if not 0 <= k < n_modes:
        raise ValueError(f"mode {k} out of range for {n_modes} modes")
    ops = [_Z] * k + [_SMINUS] + [_I2] * (n_modes - k - 1)
    return _kron_little_endian(ops).toarray()


def global_bilinear(k: int, l: int, n_modes: int) -> np.ndarray:
    """c_k c_l^dagger with the global JW string on n_modes modes (string-freeness test)."""
    return jw_annihilation(k, n_modes) @ jw_annihilation(l, n_modes).conj().T


def embed_link_op(M16: np.ndarray, link: int, n_links: int) -> sp.csr_matrix:
    """Place a 16x16 link operator on link `link` of `n_links` links (link 0 least significant)."""
    M16 = np.asarray(M16, dtype=complex)
    if M16.shape != (16, 16):
        raise ValueError("embed_link_op expects a 16x16 matrix")
    if not 0 <= link < n_links:
        raise ValueError(f"link {link} out of range for {n_links} links")
    lo = sp.identity(16 ** link, dtype=complex, format="csr")
    hi = sp.identity(16 ** (n_links - 1 - link), dtype=complex, format="csr")
    return sp.kron(hi, sp.kron(sp.csr_matrix(M16), lo, format="csr"), format="csr").tocsr()


class RishonLink:
    """All single-link rishon operators as 16x16 complex128 matrices (modes 0..3 = L1 L2 R1 R2)."""

    def __init__(self):
        self.c = [jw_annihilation(k, N_MODES) for k in range(N_MODES)]
        self.cdag = [m.conj().T.copy() for m in self.c]
        cL, cR = self.c[0:2], self.c[2:4]
        cLd, cRd = self.cdag[0:2], self.cdag[2:4]
        self._U = [[cL[i] @ cRd[j] for j in range(2)] for i in range(2)]
        self.L = [sum(T_SPIN[a][i, j] * (cLd[i] @ cL[j]) for i in range(2) for j in range(2)) for a in range(3)]
        self.R = [sum(T_SPIN[a][i, j] * (cRd[i] @ cR[j]) for i in range(2) for j in range(2)) for a in range(3)]
        n_L = sum(cLd[i] @ cL[i] for i in range(2))
        n_R = sum(cRd[i] @ cR[i] for i in range(2))
        self.N = n_L + n_R
        self.T_bcw = n_R - n_L
        self.casimir_L = sum(m @ m for m in self.L)
        self.casimir_R = sum(m @ m for m in self.R)
        self.det_U = self._U[0][0] @ self._U[1][1] - self._U[0][1] @ self._U[1][0]
        nd = np.rint(np.real(np.diag(self.N))).astype(np.int64)
        self.sector = np.flatnonzero(nd == 2).astype(np.int64)

    def U(self, i: int, j: int) -> np.ndarray:
        """U_ij = c_{L,i} c^dagger_{R,j} (BCW Eq. 4.3)."""
        return self._U[i][j]

    def Udag(self, i: int, j: int) -> np.ndarray:
        return self._U[i][j].conj().T.copy()

    def link_type(self, code: int) -> str | None:
        code = int(code)
        if code == CODE_A:
            return "A"
        if code == CODE_B:
            return "B"
        if code in CODES_Q:
            return "Q"
        return None

    def end_generator(self, a: int, end: str) -> np.ndarray:
        """4x4 matrix of L_a ('L') or R_a ('R') on the end's two qubits (bit 0 = colour 1).

        The strings of the two JW factors cancel, so the matrix is sum_ij (T_a)_ij c^dag_i c_j built with the
        2-mode JW (identical for both ends)."""
        if end not in ("L", "R"):
            raise ValueError("end must be 'L' or 'R'")
        c2 = [jw_annihilation(k, 2) for k in range(2)]
        return sum(T_SPIN[a][i, j] * (c2[i].conj().T @ c2[j]) for i in range(2) for j in range(2))
