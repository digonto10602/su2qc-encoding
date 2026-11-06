# Test report 032 — M2 step 2.5: baselines, seeds, polish, round 0

- Date: 2026-11-05
- Git commit: 7d76375 (HEAD = STATUS-only commit on top of 244f52f = acceptance-v7); working tree dirty (the step 2.4/2.5 files are uncommitted)
- Prompt in force: `prompts/006-lean-formal-verification-m2-addendum.md` (plan prompts/002 §5 row 2.5; addenda 003–006; audit 003 N4)
- Mode: step
- Related: reports/tests/027, 029 (step 2.3), 026 (builder). Raw numbers: `results/tester_m2_step2_5_baselines.json`.
- Files under test: `src/su2plaq/compress/{baselines,passes,round,metrics}.py`, `refs/trotter/plaquette_seeds.json`, `scripts/export_trotter_seeds.py`, `compress/programs/twelve/seed/000-general.py`, `tests/unit/test_compress_baselines_unit.py`.

## Verdict: PASS (step 2.5)

Everything the builder claimed is confirmed independently; no failure in step 2.5. Three m2 acceptance tests fail/pend, all belong to later steps (listed below). Four notes N1–N4 for the coordinator.

## 1. Commands

```
source /home/digimonk/anaconda3/etc/profile.d/conda.sh && conda activate coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
pytest -n auto tests/acceptance/m2/test_compress_machinery.py -v --durations=20          # 290 s
pytest -n 6 tests/unit -q                                                                  # 332 passed, 141 s
pytest -n 6 -m "not slow" tests/acceptance/m0 tests/acceptance/m1 -q                       # 54 passed, 157 s
python -m su2plaq.compress.round --encoding twelve --kind step --seed --root <scratch>     # 157 s
graphify update . ; graphify query ... ; graphify affected "general_circuit"
```
Independent scripts (scratchpad, not in the repo): `indep_sim.py`, `indep_full.py` (own numpy sparse simulator, no use of the repo evaluator), `cmp_trotter.py`, `counts.py`, `check_general.py`, `polish_t.py`, `polish_fuzz.py`, `synth_t.py`, `negctl.py`, `l3counts.py`, `run_l3.py`. Scratchpad: `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/`.

## 2. Gate checks

| check | expected | got | PASS/FAIL |
|---|---|---|---|
| `tools/check_lock.py` | LOCK OK | LOCK OK | PASS |
| `acceptance-check` | acceptance-v7 matches | PASS: matches acceptance-v7 | PASS |
| collect-only (tests/acceptance) | clean | 102 tests collected | PASS |
| unit tests | all green | 332 passed (141 s) | PASS |
| m0 + m1 non-slow | all green | 54 passed (157 s) | PASS |
| m2 `test_compress_machinery.py` | named ids green | 29 passed, 3 failed/pending (below), 290 s | PASS for step ids |

Named step-2.5 ids, all PASSED: `test_evaluator_accepts_general_circuit`, `..._accepts_global_phase`, `..._rejects_wrong_gate`, `..._rejects_dirty_ancilla`, `..._rejects_small_ancilla_leak`, `..._rejects_angle_error`, `..._rejects_partial`, `..._rejects_control_change`, `test_skeleton_angle_independent_general`, `test_run_candidate_cli_trial_and_full`, `test_metrics_match_qiskit_count_ops`, `test_t_estimate_formula`, `test_entry_has_provenance_fields`, `test_polish_valid_and_not_worse`, `test_qiskit_l3_baseline_valid`, `test_seed_import_declared[paulo34]` (275 s under load), `[lean22_v2]`, `[spinnet15]`. Also green: oracle, builder gateset / macro costs / mcx chain, T-in-Ross–Selinger band (3), T deterministic, archive roundtrip / reject-invalid, cache keyed by code hash.

### Remaining m2 failures (classification)

