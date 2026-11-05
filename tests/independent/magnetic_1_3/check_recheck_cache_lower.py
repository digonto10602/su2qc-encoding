"""Tester step 1.3 recheck: try to break decomposition_cache_key / _expand / lower(); lower() counts and unitary vs whole-circuit transpile.
Usage: PYTHONPATH=src python tests/independent/magnetic_1_3/check_recheck_cache_lower.py out.json"""
import sys, json, warnings, subprocess
import numpy as np
warnings.filterwarnings("ignore")
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Gate
from qiskit.circuit.library import (RZGate, RYGate, RXGate, CRXGate, HGate, XGate, CXGate, RCCXGate, UnitaryGate, PauliEvolutionGate, PhaseGate, MCPhaseGate, SwapGate)
from qiskit.quantum_info import Operator, SparsePauliOp, random_unitary
import su2plaq.evaluate.sparse_sim as ss
from su2plaq.metrics.logical import lower, LOGICAL_BASIS, SEED
from su2plaq.circuits.twelve import build_UB, paulo_logical

out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip() + "+uncommitted"}
def dense_of(b, ncol):
    d = np.zeros((2 ** b.n_qubits, ncol), complex); np.add.at(d, (b.keys, b.cols), b.amps); return d
def sim_err(qc):
    n = qc.num_qubits; b = ss.run_batch(qc, np.arange(2 ** n, dtype=np.int64)); return float(np.abs(dense_of(b, 2 ** n) - Operator(qc).data).max())
def low_err(qc, phase=False):
    L = lower(qc); A = Operator(L).data; B = Operator(qc).data
    if phase:
        ov = np.trace(B.conj().T @ A); A = A * (abs(ov) / ov)
    return float(np.abs(A - B).max())
def mk(name, build):
    s = QuantumCircuit(build.__code__.co_argcount and 0 or 0)  # unused
def macro(name, n, f):
    s = QuantumCircuit(n, name=name); f(s); return s.to_gate()

cases = {}
# --- same-name custom gates (the original repros)
def c_same_name():
    q = QuantumCircuit(3); q.h(0)
    for f, qs in ((lambda s: s.cx(0, 1), [0, 1]), (lambda s: s.cz(0, 1), [0, 1]), (lambda s: (s.h(0), s.cx(1, 0)), [1, 2])):
        q.append(macro("macro", 2, f), qs)
    return q
cases["same_name_different_content"] = c_same_name
def c_param_macros():
    q = QuantumCircuit(4); q.h([0, 1, 2, 3])
    for a in (0.7, -1.3, 0.2, 0.9):
        q.append(macro("pg", 2, lambda s, a=a: (s.ry(a, 0), s.cx(0, 1), s.rz(2 * a, 1))), [0, 1] if a > 0.5 else [3, 1])
    return q
cases["same_name_param_macros"] = c_param_macros
# --- standard names on custom gates (name in SIM_BASIS / LOGICAL_BASIS but different definition)
for nm, n, f in (("cx", 2, lambda s: s.cz(0, 1)), ("x", 1, lambda s: s.h(0)), ("rz", 1, lambda s: s.rx(0.4, 0)), ("h", 1, lambda s: s.x(0)), ("ccx", 3, lambda s: s.cswap(0, 1, 2)),
                 ("t", 1, lambda s: s.s(0)), ("cz", 2, lambda s: s.cx(0, 1)), ("swap", 2, lambda s: s.cx(0, 1)), ("crx", 2, lambda s: s.cry(0.3, 0, 1)), ("s", 1, lambda s: s.t(0))):
    def mkc(nm=nm, n=n, f=f):
        q = QuantumCircuit(3); q.h([0, 1, 2]); g = macro(nm, n, f); q.append(g, list(range(n))); q.t(0); return q
    cases[f"custom_named_{nm}"] = mkc
