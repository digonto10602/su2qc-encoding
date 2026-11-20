"""Benchmark 307 (tester): scripts/m11_results.py wall + peak RSS, repeated, in the clean worktree.
usage: python bench_m11_results.py <worktree> <outjson> <n_cold> <n_warm> [core]
Each run: taskset -c <core> python scripts/m11_results.py (cwd = worktree); wall by perf_counter; peak RSS = RUSAGE_CHILDREN.
cold = worktree compress/cache moved away first (gridsynth cache absent); warm = cache as left by the previous run."""
import sys, os, json, time, subprocess, resource, pathlib, shutil, hashlib
wt = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2]); nc, nw = int(sys.argv[3]), int(sys.argv[4]); core = sys.argv[5] if len(sys.argv) > 5 else "2"
env = dict(os.environ, PYTHONPATH="src", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="20261104")
junk = pathlib.Path("/home/digimonk/Projects/su2qc-encoding/should-be-deleted")
res = {"worktree": str(wt), "core": core, "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=wt, capture_output=True, text=True).stdout.strip(), "runs": []}
def one(kind):
    ld = open("/proc/loadavg").read().split()[:3]
    # RUSAGE_CHILDREN is cumulative max; use a wrapper process per run
    wrap = ("import subprocess,sys,resource,time,json;t=time.perf_counter();p=subprocess.run(sys.argv[1:],capture_output=True,text=True);"
            "print(json.dumps({'rc':p.returncode,'wall':time.perf_counter()-t,'maxrss_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'tail':(p.stdout+p.stderr)[-1500:]}))")
    p = subprocess.run([sys.executable, "-c", wrap, "taskset", "-c", core, sys.executable, "scripts/m11_results.py"], cwd=wt, env=env, capture_output=True, text=True)
    r = json.loads(p.stdout.strip().splitlines()[-1]); r["kind"] = kind; r["load_before"] = ld; r["load_after"] = open("/proc/loadavg").read().split()[:3]
    sp = json.loads((wt / "results/crosscheck/spectra.json").read_text())
    r["cross_verdict_seconds"] = [(c["circuit"], c["target"], c["which"], c["alpha"], c["seconds"]) for c in sp["ks"]["cross_verdicts"]]
    r["spectra_sha_noprov"] = hashlib.sha256(json.dumps({k: v for k, v in sp.items() if k != "provenance"}, sort_keys=True).encode()).hexdigest()
    r["cache_exists"] = (wt / "compress/cache").exists()
    return r
for i in range(nc + nw):
    kind = "cold" if i < nc else "warm"
    if kind == "cold":
        c = wt / "compress/cache"
        if c.exists(): shutil.move(str(c), str(junk / f"bench307-cache-{int(time.time())}"))
    r = one(kind); res["runs"].append(r); print(kind, i, round(r["wall"], 2), r["maxrss_kb"] // 1024, "MB rc", r["rc"], r["cache_exists"], flush=True)
    out.write_text(json.dumps(res, indent=1))
