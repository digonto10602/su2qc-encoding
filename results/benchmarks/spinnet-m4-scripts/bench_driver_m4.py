"""M4 / M7 benchmark driver (tester, reports/benchmarks/301 and 302).  Everything pinned to cores 14-19 (single-process tasks on core 14).
usage: python bench_driver_m4.py <phase> <scratch_dir>
phases: tasksA  tasksB  round  scripts  suites_m4  suites_m7  suites_unit
Writes <scratch_dir>/raw_<phase>.json (all runs, load average before each, peak RSS of the largest child process)."""
import sys, json, subprocess, os, time, pathlib, shutil
ROOT = str(pathlib.Path(__file__).resolve().parents[3])
W = ROOT + "/results/benchmarks/spinnet-m4-scripts/bench_worker_m4.py"
phase = sys.argv[1]; SCR = pathlib.Path(sys.argv[2]).resolve(); SCR.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="20261104", PYTHONPATH=ROOT + "/src")
WRAP = ("import subprocess,sys,resource,time,json;t=time.perf_counter();p=subprocess.run(sys.argv[1:],capture_output=True,text=True);"
        "print(json.dumps({'rc':p.returncode,'wall':time.perf_counter()-t,'maxrss_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,"
        "'tail':(p.stdout+p.stderr)[-500:]}))")
def load(): return open("/proc/loadavg").read().split()[:3]
raw = {"phase": phase, "t0": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "load_before": load(), "tasks": {}, "cmds": {}}
def save(): json.dump(raw, open(SCR / f"raw_{phase}.json", "w"), indent=1)

def tasks(plan):
    for task, n in plan:
        raw["tasks"][task] = []
        for i in range(n):
            ld = load()
            p = subprocess.run(["taskset", "-c", "14", sys.executable, W, task, str(SCR)], cwd=ROOT, env=env, capture_output=True, text=True)
            line = [l for l in p.stdout.splitlines() if l.startswith("RESULT ")]
            if not line: raise SystemExit(f"{task} failed: {p.stderr[-800:]}")
            r = json.loads(line[0][7:]); r["load_before"] = ld; raw["tasks"][task].append(r)
        print(task, "done", flush=True); save()

def wrapped(name, cmd, n, cpus="14-19", pre=None):
    raw["cmds"][name] = {"cmd": " ".join(cmd), "runs": []}
    for i in range(n):
        if pre: pre(i)
        ld = load()
        p = subprocess.run([sys.executable, "-c", WRAP, "taskset", "-c", cpus] + cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        r = json.loads(p.stdout.strip().splitlines()[-1]); r["load_before"] = ld; raw["cmds"][name]["runs"].append(r)
        print(name, i, round(r["wall"], 2), r["maxrss_kb"] // 1024, "MB rc", r["rc"], r["tail"][-150:].replace("\n", " | "), flush=True); save()

PY = [sys.executable]
SAFE = [ROOT + "/tools/pytest-safe", "-n", "6", "-q", "-p", "no:cacheprovider"]
CAP = [ROOT + "/tools/run-capped"]
if phase == "tasksA":
    tasks([("enc_build", 5), ("ops", 3), ("eval_UB_auto", 3), ("eval_UE", 3), ("eval_step1", 3), ("eval_step2", 3), ("eval_pairs9", 3),
           ("eval_flags4", 3), ("eval_headline", 3), ("eval_UB_outer_physical", 3), ("eval_paulo15", 3), ("eval_twelve_UB", 3),
           ("synth_UB", 3), ("synth_step1", 3), ("synth_headline", 3), ("lean_cert_headline", 3)])
elif phase == "tasksB":
    tasks([("lsh_enc_build", 5), ("lsh_eval_UE", 3), ("lsh_eval_UB", 3), ("lsh_eval_step1", 3), ("lsh_eval_step2", 3),
           ("lsh_eval_wrap_flags4", 3), ("lsh_eval_wrap_pairs9", 3), ("lsh_eval_wrap_general7", 3),
           ("lsh_synth_UE", 3), ("lsh_synth_UB", 3), ("lsh_synth_step1", 3), ("lsh_lean_cert", 3)])
elif phase == "round":
    MK = SCR / "make_root.sh"
    def mk(keepgs, tag):
        def pre(i):
            subprocess.run(["bash", str(MK), str(SCR / f"root_{tag}"), "spinnet", "5", str(keepgs)], check=True, capture_output=True)
        return pre
    for tag, keepgs in (("warm", 1), ("cold", 0)):
        wrapped(f"round5_{tag}_gridsynth_cache", CAP + PY + ["-m", "su2plaq.spinnet.loop", "round", "--round", "5", "--evaluate", "--no-lean",
                "--root", str(SCR / f"root_{tag}")], 3, pre=mk(keepgs, tag))
    cand = "compress/programs/spinnet/F1/002-dimer-linear-corner-walk.py"
    wrapped("candidate_headline_full", CAP + PY + ["-m", "su2plaq.spinnet.loop", "candidate", cand, "--full", "--json", str(SCR / "cand_headline.json")], 3)
    for prog in ("F1/005-nor3-direct-pair", "F2/005-angle-linear-design-interpreter", "F3/005-angle-linear-walk"):
        wrapped("candidate_" + prog.replace("/", "_"), CAP + PY + ["-m", "su2plaq.spinnet.loop", "candidate", f"compress/programs/spinnet/{prog}.py",
                "--full", "--json", str(SCR / f"cand_{prog.replace('/', '_')}.json")], 3)
elif phase == "scripts":
    wrapped("m3_results", CAP + PY + ["scripts/m3_results.py", "--out", str(SCR / "m3_results_out")], 3)
    def pre4(i):
        subprocess.run(["bash", str(SCR / "make_root.sh"), str(SCR / "root_m4"), "spinnet", "99", "1"], check=True, capture_output=True)
    wrapped("m4_results", CAP + PY + ["scripts/m4_results.py", "--root", str(SCR / "root_m4"), "--out", str(SCR / "m4_results_out")], 3, pre=pre4)
    wrapped("m7_results", CAP + PY + ["scripts/m7_results.py", "--out", str(SCR / "m7_results_out")], 3)
elif phase == "suites_m4":
    wrapped("pytest_m0_m1", SAFE + ["tests/acceptance/m0", "tests/acceptance/m1"], 3)
    wrapped("pytest_m3_m3x_m4", SAFE + ["tests/acceptance/m3", "tests/acceptance/m3x", "tests/acceptance/m4"], 3)
elif phase == "suites_m7":
    wrapped("pytest_m7", SAFE + ["tests/acceptance/m7"], 3)
elif phase == "suites_unit":
    wrapped("pytest_unit", SAFE + ["tests/unit"], 3)
raw["t1"] = time.strftime("%Y-%m-%dT%H:%M:%S%z"); raw["load_after"] = load(); save()
