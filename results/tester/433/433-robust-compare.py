"""Tester 433: own 20-pair recount (433-robust.json) vs production robust record (results/compress/rishon/robust.json) and vs scratch recomputation; coefficient decomposition."""
import json, math, itertools, subprocess
m = json.load(open('results/tester/433/433-robust.json'))
p = json.load(open('results/compress/rishon/robust.json'))['entries']
S = '/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/c0852fe6-e8f0-4e38-bdd5-b42d861ef247/scratchpad/r433/root/results/compress/rishon/robust.json'
sc = json.load(open(S))['entries']
out = dict(commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), seed=m['seed'], n_entries_committed=len(p), n_entries_scratch=len(sc), committed_equals_scratch=p == sc)
for c in ['r06-F1-006', 'r06-F3-006']:
    rows = m['programs'][c]['rows']; pr = p[c]
    out[c] = dict(T_list_equal=[r['t_total'] for r in rows] == pr['t_eps'], depth_list_equal=[r['depth_ct'] for r in rows] == pr['depth_ct'],
                  mine_sumT=sum(r['t_total'] for r in rows), prod_sumT=pr['t_sum'], mine_sumD=sum(r['depth_ct'] for r in rows), prod_sumD=pr['depth_sum'], robust_key=pr['robust_key'],
                  angle_linear=pr['angle_linear'])
sp = {}
for c in ['r06-F1-006', 'r06-F3-006']:
    d = json.load(open(f'results/tester/433/433-sparse-{c}.json'))
    dec = []
    for a, b in d['coefficient_set']:
        if abs(a) > 1e-12: dec.append(('alpha', a)); continue
        found = None
        for dd in (1, 2, 4):
            for mm in range(-8 * dd, 8 * dd + 1):
                for nn in range(-8 * dd, 8 * dd + 1):
                    if abs((mm + nn * math.sqrt(2)) / dd - b) < 1e-8: found = (mm, nn, dd); break
                if found: break
            if found: break
        dec.append(('beta', b, f'({found[0]} + {found[1]} sqrt2)/{found[2]}' if found else None))
    sp[c] = dec
out['coefficient_decomposition'] = sp
json.dump(out, open('results/tester/433/433-robust-compare.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
