# Tester report 451: summary Lean status from certificate records + m11 `--root` provenance

- Date: 2026-11-22. Mode: step. Tested on HEAD 3ccce75 plus uncommitted builder changes (HEAD advanced to 98c7ff4 during the run; that commit is docs/CLAUDE.md only, the code under test is unchanged).
- Prompt in force: prompts/009 (+010), project CLAUDE.md. Related: reports/tests/449, reports/tests/450, reports/audits/309 (N10).
- Raw data: `results/tester/451/` (hashes.json, json_diffs.json, m11_diffs.json, logs). Scratch outputs: `scratch/t451/`.

## Commands (all `taskset -c 0-5`, one stream at a time, env as in CLAUDE.md)
```
python results/tester/451/hashes.py                       # adapted from 448, writes 451/hashes.json
python scripts/summary_table.py --out scratch/t451/summary
git archive HEAD | tar -x -C scratch/t451/root; git init+commit there (be8befd, clean)
python scripts/m11_results.py --root $PWD/scratch/t451/root
tools/pytest-safe -n 4 tests/unit
tools/pytest-safe -n 4 tests/acceptance/m11 -m "slow or not slow"
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; git checkout -- results/spinnet/certs
```

## Results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| a. diff review: no hard-coded status/numbers | none | status values only come from records (`d["status"]`, `extra.lean.status`, `before_after` general/unit `lean`); only literal strings are source labels and the pre-existing `lean_when_not_run` (fuzzy n_a, plan 302 s0.5) | - | PASS |
| a. record for another circuit cannot override | match required | `status and matches` else archive; match = qubit count (twelve 50, LSH 31) or entry id (rishon r00-seed-000); unit test covers wrong-qubit, missing status, missing file | - | PASS (see note 1) |
| a. no test weakened | additions only | `git diff tests`: 0 removed lines, 102 added | - | PASS |
| a. number-producing paths unchanged | none | removed lines in src/scripts concern only Lean/source columns, notes text, column widths, and `git_snapshot`/`_git` cwd; `git_snapshot()` still runs the same two git commands as `provenance()` | - | PASS |
| b. 9 frozen code hashes == 434-hashes.json | 9/9 equal | 9/9 equal (`all_equal` true) | exact | PASS |
| c. general-row Lean vs source (independent read of the JSON files) | twelve/spinnet/rishon/LSH certified, fuzzy n_a | twelve cert `status`=certified (n_qubits_circuit 50); LSH `extra.lean.status`=certified (n_qubits 31); rishon m6 `before_after` general/unit r00-seed-000 `lean`=certified; spinnet summary.json row "general" Lean=certified; fuzzy: no record, n_a | exact | PASS |
| c. equals Report 11 Table 1a | native-certified / certified (compiled checker) / native-certified / native-certified / n_a | consistent for all 6 rows | exact | PASS |
| c. numeric cells identical to committed summary | no diff | recursive JSON diff: 0 numeric differences; `.md` diff only in Lean columns, Lean source column, Lean/notes text, commit line | exact | PASS |
| d. m11 `--root` provenance describes root | commit = root HEAD, dirty False | commit be8befd (root HEAD), `git_dirty` False although the run then wrote files into root; `provenance.root` = root path; not the checkout's HEAD | exact | PASS |
| d. numbers equal committed crosscheck | equal | gate-table.json: 4 diffs, all provenance (command, commit, root, timestamp); spectra.json: 13 diffs = 9 wall-clock `seconds` fields (3.43 vs 3.41 s etc.) + same 4 provenance keys; `tables.md` byte-identical | exact (seconds excluded) | PASS |
| e. unit tests | all pass | 1247 passed, 2 warnings, 463 s | - | PASS |
| e. acceptance m11 (slow+not slow) | 33 | 33 passed, 59 s | - | PASS |
| e. `check_lock.py`, `acceptance-check`, collect-only | PASS | LOCK OK; PASS (acceptance-v23); 407 collected, clean | - | PASS |

## Cells that would change in results/summary/encodings-gate-counts.{md,json} (all Lean-related)
General rows, `Lean`: twelve not_run -> certified; rishon n_a -> certified; LSH not_run -> certified; fuzzy U_B not_run -> n_a; fuzzy link U_E not_run -> n_a (spin network certified unchanged). New column `Lean source` for every row of Table 2 (the fuzzy full-step rows get "-"). Notes text for Lean rewritten (old "rishon general: 3 angles" sentence removed). Provenance: commit b8e8d76 -> 3ccce75, `results_dirty` False -> True (working tree dirty at run time; regenerate on a clean commit), timestamp. Headline Lean values unchanged.

## Notes (not failures)
1. Matching for twelve and LSH is by qubit count only (50 / 31). It is enough here (the records name the same circuit: `general_circuit(twelve, step)`, LSH `build_step(0.37,0.61,1,with_outer=True)`), but a different circuit with the same qubit count would be accepted; entry id is used for rishon.
2. The fuzzy-link headline row Lean = n_a is labelled "archive: results/compress/fuzzy_link/summary.json" (value n_a is the archive field), while fuzzy U_B headline says "no exact Lean exporter". Cosmetic inconsistency.
3. The committed summary must be regenerated on a clean commit after this change is committed (otherwise it will say "results dirty").
4. `results/spinnet/certs` restored with `git checkout`; only intended files are modified.

VERDICT: PASS
