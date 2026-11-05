# Test report 020 — M1 steps 1.7 (T tables, `error_measured_sum`) + 1.8 (6561-entry $\dim S_o$ table)

- Date: 2026-11-05
- Commit: 35cfeb6 + uncommitted (`src/su2plaq/exact/physical.py`, `src/su2plaq/metrics/cliffordt.py`, `tests/unit/test_metrics_unit.py`, `tests/unit/test_physical_unit.py`)
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` §4 rows 1.7, 1.8 (+ prompts/003, 004 tolerances)
- Mode: step
- Related: `reports/tests/004` (earlier $\dim S_o$ recount), `reports/tests/012`, `018`, `019`
- Raw numbers (all with commit, parameters): `results/m1_step_1_7_ttable_{UE,UB,step1,step2}.json`, `results/m1_step_1_8_so_table_independent.json`, `results/m1_step_1_7_prune_analysis.json`
- Independent scripts (added by the tester, not collected by pytest): `tests/independent/step_1_7_1_8/{check_so_table,check_ttable,check_prune}.py`

## Verdict: PASS (with one tolerance question for Digonto / planner: `TOL_PRUNE`, section C)

Counts: passed 51 (m0 + m1, incl. slow) + 161 unit; failed 0 real; the 3 known `M1-R1` (`results/twelve/{UE,UB,step}.json` missing, step 1.9) are PENDING; m2: 31 fail with "... is not built yet" (PENDING), 1 passes. New failures vs report 019: none.

## Commands

```
source ~/anaconda3/etc/profile.d/conda.sh && conda activate coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected "s_o_dims" ; graphify affected "synthesize"
pytest -n auto tests/unit -q                                        # 161 passed, 58 s
pytest -n auto -m "not slow" tests/acceptance/m0 tests/acceptance/m1 tests/acceptance/m2 -q
pytest -n 8 tests/acceptance/m0 tests/acceptance/m1 -q --durations=12 -rf     # incl. slow; 51 passed, 3 failed (R1), 306 s
pytest -n 8 tests/acceptance/m2 -q --tb=line -rf                    # 31 "not built yet", 1 passed
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
python tests/independent/step_1_7_1_8/check_so_table.py             # ~1 min
python tests/independent/step_1_7_1_8/check_ttable.py UE | UB | "step 1" | "step 2"      # (alpha,beta)=(0.37,0.61), 4 eps each
python tests/independent/step_1_7_1_8/check_prune.py                # ~2 min
```

`graphify affected s_o_dims`: only `test_inner_span_rank_bounds` and the new `test_outer_dont_care_table_...` (both ran, pass). `graphify affected synthesize`: none found by graph (callers: `t_table`/tests; covered by M1-T1 and `test_metrics_unit`).

## A. Acceptance / unit / lock

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| unit tests | all pass | 161 passed | - | PASS |
| M1-T1 `[UE]`, `[UB]`, `[step]` (all params, incl. $\varepsilon=10^{-6}$ synth verify, `certified`, engine sparse) | pass | pass (14.7 s, 13.9 s, ...) | per test | PASS |
| M1-O1 (`test_M1_O1_outer_dont_care_table`) | pass | pass (123 s) | exact / 1e-10 | PASS |
| m0 (34 tests incl. slow) | pass | pass | - | PASS |
| m1 except R1 (E1, B1, S1, P1 Paulo QPY, codec, ...) | pass | pass (P1: 163 s) | - | PASS |
| M1-R1 ×3 | PENDING (step 1.9) | `results/twelve/{UE,UB,step}.json` missing | - | PENDING |
| m2 | PENDING | 31 × "not built yet", 0 other errors | - | PENDING |
| `check_lock.py`, `acceptance-check`, collect-only | pass | LOCK OK; "matches acceptance-v4"; 86 collected | - | PASS |

## B. Independent: $\dim S_o$ table (step 1.8)

Own script (geometry, local index convention, SVD rank per outer key all rebuilt; `su2plaq` used only to read basis keys/amplitudes and the objects under test). Outer pattern = per outer link local index $0$ or the two $j=\tfrac12$ states with the far-end magnetic number fixed to $+\tfrac12$ (CG indices $\{0,1,3\}$ for links starting at a corner, $\{0,1,2\}$ for links ending at a corner; Paulo convention via my own permutation $[0,4,3,2,1]$: $\{0,2,4\}$ / $\{0,3,4\}$).

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| number of admissible outer patterns (own $3^8$ enumeration), CG and Paulo | 6561 | 6561 / 6561 | exact | PASS |
| `outer_patterns(basis)` == my enumeration, CG and Paulo | equal | equal / equal | exact | PASS |
| outer keys of any physical state outside my set | 0 | 0 / 0 | exact | PASS |
| `s_o_dims(basis)` == my table, entry by entry (6561), CG and Paulo | equal | equal / equal | rank tol $10^{-9}$ rel. | PASS |
| histogram of $\dim S_o$ | 0:3408, 1:976, 2:1073, 3:392, 4:320, 5:280, 8:64, 9:32, 17:16 | identical in both conventions | exact | PASS |
| closed pattern (key 0) / max | 2 / 17 | 2 / 17 | exact | PASS |
| rank of stacked inner components | 625 | 625 (CG), 625 (Paulo); smallest kept singular value 0.1111, next 0 | gap | PASS |
| `inner_span(basis)` shape | (625, 625) | (625, 625) | - | PASS |
| CG table == Paulo table under my own outer-key relabelling | equal | equal | exact | PASS |

## C. Independent: T tables and synth → evaluate (step 1.7), $(\alpha,\beta)=(0.37,0.61)$

Columns "T" = $T_{\rm total}$ from `t_table`; "T (circuit)" = number of t+tdg gates in the synthesised circuit; "T (own)" = $T_{\rm fixed}$ + my direct `gridsynth_gates` word count. All three agree in all 16 rows, and equal the builder's table exactly (tolerance: exact):

| circuit | $\varepsilon=10^{-4}$ | $10^{-6}$ | $10^{-8}$ | $10^{-10}$ | $n_{\rm rot}$ | $T_{\rm fixed}$ |
|---|---|---|---|---|---|---|
| $U_E$ | 176 | 256 | 328 | 416 | 4 | 0 |
| $U_B$ | 560 | 696 | 820 | 936 | 6 | 312 |
| step, order 1 | 736 | 952 | 1148 | 1352 | 10 | 312 |
| step, order 2 | 896 | 1224 | 1492 | 1768 | 14 | 312 |

(`t_qiskit` for reference: UE 172/236/328/380; UB 536/670/780/912; step1 700/898/1108/1324; step2 864/1174/1436/1720; all within 10 % of $T_{\rm total}$.)

`error_measured_sum` vs. my own 2×2 computation (pygridsynth called directly, own gate matrices, $\min_\phi\|U_{\rm word}-e^{i\phi}R_z(\theta)\|_2$ by scan + bounded minimisation) and the bound $n_{\rm rot}\varepsilon$:

| circuit | $\varepsilon$ | `error_measured_sum` | own $\sum_r$ error | $n_{\rm rot}\varepsilon$ | result |
|---|---|---|---|---|---|
| UE | 1e-4 / 1e-6 / 1e-8 / 1e-10 | 8.730e-5 / 1.5298e-6 / 1.3471e-8 / 1.0787e-10 | 8.730e-5 / 1.5298e-6 / 1.3471e-8 / 1.0788e-10 | 4e-4 / 4e-6 / 4e-8 / 4e-10 | PASS |
| UB | same | 2.0567e-4 / 2.3336e-6 / 1.9755e-8 / 1.6272e-10 | same to 5 digits (1.6273e-10) | 6e-4 / 6e-6 / 6e-8 / 6e-10 | PASS |
| step 1 | same | 2.9297e-4 / 3.8634e-6 / 3.3226e-8 / 2.7059e-10 | same (2.7061e-10) | 1e-3 / 1e-5 / 1e-7 / 1e-9 | PASS |
| step 2 | same | 5.8939e-4 / 5.8076e-6 / 5.5117e-8 / 5.0501e-10 | same (5.0504e-10) | 1.4e-3 / 1.4e-5 / 1.4e-7 / 1.4e-9 | PASS |

Maximum absolute difference (project − own) $\le 3\times10^{-14}$ (float64 noise in a 2-norm of a nearly-unitary difference; tolerance $10^{-12}$ abs). `error_measured_sum` $=\sum$ `per_rotation[error]` exactly, and $\le n_{\rm rot}\varepsilon$ in all 16 rows (ratio 0.22–0.42; the maximum single-word error is $\le\varepsilon$ in all rows).

Synthesised circuit re-verified with `synth_tolerances` (tol_err $=n_{\rm rot}\varepsilon+10^{-9}$, tol_gauss the same), engine sparse, all rows `certified=True`:

| circuit | $\varepsilon$ | ok / reason | op_norm_error (block + dropped + leak) | tol_err | max Gauss | max col. dropped | total dropped |
|---|---|---|---|---|---|---|---|
| UE | 1e-4 | ok | 1.230e-4 (1.06e-4 + 1.66e-5) | 4.0e-4 | 6.8e-6 | 2.4e-15 | 6.1e-14 |
| UE | 1e-6 | ok | 2.141e-6 | 4.0e-6 | 1.1e-7 | 1.8e-13 | 4.6e-12 |
| UE | 1e-8 | ok | 1.960e-8 | 4.1e-8 | 2.4e-9 | 4.7e-17 | 1.2e-15 |
| UE | 1e-10 | ok | 1.549e-10 | 1.4e-9 | 1.9e-11 | 3.0e-21 | 7.5e-20 |
| UB | 1e-4 / 1e-6 / 1e-8 / 1e-10 | ok ×4 | 1.923e-4 / 1.854e-6 / 1.926e-8 / 1.763e-10 | 6.0e-4 / 6.0e-6 / 6.1e-8 / 1.6e-9 | $\le2.1\times10^{-15}$ | $\le1.3\times10^{-14}$ | $\le2.1\times10^{-13}$ |
| step 1 | 1e-4 / 1e-6 / 1e-8 / 1e-10 | ok ×4 | 2.383e-4 / 3.243e-6 / 2.857e-8 / 2.257e-10 | 1.0e-3 / 1.0e-5 / 1.0e-7 / 2.0e-9 | 6.8e-6 / 1.1e-7 / 2.4e-9 / 1.9e-11 | 6.8e-14 / **4.7e-13** / 1.3e-14 / 1.3e-14 | 8.2e-13 / 9.2e-12 / 2.2e-13 / 2.3e-13 |
| step 2 | **1e-4** | **FAIL `pruning_bound`** | 5.774e-4 (block 4.10e-4 + leak 1.67e-4 + dropped 3.9e-11) | 1.4e-3 | 6.6e-5 | **2.63e-12** | 3.88e-11 |
| step 2 | 1e-6 / 1e-8 / 1e-10 | ok ×3 | 3.485e-6 / 5.149e-8 / 4.997e-10 | 1.4e-5 / 1.41e-7 / 2.4e-9 | 5.5e-8 / 5.6e-9 / 6.0e-11 | 1.7e-13 / 1.3e-14 / 1.5e-14 | 3.9e-12 / 2.2e-13 / 2.3e-13 |

Every op_norm_error is below `tol_err` (ratio op_norm_error/tol_err 0.11–0.48; the $\sqrt2$ sum-vs-RSS stop condition is nowhere approached). Gauss $\le n_{\rm rot}\varepsilon+10^{-9}$ in all rows. The only non-ok verdict is step order 2 at $\varepsilon=10^{-4}$, rejected solely by the fixed `TOL_PRUNE`; with that check ignored the verdict would be ok (5.8e-4 $\le$ 1.4e-3, Gauss 6.6e-5 $\le$ 1.4e-3).

Step 1.7 is complete in the sense of the plan row: bound holds, pygridsynth vs. Qiskit T within 10 % (largest deviation 8.7 %: UE at $10^{-10}$, 380 vs 416; step 1 at $10^{-6}$: 898 vs 952 = 5.7 %).

### Pruning cap `TOL_PRUNE = 1e-12`: reproduced, and my assessment (not a code change)

Reproduced: step order 2, $\varepsilon=10^{-4}$: `max_dropped_l2` $=2.629\times10^{-12} > 10^{-12}$ → `pruning_bound`, while `op_norm_error` $=5.8\times10^{-4}\le1.4\times10^{-3}$, and the dropped part ($3.9\times10^{-11}$ total) is already inside `op_norm_error` (`evaluator.py:458`). Experiments on the 625 inner codes (34-qubit circuit, `run_batch`, `PRUNE_REL` varied; the reference is `PRUNE_REL`$=10^{-17}$, since 0 exceeds a $6\times10^{7}$ amplitude cap from float noise):

| $\varepsilon$ | `PRUNE_REL` | certified bound, max column | actual max column difference to reference | actual/bound | stored amplitudes |
|---|---|---|---|---|---|
| 1e-4 | 1e-14 (production) | 2.63e-12 | 2.5e-13 | 0.10 | 136 593 (ref 208 102) |
| 1e-4 | 1e-15 | 4.2e-14 | 5.7e-15 | 0.08 | 169 689 |
| 1e-4 | 1e-16 | 1.5e-14 | 5.0e-15 | 0.19 | 170 974 |
| 1e-6 | 1e-14 | 1.75e-13 | 6.2e-14 | 0.31 | 14 437 (ref 91 670) |
| 1e-6 | 1e-15 | 1.71e-13 | 1.7e-14 | 0.10 | 63 730 |

Also, at $\varepsilon=10^{-4}$, 42 913 of the 208 102 stored amplitudes lie below $10^{-14}$ of the column maximum (largest $9.3\times10^{-15}$, total L2 $3.5\times10^{-13}$): these are real, second-order products of the gridsynth approximation errors plus rounding noise, not a bug.

Assessment (my opinion; a tolerance question for Digonto / planner):
1. For a synthesised circuit the check is redundant and arbitrary: the certified dropped weight already enters the budget, and the budget is $n_{\rm rot}\varepsilon+10^{-9}\ge10^{-9}$; $2.6\times10^{-12}$ is $2\times10^{-9}$ of the $1.4\times10^{-3}$ budget. The real pruning error is ten times smaller still ($2.5\times10^{-13}$ per column).
2. The failure is perverse: it rejects the loosest tolerance (largest approximation errors → most small second-order amplitudes), and the dropped bound is not monotonic in $\varepsilon$ (1e-4: 2.6e-12; 1e-6: 1.7e-13 for the same circuit).
3. The headroom is thin where it matters: at $\varepsilon=10^{-6}$ (the M2 loop value) step order 1 already sits at $4.7\times10^{-13}$ (factor 2.1 below the cap). A compressed M2 candidate with a different structure could exceed $10^{-12}$ at the loop's own $\varepsilon$ and be wrongly rejected as `pruning_bound` although it is correct.
4. Even for exact-angle circuits (tol_err $=10^{-10}$) the dropped bound is part of `op_norm_error`, so a separate fixed cap is only a stricter, independent guard.
Suggested options (not implemented): (a) drop the separate `pruning_bound` rejection and rely on `op_norm_error` (it contains `dropped_total`); or (b) make the cap relative, e.g. `dropped_total` $\le 10^{-2}\,$`tol_err` (gives $10^{-12}$ for exact circuits, $\ge10^{-11}$ for synthesised ones, a Gu-style loop will never see a false reject). Note `dropped_total` sums over outer groups and sqrt-sums over 625 columns, while `TOL_PRUNE` compares the per-column max; if option (b) is chosen the same quantity should be on both sides. Also: if step 1.9 stores verdicts for the full $\varepsilon$ grid, step order 2 at $10^{-4}$ will fail unless this is resolved; at $10^{-6}$ (what M1-T1 and M1-R1 use) it passes.

## D. Residual risks / notes
- The new unit test `test_outer_dont_care_table_...` pins the histogram and `outer_patterns`; independently confirmed. `s_o_dims(to_convention(b,"paulo"))` also has 6561 entries (confirmed).
- `error_measured_sum` excludes exact $\pi/4$-multiple rotations (documented, matches `n_rot`).
- Sparse peak memory not measured (benchmark mode only).
