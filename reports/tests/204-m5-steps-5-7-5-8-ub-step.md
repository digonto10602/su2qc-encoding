# Tester report 204 — M5 steps 5.7 + 5.8 (U_B, step), mode `step`

- Date: 2026-11-06
- Git: `4d2265c` + uncommitted (`src/su2plaq/circuits/rishon.py`, new `src/su2plaq/rishon/frames.py`, `tests/unit/test_rishon_circuits_unit.py`, `tests/unit/test_rishon_stubs_unit.py`). The brief said fcc5d9d; HEAD is 4d2265c (one later notes-only commit).
- Prompt in force: `prompts/200-rishon-m5-plan.md` (acceptance-v8, caps: `prompts/005`)
- Related: reports/tests/200–203
- Raw data / scripts: `results/rishon/tester-204-*` (JSON/log/py). Seeds: simulator check seed 204; verify sample seed 20261104 (production default); everything else deterministic.

**VERDICT: PASS.** No failures, no new failures. Three notes (N1–N3) for the coordinator/planner.

## Commands run (all under `taskset -c 10-19`, env `su2qc-coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`)

```
pytest -n 5 tests/acceptance/m5/test_rishon_metrics.py -k T1          # 3 passed, 1173 s
pytest -n 5 tests/acceptance/m5 -m "not slow"                          # 27 passed, 6 failed (L1, L2, R1x4), 1189 s (also ran T1 + B1 + S1)
pytest -n 5 tests/acceptance/m5/test_rishon_lean.py -k L3              # failed: PENDING HB.lean missing
pytest -n 10 tests/unit                                                # 291 passed, 55 s
pytest -n 10 -m "not slow" tests/acceptance/m0 tests/acceptance/m1     # 54 passed, 75 s
pytest --collect-only -q tests/acceptance                              # 136 collected, clean
python tools/check_lock.py                                             # LOCK OK
~/.claude/bin/acceptance-check                                         # PASS: matches acceptance-v8
python results/rishon/tester-204-{simcheck,ub-independent,counts,prune-accounting,relprune,coalesce-count,rccx-variant,adversarial}.py
```

## 1. Acceptance and regression

| check | expected | got | PASS/FAIL |
|---|---|---|---|
| `M5_B1_magnetic_inner_block[0.23, 0.61, 1.0, 2.0]` | pass | 4/4 passed (64–71 s) | PASS |
| `M5_B1_physical_with_outer_and_gauss` | pass | passed (59 s) | PASS |
| `M5_S1_step_orders[1]`, `[2]` | pass | passed (137 s, 71 s) | PASS |
| `M5_T1_t_table_and_synth_verify[UE, UB, step]` (slow) | pass | 3 passed; UB 941 s, step 1102 s, UE 42 s (under CPU contention) | PASS |
| earlier m5 ids (D1 x2, C1 x4, X1 x5, O1 x4, E1 x2, B1 verifier sensitivity) | pass | all passed | PASS |
| remaining m5 failures | only Lean L1–L3, results R1 | L1, L2, L3 ("PENDING: ...lean missing"), R1 x4 ("PENDING: missing results/rishon/*.json, step 5.10") — nothing else | PASS (pending, as agreed) |
| collection | 136 clean | 136, clean | PASS |
| unit | green | 291 passed | PASS |
| m0 + m1 `not slow` | green | 54 passed | PASS |
| `check_lock` / `acceptance-check` | PASS acceptance-v8 | LOCK OK / PASS: matches acceptance-v8 | PASS |

## 2. Independent physics (own JW reference + own simulator)

Own code (`tester-204-mysim.py`): global-JW 16-mode operators, $W=\sum U_{b,ab}U_{r,bc}U^\dagger_{t,dc}U^\dagger_{l,ad}$, $H_B^{\rm in}=-(W+W^\dagger)$ on the 1296 codes, $H_E$ from the link Casimir; batched sparse gate simulator for `x,z,h,cx,cz,ch,ccx,ccz,crx,p`. Simulator validated against `qiskit.quantum_info.Operator` on 40 random 5-qubit circuits: max difference $3.2\times10^{-16}$.

Spectrum extremes of own $H_B^{\rm in}$: $\pm5.6569=\pm4\sqrt2$. Own bright-component $\kappa$ counts: $\{1:32,\ 2:48,\ 4\sqrt2:1\}$.

