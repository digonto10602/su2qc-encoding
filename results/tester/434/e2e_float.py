"""Tester 434 item 2/3: certificate JSON -> own dict-based float simulator (independent of repo sparse_sim and of the Lean checker) at random
angle triples, compared with a dense scipy.linalg.expm construction of the physical target (target_check.py construction).
usage: e2e_float.py <label> <cert.json> <kind> ; kind in UE UB UD step"""
import sys, json, itertools, math, cmath, numpy as np, scipy.linalg as sla
from su2plaq.rishon.algebra import RishonLink
label, path, kind = sys.argv[1:4]
cert = json.load(open(path)); base = cert["base"]
rl = RishonLink(); sec = [int(s) for s in rl.sector]
def Rr(M): return np.asarray(M)[np.ix_(sec, sec)].astype(complex)
U = [[Rr(rl.U(i, j)) for j in range(2)] for i in range(2)]; Ud = [[Rr(rl.Udag(i, j)) for j in range(2)] for i in range(2)]
def kron4(ms):
    out = np.ones((1, 1), complex)
    for m in ms: out = np.kron(m, out)
    return out
W = sum(kron4([U[a][b], U[b][c], Ud[d][c], Ud[a][d]]) for a, b, c, d in itertools.product(range(2), repeat=4))
HB = -(W + W.conj().T)
c1 = np.real(np.diag(0.5 * (rl.casimir_L + rl.casimir_R)))[sec]
HE = np.diag(sum(kron4([np.diag(c1) if l == k else np.eye(6) for l in range(4)]) for k in range(4)).real)
det = Rr(rl.det_U); hD1 = det + det.conj().T
HD = sum(kron4([hD1 if l == k else np.eye(6) for l in range(4)]) for k in range(4))
codes = sorted(sum(s << (4 * l) for l, s in enumerate(cfg)) for cfg in itertools.product(sec, repeat=4))
assert codes == cert["states"]
idx = {c: i for i, c in enumerate(codes)}
S2 = math.sqrt(2)
H2 = 1 / S2
def gate_apply(g, st, th):
    k = g["g"]; q = g["q"]; out = {}
    ang = lambda: g["m"][0] * th[0] + g["m"][1] * th[1] + g["m"][2] * th[2]
    if k == "rz":
        a = ang()    # rz(theta)=diag(e^{-i theta/2}, e^{i theta/2}), theta = m . th
        return {s: v * cmath.exp(1j * a / 2 * (1 if (s >> q[0]) & 1 else -1)) for s, v in st.items()}
    if k == "p":
        a = ang(); return {s: v * (cmath.exp(1j * a) if (s >> q[0]) & 1 else 1) for s, v in st.items()}
    if k == "cp":
        a = ang(); return {s: v * (cmath.exp(1j * a) if ((s >> q[0]) & 1 and (s >> q[1]) & 1) else 1) for s, v in st.items()}
    if k in ("z", "s", "sdg", "t", "tdg"):
        ph = {"z": -1, "s": 1j, "sdg": -1j, "t": cmath.exp(1j * math.pi / 4), "tdg": cmath.exp(-1j * math.pi / 4)}[k]
        return {s: v * (ph if (s >> q[0]) & 1 else 1) for s, v in st.items()}
    if k == "x": return {s ^ (1 << q[0]): v for s, v in st.items()}
    if k == "cx": return {(s ^ (1 << q[1]) if (s >> q[0]) & 1 else s): v for s, v in st.items()}
    if k == "cz": return {s: (-v if ((s >> q[0]) & 1 and (s >> q[1]) & 1) else v) for s, v in st.items()}
    if k == "ccx": return {(s ^ (1 << q[2]) if ((s >> q[0]) & 1 and (s >> q[1]) & 1) else s): v for s, v in st.items()}
    if k == "ccz": return {s: (-v if ((s >> q[0]) & 1 and (s >> q[1]) & 1 and (s >> q[2]) & 1) else v) for s, v in st.items()}
    if k == "swap":
        def f(s):
            a, b = (s >> q[0]) & 1, (s >> q[1]) & 1
            return s if a == b else s ^ (1 << q[0]) ^ (1 << q[1])
        return {f(s): v for s, v in st.items()}
    if k in ("h", "sx"):
        m = ((H2, H2), (H2, -H2)) if k == "h" else (((1 + 1j) / 2, (1 - 1j) / 2), ((1 - 1j) / 2, (1 + 1j) / 2))
        for s, v in st.items():
            b = (s >> q[0]) & 1; s0 = s & ~(1 << q[0]); s1 = s0 | (1 << q[0])
            out[s0] = out.get(s0, 0) + m[0][b] * v; out[s1] = out.get(s1, 0) + m[1][b] * v
        return {s: v for s, v in out.items() if abs(v) > 1e-15}
    raise ValueError(k)
def target(al, be, et):
    ue = np.diag(np.exp(-1j * al * HE)); ub = sla.expm(-1j * be * HB); ud = sla.expm(-1j * et * HD)
    return {"UE": ue, "UB": ub, "UD": ud, "step": ub @ ue}[kind]
rng = np.random.default_rng(434); worst = 0.0; maxsupp = 0; leak_worst = 0.0
ins = [0, 1295, 647] + [int(x) for x in rng.choice(1296, 9, replace=False)]
res = {"label": label, "kind": kind, "cert": path, "seed": 434, "rows": []}
for t in range(3):
    al, be, et = [float(x) for x in rng.uniform(0.05, 2.5, 3)]
    th = (al / base["d_alpha"], be / base["d_beta"], S2 * be / base["d_gamma"]) if kind != "UD" else (et / base["d_alpha"], 0.0, 0.0)
    V = target(al, be, et)
    ph = cmath.exp(1j * (cert["phase"]["m"][0] * th[0] + cert["phase"]["m"][1] * th[1] + cert["phase"]["m"][2] * th[2]))
    kk = [complex(eval(x) if "/" not in x else eval(x)) for x in cert["phase"]["k"]]
    assert abs(kk[0] - 1) < 1e-15 and all(abs(x) < 1e-15 for x in kk[1:]), "phase k != 1 in this tester script"
    for k in ins:
        st = {codes[k]: 1.0 + 0j}
        for g in cert["gates"]:
            st = gate_apply(g, st, th); maxsupp = max(maxsupp, len(st))
        ref = {codes[i]: V[i, k] for i in range(1296) if abs(V[i, k]) > 1e-16}
        keys = set(st) | set(ref)
        dev = max(abs(st.get(s, 0) - ph * ref.get(s, 0)) for s in keys)
        leak = sum(abs(v) ** 2 for s, v in st.items() if s not in idx) ** 0.5
        worst = max(worst, dev); leak_worst = max(leak_worst, leak)
        res["rows"].append({"alpha": al, "beta": be, "eta": et, "input": k, "max_dev": dev, "leak": leak})
    print(label, "triple", t, (al, be, et), "worst so far", worst, flush=True)
res["worst_dev"] = worst; res["leak_worst"] = leak_worst; res["max_support"] = maxsupp
json.dump(res, open(f"results/tester/434-e2e-{label}.json", "w"), indent=1)
print(label, "WORST max|circuit(cert gates) col - target col| =", worst, " leak", leak_worst, " max support", maxsupp)
