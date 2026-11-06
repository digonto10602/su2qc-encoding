"""Time the L3 certificate path (export -> Lean file -> native check) - same calls as tests/acceptance/m5/test_rishon_lean.py::L3.
Writes into a scratch dir given as argv[1]; prints RESULT json."""
import sys, os, json, time, pathlib, resource
ROOT = os.path.expanduser("~/Projects/su2qc-rishon")
sys.path.insert(0, ROOT + "/src"); sys.path.insert(0, ROOT)
from su2plaq.rishon import lean_export as LE
tmp = pathlib.Path(sys.argv[1]); tmp.mkdir(parents=True, exist_ok=True)
T, OUT = {}, {}
def timed(n, f):
    t0 = time.perf_counter(); r = f(); T.setdefault(n, []).append(time.perf_counter() - t0); return r
cert = timed("export_hb_certificate", lambda: LE.export_hb_certificate(tmp / "hb-cert.json"))
c = json.loads(pathlib.Path(cert).read_text())
OUT["n_pairs"], OUT["n_codes"] = len(c["pairs"]), c["n_codes"]
lean_file = timed("write_hb_lean", lambda: LE.write_hb_lean(cert, tmp / "rishon-hb-structure.lean"))
OUT["lean_file_bytes"] = os.path.getsize(lean_file)
timed("check_hb_python(exact ints)", lambda: LE.check_hb_python(c))
for i in range(3):
    r = timed("check_hb(native Lean, certified)", lambda: LE.check_hb(lean_file, timeout=900))
    OUT["status_good"] = r["status"]; OUT["axioms_good"] = sorted(r["axioms"])
i = next(i for i, p in enumerate(c["pairs"]) if p["kappa"] in ("2", [2, 0], "2/1"))
c["pairs"][i]["kappa"] = "1" if isinstance(c["pairs"][i]["kappa"], str) else [1, 0]
(tmp / "hb-bad.json").write_text(json.dumps(c))
bad = LE.write_hb_lean(tmp / "hb-bad.json", tmp / "rishon-hb-bad.lean")
for i in range(3):
    r2 = timed("check_hb(tampered kappa 2->1, rejected)", lambda: LE.check_hb(bad, timeout=900))
    OUT["status_bad"] = r2["status"]
print("RESULT " + json.dumps({"times": T, "rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, "out": OUT}, default=str))
