"""Tester 205: independent classical (bit-tracking) simulation of UE and UE_outer_row from the loaded .qpy on 20000 own random valid 48-bit codes
(each 4-bit link nibble in {3,5,6,9,10,12}; seed 205).  Circuit is CX + phase gates only -> a diagonal monomial map; compare to exp(-i alpha 3/4 #Q)
(#Q = nibbles in {5,6,9,10}) up to ONE global phase, and check that the bitstring is restored."""
import json, numpy as np
from qiskit import qpy
rng = np.random.default_rng(205); NIB=np.array([3,5,6,9,10,12]); alpha=0.37
res={}
for name,nl in (("UE",4),("UE_outer_row",12)):
    qc = qpy.load(open(f"results/rishon/{name}.qpy","rb"))[0]
    nb = 4*nl; codes = np.zeros(20000, dtype=np.int64)
    for l in range(nl): codes |= NIB[rng.integers(0,6,20000)].astype(np.int64) << (4*l)
    bits = codes.copy(); ph = np.zeros(20000); names=set()
    for inst in qc.data:
        op=inst.operation; q=[qc.find_bit(x).index for x in inst.qubits]; names.add(op.name)
        if op.name=="cx": bits ^= ((bits>>q[0])&1) << q[1]
        elif op.name in ("rz","p","u1"):
            th=float(op.params[0]); b=(bits>>q[0])&1
            ph += (th*b if op.name!="rz" else th*(b-0.5))   # rz = diag(e^{-i th/2}, e^{i th/2}) ; p = diag(1, e^{i th})
            if op.name=="rz": ph += 0  # rz: phase = th*(b-1/2)
        elif op.name=="barrier": pass
        else: raise SystemExit(f"unexpected gate {op.name}")
    nq = np.zeros(20000)
    for l in range(nl): nq += np.isin((codes>>(4*l))&15,[5,6,9,10])
    tgt = -0.75*alpha*nq
    d = ph - tgt; d = np.angle(np.exp(1j*(d - d[0])))   # remove one global phase
    res[name]=dict(gates=sorted(names), restored=bool((bits==codes).all()), max_phase_dev=float(np.abs(d).max()), global_phase=float(ph[0]-tgt[0]),
                   n_codes=20000, n_distinct_nQ=sorted(set(nq.astype(int).tolist())))
    print(name,res[name])
json.dump(res, open("results/rishon/tester-205-outer-row-classical.json","w"), indent=1)
