"""Tester 3.L3: a sign flip on the INPUT side of exactly one of the 433 states (multi-controlled Z on the 16 data|outer qubits
from 15 extra clean ancillas, placed BEFORE the step circuit).  The checker must reject and name that state when it is the
only deviation; checks the whole range 0..432 is replayed."""
import sys, json, pathlib
from qiskit import QuantumCircuit, QuantumRegister
from su2plaq.circuits.spinnet import build_step
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.spinnet import lean_export as LE
enc = SpinNet(); codes = [int(c[0]) for c in enc.physical_vectors().codes]
base = build_step(0.37, 0.61, 1, with_outer=True)
def flipped(k):
    d, o, a = base.qregs
    a2 = QuantumRegister(7 + 15, 'a')
    c = QuantumCircuit(d, o, a2, global_phase=base.global_phase)
    ctrl = list(d) + list(o); ex = list(a2)[7:]
    zeros = [ctrl[i] for i in range(16) if not (codes[k] >> i) & 1]
    for z in zeros: c.x(z)
    c.ccx(ctrl[0], ctrl[1], ex[0])
    for i in range(2, 16): c.ccx(ctrl[i], ex[i - 2], ex[i - 1])
    c.z(ex[14])
    for i in range(15, 1, -1): c.ccx(ctrl[i], ex[i - 2], ex[i - 1])
    c.ccx(ctrl[0], ctrl[1], ex[0])
    for z in zeros: c.x(z)
    c.compose(base, qubits=list(d) + list(o) + list(a2)[:7], inplace=True)
    return c
res = []
for k in (0, 1, 2, 100, 216, 300, 431, 432):
    r = LE.certify(flipped(k), enc, 'step', 0.37, 0.61, 1, out_dir=pathlib.Path(sys.argv[1]))
    ok = r['status'] == 'rejected' and r['reason'].startswith(f'state {k} differs')
    res.append(dict(k=k, status=r['status'], reason=r['reason'], names_k=ok)); print(k, r['status'], r['reason'], ok, flush=True)
json.dump(res, open(sys.argv[2], 'w'), indent=1)
