"""SUMMARY: F3 controlled partner involution in CH form with the kappa selector (parent r04-F3-003), but the exact 6-CX closed CCH(Z, F -> e1c0) is gone: U = [r_t = 0 = r_r^r_l] and Z = [r = 000] are computed right after the tau fix, the corner C2H at c1, c2, c3 run as before, and the c0 C2H (controls F, q13 = g_l) is skipped on the closed sector by toggling q13 ^= Z around it (2 CX) - on the loop it only made the e1c0 superposition that the CCH undid (H X X H = X X); T(q13) before and T^dag(q13) after the first CX(Z -> q13) restore the lost (-i) relative phase on the loop (a controlled-S(F, Z) without CX), so all 81 couplings stay real and uniform per class (closed sign flipped, Walsh closed coefficient negated); rest as the parent: frame (L2 = Q flag, U_E as 4 phases on L2; h_b by two in-place rccx Fredkin halves + a Margolus Toffoli with a CZ(h_b, r.L1) gauge; one CX per corner; tau fix; one kappa=1 dark-label fold rccx(e1c3, !e2c3 -> F); e1 ^= g^delta^1; H(q3) and the closed-dark mark rccx(Z, q3 -> e1c0)), exp(i theta Pi) = W exp(i theta X_F Z_E) W with W = 4 CH(!e2 -> e1), bright flag X = AND of 4 in-place corner tests, 6-term Gray-cycle Walsh rotation on F over (X, U, Z); 220 CX (-8), T_fixed 196 (-14); all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: the exact closed CCH(Z, F -> e1c0) of the F3 frame only undoes the corner-c0 C2H on the loop (the all-Q mux garbage h is l's colour bit at c0, so the tau fix leaves the loop's e1c0 a basis bit and the c0 C2H turns it into |+->); skipping that C2H on Z = 1 by a CX(Z -> g_l) pair around it costs 2 CX instead of 6, and the missing relative phase (-i) on the loop (which would make only the closed coupling imaginary) comes back for free from T before and T^dag after the first CX: e^{i pi/4 g_l} e^{-i pi/4 (g_l ^ Z)} = e^{-i pi/4 Z} i^(F Z) on reachable labels (Z = 1 implies g_l = F).
DISCOVERY: tried and failed (exact checks over all 1296 codes): keeping q13 = g_l ^ Z (or r_l ^ Z, or F ^ Z for the other control pairs (F, !r_l), (g_l, !r_l)) to save the restore CX, with any single rccx(Z, q3 or !q3 -> t) closed-dark mark (dark all-Q labels with e2c0 = 0 or e2c3 = 0 then pass the corner tests); any 1- or 2-CX fold (CX or parity into any register, at any point after the C2H) instead of the kappa=1 rccx fold; any 1-3 single-qubit Z/S/T phases at any time instead of the CZ(q3, q4) Margolus gauge; one rccx doing both the kappa=1 fold and the closed-dark mark.
"""
FAMILY = "F3"
PARENT = "r04-F3-003"

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
    D += neg((11, 7), [g("rccx", 11, 7, U)]) + neg((15,), [g("rccx", U, 15, Z)])   # U = [r_t = 0 = r_rl], Z = [r = 000]
    for c in (1, 2, 3):
        D += cch_rel(*CH2[c], E1[c])                                            # singlet -> basis state
    # c0 C2H with control q13 = g_l ^ Z: skipped on the loop (F = g_l = 1, Z = 1), unchanged elsewhere; T / T^dag around
    # the first CX give e^{i pi/4 g_l} e^{-i pi/4 (g_l ^ Z)} = e^{-i pi/4 Z} i^(F Z) (Z = 1 implies g_l = F), the (-i)
    # relative phase that the skipped cch_rel no longer puts on the loop
    D += [g("t", 13), g("cx", Z, 13), g("tdg", 13)]
    D += cch_rel(*CH2[0], E1[0]) + [g("cx", Z, 13)]
    # the 16 kappa=1 dark labels that pass all corner tests: F ^= e1c3 & !e2c3 (zero on every bright label); the flipped F
    # runs through the conversions below and every such label then fails a corner test; Z(e1c3) gauges the rccx phases
    D += neg((14,), [g("rccx", 14, 8, F)])
    D += [g("cx", q, e) for q, e in zip(GD, E1)] + [g("x", e) for e in E1]     # e1 ^= g ^ delta ^ 1
    D += [g("cx", 9, 13), g("cx", 5, 9), g("cx", 1, 5)]                         # q13, q9, q5 = delta_c3, c2, c1
    # closed gadget: H on q3 ((vac_A +- vac_B)/sqrt2 -> q3 = 0 / 1; q3 is never read on Z = 0); closed dark (q3 = 1) ->
    # e1c0 flip (the loop needs no CCH any more: its c0 C2H was skipped above)
    D += [g("h", 3)] + [g("rccx", Z, 3, 0)]
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
    """exp(i theta X_F Z_E), theta = beta X v(U, Z): v = -2 (U = 0), -1 (U = 1, Z = 0), -4 sqrt2 (Z = 1);
    v = a + b s_U + c s_Z (v(U=0, Z=1) never occurs), 6 Walsh terms on one Gray cycle."""
    vc = 4 * math.sqrt(2.0)
    f = {"": (-2 - vc) / 2, "U": -0.5, "Z": (vc - 1) / 2}
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
