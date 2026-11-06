"""SUMMARY: F1 involution frame: per-corner frame CH(t->A).H_A.CX.CH.CX (4 CX) turns every bright pair into X_F (x) prod_c Z_{A_c}; dark flag from the frame marker B_c gated by t_c-bar plus one outer m-AND per corner (reads only the 8 outer m bits); one 6-term multiplexed Rz on F (gzu/t flags).
DISCOVERY: After the per-link relabel (legs ^= j on corners 0,2 legs; q0 ^= j_b, q9 ^= j_l for corners 1,3) the corner frame C0 = H_A CX_AB CH_BA CX_AB maps (vac, bond) to Z_A-partners with B=0, and CH(t->A) C0 does the same for the diff pair: the same-vs-diff frames differ by one t-controlled Hadamard (anticommuting partner involutions), so the frame costs 4 CX per corner.
DISCOVERY: The pair-relation sign of the frame differs from the true coupling sign only on the n1=2 patterns t=(001),(110) (u=t0^t1=0, v=t1^t2=1); folding that sign into the angle gives a 6-term Walsh multiplexer on (g, z, t1, u) with no constant term (8 CX).
DISCOVERY: A leg-only (outer-linear) marker cannot flag all dark corners: vac and one parallel triplet share the leg code, so each corner needs one AND of its two outer m bits (literal pattern (1,1) for corners 0,2, (1,0)/(0,1) for corners 1,3).
"""
FAMILY = "F1"
PARENT = None

from su2plaq.compress.builder import Builder

# corner c: leg A, leg B, outer link P, outer link Q (legs after the relabel below)
CORN = {0: (1, 10, 0, 1), 1: (0, 4, 2, 3), 2: (3, 6, 4, 5), 3: (7, 9, 6, 7)}
# outer m literal pattern of the parallel-triplet pattern that the frame leaves unmarked
KAPPA = {0: (1, 1), 1: (1, 0), 2: (1, 1), 3: (0, 1)}
PRE_Z = {0: False, 1: True, 2: False, 3: True}


def _m(k):
    return 12 + 2 * k


def _e(k):
    return 13 + 2 * k


def _rccx_lit(emit, c1, c2, t, n1=False, n2=False):
    """Relative-phase Toffoli (Margolus) with optionally negated controls (negation = X on the target in the H frame)."""
    seq = [("h", (t,)), ("t", (t,)), ("cx", (c2, t))]
    if n2:
        seq.append(("x", (t,)))
    seq += [("tdg", (t,)), ("cx", (c1, t))]
    if n1:
        seq.append(("x", (t,)))
    seq += [("t", (t,)), ("cx", (c2, t))]
    if n2:
        seq.append(("x", (t,)))
    seq += [("tdg", (t,)), ("h", (t,))]
    for name, args in seq:
        emit(name, *args)


_DAG = {"t": "tdg", "tdg": "t", "s": "sdg", "sdg": "s"}


def build(spec):
    b = Builder(spec)
    al, be = spec.alpha, spec.beta
    # electric layer U_E(alpha): exp(-i 3/4 alpha sum_l j_l)
    for q in (2, 5, 8, 11):
        b.p(-0.75 * al, q)

    fwd = []   # self-recorded prefix; its exact inverse is emitted after the rotation

    def g(name, *args):
        fwd.append((name, args))
        getattr(b, name)(*args)

    m0, m1, m2, m3, h1, h2, gq, zq = b.alloc(8, "work")
    # relabel: R (q0 ^= j_b, q9 ^= j_l) for corners 1,3; legs ^= j for corners 0,2
    for c_, t_ in ((2, 0), (11, 9), (2, 1), (11, 10), (5, 3), (8, 6)):
        g("cx", c_, t_)
    # GHZ fold: F = q2 = j_b, q11 = t0, q5 = t1, q8 = t2 (t_c = j_A ^ j_B of corner c)
    g("cx", 5, 8); g("cx", 2, 5); g("cx", 2, 11)
    mk = {0: m0, 1: m1, 2: m2, 3: m3}

    def frame(c, tq):
        # corner frame: pair partners -> Z_A related; dark marker on B (t_c = 0 corners)
        A, B, P, Q = CORN[c]
        if PRE_Z[c]:
            g("z", A)
        g("cx", A, B); g("ch", B, A); g("cx", A, B); g("h", A); g("ch", tq, A)
        k1, k2 = KAPPA[c]
        _rccx_lit(g, _m(P), _m(Q), B, k1 == 0, k2 == 0)
        # dark marker m_c = (not t_c) and B_c
        g("x", tq); g("rccx", tq, B, mk[c]); g("x", tq)

    frame(0, 11); frame(1, 5); frame(2, 8)
    g("cx", 5, 11); g("cx", 8, 11)          # q11 = t3 = t0 ^ t1 ^ t2
    frame(3, 11)
    # bright flag g = NOR(m_0..m_3)
    for q in (m0, m1, m2, m3):
        g("x", q)
    g("rccx", m0, m1, h1); g("rccx", m2, m3, h2); g("rccx", h1, h2, gq)
    # class flag z = [t0 = t1 = t2]; q11 = u = t0^t1, q8 = v = t1^t2
    g("cx", 8, 11); g("cx", 5, 8); g("x", 11); g("x", 8); g("rccx", 11, 8, zq); g("x", 11); g("x", 8)
    # Pauli string X_F prod_c Z_{A_c} -> Z_F
    g("h", 2)
    for c in range(4):
        g("cx", CORN[c][0], 2)
    # multiplexed rotation exp(-i beta f(g,z,t1,u) Z_F), f = Walsh fit incl. the coupling sign
    F, t1, u = 2, 5, 11
    w = lambda x: 2.0 * be * x
    b.cx(t1, F); b.rz(w(-0.375), F)
    b.cx(zq, F); b.rz(w(0.375), F)
    b.cx(t1, F); b.cx(u, F); b.rz(w(0.375), F)
    b.cx(gq, F); b.rz(w(-0.75), F)
    b.cx(zq, F); b.rz(w(0.25), F)
    b.cx(gq, F); b.rz(w(0.125), F)
    b.cx(u, F)
    # undo the prefix
    for name, args in reversed(fwd):
        getattr(b, _DAG.get(name, name))(*args)   # rccx, ch, cx, h, x, z are self-inverse
    b.free([m0, m1, m2, m3, h1, h2, gq, zq])
    return b
