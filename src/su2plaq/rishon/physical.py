"""Rishon physical space: corner kernels, basis, counts, Gauss residuals (prompts/200 §2.2; METHODS-rishon R3).

Physical states are products of per-corner SU(2) singlet tensors over the 48-qubit occupation basis (sparse COO,
48-bit int64 keys: link l at qubits 4l..4l+3 = L1 L2 R1 R2).  No dense 6^12 or 2^48 object is ever built.
"""
from __future__ import annotations

import functools
import itertools
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

from su2plaq.geometry import Diagram, plaquette_diagram
from su2plaq.rishon.algebra import CODE_A, CODE_B, RishonLink

LINK_TYPES = ("A", "B", "Q")
N_QUBITS = 48
N_DATA = 16
N_OUTER = 32
_N_INNER_LINKS = 4
_TYPE_INDEX = {"A": 0, "B": 1, "Q": 2}
_KERNEL_EIG_TOL = 1e-9
_NZ_TOL = 1e-14


@functools.lru_cache(maxsize=None)
def _diagram() -> Diagram:
    return plaquette_diagram()


@functools.lru_cache(maxsize=None)
def _link() -> RishonLink:
    return RishonLink()


def _end_shift(role: str) -> int:
    """Offset of an end inside its link: 'out' = L end (qubits 0,1), 'in' = R end (qubits 2,3)."""
    if role not in ("out", "in"):
        raise ValueError(f"role must be 'out' or 'in', got {role!r}")
    return 0 if role == "out" else 2


def near_shift(link: int) -> int:
    """Qubit index of the first qubit of the link's near end (inner links: the L end)."""
    D = _diagram()
    if not 0 <= link < len(D.links):
        raise ValueError(f"link {link} out of range")
    near = D.links[link].near_end or "L"
    return 4 * link + (0 if near == "L" else 2)


def far_shift(link: int) -> int:
    """Qubit index of the first qubit of the link's far end (the other end of the link)."""
    D = _diagram()
    if not 0 <= link < len(D.links):
        raise ValueError(f"link {link} out of range")
    near = D.links[link].near_end or "L"
    return 4 * link + (2 if near == "L" else 0)


def _end_codes(t: str, role: str) -> list[int]:
    """Occupation codes (2 bits, bit 0 = colour 1) an end can take for a link of type t."""
    if t == "Q":
        return [1, 2]
    if t not in ("A", "B"):
        raise ValueError(f"unknown link type {t!r}")
    code = CODE_A if t == "A" else CODE_B
    return [(code >> _end_shift(role)) & 3]


def _gen_restricted(a: int, role: str, codes: list[int]) -> np.ndarray:
    M = _link().end_generator(a, "L" if role == "out" else "R")
    return M[np.ix_(codes, codes)]


def _embed_end(M: np.ndarray, e: int, dims: list[int]) -> np.ndarray:
    full = np.array([[1.0 + 0j]])
    for q, d in enumerate(dims):          # end 0 least significant
        full = np.kron(M if q == e else np.eye(d), full)
    return full


def _real_part(M: np.ndarray, what: str) -> np.ndarray:
    if np.abs(M.imag).max() > 1e-12:
        raise ValueError(f"{what} is not real")
    return M.real


def _fix_phase(v: np.ndarray) -> np.ndarray:
    mod = np.abs(v)
    first = int(np.flatnonzero(mod >= mod.max() - 1e-10)[0])
    return v if v[first] >= 0 else -v


