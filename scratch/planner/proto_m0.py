"""Planner prototype (kickoff, 2026-11-04): checks every physics fact that the M0 acceptance
tests will lock, with an independent implementation (no import of refs/su2_plaquette_encodings.py).

Route A : electric basis |j mL mR> per link (CG conventions of su2qc-skqd), corner singlets
          = kernel of sum_a (sum_ends G_a)^2, labelled by the inner-pair spin J.
Route B : spin-network labels (j_1..12, J_1..4) on the (inner|outer) point-split graph, plaquette
          = product over the 4 inner trivalent sites of recoupling F-symbols (Zache et al. Eq. 2).

Run:  python scratch/planner/proto_m0.py
"""
from __future__ import annotations
import itertools, functools, math, sys, time
import numpy as np

np.set_printoptions(linewidth=160, precision=6, suppress=True)

# ----------------------------------------------------------------------------- SU(2) basics
def spin_matrices(j):
    d = int(round(2 * j + 1)); m = np.array([j - k for k in range(d)])
    Jz = np.diag(m).astype(complex); Jp = np.zeros((d, d), complex)
    for k in range(1, d):
        mm = m[k]; Jp[k - 1, k] = math.sqrt(j * (j + 1) - mm * (mm + 1))
    Jm = Jp.conj().T
    return [(Jp + Jm) / 2, (Jp - Jm) / 2j, Jz]

def m_values(j):
    return [j - k for k in range(int(round(2 * j + 1)))]

@functools.lru_cache(None)
def cg(j1, m1, j2, m2, J, M):
    """Clebsch-Gordan <j1 m1 j2 m2|J M>, Condon-Shortley, Racah formula (args as 2x ints)."""
    j1, m1, j2, m2, J, M = [x / 2 for x in (j1, m1, j2, m2, J, M)]
    if abs(m1 + m2 - M) > 1e-9 or J < abs(j1 - j2) - 1e-9 or J > j1 + j2 + 1e-9:
        return 0.0
    if abs(m1) > j1 + 1e-9 or abs(m2) > j2 + 1e-9 or abs(M) > J + 1e-9:
        return 0.0
    f = lambda x: math.factorial(int(round(x)))
    pref = math.sqrt((2 * J + 1) * f(J + j1 - j2) * f(J - j1 + j2) * f(j1 + j2 - J) / f(j1 + j2 + J + 1))
    pref *= math.sqrt(f(J + M) * f(J - M) * f(j1 - m1) * f(j1 + m1) * f(j2 - m2) * f(j2 + m2))
    s = 0.0
    kmin = int(round(max(0, j2 - J - m1, j1 - J + m2))); kmax = int(round(min(j1 + j2 - J, j1 - m1, j2 + m2)))
    for k in range(kmin, kmax + 1):
        s += (-1) ** k / (f(k) * f(j1 + j2 - J - k) * f(j1 - m1 - k) * f(j2 + m2 - k) * f(J - j2 + m1 + k) * f(J - j1 - m2 + k))
    return pref * s

def CG(j1, m1, j2, m2, J, M):
    return cg(*[int(round(2 * x)) for x in (j1, m1, j2, m2, J, M)])

@functools.lru_cache(None)
def six_j(a, b, c, d, e, f):
    """Wigner 6j {a b c; d e f}, Racah formula (args as 2x ints)."""
    a, b, c, d, e, f = [x / 2 for x in (a, b, c, d, e, f)]
    def tri(x, y, z):
        if z < abs(x - y) - 1e-9 or z > x + y + 1e-9 or abs(round(2 * (x + y + z)) % 2):
            return None
        F = lambda q: math.factorial(int(round(q)))
        return F(x + y - z) * F(x - y + z) * F(-x + y + z) / F(x + y + z + 1)
    ts = [tri(a, b, c), tri(a, e, f), tri(d, b, f), tri(d, e, c)]
    if any(t is None for t in ts):
        return 0.0
    F = lambda q: math.factorial(int(round(q)))
    pref = math.sqrt(np.prod(ts))
    s = 0.0
    zmin = int(round(max(a + b + c, a + e + f, d + b + f, d + e + c)))
    zmax = int(round(min(a + b + d + e, a + c + d + f, b + c + e + f)))
    for z in range(zmin, zmax + 1):
        s += (-1) ** z * F(z + 1) / (F(z - a - b - c) * F(z - a - e - f) * F(z - d - b - f) * F(z - d - e - c)
                                      * F(a + b + d + e - z) * F(a + c + d + f - z) * F(b + c + e + f - z))
    return pref * s

