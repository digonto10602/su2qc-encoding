"""Tester 436: independent exactness check of LSH seed programs with Aer statevector (own target from the METHODS-lsh rules,
own set of inner codes from the Abelian Gauss law, own gate counting).  Usage: indep_check.py label=<program.py> [...]
Not a pytest file (no test_ prefix); run by hand under tools/run-capped."""
import json, math, subprocess, sys
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL


def bit(x, k): return (x >> k) & 1
def site(x, c): return (bit(x, 3*c), bit(x, 3*c+1), bit(x, 3*c+2))      # (l_pn, l_nv, l_vp)
VALID_SITE = {(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 1, 1)}


def inner_ok(x):
    # 4 'in' sites, valid codes; Abelian Gauss law on the inner links: N_n(c) = N_p(c+1), N_n = l_pn + l_nv, N_p = l_vp + l_pn
    s = [site(x, c) for c in range(4)]
    if any(t not in VALID_SITE for t in s): return False
    for c in range(4):
        pn, nv, vp = s[c]; pn2, nv2, vp2 = s[(c+1) % 4]
        if pn + nv != vp2 + pn2: return False
    return True


INNER = [x for x in range(4096) if inner_ok(x)]
assert len(INNER) == 47, len(INNER)
IDX = {x: i for i, x in enumerate(INNER)}


def dark(x): return any(site(x, c)[1] and site(x, c)[2] for c in range(4))


def partner(x):
    d = 0
    for c in range(4):
        pn, nv, vp = site(x, c)
        d |= (6 if (nv ^ vp) else 1) << (3*c)
    return x ^ d


KW = {0: -2.0, 1: 1.0, 2: -0.5}           # k vs number of set l_nv bits (Lean coupling_by_y_weight: 2K = -4, 2, -1)


def Kmat():
    K = np.zeros((47, 47))
    for x in INNER:
        if dark(x): continue
        y = partner(x); assert y in IDX, (x, y)
        K[IDX[x], IDX[y]] = KW[sum(site(x, c)[1] for c in range(4))]
    assert np.allclose(K, K.T)
    return K


def target(alpha, beta, sign=1.0):
    w, v = np.linalg.eigh(Kmat())
    UB = (v * np.exp(-1j*sign*beta*w)) @ v.conj().T
    ph = np.array([np.exp(-1j*alpha*0.75*sum(site(x, c)[0] + site(x, c)[1] for c in range(4))) for x in INNER])
    return UB @ np.diag(ph)


def outer_touched(qc):
    off = 0; o = set()
    for r in qc.qregs:
        if r.name == "o": o |= set(range(off, off + r.size))
        off += r.size
    t = set()
    for ins in qc.data:
        for q in ins.qubits: t.add(qc.find_bit(q).index)
    return t & o


def drop_outer(qc):
    keep = [q for q in range(qc.num_qubits) if not (12 <= q < 24)]
    m = {q: i for i, q in enumerate(keep)}
    new = QuantumCircuit(len(keep))
    for ins in qc.data:
        new.append(ins.operation, [m[qc.find_bit(q).index] for q in ins.qubits])
    return new, len(keep) - 12


