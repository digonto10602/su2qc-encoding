"""Tester 444: own re-derivation of the 37 labels and the target 2K on them (task: independent of the proposer's lab.txt).
Own 24-bit codes (own_sparse.mine), own exact magnetic block HB (6j), the F3-006 frame = every gate before the first h(0) of the program as built,
run through my own sparse engine on ALL 433 physical states.  Label = bits (q1=p, q4=y1, q7=y2, q10=y3, q9=e, q13=a) of the post-frame basis state
as integer p+2*y1+4*y2+8*y3+16*e+32*a.  Pair: partner s' = the unique state with HB[s,s'] != 0 (bright states); K = HB[s,s'].
Effective pair coupling in the pivot frame: g(s) = 2 * sigma(s') * conj(sigma(s)) * K, sigma = amplitude of F1|s> (a basis state).
Checks: (1) F1|s> is a single basis state with |sigma|=1; (2) q14 = q13 xor q9; (3) partner has same label, differs in pivot (bit 0) only (after frame);
(4) g is a function of the label; set of labels and g vs lab.txt; (5) the headline walk (START_C, WALK of F3-005 and F3-006) reproduces g on all 433 states.
Run: PYTHONPATH=src python results/tester/444/labels_own.py  -> results/tester/444/labels_own.json   No RNG."""
import json, sys, subprocess, pathlib, importlib.util, warnings
warnings.filterwarnings("ignore")
import numpy as np
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, str(ROOT / "results/tester/444"))
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": None}
def prog(rel):
    return E.load_program(str(ROOT / "compress/programs/lsh" / rel))
P6 = "F3/006-exh21-negative-walk22b.py"; P5 = "F3/005-alpha-early-walk22.py"
qc = prog(P6).build(LL.spec().with_angles(0.0, 0.61)).circuit(); G = OS.gates_of(qc)   # alpha = 0: the p(-3 alpha/4) electric phases are diagonal and not part of the pair frame
i0 = next(i for i, x in enumerate(G) if x[0] == "h" and x[1] == [0])
# merged block before h(0): s(0) sdg(9) cx(0,9) s(9) = collapse CX(0,9) + the first walk toggle CX(9,0) written as CZ before h(0) (free toggle merge).
# Unmerged equivalent: frame F = (all gates before s(0)) + cx(0,9); then h(0), CX(9,0), rz(START), ... walk starts at point 0, first toggle e.
j = next(i for i, x in enumerate(G) if x[0] == "s" and x[1] == [0])
assert [x[:2] for x in G[j:i0]] == [("s", [0]), ("sdg", [9]), ("cx", [0, 9]), ("s", [9])], G[j:i0]
F1 = G[:j] + [("cx", [0, 9], [])]
# own check of the merge identity: [s0 sdg9 cx09 s9] then H0  ==  CX(0,9) then CZ(0,9) then H0 up to a global phase (4x4 matrices)
import numpy as _np
from qiskit import QuantumCircuit as _QC
from qiskit.quantum_info import Operator as _Op
a = _QC(2); a.s(0); a.sdg(1); a.cx(0, 1); a.s(1)
b = _QC(2); b.cx(0, 1); b.cz(0, 1)
A = _Op(a).data; B = _Op(b).data; ph = _np.vdot(B.ravel(), A.ravel()); ph /= abs(ph)
out["merge_identity_dev"] = float(_np.abs(A - ph * B).max())
out["n_prefix_gates"] = len(F1); out["prefix_last"] = F1[-1][:2]
bit = lambda k, q: (k >> q) & 1
lab = {}; sig = {}; piv = {}; tt = {}
for s in range(433):
    st = OS.sim(F1, OS.mine[s])
    assert len(st) == 1, ("not a single basis state", s, len(st))
    (t, a), = st.items(); assert abs(abs(a) - 1) < 1e-12
    assert not (t >> 24)
    assert bit(t, 14) == (bit(t, 13) ^ bit(t, 9)), "q14 != q13^q9"
    L = bit(t, 1) | bit(t, 4) << 1 | bit(t, 7) << 2 | bit(t, 10) << 3 | bit(t, 9) << 4 | bit(t, 13) << 5
    lab[s] = L; sig[s] = a; piv[s] = bit(t, 0); tt[s] = t
