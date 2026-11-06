"""Tester independent checks for report 107 (prompts/102 W1-W3).  Run from repo root; writes results/spinnet/tester/m3x_independent.json.
C1  exact K from sympy 6j (own implementation of METHODS section 5) == Lean twoK?/kEntry? (47x47) == production K_codes
C2  Lean ubGates (parsed from the .lean file) == gate list of qiskit build_UB(beta) for several beta (own parser)
C3  Lean-evaluated runGates(ubGates) at z = e^{i beta/4} vs qiskit Statevector of build_UB(beta) on all 47 codes (clean ancillas)
    and vs expm(-i beta K) from production K_codes (independent of Lean)
C4  Lean gate matrices vs qiskit Operator for x, cx, rccx (all 6 wirings), h, rz(a) on 3 qubits
C5  Lean eigenvector list: orthogonal, complete (433), and H V = V diag(lambda) with H = enc.h_magnetic() (production route B)
"""
import itertools, json, math, pathlib, re, subprocess, sys, time
import numpy as np, sympy
from sympy import Rational, sqrt
from sympy.physics.wigner import wigner_6j
sys.path.insert(0, "src")
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.circuits.spinnet import build_UB
from su2plaq.spinnet import lean_export as LE
from qiskit.quantum_info import Statevector, Operator
from qiskit import QuantumCircuit
import scipy.linalg as sla

res = {}
enc = SpinNet()
codes = [int(c) for c in enc.inner_codes()]
REPO = pathlib.Path(".").resolve()

# ---------------- C1 exact K with sympy ----------------
def fsym_sp(j1, j2, j12, j3, J, j23):          # all sympy Rational spins; Edmonds 6.1.5
    ph = (-1) ** int(j1 + j2 + j3 + J)
    return ph * sqrt((2 * j12 + 1) * (2 * j23 + 1)) * wigner_6j(j1, j2, j12, j3, J, j23)
half = Rational(1, 2)
def bit(x, k): return (x >> k) & 1
CP, CN = [3, 0, 1, 2], [0, 1, 2, 3]
def Jc_sp(y, c):
    if bit(y, 4 + c): return Rational(1)
    return Rational(0) if bit(y, CP[c]) == bit(y, CN[c]) else half
def valid(y): return all((not bit(y, 4 + c)) or (bit(y, CP[c]) and bit(y, CN[c])) for c in range(4))
def tri_ok(a, b, c): return abs(a - b) <= c <= a + b and (a + b + c).is_integer
def P_sp(yn, y):
    if (yn & 15) != ((y & 15) ^ 15): return 0
    if any(Jc_sp(yn, c) != Jc_sp(y, c) for c in range(4)): return 0
    amp = Rational(1)
    for c in range(4):
        jp, jn = half * bit(y, CP[c]), half * bit(y, CN[c])
        jpn, jnn = half * bit(yn, CP[c]), half * bit(yn, CN[c])
        J = Jc_sp(y, c)
        # skip inadmissible triads exactly as zero
        if not (tri_ok(J, jp, jn) and tri_ok(half, jnn, jpn) and tri_ok(J, jnn, jpn) and tri_ok(half, jp, jn)):
            pass
        try:
            amp *= fsym_sp(J, jp, jn, half, jnn, jpn)
        except ValueError:
            return 0
    return sympy.nsimplify(amp)
valid_codes = [y for y in range(256) if valid(y)]
assert valid_codes == codes, "codec differs"
K_sp = {}
for y in valid_codes:
    for yn in valid_codes:
        K_sp[(yn, y)] = -(P_sp(yn, y) + P_sp(y, yn))
twoK_sp = [2 * K_sp[(y ^ 15, y)] if (y ^ 15) in valid_codes else Rational(0) for y in codes]
tbl = LE.coupling_ints(enc)
res["C1_twoK_sympy_exact_equals_exported"] = all(sympy.simplify(a - b) == 0 for a, b in zip(twoK_sp, tbl))
res["C1_twoK_values_sorted_set"] = sorted(set(int(v) for v in twoK_sp))
# off-flip entries all zero
res["C1_offflip_all_zero"] = all(K_sp[(yn, y)] == 0 for y in valid_codes for yn in valid_codes if yn != y ^ 15)
# production K_codes
Kc = enc.K_codes
idx = {c: i for i, c in enumerate(codes)}
Kex = np.array([[float(K_sp[(yn, y)]) for y in codes] for yn in codes])
res["C1_max|K_sympy - K_codes_production|"] = float(np.abs(Kex - Kc).max())
# Lean kEntry? on all 47x47: print 2*num/den
body = ("open Su2Plaq.SpinNet in\n#eval IO.println (String.intercalate \"\\n\" (validCodes.flatMap fun y => validCodes.map fun y' =>\n"
        "  match kEntry? y' y with | some k => s!\"{y'} {y} {k.num} {k.den}\" | none => s!\"{y'} {y} 0 0\"))")
