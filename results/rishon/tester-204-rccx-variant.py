"""Tester 204: reproduce the builder's claim that an rccx ladder is rejected by the prune cap (monkeypatch, nothing written to src)."""
import sys, json, time; sys.path.insert(0,'src')
import numpy as np
import su2plaq.circuits.rishon as C
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.rishon import verify as Vf
from su2plaq.metrics.logical import logical_metrics
orig = C._pair_ops
def patched(f, anc):
    ops = orig(f, anc)
    return [("rccx", q, p) if (n == "ccx" and q[2] in anc) else (n, q, p) for n, q, p in ops]
C._pair_ops = patched
qc = C.build_UB(0.61)
m = logical_metrics(qc)
enc = RishonEncoding()
v = Vf.verify(qc, enc, 'UB', None, 0.61, gauss=False)
r = {'ops': dict(qc.count_ops()), 'cx': m['cx'], 't_fixed': m['t_fixed'], 'ok': v.ok, 'reason': v.reason, 'op_norm_error': v.op_norm_error, 'block_error': v.block_error,
     'dropped_total': v.dropped_total, 'leak': v.leak_amplitude, 'dirty': v.dirty_ancilla, 'cap': 1e-12}
# same circuit judged with a looser tol so the verdict is not decided by the cap: true op-norm error with the cap removed
v2 = Vf.verify(qc, enc, 'UB', None, 0.61, gauss=False, tol_err=1e-8)
r['loose_tol_1e-8'] = {'ok': v2.ok, 'reason': v2.reason, 'op_norm_error': v2.op_norm_error, 'dropped_total': v2.dropped_total}
print(r); json.dump(r, open('results/rishon/tester-204-rccx-variant.json','w'), indent=1, default=str)
