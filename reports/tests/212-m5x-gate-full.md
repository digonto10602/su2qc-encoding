# Report tests/212 — M5x gate step 1: tester mode `full` (m0 + m1 + m5 + m5x, unit, Lean, locks)

- Date: 2026-11-06 · Commit: `9bbc4d8` (clean tree before the run; `git status` showed only this run's `results/rishon/tester-212-*` files)
- Prompt in force: `prompts/202-rishon-m5x-wait-robustness.md` (gate row of §4; plan `prompts/200`/`201` for M5). Locked tests: acceptance-v9.
- Mode: full · Related: `reports/tests/207`, `208` (M5 gate), `209`, `210`, `211` (M5x steps W0–W4, O1)
- Raw numbers: `results/rishon/tester-212-*` (logs, junit XML, `.time` files from `/usr/bin/time -v`, `-rss.log`, `-summary.json`, `-axioms.log`, `-cert.log`, `-lakebuild.log`, `-run.sh`); scratch `scratch/tester212/Axioms.lean`.

## 1. Commands (env `su2qc-coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `source ~/.elan/env`, all under `taskset -c 10-19`)
```
results/rishon/tester-212-run.sh    # runs, in order, each with --junitxml -q -rA:
  pytest -n 10 tests/acceptance/m0 ; m1 ; pytest -n 1 tests/acceptance/m5x ; pytest -n 10 tests/acceptance/m5 (slow included)
  pytest -n 10 tests/unit ; pytest -n 10 tests/acceptance/m2 ; ~/.claude/bin/acceptance-check ; python tools/check_lock.py
cd lean && lake build Su2Plaq                       # incremental
cd lean && lake env lean ../scratch/tester212/Axioms.lean     # #print axioms for 9 M5 + 11 M5x theorems
cd lean && lake env lean certs/rishon-hb-structure.lean       # L3 certificate axioms
grep -rnwE "native_decide|sorry|admit" lean/Su2Plaq lean/Su2Plaq.lean
git diff a8f051e HEAD --stat -- src scripts lean ; git diff b4c1917 HEAD --stat -- src/su2plaq scripts
graphify update .
```

## 2. Result table
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| acceptance m0 (incl. slow) | all pass | 34 passed, 12.3 s, max single-process RSS 0.65 GB | exact | PASS |
| acceptance m1 (incl. slow) | all pass | 22 passed, 98.3 s, 1.60 GB | exact | PASS |
| acceptance m5 (incl. both slow T1 runs `[UB]`, `[step]`, plus `[UE]`, L1, L2, L3) | all pass | 34 passed, 0 skipped, 839.3 s (14 min), 6.81 GB | exact | PASS |
| acceptance m5x | all pass | 6 passed (W1, W2, W3, L, O1 x2), 10.0 s, 6.82 GB (Mathlib-loading Lean job) | exact | PASS |
| unit (`tests/unit`) | all pass | 329 passed, 104.0 s, 6.82 GB; the known flaky `test_render_is_deterministic...` also passed (HEAD hash `9bbc4d8` has no `c1`) | exact | PASS |
| acceptance m2 (laptop-owned) | PENDING-expected | 7 passed, 39 failed in 3.65 s: 38 x `PENDING: NotImplementedError: … is not built yet`, 1 x missing file `lean/certs/twelve-general-step.lean` (same list as reports/tests/207) | - | PENDING (39), no other reason |
| `acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v9` | - | PASS |
| `tools/check_lock.py` | LOCK OK | `LOCK OK` | - | PASS |
| `lake build Su2Plaq` incremental | success, `Structure/Counts.lean` not rebuilt | `Build completed successfully (9095 jobs)`, 4.2 s, 1.01 GB; log line `Replayed Su2Plaq.Structure.Counts`; its `.olean` mtime `2026-11-05 23:54:26 -0500` before and after | - | PASS |
| `native_decide` / `sorry` / `admit` under `lean/Su2Plaq/` (whole-word grep) | none | none (the only substring hits are the English word "admits" in a `Structure/Counts.lean` comment) | - | PASS |
| `#print axioms`, 2 M5 count theorems | standard only | `card_rishon_physical`, `card_rishon_closed`: `[propext]` | - | PASS |
| `#print axioms`, 7 M5 JW theorems | standard only | 6 with no axioms, `u_ladder` `[propext, Quot.sound]` | - | PASS |
| `#print axioms`, 11 M5x theorems | standard only | `hb_link_ops_from_jw`, `corner_kernel_dims`, `ue_gadget_sector`, `ue_exact_all_codes`: `[propext, Classical.choice, Quot.sound]`; the other 7 (`hb_link_ops_count`, `det_u_identity`, `u_commute`, `card_inner_codes`, `ue_gates_structure`, `ue_outer_gates_structure`, `corner_count_agree`): no axioms | - | PASS |
| L3 certificate `rishon_hb_structure` | standard + exactly one native axiom | `[propext, Classical.choice, Quot.sound, rishon_hb_structure._native.native_decide.ax_1_1]`; 0.53 s, 0.82 GB | - | PASS |
| `results/rishon/UE_outer_row_certified.json` provenance | git_commit 59e863d, dirty false | `git_commit: 59e863d`, `git_dirty: false`, timestamp 2026-11-06T16:06:41Z (= commit time 11:06 -0500), command `python scripts/m5x_outer_row.py`, `provenance` seeds `outer_row_sample: 20261104` | - | PASS |
| M5 results unchanged since the M5 gate | no change to production numerics | `git diff a8f051e HEAD --stat -- src scripts lean`: only additions (`lean_export.py` +138, `results.py` +68, `scripts/m5x_outer_row.py` new, 4 new Lean files, 1 import line); among `results/rishon/*.json` only `UE_outer_row_certified.json` (new) changed since `milestone-5` (a8f051e) | - | PASS |

## 3. Notes
- Plan check requested by the caller: `git diff b4c1917 HEAD --stat -- src/su2plaq scripts` is NOT empty (7 files, +539/-13). The M5 part of it (`circuits/rishon.py` docstring only, `observables.py` `closed_block_full`, `operators.py` `closed_block_full`, `verify.py` classify-error recording) is the audit-fix commit `86fda8e` (N4/N5/N7/N8), made before `milestone-5` and tested in reports/tests/208. After the M5 gate (`a8f051e`), `src/` changed only by additions (`lean_export.py`, `results.py`) and no M5 results file changed. Check run here: `scratch/tester212/obs_regen.py` (copy of the tester-208 script) regenerates the observables block with the current tree and diffs it against `results/rishon/observables.json` ignoring provenance: 0 differences, max abs numeric difference 0.0 (`results/rishon/tester-212-observables-regen.json`). So the committed M5 results equal what the current code produces.
- Memory: single-process maxima 6.8 GB (m5, m5x, unit, m2 and the Mathlib `lean` job each) are below the 10 GB limit. Summed RSS of all python/lean processes sampled every 5 s peaked at 12.75 GB (this over-counts shared pages; it occurred while `-n 10` workers ran). No Lean job ran concurrently with another Mathlib job.
- Wall times: sum of pytest suites 1063 s (17.7 min); m5 T1 rows are the long ones (inside the 839 s).
- `scratch/tester212/Axioms.lean` is a tester sandbox; no source, test, prompt or tolerance was touched. `graphify update .` ran clean.

VERDICT: PASS