rows = LE._lean_lines(LE.lean_eval(body), 4)
assert len(rows) == 47 * 47
bad = 0; none = 0
for yn, y, n, d in rows:
    if d == 0: none += 1; continue
    if Rational(n, d) != K_sp[(yn, y)]: bad += 1
res["C1_lean_kEntry_vs_sympy_mismatches_of_2209"] = bad
res["C1_lean_kEntry_none_count"] = none

# ---------------- C2 gate list: own parser of the .lean file ----------------
sem = (REPO / "lean/Su2Plaq/SpinNet/Semantics.lean").read_text()
m = re.search(r"def ubGates : List Gate := \[(.*?)\]\n", sem, re.S)
toks = [t.strip() for t in re.split(r",\s*(?=\.)", m.group(1))]
def parse(t):
    p = t.replace("(", " ").replace(")", " ").split()
    return (p[0][1:],) + tuple(int(x) for x in p[1:])
lean_g = [parse(t) for t in toks]
def own_gate_list(qc):
    out = []
    beta = qc.metadata["beta"]
    for ins in qc.data:
        qs = [qc._data.qubits.index(q) if hasattr(qc._data, "qubits") else None for q in ins.qubits]
        qs = [qc.find_bit(q).index for q in ins.qubits]
        n = ins.operation.name
        if n == "rz":
            out.append(("rz", qs[0], int(round(float(ins.operation.params[0]) / (beta / 2)))))
        else:
            out.append((n, *qs))
    return out
ok2 = {}
for beta in (1.0, 0.61, 0.05, 2.3, -0.7):
    ok2[str(beta)] = own_gate_list(build_UB(beta)) == lean_g
res["C2_lean_gate_list_equals_qiskit_build_UB"] = ok2
res["C2_n_gates"] = len(lean_g)
from collections import Counter
res["C2_gate_counts"] = dict(Counter(g[0] for g in lean_g))

# ---------------- C3 Lean-evaluated circuit vs Qiskit statevector and vs expm(-i beta K) ----------------
body = ("open Su2Plaq.SpinNet in\n#eval IO.println (String.intercalate \"\\n\" (validCodes.flatMap fun y =>\n"
        "  (runGates ubGates [(y, [(0, 1, 0)])]).flatMap fun p => p.2.map fun t => s!\"{y} {p.1} {t.1} {t.2.1} {t.2.2}\"))")
rows = LE._lean_lines(LE.lean_eval(body, imports=("Su2Plaq.SpinNet.Semantics",)), 5)
res["C3_lean_terms"] = len(rows)
maxdev_qk, maxdev_expm, maxanc = 0.0, 0.0, 0.0
for beta in (0.61, 1.0, 0.05, 2.3, -0.7, 3.9):
    z = np.exp(1j * beta / 4)
    qc = build_UB(beta)
    E = sla.expm(-1j * beta * Kc)
    lean_out = {}
    for y, j, mm, re_, im_ in rows:
        lean_out.setdefault(y, {}).setdefault(j, 0j)
        lean_out[y][j] += complex(re_, im_) * z ** mm
    for ci, y in enumerate(codes):
        sv = Statevector.from_label("0" * 15)  # placeholder
        v0 = np.zeros(2 ** 15, complex); v0[y] = 1
        out = np.asarray(Statevector(v0).evolve(qc).data)
        lean_vec = np.zeros(2 ** 15, complex)
        for j, c in lean_out[y].items(): lean_vec[j] = c / 2.0   # global (1/sqrt2)^2
        maxdev_qk = max(maxdev_qk, float(np.abs(out - lean_vec).max()))
        # vs expm(-i beta K) on the inner block, support only inside the 47 codes, ancillas clean
        ref = np.zeros(2 ** 15, complex)
        for cj, yp in enumerate(codes): ref[yp] = E[cj, ci]
        maxdev_expm = max(maxdev_expm, float(np.abs(lean_vec - ref).max()))
        maxanc = max(maxanc, float(np.abs(out[256:]).max()))
res["C3_max|lean_run - qiskit_statevector| (6 betas x 47 codes)"] = maxdev_qk
res["C3_max|lean_run - expm(-i beta K_production)|"] = maxdev_expm
res["C3_max qiskit ancilla/outside-data amplitude"] = maxanc

