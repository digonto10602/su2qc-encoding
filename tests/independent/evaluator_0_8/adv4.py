from common import *
from qiskit.circuit import Parameter
from qiskit.circuit.library import UnitaryGate
from su2plaq.exact.physical import gauss_residuals_coo, to_convention
VE = target(basis, "UE", alpha=alpha)
VB = target(basis, "UB", beta=beta)
rec("UB is complex-symmetric so UB^T == UB (earlier 'UB^T accepted' is not a bug)", "||UB-UB^T||=0", f"{np.abs(VB-VB.T).max():.2e}", "", np.abs(VB-VB.T).max()<1e-12)
# false accept from layout bug
th = 0.7
jo1 = J[:, 5] > 0     # outer link 1 j
qc, r = circ(True, 2, order="d,a,o"); qc.p(th, r["o"][1])   # user intends outer register qubit 1 = outer link0.q_j
v = evaluate(qc, enc, np.diag(np.exp(1j*th*jo1)))
rec("FALSE-ACCEPT probe: layout d,a(2),o; p on o[1] (=link0.q_j) vs diag(j_o1)", "fail (wrong link)", fmt(v), "", not v.ok, "F1 evidence" if v.ok else "")
# --- gauss signs
ev = enc.physical_vectors()
kl, al, kl2 = [], [], []
for c, a in zip(ev.codes, ev.amps):
    k, aa = enc.decode_state(c, a); kl.append(k); al.append(aa)
    pi = enc._paulo_indices(c); keys = np.zeros(len(c), dtype=np.int64)
    for i in range(12): keys += enc._cg_of_p[pi[:, i]] * 5**i
    kl2.append(keys)
