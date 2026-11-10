"""Independent reference numerics for the M5 (rishon) acceptance tests (LOCKED, planner-owned).

Pure numpy/scipy; no project imports (independence of the production code).  Conventions = docs/METHODS-rishon.md R1-R4:
link qubits (L1, L2, R1, R2) = (4l, 4l+1, 4l+2, 4l+3), colour 1 = up, occupied = bit 1, little-endian,
c_k = (prod_{m<k} Z_m) sigma^-_k with sigma^- = |0><1|, U_ij = c_{L,i} c^dag_{R,j}, L_a = c_L^dag (sigma_a/2) c_L.
Geometry is hard-coded from docs/METHODS.md §1 (corner ends in Corner.ends order; 'out' = link starts at the corner = L end).
Numbers quoted in the tests come from reports/research/200 (prototype scratch/planner/proto_rishon.py).
"""
from __future__ import annotations

import itertools

import numpy as np
import scipy.sparse as sp
from scipy.linalg import expm

SIGMA = [np.array([[0, 1], [1, 0]], complex), np.array([[0, -1j], [1j, 0]]), np.array([[1, 0], [0, -1]], complex)]
T_SPIN = [s / 2 for s in SIGMA]
_I2 = np.eye(2)
_Z = SIGMA[2]
_SM = np.array([[0, 1], [0, 0]], complex)

# corner c -> ((link, role),)*4 ; role 'out' = link starts at the corner (L end), 'in' = ends there (R end)
CORNERS = (((0, "out"), (3, "out"), (4, "in"), (5, "in")),
           ((0, "in"), (1, "out"), (6, "out"), (7, "in")),
           ((1, "in"), (2, "in"), (8, "out"), (9, "out")),
           ((2, "out"), (3, "in"), (10, "in"), (11, "out")))
# near end of outer link k (4..11): 'L' if its role at its corner is 'out', else 'R'
NEAR = {link: ("L" if role == "out" else "R") for ends in CORNERS for link, role in ends if link >= 4}
CODE_A, CODE_B, CODES_Q = 3, 12, (5, 6, 9, 10)          # bits L1 L2 R1 R2
SECTOR = np.array([3, 5, 6, 9, 10, 12], dtype=np.int64)
TYPE_OF = {3: "A", 12: "B", 5: "Q", 6: "Q", 9: "Q", 10: "Q"}
N_PHYS, N_CLOSED, N_U2, N_U1_SECTORS = 38432, 4352, 2192, 431
SPECTRUM_HB = {-4 * np.sqrt(2): 1, -2.0: 48, -1.0: 32, 0.0: 1134, 1.0: 32, 2.0: 48, 4 * np.sqrt(2): 1}
KAPPA_MULTISET = {1.0: 32, 2.0: 48, 4 * np.sqrt(2): 1}
AMPLITUDE_ALPHABET = (1.0, 1 / np.sqrt(2), 0.5, 0.25)


def kron_all(ops):
    """Kronecker product with ops[0] on the least significant qubit."""
    out = np.array([[1.0 + 0j]])
    for o in ops:
        out = np.kron(o, out)
    return out


def jw_c(k: int, n: int) -> np.ndarray:
    return kron_all([_Z] * k + [_SM] + [_I2] * (n - k - 1))


class RefLink:
    """One link: 4 modes, 16x16 matrices."""

    def __init__(self):
        self.c = [jw_c(k, 4) for k in range(4)]
        self.cd = [m.conj().T for m in self.c]
        cL, cR, cLd, cRd = self.c[0:2], self.c[2:4], self.cd[0:2], self.cd[2:4]
        self.L = [sum(T_SPIN[a][i, j] * (cLd[i] @ cL[j]) for i in range(2) for j in range(2)) for a in range(3)]
        self.R = [sum(T_SPIN[a][i, j] * (cRd[i] @ cR[j]) for i in range(2) for j in range(2)) for a in range(3)]
        self.N = sum(self.cd[k] @ self.c[k] for k in range(4))
        self.T_bcw = sum(cRd[i] @ cR[i] - cLd[i] @ cL[i] for i in range(2))
        self.det_U = self.U(0, 0) @ self.U(1, 1) - self.U(0, 1) @ self.U(1, 0)

    def U(self, i, j):
        return self.c[i] @ self.cd[2 + j]

    def end_op(self, a: int, role: str) -> np.ndarray:
        """4x4 generator on the two qubits of one end: 'out' -> L end (qubits 0,1), 'in' -> R end (qubits 2,3)."""
        M = self.L[a] if role == "out" else self.R[a]
        idx = list(range(4)) if role == "out" else [b << 2 for b in range(4)]
        return M[np.ix_(idx, idx)]


_LINK = None


def link() -> RefLink:
    global _LINK
    if _LINK is None:
        _LINK = RefLink()
    return _LINK


