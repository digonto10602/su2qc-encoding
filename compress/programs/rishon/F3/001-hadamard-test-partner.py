"""SUMMARY: F3 controlled partner involution, no canonicaliser: light frame (L2 = Q flag, U_E as 4 phases on L2; R2 slots as h_b / r_t / r_l / r_r^r_l registers; h_b by two in-place rccx Fredkin halves + one Toffoli into the raw R2 of link b; one CX per corner; tau fix CX(h_X -> e1); 4 relative-phase C2H; e1 ^= g^delta^1 with one CX per corner; closed gadget H(q3), CCH(Z,F), rccx) makes the partner map the involution Pi = X_F Q, Q = prod_c X^(!e2_c) on e1_c, with every one of the 81 couplings +1 (closed -1); exp(i theta Pi) = cQ exp(i theta X_F) cQ (Hadamard-test identity with the flip qubit F as the test qubit), cQ = 4 S-conjugated rccx(F, !e2, e1); bright flag = AND of 4 in-place corner tests delta_c ^ (e2 & e1) plus two kappa=1 folds; 10-term Gray-path Walsh rotation on F over (X, Z, r_t, r_r^r_l); all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: an rccx(F, m, e1) between S and S^dag acts on the F=1 branch as X^m Z^(1-m) on e1 (a real Hermitian involution), so cQ exp(i theta X_F) cQ = exp(i theta X_F Q) is an exact controlled-partner rotation at 12 CX per cQ whenever e1 = 0 at every e2 = 1 corner of a bright label; no canonical bits n_c = e1 ^ g e2 (the F1 canonicaliser) are ever formed.
DISCOVERY: in this frame the bright set is exactly {delta_c ^ (e2_c & e1_c) = 1 at all four corners} (T+- at equal corners and wrong orientations are caught by the same mux test) except 16 kappa=1 dark labels, killed by the frame-A products e1c0&!e2c0 and e1c3&!g_t folded into the c1 test; the kappa class needs no selector bit: k(r) = [r=101] + [r=000] = (1 + s_t + s_rl + s_rlt)/4 is a 4-term Walsh sum over two parity qubits.
DISCOVERY: raw R2 slots are free registers once neutralised (R2 = R1 ^ g on valid codes): link b's R2 becomes h_b with one Toffoli (h_b = q3 ^ F(q2 ^ y)), link r's R2 becomes r_r ^ r_l with CX(R1), CX(g_l); and H on q3 (never read on non-closed labels) replaces the closed CH(Z, q3).
"""
FAMILY = "F3"
PARENT = None

import math

from su2plaq.compress.builder import Builder

# ancilla slots (symbolic 16.., remapped to allocated qubits in build)
T1, N1, N2, XF, U, Z = range(16, 22)
NANC = 6
F = 1                                  # flip qubit (= g_b), also the control of the partner involution
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
            out.append((name, p, qs))      # cx, ccx, rccx, ch, h, x are self-inverse
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


def frame():
    D = [g("cx", 1, q) for q in (11, 15)]                                       # R2 of t, l: q11 = r_t, q15 = r_l
    # h_b into the raw R2 of link b (q3 = q2 ^ F on valid codes): h_b = q3 ^ F (q2 ^ y), y = r_r ? q6 : (r_t ? q8 : q12)
    # (raw end bits of a non-Q link; r_r = !g_r when F = 1), two in-place rccx Fredkin halves into q12, one Toffoli
    pre = [g("cx", 12, 8), g("rccx", 11, 8, 12), g("cx", 12, 6)] + neg((5,), [g("rccx", 5, 6, 12)]) + [g("cx", 2, 12)]
    D += pre + [g("ccx", 1, 12, 3)] + inv(pre)
    D += [g("cx", 0, 12), g("cx", 2, 4), g("cx", 10, 6), g("cx", 8, 14)]        # e2 = e_X ^ e_Y per corner
    # tau fix e1_c ^= h_X (+1 at c0, c2); q3 = h_b -> h_t = h_b ^ r_t for the two t ends
    D += [g("x", 0), g("x", 10), g("cx", 3, 0), g("cx", 3, 2), g("cx", 11, 3), g("cx", 3, 10), g("cx", 3, 8)]
    for (ga, gb), e1 in zip(CH2, E1):
        D += cch_rel(ga, gb, e1)                                                # singlet -> basis state
    # kappa=1 dark labels: e1 & !e2 at c0, e1 & !g_t at c3 (both zero on every bright label) -> T1
    D += neg((12,), [g("rccx", 0, 12, T1)]) + neg((9,), [g("rccx", 8, 9, T1)])
    D += [g("cx", q, e) for q, e in zip(GD, E1)] + [g("x", e) for e in E1]     # e1 ^= g ^ delta ^ 1
    D += [g("cx", 9, 13), g("cx", 5, 9), g("cx", 1, 5)]                         # q13, q9, q5 = delta_c3, c2, c1
    D += neg((5, 9, 13), [g("rccx", 5, 9, U), g("rccx", U, 13, Z)])             # Z = [r = 000]
    # closed gadget: H on q3 ((vac_A +- vac_B)/sqrt2 -> q3 = 0 / 1; q3 is never read on Z = 0), loop: H on e1c0 (Z and
    # F), closed dark (q3 = 1) -> e1c0 flip
    D += [g("h", 3)] + cch(Z, 1, 0) + [g("rccx", Z, 3, 0)]
    return D