def run_one(path, alpha, beta, sign_check=False):
    sp = LL.spec().with_angles(alpha, beta)
    qc = E.load_program(path).build(sp).circuit()
    t = outer_touched(qc)
    assert not t, f"outer qubits touched: {sorted(t)}"
    circ, nanc = drop_outer(qc)
    n = circ.num_qubits
    sim = AerSimulator(method="statevector")
    V = np.zeros((47, 47), complex); leak_anc = 0.0; leak_gauss = 0.0
    for j, x in enumerate(INNER):
        c2 = QuantumCircuit(n)
        for b in range(12):
            if bit(x, b): c2.x(b)
        c2.compose(circ, inplace=True)
        c2.save_statevector()
        sv = np.asarray(sim.run(transpile(c2, sim, optimization_level=0)).result().get_statevector()).reshape(2**nanc, 4096)
        p_anc = float(np.sum(np.abs(sv[1:])**2)); leak_anc = max(leak_anc, p_anc)
        out = np.array([sv[0][y] for y in INNER])
        leak_gauss = max(leak_gauss, float(np.sum(np.abs(sv[0])**2) - np.sum(np.abs(out)**2)))   # data weight outside the 47 codes
        V[:, j] = out
    T = target(alpha, beta)
    ph = np.angle(np.sum(T.conj() * V)); err = V - np.exp(1j*ph) * T
    res = {"alpha": alpha, "beta": beta, "n_qubits_simulated": int(n), "op_norm_err": float(np.linalg.norm(err, 2)),
           "max_col_err": float(np.max(np.linalg.norm(err, axis=0))), "anc_leak_prob": leak_anc, "gauss_leak_prob": leak_gauss}
    if sign_check:
        Tm = target(alpha, beta, -1.0); phm = np.angle(np.sum(Tm.conj() * V))
        res["op_norm_err_vs_minus_beta"] = float(np.linalg.norm(V - np.exp(1j*phm)*Tm, 2))
    return res


import pygridsynth
ELEM = {"cx", "h", "s", "sdg", "t", "tdg", "x", "z", "rz", "p", "u1", "u", "u2", "cz", "y", "id", "barrier"}


def count_circuit(qc, eps=1e-6):
    q = qc
    for _ in range(15):
        if {i.operation.name for i in q.data} <= ELEM: break
        q = q.decompose()
    cx = 0; tf = 0; rots = []
    for ins in q.data:
        nm = ins.operation.name
        if nm in ("cx", "cz"): cx += 1
        elif nm in ("t", "tdg"): tf += 1
        elif nm in ("rz", "p", "u1"): rots.append(float(ins.operation.params[0]))
        elif nm == "u":                      # rccx's u(0,0,lam) = phase gate; u(pi/2,0,pi) = H
            th, ph, lam = [float(v) for v in ins.operation.params]
            if abs(th) < 1e-12: rots.append(ph + lam)
            elif min(abs(th - math.pi/2), abs(th - math.pi)) < 1e-12 and all(abs(v/(math.pi/2) - round(v/(math.pi/2))) < 1e-9 for v in (ph, lam)): pass   # Clifford (H, X, ...)
            else: raise RuntimeError(f"unexpected u{(th, ph, lam)}")
        elif nm == "u2":
            ph, lam = [float(v) for v in ins.operation.params]
            if not (abs(ph) < 1e-12 and abs(lam - math.pi) < 1e-12): raise RuntimeError(f"unexpected u2{(ph, lam)}")
        elif nm in ELEM: pass
        else: raise RuntimeError(f"gate {nm}")
    tsum = 0; nrot = 0
    for th in rots:
        k = th / (math.pi/4)
        if abs(k - round(k)) < 1e-9: tf += int(round(k)) % 2
        else:
            tsum += str(pygridsynth.gridsynth_gates(theta=th, epsilon=eps)).count("T"); nrot += 1
    return {"cx": cx, "t_fixed": tf, "n_rot": nrot, "t_rot_sum": tsum, "t_total_1e-6": tf + tsum, "n_qubits": qc.num_qubits}


if __name__ == "__main__":
    out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd="/home/digimonk/Projects/su2qc-encoding").stdout.strip(),
           "engine": "qiskit-aer statevector, own target from L13 rules, own inner-code set"}
    for a in sys.argv[1:]:
        label, path = a.split("=")
        r = {}
        for ab in [(0.37, 0.61), (0.91, 0.23), (1.7, 1.0)]:
            r[str(ab)] = run_one(path, *ab, sign_check=(ab == (0.37, 0.61)))
        r["counts"] = count_circuit(E.load_program(path).build(LL.spec()).circuit())
        out[label] = r
        print(label, json.dumps(r, indent=1), flush=True)
    json.dump(out, open("/home/digimonk/Projects/su2qc-encoding/results/tester/436-indep-aer.json", "w"), indent=1)
