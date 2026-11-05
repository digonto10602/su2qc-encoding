"""Driver for the M0 baseline benchmark (tester). Runs every worker task in fresh processes, then the suites.
Output: results/benchmarks/m0-baseline.json"""
import sys, json, subprocess, os, time, resource, statistics as st, platform
ROOT = "/home/digimonk/Projects/su2qc-encoding"
sys.path.insert(0, ROOT + "/src")
env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="20261104")
W = ROOT + "/results/benchmarks/scripts/bench_worker.py"
R = {"worker": {}, "suites": {}}

def run_task(t):
    p = subprocess.run([sys.executable, W, t], cwd=ROOT, env=env, capture_output=True, text=True)
    line = [l for l in p.stdout.splitlines() if l.startswith("RESULT ")]
    if p.returncode or not line:
        print("TASK FAILED", t, p.stderr[-800:]); return None
    return json.loads(line[0][7:])

plan = [("basis", 3), ("ops", 3), ("eval_id_span", 3), ("eval_id_phys", 3), ("eval_ue", 3), ("eval_outer3", 3),
        ("metrics", 3), ("metrics_q", 3), ("metrics_c", 3), ("paulo_eval", 1)]
for t, n in plan:
    R["worker"][t] = [r for r in (run_task(t) for _ in range(n)) if r]
    print("done", t, [round(r["rss_mb"]) for r in R["worker"][t]], flush=True)
    json.dump(R, open(ROOT + "/results/benchmarks/_partial.json", "w"), default=str)

def suite(args, n):
    out = []
    for _ in range(n):
        t0 = time.perf_counter()
        r0 = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        p = subprocess.run([sys.executable, "-c",
            "import subprocess,sys,resource,time,json;t=time.perf_counter();p=subprocess.run(sys.argv[1:],capture_output=True,text=True);"
            "print(json.dumps({'rc':p.returncode,'wall':time.perf_counter()-t,'maxrss_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'tail':p.stdout.strip().splitlines()[-1]}))",
            sys.executable, "-m", "pytest", *args], cwd=ROOT, env=env, capture_output=True, text=True)
        out.append(json.loads(p.stdout.strip().splitlines()[-1])); print(args, out[-1], flush=True)
    return out
R["suites"]["acceptance_m0"] = suite(["-n", "auto", "-q", "tests/acceptance/m0"], 3)
R["suites"]["unit"] = suite(["-n", "auto", "-q", "tests/unit"], 3)
json.dump(R, open(ROOT + "/results/benchmarks/_raw.json", "w"), default=str)
print("ALL DONE")