# --- controlled custom gates, same name, with ctrl_state
def c_ctrl_custom():
    q = QuantumCircuit(4); q.h([0, 1, 2, 3])
    for k, f in enumerate((lambda s: s.cx(0, 1), lambda s: s.cz(0, 1), lambda s: s.ry(0.5, 1))):
        g = macro("m", 2, f)
        q.append(g.control(1), [2, 0, 1]); q.append(g.control(2, ctrl_state=1), [2, 3, 0, 1]); q.append(g.control(1, ctrl_state=0), [3, 1, 2])
    return q
cases["controlled_custom_same_name"] = c_ctrl_custom
# --- standard ctrl_state variants
def c_ctrl_std():
    q = QuantumCircuit(5); q.h(range(5))
    for cs in (0, 1, 2, 3, 5, 7):
        q.append(RZGate(0.4).control(3, ctrl_state=cs), [0, 1, 2, 3]); q.append(RXGate(0.4).control(3, ctrl_state=cs), [4, 1, 2, 3])
    for cs in (0, 1, 2, 3):
        q.append(RYGate(0.9).control(2, ctrl_state=cs), [0, 1, 4]); q.append(HGate().control(2, ctrl_state=cs), [0, 1, 2]); q.append(PhaseGate(0.3).control(2, ctrl_state=cs), [3, 1, 2])
        q.append(SwapGate().control(2, ctrl_state=cs), [0, 1, 2, 3]); q.append(XGate().control(2, ctrl_state=cs), [0, 2, 4])
    q.append(CRXGate(0.6, ctrl_state=0), [0, 1]); q.append(CRXGate(0.6, ctrl_state=1), [0, 1]); q.cx(2, 3, ctrl_state=0); q.ch(1, 4, ctrl_state=0)
    return q
cases["standard_ctrl_state_variants"] = c_ctrl_std
# --- subclasses of standard gates
class MyRZ(RZGate):            # same name 'rz', same params, different definition (perverse)
    def _define(self):
        q = QuantumCircuit(1); q.rx(self.params[0], 0); self.definition = q
class MyCRX(CRXGate):          # same name 'crx'
    def _define(self):
        q = QuantumCircuit(2); q.cry(self.params[0], 0, 1); self.definition = q
class MyRCCX(RCCXGate):
    pass
def c_sub():
    q = QuantumCircuit(3); q.h([0, 1, 2]); q.append(MyCRX(0.7), [0, 1]); q.append(CRXGate(0.7), [0, 1]); q.append(MyCRX(0.7), [1, 2]); return q
cases["subclass_crx_changed_definition"] = c_sub
def c_sub_rz():
    q = QuantumCircuit(2); q.h([0, 1]); q.append(MyRZ(0.7), [0]); q.append(RZGate(0.7), [1]); return q
cases["subclass_rz_changed_definition_same_name"] = c_sub_rz
def c_sub_ok():
    q = QuantumCircuit(3); q.h([0, 1, 2]); q.append(MyRCCX(), [0, 1, 2]); q.append(RCCXGate(), [2, 1, 0]); return q
cases["subclass_rccx_unchanged"] = c_sub_ok
# --- Gate subclass with params AND definition, same name different param
class Rot2(Gate):
    def __init__(self, a): super().__init__("rot2", 2, [a])
    def _define(self):
        q = QuantumCircuit(2); q.ry(self.params[0], 0); q.cx(0, 1); q.rz(self.params[0] * 2, 1); self.definition = q
class Rot2b(Rot2):    # same name and params, different definition
    def _define(self):
        q = QuantumCircuit(2); q.rx(self.params[0], 0); q.cz(0, 1); self.definition = q
def c_params_gate():
    q = QuantumCircuit(3); q.h([0, 1, 2])
    for a in (0.3, 0.3, 0.9): q.append(Rot2(a), [0, 1])
    q.append(Rot2b(0.3), [1, 2]); q.append(Rot2(0.3), [1, 2]); return q
