# Tester report 008 — M0 step 0.7 recheck (after builder fix, attempt 1)

- Date: 2026-11-04
- Commit: 06ea6bc (step files uncommitted: `evaluate/sparse_sim.py`, `evaluate/aer_check.py`, `tests/unit/test_sparse_sim_unit.py`)
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` (§2.7, §3 row 0.7)
- Mode: step (re-verification)
- Previous report: `reports/tests/007-m0-step-0-7-sparse-sim.md` (FAIL on pruning accounting)
- Verdict: **PASS** for the failing check of report 007 (pruning is now certified) and for all standard checks. Two items need a decision by the coordinator (not failures of the step's contract): (a) a residual hole in the `mcx` rejection (nested in a custom gate), (b) the Aer MPS engine is accurate to only $10^{-11}$ to $2\cdot10^{-10}$ (confirms and extends the builder's number), which affects METHODS and the tolerance the evaluator may promise for engine `aer_mps`.

## 1. Commands
```
conda activate coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected "aer_mps_block"  (no affected nodes yet: evaluator is a stub)
pytest tests/unit -q ; pytest -m "not slow" tests/acceptance/m0 -q -rA
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
# own scripts (scratch/, gitignored): chk6.py (A,B), chk7.py (C), chk8.py (mcx), chk9.py, chk10.py, chk11.py (Aer), chk12.py (lexsort path), chk5r.py / chk5br.py (timing)
```

## 2. Standard checks
| check | expected | got | tol | result |
|---|---|---|---|---|
| unit `tests/unit` | all pass | 85 passed (8 new) | – | PASS |
| M0-E1, M0-E2 | pass | pass | 1e-12 | PASS |
| earlier M0 acceptance | pass | 23 passed (incl. E1/E2) | – | PASS |
| PENDING | NotImplementedError only | 9 (E3, E4, E5, M1, M2 x3, M3, R1), all `NotImplementedError` | – | PENDING |
| lock | OK | LOCK OK; "matches acceptance-v2"; 84 collected | – | PASS |

## 3. Pruning: certified bound (failing check of report 007)
Claim under test: $\|\psi_{\rm sim}-\psi_{\rm exact}\|_2\le$ `Batch.dropped_l2[col]` for every column. Reference = same simulator with `PRUNE_REL = 0` (validated vs `Operator` to < 1e-12 on 30 circuits). Raw: `results/m0_step07_recheck_AB.json`, `results/m0_step07_recheck_C.json`.

Why it must hold: the dropped vector at gate $g$ has norm $d_g$; all later gates are unitary, so the total error is $\le\sum_g d_g$ (triangle inequality). I tried to defeat it and could not (below).

**A. Generic product rotations** ($n$ qubits through $h$-$rz(\theta)$-$h$, $n=12,16,20$, 7 angles each, 21 cases): err $\le$ bound in all 21. Largest: $n=20,\theta=0.05$: err $1.56\cdot10^{-12}$, bound $3.69\cdot10^{-12}$. Ratio bound/err 1.2 to 3.2 (previous absolute rule lost the same $1.6\cdot10^{-12}$ silently).

**B. Ry scenario of report 007** ($2^{20}$ entries, $N$ gates $R_y(2\cdot10^{-11})$ on an empty qubit): with the relative threshold the branch amplitudes ($9.8\cdot10^{-15}$) are now kept; err $=0$, bound $=0$ for $N=10,20,40$ (true rotation error $1\cdot10^{-10}$ to $4\cdot10^{-10}$ is simulated exactly, i.e. the scenario no longer biases). Push the angle down so that the relative rule drops it:

| m | N | θ (rad) | err | bound | note |
|---|---|---|---|---|---|
| 20 | 40 | 1e-14 | 2.000000000009e-13 | 1.999999999997e-13 | = true $\sin(N\theta/2)$ |
| 20 | 200 | 1e-14 | 1.0e-12 | 1.0e-12 | tight |
| 20 | 40 | 4e-15 | 8.0e-14 | 8.0e-14 | tight |
| 12 | 50 | 4e-15 | 1.0e-13 | 9.99999999999e-14 | tight |
| 10 | 50 | 1e-14 | 2.5e-13 | 2.5e-13 | tight |

The bound is attained to $10^{-12}$ relative, never exceeded beyond float rounding (differences $\sim10^{-23}$ absolute here).

**C. Forced pruning** (threshold raised to $10^{-1},10^{-2},10^{-3},10^{-5},10^{-8},10^{-14}$): 80 seeded random circuits (5 to 8 qubits, 30 to 89 gates, `h, sx, u, ry, rz, cx, ccx, cp, unitary, swap, t`, half with small angles $10^{-6}$ to $10^{-1}$ to create wide amplitude dynamic range), all $2^n$ input columns: 64 896 (circuit, threshold, column) cases. Violations (err > bound + 1e-13): **0**. Worst err − bound: $+6.5\cdot10^{-16}$ (float rounding, not a violation of the claim "up to rounding"). Max err/bound (bound > 1e-12): 1.000 (tight). At threshold $10^{-1}$ the errors reach 0.65 and the bound 4.0, still valid.

**D. Attempts to defeat the relative threshold**: (i) one dominant entry plus many tiny ones with several different column maxima in one batch (3 columns, thr up to $10^{-3}$): err 0.00173 < bound 0.006, etc. (ii) the `lexsort` path (58 qubits + 625 columns, $58+10>62$): thr $10^{-3}$: err $2.5\cdot10^{-3}$ < bound $7.5\cdot10^{-3}$; thr $10^{-1}$: $0.093<0.25$; thr $10^{-14}$: bound 0, err $5\cdot10^{-17}$; Frobenius error $5.5\cdot10^{-2}$ < `dropped_total` 0.159. (iii) coherent accumulation of many sub-threshold gates (B): bound adds linearly, equals error. (iv) exact cancellation $C\,C^\dagger$ (10 to 12 qubits, 100 to 1000 gates): stored entries per column exactly 1, `dropped_max` $2\cdot10^{-15}$ to $6\cdot10^{-15}$ (noise accounted, far below $10^{-10}$). No case with error > bound found. The theory (triangle inequality) leaves only float rounding as a gap: accumulated column-norm deviation $\le1.5\cdot10^{-14}$ over 4100 gates, negligible.

**Consequence**: the silent drop is now certified; `dropped_max` / `dropped_total` stay 0 in all four timing circuits below, so there is no cost on realistic circuits. The evaluator (step 0.8+) must actually add `dropped_total` (Frobenius, bounds op-norm) to its error budget; the evaluator is still a stub so this cannot be tested yet.

## 4. `mcx` rejection and exact multi-controlled gates
Rejected with `ValueError` (message names the gate): `qc.mcx` 3, 4, 5 controls; `C3XGate`; `C4XGate`; `MCXGate(3)`, `MCXGate(4)`; `mode="recursion"` (4 ctrl); `mode="v-chain"`; `MCXVChain(3)`; `MCXGrayCode(3)`; mcx with 3 controls in a circuit that also holds a `unitary`.

**Residual hole (not rejected, wrong result)**: `mcx([0,1,2],3)` wrapped in a custom gate (`sub.to_gate()` appended on 5 or 6 qubits): not rejected, and the result is wrong, error vs `Operator` $=0.707$ (same Qiskit idle-qubit-as-clean-ancilla mechanism as report 007). The check inspects only top-level instruction names. Guess: should also walk `op.definition` recursively (or check the operator of transpiled output against the original on a small instance). Matters if circuit builders use `to_gate()` macros around `mcx`; the plan says no native `mcx` is used, so this is a latent trap, not a present failure.

Exact multi-controlled gates still pass vs `Operator` (6 qubits, $h$ on qubits 0 and 4): ccx 0, mcx 2 ctrl 0, mcx 1 ctrl 0, mcp(3 ctrl) $6.8\cdot10^{-16}$, mcp(4 ctrl) $1.4\cdot10^{-15}$, c3sx $6.1\cdot10^{-16}$, rccx $5.9\cdot10^{-17}$, rc3x $1.4\cdot10^{-16}$, ccz 0, h·mcx2·h 0, cswap 0, controlled-$R_z$ (3 ctrl) $4.5\cdot10^{-16}$, controlled-$R_y$ (3 ctrl) $5.6\cdot10^{-16}$, explicit ccx with ancilla 0. All PASS.

## 5. `aer_check` and the Aer MPS accuracy
Test: 10 seeded random 8-qubit circuits (seeds 500..509, 60 gates incl. random 2-qubit `unitary`, nonzero global phase), 12 inputs, 20 codes on bits 0..5 (bits 6, 7 outside the mask), vs sparse+`encoded_block` and vs my own independent Aer statevector code. Raw `results/m0_step07_recheck_aer.json`.

| comparison | max over seeds | tol | result |
|---|---|---|---|
| `aer_statevector_block` M vs my Aer statevector | 0.0 (identical) | 1e-12 | PASS |
| `aer_statevector_block` M vs sparse | 1.8e-16 | 1e-12 | PASS |
| leak: sparse (direct) vs my Aer sv | 2.2e-15 | 1e-12 | PASS |
| `aer_mps_block` M vs statevector | **5.8e-11** (range 2.6e-11 to 5.8e-11) | 1e-12 | **exceeds** |
| `aer_mps_block` leak ($1-\sum|M|^2$) vs direct | **1.6e-11** (range 6e-12 to 1.6e-11) | 1e-12 | **exceeds** |

**The builder's number is confirmed**: Aer MPS with `matrix_product_state_truncation_threshold=0` differs from the exact statevector by $2.6\cdot10^{-11}$ to $5.8\cdot10^{-11}$ on random 8-qubit circuits (bond dimension 16). Additional numbers (`scratch/chk10.py`, 8 qubits, 60 gates):

| gate family | max amplitude error MPS vs sv |
|---|---|
| $h$ + CX on adjacent qubits | $4.8\cdot10^{-16}$ |
| $h$, $t$, CX on far qubits | $1.3\cdot10^{-13}$ |
| random 2-qubit `unitary`, adjacent | $1.8\cdot10^{-11}$ |
| random 2-qubit `unitary`, far | $3.4\cdot10^{-11}$ |
| $h$ + `ccx` far | $6.9\cdot10^{-11}$ |

The error is identical for threshold $0$, default, and $10^{-20}$, so it is not the truncation threshold but Aer's internal SVD/swap precision when the bond dimension is large; guess: Aer's SVD cutoff / non-adjacent swap handling. On an almost-classical circuit (18 qubits, 578 gates, 14 blocks structure, 10 inputs, 224 codes, bond 8, 2.5 s) MPS vs sparse is $2.05\cdot10^{-10}$ (sv vs sparse $1.4\cdot10^{-15}$): this is above the evaluator's $10^{-10}$ op-norm tolerance. So for METHODS: engine `aer_mps` is accurate to $\sim10^{-11}$ to $2\cdot10^{-10}$ per amplitude depending on entanglement (hence not a certifier at $10^{-10}$; tolerance for that engine should be stated as $\gtrsim10^{-9}$, and leak, being $1-\sum|M|^2$, has noise $\sim10^{-11}$ so the $10^{-12}$ leak bound cannot be enforced with it). Paulo's circuit in report/plan (2.9e-6 vs target) is dominated by his synthesis error, so it is unaffected. `aer_mps_block` docstring already says ~1e-10; METHODS (line ~62 "exact up to float64") should be corrected.

## 6. Timing regression (chk5r / chk5br, same circuits as report 007)
| circuit | gates | wall report 007 (s) | wall now (s) | dropped_max / total | RSS now (MB) |
|---|---|---|---|---|---|
| 14 blocks x 3 h, data qubits 0-7 | 4109 | 2.99 | 2.73 | 0 / 0 | 151 |
| pool 5 | 4109 | 0.47 | 0.47 | 0 / 0 | 152 |
| 40 blocks x 1 h | 3825 | 2.11 | 1.98 | 0 / 0 | 152 |
| HEAVY (2.56e6 stored) | 4131 | 22.8 | 19.8 | 0 / 0 | 844 |
No slowdown (single core machine, `nproc` = 1).

## 7. Summary
| check | expected | got | tol | result |
|---|---|---|---|---|
| unit / E1 / E2 / earlier M0 / lock | pass | 85 / pass / pass / 23 / OK | – | PASS |
| error ≤ certified bound (generic, Ry scenario, 64 896 forced-prune cases, lexsort path) | 0 violations | 0 (worst excess 6.5e-16, rounding) | rounding | PASS |
| mcx ≥ 3 controls rejected (top level, all listed variants) | reject | rejected | – | PASS |
| mcx ≥ 3 inside a custom gate | reject | not rejected, error 0.707 | – | NOTE (hole) |
| exact multi-controlled gates vs Operator | ≤ 1e-12 | ≤ 1.4e-15 | 1e-12 | PASS |
| `aer_statevector_block` | ≤ 1e-12 | 1.8e-16 | 1e-12 | PASS |
| `aer_mps_block` accuracy | (no plan tolerance) | 2.6e-11 to 5.8e-11 (random), 2.0e-10 (almost classical) | – | confirmed builder; NOTE |

Counts: passed all standard + pruning/mcx/aer-sv checks; failed 0; pending 9; new failures vs report 007: 0 (the one failure of 007 is cleared).

## 8. Recommendations (for the coordinator)
1. Evaluator (step 0.8+) must add `Batch.dropped_total` to the op-norm budget and reject when `dropped_max` > ~1e-12; add a test for it there.
2. Make the `mcx` rejection recursive into `definition` (or compare against `Operator` on a small test), or forbid composite gates containing mcx in circuit builders.
3. METHODS: replace "exact up to float64" for `aer_mps` by "$10^{-11}$ to $2\cdot10^{-10}$ per amplitude, leak noise $\sim10^{-11}$"; do not use it for the $10^{-10}$/$10^{-12}$ verdicts without a looser engine-specific tolerance.

Files: `results/m0_step07_recheck_AB.json`, `m0_step07_recheck_C.json`, `m0_step07_recheck_aer.json`, `m0_step07_recheck_timing.json`, `m0_step07_recheck_timingb.json`. No source or acceptance files modified, no tests added.
