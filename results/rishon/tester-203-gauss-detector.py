"""Tester 203 item 2(c): does the sampled Gauss check fire?  A circuit that maps codes to codes but breaks SU(2) (swap L1<->L2 of link 0 = colour flip of the L end),
given its OWN code-space block as the target, is ok at the inner-block level but must be rejected by the Gauss sample.  Also the seed/sample accounting."""
import json, subprocess, sys
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
sys.path.insert(0, "src")
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.rishon import verify as V
from su2plaq.rishon.physical import closed_indices, sample_indices
enc = RishonEncoding()
qc = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"), QuantumRegister(2, "a"))
qc.swap(0, 1)
codes = enc.inner_codes()
M = V._code_block(qc, enc.layout_of(qc), codes, 5_000_000)
out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()}
for gs in (256, 0 + 1):
    v = V.verify(qc, enc, "UE", 0.0, None, target=M, gauss_sample=gs)
    out[f"swap_L1L2_link0_gauss_sample_{gs}"] = dict(ok=v.ok, reason=v.reason, block_error=v.block_error, gauss_residual=v.gauss_residual, gauss_states=v.gauss_states, extra=v.extra)
    print(out[f"swap_L1L2_link0_gauss_sample_{gs}"])
v = V.verify(qc, enc, "UE", 0.0, None, target=M, gauss=False)
out["gauss_false"] = dict(ok=v.ok, reason=v.reason)
print(out["gauss_false"])
# boundary: err in the gap where 2*err > tol_gauss > err. phase 7e-11 on AAAA is accepted by the inner block; residual?
b = enc.basis
ids = closed_indices(b) + sample_indices(b, 256, 20261104)
out["sample"] = dict(n=len(ids), n_closed=len(closed_indices(b)), distinct=len(set(ids)), seed=20261104, first5=ids[:5], last5=ids[-5:])
# coverage of the 256-sample: how many of the 72ish... type patterns / outer-quartet counts
nq_out = [sum(1 for t in b.labels[k][0][4:] if t == "Q") for k in ids]
out["sample"]["outer_Q_count_hist"] = np.bincount(nq_out).tolist()
print(out["sample"])
json.dump(out, open("results/rishon/tester-203-gauss-detector.json", "w"), indent=1, default=str)
