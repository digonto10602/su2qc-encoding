# Test report 103 — M3 step 3.6 (`trotter_v2` vendored spinnet_v2 skeletons, `trotter_v2_circuit`, T(ε) tables, synthesised re-verification)

- Date: 2026-11-06 · Commit `ed7d630` (HEAD) + uncommitted `src/su2plaq/spinnet/trotter_v2.py`, `src/su2plaq/spinnet/walk.py` (`expand=`), `src/su2plaq/circuits/spinnet.py` (`trotter_v2_circuit`), new `tests/unit/test_spinnet_trotter_v2_unit.py`
- Branch `m3-spin-network`, prompt in force `prompts/100-spinnet-m3-plan.md` (§3 row 3.6), mode **step**, tester Claude Sonnet 5.5
- Related: `reports/tests/100`, `101`, `102`
- Raw data and scripts (track-owned, `results/spinnet/tester/`): `m3_step_3_6_fidelity.{py,json,log}`, `m3_step_3_6_verify.py` + `m3_step_3_6.{json,log,err}` (peak RSS 818 MB, wall 2 min 43 s), `m3_step_3_6_tcount.{py,json,log}`, `m3_step_3_6_synth.{py,json,log}`, `m3_step_3_6_sibling_alpha2.log`. Deterministic: no random numbers; Qiskit transpiler seeds 12345 (library), 7 and 11 (my own calls). All runs under `taskset -c 0-9`, `MemoryMax=10G`.

## Commands
```
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected trotter_v2_circuit ; graphify affected build_walk
taskset -c 0-9 pytest --collect-only -q tests/acceptance
taskset -c 0-9 pytest -n 10 -q tests/acceptance/m3 -rA --tb=line
taskset -c 0-9 pytest -n 10 -q tests/unit
taskset -c 0-9 pytest -n 10 -q -m "not slow" tests/acceptance/m0 tests/acceptance/m1
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
taskset -c 0-9 python results/spinnet/tester/m3_step_3_6_fidelity.py
systemd-run --user --scope -q -p MemoryMax=10G -p MemorySwapMax=0 taskset -c 0-9 python -u results/spinnet/tester/m3_step_3_6_verify.py
taskset -c 0-9 python results/spinnet/tester/m3_step_3_6_tcount.py
systemd-run --user --scope -q -p MemoryMax=10G -p MemorySwapMax=0 taskset -c 0-9 python -u results/spinnet/tester/m3_step_3_6_synth.py
git status --short
```
graphify: `affected build_walk` lists `build_UB`, `build_step`, `trotter_v2_circuit`, the unit tests of walk/circuits/trotter_v2, and earlier tester scripts; all callers were executed (acceptance C1/K1/P1/E1/B1/B2/B3/S1/T1/V1 and all unit tests). `affected trotter_v2_circuit`: none beyond V1 / unit tests.

## 1. Suites

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `pytest --collect-only -q tests/acceptance` | 126 clean | 126 collected | exact | PASS |
| `V1[pairs9-34-9]`, `V1[flags4-44-4]` | pass | 2 passed | — | PASS |
| `T1[UE]`, `T1[UB]`, `T1[step]` | pass | 3 passed | — | PASS |
| earlier m3 ids: C1, K1, P1, E1 ×2, B1 ×4, B2, B3, S1 ×2 | pass | 13 passed | — | PASS |
| m3 remaining failures | only L1–L3, R1 | 6 failed: L1, L2, L3 (Lean files / checker not delivered), R1[UE], R1[UB], R1[step] (`results/spinnet/*.json` not yet written) | no other reason | PASS (pending: steps 3.7, 3.L1–3.L3) |
| total m3 | — | 18 passed / 6 pending-failed / 0 real failures | | |
| `pytest -n 10 tests/unit` | all pass | 272 passed (+15 vs report 102: new `test_spinnet_trotter_v2_unit.py`) | — | PASS |
| m0+m1 `-m "not slow"` | green | 54 passed | — | PASS |
| `tools/check_lock.py` / `acceptance-check` | OK | `LOCK OK` / `PASS: tests/acceptance matches acceptance-v7` | — | PASS |

## 2. Vendoring fidelity against the sibling source (`m3_step_3_6_fidelity.py`)

I read `~/Projects/siblings/su2qc-trotter/src/su2trotter/designs/spinnet_v2.py` and, only inside this tester script (sibling `src` added to `sys.path`; production code never imports it), loaded it and compared programmatically.

