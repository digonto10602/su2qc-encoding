import sys, time
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src"); sys.path.insert(0, ".")
import numpy as np
from mk_ub import decrx
from su2plaq.circuits.twelve import build_UE, build_UB
from su2plaq.lean import certify as C, exact as E
from su2plaq.evaluate import sparse_sim as ss
enc = C._encoding()
states = E.exact_encoded_states(enc)
vecs = []
for st in states:
    vecs.append({int(c): a.to_complex() for c, a in zip(st["codes"], st["amps"])})
def worst(qc, kind, al, be, phase=None):
    perm_ok = True
    layout = enc.layout_of(qc); perm = C._perm_of(layout, qc.num_qubits)
    # use canonical frame: build run on circuit's own qubit indices; map codes through inverse perm
    inv = {v: k for k, v in perm.items()}
    def tocirc(code):
        out = 0
        for b in range(28):
            if (code >> b) & 1: out |= 1 << inv[b]
        return out
    def tocanon(key):
        out = 0
        for b in range(qc.num_qubits):
            if (key >> b) & 1: out |= 1 << perm[b]
        return out
    dA, dB = E.target_base(kind, 1)
    blocks = E.exact_target_blocks(kind, 1)
    V = {}
    for b in blocks:
        for i, j, lp in b["entries"]:
            V[(b["ks"][i], b["ks"][j])] = lp.evaluate(al/dA, be/dB)
    w = 0.0; ph = None
    for k in range(0, 433, 9):
        codes = np.array([tocirc(c) for c in vecs[k]], dtype=np.int64)
        b = ss.run_batch(qc, codes)
        out = {}
        for key, col, a in zip(b.keys.tolist(), b.cols.tolist(), b.amps):
            c0 = tocanon(key)
            out[c0] = out.get(c0, 0) + a * list(vecs[k].values())[col]
        exp = {}
        for (kp, kk), v in V.items():
            if kk == k:
                for c, a in vecs[kp].items(): exp[c] = exp.get(c, 0) + v * a
        keys = set(out) | set(exp)
        if ph is None:
            ph = sum(np.conj(exp.get(c, 0)) * out.get(c, 0) for c in keys); ph /= abs(ph)
        w = max(w, max(abs(out.get(c, 0) - ph * exp.get(c, 0)) for c in keys))
    return w, ph
for (al, be) in ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00)):
    wE, pE = worst(build_UE(al, with_outer=True), "UE", al, be)
    wB, pB = worst(decrx(build_UB(be, with_outer=True)), "UB", al, be)
    print(f"alpha={al} beta={be}: UE max|U psi - c V psi| = {wE:.2e} (c={pE:.4f});  UB: {wB:.2e} (c={pB:.4f})", flush=True)
