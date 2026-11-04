"""Route-A operators and targets on the physical basis (prompts/002 §2.4, docs/METHODS.md §2, §4).

H = g^2/2 H_E + 1/g^2 H_B,  H_E = sum_l j_l (j_l+1),  H_B = -(Tr U_P + h.c.),  U_P = U_b U_r U_t^dag U_l^dag.
The inner operator W = Tr U_P is a 625x625 matrix on the four inner links (link 0 = least significant
tensor factor); H_B^phys = -(Psi^dag (W (x) 1) Psi + h.c.) is built from sparse blocks, never a dense 5^12 operator.
"""
from __future__ import annotations

import functools
import itertools

import numpy as np
import scipy.sparse as sp
from scipy.linalg import expm

from su2plaq.su2.algebra import LinkSpace, paulo_U

_INNER = 625


@functools.lru_cache(maxsize=None)
def _W_cached(convention: str) -> np.ndarray:
    return _build_W(_U_of(convention))


def _U_of(convention: str):
    if convention == "cg":
        return LinkSpace(0.5).U()
    if convention == "paulo":
        return paulo_U()
    raise ValueError(f"unknown convention {convention!r}")


def _build_W(U) -> np.ndarray:
    """W = sum_{abcd} U_b[a,b] U_r[b,c] (U_t^dag)[c,d] (U_l^dag)[d,a]; (U^dag)[x,y] = (U[y][x])^dagger (operator adjoint).
    Operators on different links commute, so each term is a Kronecker product (link 0 least significant)."""
    d = U[0][0].shape[0]
    W = np.zeros((d ** 4, d ** 4), dtype=np.complex128)
    for a, b, c, e in itertools.product(range(2), repeat=4):
        Ub, Ur = U[a][b], U[b][c]
        Ut = U[e][c].conj().T  # (U_t^dag)_{c e}
        Ul = U[a][e].conj().T  # (U_l^dag)_{e a}
        W += np.kron(Ul, np.kron(Ut, np.kron(Ur, Ub)))
    return W


def plaquette_W(link: LinkSpace | None = None, convention: str = "cg") -> np.ndarray:
    """625x625 Tr(U_b U_r U_t^dag U_l^dag), index = sum_l s_l 5^l, link 0 least significant."""
    if link is not None:
        return _build_W(link.U())
    return _W_cached(convention).copy()



def h_electric_inner(basis) -> np.ndarray:
    """Diagonal of sum over the 4 inner links of j(j+1), length dim."""
    return np.array([sum(j * (j + 1) for j in lab[0][:4]) for lab in basis.labels], dtype=np.float64)


def h_electric_outer(basis) -> np.ndarray:
    """Diagonal of sum over the 8 outer links of j(j+1), length dim."""
    return np.array([sum(j * (j + 1) for j in lab[0][4:]) for lab in basis.labels], dtype=np.float64)


def _psi_sparse(basis):
    """Psi as sparse (625 * n_outer_patterns, dim); row = inner + 625 * (index of outer key)."""
    allk = np.concatenate(basis.keys)
    outer = allk // _INNER
    uo, oinv = np.unique(outer, return_inverse=True)
    rows = (allk % _INNER) + _INNER * oinv
    cols = np.concatenate([np.full(len(k), i) for i, k in enumerate(basis.keys)])
    vals = np.concatenate(basis.amps).astype(np.complex128)
    return sp.csr_matrix((vals, (rows, cols)), shape=(_INNER * len(uo), basis.dim)), len(uo)


def h_magnetic_phys(basis, W: np.ndarray | None = None) -> tuple[np.ndarray, float]:
    """(-(Psi^dag (W (x) 1) Psi + h.c.), physical leak max_k | ||W psi_k||^2 - sum_k' |A_k'k|^2 |)."""
    if W is None:
        W = _W_cached(basis.convention)
    Psi, n_o = _psi_sparse(basis)
    Ws = sp.csr_matrix(W)
    WPsi = sp.kron(sp.identity(n_o, format="csr"), Ws, format="csr") @ Psi
    A = (Psi.conj().T @ WPsi).toarray()
    norms = np.asarray(WPsi.conj().multiply(WPsi).sum(axis=0)).real.ravel()
    leak = float(np.max(np.abs(norms - np.sum(np.abs(A) ** 2, axis=0))))
    return -(A + A.conj().T), leak


def hamiltonian_phys(basis, g2: float, include_outer_electric: bool = False) -> np.ndarray:
    HE = h_electric_inner(basis)
    if include_outer_electric:
        HE = HE + h_electric_outer(basis)
    HB, _ = h_magnetic_phys(basis)
    return np.diag(0.5 * g2 * HE).astype(np.complex128) + HB / g2


def _UE(basis, alpha, include_outer_electric):
    HE = h_electric_inner(basis)
    if include_outer_electric:
        HE = HE + h_electric_outer(basis)
    return np.diag(np.exp(-1j * alpha * HE))


def target(basis, kind: str, alpha: float | None = None, beta: float | None = None, order: int = 1,
           include_outer_electric: bool = False) -> np.ndarray:
    """kind 'UE': diag(exp(-i alpha HE_inner)); 'UB': expm(-i beta HB_phys);
    'step': order 1 -> UB @ UE, order 2 -> UE(alpha/2) @ UB @ UE(alpha/2); dim x dim complex128 in basis order.
    include_outer_electric adds H_E^outer to every electric factor (it commutes with UB)."""
    if kind == "UE":
        if alpha is None:
            raise ValueError("kind 'UE' needs alpha")
        return _UE(basis, alpha, include_outer_electric).astype(np.complex128)
    if kind in ("UB", "step") and beta is None:
        raise ValueError(f"kind {kind!r} needs beta")
    if kind == "UB":
        HB, _ = h_magnetic_phys(basis)
        return expm(-1j * beta * HB).astype(np.complex128)
    if kind == "step":
        if alpha is None:
            raise ValueError("kind 'step' needs alpha")
        HB, _ = h_magnetic_phys(basis)
        UB = expm(-1j * beta * HB)
        if order == 1:
            return (UB @ _UE(basis, alpha, include_outer_electric)).astype(np.complex128)
        if order == 2:
            UEh = _UE(basis, alpha / 2, include_outer_electric)
            return (UEh @ UB @ UEh).astype(np.complex128)
        raise ValueError(f"order must be 1 or 2, got {order}")
    raise ValueError(f"unknown kind {kind!r}")
