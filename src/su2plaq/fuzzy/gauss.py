"""Gauss's law, physical-state counts and seeded physical states on the 12-link fuzzy diagram (M9; METHODS-fuzzy F4).

Geometry (METHODS §1): inner links b, r, t, l (loop [b+, r+, t-, l-]) run b: 0->1, r: 1->2, t: 3->2, l: 0->3 between the corners
0..3; outer links o_0..o_7 hang off the corners, two per corner.  Link ``ell`` = 0..11 in the order b, r, t, l, o_0..o_7 occupies
qubits 4 ell..4 ell+3, i.e. bits 4 ell..4 ell+3 of a 48-bit key (local index 4 row + col).  A link leaving a corner is acted on
there by calT_L (spin j_L), a link entering it by calT_R (spin j_R).  Gauss generator at corner c (P Eq. 33):
``G^A_c = sum_{out} calT_L^A + sum_{in} calT_R^A``.  Outer links: the end at the corner is the *near* end, the other end is free.
"""
from __future__ import annotations

import itertools

import numpy as np
import scipy.sparse as sp

from su2plaq.fuzzy import link as _lk

N_LINKS = 12
# (tail corner, head corner); for outer links the far end is the free one (-1); same as su2plaq.geometry._LINKS (unit-tested)
_TAIL = [0, 1, 3, 0, -1, -1, 1, -1, 2, 2, -1, 3]
_HEAD = [1, 2, 2, 3, 0, 0, -1, 1, -1, -1, 3, -1]
# near end (corner, role) of outer link ell = 4 + k: o0,o1 in at 0; o2 out, o3 in at 1; o4,o5 out at 2; o6 in, o7 out at 3
_OUTER_NEAR = {4 + k: v for k, v in enumerate([(0, "in"), (0, "in"), (1, "out"), (1, "in"), (2, "out"), (2, "out"), (3, "in"), (3, "out")])}
CORNER_ENDS: dict[int, list[tuple[int, str]]] = {
    0: [(0, "out"), (3, "out"), (4, "in"), (5, "in")],
    1: [(0, "in"), (1, "out"), (6, "out"), (7, "in")],
    2: [(1, "in"), (2, "in"), (8, "out"), (9, "out")],
    3: [(2, "out"), (3, "in"), (10, "in"), (11, "out")],
}
INNER = (0, 1, 2, 3)
OUTER = tuple(range(4, 12))


def _two(j) -> int:
    return int(round(2 * float(j)))


def _tri2(a: int, b: int) -> set[int]:
    """2 T(j, j') for twice-spins a = 2j, b = 2j'."""
    return set(range(abs(a - b), a + b + 1, 2))


def corner_singlet_dim(j1, j2, j3, j4) -> int:
    """Number of SU(2) singlets in j1 x j2 x j3 x j4 = |T(j1, j2) and T(j3, j4)| (triangle rule)."""
    a1, a2, a3, a4 = (_two(j) for j in (j1, j2, j3, j4))
    return len(_tri2(a1, a2) & _tri2(a3, a4))


def _copies() -> list[tuple[int, int]]:
    """One entry (2 j_L, 2 j_R) per irrep copy of the link space (multiplicity expanded)."""
    out = []
    for jl, jr, mult in _lk.irreps():
        out += [(_two(jl), _two(jr))] * int(mult)
    return out


def _near_far(irr: tuple[int, int], role: str) -> tuple[int, int]:
    return (irr[0], irr[1]) if role == "out" else (irr[1], irr[0])


def _corner_sum(irr_inner: dict[int, tuple[int, int]], c: int, copies, far_weighted: bool, outer_vacuum: bool) -> int:
    inn = [_near_far(irr_inner[l], r)[0] for l, r in CORNER_ENDS[c] if l in irr_inner]
    outs = [r for l, r in CORNER_ENDS[c] if l not in irr_inner]
    total = 0
    for i1, i2 in itertools.product(copies, repeat=2):
        if outer_vacuum and (i1 != (0, 0) or i2 != (0, 0)):
            continue
        n1, f1 = _near_far(i1, outs[0])
        n2, f2 = _near_far(i2, outs[1])
        n = _singlets(inn + [n1, n2])
        if far_weighted:
            n *= (f1 + 1) * (f2 + 1)
        total += n
    return total


