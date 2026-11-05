"""Tester (reports/tests m1 audit fixes), N6 adversarial: disguised gates must be simulated/counted BY CONTENT or rejected.
Usage: PYTHONPATH=src python tests/independent/audit_fixes/adversarial_n6.py results/m1_audit_fixes_n6.json
Truth = dense qiskit Operator(qc) (which expands custom gates from their definition) and, for counts, the lowering of the
circuit with every custom gate replaced by its definition (reference built independently of su2plaq)."""
import sys, json, warnings, subprocess
import numpy as np
warnings.filterwarnings("ignore")
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Gate, Instruction
from qiskit.circuit.library import (RZGate, RXGate, XGate, TGate, HGate, CXGate, CRXGate, CZGate, UnitaryGate, PhaseGate, CCXGate, SXGate,
                                   RCCXGate, MCXGate, CPhaseGate, UGate)
from qiskit.circuit.library.standard_gates import get_standard_gate_name_mapping
from qiskit.quantum_info import Operator, random_unitary
import su2plaq.evaluate.sparse_sim as ss
from su2plaq.metrics.logical import lower, logical_metrics, LOGICAL_BASIS

out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip() + "+uncommitted", "seed": 123}
STD = get_standard_gate_name_mapping()
rng = np.random.default_rng(123)

def dense_of(b, ncol):
    d = np.zeros((2 ** b.n_qubits, ncol), complex); np.add.at(d, (b.keys, b.cols), b.amps); return d

def sim_status(qc):
    n = qc.num_qubits
    try:
        b = ss.run_batch(qc, np.arange(2 ** n, dtype=np.int64))
    except ValueError as e:
        return "rejected", str(e)[:70]
    err = float(np.abs(dense_of(b, 2 ** n) - Operator(qc).data).max())
    return ("ok" if err < 1e-10 else "WRONG"), err

def ref_counts(qc):
    """independent reference: expand every non-standard-class instruction recursively into its definition, then whole-circuit
    transpile to the logical basis"""
    def is_std(op):
        r = STD.get(op.name)
        return r is not None and type(op) is type(r) or (r is not None and type(op).__name__.lstrip("_").replace("Singleton", "") == type(r).__name__ and type(op).__module__.startswith("qiskit.circuit.library"))
    def expand(c):
        o = QuantumCircuit(*c.qregs, global_phase=c.global_phase)
        for inst in c.data:
            op = inst.operation
            if is_std(op) or op.name == "barrier" and type(op).__name__ == "Barrier":
                o.append(op, inst.qubits)
            else:
                d = expand(op.definition)
                o.compose(d, qubits=inst.qubits, inplace=True)
        return o
    e = expand(qc)
    w = transpile(e, basis_gates=LOGICAL_BASIS, optimization_level=0, seed_transpiler=1, qubits_initially_zero=False)
    c = dict(w.count_ops()); c.pop("barrier", None)
    return c, e

def lower_status(qc):
    try:
        L = lower(qc)
    except ValueError as e:
        return "rejected", str(e)[:70]
    try:
        cref, e = ref_counts(qc)
    except Exception as ex:
        return "ref-fail", repr(ex)[:70]
    cl = dict(L.count_ops())
    Ud = Operator(L).data; Uo = Operator(qc).data
    ov = np.trace(Uo.conj().T @ Ud); Ud2 = Ud * (abs(ov) / ov)
    uerr = float(np.abs(Ud2 - Uo).max())
    cnt_ok = cl == cref
    return ("ok" if cnt_ok and uerr < 1e-10 else "WRONG"), dict(counts_lower=cl, counts_ref=cref, unitary_err=uerr)

def rand_content(nq, name, kind):
    """content circuit on nq qubits, guaranteed != standard gate of that name (by construction: random, with h/t/cx mix)"""
    s = QuantumCircuit(nq, name=name)
    if kind == "random_unitary":
        s.append(UnitaryGate(random_unitary(2 ** nq, seed=int(rng.integers(1 << 30)))), range(nq))
    elif kind == "cliffordt":
        for _ in range(6):
            q = int(rng.integers(nq)); s.h(q); s.t(q)
            if nq > 1: s.cx(q, (q + 1) % nq)
        s.tdg(0)
    elif kind == "x_only":
        s.x(0)
    return s

class P:
    results = []
