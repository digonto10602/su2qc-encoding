# Report 448: tester, milestone-11 gate step 1 (mode full, acceptance-v23, prompts/009 + 010)

- Date: 2026-11-20. Started from HEAD `9ded1c9` as briefed; HEAD moved to `786b6ae` before my first command (`git show --stat 786b6ae`: only `notes/STATUS.md`, so source, tests and results are identical to `9ded1c9`). `git diff 328e071 HEAD --stat -- src scripts tests compress` is empty. All numbers below are for `786b6ae` plus the uncommitted builder edits listed in "Working tree".
- Plan in force: `prompts/009` (final cross-encoding report, M11) and `prompts/010` (fuzzy headline rule) on the lock `acceptance-v23`. Related reports: 445 (previous full gate), 446 (m7/m8 on v23), 447 (11.8 snapshot fix, the lean-cert unit failure first seen there).
- Raw numbers and scripts: `results/tester/448/` (`raw/*.log|xml|mem` per milestone, `unit/`, `mem/`, `spot_check.py|json`, `compare_rerun.py|json`, `m11_results_rerun.log`, `hashes.py|json`, `run_acc.sh`, `memwall.py`). Machine omnicommander, `taskset -c 0-6`, one pytest stream at a time, `-n 3`, 1 BLAS thread. No seed of my own; tests use their own fixed seeds.

## Verdict: PASS

407 locked acceptance tests: 407 passed, 0 failed, 0 pending. Unit suite: 1235 passed, 0 failed (plus one extra copy of an old test that fails on a cold cache, see check 2). New failures compared with report 445: none. Two earlier reds are now green: M8-G2 (amended in v23) and M11_T2 (results/crosscheck regenerated).

## Plain-English summary

Every locked acceptance test of milestones 0 to 11 passes, including the slow ones, with nothing skipped. The lock is intact, the frozen code hashes are unchanged, and the committed cross-encoding result files were regenerated from scratch in a copy of HEAD and came out identical in all 2243 numbers (even `tradeoff.pdf` and `tables.md` are byte-identical). Sixty cells of Report 11 (all LSH cells included) match their source files. The unit test that failed in report 447 is not a physics problem: it depends on whether a cache inside the code was already filled by an earlier test in the same process. Run alone on the committed file it fails every time; run after any test that fills the cache it passes. The builder's uncommitted edit fills the cache first and makes it pass in every order I tried.

## Commands run

```
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
cd /home/digimonk/Projects/su2qc-encoding; export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance     # start and end
results/tester/448/run_acc.sh      # for m in m0 m1 m2 m2c m3 m3x m4 m5 m5x m6 m7 m8 m9 m10 m11:
                                   #   taskset -c 0-6 python results/tester/448/memwall.py tools/pytest-safe -n 3 tests/acceptance/$m -m "slow or not slow" -q -rfEs --durations=5 --junitxml=...
python results/tester/448/hashes.py                                    # frozen hashes vs results/tester/434-hashes.json
# unit experiments (results/tester/448/unit/):
U1  pytest-safe scratch/tester/448/test_head448_check_cross.py -k <test>        # verbatim HEAD version of the test, alone
U2  pytest-safe tests/unit/test_rishon_lean_cert_unit.py -k <test>              # working-tree version, alone
U3  pytest-safe tests/unit/test_rishon_lean_cert_unit.py                        # working-tree version, whole file
U4  pytest-safe scratch/tester/448/test_head448_full.py                         # verbatim HEAD file, whole file
U5  pytest-safe -n 3 tests/unit scratch/tester/448/test_head448_check_cross.py  # full unit suite + the HEAD copy of the test
# M11 re-run in a copy of HEAD:
git archive HEAD | tar -x -C scratch/tester/448/headcopy
taskset -c 6 python scripts/m11_results.py --root .../scratch/tester/448/headcopy   (run from the copy; 146 s)
python results/tester/448/compare_rerun.py ; python results/tester/448/spot_check.py
# memory: results/tester/448/mem/run.sh (single process, -n 0) for m3, m9_S1_step_orders, m1, m2, m9_C1, and m3 per file
```

## Results

### Check 1: acceptance, milestone by milestone (`-m "slow or not slow"`, `-n 3`, cores 0-6)

