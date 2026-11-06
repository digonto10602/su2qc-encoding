# Benchmark 300 — M9 fuzzy circuits (baseline, first fuzzy benchmark)

Date: 2026-11-06. Commit: `5669592` (branch `m9-fuzzy`). Plan in force: `prompts/300` + `prompts/301` (auditor PASS WITH NOTES, NB-1/NB-2 fixed). Host: AMD Threadripper 3960X (48 threads, 251 GB), shared with other users and one concurrent M10 builder. Env: `~/venvs/coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, CPU only (no GPU path exists for the fuzzy code). Parameters: $\alpha=0.37$, $\beta=0.61$, $\kappa_2=r\alpha/2=0.185$ ($r=1$); `verify_step_samples` default sizes (n_random=32, n_phys=8, seed 20261104, 40 inputs); `verify_link` on `link_UE(0.37)` vs `targets.UE_link`; `verify_plaquette` on `build_UB(0.61)` vs `targets.UB_row`. One fresh Python process per item, wall time measured with `time.perf_counter` around the call only (imports excluded); peak RSS from `resource.getrusage`. No earlier fuzzy benchmark exists, so there is no regression comparison; this file is the baseline. Raw: `results/tester/301-m9-gate-full-part2.json`, `results/tester_logs/301_bench_single_run{1,2}.jsonl`, `results/tester_logs/301_m9_results_bench.log`.

## Single-process timings (1 repeat, run 2 is the cleaner one)

Run 1 was taken while T1 (8 workers) and the S1 tests (135 GB) ran, host load average about 22. Run 2 was taken while `m9_results.py --jobs 14` ran, load average about 5 (the host was otherwise quiet).

| item | size | run 1 wall (s) | run 2 wall (s) | peak RSS (MB) | physics output |
|---|---|---|---|---|---|
| `build_UB(0.61)` | 23 qubits, 1718 CX, 16 rot | 0.580 | 0.539 | 111 | CX 1718, $N_{rot}$ 16, T_fixed 1826 |
| `build_step(order=1)` | 23 qubits, 1862 CX | 0.584 | 0.544 | 111 | CX 1862, $N_{rot}$ 56 |
| `build_step(order=2)` | 2006 CX | 0.613 | 0.544 | 111 | (not in step.json; part 1: CX 2006) |
| `verify_link` (16x16) | 4 data qubits | 0.0024 | 0.0024 | 106 | ok, err $4.29\times10^{-16}$ |
| `verify_plaquette` (256x256 row block) | 8 row qubits + 7 ancillas | 0.612 | 0.587 | 194 | ok, err $3.81\times10^{-14}$ |
| `verify_step_samples` order 1 | 16 inner qubits, 40 inputs, mode `layers` | 26.81 | 23.81 | 1050 | err $1.05\times10^{-14}$, Gauss $5.16\times10^{-15}$, leak 0 |
| `verify_step_samples` order 2 | same | 27.60 | 24.04 | 1046 | err $1.66\times10^{-14}$, Gauss $5.17\times10^{-15}$, leak 0 |

Run-to-run spread 3 to 13 % (shared host); physics output bit-identical in both runs. Build times are dominated by the plaquette row (the step builds the same UB inside), so build_step is about build_UB.

## `scripts/m9_results.py --jobs 14` (full run, output redirected to a scratch directory so the committed `results/fuzzy/` is untouched)

| quantity | value |
|---|---|
| wall time | 74.4 s (1:14) |
| user CPU time | 408 s (about 5.5 cores average utilisation of the 14-process pool) |
| peak RSS (main process) | 1.11 GB |
| output | 7 JSON, 5 QPY, 5 QASM3 files |
| physics output vs committed `results/fuzzy/*.json` | no difference in any field (floats compared at relative $10^{-9}$; excluded keys: seconds, provenance, files) in UE, UK, UB, step, outer_row, shared_observables, splitting; the five `.qpy` files are byte-identical; all 48 `ok` flags in UE/UK/UB/step/outer_row are true |

Deterministic: regeneration reproduces the committed numbers.

## Reference durations from the gate (same commit, loaded host, from pytest `--durations`)

| test | wall |
|---|---|
| T1 step (`t_table` x 4 eps + synthesis at $10^{-6}$ + `verify_step_samples`) | 1500 s |
| T1 UB / UE / UK | 4.3 / 0.8 / 0.8 s |
| S1 four `step_orders` cases | 63 / 67 / 79 / 85 s each (-n 1) |
| S1 peak RSS | 134.7 GB (as in part 1) |

Observation: the T1 test on the step takes about 20 times longer than the whole `m9_results.py` run (74 s x 14 workers is below 410 s CPU), because the test synthesises the whole circuit at once and re-verifies without the layer metadata, whereas the script uses `synthesize_layered`. Not a defect; relevant only for CI planning.

## Flags

No slowdown comparison possible (baseline). No physics anomalies. Caveat: wall times on a shared 48-thread host; use the run-2 column as the baseline and allow about 15 % noise.
