"""Benchmark 304 driver (tester).  A/B: old tree (git archive of tag pre-consolidation-008 = ed4d18a) vs HEAD, fresh process per run,
arms interleaved (order flips every repetition), pinned to one CPU, load average recorded before/after (waits if load1 > LOADMAX).
usage: c5_driver.py <group> [job ...]     jobs are 'name' from JOBS; no job = whole group.  Output: results/benchmarks/c5-raw/<group>.jsonl"""
import json, os, subprocess, sys, time, shutil, pathlib, resource
NEW = "/home/digimonk/Projects/su2qc-encoding"
OLD = NEW + "/scratch/bench304/old-pre008"
TREES = {"old": OLD, "new": NEW}
CPU = os.environ.get("BENCH_CPU", "4"); LOADMAX = float(os.environ.get("LOADMAX", "9"))
PY = sys.executable
SC = "results/benchmarks/c5-scripts/"
def W(script, task): return [PY, SC + script, task]
def prog(enc, rel): return f"compress/programs/{enc}/{rel}"
HEAD = {"twelve": prog("twelve", "F2/005-outer-t2-peephole.py"), "spinnet": prog("spinnet", "F1/002-dimer-linear-corner-walk.py"),
        "rishon": prog("rishon", "F1/004-pz-selector-walsh6.py"), "fuzzy_ub": prog("fuzzy_ub", "F1/010-ten-qubit-short-window-exact-angles.py"),
        "fuzzy_link": prog("fuzzy_link", "F2/001-plane_bfs_frame_fusion12.py")}
ROUND = {"twelve": (4, "twelve", ["-m", "su2plaq.compress.round", "--encoding", "twelve"]), "spinnet": (5, "spinnet", ["-m", "su2plaq.spinnet.loop", "round"]),
         "rishon": (4, "rishon", ["-m", "su2plaq.rishon.compress.round"]), "fuzzy_ub": (9, "fuzzy_ub", ["scripts/m10_round.py", "round", "--encoding", "fuzzy_ub"]),
         "fuzzy_link": (2, "fuzzy_link", ["scripts/m10_round.py", "round", "--encoding", "fuzzy_link"])}
JOBS = {}  # name -> (group, reps, kind, cmd)
def worker(group, script, tasks, reps):
    for t in tasks: JOBS[f"{group}:{t}"] = (group, reps, "worker", W(script, t))
worker("twelve", "w_twelve0.py", ["basis", "ops", "eval_id_span", "eval_outer3", "paulo_eval"], 3)
worker("twelve", "w_twelve1.py", ["m1_build", "eval_UE", "eval_UB", "eval_step1", "synth_UB"], 3)
worker("spinnet", "w_sl.py", ["ops", "enc_build", "eval_UE", "eval_UB_auto", "eval_step1", "eval_pairs9", "eval_UB_outer_physical", "eval_paulo15", "synth_UB", "synth_step1", "eval_twelve_UB"], 5)
worker("lsh", "w_sl.py", ["lsh_enc_build", "lsh_eval_UE", "lsh_eval_UB", "lsh_eval_step1", "lsh_eval_wrap_flags4", "lsh_synth_step1"], 5)
worker("rishon", "w_rishon.py", ["basis", "build", "verify_UE", "verify_UB", "verify_step", "threelayer"], 3)
worker("fuzzy", "w_fuzzy.py", ["build", "verify_link", "verify_plaquette", "verify_step1"], 3)
JOBS["twelve:cand"] = ("twelve", 3, "cand", ["-m", "su2plaq.compress.run_candidate", HEAD["twelve"], "--encoding", "twelve", "--kind", "step", "--full"])
JOBS["spinnet:cand"] = ("spinnet", 5, "cand", ["-m", "su2plaq.spinnet.loop", "candidate", HEAD["spinnet"], "--full"])
JOBS["rishon:cand"] = ("rishon", 3, "cand", ["-m", "su2plaq.rishon.compress.run_candidate", HEAD["rishon"], "--kind", "step", "--full"])
JOBS["fuzzy_ub:cand"] = ("fuzzy", 5, "cand", ["scripts/m10_round.py", "candidate", HEAD["fuzzy_ub"], "--encoding", "fuzzy_ub", "--full"])
JOBS["fuzzy_link:cand"] = ("fuzzy", 5, "cand", ["scripts/m10_round.py", "candidate", HEAD["fuzzy_link"], "--encoding", "fuzzy_link", "--full"])
for nm, sc in (("m3", "m3_results.py"), ("m4", "m4_results.py"), ("m7", "m7_results.py"), ("m1", "m1_results.py")):
    JOBS[f"scripts:{nm}"] = ("scripts", 3, "script", ["scripts/" + sc, "--out", "{O}"])
