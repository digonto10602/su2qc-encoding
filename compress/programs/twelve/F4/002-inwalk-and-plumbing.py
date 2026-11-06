"""SUMMARY: F2 pair frame (2-CX leg frame + type gates + one rccx bright flag per corner) with an 8-CX type plumbing (no outer reads, corners 0/1 flag in place into their type registers) and the top AND g=pa&pb toggled into F by an in-walk rccx (no g register; residual (-1)^(pa z) fixed by one CZ); 6-Rz (g,z,t) multiplexer + 4 electric phases.
DISCOVERY: The top AND of the bright tree needs no register: toggling F with rccx(pa,pb,F) inside the Walsh walk leaves only the Margolus phase Z_F^pa, which anticommutes with the single CX(z,F) toggle inside the g-interval and leaves (-1)^(pa*z), cancelled by one CZ(pa,z): 2 rccx + 1 CX instead of compute/uncompute rccx + 2 CX (saves 1 CX).
DISCOVERY: Type plumbing as a shortest path over register linear forms (Dijkstra) gives 8 CX instead of 10: q11^=q8 (t3) | corner3 | q5^=q8 (t2), q11^=q5 (u) | corner2 | q8^=q2 (v), z=AND(~u,~v) | q8^=q5 (t1), q11^=q8 (t0) | corners 0,1 write their bright flags in place into t0, t1; t2 stays as the walk type bit, no outer reads.
DISCOVERY: Corner 2 may use jA = j_t (the other leg's link) in C_jA(X_a) without changing the leg roles: the frame stays exact (H_B = kappa g X_F on all 433 states) and the n2 sign is still (-1)^t0, so one X on leg a of corner 0 gives kappa = 2 (n1=0), -1 (n1=2), 1/2 (n1=4).
"""
FAMILY = "F4"
PARENT = "r01-F4-001"

from su2plaq.compress.builder import Builder

_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}


def _walsh3(vals):
    return {S: sum(vals[x] * (-1) ** bin(S & x).count("1") for x in range(8)) / 8.0 for S in range(8)}


def build(spec):
    b = Builder(spec)
    fwd = []

    def g(name, *qs):
        fwd.append((name, qs))

    # electric layer: phase -3/4 alpha per active inner link (diagonal in the q_j bits)
    for q in (2, 5, 8, 11):
        b.p(-0.75 * spec.alpha, q)

    f3, f2 = b.alloc(2, "flags")
    z, pa, pb = b.alloc(3, "and")

    def corner(a, bb, jA, t, target, x_on_a):
        # W: 2-CX map |00>->|00>, Psi- -> |10>, Psi+ -> |01>, |11> -> -|11> on the two legs
        g("s", a)
        for q in (a, bb):
            g("h", q); g("sdg", q); g("h", q)
        g("cx", a, bb); g("h", a); g("t", a); g("h", a); g("t", bb); g("cx", a, bb)
        for q in (a, bb):
            g("h", q); g("s", q); g("h", q)
        g("s", a)
        if x_on_a:
            g("x", a)  # flips the sign of the diff partner map at this corner only
        # type-selected canonicalisation (diff Z_a -> X_a), partners made equal by C_jA(X_a)
        g("ch", t, a); g("cx", jA, a)
        # C_t(YH): the diff legs then never hit |01>
        g("x", a); g("ch", t, a); g("x", a); g("s", t)
        if target != t:
            g("cx", t, target)
        # bright flag: target ^= [same-type bright legs] (never on diff legs); target holds t first
        if not x_on_a:
            g("x", a)
        g("cx", t, bb); g("x", bb)
        g("rccx", a, bb, target)

    # relabel the two NOT corners (c1: end leg q0 of link b, c3: end leg q9 of link l)
    g("cx", 2, 0); g("cx", 11, 9); g("z", 0); g("z", 9)
    g("cx", 8, 11)                       # q11 = t3 = j_t ^ j_l
    corner(7, 9, 8, 11, f3, False)       # corner 3, jA = j_t (raw)
    g("cx", 8, 5)                        # q5 = t2 = j_r ^ j_t
    g("cx", 5, 11)                       # q11 = u = j_r ^ j_l
    corner(3, 6, 8, 5, f2, False)        # corner 2, jA = j_t (raw, other leg's link)
    g("cx", 2, 8)                        # q8 = v = j_b ^ j_t
    g("x", 8); g("x", 11); g("rccx", 8, 11, z); g("x", 8); g("x", 11)   # z = [all corner types equal]
    g("cx", 5, 8)                        # q8 = t1 = j_b ^ j_r
    g("cx", 8, 11)                       # q11 = t0 = j_b ^ j_l
    corner(1, 10, 2, 11, 11, True)       # corner 0: bright flag written into q11
    corner(0, 4, 2, 8, 8, False)         # corner 1: bright flag written into q8
    g("rccx", 11, 8, pa); g("rccx", f2, f3, pb)   # pair ANDs; g = pa & pb is never stored

    for name, qs in fwd:
        getattr(b, name)(*qs)

    # exp(-i beta kappa(g, z, t) X_F): kappa = -1 (n1=2), 2 (n1=0), 1/2 (n1=4), 0 (dark); F = j_b, t = t2 (q5)
    F, TB = 2, 5
    kap = {}
    for x in range(8):
        gb, zb, tb = (x >> 2) & 1, (x >> 1) & 1, x & 1
        if not gb:
            v = -1.5 if (zb and tb) else 0.0     # (g=0, z=1, t=1) never occurs (all-diff corners are bright)
        elif zb:
            v = 2.0 if tb == 0 else 0.5
        else:
            v = -1.0
        kap[x] = v
    w = _walsh3(kap)
    b.h(F)
    if abs(w[0]) > 1e-12:
        b.rz(2.0 * spec.beta * w[0], F)
    cur = 0
    for S in (1, 3, 2, 6, 4, 0):
        diff = cur ^ S
        if diff & 1:
            b.cx(TB, F)
        if diff & 2:
            b.cx(z, F)
        if diff & 4:
            b.rccx(pa, pb, F)            # toggles F by g = pa & pb up to the phase Z_F^pa (-i)^(pa pb)
        cur = S
        if S and abs(w[S]) > 1e-12:
            b.rz(2.0 * spec.beta * w[S], F)
    b.h(F)
    b.cz(pa, z)                          # the Z_F^pa phases of the two rccx straddle one CX(z,F): (-1)^(pa z)

    for name, qs in reversed(fwd):
        getattr(b, _INV.get(name, name))(*qs)
    b.free([f3, f2]); b.free([z, pa, pb])
    return b