| milestone | expected | got | wall (s) | peak summed RSS / PSS of process tree (GiB, 0.2 s sampling, 3 workers) | result |
|---|---|---|---|---|---|
| m0 | all pass | 34 passed | 15.0 | 1.60 / 1.47 | PASS |
| m1 | all pass | 22 passed | 68.3 | 4.30 / 4.14 | PASS |
| m2 | all pass | 46 passed (first try, no Lean timeout, whole file ran alone) | 165.2 | 10.87 / 8.72 | PASS |
| m2c | all pass | 28 passed | 44.0 | 2.73 / 2.44 | PASS |
| m3 | all pass | 24 passed | 18.1 | 14.86 / 7.38 | PASS |
| m3x | all pass | 4 passed | 8.6 | 8.56 / 6.83 | PASS |
| m4 | all pass | 19 passed | 64.9 | 2.92 / 1.85 | PASS |
| m5 | all pass | 56 passed | 1064.9 | 9.34 / 8.50 | PASS |
| m5x | all pass | 8 passed | 7.6 | 7.78 / 7.01 | PASS |
| m6 | all pass | 33 passed | 1252.7 | 9.50 / 8.66 | PASS |
| m7 | all pass | 29 passed | 9.7 | 8.82 / 7.45 | PASS |
| m8 | all pass (G2 amended) | 33 passed, incl. `M8_G2_best_and_headline_second_engine_aer` | 110.0 | 8.01 / 7.18 | PASS |
| m9 | all pass | 28 passed (slowest: `M9_T1_t_table_and_synth_verify[step]` 925.7 s, `M9_C1_seeded_physical_states_and_gauss` 418.0 s) | 1013.0 | 7.94 / 7.79 | PASS |
| m10 | all pass | 10 passed | 73.8 | 2.20 / 2.08 | PASS |
| m11 | all pass, T2 now green | 33 passed, incl. `M11_T2_final_report_inputs_complete` | 58.7 | 2.47 / 2.31 | PASS |
| **total** | 407 collected | **407 passed, 0 failed, 0 pending, 0 skipped** | sum 3975 s (66 min) | | **PASS** |

Differences from report 445: m2 now passes on the first try (445 had one Lean-timeout under load, passed on a quiet rerun); m9 passes first try (445 had one OOM-killed worker from two parallel streams); m8 +1 pass (G2 amended); m11 +1 pass (T2). No test changed from pass to fail.

### Check 2: the lean-cert unit test (`test_check_cross_compares_at_nominal_alternate_and_irrational_pairs`)

| run | what | expected | got | result |
|---|---|---|---|---|
| U1 | committed (HEAD) version of the test, alone | any | FAILED in 0.66 s: `assert [0.29, 0.53, ...9, 0.53, 1.07] == [0.29, 0.53, 1.07]` (6 `inner_target` calls instead of 3) | fails (as in 447) |
| U2 | working-tree version (builder edit), alone | any | 1 passed | PASS |
| U3 | working-tree version with its file (23 tests) | any | 23 passed, 32.5 s | PASS |
| U4 | committed (HEAD) file, whole file (23 tests) | any | 23 passed, 31.4 s | PASS (earlier tests warm the cache) |
| U5 | full unit suite `-n 3` (working tree) plus a copy of the HEAD test as a separate module | no new failure | 1235 of 1235 tests in `tests/unit` passed; the HEAD copy FAILED on worker `gw0` (cold cache) | PASS (copy fails by design of this experiment) |

Cause (read from `src/su2plaq/rishon/lean_cert.py` lines 276 and 300, and the test): `exact_target` is `functools.lru_cache`d, and on a cache miss it runs `_check_cross` itself, which calls `operators.inner_target` once per angle pair (3 for UD, 4 for UE). The committed test installs its spy on `inner_target` before the first `exact_target("UD")` call, so on a cold cache the spy also sees the calls made inside `exact_target`, giving 6 instead of 3. It passes whenever an earlier test in the same process has already filled the cache (file order, or the xdist worker that happened to run such a test before it: passed in 445 at `-n 8`, failed in 447 and in U1). So it depends on ordering and a cache, not on the physics or on `_check_cross`. The uncommitted builder edit (4 lines, `L.exact_target("UD")` and `("UE")` before the spy) removes the dependence: pass alone, with the file, and in the full suite. It is not committed yet. Not a tolerance change; the assertions are unchanged.