def record(case, kind, circ):
    s1 = sim_status(circ); l1 = lower_status(circ)
    ok = s1[0] in ("ok", "rejected") and l1[0] in ("ok", "rejected")
    P.results.append(dict(case=case, kind=kind, sim=s1[0], sim_detail=s1[1] if not isinstance(s1[1], float) else f"{s1[1]:.2e}",
                          lower=l1[0], lower_detail=l1[1] if isinstance(l1[1], str) else l1[1], safe=ok))
    flag = "" if ok else "   <<<<<<<< UNSAFE"
    if not ok or "genuine" in case: print(f"{case:55s} {kind:16s} sim={s1[0]:9s} lower={l1[0]:9s}{flag}", flush=True)

basis_names = sorted(set(ss.SIM_BASIS) | set(LOGICAL_BASIS))
# 1) every basis name, with different content (random unitary, clifford+T mix, X only) ; also upper/mixed case
for nm in basis_names:
    r = STD.get(nm)
    nq = r.num_qubits if r is not None else 2
    for kind in ("random_unitary", "cliffordt", "x_only"):
        if kind == "x_only" and nq != 1: continue
        if kind == "random_unitary" and nq >= 3: continue   # reference transpile of 8x8 UnitaryGate not available (harness limit)
        for variant in (nm, nm.upper(), nm.capitalize()):
            s = rand_content(nq, variant, kind)
            qc = QuantumCircuit(max(nq, 1) + 2); qc.h(range(qc.num_qubits)); qc.append(s.to_gate(), list(range(nq))); qc.t(0)
            record(f"custom_named_{variant}", kind, qc)
# 2) custom gate with params (rz/p/u/cp etc.) with a DIFFERENT angle convention
for nm, nq, build in (("rz", 1, lambda s, a: s.p(a, 0)), ("rz", 1, lambda s, a: s.rz(2 * a, 0)), ("rz", 1, lambda s, a: s.rz(a / 2, 0)),
                      ("p", 1, lambda s, a: s.rz(a, 0)), ("cp", 2, lambda s, a: s.crz(a, 0, 1)), ("u", 1, lambda s, a: s.rx(a, 0)),
                      ("rz", 1, lambda s, a: (s.rz(a, 0), s.global_phase.__class__) and s.rz(a, 0))):
    class G(Gate):
        def __init__(self, a, nm=nm, nq=nq): super().__init__(nm, nq, [a])
        def _define(self, build=build, nq=nq):
            s = QuantumCircuit(nq); build(s, self.params[0]); self.definition = s
    qc = QuantumCircuit(3); qc.h([0, 1, 2]); qc.append(G(0.77), list(range(nq))); qc.append(G(0.31), [1, 2][:nq] if nq == 2 else [2]); qc.t(1)
    record(f"param_disguise_{nm}", getattr(build, "__name__", "lam"), qc)
# rz with global phase only difference (rz vs p): phase relative matters under control
class Gp(Gate):
    def __init__(self): super().__init__("rz", 1, [0.8])
    def _define(self): q = QuantumCircuit(1); q.p(0.8, 0); self.definition = q
qc = QuantumCircuit(2); qc.h(0); qc.append(Gp().control(1), [0, 1]); qc.append(Gp().control(1, ctrl_state=0), [1, 0]); record("rz_disguise_controlled", "p-vs-rz", qc)
# 3) disguised controlled gates: custom named like base, .control(k) gives names 'cx','ccx','crz','crx' etc but ControlledGate class
for nm, nq, f in (("x", 1, lambda s: s.h(0)), ("z", 1, lambda s: s.x(0)), ("h", 1, lambda s: s.x(0)), ("rx", 1, lambda s: s.ry(0.3, 0)), ("x", 1, lambda s: (s.t(0), s.h(0)))):
    for k, cs in ((1, None), (2, None), (1, 0), (2, 1)):
        g = rand_content(nq, nm, "cliffordt").to_gate() if nm != "rx" else Gate("rx", 1, [0.3])
        s = QuantumCircuit(nq, name=nm); f(s)
        if nm == "rx":
            class RXd(Gate):
                def __init__(self): super().__init__("rx", 1, [0.3])
                def _define(self): q = QuantumCircuit(1); q.ry(0.3, 0); self.definition = q
            base = RXd()
        else:
            base = s.to_gate()
        cg = base.control(k, ctrl_state=cs)
        qc = QuantumCircuit(k + 2); qc.h(range(k + 2)); qc.append(cg, list(range(k + nq))); qc.t(0)
        record(f"disguised_controlled_{nm}_k{k}_cs{cs}", f"gate name={cg.name} cls={type(cg).__name__}", qc)
# 4) subclasses of standard classes
class RZGate(RZGate):                     # SAME class name 'RZGate', other module, overridden _define & to_matrix  (name-spoof)
    def _define(self):
        q = QuantumCircuit(1); q.rx(self.params[0], 0); self.definition = q
    def to_matrix(self):
        return RXGate(self.params[0]).to_matrix()