for e, (rnd, _, base) in ROUND.items():
    JOBS[f"{e}:round{rnd}"] = (("fuzzy" if e.startswith("fuzzy") else e), 3, "round", [*base, "--round", str(rnd), "--evaluate", "--no-lean", "--root", "{S}"])

def load1(): return float(open("/proc/loadavg").read().split()[0])
def run_one(name, arm, rep, group, kind, cmd, out):
    root = TREES[arm]; env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="20261104",
                                  BENCH_ROOT=root, PYTHONPATH="src")
    S = None
    if kind == "round":
        enc = name.split(":")[0]; rnd = ROUND[enc][0]; S = f"{NEW}/scratch/bench304/roots/{arm}_{enc}"
        subprocess.run([PY, NEW + "/results/benchmarks/c5-scripts/make_root.py", root, S, enc, str(rnd)], check=True, capture_output=True)
        cmd = [c.replace("{S}", S) for c in cmd]
    if kind == "script":
        O = f"{NEW}/scratch/bench304/out/{arm}_{name.split(':')[1]}"; os.makedirs(O, exist_ok=True); cmd = [c.replace("{O}", O) for c in cmd]
    waited = 0
    while load1() > LOADMAX and waited < 300: time.sleep(5); waited += 5
    l0 = load1(); t0 = time.perf_counter()
    p = subprocess.Popen(["taskset", "-c", CPU, PY, *cmd[1:]] if cmd[0] == PY else ["taskset", "-c", CPU, PY, *cmd], cwd=root, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    so, se = p.communicate(); wall = time.perf_counter() - t0
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    rec = dict(name=name, arm=arm, rep=rep, kind=kind, wall_s=wall, rc=p.returncode, load_before=l0, load_after=load1(), waited_s=waited, cpu=CPU,
               cmd=" ".join(cmd), t_start=time.time())
    line = [l for l in so.splitlines() if l.startswith("RESULT ")]
    if line: rec["result"] = json.loads(line[-1][7:])
    else: rec["stdout_tail"] = so[-1200:]
    if p.returncode and kind not in ("cand",): rec["stderr_tail"] = se[-1500:]
    if kind == "cand": rec["stderr_tail"] = se[-300:]
    if kind == "round":
        enc = name.split(":")[0]; rnd = ROUND[enc][0]
        rf = pathlib.Path(S) / "results/compress" / enc / f"round-{rnd:03d}.json"
        if rf.exists():
            d = json.loads(rf.read_text()); rec["round_json"] = {k: d.get(k) for k in ("wall_s", "lean_seconds", "n_valid", "n_invalid", "best_key")}
            ents = d.get("entries") or []
            rec["round_json"]["n_entries"] = len(ents)
            rec["round_json"]["entry_wall"] = [e.get("wall_s") for e in ents if isinstance(e, dict)]
    with open(out, "a") as f: f.write(json.dumps(rec, default=str) + "\n")
    print(f"{name} {arm} rep{rep} wall {wall:.2f}s rc={p.returncode} load {l0:.2f}->{rec['load_after']:.2f}", flush=True)

if __name__ == "__main__":
    group = sys.argv[1]; names = sys.argv[2:] or [n for n, j in JOBS.items() if j[0] == group]
    out = f"{NEW}/results/benchmarks/c5-raw/{group}.jsonl"
    reps_override = int(os.environ.get("REPS", "0"))
    for name in names:
        g, reps, kind, cmd = JOBS[name]; reps = reps_override or reps
        for rep in range(reps):
            arms = ("old", "new") if rep % 2 == 0 else ("new", "old")
            for arm in arms: run_one(name, arm, rep, g, kind, cmd, out)
