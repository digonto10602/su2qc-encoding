# Tester report 106 — M3 milestone gate (mode full), track S (spin network)

- Date: 2026-11-06
- Git commit under test: `de68cc8` (branch `m3-spin-network`; working tree has only the planner's `docs/METHODS-spinnet.md` edit, ignored as instructed)
- Prompt in force: `prompts/100-spinnet-m3-plan.md` (acceptance-v7)
- Related reports: `reports/tests/100`–`105`
- Mode: full (milestone gate M3). Env `su2qc-coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `taskset -c 0-9`. Peak RSS of every job < 330 MB.

## Verdict: PASS (with one expected PENDING: M3-L3)

Counts: acceptance m0+m1+m3 79 passed, 1 failed (= M3-L3, pending laptop checker); unit 286/286; lock and acceptance-check PASS; Lean build green, no `sorry`. m2 (laptop milestone): 7 passed, 39 non-pass, all classified as laptop work not yet merged; nothing that passed at the branch point `a2ec571` fails now. New failures versus earlier reports: 0.

## Commands run
```
pytest --collect-only -q tests/acceptance                                   -> 126 tests collected, clean
taskset -c 0-9 pytest -n 10 tests/acceptance/m0 tests/acceptance/m1 tests/acceptance/m3 -q -rfEs   -> 79 passed, 1 failed, 92.33 s
taskset -c 0-9 pytest -n 10 tests/acceptance/m2 -q -rfEs                    -> 7 passed, 39 failed, 5.37 s
   (baseline: git worktree at a2ec571 in the scratchpad, same command)     -> 4 passed, 42 failed, 24.97 s
taskset -c 0-9 pytest -n 10 tests/unit -q                                   -> 286 passed, 33.2 s
python tools/check_lock.py                                                  -> LOCK OK
~/.claude/bin/acceptance-check                                              -> PASS: tests/acceptance matches acceptance-v7
cd lean && taskset -c 0-9 lake build                                        -> Build completed successfully (9091 jobs), 2.6 s (all replayed; Structure/Counts.lean NOT rebuilt)
lake env lean <scratch>/ax.lean   (#print axioms for all 17 theorems in Su2Plaq/SpinNet/{Counts,Circuit}.lean)
PYTHONPATH=src python scripts/m3_results.py --out <scratch>/rerun           -> 11.24 s wall, 295 MB
python results/spinnet/tester/m3_step_3_7_repro.py <scratch>/rerun          (diff rerun vs committed)
PYTHONPATH=src python results/spinnet/tester/m3_step_3_7_verify.py          -> 133 checks, 0 failed, 21.4 s, 312 MB
```

## 1. Gate checks
| check | expected | got | tolerance | result |
|---|---|---|---|---|
| collection of `tests/acceptance` | clean | 126 collected, no errors | - | PASS |
| acceptance m0 + m1 (incl. slow) | 56 pass | 56 pass | - | PASS |
| acceptance m3 | 23 pass + L3 pending | 23 pass; only failure `test_M3_L3_native_certificate_general_step` | - | PASS |
| M3-L3 message | "laptop checker not delivered" | `PENDING: Su2PlaqCert checker not yet delivered by the laptop (prompts/006 step 2.L4)` | - | PASS (pending as agreed) |
| `L1`, `L2` Lean counts / circuit structure | pass | pass | - | PASS |
| unit | all pass | 286/286 (short hash `de68cc8` has no "c1": laptop flake not triggered) | - | PASS |
| `check_lock.py` | pass | LOCK OK | - | PASS |
| `acceptance-check` | pass | matches acceptance-v7 | - | PASS |
| `lake build` | green | 9091 jobs, success | - | PASS |
| `sorry` / `admit` in `lean/` (excluding `.lake`) | none | none | - | PASS |
| axioms of the 17 SpinNet theorems | $\subseteq\{\text{propext}\}$ | 14 depend on `[propext]` only, 3 on no axiom | - | PASS |
| `results/spinnet/{UE,UB,step}.json` provenance | commit `7a716fc`, dirty False | `7a716fc`, `git_dirty False` (all three) | - | PASS |
| `src/` changed since 7a716fc | no | `git diff 7a716fc HEAD -- src` empty | - | PASS |

## 2. m2 (laptop's milestone) — classification of the 39 non-passes at `de68cc8`
Diff of the failing sets: baseline `a2ec571` fails 42, HEAD fails 39; HEAD's failing set is a strict subset of the baseline's. The 3 tests that fail at the baseline worktree but pass at HEAD are `test_lean_generic_theorems_standard_axioms`, `test_lean_project_present_and_builds_checker`, `test_lean_counts_kernel_checked`. They fail in the fresh worktree because it has no built `lean/.lake` (the cache lives in the main clone), not because of any code difference; they are not track-S regressions. All 4 tests that pass at the baseline pass at HEAD. Track S modified no existing source: `git diff --name-status a2ec571 HEAD` shows only additions plus `lean/Su2Plaq.lean` (new imports), `notes/STATUS.md`, `tests/acceptance/LOCK.json`.

Messages of the 39 (all `PENDING` markers, i.e. `NotImplementedError` raised by laptop-owned stubs): `general_circuit is not built yet` ×17, `gridsynth_T` ×4, `Archive.load` ×4, `import_seed` ×3, `general_program_path` ×2, and one each of `qiskit_l3`, `lean.structure.symmetry_candidates`, `lean.structure.structure_facts`, `lean.structure.export_structure_certificate`, `lean.certify.export_raw_circuit`, `lean.certify.certify_circuit_kind`, `evaluate_circuit`, `code_hash` = 38. The 39th, `test_lean_formal.py::test_lean_theorem_file_general`, is `assert f.exists()` on the missing `lean/certs/twelve-general-step.lean` (laptop certificate file, not yet merged). Classification: 39 PENDING (laptop work not merged), 0 real failures caused by track-S code.

## 3. Reproducibility and independent recomputation (regression versus 100–105)
- Rerun of `scripts/m3_results.py` into a scratch dir: all numeric JSON fields identical to the committed files; the only diffs are file path strings, `git_commit` (`7a716fc` vs `de68cc8`) and `git_dirty` (True in the rerun only because of the planner's docs edit). All `.qasm3` and `.qpy` files byte-identical (qpy ops equal).
- 133 independent recomputation checks (`m3_step_3_7_verify.py`): 0 failed.

Numbers re-read from the committed JSON and compared with reports 100–105:

| quantity | reports 100–105 | now | changed |
|---|---|---|---|
| $U_B$ (GENERAL7, $\beta=0.61$): CX / rot / T_fixed / ancilla / depth | 54 / 4 / 56 / 7 / 67 | 54 / 4 / 56 / 7 / 67 | no |
| $U_E$: CX / rot / depth | 0 / 4 / 1 | 0 / 4 / 1 | no |
| step order 1: CX / rot ; order 2 rot | 54 / 8 ; 12 | 54 / 8 ; 12 | no |
| pairs9 skeleton: CX / rot / T_fixed | 34 / 9 / 24 | 34 / 9 / 24 | no |
| flags4 skeleton: CX / rot / T_fixed | 44 / 4 / 48 | 44 / 4 / 48 | no |
| $T_{\rm total}(10^{-6})$ pairs9 / flags4 | 576 / 298 | 576 / 298 | no |
| Paulo 15-qubit file CX / rot / T_fixed | 68 / 4 / 64 | 68 / 4 / 64 | no |
| Paulo file op-norm error | 9.7e-15 | 9.73e-15 | no |
| $U_B$ op-norm error (json) | 1.02e-14 (report 104, commit `0d75ba0`) | 1.08e-14 | yes, round-off level (below $10^{-13}$); regenerated after `coupling_table` snapping to half-integers (report 105) |
| step op-norm error (json) | 1.16e-14 | 1.15e-14 | yes, same reason |
| $U_E$ op-norm error | 4.44e-16 | 4.44e-16 | no |
| Gauss residual | 5.4e-16 | 5.41e-16 | no |
| $T_{\rm total}$ table for GENERAL7 $U_B$ ($\varepsilon=10^{-4},10^{-6},10^{-8},10^{-10}$) | - | 230 / 310 / 396 / 468 | (for the record) |

## 4. Wall times
| suite | wall | desktop baseline |
|---|---|---|
| acceptance m0+m1+m3 incl. slow (80 tests) | 92.3 s | m0+m1 56 passed 62.8 s (m3's 24 tests add ~30 s; slowest: `M1_O1` 78 s, `M1_P1` 58 s are the long poles) |
| acceptance m2 (at HEAD) | 5.4 s | - |
| unit | 33.2 s (286 tests) | 216 passed 30.9 s |
| `lake build` (cached) | 2.6 s | - |
| `m3_results.py` | 11.2 s | committed run 8.6 s |

## 5. Notes
- The only red test of the gate is M3-L3 (agreed pending). It must stay a hard FAIL at the final milestone gate until the laptop's `Su2PlaqCert` checker is merged.
- The spectrum 16/96/16/177/16/96/16 is not kernel-checked (pair-class counts only), as noted in STATUS/report 105.
- The verify script overwrote the tracked file `results/spinnet/tester/m3_step_3_7.json` (commit `de68cc8`, provenance `7a716fc`); new raw files `m3_gate*.{json,txt}` are in `results/spinnet/tester/`. Nothing in `src/`, `tests/acceptance/` or tolerances was touched.
- The scratch worktree used for the `a2ec571` comparison was removed.