RZspoof = RZGate
from qiskit.circuit.library import RZGate as RZstd
class MyRZ(RZstd):
    def _define(self):
        q = QuantumCircuit(1); q.rx(self.params[0], 0); self.definition = q
    def to_matrix(self): return RXGate(self.params[0]).to_matrix()
class XGate(__import__("qiskit").circuit.library.XGate):   # name-spoof of XGate
    def _define(self):
        q = QuantumCircuit(1); q.h(0); self.definition = q
    def to_matrix(self): return HGate().to_matrix()
class TGate(__import__("qiskit").circuit.library.TGate):
    def _define(self):
        q = QuantumCircuit(1); q.x(0); self.definition = q
    def to_matrix(self): return XGate().__class__.__mro__[1]().to_matrix()
class CXGate(__import__("qiskit").circuit.library.CXGate):
    def _define(self):
        q = QuantumCircuit(2); q.cz(0, 1); self.definition = q
    def to_matrix(self): return CZGate().to_matrix()
class MyT(__import__("qiskit").circuit.library.TGate):
    def _define(self):
        q = QuantumCircuit(1); q.x(0); self.definition = q
    def to_matrix(self): return np.array([[0, 1], [1, 0]], complex)
for nm, g, nq in (("RZGate-spoof", RZspoof(0.7), 1), ("MyRZ", MyRZ(0.7), 1), ("XGate-spoof", XGate(), 1), ("TGate-spoof", TGate(), 1), ("CXGate-spoof", CXGate(), 2), ("MyT", MyT(), 1)):
    qc = QuantumCircuit(3); qc.h([0, 1, 2]); qc.append(g, list(range(nq))); qc.t(2)
    record(f"std_subclass_{nm}", f"cls={type(g).__name__} mod={type(g).__module__}", qc)
# 4b) forged class: named like Qiskit's, module forged to look like qiskit
Forged = type("TGate", (__import__("qiskit").circuit.library.TGate,), {"_define": lambda self: setattr(self, "definition", (lambda q: (q.x(0), q)[1])(QuantumCircuit(1))), "__module__": "qiskit.circuit.library.standard_gates.t"})
qc = QuantumCircuit(2); qc.h([0, 1]); qc.append(Forged(), [0]); record("forged_module_TGate", "module forged to qiskit.*", qc)
# 4c) standard instance mutated: name or definition rewritten after construction
g = XGate.__mro__[1]()  # real qiskit XGate (singleton?) -> use a mutable copy
g2 = g.to_mutable(); g2.name = "t"
qc = QuantumCircuit(2); qc.h([0, 1]); qc.append(g2, [0]); record("real_XGate_renamed_t", "instance.name='t'", qc)
g3 = __import__("qiskit").circuit.library.TGate().to_mutable(); g3.name = "x"
qc = QuantumCircuit(2); qc.h([0, 1]); qc.append(g3, [0]); record("real_TGate_renamed_x", "instance.name='x'", qc)
g4 = RZstd(0.7).copy(); g4.params = [0.1]; qc = QuantumCircuit(2); qc.h([0, 1]); qc.append(g4, [0]); record("real_RZ_params_mutated", "params=[0.1]", qc)
g5 = RZstd(0.7).copy(); g5.definition = (lambda q: (q.rx(0.7, 0), q)[1])(QuantumCircuit(1)); qc = QuantumCircuit(2); qc.h([0, 1]); qc.append(g5, [0]); record("real_RZ_definition_overwritten", "definition rewritten (instance)", qc)
# 5) nested disguises: custom 'cx' containing custom 't' containing custom 'h' ...
def nest():
    inner = QuantumCircuit(1, name="h"); inner.x(0); inner.t(0)
    mid = QuantumCircuit(1, name="t"); mid.append(inner.to_gate(), [0]); mid.x(0)
    outer = QuantumCircuit(2, name="cx"); outer.append(mid.to_gate(), [1]); outer.cz(0, 1); outer.append(mid.to_gate(), [0])
    top = QuantumCircuit(2, name="rz"); top.append(outer.to_gate(), [0, 1]); top.append(outer.to_gate(), [1, 0])
    qc = QuantumCircuit(4); qc.h(range(4)); qc.append(top.to_gate(), [0, 1]); qc.append(top.to_gate(), [3, 2]); qc.t(0)
    return qc
