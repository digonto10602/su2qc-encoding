# Tester report 303: M10 gate, mode full, round 3

Date 2026-11-06. Commit `b4c5c18` (branch m9-fuzzy; src/ unchanged since tag milestone-9; docs-only commits during the run, numbers in docs untouched except wording). Prompt in force: prompts/302 (+ METHODS-fuzzy F9). acceptance-check: PASS (acceptance-v11); `tools/check_lock.py`: LOCK OK.

## Commands
- `python scratch/tester/verify_r12.py fuzzy_ub <id>` for r03-F1-003, r03-F2-003, r03-F3-003 (one process each, pinned cores)
- `python scripts/m10_round.py best-step --out scratch/tester/best-step-r3.json` and `... --no-outer --out ...-inner.json` (committed `results/fuzzy/compressed_step.json` not overwritten)
- `python tools/check_lock.py && ~/.claude/bin/acceptance-check`
- `pytest -n 32 tests/unit -q`; `pytest -n 28 tests/acceptance/m0 tests/acceptance/m1 tests/acceptance/m2 -q`; `pytest -n 4 tests/acceptance/m10 -q` (all 10 incl. slow G1/G3, R1)
- Raw: `results/tester_m10_r3_verify.json`, `results/tester_m10_best_step_r3.json`, `results/tester_m10_best_step_r3_inner.json`

## 1. Second-engine rebuild (qiskit Statevector with maximally-entangled reference, ancillas $|0\rangle$; target `UB_row(beta)`, 256x256; global phase fitted; 3 angle pairs)
| entry | max $\|B-e^{i\varphi}T\|_2$ (tol 1e-10) | skeleton equal across angles | my cx / n_rot / T_fixed / qubits | archive | sha256 | verdict |
|---|---|---|---|---|---|---|
| ub r03-F1-003 | 2.05e-14 | yes | 164 / 44 / 112 / 14 | same | match | PASS |
| ub r03-F2-003 | 2.19e-14 | yes | 165 / 44 / 106 / 14 | same | match | PASS |
| ub r03-F3-003 (global best) | 1.96e-14 | yes | 151 / 28 / 118 / 13 | same | match | PASS |

Counts are identical at all three angle pairs. T_eps/depth_ct not recomputed (needs gridsynth); archive Clifford+T re-verification in round-003.json: err $3.37\times10^{-6}\le2.8\times10^{-5}$, 28 rotations (read, not rerun).

## 2. Composed step (ub r03-F3-003 + link r02-F2-001), `verify_step_samples`, 40 inputs, seed 20261104, mode layers
| composition | err (tol 1e-10) | Gauss (1e-10) | CX | n_rot | T_fixed | qubits | verdict |
|---|---|---|---|---|---|---|---|
| with outer | 1.69e-14 | 5.87e-15 | 295 (expected 295 = 151+12x12) | 148 | 118 | 53 (5 anc) | PASS |
| inner only | 1.69e-14 | 5.21e-15 | 199 (expected 151+4x12) | 68 | 118 | 21 (5 anc) | PASS |

Rebuilt `composed` block identical to the committed `results/fuzzy/compressed_step.json` (err 1.6878e-14, Gauss 5.873e-15 match to all printed digits; depth 255; t_estimate 8967.6).

## 3. Report-10 §3 numbers vs summary.json / compressed_step.json
| item | doc | source | match |
|---|---|---|---|
| §3.1 all 8 rows (qubits, CX, T_fixed, N_rot, T(1e-6), CT-depth, err) | as in doc | fuzzy_ub summary rows | yes |
| round-1/2 best rows (200/58/3804/9501/16q; 172/96/44/2904/7206/14q) | as in doc | round-001/002 best_key + lineage | yes |
| 12 candidates / 11 valid; -91 % CX, -33 % T | | n_candidates 12, n_valid 11; 151/1718, 1902/2822 | yes |
| §3.2 all 5 rows; 5 candidates / 4 valid; -67 % | | fuzzy_link summary | yes |
| T(1e-6) per link block | 644 | fuzzy_link all rows 644 | yes |
| T(1e-6) UB before / after | 2822 / 1902 | fuzzy_ub summary | yes |
| inner before $2822+4\cdot644$ | 5398 | arithmetic 5398 | yes |
| inner after $1902+4\cdot644$ | 4478 | 4478 | yes |
| all links before $2822+12\cdot644$ | 10550 | 10550 | yes |
| all links after (with outer) $1902+12\cdot644$ = 4478 + 8x644 (5152) | 9630 | 9630 | yes |
| composed CX/n_rot/T_fixed/depth/qubits/ancilla | 295/148/118/255/53/5 | compressed_step.json | yes |
| general CX/n_rot/T_fixed/depth/qubits | 2150/136/1826/2690/55 | same | yes |
| t_estimate 8968 / 9958 | | 8967.6 / 9958.08 | yes |
| inner-only 199 / 68 / 21 (16+5) | | recomputed (section 2) | yes |
| 4.7x T vs KS 952 | | 4478/952 = 4.70 | yes (KS/12-qubit 294 CX, 952 T, 111 CX / 912 T not rechecked here; from Report 1 / M2) |

Mismatches found (wording only, no number wrong):
1. Doc §3.1 lineage "side branches F2 268 → 172 → 165": in `fuzzy_ub/summary.json` lineage, r02-F2-002 (172) has parent r01-F1-001 (not r01-F2-001, 268); r03-F2-003 (165) has parent r02-F2-002. So 268 and 172 are in the same family F2 but not parent/child. Suggest "F2: 268 (r1), then 172 (r2, child of r01-F1-001) → 165".
2. Inner-only "before" row (5398 T, 1862 CX, 23 qubits) is a derived sum, not a field of compressed_step.json (doc says so for T); 1862 and 23 come from Report 9 / tester 302 baseline (1718+4x36 = 1862 consistent).

## 4. Pytest
| suite | result |
|---|---|
| tests/unit | 486 passed, 84.6 s |
| acceptance m0 + m1 + m2 | 102 passed, 169 s |
| acceptance m10 (all 10, incl. slow G1/G3 and R1 now that the report exists) | 10 passed, 114 s; re-run at HEAD b4c5c18 after the audit-fix commit: 10 passed, 92 s |
| acceptance m9 | not run (src unchanged since milestone-9; gate reports 300-301) |
| pending | none |

Side effects: none on tracked files (git status clean apart from pre-existing untracked files and my results/tester_* JSONs).

## Verdict: PASS (0 failed, 0 pending; no new failures vs report 302; R1 now passes). Only the lineage wording note above.
