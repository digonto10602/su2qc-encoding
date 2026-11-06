# Tester report 205 — M5 steps 5.9 + 5.10 (T(eps) tables, results files), mode `step`

- Date: 2026-11-06
- Git: `56b466d` + uncommitted (new `scripts/m5_results.py`, `src/su2plaq/rishon/results.py`, `tests/unit/test_rishon_results_unit.py`, `results/rishon/{UE,UB,step,step_order2,UE_outer_row}.{json,qpy,qasm3}`, `observables.json`, `register_rows.json`). Also in the tree, NOT part of 5.9/5.10: `lean/Su2Plaq/Rishon/{Counts,JW}.lean` and a one-line import in `lean/Su2Plaq.lean` (a Lean builder was running `lake env lean Su2Plaq/Rishon/JW.lean` in this clone while I tested).
- Prompt in force: `prompts/200-rishon-m5-plan.md` (acceptance-v8, `prompts/201` test fix)
- Related: reports/tests/204 (steps 5.7+5.8), 203, 202
- Raw data / scripts: `results/rishon/tester-205-*` (`.py`, `.json`, logs, `tester-205-m5.xml`). Seeds: own random codes seed 205; production sample seed 20261104; everything else deterministic.

**VERDICT: PASS** for steps 5.9 and 5.10. Two Lean acceptance tests (L1, L2) fail as PENDING/in-progress (steps 5.L1/5.L2 not finished, out of scope here). No new failures versus report 204 (204 had R1 ×4 + L1 + L2 failing; R1 now passes). Four notes (N1-N4), none blocking.

## Commands run (all under `taskset -c 10-19`, env `su2qc-coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, peak machine use 11 GB used of 31 GB incl. the Lean builder's 6 GB)

```
pytest -n 10 tests/unit -q                                              # 303 passed, 93 s (incl. the --quick script test)
pytest -n 5 -m "not slow" tests/acceptance/m5 -q --junitxml=results/rishon/tester-205-m5.xml   # 31 passed, 2 failed, 702 s
~/.claude/bin/acceptance-check ; python tools/check_lock.py              # PASS acceptance-v8 ; LOCK OK
PYTHONPATH=src python results/rishon/tester-205-{files-gates,ttable,physics-observables,outer-row-classical,observables-regen,schema}.py
```
The two target tests and T1 ×3 were part of the m5 run (not just reports/tests/204): T1[UE] 24 s, T1[UB] 405 s, T1[step] 630 s, all PASS. `scripts/m5_results.py` (58 min) was not rerun.

## 1. Acceptance and regression

| check | expected | got | tolerance | PASS/FAIL |
|---|---|---|---|---|
| `M5_R1_results_files[UE,UB,step]` | pass | 3/3 passed | locked | PASS |
| `M5_R1_observables_and_register_rows` | pass | passed | locked | PASS |
| `M5_T1_t_table_and_synth_verify[UE,UB,step]` | pass | 3/3 passed | locked | PASS |
| rest of `tests/acceptance/m5` non-slow (D1 ×2, C1 ×3 + codec, X1 ×3 (inner_target ×2 angles), E1 ×2, B1 ×6, S1 ×2, O1 ×4, verifier sensitivity) | pass | all passed (31 of 33 total) | locked | PASS |
| `M5_L1_counts_kernel_checked` | PENDING (step 5.L1) | fails: `lake`/lean run gives `<unknown>` axioms for both count theorems | — | PENDING (not 5.9/5.10) |
| `M5_L2_jw_facts_kernel_checked` | PENDING (step 5.L2) | fails at `assert "native_decide" not in src`: the in-progress `JW.lean` docstring contains the words "no `native_decide`" | — | PENDING (see N4) |
| unit suite `tests/unit` | all pass | 303 passed (was 291 in 204; +12 new) | — | PASS |
| `acceptance-check`, `check_lock.py` | PASS | PASS acceptance-v8, LOCK OK | — | PASS |
| `pytest --collect-only` | clean | not rerun (no test file changed; acceptance-check hash matches) | — | PASS (by hash) |
| m0 + m1 regression | pass | not rerun (no source changed since 204: 54/54); new files are untracked additions only | — | not rerun |

## 2. Independent spot checks of the result files

Scripts `results/rishon/tester-205-*.py`; all numbers in the matching `.json`.

### 2a. Circuit files and gate counts (`tester-205-files-gates`)
Every `.qpy` exists, its sha256 equals the one in the JSON, and it loads (`qiskit.qpy.load`). Every `.qasm3` exists, starts with `OPENQASM 3`, declares the same registers (UE `d[16]`; outer row `d[16]`,`o[32]`; UB/step `d[16]`,`anc[10]`) and has as many gate statements as `qc.size()` (UB 4277, step 4289, step_order2 4301, UE 12, outer row 36). (`qiskit_qasm3_import` is not installed, so QASM3 was parsed as text, not reloaded.) Counts recomputed from the loaded `.qpy` by an independent Qiskit `transpile(..., optimization_level=0)` to $\{cx,h,s,s^\dagger,t,t^\dagger,x,z,r_z\}$ (not `su2plaq.metrics`):