| check | expected | got | tolerance | PASS/FAIL |
|---|---|---|---|---|
| $\lVert M_{U_B}-e^{-i\beta H_B}\rVert_2$ ($M$ = 1296x1296 block, ancillas 0), $\beta=0.23$ | 0 | $1.44\times10^{-14}$ | 1e-10 | PASS |
| same, $\beta=0.61$ | 0 | $1.41\times10^{-14}$ | 1e-10 | PASS |
| same, $\beta=1.0$ | 0 | $1.60\times10^{-14}$ | 1e-10 | PASS |
| same, $\beta=2.0$ | 0 | $1.59\times10^{-14}$ | 1e-10 | PASS |
| global phase (all four $\beta$) | 1 (none needed) | $1+0i$ (error without phase fit identical) | – | PASS |
| ancilla dirty weight, leak out of the 1296 codes (all $\beta$) | 0 | 0.0, 0.0 | 1e-20 | PASS |
| block unitarity $\lVert M^\dagger M-1\rVert$ | 0 | $2.8$–$3.2\times10^{-14}$ | – | PASS |
| $U_B(0)$ vs identity | 0 | $1.3\times10^{-14}$ | 1e-10 | PASS |
| crx angles $\lvert\theta\rvert/\beta$ (all four $\beta$) | $2\kappa$: 2 (x32), 4 (x48), $8\sqrt2=11.3137085$ (x1) | `crx:2.0` x32, `crx:4.0` x48, `crx:11.313708499` x1 | 1e-9 | PASS |
| angle linearity: $\theta(0.23)/0.23-\theta(2.0)/2.0$ over the 81 crx | 0 | 0.0 (exact) | – | PASS |
| factor convention ($U_B=e^{-i\beta H_B}$, $H_B=-\sum\kappa(\lvert u\rangle\langle v\rvert+{\rm h.c.})$, $R_x(-2s\kappa\beta)$) | agrees with expm | the four expm comparisons above (sign and factor 2 both fixed by them; wrong sign $\beta\to-\beta$ gives 1.88 error) | – | PASS |
| skeleton (gate names + qubits) identical for $\beta\in\{0.23,0.61,1,2\}$ | identical | True | exact | PASS |
| skeleton of `build_step` identical for $(\alpha,\beta)=(0.37,0.61)$ vs $(1.7,1.0)$, both orders | identical | True | exact | PASS |
| only 81 parameterised gates in $U_B$ (all crx); no fixed-angle tricks | 81 | 81 | – | PASS |
| step order 1 = $U_B U_E$ ($U_E$ first): $\lVert M-U_BU_E\rVert$ at $(0.37,0.61)$ / $(1.7,1.0)$ | 0 | $1.52\times10^{-14}$ / $1.71\times10^{-14}$ | 1e-10 | PASS |
| step order 2 = $U_E(\alpha/2)U_BU_E(\alpha/2)$ at the same angles | 0 | $1.58\times10^{-14}$ / $1.60\times10^{-14}$ | 1e-10 | PASS |
| wrong order $U_EU_B$ against order-1 circuit | $\gg10^{-10}$ | 0.515 / 1.740 | $>10^{-3}$ | PASS (rejected) |
| order-1 circuit vs order-2 target; order-2 circuit vs $U_BU_E$ | $\gg10^{-10}$ | 0.260 / 1.121 (both) | $>10^{-3}$ | PASS (rejected) |
| step circuits: ancilla dirty weight, leak | 0 | 0, 0 | 1e-20 | PASS |
| `with_outer=True`: outer qubits touched by any gate | none | none (register order `d(16), o(32), anc(10)`, 58 qubits) | – | PASS |

Production verdicts (`verify`, nominal angles): all `ok`, `certified`, engine `sparse`, Gauss residual $2.1$–$2.7\times10^{-15}$ on 273 states, `max_leak` 0, `dirty_ancilla` 0.

Verifier sensitivity on perturbed $U_B(0.61)$ (all rejected, `reason=error`): sign flip of the smallest crx 1.88; sign flip of the $8\sqrt2$ crx 0.608; $+10^{-6}$ on one crx $5.0\times10^{-7}$ (twice, $=\delta/2$ as expected); one crx deleted 1.15; $\beta\to-\beta$ 1.88. (My first attempt to mutate the angle in place had no effect on the copy; I rebuilt the circuits instead — the results above are from the rebuilt ones.)

## 3. Accounting

| check | expected | got | PASS/FAIL |
|---|---|---|---|
| gate set vs locked `ALLOWED` | $\subseteq$ ALLOWED | UB uses `ccx, x, cx, ch, cz, crx, h, z` (step adds `p`); `ch, crx, ccz` are in the locked ALLOWED set and in the METHODS.md cost table (`ch` 1 CX + 2 T, `crx` 2 CX + 2 rot, `ccx` 6 CX + 7 T) | PASS |
| native mcx with $\ge3$ controls | none | 0; largest gate is `ccx` (3 qubits); controls up to 11 are built from a `ccx` ladder on 10 clean ancillas | PASS |
| $U_B$ counts: my own tally from `count_ops` with the METHODS cost table | CX 10094, $T_{\rm fixed}$ 10218, $N_{\rm rot}$ 162 | 10094 / 10218 / 162 (`ccx` 1402, `x` 1224, `cx` 1118, `ch` 202, `cz` 200, `crx` 81, `h` 34, `z` 16) | PASS |
| same, from a real `transpile` to {cx,h,t,tdg,s,sdg,x,y,z,rz} level 0 | same | cx 10094, T 10218, 162 non-Clifford `rz` | PASS |
| step order 1 / 2 | CX 10102/10110, rot 166/170 | 10102 / 10110, 166 / 170, $T_{\rm fixed}$ 10218 (own and transpile) | PASS |
| `logical_metrics` (production) | equals above | identical | PASS |
| qubits | 26 | 26 (16 + 10 ancillas) | PASS |
| depth 2402 | – | Qiskit macro-level `qc.depth()` = 2402 (step 2405 / 2408); the lowered depth reported by `logical_metrics` is **13682** — different quantity, see N3 | note |
| `op_norm_error = block + dropped + leak` | to 1e-15 | residual 0.0 on all five verdicts | PASS |
| prune cap rule (prompts/005): reject iff `dropped_total > 1e-2 * tol_err` | as written | boundary test on $U_B(0.61)$, $d=3.02\times10^{-13}$: `tol_err` $=0.9\cdot100d$ gives `pruning_bound` (cap $2.72\times10^{-13}$), $1.1\cdot100d$ gives `ok` | PASS |

