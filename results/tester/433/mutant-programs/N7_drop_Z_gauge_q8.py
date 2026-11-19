"""SUMMARY: F3 controlled partner involution in CH form with the kappa selector and the skipped loop c0 C2H (parent r05-F3-005), with the closed-dark mark merged into the g_l restore: H(q3) now follows the tau fix directly, and the second CX(Z -> q13) around the skipped c0 C2H becomes rccx(Z, !q3 -> q13), so the closed dark (q3 = 1) keeps g_l toggled and fails a corner test while the closed bright pair is restored; the separate rccx(Z, q3 -> e1c0) is gone (-1 CX per side) and the rccx phase only flips the closed coupling sign (Walsh closed coefficient v = +4 sqrt2); two savings of r05-F1-005 carry over: the h_b Margolus gauge is CZ(q3, q2) merged into the tau-fix CX(q3 -> q2) as S(q3) CY(q3 -> q2) instead of CZ(q3, q4) (-1 CX per side), and the 4-input AND of the corner tests is rccx + a Maslov RC3X (one ancilla fewer); the U_E phases sit on each Q flag as soon as it exists (g_r on its copy in q7, g_b right after the h_b Toffoli) for a shorter Clifford+T depth; rest as the parent (U = [r_t = 0 = r_r^r_l], Z = [r = 000], T / T^dag around the first CX(Z -> q13), one kappa=1 fold rccx(e1c3, !e2c3 -> F), exp(i theta Pi) = W exp(i theta X_F Z_E) W with W = 4 CH(!e2 -> e1), 6-term Gray-cycle Walsh rotation on F over (X, U, Z)); 216 CX (-4), T_eps 832 (-8), depth_CT 1350, 52 qubits (-1); all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: the closed-dark mark of the F3 frame is free once H(q3) precedes the c0 C2H skip: the restore CX(Z -> g_l) becomes rccx(Z, !q3 -> g_l) (+2 CX, -3 for the mark), the closed dark keeps g_l ^ 1, which the GD and delta conversions carry into the corner tests (it fails one), every other all-Q dark label still fails, and the rccx relative phase only negates the closed coupling (absorbed in the Walsh table); toggling F instead of g_l for the skip fails (magnitude error 0.24).
DISCOVERY: the conditional restore cannot also absorb the kappa=1 fold: an exhaustive search over all 630 two-literal rccx restores into q13 at 3 positions without the fold gives magnitude error >= 0.66, and no single frame CX made conditional (rccx with a literal true on all bright labels, 136 candidates), redirected to a control equal on all bright labels, or doubled by a CX from a qubit zero on all bright labels kills the 16 kappa=1 dark labels (best 0.18).
DISCOVERY: U = [r_t = 0 = r_r^r_l] needs the r_r^r_l register: no AND of two single-qubit literals (q7 excluded) equals U on the components of the 306 bright codes at the point where U is formed, so the cx(6, 7), cx(13, 7) preparation cannot be dropped; no single symmetric gate deletion of the 216-CX circuit stays exact.
"""
FAMILY = "F3"
PARENT = "r05-F3-005"

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


def ry(sgn, t):
    """Ry(+-pi/4) up to a global phase, in time order: S^dag, H, T^(+-1), H, S."""
    return [g("sdg", t), g("h", t), g("t" if sgn > 0 else "tdg", t), g("h", t), g("s", t)]


def margolus(a, b, t, v):
    """Toffoli(a, b -> t) up to the single phase -1 on the input (a, b, t) = (1, 0, v); 3 CX."""
    s = 1 if v == 1 else -1
    return ry(s, t) + [g("cx", b, t)] + ry(s, t) + [g("cx", a, t)] + ry(-s, t) + [g("cx", b, t)] + ry(-s, t)


def frame(ue=()):
    D = [g("cx", 1, q) for q in (11, 15)]                                       # R2 of t, l: q11 = r_t, q15 = r_l
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
    # closed gadget: H on q3 ((vac_A +- vac_B)/sqrt2 -> q3 = 0 / 1; q3 is never read on Z = 0 except by the restore below)
    D += [g("h", 3)]
    D += neg((11, 7), [g("rccx", 11, 7, U)]) + neg((15,), [g("rccx", U, 15, Z)])   # U = [r_t = 0 = r_rl], Z = [r = 000]
    for c in (1, 2, 3):
        D += cch_rel(*CH2[c], E1[c])                                            # singlet -> basis state
    # c0 C2H with control q13 = g_l ^ Z: skipped on the loop (F = g_l = 1, Z = 1), unchanged elsewhere; T / T^dag around
    # the first CX give e^{i pi/4 g_l} e^{-i pi/4 (g_l ^ Z)} = e^{-i pi/4 Z} i^(F Z) (Z = 1 implies g_l = F), the (-i)
    # relative phase that the skipped cch_rel no longer puts on the loop
    D += [g("t", 13), g("cx", Z, 13), g("tdg", 13)]
    # restore q13 ^= Z only where q3 = 0 (closed bright pair): the closed dark (q3 = 1) keeps q13 = g_l ^ 1 and fails a
    # corner test after the conversions below (replaces the separate closed-dark mark rccx(Z, q3 -> e1c0)); the rccx
    # relative phase negates the closed coupling (Walsh closed coefficient +4 sqrt2)
    D += cch_rel(*CH2[0], E1[0]) + neg((3,), [g("rccx", Z, 3, 13)])
    # the 16 kappa=1 dark labels that pass all corner tests: F ^= e1c3 & !e2c3 (zero on every bright label); the flipped F
    # runs through the conversions below and every such label then fails a corner test; Z(e1c3) gauges the rccx phases
    D += neg((14,), [g("rccx", 14, 8, F)]) + []
    D += [g("cx", q, e) for q, e in zip(GD, E1)] + [g("x", e) for e in E1]     # e1 ^= g ^ delta ^ 1
    D += [g("cx", 9, 13), g("cx", 5, 9), g("cx", 1, 5)]                         # q13, q9, q5 = delta_c3, c2, c1
    return D


def flags():
    """bright <=> every corner test register delta_c ^ (e2_c & e1_c) is 1 (exact on all reachable labels)."""
    M = []
    for c in range(4):
        M.append(g("rccx", E2[c], E1[c], TST[c]))
    M += [g("rccx", TST[0], TST[1], N1)] + rc3x(N1, TST[2], TST[3], XF)
    return M


def rc3x(a, b, c, t):
    """Maslov relative-phase C3X (6 CX, 8 T): phases on control/target values only, cancelled by its mirror."""
    o = [g("h", t), g("t", t), g("cx", c, t), g("tdg", t), g("h", t), g("cx", a, t), g("t", t), g("cx", b, t), g("tdg", t)]
    o += [g("cx", a, t), g("t", t), g("cx", b, t), g("tdg", t), g("h", t), g("t", t), g("cx", c, t), g("tdg", t), g("h", t)]
    return o


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


def prep(ph=None):
    """L2 = g for all links, R2 = g for t, l, R2 of link r = g_r ^ g_l; with ph the U_E phases of g_t, g_l, g_r are applied
    as soon as each flag exists (g_r on its copy in q7; g_b's phase follows the h_b Toffoli in the frame)."""
    P = lambda q: [g("p", q, p=(ph,))] if ph is not None else []
    o = [g("cx", 0, 1), g("cx", 4, 5), g("cx", 8, 9)] + P(9) + [g("cx", 10, 11), g("cx", 12, 13)] + P(13)
    o += [g("cx", 14, 15), g("cx", 6, 7)] + P(7) + [g("cx", 13, 7)]
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
