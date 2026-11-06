import json, random, sys
from fractions import Fraction
import sympy as sp
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.lean import exact as E
random.seed(20261106)
B = [sp.Integer(1), sp.I, sp.sqrt(2), sp.I*sp.sqrt(2), sp.sqrt(3), sp.I*sp.sqrt(3), sp.sqrt(6), sp.I*sp.sqrt(6)]
def tosym(c): return sum(sp.Rational(x.numerator, x.denominator)*b for x, b in zip(c, B))
def fromsym(e):
    e = sp.expand(e)
    d = e.as_coefficients_dict()
    out = []
    for b in B:
        out.append(Fraction(int(d.get(b, 0).p), int(d.get(b, 0).q)) if d.get(b, 0) != 0 else Fraction(0))
    # check nothing else
    rest = sp.expand(e - tosym(out))
    assert rest == 0, (e, rest)
    return out
def fs(c): return [str(x) for x in c]
def rk(sparse=0.0):
    c = []
    for _ in range(8):
        if random.random() < sparse: c.append(Fraction(0))
        else: c.append(Fraction(random.randint(-9, 9), random.randint(1, 7)))
    return c
def conjsym(c):
    return fromsym(sp.conjugate(tosym(c)))
res = {"k": [], "lp": []}
nbad_py = 0
for t in range(1200):
    # mix: dense, sparse (rational-only, no-sqrt3 etc.)
    mode = t % 8
    if mode == 0: x, y = rk(), rk()
    elif mode == 1:
        x, y = rk(), rk(); 
        for i in range(1,8): y[i] = Fraction(0)       # y rational
    elif mode == 2:
        x, y = rk(), rk()
        for i in range(4,8): x[i] = Fraction(0); y[i] = Fraction(0)  # no sqrt3
    elif mode == 3:
        x, y = rk(0.6), rk(0.6)
    elif mode == 4:   # both real
        x, y = rk(), rk()
        for i in (1,3,5,7): x[i] = Fraction(0); y[i] = Fraction(0)
    elif mode == 5:   # x real, y general; x no sqrt3, y with
        x, y = rk(), rk()
        for i in (1,3,4,5,6,7): x[i] = Fraction(0) if i!=1 else x[i]
        x[1] = Fraction(0); x[3] = Fraction(0)
    elif mode == 6:   # x no sqrt3 (complex), y with sqrt3
        x, y = rk(), rk()
        for i in range(4,8): x[i] = Fraction(0)
    else:             # x with sqrt3 only, y no sqrt3
        x, y = rk(), rk()
        for i in range(4,8): y[i] = Fraction(0)
        for i in range(0,4): x[i] = Fraction(0)
    sx, sy = tosym(x), tosym(y)
    s = fromsym(sx + sy); p = fromsym(sx * sy); n = fromsym(-sx); cj = conjsym(x)
    # python KNum
    X, Y = E.KNum(*x), E.KNum(*y)
    assert list((X+Y).comps()) == s, "py add"
    assert list((X*Y).comps()) == p, "py mul"
    assert list((-X).comps()) == n
    assert list(X.conj().comps()) == cj, "py conj"
    if any(x):
        iv = fromsym(1/sx) if False else None
        assert (X*X.inv()) == E.KNum(1)
    res["k"].append({"x": fs(x), "y": fs(y), "sum": fs(s), "prod": fs(p), "neg": fs(n), "eq": x == y})
# equal-different-representation: x == x (same), x vs y differing in one component
# Laurent
def rl(nt):
    terms = {}
    for _ in range(nt):
        e = (random.randint(-3, 3), random.randint(-3, 3))
        terms[e] = rk(0.3)
    return terms
za, zb = sp.symbols("za zb")
def lsym(terms):
    return sum(tosym(c)*za**e[0]*zb**e[1] for e, c in terms.items())
def lfromsym(expr):
    # collect by monomial
    expr = sp.expand(expr)
    P = sp.Poly(sp.expand(expr * za**20 * zb**20), za, zb)
    out = {}
    for (i, j), co in P.terms():
        c = fromsym(co)
        if any(c): out[(i-20, j-20)] = c
    return out
for t in range(120):
    p, q = rl(random.randint(0, 6)), rl(random.randint(0, 6))
    sp_, sq = lsym(p), lsym(q)
    s = lfromsym(sp_ + sq); pr = lfromsym(sp_ * sq)
    def pl(d): return [[list(e), fs(c)] for e, c in sorted(d.items()) if any(c)]
    # python check
    P = E.Laurent(); Q = E.Laurent()
    for e, c in p.items(): P = P + E.Laurent.mono(e, E.KNum(*c))
    for e, c in q.items(): Q = Q + E.Laurent.mono(e, E.KNum(*c))
    PS = P + Q; PP = P * Q
    assert {e: list(v.comps()) for e, v in PS.items()} == s
    assert {e: list(v.comps()) for e, v in PP.items()} == pr
    res["lp"].append({"p": [[list(e), fs(c)] for e, c in p.items()], "q": [[list(e), fs(c)] for e, c in q.items()],
                      "sum": pl(s), "prod": pl(pr)})
json.dump(res, open("r2/kdata.json", "w"))
print("python KNum/Laurent ok vs sympy:", len(res["k"]), len(res["lp"]))
