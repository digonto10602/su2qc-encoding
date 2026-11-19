"""Certificate / theorem-file jobs on the snapshot of the CURRENT HEAD aaa802e (after audit-307 N1: multi-pair exact-target cross-check)."""
import json, pathlib, sys
repo = pathlib.Path("/home/digimonk/Projects/su2qc-encoding"); tree = repo / "scratch/bench305/head2"
raw = repo / "results/benchmarks/rishon-m6-raw"; tmp = repo / "scratch/bench305/tmp"
py = "/home/digimonk/miniforge3/envs/coding/bin/python"; w = str(repo / "results/benchmarks/rishon-m6-scripts/cert_worker.py")
env = {"PYTHONPATH": str(tree / "src"), "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "PYTHONHASHSEED": "20261104",
       "PATH": "/home/digimonk/.local/bin:/home/digimonk/miniforge3/envs/coding/bin:/usr/bin:/bin"}
def job(name, cmd, rep, cpus="0", cwd=tree):
    return {"name": name, "rep": rep, "cmd": cmd, "cpus": cpus, "cwd": str(cwd), "env": env, "log": str(raw / f"{name}.H2.rep{rep}.log")}
jobs = []
for rep in range(4):
    L = [job("cert_general_step", [py, w, "general", str(tree), str(tmp / f"h2cg{rep}")], rep),
         job("cert_headline", [py, w, "headline", str(tree), str(tmp / f"h2ch{rep}")], rep),
         job("cert_det_layer", [py, w, "det", str(tree), str(tmp / f"h2cd{rep}")], rep),
         job("lean_theorem_best_step", ["lake", "env", "lean", "certs/rishon-best-step.lean"], rep, cpus="0-3", cwd=tree / "lean"),
         job("lean_theorem_general_step", ["lake", "env", "lean", "certs/rishon-general-step.lean"], rep, cpus="0-3", cwd=tree / "lean")]
    k = rep % len(L); jobs += L[k:] + L[:k]
json.dump(jobs, open(sys.argv[1], "w"), indent=1); print(len(jobs))
