"""Benchmark 307: breakdown of scripts/m11_results.py in ONE process: usage w_cross.py <out.json>; BENCH_ROOT = worktree.
Times (perf_counter): spectra_results(headline=False, out=False) [KS spectra / embedding / limits / fuzzy part], then each of the 9 cross-verdicts split into
step_circuit (build; headline = sandbox subprocess), transported_target, evaluate, (general: + mutant evaluate), then gate_table(out=False), render, tradeoff_figure(out=scratch)."""
import sys, os, json, time, resource, pathlib, tempfile
ROOT = os.environ["BENCH_ROOT"]; sys.path.insert(0, ROOT + "/src")
import numpy as np
from su2plaq.crosscheck import report as R, ks as K
from su2plaq.compress.spec import get_encoding
from su2plaq.evaluate.evaluator import evaluate
tm = lambda f: (lambda t: (time.perf_counter() - t, None))(time.perf_counter())
def T(f):
    t = time.perf_counter(); r = f(); return time.perf_counter() - t, r
out = {"root": ROOT, "parts": {}, "cross": []}
out["parts"]["spectra_no_headline_total"], _ = T(lambda: R.spectra_results(out=False, headline=False))
for circ, targ, which in (("twelve", "lsh", "general"), ("spinnet", "twelve", "general"), ("lsh", "spinnet", "general"),
                          ("twelve", "spinnet", "headline"), ("spinnet", "lsh", "headline"), ("lsh", "twelve", "headline")):
    for (a, b) in ((0.37, 0.61),) if which == "general" else R.ANGLES:
        t_b, (qc, info) = T(lambda: K.step_circuit(circ, which, a, b, 1))
        t_t, tgt = T(lambda: K.transported_target(targ, circ, "step", a, b, 1))
        enc = get_encoding(circ)
        t_e, v = T(lambda: evaluate(qc, enc, tgt))
        rec = dict(circuit=circ, target=targ, which=which, alpha=a, build_s=t_b, target_s=t_t, evaluate_s=t_e, ok=bool(v.ok), total_error=float(v.total_error), read=int(v.outer_bits_read), method=v.method)
        if which == "general":
            tgt2 = K.transported_target(targ, circ, "step", a, b + 1e-6, 1)
            rec["mutant_s"], _ = T(lambda: evaluate(qc, enc, tgt2))
        out["cross"].append(rec)
out["parts"]["gate_table"], _ = T(lambda: R.gate_table(out=False))
d = tempfile.mkdtemp(prefix="bm11_", dir=os.environ.get("BENCH_SCR"))
out["parts"]["tradeoff_figure"], fig = T(lambda: R.tradeoff_figure(out=pathlib.Path(d) / "tradeoff.pdf"))
out["parts"]["render"], _ = T(lambda: R.render())
out["rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
print("RESULT " + json.dumps(out), flush=True)
