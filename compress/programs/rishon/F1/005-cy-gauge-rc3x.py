"""SUMMARY: F1 round 5 on the parent r04-F1-004 (F3 controlled-partner frame with the (P, Z) class selector, 6-term Walsh rotation on F): same frame, flags and partner rotation, but the Margolus h_b Toffoli is gauged by CZ(q3, q2) placed right after the tau-fix CX(q3 -> q2), where CZ.CX = S(q3) CY(q3 -> q2) is one CX (-2 CX), the 4-input AND of the corner tests is rccx + one Maslov relative-phase C3X instead of 3 rccx (same CX and T, one ancilla fewer), and the U_E phases sit on the g_r copy in the raw R2 of link r (CX(13, 7) after it) and on g_b after the h_b Toffoli (shorter Clifford+T depth); all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: the h_b Margolus gauge has a free merge: a CZ on (q3, q2) directly after the tau-fix CX(q3 -> q2), with no CZ(q3, q4), keeps every coupling sign uniform (the only one of the 2 x 43 placements next to a frame CX on the same pair that does), and CZ(a, b) CX(a -> b) = S(a) CY(a -> b) with CY = S(b) CX Sdg(b), one CX; no single 2-qubit gate of the frame or flags can be deleted, no CX deleted with a merged CZ added, and no Toffoli replaced by CX/X (exhaustive local checks).
DISCOVERY: relative phases of the bright-flag AND tree only need to depend on registers that the partner rotation leaves invariant (tests, N1, XF), so the Maslov RC3X (6 CX, 8 T, phases i, -i, -1 on control/target patterns) replaces rccx(T2, T3 -> N2) + rccx(N1, N2 -> XF) at equal CX and T and frees the N2 ancilla (53 -> 52 qubits).
"""
FAMILY = "F1"
PARENT = "r04-F1-004"

import math

from su2plaq.compress.builder import Builder

# ancilla slots (symbolic 16.., remapped to allocated qubits in build)
N1, XF, U, Z = range(16, 20)
NANC = 4
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


def frame(ue=()):
    # q11 = r_t, q15 = r_l (R2 of t, l); q7 = g_r -> r_r ^ r_l (R2 of link r; its U_E phase was applied while it held g_r)
    D = [g("cx", 1, 11), g("cx", 13, 7), g("cx", 1, 15)]
    # h_b into the raw R2 of link b (q3 = q2 ^ F on valid codes): h_b = q3 ^ F (q2 ^ y), y = r_r ? q6 : (r_t ? q8 : q12)
    # (raw end bits of a non-Q link; r_r = !g_r when F = 1), two in-place rccx Fredkin halves into q12, then the Toffoli
    # F & q12 -> q3 as a Margolus gate (phase -1 on (F, q12, q3) = (1, 0, 1)), gauged by a CZ(q3, q2) after the tau-fix
    # CX(q3 -> q2) below (merged with it into S(q3) CY(q3 -> q2), one CX): exact up to one coupling sign common to all open
    # pairs.  The U_E phase of g_b sits on F right after the Toffoli (F is only a control up to the fold).
    pre = [g("cx", 12, 8), g("rccx", 11, 8, 12), g("cx", 12, 6)] + neg((5,), [g("rccx", 5, 6, 12)]) + [g("cx", 2, 12)]
    D += pre + margolus(F, 12, 3, 1) + list(ue) + inv(pre)
    D += [g("cx", 0, 12), g("cx", 2, 4), g("cx", 10, 6), g("cx", 8, 14)]        # e2 = e_X ^ e_Y per corner
    # tau fix e1_c ^= h_X (+1 at c0, c2); q3 = h_b -> h_t = h_b ^ r_t for the two t ends; at c1 the CX(q3 -> q2) carries
    # the h_b gauge: CZ(q3, q2) . CX(q3 -> q2) = S(q3) . [S(q2) CX(q3 -> q2) Sdg(q2)] (time order Sdg, CX, S)
    D += [g("x", 0), g("x", 10), g("cx", 3, 0)] + [g("sdg", 2), g("cx", 3, 2), g("s", 2), g("s", 3)]
    D += [g("cx", 11, 3), g("cx", 3, 10), g("cx", 3, 8)]
    for (ga, gb), e1 in zip(CH2, E1):
        D += cch_rel(ga, gb, e1)                                                # singlet -> basis state
    # the 16 kappa=1 dark labels that pass all corner tests: F ^= e1c3 & !e2c3 (zero on every bright label); the flipped F
    # runs through the conversions below and every such label then fails a corner test; Z(e1c3) gauges the rccx phases
    D += neg((14,), [g("rccx", 14, 8, F)]) + [g("z", 8)]
    D += [g("cx", q, e) for q, e in zip(GD, E1)] + [g("x", e) for e in E1]     # e1 ^= g ^ delta ^ 1
    D += [g("cx", 9, 13), g("cx", 5, 9), g("cx", 1, 5)]                         # q13, q9, q5 = delta_c3, c2, c1
    D += neg((11, 7), [g("rccx", 11, 7, U)]) + neg((15,), [g("rccx", U, 15, Z)])   # U = P = [r_t = 0, r_r = r_l], Z = P & !r_l
    # closed gadget: H on q3 ((vac_A +- vac_B)/sqrt2 -> q3 = 0 / 1; q3 is never read on Z = 0), loop: H on e1c0 (Z and
    # F), closed dark (q3 = 1) -> e1c0 flip
    D += [g("h", 3)] + cch(Z, 1, 0) + [g("rccx", Z, 3, 0)]
    return D


