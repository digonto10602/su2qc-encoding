"""Exact reference unitaries for the fuzzy Trotter step (M9; METHODS-fuzzy F3).

U_E(alpha) = exp(-i alpha/2 K1), U_K(kappa2) = exp(-i kappa2 K2), U_B(beta) = exp(+2 i beta square),
kappa2 = r alpha / 2.  Statevectors on the 16 inner qubits: link l (b, r, t, l = 0..3) occupies qubits 4l..4l+3 with
q1 on qubit 4l+3, so the amplitude index is sum_l (8 q1 + 4 q2 + 2 q3 + q4)_l 16^l.
"""
from __future__ import annotations

import numpy as np

from .link import K1, K2
from .plaquette import plaquette_row


def _herm_exp(H: np.ndarray, c: complex) -> np.ndarray:
    """exp(c H) for Hermitian H via eigh."""
    w, V = np.linalg.eigh(H)
    return (V * np.exp(c * w)) @ V.conj().T


def UE_link(alpha: float) -> np.ndarray:
    return _herm_exp(K1(), -0.5j * alpha)


def UK_link(kappa2: float) -> np.ndarray:
    return _herm_exp(K2(), -1j * kappa2)


def UEK_link(alpha: float, kappa2: float) -> np.ndarray:
    """exp(-i(alpha/2 K1 + kappa2 K2)); [K1, K2] = 0 so this equals UK_link @ UE_link."""
    return _herm_exp(0.5 * alpha * K1() + kappa2 * K2(), -1j)


def UB_row(beta: float) -> np.ndarray:
    """exp(+2 i beta square) on the 8 row qubits (256x256)."""
    return _herm_exp(plaquette_row(), 2j * beta)


def kappa2_of(alpha: float, r: float) -> float:
    """kappa2 = r kappa1 with kappa1 = alpha/2."""
    return float(r) * float(alpha) / 2.0


def _apply_kinetic(psi: np.ndarray, M16: np.ndarray) -> np.ndarray:
    t = psi.reshape(16, 16, 16, 16)  # axes: link l, t, r, b (b least significant)
    for ax in range(4):
        t = np.moveaxis(np.tensordot(M16, t, axes=([1], [ax])), 0, ax)
    return t.reshape(-1)


def _apply_ub(psi: np.ndarray, UB: np.ndarray) -> np.ndarray:
    t = psi.reshape(4, 4, 4, 4, 4, 4, 4, 4)  # (l_row, l_col, t_row, t_col, r_row, r_col, b_row, b_col)
    rows = (0, 2, 4, 6)
    cols = (1, 3, 5, 7)
    t = t.transpose(rows + cols).reshape(256, 256)
    t = (UB @ t).reshape(4, 4, 4, 4, 4, 4, 4, 4)
    inv = np.argsort(rows + cols)
    return t.transpose(tuple(inv)).reshape(-1)


def apply_step(psi: np.ndarray, alpha: float, beta: float, kappa2: float, order: int = 1) -> np.ndarray:
    """One Trotter step on a 2^16 statevector of the inner links.

    order 1: U_B U_K(kappa2) U_E(alpha); order 2: U_EK(alpha/2, kappa2/2) U_B U_EK(alpha/2, kappa2/2).
    """
    psi = np.asarray(psi, complex).reshape(-1)
    if psi.size != 1 << 16:
        raise ValueError("psi must have 2**16 amplitudes")
    UB = UB_row(beta)
    if order == 1:
        return _apply_ub(_apply_kinetic(psi, UEK_link(alpha, kappa2)), UB)
    if order == 2:
        half = UEK_link(alpha / 2, kappa2 / 2)
        return _apply_kinetic(_apply_ub(_apply_kinetic(psi, half), UB), half)
    raise ValueError("order must be 1 or 2")
