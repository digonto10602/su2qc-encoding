"""Rishon inner operators on the 1296 valid 16-bit codes (prompts/200 §2.3; METHODS-rishon R1, R4).

Every link operator used here preserves the two-rishon sector, so it is restricted to the 6 sector states of a link
(6x6 blocks) and the inner operators are Kronecker products over the four inner links.  The sorted inner codes
`sum_l s_l << 4l` (link 0 least significant, s_l in the sorted sector) are exactly the row-major order of
`kron(link3, link2, link1, link0)`, so no code lookup is needed.  All operators are dense complex128 1296 x 1296
(or the 1296-vector of a diagonal).
"""
from __future__ import annotations

import functools
import itertools

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components

from su2plaq.geometry import plaquette_diagram
from su2plaq.rishon.algebra import CODE_A, CODE_B, CODES_Q, RishonLink

_N_INNER = 4
_TOL = 1e-12
_HEIGHT_BR = {"A": 0, "Q": 1, "B": 2}      # links b, r (0, 1)
_HEIGHT_TL = {"B": 0, "Q": 1, "A": 2}      # links t, l (2, 3)


@functools.lru_cache(maxsize=1)
def _link() -> RishonLink:
    return RishonLink()


@functools.lru_cache(maxsize=1)
def _sector_ops() -> dict:
    """16x16 link operators restricted to the 6-state sector (sector-preserving, checked)."""
    rl = _link()
    sec = rl.sector

    def restrict(M: np.ndarray) -> np.ndarray:
        out = np.zeros((16, 16), dtype=np.complex128)
        out[:, sec] = M[:, sec]
        if np.abs(out[np.setdiff1d(np.arange(16), sec)]).max() > _TOL:
            raise ValueError("operator does not preserve the two-rishon sector")
        return M[np.ix_(sec, sec)].astype(np.complex128)

    return {
        "U": [[restrict(rl.U(i, j)) for j in range(2)] for i in range(2)],
        "Ud": [[restrict(rl.Udag(i, j)) for j in range(2)] for i in range(2)],
        "L": [restrict(m) for m in rl.L],
        "R": [restrict(m) for m in rl.R],
        "det": restrict(rl.det_U),
    }


def _kron4(ms: list) -> np.ndarray:
    """ms[l] is the 6x6 operator of inner link l; link 0 least significant (matches sorted inner codes)."""
    out = np.ones((1, 1), dtype=np.complex128)
    for m in ms:
        out = np.kron(m, out)
    return out


def _eye6() -> np.ndarray:
    return np.eye(6, dtype=np.complex128)


def inner_codes() -> np.ndarray:
    """Sorted int64 16-bit data codes with two rishons on each of the four inner links (6^4 = 1296)."""
    sector = RishonLink().sector
    codes = [sum(int(s) << (4 * l) for l, s in enumerate(cfg)) for cfg in itertools.product(sector, repeat=_N_INNER)]
    return np.array(sorted(codes), dtype=np.int64)


def _types(code: int) -> tuple[str, ...]:
    rl = _link()
    out = []
    for l in range(_N_INNER):
        t = rl.link_type((int(code) >> (4 * l)) & 15)
        if t is None:
            raise ValueError(f"invalid link code in inner code {int(code):#06x}")
        out.append(t)
    return tuple(out)


@functools.lru_cache(maxsize=1)
def _W() -> np.ndarray:
    """Tr(U_b U_r U_t^dag U_l^dag) = sum_abcd (U_b)_ab (U_r)_bc (U_t^dag)_cd (U_l^dag)_da, with (U^dag)_cd = (U_dc)^dag."""
    ops = _sector_ops()
    U, Ud = ops["U"], ops["Ud"]
    W = np.zeros((1296, 1296), dtype=np.complex128)
    for a, b, c, d in itertools.product(range(2), repeat=4):
        W += _kron4([U[a][b], U[b][c], Ud[d][c], Ud[a][d]])
    if np.abs(W.imag).max() > _TOL:
        raise ValueError("the inner plaquette operator W is not real")
    W.setflags(write=False)
    return W


def plaquette_W_inner() -> np.ndarray:
    """W = Tr(U_P), U_P = U_b U_r U_t^dag U_l^dag, restricted to the inner codes (real entries, complex128)."""
    return _W().copy()


