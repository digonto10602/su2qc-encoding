from common import *
from su2plaq.exact.physical import gauss_residuals_coo
VE = target(basis, "UE", alpha=alpha)
# decode_state equals the CG-basis amplitudes of the physical basis
ev = enc.physical_vectors(); worst = 0; nneg = 0; sigconst = True
for k in range(433):
    keys, amps = enc.decode_state(ev.codes[k], ev.amps[k])
    # basis stores (inner-key, outer-key)? compare through dicts: combine
    o = np.argsort(keys); ks, am = keys[o], amps[o]
    bk, ba = np.asarray(basis.keys[k]), np.asarray(basis.amps[k]); o2 = np.argsort(bk)
    if len(ks) != len(bk) or not np.array_equal(ks, bk[o2]): worst = max(worst, 1e9); continue
    worst = max(worst, np.abs(am - ba[o2]).max())
    # sigma constant on support?
    pi = enc._paulo_indices(ev.codes[k]); s = np.ones(len(pi))
    for i in range(12): s *= enc._sign_of_p[pi[:, i]]
    sigconst &= (len(set(s.tolist())) == 1); nneg += (s[0] < 0)
rec("decode_state(physical_vectors) == CG basis amplitudes exactly", "<=1e-14", f"{worst:.2e}", 1e-14, worst <= 1e-14)
rec("V_P sign product constant on support of every physical state (=> Gauss residual blind to V_P for in-span outputs)", "True", f"{sigconst}; states with s=-1: {nneg}/433", "", True, "informational")
# output gauss residual via evaluate vs independent decode of UE output: compute directly
# make a gauge-violating output that differs under V_P: Z on q_m' of link r  vs sign
# aer_mps: certification flags
qc, r = circ(); [qc.p(-0.75*alpha, r["d"][q]) for q in (2,5,8,11)]
v = evaluate(qc, enc, VE, engine="aer_mps")
rec("aer_mps UE default tol: engine/acc/certified", "engine aer_mps, acc 2e-10, certified False", f"{fmt(v)} acc={v.engine_accuracy} certified={v.certified} ok={v.ok}", "", v.engine=="aer_mps" and v.engine_accuracy==2e-10 and v.certified is False)
v = evaluate(qc, enc, VE, engine="aer_mps", tol_err=1e-8, tol_leak=1e-8)
rec("aer_mps UE tol 1e-8: certified", "True", f"{fmt(v)} certified={v.certified}", "", v.certified is True and v.ok)
v = evaluate(qc, enc, VE, engine="sparse")
rec("sparse: engine_accuracy 0, certified True", "0,True", f"acc={v.engine_accuracy} cert={v.certified} drop={v.dropped_total}", "", v.engine_accuracy==0 and v.certified)
# negative cases under aer_mps
for nm, build, V_, exp in (("Z data", lambda qc,r: qc.z(r["d"][4]), I, "error"), ("X ancilla", lambda qc,r: qc.x(r["a"][0]), I, "dirty_ancilla"), ("UE wrong sign", lambda qc,r: [qc.p(0.75*alpha, r["d"][q]) for q in (2,5,8,11)], VE, "error")):
    qc, r = circ(nanc=1); build(qc, r)
    v = evaluate(qc, enc, V_, engine="aer_mps")
    rec(f"aer_mps rejects: {nm}", exp, fmt(v), "", (not v.ok) and v.engine=="aer_mps", "reason "+v.reason)
# aer_mps with outer read, correct diag target
th = 0.7; jo = J[:, 4] > 0
qc, r = circ(True); qc.p(th, r["o"][1])
v = evaluate(qc, enc, np.diag(np.exp(1j*th*jo)), engine="aer_mps")
rec("aer_mps outer-read correct (2 blocks)", "ok, err~1e-10", fmt(v)+f" acc={v.engine_accuracy} cert={v.certified}", "", v.ok and v.outer_bits_read==1)
v = evaluate(qc, enc, I, engine="aer_mps")
rec("aer_mps outer-read wrong target", "fail", fmt(v), "", not v.ok)
# auto fallback: cap exceeded -> aer_mps ; sparse with cap small -> unsimulable?
v = evaluate(qc, enc, np.diag(np.exp(1j*th*jo)), engine="auto", cap=10)
rec("engine=auto with tiny cap: fallback to aer_mps", "engine aer_mps", fmt(v), "", v.engine=="aer_mps")
v = evaluate(qc, enc, np.diag(np.exp(1j*th*jo)), engine="sparse", cap=10)
rec("engine=sparse with tiny cap", "unsimulable verdict", fmt(v), "", v.reason=="unsimulable")
# agreement of aer_mps and sparse op_norm_error on a nonzero-error circuit
qc, r = circ(); [qc.p(-(0.75*alpha+1e-3), r["d"][q]) for q in (2,5,8,11)]
a = evaluate(qc, enc, VE, engine="sparse"); b = evaluate(qc, enc, VE, engine="aer_mps")
rec("sparse vs aer_mps op_norm_error on UE(delta=1e-3)", "diff<=1e-9", f"{a.op_norm_error:.12e} vs {b.op_norm_error:.12e} diff {abs(a.op_norm_error-b.op_norm_error):.1e}", 1e-9, abs(a.op_norm_error-b.op_norm_error)<1e-9)
json.dump(RES, open(OUT+"adv6.json","w"), indent=1)
