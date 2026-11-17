"""Limits between different models (prompts/009 §3.3, §3.4, §5.3; docs/METHODS.md §13.3, §13.4).  Not in any hash list.

Rishon: levels of c_E H_E + c_B H_B + lam_D H_D on the 38 432 physical states (split into connected components, dense eigvalsh per
block) and on the 17 closed inner states; the KS limit lam_D = -L, c_E = g2/2 - 8L/3, c_B = 1/g2 (our derivation, METHODS §13.3).
Fuzzy: the 50-state isolated plaquette and the flavour blocks of the K1-only model (METHODS §13.4).
"""
from __future__ import annotations

import functools

import numpy as np


# ------------------------------------------------------------------------------------------------ rishon
def rishon_closed_block(c_e, c_b, lam_d) -> np.ndarray:
    """17 x 17 Hermitian closed inner block of c_e H_E + c_b H_B + lam_d H_D^in (16 electric vacua {A,B}^4 and the loop state).
    operators.closed_block_full(g2, lam) = (g2/2) H_E + H_B/g2 + lam H_D, so three evaluations give the three operators."""
    from su2plaq.rishon import operators as O

    f1 = O.closed_block_full(1.0, 0.0)          # H_E/2 + H_B
    f2 = O.closed_block_full(2.0, 0.0)          # H_E + H_B/2
    HB = (4.0 * f1 - 2.0 * f2) / 3.0
    HE = (4.0 * f2 - 2.0 * f1) / 3.0
    HD = O.closed_block_full(1.0, 1.0) - f1
    return c_e * HE + c_b * HB + lam_d * HD


@functools.lru_cache(maxsize=1)
def _rishon_phys_ops():
    """(HE, HB, HD, labels): real sparse operators on the 38 432 physical states (H_D on all 12 links) and the labels of the
    connected components of |H_B| + |H_D|.  Code-level operators are projected with P^dag T P as in rishon.physical.det_sector_structure;
    a det term is the nibble flip A <-> B with amplitude 2; H_E = 3/4 x (number of quartet links)."""
    import scipy.sparse as sp
    from scipy.sparse.csgraph import connected_components

    from su2plaq.rishon import operators as rops
    from su2plaq.rishon import physical as rphys
    from su2plaq.rishon.algebra import CODE_A, CODE_B, CODES_Q

    b = rphys.rishon_basis()
    n = int(b.dim)
    lens = np.array([len(k) for k in b.keys])
    allk = np.concatenate([np.asarray(k, dtype=np.int64) for k in b.keys])
    alla = np.concatenate([np.asarray(a, dtype=np.complex128) for a in b.amps])
    uk, row = np.unique(allk, return_inverse=True)
    nu = len(uk)
    P = sp.csr_matrix((alla, (row, np.repeat(np.arange(n), lens))), shape=(nu, n))
    codes = rops.inner_codes()
    ipos = np.searchsorted(codes, uk & 0xFFFF)
    outer = uk >> 16
    M = sp.csc_matrix(rops.h_magnetic_inner())
    rr, cc, vv = [], [], []
    for i in range(len(codes)):
        src = np.flatnonzero(ipos == i)
        if not len(src):
            continue
        for j, val in zip(M.indices[M.indptr[i]:M.indptr[i + 1]], M.data[M.indptr[i]:M.indptr[i + 1]]):
            if abs(val) < 1e-14:
                continue
            tgt = (outer[src] << 16) | codes[j]
            p = np.minimum(np.searchsorted(uk, tgt), nu - 1)
            ok = uk[p] == tgt
            rr.append(p[ok])
            cc.append(src[ok])
            vv.append(np.full(int(ok.sum()), val))
    TB = sp.csr_matrix((np.concatenate(vv), (np.concatenate(rr), np.concatenate(cc))), shape=(nu, nu))

    def det_link(link):
        sh = 4 * link
        nib = (uk >> sh) & 15
        src = np.flatnonzero((nib == CODE_A) | (nib == CODE_B))
        tgt = uk[src] ^ (np.int64(15) << sh)
        p = np.minimum(np.searchsorted(uk, tgt), nu - 1)
        ok = uk[p] == tgt
        return sp.csr_matrix((np.full(int(ok.sum()), 2.0), (p[ok], src[ok])), shape=(nu, nu))

    def phys(T):
        Mp = (P.conj().T @ (T @ P)).tocsr()
        if abs(Mp.imag).max() > 1e-12:
            raise RuntimeError("physical operator is not real")
        Mp = Mp.real.tocsr()
        Mp.data[np.abs(Mp.data) < 1e-12] = 0
        Mp.eliminate_zeros()
        return Mp

    nq = np.zeros(nu)
    for link in range(12):
        nq += np.isin((uk >> (4 * link)) & 15, np.array(CODES_Q))
    HE, HB, HD = phys(sp.diags(0.75 * nq)), phys(TB), phys(sum(det_link(link) for link in range(12)))
    _, lab = connected_components((abs(HB) + abs(HD) > 1e-12).astype(np.int8), directed=False)
    return HE, HB, HD, lab


