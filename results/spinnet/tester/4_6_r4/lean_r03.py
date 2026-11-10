"""Tester 115 (c): export_certificate for the three round-3 programs (expect n_a for F1/F2 pi/4 shifts and F3 pi/2), and
best-certified scan over the whole archive."""
import sys, json, pathlib, subprocess
from su2plaq.spinnet import loop; loop.install()
from su2plaq.spinnet import lean_export as LE
from su2plaq.compress.spec import default_spec
from su2plaq.encodings.spinnet import SpinNet
root = pathlib.Path(sys.argv[1]); T = root/"results/spinnet/tester/4_6_r4/certs"
exe = root/"lean/.lake/build/bin/su2plaq_cert_spinnet"
for eid in ("r04-F1-004","r04-F3-004"):
    ent = json.load(open(root/f"compress/archive/spinnet/entries/{eid}.json")); f = root/ent["program_path"]
    ns = {}; exec(compile(f.read_text(), str(f), "exec"), ns)
    qc = ns["build"](default_spec("spinnet","step").with_angles(0.37,0.61)).circuit()
    r = LE.export_certificate(qc, SpinNet(), "step", 0.37, 0.61, 1, T/f"{eid}-export.json")
    if isinstance(r, str) and not r.endswith(".json"): print(eid, "export ->", r[:160], "| archive lean:", ent["lean"] and (ent["lean"]["status"], ent["lean"]["reason"])); continue
    print(eid, "exported?", r)
import glob
rows = []
for fp in sorted(glob.glob(str(root/"compress/archive/spinnet/entries/*.json"))):
    d = json.load(open(fp))
    if d["valid"]: rows.append((tuple(d["key"]), d["id"], (d.get("lean") or {}).get("status")))
rows.sort(); print("valid entries by key, lean status:")
for r in rows[:8]: print("  ", r)
cert = [r for r in rows if r[2] == "certified"]
print("certified entries:", cert)
print("best certified:", cert[0] if cert else None)
