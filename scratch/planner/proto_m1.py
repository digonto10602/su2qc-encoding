"""Planner prototype for M1: SU(2) KS Hamiltonian on the 2x2 periodic lattice.

Reference A: full KS electric-basis tensor-product space at jmax=1/2, explicit
             Gauss-law generators, physical subspace from vertex intertwiners.
Reference B: spin-network basis on the point-split trivalent graph, plaquette
             operator from products of F-symbols (6j), electric term diagonal.
Both must give the same spectrum in the physical subspace.
"""
import itertools, functools, sys, time
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from sympy.physics.wigner import clebsch_gordan, wigner_6j
from sympy import Rational, S

np.set_printoptions(linewidth=150, precision=6, suppress=True)
half = Rational(1, 2)

def R(x):  # float -> sympy rational multiple of 1/2
    return Rational(int(round(2 * x)), 2)

@functools.lru_cache(None)
def cg(j1, m1, j2, m2, J, M):
    return float(clebsch_gordan(R(j1), R(j2), R(J), R(m1), R(m2), R(M)))

@functools.lru_cache(None)
def six_j(a, b, c, d, e, f):
    return float(wigner_6j(R(a), R(b), R(c), R(d), R(e), R(f)))

def jvals(jmax):
    return [k / 2 for k in range(int(round(2 * jmax)) + 1)]

def mvals(j):
    return [-j + k for k in range(int(round(2 * j)) + 1)]

def spin_matrices(j):
    ms = mvals(j); d = len(ms)
    Jz = np.diag(ms).astype(complex)
    Jp = np.zeros((d, d), complex)
    for i, m in enumerate(ms[:-1]):
        Jp[i + 1, i] = np.sqrt(j * (j + 1) - m * (m + 1))
    Jx = (Jp + Jp.conj().T) / 2; Jy = (Jp - Jp.conj().T) / (2j)
    return [Jx, Jy, Jz]

# ---------------- KS link space ----------------
class KSLink:
    def __init__(self, jmax):
        self.jmax = jmax
        self.states = [(j, mL, mR) for j in jvals(jmax) for mL in mvals(j) for mR in mvals(j)]
        self.index = {s: i for i, s in enumerate(self.states)}
        self.d = len(self.states)
        d = self.d
        # U_{alpha beta}, alpha,beta in {+1/2,-1/2}  (index 0 -> +1/2, 1 -> -1/2)
        self.U = {}
        for a in (0.5, -0.5):
            for b in (0.5, -0.5):
                M = np.zeros((d, d), complex)
                for (j, mL, mR), col in self.index.items():
                    for J in (j - 0.5, j + 0.5):
                        if J < 0 or J > jmax + 1e-9:
                            continue
                        ML, MR = mL + a, mR + b
                        if abs(ML) > J + 1e-9 or abs(MR) > J + 1e-9:
                            continue
                        val = np.sqrt((2 * j + 1) / (2 * J + 1)) * cg(j, mL, 0.5, a, J, ML) * cg(j, mR, 0.5, b, J, MR)
                        M[self.index[(J, ML, MR)], col] += val
                self.U[(a, b)] = M
        self.E2 = np.diag([j * (j + 1) for (j, _, _) in self.states]).astype(complex)
        # generators: left acts on mL as J^a ; right acts on mR as -conj(J^a)
        self.L = [np.zeros((d, d), complex) for _ in range(3)]
        self.Rg = [np.zeros((d, d), complex) for _ in range(3)]
        for j in jvals(jmax):
            Js = spin_matrices(j); ms = mvals(j)
            for a in range(3):
                for i1, m1 in enumerate(ms):
                    for i2, m2 in enumerate(ms):
                        for n in ms:
                            self.L[a][self.index[(j, m1, n)], self.index[(j, m2, n)]] += Js[a][i1, i2]
                            self.Rg[a][self.index[(j, n, m1)], self.index[(j, n, m2)]] += -np.conj(Js[a][i1, i2])

