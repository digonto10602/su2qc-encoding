# Tester report 402 — M7 (LSH) steps 7.6 (walk, build_UB) and 7.7 (build_step orders 1, 2)

- Date: 2026-11-10 · Git commit: `d65d325` (HEAD moved during the session; the LSH files `src/su2plaq/circuits/lsh.py`, `src/su2plaq/lsh/walk.py`, `tests/unit/test_lsh_codec_unit.py`, `tests/unit/test_lsh_walk_unit.py` were uncommitted and unchanged while I tested)
- Prompt in force: `prompts/400-lsh-m7-plan.md` (acceptance-v16 for m7; latest tag acceptance-v17) · Mode: step · Cores 14–17 (`-n 4`)
- Related: `reports/tests/401-m7-steps-7-3-7-5.md`, `docs/METHODS-lsh.md` L7

## Commands
```
tools/pytest-safe -n 4 -q -p no:cacheprovider --junitxml=$S/t402/m7.xml tests/acceptance/m7        # 29 tests, 9.6 s
tools/pytest-safe -n 4 -q -p no:cacheprovider tests/unit                                           # 892 passed, 1 failed, 692 s
python -m pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
PYTHONPATH=src tools/run-capped python results/lsh_tester/tester-402-independent.py results/lsh_tester/tester-402-independent.json   # 88 checks, 36 s
tools/run-capped python results/lsh_tester/tester-402-mutations.py <scratch copy> results/lsh_tester/tester-402-mutations.json     # 31 mutants
```

## 1. Locked acceptance tests (m7), junit per test
| check | expected | got | verdict |
|---|---|---|---|
| A1, K1, K2, X1, C1, C2, E1[0.37], E1[0.91], G1, T1[UE] (earlier greens) | pass | 10 passed | PASS |
| B1[0.4, 0.61, 1.0, 2.0], B2, B3, S1[1], S1[2] (steps 7.6/7.7) | pass | 8 passed (0.5–2.6 s each) | PASS |
| T1[UB], T1[step] (early green) | pass | 2 passed | PASS |
| V1[general7, pairs9, flags4], L1, L2, L3, R1[UE, UB, step] | fail only with `PENDING:` | 9 failed, 9/9 junit messages contain `PENDING:` | PASS (pending) |

20 passed, 9 pending, 0 other failures (matches the expected 20 + 9). New vs report 401: B1×4, B2, B3, S1×2, T1[UB], T1[step].

