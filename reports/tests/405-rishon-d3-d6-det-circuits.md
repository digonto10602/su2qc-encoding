# Tester report 405 — rishon steps D3 (det circuits), D4 (sector structure, observables), D5 (outer det row), D6 (script only) and the two report-222 fixes

Date: 2026-11-11 · Git commit: HEAD was `5d5d502` when I started and is `0dfe4ae` now; the builder changes for D3–D6 are **uncommitted** in the working tree (my raw-number files record the commit at run time) · Prompt in force: `prompts/204-rishon-det-term-amendment.md` (acceptance-v18), methods `docs/METHODS-rishon.md` R13–R16 · Mode: **step** · Track R (rishon) · Cores 6–11 (`-n 5/6`, one core for my own scripts)
Related: `reports/tests/222-rishon-d1-d2-prune-cap-det-operators.md` (previous rishon tester), `reports/research/203-rishon-det-term-prune-cap.md`.

Symbols (prompts/204 §2.1): $\lambda_D$ = coefficient of the det term in $H$, $\eta=\lambda_D\,dt$ = angle of the det layer. $U_1=U_BU_DU_E$, $U_2=U_E(\tfrac\alpha2)U_D(\tfrac\eta2)U_BU_D(\tfrac\eta2)U_E(\tfrac\alpha2)$. "own" = my code in `results/rishon/tester-223-*.py` (own Jordan–Wigner (JW) link algebra, own gate simulators), production imported only to build circuits or to compare afterwards.

## 0. Verdict

**PASS** for D3, D4, D5 and the D6 script, and for both report-222 fixes. 74 passed / 12 failed in the rishon acceptance run (m5, m5x, m6, not slow); all 12 failures are `PENDING:` messages for steps that are not built yet (D6 result files, C1 `three_layer`/`replay`, 6.L2/C4 Lean). Unit suite 932 passed. Every independent number agrees with production to $\le 2\times10^{-14}$ (circuits) or $\le 1.7\times10^{-15}$ (observables); all 11 mutants were caught.

Points to know (none blocks):
1. `leaving_weight` $=2.328\times10^{-10}$ is a float-cancellation artefact: it is exactly $2^{-32}$ (a quantisation step of a $\sim10^{6}$-sized sum). Computed from the residual it is $\le1.6\times10^{-25}$ (§4). Passes the locked bound $10^{-9}$.
2. `_rejudge` rejects NaN and $+\infty$ everywhere, but still accepts $-\infty$ in `leak_amplitude`/`op_norm_error` (impossible values: norms are non-negative). Recorded only.
3. Unit test coverage gap (acceptance catches it): the mutant "det layer after $U_B$ in `build_step`" is caught by the unit test only for order 2, not order 1; acceptance `DT4_three_layer_step[1]` catches it.
4. `compress/lean/structure.json` and `src/su2plaq/lean/structure.py`, `src/su2plaq/lsh/lean_export.py` changed during my session. These are other agents' work (not rishon, not me; the guard hook blocks me from editing `src/`). Not under `src/su2plaq/evaluate` or `src/su2plaq/compress`.

## 1. Commands run