| check | expected | got | verdict |
|---|---|---|---|
| step lists (pairs9, flags4, flags5, flags6) equal after mapping the sibling's `rccx_dg` → `rccx` | identical | identical for all 4 (37, 28, 31, 30 steps); `rc3x_dg` at the same positions; frames identical (`FRAME_B = ((3,1),(0,3),(0,2))` for pairs9, `FRAME = ((1,3),(0,1),(0,2))` otherwise); wires INTS = 4..7, ancillas 8, 9, 10 equal | PASS |
| gate-by-gate (sibling's lowered `Circuit` gate list vs ours with each `rccx` expanded in place to its definition): names and qubits | identical | identical for all 4: 93 / 134 / 121 / 104 gates | PASS |
| RCCX Hermitian, therefore `rccx_dg` ≡ `rccx` | $\lVert R-R^\dagger\rVert=0$, $\lVert R^2-\mathbb 1\rVert=0$ (Aer/Qiskit `Operator`) | $0.0$, $0.0$; sibling's `inverse_gates(rccx)` gives the same gate sequence as `rccx` (palindrome with $t\leftrightarrow t^\dagger$ swapped), as the gate-by-gate match shows | PASS |
| RC3X not self-inverse | $\lVert C^2-\mathbb 1\rVert\neq 0$ | $\lVert C-C^\dagger\rVert=2.0$, $\lVert C^2-\mathbb 1\rVert=2.0$; $\lVert C^{\dagger}C-\mathbb 1\rVert=6.7\times10^{-16}$ | PASS |
| negative control: flags4 with plain `rc3x` in the uncompute | rejected | block error 2.0 (dirty $4\times10^{-31}$, so it fails on the block) | PASS |
| counts vs sibling (our gate lists): CX / rotations / $T_{\rm fixed}$ | pairs9 34/9/24, flags4 44/4/48, flags5 42/5/40, flags6 36/6/32 | ours = sibling's own gate-list counts for all 4 (`ours_metrics`, `sib_metrics` in the JSON); depth ours 38 / 60 / 67 / 51 (sibling JSON `A_plaq` depth 38 for pairs9) | PASS |

**Angle gauge difference (explains every number below).** The skeletons agree gate for gate, but the solved rotation angles differ by one constant factor: $\theta^{\rm ours}_r(\beta)=-2\,\theta^{\rm sib}_r(\alpha=\beta)$ for all rotations of all 4 skeletons (e.g. pairs9 at 2.0: sibling $0.25,-0.25,0.75,\dots$, ours $-0.5, 0.5, -1.5,\dots$). So sibling $\alpha=2$ (their published run, `results_spinnet_v2.json`: `alpha: 2.0`) equals our $\beta=\mp1$: the factor 2 is the normalisation of Paulo's $\exp(+i\alpha\,\mathrm{Re\,Tr}W)$ ($\beta=\alpha_P/2$, METHODS-spinnet) and the sign is the per-pair sign gauge (route-B gauge vs the sibling's gauge; the gauge-align check below shows $D=$ `enc.gauge` exactly). The skeleton (qubits, gate order) is independent of the angles.

**Sibling's reported numbers vs ours** (sibling: `results_spinnet_v2.json` and `spinnet/archive.json`, $\alpha=2$, $\varepsilon=10^{-6}$ per rotation; ours: $\beta=1.0$, same $\varepsilon$, pygridsynth 1.2.0; `m3_step_3_6_sibling_alpha2.log`):

| skeleton | sibling CX / rot | ours CX / rot | sibling T (archive `gate_counts.t`) | ours $T_{\rm total}$ at $\beta=1$ | ours Qiskit CT |
|---|---|---|---|---|---|
| pairs9 | 34 / 9 | 34 / 9 | 600 (= `rotation_T` 576 + 24 fixed; `synthesis.rotation_T`=576, 9 rot) | **600** (576 + 24) | 576 |
| flags4 | 44 / 4 | 44 / 4 | 290 (their docstring: rotation T 248 at $\alpha=2$, + 48 fixed = 296) | **296** (248 + 48) | 289 |
| flags5 | 42 / 5 | 42 / 5 | 352 | **352** | 346 |
| flags6 | 36 / 6 | 36 / 6 | 416 | **416** | 401 |