## 2. Independent verification (`results/lsh_tester/tester-402-independent.py`, 88 checks, 0 failed)
Own code: label to 24-bit code, route-B 6j target $e^{-i\beta H_B^{6j}}$, diagonal $U_E=e^{-i\alpha\sum_{\rm inner}j(j+1)}$ from the labels, own sparse gate-walk simulator (monomial matrix of Qiskit's `RCCXGate` for `rccx`, 24 + 7 bit codes, dict amplitudes), own gate/CX/T/depth recount (rccx expanded with `RCCXGate().definition`), own pygridsynth call. Circuits built `with_outer=True`; all 433 physical states as inputs; block error = $\min_\varphi\lVert M-e^{i\varphi}V\rVert_2$.

| check | expected | got | tol | verdict |
|---|---|---|---|---|
| $U_B(\beta)$ vs target, $\beta=0.4, 0.61, 1.0, 2.0$, random $1.896933$ (seed 20261110) | 0 | 9.4e-16, 2.8e-15, 3.9e-15, 8.4e-15, 8.3e-15 | 1e-10 | PASS |
| $U_B$: leak weight, dirty-ancilla weight, outer-changed weight | 0 | leak $\le2.1\cdot10^{-28}$ (opnorm $\le2.4\cdot10^{-15}$), dirty 0, outer-changed 0 | 1e-20 | PASS |
| $U_B$: outer qubits 12..23 touched by any gate; $\lVert M^\dagger M-1\rVert$ | none; $\le10^{-10}$ | none; $\le8.9\cdot10^{-16}$ | – | PASS |
| $U_B$ gate list with vs without outer register (after relabel) | identical | identical (5 betas) | exact | PASS |
| rz angles / $\beta$ at 0.61; linearity at $\beta=2$ | $\{-7/2,-1,3/2,3\}$ | same to $10^{-12}$ | 1e-12 | PASS |
| step o1 $=U_BU_E$ and o2 $=U_E(\alpha/2)U_BU_E(\alpha/2)$ at $(\alpha,\beta)=(0.37,0.61),(0.91,0.23),(1.70,1.00)$ and random $(0.5121,1.9494)$ | 0 | worst $9.99\cdot10^{-15}$ (o2, random pair); nominal 2.9e-15 | 1e-10 | PASS (8) |
| step: leak / dirty / outer-changed weight; outer qubits untouched | 0 | $\le5.9\cdot10^{-28}$; untouched | 1e-20 | PASS |
| wrong order rejected, nominal pair: o1 vs o2 target / vs $-\beta$ / vs layer-swapped $U_EU_B$ | $>10^{-3}$ | 0.515 / 1.878 / 0.990 (o2: 0.515 / 1.878); other pairs 0.56–1.82 | 1e-3 | PASS |
| transcoder (own simulation of `W.TRANSCODE`) maps all 47 inner LSH codes to wires $[j_n=\tfrac12]$ (wire $3c$), $[J_c=1]$ ($3c+1$), $[J_c=\tfrac12]$ ($3c+2$) from the labels | 0 mismatches | 0 of 47; injective (47 images) | exact | PASS |
| transcoded (link, corner) wires $=$ SpinNet `code_of_label` low 8 bits, all 433 labels | 0 | 0 | exact | PASS |
| CX recount (cx + 3 per rccx) vs `logical_metrics` | 94 | UB 94, step o1 94, o2 94 | exact | PASS |
| $T_{\rm fixed}$ recount (4 per rccx) | 88 | 88 / 88 / 88 | exact | PASS |
| rotation count ($rz+p$) | 4 / 8 / 12 | 4 / 8 / 12 | exact | PASS |
| depth recount (rccx expanded) vs `logical_metrics` | 87 | 87 / 87 / 87 | exact | PASS |
| qubits: touched = `num_qubits` = logical | 19 | 19 / 19 / 19 (7 ancillas) | exact | PASS |
| electric phases: o1 $4\times p(-3\alpha/4)$, o2 $8\times p(-3\alpha/8)$ | – | as expected | 1e-12 | PASS |
| $T_{\rm total}(\varepsilon=10^{-6})$ own pygridsynth vs `t_table` | planner 342 / 598 | 342 / 598 / 870 (o2) | exact | PASS |
| synthesised ($\varepsilon=10^{-6}$, `synthesize`) block + leak opnorm + $\sqrt{\rm dirty}$ vs $N_{\rm rot}\varepsilon+10^{-9}$ | $\le4.0\cdot10^{-6}$ (UB), $8.0\cdot10^{-6}$ (o1), $1.2\cdot10^{-5}$ (o2) | UB $1.30\cdot10^{-6}$ (0.326 of budget); o1 $2.03\cdot10^{-6}$ (0.254); o2 $3.36\cdot10^{-6}$ (0.280); o1 at $(0.91,0.23)$ $2.92\cdot10^{-6}$ (0.365); dirty 0, outer-changed 0 | rule | PASS |
| synthesised circuit T count = $T_{\rm fixed}$ + own pygridsynth sum | 342 / 598 / 870 / 598 | equal | exact | PASS |

## 3. Mutations (scratch copy `.../scratchpad/mut402b`; repo untouched; `results/lsh_tester/tester-402-mutations.{py,json}`)
Targets per mutant: acceptance B1[0.61], B2, B3, S1[1,2], E1[0.37], T1[UB], T1[step]; 4 LSH unit-test files (39 tests); my independent checker. Baseline: 0 failures.
**31 of 31 mutants caught by the locked acceptance tests**, 29 of 31 also by unit tests, all 31 by the independent checker.

| group | n | acceptance ids that fail | unit | notes |
|---|---|---|---|---|
| drop one gate of `TRANSCODE` (forward and inverse both lose it), gate 0..11 | 12 | B1, B2, B3, S1×2, T1[UB], T1[step] (all 7 targets) | 6 failed each | builder's residual guard in `build` also raises |
| drop one gate of the transcoder inverse only (0,1,2,3,5,6,8,11) | 8 | B1, B2, S1×2, T1×2 (B3 passes: Gauss residual unchanged) | 2 each | independent: 32 failing checks |
| flip the sign of rz angle 0..3 (inside `solve_angles`), one angle $\times1.001$, all angles $\times(-1)$ | 6 | B1, B2, B3, S1×2, T1×2 | 3 each | caught by the residual guard (ValueError) as well |
| flip the sign of rz angle $k$ **after** the guard (extra run, `guard_evading.py`), $k=0..3$ | 4 | B1, B2, S1 fail | 4 failed + 9 passed in the subset; independent 32 FAIL lines | not in the 31 |
| order-1 step layers swapped ($U_E$ after $U_B$) | 1 | S1[1], T1[step] | 0 (unit tests do not simulate) | independent: 8 failing checks (layer-swapped target, o1 vs own target) |
| order-2 second electric layer dropped | 1 | S1[2] | 2 | independent 4 |
| electric layer on the corner-bit wires instead of the link wires | 1 | S1[1], S1[2], T1[step] | 0 | independent 8 |
| first cx of FRAME dropped; one X on a CBIT dropped | 2 | B1, B2, B3, S1, T1 | 6 / 3 | |

Harness remark: the "independent fails" counter in the JSON (`tester-402-mutations.json`) counts one spurious line (`FAILED_CHECKS n`) per run, so the baseline shows 1; the conclusions do not change (non-crashing mutants have 4–32 real failing checks, the crash cases are the builder's own guard raising `ValueError`). The group that has no unit-test coverage (layer swap of order 1, electric layer on the wrong wires) is covered by acceptance S1/T1 and by the independent checker; optional: a unit test pinning the order-1 layer order.

## 4. Suites and hygiene
| check | expected | got | verdict |
|---|---|---|---|
| unit suite | all pass | 892 passed, **1 failed**: `tests/unit/test_rishon_det_unit.py::test_h_det_inner_and_hamiltonian` (rishon builder's new, untracked file, mid-step; not counted) | PASS for LSH |
| `test_rishon_compress_spec_unit.py::test_committed_spec_files_equal_the_renderer` | may be red | passed in this run | note |
| LSH unit files (walk 7 tests + circuits + codec incl. new `test_decode_fallback_end_conventions` + operators) | pass | 39 passed in the mutation baseline | PASS |
| collection `tests/acceptance` | clean | 313 collected | PASS |
| `tools/check_lock.py`; `acceptance-check` | LOCK OK; PASS | LOCK OK; "tests/acceptance matches acceptance-v17" | PASS |
| shared hashed files (LOCK.json, `EVALUATOR_FILES`) modified by this step | none | the LSH diff touches only `circuits/lsh.py`, `lsh/walk.py`, `tests/unit/test_lsh_codec_unit.py` (+ new `test_lsh_walk_unit.py`); none is hashed. Other modified files in `git status` (spinnet, rishon) belong to other agents | PASS |
| `graphify affected` coverage | covered | dependents are the LSH unit tests and m7 acceptance tests, all run | PASS |

## Verdict: PASS
0 failures attributable to steps 7.6/7.7; 20 acceptance passed, 9 pending (`PENDING:` stubs: V1×3, L1–L3, R1×3). Out-of-scope observation: one red rishon unit test (other agent's mid-step file).

## Files touched by my runs
- new: `results/lsh_tester/tester-402-independent.{py,json}` (88 checks, seed 20261110), `results/lsh_tester/tester-402-mutations.{py,json}`, this report.
- scratchpad (outside repo): `.../scratchpad/mut402b` (mutation copy), `.../scratchpad/t402/*` (junit, logs, `guard_evading.py`).
- no tracked source, test or lock file modified by my runs.
