"""Tester 117: single-qubit identities for r04-F1-004: phase_fix(m) after p(l + m pi/4) == p(l) and after rz(th + m pi/4) == rz(th) up to global phase, m=-3..8; and F3-004 inline forms."""
import numpy as np, pathlib, json
ns = {"__name__": "prog"}; exec(compile(pathlib.Path("compress/programs/spinnet/F1/004-depth-forms.py").read_text(), "F1", "exec"), ns)
class Rec:
    def __init__(s): s.g = []
    def __getattr__(s, n): return lambda *a: s.g.append((n, a))
PI4 = np.pi/4
M = {"z": np.diag([1,-1]).astype(complex), "s": np.diag([1,1j]), "sdg": np.diag([1,-1j]), "t": np.diag([1,np.exp(1j*PI4)]), "tdg": np.diag([1,np.exp(-1j*PI4)]), "x": np.array([[0,1],[1,0]],complex)}
rz = lambda t: np.diag([np.exp(-1j*t/2), np.exp(1j*t/2)]); p = lambda t: np.diag([1, np.exp(1j*t)])
def eq(A, B):
    k = np.argmax(abs(B)); ph = A.flat[k]/B.flat[k]; return float(abs(A - ph*B).max()), float(abs(abs(ph)-1))
rng = np.random.default_rng(20261110); w = {"rz": 0, "p": 0, "gates_ok": True}
for m in range(-3, 9):
    r = Rec(); ns["phase_fix"](r, m, 0); P = np.eye(2, dtype=complex)
    for n, a in r.g: P = M[n] @ P
    for _ in range(25):
        th = rng.uniform(-7, 7)
        w["rz"] = max(w["rz"], eq(P @ rz(th + m*PI4), rz(th))[0]); w["p"] = max(w["p"], eq(P @ p(th + m*PI4), p(th))[0])
# exactness of phase_fix as p(-m pi/4) alone
w["fix_vs_p"] = 0
for m in range(-3, 9):
    r = Rec(); ns["phase_fix"](r, m, 0); P = np.eye(2, dtype=complex)
    for n, a in r.g: P = M[n] @ P
    w["fix_vs_p"] = max(w["fix_vs_p"], eq(P, p(-m*PI4))[0])
# F3-004 inline: p(l +- pi/2 + pi/4) tdg = p(l) s^{+-1} ; rz(th + k pi/2 + q pi/4) tdg^q ... = rz(th) sdg^k  (check q=1, k in -1..2)
e = 0
for l in rng.uniform(-7, 7, 25):
    for s, G in ((+1, M["s"]), (-1, M["sdg"])):
        e = max(e, eq(M["tdg"] @ p(l + s*np.pi/2 + PI4), p(l) @ G)[0])
Gk = {0: np.eye(2), 1: M["sdg"], 2: M["z"], -1: M["s"]}
for th in rng.uniform(-7, 7, 25):
    for k, G in Gk.items(): e = max(e, eq(M["tdg"] @ rz(th + k*np.pi/2 + PI4) @ np.eye(2), rz(th + k*np.pi/2) @ np.eye(2) )[0])
w["F3_inline"] = e
print(json.dumps(w))