record("nested_disguise_cx_t_h_rz", "3 levels", nest())
# 5b) disguise containing a wide mcx (3 controls): must stay rejected
def wide_mcx_disguise(name):
    inner = QuantumCircuit(5, name=name); inner.mcx([0, 1, 2], 3)
    qc = QuantumCircuit(6); qc.h(range(6)); qc.append(inner.to_gate(), range(5)); return qc
for nm in ("cx", "h", "t", "x", "ccx", "barrier", "rz"):
    record(f"mcx3_inside_gate_named_{nm}", "must be rejected", wide_mcx_disguise(nm))
# 5c) fake barrier: custom gate named 'barrier' with content
s = QuantumCircuit(2, name="barrier"); s.cx(0, 1); qc = QuantumCircuit(3); qc.h([0, 1, 2]); qc.append(s.to_gate(), [0, 1]); qc.t(1)
record("fake_barrier_gate_with_content", "Gate named barrier", qc)
s = Instruction("barrier", 2, 0, []); 
try:
    qc = QuantumCircuit(3); qc.h([0, 1, 2]); qc.append(s, [0, 1]); qc.t(1); record("fake_barrier_instruction_no_definition", "Instruction named barrier", qc)
except Exception as e: print("fake barrier instr", e)
qc = QuantumCircuit(3); qc.h([0, 1, 2]); qc.barrier(); qc.t(1); record("true_barrier", "control", qc)
# 5d) Instruction (not Gate) named 't' with definition
s = QuantumCircuit(1, name="t"); s.x(0); qc = QuantumCircuit(2); qc.h([0, 1]); qc.append(s.to_instruction(), [0]); record("instruction_named_t", "to_instruction", qc)
# 5e) opaque gate named like a basis gate, no definition
for nm in ("t", "cx", "rz", "unitary", "h"):
    nq = 2 if nm == "cx" else 1
    op = Gate(nm, nq, [0.3] if nm == "rz" else []); qc = QuantumCircuit(2); qc.h([0, 1]); qc.append(op, list(range(nq)))
    record(f"opaque_gate_named_{nm}", "no definition", qc)
# 5f) custom gate named unitary (not UnitaryGate) and UnitaryGate subclass
s = QuantumCircuit(1, name="unitary"); s.x(0); qc = QuantumCircuit(2); qc.h([0, 1]); qc.append(s.to_gate(), [0]); record("custom_named_unitary_X", "to_gate", qc)
class UG2(UnitaryGate): pass
qc = QuantumCircuit(2); qc.h([0, 1]); qc.append(UG2(random_unitary(2, seed=4)), [0]); record("UnitaryGate_subclass", "subclass name UG2", qc)
# 5g) annotated / modified
try:
    g = HGate().control(1, annotated=True); qc = QuantumCircuit(3); qc.h([0, 1, 2]); qc.append(g, [0, 1]); record("annotated_controlled_H", type(g).__name__, qc)
    g = RZstd(0.4).control(2, annotated=True); qc = QuantumCircuit(4); qc.h(range(4)); qc.append(g, [0, 1, 2]); record("annotated_ccrz", type(g).__name__, qc)
    from qiskit.circuit.library import XGate as X0
    g = X0().control(1, annotated=True); qc = QuantumCircuit(3); qc.h(range(3)); qc.append(g, [0, 1]); record("annotated_cx", type(g).__name__, qc)
except Exception as e: print("annot", repr(e)[:100])
# 6) controls of REAL standard gates still fine (no change)
for g, nq in ((RZstd(0.4).control(1), 2), (RZstd(0.4).control(2), 3), (CRXGate(0.3), 2), (HGate().control(2, ctrl_state=1), 3), (PhaseGate(0.4).control(2), 3)):
    qc = QuantumCircuit(4); qc.h(range(4)); qc.append(g, list(range(nq))); record(f"genuine_{g.name}", "control group", qc)

bad = [r for r in P.results if not r["safe"]]
out["n_cases"] = len(P.results); out["n_unsafe"] = len(bad); out["unsafe"] = bad; out["all"] = P.results
out["n_sim_ok"] = sum(r["sim"] == "ok" for r in P.results); out["n_sim_rejected"] = sum(r["sim"] == "rejected" for r in P.results); out["n_sim_wrong"] = sum(r["sim"] == "WRONG" for r in P.results)
out["n_low_ok"] = sum(r["lower"] == "ok" for r in P.results); out["n_low_rejected"] = sum(r["lower"] == "rejected" for r in P.results); out["n_low_wrong"] = sum(r["lower"] not in ("ok", "rejected") for r in P.results)
print({k: out[k] for k in out if k.startswith("n_")})
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)
