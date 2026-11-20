# Tester report 447: M11 provenance snapshot fix (prompts/009 step 11.8, pre-step)

- Date: 2026-11-20. Mode: step. Prompt in force: prompts/009-final-cross-encoding-report-spectra-crosscheck.md.
- Commit under test: HEAD d0a91fa (docs-only commit on top of 4fc2dcb: it changes only `docs/report-11-cross-encoding-comparison.md`; `git diff --stat 4fc2dcb d0a91fa` confirms) plus the uncommitted diff in `src/su2plaq/crosscheck/report.py`, `scripts/m11_results.py`, `tests/unit/test_crosscheck_report_unit.py`.
- Related: reports/tests/423-m11-steps-6-to-7.md.

## Commands
```
tools/pytest-safe -n 8 tests/unit -k "crosscheck or m11"            (taskset -c 0-8)
tools/pytest-safe -n 8 tests/unit                                    (taskset -c 0-8)
tools/pytest-safe -n 4 tests/acceptance/m11 -m "not slow"            (taskset -c 0-7)
python tools/check_lock.py; ~/.claude/bin/acceptance-check; pytest --collect-only -q tests/acceptance
# functional, in /home/digimonk/Projects/su2qc-wt/tester447-m11-snapshot (detached worktree of d0a91fa + 3 files copied in):
tools/run-capped python scripts/m11_results.py --no-headline
```

## Diff review (item 1)
- `git_snapshot()` calls `provenance({})` and returns only `git_commit`, `git_dirty`. `provenance` runs `git status --porcelain --untracked-files=no` (src/su2plaq/metrics/provenance.py), so it is the real status; nothing masks a dirty tree. `git_dirty` is `None` only if git itself fails (unchanged behaviour).
- `_prov(command, git=None)`: with `git=None` the dict is the old one (the new lines are skipped). With a snapshot, only `git_commit` and `git_dirty` are overwritten; versions, platform, cpu_count, seeds, timestamp and command are still read per file. Callers of `_prov` (graphify affected plus grep): `spectra_results`, `gate_table`, and the new unit test. Both new `git=` keywords default to None.
- `scripts/m11_results.py`: the snapshot is taken before `spectra_results`, the first writer. `tradeoff_figure` and `render` are untouched.
- No numerical content changes: the diff touches provenance fields only.

## Results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| unit `-k "crosscheck or m11"` | all pass | 42 passed (42.7 s) incl. new `test_m11_results_takes_one_git_snapshot_before_any_write` | 0 failures | PASS |
| unit, full `tests/unit` | all pass | 1224 passed, 1 failed (984.9 s) | 0 failures | FAIL, pre-existing (below) |
| acceptance m11 `-m "not slow"` | only T2 red | 23 passed, 1 failed = `test_M11_T2_final_report_inputs_complete` (PENDING: rows not final, caches stale or missing) | only T2 | PASS (as expected) |
| `check_lock.py` | LOCK OK | LOCK OK | - | PASS |
| `acceptance-check` | PASS | matches acceptance-v23 | - | PASS |
| `pytest --collect-only -q tests/acceptance` | clean | 407 collected, no errors | - | PASS |
| worktree = HEAD + 3 changed files (dirty at start) | both `git_dirty` True, same commit | spectra d0a91fa True; gate-table d0a91fa True | exact | PASS |
| worktree after temporary local commit 6af9dd8 (clean at start, `git status --porcelain --untracked-files=no` empty) | both False, same commit | spectra 6af9dd8 False; gate-table 6af9dd8 False; tree dirty afterwards (M gate-table.json, spectra.json) | exact | PASS |
| rerun in that now-dirty worktree | both True | both 6af9dd8 True | exact | PASS |

The clean case shows the bug is fixed. Before the fix, the same flow gave spectra False and gate-table True. The unit test reproduces the mechanism with a monkeypatched `_git` (the first write flips status to dirty) and asserts both files say False.

### Failing unit test (pre-existing, unrelated)
`tests/unit/test_rishon_lean_cert_unit.py::test_check_cross_compares_at_nominal_alternate_and_irrational_pairs`:
`assert [0.29, 0.53, ...9, 0.53, 1.07] == [0.29, 0.53, 1.07]` (6 inner_target calls, test expects 3). It fails identically when run alone at a pristine worktree of 4fc2dcb with no local changes (checked in a temporary worktree, removed afterwards). It does not touch the crosscheck report code. Guess: `_check_cross` in `src/su2plaq/rishon/lean_cert.py` (line 276) now loops over two groups of angle pairs, and the unit test assertion was not updated. This is not a regression from this change, but the coordinator should note it as an open failure (it is not in the acceptance tests, so it cannot block T2).

## Files rewritten by test runs (item 5)
Main tree, `git status --porcelain --untracked-files=no` beyond the 3 intended files:
- `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json` (modified; it was clean at the start of this session, so one of the unit or acceptance runs rewrote it; the diff is a one-line change in a single-line JSON cert). Not restored, per instructions.
- No untracked files other than this report.
- `results/crosscheck/*` in the main tree was NOT touched (all regeneration was in the worktree).

## Observations (no action needed, FYI)
- HEAD moved from 4fc2dcb to d0a91fa while I worked (coordinator committed the report draft); the three files under test were unchanged.
- In the throwaway worktree, `--no-headline` printed every gate-table row as "final", while the T2 acceptance test in the main tree reports rows pending because of stale or missing headline caches. I did not investigate (outside this change).

## Leftovers
- Throwaway worktree kept: `/home/digimonk/Projects/su2qc-wt/tester447-m11-snapshot` (detached, contains my temporary commit 6af9dd8 on top of d0a91fa; regenerated results there are NOT for use). Remove with `git worktree remove --force` when done. `/home/digimonk/Projects/su2qc-wt/regen-m11-4fc2dcb` untouched.

## Verdict
PASS for the change under test. One unrelated pre-existing unit failure (rishon lean_cert cross-check test) is reported.