| circuit | qubits (JSON / loaded) | CX | $N_{\rm rot}$ | $T_{\rm fixed}$ | macro_counts, depth, size vs JSON | PASS |
|---|---|---|---|---|---|---|
| UE | 16 / 16 | 8 / 8 | 4 / 4 | 0 / 0 | equal | PASS |
| UE_outer_row | 48 / 48 | 24 / 24 | 12 / 12 | 0 / 0 | equal | PASS |
| UB | 26 / 26 | 10 094 / 10 094 | 162 / 162 | 10 218 / 10 218 | equal | PASS |
| step | 26 / 26 | 10 102 / 10 102 | 166 / 166 | 10 218 / 10 218 | equal | PASS |
| step_order2 | 26 / 26 | 10 110 / 10 110 | 170 / 170 | 10 218 / 10 218 | equal | PASS |

Structure: step CX = UE + UB = 8 + 10 094; order 2 = 16 + 10 094; UB $N_{\rm rot}$ 162 = 2 × 81 `crx` (= 81 bright pairs); production `logical_metrics` equals the JSON for all five.

### 2b. T-count rows (`tester-205-ttable`), 5 circuits × 4 $\varepsilon$ = 20 rows, all PASS
- $t_{\rm total}=T_{\rm fixed}+\sum_r T_r(\varepsilon)$ exact in all 20 rows; $T_{\rm fixed}$ and $N_{\rm rot}$ re-derived from the independent lowering.
- Independent pygridsynth (own call of `gridsynth_gates` on the $r_z$ angles of my lowering) reproduces $\sum_r T_r$ exactly for UE at all four $\varepsilon$, and for outer row, UB, step, step_order2 at $\varepsilon\in\{10^{-4},10^{-6}\}$ (not done at $10^{-8},10^{-10}$ for the large circuits: time).
- Strictly monotone in $\varepsilon$: UE 176 < 256 < 328 < 416; UB 17 150 < 20 394 < 23 954 < 27 066; step 17 326 < 20 650 < 24 282 < 27 482; step_order2 17 486 < 20 922 < 24 626 < 27 898; outer row 528 < 768 < 984 < 1248.
- Ross-Selinger band (acceptance helper `ross_selinger_band`) holds; $t_{\rm est}=T_{\rm fixed}+3N\log_2(1/\varepsilon)$ to 1e-6.
- Qiskit CT vs pygridsynth: ratio $t_{\rm qiskit}/t_{\rm total}\in[0.904,1.000]$. Worst deviation 9.61 % (UB, $\varepsilon=10^{-4}$: 15 502 vs 17 150), then step 9.53 %, step_order2 9.42 %. All within 10 % but the margin at $\varepsilon=10^{-4}$ is only 0.4 percentage points. `cx_qiskit` $\le 1.1\,$CX + 2 everywhere.
- Synthesised re-verification (each row, $\varepsilon\in$ grid): `ok`, `tolerances`=$N_{\rm rot}\varepsilon+10^{-9}$ exactly, op-norm error, Gauss residual and leak amplitude all $\le$ that bound, `error_measured_sum` $\le$ `error_bound_sum` $\le N_{\rm rot}\varepsilon$, T gates counted in the synthesised circuit equal the table (`t_matches_table`). Largest ratio error/budget: UB at $\varepsilon=10^{-6}$: op-norm $1.84\times10^{-5}$ vs budget $1.62\times10^{-4}$ (0.11); Gauss $5.6\times10^{-6}$; leak $1.23\times10^{-5}$ (all certified, 273 Gauss states, `outer_bits_read` 0). Outer row at $10^{-4}$: $2.50\times10^{-4}$ vs $1.20\times10^{-3}$.

