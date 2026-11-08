"""SUMMARY: F3 controlled partner involution in CH form with a kappa selector (parent r03-F3-002): frame as in the parent (L2 = Q flag, U_E as 4 phases on L2; h_b by two in-place rccx Fredkin halves + a Margolus Toffoli with a CZ(h_b, r.L1) gauge; one CX per corner; tau fix CX(h_X -> e1); 4 relative-phase C2H; one kappa=1 dark-label fold rccx(e1c3, !e2c3 -> F); e1 ^= g^delta^1; closed gadget H(q3), CCH(Z,F), rccx), but the intermediate of the closed selector is now U = [r_t = 0 = r_r^r_l] (kappa=1 class or closed) from rccx(!r_t, !r_rl) and Z = rccx(U, !r_l) = [r = 000] (same 6 CX as before); exp(i theta Pi) = W exp(i theta X_F Z_E) W, W = 4 CH(!e2 -> e1), Z_E folded into the Gray path by 4 CX(e1 -> F) at each end; bright flag X = AND of 4 in-place corner tests delta_c ^ (e2 & e1); the Walsh rotation on F needs only 6 Gray-cycle terms over (X, U, Z) instead of 10 over (X, Z, r_t, r_rl) (4 CX and 4 rotations fewer); all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: the selector chain of the closed flag Z can produce the kappa class for free: U = rccx(!r_t, !r_r^r_l) is 1 exactly on the kappa=1 class r = 101 and on r = 000, Z = rccx(U, !r_l), and on the occurring (U, Z) patterns (Z implies U) the coupling-signed angle v = -2 (U=0), -1 (U=1, Z=0), +4 sqrt2 (Z=1) is a + b s_U + c s_Z with three Walsh terms, so theta = X v is a 6-term Gray cycle (6 CX) instead of 10.
DISCOVERY: in this frame the 4 corner tests cannot drop the kappa=1 fold: an exhaustive search over single-rccx tests R ^ (l1 & l2) (R a qubit or 2-parity, l1, l2 literals, 138 tests true on all bright labels) finds no 3- or 4-test cover of the 702 dark labels, no linear (<= 3-parity) replacement of any test exists, and no order of the h_b mux (6 orders) makes the 16 kappa=1 dark labels fail without the fold.
DISCOVERY: merging the GD conversion into the tau fix (CX(g_Y -> e1) moved before the C2H, which becomes C2(X H X) with an even CZ sign) keeps all couplings uniform but needs the q3 restore (h_t ^ g_l is not pair-invariant), so it saves nothing, and no single two-literal fold is exact in the merged frame.
"""
FAMILY = "F3"
PARENT = "r03-F3-002"

import math

from su2plaq.compress.builder import Builder

# ancilla slots (symbolic 16.., remapped to allocated qubits in build)
N1, N2, XF, U, Z = range(16, 21)
NANC = 5
F = 1                                  # flip qubit (= g_b): the Hadamard-test qubit of the partner rotation
E1 = (0, 2, 10, 8)                     # corner e1 bits c0..c3 (end bits of links b, b, t, t)
E2 = (12, 4, 6, 14)                    # corner e2 = e_X ^ e_Y
CH2 = ((1, 13), (1, 5), (9, 5), (9, 13))   # (g, g) controls of the C2H
GD = (13, 5, 5, 13)                    # g_c ^ delta_c of the e1 link, read from the L2 flags before their conversion
TST = (15, 5, 9, 13)                   # corner test registers = delta_c0..c3 qubits (tested in place)
_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}


def g(n, *qs, p=()):
    return (n, tuple(p), tuple(qs))


def inv(ops):
    out = []
    for name, p, qs in reversed(ops):
        if name in _INV:
            out.append((_INV[name], p, qs))
        elif name in ("rz", "p", "crx", "crz", "cp"):
            out.append((name, (-p[0],), qs))
        else:
            out.append((name, p, qs))      # cx, ccx, rccx, ch, ccz, h, x are self-inverse
    return out


def neg(qs, body):
    return [g("x", q) for q in qs] + body + [g("x", q) for q in qs]


def cch_rel(a, b, t):
    """controlled-controlled-H up to the control phase (-i)^(a b): Ry(pi/4) [CCZ . CS^dag(a, b)] Ry(-pi/4) (4 CX)."""
    o = [g(n, t) for n in ("sdg", "h", "tdg", "h")]
    o += [g("t", t), g("cx", a, t), g("tdg", t), g("cx", b, t), g("t", t), g("cx", a, t), g("tdg", t), g("cx", b, t)]
    o += [g(n, t) for n in ("h", "t", "h", "s")]
    return o


def cch(a, b, t):
    """exact controlled-controlled-H = Ry(pi/4) CCZ Ry(-pi/4)."""
    return [g(n, t) for n in ("sdg", "h", "tdg", "h")] + [g("ccz", a, b, t)] + [g(n, t) for n in ("h", "t", "h", "s")]


def ry(sgn, t):
    """Ry(+-pi/4) up to a global phase, in time order: S^dag, H, T^(+-1), H, S."""
    return [g("sdg", t), g("h", t), g("t" if sgn > 0 else "tdg", t), g("h", t), g("s", t)]


def margolus(a, b, t, v):
    """Toffoli(a, b -> t) up to the single phase -1 on the input (a, b, t) = (1, 0, v); 3 CX."""
    s = 1 if v == 1 else -1
    return ry(s, t) + [g("cx", b, t)] + ry(s, t) + [g("cx", a, t)] + ry(-s, t) + [g("cx", b, t)] + ry(-s, t)