# ---------------- lattice ----------------
class Torus2x2:
    def __init__(self):
        self.Lx = self.Ly = 2
        self.sites = [(x, y) for y in range(2) for x in range(2)]
        self.site_index = {s: i for i, s in enumerate(self.sites)}
        self.links = []  # (site, mu)
        for s in self.sites:
            for mu in (0, 1):
                self.links.append((s, mu))
        self.link_index = {l: i for i, l in enumerate(self.links)}
    def shift(self, s, mu, sign=+1):
        x, y = s
        if mu == 0: return ((x + sign) % 2, y)
        return (x, (y + sign) % 2)
    def link_ends(self, l):
        s, mu = l
        return s, self.shift(s, mu)
    def plaquettes(self):
        """list of 4 (link index, orientation) : U_x(s) U_y(s+x) U_x(s+y)^dag U_y(s)^dag"""
        out = []
        for s in self.sites:
            p = [(self.link_index[(s, 0)], +1), (self.link_index[(self.shift(s, 0), 1)], +1),
                 (self.link_index[(self.shift(s, 1), 0)], -1), (self.link_index[(s, 1)], -1)]
            out.append(p)
        return out
    def eta(self, s, mu):
        return 1 if mu == 0 else (-1) ** s[0]
    def stag_sign(self, s):
        return (-1) ** (s[0] + s[1])

# ---------------- Reference A: full KS space ----------------
def kron_list(mats):
    out = mats[0]
    for m in mats[1:]:
        out = sp.kron(out, m, format='csr')
    return out

def link_op(lat, link, d, M, i):
    mats = [sp.identity(d, format='csr')] * len(lat.links)
    mats = list(mats); mats[i] = sp.csr_matrix(M)
    return kron_list(mats)

def build_A(lat, jmax, g2=1.0):
    link = KSLink(jmax); d = link.d; nl = len(lat.links)
    N = d ** nl
    print(f"[A] jmax={jmax} d_link={d} full dim={N}")
    I = sp.identity(N, format='csr')
    def op_on(i, M):
        return link_op(lat, None, d, M, i)
    HE = sum(op_on(i, link.E2) for i in range(nl))
    # plaquette: Tr( U1 U2 U3^dag U4^dag ) with U^dag_{ab} = conj(U_{ba})  (operator adjoint)
    HB = sp.csr_matrix((N, N), dtype=complex)
    Uops = {}
    for i in range(nl):
        for ab, M in link.U.items():
            Uops[(i, ab)] = op_on(i, M)
    def Umat(i, orient):
        # returns dict (a,b) -> operator for the matrix U or U^dag
        if orient == +1:
            return {ab: Uops[(i, ab)] for ab in link.U}
        return {(a, b): Uops[(i, (b, a))].conj().T.tocsr() for (a, b) in link.U}
    plaq_ops = []
    for p in lat.plaquettes():
        mats = [Umat(i, o) for (i, o) in p]
        tot = sp.csr_matrix((N, N), dtype=complex)
        idx = [0.5, -0.5]
        for a, b, c, dd in itertools.product(idx, repeat=4):
            tot = tot + mats[0][(a, b)] @ mats[1][(b, c)] @ mats[2][(c, dd)] @ mats[3][(dd, a)]
        plaq_ops.append(tot)
        HB = HB + tot
    # Gauss generators
    G = []
    for s in lat.sites:
        for a in range(3):
            Ga = sp.csr_matrix((N, N), dtype=complex)
            for i, l in enumerate(lat.links):
                st, en = lat.link_ends(l)
                if st == s: Ga = Ga + op_on(i, link.L[a])
                if en == s: Ga = Ga + op_on(i, link.Rg[a])
            G.append(Ga)
    H = g2 / 2 * HE - 1 / (2 * g2) * (HB + HB.conj().T)
    return dict(link=link, HE=HE, HB=HB, H=H, G=G, plaq=plaq_ops, N=N, d=d)

def vertex_intertwiners(lat, link, jconf):
    """physical basis vectors (as full-space sparse column vectors) for one j-configuration"""
    d = link.d; nl = len(lat.links)
    # per link: list of local state indices with j = jconf[i]
    loc = [[link.index[(jconf[i], mL, mR)] for mL in mvals(jconf[i]) for mR in mvals(jconf[i])] for i in range(nl)]
    # vertex legs: (link i, end) ; end 0 = left(mL), 1 = right(mR)
    vert_basis = []
    for s in lat.sites:
        legs = []
        for i, l in enumerate(lat.links):
            st, en = lat.link_ends(l)
            if st == s: legs.append((i, 0))
            if en == s: legs.append((i, 1))
        # leg spaces
        dims = [len(mvals(jconf[i])) for (i, e) in legs]
        D = int(np.prod(dims))
        Gtot = [np.zeros((D, D), complex) for _ in range(3)]
        for k, (i, e) in enumerate(legs):
            j = jconf[i]; Js = spin_matrices(j)
            for a in range(3):
                M = Js[a] if e == 0 else -np.conj(Js[a])
                mats = [np.eye(dm) for dm in dims]; mats[k] = M
                full = mats[0]
                for mm in mats[1:]: full = np.kron(full, mm)
                Gtot[a] += full
        C = sum(Ga @ Ga for Ga in Gtot)
        w, v = np.linalg.eigh(C)
        null = v[:, w < 1e-9]
        vert_basis.append((legs, dims, null))
    return vert_basis

