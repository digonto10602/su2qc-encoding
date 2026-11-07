import importlib.util, json, numpy as np
def load(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
eng = load('eng', 'results/rishon/tester-217-engine.py'); m204 = load('m204', 'results/rishon/tester-204-mysim.py')
T = eng.algebra_targets(0.37, 0.61)
codes, HB, HE = m204.own_reference()
out = dict(codes_equal=bool(np.array_equal(codes, T['codes'])), HB_maxdiff=float(np.abs(HB - T['HB']).max()), HE_maxdiff=float(np.abs(HE - T['HE']).max()),
           HE_values=sorted(set(np.round(T['HE'], 12).tolist())), HB_nnz=int((np.abs(T['HB']) > 1e-12).sum()))
w = np.linalg.eigvalsh(T['HB']); vals, cnt = np.unique(np.round(w, 8), return_counts=True)
out['HB_spectrum'] = {str(v): int(c) for v, c in zip(vals, cnt)}
print(out); json.dump(out, open('results/rishon/tester-217-targets-xcheck.json', 'w'), indent=1)
