from common import *
print("n code entries", len(CODES))
VE = target(basis, "UE", alpha=alpha)
# fixed dirty-ancilla identity circuit
qc, r = circ(nanc=2)
qc.cx(r["d"][2], r["a"][0]); qc.ccx(r["d"][5], r["d"][8], r["a"][1]); qc.ccx(r["d"][5], r["d"][8], r["a"][1]); qc.cx(r["d"][2], r["a"][0])
v = evaluate(qc, enc, I); rec("dirty ancilla compute/uncompute (identity)", "ok", fmt(v), "", v.ok)

# --- A. outer-dependent diagonal targets
for k in (0, 5):
    th = 0.7
    jo = J[:, 4 + k] > 0
    Vo = np.diag(np.exp(1j * th * jo))
    qc, r = circ(True); qc.p(th, r["o"][2*k + 1])
    v = evaluate(qc, enc, Vo); rec(f"p(th) on outer{k}.q_j vs diag(e^(i th [j_o{k}=1/2]))", "ok", fmt(v), 1e-10, v.ok and v.outer_bits_read==1 and v.op_norm_error<1e-12)
    v = evaluate(qc, enc, I)
    # analytic: A=diag(e^{i th s_k}), phi = arg sum, err = max |e^{i th s}-e^{i phi}|
    s = jo.astype(float); phi = np.angle(np.sum(np.exp(1j*th*s))); exp_err = max(abs(1-np.exp(1j*phi)), abs(np.exp(1j*th)-np.exp(1j*phi)))
    rec(f"p(th) on outer{k} vs I: one global phase, analytic err", f"{exp_err:.12f} (phi={phi:.6f}), n1={int(s.sum())}", f"{v.op_norm_error:.12f} phase={np.angle(v.phase):.6f} reason={v.reason}", 1e-10, abs(v.op_norm_error-exp_err)<1e-10 and abs(np.angle(v.phase)-phi)<1e-10 and not v.ok)
# phase with outer-dependent but per block vs same global phase on all, with a global_phase compensation
th = 0.7; jo = J[:, 4] > 0
qc, r = circ(True); qc.p(th, r["o"][1]); qc.global_phase = -th/2
Vo = np.diag(np.exp(1j*th*(jo-0.5)))
v = evaluate(qc, enc, Vo); rec("outer p(th)+gphase(-th/2) vs diag(e^{i th(s-1/2)})", "ok", fmt(v), "", v.ok)
# --- B. CZ(outer j, inner j)
jb = J[:, 0] > 0; jo0 = J[:, 4] > 0
qc, r = circ(True); qc.cz(r["o"][1], r["d"][2])
V = np.diag(np.where(jb & jo0, -1.0, 1.0))
v = evaluate(qc, enc, V); rec("CZ(outer0.q_j, d2=q_j(b)) vs diag(-1 if j_b=j_o0=1/2)", "ok", fmt(v), "", v.ok and v.op_norm_error<1e-12 and v.outer_bits_read==1)
v = evaluate(qc, enc, I); rec("same vs I", "fail error", fmt(v), "", (not v.ok) and v.reason=="error" and v.op_norm_error>0.1)
# CZ(outer0.q_m, d2): outer q_m is m label, not gauge invariant -> physical target not diagonal in j; should fail vs I
# --- C. don't care on invalid codes
qc, r = circ(); qc.x(r["d"][2]); qc.cz(r["d"][0], r["d"][2]); qc.x(r["d"][2])
v = evaluate(qc, enc, I); rec("phase on invalid code (q_j=0,q_m'=1) only", "ok (don't-care)", fmt(v), "", v.ok and v.op_norm_error<1e-12)
v = evaluate(qc, enc, I, method="physical"); rec("  same, physical method", "ok", fmt(v), "", v.ok)
qc, r = circ(); qc.x(r["d"][2]); qc.cx(r["d"][0], r["d"][1]); qc.x(r["d"][2])
v = evaluate(qc, enc, I); rec("permutation of invalid codes only (001<->011)", "ok", fmt(v), "", v.ok)
qc, r = circ(nanc=1); qc.x(r["d"][2]); qc.ccx(r["d"][0], r["d"][2], r["a"][0]); qc.x(r["d"][2]); qc.h(r["a"][0]); qc.p(0.4, r["a"][0]); qc.h(r["a"][0])
qc.x(r["d"][2]); qc.ccx(r["d"][0], r["d"][2], r["a"][0]); qc.x(r["d"][2])
v = evaluate(qc, enc, I); print("   (don't-care via ancilla h p h: ", fmt(v), ")")
qc, r = circ(); qc.x(r["d"][0])
v = evaluate(qc, enc, I); rec("X on q_m' of link b: valid->invalid for j=0 states", "leak", fmt(v), "", (not v.ok) and v.reason=="leak")
qc, r = circ(); qc.x(r["d"][0]); qc.x(r["d"][1]) # 000 -> 011 invalid; 111->100 valid
v = evaluate(qc, enc, I); rec("X on q_m,q_m' of link b", "leak", fmt(v), "", (not v.ok) and v.reason=="leak")
# --- D. single-state failure
k0 = 217
V2 = VE.copy(); V2[k0, :] *= -1; 
qc, r = circ()
for q in (2,5,8,11): qc.p(-0.75*alpha, r["d"][q])
v = evaluate(qc, enc, V2, method="physical"); 
rec("exact UE vs target with one row sign-flipped (state 217)", "fail, failing_inputs=[217]", f"{fmt(v)} fail={v.failing_inputs}", "", (not v.ok) and v.reason=="error" and len(v.failing_inputs)>=1 and v.failing_inputs[0][0]==k0)
# circuit-based: phase flip on data code all-zero (mcz through ancilla chain)
qc, r = circ(nanc=11)
d = list(r["d"]); a = list(r["a"])
for q in d: qc.x(q)
qc.ccx(d[0], d[1], a[0])
for i in range(2, 12-1): qc.ccx(d[i], a[i-2], a[i-1])
qc.cz(a[9], d[11])
for i in reversed(range(2, 12-1)): qc.ccx(d[i], a[i-2], a[i-1])
qc.ccx(d[0], d[1], a[0])
for q in d: qc.x(q)
A_or = oracle_A(lambda c: c, lambda c: np.where((c & 0xFFF) == 0, -1.0, 1.0))
v = evaluate(qc, enc, A_or, method="physical", gauss=False)
rec("mcz on data==0 vs oracle A (Psi^dag D Psi) [independent]", "err<=1e-12", fmt(v), 1e-12, v.op_norm_error < 1e-12 and v.dirty_ancilla<1e-14)
v = evaluate(qc, enc, I); 
dirty_states = sorted(set(SS[(CS & 0xFFF) == 0]))
rec("  mcz on data==0 vs identity", f"fail; {len(dirty_states)} states touched", f"{fmt(v)} fail={[f[0] for f in v.failing_inputs]}", "", (not v.ok) and all(f[0] in dirty_states for f in v.failing_inputs))
# --- oracle checks with outer reads
def check_oracle(name, build, fcode, fphase):
    qc, r = circ(True, 0); build(qc, r)
    Ao = oracle_A(fcode, fphase)
    v = evaluate(qc, enc, Ao, gauss=False)
    ok = v.op_norm_error < 1e-12 and v.outer_bits_read>=1
    rec("oracle A: "+name, "err<=1e-12", fmt(v), 1e-12, ok)