def physical_basis_A(lat, link, jmax):
    nl = len(lat.links); d = link.d
    cols = []
    jl = jvals(jmax)
    for jconf in itertools.product(jl, repeat=nl):
        vb = vertex_intertwiners(lat, link, jconf)
        if any(nb.shape[1] == 0 for (_, _, nb) in vb):
            continue
        # tensor product over vertices, then map leg indices -> link local state index
        # Build full vectors: iterate over combos of vertex singlet vectors
        legs_all = [lg for (legs, dims, nb) in vb for lg in legs]
        dims_all = [dm for (legs, dims, nb) in vb for dm in dims]
        for combo in itertools.product(*[range(nb.shape[1]) for (_, _, nb) in vb]):
            vec = np.array([1.0 + 0j])
            for (legs, dims, nb), c in zip(vb, combo):
                vec = np.kron(vec, nb[:, c])
            # vec indexed by legs_all multi-index; convert to full-space index
            idxs = np.array(np.unravel_index(np.arange(vec.size), dims_all)).T  # (size, nlegs)
            # for each link: mL index, mR index
            mL = np.zeros((vec.size, nl), int); mR = np.zeros((vec.size, nl), int)
            for k, (i, e) in enumerate(legs_all):
                if e == 0: mL[:, i] = idxs[:, k]
                else: mR[:, i] = idxs[:, k]
            local = np.zeros((vec.size, nl), int)
            for i in range(nl):
                nm = len(mvals(jconf[i]))
                base = link.index[(jconf[i], mvals(jconf[i])[0], mvals(jconf[i])[0])]
                local[:, i] = base + mL[:, i] * nm + mR[:, i]
            full = np.zeros(nl, int)
            flat = np.zeros(vec.size, dtype=np.int64)
            for i in range(nl):
                flat = flat * d + local[:, i]
            nz = np.abs(vec) > 1e-14
            cols.append(sp.csr_matrix((vec[nz], (flat[nz], np.zeros(nz.sum(), int))), shape=(d ** nl, 1)))
    V = sp.hstack(cols).tocsr()
    return V

# ---------------- Reference B: spin network + 6j ----------------
def F(j1, j2, j12, j3, j4, j23):
    return (-1) ** int(round(j1 + j2 + j3 + j4)) * np.sqrt((2 * j12 + 1) * (2 * j23 + 1)) * six_j(j1, j2, j12, j3, j4, j23)

def triangle(a, b, c):
    return (abs(a - b) <= c + 1e-9) and (c <= a + b + 1e-9) and abs(round(2 * (a + b + c)) % 2) == 0

