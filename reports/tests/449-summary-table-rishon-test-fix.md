# Report 449: tester, summary-table rewrite and rishon spy-test fix (mode step)

- Date: 2026-11-20. Builder changes are uncommitted on `688af32`; HEAD moved to `c788a3d` (commits after `688af32` touch only `docs/report-11-cross-encoding-comparison.md`, `notes/STATUS.md`, `reports/audits/309`, so source, tests and result files read here are unchanged).
- Plan in force: `prompts/009` + `prompts/010` (lock `acceptance-v23`). Related reports: 448 (gate, found the order-dependent rishon test), 429 (fuzzy headline step).
- Raw data: `results/tester/449/` (`row_checks.json` 99 field checks, `out/` scratch output of the script, `unit.xml|log|time`, `provenance.json`). Checker script: scratchpad `chk449.py` (reads only the JSON sources, never imports `scripts/summary_table.py`).

## Verdict: PASS

All requested checks pass. Unit suite 1235 passed, 0 failed (582 s, `taskset -c 0-3`, `-n 3`). 99 of 99 independently recomputed numbers of the six Table 2 loop rows and the fuzzy composed row match their source JSON. Nothing is pending (step mode; no acceptance ids named for this step). Lock OK and `acceptance-check` PASS (`tests/acceptance matches acceptance-v23`).

## Commands

```
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
git diff scripts/summary_table.py tests/unit/test_rishon_lean_cert_unit.py
taskset -c 0-3 tools/pytest-safe -n 3 tests/unit/test_summary_table_unit.py tests/unit/test_rishon_lean_cert_unit.py -q   # twice
taskset -c 0-3 tools/pytest-safe -n 0 tests/unit/test_summary_table_unit.py -q
taskset -c 0-3 tools/pytest-safe -n 0 tests/unit/test_rishon_lean_cert_unit.py -q
taskset -c 0-3 tools/pytest-safe -n 0 "tests/unit/test_rishon_lean_cert_unit.py::test_check_cross_compares_at_nominal_alternate_and_irrational_pairs" -q   # x3
# same test, verbatim HEAD version in a temporary copy (moved to should-be-deleted/ afterwards), alone
taskset -c 0-3 python scripts/summary_table.py --out results/tester/449/out
python <scratchpad>/chk449.py
taskset -c 0-3 tools/pytest-safe -n 3 tests/unit -q --junitxml=results/tester/449/unit.xml
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
git checkout -- results/spinnet/certs      # nothing had changed this time
```

