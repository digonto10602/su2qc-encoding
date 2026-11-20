"""Spot-check cells of docs/report-11-cross-encoding-comparison.md against gate-table.json, spectra.json, results/compress/*/robust.json.
Run from the project root: python results/tester/448/spot_check.py"""
import json, math, statistics as st, subprocess
J = lambda p: json.load(open(p))
G = {r['encoding']: r for r in J('results/crosscheck/gate-table.json')['rows']}
S = J('results/crosscheck/spectra.json')
R = {e: J(f'results/compress/{e}/robust.json')['entries'] for e in ['twelve', 'spinnet', 'lsh', 'rishon', 'fuzzy_ub', 'fuzzy_link']}
def se(t_eps): return st.stdev(t_eps) / math.sqrt(len(t_eps))     # sample std (ddof=1) / sqrt(20)
def se0(t_eps): return st.pstdev(t_eps) / math.sqrt(len(t_eps))
rows = []
def cell(label, report, source_desc, got, tol=0.0):
    ok = (abs(report - got) <= tol) if isinstance(report, (int, float)) else (report == got)
    rows.append((label, report, source_desc, got, ok))
lsh0, lshH = R['lsh']['r00-seed-000'], R['lsh']['r05-F3-005']
mc = J('results/lsh/m8-compressed.json'); st1 = J('results/lsh/step.json'); ue = J('results/lsh/UE.json')
# --- LSH cells (Table 1a, 1b, 1c, 2, 3.4 3a)
cell('T1a LSH CX', 94, 'gate-table lsh.general.cx / robust r00-seed-000 cx', (G['lsh']['general']['cx'], lsh0['cx']) and G['lsh']['general']['cx'] if G['lsh']['general']['cx'] == lsh0['cx'] else None)
cell('T1a LSH qubits 31', 31, 'robust lsh r00-seed-000 qubits', lsh0['qubits'])
cell('T1a LSH rot 8', 8, 'gate-table lsh.general.n_rot', G['lsh']['general']['n_rot'])
cell('T1a LSH T_fixed 88', 88, 'gate-table lsh.general.t_fixed', G['lsh']['general']['t_fixed'])
cell('T1a LSH T(1e-6) 598', 598, 'gate-table lsh.general.t_1e6', G['lsh']['general']['t_1e6'])
cell('T1a LSH Tbar 592.6', 592.6, 'robust r00-seed-000 t_mean', lsh0['t_mean'], 1e-9)
cell('T1a LSH Tbar SE 1.6', 1.6, 'robust r00-seed-000 stdev(t_eps)/sqrt(20), ddof=1', round(se(lsh0['t_eps']), 1))
cell('T1b LSH entry', 'r05-F3-005', 'gate-table lsh.headline.entry', G['lsh']['headline']['entry'])
cell('T1b LSH qubits 24', 24, 'm8-compressed metrics.logical.qubits', mc['metrics']['logical']['qubits'])
cell('T1b LSH CX 68', 68, 'm8-compressed metrics.logical.cx', mc['metrics']['logical']['cx'])
cell('T1b LSH rot 22', 22, 'm8-compressed metrics.logical.n_rot', mc['metrics']['logical']['n_rot'])
cell('T1b LSH T_fixed 24', 24, 'm8-compressed metrics.logical.t_fixed', mc['metrics']['logical']['t_fixed'])
cell('T1b LSH T(1e-6) 1396', 1396, 'gate-table lsh.headline.t_nominal', G['lsh']['headline']['t_nominal'])
cell('T1b LSH Tbar 1417.4', 1417.4, 'robust r05-F3-005 t_mean', lshH['t_mean'], 1e-9)
cell('T1b LSH Tbar SE 8.0', 8.0, 'robust r05-F3-005 stdev(t_eps)/sqrt(20) ddof=1', round(se(lshH['t_eps']), 1))
cell('T1b LSH angle-linear yes', True, 'robust r05-F3-005 angle_linear', lshH['angle_linear'])
cell('T1c LSH CX -27.7%', -27.7, '(68-94)/94*100', round((68 - 94) / 94 * 100, 1))
cell('T1c LSH CX x1.38', 1.38, '94/68', round(94 / 68, 2))
cell('T1c LSH Tbar +139.2%', 139.2, '(1417.4-592.6)/592.6*100', round((lshH['t_mean'] - lsh0['t_mean']) / lsh0['t_mean'] * 100, 1))
orow = ue['extra']['outer_electric_row']['metrics']
cell('T1c LSH UE row 20 rotations', 20, 'results/lsh/UE.json extra.outer_electric_row n_rot', orow['logical']['n_rot'])
cell('T1c LSH UE row T(1e-6)=1280', 1280, 'results/lsh/UE.json extra.outer_electric_row t_table[1e-6]', [t['t_total'] for t in orow['t_table'] if t['eps'] == 1e-6][0])
lr = {p['entry']: p for p in G['lsh']['pareto']}
cell('T2 LSH headline (68,1417.4)', (68, 1417.4), 'gate-table lsh.headline', (G['lsh']['headline']['cx'], G['lsh']['headline']['t_mean']))
cell('T2 LSH T-first r00-seed-002 (84,585.1)', ('r00-seed-002', 84, 585.1), 'gate-table lsh.t_first', (G['lsh']['t_first']['entry'], G['lsh']['t_first']['cx'], G['lsh']['t_first']['t_mean']))
cell('T2 LSH general (94,592.6)', (94, 592.6), 'robust r00-seed-000', (lsh0['cx'], lsh0['t_mean']))
exp = [(68, 1417.4), (70, 1354.3), (71, 1116.0), (72, 879.4), (74, 697.6), (82, 641.1), (84, 585.1)]
got = sorted({(p['cx'], p['t_mean']) for p in G['lsh']['pareto']})
cell('T2 LSH Pareto 7 distinct points', exp, 'gate-table lsh.pareto (distinct (cx,T))', got)
cell('T2 LSH tie entries r04-F3-004, r05-F5-005 in Pareto', True, 'gate-table lsh.pareto ids', {'r04-F3-004', 'r05-F5-005', 'r05-F3-005'} <= set(lr))
cell('T2 LSH 28 ranked', 28, 'robust lsh entries with robust_key', sum(1 for v in R['lsh'].values() if v.get('robust_key')))
cell('T2 LSH T-first diff: 16 CX more, -832.3 Tbar', (16, -832.3), '84-68, 585.1-1417.4', (84 - 68, round(585.1 - 1417.4, 1)))
ck = S['ks']
cell('3a max level dev g2=0.5 2.8e-14', 2.8e-14, 'spectra ks.max_pairwise_level_dev[0.5]', ck['max_pairwise_level_dev']['0.5'], 0.05e-14)
cell('3a max level dev g2=1 1.2e-14', 1.2e-14, 'ks.max_pairwise_level_dev[1.0]', ck['max_pairwise_level_dev']['1.0'], 0.05e-14)
cell('3a max level dev g2=2 2.7e-14', 2.7e-14, 'ks.max_pairwise_level_dev[2.0]', ck['max_pairwise_level_dev']['2.0'], 0.05e-14)
cell('3a LSH multiplicities 16,96,16,177,16,96,16', [16, 96, 16, 177, 16, 96, 16], 'ks.hb_multiplicities.lsh', list(ck['hb_multiplicities']['lsh'].values()))
cell('3a transported target 3.0e-15', 3.0e-15, 'ks.transported_target_max', ck['transported_target_max'], 0.05e-15)
cv = ck['cross_verdicts']
cell('3a twelve vs LSH 2.7e-13', 2.7e-13, 'cross_verdicts[0].total_error', cv[0]['total_error'], 0.05e-13)
cell('3a spinnet vs twelve 1.1e-14', 1.1e-14, 'cross_verdicts[1].total_error', cv[1]['total_error'], 0.05e-14)
cell('3a LSH vs spinnet 1.6e-14', 1.6e-14, 'cross_verdicts[2].total_error', cv[2]['total_error'], 0.05e-14)
cell('3a mutants 2.0000000012e-6', (2.0000000012e-6, 2.0000000018e-6, 2.0000000034e-6), 'cross_verdicts[0..2].mutant.block_error', tuple(round(c['mutant']['block_error'], 16) for c in cv[:3]), 0)
cell('3a headline LSH r05-F3-005 vs twelve 1.4e-14 / 1.3e-14', (1.4e-14, 1.3e-14), 'cross_verdicts[7,8].total_error', (round(cv[7]['total_error'], 15), round(cv[8]['total_error'], 15)))
cell('3a all 9 verdicts ok & certified', True, 'cross_verdicts[*].ok and certified', all(c['ok'] and c['certified'] for c in cv))
cell('3a mutants all rejected', True, 'cross_verdicts[0..2].mutant.ok == False', all(not c['mutant']['ok'] for c in cv[:3]))
cell('3a headline_skipped empty', [], 'ks.headline_skipped', ck['headline_skipped'])
# --- other encodings (Table 1a/1b/2)
t12 = R['twelve']['r00-seed-000']; t12H = R['twelve']['r05-F2-005']
cell('T1a twelve Tbar 943.2 +- 2.3', (943.2, 2.3), 'robust twelve r00-seed-000', (t12['t_mean'], round(se(t12['t_eps']), 1)))
cell('T1b twelve r05-F2-005 (31,111,927.4)', (31, 111, 927.4), 'robust twelve r05-F2-005', (t12H['qubits'], t12H['cx'], t12H['t_mean']))
cell('T1b twelve T(1e-6) 912', 912, 'gate-table twelve.headline.t_nominal', G['twelve']['headline']['t_nominal'])
sp0 = R['spinnet']['r00-seed-000']; spH = R['spinnet']['r02-F1-002']
cell('T1a spinnet Tbar 560.6 +- 1.6', (560.6, 1.6), 'robust spinnet r00-seed-000', (sp0['t_mean'], round(se(sp0['t_eps']), 1)))
cell('T1b spinnet r02-F1-002 (17,31,1092.0 +- 3.1)', (17, 31, 1092.0, 3.1), 'robust spinnet r02-F1-002', (spH['qubits'], spH['cx'], spH['t_mean'], round(se(spH['t_eps']), 1)))
cell('T1c spinnet +94.8%', 94.8, '(1092.0-560.6)/560.6', round((spH['t_mean'] - sp0['t_mean']) / sp0['t_mean'] * 100, 1))
rs0 = R['rishon']['r00-seed-000']; rsH = R['rishon']['r06-F3-006']
cell('T1a rishon two-layer (58,10102,20620.2 +- 58.8)', (58, 10102, 20620.2, 58.8), 'robust rishon r00-seed-000', (rs0['qubits'], rs0['cx'], rs0['t_mean'], round(se(rs0['t_eps']), 1)))
cell('T1b rishon r06-F3-006 (52,216,829.8 +- 2.2)', (52, 216, 829.8, 2.2), 'robust rishon r06-F3-006', (rsH['qubits'], rsH['cx'], rsH['t_mean'], round(se(rsH['t_eps']), 1)))
cell('T1c rishon unit -96.0%', -96.0, '(829.8-20620.2)/20620.2', round((829.8 - 20620.2) / 20620.2 * 100, 1))
cell('T1a fuzzy inner (23?,1862,5398)', (1862, 5398), 'gate-table fuzzy.general cx,t_1e6', (G['fuzzy']['general']['cx'], G['fuzzy']['general']['t_1e6']))
fu0 = R['fuzzy_ub']['r00-seed-000']; fl0 = R['fuzzy_link']['r00-seed-000']
cell('T1a fuzzy Tbar 2821.0+4*628.8 = 5336.2', 5336.2, 'robust fuzzy_ub seed0 + 4 fuzzy_link seed0', round(fu0['t_mean'] + 4 * fl0['t_mean'], 1))
fuH = R['fuzzy_ub']['r10-F1-010']; flH = R['fuzzy_link']['r02-F2-001']
cell('T1b fuzzy unit UB (83,634.4 +- 3.2)', (83, 634.4, 3.2), 'robust fuzzy_ub r10-F1-010', (fuH['cx'], fuH['t_mean'], round(se(fuH['t_eps']), 1)))
cell('T1b fuzzy link (12,628.8 +- 3.8)', (12, 628.8, 3.8), 'robust fuzzy_link r02-F2-001', (flH['cx'], flH['t_mean'], round(se(flH['t_eps']), 1)))
cell('T1b fuzzy composed (131, 3149.6)', (131, 3149.6), 'gate-table fuzzy.headline', (G['fuzzy']['headline']['cx'], G['fuzzy']['headline']['t_mean']))
cell('T2 fuzzy T-first (137, 3035.2)', (137, 3035.2), 'gate-table fuzzy.t_first', (G['fuzzy']['t_first']['cx'], G['fuzzy']['t_first']['t_mean']))
cell('T2 rishon T-first r06-F1-006 (218,829.2)', ('r06-F1-006', 218, 829.2), 'gate-table rishon.t_first', (G['rishon']['t_first']['entry'], G['rishon']['t_first']['cx'], G['rishon']['t_first']['t_mean']))
cell('T2 spinnet T-first r01-F5-001 (46,486.7)', ('r01-F5-001', 46, 486.7), 'gate-table spinnet.t_first', (G['spinnet']['t_first']['entry'], G['spinnet']['t_first']['cx'], G['spinnet']['t_first']['t_mean']))
cell('T2 twelve T-first r00-seed-001 (162,666.6)', ('r00-seed-001', 162, 666.6), 'gate-table twelve.t_first', (G['twelve']['t_first']['entry'], G['twelve']['t_first']['cx'], G['twelve']['t_first']['t_mean']))
cell('T2 twelve 21 ranked / spinnet 23 / rishon 23 / fuzzy_ub 41 / fuzzy_link 4', (21, 23, 23, 41, 4), 'robust.json entries with robust_key', tuple(sum(1 for v in R[e].values() if v.get('robust_key')) for e in ['twelve', 'spinnet', 'rishon', 'fuzzy_ub', 'fuzzy_link']))
nbad = 0
for r in rows:
    print(('PASS ' if r[4] else 'FAIL ') + r[0] + ' | report=' + str(r[1]) + ' | source: ' + r[2] + ' | value=' + str(r[3]))
    nbad += (not r[4])
print('cells', len(rows), 'fail', nbad, 'commit', subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], text=True).strip())
json.dump([dict(cell=r[0], report=r[1], source=r[2], value=r[3], ok=r[4]) for r in rows], open('results/tester/448/spot_check.json', 'w'), indent=1, default=str)
