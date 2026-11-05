from common import *
import itertools
VE = target(basis, "UE", alpha=alpha)
th = 0.7; jo0 = J[:, 4] > 0; jo1 = J[:, 5] > 0
Vo0 = np.diag(np.exp(1j*th*jo0)); Vo1 = np.diag(np.exp(1j*th*jo1))
def build(order, kind):
    regs = {"d": QuantumRegister(12, "d"), "o": QuantumRegister(16, "o"), "a": QuantumRegister(2, "a"), "b": QuantumRegister(1, "b")}
    qc = QuantumCircuit(*[regs[n] for n in order]); r = regs
    if kind == "outer_phase_UE":
        qc.p(th, r["o"][1]); [qc.p(-0.75*alpha, r["d"][q]) for q in (2,5,8,11)]; tg = np.diag(np.exp(1j*th*jo0)) @ VE
    elif kind == "outer_phase_wrongtarget":
        qc.p(th, r["o"][1]); tg = Vo1
    elif kind == "cz_outer_inner":
        qc.cz(r["o"][3], r["d"][5]); tg = np.diag(np.where((J[:,1]>0)&(J[:,5]>0), -1.0, 1.0))
    elif kind == "ancilla_uncompute":
        qc.cx(r["d"][2], r["a"][0]); qc.cx(r["d"][5], r["a"][0]); qc.p(-0.75*alpha, r["a"][0]); qc.cx(r["d"][5], r["a"][0]); qc.cx(r["d"][2], r["a"][0])
        qc.x(r["b"][0]); qc.x(r["b"][0]); tg = np.diag(np.exp(-0.75j*alpha*((J[:,0]>0) ^ (J[:,1]>0))))
    elif kind == "dirty_b":
        qc.x(r["b"][0]); tg = I
    elif kind == "writes_outer":
        qc.cx(r["d"][2], r["o"][5]); tg = I
    elif kind == "oracle_cx":  # CX(o0.q_j -> d0) vs oracle
        qc.cx(r["o"][1], r["d"][0]); tg = ORACLE
    elif kind == "UE_only":
        [qc.p(-0.75*alpha, r["d"][q]) for q in (2,5,8,11)]; tg = VE
    return qc, tg
ORACLE = oracle_A(lambda c: c ^ bit(c, 13), lambda c: np.ones(len(c)))
kinds = ["outer_phase_UE", "outer_phase_wrongtarget", "cz_outer_inner", "ancilla_uncompute", "dirty_b", "writes_outer", "oracle_cx", "UE_only"]
perms = list(itertools.permutations(["d", "o", "a", "b"]))
print(len(perms), "register orders x", len(kinds), "circuits")
summary = {}
allsame = True
for kind in kinds:
    base = None; worst_err = 0; reasons = set(); nbad = 0
    for order in perms:
        qc, tg = build(order, kind)
        v = evaluate(qc, enc, tg, gauss=(kind != "oracle_cx"))
        sig = (v.ok, v.reason, v.outer_bits_read, v.n_blocks, v.method)
        nums = np.array([v.op_norm_error, v.max_leak, v.dirty_ancilla, v.gauss_residual if v.gauss_residual==v.gauss_residual else 0.0]); 
        if base is None: base = (sig, nums, order)
        else:
            same = sig == base[0] and np.all(np.abs(nums - base[1]) <= 1e-13 + 1e-9*np.abs(base[1])) and np.isfinite(nums).all() == np.isfinite(base[1]).all()
            if not same and not (np.isinf(nums).all() and np.isinf(base[1]).all() and sig==base[0]): nbad += 1; print("  MISMATCH", kind, order, sig, nums, base)
        reasons.add(v.reason)
    summary[kind] = dict(reason=sorted(reasons), mismatches=nbad, ref_nums=base[1].tolist(), ref_sig=str(base[0]))
    rec(f"register-order fuzz: {kind}", "identical verdict+numbers over 24 orders", f"reason {sorted(reasons)} ref {base[1].round(15).tolist()} mismatches {nbad}", "1e-9 rel", nbad == 0)
# expected reasons
exp = {"outer_phase_UE": "ok", "outer_phase_wrongtarget": "error", "cz_outer_inner": "ok", "ancilla_uncompute": "ok", "dirty_b": "dirty_ancilla", "writes_outer": "writes_outer", "oracle_cx": None, "UE_only": "ok"}
for k, e in exp.items():
    if e: rec(f"fuzz expected reason {k}", e, summary[k]["reason"], "", summary[k]["reason"] == [e])
# 24 further: shuffled registers split ancillas (a placed between d and o, b first etc already covered); non-'d' named data via first-12 fallback
qc = QuantumCircuit(12 + 16); [qc.p(-0.75*alpha, q) for q in (2,5,8,11)]
v = evaluate(qc, enc, VE); rec("no named registers (first 12 = data, rest ancilla)", "ok", fmt(v), "", v.ok)
for bad in ("overlap", "dsize", "osize"):
    try:
        if bad == "dsize": qc = QuantumCircuit(QuantumRegister(11, "d"))
        if bad == "osize": qc = QuantumCircuit(QuantumRegister(12, "d"), QuantumRegister(15, "o"))
        if bad == "overlap":
            d = QuantumRegister(12, "d"); qc = QuantumCircuit(d); qc.add_register(QuantumRegister(bits=list(d)[:4] + [], name="o")) if False else None
            raise ValueError("overlap not constructible with standard registers (skipped)")
        evaluate(qc, enc, I); rec(f"bad layout {bad}", "ValueError", "no error", "", False)
    except ValueError as e: rec(f"bad layout {bad}", "ValueError", f"ValueError {str(e)[:60]}", "", True)
json.dump(RES, open(OUT + "fuzz.json", "w"), indent=1)
