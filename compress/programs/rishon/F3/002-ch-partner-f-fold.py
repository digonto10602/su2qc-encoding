"""SUMMARY: F3 controlled partner involution in CH form (parent r02-F3-001): light frame (L2 = Q flag, U_E as 4 phases on L2; h_b by two in-place rccx Fredkin halves + a Margolus Toffoli with a CZ(h_b, r.L1) gauge into the raw R2 of link b; one CX per corner; tau fix CX(h_X -> e1); 4 relative-phase C2H; ONE kappa=1 dark-label fold rccx(e1c3, !e2c3 -> F) onto the flip qubit itself (no fold ancilla); e1 ^= g^delta^1; closed gadget H(q3), CCH(Z,F), rccx) maps every pair to labels related by Pi = X_F Q, Q = prod_c X^(!e2_c) Z^(e2_c) on e1_c, with the same coupling sign for all 80 open pairs; exp(i theta Pi) = W exp(i theta X_F Z_E) W, W = 4 CH(!e2 -> e1) (1 CX each), Z_E folded into the Gray path by 4 CX(e1 -> F) at each end; bright flag = AND of 4 in-place corner tests delta_c ^ (e2 & e1); 10-term class-signed Walsh rotation on F over (X, Z, r_t, r_r^r_l); all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: the controlled partner involution needs no F-controlled gate: Q = W Z_E W with W = prod_c CH(!e2_c -> e1_c) (H Z H = X at e2 = 0 corners, Z kept at e2 = 1), so exp(i theta X_F Q) = W H_F V [Walsh] V H_F W, V = prod_c CX(e1_c -> F): 2 CX per corner and side instead of 3 for the S-conjugated rccx(F, !e2, e1) (16 instead of 24 CX), and W commutes with the flag tests (they never read e1 at e2 = 0 corners).
DISCOVERY: one fold onto the flip qubit replaces both kappa=1 folds, the T1 ancilla and its CX into the c1 test: F ^= e1c3 & !e2c3 (before the GD conversion; zero on every bright label) sends each of the 16 dark labels through the GD/delta conversions to a label that fails a corner test (flag exact on all reachable labels; an exhaustive search over the 420 two-literal folds into F finds only this one); as rccx(!e2c3, e1c3 -> F) plus Z(e1c3) its relative phases give all 80 open couplings the same sign, absorbed in the Walsh table.
DISCOVERY: relative phases before the C2H can be gauged when a search over cheap corrections is exhaustive: the h_b Toffoli F & (q2 ^ y) -> q3 as a Margolus gate (phase -1 on (F, mux, q3) = (1, 0, 1)) followed by CZ(q3, q4) is exact up to one uniform coupling sign (4 CX instead of 6); of rccx / 4 Margolus variants x {Z, S, S^dag on one qubit, one CZ} only CZ(q3, q4) and CZ(q2, q3) work, and no 3-CX relative CCH replaces the closed CCH(Z, F) (its phase is i^(Z F) or a reflection on the F = 0 member).
"""
FAMILY = "F3"
PARENT = "r02-F3-001"

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
    D += neg((5, 9, 13), [g("rccx", 5, 9, U), g("rccx", U, 13, Z)])             # Z = [r = 000]
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
    """exp(i theta X_F Z_E), theta = beta [X] v(r_t, r_r^r_l, Z) with the coupling-signed values v = -1 (kappa=1 class
    (0, 0)), -2 (the three kappa=2 classes), +4 sqrt2 (closed; its coupling sign is opposite); 10 Walsh terms
    ("", t, rl, rlt, Z) x (1, X) on one Gray path inside H(F), the Z_E factor by 4 CX(e1 -> F) at both ends of the path."""
    A = {(0, 0): -1.0, (0, 1): -2.0, (1, 0): -2.0, (1, 1): -2.0}
    vc = 4 * math.sqrt(2.0)
    sgn = lambda S, t, rl: (-1) ** ((t if "t" in S else 0) + (rl if "rl" in S else 0))
    f = {}
    for k, S in (("", ()), ("t", ("t",)), ("rl", ("rl",)), ("rlt", ("rl", "t"))):
        f[k] = sum(A[(t, rl)] * sgn(S, t, rl) for t in (0, 1) for rl in (0, 1)) / 4
    f[""] += (vc - A[(0, 0)]) / 2
    f["Z"] = -(vc - A[(0, 0)]) / 2
    c = {}
    for k, v in f.items():
        c[k] = beta * v / 2
        c["X" + k] = -beta * v / 2
    R = [g("h", F)] + [g("cx", e, F) for e in E1]
    par = set()
    Q = {"t": 11, "rl": 7, "X": XF, "Z": Z}             # q7 = r_r ^ r_l, q11 = r_t

    def tog(ch):
        R.append(g("cx", Q[ch], F))
        par.symmetric_difference_update({"rl"} if ch == "rl" else {ch})

    def rz():
        key = ("X" if "X" in par else "") + ("rl" if "rl" in par else "") + ("t" if "t" in par else "") + \
              ("Z" if "Z" in par else "")
        R.append(g("rz", F, p=(-2 * c[key],)))    # exp(i c Z_parity) = Rz(-2c)
    rz()
    for ch in ("t", "rl", "t", "X", "t", "rl", "t", "Z", "X"):
        tog(ch)
        rz()
    tog("Z")
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
