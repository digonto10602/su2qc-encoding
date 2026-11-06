"""SUMMARY: Spectral frame: 2-CX corner frames + type-controlled CH + padding put every bright pair on one flip qubit F (H_B = kappa(t) g X_F), outer-AND dark bits, pairwise NOR flags, 14-term exact Walsh phase polynomial of the 7-point spectrum on F.
DISCOVERY: A 2-CX corner frame U=[HSH_A,HS_B; CX(B>A); THS_A,HTH_B; CX(B>A); S,H_B] maps the same-type partner map to X_A and the diff-type one to Z_A; with CH(t->A) and padding CX(j_B->A) interleaved with the chain fold, H_B = kappa(t)*g*X_F exactly on all 433 states, kappa=-2 (n1=0), (-1)^t0 (n1=2), +1/2 (n1=4).
DISCOVERY: In that padded frame a same-type corner's dark (inner J=1) codes are 10/11/01 vs bright 00; one AND of the two outer q_m bits (the parallel branch) makes dark a single leg bit A, so dark_c = (not t_c) and A_c (4 corners -> 2 pairwise NORs a,b).
DISCOVERY: The eigenphase beta*kappa(t)*a*b over (a,b,t1,t2,t0) has minimum Walsh support 14 (MILP over the free values), Gray-walked with 20 CX.
"""
FAMILY = "F4"
PARENT = None

import numpy as np

from su2plaq.compress.builder import Builder

# corner c: inner legs A, B (twelve qubits), outer q_m qubits of its two outer links
CORN = {0: dict(A=1, B=10, mA=12, mB=14),
        1: dict(A=0, B=4, mA=16, mB=18),
        2: dict(A=3, B=6, mA=20, mB=22),
        3: dict(A=7, B=9, mA=24, mB=26)}
F = 11          # flip qubit: j_l after the chain fold
T1, T2, T0 = 2, 5, 8   # after the fold: q2 = j_b^j_r (c1), q5 = j_r^j_t (c2), q8 = j_b^j_l (c0; holds j_t^j_l (c3) first)

# signed coupling kappa(t0,t1,t2,t3) of H_B in the padded frame: H_B = kappa * [bright] * X_F; |kappa| = 2*2^(-n1/2)
# (the H_B eigenvalues), the sign is fixed by the frame (verified on all 128 bright pairs)
KAPPA = {(0, 0, 0, 0): -2.0, (0, 0, 1, 1): 1.0, (0, 1, 0, 1): 1.0, (0, 1, 1, 0): 1.0,
         (1, 0, 0, 1): -1.0, (1, 0, 1, 0): -1.0, (1, 1, 0, 0): -1.0, (1, 1, 1, 1): 0.5}
# Walsh support over bits (a, b, t1, t2, t0), constant first, then the Gray-walk order (20 CX)
CONST = (0, 0, 0, 0, 0)
WALK = [(0, 0, 0, 1, 0), (1, 1, 0, 1, 0), (1, 1, 1, 1, 1), (0, 1, 1, 1, 0), (0, 1, 1, 0, 0), (1, 0, 1, 0, 0),
        (1, 0, 0, 0, 1), (1, 1, 0, 0, 1), (0, 1, 0, 0, 1), (0, 1, 0, 1, 1), (0, 0, 1, 1, 1), (0, 0, 1, 0, 1),
        (0, 0, 0, 0, 1)]


def walsh_coefficients():
    """Exact c_S with sum_S c_S (-1)^{S.x} = kappa(t)*a*b on every reachable (a,b,t); a = NOR(d0,d1), b = NOR(d2,d3),
    d_c = dark flag of corner c (only possible on a same-type corner)."""
    supp = [CONST] + WALK
    rows, rhs, seen = [], [], {}
    for t, kap in KAPPA.items():
        for d in np.ndindex(2, 2, 2, 2):
            if any(d[i] and t[i] for i in range(4)):
                continue
            a, b = int(not (d[0] or d[1])), int(not (d[2] or d[3]))
            x = (a, b, t[1], t[2], t[0])
            val = kap if not any(d) else 0.0
            if x in seen:
                continue
            seen[x] = val
            rows.append([(-1) ** sum(p * q for p, q in zip(S, x)) for S in supp])
            rhs.append(val)
    A, rhs = np.array(rows, float), np.array(rhs)
    c, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    if np.abs(A @ c - rhs).max() > 1e-12:
        raise RuntimeError("Walsh support does not reproduce the spectrum")
    return c


