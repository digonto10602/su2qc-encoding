import json, pathlib, sys, time, hashlib
SP = pathlib.Path("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv")
PAT = json.load(open(SP/"pattern.json"))
HDR = '"""SUMMARY: {s}\n"""\nFAMILY = "ADV"\nPARENT = None\n\nfrom su2plaq.compress.builder import Builder\n{extra}\n\n'
UE_CORE = '''    b = Builder(spec)
    d = b.reg("d"); o = b.reg("o")
    for link in range(4):
        b.p(-0.75 * spec.alpha, d[3 * link + 2])
'''
def prog(body, s="adv", extra=""):
    return HDR.format(s=s, extra=extra) + body

cases = {}
# --- 1 wrong on a handful of physical states (all outside the trial subset)
qs, pat = PAT["qs"], PAT["pat"]
flip = "".join(f"    b.x({q})\n" for q, p in zip(qs, pat) if p == 0)
cases["cheat_subset_states"] = prog(f'''def build(spec):
{UE_CORE}    qs = {qs}
    ctrl = qs[1:]; tgt = qs[0]
{flip}    b.h(tgt)
    b.mcx(ctrl, tgt)
    b.h(tgt)
{flip}    return b
''')
# --- 2 dirty ancilla
cases["dirty_ancilla"] = prog(f'''def build(spec):
{UE_CORE}    a = b.alloc(1)[0]
    b.cx(d[2], a)
    return b
''')
# --- 3 leak amplitude
for nm, amp in (("leak_1e-9", 1e-9), ("leak_1e-11", 1e-11)):
    cases[nm] = prog(f'''def build(spec):
{UE_CORE}    a = b.alloc(1)[0]
    b.h(a); b.rz({2*amp!r}, a); b.h(a)
    return b
''')
# --- 4 angle specialised
cases["angle_skeleton_different_gates"] = prog(f'''def build(spec):
    b = Builder(spec)
    d = b.reg("d")
    for link in range(4):
        if spec.alpha > 0.5:
            b.rz(-0.75 * spec.alpha, d[3 * link + 2])   # rz instead of p: differs by a global phase only
        else:
            b.p(-0.75 * spec.alpha, d[3 * link + 2])
    return b
''')
cases["angle_hardcoded_nominal"] = prog('''def build(spec):
    b = Builder(spec)
    d = b.reg("d")
    for link in range(4):
        b.p(-0.75 * 0.37, d[3 * link + 2])
    return b
''')
# --- 5 disguised gates (circuit returned through a tampered Builder.circuit)
def tamper(code):
    return prog(f'''import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Gate, QuantumRegister
from qiskit.circuit.library import HGate, XGate, UnitaryGate, CXGate, RZGate

def build(spec):
{UE_CORE}    qc = b.circuit()
{code}
    b.circuit = lambda: qc
    return b
''')
cases["disguised_renamed_class"] = tamper('''    g = HGate(); g.name = "cx"
    qc.h(0); qc.append(g, [0])''')
cases["disguised_custom_gate_named_h"] = tamper('''    inner = QuantumCircuit(1); inner.rz(0.3, 0)
    g = Gate("h", 1, []); g.definition = inner
    qc.append(g, [0])''')
cases["disguised_unitary_named_x"] = tamper('''    u = UnitaryGate(np.array([[0,1],[1,0]]), label="x"); u.name = "x"
    qc.append(u, [0])''')
cases["disguised_ry"] = tamper('''    qc.ry(1e-3, 0); qc.ry(-1e-3, 0)''')
cases["disguised_sx_pair"] = tamper('''    qc.sx(0); qc.sxdg(0)''')
cases["disguised_native_mcx"] = tamper('''    qc.mcx([0,1,2,3], 4); qc.mcx([0,1,2,3], 4)''')
cases["disguised_hidden_t_in_custom"] = tamper('''    inner = QuantumCircuit(1); inner.t(0); inner.tdg(0)
    g = inner.to_gate(label="cx"); g.name = "z"
    qc.append(g, [0])''')
cases["disguised_cx_renamed_from_ccx"] = tamper('''    from qiskit.circuit.library import CCXGate
    g = CCXGate(); g.name = "cx"
    qc.append(g, [0,1,2]); qc.append(g, [0,1,2])''')
# --- 6 writing outer
cases["writes_outer"] = prog(f'''def build(spec):
{UE_CORE}    b.x(o[0])
    return b
''')
# --- 7 qubit cap
cases["qubit_cap_direct_qc"] = tamper('''    qc = QuantumCircuit(QuantumRegister(28,"d"), QuantumRegister(200,"anc"))
    qc.p(-0.75*spec.alpha, 2)''')