| id | what happens | class |
|---|---|---|
| `test_round_dry_run_end_to_end` | `NotImplementedError: make_brief is not built yet` | PENDING (step 2.6, `compress/brief.py`) |
| `test_report_table_from_results` | `NotImplementedError: report_table is not built yet` | PENDING (step 2.8, `compress/report.py`) |
| `test_archive_best_valid_and_not_worse_than_seed` | `arch.best()` is `None` for the REAL root: no `compress/archive/twelve/` exists yet because `round --seed` has not been run on the real root. Not a NotImplementedError, but it is the "after the loop" test. I executed its exact assertions on my scratch root: best `r00-seed-001` valid, full re-evaluation valid, skeleton equal, fresh key = recorded key = (162, 660, 1029, 35), best <= min(seed keys), evaluator hash equal. | NOT-YET-RUN (real round 0, step 2.6/2.7); logic verified on the scratch root |
| Lean files (`test_lean_formal.py`, `test_lean_structure.py`) | not in scope (other tester) | ignored |

New failures versus last report (029): none.

## 3. Independent verification

### 3.1 lean22 / lean22_v2 seeds (the headline)

**(a) Vendored circuit == su2qc-trotter at 35b8b62c.** `git archive 35b8b62c src` into scratch, import `su2trotter` from there, rebuild `lean.build(alpha)` (lean22) and `designs.lean22_v2.A_plaq(alpha)` at $\alpha \in \{0, 0.37, 1, 1.22, 2, 3.3\}$ and compare gate by gate with `refs/trotter/plaquette_seeds.json`: names, qubits, register map identical (1142 gates / 22 qubits and 570 gates / 19 qubits); rz angle deviation from `coefficient * alpha` $\le 8.9\times10^{-16}$. JSON records commit 35b8b62c267421ca1b74ee42efe6fb73d513cd28, `commit_dirty: false` (and the working tree of su2qc-trotter has HEAD = that commit, tracked files clean).

**(b) Plaquette only; angle map.** Both builders in that commit are the *plaquette* (`lean.build`: no electric rz; `A_plaq` = `build_plaquette`; the electric layer is `add_electric`/`A_step`, not exported). JSON has exactly 4 `rz` gates (the rotation). Negative controls with my simulator against the exact target `U_B(0.61)` / our step:

| control | block error (op norm) | expected |
|---|---|---|
| $\alpha_P = \beta$ (wrong map) | 0.60 | reject |
| $\alpha_P = -2\beta$ (wrong sign) | 1.88 | reject |
| $U_E$ appended AFTER the plaquette (su2qc-trotter order) vs our step | 0.99 | reject |
| $\alpha_P = 2\beta$, plaquette then ... (the imported seed, $U_E$ FIRST) | $\le 2.4\times10^{-14}$ | accept |

So $\alpha_P = 2\beta$ and the $U_E$-first order are both pinned.

**(c) Independent correctness on all 433 physical states (own simulator).** All 625 distinct inner codes are propagated through the circuit (data + ancillas, ancilla register $|0\rangle$ in), then assembled into the 28-qubit physical states; compared with $\sum_m U_{mk}|\mathrm{phys}_m\rangle$ from `oracle.target`. The simulator asserts that no outer qubit is touched (passes). Columns: max over the 433 input states of the full-space vector error; "block" = $\|R-U\|_2$ with $R_{mk}=\langle\mathrm{phys}_m|\mathrm{out}_k\rangle$; Gauss = norm of the part of out$_k$ outside span(433 physical vectors); leak = rigorous triangle bound $\sum_t |a_t|\,\|\Psi_t^{\perp}\|$ for ancillas $\ne 0$.

