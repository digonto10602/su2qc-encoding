"""Tester 203: adversarial circuits against su2plaq.rishon.verify.verify (UE target, alpha=0.37).
Every case must be NOT ok except the explicitly marked 'accept' controls.  Output: JSON."""
import json, subprocess, sys, time
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Gate
from qiskit.circuit.library import UnitaryGate, CPhaseGate, SwapGate
from qiskit.circuit.library import MCXGate
sys.path.insert(0, "src")
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.rishon import verify as V
from su2plaq.circuits.rishon import build_UE

ALPHA = 0.37
enc = RishonEncoding()

def base(n_anc=2, alpha=ALPHA):
    qc = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"), *( [QuantumRegister(n_anc, "a")] if n_anc else []))
    ue = build_UE(alpha)
    qc.compose(ue, qubits=list(range(16)), inplace=True)
    return qc

cases = {}
def run(name, qc, expect_ok, kind="UE", alpha=ALPHA, **kw):
    t0 = time.time()
    try:
        v = V.verify(qc, enc, kind, alpha, None, **kw)
        rec = dict(ok=v.ok, reason=v.reason, op_norm_error=v.op_norm_error, leak=v.leak_amplitude, block=v.block_error,
                   dirty=v.dirty_ancilla, gauss=v.gauss_residual, outer_read=v.outer_bits_read, exc=None)
    except Exception as e:  # an exception is a non-accept; record it
        rec = dict(ok=False, reason="EXCEPTION", exc=f"{type(e).__name__}: {str(e)[:150]}")
    rec["expect_ok"] = expect_ok
    rec["pass"] = (rec["ok"] == expect_ok)
    rec["sec"] = round(time.time() - t0, 2)
    cases[name] = rec
    print(f"{name:55s} ok={rec['ok']!s:5} reason={rec.get('reason')} err={rec.get('op_norm_error')} pass={rec['pass']} {rec.get('exc') or ''}", flush=True)

run("control_UE_ok", base(), True)

# A1: outer read hidden in a custom gate named 'cx' (phase on outer=1 only)
sub = QuantumCircuit(2); sub.cp(0.5, 0, 1)
g = sub.to_gate(label="cx"); g.name = "cx"
qc = base(); qc.append(g, [16, 0]); run("A1_hidden_read_custom_gate_named_cx", qc, False)

# A2: Gate subclass reusing the class name CZGate with other definition
class CZGate(Gate):
    def __init__(self): super().__init__("cz", 2, [])
    def _define(self):
        q = QuantumCircuit(2); q.cp(0.7, 0, 1); self.definition = q
qc = base(); qc.append(CZGate(), [16, 0]); run("A2_subclass_named_cz_outer_read", qc, False)

# A3: UnitaryGate controlled phase on (outer, data)
m = np.diag([1, 1, 1, np.exp(0.5j)]).astype(complex)
qc = base(); qc.append(UnitaryGate(m), [16, 3]); run("A3_unitary_controlled_phase_outer", qc, False)

# A3b: nested custom gate inside custom gate
inner = QuantumCircuit(2); inner.cz(0, 1); gi = inner.to_gate(label="foo")
outer = QuantumCircuit(3); outer.append(gi, [0, 2]); go = outer.to_gate(label="bar")
qc = base(); qc.append(go, [20, 1, 5]); run("A3b_nested_custom_outer_read", qc, False)

# A4: custom gate named cx with matrix but no definition
class NoDef(Gate):
    def __init__(self): super().__init__("cx", 2, [])
    def __array__(self, dtype=None, copy=None): return np.eye(4, dtype=complex)
qc = base(); qc.append(NoDef(), [0, 1]); run("A4_gate_named_cx_no_definition", qc, False)

# A5: gate named cx whose definition is swap on data qubits (different matrix)
class FakeCX(Gate):
    def __init__(self): super().__init__("cx", 2, [])
    def _define(self):
        q = QuantumCircuit(2); q.swap(0, 1); self.definition = q
qc = base(); qc.append(FakeCX(), [0, 2]); run("A5_gate_named_cx_is_swap_on_data", qc, False)

# A5b: plain data-only wrongly-named identity-lookalike: custom gate named 'cp' that does nothing but a different phase
class FakeCP(Gate):
    def __init__(self): super().__init__("cp", 2, [0.1])
    def _define(self):
        q = QuantumCircuit(2); q.cp(0.1 + 3e-9, 0, 1); self.definition = q
qc = base(); qc.append(FakeCP(), [0, 1]); run("A5b_fake_cp_3e-9_off_on_data", qc, False)

# A6: outer-controlled gate, control |1>-active, standard cp tiny
qc = base(); qc.cp(1e-3, 16, 0); run("A6_cp_outer_control", qc, False)
qc = base(); qc.cx(16, 0); run("A6b_cx_outer_control", qc, False)

# A7: mcx with 3 controls including an outer one
qc = base(); qc.append(MCXGate(3), [16, 0, 1, 2]); run("A7_mcx3_with_outer_control", qc, False)
qc = base(); qc.append(MCXGate(2), [16, 0, 1]); run("A7b_ccx_outer_control", qc, False)

