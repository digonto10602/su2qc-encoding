"""Route-A physical basis: products of corner singlets (prompts/002 §2.3, docs/METHODS.md §4).

A physical state is the tensor product of four corner singlets (kernel of the corner Casimir
sum_a (sum_ends G_a)^2 on the product of the four end spaces), stored as a sparse COO vector over the
12-link electric multi-index  key = sum_i s_i 5^i  (s_i = LinkSpace index of link i in the basis
convention; far end of every outer link fixed to the first m value).  Only jmax = 1/2 is supported
(5 local states per link); the jmax = 1 count is done by the route-B enumeration (`spinnet.labels`).
Pattern for the corner tensors: su2qc-skqd src/skqd/vertex.py (matter fixed to 0).
"""
from __future__ import annotations

import functools
import itertools
import math
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

from su2plaq.geometry import Diagram, plaquette_diagram
from su2plaq.su2.algebra import LinkSpace, m_values, paulo_adapter, spin_matrices

_BASE = 5          # local dimension of a link at jmax = 1/2
_NL = 12
_INNER = _BASE ** 4  # 625


SIGN_TIE_TOL = 1e-10


def _canonical_sign(vec: np.ndarray) -> np.ndarray:
    """Rotate the phase so that the FIRST component (lowest index) whose modulus is within SIGN_TIE_TOL of the maximum is
    real positive (a plain argmax would let rounding noise decide among tied moduli, machine-dependently)."""
    a = np.abs(vec)
    p = int(np.flatnonzero(a >= a.max() - SIGN_TIE_TOL)[0])
    return vec * (abs(vec[p]) / vec[p])


@functools.lru_cache(maxsize=None)
def corner_singlets(js: tuple[float, float, float, float], roles: tuple[str, str, str, str]) -> tuple[np.ndarray, tuple[float, ...]]:
    """Kernel of sum_a (sum_ends G_a)^2 on the product of the 4 end spaces (end order = js order; 'out' end
    carries L = -J^T, 'in' end carries R = +J); columns are orthonormal real vectors sorted by the inner-pair
    Casimir eigenvalue J(J+1) of ends 0,1; phase: the first component within 1e-10 of the largest modulus is positive. Returns (vectors[D,k], J labels)."""
    dims = [int(round(2 * j + 1)) for j in js]
    D = int(np.prod(dims))

    def embed(op, pos):
        out = np.array([[1.0 + 0j]])
        for q, d in enumerate(dims):
            out = np.kron(out, op if q == pos else np.eye(d, dtype=complex))
        return out

    gens = []
    for e, (j, role) in enumerate(zip(js, roles)):
        Jm = spin_matrices(j)
        gens.append([embed(-Jm[a].T if role == "out" else Jm[a], e) for a in range(3)])
    G = [sum(g[a] for g in gens) for a in range(3)]
    C = sum(g @ g for g in G)
    w, v = np.linalg.eigh((C + C.conj().T) / 2)
    kern = v[:, w < 1e-9]
    if kern.shape[1] == 0:
        return np.zeros((D, 0)), ()
    Cin = sum((gens[0][a] + gens[1][a]) @ (gens[0][a] + gens[1][a]) for a in range(3))
    lab = kern.conj().T @ Cin @ kern
    lw, lv = np.linalg.eigh((lab + lab.conj().T) / 2)
    kern = kern @ lv
    Js = tuple(round(2 * (-0.5 + math.sqrt(max(x, 0.0) + 0.25))) / 2 for x in lw)
    cols = []
    for c in range(kern.shape[1]):
        vec = kern[:, c]
        vec = _canonical_sign(vec)
        if np.abs(vec.imag).max() > 1e-12:
            raise RuntimeError("corner singlet not real after phase fixing")
        cols.append(vec.real)
    return np.array(cols).T, Js


@dataclass
class PhysicalBasis:
    diagram: Diagram
    jmax: float
    convention: str  # 'cg' | 'paulo'
    labels: list[tuple[tuple[float, ...], tuple[float, ...]]]  # ((j_0..j_11),(J_0..J_3)), J by corner index
    keys: list[np.ndarray]
    amps: list[np.ndarray]
    dim: int
    _index: dict = field(default_factory=dict, repr=False, compare=False)

    def index(self, label) -> int:
        if not self._index:
            self._index.update({lab: k for k, lab in enumerate(self.labels)})
        return self._index[label]

    @staticmethod
    def inner_key(keys) -> np.ndarray:
        return np.asarray(keys) % _INNER

    @staticmethod
    def outer_key(keys) -> np.ndarray:
        return np.asarray(keys) // _INNER


_CACHE: dict = {}