| seed | kind | $(\alpha,\beta)$ | col. error | block $\|\cdot\|_2$ | Gauss | ancilla leak (bound) |
|---|---|---|---|---|---|---|
| lean22_v2 | UB | (0.37, 0.61) | 1.19e-14 | 1.71e-14 | 6.0e-15 | 4.0e-15 |
| lean22_v2 | UB | (0.91, 0.23) | 1.16e-14 | 1.69e-14 | 6.2e-15 | 3.7e-15 |
| lean22_v2 | UB | (1.7, 1.0) | 1.19e-14 | 1.68e-14 | 6.4e-15 | 3.8e-15 |
| lean22_v2 | step | (0.37, 0.61) | 1.27e-14 | 1.77e-14 | 1.3e-14 | 5.0e-15 |
| lean22_v2 | step | (0.91, 0.23) | 1.29e-14 | 2.41e-14 | 1.3e-14 | 4.5e-15 |
| lean22_v2 | step | (1.7, 1.0) | 1.32e-14 | 1.97e-14 | 8.3e-15 | 4.5e-15 |
| lean22 | UB | the same 3 pairs | 3.3e-14 | 3.9e-14 | 8.8e-15 | 1.9e-15 |
| lean22 | step | the same 3 pairs | 3.3–3.4e-14 | 3.8–4.1e-14 | 6.1e-15 | 2.4e-15 |

Tolerances: error $\le 10^{-10}$, Gauss $\le 10^{-10}$ (exact circuits). All PASS, margin $\ge 10^{3}$. Global phase fitted: $|\phi|\le 2.3\times10^{-16}$ (the circuits are exact with no extra phase). (A first reading of Gauss as $\sqrt{\|O\|^2-\|R\|^2}$ gave a spurious $10^{-7}$: pure $\sqrt{}$ of rounding noise; I recomputed it as the norm of the projection residual.)

**(d) Counts by my own lowering** (`transpile(..., basis=[cx,h,t,tdg,s,sdg,x,z,rz,p], optimization_level=0)`; Qiskit decomposes `ch` into 1 CX + 2 T; $T$ per rotation from pygridsynth at $\varepsilon=10^{-6}$):

| circuit | CX | T_fixed | n_rot | depth | qubits used / register | T(1e-6) own | repo (`metrics`) | PASS |
|---|---|---|---|---|---|---|---|---|
| lean22_v2 + $U_E$ | 162 | 160 | 8 | 260 | 19 / 35 | 660 | 162 / 160 / 8 / 260 / 35 / 660 | PASS |
| lean22 + $U_E$ | 210 | 192 | 8 | 360 | 22 / 38 | 704 | 210 / 192 / 8 / 360 / 38 / 704 | PASS |
| general (M1 step) | 294 | 312 | 10 | 292 | – / 50 | 952 | 294 / 312 / 10 / 292 / 50 / 952 | PASS |

The `qubits` key counts the whole register (12 data + 16 outer + ancillas); lean22_v2 touches only 19 of its 35 (outer never touched). This is consistent across all rows (general: 50, Paulo: 50). Compared with general: CX $-45\%$ (162 vs 294), T(1e-6) $-31\%$ (660 vs 952).

### 3.2 `000-general.py`

- Regenerating through `baselines.program_source` gives a byte-identical file (4189 bytes): PASS.
- Load the program, build at 9 angle pairs (3 fixed + 6 uniform in $[-3,3]^2$, rng 2026): 237 gates, skeleton identical at all 9: PASS.
- The 7 rotation gates were re-fitted by me by least squares in $(\alpha,\beta)$: coefficients $(-0.75, 0)\times 4$ ($p$ on qubits 2, 5, 8, 11) and $(0,-1), (0,-2), (0,-4)$; worst residual $4.4\times10^{-16}$ (tolerance $10^{-10}$): PASS.
- Program == `circuits.twelve.build_step(...)` gate for gate, names/qubits/angles, max angle deviation 0 at all 9 pairs: PASS.

### 3.3 Windowed Qiskit L3

