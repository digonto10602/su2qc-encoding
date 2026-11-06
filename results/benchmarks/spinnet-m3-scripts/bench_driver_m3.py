"""M3 benchmark driver (tester, reports/benchmarks/100).  Everything under taskset -c 0-9, OMP/OPENBLAS/MKL=1.
usage: python bench_driver_m3.py <scratch_dir>   -> writes <scratch_dir>/raw.json"""
import sys, json, subprocess, os, time, pathlib, statistics
ROOT = str(pathlib.Path(__file__).resolve().parents[3])
W = ROOT + "/results/benchmarks/scripts/bench_worker_m3.py"
SCR = pathlib.Path(sys.argv[1]); SCR.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="20261104", PYTHONPATH=ROOT + "/src")
TS = ["taskset", "-c", "0-9"]
WRAP = ("import subprocess,sys,resource,time,json;t=time.perf_counter();p=subprocess.run(sys.argv[1:],capture_output=True,text=True);"
        "print(json.dumps({'rc':p.returncode,'wall':time.perf_counter()-t,'maxrss_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,"
        "'tail':(p.stdout+p.stderr)[-600:]}))")
def load(): return open("/proc/loadavg").read().split()[:3]
raw = {"tasks": {}, "cmds": {}, "load_before": load(), "t0": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
plan = [("enc_build", 5), ("eval_UB_outer_physical", 3), ("eval_UB_auto", 3), ("eval_UE", 3), ("eval_step1", 3), ("eval_step2", 3),
        ("eval_paulo15", 3), ("eval_pairs9", 3), ("eval_flags4", 3), ("eval_twelve_UB", 3), ("synth_UB", 3), ("synth_step1", 3)]
for task, n in plan:
    raw["tasks"][task] = []
    for i in range(n):
        p = subprocess.run(TS + [sys.executable, W, task], cwd=ROOT, env=env, capture_output=True, text=True)
        line = [l for l in p.stdout.splitlines() if l.startswith("RESULT ")]
        if not line: raise SystemExit(f"{task} failed: {p.stderr[-800:]}")
        raw["tasks"][task].append(json.loads(line[0][7:]))
    print(task, "done", flush=True)
def wrapped(name, cmd, n):
    raw["cmds"][name] = {"cmd": " ".join(cmd), "runs": []}
    for i in range(n):
        p = subprocess.run([sys.executable, "-c", WRAP] + TS + cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        r = json.loads(p.stdout.strip().splitlines()[-1]); r["load_before"] = load(); raw["cmds"][name]["runs"].append(r)
        print(name, i, round(r["wall"], 2), r["maxrss_kb"] // 1024, "MB rc", r["rc"], r["tail"][-120:].replace("\n", " | "), flush=True)
    json.dump(raw, open(SCR / "raw.json", "w"), indent=1)
PY = [sys.executable]
wrapped("m3_results", PY + ["scripts/m3_results.py", "--out", str(SCR / "m3_results_out")], 3)
wrapped("pytest_unit", PY + ["-m", "pytest", "-n", "10", "-q", "tests/unit"], 3)
wrapped("pytest_m0_m1_m3", PY + ["-m", "pytest", "-n", "10", "-q", "tests/acceptance/m0", "tests/acceptance/m1", "tests/acceptance/m3"], 3)
raw["t1"] = time.strftime("%Y-%m-%dT%H:%M:%S%z"); raw["load_after"] = load()
json.dump(raw, open(SCR / "raw.json", "w"), indent=1)