Prune-bound numbers (exact-angle tol 1e-10, cap $10^{-12}$): $U_B(0.61)$: block $4.14\times10^{-14}$, dropped $3.02\times10^{-13}$, total $3.43\times10^{-13}$ (headroom to cap 3.31); $U_B(2.0)$: dropped $3.16\times10^{-13}$ (3.17); step 1: $3.68\times10^{-13}$ (2.72); step 2: $3.65\times10^{-13}$ (2.74); step 2 at (1.7,1.0): $3.86\times10^{-13}$ (2.59). Pruning is 88–90 % of the certified error.

Is the bound sound? True error against exact expm (my simulator): $1.4\times10^{-14}$ $\le$ certified $3.4\times10^{-13}$. Yes, with a 24x margin. My own simulator accumulates the same quantity (sum over merges of $\sqrt{\text{dropped weight}}$ per column, then Frobenius over columns) at $1.8\times10^{-15}$; same value with an absolute $10^{-15}$ threshold or the production relative $10^{-14}$ threshold. The production number is 163x larger: it simulates the lowered circuit (819 coalesces vs my 317, because `ch`/`crx` are lowered to Clifford+rz by transpile) and drops more rounding noise per coalesce (`dropped_max` $1.47\times10^{-14}$ vs my $5.7\times10^{-16}$). Both are valid upper bounds; the production one is merely conservative. Method of accounting is correct; the magnitude is a property of the lowered simulation (a guess for the cause of the 163x).

## 4. Hygiene

- `git status --short`: modified `src/su2plaq/circuits/rishon.py` (track-R file), `tests/unit/test_rishon_stubs_unit.py` (removes the three now-implemented names from the "pending raises" list — legitimate); new `frames.py`, `test_rishon_circuits_unit.py`. No laptop-owned file, no `tests/acceptance`, no `docs`, no `prompts` modified.
- No `try/except` in `frames.py` or `circuits/rishon.py`; all `ValueError`s are raised, not swallowed.
- No hard-coded expected numbers: $\kappa$, pivots, controls, signs are solved from `operators.bright_pairs()`; the only constants are numerical tolerances (`_TOL_AMP`, `_CTRL_TOL` = 1e-9). The 2 / 4 / $8\sqrt2$ appear only in docstrings.
- graphify `affected` for `designs`/`pair_frames`: only `_n_ancillas`, `_emit_ub`, `build_UB`, `build_step` (all exercised above).

## Notes (not failures)

- **N1 (design consequence of the prune cap, planner matter).** The builder's claim is reproduced: replacing the ancilla `ccx` ladder by `rccx` (my monkeypatch, nothing written to `src/`) keeps the circuit exact (true block error $3.4\times10^{-13}$, `ok` at `tol_err` $10^{-8}$, ancillas clean) but `dropped_total` $=2.28\times10^{-12}>10^{-12}$, so the verdict is `pruning_bound`. That variant would cost CX 6866 / $T_{\rm fixed}$ 7262 against 10094 / 10218 (-32 % / -29 %). The cap rule (1 % of `tol_err`) is applied as written; it is a conservative simulator artefact (24x–160x above the true error) that currently decides the gate choice. Raise with the planner before M5 compression/benchmark claims. `results/rishon/tester-204-rccx-variant.json`.
- **N2.** Headroom of exact-angle circuits to the cap is only 2.6–3.3x for $U_B$/steps (planner's 12-qubit table had 6.6–8.3x). Any further growth of the circuit (more branching gates) can trip `pruning_bound` without any physics error.
- **N3.** "depth 2402" in the builder summary is the macro-level Qiskit depth; `logical_metrics` reports depth 13682 for the lowered circuit. Make sure reports quote the one the plan means.
- Wall time: T1 UB 941 s / step 1102 s (non-slow run, contended) and 1173 s (T1 alone, 5 workers); builder quoted 411 s / 611 s — same order, CPU was shared with other jobs. Not a benchmark (mode `step`).
- Another agent's `pytest -n 10 ... m0 m1` ran briefly on the same cores while I worked; it did not interfere with correctness.

## Summary counts

passed: 27 (m5, incl. T1 x3) + 291 unit + 54 (m0+m1) ; failed: 0 real ; pending (Lean/results): 7 (L1, L2, L3, R1 x4) ; new failures vs. report 203: 0.
