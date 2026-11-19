"""SUMMARY: Parent F4/001 (native three-product frame: f_c, w_c per site, raw l_nv parity folded into site 0, three real-phase Margolus Toffolis give y1..y3, collapse onto f_0, flagless 18-term Walsh multiplexer R_X on f_0) with the last walk toggle CX(w_1 -> f_0) replaced by its physical twin CX(g_1 -> f_0) on the collapse wire q3 and merged as CZ into the inverse collapse CX(0,3); 73 CX.
DISCOVERY: (claim) the w_c wires duplicate collapse forms (w_1 = f_0 ^ f_1 = q3 after the collapse), so a walk toggle from a w wire next to h(pivot) can be re-sourced from the collapse wire and merged as CZ into the adjacent collapse CX for free; on the parent's 18-term support the exact open Gray tour (subset DP, free ends in span of the collapse forms, all 8 dark-flag shifts y_S) is 27 toggles, so this frame + support cannot go below 73 with pivot-only walks.
DISCOVERY: (claim) in this frame (y0 hidden by the fold, p explicit) no single AND of two linear literals F lets the coupling be a function of (F, p^y1^y2^y3, one y_c, two g-forms) on all 39 labels (exhaustive over 10108 distinct flags), so the seed's one-flag walk (a1 = [y0=y2=0]) cannot be transplanted onto the fold frame.
"""
FAMILY = "F4"
PARENT = "r01-F4-001"

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
]
# the parent's final toggle ("cx", 5) (q5 = w_1 = f_0 ^ f_1) equals CX(3 -> 0) on physical codes (q3 = f_1 ^ f_0
# after the collapse); right before h(0) it is CZ(3, 0) after h(0), merged with the inverse collapse CX(0, 3).


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


def _frame(b, spec, inverse, merged_first=False):
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
    if merged_first:
        assert ops[0] == ("cx", 0, 3)
        # CZ(0,3) then CX(0 -> 3)  ==  sdg(3), cx(0, 3), s(3), sdg(0)
        b.sdg(3); b.cx(0, 3); b.s(3); b.sdg(0)
        ops = ops[1:]
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
    _frame(b, spec, inverse=True, merged_first=True)
    return b
