# Tester report 108 — full suite after merging laptop milestone-2 (track S, mode `full`)

- Date: 2026-11-06
- Commit: `a7f8dcf` (branch `m3-spin-network` = merge of laptop `5111d69`, tag `milestone-2`, into our M3/M3x work)
- Prompt in force: `prompts/103-spinnet-m3x-test-fixes.md` (highest number; plan chain `prompts/100`, `102`, `103`; M2 plan `prompts/006`)
- Related: `reports/tests/106-m3-gate-full.md` (previous full run, pre-merge), `reports/tests/107-m3x-lean-exact-w0-w4.md`, `notes/merge-notes-spinnet.md`
- Raw numbers: `results/spinnet/tester/m4_merge_full_suite.json`, `results/spinnet/tester/m4_merge_full_suite_summary.txt`

## Verdict: FAIL (two items, both bookkeeping/PENDING, no physics failure)

1. `~/.claude/bin/acceptance-check` exits 1 (it compares against our newest tag `acceptance-v9`, which predates the merge).
2. `tests/acceptance/m3/test_spinnet_lean.py::test_M3_L3_native_certificate_general_step` is PENDING (`lean_export.certify` not built); in `full` mode PENDING in milestones 1..3 counts as FAIL.

Everything else is green: 34 + 22 + 46 + 23 + 4 acceptance tests and 489 unit tests, no skips, no xfail.

## Commands (all in `~/Projects/su2qc-spinnet`, env `su2qc-coding`)

```
cd lean && taskset -c 0-9 lake build --no-build +Su2Plaq.Structure.Counts     # exit 0: replay only
cd lean && taskset -c 0-9 lake build Su2Plaq.Gates Su2Plaq.Rewrites           # the two files the laptop changed
cd lean && taskset -c 0-9 lake build Su2Plaq Su2PlaqCert ; lake build ; lake build --no-build
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
taskset -c 0-9 pytest -n 10 -p no:cacheprovider -q -rfEs --durations=8 tests/acceptance/<m0|m1|m2|m3|m3x>   # one call per suite
taskset -c 0-9 pytest -n 10 ... tests/unit
~/.claude/bin/acceptance-check ; python tools/check_lock.py
```
Slow tests were included (no `-m "not slow"`). No install; `PYTHONPATH=src`.

## Results

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `Counts.lean` (15.7 GB) not rebuilt | `lake build --no-build` exit 0, "Replayed" | exit 0, Replayed; `Counts.olean` mtime 2026-11-05 23:54 unchanged | – | PASS |
| Lean `Su2Plaq.Gates`, `Su2Plaq.Rewrites` (laptop-changed) | build | built 2.7 s + 2.2 s, peak RSS 6.9 GB | – | PASS |
| Lean `Su2Plaq`, `Su2PlaqCert`, default targets (incl. `su2plaq_cert` exe) | build ok, then `--no-build` up-to-date | exit 0, 9101 jobs, "All targets up-to-date" | – | PASS |
| `native_decide` under `lean/Su2Plaq/` | 0 occurrences | 0 (grep) | – | PASS |
| m0 acceptance | all pass | 34 / 34 (12.4 s) | – | PASS |
| m1 acceptance (incl. slow) | all pass | 22 / 22 (101.3 s) | – | PASS |
| m2 acceptance (incl. slow, Lean-calling) | all pass | 46 / 46 (125.1 s) | – | PASS |
| m3 acceptance | 24 pass | 23 / 24 (6.4 s) | – | FAIL (L3) |
| m3x acceptance | 4 pass | 4 / 4 (4.8 s) | – | PASS |
| `tests/unit` | all pass | 489 / 489 (137.5 s) | – | PASS |
| `tools/check_lock.py` | LOCK OK | LOCK OK | – | PASS |
| `~/.claude/bin/acceptance-check` | PASS | exit 1: "tests/acceptance differs from acceptance-v9"; changed: `LOCK.json`, `m2/test_compress_machinery.py`, `m2/test_lean_formal.py` | – | FAIL |

Counts: passed 618 (34+22+46+23+4+489), failed 1, errors 0, skipped 0, xfail 0. Compared with `reports/tests/106` (pre-merge, m3 24/24 with L3 reported as PENDING): the only change in outcome is that L3 now gets past its own PENDING guard (see F1); the laptop's 46 m2 tests and 489 unit tests all pass on the merge.

## Failures

### F1. `test_M3_L3_native_certificate_general_step` — OURS (`su2plaq/spinnet/lean_export.py`); not applicable to laptop master
```
lean_export.certify is not built yet
PENDING: NotImplementedError: lean_export.certify is not built yet
```
The test's own PENDING guard (`"REJECT unimplemented" in Su2PlaqCert/Main.lean`) is now passed because the laptop delivered the checker, so the test proceeds to `LE.certify(...)`, which is still the stub. This is step 3.L3 of `prompts/100`, planned to be PENDING until this merge. The test exists only on track S, so "also fails on laptop master" does not apply. Guess: simply the not-yet-written step 3.L3 (exporter `export_certificate` plus `certify` wrapper calling `lake exe su2plaq_cert check`).

### F2. `acceptance-check` exit 1 — lock bookkeeping, not tampering (neither side's code)
The script compares `tests/acceptance` with the newest `acceptance-vN` tag (ours: `acceptance-v9`). The merge brought in the laptop's own m2 fix (laptop `acceptance-v7`, commit 244f52f, "prompts/006 §12: fix no-op in-place tampering in two locked tests", approved by Digonto 2026-11-05), so those two m2 files and `LOCK.json` differ from `acceptance-v9`.
Evidence that nothing is tampered:
- `git diff 5111d69 HEAD -- tests/acceptance/m0 m1 m2` is empty (m0–m2 byte-identical to laptop master).
- `git diff laptop-acceptance-v7 HEAD -- tests/acceptance/m0 m1 m2 _api.py conftest.py` is empty.
- `git diff laptop-acceptance-v7 5111d69 -- tests/acceptance` is empty (laptop master equals its own lock).
- `python tools/check_lock.py` prints LOCK OK for m0 m1 m2 m3 m3x.
Fix is a coordinator action: lock the merge commit with the project's lock script so a new tag (for example `acceptance-v10`) exists; the tester does not run it. The tag name `acceptance-v7` clashes with ours, hence the fetched name `laptop-acceptance-v7`. Guess: that is the whole fix.

## Other observations
- The working tree is dirty after the run: `compress/lean/structure.json` (laptop-owned data) was rewritten by a laptop m2 test; the diff is only `provenance.git_commit` `4fa765b` → `a7f8dcf` and `structure_certificate.seconds` 53.37 → 25.10. Not committed or reverted by the tester.
- The known laptop-owned flaky unit test `test_results_unit.py::test_render_is_deterministic_and_contains_only_json_numbers` (fails when the short hash contains "c1") did not trigger: `a7f8dcf` has no "c1". It will fail for any such commit.
- Memory: largest single-process RSS 6.81 GB (pytest xdist worker or Lean with Mathlib mapped). `/usr/bin/time` maxima per suite: 0.66, 1.60, 6.82, 6.82, 6.82, 6.81 GB (m0, m1, m2, m3, m3x, unit); Lean builds 6.9, 6.8, 1.1 GB. Sum of RSS over all python/lean processes sampled once per second: peak 19.96 GB (over-counts shared pages). `~/su2qc-sync/memguard.log` shows no kill during this run.
- Wall time: Lean builds 19 s in total; tests 387.5 s (sum of six pytest runs); about 7 min overall.
- Not run: benchmark (not in `full` mode). No source or test files were edited by the tester.
