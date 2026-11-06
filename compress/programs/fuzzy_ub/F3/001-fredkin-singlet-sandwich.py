"""SUMMARY: per-sector f-controlled Fredkin routing of q2 spins so each parity sector is X_f (x) (vertex-singlet projector); Bell-decode the singlet pairs into flags and apply one multi-controlled R_x(-4 beta sigma) on f per sector.
DISCOVERY: with f-controlled swaps of q2 (control q1^b) every parity sector becomes exactly sigma X_f (x) |S><S|_pairs (x) I: p0 (b r)(t l)->rt, p1 (r t)(r l)->br, p2 (b r)(r t)->tl, p3 (b t)->br&tl sigma 4, p4 (b r)(r l)->rt, p5 (b l)(r t)->br, p6 (b r)(r t)(t l)->identity sigma 1, p7 (b t)(t l)->br.
DISCOVERY: no product of <=3 raw-q1-controlled q2 swaps brings all 8 sectors into that normal form simultaneously.
"""
FAMILY = "F3"
PARENT = None

from su2plaq.compress.builder import Builder

# sector -> (fredkin pairs (link indices b=0,r=1,t=2,l=3), decoded pairs, sigma)
SECTORS = {
    0: ([(0, 1), (2, 3)], [(1, 2)], 2),
    1: ([(1, 2), (1, 3)], [(0, 1)], 2),
    2: ([(0, 1), (1, 2)], [(2, 3)], 2),
    3: ([(0, 2)], [(0, 1), (2, 3)], 4),
    4: ([(0, 1), (1, 3)], [(1, 2)], 2),
    5: ([(1, 2), (0, 3)], [(0, 1)], 2),
    6: ([(0, 1), (1, 2), (2, 3)], [], 1),
    7: ([(0, 2), (2, 3)], [(0, 1)], 2),
}
ORDER = [0, 4, 2, 6, 1, 5, 3, 7]
F = 1  # q1^b


def fredkin(b, x, y):
    qx, qy = 2 * x, 2 * y
    b.cx(qy, qx)
    b.ccx(F, qx, qy)
    b.cx(qy, qx)


def mcrx(b, theta, controls, anc):
    if len(controls) == 1:
        b.crx(theta, controls[0], F)
        return
    chain = []
    cur = controls[0]
    for i, c in enumerate(controls[1:]):
        b.rccx(cur, c, anc[i])
        chain.append((cur, c, anc[i]))
        cur = anc[i]
    b.crx(theta, cur, F)
    for g in reversed(chain):
        b.rccx(*g)


def build(spec):
    b = Builder(spec)
    anc = b.alloc(6, "work")
    pq = [3, 5, 7]
    ops = []

    def push(op):
        # adjacent self-inverse / inverse-pair cancellation at the macro level
        if ops and op[0] in ("F", "B", "Bd") and ops[-1][1:] == op[1:] and (
                (op[0] == "F" and ops[-1][0] == "F") or {op[0], ops[-1][0]} == {"B", "Bd"}):
            ops.pop()
        else:
            ops.append(op)

    for s in ORDER:
        fr, pairs, sig = SECTORS[s]
        for (x, y) in fr:
            push(("F", x, y))
        for (x, y) in pairs:
            push(("B", x, y))
        push(("R", s, tuple(pairs), sig))
        for (x, y) in reversed(pairs):
            push(("Bd", x, y))
        for (x, y) in reversed(fr):
            push(("F", x, y))
    b.cx(1, 3); b.cx(1, 5); b.cx(1, 7)
    for op in ops:
        if op[0] == "F":
            fredkin(b, op[1], op[2])
        elif op[0] == "B":
            b.cx(2 * op[1], 2 * op[2]); b.h(2 * op[1])
        elif op[0] == "Bd":
            b.h(2 * op[1]); b.cx(2 * op[1], 2 * op[2])
        else:
            _, s, pairs, sig = op
            neg = [pq[k] for k in range(3) if not (s >> k) & 1]
            for q in neg:
                b.x(q)
            ctrls = pq + [q for (x, y) in pairs for q in (2 * x, 2 * y)]
            mcrx(b, -4.0 * sig * spec.beta, ctrls, anc)
            for q in neg:
                b.x(q)
    b.cx(1, 7); b.cx(1, 5); b.cx(1, 3)
    b.free(anc)
    return b
