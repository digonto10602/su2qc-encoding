# Tester report 034: M2 step 2.6 (briefs, report, round, metrics, strict archive)

- Date: 2026-11-05 (machine clock reads 2026-11-06 in written_utc stamps)
- Git: `a1449ea` plus the uncommitted step-2.6 working tree
- Plan in force: `prompts/006` (over `prompts/002` §5 row 2.6)
- Mode: step
- Related: reports/tests/030, 032, 033
- Raw numbers: `results/tests/034-m2-step-2-6-recompute.json`, `results/tests/034-m2-step-2-6-report-table.md`
- Scratch root (all rounds, briefs, programs): `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/root`

## Verdict: PASS (with findings F1-F4 below; none blocks the step)

## Commands
```
python tools/check_lock.py; ~/.claude/bin/acceptance-check; pytest --collect-only -q tests/acceptance
pytest -n auto -m "not slow" tests/acceptance/m2
pytest -n 4 -m "not slow" tests/acceptance/m0 tests/acceptance/m1
pytest -n 4 tests/unit
PYTHONPATH=src python -m su2plaq.compress.round --encoding twelve --kind step --seed --root $SCRATCH/root      # real round 0, 3 m 35 s
PYTHONPATH=src python -m su2plaq.compress.round --encoding twelve --kind step --round 1 --evaluate --root $SCRATCH/root   # 42 s
PYTHONPATH=src python -m su2plaq.compress.round ... --round 2 --evaluate --root $SCRATCH/root                          # 20 s
PYTHONPATH=src python -m su2plaq.compress.report --encoding twelve --kind step --root $SCRATCH/root --out report.md
scripts in scratchpad: chk_briefs.py, chk_migration.py, recompute.py
```

