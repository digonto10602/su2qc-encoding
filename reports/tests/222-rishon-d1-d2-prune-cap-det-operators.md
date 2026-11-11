# Tester report 222 — rishon steps D1 (prune cap 10 %) and D2 (det operators / targets)

Date: 2026-11-10 · Git commit: `6beb713` (HEAD; the D1/D2 builder changes are uncommitted in the working tree) · Prompt in force: `prompts/204-rishon-det-term-amendment.md` (acceptance-v17), research `reports/research/203`, METHODS-rishon R13–R16 · Mode: **step** · Track R (rishon) · Cores 6–13 (`-n 8`)
Related: `reports/tests/221-m6-round-004-step-6-4b.md` (previous rishon tester), `reports/research/203-rishon-det-term-prune-cap.md`.

Symbols (from prompts/204 §2.1): $\lambda_D$ = coefficient of the det term in $H$, $\eta=\lambda_D\,dt$ = angle of the det layer. Orders: $U_1=U_BU_DU_E$, $U_2=U_E(\tfrac\alpha2)U_D(\tfrac\eta2)U_BU_D(\tfrac\eta2)U_E(\tfrac\alpha2)$.

## 0. Verdict

**PASS** for D1 and D2 as defined. Every named acceptance id is green; every other new det test fails only with a `PENDING:` message; my independent numbers agree with production to $\le 6.6\times10^{-15}$. Two things differ from the briefing and are reported below (section 4): (a) `M6_G4` does **not** fail because of the evaluator hash — it fails because `summary.json` has no `headline` key until `python -m su2plaq.rishon.compress.robust report` has been run (pre-existing, independent of D1/D2; G4 is green after that command); (b) `acceptance-check` fails only because of another planner's untracked `tests/acceptance/m2c/`.

## 1. Commands run

