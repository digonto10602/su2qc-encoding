"""Tester 118 (extra): own synthesised (eps=1e-6) circuit via own pygridsynth words (X->HSSH, W dropped), Aer statevector on a seeded subset of 60 of the 433 codes, nominal angles.
Error = ||M_sub - e^{i phi} V_sub||_2 (columns of the subset, all 433 rows) plus leak/ancilla weight; bound N_rot*eps + 1e-9 (+ leak)."""
import sys, json, math, random, pathlib, numpy as np, mpmath, pygridsynth
from qiskit import QuantumCircuit, transpile
import aer_verify as AV
BASIS = ["cx","h","s","sdg","t","tdg","rz","p","x","z","cz"]
EX = {0:"",1:"T",2:"S",3:"ST",4:"SS",5:"SST",6:"SSS",7:"SSST"}
def word(th, eps=1e-6):
    k = th/(math.pi/4)
    if abs(k-round(k)) < 1e-12: return EX[round(k) % 8]
    return str(pygridsynth.gridsynth_gates(mpmath.mpf(repr(th)), mpmath.mpf(repr(eps))))
def synth(qc):
    low = transpile(qc, basis_gates=BASIS, optimization_level=0); q = QuantumCircuit(low.num_qubits); nrot = 0
    for i in low.data:
        qs = [low.find_bit(x).index for x in i.qubits]
        if i.operation.name in ("rz","p"):
            nrot += 1
            for ch in reversed(word(float(i.operation.params[0]))):
                if ch == "H": q.h(qs[0])
                elif ch == "S": q.s(qs[0])
                elif ch == "T": q.t(qs[0])
                elif ch == "X": q.h(qs[0]); q.s(qs[0]); q.s(qs[0]); q.h(qs[0])
        else: q.append(i.operation, qs)
    return q, nrot
eid = sys.argv[1]; root = pathlib.Path(".")
ent = json.load(open(root/f"compress/archive/spinnet/entries/{eid}.json")); f = root/ent["program_path"]
a, b = 0.37, 0.61; qc = AV.build(f, a, b); sq, nrot = synth(qc)
body = transpile(sq, AV.sim, optimization_level=0)
sub = sorted(random.Random(20261110).sample(range(433), 60)); V = AV.target(a, b)
# reuse AV.run on the subset by temporarily restricting codes
M = np.zeros((433, len(sub)), complex); anc = leak = 0.0
n = sq.num_qubits
for c_i, k in enumerate(sub):
    prep = QuantumCircuit(n)
    for q in range(16):
        if (int(AV.codes[k]) >> q) & 1: prep.x(q)
    full = prep.compose(body); full.save_statevector()
    psi = np.asarray(AV.sim.run(full, shots=1).result().get_statevector(full))
    for i in np.nonzero(np.abs(psi) > 1e-15)[0]:
        z = psi[i]; w = abs(z)**2
        if int(i) >> 16: anc += w; continue
        j = AV.index.get(int(i))
        if j is None: leak += w
        else: M[j, c_i] = z
Vs = V[:, sub]; ov = np.trace(Vs.conj().T @ M); ph = ov/abs(ov)
err = float(np.linalg.norm(M - ph*Vs, 2)); bound = nrot*1e-6 + 1e-9
r = {"id": eid, "n_rot": nrot, "T_gates_in_synth": sum(1 for i in sq.data if i.operation.name in ("t","tdg")), "cols": len(sub), "block_err_2norm": err, "bound_N_eps_plus_1e-9": bound, "ancilla_weight": anc, "leak_weight": leak, "leak_amp": math.sqrt(leak), "ok": err + math.sqrt(leak + anc) <= bound}
print(json.dumps(r)); json.dump(r, open(f"results/spinnet/tester/4_6_r5/synth_aer_{eid}.json", "w"))
