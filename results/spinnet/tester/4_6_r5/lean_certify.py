"""Tester 118: lean_export.certify (the loop's path) on the three r05 programs at the nominal pair and at (1.70,1.00), cert dir = tester dir."""
import sys, json, pathlib
from su2plaq.spinnet import loop; loop.install()
from su2plaq.spinnet import lean_export as LE
from su2plaq.compress.spec import default_spec
from su2plaq.encodings.spinnet import SpinNet
root = pathlib.Path(sys.argv[1]); out = {}
for eid in sys.argv[2:]:
    ent = json.load(open(root/f"compress/archive/spinnet/entries/{eid}.json")); ns = {}; f = root/ent["program_path"]; exec(compile(f.read_text(), str(f), "exec"), ns)
    for (a, b) in ((0.37, 0.61), (1.70, 1.00)):
        qc = ns["build"](default_spec("spinnet", "step").with_angles(a, b)).circuit()
        r = LE.certify(qc, SpinNet(), "step", a, b, 1, out_dir=root/"results/spinnet/tester/4_6_r5/certs_certify")
        out[f"{eid}@{a},{b}"] = {k: r[k] for k in ("status", "reason", "seconds", "check_seconds", "checker_sha256") if k in r}; print(eid, a, b, out[f"{eid}@{a},{b}"], flush=True)
json.dump(out, open(root/"results/spinnet/tester/4_6_r5/lean_certify.json", "w"), indent=1)