# A8: open control on outer
qc = base(); qc.cx(16, 0, ctrl_state=0); run("A8_cx_open_control_outer", qc, False)
qc = base(); qc.crz(0.3, 16, 0); run("A8b_crz_outer_control", qc, False)
qc = base(); qc.cry(0.3, 16, 0); run("A8c_cry_outer_control", qc, False)
qc = base(); qc.rzz(0.3, 16, 0); run("A8d_rzz_outer_data", qc, False)
qc = base(); qc.rz(0.3, 16); run("A8e_rz_on_outer_only", qc, False)
qc = base(); qc.swap(16, 17); run("A8f_swap_outer", qc, False)
qc = base(); qc.x(16); qc.x(16); run("A8g_x_x_on_outer_restored", qc, False)
qc = base(); qc.rx(1e-13, 16); run("A8h_rx_1e-13_on_outer", qc, False)

# A9: ancilla dirtied only on code AAAA (bits 0,1,4,5,8,9,12,13 all 1): AND chain into ancillas, last not uncomputed
def and_chain(qc, ctrls, anc, uncompute_last=False, phase=None):
    # anc list of len(ctrls)-1 ancillas; anc[0] = c0&c1, anc[i] = anc[i-1]&c[i+1]
    qc.ccx(ctrls[0], ctrls[1], anc[0])
    for i in range(1, len(anc)):
        qc.ccx(anc[i - 1], ctrls[i + 1], anc[i])
    if phase is not None: qc.p(phase, anc[-1])
    if uncompute_last:
        for i in range(len(anc) - 1, 0, -1): qc.ccx(anc[i - 1], ctrls[i + 1], anc[i])
        qc.ccx(ctrls[0], ctrls[1], anc[0])
    else:
        for i in range(len(anc) - 2, 0, -1): qc.ccx(anc[i - 1], ctrls[i + 1], anc[i])
        qc.ccx(ctrls[0], ctrls[1], anc[0])
aaaa = [0, 1, 4, 5, 8, 9, 12, 13]
qc = base(n_anc=7); and_chain(qc, aaaa, list(range(48, 55)), uncompute_last=False)
# the uncompute above leaves anc[0..5] cleaned but anc[6] holds the AND (anc[6] computed from anc[5]): redo cleanly
run("A9_ancilla_dirty_only_on_code_AAAA", qc, False)

# A10: phase error exp(i*eps) only on code AAAA, ancillas fully restored
for eps in (3.0, 1e-3, 1e-6, 5e-10, 2e-10):
    qc = base(n_anc=7); and_chain(qc, aaaa, list(range(48, 55)), uncompute_last=True, phase=eps)
    run(f"A10_phase_{eps}_only_on_AAAA", qc, False)
# 5e-11 is below tol_err=1e-10: honest accept (error 5e-11 <= 1e-10); mark expected ok
qc = base(n_anc=7); and_chain(qc, aaaa, list(range(48, 55)), uncompute_last=True, phase=5e-11)
run("A10_phase_5e-11_only_on_AAAA_(below_tol: accept)", qc, True)

# A11: phase on an invalid-code pattern only (don't-care): accept
qc = base(); qc.ccz(0, 1, 2); run("A11_ccz_on_invalid_pattern_dontcare(accept)", qc, True)
# A11b: a phase on a valid code outside nothing: ccz(0,1,4) acts on valid (A,A..) codes
qc = base(); qc.ccz(0, 1, 4); run("A11b_ccz_on_valid_codes", qc, False)

# A12: layout abuse
bad = QuantumCircuit(QuantumRegister(15, "d"), QuantumRegister(33, "o")); run("A12_bad_layout", bad, False)
bad = QuantumCircuit(QuantumRegister(16, "x")); run("A12b_unnamed_registers", bad, False)
# A13: measure / reset
qc = base(); qc.reset(0); run("A13_reset", qc, False)
qc = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"), QuantumRegister(2, "a"), __import__("qiskit").ClassicalRegister(1))
qc.compose(build_UE(ALPHA), qubits=list(range(16)), inplace=True); qc.measure(0, 0); run("A13b_measure", qc, False)
# A14: global phase only (accept)
qc = base(); qc.global_phase = 0.3; run("A14_global_phase(accept)", qc, True)
# A15: wrong sign alpha / wrong target kind
run("A15_wrong_alpha_sign", base(alpha=-ALPHA), False)
run("A15b_wrong_kind", base(), False, kind="UB", alpha=None) if False else None
# A16: Z on one rarely-hit code via gauss-sample-miss: tested by A10
# A17: rz instead of p on L2 (differs by a Z-dependent phase on quartets only? control: equivalent up to global phase -> check)
qc = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"), QuantumRegister(2, "a"))
for l in range(4):
    qc.cx(4*l, 4*l+1); qc.rz(-0.75*ALPHA, 4*l+1); qc.cx(4*l, 4*l+1)
run("A17_rz_instead_of_p(per link phase differs by a global e^{-i...}: expect accept after global phase)", qc, True)
json.dump(dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip(), alpha=ALPHA, cases=cases),
          open("results/rishon/tester-203-adversarial.json", "w"), indent=1, default=str)
print("n_cases", len(cases), "n_mismatch", sum(not c["pass"] for c in cases.values()))
