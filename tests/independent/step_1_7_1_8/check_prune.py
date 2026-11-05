"""Tester: how real is the pruning bound? Step order 2, (0.37,0.61): run_batch on the 625 inner codes with PRUNE_REL = 1e-14 (production),
1e-15, 1e-16 and 0 (no pruning) and compare amplitudes; also the dropped_l2 certified bound per column."""
import sys, json, time, warnings
import numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.circuits.twelve import build_step
from su2plaq.metrics.cliffordt import synthesize
import su2plaq.evaluate.sparse_sim as ss

enc = TwelveQubit(); inner = np.asarray(enc.inner_codes(), dtype=np.int64)
qc = build_step(0.37, 0.61, order=2)
res = []
for eps in (1e-4, 1e-6):
    synth, info = synthesize(qc, eps)
    runs = {}
    for rel in (1e-14, 1e-15, 1e-16, 1e-17):
        ss.PRUNE_REL = rel
        t0 = time.time()
        try:
            b = ss.run_batch(synth, inner, cap=60_000_000)
        except ss.SimCapExceeded as e:
            runs[rel] = None; print(eps, rel, "cap exceeded", e, flush=True); continue
        runs[rel] = b
        print(f"eps={eps:g} PRUNE_REL={rel:g}: stored {len(b.keys)}, dropped_max {b.dropped_max:.3e}, dropped_total {b.dropped_total:.3e}, {time.time()-t0:.1f}s", flush=True)
    ref = runs[1e-17]
    if ref is None: continue
    def dense(b):
        d = {}
        for k, c, a in zip(b.keys.tolist(), b.cols.tolist(), b.amps):
            d[(c, k)] = a
        return d
    dref = dense(ref)
    ncol = len(inner)
    for rel in (1e-14, 1e-15, 1e-16):
        b = runs[rel]; d = dense(b)
        diff2 = np.zeros(ncol)
        for key in set(d) | set(dref):
            diff2[key[0]] += abs(d.get(key, 0) - dref.get(key, 0)) ** 2
        diff = np.sqrt(diff2)
        row = dict(eps=eps, prune_rel=rel, bound_dropped_max=b.dropped_max, actual_diff_max=float(diff.max()),
                   ratio_actual_over_bound_at_worst_col=float(diff[np.argmax(b.dropped_l2)] / b.dropped_l2.max()),
                   bound_col_worst=int(np.argmax(b.dropped_l2)), actual_total_frob=float(np.sqrt((diff**2).sum())), bound_total=b.dropped_total,
                   stored_pruned=len(b.keys), stored_exact=len(ref.keys))
        print(row, flush=True); res.append(row)
    # unpruned: how many amplitudes sit below 1e-14 of the column max (genuine small amplitudes)
    mag = np.abs(ref.amps); cm = np.zeros(ncol); np.maximum.at(cm, ref.cols, mag)
    small = mag <= 1e-14 * cm[ref.cols]
    print(f"eps={eps:g} unpruned: {small.sum()} of {len(mag)} amplitudes <= 1e-14*colmax; largest such {mag[small].max():.2e}; their L2 total {np.sqrt((mag[small]**2).sum()):.3e}", flush=True)
    res.append(dict(eps=eps, n_small=int(small.sum()), n_all=int(len(mag)), small_l2_total=float(np.sqrt((mag[small]**2).sum()))))
json.dump(res, open("results/m1_step_1_7_prune_analysis.json", "w"), indent=1)
