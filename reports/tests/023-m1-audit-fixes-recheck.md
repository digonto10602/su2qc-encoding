# 023 — M1 audit fixes, recheck after builder repair of N6 (attempt 1)

- Date: 2026-11-05
- Git: HEAD `7a54eaa` plus uncommitted working tree (`sparse_sim.py` now with class-identity `is_standard_gate`, recursive `_reject_wide_mcx`)
- Plan in force: `prompts/005-relative-prune-cap.md` (on `prompts/002`; addenda 003, 004); lock `acceptance-v5`
- Mode: step (recheck)
- Related: `reports/tests/022-m1-audit-fixes.md` (the two findings F1, F2 and the note N6-b), `reports/audits/003`
- Raw numbers: `results/m1_audit_fixes_recheck*.json`; scripts: `tests/independent/audit_fixes/` (new: `ctrl_and_mcx_cases.py`, `contradictory_spoof.py`)

## Verdict: PASS

F1 (name-spoofed non-singleton subclass), F2 (open-control CX rejected) and the N6-b note (hidden `mcx` bypass) are all fixed. No regression for genuine standard gates.

## Commands

```
pytest -n auto tests/unit ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
pytest -n auto tests/acceptance/m0 tests/acceptance/m1          # includes slow
PYTHONPATH=src python tests/independent/audit_fixes/{adversarial_n6,subclass_spoof,spoof_nonsingleton,ctrl_and_mcx_cases,contradictory_spoof}.py <out.json>
PYTHONPATH=src python tests/independent/magnetic_1_3/check_recheck_cache_lower.py results/m1_audit_fixes_recheck2_lower.json
PYTHONPATH=src python tests/independent/audit_fixes/sim_regression_tolerant.py results/m1_audit_fixes_recheck2_sim_regression.json
PYTHONPATH=src python scripts/m1_results.py --out <scratch>/m1out2
```

## Suites

| check | expected | got | result |
|---|---|---|---|
| acceptance m0 + m1 incl. slow | 56 pass | 56 passed, 204 s | PASS |
| unit | all pass | 176 passed (173 in 022; +3 new), 60 s | PASS |
| `tools/check_lock.py` / `acceptance-check` | OK / PASS | `LOCK OK` / `PASS: tests/acceptance matches acceptance-v5` | PASS |
| m2 | pending | not run in this round (unchanged since 022: 31 `NotImplementedError`) | PENDING |

## N6 adversarial recheck

| script | what | result |
|---|---|---|
| `spoof_nonsingleton.py` (F1) | user classes named `RZGate`, `PhaseGate`, `CPhaseGate`, `UGate`, `RXGate`, `CRXGate` (other module), define-only and with `to_matrix`; `SXGate` | 14 of 14: `is_standard_gate` False, simulated and lowered by content, error vs intended content <= 1e-10 (before: 11 of 12 wrong, error 0.34) |
| `subclass_spoof.py` | singleton-class spoofs, module forged to `qiskit.*`, `MyRZ`, `MyT`, `MyH`, define-only | 12 of 12 by content (was 10 of 12 right and 2 wrong) |
| `ctrl_and_mcx_cases.py` (F2, N6-b) | 22 genuine open-control / annotated gates (`cx/ccx/ch/cz/ccz/crx/cry/crz/cp/cswap` with `ctrl_state`, `X.control(1, ctrl_state=0)`, `X/Z/H.control(1, annotated=True)`, `.control(2/3, ctrl_state)`) | all simulated and lowered; max error sim 2.5e-16, lower 3.3e-16 (before: `cx_o0` and annotated `cx` rejected). `RZ.control(2, annotated=True)` is rejected (`AnnotatedOperation`, no definition; allowed) |
| same | `mcx` with 3 or 4 controls inside a custom gate named `my_wrap, cx, h, t, x, ccx, barrier, rz, unitary, ccz, swap`, and nested `cx > h` | 23 of 23 rejected by both sim and lower (before: accepted under standard names). `mcx2` still accepted, error 0.0 |
| `adversarial_n6.py` | 201 cases | 8 flagged by the script, 0 defects (see below) |

### The 8 remaining flags of `adversarial_n6.py`: all are test-reference artefacts, no defect

