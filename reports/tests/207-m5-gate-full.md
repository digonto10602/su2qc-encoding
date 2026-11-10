# Report 207 — M5 milestone gate, tester mode `full` (desktop track R)

- Date: 2026-11-06
- Commit tested: `f1cafdc` at start; HEAD moved to `ac4c210` ("STATUS: gate started") during the run. `git diff --stat f1cafdc ac4c210` = `notes/STATUS.md` only (1 line), so the code/tests/results tested are identical.
- Branch `m5-rishon`, acceptance tag state: `acceptance-v8` (LOCK OK).
- Prompt in force: `prompts/200-rishon-m5-plan.md` (+ one-off test fix `prompts/201`)
- Mode: full (milestone gate step 1 for M5), slow tests included
- Related reports: `reports/tests/200` … `206` (steps 5.0–5.10, Lean 5.L1–5.L3)
- Raw outputs: `results/rishon/tester-207-*` (logs, junit XML, `.time` files with `/usr/bin/time -v`, `tester-207-m2-classified.json`, `tester-207-qpy-counts.{py,json}`)

## Commands (env `su2qc-coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `source ~/.elan/env`, all under `taskset -c 10-19`)
```
pytest -n 10 tests/acceptance/m0   --junitxml=results/rishon/tester-207-m0.xml -q -rA
pytest -n 10 tests/acceptance/m1   ...
pytest -n 10 tests/acceptance/m5   ...                 # includes @slow T1 tests
pytest -n 10 tests/unit            ...
pytest -n 10 tests/acceptance/m2   ...                 # laptop-owned, PENDING expected
~/.claude/bin/acceptance-check ; python tools/check_lock.py
git diff b4c1917 f1cafdc --stat -- src/su2plaq scripts tools
```
No source, test, prompt or tolerance file was edited (`git status` shows only `results/rishon/tester-207-*` untracked).

## Results

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| acceptance m0 | all pass | 34 passed, 0 fail, 0 skip, 12.2 s wall | exact | PASS |
| acceptance m1 | all pass (incl. slow) | 22 passed, 0 fail, 97.6 s wall | exact | PASS |
| acceptance m5 | all pass (incl. slow T1) | 34 passed, 0 fail, 0 skip, 840.6 s wall (T1[step] 473 s, T1[UB] 366 s, S1 order 2 106 s, B1 sensitivity 78 s) | exact | PASS |
| unit (`tests/unit`) | all pass | 308 passed, 0 fail, 97 s wall | exact | PASS |
| `acceptance-check` | PASS | "PASS: tests/acceptance matches acceptance-v8", exit 0 | — | PASS |
| `tools/check_lock.py` | LOCK OK | "LOCK OK", exit 0 | — | PASS |
| m2 (laptop-owned) | PENDING-expected | 7 passed, 39 failed, 3.7 s; 38 of 39 are `NotImplementedError: … is not built yet`; 1 is a missing artifact `lean/certs/twelve-general-step.lean` (M2 deliverable not yet generated) | not a failure on this branch | PENDING (39), none for another reason |
| results provenance | `git_commit` b4c1917, dirty false | all 7 `results/rishon/{UB,UE,UE_outer_row,step,step_order2,observables,register_rows}.json`: `b4c1917`, `git_dirty: false`; command `python scripts/m5_results.py --jobs 6`, `quick: false` | exact | PASS |
| code changed since b4c1917 | only inert files | `git diff b4c1917 f1cafdc -- src/su2plaq scripts tools` = `src/su2plaq/rishon/lean_export.py` only | — | PASS |
| `lean_export` not used by results script | not imported | imports of `scripts/m5_results.py` are circuits.rishon, encodings.rishon, metrics.{cliffordt,logical,provenance}, results.store, rishon.{observables,results,verify}; `grep -rn lean_export src scripts tools` hits only `lean_export.py` itself; users are tests only (`tests/acceptance/m5/test_rishon_lean.py`, two unit tests) | — | PASS |
| stored gate counts (spot check of JSON `metrics.gates_lowered`) | match 204/205 | UB 10 094 CX / 162 rz / lowered depth 13 682; step 10 102 CX / 166 rz / 13 685; order-2 10 110 CX / 170 rz; UE 8 CX / 4 rz / depth 3; UE_outer_row 24 CX / 12 rz (= 8+16, 4+8) | exact | PASS |
| verification flags in JSON | ok | UB, UE, step, step_order2: `ok` and `certified` true (method `inner_block`); UE_outer_row `ok` true, `certified` false, method `outer_electric_check` (sampled, labelled as such) | — | PASS (as designed) |

Pending-expected m2 list: 17 × `general_circuit`, 4 × `Archive.load`, 4 × `gridsynth_T`, 3 × `import_seed`, 2 × `general_program_path`, 1 each `evaluate_circuit`, `code_hash`, `qiskit_l3`, `lean.certify.export_raw_circuit`, `lean.certify.certify_circuit_kind`, `lean.structure.{export_structure_certificate, symmetry_candidates, structure_facts}`, plus the missing file `lean/certs/twelve-general-step.lean` (`test_lean_theorem_file_general`). Details: `results/rishon/tester-207-m2-classified.json`.

## Flaky test
`tests/unit/test_results_unit.py::test_render_is_deterministic_and_contains_only_json_numbers` asserts `"c1" in t` / `"c1" not in t_noq`; it fails only when the HEAD hash contains the substring `c1`. HEAD was `f1cafdc` and then `ac4c210`; neither contains `c1`, and the test PASSED. (The old commit b4c1917 does contain `c1`; that is why it failed in report 206.) No hash-only failure this run.

## Resources (wall times above)
- `/usr/bin/time -v` max resident set of the largest single process: m0 0.65 GB, m1 1.60 GB, m5 6.81 GB, unit 6.82 GB, m2 6.82 GB. (The 6.8 GB figure for a 3.7 s m2 run is suspicious; a trivial python under the same wrapper gives 10 MB. Guess: one oracle/spec test allocates a dense 12-qubit-scale or 38 432-state object. Not investigated further.)
- During m5, summed RSS of all python processes sampled every 10 s: peak 5.84 GB (below the 10 GB limit). Summed RSS for the unit and m2 runs was not sampled; no memguard kill occurred and no test failed with MemoryError.

## Notes (none blocking)
- Peak single-process RSS of 6.8 GB in unit tests leaves ~3 GB headroom to the 10 GB per-job budget if two such workers coincide; summed unit peak unknown (not measured).
- Open planner items already in `notes/STATUS.md` (reports 204 N1–N3, 203 N3, 205 N3) are unchanged by this run.

VERDICT: PASS