- Valid: independent sparse simulation with macros (ccx/rccx/ccz) native, 24 of 433 states (rng 12345, state 0 included), 3 angle pairs: col. error $\le 2.1\times10^{-14}$, Gauss $\le 7.4\times10^{-15}$, leak 0 (this subset only; the repo evaluator covers all 433 in `test_qiskit_l3_baseline_valid`, PASSED, and in round 0, valid). The general circuit itself: $2.1\times10^{-15}$. Max sparse support for L3 1.14 M amplitudes per state (general: 2.2 k).
- Counts reproduced: windowed (32, level 3, seed 12345): CX 290, T_fixed 302, n_rot 10, depth 269 (general 294/312/10/292); key in the archive (290, 918, 1387, 50). Seeds 1, 2, 3 give identical counts (the L3 result does not depend on the transpiler seed here).
- **Does "windowed" change the meaning of the baseline?** Yes, slightly, and the direction is that the windowed baseline is *weaker* (worse) than the stock one. Whole-circuit L3 (`qiskit_l3_whole`): CX 290, T_fixed 294, depth 268. Window sweep (CX / T_fixed / depth): 8: 290/308/273; 32: 290/302/269; 64: 290/302/268; 128: 290/300/268; whole (= window 100000): 290/294/268. So the window cost is $+8$ T_fixed ($+2.7\%$), CX unchanged. The whole-circuit circuit could not be verified: my sparse sim needs $>5\times10^8$ amplitudes for the vacuum (hoisted Hadamards over ancillas), i.e. it is unsimulable by the exact sparse engine, so its validity is *unknown*, not wrong. For Report 2: say "Qiskit level 3, applied in 32-instruction windows because the whole-circuit level-3 output cannot be verified by the exact sparse engine; the unverified whole-circuit counts are CX 290 / T_fixed 294 (T(1e-6) $\approx$ 892 estimated)". All our results (CX 162) beat both, so no conclusion changes. A fair claim is "CX −44 % vs Qiskit L3 (290)".

### 3.4 Polish

- On the general circuit: removes 6 gates (inverse pairs of self-inverse Paulis), key unchanged (294, 909.9, 292, 50) ⇒ not strictly better ⇒ input kept (it never replaces the circuit unless strictly better in the key and valid in trial mode): PASS (never worse).
- Injected-cancellation inputs (general circuit with junk prepended): (i) `x; cx; x; t; tdg; cx; h h; s sdg` → 16 gates cancelled, key (296, 911.9, 294, 50) → (294, 909.9, 292, 50), output valid, accepted; (ii) the same plus `rz(0.2) rz(0.3)` on an ancilla: 14 cancelled + 1 merged, key (296, 1031.5, 294, 50) → (294, 969.7, 292, 50), valid, accepted; (iii) two extra `p` gates on a data qubit (an invalid input): polish merges, trial evaluation rejects the candidate, the input is returned unchanged.
- Rewrite soundness fuzz: 3000 random 4-qubit circuits (names x z h s sdg t tdg rz p cx cz swap ch crz crx cp ccx ccz rccx, forced inverse insertions, qubit order permuted for symmetric gates), 2819 of them rewritten: $\|U_{\rm before}-U_{\rm after}\|_\infty$ vs `qiskit.quantum_info.Operator`: 0 mismatches at $10^{-10}$ (rng 7). Note `rccx(0,1,2) rccx(1,0,2)` is NOT the identity (checked) and polish does not cancel swapped-control rccx pairs (the same-qubit-tuple rule): PASS.

### 3.5 Clifford+T re-verification of the best circuit (lean22_v2 + $U_E$), $\varepsilon = 10^{-6}$

| check | expected | got | PASS |
|---|---|---|---|
| `verify_synthesised`: ok and certified | True | ok True, certified True (sparse engine) | PASS |
| n_rot | 8 | 8 | PASS |
| T_total | 660 | 660 (my count of t+tdg in the synthesised circuit: 580 + 80) | PASS |
| tolerance `synth_tolerances(8, 1e-6)` | $8\times10^{-6}+10^{-9}$ | 8.001e-6 (error and Gauss) | PASS |
| op_norm_error (repo) | $\le 8.001\times10^{-6}$ | $2.989\times10^{-6}$ | PASS |
| independent column error (own sim, global-phase fit) | $\le n_{\rm rot}\varepsilon = 8\times10^{-6}$ | $2.48\times10^{-6}$ | PASS |
| independent Gauss | $\le 8.0\times10^{-6}$ | $3.4\times10^{-7}$ | PASS |
| independent ancilla-leak triangle bound | $\le 8\times10^{-6}$ | $6.2\times10^{-6}$ (a conservative bound) | PASS |
| $\varepsilon = 10^{-8}$ | T 818, error $\le 8\times10^{-8}$ | T 818, error $1.38\times10^{-8}$, Gauss $7.2\times10^{-9}$, leak bound $1.2\times10^{-7}$ | PASS (leak is the loose triangle bound) |