def SIXJ(*args):
    return six_j(*[int(round(2 * x)) for x in args])

def F_recoupling(j1, j2, j12, j3, J, j23):
    """<(j1 j2) j12, j3; J | j1, (j2 j3) j23; J> = (-1)^{j1+j2+j3+J} sqrt((2j12+1)(2j23+1)) {j1 j2 j12; j3 J j23}
    (Edmonds 6.1.5 / Varshalovich 8.1(2))."""
    return (-1) ** int(round(j1 + j2 + j3 + J)) * math.sqrt((2 * j12 + 1) * (2 * j23 + 1)) * SIXJ(j1, j2, j12, j3, J, j23)

# ----------------------------------------------------------------------------- link space (skqd conventions)
class LinkSpace:
    def __init__(self, jmax=0.5):
        self.spins = [k / 2 for k in range(int(round(2 * jmax)) + 1)]
        self.states = [(j, mL, mR) for j in self.spins for mL in m_values(j) for mR in m_values(j)]
        self.index = {s: k for k, s in enumerate(self.states)}
        self.dim = len(self.states)
        d = self.dim; col = [0.5, -0.5]
        self.U = [[np.zeros((d, d), complex) for _ in range(2)] for _ in range(2)]
        for (j, mL, mR), k in self.index.items():
            for jp in self.spins:
                if abs(jp - j) != 0.5:
                    continue
                for a, i_col in enumerate(col):
                    for b, j_col in enumerate(col):
                        mLp, mRp = mL + i_col, mR + j_col
                        if abs(mLp) > jp + 1e-9 or abs(mRp) > jp + 1e-9:
                            continue
                        val = math.sqrt((2 * j + 1) / (2 * jp + 1)) * CG(0.5, i_col, j, mL, jp, mLp) * CG(0.5, j_col, j, mR, jp, mRp)
                        self.U[a][b][self.index[(jp, mLp, mRp)], k] += val
        self.L = [np.zeros((d, d), complex) for _ in range(3)]; self.R = [np.zeros((d, d), complex) for _ in range(3)]
        for j in self.spins:
            J = spin_matrices(j); mv = m_values(j)
            for a in range(3):
                for p, mL in enumerate(mv):
                    for q, mLp in enumerate(mv):
                        for mR in mv:
                            self.L[a][self.index[(j, mLp, mR)], self.index[(j, mL, mR)]] += (-J[a].T)[q, p]
                for p, mR in enumerate(mv):
                    for q, mRp in enumerate(mv):
                        for mL in mv:
                            self.R[a][self.index[(j, mL, mRp)], self.index[(j, mL, mR)]] += J[a][q, p]
        self.E2 = np.diag([j * (j + 1) for (j, _, _) in self.states]).astype(complex)