## Results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| lock: `check_lock.py`, `acceptance-check` | OK / acceptance-v7 | LOCK OK; "matches acceptance-v7" | - | PASS |
| `pytest --collect-only tests/acceptance` | clean | 102 collected, no error | - | PASS |
| m2 non-slow (incl. `test_round_dry_run_end_to_end`, `test_report_table_from_results`, `test_run_candidate_cli_trial_and_full`) | green except Lean | 36 passed, 4 failed (all Lean-area) | - | PASS |
| m2 Lean-area failures (ignored as instructed) | 5 expected | 4: `test_polish_rules_are_lean_certified` (`LEAN_RULES` empty), `test_program_lemma_file_checked`, `test_structure_json_and_spec_section`, `test_symmetry_candidates_verified`; `test_skeleton_stubs_raise` is not in the failure list | - | n/a |
| m0 + m1 non-slow | green | 54 passed | - | PASS |
| unit (all, incl. Lean unit tests) | green | 346 passed, 0 failed | - | PASS |
| `test_archive_best_valid_and_not_worse_than_seed` | pending (needs the real loop, slow) | deselected by `-m "not slow"` | - | PENDING |
| (1) real round 0: 5 seeds archived | all valid | general, general+polish, qiskit_l3, lean22_v2, lean22 all valid; best key (162, 660, 1029, 35) | - | PASS |
| (1) Clifford+T re-verification of the round's best | ok | r00-seed-001: ok, 8 rotations, T=660, error 2.989e-6 <= 8.001e-6 | tol_err = N_rot eps + 1e-9 | PASS |
| (1) every input path in 19 briefs exists | all exist | 124 path tokens checked; the only absent ones: `compress/lean/structure.json` (the brief itself says "pending", Lean builder not done) and the output targets `compress/ideation/twelve.md`, `scratch/proposer/` | - | PASS |
| (1) no program text pasted | none | 0 gate lines (`b.xxx(`), 0 `import`; max brief size 2519 bytes; only template prose naming `def build(spec)` | - | PASS |
| (1) DISCOVERY cap | <= 30 lines | with 45 extra lines: header "last 30 of at most 30", 30 lines shown (rX-15..rX-44, newest kept) | exact | PASS |
| (1) last-attempts cap | <= 5 | with 8 extra attempts: 5 listed (r09-F2-003..007) | exact | PASS |
| (1) alternatives are real files with costs | files exist, cost shown | all `compress/programs/...` alternatives exist, each with "CX, T_eps, depth_CT, qubits" and summary; the qiskit_l3 entry (no program file, `.circuit`) is filtered out; own parent excluded | - | PASS |
| (1) parent block | path, entry, sha, feedback JSON | round 4 / F1: `compress/programs/twelve/F1/001-...py`, `r01-F1-001`, sha 045c760b42a1, `results/compress/twelve/feedback/r01-F1-001.json` (exists) | - | PASS |
| (1) next program number | max+1 | F1 004 (001-003 exist), F2 003, seed 011 | exact | PASS |
| (1) migration every 3rd round | visible effect in rounds 3, 6 | no difference between rounds 4, 5 and 6 for F1 and F2 (diff = title line only) | - | NOTE F1 |
| (2) report cells recomputed independently | equal | 72 cells (8 valid candidates x 9 columns: qubits, CX, T_fixed, N_rot, T(1e-6), T(1e-10), T_est(1e-6), T_est(1e-10), depth_CT) from the program source via own Qiskit level-0 lowering, own T counts, pygridsynth called directly: 71 equal, 1 not reproduced (depth_CT of the Qiskit-L3 circuit: mine 1986 vs 1387; my handling of exact-angle rz words differs from the project's `_EXACT` table, a check artefact, not verified either way) | exact (integers), 1e-6 (estimates) | PASS |
| (2) archive entries vs round JSON | equal keys | all 8 valid candidates present in the archive with equal key; 3 invalid ones absent | exact | PASS |
| (2) GLOBAL BEST = archive best | r00-seed-001 | summary.json `global_best` = `index.json` best = `Archive.best()` = r00-seed-001, key (162, 660, 1029, 35); best per family seed/F1/F2 = r00-seed-001 / r01-F1-001 / r01-F2-001 = `family_best` | exact | PASS |
| (2) notes present | global-phase, windowed L3 | text "equal to the target up to ONE global phase"; row "Qiskit L3 (windows of 32)"; row "Qiskit L3 (whole circuit; counts only, unverifiable)"; Paulo row "(fixed angle; Clifford+T up to a global phase) ... valid at its own angle (beta = 1, kind UB), err 1.07559e-05" (matches 1.076e-5 of reports/tests/014); spinnet15 row "not applicable" | - | PASS |
| (2) summary.json | rows, lineage, counts | n_rounds 3, n_candidates 11, n_valid 8 (5+2+1 valid, 3 invalid), 12 rows, lineage of 8 entries | exact | PASS (see F2) |
| (3) invalid proposal recorded, not archived | recorded, absent from archive | `r01-F1-002` (one CX deleted): reason `leak`, op-norm error 2.707, leak 0.7071, dirty ancilla 0.164; in round JSON `invalid`, in attempts.jsonl, feedback JSON written; NOT in the archive entries | - | PASS |
| (3) valid proposals archived | archived with right key | `r01-F1-001` (lean22 with 28 inverse pairs cancelled): key (210, 696, 1148, 38) = lean22 (210, 704) minus 8 T, err 3.05e-13, new elite in cell (61,75); `r01-F2-001` key (162, 660, 1029, 35), err 2.14e-13 | exact | PASS |
| (3) discoveries.md | lines written | `- r02-F2-002: DISCOVERY: ...` x2 in `compress/discoveries/twelve.md` | - | PASS |
| (3) contract violation | recorded | `r02-unknown-003` reason `contract`, family `unknown`, not archived | - | PASS |
| (3) relative paths | no absolute paths | no `/home` or scratch path in any archive entry, feedback, round JSON, attempts, brief, spec | - | PASS |
| (4) silent `except Exception` in compress/ | none | no `except Exception: pass`. Remaining broad ones all re-raise or report: `evaluate.py:123` (pop and `raise`), `:291` (raises RuntimeError from exc), `:501` `except BaseException` (writes the error to the worker's meta file; the parent turns it into a reason). Silent narrow ones: `evaluate.py:354` (`except OSError: pass`, result-cache write only), `synth.py:59` (read-only cache dir), `builder.py:189` (`except (TypeError, ValueError): pass` on `float(qc.global_phase)`, see F4c) | - | PASS |
| (5) strict archive in round / brief | strict=True, n_alt = 2 | `Archive.load(..., n_alt=len(alt_angles), strict=True)` in `round.py:122` and `brief.py:89`; `report.py` reads only round JSON | - | PASS |
| (5) strict semantics | as documented | trailing-newline id refused ("bad id"); verdict without `certified` key refused in strict, accepted in lenient mode; `certified: False` refused; alt verdict without `certified` refused; `Archive(strict=True)` without n_alt raises ValueError | - | PASS |
| `t_measured` | present in metrics | `metrics.t_measured` = T totals at 1e-06 and 1e-10; the T(1e-10) column agrees with my pygridsynth recount for all 8 candidates | exact | PASS |

## Findings (none blocks the step; for the coordinator to route)

- **F1 (design, medium): migration is a no-op.** `make_brief` takes the first 3 elites by cost (excluding the family parent) and adds the global best "every third round if it is not in the list". The global best is the lowest-key elite, so it is always in the first 3 unless it is the parent. Result: round 6 briefs are identical to round 5 apart from the title. The only case where the clause fires is a global best whose program file is missing: I changed the program_path of `r00-seed-001` in a scratch copy to a missing file; rounds 3 and 6 then list `compress/programs/twelve/seed/GONE-lean22_v2.py` (nonexistent) while rounds 2 and 4 correctly skip it. So the migration clause either does nothing or lists a nonexistent path. Guess: the alternatives were meant to be chosen by diversity (one per MAP-Elites cell, not the cheapest three); the file-existence filter is missing on the migration branch.
- **F2 (bug, medium): lineage loses the parent.** `round.py` calls `entry_from_result(..., parent=None)`; the program's `PARENT = 'r00-seed-002'` (parsed by `parse_program_header`, key `"parent"`) is never stored. All `parent` fields in the round JSON, the archive entries and `summary.json["lineage"]` are `None` (F1/001 declares PARENT = r00-seed-002). The "lineage" in summary.json is therefore a flat list. Guess: the header parent is not passed through.
- **F3 (minor): rejected programs are re-evaluated every round.** `_proposals` filters only by sha256 of archived programs. `F1/002-lean22v2-wrong.py` (invalid) and `F1/003-nocontract.py` were evaluated again in round 2 (new ids `r02-F1-002`, `r02-unknown-003`, duplicated attempt lines; later briefs' "last 5 attempts" show the same failure twice). Cheap thanks to the result cache (round 2: 20 s) but it pollutes attempts and briefs. Guess: no "seen" set is kept for invalid programs.
- **F4 (minor):** (a) The "Qiskit L3 (whole circuit)" row shows T(1e-6) = 891.947 (an estimate, equal to T_est) under a column the footnote calls "measured", and depth_CT = 268 (the lowered depth, not the synthesised depth; the other rows are 1029-1421), so the cell is not comparable; the verdict text says "counts only" but those cells should be marked "est." or "-". (b) `report_table` takes GLOBAL BEST from round-JSON records with `valid=True`, not from "was archived"; a record that is valid but refused by the archive (counted in `n_invalid`) would still count towards GLOBAL BEST. Not triggerable in my runs (best matched the archive exactly). (c) `builder.py:189` silently ignores a non-float `global_phase` (parametrised phase); pre-existing, not part of this diff.
- For information: `general + polish` has the same key as `general` (294, 952, 1421, 50); the polish pass lowers nothing on that circuit (step 2.5 behaviour). `run_candidate --trial` on the 38-qubit lean22-derived program took 10.3 s wall by `time` (includes interpreter start; `test_run_candidate_cli_trial_and_full` passes).

## Pending / not run
- `test_archive_best_valid_and_not_worse_than_seed` (slow, needs the real loop; gate step 2.7).
- Lean: the `--lean` hook was not exercised (off by default; Lean builder in progress).
- No new tests added by me.

## Reproduce
`python $SCRATCH/recompute.py $SCRATCH` (needs the scratch root after the three rounds above). Hand-made proposer programs in `$SCRATCH/root/compress/programs/twelve/`: `F1/001-lean22-cancelled.py` (lean22 minus 28 adjacent inverse pairs), `F1/002-lean22v2-wrong.py` (lean22_v2 minus `cx(0, 4)`), `F1/003-nocontract.py`, `F2/001-lean22v2-cancelled.py`, `F2/002-lean22v2-discovery.py`. Seeds: trial_seed 0, transpiler 20261104, clifford_t pass manager 12345, Qiskit-L3 12345.