The synthesised circuit's global phase is not tracked (without the fit I get the phase of order 1: $\sqrt2$/1.85 errors, i.e. the phase $\phi = 2.356$ / $1.571$): this is by design, the evaluator fits a global phase (`test_evaluator_accepts_global_phase` PASSED) and the circuit is a *unitary up to a global phase*, which is physically irrelevant for a standalone $U$. Note for Report 2: a controlled use of the circuit would not tolerate it.

### 3.6 `run_round --seed` into a scratch root (`.../scratchpad/round_root`)

Wall 156 s. Output: `n_valid` 5, `n_invalid` 0, `best_key` [162, 660, 1029, 35].

| entry | key (CX, T(1e-6) measured, depth_ct, qubits) | cell | valid |
|---|---|---|---|
| r00-seed-000 (general program) | (294, 952, 1421, 50) | (65, 79) | yes |
| r00-seed-general+polish | (294, 952, 1421, 50) | (65, 79) | yes |
| r00-seed-qiskit_l3 | (290, 918, 1387, 50) | (65, 78) | yes |
| r00-seed-001 (lean22_v2) | (162, 660, 1029, 35) | (58, 74) | yes, best |
| r00-seed-002 (lean22) | (210, 704, 1148, 38) | (61, 75) | yes |

- Archive index: 5 entries, family `seed` best `r00-seed-001`, elites 4 cells. `external`: `paulo34` (fixed angle $\beta=1$, kind UB, valid, op_norm_error $1.0756\times10^{-5}\le 1.6\times10^{-5}$, 294 CX, T 1162, depth 2549, qubits 50, NOT in the archive: good) and `spinnet15` (reason string). `synthesis_verification`: entry r00-seed-001 ok True, n_rot 8, T_total 660, op_norm_error $2.99\times10^{-6}$, certified. Provenance in the round JSON: commit 7d76375, `git_dirty` True, versions, platform, `evaluator_sha256`, `spec_sha256`, `trial_seed` 0. `attempts/twelve.jsonl` has 5 lines (the lean entries as well), no `discoveries` file.
- The repo tree was not changed by my round (git status before/after identical apart from the other tester's files).

## 4. Notes (non-blocking)

- **N1.** `round._circuit_of` swallows every exception (`except Exception: return None`), so a failing circuit rebuild silently turns the Clifford+T re-verification into `synthesis_verification: null`. Suggest recording the failure message in the round JSON (hard rule: no silent catches in numerical code).
- **N2.** Archive entries store `program_path` as an ABSOLUTE path for programs (`/…/compress/programs/…`) but a relative pseudo-path (`compress/programs/twelve/seed/qiskit_l3.circuit`) for circuit seeds (these files do not exist). `test_archive_best_valid_and_not_worse_than_seed` does `root / best.program_path`; works with absolute paths, but the archive is not relocatable. Also the circuit-seed pseudo paths cannot be re-evaluated from source (the best entry will be a program, so the test is fine).
- **N3.** Windowed L3 is a weaker baseline than whole-circuit L3 by 8 T_fixed (3.3 above); keep that sentence in Report 2.
- **N4.** The Clifford+T circuits carry an untracked global phase; fine for standalone $U$, but the final report should say "up to a global phase".
- The `time` of `test_seed_import_declared[paulo34]` is 275 s under load (aer_mps evaluation of Paulo's circuit); it is the slowest test in the file.

## 5. Raw data

`results/tester_m2_step2_5_baselines.json` (commit 7d76375, dirty tree; rng seeds: L3 transpiler 12345, state subset 12345, polish fuzz 7, angle fit 2026, trial 0).