def check_link_algebra(ls):
    T = [s / 2 for s in [np.array([[0, 1], [1, 0]]), np.array([[0, -1j], [1j, 0]]), np.array([[1, 0], [0, -1]])]]
    err = 0.0
    for a in range(3):
        for i in range(2):
            for j in range(2):
                lhs = ls.L[a] @ ls.U[i][j] - ls.U[i][j] @ ls.L[a]
                rhs = -sum(T[a][i, k] * ls.U[k][j] for k in range(2))
                err = max(err, abs(lhs - rhs).max())
                lhs = ls.R[a] @ ls.U[i][j] - ls.U[i][j] @ ls.R[a]
                rhs = sum(ls.U[i][k] * T[a][k, j] for k in range(2))
                err = max(err, abs(lhs - rhs).max())
    cas = sum(l @ l for l in ls.L); err = max(err, abs(cas - ls.E2).max())
    cas = sum(r @ r for r in ls.R); err = max(err, abs(cas - ls.E2).max())
    return err

# ----------------------------------------------------------------------------- Paulo adapter V_P
def paulo_U():
    """Paulo Eq. 28 in basis [|0>, |++>, |+->, |-+>, |-->], colour indices (0:+, 1:-)."""
    s = {0: +1, 1: -1}; bar = {0: 1, 1: 0}
    idx = {None: 0, (0, 0): 1, (0, 1): 2, (1, 0): 3, (1, 1): 4}
    U = [[np.zeros((5, 5), complex) for _ in range(2)] for _ in range(2)]
    r = 1 / math.sqrt(2)
    for a in range(2):
        for b in range(2):
            U[a][b][0, idx[(a, b)]] = r                              # U_ab |ab> = r |0>
            U[a][b][idx[(bar[a], bar[b])], 0] = r * s[a] * s[b]      # U_ab |0> = r s(a)s(b) |abar bbar>
    return U

def find_signed_permutation(Ucg, Up):
    best = None
    for perm in itertools.permutations(range(5)):
        for signs in itertools.product([1, -1], repeat=5):
            V = np.zeros((5, 5));
            for i in range(5):
                V[perm[i], i] = signs[i]
            err = max(abs(V @ Ucg[a][b] @ V.T - Up[a][b]).max() for a in range(2) for b in range(2))
            if err < 1e-14:
                if best is None or signs[0] > 0:
                    best = (perm, signs, err)
    return best

# ----------------------------------------------------------------------------- geometry
# inner links b,r,t,l = 0..3 ; outer 4..11 in corner order c0=(0,0), c1=(1,0), c2=(1,1), c3=(0,1)
LINKS = [("b", (0, 0), (1, 0)), ("r", (1, 0), (1, 1)), ("t", (0, 1), (1, 1)), ("l", (0, 0), (0, 1)),
         ("o0", (-1, 0), (0, 0)), ("o1", (0, -1), (0, 0)),     # into (0,0)
         ("o2", (1, 0), (2, 0)), ("o3", (1, -1), (1, 0)),      # out of / into (1,0)
         ("o4", (1, 1), (2, 1)), ("o5", (1, 1), (1, 2)),       # out of (1,1)
         ("o6", (-1, 1), (0, 1)), ("o7", (0, 1), (0, 2))]      # into / out of (0,1)
CORNERS = [(0, 0), (1, 0), (1, 1), (0, 1)]
LOOP = [(0, +1), (1, +1), (2, -1), (3, -1)]
NL = 12

def corner_ends(c):
    """ends in canonical order (inner_a, inner_b, outer_c, outer_d): (link, 'out'|'in')."""
    ends = []
    for i, (name, s, e) in enumerate(LINKS):
        if s == c: ends.append((i, "out"))
        if e == c: ends.append((i, "in"))
    inner = [x for x in ends if x[0] < 4]; outer = [x for x in ends if x[0] >= 4]
    assert len(inner) == 2 and len(outer) == 2
    return tuple(inner + outer)

CORNER_ENDS = [corner_ends(c) for c in CORNERS]