def embed(M16: np.ndarray, l: int, n_links: int) -> sp.csr_matrix:
    out = sp.identity(1, format="csr", dtype=complex)
    for q in range(n_links):
        out = sp.kron(sp.csr_matrix(M16) if q == l else sp.identity(16, format="csr"), out, format="csr")
    return out


def inner_codes() -> np.ndarray:
    codes = np.array([sum(int(s) << (4 * l) for l, s in enumerate(cfg)) for cfg in itertools.product(SECTOR, repeat=4)], dtype=np.int64)
    return np.sort(codes)


def types_of(code: int) -> tuple[str, ...]:
    return tuple(TYPE_OF[(int(code) >> (4 * l)) & 15] for l in range(4))


_W = None


def W_inner() -> np.ndarray:
    """Tr(U_b U_r U_t^dag U_l^dag) on the 1296 inner codes (real)."""
    global _W
    if _W is None:
        lk = link()
        W = sp.csr_matrix((16 ** 4, 16 ** 4), dtype=complex)
        for a, b, c, d in itertools.product(range(2), repeat=4):
            W = W + embed(lk.U(a, b), 0, 4) @ embed(lk.U(b, c), 1, 4) @ embed(lk.U(d, c).conj().T, 2, 4) @ embed(lk.U(a, d).conj().T, 3, 4)
        codes = inner_codes()
        _W = W[codes][:, codes].toarray()
    return _W


def HE_inner() -> np.ndarray:
    return np.array([0.75 * sum(t == "Q" for t in types_of(c)) for c in inner_codes()])


def gauss_inner(corner: int, a: int) -> np.ndarray:
    lk = link()
    G = sp.csr_matrix((16 ** 4, 16 ** 4), dtype=complex)
    for l, role in CORNERS[corner]:
        if l < 4:
            G = G + embed(lk.L[a] if role == "out" else lk.R[a], l, 4)
    codes = inner_codes()
    return G[codes][:, codes].toarray()


# ------------------------------------------------------------------ counts (route 1: types x fusion; independent of states)
def _fuse(a, b):
    return {(0, 0): {0}, (0, 1): {1}, (1, 0): {1}, (1, 1): {0, 2}}[(a, b)]


def n_corner(js) -> int:
    return len(_fuse(js[0], js[1]) & _fuse(js[2], js[3]))


def fusion_counts() -> dict:
    """{'dim', 'closed', 'u2_sector', 'n_u1_sectors', 'type_patterns'} by enumerating link types in {A,B,Q}^12."""
    tot = closed = u2 = pats = 0
    sectors = set()
    occ_out = {"A": 2, "B": 0, "Q": 1}
    occ_in = {"A": 0, "B": 2, "Q": 1}
    for tps in itertools.product("ABQ", repeat=12):
        js = [1 if t == "Q" else 0 for t in tps]
        w = 1
        Qs = []
        for ends in CORNERS:
            w *= n_corner([js[i] for i, _ in ends])
            if w == 0:
                break
            Qs.append(sum(occ_out[tps[i]] if r == "out" else occ_in[tps[i]] for i, r in ends))
        if w == 0:
            continue
        tot += w
        pats += 1
        sectors.add(tuple(Qs))
        if all(q == 4 for q in Qs):
            u2 += w
        if all(t != "Q" for t in tps[4:]):
            closed += w
    return {"dim": tot, "closed": closed, "u2_sector": u2, "n_u1_sectors": len(sectors), "type_patterns": pats}


def ks_weighted_count(labels) -> tuple[int, int]:
    """Route 2: KS labels ((j_0..j_11), (J_0..J_3)) weighted by 2^{#j=0}; returns (total, closed)."""
    tot = closed = 0
    for js, _ in labels:
        w = 2 ** sum(1 for j in js if j == 0.0)
        tot += w
        if all(j == 0.0 for j in js[4:]):
            closed += w
    return tot, closed


# ------------------------------------------------------------------ Gauss on 48-bit COO states (2-qubit end operators)
def _apply_2q(keys, amps, q0, M4):
    sub = (keys >> q0) & 3
    outk, outa = [], []
    for r in range(4):
        col = M4[r, sub]
        nz = np.abs(col) > 1e-15
        if nz.any():
            outk.append((keys[nz] & ~(np.int64(3) << q0)) | (np.int64(r) << q0))
            outa.append(amps[nz] * col[nz])
    if not outk:
        return np.zeros(0, np.int64), np.zeros(0, complex)
    k = np.concatenate(outk)
    a = np.concatenate(outa)
    uk, inv = np.unique(k, return_inverse=True)
    ua = np.zeros(len(uk), complex)
    np.add.at(ua, inv, a)
    return uk, ua


