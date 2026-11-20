"""SUMMARY: F1 recode-gate fusion probe: F3-style 46-CX frame (raw l_nv parity folded into site 0, three Margolus Toffolis) whose site-c Toffoli is controlled by f_D instead of f_c (D = (3, 0, 1)), so the labels become y_c xor w_c (f_c xor f_D) at no extra CX; SA walk of 30 toggles (free ends in span{u, v, e}), 24 walk rotations; 76 CX, a negative result versus the 68-CX headline.
DISCOVERY: (claim, numerical) in the 3-Toffoli fold frame each site Toffoli may take its second control from any f_D (Margolus, 3 CX): the frame stays exact (partner pairs differ only in the pivot, all pair signs +1) and the labels become y_c xor w_c (f_c xor f_D), i.e. products of w's for free; but with SA over walks (8-dim cube, 51 labels) the D = (3, 0, 1) frame gave no walk shorter than 30 toggles versus 27 for the plain frame under the same search.
DISCOVERY: (claim, numerical) F3 frame plus one 2-literal AND flag (26 pairs of dark-related wires tried: y1-y3, p and outer l_2v/l_v1, incl. y0 = l_2v(0) AND l_v1(0); 52 CX) and the F1 frame without its flag (50 CX, y0..y3 explicit, outer generators) gave no exact walk <= 18 (resp. 20) toggles in short SA runs; these SA runs also failed to re-find known walks (F1 frame: 16 found vs 15 known; F3 frame: 27 vs 22), so they are weak bounds."""
FAMILY = "F1"
PARENT = "r02-F1-002"

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Site c in 1..3: Margolus Toffoli (f_D[c], w_c -> l_nv(c)) with D = DS[c-1]; D = c gives the plain y_c,
# D != c gives y_c xor w_c (f_c xor f_D), a nonlinear label of the f pattern at no extra cost.
DS = (3, 0, 1)
START = [6, 9]        # collapse targets whose first walk toggle is merged as CZ into the collapse CX
END = [6, 9]            # collapse targets whose last walk toggle is merged as CZ into the inverse collapse CX
START_C = Fraction('-1/2')
WALK = [(11, Fraction(1, 4)), (1, Fraction(-1, 4)), (4, Fraction(-1, 4)), (10, Fraction(-1, 4)), (6, Fraction(1, 2)), (5, Fraction(-1, 4)), (11, Fraction(-1, 4)), (4, Fraction(-1, 4)), (7, Fraction(-1, 2)), (9, Fraction(1, 4)), (10, Fraction(1, 4)), (13, Fraction(0, 1)), (14, Fraction(-1, 4)), (8, Fraction(0, 1)), (9, Fraction(-1, 4)), (1, Fraction(0, 1)), (9, Fraction(-1, 4)), (4, Fraction(-1, 2)), (5, Fraction(1, 4)), (1, Fraction(0, 1)), (6, Fraction(-1, 4)), (10, Fraction(-1, 4)), (1, Fraction(-1, 4)), (4, Fraction(0, 1)), (6, Fraction(-1, 4)), (7, Fraction(-1, 4)), (5, Fraction(0, 1)), (4, Fraction(-1, 4)), (10, Fraction(-1, 4)), (4, Fraction(0, 1))]


def _ry8(b, q, sign):
    b.sdg(q)
    b.h(q)
    if sign > 0:
        b.t(q)
    else:
        b.tdg(q)
    b.h(q)
    b.s(q)


def margolus(b, a, c, t):
    """Real-phase Toffoli: CCX(a, c -> t) times -1 on |a=1, c=0, t=1>; self-inverse; 3 CX, 4 T."""
    _ry8(b, t, +1)
    b.cx(c, t)
    _ry8(b, t, +1)
    b.cx(a, t)
    _ry8(b, t, -1)
    b.cx(c, t)
    _ry8(b, t, -1)


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    b.cx(1, 2)
    b.cx(1, 0)
    b.cx(4, 1)
    b.cx(7, 1)
    b.cx(10, 1)
    for c in (1, 2, 3):
        b.cx(3 * c + 1, 3 * c + 2)
        b.cx(3 * c + 1, 3 * c)
    for c in (1, 2, 3):
        margolus(b, 3 * DS[c - 1], 3 * c + 2, 3 * c + 1)
    for q in (0, 3, 6, 9):
        b.p(-0.75 * spec.alpha, q)
    for q in (3, 6, 9):
        if q in START:
            b.s(0); b.sdg(q); b.cx(0, q); b.s(q)
        else:
            b.cx(0, q)
    b.h(0)
    if START_C != 0:
        b.rz(float(START_C) * beta, 0)
    for g, c in WALK:
        b.cx(g, 0)
        if c != 0:
            b.rz(float(c) * beta, 0)
    b.h(0)
    for q in (9, 6, 3):
        if q in END:
            b.sdg(0); b.sdg(q); b.cx(0, q); b.s(q)
        else:
            b.cx(0, q)
    for c in (3, 2, 1):
        margolus(b, 3 * DS[c - 1], 3 * c + 2, 3 * c + 1)
    for c in (3, 2, 1):
        b.cx(3 * c + 1, 3 * c)
        b.cx(3 * c + 1, 3 * c + 2)
    b.cx(10, 1)
    b.cx(7, 1)
    b.cx(4, 1)
    b.cx(1, 0)
    b.cx(1, 2)
    return b
