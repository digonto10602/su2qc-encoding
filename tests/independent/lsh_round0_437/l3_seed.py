"""Tester 437: independent Aer check of the circuit-valued round-0 seed qiskit_l3 (no program file), rebuilt from LL.seed_candidates in a scratch root."""
import json, sys, pathlib
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/tests/independent/lsh_m8_436")
import indep_check as IC
from su2plaq.lsh import loop as LL
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit import transpile
import numpy as np
root = pathlib.Path(sys.argv[1]); root.mkdir(parents=True, exist_ok=True)
res = {}
for lab, path, fn in LL.seed_candidates(LL.spec(), root):
    if lab != "qiskit_l3": continue
    for ab in [(0.37, 0.61), (0.91, 0.23), (1.7, 1.0)]:
        sp = LL.spec().with_angles(*ab)
        qc = fn(sp)
        t = IC.outer_touched(qc); assert not t
        circ, nanc = IC.drop_outer(qc); n = circ.num_qubits
        sim = AerSimulator(method="statevector"); V = np.zeros((47, 47), complex); leak = 0.0
        for j, x in enumerate(IC.INNER):
            c2 = QuantumCircuit(n)
            for b in range(12):
                if IC.bit(x, b): c2.x(b)
            c2.compose(circ, inplace=True); c2.save_statevector()
            sv = np.asarray(sim.run(transpile(c2, sim, optimization_level=0)).result().get_statevector()).reshape(2**nanc, 4096)
            leak = max(leak, float(np.sum(np.abs(sv[1:])**2))); V[:, j] = [sv[0][y] for y in IC.INNER]
        T = IC.target(*ab); ph = np.angle(np.sum(T.conj()*V))
        res[str(ab)] = {"op_norm_err": float(np.linalg.norm(V - np.exp(1j*ph)*T, 2)), "anc_leak": leak, "nq_sim": n}
    res["counts"] = IC.count_circuit(fn(LL.spec()))
print(json.dumps(res, indent=1)); json.dump(res, open("/home/digimonk/Projects/su2qc-encoding/results/tester/437-l3-seed.json", "w"), indent=1)