@functools.lru_cache(maxsize=1)
def _HE() -> np.ndarray:
    codes = inner_codes()
    q = np.zeros(len(codes))
    for l in range(_N_INNER):
        nib = (codes >> (4 * l)) & 15
        q += np.isin(nib, CODES_Q)
    return 0.75 * q


def h_electric_inner() -> np.ndarray:
    """Diagonal of H_E on the inner codes: 3/4 per quartet (Q) inner link."""
    return _HE().copy()


def h_magnetic_inner() -> np.ndarray:
    """H_B^in = -(W + W^dag)."""
    W = _W()
    return -(W + W.conj().T)


def gauss_inner(corner: int, a: int) -> np.ndarray:
    """Inner-end part of G^a_corner: sum of L_a / R_a over the inner links ending at the corner."""
    D = plaquette_diagram()
    if not 0 <= corner < len(D.corners):
        raise ValueError(f"corner {corner} out of range")
    if a not in (0, 1, 2):
        raise ValueError(f"colour index a={a} out of range")
    ops = _sector_ops()
    G = np.zeros((1296, 1296), dtype=np.complex128)
    for link, role in D.corners[corner].ends:
        if link >= _N_INNER:
            continue
        ms = [_eye6()] * _N_INNER
        ms[link] = ops["L"][a] if role == "out" else ops["R"][a]
        G += _kron4(ms)
    return G


def heights(code: int) -> tuple[int, int, int, int]:
    """Link heights of an inner code: h(A,Q,B) = (0,1,2) for b, r and (2,1,0) for t, l."""
    t = _types(code)
    return (_HEIGHT_BR[t[0]], _HEIGHT_BR[t[1]], _HEIGHT_TL[t[2]], _HEIGHT_TL[t[3]])


def _fix_sign(x: np.ndarray) -> np.ndarray:
    """Sign convention: the first component of maximal modulus (within 1e-10) is positive."""
    first = int(np.flatnonzero(np.abs(x) >= np.abs(x).max() - 1e-10)[0])
    return x if x[first] > 0 else -x


@functools.lru_cache(maxsize=1)
def _bright() -> tuple:
    """(pairs, dark mask): one bright pair per connected component of |H_B^in| (spectrum {+k, -k, 0, ...} on it)."""
    W = _W()
    HB = -(W + W.conj().T)
    ncomp, lab = connected_components(sp.csr_matrix(np.abs(HB) > _TOL), directed=False)
    pairs = []
    bright = np.zeros(len(W), dtype=bool)
    for ci in range(ncomp):
        idx = np.flatnonzero(lab == ci)
        if len(idx) == 1:
            continue
        sub = np.real(HB[np.ix_(idx, idx)])
        w, V = np.linalg.eigh(sub)
        kappa = float(w[-1])
        if abs(w[0] + kappa) > 1e-9 or (len(w) > 2 and np.abs(w[1:-1]).max() > 1e-9):
            raise ValueError("a bright component of H_B^in does not have the spectrum {+k, -k, 0...}")
        p_vec, m_vec = _fix_sign(V[:, -1]), _fix_sign(V[:, 0])       # eigenvalues +kappa and -kappa of H_B
        uu = (m_vec + p_vec) / np.sqrt(2.0)                          # H_B = -kappa (|u><v| + h.c.)
        vv = (m_vec - p_vec) / np.sqrt(2.0)
        if not np.array_equal(_fix_sign(uu), uu):
            uu, vv = -uu, -vv               # the joint flip leaves |u><v| + h.c. invariant
        u = np.zeros(len(W))
        v = np.zeros(len(W))
        u[idx] = uu
        v[idx] = vv
        u[np.abs(u) < 1e-13] = 0.0
        v[np.abs(v) < 1e-13] = 0.0
        bright[idx] = True
        pairs.append((u, v, kappa, int(idx[0])))
    pairs.sort(key=lambda p: (round(p[2], 9), p[3]))
    return tuple((u, v, k) for u, v, k, _ in pairs), ~bright


