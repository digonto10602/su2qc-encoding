"""SUMMARY: F4 flat direction-qubit dilation (parent r03-F4-003; frame, class flags, direction NAND, Maslov RC3X^dag lowering, class-multiplexed Rx on q and closed toggle unchanged) with a cheaper bright test from an exact set-cover search over the J-frame labels: 5 leaves instead of 8 (three in-place corner literals w_c ^ (c_c & !(a_c ^ b_{c-1})) at c0, c1, c2 by one rccx each on the w bits, P_c1 ^ dark_c3 by one rccx into q5, P_c3 by one CX), ANDed by 4 rccx into 4 ancillas instead of 11 rccx into 11 (test 29 CX per side instead of 37); the test preps leave vac_A and the loop differing in 3 data bits instead of 4, so the closed A<->L toggle ladder is 2 CX per side instead of 3; all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: the bright test needs neither P_c0 nor P_c2 nor two OR ancillas: on the 1388 dark J-frame labels the AND of q3 = w1 ^ (c1 & !(b0 ^ a1)), q7 = w2 ^ (c2 & !(b1 ^ a2)), q13 = w0 ^ (c0 & !(a0 ^ b3)), q5 = P_c1 ^ (!c3 & !w3) and q15 = P_c3 is 0 and on all 164 bright labels 1; an exact branch-and-bound cover over linear literals (<= 3-bit parities), single in-place rccx literals X ^ (l1 & l2) and double ones finds 29 CX per side as the minimum (the parent's 8-literal test costs 37).
DISCOVERY: vac_A and the loop differ in all 8 source-end bits in the J-frame and each in-place parity prep between two of them (and each in-place literal written onto one) removes one bit of that difference, so the test preps also shorten the closed A<->L toggle ladder: with the 5 preps above the two images differ only in q4, q11, q14 (ladder CX(q11 -> q4), CX(q11 -> q14)), and the test rccx phases need no gauge.
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


def test_ops(n1, n2, n3, z):
    """bright test: AND of 5 leaves, three of them in-place corner literals w ^ (c & !(parity)) (cover search)."""
    T = [g("cx", 4, 1)] + neg((1,), [g("rccx", 2, 1, 3)])          # q3 = w1 ^ (c1 & !(b0 ^ a1))
    T += [g("cx", 5, 10)] + neg((10,), [g("rccx", 6, 10, 7)])      # q7 = w2 ^ (c2 & !(b1 ^ a2))
    T += [g("cx", 15, 0)] + neg((0,), [g("rccx", 12, 0, 13)])      # q13 = w0 ^ (c0 & !(a0 ^ b3))
    T += [g("cx", 4, 5)] + neg((8, 9), [g("rccx", 8, 9, 5)])       # q5 = P_c1 ^ (!c3 & !w3)
    T += [g("cx", 14, 15)]                                          # q15 = P_c3
    T += [g("rccx", 3, 7, n1), g("rccx", 13, 5, n2), g("rccx", n1, n2, n3), g("rccx", n3, 15, z)]
    return T


def build(spec) -> Builder:
    b = Builder(spec)
    al, be = spec.alpha, spec.beta
    r2 = math.sqrt(2.0)
    (e, k0, q) = b.alloc(3, "flags")
    F = frame(al) + class_flags(e, k0) + E(q, k0) + J(q)
    (n1, n2, n3, z) = b.alloc(4, "and")
    T = test_ops(n1, n2, n3, z)
    lam2, mu1, mu0 = 4.0 * be, -2.0 * be, 4.0 * r2 * be - 4.0 * be
    mu0 = mu0 - mu1
    c0 = lam2 / 2 + mu1 / 4 + mu0 / 4
    R = [g("h", q)] + pp_rz(q, [(None, c0), (e, -mu1 / 4), (z, mu1 / 4), (e, -c0), (k0, mu0 / 4), (z, -mu0 / 4), (k0, None)])
    R += [g("h", q)]
    piv = 11                                       # vac_A and loop images differ in q4, q11, q14 after the test
    lad = [g("cx", piv, 4), g("cx", piv, 14)]
    nu = 4.0 * r2 * be
    R += lad + [g("h", piv)] + pp_rz(piv, [(None, nu / 4), (z, -nu / 4), (k0, nu / 4), (z, -nu / 4), (k0, None)])
    R += [g("h", piv)] + inv(lad)
    Fb = frame(None) + F[len(frame(al)):]
    ops = F + T + R + inv(T) + inv(Fb)
    for name, p, qs in ops:
        getattr(b, name)(*p, *qs)
    b.free([n1, n2, n3, z]); b.free([e, k0, q])
    return b
