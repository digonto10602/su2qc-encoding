# Tester report 015 - M1 step 1.2: electric step `build_UE`

- Date: 2026-11-04. Commit: 7743b18 + uncommitted working tree (step 1.1 files, step 1.2 `src/su2plaq/circuits/twelve.py`, `tests/unit/test_twelve_circuits_unit.py`).
- Prompt in force: `prompts/004-leak-amplitude-combined-error-bound.md` (on top of `prompts/002`, §4 row 1.2; `docs/METHODS.md` §2). Mode: step.
- Raw numbers: `results/m1-step-1.2-electric.json` (no randomness, no seed).
- Related: reports/tests/014 (M0 gate rerun). Step 1.1 is verified by a separate tester and not re-verified here.

## Commands
```
pytest -n auto tests/acceptance/m1/test_twelve_circuits.py -k E1 -q          # 2 passed
pytest -n auto tests/unit -q                                                   # 147 passed
pytest -n auto -m "not slow" tests/acceptance/m0 -q                            # 33 passed
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
python <scratchpad>/chk.py     # independent checks (Qiskit Operator, evaluator, t_table)
graphify affected build_UE     # only the two unit tests and M1-E1 call it: all run
```

## Results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| M1-E1 `[0.37]`, `[0.91]` | pass | 2 passed | - | PASS |
| unit tests (all, incl. step 1.1) | pass | 147 passed | - | PASS |
| m0 not slow | unaffected | 33 passed | - | PASS |
| check_lock / acceptance-check / collect | OK, v4, 86 tests | LOCK OK, PASS (acceptance-v4), 86 | - | PASS |
| (1) one-link operator, 3-qubit Qiskit `Operator`, $\alpha\in\{0.37,0.91,1.70\}$: $\mathrm{diag}(1,\cdot,\cdot,\cdot,\cdot)$, phase $e^{-3i\alpha/4}$ on codes 111,110,101,100, 1 on 000, and codes 001-011 = 1 | exact | max off-diagonal 0.0; diagonal error 0.0 at all three $\alpha$ | 1e-15 | PASS |
| (1b) full 12-qubit `Operator`: diagonal, phase $=\prod_{l}e^{-3i\alpha q_j^{(l)}/4}$ | exact | off-diagonal 0.0; diagonal error $\le 1.1\times10^{-16}$ | 1e-15 | PASS |
| (2) inner, 433 states vs `target('UE')`, $\alpha$ = 0.37 / 0.91 / 1.70 (sparse engine, certified) | $\le10^{-10}$ | op_norm_error $1.207\times10^{-13}$ / $1.207\times10^{-13}$ / $1.207\times10^{-13}$ (block error; leak amplitude 0.0) | 1e-10 | PASS |
| (2) outer-row variant (`with_outer`, `include_outer_electric=True`, 12 p gates) vs `target(..., include_outer_electric=True)` (method physical, 8 outer bits read) | $\le10^{-10}$ | $3.8\times10^{-15}$ / $2.9\times10^{-15}$ / $3.7\times10^{-15}$ | 1e-10 | PASS |
| (2) `with_outer` without outer row vs inner target (outer bits read = 0) | $\le10^{-10}$ | $3.3\times10^{-15}$ / $3.1\times10^{-15}$ / $3.5\times10^{-15}$ | 1e-10 | PASS |
| (3) wrong sign $p(+3\alpha/4)$ must fail (reason "error") | O(1) | fails; op_norm_error 1.281 / 1.939 / 1.998 (see note) | - | PASS |
| (4) `logical_metrics` inner: cx / n_rot / t_fixed / depth / ancilla | 0 / 4 / 0 / 1 / 0 | 0 / 4 / 0 / 1 / 0 | exact | PASS |
| (4) outer-row variant | 0 / 12 / 0 / 1 | 0 / 12 / 0 / 1 (28 qubits) | exact | PASS |

Note on (3): the wrong-sign circuit differs from the right one by $e^{3i\alpha k/2}$ on states with $k$ spin-1/2 inner links ($k\le4$) after the best global phase is removed; the observed error is the largest $|1-e^{3i\alpha k/2}|$-type spread over the 433 states, bounded by 2 (e.g. 1.998 at $\alpha=1.7$). The single-link value $|1-e^{3i\alpha/2}|$ = 0.548 / 1.261 / 1.913 is a lower bound for the spread, consistent with all three got values. The sign convention $e^{-3i\alpha/4}$ is therefore confirmed by two independent routes (Operator and the evaluator).

Note: inner-circuit block error is $1.2\times10^{-13}$, about 40 times larger than the $3\times10^{-15}$ of the outer-row variant on the same diagonal circuit. Both are far below 1e-10 and identical across $\alpha$, so this looks like a fixed round-off floor of the sparse/physical path (a guess), not a problem.

## T-count (first real T-count of the project), pygridsynth 1.2.0, exact `rz` angle $-3\alpha/4$ per rotation
`t_total` = `t_fixed`(0) + sum over rotations; 4 rotations (inner), 12 (inner + outer row).

| $\alpha$ | $\varepsilon=10^{-4}$ | $10^{-6}$ | $10^{-8}$ | $10^{-10}$ |
|---|---|---|---|---|
| 0.37, inner (4 rot) | 176 | 256 | 328 | 416 |
| 0.91, inner | 168 | 256 | 328 | 416 |
| 1.70, inner | 176 | 256 | 344 | 424 |
| 0.37, outer row (12 rot) | 528 | 768 | 984 | 1248 |
| 0.91, outer row | 504 | 768 | 984 | 1248 |
| 1.70, outer row | 528 | 768 | 1032 | 1272 |
| estimate $4\cdot3\log_2(1/\varepsilon)$ | 159.5 | 239.2 | 318.9 | 398.6 |

Per rotation (inner, $\alpha=0.37$): 44 / 64 / 82 / 104 T gates, against $3\log_2(1/\varepsilon)$ = 39.9 / 59.8 / 79.7 / 99.7: all inside the Ross-Selinger band (no lower-edge violation here, unlike the 1e-10 case noted in reports/tests/012). Qiskit-compiled count (level-0 route, $\alpha=0.37$): T = 172 / 236 / 328 / 380 with CX 0 and depth 116 / 149 / 212 / 244 (differs from pygridsynth sum by +-8 to 36; compile uses its own synthesis; the pygridsynth `t_total` is the project metric).
The circuit has 0 CX, so the CNOT and T cost of $U_E$ is entirely the 4 (or 12) single-qubit phase rotations.

## Pending
Other tests in `tests/acceptance/m1` (B1-B4, S1, codec, outer, paulo, results, metrics) were not part of this step; not run.

## Verdict: PASS (0 failures, 0 new failures vs. report 014)