```
source ~/miniforge3/etc/profile.d/conda.sh && conda activate coding; cd /home/digimonk/Projects/su2qc-encoding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected "verify"
taskset -c 6-13 tools/pytest-safe -n 8 -m "not slow" -q -rfEs --durations=15 --junitxml=... tests/acceptance/m5 tests/acceptance/m5x tests/acceptance/m6   # 746.7 s
taskset -c 6-13 tools/pytest-safe -n 8 -q tests/unit                                                                                          # 235.7 s
taskset -c 6-13 tools/pytest-safe -q tests/acceptance/m6/test_rishon_m6_gate.py -k G4 / -k G1 ; ... test_rishon_m6_seeds.py -k S3
PYTHONPATH=src taskset -c 6-13 tools/run-capped python -m su2plaq.rishon.compress.robust report
PYTHONPATH=src taskset -c 6-13 tools/run-capped python results/rishon/tester-222-{det-independent,closed17,rejudge-mutations,rejudge-gauss,prune-cap-ub,enc-passthrough}.py
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
```
Raw numbers: `results/rishon/tester-222-*.json` (each with `git` = `6beb713`; scripts next to them; seeds: `20261110` where random, `20261104` inside production's Gauss sample).

## 2. Acceptance results (m5, m5x, m6, not slow): 61 passed, 25 failed (all 25 explained)

| Check | Expected | Got | Tolerance | Result |
|---|---|---|---|---|
| `m5::M5_V2_rishon_prune_cap` | green | pass (156.6 s under load) | locked | PASS |
| `m6::M6_K2_structure_facts_and_spec_text` | green | pass | locked | PASS |
| `m5::M5_DT1_link_det_operator` | green | pass | $10^{-12}$ | PASS |
| `m5::M5_DT2_inner_det_hamiltonian` | green | pass (20.5 s) | $10^{-12}$ / $10^{-9}$ | PASS |
| `m5::M5_DT3_targets` × 3 triples | green | pass (52.6, 65.6, 49.9 s) | $10^{-10}$ | PASS |
| `m5::M5_DT3_trotter_orders` | green | pass (56.7 s) | slopes ±0.05 | PASS |
| `M5_DT4` ×6 (`det_layer_circuit` ×3, `three_layer_step` ×2, `physical_cross_check_and_compose`) | PENDING (step D3) | fail with `PENDING: ... build_UD / build_step(eta=...)` | — | PENDING (expected) |
| `M5_DT5`, `M5_DT6` ×4 | PENDING (step D4) | fail with `PENDING: det_sector_structure / observables(eta=) / closed_spectra(lam_d)` | — | PENDING (expected) |
| `M5_DT7` ×4 | PENDING (step D6) | `PENDING: missing results/rishon/{UD,step3,step3_order2,observables_det}.json` | — | PENDING (expected) |
| `m5x::M5X_O2` ×2 | PENDING (D3/D6) | `PENDING: build_UD`; `PENDING: UD_outer_row_certified.json missing` | — | PENDING (expected) |
| `m6::M6_H3`, `H4`, `G6`, `G5` | PENDING (step C1) | `PENDING: cannot import ...three_layer / ...replay` | — | PENDING (expected) |
| `m6::M6_L2`, `L3`, `L9` | PENDING (6.L2 / C4) | `PENDING: Laurent3.lean missing`, `recognise_angle_single` missing | — | PENDING (expected) |
| `m6::M6_G4_summary_and_budgets` | briefing: fails only on the evaluator hash | **fails on `summary["headline"]` being absent** (see §4) | locked | FAIL, not caused by D1/D2; green after `robust report` |
| `m6::M6_G1` (slow), `M6_S3` (slow) | PENDING until replay | `PENDING: the archive has not been replayed under the 10 % cap (prompts/204 step C2)` | — | PENDING (expected) |
| all other m5 / m5x / m6 not-slow tests (50 incl. `M5_T1[UB]` 663 s, `M5_S1`, `M5_B1`, `M5_E1`, `M5_O1`, `M5X_O1`, `M6_E3`, `M6_R2`, …) | pass | 61 pass in total | locked | PASS |

Unit suite: **909 passed**, 0 failed (`tests/unit`, 235.7 s). `pytest --collect-only -q tests/acceptance`: 318 tests collected, clean (313 + 5 from the untracked `m2c`). `python tools/check_lock.py`: **LOCK OK**. `git diff HEAD --stat -- tests/acceptance`: empty (no locked test touched).
`~/.claude/bin/acceptance-check`: **FAIL**, reason printed: `tests/acceptance differs from acceptance-v17 ... Untracked: tests/acceptance/m2c/test_consolidation_registry.py` — another planner's uncommitted work (prompts/008), not this step; every m5/m5x/m6 file is identical to acceptance-v17.

## 3. Independent checks (own code: `results/rishon/tester-222-*.py`; no production import until the comparison)

Own Jordan–Wigner construction: 4 modes per link, $c_k=\big(\prod_{m<k}Z_m\big)\sigma^-_k$, little-endian, codes $A=3$, $B=12$, $U_{ij}=c_{L,i}c^\dagger_{R,j}$, sector $[3,5,6,9,10,12]$, inner space = row-major $\mathrm{kron}(\text{link}_3,\dots,\text{link}_0)$; $W=\mathrm{Tr}(U_bU_rU_t^\dagger U_l^\dagger)$, $H_B=-(W+W^\dagger)$, $H_E=\tfrac34\#Q$ (Casimir evaluated from the algebra).

**3.1 The det term on one link** (`tester-222-det-independent.json`)

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| CAR of own modes | 0 | 0.0 | $10^{-14}$ | PASS |
| $\det U=U_{11}U_{22}-U_{12}U_{21}$ vs $2c_{L1}c^\dagger_{R1}c_{L2}c^\dagger_{R2}$ | equal | $0.0$ | $10^{-14}$ | PASS |
| only non-zero entry of $\det U$ | $(B\leftarrow A)=+2$ | $(12,3)=2.0$ | exact | PASS |
| $H_D^{\rm link}=\det U+\det U^\dagger$ vs $2(\lvert B\rangle\langle A\rvert+\lvert A\rangle\langle B\rvert)$ | equal | $0.0$ | $10^{-14}$ | PASS |
| eigenvalues of $H_D^{\rm link}$ (16-dim) | $+2,-2$, and 14 zeros | $\{-2,+2\}$ + 14 zeros; eigenvectors $(A\pm B)/\sqrt2$ residual 0.0; quartet codes annihilated 0.0 | $10^{-12}$ | PASS |
| $\det U$ preserves the two-rishon sector | 0 | 0.0 | $10^{-12}$ | PASS |
| $H_D^{\rm in}$ symmetric, spectrum | $\{\pm8{:}1,\pm6{:}16,\pm4{:}100,\pm2{:}304,0{:}454\}$ | identical | exact | PASS |
| production `h_det_inner()` vs own (float64, symmetric) | 0 | 0.0 (dtype float64; equals `det_term_inner()` exactly) | $10^{-12}$ | PASS |

**3.2 Sign of $\lambda_D$, commutators** (inner 1296-dim space)

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| $S=\prod_\ell e^{i\frac\pi4(n_R-n_L)_\ell}$: $SH_DS^\dagger+H_D$ | 0 | $2.4\times10^{-16}$ | $10^{-12}$ | PASS |
| $SH_ES^\dagger-H_E$, $SH_BS^\dagger-H_B$ | 0 | $1.2\times10^{-32}$, $0.0$ | $10^{-12}$ | PASS |
| spectrum $H(+\lambda_D)$ vs $H(-\lambda_D)$ at $g^2=1.1014$, $\lambda_D=0.4316$ | equal | $1.3\times10^{-14}$ | $10^{-10}$ | PASS |
| $[H_D,H_E]$ (max abs entry) | 0 exactly | 0.0 | exact | PASS |
| $\lVert[H_D,H_B]\rVert_2$ | $16\sqrt2=22.6274170$ | $22.627416997969522$ (difference $0.0$) | $10^{-9}$ | PASS |
| $H_B$ spectrum | $\pm4\sqrt2{:}1,\pm2{:}48,\pm1{:}32,0{:}1134$ | identical | exact | PASS |

**3.3 Three-layer targets and orders** — own composition with `eigh`-based exponentials (cross-checked against `scipy.linalg.expm`: $U_B$ $7.2\times10^{-15}$, $U_D$ $2.0\times10^{-15}$; closed form of $U_D$ vs expm $2.0\times10^{-15}$; $\lVert[U_D,U_E]\rVert=2.3\times10^{-15}$, $\lVert[U_D,U_B]\rVert=0.34$ at $(0.53,0.23)$, so the order matters)

| triple $(\alpha,\beta,\eta)$ | $\lvert U_D^{\rm prod}-U_D^{\rm own}\rvert_{\max}$ | $U_1$ prod vs own | $U_2$ prod vs own | wrong order $U_EU_DU_B$ vs prod $U_1$ ($\lVert\cdot\rVert_2$) | $\lVert U_1-U_2\rVert_2$ | tol | result |
|---|---|---|---|---|---|---|---|
| (0.37, 0.61, 0.29) | $2.0\times10^{-15}$ | $4.1\times10^{-15}$ | $5.2\times10^{-15}$ | 1.63 | 1.05 | $10^{-10}$ (own bar: $10^{-12}$) | PASS |
| (0.91, 0.23, 0.53) | $3.3\times10^{-15}$ | $3.3\times10^{-15}$ | $3.5\times10^{-15}$ | 1.81 | 1.40 | same | PASS |
| (1.70, 1.00, 1.07) | $4.0\times10^{-15}$ | $6.6\times10^{-15}$ | $4.6\times10^{-15}$ | 1.65 | 1.91 | same | PASS |

Production `hamiltonian_inner(1.1014, 0.4316)` vs own $H$: $0.0$; default `lam_d=0` vs own two-term $H$: $0.0$. Unitarity of production $U_1$: $\le7.8\times10^{-16}$.

**3.4 Local-error slopes** (operator-norm distance to the exact $e^{-i\,dt\,H}$, $g^2=1.1014$, $\lambda_D=0.4316$, $\alpha=g^2dt/2$, $\beta=dt/g^2$, $\eta=\lambda_Ddt$)

| $dt$ | 0.1 | 0.05 | 0.025 | 0.0125 | slope 0.05→0.025 | slope 0.025→0.0125 | expected | result |
|---|---|---|---|---|---|---|---|---|
| order 1 error | 0.06003 | 0.015256 | 0.003830 | 0.000958 | **1.9940** | 1.9985 | 2 ± 0.05 | PASS |
| order 2 error | 0.008836 | 0.0011239 | 0.00014111 | 0.000017657 | **2.9937** | 2.9984 | 3 ± 0.05 | PASS |

**3.5 `eta=0` and `eta=None` limits against HEAD** (HEAD's `operators.py` loaded from `git show HEAD:...` under another module name)
`np.array_equal(old.inner_target("step", α, β, order), new.inner_target(..., eta=None))` and `(..., eta=0.0)`: **True for all 6 cases** (orders 1, 2 at (0.37,0.61), (0.91,0.23), (1.70,1.00)); `UE`, `UB` targets identical; `closed_block_full(g2)` and `closed_block_full(g2, 0.0)` identical to HEAD at $g^2\in\{0.5,1,2\}$. Error handling: `inner_target("UD", eta=None)`, `("UE", eta=…)`, `("UB", eta=…)`, `("step", order=3, eta=…)` all raise `ValueError`.

**3.6 17×17 closed block with det** (`tester-222-closed17.json`): the basis (16 vacua $\{A,B\}^4$ plus the loop state $-H_B|{\rm vac}_A\rangle/4$) is orthonormal (0.0), is an invariant subspace of own $H$ at all $g^2\in\{0.5,1,2\}$, $\lambda_D\in\{0,0.2,0.5,-0.5\}$ (invariance defect 0.0), and the projected block equals the plan's closed form (prompts/204 §2.5: $\tfrac{g^2}{2}3\lvert\ell\rangle\langle\ell\rvert-\tfrac4{g^2}(\ldots)+2\lambda_D\sum_\ell X_\ell$) entry for entry (0.0) and the production `closed_block_full(g2, lam_d)` entry for entry (0.0; eigenvalues $\le1.4\times10^{-14}$). Zero levels: 15 at $\lambda_D=0$, 5 at $\lambda_D\ne0$, as in the plan.

**3.7 Encoding pass-through** (`tester-222-enc-passthrough.json`): `RishonEncoding.target(kind, α, β, order, states=…, eta=…)` on 17 closed + 15 seeded physical states vs own contraction $\sum_o\langle z_{k'}^o|V|z_k^o\rangle$ with own $V$: `UD`, step order 1, step order 2 at two triples $\le1.1\times10^{-15}$; `eta=None` two-layer target $7.9\times10^{-16}$; `enc.inner_target(step, eta)` vs own $4.1\times10^{-15}$. (UD vs step targets differ by 1.66, so the test discriminates.)

## 4. Prune cap (D1) and the two items that differ from the briefing

**4.1 Shared code untouched.** `git diff HEAD` on every tracked file under `src/su2plaq/evaluate/` and `src/su2plaq/compress/`: empty (checked file by file; also `git status` shows nothing there). Shared `provenance.code_hash()` = `0bd7e7d91d9d7bcfc78641d1a14bb87f0f82f932c41c601fb991d30de13a0582` (= the pre-step value `0bd7e7d9…`). Shared `PRUNE_FRACTION` is still $10^{-2}$ (M5_V2 asserts it; mutation run asserts it after the runs). `TaskSpec` unchanged by construction (no shared files).

**4.2 Rishon cap is applied only to rishon.** The only consumers are `rishon.verify.verify` (and through it `rishon/compress/evaluate.py` and `verify_synthesised`); `rishon/compress/{spec,brief}.py` read the same constant. The four spec/brief numbers agree: cap text $10^{-11}$, "prune cap = 0.1 x tolerance for this encoding", budget **9090**, and `1e-12` occurs **0 times** in `compress/specs/rishon-step.md` and `rishon-structure.json`. Rishon evaluator hash is now `ddb440ad…` (rounds 2–4 files carry `43ae85b4…`, rounds 0–1 `d45ffb31…`), as predicted in prompts/204 §3.

**4.3 D1 done-check: $U_B(0.61)$, rccx ladder** (`tester-222-prune-cap-ub.json`, 8–11 s each)

| ladder | rishon verdict | `dropped_total` | `op_norm_error` (block / leak / dropped) | Gauss (273 states) | shared verdict (`inner_verdict`) | physical cross-check |
|---|---|---|---|---|---|---|
| ccx | ok, certified | $3.02\times10^{-13}$ | $3.43\times10^{-13}$ ($4.1\times10^{-14}$ / 0 / $3.0\times10^{-13}$) | $2.3\times10^{-15}$ | ok | — |
| **rccx** | **ok, certified** | **$2.281\times10^{-12}$** (plan: $2.28\times10^{-12}$) | $2.62\times10^{-12}$ ($3.4\times10^{-13}$ / 0 / $2.3\times10^{-12}$) | $2.7\times10^{-14}$ | **`pruning_bound`, ok=False** | 273 states, max abs diff $3.1\times10^{-13}$, phase $1+2.4\times10^{-15}i$ |
| mcx | ok, certified | $2.131\times10^{-12}$ | $2.44\times10^{-12}$ | $2.4\times10^{-14}$ | `pruning_bound` | — |

`extra` = `{prune_fraction: 0.1, prune_cap: 1.0e-11, laptop_reason: "pruning_bound"}` for rccx/mcx. Also run in M5_V2: threshold at $0.9\times$ / $1.1\times$ the measured bound flips as required; `prune_fraction=1e-3` raises `ValueError`; a wrong circuit ($\beta+10^{-6}$) is still `error`.

**4.4 Re-judge cascade cannot accept what the shared evaluator rejects for another reason** (`tester-222-rejudge-mutations.json`, 54 cases; my process only, `su2plaq.rishon.verify.evaluate` swapped for a function returning the real shared verdict with fields overwritten by `dataclasses.replace`; nothing in `src/` edited)

| mutation | expected | got | result |
|---|---|---|---|
| shared reason $\in$ {error, leak, dirty_ancilla, gauss, bad_layout, writes_outer, disallowed_gate, unsimulable, eval_budget, an unknown string} × `dropped_total` $\in\{0,10^{-13},5\times10^{-12}\}$ (30 cases) | never accepted, same reason returned | 30/30 rejected, reason unchanged | PASS |
| shared `pruning_bound`, `dropped_total` = $5\times10^{-12}$, $9.99\times10^{-12}$ | re-judged `ok` | ok | PASS |
| shared `pruning_bound`, `dropped_total` = $1.001\times10^{-11}$, $10^{-9}$, 0.5 | `pruning_bound` | `pruning_bound` | PASS |
| shared `pruning_bound` + `leak_amplitude` $10^{-9}$ (ancilla- / invalid-code-dominated) | rejected | `dirty_ancilla` / `leak` | PASS |
| shared `pruning_bound` + `op_norm_error` $2\times10^{-10}$ and $1.0000001\times10^{-10}$ | rejected `error` | `error` | PASS |
| shared `pruning_bound` + `op_norm_error` $0.99\times10^{-10}$ | accepted | ok | PASS |
| shared `pruning_bound` + $\infty$ `op_norm_error` | rejected | `error` | PASS |
| Gauss decides after a re-judged `ok` (`tester-222-rejudge-gauss.json`): circuits $\mathrm{rz}(0.7)$, $\mathrm{cz}(0,4)$, $\mathrm{swap}(0,4)$ appended to $U_E$, shared verdict faked clean `pruning_bound` | `gauss` | `gauss`, residual 0.343, 1.0, 0.5 | PASS |
| real wrong circuit (rx 0.7) unfaked | rejected | `leak` | PASS |
| `prune_fraction` $0.001,\ 0.00999$ | `ValueError` | `ValueError` | PASS |
| `prune_fraction` $0.01,\ 0.1,\ 0.5$ | allowed | allowed | PASS |
| `prune_fraction=0.01` with faked `dropped_total` $5\times10^{-12}$ | `pruning_bound` (cap $10^{-12}$ honoured) | `pruning_bound`, `prune_cap` $=1.0\times10^{-12}$ | PASS |
| `inner_verdict` stays the untouched shared verdict | `pruning_bound`, ok False | yes | PASS |

Non-blocking observations from the same run (impossible inputs, same weakness as the shared cascade):
* A faked shared `pruning_bound` verdict with `NaN` in `dropped_total`, `op_norm_error` or `leak_amplitude` is re-judged `ok` (NaN comparisons are false). The shared cascade itself has the same property (NaN `err_total` > tol is false). A real `pruning_bound` verdict has `dropped_total` $>10^{-12}$, so `dropped_total` cannot be NaN there, but `op_norm_error`/`leak_amplitude` NaN could. Suggest `not (x <= bound)` style comparisons in `_rejudge` at some point (guess: low priority, upstream behaves the same).
* The `leak` vs `dirty_ancilla` label in `_rejudge` uses `dirty_ancilla >= 0.5*max_leak`, the shared one uses `dirty >= inv_max` (the shared `Verdict` has no `inv_max`). Label only, validity unaffected; the plan says so (prompts/204 §3).
* The rx-leakage case: a circuit that leaves the valid codes is invisible to the Gauss sample by construction (`decode_state` drops invalid codes), and relies on the leak amplitude; with the leak amplitude faked clean it is accepted. Not realistic (real shared verdict says `leak`, see the unfaked case above).

**4.5 Briefing item (1): the cause of the `M6_G4` failure.** The briefing said G4 (and slow G1) fail only because the rishon evaluator hash changed (robust cache keyed on it) and that C2 fixes it. What I measured:
* G4 failed with `assert summary.get("headline", {}).get("id") == h["id"]` — `summary["headline"]` is absent. `results/compress/rishon/summary.json` did not exist when I started (not in the initial `git status`); G4's own fallback `report_table(...)` (the shared writer, no headline) created it and then asserted a headline. The headline itself came out right: `r04-F1-004`, robust key (228, 16876, 0, 28328, 53), $\bar T=843.8$.
* The hash change only costs time: the robust cache is keyed on the evaluator hash, so G4 spent ~145 s rebuilding it once (`robust.json` now differs from HEAD in **one line**: `evaluator_sha256` `43ae85b4…` → `ddb440ad…`; all 19 entries' robust keys unchanged).
* After `python -m su2plaq.rishon.compress.robust report` (0.2 s, cache warm), `pytest ... -k G4`: **1 passed**. So G4 needs that command (the known note in `notes/STATUS.md` decision log 138/140), not the replay.
* G1 and S3 (slow) fail with `PENDING: ... not replayed under the 10 % cap (prompts/204 step C2)` — that is the replay's job (they also compare `best.evaluator_sha256` with the current hash, which would be the next failure; the replay replaces the stored hash).
Summary: hash change is **not** the cause of G4; C2 is what clears G1/S3/G5 but is not needed for G4.

**4.6 Minor note on the spec text.** The new sentence says the uncompressed circuit, its rccx variants and the Qiskit L3 transpile "use about 3 500-4 400" branching gates. The three round-0 seeds measure `dropped_total` = $3.79\times10^{-12}$ (qiskit_l3), $2.91\times10^{-12}$ (seed-001), $2.69\times10^{-12}$ (seed-002) in `round-000.json`, which at $1.1\times10^{-15}$ per gate is about 2 450–3 450 gates. The sentence is taken from the plan (prompts/204 §5), I did not count the lowering independently. Harmless (order of magnitude, far below 9090); worth a wording fix when the spec is next touched. Guess: the plan used a different weighting of `ch`/`crx`.

## 5. Failures / pending, with guessed cause

| item | status | guess |
|---|---|---|
| `M6_G4` | FAIL on a fresh checkout until `robust report` is run | test relies on `summary.json` having the `headline` key, which only `robust.report_table` writes; its fallback uses the shared writer (pre-existing, unrelated to D1/D2) |
| `acceptance-check` | FAIL | untracked `tests/acceptance/m2c/` (consolidation planner, prompts/008) — not rishon |
| D3–D7 / C1 / C4 tests (24 ids) | PENDING | later steps, expected |

New failures vs the last rishon report (221): none from D1/D2 code. Passed 61 / failed 0 genuine / pending 24 / G4 flagged 1.

## 6. Files touched by my runs
* New: `results/rishon/tester-222-*.{py,json}` (6 scripts + outputs + junit summary), this report.
* Written by the test suite / my commands: `results/compress/rishon/robust.json` (tracked; one line: `evaluator_sha256`, robust cache refreshed under the new hash — the replay step moves it to `pre-204` anyway; revert is the coordinator's call), `results/compress/rishon/summary.json` (untracked; now contains the headline), robust-cache/`__pycache__` byproducts.
* No file under `src/`, `tests/`, `compress/` edited by me.
