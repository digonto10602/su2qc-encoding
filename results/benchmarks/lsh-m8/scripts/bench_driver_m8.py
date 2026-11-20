"""LSH M8 benchmark driver (tester, reports/benchmarks/306).  usage: python bench_driver_m8.py <phase> <scratch_dir>
phases: evalprog robust seed certify m7tasks scripts suite_m7 suite_m8 suite_unit
All single-process tasks pinned with `taskset -c 0` (P-core 0, SMT sibling cpu 1 idle); scripts/suites with `taskset -c 0-8` (suite_m8: 0-7).
Writes <scratch_dir>/raw_<phase>.json: every run, load average before and after it, wall, peak RSS of the largest child."""
import sys, json, subprocess, os, time, pathlib, shutil, tempfile
ROOT = str(pathlib.Path(__file__).resolve().parents[4])
HERE = pathlib.Path(__file__).resolve().parent
phase = sys.argv[1]; SCR = pathlib.Path(sys.argv[2]).resolve(); SCR.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="20261104", PYTHONPATH=ROOT + "/src", BENCH_SCR=str(SCR))
WRAP = ("import subprocess,sys,resource,time,json,os;t=time.perf_counter();p=subprocess.run(sys.argv[1:],capture_output=True,text=True);"
        "open(os.environ['BENCH_LOG'],'w').write(p.stdout+p.stderr) if os.environ.get('BENCH_LOG') else None;print(json.dumps({'rc':p.returncode,'wall':time.perf_counter()-t,'maxrss_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,"
        "'tail':(p.stdout+p.stderr)[-600:]}))")