- 7 flags (`std_subclass_*`, `forged_module_TGate`): the script's reference is `Operator(qc)`. For a subclass of a Qiskit gate class, Qiskit's `Operator` (and `transpile` when the name is in the basis) uses the Rust-standard fast path / `to_matrix` and ignores the override of `_define`. In these spoofs `to_matrix` and `definition` agree with each other (intended content), so the evaluator (which expands from the definition) is right and `Operator` is wrong. The clean version of the same cases, with the intended content hand-built, is `subclass_spoof.py` and `spoof_nonsingleton.py`: 26 of 26 correct. For comparison the older `check_recheck_cache_lower.py` hostile entries `subclass_crx_changed_definition` (error 0.43) and `subclass_rz_changed_definition_same_name` (0.34) show the same artefact (they compare to `Operator`).
- 1 flag (`annotated_cx`): sim is `ok`; `lower=ref-fail` is my reference helper failing on `AnnotatedOperation`, not `lower`. Checked directly in `ctrl_and_mcx_cases.py`: `X.control(1, annotated=True)` sim 2.8e-17, lower 1.8e-33.

### Definition vs `to_matrix` for contradictory objects (`contradictory_spoof.py`)

Gates whose `to_matrix()` contradicts their `definition` (4 cases: singleton `TGate`-named and `MyT` with definition X / matrix T; `RZGate`-named and `MyRZ` with definition RX / matrix RZ):

| quantity | follows definition | follows `to_matrix` |
|---|---|---|
| our simulator | yes (error vs definition circuit 2.8e-17 / 6.2e-17) | no (0.71 / 0.24) |
| our `lower` (counts and unitary) | yes (1.8e-33 / 7.9e-17) | no |
| Qiskit `Operator(qc)` | no | yes |
| Qiskit `transpile` to our basis (name in basis) | no | yes |

My view on the semantics: the evaluator must simulate and count the same circuit, and it does (sim and `lower` agree with each other in all 4 cases, both derived from the definition). The definition is also what any export path executes (QPY and QASM3 write the definition body of a custom gate), and it is what Qiskit's transpiler uses for every name that is not a native basis gate; so I agree with the coordinator: definition semantics is right. A contradictory object is ill-formed. The only residual would be an evaluator-side policy of rejecting gates whose `to_matrix` and `definition` disagree, which I do not consider necessary because the definition is unambiguous in our evaluator.

## Regression for genuine standard gates (HEAD source vs working tree)

| check | HEAD | now | result |
|---|---|---|---|
| simulator vs `Operator`, 36 random circuits (24 with foreign gates), max | 2.156e-15 | 2.156e-15 (every circuit within 1e-15 of HEAD) | PASS |
| simulator vs Aer statevector, 36 | 2.433e-15 | 2.433e-15 | PASS |
| program-order vs DAG-order | 7.31e-16 | 7.31e-16 | PASS |
| forced pruning bound, 64 896 cases | 0 violations | 0 violations, max err/bound 1.000006 | PASS |
| 24 hostile rejections | all `ValueError` | identical | PASS |
| accepted exact controls (ccx, mcx2, mcp4, rccx, rc3x, c3sx, ...) | <= 1.4e-15 | <= 1.4e-15 (mcx2 back to 0.0, as at HEAD) | PASS |
| hostile cases incl. `ctrl_state_variants` | 7.6e-16 | 7.6e-16 (was REJECTED in 022) | PASS |
| `lower` vs whole-circuit transpile, 30 circuits: counts equal | 30/30 | 30/30; cx/t/rz identical to the previous round; unitary error max 1.07e-14 | PASS |
| `lower(build_UB(0.61))` (with/without outer) | cx 294, h 178, t 160, tdg 152, x 50, s 8, sdg 8, rz 6, z 4; depth 292 | identical | PASS |
| `lower(paulo_logical(1))` | cx 294, t 152, tdg 144, rz 56, ...; depth 391 | identical | PASS |
| lowered `build_UB` vs `build_UB` on 625 inputs | 6.0e-15 | 6.0e-15 | PASS |
| `build_UB` via `to_gate()` vs $U_B(0.61)$ / $U_B(0.60)$ | ok / rejected | ok / rejected | PASS |

## Results files

`scripts/m1_results.py --out <scratch>/m1out2` (rc 0): `UE.json`, `UB.json`, `step.json` have the same 326 / 408 / 456 leaves as `results/twelve/*.json`; the only differing leaves are `seconds`, `timestamp` and `files` paths (11, 11, 15); 0 numerical differences; all 5 `.qpy` and 5 `.qasm3` files are byte-identical (sha256). The builder's claim that no M1 number changes is confirmed. Strict JSON parse passes (no `NaN` / `Infinity`). Provenance still reads `git_commit 7a54eaa`, `git_dirty true` (audit N1: regenerate on the clean commit before tagging).

## Failures

None.