def _singlets(twos: list[int]) -> int:
    return len(_tri2(twos[0], twos[1]) & _tri2(twos[2], twos[3]))


def physical_count(far_weighted: bool, outer_vacuum: bool = False) -> int:
    """Route A: dimension of the Gauss kernel on the 12 links with the corner-factorised Clebsch-Gordan rule (F4).
    far_weighted=False fixes the far end of each outer link to one state; True counts all far-end states (weight 2 j_far + 1);
    outer_vacuum restricts both outer links of every corner to (0,0) copies."""
    copies = _copies()
    total = 0
    for assign in itertools.product(range(len(copies)), repeat=4):
        irr = {l: copies[a] for l, a in zip(INNER, assign)}
        prod = 1
        for c in range(4):
            prod *= _corner_sum(irr, c, copies, far_weighted, outer_vacuum)
            if prod == 0:
                break
        total += prod
    return int(total)


def isolated_plaquette_count() -> int:
    """Gauss-kernel dimension of the four inner links alone (outer links removed: every corner is 2-valent)."""
    copies = _copies()
    total = 0
    for assign in itertools.product(range(len(copies)), repeat=4):
        irr = {l: copies[a] for l, a in zip(INNER, assign)}
        prod = 1
        for c in range(4):
            nears = [_near_far(irr[l], r)[0] for l, r in CORNER_ENDS[c] if l in irr]
            prod *= 1 if nears[0] == nears[1] else 0
        total += prod
    return int(total)


def physical_count_characters(far_weighted: bool, n_points: int = 40) -> float:
    """Route B: Haar character integral over the four corner group elements (Weyl integration, Gauss-Legendre in the class
    angle theta in (0, pi) with weight (2/pi) sin^2 theta; exact for the trigonometric-polynomial integrand if n_points is large
    enough, 40 suffices).  Returns a float that rounds to the count."""
    copies = _copies()
    x, w = np.polynomial.legendre.leggauss(n_points)
    th = (x + 1) * np.pi / 2
    w = w * (np.pi / 2) * (2 / np.pi) * np.sin(th) ** 2
    shp = lambda i: tuple(-1 if k == i else 1 for k in range(4))  # noqa: E731
    TH = [th.reshape(shp(i)) for i in range(4)]

    def chi(two_j, t):
        return np.sin((two_j + 1) * t) / np.sin(t)

    f = np.ones((n_points,) * 4)
    for l in INNER:
        tl, hd = _TAIL[l], _HEAD[l]
        f = f * sum(chi(a, TH[tl]) * chi(b, TH[hd]) for a, b in copies)
    for l in OUTER:
        c, role = _OUTER_NEAR[l]
        f = f * sum(chi(_near_far(irr, role)[0], TH[c]) * ((_near_far(irr, role)[1] + 1) if far_weighted else 1) for irr in copies)
    W = w.reshape(shp(0)) * w.reshape(shp(1)) * w.reshape(shp(2)) * w.reshape(shp(3))
    return float(np.sum(W * f))


# --------------------------------------------------------------------------- Gauss operators on COO states
_G_CACHE: dict[tuple[int, int], sp.csr_matrix] = {}


def _corner_operator(c: int, A: int) -> sp.csr_matrix:
    """G^A_c on the 65536-dim space of the four links at corner c; nibble i (bits 4i..4i+3) = link CORNER_ENDS[c][i]."""
    if (c, A) not in _G_CACHE:
        G = sp.csr_matrix((1 << 16, 1 << 16), dtype=complex)
        for i, (_, role) in enumerate(CORNER_ENDS[c]):
            M = _lk.calT_L(A) if role == "out" else _lk.calT_R(A)
            M = sp.csr_matrix(np.where(np.abs(M) > 1e-15, M, 0))
            op = sp.identity(1, dtype=complex, format="csr")
            for k in (3, 2, 1, 0):   # kron order: most significant nibble first
                op = sp.kron(op, M if k == i else sp.identity(16, dtype=complex), format="csr")
            G = G + op
        _G_CACHE[(c, A)] = G.tocsr()
    return _G_CACHE[(c, A)]


