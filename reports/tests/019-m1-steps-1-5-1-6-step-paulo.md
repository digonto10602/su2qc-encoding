# Tester report 019 — M1 steps 1.5 (build_step) + 1.6 (paulo_circuit)

- Date: 2026-11-05. Commit: `4e25639` + uncommitted changes (`src/su2plaq/circuits/twelve.py`, `src/su2plaq/metrics/cliffordt.py`, `tests/unit/test_twelve_circuits_unit.py`).
- Plan in force: `prompts/002-…` §4 rows 1.5, 1.6 (amended by prompts/003, 004). Mode: **step**. Related: reports/tests/014, 017, 018.
- Raw numbers: `results/m1_step_1_5_orders.json`, `results/m1_step_1_5_paulo.json`. Independent scripts (new, not acceptance): `tests/independent/step_1_5/{check_step_orders,check_paulo_outer,check_small_angle_scaling}.py`.

## Verdict: PASS

Steps 1.5 and 1.6 are correct. The four failing acceptance tests are the known pending ones (O1 = step 1.8, R1 x3 = step 1.9); they are not regressions and not new failures.

## Commands
```
source .../conda.sh && conda activate coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python tools/check_lock.py; ~/.claude/bin/acceptance-check
pytest -n 4 tests/acceptance/m0 tests/acceptance/m1 tests/unit -q -rA --durations=8          # incl. slow
PYTHONPATH=src python tests/independent/step_1_5/check_step_orders.py results/m1_step_1_5_orders.json
PYTHONPATH=src python tests/independent/step_1_5/check_paulo_outer.py results/m1_step_1_5_paulo.json
PYTHONPATH=src python tests/independent/step_1_5/check_small_angle_scaling.py
graphify update . ; graphify affected build_step   # -> only the 2 unit tests + M1-S1
```

