"""SUMMARY: F2 pair frame: per corner a 2-CX leg frame + type-selected C_{jA}(X) makes both partners of every bright pair equal except the flip bit F=j_b; one rccx per corner leaves the bright flag; U_B = one (g, z, t)-multiplexed X rotation of F (6 Rz), U_E = 4 phases.
DISCOVERY: the leg map |00>->|00>, Psi- -> |10>, Psi+ -> |01>, |11> -> -|11> (equal to CX(a,b) CH(b,a) CX(a,b) on all bright legs) has Weyl point (pi/8, pi/8, 0) and the 2-CX, 2-T circuit S_a (HSdgH)^2 CX(a,b) (HTH_a, T_b) CX(a,b) (HSH)^2 S_a: one CX less per corner and side.
DISCOVERY: in that frame same-type bright legs are |00>, dark legs are basis states != |00>, and with C_t(H) CX(jA,a) C_t(YH) the diff legs never hit |01>, so bright_c = t ^ (~a)(~b ^ t) costs 1 CX + 1 rccx; a CX-only flag is impossible (the frame images of |00>, Psi-, Psi+, |11> are four basis states with XOR 0).
DISCOVERY: an X on leg a of corner 0 between the frame and the type gates flips only the diff partner sign there, so kappa = -1 for every n1=2 pair (2 for n1=0, 1/2 for n1=4, 0 dark) and the Walsh mux over (g, z=[all types equal], t) needs 6 CX; a chain fold q11=t3, q8=t2, q5=t1 gives three corner types without outer reads.
"""
FAMILY = "F2"
PARENT = None

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

    tau0, f1, f2, f3 = b.alloc(4, "flags")
    z, pa, pb, gg = b.alloc(4, "and")

    def corner(a, bb, jA, t, target, x_on_a):
        # W: 2-CX Clifford+T map |00>->|00>, Psi-->|10>, Psi+->|01> (|11>->-|11>) on the two legs
        g("s", a)
        for q in (a, bb):
            g("h", q); g("sdg", q); g("h", q)
        g("cx", a, bb); g("h", a); g("t", a); g("h", a); g("t", bb); g("cx", a, bb)
        for q in (a, bb):
            g("h", q); g("s", q); g("h", q)
        g("s", a)
        if x_on_a:
            g("x", a)  # flips the sign of the diff partner map at this corner only
        # type-selected canonicalisation: diff Z_a -> X_a, then the pair partners are made equal by C_{jA}(X_a)
        g("ch", t, a); g("cx", jA, a)
        # second type gate C_t(YH) = S(t) X_a CH(t,a) X_a: the diff legs then miss one basis state
        g("x", a); g("ch", t, a); g("x", a); g("s", t)
        if target != t:
            g("cx", t, target)
        # bright flag: target ^= [legs = same-bright state] (diff: never), via one relative-phase Toffoli
        if not x_on_a:
            g("x", a)
        g("cx", t, bb); g("x", bb)
        g("rccx", a, bb, target)

    # relabel the two NOT corners (c1: end leg q0 of link b, c3: end leg q9 of link l)
    g("cx", 2, 0); g("cx", 11, 9); g("z", 0); g("z", 9)
    g("cx", 13, tau0); g("cx", 15, tau0)          # type of corner 0 from its outer links
    g("cx", 8, 11)                               # q11 = j_t ^ j_l = type of corner 3
    corner(7, 9, 8, 11, f3, False)
    g("cx", 5, 8)                                # q8 = j_r ^ j_t = type of corner 2
    corner(3, 6, 5, 8, f2, False)
    g("cx", 2, 5)                                # q5 = j_b ^ j_r = type of corner 1; q2 = F = j_b
    corner(0, 4, 2, 5, f1, False)
    corner(1, 10, 2, tau0, tau0, True)
    # z = [all corner types equal]
    g("cx", 8, 5); g("cx", 8, 11)
    g("x", 5); g("x", 11); g("rccx", 5, 11, z); g("x", 5); g("x", 11)
    # g = AND of the four bright flags
    g("rccx", tau0, f1, pa); g("rccx", f2, f3, pb); g("rccx", pa, pb, gg)

    for name, qs in fwd:
        getattr(b, name)(*qs)

    # rotation exp(-i beta kappa(g, z, t) X_F): kappa = -1 (n1=2), 2 (n1=0), 1/2 (n1=4), 0 (dark)
    F, TB = 2, 8
    kap = {}
    for x in range(8):
        gb, zb, tb = (x >> 2) & 1, (x >> 1) & 1, x & 1
        if not gb:
            v = -1.5 if (zb and tb) else 0.0     # (g=0, z=1, t=1) never occurs
        elif zb:
            v = 2.0 if tb == 0 else 0.5
        else:
            v = -1.0
        kap[x] = v
    w = _walsh3(kap)
    ctrl = {4: gg, 2: z, 1: TB}
    b.h(F)
    if abs(w[0]) > 1e-12:
        b.rz(2.0 * spec.beta * w[0], F)
    cur = 0
    for S in (1, 3, 2, 6, 4, 0):
        diff = cur ^ S
        for bit in (4, 2, 1):
            if diff & bit:
                b.cx(ctrl[bit], F)
        cur = S
        if S and abs(w[S]) > 1e-12:
            b.rz(2.0 * spec.beta * w[S], F)
    b.h(F)

    for name, qs in reversed(fwd):
        getattr(b, _INV.get(name, name))(*qs)
    b.free([tau0, f1, f2, f3]); b.free([z, pa, pb, gg])
    return b
