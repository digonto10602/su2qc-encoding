from common import *
from qiskit.circuit.library import UnitaryGate
VE = target(basis, "UE", alpha=alpha)
# --- fixed permutation of invalid codes only
qc, r = circ(); qc.x(r["d"][2]); qc.ccx(r["d"][0], r["d"][2], r["d"][1]); qc.x(r["d"][2])
v = evaluate(qc, enc, I); rec("permutation of invalid codes only (001<->011)", "ok", fmt(v), "", v.ok and v.op_norm_error<1e-12)
# --- layout adversarials: o register position
th = 0.7; jo = J[:, 0+4] > 0; Vo = np.diag(np.exp(1j*th*jo))
for order in ("d,o", "d,a,o", "d,o,a"):
    qc, r = circ(True, 2, order=order); qc.p(th, r["o"][1])
    try:
        v = evaluate(qc, enc, Vo); rec(f"o-register order {order}: p(th) on o[1] vs diag(j_o0)", "ok", fmt(v)+f" fail={v.failing_inputs[:2]}", "", v.ok)
    except Exception as e:
        rec(f"o-register order {order}", "ok", f"EXC {type(e).__name__}: {e}", "", False)
for order in ("o,d", "a,d,o"):
    qc, r = circ(True, 2, order=order); qc.p(th, r["o"][1])
    try:
        v = evaluate(qc, enc, Vo); rec(f"layout {order} (o/a before data)", "reject or evaluate with o=register", fmt(v), "", False, "informational")
    except Exception as e:
        rec(f"layout {order}", "reject", f"EXC {type(e).__name__}: {str(e)[:100]}", "", True, "informational")
# register named differently / 28 plain qubits
qc = QuantumCircuit(28); qc.p(th, 13)
v = evaluate(qc, enc, Vo); rec("28 unnamed qubits, p on qubit 13 (treated as ancilla)", "dirty-free; phase on |0> trivial -> identity vs diag => fail error", fmt(v), "", not v.ok)
qc = QuantumCircuit(11)
try: evaluate(qc, enc, I); rec("11 qubits", "ValueError", "no error", "", False)
except ValueError as e: rec("11 qubits", "ValueError", "ValueError", "", True)
# --- UB unitary
idx = np.arange(625)
codes_by_idx = np.zeros(625, dtype=np.int64)
for l in range(4): codes_by_idx |= enc._code3[(idx // 5**l) % 5] << (3*l)
def embed(U625):
    G = np.eye(4096, dtype=complex); G[np.ix_(codes_by_idx, codes_by_idx)] = U625; return G
UB = inner_target(enc, "UB", None, beta)
G = embed(UB)
print("unitarity of embed", np.abs(G.conj().T@G - np.eye(4096)).max())
VB = target(basis, "UB", beta=beta)
qc, r = circ(); qc.append(UnitaryGate(G), list(range(12)))
res = {}
for m in ("inner_span", "physical"):
    t=time.time(); v = evaluate(qc, enc, VB, method=m); res[m]=v
    rec(f"12-qubit unitary UB(beta=.61) embed vs target(UB) [{m}]", "ok, err~1e-14", fmt(v), 1e-10, v.ok and v.op_norm_error<1e-11)
# sign-flipped / wrong-beta targets
for lab, Vt in (("UB(beta=-0.61)", target(basis,"UB",beta=-beta)), ("UB(beta=0.5)", target(basis,"UB",beta=0.5)), ("UB^T", VB.T), ("conj(UB)", VB.conj())):
    ves = [evaluate(qc, enc, Vt, method=m) for m in ("inner_span", "physical")]
    rec(f"UB circuit vs wrong target {lab}", "fail both methods", " | ".join(f"{x.reason} {x.op_norm_error:.3f}" for x in ves), "", all(not x.ok for x in ves))
# step: UB UE
qcs, r = circ()
for q in (2,5,8,11): qcs.p(-0.75*alpha, r["d"][q])
qcs.append(UnitaryGate(G), list(range(12)))
Vs = target(basis, "step", alpha=alpha, beta=beta, order=1)
for m in ("inner_span","physical"):
    v = evaluate(qcs, enc, Vs, method=m); rec(f"UB.UE circuit vs target(step,order1) [{m}]", "ok", fmt(v), 1e-10, v.ok and v.op_norm_error<1e-11)
v = evaluate(qcs, enc, target(basis,"step",alpha=alpha,beta=beta,order=2)); rec("UB.UE circuit vs step order 2 (Strang)", "fail", fmt(v), "", not v.ok)
# commuting-order test: UE.UB circuit must NOT match UB.UE
qcr, r = circ(); qcr.append(UnitaryGate(G), list(range(12)))
for q in (2,5,8,11): qcr.p(-0.75*alpha, r["d"][q])
v = evaluate(qcr, enc, Vs); rec("UE.UB circuit vs UB.UE target", "fail (operators do not commute)", fmt(v), "", not v.ok)
# inner_target('step') vs physical(step) vs circuits
# --- inner_span vs physical agreement over >=5 circuits
cases = []
qc, r = circ(); cases.append(("identity", qc, I))
qc, r = circ(); [qc.p(-0.75*alpha, r["d"][q]) for q in (2,5,8,11)]; cases.append(("UE", qc, VE))
cases.append(("UB unitary", qcs.copy_empty_like() if False else None, None))
qc, r = circ(); qc.append(UnitaryGate(G), list(range(12))); cases[-1] = ("UB unitary", qc, VB)
cases.append(("UB.UE", qcs, Vs))
cases.append(("UB vs wrong beta", qc, target(basis,"UB",beta=0.5)))
qc2, r = circ(); [qc2.p(+0.75*alpha, r["d"][q]) for q in (2,5,8,11)]; cases.append(("UE wrong sign", qc2, VE))
qc3, r = circ(); qc3.z(r["d"][4]); cases.append(("Z data", qc3, I))
qc4, r = circ(); qc4.p(0.3, r["d"][2]); qc4.cp(0.5, r["d"][2], r["d"][5]); qc4.cp(0.9, r["d"][8], r["d"][5]); 
Vd = np.diag(np.exp(1j*(0.3*(J[:,0]>0) + 0.5*((J[:,0]>0)&(J[:,1]>0)) + 0.9*((J[:,2]>0)&(J[:,1]>0))))); cases.append(("diag p/cp network", qc4, Vd))
cases.append(("diag network vs I", qc4, I))
agree = []
for nm, qc_, V_ in cases:
    a = evaluate(qc_, enc, V_, method="inner_span"); b = evaluate(qc_, enc, V_, method="physical")
    same = (a.ok == b.ok) and (a.reason == b.reason or (not a.ok and not b.ok))
    both_small = a.op_norm_error < 1e-11 and b.op_norm_error < 1e-11
    agree.append(dict(name=nm, span=a.op_norm_error, phys=b.op_norm_error, ok_span=a.ok, ok_phys=b.ok, reason=(a.reason,b.reason)))
    rec(f"inner_span vs physical: {nm}", "same verdict; equal err if exact", f"span {a.op_norm_error:.3e} ({a.reason}) / phys {b.op_norm_error:.3e} ({b.reason})", "", same and ((a.ok and both_small) or (not a.ok)))
json.dump(RES, open(OUT+"adv3.json","w"), indent=1)
json.dump(agree, open(OUT+"adv3_agree.json","w"), indent=1)
