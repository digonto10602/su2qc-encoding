"""Tester step 1.3: why the sparse engine cannot do synthesised U_B: stored amplitudes per input vs number of synthesised rotations.
Usage: PYTHONPATH=src python tests/independent/magnetic_1_3/check_sparse_growth.py out.json"""
import sys, json, time, warnings
import numpy as np
warnings.filterwarnings("ignore")
from qiskit import QuantumCircuit
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.circuits.twelve import build_UB
from su2plaq.evaluate import sparse_sim as ss
from su2plaq.metrics.logical import lower, is_clifford_t_angle
from su2plaq.metrics.cliffordt import pygridsynth_word

enc = TwelveQubit(); qc = build_UB(0.61); low = lower(qc); codes = enc.inner_codes()
rng = np.random.default_rng(20261104); pick = np.array(sorted(rng.choice(len(codes), 8, replace=False)))
res = []
for eps in (1e-4, 1e-6):
    for k in range(0, 7):
        out = QuantumCircuit(*low.qregs, global_phase=low.global_phase); seen = 0
        for inst in low.data:
            op = inst.operation; qs = [out.qubits[low.find_bit(q).index] for q in inst.qubits]
            if op.name == "rz" and not is_clifford_t_angle(float(op.params[0])):
                if seen < k:
                    for ch in reversed(pygridsynth_word(float(op.params[0]), eps)):
                        {"H": out.h, "S": out.s, "T": out.t}.get(ch, lambda q: None)(qs[0]) if ch in "HST" else (out.h(qs[0]), out.s(qs[0]), out.s(qs[0]), out.h(qs[0])) if ch == "X" else None
                else:
                    out.rz(float(op.params[0]), qs[0])
                seen += 1
            else:
                out.append(op, qs)
        t0 = time.time()
        try:
            b = ss.run_batch(out, codes[pick], cap=400_000_000)
            r = dict(eps=eps, k_synth=k, stored_total=int(len(b.keys)), per_input=len(b.keys) / len(pick), seconds=time.time() - t0, dropped=b.dropped_max)
        except ss.SimCapExceeded:
            r = dict(eps=eps, k_synth=k, stored_total=None, seconds=time.time() - t0, note="cap 4e8 exceeded")
        res.append(r); print(r, flush=True)
json.dump(dict(inputs=pick.tolist(), results=res), open(sys.argv[1], "w"), indent=1)