## Suite results
| check | expected | got | tol | verdict |
|---|---|---|---|---|
| check_lock / acceptance-check | LOCK OK, matches acceptance-v4 | LOCK OK, PASS | - | PASS |
| m0 acceptance (34 tests, incl. slow, not rerun by builder) | all pass | 34 / 34 | - | PASS |
| m1 S1[1], S1[2] | pass | pass | 1e-10 | PASS |
| m1 T1[UE], T1[UB], T1[step] (sparse, certified) | pass | pass | n_rot eps + 1e-9 | PASS |
| m1 P1 (slow), P2 | pass | pass (P1 162 s under 4-way load) | 2e-5 | PASS |
| earlier m1: B1-B4, C1, E1 | pass | 11 / 11 pass | - | PASS |
| unit tests | pass | 160 / 160 | - | PASS |
| m1 O1 (step 1.8: dim S_o table has 3153 not 6561 entries) | PENDING | fails `3153 == 6561` | - | PENDING |
| m1 R1[UE/UB/step] (step 1.9: results/twelve/*.json missing) | PENDING | missing files | - | PENDING |

Totals: 210 passed, 4 failed (all 4 pending later steps), 0 new failures vs. report 018.

## (1) build_step vs `target(kind='step', order)` (independent, evaluator defaults, Gauss on)
| (alpha, beta) | order | op-norm error | block | leak | Gauss | engine | verdict |
|---|---|---|---|---|---|---|---|
| (0.37, 0.61) | 1 | 2.69e-13 | 1.22e-13 | 0 | 3.9e-15 | sparse, certified | PASS |
| (0.37, 0.61) | 2 | 2.74e-13 | 1.22e-13 | 0 | 9.6e-16 | sparse, certified | PASS |
| (0.91, 0.23) | 1 / 2 | 2.69e-13 / 2.71e-13 | 1.22e-13 | 0 | <= 2.6e-15 | sparse, certified | PASS |
| (1.70, 1.00) | 1 / 2 | 2.67e-13 / 2.70e-13 | 1.22e-13 | 0 | <= 1.0e-15 | sparse, certified | PASS |

Tolerance 1e-10 (leak <= 1e-10, max_leak and dirty_ancilla = 0 <= 1e-20).

Wrong-order controls (all rejected, `ok=False`; error sizes, op-norm after one global phase):
| circuit vs target | (0.37, 0.61) | (0.91, 0.23) | (1.70, 1.00) |
|---|---|---|---|
| order-1 circuit vs order-2 target | 0.5145 | 0.5600 | 1.7396 |
| order-2 circuit vs order-1 target | 0.5145 | 0.5600 | 1.7396 |
| U_E U_B (swapped composition) vs order-1 target | 0.9897 | 0.8692 | 1.6099 |

Scaling check: $\|[H_B,H_E]\|_2 = 6.000$ (limit of $\|U_BU_E-U_EU_B\|/s^2$ = 5.99938 at s=0.01, 5.99998 at s=0.002; equals reports/tests/005). $\|U_2-U_1\|\approx\tfrac12\alpha\beta\|[H_B,H_E]\| = 3\alpha\beta$: measured ratio err/($\alpha\beta$) = 2.910, 2.977, 2.994, 2.9986 at $\alpha=\beta$ = 0.2, 0.1, 0.05, 0.025; log-log slope 0.993 (-> 1). Expected and consistent with M0 step 0.5. The order-1 and swapped-composition targets differ at $O(\alpha\beta)$, so the exact errors above are far from the $10^{-10}$ threshold: the tests have teeth.

## (2) Second-order structure, gate for gate (alpha=0.37, beta=0.61)
`build_step(order=2)` equals `UE(alpha/2) . UB(beta) . UE(alpha/2)` compose-built from `build_UE`/`build_UB`: gate names, qubit indices and parameters (rounded 1e-15) identical, 241 gates (4 + 233 + 4), global phase 0 on both. Same for order 1 vs `UE(alpha) . UB(beta)` (237 gates). PASS.

## (3) paulo_circuit
| check | expected | got | verdict |
|---|---|---|---|
| plain: qubits / cx / T | 34 / 294 / 1162 | 34 / 294 / 1162; registers d12 p4 e4 w7 g3 tmp3 h1 | PASS |
| with_outer: qubits / cx / T | 50 / 294 / 1162 | 50 / 294 / 1162, no gate touches o[0..15] | PASS |
| plain vs UB(beta=1), tol 2e-5 | ok, certified | ok, certified, aer_mps, inner_span, 84.4 s | PASS |
| plain: block / leak / total | cf. report 014: 2.905e-6 / 7.851e-6 / 1.076e-5 | 2.9048e-6 / 7.8511e-6 / 1.07559e-5 | PASS (identical) |
| plain: Gauss, max_leak, dirty | cf. 014 | 1.160e-10, 6.16e-11, 8.8e-20 | PASS |
| with_outer vs UB(1): block / leak / total | same as plain | 2.9048e-6 / 7.8511e-6 / 1.07559e-5, certified, outer_bits_read 0, n_blocks 1, 81.8 s | PASS |
| with_outer Gauss, dirty | - | 1.234e-10, 2.1e-20 | PASS |
| inverse target ($U_B(-1)$) | rejected | ok=False, error 1.8186 (both) | PASS |

Differences plain vs with_outer ($\le 10^{-11}$) are Aer MPS noise (the outer register is idle, so the verdict is the same single block).

## (4) `error_bound_sum` change
- Definition: nowhere in docs/METHODS.md; prompts/002 line 169 only lists the key; the only consumers are the acceptance bound `info["error_bound_sum"] <= n_rot*eps` (M1-T1, `test_twelve_metrics.py:46`), unit tests `test_metrics_unit.py:73,75` and my older scripts. It means the certified budget: $N_{\rm rot}\varepsilon$ (sum of the per-rotation *bounds* $\varepsilon$), the same quantity `synth_tolerances` uses, not the sum of measured errors.
- Why the change was needed (reproduced): the old running float sum overshoots $n\varepsilon$ by 1 ulp in 16 of 32 tested $(\varepsilon,n)$ combinations, e.g. $n=10$ (build_step order 1) and $n=14$ (order 2) at $\varepsilon=10^{-6}$ (diff $+1.7\cdot10^{-21}$, $+3.4\cdot10^{-21}$). The strict acceptance test `<= n_rot*eps` would have failed for `step`. The new value equals $n_{\rm rot}\varepsilon$ exactly, so the change is not a weakening (same quantity, rounding removed) and not mislabelled. `synth_tolerances`, the evaluator and reports do not read the field (grep and graphify: no dependants).
- Measured per-rotation errors are still returned in `per_rotation[i]["error"]` and are all $\le\varepsilon$ (max/$\varepsilon$ = 0.48, 0.47, 0.45, 0.50 at $\varepsilon=10^{-4},10^{-6},10^{-8},10^{-10}$). Sum of measured errors for the 14 non-exact rotations of order 2: 5.89e-4, 5.81e-6, 5.51e-8, 5.05e-10, i.e. about 0.41 x $n\varepsilon$ (1.4e-3, 1.4e-5, 1.4e-7, 1.4e-9).
- Suggestion (not a failure): report the measured sum separately, as an extra key (e.g. `error_measured_sum`), and say in the Report 1 table which is which; the budget $n\varepsilon$ is what tolerances use, the measured sum is what is actually realised (the realised op-norm error of the whole synthesised circuit is smaller still, e.g. 1.854e-6 for U_B at $\varepsilon=10^{-6}$ in report 018). Also worth documenting the key in METHODS.

## (5) Resource tables, `build_step(0.37, 0.61)` (34 qubits, 22 ancillas; with_outer: 50 qubits, same counts)
| order | cx | n_rot | T_fixed | depth |
|---|---|---|---|---|
| 1 | 294 | 10 (6 UB + 4 UE) | 312 | 292 |
| 2 | 294 | 14 (6 UB + 8 UE) | 312 | 293 |

$T(\varepsilon)=T_{\rm fixed}+\sum_{\rm rot}T_r$ (pygridsynth); estimate = $T_{\rm fixed}+3N\log_2(1/\varepsilon)$; Qiskit level-0 compile `t_qiskit` and its depth for reference:
| order | eps | T_rot | T_total | estimate | t_qiskit | depth_qiskit |
|---|---|---|---|---|---|---|
| 1 | 1e-4 | 424 | 736 | 710.6 | 700 | 973 |
| 1 | 1e-6 | 640 | 952 | 909.9 | 898 | 1348 |
| 1 | 1e-8 | 836 | 1148 | 1109.3 | 1108 | 1702 |
| 1 | 1e-10 | 1040 | 1352 | 1308.6 | 1324 | 2065 |
| 2 | 1e-4 | 584 | 896 | 870.1 | 864 | 1083 |
| 2 | 1e-6 | 912 | 1224 | 1149.1 | 1174 | 1527 |
| 2 | 1e-8 | 1180 | 1492 | 1428.2 | 1436 | 1904 |
| 2 | 1e-10 | 1456 | 1768 | 1707.2 | 1720 | 2340 |

## Failures and pending
No failures. Pending (not failures in step mode): M1-O1 (`3153 == 6561`: known, step 1.8), M1-R1 x3 (results/twelve/{UE,UB,step}.json absent: step 1.9). At the milestone gate these count as FAIL.

## Notes
- The `outer_touched` field for the plain Paulo circuit in the results JSON lists indices 12-27 only because Paulo's own p/e/w/g/tmp/h registers occupy those indices in the 34-qubit layout; it is not an outer-register touch (the with_outer circuit touches none of o[0..15]).
- Wall times (84 s / 82 s for the aer_mps evaluate) match report 014 (84 s).
- The working tree was dirty; the three modified files are the step-1.5/1.6 change set. I added only tests/independent scripts and results files.
