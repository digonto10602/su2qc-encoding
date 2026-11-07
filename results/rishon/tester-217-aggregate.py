import json, subprocess, sys
import numpy as np
out = {'commit_tested': 'c75aad5', 'prompt': 'prompts/203', 'tester': 'Claude Sonnet 5.5'}
for tag, f in (('aer_general_nominal_le24q', 'results/rishon/tester-217-aer-general-nominal.npz'), ('aer_general_nominal_26q_sample', 'results/rishon/tester-217-aer-general-26q.npz'), ('aer_general_alt1_sample', 'results/rishon/tester-217-aer-general-alt1.npz'), ('aer_general_alt2_sample', 'results/rishon/tester-217-aer-general-alt2.npz')):
    try:
        d = np.load(f)
    except OSError:
        continue
    nq = d['nq']
    out[tag] = dict(n_codes=int(len(d['cols'])), qubit_hist={int(k): int(v) for k, v in zip(*np.unique(nq, return_counts=True))},
                    max_col_maxabs_err=float(d['colerr_max'].max()), max_col_l2_err=float(d['colerr_l2'].max()),
                    mean_col_l2_err=float(d['colerr_l2'].mean()), max_weight_outside_code_or_dirty=float(np.abs(d['w_out']).max()),
                    phase=[float(d['phase'].real), float(d['phase'].imag)], total_aer_seconds=float(d['seconds'].sum()),
                    per_qubit_max_l2={int(q): float(d['colerr_l2'][nq == q].max()) for q in np.unique(nq)})
sp = json.load(open('results/rishon/tester-217-sparse.json'))
out['sparse_rows'] = sp['rows']
for f, k in (('results/rishon/tester-217-recount.json', 'recount'), ('results/rishon/tester-217-recount2.json', 'recount2'), ('results/rishon/tester-217-targets-xcheck.json', 'targets'),
             ('results/rishon/tester-217-mutants.json', 'mutants'), ('results/rishon/tester-217-l3whole.json', 'l3whole'), ('results/rishon/tester-217-archive-consistency.json', 'archive')):
    out[k] = json.load(open(f))
out['seeds'] = {'l3whole_codes_rng': 217, 'aer_sample_rng': 217, 'trial_seed_round': 0}
json.dump(out, open('results/rishon/tester-217-summary.json', 'w'), indent=1)
print({k: v for k, v in out.items() if k.startswith('aer')})
