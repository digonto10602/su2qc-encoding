# Tester report 012 - M0 step 0.9 (metrics: CX/depth/N_rot/T_fixed, pygridsynth T(eps), Qiskit CT, synthesize)

- Date: 2026-11-04. Commit: `803d56a` (step 0.9 files uncommitted: `src/su2plaq/metrics/{logical,cliffordt}.py`, `tests/unit/test_metrics_unit.py`).
- Prompt in force: `prompts/003-gauss-tolerance-synthesised-circuits-engine-policy.md` on top of `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` (step 0.9, §2.8, §3). Mode: step.
- Related: `reports/tests/009-011` (evaluator). Raw numbers: `results/tester_012_metrics_step09.json`; scripts: `results/tester_012_scripts/t1..t4.py` (seed 20261104; transpiler seeds 20261104 / 12345).

## Commands
```
pytest -n auto tests/acceptance/m0/test_metrics.py          # 5 passed
pytest -n auto tests/unit                                    # 127 passed
pytest -n auto -m "not slow" tests/acceptance/m0             # 31 passed, 1 failed = M0-R1 (PENDING: NotImplementedError save_result)
pytest --collect-only -q tests/acceptance                    # 84 collected, clean
python tools/check_lock.py                                   # LOCK OK
~/.claude/bin/acceptance-check                               # PASS (matches acceptance-v3)
graphify update . ; graphify affected logical_metrics ; graphify affected synthesize
python -I results/tester_012_scripts/t1.py ... t4.py         # independent checks below
```
`graphify affected`: `logical_metrics` -> `t_table`, `test_M1_P2_port_reproduces_counts` (pending, M1); `synthesize` -> nothing yet (first consumer is step 1.7).

## Verification table
| check | expected | got | tol | verdict |
|---|---|---|---|---|
| acceptance M0-M1 macro costs, M0-M2[1e-4,1e-6,1e-8], M0-M3 | pass | 5/5 pass | - | PASS |
| unit tests (all) | pass | 127/127 | - | PASS |
| non-slow m0 | only M0-R1 pending | 31 pass, M0-R1 = `NotImplementedError: save_result is not built yet` | - | PASS (1 PENDING) |
| collect / check_lock / acceptance-check | clean / OK / PASS | 84 collected / LOCK OK / PASS (acceptance-v3); no diff in `tests/acceptance` | - | PASS |
| (1) 30 seeded random circuits (3-5 qubits, 8-24 gates from h,s,sdg,t,tdg,x,z,rz,p,cx,cz,swap,ccx,rccx,ch,crz,crx,cry,cp,ccz; 30 % of angles are multiples of $\pi/4$): cx, depth, n_rot, t_fixed vs own recount of Qiskit `count_ops`/`depth` after the same level-0 lowering; `gates` dict equal | 0 mismatches | 0 / 30 mismatches | exact | PASS |
| (1b) lowering unitary-equal to the input up to global phase, same 30 circuits | small | max 3.8e-15 | 1e-10 | PASS |
| (1c) macro table measured (CX, T_fixed, N_rot; depth): ccx (6,7,0; 11), rccx (3,4,0; 9), ccz (6,7,0; 12), swap (3,0,0; 3), ch (1,2,0; 7), crz (2,0,2; 4), crx (2,0,2; 6), cp (2,0,3; 5), cz (1,0,0; 3) | METHODS §7 | identical to METHODS; each lowering unitary-equal to its gate, max err 6.7e-16 | exact | PASS |
| (2) 24 seeded generic angles $\theta\in[-\pi,\pi]$ x 4 eps: word error (own 2x2 product, $\min_\phi\|U_w-e^{i\phi}R_z(\theta)\|_2$) $\le\varepsilon$ | 0 violations | 0 / 96; max error = 0.50 eps (5.0e-5, 5.0e-7, 4.96e-9, 4.95e-11) | eps | PASS |
| (2b) `pygridsynth_word` equals an independent direct `gridsynth_gates` call | equal | 96/96 | exact | PASS |
| (3) `synthesize` on 12 seeded circuits (2-4 qubits, 3-5 non-Clifford rotations incl. crz, cp, rx, ccx, plus exact rz($3\pi/4$), rz($\pi/2$)) x eps in {1e-3, 1e-6, 1e-9}: $\min_\phi\|U-e^{i\phi}V\|_2\le\sum$ actual word errors $\le N_{\rm rot}\varepsilon$ | holds | 36/36; max opdist/($N_{\rm rot}\varepsilon$) = 0.44; output gates only {cx,h,s,sdg,t,tdg,x,z}; T of output circuit = `t_fixed + t_rot` exactly (36/36); n_rot = logical_metrics n_rot | - | PASS |
| (3b) error definition: `word_error` = operator 2-norm after one optimal phase = what gridsynth guarantees and what the prompts/003 §2 triangle-inequality budget $N_{\rm rot}\varepsilon$ assumes | same | same (checked by (2), (3)) | - | PASS |
| (4) `ct_compile` on Paulo's uncompiled circuit (rebuilt by executing cells 3-23 of `refs/paulo/optimized_plaquette_dontcare_lowT.ipynb`; fixed structural T = 296 as in his notebook), eps=1e-6, level 3, seed 12345 | cx 294, T 1162 | cx 294, T 1162, depth 2549, 34 qubits; gate_counts identical to his metadata (h 1155, t 1027, s 504, cx 294, tdg 135, sdg 92) | exact | PASS |
| (4b) determinism: two runs, same seed | identical | identical | exact | PASS |
| (4c) `logical_metrics` of the same circuit | cx 294, T_fixed 296 | cx 294, T_fixed 296, n_rot 14, depth 391, ancilla 22 | exact | PASS |

