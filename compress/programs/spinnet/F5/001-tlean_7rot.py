"""SUMMARY: T-lean step with 7 rotations (3 for U_E, 4 for U_B, the minimum for +-1 phase decompositions): U_E = phases on y_b, on the pivot r^t^l and on maj(r,t,l) (one rccx pair onto the pivot); U_B = 4-term pivot walk over B, F, F&~e with B and F&~e toggled onto the pivot by nested rccx pairs and the A flag XORed into corner qubit c3; 17 qubits, angles k*alpha/4 and k*beta/2 (one shifted by -pi/4).
DISCOVERY: U_E needs only 3 rotations: w(y) = y_b + (y_r^y_t^y_l) + 2 maj(y_r,y_t,y_l), and maj = P ^ OR(t^l, r^l) is one rccx onto the pivot P = r^t^l of the frame (b^r^t^l, t^l, P, r^l); U_B's pivot angle needs 4 rotations: f = -1/4 + 3/4 Z_A + 1/4 Z_B - 3/4 Z_B Z_(A&~e) (B=1 bright; no 3-term +-1 decomposition of {0,1,-2,-1/2} exists, exhaustive search).
DISCOVERY: On dark codes the A flag F only has to satisfy F=1 => t=l (then f=0), so A can be XORed into corner qubit c3 (c3=1 forces t=l=1/2): no A ancilla, 17 qubits.
DISCOVERY: rccx pairs on a non-clean target cancel their relative phase whenever the enclosed walk is closed on that target; cx(a,P)*rccx(a,e,P) fuses to rccx(a,~e,P), and back-to-back rccx on the pivot share their h/t edges (T_fixed 48 -> 45).
"""
FAMILY = "F5"
PARENT = None

from su2plaq.compress.builder import Builder


def build(spec):
    b = Builder(spec)
    al, be = spec.alpha, spec.beta
    g = 0.75 * al                      # U_E = exp(-i g w(y)), w = number of j=1/2 inner links
    (c,) = b.alloc(1, "corner_and")
    P = 2                              # pivot qubit
    F = 7                              # corner qubit c3, carries c3 ^ A during U_B

    # ---- U_E part 1: phase on y_b (qubit 0); q0 is only a control until the last frame CX, so this runs in parallel
    b.p(-g, 0)
    # ---- pivot frame: q0 = b^r^t^l, q1 = t^l (= e where A=1), q2 = P = r^t^l, q3 = v = r^l
    b.cx(1, 3)
    b.cx(3, 2)
    # ---- U_E part 2: parity r^t^l sits on the pivot (emitted before q2 becomes a control: runs beside the y_b phase)
    b.p(-g, P)
    b.cx(2, 1)
    b.cx(2, 0)
    # ---- U_E part 3: maj(r,t,l) = P ^ OR(t^l, r^l); toggle P by ~q1&~q3 -> P holds NOT maj
    b.x(1)
    b.x(3)
    _rccx_head(b, 1, 3, P); _rccx_tail(b, 1, 3, P)
    b.p(2 * g, P)                      # exp(-2ig maj) = global * exp(+2ig (1-maj))
    _rccx_head(b, 1, 3, P)             # its trailing tdg.h is merged into the walk below
    # q1 stays negated (~e on A=1) and q3 negated (~v) for the flags
    # ---- flags: corner AND c = ~c0&~c1&~c3 (rc3x); A = ~q0&~v XORed into c3's qubit
    b.x(0)
    for q in (4, 5, 6, 7):
        b.x(q)
    _rc3x(b, 4, 5, F, c)
    b.x(F)                             # qubit 7 = c3 again
    b.rccx(0, 3, F)                    # qubit 7 = c3 ^ A  (= A on bright codes)
    # ---- U_B: exp(-i beta f X_P), f = -1/4 + 3/4 Z_F + 1/4 Z_B - 3/4 Z_B Z_(F&~e)
    # walk opening: [tdg . h] (maj tail) . h(P) = tdg; tdg . rz(t0) = rz(t0 - pi/4) up to phase
    b.cx(P, F)
    b.rz(2 * be * 0.75, F)             # Z_P Z_F term on the flag qubit, in parallel with the Z_P term
    b.rz(2 * be * (-0.25) - _PI4, P)
    b.cx(P, F)
    b.rccx(c, 6, P)                    # B-on: P^B   (B = c & ~c2 = bright)
    b.rz(2 * be * 0.25, P)
    b.rccx(F, 1, P)                    # toggle by F & ~e
    b.rz(2 * be * (-0.75), P)          # P^B^(F&~e)
    _rccx_head(b, F, 1, P)             # Ae-off without its tdg.h ...
    _rccx_core_tail(b, c, 6, P)        # ... B-off without its h.t (tdg.h.h.t = 1); walk closing h(P) cancels B-off's h
    # ---- uncompute flags
    b.rccx(0, 3, F)
    b.x(F)
    _rc3x_inv(b, 4, 5, F, c)
    for q in (7, 6, 5, 4):
        b.x(q)
    b.x(0)
    b.x(1)
    b.x(3)
    # ---- inverse frame
    b.cx(2, 0)
    b.cx(2, 1)
    b.cx(3, 2)
    b.cx(1, 3)
    b.free([c])
    return b


_PI4 = 0.7853981633974483


def _rccx_head(b, c0, c1, t):
    """qiskit RCCX = head . tail; head = h t cx(c1) tdg cx(c0) t cx(c1)."""
    b.h(t); b.t(t); b.cx(c1, t); b.tdg(t); b.cx(c0, t); b.t(t); b.cx(c1, t)


def _rccx_tail(b, c0, c1, t):
    b.tdg(t); b.h(t)


def _rccx_core_tail(b, c0, c1, t):
    """RCCX without its leading h.t: cx(c1) tdg cx(c0) t cx(c1) tdg (and without the trailing h, cancelled by the caller)."""
    b.cx(c1, t); b.tdg(t); b.cx(c0, t); b.t(t); b.cx(c1, t); b.tdg(t)


def _rc3x(b, c0, c1, c2, t):
    """Relative-phase 3-control Toffoli (qiskit RC3X pattern, 6 CX, 8 T)."""
    b.h(t); b.t(t); b.cx(c2, t); b.tdg(t); b.h(t)
    b.cx(c0, t); b.t(t); b.cx(c1, t); b.tdg(t); b.cx(c0, t); b.t(t); b.cx(c1, t); b.tdg(t)
    b.h(t); b.t(t); b.cx(c2, t); b.tdg(t); b.h(t)


def _rc3x_inv(b, c0, c1, c2, t):
    b.h(t); b.t(t); b.cx(c2, t); b.tdg(t); b.h(t)
    b.t(t); b.cx(c1, t); b.tdg(t); b.cx(c0, t); b.t(t); b.cx(c1, t); b.tdg(t); b.cx(c0, t)
    b.h(t); b.t(t); b.cx(c2, t); b.tdg(t); b.h(t)
