# Report 301 — M9 gate, full mode, part 2 (tester)

Date: 2026-11-06. Commit: `5669592` (branch `m9-fuzzy`, HEAD committed; untracked M10 builder files and `results/fuzzy/compressed_step.json` ignored, `tests/acceptance/m10` not run). Plan in force: `prompts/300` + `prompts/301` (`prompts/302` is the M10 plan, not run). Acceptance lock: `acceptance-v11`. Mode: full, part 2 (R1, T1, `O1_shared_table_file`, regression after audit fixes NB-1/NB-2, independent recomputation). Env: `~/venvs/coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`. Part 1: `reports/tests/300-m9-gate-full-part1.md` (PASS). Graphify: `graphify update .` run, no code-graph topology change; `affected` is covered because the full unit suite and all four m9 acceptance files that exercise `verify.py`/`gauss.py` were run. Benchmark: `reports/benchmarks/300-m9-fuzzy-benchmark.md`.

## Commands and results

| # | command | expected | got | wall | verdict |
|---|---|---|---|---|---|
| 1 | `python tools/check_lock.py && ~/.claude/bin/acceptance-check` | lock OK | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v11` | <1 s | PASS |
| 2 | `pytest -n 8 tests/unit -q` (8 instead of 16 because T1 ran on the other 8 cores of the 16-core share) | all pass | 486 passed, 0 failed (part 1 had 453; +33 new unit tests) | 140 s | PASS |
| 3 | `pytest -n 4 tests/acceptance/m9/test_fuzzy_results.py tests/acceptance/m9/test_fuzzy_observables.py -q` | all pass | 7 passed (R1 x5, O1 `definitions_and_identities`, O1 `shared_table_file`), 0 failed, 0 pending | 1.9 s | PASS |
| 4 | `pytest -n 8 -m slow tests/acceptance/m9/test_fuzzy_metrics.py -q` (T1) | all pass | 4 passed: step 1500.4 s, UB 4.27 s, UE 0.82 s, UK 0.78 s | 1501 s (25:01) | PASS |
| 5 | `pytest -n 1 tests/acceptance/m9/test_fuzzy_circuits.py -q -k "S1 or K1 or B1"` (rerun, `verify.py` changed) | all pass | 12 passed: S1 x5 (63 to 85 s each, `outer_row_and_gauss_on_outputs` 10.5 s), K1 x4, B1 x3; peak RSS 134.7 GB | 308 s | PASS |
| 6 | independent recomputation, see below | match | match | 2 s | PASS |

M9 acceptance accounting (28 collected tests): part 1 ran 18 (S1 5 + 13 others), part 2 ran T1 4 + R1 5 + `shared_table_file` 1 = 10; steps 3 to 5 re-ran R1/O1 (7), T1 (4), S1/K1/B1 (12). Every one of the 28 m9 tests has passed on this code base (S1/K1/B1 rerun after the `verify.py` change at the HEAD under test; D1, D2, C1 and the O1 identities were last run in part 1 at `8e71c38`, before the NB-1/NB-2 commit `530dc1a`, and are exercised again only by the unit suite here). Pending (raising `NotImplementedError`): 0. M0 to M2 acceptance (regression) was not re-run in this part; the NB-1/NB-2 commit touched only `src/su2plaq/fuzzy/verify.py` and `gauss.py`, and the unit suite (486) passes.

Side effects: none on tracked files (`git status` shows no modified tracked file).

## Step 6: independent recomputation from source (seed-free, deterministic)

Method: rebuild each circuit from `su2plaq.circuits.fuzzy` at $(\alpha,\beta)=(0.37,0.61)$, $\kappa_2=0.185$, lower the whole circuit with `qiskit.transpile(basis=[cx,h,s,sdg,t,tdg,x,z,rz], optimization_level=0, seed 1)`, count CX and T/Tdg there, count $N_{\rm rot}$ as the `rz` gates whose angle is not a multiple of $\pi/2$ (the rest come from fixed-angle lowering of controlled gates), and call `pygridsynth.gridsynth_gates(theta, eps=10^{-6})` directly on every `rz` angle, counting the `T` letters in the word (not through `cliffordt.t_table`). Compared with `results/fuzzy/step.json` and `UB.json` (generated at commit 8e71c38, file `metrics`).

| check | expected (json) | got (independent) | tolerance | verdict |
|---|---|---|---|---|
| step order 1: CX | 1862 | 1862 | exact | PASS |
| step order 1: $N_{\rm rot}$ | 56 | 56 (64 `rz`, 8 of them Clifford angles) | exact | PASS |
| step order 1: $T_{\rm fixed}$ | 1826 | 1826 (1036 T + 790 Tdg) | exact | PASS |
| step order 1: $T_{\rm rot}(\epsilon=10^{-6})$ | 3572 | 3572 | exact | PASS |
| step order 1: $T_{\rm total}(10^{-6})$ | 5398 | 5398 | exact | PASS |
| UB: CX | 1718 | 1718 | exact | PASS |
| UB: $N_{\rm rot}$ | 16 | 16 (24 `rz`, 8 Clifford angles) | exact | PASS |
| UB: $T_{\rm fixed}$ | 1826 | 1826 | exact | PASS |
| UB: $T_{\rm rot}(10^{-6})$ | 996 | 996 | exact | PASS |
| UB: $T_{\rm total}(10^{-6})$ | 2822 | 2822 | exact | PASS |

Plus the determinism check from the benchmark run: `scripts/m9_results.py --jobs 14` regenerated into a scratch directory gives identical numbers in all seven JSON files (floats compared at relative $10^{-9}$, excluding timings, provenance and file hashes) and byte-identical `.qpy` for UE, UK, UB, step and step_order2. The exact-angle verification blocks in the committed JSON: UE err $4.3\times10^{-16}$, UK $1.5\times10^{-15}$, UB $3.8\times10^{-14}$, step (sampled, 40 inputs, layers mode) $1.05\times10^{-14}$ with Gauss residual $5.2\times10^{-15}$, all below $10^{-10}$; every `ok` flag (48) is true. Two numerically cross-checked at the same time in the benchmark process: `verify_plaquette` and `verify_step_samples` (orders 1 and 2) reproduce the JSON errors exactly.

## Notes (not failures)

1. `results/fuzzy/*.json` provenance records `git_commit 8e71c38`, the commit at which the script was run; HEAD is `5669592`. The only intervening source change is the NB-1/NB-2 commit, and regeneration at HEAD gives identical numbers, so the JSON is current.
2. T1 on the step takes 25 min because the test synthesises the whole circuit at once and re-verifies without layer metadata; the script uses `synthesize_layered` and does the full result set in 74 s on 14 workers.
3. S1 peak RSS 134.7 GB needs `-n 1` (known).

## Verdict

PASS. Counts for this part: 486 unit + 7 + 4 + 12 = 509 pytest tests passed, 0 failed, 0 pending; independent recomputation 10 of 10 numbers equal; acceptance-check PASS (acceptance-v11). No new failures vs. report 300. Raw numbers: `results/tester/301-m9-gate-full-part2.json`, `results/tester/301-independent-recompute.json`, logs in `results/tester_logs/301_*.log`.
