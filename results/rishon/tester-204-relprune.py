"""Tester 204: re-run my own simulator with the production-style relative prune rule (|a| <= 1e-14 * column max) and compare my
accumulated sqrt-weight bound with production dropped_total (3.02e-13 at beta=0.61) and the true error vs expm."""
import sys, json, importlib.util
sys.path.insert(0, 'src')
import numpy as np
from scipy.linalg import expm
spec = importlib.util.spec_from_file_location('mysim', 'results/rishon/tester-204-mysim.py'); ms = importlib.util.module_from_spec(spec); spec.loader.exec_module(ms)
import su2plaq.circuits.rishon as C
codes, HB, HE = ms.own_reference()
REL = 1e-14
def merge_rel(key, amp, thr=None):
    o = np.argsort(key, kind='stable'); key, amp = key[o], amp[o]
    first = np.r_[True, key[1:] != key[:-1]]; idx = np.flatnonzero(first)
    amp = np.add.reduceat(amp, idx); key = key[idx]
    col = key >> ms.NQ_SHIFT
    cmax = np.zeros(col.max() + 1); np.maximum.at(cmax, col, np.abs(amp))
    small = np.abs(amp) <= REL * cmax[col]
    return key[~small], amp[~small], (key[small] >> ms.NQ_SHIFT, np.abs(amp[small]) ** 2)
ms.merge = merge_rel
beta = 0.61
s = ms.Sim(codes, 26).run(C.build_UB(beta))
M, wa, wo = s.block(codes, 0xFFFF)
V = expm(-1j * beta * HB)
err = float(np.linalg.norm(M - V, 2))
res = {'beta': beta, 'my_relprune_dropped_total': float(np.sqrt((s.dw ** 2).sum())), 'my_relprune_dropped_max': float(s.dw.max()), 'true_opnorm_error': err,
       'production_dropped_total': 3.0197027465763763e-13, 'production_block_error': 4.1436388124413177e-14}
print(res); json.dump(res, open('results/rishon/tester-204-relprune.json', 'w'), indent=1)