### Check 3: lock and hashes

| check | expected | got | result |
|---|---|---|---|
| `pytest --collect-only -q tests/acceptance` | clean | 407 tests collected in 0.3 s, no errors (start and end) | PASS |
| `python tools/check_lock.py` | LOCK OK | `LOCK OK` (start and end) | PASS |
| `~/.claude/bin/acceptance-check` | matches v23 | `PASS: tests/acceptance matches acceptance-v23` (start and end) | PASS |
| frozen hashes (9 keys) vs `results/tester/434-hashes.json` | equal | all 9 equal: provenance and twelve `99663fa6...3e37`, spinnet `10f5727f...e15c`, fuzzy_ub = fuzzy_link `b4bd20fe...87f9`, rishon = `rishon.compress.code_hash` `5f5decfa...ef23`, lsh `88e0d76b...c1ca`, `spinnet.loop.code_hash` `f1314a01...63d4` (`results/tester/448/hashes.json`) | PASS |

### Check 4: M11 specifics

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| provenance of `results/crosscheck/spectra.json` and `gate-table.json` | `git_dirty` false, commit 328e071 | both: `git_commit` 328e071, `git_dirty` false, timestamp 2026-11-20T20:45:07Z, command `python scripts/m11_results.py` | exact | PASS |
| `src`, `scripts`, `tests`, `compress` unchanged since 328e071 | empty diff | empty (`git diff 328e071 HEAD --stat -- src scripts tests compress`) | exact | PASS |
| re-run `scripts/m11_results.py --root <copy of HEAD>` (146 s, one core): `spectra.json` | all numbers equal | 2062 numbers compared, 0 differences (relative difference 0.0, bit-identical) | exact | PASS |
| same, `gate-table.json` | all numbers equal | 181 numbers compared, 0 differences | exact | PASS |
| same, strings, lists and booleans (all keys except `provenance`, `seconds`, `timestamp_utc`) | equal | 0 differences | exact | PASS |
| same, `tables.md` and `tradeoff.pdf` | equal | `tables.md` identical; `tradeoff.pdf` sha256 prefix `0bc4df38da4911be` in both | exact | PASS |
| 9 cross-verdicts, 0 headline cross-verdicts skipped, all five gate-table rows `final` | | printed by the re-run (`m11_results_rerun.log`) | | PASS |

Only provenance differs in the re-run (commit 786b6ae and `git_dirty` true, from the working tree; the command line has `--root`).

Spot-check of Report 11 (`docs/report-11-cross-encoding-comparison.md`) against `gate-table.json`, `spectra.json`, `results/compress/*/robust.json`, `results/lsh/{step,UE,m8-compressed}.json`: 60 cells, 60 PASS, 0 FAIL (`results/tester/448/spot_check.py`, full table in `spot_check.json`). Standard error = sample standard deviation (ddof 1) of the 20 `t_eps` values divided by $\sqrt{20}$. Percentages recomputed from the CX and mean-T values. Cells:

| # | cell (report) | source | value |
|---|---|---|---|
| 1 | Table 1a LSH: CX 94, rot 8, $T_{\rm fixed}$ 88, $T(10^{-6})$ 598 | `gate-table.json` lsh.general | 94, 8, 88, 598 |
| 2 | Table 1a LSH qubits 31 | `robust.json` lsh `r00-seed-000` | 31 |
| 3 | Table 1a LSH $\bar T=592.6\pm1.6$ | `robust.json` lsh `r00-seed-000` `t_mean`, stdev/$\sqrt{20}$ | 592.6, 1.6 |
| 4 | Table 1b LSH entry `r05-F3-005`, $T(10^{-6})$ 1396 | `gate-table.json` lsh.headline | `r05-F3-005`, 1396 |
| 5 | Table 1b LSH 24 qubits, CX 68, 22 rot, $T_{\rm fixed}$ 24 | `results/lsh/m8-compressed.json` metrics.logical | 24, 68, 22, 24 |
| 6 | Table 1b LSH $\bar T=1417.4\pm8.0$, angle-linear yes | `robust.json` lsh `r05-F3-005` | 1417.4, 8.0, true |
| 7 | Table 1c LSH $94\to68$, $\times1.38$, $-27.7\%$ | recomputed from rows 1 and 5 | 1.38, -27.7 |
| 8 | Table 1c LSH $592.6\to1417.4$, $+139.2\%$ | recomputed | +139.2 |
| 9 | Table 1c LSH UE row: 20 rotations, $T=1280$ | `results/lsh/UE.json` extra.outer_electric_row | 20, 1280 |
| 10 | Table 2 LSH headline (68, 1417.4); T-first `r00-seed-002` (84, 585.1); general (94, 592.6); 28 ranked; differences 16 CX and $-832.3$ | `gate-table.json` lsh.{headline,t_first}; `robust.json` lsh | all equal |
| 11 | Table 2 LSH Pareto: 7 distinct points (68,1417.4) (70,1354.3) (71,1116.0) (72,879.4) (74,697.6) (82,641.1) (84,585.1); `r04-F3-004`, `r05-F5-005` in the front | `gate-table.json` lsh.pareto | equal |
| 12 | 3a level deviation $2.8\times10^{-14}$, $1.2\times10^{-14}$, $2.7\times10^{-14}$ | `spectra.json` ks.max_pairwise_level_dev | 2.753e-14, 1.199e-14, 2.665e-14 |
| 13 | 3a plaquette multiplicities 16, 96, 16, 177, 16, 96, 16 (LSH) | ks.hb_multiplicities.lsh | equal |
| 14 | 3a transported target $3.0\times10^{-15}$ | ks.transported_target_max | 3.037e-15 |
| 15 | 3a cross-verdicts twelve vs LSH $2.7\times10^{-13}$, spinnet vs twelve $1.1\times10^{-14}$, LSH vs spinnet $1.6\times10^{-14}$ | ks.cross_verdicts[0..2].total_error | 2.721e-13, 1.105e-14, 1.648e-14 |
| 16 | 3a negative control block errors $2.0000000012$, $...018$, $...034\times10^{-6}$, all rejected | ks.cross_verdicts[0..2].mutant | equal to 10 digits, ok false |
| 17 | 3a LSH `r05-F3-005` vs twelve $1.4\times10^{-14}$, $1.3\times10^{-14}$; all 9 verdicts ok and certified; `headline_skipped` empty | ks.cross_verdicts[7,8] | 1.441e-14, 1.301e-14; true; [] |
| 18 | other blocks: twelve $\bar T=943.2\pm2.3$, `r05-F2-005` (31, 111, 927.4); spinnet $560.6\pm1.6$, `r02-F1-002` (17, 31, 1092.0$\pm$3.1), $+94.8\%$; rishon (58, 10102, 20620.2$\pm$58.8), `r06-F3-006` (52, 216, 829.8$\pm$2.2), $-96.0\%$; fuzzy 5336.2, units (83, 634.4$\pm$3.2) and (12, 628.8$\pm$3.8), composed (131, 3149.6), T-first (137, 3035.2); T-first picks of twelve, spinnet, rishon; ranked counts 21, 23, 23, 41, 4 | `robust.json`, `gate-table.json` | all equal |

Independent recomputation: from `robust.json` alone I re-derived the headline (smallest robust key, full ties by the next key components) and the T-first pick (first two key components exchanged) of all six archives; they equal `gate-table.json` and the report (twelve `r05-F2-005` / `r00-seed-001`, spinnet `r02-F1-002` / `r01-F5-001`, LSH `r05-F3-005` / `r00-seed-002`, rishon `r06-F3-006` / `r06-F1-006`, fuzzy $U_B$ `r10-F1-010` / `r13-F3-013`, link `r02-F2-001`).

### Check 5: peak memory

Memory is the process tree of `tools/pytest-safe` (python workers plus Lean processes), summed over processes every 0.2 s. RSS double counts shared pages (so m3 at `-n 3` shows 14.9 GiB), PSS does not. Single-process runs (`-n 0`):