# ----------------------------------------------------------------------------- route A
@functools.lru_cache(None)
def corner_singlets(js, roles):
    """kernel of sum_a (sum_ends G_a)^2 on the product of the 4 end spaces; columns labelled by the
    inner-pair Casimir (ends 0,1). Returns (vectors [dim, k], J labels)."""
    dims = [int(round(2 * j + 1)) for j in js]; D = int(np.prod(dims))
    def embed(op, pos):
        mats = [np.eye(d, dtype=complex) for d in dims]; mats[pos] = op
        out = np.array([[1.0 + 0j]])
        for m in mats: out = np.kron(out, m)
        return out
    gens = []
    for e, (j, role) in enumerate(zip(js, roles)):
        J = spin_matrices(j)
        gens.append([embed(-J[a].T if role == "out" else J[a], e) for a in range(3)])
    G = [sum(g[a] for g in gens) for a in range(3)]
    C = sum(g @ g for g in G)
    w, v = np.linalg.eigh((C + C.conj().T) / 2)
    kern = v[:, w < 1e-9]
    if kern.shape[1] == 0:
        return np.zeros((D, 0)), ()
    Gin = [gens[0][a] + gens[1][a] for a in range(3)]
    Cin = sum(g @ g for g in Gin)
    lab = kern.conj().T @ Cin @ kern
    lw, lv = np.linalg.eigh((lab + lab.conj().T) / 2)
    kern = kern @ lv
    Js = tuple(round(2 * (-0.5 + math.sqrt(0.25 + x)), 0) / 2 for x in lw)   # J(J+1) -> J
    out = []
    for c in range(kern.shape[1]):
        vec = kern[:, c]
        p = np.argmax(abs(vec)); vec = vec * (abs(vec[p]) / vec[p])        # largest component real positive
        assert abs(vec.imag).max() < 1e-12
        out.append(vec.real)
    return np.array(out).T, Js

def physical_basis_A(ls):
    """433 physical states as sparse vectors over the 12-link electric multi-index.
    key = sum_i s_i 5^i, s_i = LinkSpace index of link i; far ends of outer links fixed to m=+1/2 (first m)."""
    states = []  # (jconf tuple, Jlabels tuple, keys, amps)
    for jconf in itertools.product([0.0, 0.5], repeat=NL):
        per_corner = []
        ok = True
        for ends in CORNER_ENDS:
            js = tuple(jconf[i] for i, _ in ends); roles = tuple(r for _, r in ends)
            vecs, Js = corner_singlets(js, roles)
            if vecs.shape[1] == 0:
                ok = False; break
            per_corner.append((ends, js, vecs, Js))
        if not ok:
            continue
        for combo in itertools.product(*[range(v.shape[1]) for _, _, v, _ in per_corner]):
            # tensor product over corners; then map leg values to link local indices
            legs = []; dims = []; vec = np.array([1.0])
            for (ends, js, vecs, Js), c in zip(per_corner, combo):
                vec = np.kron(vec, vecs[:, c]); legs += list(ends); dims += [int(round(2 * j + 1)) for j in js]
            nz = np.where(abs(vec) > 1e-14)[0]
            idxs = np.array(np.unravel_index(nz, dims)).T
            keys = np.zeros(len(nz), dtype=np.int64)
            for i in range(NL):
                j = jconf[i]; mv = m_values(j)
                mL = np.zeros(len(nz), int); mR = np.zeros(len(nz), int)   # default far end = index 0 (m=+j)
                for k, (link, role) in enumerate(legs):
                    if link != i: continue
                    if role == "out": mL = idxs[:, k]
                    else: mR = idxs[:, k]
                local = np.array([ls.index[(j, mv[a], mv[b])] for a, b in zip(mL, mR)])
                keys += local * 5 ** i
            Jl = tuple(per_corner[q][3][combo[q]] for q in range(4))
            states.append((jconf, Jl, keys, vec[nz]))
    return states

