from common import *
VE = target(basis, "UE", alpha=alpha)
for nr in (4, 8, 16):
    qc, r = circ(True); [qc.p(0.1*(i+1), r["o"][i]) for i in range(nr)]
    [qc.p(-0.75*alpha, r["d"][q]) for q in (2,5,8,11)]
    t = time.time(); v = evaluate(qc, enc, VE); 
    print(f"read {nr} outer qubits: blocks={v.n_blocks} wall={time.time()-t:.1f}s {v.reason} err={v.op_norm_error:.3f}", flush=True)
# oracle for the 16-read case: diag phases from outer bits only, times UE
th = np.array([0.1*(i+1) for i in range(16)])
ph = lambda c: np.exp(1j*sum(th[i]*bit(c, 12+i) for i in range(16)))
Ao = oracle_A(lambda c: c, ph)
Vx = Ao @ VE   # UE diagonal commutes with outer-diag phases? both diagonal in code basis => product of A's valid? check numerically below
qc, r = circ(True); [qc.p(th[i], r["o"][i]) for i in range(16)]
v = evaluate(qc, enc, Ao, gauss=False); rec("16 outer-read phases vs oracle A", "err<=1e-12", fmt(v), 1e-12, v.op_norm_error < 1e-12)
