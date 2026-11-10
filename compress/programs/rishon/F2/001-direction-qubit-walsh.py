"""SUMMARY: F2 explicit direction qubit: link prep, g-controlled canonicaliser + Bell map at corners c0/c2, direction f = [x0=g_b][x10=g_t] in one Toffoli, f-controlled lowering at c1/c3, c0/c2 partner fix, then a 6-term Walsh multiplexer on f over four good-equal-corner bits plus kappa=1 and closed-pair gadgets; all angles are integer (closed: sqrt2) multiples of beta.
DISCOVERY: after the g-controlled canonicaliser + Bell map at opposite corners c0,c2 the true direction (upper member) is f = [x0==g_b] AND [x10==g_t] on every non-closed bright member (one Toffoli), although f is not even quadratic in the raw code bits.
DISCOVERY: in the lowered frame a kappa=2 label is bright iff both bits are 1 at its two equal corners and its Rx angle depends only on their geometry (adjacent +4 beta, opposite -4 beta); kappa=1 labels are bright iff x0 = x10 = NOT s_b (-2 beta), the closed pair gets -8 sqrt2 beta.
DISCOVERY: the 4-bit multiplexer needs only 6 Walsh terms (12 CX) if the never-occurring weight>=3 patterns get angles (-4,4,4,4,0) beta; the sparse engine caps circuits at 62 qubits, so the four link R2 qubits (|0> after link prep) serve as scratch.
"""
FAMILY = "F2"
PARENT = None

import math

from su2plaq.compress.builder import Builder

# Corners (eS, eD, gS, gD): e-bits of the source / drain end and the Q-flags (L2 after the link prep) of their links.
# c0 = (b.L, l.L), c1 = (r.L, b.R), c2 = (t.R, r.R), c3 = (l.R, t.L).
CORN = [(0, 12, 1, 13), (4, 2, 5, 1), (10, 6, 9, 5), (14, 8, 13, 9)]
ANC = ["F", "T0", "T2", "Z", "E0", "E1", "E2", "E3", "C01", "C", "M0", "M1", "M2", "M3"]
# R2 qubits (3, 7, 11, 15) are |0> on every valid code after the link prep: used as scratch.
DATA_SCRATCH = {"C4": 3, "R101": 7, "XA": 11, "C23": 15}
INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}
# Rx-angle table of the multiplexer in units of beta; pattern m = (M0..M3) of the "good equal corner" bits.
# kappa = 2 sectors: adjacent equal corners +4, opposite -4; patterns of weight >= 3 never occur (free values
# chosen so that only 6 Walsh terms survive).
PAIR = {(0, 1): 4, (1, 2): 4, (2, 3): 4, (0, 3): 4, (0, 2): -4, (1, 3): -4}
FREE = {7: -4, 11: 4, 13: 4, 14: 4, 15: 0}
K1 = -2.0          # kappa = 1 sectors (all four corners different)
KC = -8.0          # closed pair (kappa = 4 sqrt2): Rx angle -8 sqrt2 beta


def _inv(ops):
    out = []
    for n, p, q in reversed(ops):
        if n in INV:
            out.append((INV[n], p, q))
        elif n in ("rz", "p", "crx", "crz", "cp"):
            out.append((n, (-p[0],), q))
        else:
            out.append((n, p, q))
    return out


def _cch(o, a, b, t):
    """doubly controlled H on t: Ry(pi/4) CCZ Ry(-pi/4)."""
    o += [("sdg", (), (t,)), ("h", (), (t,)), ("tdg", (), (t,)), ("h", (), (t,)), ("s", (), (t,)),
          ("ccz", (), (a, b, t)),
          ("sdg", (), (t,)), ("h", (), (t,)), ("t", (), (t,)), ("h", (), (t,)), ("s", (), (t,))]


def _c2rx(o, th, c1, c2, t):
    """Barenco doubly controlled Rx (no ancilla)."""
    o += [("crx", (th / 2,), (c2, t)), ("cx", (), (c1, c2)), ("crx", (-th / 2,), (c2, t)), ("cx", (), (c1, c2)),
          ("crx", (th / 2,), (c1, t))]


def link_prep():
    o = []
    for l in range(4):
        o += [("cx", (), (4 * l, 4 * l + 1)), ("cx", (), (4 * l + 2, 4 * l + 3)), ("cx", (), (4 * l + 1, 4 * l + 3))]
    return o


def frame(A):
    """After link prep: lowering frame.  Bright pair members become |lambda, F=0/1>."""
    F = A["F"]
    o = []
    for c in (0, 2):                        # g-controlled canonicaliser + Bell map at c0, c2
        eS, eD, gS, gD = CORN[c]
        o += [("cx", (), (eS, eD)), ("ccx", (), (gS, eD, eS))]
        _cch(o, gS, gD, eS)
    # direction f = [x0 == g_b] and [x10 == g_t]
    o += [("cx", (), (1, 0)), ("cx", (), (9, 10)), ("x", (), (0,)), ("x", (), (10,)),
          ("rccx", (), (0, 10, F)), ("sdg", (), (F,)),
          ("x", (), (0,)), ("x", (), (10,)), ("cx", (), (1, 0)), ("cx", (), (9, 10))]
    for c in (1, 3):                        # f-controlled lowering + Bell map at c1, c3
        eS, eD, gS, gD = CORN[c]
        o += [("cx", (), (eS, eD)), ("ccx", (), (F, eD, eS))]
        _cch(o, gS, gD, eS)
    # sector bits: q9 = s_r^s_t (d2), q13 = s_b^s_l (d0) are f-free; q1 = s_b, q5 = s_r
    o += [("cx", (), (5, 9)), ("cx", (), (1, 13)), ("cx", (), (F, 1)), ("cx", (), (F, 5))]
    return o