@functools.lru_cache(maxsize=None)
def _corner_kernel_cached(types_roles: tuple):
    spaces = [_end_codes(t, r) for t, r in types_roles]
    dims = [len(s) for s in spaces]
    gens = []
    for e, (t, r) in enumerate(types_roles):
        gens.append([_embed_end(_gen_restricted(a, r, spaces[e]), e, dims) for a in range(3)])
    G = [sum(g[a] for g in gens) for a in range(3)]
    C = _real_part(sum(g @ g for g in G), "corner Casimir")
    w, v = np.linalg.eigh(C)
    K = v[:, w < _KERNEL_EIG_TOL]
    if K.shape[1] == 0:
        return spaces, K, ()
    # label by the spin J of the first two ends (its Casimir is diagonalised inside the kernel)
    G01 = [gens[0][a] + gens[1][a] for a in range(3)]
    C01 = _real_part(sum(g @ g for g in G01), "pair Casimir")
    x, V = np.linalg.eigh(K.T @ C01 @ K)
    K = K @ V
    J = (-1.0 + np.sqrt(1.0 + 4.0 * x)) / 2.0
    Jr = np.round(2.0 * J) / 2.0
    if np.abs(J - Jr).max() > 1e-8:
        raise ValueError("pair spin is not a half-integer on the corner kernel")
    K = np.stack([_fix_phase(K[:, i]) for i in range(K.shape[1])], axis=1)
    return spaces, K, tuple(float(j) for j in Jr)


def corner_kernel(types_roles: tuple[tuple[str, str], ...]):
    """Gauss kernel at one corner; types_roles = ((type, role),)*4 in Corner.ends order.

    Returns (end code lists, kernel vectors [D, k] real orthonormal (end 0 least significant), J labels of ends 0,1)."""
    spaces, K, J = _corner_kernel_cached(tuple((str(t), str(r)) for t, r in types_roles))
    return [list(s) for s in spaces], K.copy(), J


