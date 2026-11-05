import sys, json, time
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding")
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import UnitaryGate
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.evaluate.evaluator import evaluate, inner_target
from su2plaq.exact.operators import target

enc = TwelveQubit()
basis = enc.basis
I = np.eye(433, dtype=complex)
alpha, beta = 0.37, 0.61
RES = []

def rec(name, expected, got, tol, ok, note=""):
    RES.append(dict(check=name, expected=str(expected), got=str(got), tol=str(tol), ok=bool(ok), note=note))
    print(("PASS" if ok else "FAIL"), name, "| exp:", expected, "| got:", got, "|", note, flush=True)

def circ(outer=False, nanc=0, order="d,o,a"):
    regs = {"d": QuantumRegister(12, "d")}
    if outer: regs["o"] = QuantumRegister(16, "o")
    if nanc: regs["a"] = QuantumRegister(nanc, "a")
    names = [n for n in order.split(",") if n in regs]
    qc = QuantumCircuit(*[regs[n] for n in names])
    return qc, regs

def fmt(v):
    return f"ok={v.ok} reason={v.reason} err={v.op_norm_error:.3e} leak={v.max_leak:.2e} dirty={v.dirty_ancilla:.2e} gauss={v.gauss_residual:.2e} read={v.outer_bits_read} method={v.method} fail={v.failing_inputs[:2]}"

VE = target(basis, "UE", alpha=alpha)
# ---- 1. known verdicts
qc, r = circ()
v = evaluate(qc, enc, I); rec("identity", "ok", fmt(v), "", v.ok and v.op_norm_error < 1e-13)
qc, r = circ()
for q in (2, 5, 8, 11): qc.p(-0.75 * alpha, r["d"][q])
v = evaluate(qc, enc, VE); rec("UE p(-3a/4) vs UE", "ok, err~1e-15", fmt(v), 1e-10, v.ok and v.op_norm_error < 1e-12)
UE_err = v.op_norm_error
v = evaluate(qc, enc, VE, method="physical"); rec("UE physical method", "ok", fmt(v), 1e-10, v.ok and v.op_norm_error < 1e-12)
qc, r = circ()
for q in (2, 5, 8, 11): qc.p(+0.75 * alpha, r["d"][q])
v = evaluate(qc, enc, VE); rec("UE p(+3a/4) vs UE (wrong sign)", "fail error", fmt(v), "", (not v.ok) and v.reason == "error" and v.op_norm_error > 0.1)
v2 = evaluate(qc, enc, VE.conj().T); rec("p(+3a/4) vs UE^dagger", "ok", fmt(v2), "", v2.ok)
qc, r = circ(); qc.global_phase = 0.9
v = evaluate(qc, enc, I); rec("global phase only", "ok phase e^{0.9i}", fmt(v)+f" phase={v.phase}", 1e-12, v.ok and abs(v.phase-np.exp(0.9j))<1e-12)
qc, r = circ(); qc.z(r["d"][4])
v = evaluate(qc, enc, I); rec("Z on data qubit 4 (q_m of link r)", "fail error", fmt(v), "", (not v.ok) and v.reason == "error")
qc, r = circ(nanc=1); qc.x(r["a"][0])
v = evaluate(qc, enc, I); rec("X on ancilla dirty", "dirty_ancilla", fmt(v), "", (not v.ok) and v.reason == "dirty_ancilla" and v.dirty_ancilla > 1-1e-12)
qc, r = circ(nanc=2)
qc.cx(r["d"][2], r["a"][0]); qc.ccx(r["d"][5], r["d"][8], r["a"][1]); qc.p(0.3, r["a"][0]); qc.t(r["a"][1])
qc.ccx(r["d"][5], r["d"][8], r["a"][1]); qc.cx(r["d"][2], r["a"][0])
# leftover phases on ancilla depending on data: ancilla returns to 0 so p on |0> trivial... construct: compute, phase on data, uncompute
qc2, r = circ(nanc=2)
qc2.cx(r["d"][2], r["a"][0]); qc2.cx(r["d"][5], r["a"][0]); qc2.p(-0.75*alpha, r["a"][0])  # a0 = j_b xor j_r  : phase -3a/4*(jb xor jr)
qc2.cx(r["d"][5], r["a"][0]); qc2.cx(r["d"][2], r["a"][0])
v = evaluate(qc, enc, I); rec("dirty ancilla computed+uncomputed (phases on |0> anc)", "ok", fmt(v), "", v.ok)
# compute-use-uncompute with real effect: phase on ancilla = jb XOR jr
jb = np.array([l[0][0] for l in basis.labels]) > 0; jr = np.array([l[0][1] for l in basis.labels]) > 0
Vx = np.diag(np.exp(-0.75j*alpha*(jb ^ jr)))
v = evaluate(qc2, enc, Vx); rec("compute-use-uncompute (phase on a0=jb^jr)", "ok", fmt(v), "", v.ok and v.op_norm_error<1e-12)
v = evaluate(qc2, enc, I); rec("same vs identity", "fail error", fmt(v), "", (not v.ok) and v.reason=="error")
# unclean: forget to uncompute one cx
qc3, r = circ(nanc=1); qc3.cx(r["d"][2], r["a"][0]); qc3.cx(r["d"][5], r["a"][0]); qc3.p(-0.75*alpha, r["a"][0]); qc3.cx(r["d"][5], r["a"][0])
v = evaluate(qc3, enc, Vx); rec("forgot to uncompute (a=jb left)", "dirty_ancilla", fmt(v), "", (not v.ok) and v.reason=="dirty_ancilla")
# small ancilla rotation
for eps in (1e-5, 1e-7):
    qc, r = circ(nanc=1); qc.ry(eps, r["a"][0])
    v = evaluate(qc, enc, I); w = np.sin(eps/2)**2
    rec(f"ancilla ry({eps}) weight {w:.2e}", "fail" if w>1e-12 else "ok", fmt(v), "leak<=1e-12 (weight)", (not v.ok) == (w>1e-12))
