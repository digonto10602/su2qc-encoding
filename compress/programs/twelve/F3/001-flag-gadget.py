"""SUMMARY: per-corner 10-CX gadget (two Margolus + CX + 2 CH, partner map X on one leg, dark flag left in a corner ancilla), 5-CX fold that exposes the corner types t_c as qubits, 4-input AND of the bright flags, 12-term Walsh multiplexed Rx on j_b (CX 132).
DISCOVERY: A 10-CX corner gadget [rccx(jA,jB->a), cx(A->B), ch(B->A), cx(a->B), rccx(A,~B->a), ch(t->A)] maps every bright pair to a partner differing by X on leg A only and leaves a=1 exactly on dark corners; corners 1,3 need cx(jA->A)+z(A) first.
DISCOVERY: The fold j_b->j_r, j_l->j_t, j_b->j_l, j_r->j_t, j_t->j_l (5 CX) exposes all four corner types t_c for the t-controlled H and leaves (t1, t1^t3, t2); in that encoding the rotation (angle g*2*beta*h*s, one free point at n1=4,g=0) has an 11-term Walsh support walked with 12 CX.
DISCOVERY: Outer reads do not pay here: t_c from the j-fold is cheaper than eA^eB, and every dark flag needs inner Bell structure plus j (E-par dark legs equal the vacuum legs), so no flag can be precomputed once; in the 3-CX partner frames (cx, ch, ch(t)) no single-AND dark flag exists (exhaustive check).
"""
FAMILY = "F3"
PARENT = None

from fractions import Fraction

from su2plaq.compress.builder import Builder

# data-register qubits of the twelve encoding: link l in (b, r, t, l) -> (q_m', q_m, q_j) = (3l, 3l+1, 3l+2)
JB, JR, JT, JL = 2, 5, 8, 11
# corners in the convention of corner 0 (bond (|10>-|01>)/sqrt2 on (A,B), label copied between legs):
# (leg A, leg B, j of link holding A, j of link holding B, needs relabel cx(jA->A); z(A))
CORNERS = [(1, 10, JB, JL, False), (0, 4, JB, JR, True), (3, 6, JR, JT, False), (7, 9, JT, JL, True)]

# Walsh terms of the rotation angle (units of beta) over the controls (g, q5=t1, q8=t1^t3, q11=t2), Gray-walk order.
# Rx angle on a bright pair = 2*beta*h*s, h the coupling (+-2, +-1, +-1/2 by class), s the frame sign; 0 when g = 0.
MUX_CONST = Fraction(-3, 8)
MUX = [((0, 0, 1, 0), Fraction(-3, 8)), ((0, 1, 1, 0), Fraction(-3, 8)), ((1, 1, 1, 0), Fraction(3, 4)),
       ((1, 1, 0, 0), Fraction(3, 4)), ((0, 1, 0, 0), Fraction(-3, 8)), ((0, 1, 0, 1), Fraction(-3, 8)),
       ((0, 1, 1, 1), Fraction(-3, 8)), ((0, 0, 1, 1), Fraction(5, 8)), ((1, 0, 1, 1), Fraction(-1, 4)),
       ((1, 0, 0, 1), Fraction(3, 4)), ((0, 0, 0, 1), Fraction(-3, 8))]


def _frame(anc):
    """Frame D as a gate list [(name, qubits)]: corner gadgets, fold of the j's (with the t-controlled H of each
    corner), fold of leg A into j_b.  Every gate in it is self-inverse, so D^dagger is the reversed list."""
    D = []
    for A, B, jA, jB, conv in CORNERS:
        if conv:
            D += [("cx", (jA, A)), ("z", (A,))]
    for (A, B, jA, jB, conv), a in zip(CORNERS, anc):
        D += [("rccx", (jA, jB, a)),        # a = jA & jB (both inner links of the corner active)
              ("cx", (A, B)),
              ("ch", (B, A)),               # bond -> |11>, triplet M=0 -> |01>
              ("cx", (a, B)),
              ("x", (B,)), ("rccx", (A, B, a)), ("x", (B,))]   # a ^= A & ~B : a = 1 exactly on dark corners
    D += [("cx", (JB, JR)), ("ch", (JR, CORNERS[1][0])),     # q5 = t1 = jb^jr
          ("cx", (JL, JT)), ("ch", (JT, CORNERS[3][0])),     # q8 = t3 = jt^jl
          ("cx", (JB, JL)), ("ch", (JL, CORNERS[0][0])),     # q11 = t0 = jb^jl
          ("cx", (JR, JT)),                                  # q8 = t1^t3
          ("cx", (JT, JL)), ("ch", (JL, CORNERS[2][0]))]     # q11 = t0^t1^t3 = t2
    D += [("cx", (JB, A)) for A, B, jA, jB, conv in CORNERS]  # partner map is X on leg A: fold it into j_b
    return D


def build(spec):
    b = Builder(spec)
    for q in (JB, JR, JT, JL):     # electric layer U_E (first in the circuit)
        b.p(-0.75 * spec.alpha, q)
    anc = b.alloc(4, "dark")
    D = _frame(anc)
    for name, qs in D:
        getattr(b, name)(*qs)
    x, y, g = b.alloc(3, "bright")
    for a in anc:
        b.x(a)
    b.rccx(anc[0], anc[1], x)
    b.rccx(x, anc[2], y)
    b.rccx(y, anc[3], g)           # g = no dark corner
    ctrls = [g, JR, JT, JL]
    b.h(JB)
    b.rz(float(MUX_CONST) * spec.beta, JB)
    cur = (0, 0, 0, 0)
    for S, w in MUX:
        for i, (p, q) in enumerate(zip(cur, S)):
            if p != q:
                b.cx(ctrls[i], JB)
        cur = S
        b.rz(float(w) * spec.beta, JB)
    for i, p in enumerate(cur):
        if p:
            b.cx(ctrls[i], JB)
    b.h(JB)
    b.rccx(y, anc[3], g)
    b.rccx(x, anc[2], y)
    b.rccx(anc[0], anc[1], x)
    for a in anc:
        b.x(a)
    b.free([x, y, g])
    for name, qs in reversed(D):           # D^dagger
        getattr(b, name)(*qs)
    b.free(anc)
    return b