Three of four equal the sibling exactly, flags4 equals the sibling's own docstring (248 rotation T) and is 6 above the archive entry 290 (guess: the archive entry is after the sibling's own post-synthesis T-cancellation; our Qiskit CT value 289 is within 1 of it). The sibling JSON's `logical_metrics.t` = 564 for pairs9 is a different metric (60 T per rotation estimate: $24+9\cdot60$); not comparable to a synthesised count. At the project's nominal $\beta=0.61$ the counts are lower/different because the angles are different (builder's table, confirmed below).

## 3. Independent physics (Aer statevector, own targets; `m3_step_3_6_verify.py`)

Method as in report 102: Aer statevector (not the library sparse engine), 47 inner codes on the no-outer circuit (8 data + 3 ancillas = 11 qubits) assembled to the $433\times433$ matrix $W$; additionally the **with-outer** circuit (8 + 8 + 3 = 19 qubits) run directly on **all 433** inputs (chunks of 20). Error $=\lVert W-e^{i\varphi}V\rVert_2$, $V=\exp(-i\beta H_B)$ from `enc.h_magnetic()` (route B). Gauss residual from my own corner operators on route-A decoded vectors (floor $1.1\times10^{-15}$). Dirty = max ancilla$\neq0$ probability.

| circuit | β | error vs route B | leak | dirty | Gauss | unitarity | tol | verdict |
|---|---|---|---|---|---|---|---|---|
| pairs9 | 0.23 / 0.61 / 1.0 | 1.76e-15 / 1.73e-15 / 1.72e-15 | ≤ 8.1e-16 | ≤ 2.4e-31 | 1.1e-15 | ≤ 3.7e-15 | 1e-10 | PASS |
| flags4 | 0.23 / 0.61 / 1.0 | 3.34e-15 / 3.29e-15 / 3.39e-15 | ≤ 1.6e-15 | ≤ 4.3e-31 | 1.1e-15 | ≤ 6.7e-15 | 1e-10 | PASS |
| flags5 | 0.23 / 0.61 / 1.0 | 2.54e-15 / 2.61e-15 / 2.87e-15 | ≤ 9.7e-16 | ≤ 4.7e-31 | 1.1e-15 | ≤ 5.1e-15 | 1e-10 | PASS |
| flags6 | 0.23 / 0.61 / 1.0 | 2.07e-15 / 1.98e-15 / 2.20e-15 | ≤ 8.1e-16 | ≤ 4.6e-31 | 1.1e-15 | ≤ 4.3e-15 | 1e-10 | PASS |
| with outer, 19 qubits, all 433 inputs, β = 0.61: pairs9 / flags4 / flags5 / flags6 | | 1.68e-15 / 3.34e-15 / 2.68e-15 / 2.03e-15 | ≤ 1.1e-15 | ≤ 4.7e-31 | 1.1e-15 | ≤ 6.7e-15 | 1e-10 | PASS |
| outer qubits 8..15 touched | none | none (all four) | | | | | | PASS |
| with-outer vs no-outer matrix, max entry deviation | 0 | 4.4e-16 / 9.0e-16 / 6.7e-16 / 6.9e-16 | | | | | 1e-12 | PASS |
| route A: `gauge_align` residual (circuit vs `exact.operators.target`, β = 0.61); gauge $D=$ `enc.gauge` | ≤ 1e-10 | 1.6e-15 / 3.0e-15 / 2.5e-15 / 2.1e-15; D equals `enc.gauge`: True ×4 (ungauged route-A error 1.146, i.e. the gauge matters) | | | | | 1e-10 | PASS |
| negative control: circuit built at $-\beta$ vs target $+\beta$ (pairs9, flags4) | rejected | 1.878, 1.878 (also $-\beta$ target at 0.23/0.61/1.0 gives 0.89/1.88/1.82; target at $\beta/2$ gives 0.23/0.60/0.96) | | | | | > 0.1 | PASS |
| negative control: one step dropped from the pairs9 walk | rejected | `build_walk` refuses: "skeleton does not reproduce the coupling table: residual 9.78e-01" (no silent wrong circuit) | | | | | | PASS |

## 4. T(ε) re-count (`m3_step_3_6_tcount.py`)

Own $T_{\rm fixed}$ from the expanded gate list (RCCX 4 T, RC3X 8 T, counted from the Qiskit definitions, not from `logical_metrics`), own call of `pygridsynth.gridsynth.gridsynth_gates` for every rotation angle of the β = 0.61 circuit with an independent $2\times2$ word-error check (every word error ≤ ε).

| skeleton (β = 0.61) | $T_{\rm fixed}$ own / lib | ε | own $T_{\rm rot}$ | own $T_{\rm total}$ | lib $T_{\rm total}$ | Qiskit CT $T$ | Qiskit vs total | max word error |
|---|---|---|---|---|---|---|---|---|
| pairs9 | 24 / 24 | 1e-4 / 1e-6 / 1e-8 / 1e-10 | 384 / 552 / 750 / 936 | 408 / 576 / 774 / 960 | 408 / 576 / 774 / 960 | 390 / 570 / 746 / 939 | −4.4 % / −1.0 % / −3.6 % / −2.2 % | 4.1e-5 / 4.3e-7 / 4.8e-9 / 5.0e-11 |
| flags4 | 48 / 48 | same | 174 / 250 / 338 / 416 | 222 / 298 / 386 / 464 | 222 / 298 / 386 / 464 | 215 / 290 / 374 / 451 | −3.2 % / −2.7 % / −3.1 % / −2.8 % | 4.8e-5 / 4.9e-7 / 3.8e-9 / 4.4e-11 |
| flags5 | 40 / 40 | same | 212 / 310 / 420 / 520 | 252 / 350 / 460 / 560 | equal | 244 / 343 / 444 / 548 | −3.2 % / −2.0 % / −3.5 % / −2.1 % | ≤ 4.4e-5 … 4.3e-11 |
| flags6 | 32 / 32 | same | 256 / 370 / 502 / 626 | 288 / 402 / 534 / 658 | equal | 277 / 397 / 513 / 640 | −3.8 % / −1.2 % / −3.9 % / −2.7 % | ≤ 4.6e-5 … 4.6e-11 |

All own totals equal the library's `t_table` for every skeleton and ε (builder's table pairs9 408/576/774/960 and flags4 222/298/386/464 reproduced exactly). Qiskit CT (library call, seed 12345) is within the 10 % band everywhere (worst −4.4 %); my own independent Qiskit calls (seed 7 level 3; seed 11 level 1; pairs9 and flags4, ε = 1e-4, 1e-6) give identical T (390/570 and 215/290) and CX 34/44, so the cross-check is not seed dependent. Qiskit CX after CT = logical CX (34, 44, 42, 36). Leading-term estimate $t_{\rm est}=t_{\rm fixed}+3\,n_{\rm rot}\log_2(1/\varepsilon)$ is 1–6 % below the exact count (e.g. pairs9 ε = 1e-6: 562.2 vs 576), consistent with the Ross–Selinger band the T1 test enforces.