def rc3x(a, b, c, t):
    """Maslov relative-phase C3X (6 CX, 8 T): phases on control/target values only, cancelled by its mirror."""
    o = [g("h", t), g("t", t), g("cx", c, t), g("tdg", t), g("h", t), g("cx", a, t), g("t", t), g("cx", b, t), g("tdg", t)]
    o += [g("cx", a, t), g("t", t), g("cx", b, t), g("tdg", t), g("h", t), g("t", t), g("cx", c, t), g("tdg", t), g("h", t)]
    return o


def flags():
    """bright <=> every corner test register delta_c ^ (e2_c & e1_c) is 1 (exact on all reachable labels)."""
    M = []
    for c in range(4):
        M.append(g("rccx", E2[c], E1[c], TST[c]))
    M += [g("rccx", TST[0], TST[1], N1)] + rc3x(N1, TST[2], TST[3], XF)
    return M


def wq():
    """W = prod_c CH(!e2_c -> e1_c): maps Q = prod_c X^(!e2_c) Z^(e2_c) (on e1_c) to Z_E = prod_c Z(e1_c); W = W^dag."""
    o = []
    for c in range(4):
        o += neg((E2[c],), [g("ch", E2[c], E1[c])])
    return o


def rotation(beta):
    """exp(i theta X_F Z_E), theta = beta [X] psi(P, Z), psi = -2 (P = 0), -1 (P = 1, Z = 0), 4 sqrt2 (Z = 1);
    on the occurring patterns psi = a + b X_P + c X_Z: 6 Walsh terms on one Gray cycle inside H(F)."""
    vc = 4 * math.sqrt(2.0)
    f = {"": (vc - 2) / 2, "P": -0.5, "Z": (-1 - vc) / 2}
    c = {}
    for k, v in f.items():
        c[k] = beta * v / 2
        c["X" + k] = -beta * v / 2
    R = [g("h", F)] + [g("cx", e, F) for e in E1]
    Q = {"P": U, "X": XF, "Z": Z}
    par = set()
    def rz():
        key = ("X" if "X" in par else "") + ("P" if "P" in par else "") + ("Z" if "Z" in par else "")
        R.append(g("rz", F, p=(-2 * c[key],)))
    rz()
    for ch in ("P", "X", "P", "Z", "X"):
        R.append(g("cx", Q[ch], F)); par.symmetric_difference_update({ch}); rz()
    R.append(g("cx", Q["Z"], F))
    R += [g("cx", e, F) for e in E1]
    R.append(g("h", F))
    return R


def prep(ph=None):
    """L2 = g for all links, R2 = g for t, l, R2 of link r = g_r; with ph the U_E phases of g_t, g_l, g_r are applied as
    soon as the flag exists (g_b's phase follows the h_b Toffoli in the frame)."""
    P = lambda q: [g("p", q, p=(ph,))] if ph is not None else []
    o = [g("cx", 0, 1), g("cx", 4, 5), g("cx", 8, 9)] + P(9) + [g("cx", 10, 11), g("cx", 12, 13)] + P(13)
    o += [g("cx", 14, 15), g("cx", 6, 7)] + P(7)
    return o


def ops(alpha, beta):
    ph = -0.75 * alpha                              # U_E = exp(-i 3/4 alpha #Q): one phase per Q flag, applied once
    fwd = prep(ph) + frame(ue=[g("p", F, p=(ph,))])
    bwd = inv(prep() + frame())
    M = flags()
    hd = wq() + rotation(beta) + wq()               # exp(i theta Pi) = W exp(i theta X_F Z_E) W, Pi = X_F Q
    return fwd + M + hd + inv(M) + bwd


def build(spec) -> Builder:
    b = Builder(spec)
    anc = b.alloc(NANC, "work")
    q = lambda i: i if i < 16 else anc[i - 16]
    for name, p, qs in ops(spec.alpha, spec.beta):
        getattr(b, name)(*p, *[q(i) for i in qs])
    return b
