"""Tester 221: independent audit of lean_cert.recognise_angle (three-variable angle recogniser) at the nominal pair (0.37, 0.61).
(1) locked examples; (2) random TRUE expressions (m_a a + m_b b + m_g sqrt2 b)/d by family, check the returned tuple is EQUAL in value at the 20 locked pairs
(soundness of the classification: an alias that matches at the nominal pair but not elsewhere is what robust_metrics' 1e-9 refit must catch); (3) angles that must be None."""
import json, math, subprocess, os, time
import numpy as np
from su2plaq.rishon.lean_cert import recognise_angle as ra
here = os.path.dirname(os.path.abspath(__file__))
a0, b0 = 0.37, 0.61
rng = np.random.default_rng(20261107)
al = rng.uniform(0.05, 2.0, 20); be = rng.uniform(0.05, 1.2, 20)
S2 = math.sqrt(2)
def val(t, a, b):
    ma, mb, mg, d = t; return (ma * a + mb * b + mg * S2 * b) / d
res = {}
t0 = time.time()
res['locked'] = dict(g8=ra(8 * S2 * b0, a0, b0), p0123=ra(0.123, a0, b0), m0123=ra(-0.123, a0, b0), zero=ra(0.0, a0, b0),
                     alpha34=ra(-0.75 * a0, a0, b0), half_beta=ra(0.5 * b0, a0, b0), f1=[ra(x * b0, a0, b0) for x in (0.5, 1.828427124746, 3.328427124746)],
                     f1_exact=[ra((2 * S2 - 1) * b0, a0, b0), ra((2 * S2 + 0.5) * b0, a0, b0), ra((2 * S2 - 0.5) * b0, a0, b0)])
print(res['locked'])
fam = {'alpha': 0, 'beta_g': 0, 'alpha_g': 0, 'alpha_beta_noG': 0, 'beta_only': 0, 'all3': 0}
stats = {k: dict(n=0, none=0, equal_everywhere=0, wrong_alias=0, examples=[]) for k in fam}
for k in fam:
    for _ in range(300):
        d = int(rng.integers(1, 33))
        ma = int(rng.integers(-12, 13)); mb = int(rng.integers(-12, 13)); mg = int(rng.integers(-12, 13))
        if k == 'alpha': mb = mg = 0
        elif k == 'beta_g': ma = 0
        elif k == 'alpha_g': mb = 0
        elif k == 'alpha_beta_noG': mg = 0
        elif k == 'beta_only': ma = mg = 0
        if (ma, mb, mg) == (0, 0, 0): continue
        th = val((ma, mb, mg, d), a0, b0)
        r = ra(th, a0, b0)
        s = stats[k]; s['n'] += 1
        if r is None: s['none'] += 1; continue
        ok = all(abs(val(r, a, b) - val((ma, mb, mg, d), a, b)) < 1e-9 for a, b in zip(al, be))
        if ok: s['equal_everywhere'] += 1
        else:
            s['wrong_alias'] += 1
            if len(s['examples']) < 3: s['examples'].append(dict(true=[ma, mb, mg, d], got=list(r)))
for k, v in stats.items(): print(k, {x: v[x] for x in ('n', 'none', 'equal_everywhere', 'wrong_alias')}, v['examples'])
# random decimals must be None with overwhelming probability
nn = 0; hits = []
for x in rng.uniform(-3, 3, 400):
    r = ra(round(float(x), 3), a0, b0)
    if r is not None: hits.append((round(float(x), 3), r))
res['random_decimal_non_none'] = hits[:10]; print('random 3-decimal angles recognised:', len(hits), hits[:5])
res['stats'] = stats; res['seconds'] = time.time() - t0
json.dump(dict(commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), seed=20261107, result=res), open(os.path.join(here, 'tester-221-recognise.json'), 'w'), indent=1, default=str)
