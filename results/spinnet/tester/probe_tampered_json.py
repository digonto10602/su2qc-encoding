"""Tester 3.L3: tamper with a valid certificate's JSON and run the Lean checker directly."""
import json, copy, pathlib, sys, subprocess
src = json.load(open('results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json'))
exe = 'lean/.lake/build/bin/su2plaq_cert_spinnet'
out = pathlib.Path(sys.argv[1]); out.mkdir(exist_ok=True, parents=True)
def run(name, c, expect_reject=True):
    p = out / f'{name}.json'; p.write_text(json.dumps(c))
    r = subprocess.run([exe, 'check', str(p)], capture_output=True, text=True)
    line = r.stdout.strip().splitlines()[0] if r.stdout.strip() else r.stderr[:100]
    ok = line.startswith('REJECT') == expect_reject
    print(('OK  ' if ok else 'BAD ') + f'{name:40s} {line[:120]}', flush=True); return dict(name=name, line=line, ok=ok)
res = []
c = copy.deepcopy(src); res.append(run('control_valid', c, False))
c = copy.deepcopy(src); c['states'][3], c['states'][4] = c['states'][4], c['states'][3]
c['states'][3]['k'], c['states'][4]['k'] = 3, 4; res.append(run('swap_two_states', c))
c = copy.deepcopy(src); c['states'].pop(); res.append(run('drop_last_state', c))
c = copy.deepcopy(src); c['states'][5]['terms'][0]['code'] = 3 + (1 << 20) ; res.append(run('state_support_on_ancilla', c))
c = copy.deepcopy(src); c['states'][5]['terms'][0]['code'] = c['states'][6]['terms'][0]['code']; res.append(run('duplicate_state_code', c))
c = copy.deepcopy(src); c['states'][7]['terms'][0]['c'][0] = '1/2'; res.append(run('state_not_normalised', c))
c = copy.deepcopy(src); c['target']['blocks'][0]['entries'][0][2][0][1][0] = '2'; res.append(run('target_coeff_changed', c))
c = copy.deepcopy(src); c['target']['blocks'][0]['entries'][0][2].append([[0, 0], ['1', '0', '0', '0', '0', '0', '0', '0']]); res.append(run('target_extra_term', c))
c = copy.deepcopy(src); c['target']['kind'] = 'UB'; res.append(run('kind_UB_with_step_target', c))
c = copy.deepcopy(src); c['target']['order'] = 2; res.append(run('order2_with_order1_target', c))
c = copy.deepcopy(src); c['base'] = {'d_alpha': 8, 'd_beta': 4}; res.append(run('base_doubled_unscaled', c))
c = copy.deepcopy(src); c['phase']['m'] = [1, 0]; res.append(run('phase_wrong', c))
c = copy.deepcopy(src); c['phase']['k'] = ['0', '0', '1/2', '1/2', '0', '0', '0', '0']; res.append(run('phase_omega', c))
c = copy.deepcopy(src); c['gates'] = []; res.append(run('empty_gate_list', c))
c = copy.deepcopy(src); c['gates'] = c['gates'][:-1]; res.append(run('last_gate_dropped_json', c))
c = copy.deepcopy(src); c['n_data'] = 12; c['n_outer'] = 8; res.append(run('n_data_12', c))
c = copy.deepcopy(src); del c['target']; res.append(run('no_target', c))
c = copy.deepcopy(src); c['schema'] = 'su2plaq-cert-2'; res.append(run('bad_schema', c))
# the laptop's twelve-qubit checker must reject a spin-network certificate (different pins), confirming the two checkers are not interchangeable
r = subprocess.run(['lean/.lake/build/bin/su2plaq_cert', 'check', 'results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json'], capture_output=True, text=True)
print('laptop su2plaq_cert on spin-network cert:', r.stdout.strip()[:150])
res.append(dict(name='laptop_checker_on_spinnet_cert', line=r.stdout.strip()[:200], ok=r.stdout.startswith('REJECT')))
json.dump(res, open(sys.argv[2], 'w'), indent=1)
print('SUMMARY', sum(x['ok'] for x in res), '/', len(res))
