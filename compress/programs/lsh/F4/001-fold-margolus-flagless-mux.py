"""SUMMARY: Native three-product frame (per-site f_c, w_c; raw l_nv parity folded into site 0 as class bit; three real-phase Margolus Toffolis give y1..y3; collapse onto f_0) + flagless 18-term Walsh multiplexer R_X on f_0; 74 CX.
DISCOVERY: Folding the four raw l_nv into site 0 gives p = [#w=2] xor (number of dark sites mod 2), invariant on all 47 codes; with Toffolis (w_c, f_c -> l_nv) on sites 1..3 only, the frame holds the same information as the seed's frame after its class AND (p xor y1 xor y2 xor y3 = y0 xor [#w=2]), so the fold replaces that AND but y0 is no longer linear.
DISCOVERY: qiskit rccx with controls (w_c, f_c) leaves a pair-phase ratio of +-i when an odd number of w=1 sites carry a Toffoli; a Margolus Toffoli (h/t/s, 3 CX, 4 T, -1 only on w=1, f=0, l_nv=1) adds no phase on any physical code, so a three-Toffoli frame is phase-free.
DISCOVERY: Flagless multiplexer on the moving bit in this frame: minimum Walsh support 16..18 terms (HiGHS, 400 s; 18 found, all coefficients +-1/8), but the shortest Gray tour over the 10 single-qubit forms is 27-28 CX, so frame (46) + mux = 74 CX; one-AND flags do not lower the LP support below 16.
"""
FAMILY = "F4"
PARENT = None

from fractions import Fraction
from su2plaq.compress.builder import Builder

# Multiplexed R_X on the moving bit q0 (in the H basis): ("cx", control) or ("rz", c) = rz(2*beta*c).
# c are the Walsh coefficients of the coupling k on the 47 inner codes in the frame (rational, exact).
FOLD = [4, 7, 10]
COLLAPSE = [(3, 9), (0, 6), (0, 3)]
MUX = [
    ("rz", "1/8"),
    ("cx", 1),
    ("rz", "-1/8"),
    ("cx", 4),
    ("rz", "-1/8"),
    ("cx", 10),
    ("rz", "-1/8"),
    ("cx", 4),
    ("rz", "-1/8"),
    ("cx", 7),
    ("rz", "-1/8"),
    ("cx", 11),
    ("cx", 10),
    ("rz", "-1/8"),
    ("cx", 1),
    ("cx", 2),
    ("rz", "-1/8"),
    ("cx", 7),
    ("cx", 10),
    ("rz", "-1/8"),
    ("cx", 7),
    ("cx", 9),
    ("rz", "-1/8"),
    ("cx", 4),
    ("cx", 7),
    ("rz", "-1/8"),
    ("cx", 2),
    ("cx", 7),
    ("rz", "-1/8"),
    ("cx", 1),
    ("rz", "-1/8"),
    ("cx", 10),
    ("cx", 6),
    ("rz", "-1/8"),
    ("cx", 1),
    ("cx", 2),
    ("cx", 8),
    ("rz", "-1/8"),
    ("cx", 8),
    ("cx", 7),
    ("rz", "-1/8"),
    ("cx", 4),
    ("rz", "-1/8"),
    ("cx", 2),
    ("rz", "-1/8"),
    ("cx", 5),
]


def _ry8(b, sgn, t):
    # Ry(sgn*pi/4) up to global phase (pairs of t/tdg cancel the phase over a Margolus gate)
    b.sdg(t); b.h(t)
    if sgn > 0:
        b.t(t)
    else:
        b.tdg(t)
    b.h(t); b.s(t)


def _margolus(b, a, c, t):
    """Real-phase Toffoli (3 CX, 4 T): CCX(a, c -> t) times -1 on |a=1, c=0, t=1> (never reached on physical codes)."""
    _ry8(b, +1, t); b.cx(c, t); _ry8(b, +1, t); b.cx(a, t); _ry8(b, -1, t); b.cx(c, t); _ry8(b, -1, t)


def _frame(b, spec, inverse):
    ops = []
    for c in range(4):
        ops.append(("cx", 3 * c + 1, 3 * c))          # pn_c := f_c = l_pn ^ l_nv (flux of the next inner link)
        if not inverse:
            ops.append(("p", 3 * c))                     # U_E: -3 alpha/4 per unit of N_n = f_c
    ops.append(("cx", 1, 2))                           # vp_0 := w_0 = l_nv ^ l_vp
    for q in FOLD:
        ops.append(("cx", q, 1))                       # nv_0 := parity of the raw l_nv (+ chosen w_c): invariant
    for c in (1, 2, 3):
        ops.append(("cx", 3 * c + 1, 3 * c + 2))       # vp_c := w_c = l_nv ^ l_vp
    for c in (1, 2, 3):
        ops.append(("mg", 3 * c + 2, 3 * c, 3 * c + 1))  # nv_c := dark flag y_c (cleans l_nv on sites 1..3)
    for src, dst in COLLAPSE:
        ops.append(("cx", src, dst))                   # collapse: the move is X on q0 = f_0
    if inverse:
        ops = ops[::-1]
    for op in ops:
        if op[0] == "cx":
            b.cx(op[1], op[2])
        elif op[0] == "p":
            b.p(-0.75 * spec.alpha, op[1])
        else:
            _margolus(b, op[1], op[2], op[3])


def build(spec):
    b = Builder(spec)
    _frame(b, spec, inverse=False)
    b.h(0)
    for kind, v in MUX:
        if kind == "cx":
            b.cx(v, 0)
        else:
            b.rz(2.0 * float(Fraction(v)) * spec.beta, 0)
    b.h(0)
    _frame(b, spec, inverse=True)
    return b
