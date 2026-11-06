"""Shared observables, fuzzy theory vs Kogut-Susskind (M9-O1; METHODS-fuzzy F7).

Fuzzy Hamiltonian on the four inner links (the eight outer links in the Psi = 1/2 copy contribute only a constant
phase, see ``outer_vacuum_energy``):

    H(g2, r) = (g2/4) sum_{l in inner} (K1(l) + r K2(l)) - (2/g2) square,           (F3)

acting on 16**4 = 65536 amplitudes (link l at 16**l, link b least significant).  The strong-coupling vacuum is
Omega = tensor_l (1/2) 1  (<K1> = 0, <K2> = -4 per link, <square> = 0, |square Omega| = 1).

Closed sector = cyclic subspace of Omega under H.  It is computed as the smallest subspace containing Omega that is
invariant under the three H-building blocks (sum_l K1, sum_l K2 [only if r != 0], square); this equals the Krylov
space of H for generic (g2, r) (checked: dimension 12 for r != 0, 9 for r = 0) but does not depend on g2, so H(g2, r)
is assembled from fixed projected blocks.  Basis vector 0 is Omega.

KS reference: the 2x2 closed sector [[0, -2/g2], [-2/g2, 3 g2/2]] in {|0000>, |16>} (METHODS section 4); the
plaquette observable there is Re Tr W = (W + W^dag)/2 with H_B = -2 Re Tr W, i.e. sigma_x in that basis (matching
the fuzzy square, for which <1|square|0> = 1).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .link import K1, K2
from .plaquette import plaquette_row
from .targets import apply_step, kappa2_of

_TOL_KRYLOV = 1e-9  # a new basis vector is kept if its norm after full re-orthogonalisation exceeds this


# ---------------------------------------------------------------------------------------------------------------- operators
def _kin(M16: np.ndarray, v: np.ndarray) -> np.ndarray:
    """sum over the four inner links of M16 acting on link l; v has shape (16,)*4."""
    out = np.zeros_like(v)
    for ax in range(4):
        out += np.moveaxis(np.tensordot(M16, v, axes=([1], [ax])), 0, ax)
    return out


def _square(W: np.ndarray, v: np.ndarray) -> np.ndarray:
    """square (256x256 on row indices) acting on a (16,)*4 tensor; columns are spectators."""
    t = v.reshape(4, 4, 4, 4, 4, 4, 4, 4)  # l_row, l_col, t_row, t_col, r_row, r_col, b_row, b_col
    t = t.transpose(0, 2, 4, 6, 1, 3, 5, 7).reshape(256, 256)
    t = (W @ t).reshape(4, 4, 4, 4, 4, 4, 4, 4)
    return t.transpose(0, 4, 1, 5, 2, 6, 3, 7).reshape(16, 16, 16, 16)


def _vacuum() -> np.ndarray:
    link = 0.5 * np.eye(4).reshape(16)  # Psi = 1/2 * identity, row-major vec
    return np.einsum("a,b,c,d->abcd", link, link, link, link).reshape(-1).astype(complex)


@lru_cache(maxsize=None)
def _blocks(with_k2: bool):
    """(V, K1p, K2p, Sp): orthonormal basis V (65536 x d, column 0 = Omega) of the invariant subspace and the projected
    sum_l K1, sum_l K2, square.  with_k2 False: K2 is not a generator (r = 0); K2p is still projected (only valid if
    the subspace is K2-invariant, so it is returned as None)."""
    k1, k2, W = K1(), K2(), plaquette_row()
    gens = [lambda v: _kin(k1, v), lambda v: _square(W, v)]
    if with_k2:
        gens.append(lambda v: _kin(k2, v))
    basis = [_vacuum()]
    i = 0
    while i < len(basis):
        for g in gens:
            w = g(basis[i].reshape(16, 16, 16, 16)).reshape(-1)
            for _ in range(2):  # full re-orthogonalisation, twice
                for b in basis:
                    w = w - np.vdot(b, w) * b
            n = np.linalg.norm(w)
            if n > _TOL_KRYLOV:
                basis.append(w / n)
        i += 1
    V = np.array(basis).T  # 65536 x d
    d = V.shape[1]

    def proj(g):
        return np.array([V.conj().T @ g(V[:, j].reshape(16, 16, 16, 16)).reshape(-1) for j in range(d)]).T

    K1p = proj(gens[0])
    Sp = proj(gens[1])
    K2p = proj(gens[2]) if with_k2 else None
    herm = lambda A: 0.5 * (A + A.conj().T)
    return V, herm(K1p), (herm(K2p) if K2p is not None else None), herm(Sp)


def _sector(g2: float, r: float):
    r = float(r)
    _, K1p, K2p, Sp = _blocks(r != 0.0)
    H = 0.25 * g2 * K1p - (2.0 / g2) * Sp
    if r != 0.0:
        H = H + 0.25 * g2 * r * K2p
    return 0.5 * (H + H.conj().T), Sp


# ---------------------------------------------------------------------------------------------------------------- public API
def g2_of(alpha: float, beta: float) -> float:
    """g^2 = sqrt(2 alpha / beta)  (alpha = g^2 dt/2, beta = dt/g^2)."""
    return float(np.sqrt(2.0 * alpha / beta))


def electric_spectrum(g2: float) -> list:
    """Spectrum of (g2/4) K1 on one link: {0, 3 g2/8, g2/2}."""
    return [0.0, 0.375 * float(g2), 0.5 * float(g2)]


def outer_vacuum_energy(g2: float, r: float, n_outer: int = 8) -> float:
    """Constant energy of the outer links in the Psi = 1/2 copy: n_outer * (g2/4) * r * (-4) (K1 = 0 there)."""
    return float(n_outer) * 0.25 * g2 * r * (-4.0)


def closed_sector(g2: float, r: float):
    """(H, dim): H(g2, r) on the closed sector generated from Omega; Hermitian dim x dim, basis vector 0 = Omega."""
    H, _ = _sector(float(g2), r)
    return H, H.shape[0]


def _evolve_vacuum(ts, H):
    w, U = np.linalg.eigh(H)
    c0 = U[0, :].conj()  # <eig|Omega> = conj(U[0, k]); amplitude in eigenbasis
    ts = np.atleast_1d(np.asarray(ts, float))
    # psi(t) = U diag(exp(-i w t)) U^dag e0 ;  U^dag e0 = conj(U[0, :])
    return ts, w, U, c0


def plaquette_at_time(t: float, g2: float, r: float) -> float:
    """<Omega| e^{iHt} (square + square^dag)/2 e^{-iHt} |Omega>, evaluated in the closed sector."""
    H, Sp = _sector(float(g2), r)
    _, w, U, c0 = _evolve_vacuum(t, H)
    psi = U @ (np.exp(-1j * w * float(t)) * c0)
    P = 0.5 * (Sp + Sp.conj().T)
    return float(np.real(np.vdot(psi, P @ psi)))


def loschmidt(ts, g2: float, r: float) -> np.ndarray:
    """L(t) = |<Omega| e^{-iHt} |Omega>|^2 for an array of times."""
    H, _ = _sector(float(g2), r)
    ts, w, U, c0 = _evolve_vacuum(ts, H)
    amp = np.array([np.sum(np.abs(U[0, :]) ** 2 * np.exp(-1j * w * t)) for t in ts])
    return np.abs(amp) ** 2


def ks_closed_sector(g2: float) -> np.ndarray:
    """KS closed sector in {|0000>, |16>}: [[0, -2/g2], [-2/g2, 3 g2/2]]."""
    g2 = float(g2)
    return np.array([[0.0, -2.0 / g2], [-2.0 / g2, 1.5 * g2]])


def ks_loschmidt(ts, g2: float) -> np.ndarray:
    w, U = np.linalg.eigh(ks_closed_sector(g2))
    ts = np.atleast_1d(np.asarray(ts, float))
    amp = np.array([np.sum(np.abs(U[0, :]) ** 2 * np.exp(-1j * w * t)) for t in ts])
    return np.abs(amp) ** 2


def ks_plaquette_at_time(t: float, g2: float) -> float:
    """<Re Tr W>(t) from the vacuum in the KS 2x2 block, Re Tr W = sigma_x there."""
    w, U = np.linalg.eigh(ks_closed_sector(g2))
    psi = U @ (np.exp(-1j * w * float(t)) * U[0, :].conj())
    X = np.array([[0.0, 1.0], [1.0, 0.0]])
    return float(np.real(np.vdot(psi, X @ psi)))


def one_step_plaquette(alpha: float, beta: float, r: float, order: int = 1) -> float:
    """<Omega| U^dag (square + square^dag)/2 U |Omega> after one Trotter step of the given order (0 exactly)."""
    psi = apply_step(_vacuum(), alpha, beta, kappa2_of(alpha, r), order)
    W = plaquette_row()
    s = _square(W, psi.reshape(16, 16, 16, 16)).reshape(-1)
    return float(np.real(np.vdot(psi, s)))


# grids of the shared table (same in all rows)
BETA_GRID = (0.1, 0.25, 0.4, 0.61, 0.8, 1.0, 1.5)
T_GRID = tuple(float(x) for x in np.linspace(0.0, 4.0, 21))


def shared_table(alpha: float = 0.37, beta: float = 0.61, prov: dict | None = None) -> dict:
    """Content of results/fuzzy/shared_observables.json.  ``prov`` overrides the provenance snapshot (m9_results.py
    passes its shared one)."""
    from ..metrics.provenance import provenance

    g2 = g2_of(alpha, beta)
    ts = np.array(T_GRID)
    rows = {}
    for name, r in (("fuzzy_r1", 1.0), ("fuzzy_r0", 0.0)):
        H, dim = closed_sector(g2, r)
        L = loschmidt(ts, g2, r)
        rows[name] = {
            "r": r,
            "electric_per_link": [float(x) for x in electric_spectrum(g2)],
            "closed_sector_dim": int(dim),
            "closed_sector_spectrum": [float(x) for x in np.linalg.eigvalsh(H)],
            "plaquette_vs_beta": [[float(b), plaquette_at_time(b * g2, g2, r)] for b in BETA_GRID],
            "loschmidt": [[float(t), float(v)] for t, v in zip(ts, L)],
        }
    Lk = ks_loschmidt(ts, g2)
    rows["ks"] = {
        "electric_per_link": [0.0, 0.375 * g2],
        "closed_sector_dim": 2,
        "closed_sector_spectrum": [float(x) for x in np.linalg.eigvalsh(ks_closed_sector(g2))],
        "plaquette_vs_beta": [[float(b), ks_plaquette_at_time(b * g2, g2)] for b in BETA_GRID],
        "loschmidt": [[float(t), float(v)] for t, v in zip(ts, Lk)],
    }
    return {"g2": float(g2), "alpha": float(alpha), "beta": float(beta), "rows": rows,
            "provenance": prov if prov is not None else provenance({})}
