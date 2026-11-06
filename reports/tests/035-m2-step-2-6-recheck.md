# Tester report 035: M2 step 2.6 recheck (fixes for F1-F4 of report 034)

- Date: 2026-11-05
- Git: `1ffe010` plus uncommitted changes in `src/su2plaq/compress/{brief,builder,report,round}.py` and tests
- Plan in force: `prompts/006` (over `prompts/002` §5 row 2.6)
- Mode: step
- Related: reports/tests/034
- Scratch root: `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/root2` (fresh real round 0, then simulated rounds 1-4; briefs for rounds 1-6 of seed, F1-F4)

## Verdict: PASS

## Commands
```
python tools/check_lock.py; ~/.claude/bin/acceptance-check; pytest --collect-only -q tests/acceptance
pytest -n 4 -m "not slow" tests/acceptance/m2 ; pytest -n 4 -m "not slow" tests/acceptance/m0 tests/acceptance/m1 ; pytest -n 4 tests/unit
PYTHONPATH=src python -m su2plaq.compress.round --encoding twelve --kind step --seed --root $SCRATCH/root2          # real round 0 (6 m 25 s, machine under load)
... --round 1 / 2 / 3 / 4 --evaluate --root $SCRATCH/root2      # hand-written proposer programs F1-F5
PYTHONPATH=src python $SCRATCH/chk2.py $SCRATCH ; python -m su2plaq.compress.report ... --root $SCRATCH/root2 ; python $SCRATCH/recompute2.py $SCRATCH
```

## Results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| lock (`check_lock`, `acceptance-check`, collect) | OK | LOCK OK; matches acceptance-v7; 102 collected | - | PASS |
| m2 non-slow | green except Lean | 36 passed, 4 failed (Lean-area: `test_polish_rules_are_lean_certified`, `test_program_lemma_file_checked`, `test_symmetry_candidates_verified`, `test_structure_json_and_spec_section`); incl. `test_round_dry_run_end_to_end`, `test_report_table_from_results` | - | PASS |
| m0 + m1 non-slow | green | 54 passed | - | PASS |
| unit | green | 352 passed (346 before, +6 new) | - | PASS |
| round 0 real | 5 seeds valid | 5 valid, best (162, 660, 1029, 35) = lean22_v2; Clifford+T check error 2.99e-6 <= 8.0e-6 | - | PASS |
| F1 alternatives by diversity | other families first, then other cells | F1 brief: [seed best lean22_v2, F3, F4]; F2 brief: [lean22_v2, F3, F1]; F3: [lean22_v2, F1, F4]; seed brief: [F3, F1, F4] (all 3 from other families, cheapest first) | - | PASS |
| F1 file-exists filter | no missing alternative path | 232 path tokens in 31 briefs; only absent: `compress/lean/structure.json` (brief says "pending"), `compress/ideation/twelve.md`, `scratch/proposer/` (output targets) | - | PASS |
| F1 migration fires with real files | rounds 3, 6 differ from 4, 5 | seed family: rounds 3 and 6 = [F3, F1, **r00-seed-001**] (global best, real file `compress/programs/twelve/seed/001-lean22_v2.py`), rounds 1, 2, 4, 5 = [F3, F1, F4]; alts 4==5 True, 5==6 False, 3==4 False | - | PASS |
| F1 other families | no change when global best already offered | F1-F4 briefs identical across rounds 1-6 (global best is always among the other-family picks, so migration has nothing to add) | - | NOTE (by construction) |
| F1 parent block | present | F1 round 4: `F1/001-lean22-cancelled.py`, entry r01-F1-001, feedback JSON exists | - | PASS |
| F2 header PARENT stored | parent in attempts, archive, round JSON, lineage | r01-F1-001 -> r00-seed-002, r01-F2-001 / r02-F2-002 / r03-F3-002 / r03-F4-002 -> r00-seed-001; summary.json lineage carries the same 10 `parent` values | exact | PASS |
| F2 unknown parent | `parent_known: false` | program with `PARENT = 'r77-ghost-009'`: attempts `parent_known False`, round JSON `parent_known False`; known parents `True` | - | PASS |
| F3 rejected programs not re-evaluated | once only | round 2: n_invalid 3 = new programs only (nocontract, F3/001 and F4/001 build_error); `r01-F1-002` (invalid) not re-listed; round 3: n_invalid 0 although F3/001, F4/001, F1/002, F1/003 still sit in the tree; briefs show F1's attempts as 2 (no duplicate) | - | PASS |
| F3 attempts store sha | program_sha256 in each line | present in every line except the circuit-only baseline (qiskit_l3: empty, it has no program file) | - | PASS |
| F4a whole-circuit L3 row | estimate-only, n/a cells | row "Qiskit L3 (whole circuit; counts only)": CX 290, T_fixed 294, N_rot 10, T_est(1e-6) 891.947, T(1e-6) / T(1e-10) / depth_CT = "n/a (unverifiable)" | - | PASS |
| F4b GLOBAL BEST / per-family from archived entries only | fake record ignored | injected a valid record `r04-FAKE-001` (CX 100) into a copy of round-004.json without listing it in `entries`: GLOBAL BEST stays r00-seed-001 (162, 660, 1029, 35), no FAKE row; on the real root2 GLOBAL BEST = archive best | exact | PASS |
| F4c `append_qiskit` global phase | raises | parametrised phase -> `BuilderError: the circuit's global phase must be a number`; NaN -> `BuilderError: ... must be finite` | - | PASS |
| report cells recomputed independently | equal | 99 cells (11 valid candidates x 9 columns) from program source, own lowering + pygridsynth: 98 equal; 1 not reproduced = depth_CT of the Qiskit-L3 circuit (mine 1986 vs 1387), same artefact as report 034 (my exact-angle word handling), unchanged | exact | PASS |
| strict archive in round / brief | strict=True | unchanged (`round.py`, `brief.py`) | - | PASS |
| silent `except Exception` | none | the removed silent `except (TypeError, ValueError): pass` in `builder.py` is gone; no new silent handler in the diff | - | PASS |

## Notes
- Hand-made programs used (in root2): F1/001 lean22 minus 28 adjacent inverse pairs (T_eps 696), F1/002 wrong (one CX removed, leak 0.707), F1/003 no contract, F2/001-002 lean22_v2 cancelled, F3/002 and F4/002 lean22_v2 plus 20 / 40 redundant CX pairs (CX 202 / 242, own MAP-Elites cells), F5/001 ghost parent. F3/001, F4/001 (placing the pairs before `alloc`) failed with `build_error` in round 2, as they should, and were not re-evaluated afterwards.
- The not-reproduced depth_CT cell and the 4 Lean failures are the same as in report 034.
- Raw numbers: not re-saved (same script as 034, `recompute2.py` in the scratchpad; 98/99 cells equal).
