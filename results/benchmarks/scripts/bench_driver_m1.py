"""Driver for the M1 benchmark (tester, reports/benchmarks/002). Output: results/benchmarks/_m1_raw.json (merged by hand into m1.json)."""
import sys, json, subprocess, os, time, tempfile, pathlib
ROOT = "/home/digimonk/Projects/su2qc-encoding"
sys.path.insert(0, ROOT + "/src")
env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="20261104", PYTHONPATH=ROOT + "/src")
W = ROOT + "/results/benchmarks/scripts/bench_worker_m1.py"
R = {"worker": {}, "suites": {}}
WRAP = ("import subprocess,sys,resource,time,json;t=time.perf_counter();p=subprocess.run(sys.argv[1:],capture_output=True,text=True);"
        "print(json.dumps({'rc':p.returncode,'wall':time.perf_counter()-t,'maxrss_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,"
        "'tail':p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-300:]}))")

def run_task(t):
    p = subprocess.run([sys.executable, W, t], cwd=ROOT, env=env, capture_output=True, text=True)
    line = [l for l in p.stdout.splitlines() if l.startswith("RESULT ")]
    if p.returncode or not line:
        print("TASK FAILED", t, p.stderr[-800:], flush=True); return None
    return json.loads(line[0][7:])

plan = [("m1_build", 3), ("eval_UE", 3), ("eval_UB", 3), ("eval_step1", 3), ("eval_step2", 3),
        ("synth_UB", 3), ("synth_step1", 3), ("synth_step2", 3), ("paulo_m1", 1)]
for t, n in plan:
    R["worker"][t] = [r for r in (run_task(t) for _ in range(n)) if r]
    print("done", t, [round(r["rss_mb"]) for r in R["worker"][t]], flush=True)
    json.dump(R, open(ROOT + "/results/benchmarks/_m1_partial.json", "w"), default=str)

def run(cmd, tag, n):
    out = []
    for _ in range(n):
        p = subprocess.run([sys.executable, "-c", WRAP, *cmd], cwd=ROOT, env=env, capture_output=True, text=True)
        out.append(json.loads(p.stdout.strip().splitlines()[-1])); print(tag, out[-1], flush=True)
    return out
scratch = tempfile.mkdtemp(prefix="m1res_", dir=ROOT + "/scratch")
R["suites"]["m1_results_script"] = run([sys.executable, "scripts/m1_results.py", "--out", scratch], "m1_results", 1)
R["suites"]["acceptance_m0_m1"] = run([sys.executable, "-m", "pytest", "-n", "auto", "-q", "tests/acceptance/m0", "tests/acceptance/m1"], "acc", 3)
R["suites"]["unit"] = run([sys.executable, "-m", "pytest", "-n", "auto", "-q", "tests/unit"], "unit", 3)
json.dump(R, open(ROOT + "/results/benchmarks/_m1_raw.json", "w"), default=str)
print("ALL DONE", flush=True)