def physical_basis(diagram: Diagram | None = None, jmax: float = 0.5, convention: str = "cg") -> PhysicalBasis:
    if convention not in ("cg", "paulo"):
        raise ValueError(f"unknown convention {convention!r}")
    if abs(jmax - 0.5) > 1e-12:
        raise NotImplementedError("route-A physical_basis is implemented for jmax = 1/2 only (5 states per link)")
    if diagram is None and (jmax, convention) in _CACHE:
        return _CACHE[(jmax, convention)]
    d = diagram if diagram is not None else plaquette_diagram()
    basis = _build_cg(d, jmax)
    if convention == "paulo":
        basis = to_convention(basis, "paulo")
    if diagram is None:
        _CACHE[(jmax, convention)] = basis
    return basis


def _build_cg(d: Diagram, jmax: float) -> PhysicalBasis:
    ls = LinkSpace(jmax)
    spins = ls.spins
    local = {j: np.array([[ls.index[(j, ma, mb)] for mb in m_values(j)] for ma in m_values(j)]) for j in spins}
    corner_ends = [c.ends for c in d.corners]
    labels, keys_l, amps_l = [], [], []
    for jconf in itertools.product(spins, repeat=_NL):
        per_corner = []
        for ends in corner_ends:
            js = tuple(jconf[i] for i, _ in ends)
            roles = tuple(r for _, r in ends)
            vecs, Js = corner_singlets(js, roles)
            if vecs.shape[1] == 0:
                per_corner = None
                break
            per_corner.append((ends, js, vecs, Js))
        if per_corner is None:
            continue
        for combo in itertools.product(*[range(pc[2].shape[1]) for pc in per_corner]):
            legs, dims, vec = [], [], np.array([1.0])
            for (ends, js, vecs, _Js), c in zip(per_corner, combo):
                vec = np.kron(vec, vecs[:, c])
                legs += list(ends)
                dims += [int(round(2 * j + 1)) for j in js]
            nz = np.where(np.abs(vec) > 1e-14)[0]
            idxs = np.array(np.unravel_index(nz, dims)).T
            keys = np.zeros(len(nz), dtype=np.int64)
            for i in range(_NL):
                mL = np.zeros(len(nz), dtype=int)  # far end: first m value
                mR = np.zeros(len(nz), dtype=int)
                for k, (link, role) in enumerate(legs):
                    if link == i:
                        if role == "out":
                            mL = idxs[:, k]
                        else:
                            mR = idxs[:, k]
                keys += local[jconf[i]][mL, mR].astype(np.int64) * _BASE ** i
            labels.append((tuple(float(x) for x in jconf), tuple(float(per_corner[q][3][combo[q]]) for q in range(4))))
            keys_l.append(keys)
            amps_l.append(vec[nz].astype(np.complex128))
    return PhysicalBasis(d, jmax, "cg", labels, keys_l, amps_l, len(labels))


