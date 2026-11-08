"""SUMMARY: F1 round 4 on the F3 controlled-partner frame (parent r03-F3-002) with the class selector of the F1 line: frame, CH partner W Z_E W, single dark-label fold onto F, Margolus+CZ h_b Toffoli, 4 relative-phase C2H, closed gadget and the AND of 4 in-place corner tests as in the parent, but the closed-sector flag is built as Z = P & !r_l from the selector P = [r_t = 0 and r_r = r_l] = rccx(!r_t, !(r_r ^ r_l)) (same 6 CX as the delta chain it replaces), so the class-signed angle psi(P, Z) = -2, -1, 4 sqrt2 needs 3 Walsh terms instead of 5: the rotation on F is 6 Gray-cycle terms over (X, P, Z) instead of 10 (-4 CX, -4 rotations); all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: the angle of every bright pair depends only on (P, Z) with P = [r_t = 0 and r_r = r_l] = [r in {000, 101}] (r = 101 is the kappa = 1 class, r = 000 the closed pair, all other classes kappa = 2 with one common coupling sign); on the occurring patterns (Z = 1 implies P = 1) psi = (4 sqrt2 - 2)/2 - 1/2 X_P - (1 + 4 sqrt2)/2 X_Z, so the X-controlled rotation needs 6 Walsh terms, and P costs nothing extra because it replaces the intermediate !d1 & !d2 of the Z chain (Z = P & !r_l).
DISCOVERY: rccx-based Toffoli toggles rccx(N1, N2 -> F) in the Gray path (instead of computing XF) leave the phase (-1)^(N1 p), p the parity of the controls toggled between the two X toggles; in a 2-register (P, Z) cube the X block's endpoints always differ in both registers, so the fix needs 2 CZ and the trick nets 0 CX.
"""
FAMILY = "F1"
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
    D += neg((11, 7), [g("rccx", 11, 7, U)]) + neg((15,), [g("rccx", U, 15, Z)])   # U = P = [r_t = 0, r_r = r_l], Z = P & !r_l
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