def label_stage(A):
    F = A["F"]
    T0, T2 = A["T0"], A["T2"]
    o = [("x", (), (13,)), ("x", (), (9,)),
         ("rccx", (), (1, 13, T0)), ("rccx", (), (5, 9, T2)),      # T0 = s_b s_l, T2 = s_r s_t
         ("x", (), (13,)), ("x", (), (9,)),
         ("rccx", (), (T0, F, 0)), ("rccx", (), (T2, F, 10)),      # c0 / c2 partner fix
         ("cp", (-math.pi / 2,), (T0, F)), ("cp", (-math.pi / 2,), (T2, F)),
         ("cx", (), (1, 5))]                                        # q5 = d1 = s_b^s_r
    D = [13, 5, 9]
    za = [("rccx", (), (13, 5, A["M0"]))]                            # transient in the M0 slot
    o += [("x", (), (13,)), ("x", (), (5,)), ("x", (), (9,))] + za + [("rccx", (), (A["M0"], 9, A["Z"]))] + za
    o += [("x", (), (13,)), ("x", (), (5,)), ("x", (), (9,))]
    E = [A["E0"], A["E1"], A["E2"], A["E3"]]
    for c in range(4):
        o.append(("rccx", (), (CORN[c][0], CORN[c][1], E[c])))
    o += [("rccx", (), (E[0], E[1], A["C01"])), ("rccx", (), (E[2], E[3], A["C23"])),
          ("rccx", (), (A["C01"], A["C23"], A["C4"])), ("rccx", (), (A["C4"], A["Z"], A["C"]))]
    ra = [("rccx", (), (13, 5, A["M1"]))]                            # transient in the M1 slot
    o += ra + [("rccx", (), (A["M1"], 9, A["R101"]))] + ra
    o += [("cx", (), (1, 0)), ("rccx", (), (A["R101"], 0, A["XA"])), ("cx", (), (1, 0))]
    for d in D:                                                     # r = 000 -> all corners look different
        o.append(("cx", (), (A["Z"], d)))
    M = [A["M0"], A["M1"], A["M2"], A["M3"]]
    for c in range(3):
        o += [("x", (), (D[c],)), ("rccx", (), (E[c], D[c], M[c])), ("x", (), (D[c],))]
    o += [("cx", (), (9, 13)), ("cx", (), (5, 13)), ("x", (), (13,)), ("rccx", (), (E[3], 13, M[3])),
          ("x", (), (13,)), ("cx", (), (5, 13)), ("cx", (), (9, 13))]
    return o


def _table():
    th = {}
    for m in range(16):
        if bin(m).count("1") <= 2:
            th[m] = float(sum(c for (i, j), c in PAIR.items() if (m >> i) & 1 and (m >> j) & 1))
        else:
            th[m] = float(FREE[m])
    return th


def _walsh(th):
    out = {}
    for S in range(16):
        w = sum(th[m] * (-1) ** bin(m & S).count("1") for m in range(16)) / 16.0
        if abs(w) > 1e-12:
            out[S] = w
    return out


def _walk(terms):
    """shortest closed walk 0 -> all parity masks -> 0 (CX count = Hamming steps); exact DP."""
    terms = frozenset(s for s in terms if s)
    memo = {}

    def dp(cur, rem):
        key = (cur, rem)
        if key not in memo:
            if not rem:
                memo[key] = (bin(cur).count("1"), ())
            else:
                best = None
                for s in sorted(rem):
                    c, path = dp(s, rem - {s})
                    c += bin(cur ^ s).count("1")
                    if best is None or c < best[0]:
                        best = (c, (s,) + path)
                memo[key] = best
        return memo[key]

    return dp(0, terms)[1]


def rotation(A, beta):
    F = A["F"]
    M = [A["M0"], A["M1"], A["M2"], A["M3"]]
    w = _walsh(_table())                       # Rx(theta(m) beta) = H Rz(theta(m) beta) H
    o = [("h", (), (F,))]
    if 0 in w:
        o.append(("rz", (w[0] * beta,), (F,)))
    cur = 0
    for S in list(_walk(w)) + [0]:
        for c in range(4):
            if ((cur ^ S) >> c) & 1:
                o.append(("cx", (), (M[c], F)))
        cur = S
        if S:
            o.append(("rz", (w[S] * beta,), (F,)))
    o.append(("h", (), (F,)))
    # kappa = 1: control R101 & (x0^s_b) [XA] & (x10^s_b)
    o += [("cx", (), (1, 10))]
    _c2rx(o, K1 * beta, A["XA"], 10, F)
    o += [("cx", (), (1, 10))]
    # closed pair: (vacA + vacB)/sqrt2 <-> loop, kappa = 4 sqrt2
    T = [("z", (), (1,)), ("cx", (), (1, F)), ("cx", (), (1, A["T0"])), ("cx", (), (1, A["T2"])),
         ("x", (), (F,)), ("ch", (), (F, 1)), ("x", (), (F,)), ("x", (), (1,))]
    o += T
    _c2rx(o, KC * math.sqrt(2) * beta, A["C"], 1, F)
    o += _inv(T)
    return o


def all_ops(alpha, beta, A):
    pre = link_prep()
    ue = [("p", (-0.75 * alpha,), (4 * l + 1,)) for l in range(4)]     # U_E = exp(-i 3/4 alpha #Q), #Q = sum g
    V = frame(A) + label_stage(A)
    return pre + ue + V + rotation(A, beta) + _inv(V) + _inv(pre)


def build(spec):
    b = Builder(spec)
    A = dict(zip(ANC, b.alloc(len(ANC))))
    A.update(DATA_SCRATCH)
    for name, params, q in all_ops(spec.alpha, spec.beta, A):
        getattr(b, name)(*params, *q)
    return b
