# Tester report 025 — M2 step 2.L1 (Lean project skeleton)

- Date: 2026-11-05; git: `cdc6551` (HEAD moved from fb0678d during the run; working tree dirty with the 2.L1 and 2.1 files)
- Plan in force: `prompts/006-lean-formal-verification-m2-addendum.md` (§2–§6), acceptance-v6
- Mode: step. Out of scope (other builder, step 2.1): `src/su2plaq/compress/*`, compress unit/acceptance tests.
- Raw numbers: `results/tester_m2_step2l1_lean.json`; scratch scripts `scratch/t2l1_axioms.py`, `scratch/t2l1_sorry.py`.

## Commands
```
graphify update . ; graphify query ...
mv lean/.lake/build <scratchpad>/old_build && (time lake build)         # clean build
lake env lean <each Su2PlaqCert/*.lean>; printf 'import Su2PlaqCert\n#check Real' | lake env lean
pytest tests/acceptance/m2/test_lean_formal.py -k test_lean_project_present_and_builds_checker
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
pytest -n auto tests/unit  (x4) ; pytest tests/unit/test_lean_project_unit.py (x2 serial)
pytest -n auto -m "not slow" tests/acceptance/m0 tests/acceptance/m1 ; pytest -m "not slow" tests/acceptance/m2
python -I scratch/t2l1_axioms.py ; python -I scratch/t2l1_sorry.py ; ast comparison of the locked lists
```

## Results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `m2/test_lean_formal.py::test_lean_project_present_and_builds_checker` | PASS | PASS (2.9 s, warm build) | <= 600 s | PASS |
| collect-only `tests/acceptance` | 102, clean | 102 collected, no error | exact | PASS |
| `tools/check_lock.py`, `acceptance-check` | LOCK OK / PASS v6 | "LOCK OK" / "PASS: matches acceptance-v6" | – | PASS |
| m0+m1 acceptance, not slow | all green | 54 passed (183 s) | – | PASS |
| unit suite `-n auto` runs 1,3,4 | green | 201, 202, 202 passed | – | PASS |
| unit suite `-n auto` run 2 | green | 200 passed, 1 failed (see N1) | – | FAIL (test-race, not product bug) |
| `test_lean_project_unit.py` serial x2 | green | 7 passed both (17 s) | – | PASS |
| 6 concurrent `print_axioms` processes | all correct, no leftover file | 6/6 correct; no `lean/AxiomCheck*` left | – | PASS (per-pid fix works) |
| clean `lake build` (`.lake/build` moved away) | succeeds, no Mathlib from source | rc 0, 22.4 s wall (84 s user), 9089 jobs; log lines start at job 9046 = only Su2PlaqCert*, su2plaq_cert, Su2Plaq* built; 0 Mathlib/Aesop/Batteries/Qq/Plausible modules compiled; 10 `Su2Plaq.*` Mathlib-importing modules built in 8–9 s each | <= 600 s | PASS |
| `Su2PlaqCert` Mathlib-free | no Mathlib import; compiles standalone | grep: no `import` outside `Su2PlaqCert.*`; all 10 files pass `lake env lean`; `import Su2PlaqCert` + `#check Real` -> "Unknown identifier `Real`" | – | PASS |
| exe stub | `REJECT unimplemented`, rc 1 | exactly that, rc 1 | – | PASS |
| `print_axioms` classification (scratch theorems) | see below | see below | – | PASS |
| `no_sorry` (16 edge cases) | 16 correct | 15 correct, 1 missed (N2) | – | PASS for locked usage, N2 note |
| GENERIC_THEOREMS == locked list | equal | 26 names, identical incl. order | exact | PASS |
| COUNT_THEOREMS == locked list (`test_lean_structure.py`) | equal | 8 names, identical incl. order | exact | PASS |

### print_axioms classification (scratch file, `Lean 4.35.0`)
| theorem | axioms | `<= STANDARD` | native (`is_native_axiom`) |
|---|---|---|---|
| `rfl` | none | yes | no |
| `propext h` | propext | yes | no |
| `Classical.em` | Classical.choice, Quot.sound, propext | yes | no |
| `by native_decide` | propext, `scratch_native._native.native_decide.ax_1_1` | no | yes -> allowed only with `allow_native` |
| `by sorry` | sorryAx | no | no -> rejected in both modes |
| mixed propext + native_decide | propext, `…native_decide.ax_1_1` | no | yes |

### Pending (expected, not failures at this step)
`pytest -m "not slow" tests/acceptance/m2`: 5 passed, 35 failed, all `PENDING: NotImplementedError` / unknown theorem names (Lean theorems of steps 2.L2–2.L7; `export_raw_circuit`, `certify_circuit_kind`, `structure_facts`, `symmetry_candidates`, `general_circuit`, …) or step-2.1 compress tests (not judged). The Lean ones: `test_lean_generic_theorems_standard_axioms` (names unknown), `test_lean_checker_semantics_match_sparse_sim`, `test_lean_certificate_small_accept_reject_na`, `test_polish_rules_are_lean_certified`, `test_program_lemma_file_checked`, `test_lean_counts_kernel_checked`, `test_structure_json_and_spec_section`, `test_symmetry_candidates_verified`.

## Notes (non-blocking, none block 2.L1)
- N1 (test hygiene, guess: builder's final assertion is too global): `tests/unit/test_lean_project_unit.py::test_print_axioms_real_and_unknown` ends with `assert not list(LEAN_DIR.glob("AxiomCheck*.lean"))`. It fails whenever any OTHER process is inside `print_axioms` at that moment: reproduced deterministically with a foreign print_axioms loop running (1 failed), and once as an unexplained failure in unit run 2 (leftover `AxiomCheck_2658514.lean` from a foreign pid). Product code is fine (per-pid files, 6-way concurrency OK, files removed). It will flake when Lean acceptance tests run under `-n auto` together with unit tests. Suggest asserting only that this process's own `AxiomCheck_<pid>.lean` is gone.
- N2 (`no_sorry`, guess: tokenizer has no char-literal state): a char literal `'"'` opens a "string" and hides a following `sorry` (false negative, 1 of 16 edge cases). Everything else correct: line/doc/nested-block comments, plain/escaped/multi-line strings, identifiers `sorryFree`, `my_sorry`, `sorryAx`, `sorry`/`admit` after `/- -/` or `"..."` on the same line. Harmless in practice because `print_axioms` also catches `sorryAx`; no `'"'` in the project.
- N3: every `Su2Plaq.*` module emits the Mathlib "consider adding `module`" warning (harmless).
- N4: the clean build is fast (22 s) only because the Mathlib oleans are reused from the copied `.lake/packages` (7.3 GB); on a fresh machine the Mathlib cache must be copied or fetched.

## Verdict
PASS for step 2.L1: 1/1 named acceptance test, collect 102 clean, lock OK, m0+m1 54/54, independent checks (1)–(5) as above. 0 new failures vs. last report (m2 later steps pending as expected).
