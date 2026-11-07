"""SUMMARY: exact degree-1 spectral transform of a flat dilation of W = prod_c K_c (F4): corner-local Dicke frame (pseudo-spin chain e1 -> S -> e3 made classical, U_E as 4 free phases), direction qubit q = f(data), q-controlled corner-local lowering J so both members of every bright pair share the data register, then one class-multiplexed Rx on q gated by AND_c[corner is a raising source and not dark]; closed chain via q=|+> on the all-Q loop plus an A<->L toggle.
DISCOVERY: W/kappa is a product of corner partial isometries (pseudo-spin raising J+/|J+|); with a direction qubit the dilated block is flat (all 81 pairs at singular value 1, the kappa=4sqrt2 pair too if q=|+> on the loop), so exp(i beta H_B) is exp(i theta_kappa X_q) in the J-frame gated by a corner-local test: no polynomial, no bright-pair labels.
DISCOVERY: corner frame CX(s1,t1) CX(s2,t2) CX(t1,t2) CX(s1,s2), C2H(s2=1,t2=0 -> s1), CCX(t1,s2 -> s1): every raising source has s1 xor s2 = 1, every other state outside the dark sector (t1,t2)=(0,0) has 0; the lowering is s1 ^= q !t2 s2, s2 ^= q.
DISCOVERY: the corner signs of W are (-1)^[N_c=1]; the free gauge Z(s1)Z(s2) plus CY (instead of CX) for the q-controlled s2 flip makes the sign of all 81 lowerings +1 (phases i, i, -i, -i for N=1, N=3, e3->S, S->e1).
"""
FAMILY = "F4"
PARENT = None

import math

from su2plaq.compress.builder import Builder

# corner c: (source end colour 1, colour 2, target end colour 1, colour 2); K_c hops source -> target (W raises all heights)
CORNERS = [(0, 1, 12, 13), (4, 5, 2, 3), (10, 11, 6, 7), (14, 15, 8, 9)]


def _c2h(b, c1, c2, t):
    """controlled-H on t with controls c1, c2 (both 1): Ry(pi/4) CCZ Ry(-pi/4) (exact, 6 CX)."""
    b.sdg(t)
    b.h(t)
    b.tdg(t)
    b.h(t)
    b.s(t)
    b.ccz(c1, c2, t)
    b.sdg(t)
    b.h(t)
    b.t(t)
    b.h(t)
    b.s(t)


def _frame(b, alpha=None):
    """raw corner bits -> codes (a, b, c, d) = (s1, s2, t1, t2); U_E phases inserted when alpha is given."""
    for (s1, s2, t1, t2) in CORNERS:
        b.cx(s1, t1)
        b.cx(s2, t2)
        b.cx(t1, t2)
        b.cx(s1, s2)
        if alpha is not None:
            b.p(-0.75 * alpha, s2)          # s2 = [source end single] = Q-flag of the link owning this end
        b.x(t2)
        _c2h(b, s2, t2, s1)                 # Dicke: singlet / triplet-0 of the both-single sector become basis codes
        b.x(t2)
        b.ccx(t1, s2, s1)                   # species relabel
        b.z(s1)                             # sign gauge (-1)^(a xor b); with the CY in J all 81 pairs get sign +1
        b.z(s2)


def _frame_inv(b):
    for (s1, s2, t1, t2) in reversed(CORNERS):
        b.z(s1)
        b.z(s2)
        b.ccx(t1, s2, s1)
        b.x(t2)
        _c2h(b, s2, t2, s1)
        b.x(t2)
        b.cx(s1, s2)
        b.cx(t1, t2)
        b.cx(s2, t2)
        b.cx(s1, t1)


def _and_chain(b, lits):
    """rccx chain computing AND(lits) into a fresh ancilla; returns (result, ops) for the mirrored uncompute."""
    temps = []
    cur = lits[0]
    for x in lits[1:]:
        (u,) = b.alloc(1, "and")
        b.rccx(cur, x, u)
        temps.append((cur, x, u))
        cur = u
    return cur, temps


def _unchain(b, temps):
    for (c1, c2, u) in reversed(temps):
        b.rccx(c1, c2, u)
        b.free(u)


def _f_into_q(b, q):
    """q ^= f, f = NOT AND_{c0,c1,c2} (a xor b)  (0 on lower members, 1 on upper members, f(A)=f(L)=0, f(B)=1)."""
    for (s1, s2, t1, t2) in CORNERS[:3]:
        b.cx(s1, s2)
    b.x(q)
    b.mcx([CORNERS[0][1], CORNERS[1][1], CORNERS[2][1]], q)
    for (s1, s2, t1, t2) in CORNERS[:3]:
        b.cx(s1, s2)


def _E(b, q, k0):
    _f_into_q(b, q)
    _c2h(b, k0, CORNERS[0][1], q)           # all-Q loop L (closed class, corner 0 in S) -> q = |+>


def _E_inv(b, q, k0):
    _c2h(b, k0, CORNERS[0][1], q)
    _f_into_q(b, q)


def _cy(b, c, t):
    b.sdg(t)
    b.cx(c, t)
    b.s(t)


