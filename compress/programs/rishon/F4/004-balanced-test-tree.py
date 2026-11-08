"""SUMMARY: F4 flat direction-qubit dilation, parent r03-F4-003 unchanged except the bright test: the 8 literals (P_c = a^b, notdark_c = c or w per corner) are ANDed in a balanced rccx tree (4 + 2 + 1, same 7 rccx and 21 CX) instead of a linear chain, lowering the depth at equal CX and T; frame (3-CX cross-corner sector frame, 4-CX relative C2H, rccx+CS relabel), class flags e, k0, direction q = NAND(P_c0, P_c2), Maslov RC3X^dag lowering + CY, class-multiplexed Rx on q and the closed A<->L toggle as in the parent; all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: the F4 direction mechanism is dominated by the F3 invariant-label partner: the q-controlled lowering must skip the e1-state/S_up transition at even corners (a 3-control condition q & !(g_X g_Y) after the relabel, q & e2 & !(g_X g_Y) without it), so it costs >= 7 CX per corner and side against 1 (tau fix) + 2 (W, V) for F3; q needs the singlet already basis-ified (before the C2H the source flag (x1 | g_X)(!y1 | g_Y) is not affine on the bright corner states; after it, x1 ^ g_X !e2), so h_b = g_b ^ q cannot feed the pre-CCH tau fix, and a post-CCH tau fix flips the S label with d; estimated F4 floor >= 244 CX (> 232).
DISCOVERY: the per-corner test predicate (a^b)(c | w) has weight 6 on the 16 reachable (a, b, c, bp) labels, so no single in-place rccx literal (weights 4, 8, 12) replaces the two literals; dropping notdark at c0, c2 or c1, c3 fails (op error 1.95), and the relabel CS cannot be removed: a Margolus relabel has no gauge with Z's plus <= 4 CZ, an rccx relabel none with S's plus <= 1 CZ (exhaustive GF(2) / Z4 solves over the 80 open couplings).
"""
FAMILY = "F4"
PARENT = "r03-F4-003"

import math

from su2plaq.compress.builder import Builder

# corner c: (s1, s2, t1, t2) = source end colour 1, 2, target end colour 1, 2; K_c hops source -> target
CORNERS = [(0, 1, 12, 13), (4, 5, 2, 3), (10, 11, 6, 7), (14, 15, 8, 9)]
PREV = [3, 0, 1, 2]           # corner whose source link is the target link of corner c
_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}
ROT = ("rz", "p")


def g(n, *qs, p=()):
    return (n, tuple(p), tuple(qs))


def inv(ops):
    out = []
    for name, p, qs in reversed(ops):
        if name in _INV:
            out.append((_INV[name], p, qs))
        elif name in ROT:
            out.append((name, (-p[0],), qs))
        else:
            out.append((name, p, qs))          # cx, x, z, h, rccx, ccz are self-inverse
    return out


def neg(qs, body):
    return [g("x", q) for q in qs] + body + [g("x", q) for q in qs]


def c2h_exact(c1, c2, t):
    o = [g(n, t) for n in ("sdg", "h", "tdg", "h", "s")] + [g("ccz", c1, c2, t)]
    return o + [g(n, t) for n in ("sdg", "h", "t", "h", "s")]


def c2h_rel(c1, c2, t):
    """controlled-H on t up to the control phase (-i)^(c1 c2) (4 CX)."""
    o = [g(n, t) for n in ("sdg", "h", "tdg", "h")]
    o += [g("t", t), g("cx", c1, t), g("tdg", t), g("cx", c2, t), g("t", t), g("cx", c1, t), g("tdg", t), g("cx", c2, t)]
    return o + [g(n, t) for n in ("h", "t", "h", "s")]


def cs(a, c):
    return [g("t", a), g("t", c), g("cx", a, c), g("tdg", c), g("cx", a, c)]


def rc3x_dag(a, b_, c, t):
    """inverse of the Maslov relative-phase 3-control Toffoli (6 CX); c is the outer control."""
    return [g("h", t), g("t", t), g("cx", c, t), g("tdg", t), g("h", t), g("t", t), g("cx", b_, t), g("tdg", t),
            g("cx", a, t), g("t", t), g("cx", b_, t), g("tdg", t), g("cx", a, t), g("h", t), g("t", t), g("cx", c, t),
            g("tdg", t), g("h", t)]


def cy(c, t):
    return [g("sdg", t), g("cx", c, t), g("s", t)]