| run | peak RSS / PSS (GiB) | wall (s) |
|---|---|---|
| `m3/test_spinnet_lean.py` (Lean checker processes; the other five m3 files are 0.05 to 0.30) | 7.38 / 6.70 | 9.3 |
| `m2` (whole milestone, includes Lean) | 7.86 / 7.19 | 219 |
| `M9_C1_seeded_physical_states_and_gauss` (one python process) | 5.24 / 5.23 | 379 |
| `m1` (whole milestone) | 2.56 / 2.56 | 134 |
| `M9_S1_step_orders` (4 params; the case of the 2026-11 crash) | 1.04 / 1.03 | 132 |
| `M8_G2` (report 446, not repeated) | 1.64 / 1.61 | 114 |

Largest: the Lean-based `test_spinnet_lean.py` at about 7.4 GiB (6.7 PSS). Largest pure-python test: `M9_C1` at 5.2 GiB. Both are well above the "all acceptance tests peak at most 2.2 GB" statement in project `CLAUDE.md`, but inside the 11 G slice cap when run one stream at a time. Not a failure (no acceptance test states a memory tolerance except the 2.2 GB budget in prompts/007 for `M9_S1`, which holds at 1.04 GiB). `m2` at `-n 3` reached 10.87 GiB summed RSS (8.72 PSS) against an 11 G cap: close; do not add a second stream beside it.

### Unit suite

| suite | expected | got | wall | result |
|---|---|---|---|---|
| `tests/unit` (`-n 3`, working tree) | all pass | 1235 passed, 0 failed (445 had 1224 tests; +11 from the new untracked `tests/unit/test_summary_table_unit.py`) | 495.8 s, peak 11.0 GiB summed RSS (10.2 PSS) | PASS |

No Lean lemma timeout this time (445 had three under load).

## Working tree and files rewritten by test runs

- HEAD at my start `786b6ae` (briefed `9ded1c9`). Uncommitted at start and end, unchanged during my runs (sha256 recorded in `results/tester/448/unit/sha_at_unit_start.txt` and rechecked at the end): `scripts/summary_table.py` (`985c24c2...`), `tests/unit/test_rishon_lean_cert_unit.py` (`d2998828...`, the 4-line cache warm-up), `tests/unit/test_summary_table_unit.py` (untracked, `6325d20e...`). `src/` has no uncommitted change. No acceptance test imports `scripts/summary_table.py` (grep: only the new unit test does), and no acceptance result depends on the unit-test edit, so the acceptance results are unaffected. The unit run did include the two builder unit files (the new one passed, 11 tests, within the 1235).
- Tracked files rewritten by test runs (known): `results/spinnet/certs/spinnet-UB-o1-33d95284ebb7.json`, `spinnet-UB-o1-458a39365261.json`, `spinnet-UE-o1-df0c79b22d3f.json`, `spinnet-step-o1-066f66922ff8.json`, `spinnet-step-o1-b0a415d9322f.json` (one-line files, diff shows the line rewritten). I did not restore them.
- Untracked and mine: `results/tester/448/`, `scratch/tester/448/` (gitignored: HEAD copy of the repo for the re-run, copies of the HEAD test). Nothing in `results/crosscheck` or `results/summary` was changed by my runs (`--root` pointed to the copy).

## Observations (not failures)

- O1: Report 11 Table 2 labels the Pareto point of a tie with a name that does not follow its own rule "ties in both keep the first by id": twelve (111, 927.4) is shown as `r05-F2-005` (the headline; first by id would be `r04-F2-004`, and `gate-table.json` lists all five tied ids); spin network (32, 847.4) as `r05-F3-005` (first by id `r01-F1-001`); fuzzy $U_B$ (83, 634.4) as `r10-F1-010` (first by id `r09-F1-009`); but LSH (68, 1417.4) as `r04-F3-004` (first by id, not the headline `r05-F3-005`). The numbers are right in every case; only the label convention is inconsistent (headline-by-key for twelve, spinnet, fuzzy; first-by-id for LSH). Suggest a one-line wording fix in the report or in the Table 2 note.
- O2: the committed lean-cert unit test is order dependent (check 2). The builder edit fixes it; it needs a commit.
- O3: memory figures exceed the 2.2 GB statement of `CLAUDE.md` for Lean-based tests and `M9_C1` (check 5). Under the 11 G slice and one stream all passed without an OOM kill.
- O4: `tradeoff.pdf` is reproducible byte for byte (same matplotlib output), which is convenient for later regeneration checks.

## Failures

None.