def build_B(lat, jmax, g2=1.0):
    """Point-split graph: site s -> s_out (legs x_out, y_out, virt), s_in (legs x_in, y_in, virt).
    Edges: 8 real links + 4 virtual links (one per site). Trivalent vertices: 8."""
    nl = len(lat.links); ns = len(lat.sites)
    nedge = nl + ns  # virtual link of site k has edge index nl + k
    # vertices: (site, 'out') and (site, 'in'), each with 3 edges
    verts = []
    for s in lat.sites:
        k = lat.site_index[s]
        eo = [lat.link_index[(s, 0)], lat.link_index[(s, 1)], nl + k]
        ei = [lat.link_index[(lat.shift(s, 0, -1), 0)], lat.link_index[(lat.shift(s, 1, -1), 1)], nl + k]
        verts.append(((s, 'out'), eo)); verts.append(((s, 'in'), ei))
    # enumerate SN basis: j on real links <= jmax, virtual any value consistent with triangles
    jreal = jvals(jmax); jvirt = jvals(2 * jmax)
    basis = []
    for jr in itertools.product(jreal, repeat=nl):
        for jv in itertools.product(jvirt, repeat=ns):
            j = list(jr) + list(jv)
            if all(triangle(j[e[0]], j[e[1]], j[e[2]]) for (_, e) in verts):
                basis.append(tuple(j))
    index = {b: i for i, b in enumerate(basis)}
    NB = len(basis)
    print(f"[B] jmax={jmax} SN basis dim={NB}")
    HE = sp.diags([sum(j[e] * (j[e] + 1) for e in range(nl)) for j in basis]).tocsr()
    # plaquette loops as hexagons through vertices: list of (vertex edges) and the inner edges
    def hexagon(s):
        sx = lat.shift(s, 0); sy = lat.shift(s, 1); sxy = lat.shift(sx, 1)
        k = lambda q: nl + lat.site_index[q]
        # vertices in loop order and inner edge between consecutive vertices
        vlist = [(s, 'out'), (sx, 'in'), (sx, 'out'), (sxy, 'in'), (sy, 'out'), (sy, 'in')]
        inner = [lat.link_index[(s, 0)], k(sx), lat.link_index[(sx, 1)], lat.link_index[(sy, 0)], k(sy), lat.link_index[(s, 1)]]
        vedges = dict(verts)
        outer = []
        for i, v in enumerate(vlist):
            e_prev = inner[i - 1]; e_next = inner[i]
            o = [e for e in vedges[v] if e not in (e_prev, e_next)]
            assert len(o) == 1, (v, vedges[v], e_prev, e_next)
            outer.append(o[0])
        return vlist, inner, outer
    HB = sp.lil_matrix((NB, NB), dtype=complex)
    plaqs = []
    for s in lat.sites:
        vlist, inner, outer = hexagon(s)
        P = sp.lil_matrix((NB, NB), dtype=complex)
        for col, j in enumerate(basis):
            # new inner labels j' = j +- 1/2 on each inner edge
            for signs in itertools.product((+0.5, -0.5), repeat=6):
                jn = list(j)
                ok = True
                for e, sgn in zip(inner, signs):
                    jn[e] = j[e] + sgn
                    if jn[e] < -1e-9: ok = False
                    if e < nl and jn[e] > jmax + 1e-9: ok = False
                if not ok: continue
                jn = tuple(jn)
                if jn not in index: continue
                amp = 1.0
                for i in range(6):
                    e_prev = inner[i - 1]; e_next = inner[i]; o = outer[i]
                    # vertex factor F^{j_o, j_prev, j_next}_{1/2, j'_next, j'_prev}
                    amp *= F(j[o], j[e_prev], j[e_next], 0.5, jn[e_next], jn[e_prev])
                if abs(amp) > 1e-14:
                    P[index[jn], col] += amp
        P = P.tocsr(); plaqs.append(P); HB = HB + P
    HB = HB.tocsr()
    H = g2 / 2 * HE - 1 / (2 * g2) * (HB + HB.conj().T)
    return dict(H=H, HE=HE, HB=HB, basis=basis, plaq=plaqs, N=NB)

def spectrum(Hs, k=None):
    Hd = Hs.toarray() if sp.issparse(Hs) else Hs
    return np.linalg.eigvalsh((Hd + Hd.conj().T) / 2)

if __name__ == "__main__":
    lat = Torus2x2()
    t0 = time.time()
    A = build_A(lat, 0.5)
    print("built A in", time.time() - t0)
    # gauge invariance of each term
    for name, O in [("HE", A["HE"]), ("HB", A["HB"])]:
        mx = max(abs((O @ G - G @ O)).max() if (O @ G - G @ O).nnz else 0 for G in A["G"])
        print(f"max |[{name}, G]| = {mx:.2e}")
    V = physical_basis_A(lat, A["link"], 0.5)
    print("physical dim (A, vertex intertwiners):", V.shape[1])
    # orthonormality
    ov = (V.conj().T @ V).toarray(); print("orthonormality err", np.abs(ov - np.eye(V.shape[1])).max())
    # check Gauss on the basis
    print("max |G V|:", max(abs(G @ V).max() if (G @ V).nnz else 0 for G in A["G"]))
    HA = (V.conj().T @ A["H"] @ V).toarray()
    HBA = (V.conj().T @ A["HB"] @ V).toarray()
    print("HB hermitian in phys?", np.abs(HBA - HBA.conj().T).max())
    eA = spectrum(HA)
    B = build_B(lat, 0.5)
    HBB = B["HB"].toarray()
    print("HB (B) hermitian?", np.abs(HBB - HBB.conj().T).max())
    eB = spectrum(B["H"])
    print("dim A/B:", HA.shape[0], B["N"])
    print("eA[:12]", eA[:12]); print("eB[:12]", eB[:12])
    print("max |eA-eB|", np.abs(eA - eB).max() if eA.shape == eB.shape else "dim mismatch")
    np.save("/home/digimonk/Projects/su2qc-encoding/scratch/planner/eA_jhalf.npy", eA)
