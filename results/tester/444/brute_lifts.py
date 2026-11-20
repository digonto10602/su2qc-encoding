"""Tester 444: INDEPENDENT brute force of the e-lift phase of the proposer's exhaustive search (evidence/r06-F3-exh21/x.c, phase 2).
Own labels/targets: results/tester/444/labels_own.json (my_g, derived from the physical states by labels_own.py), NOT lab.txt.
For a fixed closed Q5 walk q (Q5 point = low4 bits + a at bit 4), enumerate EVERY raw walk of the 7-generator model {1,2,4,8,16,32,48} on F2^6
(p=1,y1=2,y2=4,y3=8,e=16,a=32) that projects onto q: start in {0,16}, any number n_i >= 0 of e-moves (generator 16) inserted at EVERY position i = 0..m
(no domination assumption), every a-move may be 32 or 48, end anywhere in {0,16}; cost = m + sum n_i <= LT.  Visited set U = all points visited.
Feasible = g (on my 37 labels) in span{chi_x : x in U}; chi_x(L) = (-1)^{popcount(x & L)}.  Own feasibility = exact rank over GF(2^61-1) (own code).
Output: dict U-bitmask -> minimal cost, for the feasible U only.  Usage: python brute_lifts.py "<q5 walk comma list>" LT -> prints count and writes json."""
import sys, json, itertools, pathlib
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
G = {int(k): int(round(v)) for k, v in json.load(open(ROOT / "results/tester/444/labels_own.json"))["my_g"].items()}
LABS = sorted(G)
PM = (1 << 61) - 1
def pt(v, e): return (v & 15) | (e << 4) | (((v >> 4) & 1) << 5)
CH = {x: [(-1 if bin(x & L).count("1") & 1 else 1) % PM for L in LABS] for x in range(64)}
GV = [g % PM for g in (G[L] for L in LABS)]
def rank_modp(cols):
    # rows = labels; columns given; Gaussian elimination mod p on a list of column vectors (transpose handled: eliminate over columns as vectors)
    basis = []  # list of (pivot index, vector) with vector[pivot]==1
    for c in cols:
        v = c[:]
        for pi, b in basis:
            if v[pi]:
                f = v[pi]
                v = [(a - f * bb) % PM for a, bb in zip(v, b)]
        piv = next((i for i, a in enumerate(v) if a), None)
        if piv is None: continue
        inv = pow(v[piv], PM - 2, PM); v = [a * inv % PM for a in v]
        basis.append((piv, v))
    return basis
cache = {}
def feasible(Umask):
    if Umask in cache: return cache[Umask]
    xs = [x for x in range(64) if Umask >> x & 1]
    basis = rank_modp([CH[x] for x in xs])
    v = GV[:]
    for pi, b in basis:
        if v[pi]:
            f = v[pi]; v = [(a - f * bb) % PM for a, bb in zip(v, b)]
    r = not any(v); cache[Umask] = r; return r
def run(q, LT):
    m = len(q) - 1; K = LT - m; assert q[0] == 0 and q[-1] == 0
    best = {}
    kinds = [(q[i] ^ q[i + 1]) for i in range(m)]
    assert all(bin(k).count("1") == 1 for k in kinds)
    isA = [k == 16 for k in kinds]            # Q5 bit 4 = a
    nraw = 0
    # distributions of n_i (0..K) at positions 0..m with sum <= K
    def dists(pos, left):
        if pos == m + 1: yield (); return
        for n in range(left + 1):
            for rest in dists(pos + 1, left - n): yield (n,) + rest
    D = list(dists(0, K))
    A = [i for i in range(m) if isA[i]]
    for e0 in (0, 1):
        for ch in itertools.product((0, 1), repeat=len(A)):
            carry = dict(zip(A, ch))
            for d in D:
                e = e0; U = 0
                for i in range(m + 1):
                    U |= 1 << pt(q[i], e)
                    if d[i] >= 1: U |= 1 << pt(q[i], e ^ 1)
                    e ^= d[i] & 1
                    if i < m and isA[i]: e ^= carry[i]
                cost = sum(d)
                nraw += 1
                if best.get(U, 99) > cost:
                    best[U] = cost if True else cost
    feas = {U: c for U, c in best.items() if feasible(U)}
    return nraw, len(best), feas
if __name__ == "__main__":
    q = [int(t) for t in sys.argv[1].split(",")]; LT = int(sys.argv[2])
    nraw, nU, feas = run(q, LT)
    print(f"m={len(q)-1} LT={LT} raw walks {nraw}, distinct visited sets {nU}, feasible sets {len(feas)}, min cost histogram {sorted(__import__('collections').Counter(feas.values()).items())}")
    json.dump({"q": q, "LT": LT, "raw": nraw, "n_sets": nU, "feasible": {f"{U:016x}": c for U, c in feas.items()}}, open(sys.argv[3], "w") if len(sys.argv) > 3 else open("/dev/null", "w"))