cases["gate_subclass_params_same_name"] = c_params_gate
# --- others
cases["pauli_evolution_two_times"] = lambda: (lambda q: (q.h([0, 1]), q.append(PauliEvolutionGate(SparsePauliOp("XX"), time=0.3), [0, 1]), q.append(PauliEvolutionGate(SparsePauliOp("XX"), time=0.8), [0, 1]), q)[-1])(QuantumCircuit(2))
cases["mcphase_variants"] = lambda: (lambda q: (q.h(range(4)), q.append(MCPhaseGate(0.5, 3), [0, 1, 2, 3]), q.append(MCPhaseGate(0.9, 3), [0, 1, 2, 3]), q.append(MCPhaseGate(0.5, 2), [0, 1, 2]), q)[-1])(QuantumCircuit(4))
def c_gp():
    q = QuantumCircuit(2); q.h([0, 1])
    for ph in (0.3, 1.1):
        s = QuantumCircuit(2, name="gp", global_phase=ph); s.cx(0, 1); q.append(s.to_gate(), [0, 1])
    return q
cases["same_name_different_global_phase"] = c_gp
def c_nested():
    inner = lambda a: macro("in", 2, lambda s: (s.ry(a, 0), s.cx(0, 1)))
    q = QuantumCircuit(3); q.h([0, 1, 2])
    for a in (0.2, 0.8):
        o = QuantumCircuit(3, name="outer"); o.append(inner(a), [0, 1]); o.append(inner(a + 1), [1, 2]); q.append(o.to_gate(), [0, 1, 2])
    return q
cases["nested_same_names"] = c_nested
def c_cache_order():   # poison attempt: first use a standard gate, then a custom gate of the same name
    q = QuantumCircuit(3); q.h([0, 1, 2]); q.crx(0.5, 0, 1); q.append(macro("crx", 2, lambda s: s.cz(0, 1)), [0, 1]); q.crx(0.5, 1, 2); q.append(macro("crx", 2, lambda s: s.cx(1, 0)), [1, 2]); return q
cases["standard_then_custom_same_name"] = c_cache_order
cases["unitary_gate_controlled"] = lambda: (lambda q: (q.h([0, 1, 2]), q.append(UnitaryGate(random_unitary(2, seed=1)).control(1), [0, 1]), q.append(UnitaryGate(random_unitary(2, seed=2)).control(1), [0, 1]), q)[-1])(QuantumCircuit(3))

res = {}
for k, f in cases.items():
    qc = f()
    r = {}
    for fresh in (True, False):   # fresh caches vs. warm
        if fresh: ss._DECOMP_CACHE.clear()
        try: r["sim_err_" + ("cold" if fresh else "warm")] = sim_err(qc)
        except Exception as e: r["sim_err_" + ("cold" if fresh else "warm")] = f"EXC {type(e).__name__}: {str(e)[:80]}"
    try: r["lower_unitary_err_up_to_phase"] = low_err(qc, True); r["lower_exact_phase_err"] = low_err(qc, False)
    except Exception as e: r["lower_unitary_err_up_to_phase"] = f"EXC {type(e).__name__}: {str(e)[:80]}"
    res[k] = r; print(k, r, flush=True)
out["hostile"] = res

# --- the build_UB to_gate repro
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.evaluate.evaluator import evaluate
enc = TwelveQubit()
qc = QuantumCircuit(*build_UB(0.3).qregs); qc.append(build_UB(0.3).to_gate(), qc.qubits); qc.append(build_UB(0.31).to_gate(), qc.qubits)
ss._DECOMP_CACHE.clear()
v61 = evaluate(qc, enc, enc.target("UB", None, 0.61)); v60 = evaluate(qc, enc, enc.target("UB", None, 0.60))
out["ub_to_gate"] = dict(vs_0p61=dict(ok=v61.ok, err=v61.op_norm_error, leak=v61.leak_amplitude, gauss=v61.gauss_residual, sec=v61.seconds), vs_0p60=dict(ok=v60.ok, err=v60.op_norm_error))
print(out["ub_to_gate"])

