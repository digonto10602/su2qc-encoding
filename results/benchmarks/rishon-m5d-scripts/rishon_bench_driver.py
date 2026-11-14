"""Driver: runs each worker task in a fresh process (taskset -c 10-19, 1 BLAS thread), sequentially, N repeats.
usage: rishon_bench_driver.py <out.jsonl> task:reps [task:reps ...]"""
import json, subprocess, sys, time, os
ROOT = "/home/digimonk/Projects/su2qc-encoding"
out = sys.argv[1]
env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="20261104")
worker = sys.argv[0].replace("rishon_bench_driver.py", os.environ.get("RISHON_WORKER", "rishon_bench_worker.py"))
for spec in sys.argv[2:]:
    task, reps = spec.rsplit(":", 1)
    for r in range(int(reps)):
        t0 = time.time()
        p = subprocess.run(["taskset", "-c", os.environ.get("BENCH_CPU","14"), sys.executable, worker, task], cwd=ROOT, env=env, capture_output=True, text=True, timeout=7200)
        wall = time.time() - t0
        line = [l for l in p.stdout.splitlines() if l.startswith("RESULT ")]
        rec = {"task": task, "rep": r, "wall_process_s": wall, "returncode": p.returncode}
        if line:
            rec.update(json.loads(line[-1][7:]))
        else:
            rec["stderr_tail"] = p.stderr[-1500:]
        with open(out, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"{task} rep{r} wall {wall:.1f}s rc={p.returncode}", flush=True)