def rishon_block_sizes() -> np.ndarray:
    """Sizes of the connected components of |H_B| + |H_D| on the 38 432 physical states (305 blocks, largest 4352)."""
    return np.bincount(_rishon_phys_ops()[3])


def rishon_levels(c_e, c_b, lam_d, k=None) -> np.ndarray:
    """Sorted levels of c_e H_E + c_b H_B + lam_d H_D (12 links) on the 38 432 physical states; the k lowest if k is given."""
    HE, HB, HD, lab = _rishon_phys_ops()
    H = (c_e * HE + c_b * HB + lam_d * HD).tocsr()
    ev = []
    for c in range(int(lab.max()) + 1):
        idx = np.flatnonzero(lab == c)
        ev.append(np.linalg.eigvalsh(H[idx][:, idx].toarray()))
    ev = np.sort(np.concatenate(ev))
    return ev if k is None else ev[:k]


def rishon_ks_limit(g2, L) -> dict:
    """{"g2", "L", "levels": 433 lowest of rishon_levels(g2/2 - 8L/3, 1/g2, -L) + 24 L, "ks_levels": 433 KS levels (outer electric
    included), "max_dev", "gap_to_next_band": level 434 - level 433}."""
    from su2plaq.exact.operators import hamiltonian_phys
    from su2plaq.exact.physical import physical_basis

    ev = rishon_levels(g2 / 2 - 8 * L / 3, 1 / g2, -L, k=434) + 24 * L
    ks = np.sort(np.linalg.eigvalsh(hamiltonian_phys(physical_basis(convention="cg"), g2, include_outer_electric=True)))
    return {"g2": float(g2), "L": float(L), "levels": ev[:433], "ks_levels": ks, "max_dev": float(np.abs(ev[:433] - ks).max()),
            "gap_to_next_band": float(ev[433] - ev[432])}


# ------------------------------------------------------------------------------------------------ fuzzy
def isolated_plaquette_basis():
    """Orthonormal basis (50, 65536) of the Gauss kernel of the four inner links alone (outer links removed: every corner is
    2-valent), index sum_l nib_l 16^l.  Exact reduction: corners 0 and 2 involve the disjoint link pairs (0,3) and (1,2); their
    pair kernels N_a, N_b (256 x d) span a space of dimension d_a d_b in which corners 1 and 3 are small matrices built from the
    pair-level matrices N^dag T N (cross terms factorise, same-link terms use N^dag T T N)."""
    from su2plaq.fuzzy import gauss as gz
    from su2plaq.fuzzy import link as lk

    def T_of(A, role):
        return lk.calT_L(A) if role == "out" else lk.calT_R(A)

    def inner_ends(c):
        return [(l, r) for l, r in gz.CORNER_ENDS[c] if l < 4]

    pairs = {}
    for c in (0, 2):
        (la, ra), (lb, rb) = inner_ends(c)
        H = np.zeros((256, 256), dtype=np.complex128)
        for A in range(3):
            G = np.kron(T_of(A, ra), np.eye(16)) + np.kron(np.eye(16), T_of(A, rb))
            H += G.conj().T @ G
        w, V = np.linalg.eigh(H)
        pairs[c] = ((la, lb), V[:, w < 1e-9])
    (la, lb), Na = pairs[0]
    (lc, ld), Nb = pairs[2]
    da, db = Na.shape[1], Nb.shape[1]
    where = {}                                              # link -> (pair index, position in pair)
    for pi, (l1, l2) in enumerate(((la, lb), (lc, ld))):
        where[l1], where[l2] = (pi, 0), (pi, 1)
    Ns = (Na, Nb)

    def one(l, X):
        """N^dag (X on link l) N on the pair containing l (d x d)."""
        pi, pos = where[l]
        M = np.kron(X, np.eye(16)) if pos == 0 else np.kron(np.eye(16), X)
        return pi, Ns[pi].conj().T @ M @ Ns[pi]

    def embed(pi, M):
        return np.kron(M, np.eye(db)) if pi == 0 else np.kron(np.eye(da), M)

    Hred = np.zeros((da * db, da * db), dtype=np.complex128)
    for c in (1, 3):
        ends = inner_ends(c)
        for A in range(3):
            for i, (l1, r1) in enumerate(ends):
                for j, (l2, r2) in enumerate(ends):
                    T1, T2 = T_of(A, r1), T_of(A, r2)
                    if l1 == l2:
                        pi, M = one(l1, T1 @ T2)
                        Hred += embed(pi, M)
                    else:
                        p1, M1 = one(l1, T1)
                        p2, M2 = one(l2, T2)
                        assert p1 != p2
                        Hred += np.kron(M1, M2) if p1 == 0 else np.kron(M2, M1)
    w, V = np.linalg.eigh(0.5 * (Hred + Hred.conj().T))
    Z = V[:, w < 1e-9]
    letters = {0: "p", 1: "q", 2: "r", 3: "s"}              # tensor axes (link3, link2, link1, link0) = (s, r, q, p)
    # basis vector n = sum_{ab} Z[(a,b), n] N_a[(x,y), a] N_b[(z,w), b]
    Zt = Z.T.reshape(-1, da, db)
    Xa = Na.reshape(16, 16, da)
    Xb = Nb.reshape(16, 16, db)
    vecs = np.einsum(f"{letters[la]}{letters[lb]}a,{letters[lc]}{letters[ld]}b,nab->nsrqp", Xa, Xb, Zt).reshape(Z.shape[1], 65536)
    return vecs, w


