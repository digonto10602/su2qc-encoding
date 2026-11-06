import sys, json; sys.path.insert(0,'src')
import numpy as np
import su2plaq.evaluate.sparse_sim as ss
import su2plaq.circuits.rishon as C
from su2plaq.rishon import operators as O
n = {'calls': 0}
orig = ss._coalesce
def wrap(*a, **k):
    n['calls'] += 1; return orig(*a, **k)
ss._coalesce = wrap
qc = C.build_UB(0.61)
b = ss.run_batch(qc, O.inner_codes())
r = {'coalesce_calls_production': n['calls'], 'my_merge_calls': 202+34+81, 'production_dropped_total': b.dropped_total, 'production_dropped_max': b.dropped_max,
     'ratio_to_mine': b.dropped_total/1.8484373285187024e-15}
# per-call noise scale if calls were equal: sqrt(calls ratio) .. linear accumulation
r['calls_ratio'] = n['calls']/(202+34+81)
print(r); json.dump(r, open('results/rishon/tester-204-coalesce-count.json','w'), indent=1)
