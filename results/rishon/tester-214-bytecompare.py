"""Tester 214: rebuild the five committed M5 circuits with the step-6.0 code (ladder default and ladder='ccx') and compare qasm3/qpy bytes
with results/rishon/*.{qasm3,qpy}.  Run: PYTHONPATH=src python results/rishon/tester-214-bytecompare.py"""
import io, json, pathlib, subprocess
from qiskit import qasm3, qpy
from su2plaq.circuits import rishon as C
from su2plaq.encodings.rishon import RISHON_NOMINAL
A, B = RISHON_NOMINAL
R = pathlib.Path("results/rishon")
cases = {
 "UE": lambda **k: C.build_UE(A),
 "UE_outer_row": lambda **k: C.build_UE(A, with_outer=True, include_outer_electric=True),
 "UB": lambda **k: C.build_UB(B, **k),
 "step": lambda **k: C.build_step(A, B, 1, **k),
 "step_order2": lambda **k: C.build_step(A, B, 2, **k),
}
out = {"commit": subprocess.check_output(["git","rev-parse","--short","HEAD"], text=True).strip(), "rows": []}
for name, f in cases.items():
    for label, kw in (("default", {}), ("ladder=ccx", {"ladder": "ccx"})):
        if name.startswith("UE") and kw: continue
        qc = f(**kw)
        buf = io.BytesIO(); qpy.dump(qc, buf)
        q_ok = buf.getvalue() == (R/f"{name}.qpy").read_bytes()
        a_ok = qasm3.dumps(qc) == (R/f"{name}.qasm3").read_text()
        out["rows"].append({"circuit": name, "variant": label, "qpy_equal": q_ok, "qasm3_equal": a_ok, "gates": len(qc.data)})
        print(name, label, "qpy", q_ok, "qasm3", a_ok, len(qc.data))
json.dump(out, open(R/"tester-214-bytecompare.json","w"), indent=1)
