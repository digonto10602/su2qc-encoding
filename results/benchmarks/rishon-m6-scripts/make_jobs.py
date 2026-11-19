import json, sys, pathlib
repo = pathlib.Path("/home/digimonk/Projects/su2qc-encoding"); tree = repo / "scratch/bench305/head"
raw = repo / "results/benchmarks/rishon-m6-raw"; tmp = repo / "scratch/bench305/tmp"
py = "/home/digimonk/miniforge3/envs/coding/bin/python"
env = {"PYTHONPATH": str(tree / "src"), "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "PYTHONHASHSEED": "20261104"}
env["PATH"] = "/home/digimonk/.local/bin:" + "/home/digimonk/miniforge3/envs/coding/bin:/usr/bin:/bin"
P = "compress/programs/rishon"
rc = lambda prog, mode: [py, "-m", "su2plaq.rishon.compress.run_candidate", f"{P}/{prog}", "--kind", "step", mode]
def job(name, cmd, rep, cpus="0", cwd=tree):
    return {"name": name, "rep": rep, "cmd": cmd, "cpus": cpus, "cwd": str(cwd), "env": env, "log": str(raw / f"{name}.rep{rep}.log")}
reps = int(sys.argv[1]); jobs = []
for rep in range(reps + 1):      # rep 0 = warm-up (disk/page cache, gridsynth cache, pyc); excluded from the medians
    L = [
     job("rc_general_trial", rc("seed/000-general.py", "--trial"), rep),
     job("rc_general_full", rc("seed/000-general.py", "--full"), rep),
     job("rc_headline_trial", rc("F3/006-closed-mark-in-restore.py", "--trial"), rep),
     job("rc_headline_full", rc("F3/006-closed-mark-in-restore.py", "--full"), rep),
     job("rc_ctl_F1_004_full", rc("F1/004-pz-selector-walsh6.py", "--full"), rep),
     job("cert_general_step", [py, str(repo / "results/benchmarks/rishon-m6-scripts/cert_worker.py"), "general", str(tree), str(tmp / f"cg{rep}")], rep),
     job("cert_headline", [py, str(repo / "results/benchmarks/rishon-m6-scripts/cert_worker.py"), "headline", str(tree), str(tmp / f"ch{rep}")], rep),
     job("cert_det_layer", [py, str(repo / "results/benchmarks/rishon-m6-scripts/cert_worker.py"), "det", str(tree), str(tmp / f"cd{rep}")], rep),
     job("three_layer_headline", [py, "-m", "su2plaq.rishon.compress.three_layer", "--out", str(tmp / f"tl{rep}.json")], rep),
     job("three_layer_ctl_F1_004", [py, "-m", "su2plaq.rishon.compress.three_layer", "--entry", "r04-F1-004", "--out", str(tmp / f"tlc{rep}.json")], rep),
     job("lean_theorem_best_step", ["lake", "env", "lean", "certs/rishon-best-step.lean"], rep, cpus="0-3", cwd=tree / "lean"),
     job("lean_theorem_general_step", ["lake", "env", "lean", "certs/rishon-general-step.lean"], rep, cpus="0-3", cwd=tree / "lean"),
    ]
    k = rep % len(L)
    jobs += L[k:] + L[:k]
json.dump(jobs, open(sys.argv[2], "w"), indent=1)
print(len(jobs), "jobs")
