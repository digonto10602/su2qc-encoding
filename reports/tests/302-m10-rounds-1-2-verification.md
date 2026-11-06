# Tester report 302: M10 rounds 1-2 verification (mode: step)

Date 2026-11-06. Commit `ebd52e9` (branch m9-fuzzy; round-3 proposer files untracked, ignored). Prompt in force: prompts/302 (+ METHODS-fuzzy F9). acceptance-check: PASS (acceptance-v11).

## Commands
- `python scratch/tester/verify_r12.py <unit> <id>` (one process per entry, `taskset -c 0-7`) and `python scratch/tester/skel.py`
- `python scripts/m10_round.py best-step --out scratch/tester/best-step-r2.json` and `... best-step --no-outer --out scratch/tester/best-step-r2-inner.json`
- `pytest -n 4 -m "not slow" tests/acceptance/m10 -q`; `pytest -n 4 tests/acceptance/m10 -q -k G2`; `pytest -n 3 tests/acceptance/m10 -q -k "G1 or G3"`
- Raw: `results/tester_m10_r12_verify.json`, `results/tester_m10_best_step_r2.json`, `results/tester_m10_best_step_r2_inner.json`

## Check 1-2: independent rebuild (second engine = qiskit `Statevector`, maximally-entangled reference register, ancillas |0>)
Entries rebuilt via `circuit_of_entry` at nominal (0.37, 0.61) and both alternates; target `UB_row(beta)` (256x256) or `UEK_link(alpha, kappa2=spec.beta)` (16x16); global phase fitted by $\mathrm{tr}(T^\dagger B)$; error = $\|B - e^{i\varphi}T\|_2$. Tolerance: err <= 1e-10; leak = amplitude outside ancilla-|0>; counts from my own `transpile(basis=[cx,h,s,sdg,t,tdg,x,z,rz], opt 0)` (n_rot = rz not a multiple of $\pi/4$; T_fixed = t+tdg+odd-multiple rz) compared to the archive's `metrics_raw` (cx/n_rot/t_fixed/qubits). Max over the 3 angle pairs. Program sha256 matches the archive for all 8.

| unit | entry | max op-norm err | leak | $\|B^\dagger B-1\|$ | my cx/n_rot/T_fixed/qubits | archive | counts equal across angles | skeleton equal | verdict |
|---|---|---|---|---|---|---|---|---|---|
| link | r01-F1-001 | 4.1e-15 | 0 | 1.3e-15 | 13/10/0/4 | 13/10/0/4 | yes | yes | PASS |
| link | r02-F2-001 | 5.2e-15 | 0 | 4.8e-15 | 12/10/0/4 | 12/10/0/4 | yes | yes | PASS |
| ub | r01-F1-001 | 1.8e-14 | 0 | 1.1e-14 | 200/58/112/16 | same | yes | yes | PASS |
| ub | r01-F2-001 | 1.8e-14 | 0 | 3.2e-15 | 268/16/280/14 | same | yes | yes | PASS |
| ub | r01-F3-001 | 1.8e-14 | 0 | 3.5e-15 | 390/16/396/14 | same | yes | yes | PASS |
| ub | r02-F1-002 | 1.8e-14 | 0 | 8.6e-15 | 172/44/96/14 | same | yes | yes | PASS |
| ub | r02-F2-002 | 2.3e-14 | 8.1e-15 | 3.6e-14 | 172/44/116/15 | same | yes | yes | PASS |
| ub | r02-F3-002 | 2.0e-14 | 0 | 3.1e-14 | 192/58/128/16 | same | yes | yes | PASS |

Skeleton = gate names, qubit tuples and all non-angle parameters identical at the three angle pairs (`skel.py`; only angle gates such as rz/crx differ in angle). Note: the archive key's T_eps and depth_ct were not recomputed (needs gridsynth); only cx / n_rot / T_fixed / qubits were.

## Check 3: best step composition (order 1; best units = ub r02-F1-002, link r02-F2-001)
`verify_step_samples`: 40 inputs, seed 20261104, mode "layers".

| composition | err (tol 1e-10) | Gauss (tol 1e-10) | CX | n_rot | T_fixed | qubits | T-estimate(1e-6) | general baseline (CX / n_rot / T_fixed / qubits) | PASS |
|---|---|---|---|---|---|---|---|---|---|
| with outer (UB + 4 inner + 8 outer link blocks) | 1.1e-14 | 5.9e-15 | 316 | 164 | 96 | 54 (6 anc) | 9902 | 2150 / 136 / 1826 / 55 | PASS |
| inner only (UB + 4 link blocks) | 1.1e-14 | 5.2e-15 | 220 | 84 | 96 | 22 | 5119 | 1862 / 56 / 1826 / 23 | PASS |

Consistency: 316 = 172 + 12*12, 220 = 172 + 4*12, n_rot 164 = 44 + 12*10, 84 = 44 + 4*10. Note the composed T-estimate with outer (9902) is only 0.6 % below the general step (9958): the rotations (164 vs 136) now dominate T cost, so CX shrank 6.8x but T count barely.

## Check 4: pytest
- `-m "not slow" tests/acceptance/m10`: 6 passed, 1 failed, 3 deselected (slow). Failure: `test_M10_R1_reports_rendered_with_lean_column`: `docs/report-10-fuzzy-compression.md` does not exist (assert doc.exists()); the per-unit report_table part passed up to that line. Expected before the final report (guess).
- `-k G2`: 2 passed (fuzzy_ub-UB, fuzzy_link-UE).
- `-k "G1 or G3"` (slow-marked): 3 passed (G1 both units, G3 composed step).
- Pending/open: only R1 (needs `docs/report-10-fuzzy-compression.md` with before/after table, Lean column, composed-step row). Side effect: R1's report_table writes results/compress/<enc>/summary.json.

## Verdict: PASS (rounds 1-2). No new failures; one expected-open test (R1).