## 5. Synthesised circuits and the certified bound (`m3_step_3_6_synth.py`)

Synthesis by `synthesize(qc, ε)`; verification by my own Aer run on the synthesised circuit (no sparse engine) and by the library `evaluate(..., **synth_tolerances(n_rot, ε))`. Rule: $\text{op\_norm\_error}=\text{block}+\text{leak}+\text{prune}\le N_{\rm rot}\varepsilon+10^{-9}$ (Gauss residual under the same cap).

| circuit | ε | $N_{\rm rot}$ | my block | my leak | my block+leak | lib op_norm_error (block + leak + prune) | bound $N_{\rm rot}\varepsilon$ | tol (+1e-9) | my Gauss | T in circuit = table | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pairs9 | 1e-4 | 9 | 1.95e-4 | 1.47e-4 | 3.41e-4 | 3.41e-4 | 9.0e-4 | 9.000001e-4 | 1.1e-15 | 408 = 408 | PASS |
| pairs9 | 1e-6 | 9 | 2.53e-6 | 1.40e-6 | **3.93e-6** | 3.93e-6 | 9.0e-6 | 9.001e-6 | 1.1e-15 | 576 = 576 | PASS |
| pairs9 | 1e-8 | 9 | 1.73e-8 | 1.86e-8 | 3.59e-8 | 3.59e-8 | 9.0e-8 | 9.1e-8 | 1.1e-15 | 774 = 774 | PASS |
| flags4 | 1e-4 | 4 | 1.22e-4 | 6.0e-5 | 1.82e-4 | 1.82e-4 | 4.0e-4 | 4.000001e-4 | 1.1e-15 | 222 = 222 | PASS |
| flags4 | 1e-6 | 4 | 8.84e-7 | 5.15e-7 | **1.40e-6** | 1.40e-6 | 4.0e-6 | 4.001e-6 | 1.1e-15 | 298 = 298 | PASS |
| flags4 | 1e-8 | 4 | 8.58e-9 | 6.81e-9 | 1.54e-8 | 1.54e-8 | 4.0e-8 | 4.1e-8 | 1.1e-15 | 386 = 386 | PASS |
| flags5 | 1e-6 | 5 | 2.09e-6 | 3.4e-7 | 2.43e-6 | 2.43e-6 | 5.0e-6 | 5.001e-6 | 1.1e-15 | 350 = 350 | PASS |
| flags6 | 1e-6 | 6 | 2.08e-6 | 9.3e-7 | 3.00e-6 | 3.00e-6 | 6.0e-6 | 6.001e-6 | 1.1e-15 | 402 = 402 | PASS |