def frame(b, k, ab):
    """V: corner frames + fold + dark flags + pair NORs.  Returns the emitted op list (mirrored afterwards)."""
    ops = []

    def o(name, *q):
        ops.append((name, q))
        getattr(b, name)(*q)

    def corner_U(c):
        A, B = CORN[c]["A"], CORN[c]["B"]
        o("h", A); o("s", A); o("h", A); o("h", B); o("s", B)
        o("cx", B, A)
        o("t", A); o("h", A); o("s", A); o("h", B); o("t", B); o("h", B)
        o("cx", B, A)
        o("s", B); o("h", B)           # B is never touched again: basis change that keeps the codes sparse

    def dark_fix(c, negA):
        A, mA, mB = CORN[c]["A"], CORN[c]["mA"], CORN[c]["mB"]
        if negA:   # A ^= (not mA) and mB: the rccx gate sequence with an X on the target at the mA-controlled CX
            o("h", A); o("t", A); o("cx", mB, A); o("tdg", A); o("x", A); o("cx", mA, A)
            o("t", A); o("cx", mB, A); o("tdg", A); o("h", A)
        else:      # A ^= mA and mB
            o("rccx", mA, mB, A)

    def gate(c, tq):                   # k_c = (not t_c) and A_c
        o("x", tq); o("rccx", tq, CORN[c]["A"], k[c]); o("x", tq)

    # relabel the two NOT corners (c1, c3) to the copy convention
    o("cx", 2, 0); o("z", 0)
    o("cx", 8, 7); o("z", 7)
    for c in range(4):
        corner_U(c)
    # chain fold interleaved with CH(t->A) (diff type Z_A -> X_A) and padding with the corner's B-link j (X_F X_A -> X_F)
    o("cx", 5, 2); o("ch", 2, 0); o("cx", 5, 0)            # c1: t1 in q2, pad with raw j_r
    o("cx", 8, 5); o("ch", 5, 3); o("cx", 8, 3)            # c2: t2 in q5, pad with raw j_t
    o("cx", 11, 8); o("ch", 8, 7); o("cx", 11, 7)          # c3: t3 in q8, pad with j_l
    dark_fix(3, True); gate(3, 8)
    o("cx", 2, 8); o("cx", 5, 8)                           # q8 = t1^t2^t3 = t0
    o("ch", 8, 1); o("cx", 11, 1)                          # c0: CH(t0->A0), pad with j_l
    dark_fix(0, False); gate(0, 8)
    dark_fix(1, True); gate(1, 2)
    dark_fix(2, False); gate(2, 5)
    # pair NORs a = NOR(k0,k1), b = NOR(k2,k3)
    for c in range(4):
        o("x", k[c])
    o("rccx", k[0], k[1], ab[0]); o("rccx", k[2], k[3], ab[1])
    return ops


def unframe(b, ops):
    inv = {"t": "tdg", "tdg": "t", "s": "sdg", "sdg": "s"}
    for name, q in reversed(ops):
        getattr(b, inv.get(name, name))(*q)


def build(spec):
    b = Builder(spec)
    # electric layer U_E = exp(-i 3/4 alpha sum_l j_l) on the four q_j
    for q in (2, 5, 8, 11):
        b.p(-0.75 * spec.alpha, q)
    k = b.alloc(4, "k")
    ab = b.alloc(2, "nor")
    ops = frame(b, k, ab)
    # exp(-i beta kappa(t) a b X_F) as an exact Walsh phase polynomial on F in its X basis
    coeff = walsh_coefficients()
    bits = (ab[0], ab[1], T1, T2, T0)
    b.h(F)
    b.rz(2.0 * spec.beta * float(coeff[0]), F)
    cur = CONST
    for S, c in zip(WALK, coeff[1:]):
        for i in range(5):
            if S[i] != cur[i]:
                b.cx(bits[i], F)
        cur = S
        b.rz(2.0 * spec.beta * float(c), F)
    for i in range(5):
        if cur[i]:
            b.cx(bits[i], F)
    b.h(F)
    unframe(b, ops)
    b.free(k + ab)
    return b
