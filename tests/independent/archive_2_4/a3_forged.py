"""N6 and forged worker outputs (tester, M2 step 2.4). Every case must come back as a ProgramResult (valid False), never raise."""
import json, pathlib, sys, tempfile
sys.path.insert(0, "src")
from su2plaq.compress import evaluate as E
from su2plaq.compress.spec import default_spec

HDR = '"""SUMMARY: forge.\n"""\nFAMILY = "F0"\nPARENT = None\n\nfrom su2plaq.compress.builder import Builder\nimport su2plaq.compress.builder as BB\n\n\n'
GOODBODY = '''    b = Builder(spec)
    d = b.reg("d")
    for l in range(4):
        b.p(-0.75 * spec.alpha, d[3 * l + 2])
    return b
'''
PRE = '''def build(spec):
    out = BB.pathlib.sys.argv[4]; meta = BB.pathlib.sys.argv[5]; P = BB.pathlib.Path
    os_ = BB.pathlib.os
'''
cases = {
 "n6_meta_forged_exit0": PRE + '    P(meta).write_text(\'{"discoveries": [[],[],[]]}\'); os_._exit(0)\n',
 "meta_forged_exit0_trial_count": PRE + '    P(meta).write_text(\'{"discoveries": [[]]}\'); os_._exit(0)\n',
 "meta_garbage_exit0": PRE + '    P(meta).write_text("\\x00not json"); os_._exit(0)\n',
 "meta_list_exit0": PRE + '    P(meta).write_text("[1,2]"); os_._exit(0)\n',
 "meta_discoveries_wrong_type": PRE + '    P(meta).write_text(\'{"discoveries": {"a": 1}}\'); os_._exit(0)\n',
 "meta_error_key_contract": PRE + '    P(meta).write_text(\'{"error": "x", "kind": "contract"}\'); os_._exit(0)\n',
 "meta_error_huge": PRE + '    P(meta).write_text(json_dump := \'{"error": "\' + "A" * 5_000_000 + \'"}\'); os_._exit(0)\n',
 "qpy_garbage_meta_ok": PRE + '    P(out).write_bytes(b"QPY\\x00junk" * 100); P(meta).write_text(\'{"discoveries": [[],[],[]]}\'); os_._exit(0)\n',
 "qpy_empty_file": PRE + '    P(out).write_bytes(b""); P(meta).write_text(\'{"discoveries": [[],[],[]]}\'); os_._exit(0)\n',
 "qpy_huge_discoveries_strings": PRE + '    P(meta).write_text(\'{"discoveries": [["\' + "x"*10**6 + \'"]]}\'); os_._exit(0)\n',
 "no_files_exit0": PRE + '    os_._exit(0)\n',
 "no_files_exit3": PRE + '    os_._exit(3)\n',
 "meta_symlink_dir": PRE + '    P(meta).unlink(missing_ok=True); os_._exit(0)\n',
 "legit_then_overwrite_meta_with_forged_error": '''def build(spec):
    b = Builder(spec)
    d = b.reg("d")
    for l in range(4):
        b.p(-0.75 * spec.alpha, d[3 * l + 2])
    BB.pathlib.Path(BB.pathlib.sys.argv[5]).write_text('{"error":"x"}')
    return b
''',
}
# circuit forged: write a QPY with a forbidden native gate (mcx 4 controls) and a unitary; real Qiskit objects
cases["qpy_forged_native_mcx_circuit"] = PRE + '''    import qiskit.qpy as q
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import MCXGate
    n = len(spec.alt_angles) + 1
    qcs = []
    for _ in range(n):
        c = QuantumCircuit(40); c.append(MCXGate(4), [0, 1, 2, 3, 4]); qcs.append(c)
    fh = P(out).open("wb"); q.dump(qcs, fh); fh.close()
    P(meta).write_text(json_ := '{"discoveries": [[],[],[]]}'); os_._exit(0)
'''
cases["qpy_forged_identity_circuits"] = PRE + '''    import qiskit.qpy as q
    from qiskit import QuantumCircuit
    qcs = [QuantumCircuit(40) for _ in range(len(spec.alt_angles) + 1)]
    fh = P(out).open("wb"); q.dump(qcs, fh); fh.close()
    P(meta).write_text('{"discoveries": [[],[],[]]}'); os_._exit(0)
'''

res = {}
ONLY = set(sys.argv[1:]) or set(cases)
spec = default_spec("twelve", "UE")
with tempfile.TemporaryDirectory() as td:
    for name, body in cases.items():
        if name not in ONLY: continue
        f = pathlib.Path(td) / f"{name}.py"; f.write_text(HDR + (body if body.startswith("def build") else body))
        for mode in ("trial", "full"):
            try:
                r = E.evaluate_program(f, spec, mode)
                res[f"{name}/{mode}"] = dict(valid=r.valid, reason=r.reason, verdict_none=r.verdict is None, msg=r.message[:90].replace("\n", " "), disc=len(r.discoveries))
            except BaseException as ex:
                res[f"{name}/{mode}"] = dict(RAISED=f"{type(ex).__name__}: {str(ex)[:100]}")
bad = {k: v for k, v in res.items() if "RAISED" in v or v["valid"] or v["reason"] not in ("build_error", "contract", "error", "skeleton", "dirty_ancilla", "wrong_gate", "gate") and False}
for k, v in res.items(): print(k, v)
print("RAISED:", [k for k, v in res.items() if "RAISED" in v]); print("VALID:", [k for k, v in res.items() if v.get("valid")])
json.dump(res, open("results/tester_m2_step2_4_recheck_forged.json", "w"), indent=1)