def apply_link_op(keys, amps, link: int, M: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(M acting on the local index of `link`) applied to the COO vector; output coalesced and sorted."""
    keys = np.asarray(keys, dtype=np.int64)
    amps = np.asarray(amps, dtype=np.complex128)
    p = _BASE ** link
    s = (keys // p) % _BASE
    base = keys - s * p
    outk, outa = [], []
    for sp_ in range(M.shape[0]):
        col = M[sp_, s]
        nz = np.abs(col) > 0
        if nz.any():
            outk.append(base[nz] + sp_ * p)
            outa.append(col[nz] * amps[nz])
    if not outk:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.complex128)
    return _coalesce(np.concatenate(outk), np.concatenate(outa))


def _coalesce(k, a):
    uk, inv = np.unique(k, return_inverse=True)
    ua = np.zeros(len(uk), dtype=np.complex128)
    np.add.at(ua, inv, a)
    return uk, ua


@functools.lru_cache(maxsize=None)
def _generators(convention: str):
    L, R = LinkSpace(0.5).generators()
    if convention == "cg":
        return L, R
    V = paulo_adapter()
    return [V @ g @ V.T for g in L], [V @ g @ V.T for g in R]


def gauss_residuals_coo(basis: PhysicalBasis, keys_list, amps_list) -> np.ndarray:
    """Gauss residual max_{c,a} ||sum_{ends of c} G_a psi|| for many COO states at once (state id folded into the key
    above 5^12, which no link operator touches)."""
    L, R = _generators(basis.convention)
    n = len(keys_list)
    sid = np.concatenate([np.full(len(k), i, dtype=np.int64) for i, k in enumerate(keys_list)])
    keys = np.concatenate([np.asarray(k, dtype=np.int64) for k in keys_list]) + sid * _BASE ** _NL
    amps = np.concatenate([np.asarray(a, dtype=np.complex128) for a in amps_list])
    worst = np.zeros(n)
    for corner in basis.diagram.corners:
        for a in range(3):
            ks, vs = [], []
            for link, role in corner.ends:
                k2, v2 = apply_link_op(keys, amps, link, L[a] if role == "out" else R[a])
                ks.append(k2)
                vs.append(v2)
            uk, v = _coalesce(np.concatenate(ks), np.concatenate(vs))
            w = np.bincount(uk // _BASE ** _NL, weights=np.abs(v) ** 2, minlength=n)
            worst = np.maximum(worst, np.sqrt(w))
    return worst


def gauss_residual(basis: PhysicalBasis, keys, amps) -> float:
    """max over corners c and a of || sum_{ends of c} G_a psi || (G = L for 'out', R for 'in', in basis.convention)."""
    return float(gauss_residuals_coo(basis, [keys], [amps])[0])


def gauss_residuals(basis) -> np.ndarray:
    return gauss_residuals_coo(basis, basis.keys, basis.amps)


def _sparse_matrix(basis):
    allk = np.concatenate(basis.keys)
    uk, inv = np.unique(allk, return_inverse=True)
    cols = np.concatenate([np.full(len(k), i) for i, k in enumerate(basis.keys)])
    vals = np.concatenate(basis.amps)
    return sp.csr_matrix((vals, (inv, cols)), shape=(len(uk), basis.dim)), uk


def gram(basis) -> np.ndarray:
    A, _ = _sparse_matrix(basis)
    return (A.conj().T @ A).toarray()


def counts(basis) -> dict:
    strings: dict = {}
    for j, _J in basis.labels:
        strings[j] = strings.get(j, 0) + 1
    return {
        "dim": basis.dim,
        "closed": sum(1 for j, _ in basis.labels if all(x == 0.0 for x in j[4:])),
        "link_strings": len(strings),
        "ambiguous": sum(1 for v in strings.values() if v > 1),
        "far_end_weighted": int(sum(np.prod([2 * x + 1 for x in j[4:]]) for j, _ in basis.labels)),
    }


def _inner_components(basis):
    """{outer key: list of (state, inner keys, amps)}."""
    out: dict = {}
    for k, (keys, amps) in enumerate(zip(basis.keys, basis.amps)):
        ok = keys // _INNER
        ik = keys % _INNER
        for o in np.unique(ok):
            sel = ok == o
            out.setdefault(int(o), []).append((k, ik[sel], amps[sel]))
    return out


def s_o_support(basis) -> dict[int, np.ndarray]:
    return {o: np.unique(np.concatenate([ik for _, ik, _ in items])) for o, items in _inner_components(basis).items()}


def _dense_inner(items):
    M = np.zeros((_INNER, len(items)), dtype=np.complex128)
    for c, (_, ik, a) in enumerate(items):
        M[ik, c] = a
    return M


def _rank_basis(M, tol=1e-9):
    u, s, _ = np.linalg.svd(M, full_matrices=False)
    r = int((s > tol * max(1.0, s[0] if len(s) else 1.0)).sum())
    return u[:, :r]


def s_o_dims(basis) -> dict[int, int]:
    return {o: _rank_basis(_dense_inner(items)).shape[1] for o, items in _inner_components(basis).items()}


def inner_span(basis) -> np.ndarray:
    """(625, r) orthonormal basis of span_o S_o."""
    M = np.concatenate([_dense_inner(items) for items in _inner_components(basis).values()], axis=1)
    return _rank_basis(M)


def to_convention(basis, convention: str) -> PhysicalBasis:
    """Apply V_P (or V_P^T for paulo -> cg; V_P is symmetric) to every link: a signed permutation of local indices."""
    if convention not in ("cg", "paulo"):
        raise ValueError(f"unknown convention {convention!r}")
    if convention == basis.convention:
        return basis
    V = paulo_adapter()
    M = V if convention == "paulo" else V.T
    perm = np.array([int(np.nonzero(M[:, c])[0][0]) for c in range(_BASE)], dtype=np.int64)
    sign = np.array([M[perm[c], c] for c in range(_BASE)])
    keys_new, amps_new = [], []
    for keys, amps in zip(basis.keys, basis.amps):
        nk = np.zeros_like(keys)
        na = amps.astype(np.complex128).copy()
        for i in range(_NL):
            s = (keys // _BASE ** i) % _BASE
            nk += perm[s] * _BASE ** i
            na = na * sign[s]
        keys_new.append(nk)
        amps_new.append(na)
    return PhysicalBasis(basis.diagram, basis.jmax, convention, list(basis.labels), keys_new, amps_new, basis.dim)