def _J(b, q):
    """q-controlled lowering W_V^dagger on corner codes: a ^= q & !d & b ; b ^= q (as CY: phases i^(..) fix the signs)."""
    for (s1, s2, t1, t2) in CORNERS:
        b.x(t2)
        b.mcx([q, t2, s2], s1)
        b.x(t2)
        _cy(b, q, s2)


def _J_inv(b, q):
    for (s1, s2, t1, t2) in reversed(CORNERS):
        _cy(b, q, s2)
        b.x(t2)
        b.mcx([q, t2, s2], s1)
        b.x(t2)


def _class_flags(b, d, e, k0):
    """e ^= [d0 = d1 = d2] (n_d in {0,4}), k0 ^= e & !d1 (all even).  rccx: e, k0 and the d bits are only read until the
    mirrored uncompute, so the relative phases cancel."""
    b.cx(d[1], d[0])
    b.cx(d[1], d[2])
    b.x(d[0])
    b.x(d[2])
    b.rccx(d[0], d[2], e)
    b.x(d[0])
    b.x(d[2])
    b.cx(d[1], d[2])
    b.cx(d[1], d[0])
    b.x(d[1])
    b.rccx(e, d[1], k0)
    b.x(d[1])


def _class_flags_inv(b, d, e, k0):
    b.x(d[1])
    b.rccx(e, d[1], k0)
    b.x(d[1])
    b.cx(d[1], d[0])
    b.cx(d[1], d[2])
    b.x(d[0])
    b.x(d[2])
    b.rccx(d[0], d[2], e)
    b.x(d[0])
    b.x(d[2])
    b.cx(d[1], d[2])
    b.cx(d[1], d[0])


def _pp_rz(b, tgt, terms):
    """exp(-i/2 sum_S c_S Z_S Z_tgt) along the parity cycle given as [(cx-control or None, angle)]."""
    for ctrl, ang in terms:
        if ctrl is not None:
            b.cx(ctrl, tgt)
        if ang is not None and abs(ang) > 0:
            b.rz(ang, tgt)


def build(spec):
    b = Builder(spec)
    al, be = spec.alpha, spec.beta
    r2 = math.sqrt(2.0)
    _frame(b, alpha=al)
    # class flags (d = t2 = [N_c odd] is never changed below; n_d in {0, 2, 4}): e = all equal, k0 = all even
    d = [c[3] for c in CORNERS]
    (k1, k0) = b.alloc(2, "class")         # k1 holds e = [n_d in {0,4}] = all-odd or all-even
    _class_flags(b, d, k1, k0)
    (q,) = b.alloc(1, "dir")
    _E(b, q, k0)
    _J(b, q)
    # ---- J-frame: bright pairs are (q=0, u), (q=1, u) with u all-source
    for (s1, s2, t1, t2) in CORNERS:
        b.cx(s1, s2)                         # s2 <- a xor b
    darks = []
    for (s1, s2, t1, t2) in CORNERS:
        (o,) = b.alloc(1, "notdark")
        b.x(t1)
        b.x(t2)
        b.rccx(t1, t2, o)                    # o = dark sector
        b.x(t1)
        b.x(t2)
        b.x(o)                               # o = not dark
        darks.append((t1, t2, o))
    lits = []
    for (s1, s2, t1, t2), (_, _, o) in zip(CORNERS, darks):
        lits += [s2, o]
    z, t_z = _and_chain(b, lits)
    # Rx_q(L), L = z*(-4b) + z*k1*(2b) + z*k0*(-2(2r2-2)b); phase polynomial on the parity cycle 0, k1, z k1, z, z k0, k0
    lam2, mu1, mu0 = -4.0 * be, 2.0 * be, -2.0 * (2.0 * r2 - 2.0) * be
    mu0 = mu0 - mu1                          # k1 carries e = k0 or k1_true:  L = z (lam2 + mu1 e + (mu0 - mu1) k0)
    c0 = lam2 / 2 + mu1 / 4 + mu0 / 4
    b.h(q)
    _pp_rz(b, q, [(None, c0), (k1, -mu1 / 4), (z, mu1 / 4), (k1, -c0), (k0, mu0 / 4), (z, -mu0 / 4), (k0, None)])
    b.h(q)
    # closed chain: Rx(-4 r2 b) on the A <-> L toggle when z and k0
    a0 = CORNERS[0][0]
    for c in CORNERS[1:]:
        b.cx(a0, c[0])
    nu = -4.0 * r2 * be
    b.h(a0)
    _pp_rz(b, a0, [(None, nu / 4), (z, -nu / 4), (k0, nu / 4), (z, -nu / 4), (k0, None)])
    b.h(a0)
    for c in reversed(CORNERS[1:]):
        b.cx(a0, c[0])
    _unchain(b, t_z)
    for (t1, t2, o) in reversed(darks):
        b.x(o)
        b.x(t1)
        b.x(t2)
        b.rccx(t1, t2, o)
        b.x(t1)
        b.x(t2)
        b.free(o)
    for (s1, s2, t1, t2) in CORNERS:
        b.cx(s1, s2)
    # ---- back
    _J_inv(b, q)
    _E_inv(b, q, k0)
    b.free(q)
    _class_flags_inv(b, d, k1, k0)
    b.free([k1, k0])
    _frame_inv(b)
    return b