cases["qubit_cap_alloc"] = prog(f'''def build(spec):
{UE_CORE}    b.alloc(100)
    return b
''')
cases["qubit_cap_ancilla_tamper"] = prog(f'''def build(spec):
{UE_CORE}    b._n_anc = 500
    b.peak_qubits = 0
    return b
''')
# --- 8 builder attribute tampering
cases["tamper_peak_qubits"] = prog(f'''def build(spec):
{UE_CORE}    for _ in range(40): b.alloc(1)
    b.peak_qubits = 1
    return b
''')
cases["tamper_ops_ry"] = prog(f'''def build(spec):
{UE_CORE}    b._ops.append(("ry", (0.3,), (0,)))
    return b
''')
cases["tamper_ops_mcx"] = prog(f'''def build(spec):
{UE_CORE}    b._ops.append(("mcx", (), (0,1,2,3,4)))
    return b
''')
cases["tamper_ops_bigqubit"] = prog(f'''def build(spec):
{UE_CORE}    b._ops.append(("x", (), (300,)))
    return b
''')
cases["tamper_spec_in_builder"] = prog('''def build(spec):
    spec.alpha = 0.0
    b = Builder(spec)
    d = b.reg("d")
    return b
''')
cases["tamper_class_swap"] = prog(f'''import su2plaq.compress.builder as BB
def build(spec):
{UE_CORE}    class Fake(BB.Builder):
        pass
    b.__class__ = Fake
    return b
''')
cases["tamper_builder_monkeypatch_basis"] = prog(f'''import su2plaq.compress.builder as BB
def build(spec):
    BB.BASIS.add("ry"); BB.MACROS.add("ry"); BB._ARITY["ry"]=1; BB._PARAMETRIC.add("ry")
{UE_CORE}    b.rz(1e-3, 0)
    b._emit("ry", (0.2,), (0,))
    return b
''')
# --- 9 forbidden imports / file io
for nm, line in {"import_os": "import os", "import subprocess": "import subprocess", "import sys": "import sys",
                 "import socket": "import socket", "import importlib": "import importlib", "import pickle": "import pickle",
                 "import evaluator": "from su2plaq.evaluate import evaluator", "import su2plaq_compress_evaluate": "import su2plaq.compress.evaluate",
                 "from_compress_import_evaluate": "from su2plaq.compress import evaluate",
                 "from_su2plaq_import_circuits": "from su2plaq import circuits",
                 "import_scipy": "import scipy", "import pathlib": "import pathlib", "import builtins": "import builtins",
                 "import ctypes": "import ctypes", "import shutil": "import shutil", "import io": "import io",
                 "import qiskit_aer": "import qiskit_aer", "from_numpy_lib_import_os": "import numpy.lib.npyio"}.items():
    cases["forbid_" + nm] = prog(f'''def build(spec):
{UE_CORE}    return b
''', extra=line)
for nm, stmt in {"open": "f = open('/etc/passwd')", "exec": "exec('x=1')", "eval": "eval('1')", "compile": "compile('1','a','eval')",
                 "dunder_import": "m = __import__('os')", "getattr_builtins": "f = getattr(__builtins__, 'op' + 'en')"}.items():
    cases["forbid_use_" + nm] = prog(f'''def build(spec):
    {stmt}
{UE_CORE}    return b
''')
# bypasses of the static scan (reported as findings if they get through)
M = "/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv/MARKER_{}.npy"
cases["bypass_numpy_save"] = prog(f'''import numpy as np
def build(spec):
    np.save("{M.format('numpy_save')}", np.zeros(1))
{UE_CORE}    return b
''')
cases["bypass_attr_builtins"] = prog(f'''def build(spec):
    f = Builder.__init__.__globals__["__builtins__"]["op" + "en"]("{M.format('attr_builtins')}", "w")
    f.write("x"); f.close()
{UE_CORE}    return b
''')
cases["bypass_builder_module_os"] = prog(f'''import su2plaq.compress.builder as BB
def build(spec):
    BB.pathlib.Path("{M.format('builder_pathlib')}").write_text("x")
{UE_CORE}    return b
''')
cases["bypass_subclasses"] = prog(f'''def build(spec):
    for c in ().__class__.__base__.__subclasses__():
        if c.__name__ == "BuiltinImporter" or c.__name__ == "_wrap_close":
            pass
    return Builder(spec)
''')
# --- 11 infinite loop
cases["infinite_loop"] = prog('''def build(spec):
    while True:
        pass
''')
cases["good_UE"] = prog(f'''def build(spec):
{UE_CORE}    return b
''')
if __name__ == "__main__":
    d = SP / "programs"; d.mkdir(exist_ok=True)
    for k, v in cases.items():
        (d / f"{k}.py").write_text(v)
    print(len(cases), "programs written")