## Results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| a1. rishon test diff vs HEAD | assertions byte-identical | `git diff -U0`: only 4 added lines (2 comment lines, `L.exact_target("UD")`, `L.exact_target("UE")`), 0 removed lines, no assertion line touched | exact | PASS |
| a2. warm-up does not weaken the test | spy must still see exactly the explicit `_check_cross` calls | `exact_target` is `lru_cache`d and runs `_check_cross` on a miss (hence 3 extra spy items on a cold cache); after warming, the assertions `[s[3]...] == [NOMINAL_ETA, *ALT_ETA]` and `pairs == [NOMINAL, *ALT_ANGLES, IRRATIONAL]` are unchanged and still exercise the explicit calls | n/a | PASS |
| a3. no hard-coded numbers in `summary_table.py` | every emitted number read from a results file | diff reviewed: numbers only in labelled `HAND_WRITTEN` / `STOP_REASON_TEXT` text and note strings (see Notes) | n/a | PASS |
| b1. new test file alone | 10 pass | 10 passed (0.5 s) | exact | PASS |
| b2. rishon file alone | all pass | 23 passed (32 s) | exact | PASS |
| b3. both files together, 2 runs, `-n 3` | all pass | 33 passed, 33 passed (34 s each) | exact | PASS |
| b4. single rishon test alone, `-n 0`, 3 repeats | pass each time | 1 passed x3 (0.75 s) | exact | PASS |
| b5. same test, verbatim HEAD file alone (control) | fails on cold cache (as in report 448) | FAILED: "Left contains 3 more items, first extra item: 0.29" (the 3 extra spy items from the cache miss) | n/a | confirms the fix targets the real cause |
| c1. headline id of 6 loops vs `summary.json["headline"]["id"]` | equal | twelve r05-F2-005, spinnet r02-F1-002, rishon r06-F3-006, LSH r05-F3-005, fuzzy U_B r10-F1-010, fuzzy link r02-F2-001: 6/6 equal; also equal to the id inside `m4/m6/m8-compressed.json` | exact | PASS |
| c2. robust-key rule | headline = entry of minimum `robust_key` in `results/compress/<enc>/robust.json` | 6/6 minimum equals headline (all 28/N entries of each file considered, not only valid ones) | exact | PASS |
| c3. qubits / CX / rotations / T(1e-6) of the 6 headline rows | equal to source JSON | 24 + 4 numbers per row from `m4/m6/m8` files (T from `t_table` at eps = 1e-6), summary rows (twelve, fuzzy link) and `round-010.json` (fuzzy U_B): all equal; `m4/m6/m8` agree with the summary row of the same id where one exists (rishon, LSH) | exact | PASS |
| c4. error / Lean strings | equal to source | e.g. LSH `valid (err 1.44056e-14)`, `certified` = `m8.extra.headline.lean`; rishon `1.34848e-13`, `certified`; spinnet `5.12669e-15`, `certified`; fuzzy U_B `5.43744e-14`, `n_a` (round-010 candidate has `lean: None`, script uses `HAND_WRITTEN["lean_when_not_run"]`) | exact | PASS |
| c5. general rows, archive best, T_mean, n_rounds | equal to `summary.json` | 6 x 6 fields equal | exact | PASS |
| c6. fuzzy composed step | equal to `compressed_step_headline.json` | CX 227, depth 151, rotations 129, qubits 50, error 1.2e-14; units U_B r10-F1-010 + link r02-F2-001 equal to the two summary headlines; inner arithmetic $83+4\times12=131$ CX | exact | PASS |
| c7. LSH row | r05-F3-005, 24 qubits, 68 CX, 22 rotations, T 1396, certified, "stopped after round 6 (session limit)" | exactly this; `stop.json["reasons"][0] = "max_sessions"` | exact | PASS |
| c8. rishon row | certified, "stopped after round 6" | 52 qubits, 216 CX, 10 rotations, T 832, certified; `n_rounds = 7`; no `stop.json` for rishon so no reason text | exact | PASS |
| c9. cross-check with Report 11 Table 1b and `results/crosscheck/gate-table.json` | same numbers | Table 1b / gate-table headline entries, qubits, CX, nominal T, Lean: twelve 31/111/912, spinnet 17/31/1086, LSH 24/68/1396, rishon 52/216/832, fuzzy U_B 10/83/638, link 4/12/644, composed 131 CX inner and 227 CX with outer, 50 qubits: no mismatch; Table 1c general CX 294, 54, 94, 10102 (unit) all equal to the Table 2 general rows | exact | PASS |
| d. consumers of `loops[].best` | none | no code or test reads `results/summary/encodings-gate-counts.json` (grep over `src scripts tests tools lean`; only the new unit test and the script itself mention the file). Prose in reports 5-addendum, 7, 9, 11 cites the `.md` by name only. The JSON key `best` is not read anywhere | n/a | PASS |
| e. full unit suite `-n 3` | all pass | 1235 passed, 0 failed, 2 warnings (fork DeprecationWarning), 582 s; same count as report 448 (whose working tree already held the 10 new tests) | exact | PASS |
| f. lock | OK | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v23` | n/a | PASS |

## Changes the new script would make to the committed `results/summary/encodings-gate-counts.{md,json}`

Generated into `results/tester/449/out/` (not committed), diffed against `git show HEAD:...`:

Table 1 (general circuits): numbers unchanged. Only the LSH source citations change, read from the result files: `results/lsh/{UE,UB,step}.json @ 3d99f68` becomes `@ 76fd221` (the JSONs were regenerated on a clean commit by the M8 phase-0 step; numbers equal).

Table 2 (compression loops), `best` column renamed `headline`; header "general vs best" becomes "general vs headline":

| row | committed | new script |
|---|---|---|
| 1. 12-qubit | best 31 / 111 / 13 / 912, certified, r05-F2-005, "stopped after round 5" | same numbers; label best becomes headline |
| 2. Spin network | 17 / 31 / 17 / 1086, certified, `r02-F1-002 (headline)` | same numbers; entry text without the "(headline)" suffix; JSON entry commit `02c499d` becomes `5bbaf0f` (provenance commit of `m4-compressed.json`) |
| 3. Rishon | 53 qubits, 228 CX, 10 rot, T 846, err 1.5e-13, Lean n_a, r04-F1-004, "paused: replay rounds 0-4 under 10 % cap" | 52 qubits, 216 CX, 10 rot, T 832, err 1.3e-13, certified, r06-F3-006, "stopped after round 6" |
| 4. LSH | row absent ("M8 not started") | new rows: general 31 / 94 / 8 / 598 (r00-seed-000, `not_run`); headline 24 / 68 / 22 / 1396, err 1.4e-14, certified, r05-F3-005, "stopped after round 6 (session limit)"; the "4. Loop-string-hadron, M8 not started" line is removed |
| 5. Fuzzy U_B | best 11 qubits, 87 CX, 9 rot, T 650, err 4.6e-14, r06-F3-006, "running (round 7)" | headline 10 / 83 / 9 / 638, err 5.4e-14, n_a, r10-F1-010, "stopped after round 13 (Digonto)" |
| 5. Fuzzy link U_E | 4 / 12 / 10 / 644, err 5.6e-15, r02-F2-001, "finished" | same numbers; err 5.5e-15 (formatting `%.6g` of 5.50205e-15 vs old 2-digit rounding; no value change); "finished" |
| 5. Fuzzy composed | 53 qubits, 295 CX, 148 rot, err 1.7e-14, U_B r03-F3-003, "uses the old U_B; to rebuild" | 50 qubits, 227 CX, 129 rot (depth 255 to 151, T fixed 118 to 72, ancilla 5 to 2), err 1.2e-14, "headline composed", U_B r10-F1-010; link r02-F2-001, "headline units (prompts/010)" |
| Notes | "Spin-network best = headline ..." etc. | new text: rule description, two lines naming the loops where headline differs from archive best (spinnet r02-F1-002 vs r04-F1-004, key (31, 1062, 2173, 17); fuzzy U_B r10-F1-010 vs r12-F1-012, key (83, 638, 1517, 10)); Lean note reworded; commit line cites the new commit |

JSON-only additions: `loops[].headline`, `headline_id`, `archive_best`, `archive_best_key`, `t_mean_robust` replace `loops[].best`; `fuzzy_composed_step.rule`, `units.*.robust_key`, `units.*.t_mean`; `fuzzy_composed_step.commit` `7b0e5d0` becomes `cd468e2`; `provenance.git_commit` and `written_utc` change.

## Notes and minor observations (none blocks)

1. Hand-written text (not read from a file): the `20 angle pairs` and `433 states` in note strings, `8e71c38` (fuzzy dirty-tree remark, pre-existing), `" (Digonto)"`, `"finished"`, and fuzzy Lean `n_a`. All sit in `HAND_WRITTEN` / `STOP_REASON_TEXT` or the notes list; none is a result number.
2. Rishon's "stopped after round 6" omits the real stop reason (20 proposer sessions used), because `results/compress/rishon/stop.json` does not exist. Not wrong, only less informative than the LSH row.
3. The entry text in the JSON `entry / commit` field is the commit of the results file for spinnet / rishon / LSH (e.g. rishon `@ 072cdfe`, LSH `@ b422e78`), but the entry's own commit for the other rows. The Markdown prints only the entry id, so tables are unaffected. Report 11 Table 1b cites `m6-compressed.json @ fcd61dd`, whereas the file now carries `072cdfe` (regenerated in `108b458`, numbers unchanged). Citation only.
4. JSON value types are mixed (strings for summary-row fields, ints for the m4/m6/m8 and round-file fields). Pre-existing for spinnet; formatted identically in the Markdown.
5. The script prints `(results dirty)` in the commit line when the results tree has untracked files. My scratch dir `results/tester/449/` made it dirty; the committed copy must be regenerated on a clean tree (or `results/tester/449` committed or moved first) to avoid that text.
6. `results/spinnet/certs/*.json` were not rewritten by this run (`git checkout -- results/spinnet/certs` was a no-op). The temporary HEAD copy of the rishon test was moved to `should-be-deleted/_tmp_head_rishon_cert_449.py`.

## Failures

None.