def apply_link_op(keys, amps, link, M):
    """(M on link) |psi>, COO in/out, coalesced."""
    s = (keys // 5 ** link) % 5
    base = keys - s * 5 ** link
    outk = []; outa = []
    for sp in range(5):
        col = M[sp, s]
        nz = abs(col) > 0
        if nz.any():
            outk.append(base[nz] + sp * 5 ** link); outa.append(col[nz] * amps[nz])
    if not outk:
        return np.zeros(0, np.int64), np.zeros(0, complex)
    k = np.concatenate(outk); a = np.concatenate(outa)
    uk, inv = np.unique(k, return_inverse=True)
    ua = np.zeros(len(uk), complex); np.add.at(ua, inv, a)
    return uk, ua

def add_coo(k1, a1, k2, a2):
    k = np.concatenate([k1, k2]); a = np.concatenate([a1, a2])
    uk, inv = np.unique(k, return_inverse=True); ua = np.zeros(len(uk), complex); np.add.at(ua, inv, a)
    return uk, ua

def gauss_residual(ls, keys, amps):
    worst = 0.0
    for ends in CORNER_ENDS:
        for a in range(3):
            k = np.zeros(0, np.int64); v = np.zeros(0, complex)
            for link, role in ends:
                M = ls.L[a] if role == "out" else ls.R[a]
                k2, v2 = apply_link_op(keys, amps, link, M)
                k, v = add_coo(k, v, k2, v2)
            worst = max(worst, np.linalg.norm(v))
    return worst

def plaquette_W(ls):
    """625x625 inner operator Tr(U_b U_r U_t^dag U_l^dag) on links (b,r,t,l) = tensor factors 0..3 (link 0 = least significant)."""
    d = ls.dim
    def op_on(M, i):
        mats = [np.eye(d, dtype=complex)] * 4; mats = list(mats); mats[i] = M
        out = np.array([[1.0 + 0j]])
        for m in reversed(mats):   # link 0 least significant => kron(m3, m2, m1, m0)
            out = np.kron(out, m)
        return out
    U = lambda i, a, b: op_on(ls.U[a][b], i)
    Ud = lambda i, a, b: op_on(ls.U[b][a].conj().T, i)   # (U^dag)_{ab} = (U_{ba})^dag as operator
    W = np.zeros((d ** 4, d ** 4), complex)
    for a, b, c, dd in itertools.product(range(2), repeat=4):
        W += U(0, a, b) @ U(1, b, c) @ Ud(2, c, dd) @ Ud(3, dd, a)
    return W

def inner_key(keys):
    return keys % 625

def outer_key(keys):
    return keys // 625

def apply_W_phys(W, keys, amps):
    """(W (x) 1)|psi> as COO."""
    ik = inner_key(keys); ok = outer_key(keys)
    outk = []; outa = []
    for o in np.unique(ok):
        sel = ok == o
        vec = np.zeros(625, complex); vec[ik[sel]] = amps[sel]
        res = W @ vec
        nz = np.where(abs(res) > 1e-15)[0]
        outk.append(nz + o * 625); outa.append(res[nz])
    return np.concatenate(outk), np.concatenate(outa)

def overlap(k1, a1, k2, a2):
    common, i1, i2 = np.intersect1d(k1, k2, return_indices=True)
    return np.vdot(a1[i1], a2[i2])

def gauge_align(A, B, tol=1e-9):
    """find diagonal unitary D with A = D B D^dag (up to tol); return (D, residual)."""
    n = A.shape[0]; D = np.zeros(n, complex); seen = np.zeros(n, bool)
    if abs(abs(A) - abs(B)).max() > tol:
        return None, abs(abs(A) - abs(B)).max()
    for root in range(n):
        if seen[root]: continue
        D[root] = 1.0; seen[root] = True; stack = [root]
        while stack:
            i = stack.pop()
            for j in np.where((abs(B[i]) > tol) & ~seen)[0]:
                D[j] = D[i] * B[i, j] / A[i, j]      # A_ij = D_i B_ij conj(D_j)  => conj(D_j) = A_ij/(D_i B_ij)
                D[j] = np.conj(D[j]) ; D[j] = D[j]/abs(D[j])
                seen[j] = True; stack.append(j)
    res = abs(A - np.diag(D) @ B @ np.diag(D).conj().T).max()
    return D, res

# ----------------------------------------------------------------------------- route B
def labels_B():
    """(j_0..j_11, J_0..J_3) admissible at the 8 trivalent sites of the (inner|outer) split graph."""
    def tri(a, b, c):
        return abs(a - b) - 1e-9 <= c <= a + b + 1e-9 and round(2 * (a + b + c)) % 2 == 0
    out = []
    for jconf in itertools.product([0.0, 0.5], repeat=NL):
        choices = []
        for ends in CORNER_ENDS:
            ja, jb, j1, j2 = [jconf[i] for i, _ in ends]
            Js = [J / 2 for J in range(0, 3) if tri(ja, jb, J / 2) and tri(j1, j2, J / 2)]
            choices.append(Js)
        for Jl in itertools.product(*choices):
            out.append((jconf, Jl))
    return out

def plaquette_B(labels):
    """P[new, old] = prod over 4 inner sites of F(J_c, j_prev, j_next ; 1/2 ; j'_next, j'_prev) (proto_m1 hexagon rule).
    The loop visits corner c between inner links: c0=(l,b), c1=(b,r), c2=(r,t), c3=(t,l)."""
    index = {lab: i for i, lab in enumerate(labels)}
    n = len(labels); P = np.zeros((n, n))
    corner_pairs = [(3, 0), (0, 1), (1, 2), (2, 3)]   # (prev, next) inner link at corners c0..c3
    for col, (j, Jl) in enumerate(labels):
        for signs in itertools.product((+0.5, -0.5), repeat=4):
            jn = list(j)
            for e, s in zip(range(4), signs):
                jn[e] = j[e] + s
            if min(jn[:4]) < -1e-9 or max(jn[:4]) > 0.5 + 1e-9:
                continue
            lab = (tuple(jn), Jl)
            if lab not in index:
                continue
            amp = 1.0
            for c, (ep, en) in enumerate(corner_pairs):
                amp *= F_recoupling(Jl[c], j[ep], j[en], 0.5, jn[en], jn[ep])
            if abs(amp) > 1e-14:
                P[index[lab], col] += amp
    return P

# ----------------------------------------------------------------------------- main
if __name__ == "__main__":
    t0 = time.time()
    ls = LinkSpace(0.5)
    print("link algebra residual (jmax=1/2):", check_link_algebra(ls))
    print("link algebra residual (jmax=1):  ", check_link_algebra(LinkSpace(1.0)))

    # 6j vs sympy spot-check
    try:
        from sympy.physics.wigner import wigner_6j
        from sympy import Rational
        worst = 0.0; n = 0
        vals = [0, 0.5, 1, 1.5]
        for args in itertools.product(vals, repeat=6):
            ours = SIXJ(*args)
            ref = float(wigner_6j(*[Rational(int(round(2 * x)), 2) for x in args]))
            worst = max(worst, abs(ours - ref)); n += 1
        print(f"6j vs sympy over {n} arg tuples: max |diff| = {worst:.2e}")
    except Exception as e:
        print("sympy check skipped:", e)

    # V_P
    Up = paulo_U()
    best = find_signed_permutation(ls.U, Up)
    print("Paulo adapter signed permutation (perm, signs, err):", best)
    print("  CG basis order:", ls.states)

    # route A
    states = physical_basis_A(ls)
    print(f"route A: {len(states)} physical states  ({time.time()-t0:.1f}s)")
    closed = [s for s in states if all(s[0][i] == 0 for i in range(4, 12))]
    strings = {s[0] for s in states}
    mult = {}
    for s in states: mult[s[0]] = mult.get(s[0], 0) + 1
    amb = sum(1 for v in mult.values() if v > 1)
    weighted = sum(int(np.prod([2 * s[0][i] + 1 for i in range(4, 12)])) for s in states)
    print(f"  closed={len(closed)}  distinct link strings={len(strings)}  ambiguous strings={amb}  far-end weighted={weighted}")
    # gram + gauss
    gram_err = 0.0
    for i in range(len(states)):
        for k in range(i, len(states)):
            ov = overlap(states[i][2], states[i][3], states[k][2], states[k][3])
            gram_err = max(gram_err, abs(ov - (1.0 if i == k else 0.0)))
    print("  Gram deviation from identity:", gram_err)
    gres = max(gauss_residual(ls, k, a) for _, _, k, a in states)
    print("  max Gauss residual:", gres)

    # operators
    W = plaquette_W(ls)
    # W leaves the physical space invariant? compute HB_phys and the leak
    n = len(states)
    HBp = np.zeros((n, n), complex); leak = 0.0
    Wpsi = [apply_W_phys(W, k, a) for _, _, k, a in states]
    for kk in range(n):
        wk, wa = Wpsi[kk]; tot = np.linalg.norm(wa) ** 2; proj = 0.0
        for kp in range(n):
            ov = overlap(states[kp][2], states[kp][3], wk, wa)
            HBp[kp, kk] = ov; proj += abs(ov) ** 2
        leak = max(leak, abs(tot - proj))
    TrW = HBp.copy()
    HB_A = -(TrW + TrW.conj().T)
    print("  physical leak of W:", leak, " hermiticity |TrW - TrW^dag|max:", abs(TrW - TrW.conj().T).max())
    HE_A = np.diag([sum(j * (j + 1) for j in s[0][:4]) for s in states])
    HEo_A = np.diag([sum(j * (j + 1) for j in s[0][4:]) for s in states])
    # closed block
    ci = [i for i, s in enumerate(states) if all(s[0][i2] == 0 for i2 in range(4, 12))]
    print("  closed-sector indices:", ci, "labels:", [states[i][:2] for i in ci])
    for g2 in (1.0,):
        Hc = (g2 / 2) * HE_A[np.ix_(ci, ci)] + (1 / g2) * HB_A[np.ix_(ci, ci)]
        print(f"  closed 2x2 block at g^2={g2}:\n", Hc)
    # J conservation and outer-block structure
    Jlab = [s[1] for s in states]; olab = [s[0][4:] for s in states]
    viol = max(abs(HB_A[i, k]) for i in range(n) for k in range(n) if Jlab[i] != Jlab[k])
    violo = max(abs(HB_A[i, k]) for i in range(n) for k in range(n) if olab[i] != olab[k])
    print("  max |HB| between different J labels:", viol, " between different outer labels:", violo)

    # route B
    labs = labels_B()
    print(f"route B: {len(labs)} labels")
    P = plaquette_B(labs)
    HB_B = -(P + P.T)
    HE_B = np.diag([sum(j * (j + 1) for j in l[0][:4]) for l in labs])
    print("  P hermitian? |P-P^T|max =", abs(P - P.T).max())
    # align state orders: route A states carry (jconf, Jl) labels too
    idxA = {(s[0], s[1]): i for i, s in enumerate(states)}
    perm = [idxA[l] for l in labs]
    HB_A2 = HB_A[np.ix_(perm, perm)]; HE_A2 = HE_A[np.ix_(perm, perm)]
    for g2 in (0.5, 1.0, 2.0):
        eA = np.linalg.eigvalsh((g2 / 2) * HE_A2 + HB_A2 / g2); eB = np.linalg.eigvalsh((g2 / 2) * HE_B + HB_B / g2)
        print(f"  spectra A vs B at g^2={g2}: max|diff| = {abs(eA-eB).max():.2e}")
    D, res = gauge_align(HB_A2, HB_B)
    print("  gauge_align(HB_A, HB_B): residual =", res, " (D real signs only?)", None if D is None else abs(D.imag).max())
    # K_inner: 47 inner labels; check every outer block equals K restricted (up to gauge)
    inner_labels = sorted({(l[0][:4], l[1]) for l in labs})
    print("  distinct inner labels (j_b j_r j_t j_l, J):", len(inner_labels))
    # build K from route B by taking any outer pattern realising the label: by construction P depends only on inner label
    iidx = {lab: i for i, lab in enumerate(inner_labels)}
    K = np.zeros((47, 47)); seen = np.zeros((47, 47), bool); consistent = True
    for a, la in enumerate(labs):
        for b, lb in enumerate(labs):
            if la[0][4:] != lb[0][4:]: continue
            ia, ib = iidx[(la[0][:4], la[1])], iidx[(lb[0][:4], lb[1])]
            if seen[ia, ib] and abs(K[ia, ib] - HB_B[a, b]) > 1e-12: consistent = False
            K[ia, ib] = HB_B[a, b]; seen[ia, ib] = True
    print("  K_inner (47x47) consistent across outer patterns (route B):", consistent)
    # route A blocks vs K up to gauge
    worst = 0.0; nblocks = 0
    outer_patterns = sorted({l[0][4:] for l in labs})
    for o in outer_patterns:
        sel = [i for i, l in enumerate(labs) if l[0][4:] == o]
        il = [iidx[(labs[i][0][:4], labs[i][1])] for i in sel]
        blockA = HB_A2[np.ix_(sel, sel)]; blockK = K[np.ix_(il, il)]
        Dd, r = gauge_align(blockA, blockK)
        worst = max(worst, r if Dd is not None else 1.0); nblocks += 1
    print(f"  route-A outer blocks ({nblocks} patterns, dims {min(len([1 for l in labs if l[0][4:]==o]) for o in outer_patterns)}..{max(len([1 for l in labs if l[0][4:]==o]) for o in outer_patterns)}) vs K up to diagonal gauge: worst residual = {worst:.2e}")
    # H_B^phys A: is it block-identical to K (without gauge) ?
    worst_nogauge = 0.0
    for o in outer_patterns:
        sel = [i for i, l in enumerate(labs) if l[0][4:] == o]
        il = [iidx[(labs[i][0][:4], labs[i][1])] for i in sel]
        worst_nogauge = max(worst_nogauge, abs(HB_A2[np.ix_(sel, sel)] - K[np.ix_(il, il)]).max())
    print("  without gauge: worst |blockA - K| =", worst_nogauge)
    # Paulo's Eq.37 check on K: vacuum <-> all-half with J=0 coupling
    vac = iidx[((0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0))]; full0 = iidx[((0.5, 0.5, 0.5, 0.5), (0.0, 0.0, 0.0, 0.0))]
    print("  K[vac, all-half J=0] =", K[vac, full0], "; K[vac, :] nonzeros:", [(inner_labels[i], K[vac, i]) for i in np.where(abs(K[vac]) > 1e-12)[0]])
    # dark labels (J=1 corners)
    dark = [lab for lab in inner_labels if abs(K[iidx[lab]]).max() < 1e-12]
    print("  dark inner labels (K row = 0):", len(dark))
    # dim S_o: inner codes per outer pattern (route A support)
    dims = {}
    for s in states:
        o = tuple(outer_key(s[2])) ;
    # inner support per outer computational pattern = per (outer electric index); count distinct inner keys
    supp = {}
    for s in states:
        for ok_, ik_ in zip(outer_key(s[2]), inner_key(s[2])):
            supp.setdefault(ok_, set()).add(ik_)
    allinner = set().union(*supp.values())
    print(f"  outer electric patterns with support: {len(supp)}; inner codes used overall: {len(allinner)}; "
          f"dim S_o range: {min(len(v) for v in supp.values())}..{max(len(v) for v in supp.values())}")
    # rank of inner span (over all physical states, the inner components)
    print(f"done in {time.time()-t0:.1f}s")