## T(eps): measured vs $3\log_2(1/\varepsilon)$ vs the "+3 ln eps" form (24 angles per eps, seed 20261104)
| $\varepsilon$ | T per rotation: mean / min / max | $3\log_2(1/\varepsilon)$ | offset mean [min, max] | $3\ln\varepsilon$ | acceptance band |
|---|---|---|---|---|---|
| 1e-4  | 42.58 / 38 / 48   | 39.86 | +2.72 [-1.86, +8.14] | -27.63 | [35.9, 61.1] |
| 1e-6  | 62.83 / 56 / 66   | 59.79 | +3.04 [-3.79, +6.21] | -41.45 | [55.8, 82.7] |
| 1e-8  | 82.58 / 78 / 86   | 79.73 | +2.86 [-1.73, +6.27] | -55.26 | [75.7, 103.9] |
| 1e-10 | 101.92 / 94 / 106 | 99.66 | +2.26 [-5.66, +6.34] | -69.08 | [95.7, 124.8] |

Reading: $T_r\approx3\log_2(1/\varepsilon)+3\pm4$. Evaluated literally, "$3\ln\varepsilon$" is negative ($-41.45$ at $10^{-6}$) and is 104 away from the measured 62.8. With the sign fixed, $3\ln(1/\varepsilon)=41.45$ still underestimates by the factor $\ln 2=0.693$ (the base must be 2), and it is per rotation, not once per circuit. On Paulo's circuit (14 rotations, $\varepsilon=10^{-6}$): $T_{\rm fixed}=296$; $T_{\rm est}=296+14\cdot59.79=1133.1$; pygridsynth total $296+884=1180$; Qiskit CT 1162.

## Notes (not failures)
1. The acceptance band lower edge $3\log_2(1/\varepsilon)-4$ is violated once at $\varepsilon=10^{-10}$ (T=94 < 95.7; 1 of 24 angles). $10^{-10}$ is not an acceptance parametrisation (only 1e-4, 1e-6, 1e-8; all 24 angles are inside the band there), but `t_table` defaults include 1e-10, so a future band assertion there could fail. METHODS' "measured 42-44 / 62-64 / ..." refers to 5 angles; with 24 angles the spread is wider (38-48, 56-66, 78-86, 94-106).
2. `t_table()["t_qiskit"]` runs `ct_compile` on the level-0 lowered circuit, giving 1096 T at $10^{-6}$ for Paulo's circuit, whereas `ct_compile` on the original circuit gives his 1162 (difference 66). Both are valid Qiskit runs; do not compare the `t_table` Qiskit column to his metadata. pygridsynth total minus `t_qiskit`(lowered) = 84 = $6\times14$, exactly at the +-6 per rotation criterion (the M3 test checks that only per single rotation).
3. `ct_compile` takes 0.1 s on Paulo's circuit (Qiskit caches rz syntheses).
4. M1/M2 acceptance tests needing later steps fail (missing `results/twelve/*.json`, codec, ...): PENDING, outside step 0.9. M1-T1 (the consumer of `t_table`/`synthesize`) and M1-P2 are among them, so `synthesize` plus evaluator re-verification is not exercised yet (planned step 1.7).

## Failures
None.

VERDICT: PASS (acceptance lock intact; 5/5 step acceptance, 127/127 unit, 0 new failures; 1 PENDING in m0 (M0-R1); later-step M1/M2 tests pending).