# --- lower(): counts equal whole-circuit transpile on >= 20 random circuits + build_UB / paulo_logical; unitary equal up to phase
src = open("tests/independent/magnetic_1_3/check_sim_regression.py").read().split("# ---------------- (a)")[0].replace("import su2plaq.evaluate.sparse_sim as ss", "ss=None")
ns = {}; exec(src, ns); rand_circ = ns["rand_circ"]; IN = ns["IN"]; FOREIGN = ns["FOREIGN"]
rows = []
pool = [g for g in IN if g != "unitary"] + [g for g in FOREIGN if g not in ("mcp3",)]   # no unitary (lower rejects); keep mcp3 out? include below
pool = pool + ["mcp3"]
for seed in range(30):
    rng = np.random.default_rng(7000 + seed); n = int(rng.integers(4, 9)); qc = rand_circ(n, int(rng.integers(30, 70)), rng, pool)
    L = lower(qc); W = transpile(qc, basis_gates=LOGICAL_BASIS, optimization_level=0, seed_transpiler=SEED, qubits_initially_zero=False)
    cl, cw = dict(L.count_ops()), dict(W.count_ops()); cw.pop("barrier", None)
    A = Operator(L).data; B = Operator(qc).data
    rows.append(dict(seed=7000 + seed, n=n, gates=len(qc.data), counts_equal=cl == cw, cx=(cl.get("cx", 0), cw.get("cx", 0)), t=(cl.get("t", 0) + cl.get("tdg", 0), cw.get("t", 0) + cw.get("tdg", 0)),
                     rz=(cl.get("rz", 0), cw.get("rz", 0)), unitary_err_exact_phase=float(np.abs(A - B).max()), unitary_err_whole=float(np.abs(Operator(W).data - B).max())))
print("lower vs whole-circuit transpile: counts equal in", sum(r["counts_equal"] for r in rows), "/", len(rows), " max unitary err (exact phase)", max(r["unitary_err_exact_phase"] for r in rows))
for r in rows:
    if not r["counts_equal"]: print("  differs:", r)
out["lower_random"] = rows
for nm, c in (("build_UB(0.61)", build_UB(0.61)), ("build_UB(0.61,outer)", build_UB(0.61, with_outer=True)), ("paulo_logical(1)", paulo_logical(1.0))):
    L = lower(c); W = transpile(c, basis_gates=LOGICAL_BASIS, optimization_level=0, seed_transpiler=SEED, qubits_initially_zero=False); cw = dict(W.count_ops())
    out["lower_" + nm] = dict(counts_lower=dict(L.count_ops()), counts_whole=cw, equal=dict(L.count_ops()) == cw, depth_lower=L.depth(), depth_whole=W.depth(), phase_lower=float(L.global_phase), phase_whole=float(W.global_phase))
    print(nm, out["lower_" + nm]["equal"], out["lower_" + nm]["counts_lower"], "depth", L.depth(), W.depth())
# lowered unitary of build_UB on the 625 inner codes vs original (sparse sim)
codes = enc.inner_codes(); L = lower(build_UB(0.61))
b1 = ss.run_batch(build_UB(0.61), codes); b2 = ss.run_batch(L, codes)
d1 = dense_of(b1, len(codes)) if False else None
from scipy.sparse import csr_matrix
def spm(b): 
    return csr_matrix((b.amps, (b.keys, b.cols)), shape=(1 << b.n_qubits if False else int(max(b.keys.max(), 1)) + 1, len(codes)))
k = int(max(b1.keys.max(), b2.keys.max())) + 1
M1 = csr_matrix((b1.amps, (b1.keys, b1.cols)), shape=(k, len(codes))); M2 = csr_matrix((b2.amps, (b2.keys, b2.cols)), shape=(k, len(codes)))
out["lowered_UB_vs_original_625cols_maxabs_diff"] = float(abs(M1 - M2).max())
print("lowered build_UB vs build_UB on 625 inputs (exact phase):", out["lowered_UB_vs_original_625cols_maxabs_diff"])
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)