check_oracle("CX(o0.q_j -> d0)", lambda qc,r: qc.cx(r["o"][1], r["d"][0]), lambda c: c ^ (bit(c,13)), lambda c: np.ones(len(c)))
check_oracle("CCX(o0.q_j,o3.q_j -> d5)", lambda qc,r: qc.ccx(r["o"][1], r["o"][7], r["d"][5]), lambda c: c ^ ((bit(c,13)&bit(c,19))<<5), lambda c: np.ones(len(c)))
check_oracle("CZ(o2.q_m,d4) + T(o2.q_m) + CP(0.6;o4.q_j,d7)", lambda qc,r: (qc.cz(r["o"][4], r["d"][4]), qc.t(r["o"][4]), qc.cp(0.6, r["o"][9], r["d"][7])),
             lambda c: c, lambda c: (-1.0)**(bit(c,16)&bit(c,4)) * np.exp(1j*np.pi/4*bit(c,16)) * np.exp(0.6j*bit(c,21)*bit(c,7)))
def b5(qc, r):
    qc.cx(r["o"][1], r["d"][2]); qc.cp(0.9, r["o"][1], r["o"][3]); qc.cx(r["d"][2], r["d"][5]); qc.ccx(r["o"][3], r["d"][5], r["d"][8]); qc.rz(0.8, r["o"][5]); qc.global_phase = 0.2
def f5(c):
    c = c ^ (bit(c,13)<<2); c = c ^ (bit(c,2)<<5); c = c ^ ((bit(c,15)&bit(c,5))<<8); return c
def p5(c):
    c0 = c; ph = np.exp(0.9j*bit(c0,13)*bit(c0,15))
    c1 = c ^ (bit(c,13)<<2); c2 = c1 ^ (bit(c1,2)<<5)
    return ph * np.exp(0.8j*(bit(c2,17)-0.5)) * np.exp(0.2j)
check_oracle("mixed 5-gate permutation+phase circuit", b5, f5, p5)
json.dump(RES, open(OUT+"adv2.json","w"), indent=1)