def bright_pairs() -> list[tuple[np.ndarray, np.ndarray, float]]:
    """81 pairs (u, v, kappa) with H_B^in = -sum kappa (|u><v| + h.c.): u = (m + p)/sqrt2, v = (m - p)/sqrt2 for the
    eigenvectors p, m of H_B^in with eigenvalues +kappa, -kappa of each connected component (each with its first
    max-modulus component positive); then (u, v) -> (-u, -v) if u's first max-modulus component is negative.
    Real orthonormal unit vectors on the 1296 codes.  Sorted by (kappa, first code index of the component)."""
    return [(u.copy(), v.copy(), k) for u, v, k in _bright()[0]]


def dark_codes() -> np.ndarray:
    """Inner codes that are isolated in H_B^in (W psi = W^dag psi = 0): 990 of them."""
    return inner_codes()[_bright()[1]]


def _ue(alpha: float | None) -> np.ndarray:
    if alpha is None:
        raise ValueError("alpha is required for kind 'UE'/'step'")
    return np.diag(np.exp(-1j * float(alpha) * _HE())).astype(np.complex128)


def _ub(beta: float | None) -> np.ndarray:
    """exp(-i beta H_B^in) = 1 + sum_p [(cos k b - 1)(|u><u| + |v><v|) + i sin(k b)(|u><v| + |v><u|)]."""
    if beta is None:
        raise ValueError("beta is required for kind 'UB'/'step'")
    out = np.eye(1296, dtype=np.complex128)
    for u, v, k in _bright()[0]:
        c, s = np.cos(k * beta), np.sin(k * beta)
        out += (c - 1.0) * (np.outer(u, u) + np.outer(v, v)) + 1j * s * (np.outer(u, v) + np.outer(v, u))
    return out


def inner_target(kind: str, alpha: float | None, beta: float | None, order: int = 1) -> np.ndarray:
    """Unitary 1296 x 1296 target: 'UE' = exp(-i alpha H_E), 'UB' = exp(-i beta H_B^in), 'step' order 1 = UB UE,
    order 2 = UE(alpha/2) UB UE(alpha/2) (METHODS §2)."""
    if kind == "UE":
        return _ue(alpha)
    if kind == "UB":
        return _ub(beta)
    if kind == "step":
        if order == 1:
            return _ub(beta) @ _ue(alpha)
        if order == 2:
            half = _ue(None if alpha is None else float(alpha) / 2)
            return half @ _ub(beta) @ half
        raise ValueError(f"step order must be 1 or 2, got {order}")
    raise ValueError(f"unknown kind {kind!r}; expected 'UE', 'UB' or 'step'")


@functools.lru_cache(maxsize=1)
def _closed() -> tuple:
    codes = inner_codes()
    va = CODE_A | (CODE_A << 4) | (CODE_B << 8) | (CODE_B << 12)
    vb = CODE_B | (CODE_B << 4) | (CODE_A << 8) | (CODE_A << 12)
    ia = int(np.searchsorted(codes, va))
    ib = int(np.searchsorted(codes, vb))
    col = _W()[:, ia]
    nrm = float(np.linalg.norm(col))
    loop_idx = np.flatnonzero(np.abs(col) > _TOL)
    loop_vec = np.real(col) / nrm
    return va, vb, ia, ib, codes[loop_idx].copy(), loop_vec


def closed_codes() -> tuple[int, int, np.ndarray]:
    """(code of vac_A, code of vac_B, the 16 inner codes of the loop state |loop> ~ W |vac_A>)."""
    va, vb, _, _, loop, _ = _closed()
    return va, vb, loop.copy()


def closed_block(g2: float) -> np.ndarray:
    """3x3 block of H(g2) = (g2/2) H_E + H_B^in / g2 in the basis (vac_A, loop, vac_B), computed from W."""
    _, _, ia, ib, _, ln = _closed()
    B = np.zeros((3, 1296))
    B[0, ia] = 1.0
    B[1] = ln
    B[2, ib] = 1.0
    H = 0.5 * g2 * np.diag(_HE()) + h_magnetic_inner().real / g2
    return (B @ H @ B.T).astype(np.complex128)


def det_term_inner() -> np.ndarray:
    """sum over the four inner links of (det U_l + h.c.) on the inner codes (gamma = 0 in M5: defined, not used)."""
    det = _sector_ops()["det"]
    D = np.zeros((1296, 1296), dtype=np.complex128)
    for l in range(_N_INNER):
        ms = [_eye6()] * _N_INNER
        ms[l] = det
        T = _kron4(ms)
        D += T + T.conj().T
    return D