def gauss_residual(keys: np.ndarray, amps: np.ndarray) -> float:
    """max over corners c and a of || G^a_c psi || for a 48-bit COO state."""
    lk = link()
    keys = np.asarray(keys, dtype=np.int64)
    amps = np.asarray(amps, dtype=complex)
    worst = 0.0
    for ends in CORNERS:
        for a in range(3):
            ks, vs = [], []
            for l, role in ends:
                q0 = 4 * l + (0 if role == "out" else 2)
                k2, a2 = _apply_2q(keys, amps, q0, lk.end_op(a, role))
                ks.append(k2)
                vs.append(a2)
            k = np.concatenate(ks)
            v = np.concatenate(vs)
            if len(k) == 0:
                continue
            uk, inv = np.unique(k, return_inverse=True)
            ua = np.zeros(len(uk), complex)
            np.add.at(ua, inv, v)
            worst = max(worst, float(np.linalg.norm(ua)))
    return worst


def valid_code(code: int) -> bool:
    """48-bit code: every link has two rishons; outer far ends fixed (A/B determined, Q far colour 1)."""
    code = int(code)
    for l in range(12):
        s = (code >> (4 * l)) & 15
        if s not in TYPE_OF:
            return False
        if l >= 4:
            far = (s >> 2) & 3 if NEAR[l] == "L" else s & 3
            t = TYPE_OF[s]
            if t == "Q" and far != 0b01:
                return False
    return True


def vac_codes() -> tuple[int, int]:
    """Inner codes of vac_A (types A A B B) and vac_B (B B A A)."""
    va = CODE_A | (CODE_A << 4) | (CODE_B << 8) | (CODE_B << 12)
    vb = CODE_B | (CODE_B << 4) | (CODE_A << 8) | (CODE_A << 12)
    return va, vb


def outer_near_empty_code() -> int:
    """Outer part (bits 16..47) with every outer link in its near-end-empty singlet (far end full)."""
    out = 0
    for l in range(4, 12):
        s = CODE_B if NEAR[l] == "L" else CODE_A    # near L empty -> both at R = B ; near R empty -> A
        out |= s << (4 * l)
    return out


# ------------------------------------------------------------------ closed blocks and shared observables
def rishon_closed_block(g2: float) -> np.ndarray:
    adj = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], float)
    return 0.5 * g2 * np.diag([0.0, 3.0, 0.0]) - (4.0 / g2) * adj


def ks_closed_block(g2: float) -> np.ndarray:
    return np.array([[0.0, -2.0 / g2], [-2.0 / g2, 1.5 * g2]])


def closed_eigs(g2: float) -> tuple[np.ndarray, np.ndarray]:
    """(rishon {0, 3g2/4 ± sqrt(9g2^2/16 + 32/g2^2)}, KS {3g2/4 ± sqrt(9g2^2/16 + 4/g2^2)}) sorted."""
    s = 0.75 * g2
    r = np.sort(np.array([0.0, s - np.sqrt(s * s + 32 / g2 ** 2), s + np.sqrt(s * s + 32 / g2 ** 2)]))
    k = np.sort(np.array([s - np.sqrt(s * s + 4 / g2 ** 2), s + np.sqrt(s * s + 4 / g2 ** 2)]))
    return r, k


def _step(HE, HB, alpha, beta, order):
    UE = lambda a: expm(-1j * a * HE)
    UB = expm(-1j * beta * HB)
    return UB @ UE(alpha) if order == 1 else UE(alpha / 2) @ UB @ UE(alpha / 2)


def observables_closed(alpha: float, beta: float, n: int, order: int = 1) -> dict:
    """{'rishon': {'E_link','P','echo'}, 'ks': {...}} after n first-order steps from the vacuum (closed blocks)."""
    HEr, HBr = np.diag([0.0, 3.0, 0.0]), -4.0 * np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], float)
    HEk, HBk = np.diag([0.0, 3.0]), -2.0 * np.array([[0, 1], [1, 0]], float)
    out = {}
    for name, HE, HB in (("rishon", HEr, HBr), ("ks", HEk, HBk)):
        U = np.linalg.matrix_power(_step(HE, HB, alpha, beta, order), n)
        psi = U[:, 0]
        out[name] = {"E_link": float(np.real(np.vdot(psi, HE @ psi))) / 4.0,
                     "P": float(np.real(np.vdot(psi, (-0.5 * HB) @ psi))),
                     "echo": float(abs(psi[0]) ** 2)}
    return out


def closed_forms(alpha: float, beta: float) -> dict:
    tk, tr = 2 * beta, 4 * np.sqrt(2) * beta
    return {"rishon": {"E_link": 0.375 * np.sin(tr) ** 2, "P": 0.0, "echo": 0.25 * (1 + np.cos(tr)) ** 2},
            "ks": {"E_link": 0.75 * np.sin(tk) ** 2, "P": 0.0, "echo": np.cos(tk) ** 2}}


ANGLES = ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00))
