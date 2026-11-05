"""N5: global phase bookkeeping of paulo_circuit(with_outer=True) and build_step.
Usage: PYTHONPATH=src python tests/independent/audit_fixes/check_n5_phases.py results/m1_audit_fixes_n5.json"""
import sys, json, math, subprocess, warnings
import numpy as np
warnings.filterwarnings("ignore")
from qiskit import QuantumCircuit, QuantumRegister, qpy
from qiskit.quantum_info import Operator
from su2plaq.circuits import twelve as C

out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip() + "+uncommitted", "checks": {}}
def rec(name, expected, got, tol):
    ok = abs(((got - expected) + math.pi) % (2 * math.pi) - math.pi) <= tol
    out["checks"][name] = dict(expected=expected, got=got, tol=tol, ok=bool(ok)); print(("PASS" if ok else "FAIL"), name, expected, got, flush=True)

src = C.paulo_circuit()
with open("refs/paulo/SU2_plaquette_jmax_half_CT.qpy", "rb") as fh:
    raw = qpy.load(fh)[0]
rec("paulo_circuit() phase == raw QPY phase", float(raw.global_phase), float(src.global_phase), 1e-15)
rec("paulo_circuit(with_outer=True) phase == raw QPY phase (not doubled)", float(raw.global_phase), float(C.paulo_circuit(True).global_phase), 1e-15)
print("  raw phase", raw.global_phase, " instructions equal count:", len(raw.data), len(C.paulo_circuit(True).data))
# real build_* phases
ub = C.build_UB(0.61); ue1 = C.build_UE(0.37); ue2 = C.build_UE(0.185)
for wo in (False, True):
    ubw = C.build_UB(0.61, with_outer=wo)
    rec(f"build_UB(0.61, outer={wo}) phase", 0.0, float(ubw.global_phase), 1e-15)
    for order in (1, 2):
        st = C.build_step(0.37, 0.61, order=order, with_outer=wo)
        parts = float(ubw.global_phase) + (float(ue1.global_phase) if order == 1 else 2 * float(ue2.global_phase))
        rec(f"build_step order {order} outer={wo} phase == sum of parts", parts, float(st.global_phase), 1e-15)
# nonzero phases by wrapping the builders (the production build_step code path), 4 combos
orig_ue, orig_ub = C.build_UE, C.build_UB
for (pu, pb) in ((0.1, 0.3), (-0.7, 2.0), (3.0, 0.0)):
    def ue(alpha, *a, **k):
        q = orig_ue(alpha, *a, **k); q.global_phase = pu; return q
    def ubb(beta, *a, **k):
        q = orig_ub(beta, *a, **k); q.global_phase = pb; return q
    C.build_UE, C.build_UB = ue, ubb
    try:
        for order, exp in ((1, pu + pb), (2, 2 * pu + pb)):
            rec(f"wrapped phases ue={pu} ub={pb} order={order}", exp, float(C.build_step(0.37, 0.61, order=order).global_phase), 1e-15)
    finally:
        C.build_UE, C.build_UB = orig_ue, orig_ub
# Operator-level proxy using the very same code patterns as the production lines: 3 data + 2 outer + 2 ancilla qubits
def proxy_embed(src, qmap, regs):
    o = QuantumCircuit(*regs, name=src.name)      # pattern of paulo_circuit(with_outer=True) after the fix
    o.compose(src, qubits=qmap, inplace=True); return o
s = QuantumCircuit(QuantumRegister(3, "d"), QuantumRegister(2, "a"), global_phase=0.77); s.h(0); s.cx(0, 3); s.ry(0.3, 4); s.ccx(0, 3, 1)
regs = [QuantumRegister(3, "d"), QuantumRegister(2, "o"), QuantumRegister(2, "a")]
e = proxy_embed(s, [0, 1, 2, 5, 6], regs)
ref = QuantumCircuit(7, global_phase=0.77)
ref.h(0); ref.cx(0, 5); ref.ry(0.3, 6); ref.ccx(0, 5, 1)
err = float(np.abs(Operator(e).data - Operator(ref).data).max())
out["checks"]["proxy_embed_operator"] = dict(expected=0.0, got=err, tol=1e-14, ok=err < 1e-14); print("proxy embed operator err", err)
# step pattern proxy
a = QuantumCircuit(2, global_phase=0.2); a.h(0); a.t(1)
b = QuantumCircuit(3, global_phase=0.5); b.cx(0, 2); b.h(1)
st = b.copy_empty_like(name="step"); st.global_phase = 0.0; st.compose(a, qubits=[0, 1], inplace=True); st.compose(b, inplace=True)
refst = QuantumCircuit(3, global_phase=0.7); refst.h(0); refst.t(1); refst.cx(0, 2); refst.h(1)
err = float(np.abs(Operator(st).data - Operator(refst).data).max())
out["checks"]["proxy_step_operator"] = dict(expected=0.0, got=err, tol=1e-14, ok=err < 1e-14); print("proxy step operator err", err)
out["all_ok"] = all(v["ok"] for v in out["checks"].values()); print("ALL", out["all_ok"])
json.dump(out, open(sys.argv[1], "w"), indent=1)