# ---------------- C4 gate matrices ----------------
def qk_gate(name, qs, a, n, beta):
    qc = QuantumCircuit(n)
    if name == "x": qc.x(*qs)
    elif name == "cx": qc.cx(*qs)
    elif name == "rccx": qc.rccx(*qs)
    elif name == "h": qc.h(*qs)
    elif name == "rz": qc.rz(a * beta / 2, qs[0])
    return Operator(qc).data
dev = {}
beta = 0.61
cases = [("x", (q,), None, 3) for q in range(3)] + [("cx", p, None, 3) for p in itertools.permutations(range(3), 2)] + \
        [("rccx", p, None, 3) for p in itertools.permutations(range(3), 3)] + [("h", (q,), None, 3) for q in range(3)] + \
        [("rz", (q,), a, 3) for q in (0, 2) for a in (-7, -2, 3, 6)]
for name, qs, a, n in cases:
    g = (name, *qs) if name != "rz" else ("rz", qs[0], a)
    M = LE.lean_gate_images(g, n, beta)
    R = qk_gate(name, qs, a, n, beta)
    dev[f"{name}{qs}{'' if a is None else a}"] = float(np.abs(M - R).max())
res["C4_max_dev"] = max(dev.values()); res["C4_n_cases"] = len(dev)
res["C4_worst_case"] = max(dev, key=dev.get)

# ---------------- C5 eigenvectors ----------------
body = ("open Su2Plaq.SpinNet in\n#eval IO.println (String.intercalate \"\\n\" (blocks.flatMap fun ob => (eigsOf ob.2).map fun e =>\n"
        "  s!\"{ob.1} {e.1} {e.2.1} {e.2.2}\"))")
rows = LE._lean_lines(LE.lean_eval(body, imports=("Su2Plaq.SpinNet.Spectrum",)), 4)
res["C5_n_eigvecs"] = len(rows)
lab_codes = [int(c) for c in enc._codes]            # y + 256 o  in encoding order
pos = {c: i for i, c in enumerate(lab_codes)}
V = np.zeros((433, 433)); lam = np.zeros(433)
for k, (o, y, s, l2) in enumerate(rows):
    V[pos[y + 256 * o], k] = 1
    if s != 0: V[pos[(y ^ 15) + 256 * o], k] = s
    lam[k] = l2 / 2.0
H = enc.h_magnetic()
res["C5_H_symmetric_dev"] = float(np.abs(H - H.T).max())
res["C5_max|H V - V diag(lambda)|"] = float(np.abs(H @ V - V * lam).max())
G = V.T @ V
res["C5_max offdiag Gram (orthogonality)"] = float(np.abs(G - np.diag(np.diag(G))).max())
res["C5_min diag Gram"] = float(np.diag(G).min())
res["C5_rank V"] = int(np.linalg.matrix_rank(V))
ev = np.linalg.eigvalsh(H)
res["C5_lean_vs_eigvalsh_sorted_maxdev"] = float(np.abs(np.sort(lam) - np.sort(ev)).max())
res["C5_multiplicities_2lambda"] = {int(k): int((np.round(2 * lam) == k).sum()) for k in (-4, -2, -1, 0, 1, 2, 4)}
res["C5_pairs_per_block_dups"] = int(len(set((o, y) for o, y, s, l in rows)) != 433)
# also Lean's own hb2 vs production H
body = ("open Su2Plaq.SpinNet in\n#eval IO.println (String.intercalate \"\\n\" (states.flatMap fun s => states.filterMap fun t =>\n"
        "  let v := hb2 t s; if v == 0 then none else some s!\"{t.1 + 256 * t.2} {s.1 + 256 * s.2} {v}\"))")
t0 = time.time()
rows = LE._lean_lines(LE.lean_eval(body, imports=("Su2Plaq.SpinNet.Spectrum",), timeout=600), 3)
Hl = np.zeros((433, 433))
for t, s, v in rows: Hl[pos[t], pos[s]] = v / 2.0
res["C5_max|Lean hb2/2 - production h_magnetic| (433x433 dense)"] = float(np.abs(Hl - H).max())
res["C5_hb2_nonzero_entries"] = len(rows)
res["_meta"] = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() + "+uncommitted",
                "seed": None, "betas_C3": [0.61, 1.0, 0.05, 2.3, -0.7, 3.9], "beta_C4": 0.61}
pathlib.Path("results/spinnet/tester/m3x_independent.json").write_text(json.dumps(res, indent=1, default=str))
for k, v in res.items(): print(k, v)
