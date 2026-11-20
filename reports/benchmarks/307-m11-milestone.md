# Benchmark report 307 - milestone 11 gate, step 3 (mode benchmark)

- Date: 2026-11-20 (runs about 17:40-18:05 EST). Benchmarked commit: `5e9f808` in a clean detached worktree `/home/digimonk/Projects/su2qc-wt/bench307` (`git worktree add --detach ... 5e9f808`; left in place; `git status` there is clean at the end). The main tree's HEAD had moved to `1895792` by the end; `git diff --stat 5e9f808 1895792` touches only `notes/STATUS.md`.
- Prompt in force: `prompts/009` (final cross-encoding report) + `prompts/010` (fuzzy headline rule), lock `acceptance-v23` (`tools/check_lock.py`: `LOCK OK`; `acceptance-check`: `PASS: tests/acceptance matches acceptance-v23`).
- Related: previous benchmark `reports/benchmarks/306-lsh-milestone-8.md` (method and LSH baselines); tester `reports/tests/423` (first timing of `m11_results.py`), `447`, `448` (gate step 1, PASS), `449` (summary-table fix); audit `reports/audits/309` (PASS WITH NOTES).
- Raw numbers, scripts, logs: `results/benchmarks/m11/` (`summary.json`, `raw/*.json`, `raw/*.log`, `raw/prof_spectra.txt`, `scripts/`). The scripts take the worktree as an argument or `BENCH_ROOT`, so every number below was measured in the worktree's source.
- Machine: `omnicommander` (i7-12700KF, 20 logical CPUs, 31 GiB, no GPU), python 3.12, numpy 2.5.4, scipy 1.18.1, qiskit 2.5.2. `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `PYTHONHASHSEED=20261104`. Single-process tasks `taskset -c 2` (one fixed P-core); the pytest suite `taskset -c 0-7 tools/pytest-safe -n 4`. One timed job at a time. 1-minute load average before each run was 1.0-1.7 (mostly my own job plus a qemu VM and Chrome renderers), recorded in the JSON. Nothing stochastic is timed; no seed of my own.
- Statistic: median [min, max]. "warm" = later calls after one warm-up in a fresh process; "first" = first call in a fresh process.

## Verdict: PASS (no quantity more than 10 % slower than a like-for-like earlier value)

Every number that has a like-for-like earlier value is within 5 % of it. The only larger ratios are against earlier numbers that were not like-for-like (explained in "Comparison notes"). Physics output reproduces exactly: regenerated `spectra.json` and `gate-table.json` equal the committed files in every number (provenance and the per-verdict `seconds` fields excluded), `tables.md` and `tradeoff.pdf` come out byte-identical (git shows them unmodified after the run).

## Table of results

| # | quantity | value (median [min, max], n) | previous | ratio | flag |
|---|---|---|---|---|---|
| 1 | `python scripts/m11_results.py` full wall, one core (worktree, headline cross-verdicts included) | **76.9 s** [76.3, 78.6], n=6 (3 with the gridsynth cache dir removed, 3 after; identical, the script never touches that cache) | tests 423: 62 s and 68 s, but with only 3 cross-verdicts (no cached headlines in that scratch root); tester 448: 146 s (`taskset -c 6`, `--root` copy, see notes) | 77 s vs 68 s is not like-for-like (+11.3 s of headline verdicts; 68 + 11.3 = 79 s); vs 448: 0.53 | none |
| 1b | peak RSS of that run (`RUSAGE_CHILDREN`) | 1082 MB [1041, 1083], n=6 | no earlier value | - | new baseline |
| 1c | regenerated `spectra.json`, `gate-table.json` against committed | equal except `provenance` and `seconds` (all 2243 compared numbers; `tables.md`, `tradeoff.pdf` byte-identical); `git diff` shows only provenance and seconds lines | committed at `328e071` | exact | PASS |
| 2 | cross-verdict twelve circuit vs LSH target, general (in-script `seconds`, incl. mutant control) | 3.543 s [3.428, 3.586], n=6 | committed 3.412 | 1.04 | none |
| 2 | spinnet circuit vs twelve target, general | 0.371 s [0.354, 0.410] | committed 0.367 | 1.01 | none |
| 2 | LSH circuit vs spinnet target, general | 0.290 s [0.276, 0.323] | committed 0.301 | 0.96 | none |
| 2 | twelve headline r05-F2-005 vs spinnet target, nominal / alternate angles | 4.394 / 4.422 s | committed 4.215 / 4.222 | 1.04 / 1.05 | none |
| 2 | spinnet headline r02-F1-002 vs LSH target, nominal / alternate | 0.702 / 0.697 s | committed 0.667 / 0.663 | 1.05 / 1.05 | none |
| 2 | LSH headline r05-F3-005 vs twelve target, nominal / alternate | 0.819 / 0.801 s | committed 0.780 / 0.764 | 1.05 / 1.05 | none |
| 2b | spectra/KS part without headline verdicts: `spectra_results(headline=False)` (includes the 3 general verdicts above) | 64.2 s [62.3, 65.8], n=3 | no earlier value | - | new baseline |
| 2c | headline cross-verdicts, 6 of them: build + target + evaluate | 11.3 s total | - | - | new baseline |
| 2d | `gate_table(out=False)` / `tradeoff_figure` / `render` | 0.032 s / 0.555 s / 0.0007 s, n=3 | - | - | new baseline |
| 3 | `pytest tests/acceptance/m11 -m "slow or not slow"`, `-n 4`, CPUs 0-7 (33 tests, all pass) | **55.0 s** [54.9, 55.2], n=3; peak RSS 1295 MB (largest single process) | report 11: 54 s at `-n 4`; tester 448: 58.7 s at `-n 3` | 1.02 / 0.94 | none |
| 4a | LSH `evaluate_program`, headline r05-F3-005, warm, key (68, 1396, 3210, 24) | **1.184 s** [1.175, 1.246], n=25 | 306: 1.183 [1.173, 1.200] | 1.00 | none |
| 4a | same, first call in process / cold gridsynth cache first call | 1.955 s [1.933, 2.108], n=5 / 2.098 s (later calls 1.18-1.19) | 306: 1.941 / 2.096 | 1.01 / 1.00 | none |
| 4b | seed `005-wrap_sn_headline.py`, warm, key (71, 1118, 2276, 25) | **1.065 s** [1.057, 1.119], n=25 | 306: 1.065 [1.059, 1.096] | 1.00 | none |
| 4c | reference `000-general.py`, warm, key (94, 598, 880, 31) | 1.049 s [1.043, 1.071], n=25 | 306: 1.052 | 1.00 | none |
| 4d | `robust_metrics("lsh","step",headline)`, warm, robust key (68, 28348, 0, 63378, 24) | **1.563 s** [1.548, 1.668], n=25 | 306: 1.573 [1.551, 1.602] | 0.99 | none |
| 4d | same, first call in process | 2.508 s [2.498, 5.899], n=5 (the 5.9 s outlier is the first process after the cold-cache run emptied the file cache; the other four are 2.50-2.52) | 306: 2.499 | 1.00 | none |
| 4e | pieces of 4a: sandbox build / `evaluate_circuit` / verdict-level `evaluate` | 0.439 s / 0.744 s / 0.229 s | 306: 0.437 / 0.746 / 0.230 | 1.00 | none |
| 4f | peak RSS of `evaluate_program` | 259 MB | 306: 258 MB | 1.00 | none |
| 4g | route-A build time, compression round wall time | not affected: `git diff --stat 5082162 5e9f808 -- src` lists only `src/su2plaq/crosscheck/report.py` (17 insertions, 5 deletions; a `git_snapshot()` helper and a `git=` argument for the provenance dict); compression round (306: 5.69 s) and seed (23.2 s) code paths unchanged | 306 | - | not re-run |

All LSH verdicts `ok`, operator-norm error $1.44\times10^{-14}$ (headline) / $8.9\times10^{-15}$ (wrapped seed) / $1.6\times10^{-14}$ (general), Gauss residual $\le 6\times10^{-16}$, outer bits read 2 / 0 / 0, identical to 306 (section 7 there). All 9 cross-verdicts `ok=True`, `total_error` between $4.8\times10^{-15}$ and $1.0\times10^{-13}$ (as committed).

## Where the 77 s of `m11_results.py` goes (single process, `cProfile` in `raw/prof_spectra.txt`, `parts` in `raw/rest/cross_*.json`)

| part | seconds | note |
|---|---|---|
| `spectra_results(headline=False)` | 64.2 | `rishon_ks_limit` 34.7 s (6 calls, mostly 2017 `eigvalsh` calls, 27.9 s); `fuzzy_isolated_levels` 17.5 s (one `isolated_plaquette_basis` 16.5 s, `einsum` 12.5 s); rishon physical basis 6.4 s; the 3 general cross-verdicts about 6.4 s (under cProfile) |
| 6 headline cross-verdicts | 11.3 | twelve-vs-spinnet headline ones dominate: 3.80 s `evaluate` each (method `physical`, 4 outer bits read) plus 0.37 s sandbox build; the others 0.7-0.8 s |
| `gate_table`, `tradeoff_figure`, `render` | 0.6 | |
| total | about 76.1 (sum of parts) vs 76.9 measured | consistent |

In-script `seconds` of the first cross-verdict (3.5 s) is larger than the pure build + two evaluate calls measured warm in `w_cross.py` (0.001 + 0.020 + 1.110 + 1.104 = 2.2 s) because it includes one-time first-call set-up (imports and cache fills) in a fresh process; this is the same in the committed file (3.41 s).

## Comparison notes (flags considered, none raised)

1. **`m11_results.py`: 77 s against "73.8 s" in the brief.** The 73.8 s in the tester 448 table is the wall time of the **m10 acceptance milestone** (`| m10 | ... | 73.8 |`), not of `m11_results.py`; no earlier unrecorded timing of the script exists in the reports I could find. Tests 423 recorded 62 s and 68 s for the script, but that scratch root had no cached headlines (the figure had "six empty panels, pending") so it ran only the 3 general cross-verdicts; adding the measured 11.3 s of the six headline verdicts to 68 s gives 79 s, in line with 77 s.
2. **Tester 448's 146 s (`taskset -c 6`, `--root` copy)** is 1.9 times my 77 s. Guess, not tested: core 6 was shared with the `-n 3` acceptance workers pinned to cores 0-6 in the same session. My runs use a core outside any other job of mine and showed a spread of 3 % over 6 runs.
3. **Cross-verdict `seconds`** are 0 to 5 % above the committed values (committed file was generated at `328e071` in a different session); the largest are +4-5 % on the headline verdicts, inside the 10 % threshold and within the session-to-session drift (306 saw 1-9 % between sessions).
4. **m11 suite:** the slowest tests are `test_M11_H3_fuzzy_step_composed_from_the_headline_units` 32.5 s, the four `test_M11_E3_rishon_*` cases 19.0-25.4 s, `test_M11_F2_fuzzy_isolated_plaquette_gap` 25.1 s, `test_M11_K4_headline_circuit_against_another_encodings_target[twelve-spinnet]` 18.1 s, `K3[twelve-lsh]` 6.7 s, `K2` 4.8 s, `K4[spinnet-lsh]` 2.5 s (`--durations=10`, run 0; all others under 2.5 s). The wall time is limited by H3 plus the fixed set-up: with 4 workers 33 tests of summed call time about 190 s take 55 s. The E3[0.5]/E3[2.0] cases were 26.8-26.9 s in tests 422 and are now 24.8 / 25.4 s (7 % faster).
5. `compress/cache/gridsynth` is not used by `m11_results.py` (the directory was never created in the worktree during those runs); it is created by the LSH warm-up calls in item 4 and was left in the worktree (gitignored).

## Physics output unchanged

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| `spectra.json` regenerated vs committed (no `provenance`, no per-verdict `seconds`) | equal | equal (Python `==` on the parsed JSON, all fields) | exact | PASS |
| `gate-table.json` regenerated vs committed (no `provenance`) | equal | equal | exact | PASS |
| `tables.md`, `tradeoff.pdf` | byte-identical | `git status` shows them unmodified after 6 runs | exact | PASS |
| headline key and robust key of r05-F3-005 | (68, 1396, 3210, 24) / (68, 28348, 0, 63378, 24) | same, in 25 of 25 and 25 of 25 calls | exact | PASS |
| seed round-0 key and reference key | (71, 1118, 2276, 25) / (94, 598, 880, 31) | same | exact | PASS |
| m11 acceptance | 33 pass | 33 passed in 3 of 3 runs | - | PASS |
| `tools/check_lock.py`, `acceptance-check` | OK | `LOCK OK`, `PASS ... acceptance-v23` | - | PASS |

## Files touched by my runs

- Worktree `bench307`: `results/crosscheck/{spectra,gate-table}.json` were rewritten by the script (provenance and `seconds`), then restored with `git checkout -- results/crosscheck` before the suite run; untracked/gitignored: `compress/cache/gridsynth` (created by the LSH warm-up). `git status --short` there at the end: empty. The m11 test run did not modify `results/spinnet/certs`.
- Nothing moved to `should-be-deleted/` (the worktree had no gridsynth cache directory during the six `m11_results.py` runs, so the "cold" step had nothing to remove).
- Main tree: only the new untracked `results/benchmarks/m11/` and this report. `src/`, `tests/`, `compress/` were not touched.

## Commands

```
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
git worktree add --detach /home/digimonk/Projects/su2qc-wt/bench307 5e9f808
python results/benchmarks/m11/scripts/bench_m11_results.py <wt> results/benchmarks/m11/raw/m11_results_runs.json 3 3 2   # taskset -c 2 python scripts/m11_results.py, 6 runs
results/benchmarks/m11/scripts/run_rest.sh <wt> results/benchmarks/m11/raw/rest   # w_cross.py x3, w_eval.py eval x5 per program (1 warm-up + 5 timed), robust x5, cold x1; taskset -c 2
taskset -c 2 python results/benchmarks/m11/scripts/prof_spectra.py                  # cProfile of spectra_results(headline=False)
python results/benchmarks/m11/scripts/run_suite.py <wt> results/benchmarks/m11/raw/suite_m11.json 3   # taskset -c 0-7 tools/pytest-safe -n 4 tests/acceptance/m11 -m "slow or not slow" --durations=10
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
```