def flags():
    """bright <=> every corner test register delta_c ^ (e2_c & e1_c) (^ the kappa=1 folds at c1) is 1."""
    M = [g("cx", T1, 5)]
    for c in range(4):
        M.append(g("rccx", E2[c], E1[c], TST[c]))
    M += [g("rccx", TST[0], TST[1], N1), g("rccx", TST[2], TST[3], N2), g("rccx", N1, N2, XF)]
    return M


def cq():
    """F-controlled e-part Q of the partner involution: on F = 1, per corner X (e2 = 0) / Z (e2 = 1) on e1 (S-conjugated
    rccx: on its firing branch Y -> X, on c1 = 1, c2 = 0 the -1 phase is the Z); Q is a real Hermitian involution."""
    o = []
    for c in range(4):
        o += [g("s", E1[c])] + neg((E2[c],), [g("rccx", F, E2[c], E1[c])]) + [g("sdg", E1[c])]
    return o


def rotation(beta):
    """exp(i theta X_F), theta = beta X (2 - k(r) + cz Z) with k = [r=101] + [r=000] = (1 + s_t + s_r s_l + s_r s_l s_t)/4
    (s = (-1)^bit) and cz = -4 sqrt2 - 1 (closed coupling sign -1 in this frame): 10 Walsh terms on a Gray path."""
    cz = -4 * math.sqrt(2.0) - 1
    f = {"": 2 - 0.25 + cz / 2, "t": -0.25, "rl": -0.25, "rlt": -0.25, "Z": -cz / 2}
    c = {}
    for k, v in f.items():
        c[k] = beta * v / 2
        c["X" + k] = -beta * v / 2
    R = [g("h", F)]
    par = set()
    Q = {"t": 11, "rl": 7, "X": XF, "Z": Z}             # q7 = r_r ^ r_l, q11 = r_t

    def tog(ch):
        R.append(g("cx", Q[ch], F))
        par.symmetric_difference_update(set(ch) if ch == "rl" else {ch})

    def rz():
        key = ("X" if "X" in par else "") + "".join(ch for ch in "rlt" if ch in par) + ("Z" if "Z" in par else "")
        R.append(g("rz", F, p=(-2 * c[key],)))    # exp(i c Z_parity) = Rz(-2c)
    rz()
    tog("t"); rz()
    tog("rl"); rz()
    tog("t"); rz()
    tog("X"); rz()
    tog("t"); rz()
    tog("rl"); rz()
    tog("t"); rz()
    tog("Z"); rz()
    tog("X"); rz()
    tog("Z")
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
    hd = cq() + rotation(beta) + cq()                 # exp(i theta Pi) = cQ exp(i theta X_F) cQ, Pi = X_F Q
    return prep + ue + D + M + hd + inv(M) + inv(D) + inv(prep)


def build(spec) -> Builder:
    b = Builder(spec)
    anc = b.alloc(NANC, "work")
    q = lambda i: i if i < 16 else anc[i - 16]
    for name, p, qs in ops(spec.alpha, spec.beta):
        getattr(b, name)(*p, *[q(i) for i in qs])
    return b