### 2c. Physics block and observables (`tester-205-physics-observables`)
| check | expected | got | tolerance | PASS/FAIL |
|---|---|---|---|---|
| physics block identical in all 5 JSONs | same | same | exact | PASS |
| dim, closed, $U(2)$ sector, inner span, pairs | 38 432, 4352, 2192, 1296, 81 | same (file); my own 1296 codes (own JW) → $H_B$ spectrum has 162 nonzero eigenvalues → 81 pairs | exact | PASS |
| $\kappa$ multiset | {1:32, 2:48, 4√2:1} | file `{1:32, 2:48, 5.65685425:1}` = 81 pairs; my $H_B$ eigenvalues $\pm1(32)$, $\pm2(48)$, $\pm5.656854(1)$, $0(1134)$ | 1e-6 | PASS |
| dark codes | 990 + 306 bright-component codes = 1296; 306 = 162 paired + 144 zero modes | consistent with file and with my 1134 zero eigenvalues (990 + 144) | exact | PASS |
| file observables vs own `expm_multiply` simulation (12 rows: rishon+KS, 3 angle pairs, $n=1,2$) | agree | max dev $3.2\times10^{-15}$ | 1e-10 | PASS |
| $n=1$ rishon vs KS closed forms ($\tfrac38\sin^2\theta_R,\tfrac14(1+\cos\theta_R)^2$ vs $\tfrac34\sin^2\theta_{KS},\cos^2\theta_{KS}$; $P(1)=0$) | agree | max dev $7.8\times10^{-16}$ | 1e-12 | PASS |
| closed spectra, $g^2\in\{0.5,1,2\}$ | rishon $0,\ \tfrac34g^2\pm\sqrt{\tfrac9{16}g^4+32g^{-4}}$ with multiplicities (1,15,1); KS 2 levels | max dev $1.8\times10^{-15}$; multiplicities (1,15,1) and (1,1) at all three | 1e-9 | PASS |
| register rows | 48 / 36 / touched 16 | 48 / 36 / 16 (step touches data qubits 0-15; UE alone touches 8) | exact | PASS |
| outer electric row, independent classical bit-tracking simulation of the loaded `.qpy` on 20 000 own random valid 48-bit codes (seed 205) vs $e^{-i\alpha\frac34\#Q}$ (one global phase) | agree, bits restored | max phase deviation $4.4\times10^{-16}$ rad, all 20 000 restored; UE (16 qubits) deviation 0.0 | 1e-10 | PASS |

Labelling of the outer row is honest: its `verification` block has `method: outer_electric_check`, `sampled: true`, `certified: false`, 3515 codes, seed, and the `extra.note` says "not a certificate"; the T-table synthesised rows keep `certified: false`. It has no `reason` key (differs from UE/UB/step; not required by the test).

### 2d. Provenance / schema (`tester-205-schema`, `tester-205-observables-regen`)
- `list(json) == RESULT_KEYS` for all five circuit files. Commit `56b466d`, host `SupremeCommander`, platform, versions, seeds (`transpiler_logical`, `clifford_t_pass_manager` 12345, `gauss_sample`/`outer_row_sample` 20261104), command, wall time 3490.8 s, peak RSS 496 MB main / 3091 MB largest worker, `quick: false`, `jobs: 8`, UTC timestamp; same snapshot in `observables.json` and `register_rows.json`. Params $(\alpha,\beta,{\rm order})$ recorded.
- All 7 JSONs have the same commit `56b466d` and `git_dirty: false`.

## 3. Notes (misleading names / provenance; none blocks the verdict)

- **N1 (provenance is wrong in the files).** The files were produced by code that was uncommitted at the time (`scripts/m5_results.py`, `src/su2plaq/rishon/results.py` untracked), yet every JSON says `git_commit: 56b466d`, `git_dirty: false`. Cause (certain): the laptop-owned `provenance()` computes `git_dirty` with `git status --porcelain --untracked-files=no`, so untracked sources do not count. Nothing in the files flags this. The coordinator's planned regeneration on a clean commit fixes it; until then the files are not traceable to a commit as the global rules require.
- **N2 (`observables.json` is stale by sign-of-zero).** The file contains six `-0.0` for $P(1)$; the current `observable_rows` (with the builder's `+ 0.0` fix) produces `0.0`. Regenerating the observables block with the current tree and diffing against the file: 6 differences, all `0.0` vs `-0.0`, max numeric difference 0.0. Harmless, but the committed file differs byte-wise from what the final code writes (another reason to regenerate).
- **N3 (schema oddities).** (a) The JSONs contain the non-strict token `NaN` at `verification.inner_verdict.gauss_residual` and in every synthesised verdict (value "not computed" by the laptop inner verdict; the outer `gauss_residual` is the real one). Python reads it, strict JSON parsers do not. (b) `register_rows.json` key `touched` is defined as "qubits touched by the step circuit" and is 16, while UE touches 8 (also given, `touched_by_circuit`); the codeword row has `touched: null`. (c) `extra.physics_detail.kappa_multiset` key `5.65685425` stands for $4\sqrt2$ (rounded to 9 digits), and the `qasm3` field of the macro-gate circuits holds macro gates (`rccx`, `crx`, ...), so `qasm3` size counts (4277) are macro statements, not the 13 682-depth lowered circuit. The macro/lowered distinction is labelled in `metrics.macro.depth_label`.
- **N4 (Lean state in this clone, not part of 5.9/5.10).** A Lean builder was active in the same clone during my run (uncommitted `lean/Su2Plaq/Rishon/{Counts,JW}.lean`, `lean/Su2Plaq.lean` import). `M5_L2` fails its first assertion because the draft `JW.lean` docstring contains the literal text "no `native_decide`" — the acceptance test greps the source for the substring (guess: reword the comment). `M5_L1` fails because the checker reports `<unknown>` axioms (build not finished or `#print axioms` output not parsed). Both are 5.L1/5.L2 matters.
- Margin note carried from 204: Qiskit CT is within 10 % with only 0.4 pp to spare at $\varepsilon=10^{-4}$ for UB/step/step_order2 (9.61 %, 9.53 %, 9.42 %). A different Qiskit CT seed or a lower-level circuit change could break the locked bound.

## 4. Verdict
Steps 5.9 and 5.10: PASS (T1 ×3, R1 ×4 pass; unit 303/303; acceptance-check PASS; independent file, gate-count, T-table, physics and observable checks all within tolerance). Pending: Lean L1, L2. Do not treat the current `results/rishon/*.json` as final: regenerate on a clean commit (N1, N2).