out["q14_equals_q13_xor_q9"] = True
HB = OS.HB
bright = [s for s in range(433) if np.abs(HB[s]).max() > 1e-12]
out["n_bright_rows"] = len(bright)
nz = [int(np.count_nonzero(np.abs(HB[s]) > 1e-12)) for s in bright]
out["nonzeros_per_bright_row"] = sorted(set(nz))
g = {}; bad = []
for s in range(433):
    if s not in bright: g[s] = 0.0; continue
    js = np.flatnonzero(np.abs(HB[s]) > 1e-12); assert len(js) == 1 and js[0] != s
    sp = int(js[0]); K = HB[s, sp]
    if lab[sp] != lab[s] or (tt[s] ^ tt[sp]) != 1: bad.append((s, sp))
    g[s] = 2 * sig[sp] * np.conj(sig[s]) * K
out["pair_bad"] = len(bad)
imag = max(abs(np.imag(v)) for v in g.values()); out["max_imag_g"] = float(imag)
byl = {}
for s in range(433): byl.setdefault(lab[s], set()).add(round(float(np.real(g[s])), 9))
out["n_labels"] = len(byl); out["labels_with_multiple_g"] = {int(k): sorted(v) for k, v in byl.items() if len(v) > 1}
mylab = {int(k): next(iter(v)) for k, v in byl.items()}
txt = [l.split() for l in open(ROOT / "results/compress/lsh/evidence/r06-F3-exh21/lab.txt").read().split("\n")[1:] if l.strip()]
theirs = {int(a): float(b) for a, b in txt}
out["labels_equal_set"] = set(mylab) == set(theirs)
out["labels_only_mine"] = sorted(set(mylab) - set(theirs)); out["labels_only_theirs"] = sorted(set(theirs) - set(mylab))
out["g_equal"] = all(abs(mylab[k] - theirs[k]) < 1e-9 for k in set(mylab) & set(theirs))
out["g_equal_up_to_global_sign"] = all(abs(mylab[k] + theirs[k]) < 1e-9 for k in set(mylab) & set(theirs))
out["my_g"] = {str(k): v for k, v in sorted(mylab.items())}
# states per label and nonzero g labels
out["labels_nonzero_g"] = {str(k): v for k, v in sorted(mylab.items()) if abs(v) > 1e-9}
# walks of the known exact circuits reproduce g?
from fractions import Fraction
src = {"p": 1, "y1": 2, "y2": 4, "y3": 8, "e": 16, "oA0": 32, "oB0": 48}
def walk_coeffs(rel):
    m = importlib.util.spec_from_file_location("pp", ROOT / "compress/programs/lsh" / rel); mod = importlib.util.module_from_spec(m); m.loader.exec_module(mod)
    c = {}; x = 16; c[16] = c.get(16, 0) + float(mod.START_C)       # start point e (free first toggle merged into the collapse CX)
    for gname, cc in mod.WALK:
        x ^= src[gname]; c[x] = c.get(x, 0) + float(cc)
    return c, x
def chi(x, L): return -1.0 if bin(x & L).count("1") & 1 else 1.0
out["walk_check"] = {}
for nm, rel in (("F3-006", P6), ("F3-005", P5)):
    c, xend = walk_coeffs(rel)
    pred = {L: sum(v * chi(x, L) for x, v in c.items()) for L in mylab}
    d = max(abs(pred[L] - mylab[L]) for L in mylab); ds = max(abs(pred[L] + mylab[L]) for L in mylab)
    out["walk_check"][nm] = {"end_point": xend, "n_support": sum(1 for v in c.values() if abs(v) > 1e-12), "n_points": len(c), "max_dev_vs_my_g": d, "max_dev_vs_minus_g": ds,
                              "sum_of_walk_counts": len(rel)}
# F3-005 walk uses generators of the same set?
print(json.dumps({k: v for k, v in out.items() if k not in ("my_g", "labels_nonzero_g")}, indent=1))
print("nonzero g:", out["labels_nonzero_g"])
json.dump(out, open(ROOT / "results/tester/444/labels_own.json", "w"), indent=1, default=str)