# writes outer
def wo(build, name):
    qc, r = circ(True); build(qc, r)
    v = evaluate(qc, enc, I); rec(name, "writes_outer", f"reason={v.reason}", "", v.reason=="writes_outer" and not v.ok)
wo(lambda qc,r: qc.cx(r["d"][2], r["o"][1]), "CX inner->outer")
wo(lambda qc,r: qc.x(r["o"][3]), "X on outer")
wo(lambda qc,r: qc.h(r["o"][3]), "H on outer")
wo(lambda qc,r: qc.ry(0.4, r["o"][3]), "RY on outer")
wo(lambda qc,r: qc.rx(0.4, r["o"][3]), "RX on outer")
wo(lambda qc,r: qc.swap(r["o"][3], r["d"][0]), "SWAP outer-inner")
wo(lambda qc,r: qc.ccx(r["d"][0], r["d"][1], r["o"][3]), "CCX target outer")
wo(lambda qc,r: qc.cy(r["d"][0], r["o"][3]), "CY target outer")
wo(lambda qc,r: qc.cry(0.3, r["d"][0], r["o"][3]), "CRY target outer")
wo(lambda qc,r: qc.sx(r["o"][3]), "SX on outer")
wo(lambda qc,r: qc.unitary(np.array([[0,1],[1,0]]), [r["o"][3]]), "unitary X on outer")
wo(lambda qc,r: qc.cx(r["o"][3], r["o"][4]), "CX outer->outer")
wo(lambda qc,r: qc.cswap(r["d"][0], r["o"][3], r["d"][1]), "CSWAP(inner; outer, inner) swaps outer")
def hidden(qc, r):
    sub = QuantumCircuit(2, name="mygate"); sub.h(1); sub.cx(0, 1); sub.h(1)  # = CZ on (0,1)?  no: H cx H = CZ-like diag
    sub2 = QuantumCircuit(2, name="evil"); sub2.cx(0, 1)
    qc.append(sub2.to_instruction(), [r["d"][0], r["o"][2]])
wo(hidden, "custom gate hiding CX inner->outer")
# diagonal-allowed on outer
def rd(build, name, nread):
    qc, r = circ(True); build(qc, r)
    v = evaluate(qc, enc, I); rec(name, f"not writes_outer, read={nread}", fmt(v), "", v.reason!="writes_outer" and v.outer_bits_read==nread)
rd(lambda qc,r: qc.cz(r["o"][1], r["d"][2]), "CZ(outer,inner)", 1)
rd(lambda qc,r: qc.cx(r["o"][1], r["d"][2]), "CX(outer->inner)", 1)
rd(lambda qc,r: qc.cx(r["o"][1], r["d"][2]), "CX(outer->inner)", 1)
rd(lambda qc,r: qc.ccx(r["o"][1], r["o"][3], r["d"][2]), "CCX(outer,outer->inner)", 2)
rd(lambda qc,r: (qc.cry(0.4, r["o"][1], r["d"][2])), "CRY(outer ctrl -> inner)", 1)
rd(lambda qc,r: (qc.rzz(0.4, r["o"][1], r["d"][2])), "RZZ(outer,inner) (diag; may be conservatively rejected)", 1)
rd(lambda qc,r: (qc.rzz(0.4, r["d"][2], r["o"][1])), "RZZ(inner,outer)", 1)
rd(lambda qc,r: qc.p(0.3, r["o"][1]), "P on outer", 1)
rd(lambda qc,r: qc.cp(0.3, r["o"][1], r["o"][3]), "CP(outer,outer)", 2)
rd(lambda qc,r: qc.id(r["o"][1]), "id on outer", 0)
rd(lambda qc,r: qc.barrier(), "barrier", 0)
json.dump(RES, open("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv1.json", "w"), indent=1)
print("UE_err", UE_err)
