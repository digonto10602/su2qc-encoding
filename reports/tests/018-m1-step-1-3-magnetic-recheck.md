# Tester report 018 — M1 step 1.3 recheck (after builder fix, attempt 1)

- Date: 2026-11-04. Git commit: 99846e4 + uncommitted `src/su2plaq/{circuits/twelve,evaluate/sparse_sim,metrics/logical}.py` and unit tests. Prompt in force: `prompts/004` (over 002, 003). Mode: step.
- Previous report: `reports/tests/017-m1-step-1-3-magnetic.md` (FAIL: cache collision, T1[UB] engine).
- **VERDICT: PASS** for both failures of 017. One low-severity note (custom gates named like a basis gate, pre-existing).
- Raw numbers: `results/m1_step_1_3_recheck_*.json`; scripts `tests/independent/magnetic_1_3/` (new: `check_recheck_cache_lower.py`).

## Commands
```
pytest -n auto tests/unit                    # 156 passed (was 151), 57.7 s
pytest -n auto tests/acceptance/m0           # 34 passed incl. slow, 33.1 s
pytest -n auto tests/acceptance/m1 -rA       # 12 passed (T1[UB] new), 8 not green (all later steps), 19.4 s
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance   # LOCK OK ; PASS (acceptance-v4) ; 86 collected
check_recheck_cache_lower.py, check_sim_regression.py, check_ub_physics.py, check_ub_counts_synth.py, check_sparse_peak.py
```

## 1. Locked tests
| check | result |
|---|---|
| M1-B1 [0.4, 1.0, 2.0], B2, B3, B4, P2, C1, E1 [0.37, 0.91], T1[UE] | all PASS |
| **M1-T1[UB]** | **PASS** (was FAIL), on `sparse` |
| M0 incl. slow (E1/E2 on the changed simulator) | 34 passed |
| unit | 156 passed |
| lock | LOCK OK / acceptance-v4 PASS |
Still not green (later steps, none for 1.3): S1[1], S1[2], T1[step] (`build_step`), P1 (`paulo_circuit`, 1.6), O1 (3153 vs 6561, 1.8), R1 x3 (results files, 1.9).

## 2. Original repros
| repro | before (017) | now |
|---|---|---|
| two 2-qubit `to_gate` macros named "m" (cx vs cz), vs `Operator` | 0.707 | 0.0 (cold and warm cache) |
| four `ry/cx/rz` macros named "pg" with different angles | 0.737 | 1.1e-16 |
| `build_UB(0.3).to_gate()` then `build_UB(0.31).to_gate()` vs target(0.61) | err 2.0e-2, "ok" for 0.60 | ok, op-norm 3.6e-13, Gauss 3.2e-15; vs target 0.60: not ok (2.0e-2) |
| special cases of 017 (ctrl_state variants, same gate on other qubits, near-equal params, phases, bound parameter) | <= 9.7e-16 | <= 7.6e-16 |

## 3. Trying to break the new cache key / `_expand` (each case: simulator vs `Operator`, cold and warm cache; and `lower` unitary vs `Operator`)
| case | sim error | lower error (up to phase) |
|---|---|---|
| standard gate cached first, then custom gate of the same name ("crx") | 1.3e-16 | 2.8e-16 |
| three custom gates same name, different content, as `.control(1)` with ctrl_state 0 and 1 | 5.6e-17 | 5.8e-16 |
| 3 standard-library controlled gates, ctrl_state 0..3: RZ, RX (two states in one circuit), RY, H, Phase, X (=ccx), Swap(1 ctrl) | <= 1.7e-16 | <= 9.9e-16 |
| CRX ctrl_state 0 and 1 in one circuit; `cx(ctrl_state=0)`, `ch(ctrl_state=0)` | <= 1.4e-16 | <= 2.9e-16 |
| RZ.control(3) and ctrl_state=2 | 2.5e-16 | 2.3e-19 |
| `Gate` subclass with params and `_define` (same name, same params, different definition: `Rot2`, `Rot2b`) | 2.0e-16 | 7.8e-16 |
| subclass `MyRCCX(RCCXGate)` (unchanged) mixed with `RCCXGate` | 1.8e-16 | 3.3e-16 |
| `PauliEvolutionGate` two times (same operator) | 2.8e-16 | 3.0e-16 |
| `MCPhaseGate(0.5,3)`, `(0.9,3)`, `(0.5,2)` | 5.8e-16 | 2.1e-16 |
| same-name custom gates with different global phase | 6.2e-17 | 6.2e-17 |
| nested custom gates with equal names at both levels | 0.0 | 4.4e-16 |
| controlled `UnitaryGate`, two different matrices | 2.3e-16 | 1.7e-15 |
| `subclass of RZGate` overriding `_define` but keeping name "rz" | 5.6e-17 (treated as rz, matches `Operator`) | 0 |
| custom gates `.control(2)`, `H.control(3)`, native mcx | rejected by the mcx policy (ValueError), as designed | same |

Notes (not failures of the fix):
- **Custom gate whose name is a basis-gate name** (`Gate("cx")` defined as cz, same for x, ccx, t, cz, swap, s; "rz" gives IndexError, "h" gives a CircuitError): the simulator trusts the name, error 0.35 to 0.71. This is the same rule as before the change (HEAD tested `name in SIM_BASIS` too) and the same as Qiskit's own `transpile`, so it is not a regression; a builder or proposer never has a reason to do this. In `lower` such a gate is kept as is (unitary right, but its counts are those of the named gate). Low severity; mention in METHODS if desired.
- `MyCRX(CRXGate)` that changes `_define` to `cry` and keeps name "crx": simulator and `lower` follow the definition (error 0.43 vs `Operator`, which uses the class matrix `__array__`). Perverse and ambiguous; not a defect.