@functools.lru_cache(maxsize=None)
def _corner_coo(corner: int, types4: tuple):
    """Per kernel vector of corner `corner` with the given 4 end types: (keys, amps) over the corner's end bits."""
    ends = _diagram().corners[corner].ends
    spaces, K, J = _corner_kernel_cached(tuple((t, r) for t, (_, r) in zip(types4, ends)))
    dims = [len(s) for s in spaces]
    out = []
    for i in range(K.shape[1]):
        nz = np.flatnonzero(np.abs(K[:, i]) > _NZ_TOL)
        keys = np.zeros(len(nz), dtype=np.int64)
        stride = 1
        for e, ((link, role), sp_) in enumerate(zip(ends, spaces)):
            idx = (nz // stride) % dims[e]
            stride *= dims[e]
            codes = np.array(sp_, dtype=np.int64)[idx]
            keys |= codes << (4 * link + _end_shift(role))
        out.append((keys, K[nz, i].astype(np.complex128)))
    return out, J


# ------------------------------------------------------------------ type patterns (vectorised over 3^12)
_ALL_DIGITS = None


def _type_digits() -> np.ndarray:
    """[3^12, 12] int8 digits (0=A, 1=B, 2=Q); link 0 most significant (itertools.product order)."""
    global _ALL_DIGITS
    if _ALL_DIGITS is None:
        n = 3 ** 12
        idx = np.arange(n)
        d = np.zeros((n, 12), dtype=np.int8)
        for l in range(11, -1, -1):
            d[:, l] = idx % 3
            idx = idx // 3
        _ALL_DIGITS = d
    return _ALL_DIGITS


def _corner_index(digits: np.ndarray, corner: int) -> np.ndarray:
    ends = _diagram().corners[corner].ends
    idx = np.zeros(len(digits), dtype=np.int64)
    for link, _ in ends:
        idx = idx * 3 + digits[:, link]
    return idx


def _all_types4(corner: int):
    n = len(_diagram().corners[corner].ends)
    return list(itertools.product(LINK_TYPES, repeat=n))     # order matches _corner_index (first end most significant)


def _fuse(a: int, b: int) -> set[int]:
    """Spin fusion in units of 1/2 (2j): sets of 2J."""
    return set(range(abs(a - b), a + b + 1, 2))


def _n_singlets(twoj: tuple[int, ...]) -> int:
    """Number of SU(2) singlets in the product of spins 2j = twoj."""
    # sequential fusion with multiplicities
    mult = {0: 1}
    for j in twoj:
        new: dict[int, int] = {}
        for J, m in mult.items():
            for J2 in _fuse(J, j):
                new[J2] = new.get(J2, 0) + m
        mult = new
    return mult.get(0, 0)


def _fusion_tables():
    """Per corner: n_c and charge tables over the 3^4 type combos (first end most significant)."""
    D = _diagram()
    n_tab, q_tab = [], []
    for c in range(len(D.corners)):
        ends = D.corners[c].ends
        ns, qs = [], []
        for types4 in _all_types4(c):
            ns.append(_n_singlets(tuple(1 if t == "Q" else 0 for t in types4)))
            qs.append(sum(_occupation_count(t, r) for t, (_, r) in zip(types4, ends)))
        n_tab.append(np.array(ns, dtype=np.int64))
        q_tab.append(np.array(qs, dtype=np.int64))
    return n_tab, q_tab


def _occupation_count(t: str, role: str) -> int:
    if t == "Q":
        return 1
    return bin(_end_codes(t, role)[0]).count("1")


def count_by_fusion() -> dict:
    """Combinatorial counts (link types x SU(2) fusion at each corner); no state is built."""
    D = _diagram()
    digits = _type_digits()
    n_tab, q_tab = _fusion_tables()
    w = np.ones(len(digits), dtype=np.int64)
    Q = []
    for c in range(len(D.corners)):
        idx = _corner_index(digits, c)
        w = w * n_tab[c][idx]
        Q.append(q_tab[c][idx])
    Q = np.stack(Q, axis=1)
    live = w > 0
    outer = [l for l in D.outer_links()]
    closed_mask = np.all(digits[:, outer] != _TYPE_INDEX["Q"], axis=1)
    u2 = np.all(Q == 4, axis=1)
    return {
        "dim": int(w.sum()),
        "closed": int(w[closed_mask].sum()),
        "n_u1_sectors": int(len(np.unique(Q[live], axis=0))),
        "u2_sector": int(w[u2].sum()),
        "type_patterns": int(live.sum()),
    }


# ------------------------------------------------------------------ the basis
@dataclass
class RishonBasis:
    diagram: Diagram
    labels: list
    keys: list
    amps: list
    dim: int
    _charges: np.ndarray | None = field(default=None, repr=False)
    _index: dict | None = field(default=None, repr=False)

    def index(self, label) -> int:
        if self._index is None:
            self._index = {lab: i for i, lab in enumerate(self.labels)}
        types, js = label
        return self._index[(tuple(types), tuple(float(j) for j in js))]

    @staticmethod
    def inner_key(keys) -> np.ndarray:
        return np.asarray(keys, dtype=np.int64) & 0xFFFF

    @staticmethod
    def outer_key(keys) -> np.ndarray:
        return np.asarray(keys, dtype=np.int64) >> 16

    def u1_charges(self, k: int) -> tuple[int, int, int, int]:
        """Q_c = number of occupied end modes at corner c (all ends at the corner, outer near ends included)."""
        if self._charges is None:
            self._charges = _charges_of(self.diagram, self.keys)
        return tuple(int(x) for x in self._charges[k])


def _charges_of(D: Diagram, keys_list) -> np.ndarray:
    out = np.zeros((len(keys_list), len(D.corners)), dtype=np.int64)
    for k, keys in enumerate(keys_list):
        key = int(keys[0])
        for c, corner in enumerate(D.corners):
            out[k, c] = sum(bin((key >> (4 * l + _end_shift(r))) & 3).count("1") for l, r in corner.ends)
    return out


def _build_basis() -> RishonBasis:
    D = _diagram()
    digits = _type_digits()
    ncorner = len(D.corners)
    # corner kernel dimensions (from the qubit-representation kernels) decide which type patterns are live
    live = np.ones(len(digits), dtype=bool)
    for c in range(ncorner):
        tab = np.array([_corner_kernel_cached(tuple((t, r) for t, (_, r) in zip(types4, D.corners[c].ends)))[1].shape[1]
                        for types4 in _all_types4(c)], dtype=np.int64)
        live &= tab[_corner_index(digits, c)] > 0
    patterns = np.flatnonzero(live)
    # far-end spectator bits of the outer links per type
    far_bits = {}
    for l in D.outer_links():
        near = D.links[l].near_end
        far_role = "in" if near == "L" else "out"
        for t in LINK_TYPES:
            code = 1 if t == "Q" else _end_codes(t, far_role)[0]
            far_bits[(l, t)] = code << far_shift(l)
    labels, keys_list, amps_list = [], [], []
    for p in patterns:
        types = tuple(LINK_TYPES[int(d)] for d in digits[p])
        const = 0
        for l in D.outer_links():
            const |= far_bits[(l, types[l])]
        coo, Js = [], []
        for c in range(ncorner):
            data, J = _corner_coo(c, tuple(types[l] for l, _ in D.corners[c].ends))
            coo.append(data)
            Js.append(J)
        for combo in itertools.product(*[range(len(d)) for d in coo]):
            keys = np.array([const], dtype=np.int64)
            amps = np.ones(1, dtype=np.complex128)
            for c, ci in enumerate(combo):
                kc, ac = coo[c][ci]
                keys = (keys[:, None] | kc[None, :]).ravel()
                amps = (amps[:, None] * ac[None, :]).ravel()
            order = np.argsort(keys, kind="stable")
            keys_list.append(keys[order])
            amps_list.append(amps[order])
            labels.append((types, tuple(Js[c][ci] for c, ci in enumerate(combo))))
    return RishonBasis(diagram=D, labels=labels, keys=keys_list, amps=amps_list, dim=len(labels))


@functools.lru_cache(maxsize=1)
def rishon_basis() -> RishonBasis:
    """All physical states, built once from the corner kernels (cached)."""
    b = _build_basis()
    b._charges = _charges_of(b.diagram, b.keys)
    return b


def counts(basis) -> dict:
    """Same keys as count_by_fusion, taken from the built basis, plus coo_entries and max_components."""
    D = basis.diagram
    outer = D.outer_links()
    closed = sum(1 for lab in basis.labels if all(lab[0][l] != "Q" for l in outer))
    ch = np.array([basis.u1_charges(k) for k in range(basis.dim)], dtype=np.int64)
    return {
        "dim": int(basis.dim),
        "closed": int(closed),
        "n_u1_sectors": int(len(np.unique(ch, axis=0))),
        "u2_sector": int(np.sum(np.all(ch == 4, axis=1))),
        "type_patterns": int(len({lab[0] for lab in basis.labels})),
        "coo_entries": int(sum(len(k) for k in basis.keys)),
        "max_components": int(max(len(k) for k in basis.keys)),
    }


def _near_empty_type(link: int) -> str:
    """The singlet type of an outer link whose near end is empty."""
    near = _diagram().links[link].near_end
    role = "out" if near == "L" else "in"
    for t in ("A", "B"):
        if _end_codes(t, role)[0] == 0:
            return t
    raise ValueError("no near-empty singlet type")


def closed_indices(basis) -> list[int]:
    """The 17 closed reference states: outer links near-end-empty; vac_A, vac_B, loop, then the other 14 vacua."""
    D = basis.diagram
    outer_types = tuple(_near_empty_type(l) for l in D.outer_links())
    zero_j = (0.0,) * len(D.corners)

    def idx(inner):
        return basis.index((tuple(inner) + outer_types, zero_j))

    first = [idx("AABB"), idx("BBAA"), idx("QQQQ")]
    rest = [idx(t) for t in itertools.product("AB", repeat=_N_INNER_LINKS) if "".join(t) not in ("AABB", "BBAA")]
    return first + rest


def sample_indices(basis, n: int = 256, seed: int = 20261104) -> list[int]:
    """Seeded distinct physical-state indices, excluding the closed reference states (sorted)."""
    excl = set(closed_indices(basis))
    cand = np.array([k for k in range(basis.dim) if k not in excl], dtype=np.int64)
    if n > len(cand):
        raise ValueError("sample larger than the candidate set")
    rng = np.random.default_rng(seed)
    return sorted(int(x) for x in rng.choice(cand, size=n, replace=False))


# ------------------------------------------------------------------ Gauss residuals (2-qubit end operators)
def gauss_residuals_coo(keys_list, amps_list) -> np.ndarray:
    """Per state: max over corners c and a of ||G^a_c psi||, G^a_c = sum of the 2-qubit end generators (48-bit keys)."""
    D = _diagram()
    n = len(keys_list)
    res = np.zeros(n)
    rl = _link()
    mats = {(a, side): rl.end_generator(a, side) for a in range(3) for side in ("L", "R")}
    chunk = 1 << 15
    for lo in range(0, n, chunk):
        ks = keys_list[lo:lo + chunk]
        am = amps_list[lo:lo + chunk]
        m = len(ks)
        lens = np.array([len(k) for k in ks], dtype=np.int64)
        sid = np.repeat(np.arange(m, dtype=np.uint64), lens)
        key = np.concatenate([np.asarray(k, dtype=np.int64) for k in ks]) if m else np.zeros(0, np.int64)
        amp = np.concatenate([np.asarray(a, dtype=np.complex128) for a in am]) if m else np.zeros(0, np.complex128)
        best = np.zeros(m)
        for corner in D.corners:
            for a in range(3):
                oc, oa = [], []
                for link, role in corner.ends:
                    q0 = 4 * link + _end_shift(role)
                    M = mats[(a, "L" if role == "out" else "R")]
                    sub = (key >> q0) & 3
                    base = key & ~(np.int64(3) << q0)
                    for r in range(4):
                        coef = M[r][sub]
                        nz = np.abs(coef) > 1e-15
                        if nz.any():
                            oc.append((sid[nz] << np.uint64(48)) | (base[nz] | (np.int64(r) << q0)).astype(np.uint64))
                            oa.append(amp[nz] * coef[nz])
                if not oc:
                    continue
                comp = np.concatenate(oc)
                val = np.concatenate(oa)
                order = np.argsort(comp, kind="stable")
                comp, val = comp[order], val[order]
                starts = np.flatnonzero(np.concatenate(([True], comp[1:] != comp[:-1])))
                tot = np.add.reduceat(val, starts)
                state = (comp[starts] >> np.uint64(48)).astype(np.int64)
                sq = np.bincount(state, weights=np.abs(tot) ** 2, minlength=m)
                best = np.maximum(best, np.sqrt(sq))
        res[lo:lo + m] = best
    return res


def gauss_residual(keys, amps) -> float:
    return float(gauss_residuals_coo([np.asarray(keys, dtype=np.int64)], [np.asarray(amps, dtype=np.complex128)])[0])


# ------------------------------------------------------------------ inner span
def inner_span(basis) -> np.ndarray:
    """Orthonormal basis (1296, r) of the span of inner components over all states and outer patterns
    (rows indexed by the sorted valid inner codes)."""
    from su2plaq.rishon.operators import inner_codes

    codes = inner_codes()
    lens = np.array([len(k) for k in basis.keys], dtype=np.int64)
    sid = np.repeat(np.arange(basis.dim, dtype=np.uint64), lens)
    key = np.concatenate(basis.keys)
    amp = np.concatenate(basis.amps)
    inner = key & 0xFFFF
    outer = (key >> 16).astype(np.uint64)
    comp = (sid << np.uint64(32)) | outer
    _, col = np.unique(comp, return_inverse=True)
    rows = np.searchsorted(codes, inner)
    if np.any(rows >= len(codes)) or np.any(codes[np.minimum(rows, len(codes) - 1)] != inner):
        raise ValueError("a physical state has an inner component outside the valid code space")
    Z = sp.csr_matrix((amp, (rows, col)), shape=(len(codes), int(col.max()) + 1))
    G = (Z @ Z.conj().T).toarray()
    w, v = np.linalg.eigh((G + G.conj().T) / 2)
    keep = w > 1e-9 * w.max()
    return v[:, keep]


def inner_span_rank_by_corners() -> int:
    """Rank of the inner span by corner factorisation (no states built): sum over inner type patterns of the product
    over corners of the rank of the inner-end components of all kernel vectors (all outer types and outer end states)."""
    D = _diagram()
    nc = len(D.corners)
    total = 0
    for inner_t in itertools.product(LINK_TYPES, repeat=_N_INNER_LINKS):
        prod = 1
        for c in range(nc):
            ends = D.corners[c].ends
            in_pos = [e for e, (l, _) in enumerate(ends) if l < _N_INNER_LINKS]
            out_pos = [e for e, (l, _) in enumerate(ends) if l >= _N_INNER_LINKS]
            rows = []
            for outer_t in itertools.product(LINK_TYPES, repeat=len(out_pos)):
                types = [None] * len(ends)
                for e in in_pos:
                    types[e] = inner_t[ends[e][0]]
                for e, t in zip(out_pos, outer_t):
                    types[e] = t
                spaces, K, _ = _corner_kernel_cached(tuple((t, r) for t, (_, r) in zip(types, ends)))
                if K.shape[1] == 0:
                    continue
                dims = [len(s) for s in spaces]
                n_in = int(np.prod([dims[e] for e in in_pos]))
                for i in range(K.shape[1]):
                    T = K[:, i].reshape(dims[::-1])                    # axis (n-1-e) is end e
                    in_axes = [len(ends) - 1 - e for e in in_pos]
                    out_axes = [len(ends) - 1 - e for e in out_pos]
                    M = np.transpose(T, out_axes + in_axes).reshape(-1, n_in)
                    rows.extend(r for r in M if np.linalg.norm(r) > 1e-12)
            if not rows:
                prod = 0
                break
            prod *= int(np.linalg.matrix_rank(np.array(rows), tol=1e-9))
        total += prod
    return int(total)


def det_sector_structure(basis=None) -> dict:
    """Block structure of the 38 432-state physical space under the det term (METHODS-rishon R13; locked in M5-DT5).

    Matrices are formed at the code level on the union of the physical states' 48-bit codes and projected as P^dag T P: H_B from
    `operators.h_magnetic_inner` acting on the inner 16 bits (outer bits spectators), the det term of link l as the nibble flip
    A (3) <-> B (12) with amplitude 2.  Blocks = connected components of H_B (lam0), H_B + inner det (links 0-3), H_B + all 12 det
    terms.  -> {"dim", "u1_sectors", "blocks": {"lam0","inner_det","full_det"}, "max_block", "ref_block_dim", "ref_block_u1_sectors",
    "charge_change_rank": {...}, "leaving_weight"}; leaving_weight = largest weight that any det / H_B term sends out of the
    physical space, the squared Frobenius norm of the residual (1 - P P^dag) T P (about 1e-25: SU(2) Gauss law kept).  The residual has
    two parts that are summed: rows inside the union of the physical states' codes (X - P P^dag X) and the images T sends to a 48-bit code
    that is not one of those codes at all (the dropped images, formed as extra rows and counted by their squared amplitude, never
    discarded); reference state = closed_indices(basis)[0] (vac_A)."""
    from scipy.sparse.csgraph import connected_components

    from su2plaq.rishon import operators as _o

    b = rishon_basis() if basis is None else basis
    n = int(b.dim)
    lens = np.array([len(k) for k in b.keys])
    allk = np.concatenate([np.asarray(k, dtype=np.int64) for k in b.keys])
    alla = np.concatenate([np.asarray(a, dtype=np.complex128) for a in b.amps])
    uk, row = np.unique(allk, return_inverse=True)
    nu = len(uk)
    P = sp.csr_matrix((alla, (row, np.repeat(np.arange(n), lens))), shape=(nu, n))
    codes = _o.inner_codes()
    ipos = np.searchsorted(codes, uk & 0xFFFF)
    outer = uk >> 16
    M = sp.csc_matrix(_o.h_magnetic_inner())
    rr, cc, vv = [], [], []
    drop_t, drop_s, drop_v = [], [], []                  # images whose target code is not a code of any physical state
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
            rr.append(p[ok]); cc.append(src[ok]); vv.append(np.full(int(ok.sum()), val))
            drop_t.append(tgt[~ok]); drop_s.append(src[~ok]); drop_v.append(np.full(int((~ok).sum()), val))
    TB = sp.csr_matrix((np.concatenate(vv), (np.concatenate(rr), np.concatenate(cc))), shape=(nu, nu))
    DB = (np.concatenate(drop_t), np.concatenate(drop_s), np.concatenate(drop_v))

    def det_link(link: int):
        sh = 4 * link
        nib = (uk >> sh) & 15
        src = np.flatnonzero((nib == CODE_A) | (nib == CODE_B))
        tgt = uk[src] ^ (np.int64(15) << sh)             # A = 0b0011 <-> B = 0b1100: flip the whole nibble
        p = np.minimum(np.searchsorted(uk, tgt), nu - 1)
        ok = uk[p] == tgt
        return (sp.csr_matrix((np.full(int(ok.sum()), 2.0), (p[ok], src[ok])), shape=(nu, nu)),
                (tgt[~ok], src[~ok], np.full(int((~ok).sum()), 2.0)))

    def det_sum(links):
        parts = [det_link(l) for l in links]
        return sum(m for m, _ in parts[1:]) + parts[0][0], tuple(np.concatenate([d[i] for _, d in parts]) for i in range(3))

    leaving = [0.0]

    def phys(T, dropped):
        X = T @ P
        Mp = (P.conj().T @ X).tocsr()
        # weight leaving the physical space = ||(1 - P P^dag) T P||_F^2, summed entrywise from the residual (P has orthonormal columns);
        # not ||T P||^2 - ||P^dag T P||^2, a difference of two sums of size ~1e6 that only shows a rounding quantum (2^-32 ~ 2.3e-10)
        res = (X - P @ Mp).tocsr()
        # plus the images outside the code union (rows of T that were not formed above): orthogonal to the rows of X, so the weights add
        dt, ds, dv = dropped
        wdrop = 0.0
        if len(dt):
            ut, urow = np.unique(dt, return_inverse=True)
            Xd = (sp.csr_matrix((dv.astype(np.complex128), (urow, ds)), shape=(len(ut), nu)) @ P).tocsr()
            wdrop = float(np.sum(np.abs(Xd.data) ** 2))
        leaving[0] = max(leaving[0], float(np.sum(np.abs(res.data) ** 2)) + wdrop)
        Mp.data[np.abs(Mp.data) < 1e-12] = 0
        Mp.eliminate_zeros()
        return Mp

    HB = phys(TB, DB)
    Din = phys(*det_sum(range(0, 4)))
    Dout = phys(*det_sum(range(4, 12)))
    ch = np.array([b.u1_charges(k) for k in range(n)], dtype=np.int64)

    def comps(Mx):
        return connected_components((abs(Mx) > 1e-12).astype(np.int8), directed=False)

    def dq_rank(Ms):
        rows = set()
        for Mx in Ms:
            coo = Mx.tocoo()
            rows |= {tuple(int(y) for y in x) for x in (ch[coo.row] - ch[coo.col])}
        return int(np.linalg.matrix_rank(np.array(sorted(rows)))) if rows else 0

    names = ("lam0", "inner_det", "full_det")
    parts = [comps(HB), comps(HB + Din), comps(HB + Din + Dout)]
    k0 = closed_indices(b)[0]
    u1 = lambda mask: len({tuple(int(y) for y in x) for x in ch[mask]})
    return {"dim": n, "u1_sectors": u1(np.ones(n, dtype=bool)),
            "blocks": {nm: int(c) for nm, (c, _) in zip(names, parts)},
            "max_block": {nm: int(np.bincount(lab).max()) for nm, (_, lab) in zip(names, parts)},
            "ref_block_dim": {nm: int(np.sum(lab == lab[k0])) for nm, (_, lab) in zip(names, parts)},
            "ref_block_u1_sectors": {nm: u1(lab == lab[k0]) for nm, (_, lab) in zip(names, parts)},
            "charge_change_rank": {"lam0": dq_rank([HB]), "inner_det": dq_rank([HB, Din]), "full_det": dq_rank([HB, Din, Dout])},
            "leaving_weight": float(leaving[0]), "reference_state": int(k0)}
