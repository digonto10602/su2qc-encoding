# Report 300 — M9 gate, full mode, part 1 (tester)

Date: 2026-11-06. Commit: `8e71c38` (branch `m9-fuzzy`, HEAD committed; untracked builder files `scripts/m9_results.py`, `results/fuzzy/`, `tests/unit/test_m9_results_script_unit.py` ignored). Plan in force: `prompts/300` + `prompts/301`. Acceptance lock: `acceptance-v10`. Mode: full, part 1 (R1, T1, `shared_table_file` deferred to part 2). Env: `~/venvs/coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`. The builder ran `scripts/m9_results.py` on ~10 cores concurrently, so wall times are somewhat inflated. Steps 2-3 used `-n 16` instead of `-n 24` because step 4 (`-n 8`) ran at the same time (24-core share).

## Commands and results

| # | command | expected | got | wall | verdict |
|---|---|---|---|---|---|
| 1 | `python tools/check_lock.py && ~/.claude/bin/acceptance-check` | lock OK | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v10` | 0.05 s | PASS |
| 2 | `pytest -n 16 tests/unit -q` | all pass | 453 passed, 0 failed | 109 s | PASS |
| 3 | `pytest -n 16 tests/acceptance/m0 m1 m2 -q` | all pass | 102 passed, 0 failed, 0 pending/skipped | 109 s | PASS |
| 4 | `pytest -n 8 tests/acceptance/m9 -q -k "not S1 and not R1 and not T1 and not shared_table_file"` | all pass | 13 passed, 0 failed (22:43 wall; includes C1) | 1363 s | PASS |
| 5 | `pytest -n 1 tests/acceptance/m9/test_fuzzy_circuits.py -q -k S1` | all pass | 5 passed (4 `S1_step_orders` + `S1_outer_row_and_gauss_on_outputs`), peak RSS 134.8 GB | 284 s | PASS |

No m2 failures, so the master-worktree comparison was not needed. Step-4 tests (13): D1, D2, C1 x3, O1 identities, K1 x4 (E: 0.37, 0.91; K2: 0.185, 0.455), B1 x3 (0.61, 0.23, 1.0). Of the 28 collected m9 tests, 5 (S1) + 13 (step 4) = 18 ran; the other 10 (T1 x4, R1 x5, `shared_table_file`) are part 2. Not pending: none raised `NotImplementedError`.

Notes: (i) running the suite rewrites provenance in tracked `compress/lean/structure.json` (`git_commit` 4fa765b -> 8e71c38, timing field); this is a test side effect, left uncommitted, not a physics change. (ii) `python3` outside the venv fails `tools/check_lock.py` with `TypeError: 'type' object is not subscriptable` (system python < 3.9); with the venv it passes. Environment issue only.

## Independent spot checks (scratch/tester/, raw data in results/tester_logs/)

Seed 20261106 for random states. Parameters $\alpha=0.37$, $\beta=0.61$, $\kappa_2 = r\alpha/2$.

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| (a) `build_UB(0.61)` through Aer statevector (second engine), all 256 row basis columns, ancillas $|0\rangle$ vs `targets.UB_row(0.61)`; touches only row qubits {2,3,6,7,10,11,14,15} + 7 ancillas | $\lVert M-U_B\rVert_2 = 0$ | $\lVert M-U_B\rVert_2 = 2.6\times10^{-14}$ (global phase $-6.7\times10^{-15}$, i.e. exact phase 1); 8 random states max err $1.1\times10^{-14}$; $\lVert M^\dagger M-1\rVert=2.3\times10^{-14}$; ancilla leakage 0.0 | 1e-10 | PASS |
| (b) `build_step` order 1, $r=1$, 4 random inner states, Qiskit `Statevector` on 23 qubits (16 + 7 ancillas) vs `targets.apply_step` | $\lVert\psi_{\rm circ}-\psi_{\rm ref}\rVert=0$ | max err 3.3e-15 (raw), 3.3e-15 (after phase fit), phase $\le 4.6\times10^{-16}$, leakage 0 | 1e-10 | PASS |
| (b) order 2, $r=1$ | same | max err 7.5e-15, leakage 0 | 1e-10 | PASS |
| (b) order 1, $r=0$ ($\kappa_2=0$) | same | max err 3.0e-15, leakage 0 | 1e-10 | PASS |
| (b) order 2, $r=0$ | same | max err 7.5e-15, leakage 0 | 1e-10 | PASS |
| (c) CX/T/rotation counts, `build_UE(0.37)`: project `logical_metrics` vs whole-circuit `transpile(basis=[cx,h,s,sdg,t,tdg,x,z,rz], opt 0, seed 1)` vs closed form $4(2+2\cdot 8)$ | 72 CX, 24 rz, 0 T | 72 / 24 / 0 in all three | exact | PASS |
| (c) `build_UK(0.185)`; closed form $4(4+2\cdot7)$ CX, $4\cdot4$ rz | 72 CX, 16 rz, 0 T | 72 / 16 / 0 in all three | exact | PASS |
| (c) `build_UB(0.61)` (raw ops: 246 ccx, 158 cx, 52 ch, 16 cz, 8 crx, 8 p, 176 x) | project = whole transpile | CX 1718 = 1718; $N_{\rm rot}$ 16 = 16 ($=2\times$8 crx); T-type 1826 = 1826. Hand count: $158+6\cdot246+52\cdot1+16+2\cdot8=1718$ (ch = 1 CX); T $=7\cdot246+2\cdot52=1826$ | exact | PASS |
| (c) `build_step` order 1 | CX = UE+UK+UB | 1862 = 72+72+1718 (project = whole transpile); $N_{\rm rot}$ 56 = 24+16+16; T 1826 | exact | PASS |
| (c) `build_step` order 2 | CX = 2UE_half+2UK_half+UB | 2006 = 2·72+2·72+1718; $N_{\rm rot}$ 96 = 48+32+16; T 1826 | exact | PASS |

Caveat (c): the T-type count 1826 counts Clifford+T gates after the Qiskit level-0 lowering (Toffoli = 7 T, CH = 2 T-type); it is the design count, not an optimised T-count.

## Verdict

PASS for part 1: 0 failures, 0 pending. Counts: 453 + 102 + 13 + 5 = 573 pytest tests passed, 3 spot-check groups (a, b, c) passed, acceptance-check PASS (acceptance-v10). No new failures vs. any earlier report (first m9 gate report). Raw numbers: `results/tester/300-m9-gate-full-part1.json`, `results/tester_logs/`.

Open for part 2: T1 (x4), R1 (x5), `O1_shared_table_file`.