def frame(alpha):
    o = []
    for (s1, s2, t1, t2) in CORNERS:
        o += [g("cx", s2, t2), g("cx", s1, s2), g("cx", s1, t1)]     # (a, b, c, w) = (s1, s1^s2, s1^t1, s2^t2)
        if alpha is not None:
            o.append(g("p", s2, p=(-0.75 * alpha,)))                 # b = Q flag of the source link (U_E, once)
    for k, (s1, s2, t1, t2) in enumerate(CORNERS):
        o += c2h_rel(s2, CORNERS[PREV[k]][1], s1)                    # sector: source single and target single
    for (s1, s2, t1, t2) in CORNERS:
        o += [g("rccx", t1, s2, s1)] + cs(t1, s2) + [g("z", s1), g("z", s2)]
    return o


def class_flags(e, k0):
    b0, b1, b2, b3 = (c[1] for c in CORNERS)
    o = [g("cx", b2, b0), g("cx", b3, b1)]
    o += neg((b0, b1), [g("rccx", b0, b1, e)])                         # e = [g_b = g_t][g_r = g_l]
    o += [g("cx", b2, b3)] + neg((b3,), [g("rccx", e, b3, k0)])         # k0 = e [g_t = g_l]
    o += [g("cx", b2, b3), g("cx", b3, b1), g("cx", b2, b0)]
    return o


def E(q, k0):
    c0, c2 = CORNERS[0], CORNERS[2]
    o = [g("cx", c0[0], c0[1]), g("cx", c2[0], c2[1]), g("x", q), g("rccx", c0[1], c2[1], q), g("z", c0[1]), g("s", q)]
    o += [g("cx", c0[0], c0[1]), g("cx", c2[0], c2[1])]
    return o + c2h_exact(k0, c0[1], q)


def J(q):
    o = []
    for k, (s1, s2, t1, t2) in enumerate(CORNERS):
        o += [g("s", s1), g("t", CORNERS[PREV[k]][1])] + rc3x_dag(q, s2, CORNERS[PREV[k]][1], s1)
    for (s1, s2, t1, t2) in CORNERS:
        o += cy(q, s2)
    return o


def pp_rz(tgt, terms):
    o = []
    for ctrl, ang in terms:
        if ctrl is not None:
            o.append(g("cx", ctrl, tgt))
        if ang is not None and abs(ang) > 0:
            o.append(g("rz", tgt, p=(ang,)))
    return o


def build(spec) -> Builder:
    b = Builder(spec)
    al, be = spec.alpha, spec.beta
    r2 = math.sqrt(2.0)
    (e, k0, q) = b.alloc(3, "flags")
    F = frame(al) + class_flags(e, k0) + E(q, k0) + J(q)
    T = [g("cx", s1, s2) for (s1, s2, t1, t2) in CORNERS]
    nds = b.alloc(4, "notdark")
    for (s1, s2, t1, t2), o in zip(CORNERS, nds):
        T += neg((t1, t2), [g("rccx", t1, t2, o)]) + [g("x", o)]
    lits = []
    for (s1, s2, t1, t2), o in zip(CORNERS, nds):
        lits += [s2, o]
    ch = b.alloc(len(lits) - 1, "and")
    lev, k = list(lits), 0
    while len(lev) > 1:
        nxt = []
        for x, y in zip(lev[0::2], lev[1::2]):
            T.append(g("rccx", x, y, ch[k])); nxt.append(ch[k]); k += 1
        lev = nxt
    z = lev[0]
    lam2, mu1, mu0 = 4.0 * be, -2.0 * be, 4.0 * r2 * be - 4.0 * be
    mu0 = mu0 - mu1
    c0 = lam2 / 2 + mu1 / 4 + mu0 / 4
    R = [g("h", q)] + pp_rz(q, [(None, c0), (e, -mu1 / 4), (z, mu1 / 4), (e, -c0), (k0, mu0 / 4), (z, -mu0 / 4), (k0, None)])
    R += [g("h", q)]
    a0 = CORNERS[0][0]
    lad = [g("cx", a0, c[0]) for c in CORNERS[1:]]
    nu = 4.0 * r2 * be
    R += lad + [g("h", a0)] + pp_rz(a0, [(None, nu / 4), (z, -nu / 4), (k0, nu / 4), (z, -nu / 4), (k0, None)])
    R += [g("h", a0)] + inv(lad)
    Fb = frame(None) + F[len(frame(al)):]
    ops = F + T + R + inv(T) + inv(Fb)
    for name, p, qs in ops:
        getattr(b, name)(*p, *qs)
    b.free(list(ch)); b.free(list(nds)); b.free([e, k0, q])
    return b
