"""Tester 217: own sparse engine on all 1296 inner codes x 3 angle pairs for the five round-0 seeds, against own dense-expm targets
(rishon.algebra only).  Output results/rishon/tester-217-sparse.json."""
import sys, time, json, importlib.util, subprocess
import numpy as np
spec_ = importlib.util.spec_from_file_location('eng', 'results/rishon/tester-217-engine.py'); eng = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(eng)
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.rishon.compress import baselines as BL
from su2plaq.compress import evaluate as LE

s0 = rishon_spec('step')
pairs = [(s0.alpha, s0.beta)] + [tuple(p) for p in s0.alt_angles]
PR = 'compress/programs/rishon/seed/'
cands = [('general', PR + '000-general.py', None), ('general+polish', PR + '010-general_polish.py', None),
         ('general-rccx', PR + '001-general-rccx.py', None), ('general-mcx', PR + '002-general-mcx.py', None),
         ('qiskit_l3', None, lambda sp: BL.qiskit_l3(sp, seed=12345))]
targets = {p: eng.algebra_targets(*p) for p in pairs}
for p, T in targets.items():
    print('targets', p, 'HE offdiag', T['he_offdiag'], 'HB herm', T['hb_herm'], 'W imag', T['W_real'],
          'unitarity UB', np.abs(T['UB'].conj().T @ T['UB'] - np.eye(1296)).max(), flush=True)
out = {'pairs': pairs, 'rows': []}
for label, path, fn in cands:
    for p in pairs:
        sp_ = s0.with_angles(*p)
        qc = LE.load_program(path).build(sp_).circuit() if path else fn(sp_)
        ops = eng.lower(qc)
        qs = eng.used_qubits(ops)
        T = targets[p]
        for thr in (1e-15, 1e-13) if label in ('general-rccx', 'general-mcx', 'qiskit_l3') and p == pairs[0] else (1e-15,):
            t0 = time.time()
            sim = eng.Sim(T['codes'], qs, thr=thr); sim.run(ops)
            M, wd, wo = sim.block(T['codes'], list(range(16)))
            ph, e2, emax = eng.compare(M, T['step'])
            outer_touched = sorted(q for q in qs if 16 <= q < 48)
            row = dict(label=label, alpha=p[0], beta=p[1], thr=thr, n_gates=len(ops), n_qubits_touched=len(qs), outer_touched=outer_touched,
                       block_err_spectral=e2, block_err_maxabs=emax, leak_dirty_max=float(np.sqrt(wd.max())), leak_nocode_max=float(np.sqrt(wo.max())),
                       leak_total_fro=float(np.sqrt((wd + wo).sum())), my_dropped_fro=float(np.sqrt(sim.dw_sq.sum())),
                       my_dropped_triangle=float(np.sqrt((sim.dw_tri ** 2).sum())), max_state_size=int(sim.maxsize),
                       phase_abs_minus_1=float(abs(ph) - 1), phase_angle=float(np.angle(ph)), seconds=time.time() - t0,
                       cx=sum(1 for o in ops if o[0] != 'phase' and len(o[0]) == 1 and o[3] == 'cx'))
            out['rows'].append(row)
            print(label, p, thr, 'err %.2e leak %.1e/%.1e dropped(fro) %.2e tri %.2e size %d  %.1fs' % (e2, row['leak_dirty_max'], row['leak_nocode_max'], row['my_dropped_fro'], row['my_dropped_triangle'], sim.maxsize, row['seconds']), flush=True)
out['commit'] = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()
json.dump(out, open('results/rishon/tester-217-sparse.json', 'w'), indent=1)