## 4. Simulator regression (re-run, same 36 circuits, seeds 3000..3035)
| check | got | tol | result |
|---|---|---|---|
| vs dense `Operator` | 2.2e-15 | 1e-12 | PASS |
| vs Aer statevector | 2.4e-15 | 1e-12 | PASS |
| program order vs DAG order | 7.3e-16 | 1e-12 | PASS |
| norm deviation | 1.0e-14 | 1e-12 | PASS |
| forced pruning, 64 896 cases | 0 violations, worst err - bound = +8.7e-16, max ratio 1.0000 | 1e-13 | PASS |
| mcx >= 3 rejected (19 variants incl. wrapped 3 deep); measure/reset/delay/if/for rejected | all ValueError | - | PASS |
| exact multi-controlled gates still accepted | <= 1.4e-15 | 1e-12 | PASS |
| cap: program order overflows, DAG fallback gives dense-exact result; wide circuit raises `SimCapExceeded` | as designed | - | PASS |

## 5. `lower` (program order) vs whole-circuit transpile
| check | got | result |
|---|---|---|
| 30 random circuits (seeds 7000..7029, 4 to 8 qubits, 30 to 70 gates, 28 foreign gate types, custom gates, no `unitary`): full `count_ops` equal to `transpile(basis_gates=LOGICAL_BASIS, level 0, seed 20261104)` | 30 / 30 equal (cx, t+tdg, rz, h, ... all) | PASS |
| lowered unitary vs `Operator(qc)` with the exact global phase | max 1.1e-14 | PASS |
| `build_UB(0.61)` (also with outer): counts | cx 294, h 178, t 160, tdg 152, x 50, s 8, sdg 8, rz 6, z 4; equal to whole-circuit transpile; depth 292 = 292 | PASS |
| `paulo_logical(1)`: counts | cx 294, h 190, t 152, tdg 144, sdg 56, rz 56, x 50, s 8, z 4; equal; depth 391 = 391 (P2: t_fixed 296, n_rot 14) | PASS |
| lowered `build_UB(0.61)` vs original on the 625 inner inputs (sparse sim, exact phase) | 6.0e-15 | PASS |
| `ct_compile(paulo_logical(1), 1e-6)` | cx 294, T 1162, depth 2549, gate counts identical to Paulo's metadata | PASS |

## 6. U_B physics (unchanged results; independent 433-state assembly, re-run)
beta in {0.4, 0.61, 1, 2}: block error 1.7e-14, leak 5.9e-15 to 6.9e-15, unitarity 3.4e-14, Gauss <= 9.6e-16, outer bits read 0, `evaluate` ok (tol 1e-10). Wrong targets (beta -> -beta = dagger = conjugate: 1.4 to 1.9; 1.01 beta: 8e-3 to 4e-2; 1.0001 beta: 8e-5 to 4e-4; identity: 0.8 to 1.8) all rejected. Composition `UB(0.3)` then `UB(0.31)` vs target(0.61): 3.0e-14; `UB(0.3)` twice vs 0.61: 2.0e-2 (fails as it must). `paulo_logical(1)` vs inner target: 1.2e-14, vs `build_UB(1)`: 9.3e-16. Counts of `build_UB(0.61)`: cx 294, n_rot 6 (all on `d[11]`), t_fixed 312, depth 292, 34 qubits, 22 ancillas; outer register touched by 0 gates; T(eps) table unchanged (560 / 696 / 820 / 936 at 1e-4 / 1e-6 / 1e-8 / 1e-10; Qiskit 536 / 670 / 780 / 912, within 2.6 to 4.9 %).

## 7. M1-T1[UB]: synthesis on the sparse engine
`synthesize(build_UB(0.61), eps)`, `evaluate(..., **synth_tolerances(6, eps))`, inner-span method, 625 inputs, engine `sparse`, certified:
| eps | op-norm error | tolerance $6\varepsilon+10^{-9}$ | block / leak amplitude | Gauss (tol same) | dropped bound | wall | T in circuit |
|---|---|---|---|---|---|---|---|
| 1e-4 | 1.923e-4 | 6.0e-4 | 1.518e-4 / 4.05e-5 | 1.6e-15 | 1.8e-13 | 3.3 s (auto), 8.0 s (first, cold) | 560 = 248 + 312 |
| 1e-6 | 1.854e-6 | 6.001e-6 | 1.315e-6 / 5.39e-7 | 1.9e-15 | 2.0e-13 | 3.6 s | 696 = 384 + 312 |
Peak stored amplitudes per input (5 inputs): 28.8 in both orders (was $2^{21}$ = 2 097 152). Previously forced-sparse was unsimulable and `aer_mps` took 52 s with Gauss 1.3e-10; the same synthesised circuit now gives Gauss 1.6e-15 to 1.9e-15, as it should for a word that is exactly unitary. (The builder reports 8.4 s and 1.85e-6 for eps = 1e-6; my cold-cache run gives 3.6 s with the same error.)

## 8. Failures
None. New observation only: the by-name treatment of custom gates called like a basis gate (section 3 notes), pre-existing and Qiskit-conformant.
