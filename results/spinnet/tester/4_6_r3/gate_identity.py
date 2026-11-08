"""Tester 115 (a): single-qubit identities of the pi/4-shift rewrites (independent of the 433-state target).  F1 r03 `phase_fix` is called with a recording mock builder."""
import numpy as np, pathlib, sys, json
root = pathlib.Path(sys.argv[1])
ns = {"__name__": "prog"}; src = (root/"compress/programs/spinnet/F1/003-cheap-angle-forms.py").read_text(); exec(compile(src, "F1", "exec"), ns)
class Rec:
    def __init__(s): s.g = []
    def __getattr__(s, n): return lambda *a: s.g.append((n, a))
M = {"z": np.diag([1, -1]).astype(complex), "s": np.diag([1, 1j]), "sdg": np.diag([1, -1j]), "t": np.diag([1, np.exp(1j*np.pi/4)]), "tdg": np.diag([1, np.exp(-1j*np.pi/4)]), "x": np.array([[0,1],[1,0]], complex)}
rz = lambda t: np.diag([np.exp(-1j*t/2), np.exp(1j*t/2)]); p = lambda t: np.diag([1, np.exp(1j*t)])
def eq_phase(A, B):
    k = np.argmax(abs(B)); ph = A.flat[k]/B.flat[k]; return float(abs(A - ph*B).max()), abs(abs(ph)-1)
rng = np.random.default_rng(20261108); worst = {"rz": 0, "p": 0}; PI4 = np.pi/4
for m in range(-3, 9):
    r = Rec(); ns["phase_fix"](r, m, 0)
    P = np.eye(2, dtype=complex)
    for n, a in r.g: P = M[n] @ P        # gates applied in emission order: later gates on the left
    for _ in range(25):
        th = rng.uniform(-7, 7)
        # emitted: rz(th + m pi/4) then phase_fix(m)  == rz(th) up to global phase
        e1 = eq_phase(P @ rz(th + m*PI4), rz(th))[0]
        # electric: p(lam + m pi/4) then phase_fix(m) == p(lam) up to global phase, exactly (relative phase of |1> vs |0>)
        e2 = eq_phase(P @ p(th + m*PI4), p(th))[0]
        worst["rz"] = max(worst["rz"], e1); worst["p"] = max(worst["p"], e2)
# sign flips: X rz(t) X = rz(-t); X p(l) X = diag(e^{il},1) = e^{il} p(-l)
e3 = max(eq_phase(M["x"] @ rz(t) @ M["x"], rz(-t))[0] for t in rng.uniform(-7, 7, 25))
e4 = max(eq_phase(M["x"] @ p(t) @ M["x"], p(-t))[0] for t in rng.uniform(-7, 7, 25))
# F2: p(l + pi/4) tdg == p(l); rz(th +- pi/4) tdg/t == rz(th) up to phase
e5 = max(eq_phase(M["tdg"] @ p(t + PI4), p(t))[0] for t in rng.uniform(-7, 7, 25))
e6 = max(max(eq_phase(M["tdg"] @ rz(t + PI4), rz(t))[0], eq_phase(M["t"] @ rz(t - PI4), rz(t))[0]) for t in rng.uniform(-7, 7, 25))
print(json.dumps({"F1_phase_fix_rz_worst": worst["rz"], "F1_phase_fix_p_worst": worst["p"], "X_conj_rz": e3, "X_conj_p": e4, "F2_p_shift_tdg": e5, "F2_rz_shift_t_tdg": e6}))
