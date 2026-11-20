import subprocess, sys, json, time, os, resource
wt = sys.argv[1]; out = sys.argv[2]; n = int(sys.argv[3])
wrap = ("import subprocess,sys,resource,time,json;t=time.perf_counter();p=subprocess.run(sys.argv[1:],capture_output=True,text=True);"
        "print(json.dumps({'rc':p.returncode,'wall':time.perf_counter()-t,'maxrss_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'out':p.stdout[-6000:]}))")
res = []
for i in range(n):
    ld = open("/proc/loadavg").read().split()[:3]
    p = subprocess.run([sys.executable, "-c", wrap, "taskset", "-c", "0-7", "tools/pytest-safe", "-n", "4", "tests/acceptance/m11", "-m", "slow or not slow", "-q", "--durations=10", "-p", "no:cacheprovider"],
                       cwd=wt, capture_output=True, text=True, env=dict(os.environ, PYTHONPATH="src", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1"))
    r = json.loads(p.stdout.strip().splitlines()[-1]); r["load_before"] = ld; res.append(r); print(i, round(r["wall"], 1), r["rc"], r["maxrss_kb"] // 1024, flush=True)
    open(out, "w").write(json.dumps(res, indent=1))