g_signs = gauss_residuals_coo(basis, kl, al).max()
g_nosign = gauss_residuals_coo(basis, kl2, [np.asarray(a) for a in ev.amps]).max()
rec("Gauss residual of exact embedded states, CG decode WITH V_P signs", "<=1e-10", f"{g_signs:.2e}", 1e-10, g_signs<=1e-10)
rec("  same WITHOUT the V_P signs (sensitivity of the check)", ">0.1", f"{g_nosign:.2e}", "", g_nosign>0.1)
# D UB D circuit: conjugation by sign diag
idx = np.arange(625); sgn = np.ones(625)
for l in range(4): sgn *= enc._sign_of_p[(idx//5**l)%5]
UB = inner_target(enc, "UB", None, beta)
codes_by_idx = np.zeros(625, dtype=np.int64)
for l in range(4): codes_by_idx |= enc._code3[(idx//5**l)%5] << (3*l)
def embed(U):
    G = np.eye(4096, dtype=complex); G[np.ix_(codes_by_idx, codes_by_idx)] = U; return G
qc, r = circ(); qc.append(UnitaryGate(embed(np.diag(sgn)@UB@np.diag(sgn))), list(range(12)))
v = evaluate(qc, enc, VB); rec("D.UB.D (V_P sign-conjugated UB) vs target UB", "fail; Gauss violated", fmt(v), "", (not v.ok) and v.gauss_residual>0.1)
# sign-error in the 625 inner target relative to physical target: UB with W -> W with one sign flip of a link basis state ordering
# --- inconsistent target for inner_span
jo = J[:, 4] > 0; Vo = np.diag(np.exp(0.7j*jo))
qc, r = circ()
va = evaluate(qc, enc, Vo, method="inner_span"); vb = evaluate(qc, enc, Vo, method="physical")
rec("identity circuit vs outer-dependent diag target (inner-unrealisable)", "fail in both", f"span {va.reason} {va.op_norm_error:.3e} | phys {vb.reason} {vb.op_norm_error:.3e}", "", (not va.ok) and (not vb.ok), "inner_span least-squares V_in hides the unrealisable part" if va.ok else "")
# --- span leak with / without gauss
for eps in (1e-5, 1e-3):
    qc, r = circ(True); [qc.p(-0.75*alpha, r["d"][q]) for q in (2,5,8,11)]; qc.p(0.0, r["o"][1]); qc.crx(eps, r["d"][2], r["d"][1])
    vg = evaluate(qc, enc, VE, gauss=True); vn = evaluate(qc, enc, VE, gauss=False)
    qc2, r = circ(); [qc2.p(-0.75*alpha, r["d"][q]) for q in (2,5,8,11)]; qc2.crx(eps, r["d"][2], r["d"][1])
    vs = evaluate(qc2, enc, VE, gauss=False)
    rec(f"span-leak probe crx({eps}) [physical,gauss=True | physical,gauss=False | inner_span,gauss=False]", "all three should reject if error>1e-10",
        f"{vg.reason}({vg.op_norm_error:.2e},g={vg.gauss_residual:.1e}) | {vn.reason}({vn.op_norm_error:.2e}, span_leak={vn.extra['max_span_leak']:.1e}) | {vs.reason}({vs.op_norm_error:.2e})",
        "", (not vg.ok) and (not vs.ok), "gauss=False physical => " + ("ACCEPTED" if vn.ok else "rejected"))
# --- perturbation sensitivity vs analytic
n_phys = (J[:, :4] > 0).sum(axis=1).astype(float)
inner = enc.inner_codes(); n_in = sum(bit(inner, 3*l+2) for l in range(4)).astype(float)
for dl in (1e-3, 1e-6, 1e-9, 3e-10, 1e-10, 3e-11):
    qc, r = circ(); [qc.p(-(0.75*alpha+dl), r["d"][q]) for q in (2,5,8,11)]
    A = np.exp(-1j*(0.75*alpha+dl)*n_phys); Vd = np.exp(-1j*0.75*alpha*n_phys)
    phi = np.angle(np.sum(np.conj(Vd)*A)); exp_phys = np.abs(A - np.exp(1j*phi)*Vd).max()
    exp_span = np.abs(np.exp(-1j*dl*n_in) * 1.0 - np.exp(1j*phi)).max()   # relative to V_in
    vs = evaluate(qc, enc, VE, method="inner_span"); vp = evaluate(qc, enc, VE, method="physical")
    exp_ok = exp_span <= 1e-10
    rec(f"UE angle perturbation delta={dl:g}", f"span err {exp_span:.3e} / phys {exp_phys:.3e}", f"span {vs.op_norm_error:.3e} ({vs.reason}) / phys {vp.op_norm_error:.3e} ({vp.reason})", "1e-10",
        abs(vs.op_norm_error-exp_span) < 3e-13 + 1e-6*exp_span and abs(vp.op_norm_error-exp_phys) < 3e-14+1e-6*exp_phys and vs.ok == exp_ok)
# --- unusual gates
qc, r = circ(nanc=1); qc.measure_all() if False else None
qc = QuantumCircuit(12, 1); qc.measure(0, 0)
try: v = evaluate(qc, enc, I); rec("measure", "reject (disallowed_gate)", fmt(v), "", (not v.ok) and v.reason=="disallowed_gate")
except Exception as e: rec("measure", "reject", f"EXC {type(e).__name__}: {str(e)[:80]}", "", False, "raised instead of verdict")
qc = QuantumCircuit(12); qc.reset(0)
try: v = evaluate(qc, enc, I); rec("reset", "reject", fmt(v), "", (not v.ok) and v.reason=="disallowed_gate")
except Exception as e: rec("reset", "reject", f"EXC {type(e).__name__}: {str(e)[:80]}", "", False, "raised instead of verdict")
qc = QuantumCircuit(12); qc.rz(Parameter("x"), 0)
try: v = evaluate(qc, enc, I); rec("unbound parameter", "reject", fmt(v), "", not v.ok)
except Exception as e: rec("unbound parameter", "reject/raise", f"EXC {type(e).__name__}: {str(e)[:80]}", "", True, "raised")
qc = QuantumCircuit(12+4)
qc.mcx([0,1,2], 3)
v = evaluate(qc, enc, I); rec("mcx 3 controls", "disallowed_gate", fmt(v), "", v.reason=="disallowed_gate")
sub = QuantumCircuit(5, name="deep"); sub.mcx([0,1,2,3], 4)
qc = QuantumCircuit(17); qc.append(sub.to_gate(), [0,1,2,3,16])
v = evaluate(qc, enc, I); rec("mcx hidden in custom gate", "disallowed_gate", fmt(v), "", v.reason=="disallowed_gate")
sub2 = QuantumCircuit(5, name="deeper"); sub2.append(sub.to_gate(), range(5))
qc = QuantumCircuit(17); qc.append(sub2.to_gate(), [0,1,2,3,16])
v = evaluate(qc, enc, I); rec("mcx hidden 2 levels deep", "disallowed_gate", fmt(v), "", v.reason=="disallowed_gate")
from qiskit.circuit.library import C3XGate, C4XGate, MCXVChain, MCXGrayCode, RC3XGate
qc = QuantumCircuit(17); qc.append(C3XGate(), [0,1,2,16])
v = evaluate(qc, enc, I); rec("C3XGate", "disallowed_gate", fmt(v), "", v.reason=="disallowed_gate")
qc = QuantumCircuit(17); qc.append(RC3XGate(), [0,1,2,16])
try: v = evaluate(qc, enc, I); rec("RC3XGate (relative-phase)", "(informational)", fmt(v), "", True)
except Exception as e: rec("RC3XGate", "info", f"EXC {e}", "", True)
qc = QuantumCircuit(12+3); qc.append(MCXGrayCode(4), [0,1,2,3,14])
try: v = evaluate(qc, enc, I); rec("MCXGrayCode(4)", "disallowed or exact", fmt(v), "", True, "informational")
except Exception as e: rec("MCXGrayCode", "info", f"EXC {e}", "", True)
# mcx v-chain with ancillas (3 controls), identity net: compute and uncompute, ancilla used inside
qc = QuantumCircuit(12+3); qc.append(MCXVChain(4, dirty_ancillas=False), [0,1,2,3,14,12,13]) if False else None
json.dump(RES, open(OUT+"adv4.json","w"), indent=1)