def frame():
    D = [g("cx", 1, q) for q in (11, 15)]                                       # R2 of t, l: q11 = r_t, q15 = r_l
    # h_b into the raw R2 of link b (q3 = q2 ^ F on valid codes): h_b = q3 ^ F (q2 ^ y), y = r_r ? q6 : (r_t ? q8 : q12)
    # (raw end bits of a non-Q link; r_r = !g_r when F = 1), two in-place rccx Fredkin halves into q12, then the Toffoli
    # F & q12 -> q3 as a Margolus gate (phase -1 on (F, q12, q3) = (1, 0, 1)) gauged by CZ(q3, q4): exact up to one
    # coupling sign common to all open pairs
    pre = [g("cx", 12, 8), g("rccx", 11, 8, 12), g("cx", 12, 6)] + neg((5,), [g("rccx", 5, 6, 12)]) + [g("cx", 2, 12)]
    D += pre + margolus(F, 12, 3, 1) + [g("cz", 3, 4)] + inv(pre)
    D += [g("cx", 0, 12), g("cx", 2, 4), g("cx", 10, 6), g("cx", 8, 14)]        # e2 = e_X ^ e_Y per corner
    # tau fix e1_c ^= h_X (+1 at c0, c2); q3 = h_b -> h_t = h_b ^ r_t for the two t ends
    D += [g("x", 0), g("x", 10), g("cx", 3, 0), g("cx", 3, 2), g("cx", 11, 3), g("cx", 3, 10), g("cx", 3, 8)]
    for (ga, gb), e1 in zip(CH2, E1):
        D += cch_rel(ga, gb, e1)                                                # singlet -> basis state
    # the 16 kappa=1 dark labels that pass all corner tests: F ^= e1c3 & !e2c3 (zero on every bright label); the flipped F
    # runs through the conversions below and every such label then fails a corner test; Z(e1c3) gauges the rccx phases
    D += neg((14,), [g("rccx", 14, 8, F)]) + [g("z", 8)]
    D += [g("cx", q, e) for q, e in zip(GD, E1)] + [g("x", e) for e in E1]     # e1 ^= g ^ delta ^ 1
    D += [g("cx", 9, 13), g("cx", 5, 9), g("cx", 1, 5)]                         # q13, q9, q5 = delta_c3, c2, c1
    D += neg((11, 7), [g("rccx", 11, 7, U)]) + neg((15,), [g("rccx", U, 15, Z)])   # U = [r_t = 0 = r_rl], Z = [r = 000]
    # closed gadget: H on q3 ((vac_A +- vac_B)/sqrt2 -> q3 = 0 / 1; q3 is never read on Z = 0), loop: H on e1c0 (Z and
    # F), closed dark (q3 = 1) -> e1c0 flip
    D += [g("h", 3)] + cch(Z, 1, 0) + [g("rccx", Z, 3, 0)]
    return D


def flags():
    """bright <=> every corner test register delta_c ^ (e2_c & e1_c) is 1 (exact on all reachable labels)."""
    M = []
    for c in range(4):
        M.append(g("rccx", E2[c], E1[c], TST[c]))
    M += [g("rccx", TST[0], TST[1], N1), g("rccx", TST[2], TST[3], N2), g("rccx", N1, N2, XF)]
    return M


def wq():
    """W = prod_c CH(!e2_c -> e1_c): maps Q = prod_c X^(!e2_c) Z^(e2_c) (on e1_c) to Z_E = prod_c Z(e1_c); W = W^dag."""
    o = []
    for c in range(4):
        o += neg((E2[c],), [g("ch", E2[c], E1[c])])
    return o


def rotation(beta):
    """exp(i theta X_F Z_E), theta = beta X v(U, Z): v = -2 (U = 0), -1 (U = 1, Z = 0), +4 sqrt2 (Z = 1);
    v = a + b s_U + c s_Z (v(U=0, Z=1) never occurs), 6 Walsh terms on one Gray cycle."""
    vc = 4 * math.sqrt(2.0)
    f = {"": (vc - 2) / 2, "U": -0.5, "Z": (-1 - vc) / 2}
    c = {}
    for k, v in f.items():
        c[k] = beta * v / 2
        c["X" + k] = -beta * v / 2
    R = [g("h", F)] + [g("cx", e, F) for e in E1]
    Q = {"U": U, "X": XF, "Z": Z}
    par = set()

    def rz():
        key = ("X" if "X" in par else "") + ("U" if "U" in par else "") + ("Z" if "Z" in par else "")
        R.append(g("rz", F, p=(-2 * c[key],)))
    rz()
    for ch in ("U", "X", "U", "Z", "X"):
        R.append(g("cx", Q[ch], F)); par.symmetric_difference_update({ch}); rz()
    R.append(g("cx", Q["Z"], F))
    R += [g("cx", e, F) for e in E1]
    R.append(g("h", F))
    return R


def ops(alpha, beta):
    prep = []
    for l in range(4):
        prep += [g("cx", 4 * l, 4 * l + 1)] + ([g("cx", 4 * l + 2, 4 * l + 3)] if l >= 2 else [])  # L2 = g; R2 = g (t, l)
    prep += [g("cx", 6, 7), g("cx", 13, 7)]                                    # R2 of link r -> r_r ^ r_l
    ue = [g("p", 4 * l + 1, p=(-0.75 * alpha,)) for l in range(4)]
    D = frame()
    M = flags()
    hd = wq() + rotation(beta) + wq()               # exp(i theta Pi) = W exp(i theta X_F Z_E) W, Pi = X_F Q
    return prep + ue + D + M + hd + inv(M) + inv(D) + inv(prep)


def build(spec) -> Builder:
    b = Builder(spec)
    anc = b.alloc(NANC, "work")
    q = lambda i: i if i < 16 else anc[i - 16]
    for name, p, qs in ops(spec.alpha, spec.beta):
        getattr(b, name)(*p, *[q(i) for i in qs])
    return b