```
source ~/miniforge3/etc/profile.d/conda.sh && conda activate coding; cd /home/digimonk/Projects/su2qc-encoding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected "_emit_ud" / "_rejudge" / "build_step"
taskset -c 6-10 tools/pytest-safe -n 5 -m "not slow" -q -rfEs --junitxml=... tests/acceptance/m5 tests/acceptance/m5x tests/acceptance/m6     # 1198.8 s
taskset -c 6-11 tools/pytest-safe -n 6 -q tests/unit                                                                                     # 282.9 s
taskset -c 6-10 tools/pytest-safe -n 5 -m "not slow" -q tests/acceptance/{m0,m1,m2,m2c,m3,m3x,m4}                                         # 129 s
PYTHONPATH=src taskset -c 11 tools/run-capped python results/rishon/tester-223-{det-circuits,step-orders,sector-structure,outer-row-and-prepend,det-metrics,observables,rejudge-nan}.py
mutants: results/rishon/tester-223-mutant-run_one.sh <mutant> <core> <test ids>  (plugin results/rishon/tester-223-mutant-plugin.py, env MUT223=<name>)
PYTHONPATH=src taskset -c 11 tools/run-capped python scripts/m5_det_results.py --quick --out <scratch dir>                                  # schema/run check only
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
```
Raw numbers: `results/rishon/tester-223-*.json` (random seed `20261110` everywhere; production's own Gauss sample seed `20261104`).

## 2. Acceptance and unit results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| `M5_DT4_det_layer_circuit` ×3 (η 0.29, 0.53, 1.07) | green | pass (45 / 70 / 66 s) | locked | PASS |
| `M5_DT4_three_layer_step` ×2 (orders 1, 2) | green | pass (196 / 218 s) | locked | PASS |
| `M5_DT4_physical_cross_check_and_compose` | green | pass (75 s) | locked | PASS |
| `M5_DT5_sector_structure_with_det` | green | pass (6 s) | integers exact; leaving $\le10^{-9}$ | PASS |
| `M5_DT6_observables_with_det` ×3, `M5_DT6_closed_spectrum_with_det` | green | pass | $10^{-10}$ | PASS |
| `M5X_O2_outer_det_row_certified` | green | pass (9 s) | $\le10^{-10}$ | PASS |
| earlier greens: `M5_DT1–DT3`, `M5_V2`, `M6_K2`, `M5_S1`, `M5_B1`, `M5_E1`, `M5_O1`, `M5X_O1`, `M5_T1[UB]` (989 s), `M6_E3`, `M6_G4`, `M6_R2`, … | green | all pass: **74 passed** of 86 | locked | PASS |
| `M5_DT7` ×4 (`UD`, `step3`, `step3_order2`, `observables_det`), `M5X_O2_..._results_file` | PENDING (D6 files) | `PENDING: missing results/rishon/{UD,step3,step3_order2,observables_det,UD_outer_row_certified}.json` | — | PENDING (expected) |
| `M6_H3`, `M6_H4`, `M6_G6` (C1 `three_layer`), `M6_G5` (C1 `replay`) | PENDING | `PENDING: cannot import ...three_layer / ...replay` | — | PENDING (expected) |
| `M6_L2`, `M6_L3` (Laurent3.lean, 6.L2), `M6_L9` (`recognise_angle_single`, C4) | PENDING | `PENDING: ... missing` | — | PENDING (expected) |
| slow `M6_G1`, `M6_S3`, `M5_T1[step]`, `M6_H1/H2` | not run (mode step, `-m "not slow"`) | — | — | not run (C2 / milestone gate) |
| unit suite `tests/unit` | all green | **932 passed** (222 had 909) | — | PASS |
| regression m0, m1, m2, m3, m3x, m4 (not slow) | green | **133 passed**, 0 failed | locked | PASS |
| m2c (`prompts/008` consolidation, acceptance-v18, unbuilt) | PENDING | 18 failures, every one `PENDING: ... encodings.registry / compress.replay / Verdict has no span_leak ...` | — | PENDING (expected) |
| `pytest --collect-only -q tests/acceptance` | clean | 341 tests, no error | — | PASS |
| `python tools/check_lock.py` | LOCK OK | LOCK OK | — | PASS |
| `~/.claude/bin/acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v18` | — | PASS |

No new failures versus report 222 (its 25 failures: 13 are now green — DT4 ×6, DT5, DT6 ×4, O2 certificate, G4 — and the 12 left are all PENDING-only; G4 now passes because `summary.json` has the headline from my earlier `robust report`).

## 3. Independent checks

Own construction in every script: JW modes $c_k=\big(\prod_{m<k}Z_m\big)\sigma^-_k$ (link qubits $L_1L_2R_1R_2$, codes $A=3$, $B=12$, sector $[3,5,6,9,10,12]$), $\det U=U_{11}U_{22}-U_{12}U_{21}$, $H_D^{\rm in}=\sum_{\ell\le4}(\det U_\ell+{\rm h.c.})$, $H_B$, $H_E$ as in report 222.

### 3.1 (a) Det-layer circuit vs the own target on all 1296 inner codes (`tester-223-det-circuits.py`, own numpy gate applier for h/cx/rz on the full 16-qubit space; Qiskit `Operator` not used; applier self-test against dense matrices: 0 deviation)

| η | gate counts (`count_ops`) | rz angle | max amplitude error vs own $e^{-i\eta H_D^{\rm in}}$ (1296 columns, all 65536 amplitudes) | weight on invalid codes | fitted global phase | sign-flipped target distance | PASS |
|---|---|---|---|---|---|---|---|
| 0.29 | cx 32, h 16, rz 8 | 0.58 = 2η | $1.3\times10^{-15}$ | 0 | $1+0i$ (spread 0) | 0.917 | yes |
| 0.53 | cx 32, h 16, rz 8 | 1.06 = 2η | $1.4\times10^{-15}$ | 0 | $1-10^{-16}$ | 0.853 | yes |
| 1.07 | cx 32, h 16, rz 8 | 2.14 = 2η | $1.2\times10^{-15}$ | 0 | $1+0i$ | 0.908 | yes |

Claim check: per link 8 CX, 2 rotations $\mathrm{rz}(2\eta)$, 4 H, no ancilla (16 qubits, register `d`), gates $\subset\{h,cx,rz\}$, `global_phase` attribute 0: **confirmed**. Closed form of $U_D$ vs eigh of the 1296-dim $H_D^{\rm in}$: $\le4.0\times10^{-15}$.

### 3.2 (b) Three-layer step circuits vs own composition and Trotter slopes (`tester-223-step-orders.py`, own sparse simulator for the full 26-qubit circuits incl. ancillas; inputs: $|{\rm vac}_A\rangle$ and 40 seeded random valid codes)

| $(\alpha,\beta,\eta)$ | order | max amp error vs own $U$ (41 columns) | max col. 2-norm error | ancilla leak | invalid-code weight | distance to the wrong order $U_EU_DU_B$ | distance to the no-det step | PASS |
|---|---|---|---|---|---|---|---|---|
| (0.37, 0.61, 0.29) | 1 | $1.4\times10^{-14}$ | $1.6\times10^{-14}$ | 0 | 0 | 1.14 | 1.01 | yes |
| (0.37, 0.61, 0.29) | 2 | $1.7\times10^{-14}$ | $2.2\times10^{-14}$ | 0 | 0 | — | 0.86 | yes |
| (0.91, 0.23, 0.53) | 1 | $1.6\times10^{-14}$ | $1.7\times10^{-14}$ | 0 | 0 | 1.16 | 1.37 | yes |
| (0.91, 0.23, 0.53) | 2 | $1.5\times10^{-14}$ | $1.8\times10^{-14}$ | 0 | 0 | — | 1.36 | yes |
| (1.70, 1.00, 1.07) | 1 | $1.4\times10^{-14}$ | $1.7\times10^{-14}$ | 0 | 0 | 1.34 | 2.00 | yes |
| (1.70, 1.00, 1.07) | 2 | $1.6\times10^{-14}$ | $1.9\times10^{-14}$ | 0 | 0 | — | 2.00 | yes |

(own simulator pruned amplitudes below $10^{-15}$: dropped 2-norm $\le1.7\times10^{-15}$.) `build_step(eta=None)`, orders 1 and 2: $\le1.5\times10^{-14}$ from the own two-layer composition.
Order 1 = electric, det, magnetic; order 2 = half-angle det gadgets on both sides of $U_B$ — confirmed by the two-circuit separations above (the other order is $\ge0.39$ away).

Trotter slopes from the **circuit columns** (distance to exact $e^{-i\,dt\,H}$, $g^2=1.1014$, $\lambda_D=0.4316$, $\alpha=g^2dt/2$, $\beta=dt/g^2$, $\eta=\lambda_D dt$, max over the 41 inputs):

| order | dt = 0.1 | 0.05 | 0.025 | 0.0125 | slope 0.05→0.025 | slope 0.025→0.0125 | expected | result |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.02949 | 0.007467 | 0.001873 | 0.0004686 | 1.9953 | 1.9988 | 2 ± 0.05 | PASS |
| 2 | 0.005628 | 0.0007195 | 9.045e-5 | 1.132e-5 | 2.9919 | 2.9980 | 3 ± 0.05 | PASS |

### 3.3 `eta=None` against HEAD, `prepend_det_layer`, outer det row (`tester-223-outer-row-and-prepend.py`)

| check | expected | got | tol | result |
|---|---|---|---|---|
| `build_step(eta=None)` vs HEAD's `circuits/rishon.py` (loaded via `git show HEAD:...`): instruction list (name, qubits, params), global phase, metadata, registers — 48 circuits ({4 angle pairs} × orders 1, 2 × ladders ccx/rccx/mcx × with/without outer); also `eta=None` keyword explicit | identical | **48/48 identical**; `build_UE` ×2, `build_UB` ×4 identical | exact | PASS |
| `prepend_det_layer(build_step(α,β,1), η)` vs own $U_BU_DU_E$ (41 columns, 3 triples) | equal | $1.5\times10^{-14}$, $1.5\times10^{-14}$, $1.5\times10^{-14}$; wrong order $U_DU_BU_E$ is 0.53 / 0.39 / 0.77 away; leak 0; +32 CX, +8 rz, +16 H; unit instructions preserved in order; registers `d[16]`, `anc[10]` | $10^{-10}$ | PASS |
| `prepend_det_layer` on a unit whose first register is not `d[16]` (`d[15]`, `x[16]`) | `ValueError` | `ValueError` ×2 | — | PASS |
| outer det row (`build_UD(η, with_outer=True, include_outer_det=True)`): qubits, counts | 48 qubits, 96 CX, 24 rz | 48, `{cx 96, h 48, rz 24}`; every gate on a single link (0 cross-link gates) | exact | PASS |
| outer row vs own tensor-product target (24 seeded random products of sector codes on 12 links) | equal | $3.4\times10^{-15}$ (η 0.29), $4.0\times10^{-15}$ (0.53), $2.3\times10^{-15}$ (1.07) | $10^{-10}$ | PASS |
| `outer_det_certify` bound, 12 links | $\le10^{-10}$; builder: $4.0\times10^{-15}$ | $3.997\times10^{-15}$ (0.29), $3.997\times10^{-15}$ (0.53), $4.39\times10^{-15}$ (1.07); certified, 12 links | $10^{-10}$ | PASS |

### 3.4 Det-layer cost and production verdict (`tester-223-det-metrics.py`; own T count: `pygridsynth.gridsynth_gates` called directly, word error recomputed with own $H,S,T,X,W$ matrices)

| check | expected (builder) | got | tol | result |
|---|---|---|---|---|
| $T(\varepsilon=10^{-6})$ of `build_UD(0.29)` = 8 × T per rz(0.58) | 496 | 62 per rotation, **496** (word error $4.9\times10^{-7}\le10^{-6}$); η = 0.53: 496; η = 1.07: 512 | exact | PASS |
| η-set of 20 (seed 20261110, uniform(0.05, 1.2)) | mean 500.8, range 480–512 | mean 500.8, 480–512 | exact | PASS |
| `verify(build_UD(η), "UD", eta=η)` η = 0.29 | ok, certified, `op_norm_error` 2.8e-15, Gauss 2.1e-16 | ok, certified, **2.756e-15**, **2.15e-16** (inner block, 273 Gauss states, 0 outer bits read) | $10^{-10}$ | PASS |
| same, η = 0.53 / 1.07 | — | $4.60\times10^{-15}$, $1.96\times10^{-16}$ / $4.12\times10^{-15}$, $1.96\times10^{-16}$ | $10^{-10}$ | PASS |
| depth (Qiskit) | 10 | 10 | exact | PASS |

### 3.5 (c) Sector structure, my own way (`tester-223-sector-structure.py`; production only for the physical basis: 38 432 states with their 48-bit codes and amplitudes, and the U(1) corner charges)

$H_B$ built from my own 1296-dim JW operator applied to the inner 16 bits of every code; det of link $\ell$ = nibble flip $A\leftrightarrow B$ with amplitude 2 (taken from my own $\det U$: single non-zero entry $(12,3)=+2$); matrices $P^\dagger T P$ on the 352 016 distinct codes; blocks = connected components (thresholds $10^{-9}$, $10^{-12}$, $10^{-14}$ all give the same counts).

| quantity | expected (plan) | own | production `det_sector_structure` | result |
|---|---|---|---|---|
| dim, U(1) sectors | 38 432, 431 | 38 432, 431 | same | PASS |
| blocks $\lambda_D=0$ / inner det / all 12 links | 31 870 / 4 976 / 305 | 31 870 / 4 976 / 305 (block sizes at $\lambda_D=0$: 25 933×1, 5 312×2, 625×3) | same | PASS |
| largest block | 3 / 17 / 4 352 | 3 / 17 / 4 352 | same | PASS |
| reference block dim (vac$_A$) | 3 / 17 / 4 352 | 3 / 17 / 4 352 | same | PASS |
| reference block U(1) sectors | 1 / 15 / 431 | 1 / 15 / 431 | same | PASS |
| charge-change rank | 0 / 3 / 4 | 0 / 3 / 4 (8 inner changes of pattern $\{\pm2,\mp2,0,0\}$, 8 outer changes of pattern $\{\pm2,0,0,0\}$, $H_B$: only $(0,0,0,0)$) | same | PASS |
| outer det row commutes with $H_B$ and with the inner det terms (physical space) | 0 | $5.3\times10^{-15}$, $0$; inner det vs $H_B$: 8.0 | $10^{-12}$ | PASS |
| Gram of the basis | identity | max deviation $8.0\times10^{-15}$ | — | PASS |

**`leaving_weight` — is $2.3\times10^{-10}$ just float cancellation? Yes.** Production returns $2.3283064365386963\times10^{-10}=2^{-32}$ exactly (it computes $\sum|TP|^2-\sum|P^\dagger TP|^2$, a difference of two sums of size $\sim10^6$; one rounding quantum of such a sum is $\sim10^{-10}$). The same quantity computed from the residual $R=TP-P(P^\dagger TP)$, $\|R\|_F^2$ summed entrywise: $H_B$ $9.9\times10^{-27}$, each of the 12 det terms $\le6\times10^{-26}$ (largest single residual entry $7.8\times10^{-16}$), inner det sum $6.1\times10^{-26}$, outer det sum $1.6\times10^{-25}$, i.e. **$\le1.6\times10^{-25}$**: the Gauss space is invariant to machine precision. The plan's "$\le6\times10^{-11}$" was the same artefact on another run; the locked bound $10^{-9}$ is fine. Suggestion (non-blocking): return the residual form so the number reads $10^{-25}$ instead of a rounding quantum.

### 3.6 Observables and closed spectra (`tester-223-observables.py`)

Own $U_1=U_BU_DU_E$ on the 1296-dim space, from $|{\rm vac}_A\rangle$: $E_{\rm link}=\tfrac14\langle H_E\rangle$, $P=-\tfrac12\langle H_B\rangle$, echo $=|\langle{\rm vac}_A|U^n|{\rm vac}_A\rangle|^2$, $n=1,2$, three triples: max deviation from `observables(eta=)`: **$1.7\times10^{-15}$**; $P(1)=0$ exactly; `eta=None` identical to the M5 result, `eta=0.0` deviation 0, KS rows unchanged. Closed spectra $g^2\in\{0.5,1,2\}\times\lambda_D\in\{0,0.2,0.5\}$ against my own 17-dim block (invariance defect 0.0): max deviation $1.4\times10^{-14}$; zero levels 15 at $\lambda_D=0$, **5** at $\lambda_D=0.2,0.5$ (plan: 15 → 5); `closed_spectra(lam_d=0.0)` identical to the default.

### 3.7 `_rejudge` NaN / $\infty$ (`tester-223-rejudge-nan.py`, faked shared `pruning_bound` verdict through `verify`; plus `_rejudge` called directly)

| input | expected | got | result |
|---|---|---|---|
| `dropped_total` NaN, $+\infty$ | `pruning_bound` | `pruning_bound` | PASS |
| `leak_amplitude` NaN, $+\infty$ | `leak`/`dirty_ancilla` | `leak`/`dirty_ancilla` | PASS |
| `op_norm_error` NaN, $+\infty$ | `error` | `error` | PASS |
| pairs (NaN, $+\infty$)² | rejected | rejected | PASS |
| `leak_amplitude` $=-\infty$, `op_norm_error` $=-\infty$ | (impossible values) | accepted as `ok` | recorded, not counted (a norm cannot be negative) |
| equality with the bounds ($10^{-11}$, $10^{-10}$, $10^{-10}$) | accepted ($\le$, as in the shared cascade) | accepted | PASS |
| mutation: HEAD's `_rejudge` put back | caught | the three NaN unit tests fail (`test_rejudge_rejects_non_finite[nan-*]`) | PASS |

### 3.8 Report-222 fix: spec sentence from measured constants

`compress/specs/rishon-step.md` equals `render_spec(rishon_spec("step"))` byte for byte; the sentence now reads "…measure `dropped_total` 2.7e-12 to 3.8e-12, i.e. about 2450 to 3450 branching gates at that rate". The constants `PRUNE_SEEDS_MEASURED` (2.7e-12, 2.9e-12, 3.8e-12) match `results/compress/rishon/round-000.json` (2.6949e-12, 2.9148e-12, 3.7884e-12) and $2.7\times10^{-12}/1.1\times10^{-15}=2455\to2450$, $3.8\times10^{-12}/1.1\times10^{-15}=3455\to3450$. They are typed constants with a provenance comment, not read from the round file at run time (non-blocking). `1e-12` occurs 0 times in `rishon-step.md` and `rishon-structure.json`.

## 4. Mutants (`tester-223-mutants.json`; in-process monkeypatch plugin, `src/` never edited, all mutants reverted by construction: they live in the pytest process only)

Each mutant ran `tests/unit/test_rishon_det_unit.py` plus the named acceptance ids.

| mutant | caught by | result |
|---|---|---|
| `rz(-2η)` (wrong sign) | unit `det_layer_exact…wrong_sign_rejected`, `outer_det_certify_basic`; acceptance `DT4_det_layer_circuit[0.29]` | CAUGHT |
| `rz(η)` instead of `rz(2η)` | same three | CAUGHT |
| missing `h(R1)` | same three | CAUGHT |
| wrong link wiring (`cx(L2,R1)` takes the next link's $L_2$) | same three | CAUGHT |
| det layer drops the last link | unit `build_UD_counts…`, `det_layer_exact…`, `outer_det_certify_basic`; acceptance `DT4_det_layer_circuit[0.29]` | CAUGHT |
| outer links get $\mathrm{rz}$ sign flipped (inner links correct) | unit `outer_det_certify_basic`; acceptance `M5X_O2_outer_det_row_certified`; `DT4_det_layer_circuit[0.29]` correctly still passes | CAUGHT |
| det layer placed after $U_B$ in `build_step` | acceptance `DT4_three_layer_step[1]`; unit `build_step_eta_structure[2]` only (**order-1 unit test passes: gap**) | CAUGHT (acceptance) |
| order 2 uses the full angle $\eta$ instead of $\eta/2$ | acceptance `DT4_three_layer_step[2]`; unit `build_step_eta_structure[2]` | CAUGHT |
| `prepend_det_layer` appends the det layer after the unit | acceptance `DT4_physical_cross_check_and_compose`; unit `prepend_det_layer` | CAUGHT |
| HEAD's `_rejudge` (NaN comparisons false) | unit ×3 | CAUGHT |
| `outer_det_certify` against $-\eta$ | unit `outer_det_certify_basic`; acceptance `M5X_O2_outer_det_row_certified` | CAUGHT |

NaN cases at circuit level: not applicable (angles are floats from the caller); NaN in the verdict is §3.7.

## 5. Shared code, hashes, files

| check | expected | got | result |
|---|---|---|---|
| `git diff HEAD -- src/su2plaq/evaluate src/su2plaq/compress` | empty | empty (0 lines) | PASS |
| shared `provenance.code_hash()` | `0bd7e7d9…` | `0bd7e7d9` (computed twice, at start and end) | PASS |
| `rishon_spec("step").sha256()` | `bb0b575b…` | `bb0b575b` | PASS |
| `compress/specs/rishon-structure.json` | byte-identical | `git diff HEAD` empty | PASS |
| rishon evaluator hash `su2plaq.rishon.compress.code_hash()` | changes (spec.py, verify.py are hashed) | `055b2107…` (was `ddb440ad…` at report 222; stored in `results/compress/rishon/robust.json` → stale until replay C2, as planned) | as planned |
| `src/` tracked by me | not touched | my files changed nothing in `src/`; two lean/LSH files changed meanwhile by other agents (see §0.4) | n/a |
| `scripts/m5_det_results.py --quick` (schema run to a scratch directory) | runs | wrote `UD`, `step3`, `UD_outer_row_certified` (bound $3.997\times10^{-15}$, certified), `observables_det` (.json/.qpy/.qasm3) in ~1.5 min; full run (30–40 min) left to the coordinator's clean-worktree run | PASS (D6 script only) |

## 6. Files touched by my runs
New (mine): `results/rishon/tester-223-*` (7 scripts + JSONs, `-mutants.json`, `-mutant-plugin.py`, `-mutant-run_one.sh`, `-acceptance-junit.json`), this report. Tests rewrote `results/compress/rishon/robust.json` (evaluator hash only: `ddb440ad…` → `055b2107…`; **restored with `git checkout -- results/compress/rishon/robust.json`**; its tracked content is unchanged), and byproducts under `compress/lean/structure.json` (provenance fields only: commit/exporter hash/seconds; written by the Lean-structure tests, not restored — other tracks' exporter changed too). No file in `src/`, `tests/acceptance/` or any tolerance was changed.

## 7. Failures
None. Pending list (all `PENDING:` text, 12 in m5/m5x/m6 + 18 in m2c): see §2. Guessed cause of each: step not built yet (D6 result files = coordinator run; C1 `three_layer`/`replay` modules; 6.L2/C4 Lean; prompts/008 registry and replay).