In all 8 cases: library `op_norm_error` equals block + leak + prune to $\le10^{-12}$ (prune $\le4.5\times10^{-15}$, i.e. sparse engine exact), `certified=True`, engine `sparse`, library block/leak agree with my Aer values to $\le10^{-14}$ relative; my block error $\le$ sum of measured per-word errors (triangle inequality: e.g. pairs9 1e-6: 2.53e-6 ≤ 3.75e-6); gate set after synthesis ⊂ {cx, h, s, t, tdg, x}; dirty ancilla $\le6.4\times10^{-31}$. The builder's figures (pairs9 3.9e-6 ≤ 9e-6; flags4 1.4e-6 ≤ 4e-6) are reproduced. Synthesised with-outer circuits through the library `physical` evaluator (all 433 states, Gauss on): pairs9 ε = 1e-6 error 3.93e-6, Gauss 5.5e-16, `outer_bits_read` 0, ok; flags4 error 1.40e-6, Gauss 5.5e-16, `outer_bits_read` 0, ok.

## 6. Hygiene

| check | result |
|---|---|
| `git status --short` (tracked) | modified: `src/su2plaq/circuits/spinnet.py`, `src/su2plaq/spinnet/trotter_v2.py`, `src/su2plaq/spinnet/walk.py`; new `tests/unit/test_spinnet_trotter_v2_unit.py`. All track-S files; no laptop-owned file, no `tests/acceptance/`, no `docs/`, no `notes/` modified. The `trotter_v2.py` and `walk.py` files are the track's own spin-network modules. PASS |
| su2qc-trotter imported by production code or tests | no: `grep su2trotter src tests` only finds the string in the `SOURCE` text and docstring; `trotter_v2.py` imports only `su2plaq.spinnet.walk`. The import occurs only in my tester script. PASS |
| silent exception catching in the new/changed code | none (`grep except/try` in the diff and in `trotter_v2.py`, unit test: no matches); invalid skeleton raises `ValueError`; non-representable skeleton raises with the residual. PASS |
| hard-coded expected numbers in source | none: rotation angles are solved from K by `solve_angles` (`metadata.angles` / `angle_fractions` come from the solve); the CX/rotation counts 34/9, 44/4 etc. appear only in tests. Only structure (frames, step lists, wire numbers) is vendored. PASS |
| `tools/check_lock.py`, `acceptance-check` | `LOCK OK`, `PASS ... acceptance-v7`. PASS |

## Failures / problems

None. Notes (not failures):
1. Sibling flags4 archive T = 290 vs our $\beta=1$ count 296 (= sibling's own docstring 248 + 48): 6 T difference only for flags4; guess: the sibling's archive value is after its own post-synthesis T-cancellation pass. Other three skeletons match exactly (600, 352, 416).
2. The sibling's `logical_metrics.t` (564, 804, ...) uses 60 T per rotation and must not be quoted next to synthesised counts.
3. The remaining m3 failures are exactly the planned later steps: L1–L3 (Lean, steps 3.L1–3.L3) and R1 ×3 (results files, step 3.7).
4. Pending (carried over): METHODS-spinnet §3 fallback-decode wording; laptop-owned flaky `test_results_unit` (not triggered this run: 272/272).

## Verdict

**PASS.** m3 acceptance 18 passed / 6 pending (L1–L3, R1 ×3) / 0 new failures; unit 272/272; m0+m1 not-slow 54/54; collection 126; lock + acceptance-check PASS. All four skeletons agree with the sibling source gate for gate; exact to $\le3.4\times10^{-15}$ on all 433 states (also with the outer register, 19 qubits); synthesised circuits are certified with $\text{block}+\text{leak}+\text{prune}\le N_{\rm rot}\varepsilon$.