class _CornerView:
    """A COO state regrouped by the spectator links (all links not at corner c) vs the 16 bits of the corner links."""

    def __init__(self, c: int, keys: np.ndarray, amps: np.ndarray):
        self.c = c
        ells = [l for l, _ in CORNER_ENDS[c]]
        self.ells = ells
        mask = np.int64(0)
        cidx = np.zeros(len(keys), dtype=np.int64)
        for i, l in enumerate(ells):
            mask |= np.int64(15) << (4 * l)
            cidx |= ((keys >> (4 * l)) & 15) << (4 * i)
        self.spect, inv = np.unique(keys & ~mask, return_inverse=True)
        self.mat = sp.csr_matrix((amps, (inv, cidx)), shape=(len(self.spect), 1 << 16))

    def apply(self, A: int) -> sp.csr_matrix:
        return (self.mat @ _corner_operator(self.c, A).T).tocsr()

    def to_coo(self, out: sp.csr_matrix) -> tuple[np.ndarray, np.ndarray]:
        out = out.tocoo()
        keys = self.spect[out.row].copy()
        for i, l in enumerate(self.ells):
            keys |= ((out.col.astype(np.int64) >> (4 * i)) & 15) << (4 * l)
        o = np.argsort(keys)
        return keys[o], out.data[o]


