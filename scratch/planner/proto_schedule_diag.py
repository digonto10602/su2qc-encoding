import sys, time, math, numpy as np
from qiskit import qasm3
QASM = "/home/digimonk/Projects/su2qc-paulo-code/SU2_plaquette_12qubit_encoding/SU2_plaquette_jmax_half_CT.qasm"
qc = qasm3.load(QASM); n = qc.num_qubits
qi = {q: i for i, q in enumerate(qc.qubits)}
gates = [(inst.operation.name, tuple(qi[q] for q in inst.qubits)) for inst in qc.data]
# static: count open H per qubit in original order
openq = set(); peak = 0; hist = []
for name, qs in gates:
    if name == "h":
        q = qs[0]
        if q in openq: openq.discard(q)
        else: openq.add(q)
    peak = max(peak, len(openq)); hist.append(len(openq))
print("original order: peak simultaneously-open H qubits =", peak, "; H count per qubit:", {q: sum(1 for g in gates if g[0]=='h' and g[1][0]==q) for q in range(n)})
# dynamic single-input run with progress, original order, 60 s budget
PH = {"s": 1j, "sdg": -1j, "t": np.exp(1j*math.pi/4), "tdg": np.exp(-1j*math.pi/4)}
R2 = 1/math.sqrt(2)
keys = np.array([0], np.int64); amps = np.ones(1, complex); t0 = time.time(); pk = 0
for gi, (name, qs) in enumerate(gates):
    if name == "cx":
        mc, mt = 1<<qs[0], 1<<qs[1]; keys = np.where(keys & mc != 0, keys ^ mt, keys)
    elif name in PH:
        m = 1<<qs[0]; amps = np.where(keys & m != 0, amps*PH[name], amps)
    elif name == "h":
        m = 1<<qs[0]; b = (keys & m) != 0
        keys = np.concatenate([keys & ~m, keys | m]); amps = np.concatenate([amps*R2, np.where(b, -amps*R2, amps*R2)])
        u, inv = np.unique(keys, return_inverse=True); a = np.zeros(len(u), complex); np.add.at(a, inv, amps)
        keep = np.abs(a) > 1e-14; keys, amps = u[keep], a[keep]
    pk = max(pk, len(keys))
    if gi % 300 == 0 or time.time()-t0 > 60:
        print(f"gate {gi}: {len(keys)} components, open={hist[gi]}, {time.time()-t0:.1f}s")
        if time.time()-t0 > 60: break
print("peak components (single input, vacuum):", pk)
