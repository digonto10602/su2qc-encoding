"""Collect raw benchmark records into results/benchmarks/rishon-m5.json (median [min,max] per quantity) + provenance."""
import json, os, re, statistics as st, subprocess, sys, glob, xml.etree.ElementTree as ET
from collections import defaultdict
ROOT = os.path.expanduser("~/Projects/su2qc-rishon"); RAW = ROOT + "/results/benchmarks/rishon-m5-raw"
def stat(xs):
    xs = sorted(xs); return {"median": st.median(xs), "min": xs[0], "max": xs[-1], "n": len(xs), "spread_pct": 100 * (xs[-1] - xs[0]) / st.median(xs) if st.median(xs) else None}
def load(p):
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip(),
       "git_dirty_src": bool(subprocess.check_output(["git", "status", "--porcelain", "src", "tests", "scripts", "prompts"], cwd=ROOT, text=True).strip()),
       "machine": "SupremeCommander: i7-12700KF (8P+4E, 20 threads), 32 GB, RTX 3070 idle; taskset -c 10-19 = P-core threads 10-15 + E-core threads 16-19; 1 BLAS/OMP thread",
       "env": "conda su2qc-coding, python 3.12.16, OMP/OPENBLAS/MKL_NUM_THREADS=1, PYTHONHASHSEED=20261104", "seeds": {"gauss_sample": 20261104, "ct_compile": 12345}}
for name, f in (("rishon", "phase1.jsonl"), ("twelve_same_machine", "phase2-twelve.jsonl")):
    g = defaultdict(list)
    for r in load(f"{RAW}/{f}"): g[r["task"]].append(r)
    blk = {}
    for t, rs in g.items():
        d = {"n_processes": len(rs), "process_wall_s": stat([r["wall_process_s"] for r in rs]), "peak_rss_mb": stat([r["rss_mb"] for r in rs]), "times_first_call_s": {}, "times_later_calls_s": {}}
        for n in rs[0]["times"]:
            d["times_first_call_s"][n] = stat([r["times"][n][0] for r in rs])
            later = [v for r in rs for v in r["times"][n][1:]]
            if later: d["times_later_calls_s"][n] = stat(later)
        d["cpus_start_end"] = [(r.get("cpu_start"), r.get("cpu_end")) for r in rs]
        d["out_rep0"] = {k: v for k, v in rs[0]["out"].items() if k != "t_table"} if isinstance(rs[0]["out"], dict) else rs[0]["out"]
        blk[t] = d
    out[name] = blk
out["pytest"] = {}
for p in sorted(glob.glob(RAW + "/pytest_m5_*.xml")):
    root = ET.parse(p).getroot(); ts = root if root.tag == "testsuite" else root.find("testsuite")
    key = os.path.basename(p)[:-4]
    tm = open(p[:-4] + ".time").read()
    wall = re.search(r"Elapsed \(wall clock\) time.*: (.*)", tm).group(1); rss = int(re.search(r"Maximum resident set size \(kbytes\): (\d+)", tm).group(1))
    out["pytest"][key] = {"tests": int(ts.get("tests")), "failures": int(ts.get("failures")), "errors": int(ts.get("errors")), "skipped": int(ts.get("skipped")),
                          "pytest_time_s": float(ts.get("time")), "time_v_wall": wall, "max_single_proc_rss_mb": rss / 1024,
                          "per_test_s": {tc.get("classname").split(".")[-1] + "::" + tc.get("name"): float(tc.get("time")) for tc in ts.iter("testcase")}}
rs = [l.split() for l in open(RAW + "/pytest-rss.log")] if os.path.exists(RAW + "/pytest-rss.log") else []
if rs: out["pytest_summed_python_rss_mb_peak"] = max(float(x[1]) for x in rs)
if os.path.exists(RAW + "/lean.txt"): out["lean_lines"] = open(RAW + "/lean.txt").read().splitlines()
if os.path.exists(RAW + "/l3.out"):
    for l in open(RAW + "/l3.out"):
        if l.startswith("RESULT "): out["l3"] = json.loads(l[7:])
mon = open(RAW + "/monitor.log").read().splitlines()
out["monitor_samples"] = len(mon)
json.dump(out, open(ROOT + "/results/benchmarks/rishon-m5.json", "w"), indent=1, default=str)
print("written", len(json.dumps(out)))