def _kin(M16, v):
    """sum over the four links of M16 acting on the link axis of v (16, 16, 16, 16)."""
    out = np.zeros_like(v)
    for ax in range(4):
        out += np.moveaxis(np.tensordot(M16, v, axes=([1], [ax])), 0, ax)
    return out


def _square(W, v):
    """The plaquette row W (256 x 256, plaquette_row) applied to v (16, 16, 16, 16): link pairs (a_l, b_l) of the four links."""
    t = v.reshape(4, 4, 4, 4, 4, 4, 4, 4).transpose(0, 2, 4, 6, 1, 3, 5, 7).reshape(256, 256)
    t = (W @ t).reshape(4, 4, 4, 4, 4, 4, 4, 4)
    return t.transpose(0, 4, 1, 5, 2, 6, 3, 7).reshape(16, 16, 16, 16)


def _herm(A):
    return 0.5 * (A + A.conj().T)


@functools.lru_cache(maxsize=1)
def _fuzzy_isolated_blocks():
    """(sum K1, sum K2, square) projected on the 50 Gauss-law states of the isolated plaquette."""
    from su2plaq.fuzzy import link as fz
    from su2plaq.fuzzy.plaquette import plaquette_row

    vecs, _w = isolated_plaquette_basis()
    B = np.asarray(vecs).T
    K1, K2, W = fz.K1(), fz.K2(), plaquette_row()

    def project(g):
        return _herm(np.array([B.conj().T @ g(B[:, j].reshape(16, 16, 16, 16)).reshape(-1) for j in range(B.shape[1])]).T)

    return project(lambda v: _kin(K1, v)), project(lambda v: _kin(K2, v)), project(lambda v: _square(W, v))


def fuzzy_isolated_levels(g2, a=1.0, b=1.0) -> np.ndarray:
    """50 sorted levels of (g2/4) sum_l (a K1 + b K2) - (2/g2) square on the Gauss-law states of the isolated plaquette.
    Computed as (2/g2) eig(-square + (g2^2/8)(a K1 + b K2)): keeps the tiny weak-coupling gap accurate."""
    K1p, K2p, Sp = _fuzzy_isolated_blocks()
    return (2.0 / g2) * np.linalg.eigvalsh(_herm(-Sp + (g2 ** 2 / 8.0) * (a * K1p + b * K2p)))


@functools.lru_cache(maxsize=None)
def _flavour_blocks(signs):
    from su2plaq.fuzzy import link as fz
    from su2plaq.fuzzy.plaquette import plaquette_row

    K1, W = fz.K1(), plaquette_row()
    G5 = np.diag([1.0, 1.0, -1.0, -1.0])
    links = [((np.eye(4) + s * G5) / (2 * np.sqrt(2))).reshape(16) for s in signs]        # (b, r, t, l)
    v0 = np.einsum("a,b,c,d->abcd", links[3], links[2], links[1], links[0]).reshape(-1).astype(np.complex128)   # link b least significant
    gens = [lambda v: _kin(K1, v), lambda v: _square(W, v)]
    basis = [v0]
    i = 0
    while i < len(basis):
        for g in gens:
            w = g(basis[i].reshape(16, 16, 16, 16)).reshape(-1)
            for _ in range(2):
                for bb in basis:
                    w = w - np.vdot(bb, w) * bb
            nrm = np.linalg.norm(w)
            if nrm > 1e-9:
                basis.append(w / nrm)
        i += 1
    V = np.array(basis).T

    def project(g):
        return _herm(np.array([V.conj().T @ g(V[:, j].reshape(16, 16, 16, 16)).reshape(-1) for j in range(V.shape[1])]).T)

    return project(gens[0]), project(gens[1])


def fuzzy_flavour_block(g2, signs) -> np.ndarray:
    """(g2/4) sum K1 - (2/g2) square on the cyclic subspace of the flavour vacuum, signs = (F_b, F_r, F_t, F_l) in +-1; basis vector 0
    is that vacuum (vacuum = tensor product over links of (1 + F Gamma_5)/(2 sqrt 2), row-major 16-vectors)."""
    signs = tuple(int(s) for s in signs)
    if len(signs) != 4 or any(s not in (1, -1) for s in signs):
        raise ValueError(f"signs must be four values +-1, got {signs}")
    k1, sq = _flavour_blocks(signs)
    return 0.25 * g2 * k1 - (2.0 / g2) * sq
