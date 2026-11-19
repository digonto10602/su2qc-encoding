"""RSS of the heavy CLI jobs: one run per arm; peak RSS = ru_maxrss of the child tree (RUSAGE_CHILDREN of a fresh wrapper).  Output c5-raw/rss.json"""
import json, os, subprocess, sys, resource, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c5_driver as D
out = {}
for name in ("twelve:cand", "spinnet:cand", "rishon:cand", "fuzzy_ub:cand", "fuzzy_link:cand", "scripts:m3", "scripts:m7", "scripts:m4", "scripts:m1"):
    g, reps, kind, cmd = D.JOBS[name]
    for arm in ("old", "new"):
        root = D.TREES[arm]
        c = list(cmd)
        if kind == "script":
            O = f"{D.NEW}/scratch/bench304/out/rss_{arm}_{name.split(':')[1]}"; os.makedirs(O, exist_ok=True); c = [x.replace("{O}", O) for x in c]
        env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="20261104", BENCH_ROOT=root, PYTHONPATH="src")
        wrapper = "import subprocess,sys,resource,json;p=subprocess.run(sys.argv[1:],capture_output=True);print(json.dumps({'rc':p.returncode,'rss_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}))"
        argv = ["taskset", "-c", D.CPU, D.PY, *c] if c[0] != D.PY else ["taskset", "-c", D.CPU, *c]
        r = subprocess.run([sys.executable, "-c", wrapper, *argv], cwd=root, env=env, capture_output=True, text=True)
        d = json.loads(r.stdout.strip().splitlines()[-1]); out.setdefault(name, {})[arm] = d["rss_kb"] / 1024.0
        print(name, arm, d, flush=True)
json.dump(out, open(D.NEW + "/results/benchmarks/c5-raw/rss.json", "w"), indent=1)