def _merge(keys: np.ndarray, amps: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sum amplitudes of equal keys; returns sorted unique keys."""
    if len(keys) == 0:
        return np.zeros(0, np.int64), np.zeros(0, complex)
    uk, inv = np.unique(keys, return_inverse=True)
    ua = np.zeros(len(uk), complex)
    np.add.at(ua, inv, amps)
    return uk, ua


def _prep(keys, amps) -> tuple[np.ndarray, np.ndarray]:
    keys = np.asarray(keys, dtype=np.int64)
    amps = np.asarray(amps, dtype=complex)
    if keys.shape != amps.shape or keys.ndim != 1:
        raise ValueError("keys and amps must be 1-d arrays of equal length")
    return keys, amps


def corner_generator_apply(c: int, A: int, keys: np.ndarray, amps: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """G^A_c |psi> for a 48-qubit COO state (keys < 2^48 int64): sum of calT_L^A over the links leaving corner c and calT_R^A
    over the links entering it.  Returns (keys sorted, amps) with duplicate keys already summed (exact zeros may be kept)."""
    keys, amps = _prep(keys, amps)
    if len(keys) == 0:
        return np.zeros(0, np.int64), np.zeros(0, complex)
    view = _CornerView(c, keys, amps)
    return view.to_coo(view.apply(A))


def gauss_residual(keys: np.ndarray, amps: np.ndarray) -> float:
    """max over corners c and A = 0..2 of ||G^A_c psi|| (not normalised)."""
    keys, amps = _prep(keys, amps)
    if len(keys) == 0:
        return 0.0
    worst = 0.0
    for c in range(4):
        view = _CornerView(c, keys, amps)
        for A in range(3):
            out = view.apply(A)
            worst = max(worst, float(np.sqrt(np.sum(np.abs(out.data) ** 2))))
    return worst


# --------------------------------------------------------------------------- seeded physical states (route-A tensors)
def _spin_mats(two_j: int) -> list[np.ndarray]:
    """Standard spin-j matrices J^1, J^2, J^3 in the basis m = j, j-1, ..., -j."""
    d = two_j + 1
    j = two_j / 2
    m = j - np.arange(d)
    Jp = np.zeros((d, d), complex)
    for a in range(1, d):  # |m_a> -> |m_{a-1}> = m_a + 1
        Jp[a - 1, a] = np.sqrt((j - m[a]) * (j + m[a] + 1))
    Jm = Jp.conj().T
    return [(Jp + Jm) / 2, (Jp - Jm) / 2j, np.diag(m).astype(complex)]


_BASIS_CACHE: dict[tuple[int, int, int], np.ndarray] = {}


def _link_irrep_basis(two_jl: int, two_jr: int, sign_f: int) -> np.ndarray:
    """Standard-basis vectors e[a, b, :] (16-dim, m_L = j_L - a, m_R = j_R - b) of the irrep copy (j_L, j_R) with flavour
    F = sign_f (F = Psi -> Psi Gamma_5 commutes with all generators, so it separates the copies).  calT_L and calT_R act on e as
    the standard spin matrices."""
    key = (two_jl, two_jr, sign_f)
    if key in _BASIS_CACHE:
        return _BASIS_CACHE[key]
    jl, jr = two_jl / 2, two_jr / 2
    TL = [_lk.calT_L(A) for A in range(3)]
    TR = [_lk.calT_R(A) for A in range(3)]
    Lp, Lm = TL[0] + 1j * TL[1], TL[0] - 1j * TL[1]
    Rp, Rm = TR[0] + 1j * TR[1], TR[0] - 1j * TR[1]
    I16 = np.eye(16)
    M = np.vstack([Lp, Rp, TL[2] - jl * I16, TR[2] - jr * I16, _lk.flavour() - sign_f * I16])
    _, s, vh = np.linalg.svd(M)
    null = vh[np.flatnonzero(np.concatenate([s, np.zeros(16 - len(s))]) < 1e-9)].conj()
    if len(null) != 1:
        raise RuntimeError(f"highest-weight space of ({jl},{jr}), F={sign_f} has dimension {len(null)} != 1")
    v = null[0]
    v = v * np.exp(-1j * np.angle(v[np.argmax(np.abs(v))]))
    E = np.zeros((two_jl + 1, two_jr + 1, 16), complex)
    for b in range(two_jr + 1):
        col = v if b == 0 else None
        if b > 0:
            mr = jr - (b - 1)
            col = Rm @ E[0, b - 1] / np.sqrt((jr + mr) * (jr - mr + 1))
        E[0, b] = col
        for a in range(1, two_jl + 1):
            ml = jl - (a - 1)
            E[a, b] = Lm @ E[a - 1, b] / np.sqrt((jl + ml) * (jl - ml + 1))
    E[np.abs(E) < 1e-13] = 0.0
    _BASIS_CACHE[key] = E
    return E


def _resolve_copies() -> list[tuple[int, int, int]]:
    """Copies with their F signs, determined by the dimension of the highest-weight space (robust to ordering)."""
    res = []
    for jl, jr, mult in _lk.irreps():
        good = []
        for sf in (+1, -1):
            try:
                _link_irrep_basis(_two(jl), _two(jr), sf)
            except RuntimeError:
                continue
            good.append((_two(jl), _two(jr), sf))
        if len(good) != int(mult):
            raise RuntimeError(f"flavour does not resolve the copies of ({jl},{jr}): {len(good)} vs {mult}")
        res += good
    return res


_SINGLET_CACHE: dict[tuple[int, ...], np.ndarray] = {}


def _corner_singlets(twos: tuple[int, ...]) -> np.ndarray:
    """Orthonormal basis (columns) of the singlet space of the tensor product of spins 2j = twos (standard bases)."""
    if twos in _SINGLET_CACHE:
        return _SINGLET_CACHE[twos]
    mats = [_spin_mats(t) for t in twos]
    dims = [t + 1 for t in twos]
    D = int(np.prod(dims))
    C = np.zeros((D, D), complex)
    for A in range(3):
        JA = np.zeros((D, D), complex)
        for i, mm in enumerate(mats):
            op = np.eye(1, dtype=complex)
            for k, d in enumerate(dims):
                op = np.kron(op, mm[A] if k == i else np.eye(d))
            JA += op
        C += JA @ JA
    w, V = np.linalg.eigh(C)
    S = V[:, w < 1e-9]
    if len(twos) == 4 and S.shape[1] != _singlets(list(twos)):
        raise RuntimeError("singlet space dimension disagrees with the triangle rule")
    _SINGLET_CACHE[twos] = S
    return S


def _build_state(choice: list[int], copies, far_m: list[int], rng: np.random.Generator, max_components: int):
    """One state from copy indices per link; None if a corner has no singlet or the state is too big."""
    # corner tensors
    supports = []   # per corner: (ends list, labels array (n, 4), coefficients (n,))
    est = 1
    for c in range(4):
        ends = CORNER_ENDS[c]
        twos = tuple(_near_far(copies[choice[l]][:2], r)[0] for l, r in ends)
        S = _corner_singlets(twos)
        if S.shape[1] == 0:
            return None
        coef = S @ (rng.normal(size=S.shape[1]) + 1j * rng.normal(size=S.shape[1]))
        coef /= np.linalg.norm(coef)
        nz = np.flatnonzero(np.abs(coef) > 1e-12)
        est *= len(nz)
        if est > max_components:
            return None
        dims = [t + 1 for t in twos]
        lab = np.array(np.unravel_index(nz, dims)).T      # (n, 4) of 'a' indices (m = j - a) at each end
        supports.append((ends, lab, coef[nz]))
    # configurations = cartesian product of corner supports
    idx = np.array(list(itertools.product(*[range(len(s[2])) for s in supports])), dtype=np.int64).reshape(-1, 4)
    amp_cfg = np.ones(len(idx), complex)
    a_of = np.zeros((len(idx), N_LINKS, 2), dtype=np.int64)    # (a for tail/j_L index, b for head/j_R index)
    for c, (ends, lab, coef) in enumerate(supports):
        amp_cfg *= coef[idx[:, c]]
        for e, (l, role) in enumerate(ends):
            col = 0 if role == "out" else 1
            a_of[:, l, col] = lab[idx[:, c], e]
    for l in OUTER:  # far end fixed at the chosen m
        role = _OUTER_NEAR[l][1]
        a_of[:, l, 1 if role == "out" else 0] = far_m[l]
    E = [_link_irrep_basis(*copies[choice[l]]) for l in range(N_LINKS)]
    allk, alla = [], []
    for ci in range(len(idx)):
        keys = np.zeros(1, np.int64)
        amps = np.array([amp_cfg[ci]])
        for l in range(N_LINKS):
            vec = E[l][a_of[ci, l, 0], a_of[ci, l, 1]]
            nz = np.flatnonzero(np.abs(vec) > 0)
            keys = (keys[:, None] | (nz[None, :].astype(np.int64) << (4 * l))).ravel()
            amps = (amps[:, None] * vec[nz][None, :]).ravel()
        allk.append(keys)
        alla.append(amps)
    keys, amps = _merge(np.concatenate(allk), np.concatenate(alla))
    keep = np.abs(amps) > 1e-13
    keys, amps = keys[keep], amps[keep]
    if len(keys) == 0 or len(keys) > max_components:
        return None
    amps = amps / np.linalg.norm(amps)
    return keys, amps


def sample_physical_states(n: int, seed: int, max_components: int = 4096, max_attempts: int = 20000) -> list[tuple[np.ndarray, np.ndarray]]:
    """n distinct unit-norm physical (Gauss-law) states as 48-bit COO vectors, deterministic in ``seed``.

    Each state: a random irrep copy per link (the copies are separated by the flavour F), a random unit combination of the
    corner singlets (route-A tensors from eigh on <= 81x81), a random magnetic quantum number for the free far end of every outer
    link; the product of the corner tensors with the standard irrep bases of the links is the state.  Draws whose support exceeds
    ``max_components`` are rejected."""
    copies = _resolve_copies()
    rng = np.random.default_rng(seed)
    out: list[tuple[np.ndarray, np.ndarray]] = []
    seen = set()
    for _ in range(max_attempts):
        if len(out) == n:
            break
        choice = [int(rng.integers(len(copies))) for _ in range(N_LINKS)]
        far_m = {}
        for l in OUTER:
            role = _OUTER_NEAR[l][1]
            c = copies[choice[l]]
            far_m[l] = int(rng.integers(_near_far(c[:2], role)[1] + 1))
        # corner dims must admit singlets (checked in _build_state)
        sub = np.random.default_rng(int(rng.integers(2 ** 62)))
        res = _build_state(choice, copies, far_m, sub, max_components)
        if res is None:
            continue
        keys, amps = res
        tag = (tuple(keys.tolist()), tuple(np.round(amps, 10).tolist()))
        if tag in seen:
            continue
        seen.add(tag)
        out.append((keys, amps))
    if len(out) < n:
        raise RuntimeError(f"could only generate {len(out)} of {n} physical states with <= {max_components} components")
    return out