def load(): return open("/proc/loadavg").read().split()[:3]
def commit(): return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
raw = {"phase": phase, "commit": commit(), "t0": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "load_before": load(), "host": os.uname().nodename,
       "env": {k: env[k] for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONHASHSEED")}, "runs": {}}
def save(): json.dump(raw, open(SCR / f"raw_{phase}.json", "w"), indent=1)

def worker(name, args, n, cpu="0", script="w_eval.py", extra_env=None, label=None):
    """n fresh processes of a RESULT-printing worker."""
    raw["runs"].setdefault(name, {"cmd": f"taskset -c {cpu} python {script} " + " ".join(args), "runs": []})
    for i in range(n):
        ld = load()
        e = dict(env, **(extra_env or {}))
        p = subprocess.run(["taskset", "-c", cpu, sys.executable, str(HERE / script)] + args, cwd=ROOT, env=e, capture_output=True, text=True)
        line = [l for l in p.stdout.splitlines() if l.startswith("RESULT ")]
        if not line: raise SystemExit(f"{name} failed: {p.stderr[-800:]}")
        r = json.loads(line[0][7:]); r["load_before"] = ld; r["load_after"] = load(); raw["runs"][name]["runs"].append(r)
    print(name, "done", flush=True); save()

def wrapped(name, cmd, n, cpus="0-8", pre=None, post=None, extra_env=None):
    raw["runs"][name] = {"cmd": f"taskset -c {cpus} " + " ".join(cmd), "runs": []}
    for i in range(n):
        ctx = pre(i) if pre else None
        ld = load()
        e = dict(env, **(extra_env or {}))
        run_cmd = ctx if ctx is not None else cmd
        e2 = dict(e, BENCH_LOG=str(SCR / f"log_{name}_{i}.txt"))
        p = subprocess.run([sys.executable, "-c", WRAP, "taskset", "-c", cpus] + run_cmd, cwd=ROOT, env=e2, capture_output=True, text=True)
        r = json.loads(p.stdout.strip().splitlines()[-1]); r["load_before"] = ld; r["load_after"] = load()
        if post: r["post"] = post(i)
        raw["runs"][name]["runs"].append(r)
        print(name, i, round(r["wall"], 2), r["maxrss_kb"] // 1024, "MB rc", r["rc"], r["tail"][-120:].replace("\n", " | "), flush=True); save()


def make_lsh_root(tag, i, with_certs=False, with_robust=True):
    """scratch copy of the LSH loop state (archive, programs, attempts, specs, lean hook dir, results/compress/lsh [+ robust cache])"""
    d = SCR / f"root_{tag}_{i}_{int(time.time())}"; d.mkdir(parents=True)
    for sub in ("archive", "programs", "attempts", "specs", "discoveries"):
        src = pathlib.Path(ROOT) / "compress" / sub
        if src.exists(): shutil.copytree(src, d / "compress" / sub, ignore=shutil.ignore_patterns("__pycache__"))
    (d / "results" / "compress").mkdir(parents=True)
    shutil.copytree(pathlib.Path(ROOT) / "results/compress/lsh", d / "results/compress/lsh")
    if not with_robust: (d / "results/compress/lsh/robust.json").unlink()
    if with_certs: shutil.copytree(pathlib.Path(ROOT) / "results/lsh/certs", d / "results/lsh/certs")
    return d

PY = [sys.executable]
CAP = [ROOT + "/tools/run-capped"]
HEAD_P = "compress/programs/lsh/F3/005-alpha-early-walk22.py"
SEED_P = "compress/programs/lsh/seed/005-wrap_sn_headline.py"
GEN_P = "compress/programs/lsh/seed/000-general.py"

if phase == "evalprog":
    for tag, p in (("headline_F3_005", HEAD_P), ("seed005_wrap_sn_headline", SEED_P), ("seed000_general", GEN_P)):
        worker(f"eval_{tag}_warm", ["eval", p, "5"], 5)
        worker(f"eval_{tag}_cold", ["eval", p, "3", "cold"], 5)
elif phase == "robust":
    worker("robust_headline_warm", ["robust", HEAD_P, "5"], 5)
    worker("robust_headline_cold", ["robust", HEAD_P, "2", "cold"], 5)
    worker("robust_seed005_warm", ["robust", SEED_P, "5"], 3)
    roots = []
    def pre_h(i):
        d = make_lsh_root("headline_refresh", i, with_robust=False); roots.append(d)
        return CAP + PY + ["-m", "su2plaq.lsh.loop", "headline", "--refresh", "--root", str(d)]
    def post_h(i):
        h = json.loads(open(SCR / f"log_headline_refresh_all_entries_{i}.txt").read())
        return {"id": h["id"], "robust_key": h["robust_key"], "n_ranked": len(h["ranking"]), "n_unrankable": len(h["unrankable"])}
    wrapped("headline_refresh_all_entries", [], 3, pre=pre_h, post=post_h)
elif phase == "certify":
    import filecmp
    roots = []
    def pre_c(i):
        d = make_lsh_root("certify", i); roots.append(d); (d / "lean" / "certs").mkdir(parents=True)
        return CAP + PY + ["-m", "su2plaq.lsh.loop", "certify-headline", "--root", str(d)]
    def post_c(i):
        d = roots[-1]; res = json.loads(open(SCR / f"log_certify_headline_cli_{i}.txt").read())
        lh = res["lean_headline"]; cp = pathlib.Path(lh["cert_path"]) if lh.get("cert_path") else None
        out = {"headline": res["headline"], "status": lh.get("status"), "seconds": lh.get("seconds"), "check_seconds": lh.get("check_seconds"),
               "checker_sha256": lh.get("checker_sha256"), "git_dirty": res.get("git_dirty")}
        if cp is not None:
            cp = cp if cp.is_absolute() else d / cp
            com = pathlib.Path(ROOT) / "results/lsh/certs" / cp.name
            out["cert_name"] = cp.name; out["committed_exists"] = com.exists()
            if com.exists():
                a, b = json.loads(com.read_text()), json.loads(cp.read_text())
                out["bytes_identical"] = com.read_bytes() == cp.read_bytes()
                out["fields_differing"] = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        th = d / "lean/certs/lsh-best-step.lean"; tc = pathlib.Path(ROOT) / "lean/certs/lsh-best-step.lean"
        out["theorem_file_identical"] = th.exists() and tc.exists() and th.read_bytes() == tc.read_bytes()
        return out
    wrapped("certify_headline_cli", [], 5, pre=pre_c, post=post_c)
elif phase == "seed":
    def mk(tag):
        def pre(i):
            d = SCR / f"root_{tag}_{i}_{int(time.time())}"; d.mkdir(parents=True)
            return d
        return pre
    for tag, extra in (("seed_lean_warm", []), ("seed_nolean_warm", ["--no-lean"])):
        roots = []
        def pre(i, tag=tag, extra=extra):
            d = SCR / f"root_{tag}_{i}_{int(time.time())}"; d.mkdir(parents=True); roots.append(d)
            return CAP + PY + ["-m", "su2plaq.lsh.loop", "seed", "--root", str(d)] + extra
        def post(i):
            d = roots[-1]; fs = [p for p in d.rglob("*") if p.is_file()]
            r0 = json.loads((d / "results/compress/lsh/round-000.json").read_text())
            return {"n_files": len(fs), "best_key": r0.get("best_key"), "n_valid": r0.get("n_valid")}
        wrapped(tag, [], 5, pre=pre, post=post)
    roots = []
    def pre_c(i):
        d = SCR / f"root_seed_cold_{i}_{int(time.time())}"; d.mkdir(parents=True); roots.append(d)
        gs = SCR / f"gs_seedcold_{i}_{int(time.time())}"
        return CAP + PY + [str(HERE / "seed_cold.py"), str(d), str(gs)]
    wrapped("seed_lean_cold_gridsynth", [], 3, pre=pre_c)
elif phase == "m7tasks":
    m7src = ROOT + "/scratch/bench-m8/m7tree/src"   # `git archive milestone-7 src | tar -x -C scratch/bench-m8/m7tree`
    assert (pathlib.Path(m7src) / "su2plaq" / "__init__.py").exists(), m7src
    tasks = ["lsh_enc_build", "lsh_eval_UE", "lsh_eval_UB", "lsh_eval_step1", "lsh_eval_step2", "lsh_eval_wrap_flags4", "lsh_eval_wrap_pairs9",
             "lsh_eval_wrap_general7", "lsh_synth_UE", "lsh_synth_UB", "lsh_synth_step1"]
    for task in tasks:               # interleave HEAD and milestone-7 source, 5 fresh processes each
        for i in range(5):
            for tag, src in (("head", ROOT + "/src"), ("m7src", m7src)):
                name = f"{task}@{tag}"
                raw["runs"].setdefault(name, {"cmd": f"BENCH_SRC={src} taskset -c 0 python bench_worker_lsh.py {task}", "runs": []})
                ld = load()
                p = subprocess.run(["taskset", "-c", "0", sys.executable, str(HERE / "bench_worker_lsh.py"), task, str(SCR)], cwd=ROOT,
                                   env=dict(env, BENCH_SRC=src), capture_output=True, text=True)
                line = [l for l in p.stdout.splitlines() if l.startswith("RESULT ")]
                if not line: raise SystemExit(f"{name} failed: {p.stderr[-800:]}")
                r = json.loads(line[0][7:]); r["load_before"] = ld; r["load_after"] = load(); raw["runs"][name]["runs"].append(r)
        print(task, "done", flush=True); save()
    for i in range(5):               # certificate task (HEAD only: the milestone-7 tree has no compiled checker)
        pass
    worker("lsh_lean_cert@head", ["lsh_lean_cert", str(SCR)], 5, script="bench_worker_lsh.py")
elif phase == "round":
    roots = []
    MK = ROOT + "/results/benchmarks/spinnet-m4-scripts/make_root.sh"
    def mk_round(cold):
        def pre(i):
            d = SCR / f"root_round_{'cold' if cold else 'warm'}_{i}_{int(time.time())}"
            subprocess.run(["bash", MK, str(d), "lsh", "5", "0"], check=True, capture_output=True, env=env); roots.append(d)
            base = CAP + PY
            if cold:
                return base + [str(HERE / "loop_cold.py"), str(SCR / f"gs_roundcold_{i}_{int(time.time())}"), "round", "--round", "5", "--evaluate", "--no-lean", "--root", str(d)]
            return base + ["-m", "su2plaq.lsh.loop", "round", "--round", "5", "--evaluate", "--no-lean", "--root", str(d)]
        return pre
    def post_r(i):
        r = json.loads(open(roots[-1] / "results/compress/lsh/round-005.json").read()) if (roots[-1] / "results/compress/lsh/round-005.json").exists() else {}
        return {"best_key": r.get("best_key"), "n_valid": r.get("n_valid"), "entries": r.get("entries")}
    wrapped("lsh_round5_3programs_warm_gridsynth", [], 5, pre=mk_round(False), post=post_r)
    wrapped("lsh_round5_3programs_cold_gridsynth", [], 3, pre=mk_round(True), post=post_r)
elif phase == "m7results_ab":
    m7src = ROOT + "/scratch/bench-m8/m7tree/src"; m7script = ROOT + "/scratch/bench-m8/m7tree/scripts/m7_results.py"
    for i in range(5):
        for tag, src, script in (("head_src_m7script", ROOT + "/src", m7script), ("m7src_m7script", m7src, m7script), ("head_src_head_script", ROOT + "/src", "scripts/m7_results.py")):
            wrapped_one = None
            name = f"m7_results@{tag}"
            raw["runs"].setdefault(name, {"cmd": f"PYTHONPATH={src} taskset -c 0-8 python {script} --out <scratch>", "runs": []})
            ld = load(); out = SCR / f"m7r_{tag}_{i}"
            e2 = dict(env, PYTHONPATH=src)
            p = subprocess.run([sys.executable, "-c", WRAP, "taskset", "-c", "0-8", sys.executable, script, "--out", str(out)], cwd=ROOT, env=e2, capture_output=True, text=True)
            r = json.loads(p.stdout.strip().splitlines()[-1]); r["load_before"] = ld; r["load_after"] = load(); raw["runs"][name]["runs"].append(r)
            print(name, i, round(r["wall"], 2), r["maxrss_kb"] // 1024, "MB rc", r["rc"], flush=True); save()
elif phase == "scripts":
    wrapped("m7_results", CAP + PY + ["scripts/m7_results.py", "--out", str(SCR / "m7_results_out")], 5)
elif phase == "suite_m7":
    wrapped("pytest_m7", [ROOT + "/tools/pytest-safe", "-n", "6", "-q", "-p", "no:cacheprovider", "tests/acceptance/m7"], 3)
elif phase == "suite_m8":
    wrapped("pytest_m8", [ROOT + "/tools/pytest-safe", "-n", "2", "-q", "-p", "no:cacheprovider", "--durations=0", "tests/acceptance/m8", "-m", "slow or not slow"], 1,
            cpus="0-7")
elif phase == "suite_unit":
    wrapped("pytest_unit", [ROOT + "/tools/pytest-safe", "-n", "6", "-q", "-p", "no:cacheprovider", "tests/unit"], 1)
raw["t1"] = time.strftime("%Y-%m-%dT%H:%M:%S%z"); raw["load_after"] = load(); save()
