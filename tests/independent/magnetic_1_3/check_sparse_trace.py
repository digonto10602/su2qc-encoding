"""Tester step 1.3 (diagnostic): where does the sparse state of synthesised U_B grow? one input, program order."""
import sys, json, warnings
import numpy as np
warnings.filterwarnings("ignore")
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.circuits.twelve import build_UB
from su2plaq.evaluate import sparse_sim as ss
from su2plaq.metrics.cliffordt import synthesize, pygridsynth_word
enc = TwelveQubit(); codes = enc.inner_codes()
qc = build_UB(0.61); s, info = synthesize(qc, 1e-4)
print("words:", [pygridsynth_word(p["theta"], 1e-4)[:60] for p in info["per_rotation"] if not p["exact"]][:3])
ops, ph = ss._translate(s)
hist = []; orig = ss._coalesce; calls = [0]
def spy(keys, cols, amps, n_qubits, n_cols, dropped):
    r = orig(keys, cols, amps, n_qubits, n_cols, dropped); hist.append(len(r[0])); return r
ss._coalesce = spy
# track which op index each call belongs to: run with ops list, record by wrapping branching gates count
branch_idx = [i for i, o in enumerate(ops) if o[0] in ss._BRANCH]
b = ss._run(ops, ph, s.num_qubits, np.array([int(codes[7])], dtype=np.int64), 10**8, range(len(ops)))
names = {}
for r in s.qregs:
    for k, q in enumerate(r): names[s.find_bit(q).index] = f"{r.name}[{k}]"
hist = np.array(hist); print("n branching ops", len(branch_idx), "calls", len(hist), "peak", hist.max())
first = int(np.argmax(hist > 1000)); print("first call >1000 at branching-op #", first, "gate index", branch_idx[first] if first < len(branch_idx) else None)
i0 = branch_idx[first]
for i in range(max(0, i0 - 12), i0 + 3): print(i, ops[i][0], [names[q] for q in ops[i][1]])
# growth profile at rz-word positions: print stored size vs branching-op number at multiples
for j in range(0, len(hist), max(1, len(hist) // 30)): print(j, branch_idx[j], ops[branch_idx[j]][0], [names[q] for q in ops[branch_idx[j]][1]], hist[j])
