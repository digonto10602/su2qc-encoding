"""Extra: export_certificate for F2, F3, F5 round-2 programs (not requested by the loop) -> expect F2/F5 certified-able (ACCEPT) and F3 n_a (affine pi/2 angles)."""
import sys, json, pathlib, subprocess
from su2plaq.spinnet import loop; loop.install()
from su2plaq.spinnet import lean_export as LE
from su2plaq.compress.spec import default_spec
from su2plaq.encodings.spinnet import SpinNet
root = pathlib.Path(sys.argv[1]); T = root/"results/spinnet/tester/4_6_r2/certs"
exe = root/"lean/.lake/build/bin/su2plaq_cert_spinnet"
for fam in ("F1","F2","F3","F5"):
    ent = json.load(open(root/f"compress/archive/spinnet/entries/r02-{fam}-002.json")); f = root/ent["program_path"]
    ns = {}; exec(compile(f.read_text(), str(f), "exec"), ns)
    qc = ns["build"](default_spec("spinnet","step").with_angles(0.37,0.61)).circuit()
    r = LE.export_certificate(qc, SpinNet(), "step", 0.37, 0.61, 1, T/f"{fam}-r2-export.json")
    if isinstance(r, str): print(fam, "export ->", r[:120]); continue
    p = subprocess.run([str(exe),"check",str(r)],capture_output=True,text=True)
    print(fam, "export ok; checker:", p.stdout.strip().splitlines()[0] if p.stdout.strip() else p.stderr[-200:], "circuit_id", json.load(open(r))["circuit_id"])
