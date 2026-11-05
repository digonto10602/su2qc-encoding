# 005 — Addendum to prompts/002 + 003 + 004: relative cap on the certified pruning bound

- Date: 2026-11-05
- Author: planner (Claude Fable 5.1)
- Git commit at writing: 0495049 (+ uncommitted step-1.9 work in `scripts/m1_results.py`, `results/twelve/*.json`, `tests/unit/test_m1_results_script.py` — untouched by this plan)
- Plan in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` + addenda `prompts/003`, `prompts/004`, and this file. Everything not mentioned here is unchanged.
- Trigger: `reports/tests/020-m1-steps-1-7-1-8-ttable-outer.md` §C (tester, PASS with a tolerance question); Digonto's decision 2026-11-05 recorded in `notes/STATUS.md` ("Known issues"): *relative cap — reject only if the dropped-norm bound exceeds 1 % of the circuit's error budget (= 1e-12 for exact-angle circuits as now, >= 1e-11 for synthesised)*.
- Research report: none (no new numerical method; the rule follows from the error analysis already in `reports/research/003` §2 and from the measurements in `reports/tests/020` and `results/twelve/*.json`). The construction used by the new acceptance test was prototyped in `scratch/planner/proto_prune_cap.py` (numbers in §7).

## 0. Diagnosis

The sparse engine (`su2plaq.evaluate.sparse_sim`) drops, after every branching gate, amplitudes with $|a|\le$ `PRUNE_REL` $\times$ (largest $|a|$ of the same input column), `PRUNE_REL` $=10^{-14}$, and certifies per input column $c$ the dropped L2 weight $d_c=\sum_{\text{coalesce}}\sqrt{\sum_{\text{dropped}}|a|^2}$ (`Batch.dropped_l2`; the per-coalesce sum is a valid bound on the column error because each drop is a perturbation of norm $\sqrt{\sum|a|^2}$ and unitaries do not increase norms). `Batch.dropped_total` $=\sqrt{\sum_c d_c^2}$ bounds the Frobenius and hence the operator norm of the pruning error $E$ of the simulated $2^n\times625$ block; `Batch.dropped_max` $=\max_c d_c$.

Three things were inconsistent (reports/tests/020 §C):
1. The verdict rejected (`pruning_bound`) when the **per-column maximum** `dropped_max` exceeded a **fixed** `TOL_PRUNE = 1e-12`, independent of the tolerance the circuit is judged by, although `dropped_total` is already the second term of `op_norm_error` (prompts/004). Consequence: the correct synthesised step order 2 at $\varepsilon=10^{-4}$ (`dropped_max` $2.63\times10^{-12}$, `dropped_total` $3.88\times10^{-11}$, `op_norm_error` $5.77\times10^{-4}\le$ `tol_err` $1.4\times10^{-3}$) was rejected; at the loop value $\varepsilon=10^{-6}$ step order 1 sat at $4.7\times10^{-13}$, a factor 2.1 below the cap.
2. The cap compared a different quantity (per-column max) from the one in the budget (Frobenius bound summed over outer groups).
3. The sum over outer-bit groups (`dropped_total += dt`) is valid but pessimistic by up to the number of groups: the pruning error is block-diagonal in the outer pattern (§2), so the operator norm is the maximum over groups. With the sum, the relative cap would shrink the headroom of a correct exact-angle circuit that reads $b$ outer bits by up to $2^b$.

## 1. The rule (replaces `TOL_PRUNE`)

$$\texttt{pruning\_bound}\iff\texttt{dropped\_total}>\texttt{PRUNE\_FRACTION}\cdot\texttt{tol\_err},\qquad\texttt{PRUNE\_FRACTION}=10^{-2},$$

where `dropped_total` is **the same number that enters** $\texttt{op\_norm\_error}=\texttt{block\_error}+\texttt{dropped\_total}+\texttt{leak\_amplitude}$ (prompts/004 Eq. in §1), now defined as

$$\texttt{dropped\_total}=\max_{r\in\text{outer groups}}\ \sqrt{\sum_{c=1}^{625}d_{c}^{(r)\,2}}\quad(\text{`Batch.dropped\_total` of group }r),$$

i.e. the **maximum over outer-bit groups** of the per-group Frobenius bound (was: the sum). `tol_err` is the tolerance actually applied to the verdict ($10^{-10}$ for exact-angle circuits, $N_{\rm rot}\varepsilon+10^{-9}$ from `synth_tolerances` for synthesised ones). Consequences: exact-angle cap $=10^{-12}$ exactly as before (now on the Frobenius bound, see §5); synthesised cap $\ge10^{-2}\cdot1.1\times10^{-9}=1.1\times10^{-11}$, and $10^{-7}$ at the loop value $N_{\rm rot}=10,\ \varepsilon=10^{-6}$. The error budget itself is unchanged: `op_norm_error` $\le$ `tol_err` still contains the full `dropped_total`, so a verdict `ok` remains a rigorous statement about the circuit.

`dropped_max` stays a diagnostic only (`Verdict.extra["max_dropped_l2"]`); it is judged by nothing.

## 2. Why the maximum over outer groups is the correct aggregation (proof)

Notation as in `reports/research/003` §2. Let $\Phi=\sum_o|o\rangle\otimes\Psi_o$ be the $2^{n}\times433$ isometry whose columns are the physical states ($\Psi_o$ = inner components of the states at outer pattern $o$; $\Phi^\dagger\Phi=I$, Gram error $3\times10^{-15}$, reports/tests/016). The evaluator simulates one inner-register matrix $M_r$ per group $r$ of outer patterns sharing the values of the read outer bits; every pattern $o$ in group $r(o)$ gets the same $M_r$, and this is exact because the specialised circuit is the same for all of them. The pruned result is $M'_r=M_r+E_r$ with $\|E_r\|_2\le\|E_r\|_F\le$ `Batch.dropped_total`$_r=:t_r$. The full-register pruning error is therefore block-diagonal in the outer pattern,
$$E=\sum_o|o\rangle\langle o|\otimes E_{r(o)},\qquad\|E\|_2=\max_o\|E_{r(o)}\|_2\le\max_r t_r .$$
Every judged quantity is built from $U'\Phi=(U+E)\Phi$ (the physical block $A'=\Phi^\dagger U'\Phi$, the leak $X'$, the span leak $S'$ — orthogonal components of the same columns), so by the triangle inequality on the full-register quantity that `op_norm_error` bounds (research/003 §2),
$$\|(U-e^{i\varphi}\Phi V\Phi^\dagger)\Phi\|_2\le\|(U'-e^{i\varphi}\Phi V\Phi^\dagger)\Phi\|_2+\|E\Phi\|_2\le\texttt{block\_error}+\texttt{leak\_amplitude}+\|S'\|_2+\max_rt_r .$$
Hence a single $+\max_r t_r$ is rigorous; the previous $\sum_r t_r$ was an over-bound by up to the number of groups. (Measured impact today: zero — every branching circuit evaluated so far reads no outer bit, `n_blocks` $=1$; the 128-group outer-electric row has `dropped_total` $=0$ because it has no branching gate.) The Gauss residual is also computed from pruned outputs; its pruning error is $\le\|G^a_c\|_{\rm op}\max_rt_r=2\max_rt_r\le2\times10^{-2}$ `tol_err` under the cap and is **not** added to the Gauss comparison (unchanged policy; noted, not a change).

## 3. Why 1 % (justification of the constant)

The separate rejection is a safety net, not part of the correctness bound: `op_norm_error` is rigorous for any amount of pruning. Its only job is to guarantee that the simulator's own contribution can never decide a verdict — with the cap, at most 1 % of the budget is spent by the simulator, so `ok` implies the circuit's own certified error (`block_error + leak_amplitude`) is $\le$ `tol_err` and the certified bound is at most 1 % pessimistic from pruning. One per cent was chosen by Digonto; it is also the natural order of the other non-circuit term in the system (`synth_tolerances` adds a fixed $10^{-9}$ float budget, which is 1 % of the smallest synthesised budget actually used in the T tables, $N_{\rm rot}\varepsilon=10^{-7}$ at $\varepsilon=10^{-8}$, and $\le0.1$ % elsewhere). The acceptance test pins the constant to $\pm20$ % (§7), so neither $2\times10^{-2}$ nor $5\times10^{-3}$ passes.

Measured headroom (cap / `dropped_total`, values from `results/twelve/{UE,UB,step}.json`, commit 0495049, $(\alpha,\beta)=(0.37,0.61)$; all `n_blocks` $=1$, so sum = max):

| circuit | tolerance | `dropped_total` | new cap $10^{-2}$`tol_err` | headroom | old rule (`dropped_max` vs $10^{-12}$) |
|---|---|---|---|---|---|
| UE exact | $10^{-10}$ | 0 (no branching gate) | $10^{-12}$ | — | — |
| UB exact | $10^{-10}$ | $1.20\times10^{-13}$ | $10^{-12}$ | 8.3 | $6.1\times10^{-15}$: 160 |
| step 1 exact | $10^{-10}$ | $1.47\times10^{-13}$ | $10^{-12}$ | 6.8 | $7.9\times10^{-15}$: 126 |
| step 2 exact | $10^{-10}$ | $1.52\times10^{-13}$ | $10^{-12}$ | 6.6 | $9.2\times10^{-15}$: 108 |
| step 2, $\varepsilon=10^{-4}$ | $1.4\times10^{-3}$ | $3.88\times10^{-11}$ | $1.4\times10^{-5}$ | $3.6\times10^{5}$ | $2.63\times10^{-12}$: **rejected** |
| step 1, $\varepsilon=10^{-6}$ | $1.0\times10^{-5}$ | $9.16\times10^{-12}$ | $1.0\times10^{-7}$ | $1.1\times10^{4}$ | $4.7\times10^{-13}$: 2.1 |
| UE, $\varepsilon=10^{-6}$ | $4.0\times10^{-6}$ | $4.58\times10^{-12}$ | $4.0\times10^{-8}$ | $8.7\times10^{3}$ | $1.8\times10^{-13}$: 5.5 |
| UB, $\varepsilon=10^{-10}$ | $1.6\times10^{-9}$ | $2.05\times10^{-13}$ | $1.6\times10^{-11}$ | 78 | $1.3\times10^{-14}$: 77 |
| step 1, $\varepsilon=10^{-10}$ | $2.0\times10^{-9}$ | $2.28\times10^{-13}$ | $2.0\times10^{-11}$ | 88 | $1.3\times10^{-14}$: 77 |
| step 2, $\varepsilon=10^{-10}$ | $2.4\times10^{-9}$ | $2.32\times10^{-13}$ | $2.4\times10^{-11}$ | 103 | $1.5\times10^{-14}$: 67 |

Reading: for synthesised circuits the new rule is never tighter than the old one on any measured row and removes the false rejection; at the loop value ($\varepsilon=10^{-6}$) the headroom is $\ge8.7\times10^{3}$ instead of 2.1. For exact-angle circuits the cap value is unchanged ($10^{-12}$) but it is now applied to the Frobenius bound ($\le25\times$ the per-column maximum), so the measured headroom is 6.6–8.3 instead of $\gtrsim100$. This is the honest consequence of comparing the same quantity that enters the budget; see the stop condition in §9 for what to do if an exact-angle M2 candidate ever reaches it (ask, never loosen in the loop).

## 4. Interface (builder: stubs/edits in `src/su2plaq/evaluate/evaluator.py` only)

```python
# src/su2plaq/evaluate/evaluator.py
PRUNE_FRACTION = 1e-2   # pruning_bound iff dropped_total > PRUNE_FRACTION * tol_err (prompts/005 §1). Replaces TOL_PRUNE (delete it; no alias).

# evaluate(...): signature unchanged (no new kwargs).  Inside:
#   dropped_total = max(dropped_total, dt)      # was: += dt   (max over outer groups, prompts/005 §2)
#   dropped_max   = max(dropped_max, dm)        # unchanged, diagnostic only -> Verdict.extra["max_dropped_l2"]
#   verdict order unchanged: pruning_bound -> dirty_ancilla/leak -> error -> gauss -> ok, with
#   if dropped_total > PRUNE_FRACTION * tol_err: reason = "pruning_bound"
#   failing_inputs for pruning_bound = [("dropped_total", dropped_total), ("prune_cap", PRUNE_FRACTION * tol_err)]
# Verdict: fields unchanged; update the comment on dropped_total:
#   "certified pruning bound (max over outer groups of the per-group Frobenius bound), already included in op_norm_error"
```

`op_norm_error == block_error + dropped_total + leak_amplitude` must keep holding to $10^{-15}$ (asserted by locked tests and unit tests). `sparse_sim.py` (`PRUNE_REL`, `Batch.dropped_l2/dropped_total/dropped_max`, `_coalesce`) is **not** changed. `su2plaq.compress.evaluate` and `scripts/m1_results.py` do not reference `TOL_PRUNE` (checked 2026-11-05).

## 5. Consequences

- Exact-angle circuits: cap value unchanged at $10^{-12}$; compared quantity is now the (max-over-groups) Frobenius bound. All existing exact-angle verdicts stay `ok` (table in §3; `dropped_total` $\le1.52\times10^{-13}$).
- Synthesised circuits: cap becomes $10^{-2}(N_{\rm rot}\varepsilon+10^{-9})\ge1.1\times10^{-11}$; step order 2 at $\varepsilon=10^{-4}$ becomes `ok` (its `op_norm_error` $5.77\times10^{-4}\le1.4\times10^{-3}$ was always within budget). The error budget, `synth_tolerances`, the Gauss rule (prompts/003) and the leak-as-amplitude bound (prompts/004) are unchanged.
- `results/twelve/step.json` `extra/order2/metrics/t_table[0]/synth/verdict` changes from `pruning_bound` to `ok`; `dropped_total` values change only for multi-group branching circuits (none today). Step 1.9 regenerates the files after this step.
- Unit test `tests/unit/test_evaluator_unit.py::test_pruning_bound_reason` (PRUNE_REL monkeypatched to 1.5, tol_err $10^{-10}$) remains valid: everything is dropped, `dropped_total` $\gg10^{-12}$.

## 6. Steps (one step; insert before M1 step 1.9's regeneration of results)

| step | what | done-check (tester) | acceptance ids that must turn green |
|---|---|---|---|
| 1.9-pre (this plan) | §4 edits in `evaluator.py`; delete `TOL_PRUNE`; update docstrings; unit tests: keep `test_pruning_bound_reason`, add one unit test that `failing_inputs` of a `pruning_bound` verdict carries `("dropped_total", v.dropped_total)` and `("prune_cap", 1e-2*tol_err)`; `graphify update .` | `pytest -n auto tests/unit` green; `pytest -n auto -m "not slow" tests/acceptance/m0 tests/acceptance/m1 -k "evaluator or V1 or V2 or T1"` green; `grep -rn TOL_PRUNE src tests` empty; `pytest --collect-only -q tests/acceptance` clean; then re-run `python scripts/m1_results.py` (step 1.9) and confirm `results/twelve/step.json` order-2 $\varepsilon=10^{-4}$ verdict is `ok` | `tests/acceptance/m1/test_evaluator_prune.py::test_M1_V1_pruning_cap_is_relative_to_tol_err`, `tests/acceptance/m1/test_evaluator_prune.py::test_M1_V2_pruning_bound_is_max_over_outer_groups`; must stay green: `tests/acceptance/m0/test_evaluator.py` (E3–E6), `tests/acceptance/m1/test_twelve_metrics.py::test_M1_T1_t_table_and_synth_verify[UE|UB|step]`, `tests/acceptance/m1/test_twelve_circuits.py` |

Builder brief must include: graphify-first rule (`graphify query "evaluate verdict pruning"`, `graphify affected "evaluate"` before editing), the §4 snippet, and "do not touch `sparse_sim.py`, `tests/acceptance/`, `scripts/m1_results.py` beyond re-running it".

## 7. Acceptance tests added (new file, locked with this plan) — and tolerances

File `tests/acceptance/m1/test_evaluator_prune.py` (M1 folder: the change is made during M1 and the gate runs m0+m1; nothing in `m0/` is edited — no locked test asserted the old fixed cap, `grep -rn "pruning\|TOL_PRUNE\|dropped" tests/acceptance` on 2026-11-05 found only the comment in `m0/test_evaluator.py:183`, which stays true).

Construction (deterministic, no randomness, no monkeypatch of `src`): $k=250$ gates $u(2\delta,0,0)=R_y(2\delta)$ on data qubit `d[0]` with $\delta=\tfrac12$`PRUNE_REL` $=5\times10^{-15}$. Each gate creates one amplitude $\sin\delta$ per input column, below the threshold `PRUNE_REL` $\times$ column max $=10^{-14}$, so it is dropped and certified: $d_c=k\sin\delta=1.25\times10^{-12}$ for every column, `dropped_total` $=25k\sin\delta=3.125\times10^{-11}$; the kept amplitude $\cos\delta=1.0$ exactly in float64, so the circuit is the identity up to rounding (`block_error` $2.9\times10^{-13}$ measured, leak 0). Prototype `scratch/planner/proto_prune_cap.py` (current code): `dropped_total` $3.1250\times10^{-11}$, `max_dropped_l2` $1.2500\times10^{-12}$, 1.4–5.8 s per `evaluate`; with the identity pair `cz(o[0],d[1])`$^2$ (one outer bit read, 2 groups): current sum gives $6.25\times10^{-11}$, max gives $3.125\times10^{-11}$.

- `test_M1_V1_pruning_cap_is_relative_to_tol_err` (one circuit, five verdicts): (a) `synth_tolerances(10,1e-6)`: `dropped_total` in $(10^{-12},10^{-7}]$ → `ok`, certified, `failing_inputs == []`; the old rule rejected it (`dropped_max` $1.25\times10^{-12}>10^{-12}$). (b) `synth_tolerances(1,1e-10)` (cap $1.1\times10^{-11}$): `dropped_max` $<$ cap $<$ `dropped_total` → `pruning_bound`, and `block_error + leak_amplitude <= tol_err` so the cap is the sole reason; `failing_inputs` contains `("dropped_total", v.dropped_total)` — pins **total, not per-column max**. (c) default $10^{-10}$ → `pruning_bound` (exact-angle cap $10^{-12}$ unchanged). (d,e) `tol_err = 1.2 x dropped_total/1e-2` → `ok`; `0.8 x` → `pruning_bound`: pins `PRUNE_FRACTION` to $\pm20$ %. Also asserts `PRUNE_FRACTION == 1e-2`, `op_norm_error == block + dropped + leak` ($10^{-15}$), `max_dropped_l2 <= dropped_total`.
  Tolerances: `dropped_total` vs $25k\sin\delta$: $10^{-6}$ relative — the bound is a float64 sum of $k=250$ identical terms per column, sqrt-summed over 625 columns, relative rounding $\lesssim k\cdot2^{-52}\approx6\times10^{-14}$; $10^{-6}$ leaves $10^{7}$ margin and still rejects any change of the aggregation (sum over groups $=2\times$) or of the per-column accounting. `block_error <= 1e-12`: measured $2.9\times10^{-13}$ from 250 float64 gate applications on 625 columns ($\sim k\cdot10^{-16}\cdot\sqrt{625}$); $10^{-12}$ is $3.4\times$ the measurement and $100\times$ below the exact-angle budget, so it cannot mask a real error. $\pm20$ % on the fraction: the two boundary tolerances are $1.2\times$ and $0.8\times$ the exact boundary $3.125\times10^{-9}$; the only float uncertainty is the $10^{-6}$ relative one on `dropped_total`.
- `test_M1_V2_pruning_bound_is_max_over_outer_groups`: same drops plus the identity `cz` pair reading `o[0]` → `n_blocks == 2`, `method == "physical"`, `dropped_total == 25k\sin\delta` ($10^{-6}$ relative; the sum would give $2\times$), equal to the no-outer value, verdict `ok` at `synth_tolerances(10,1e-6)`.

Run time (patched scratch copy, 1 thread): V1 16 s, V2 3.4 s — below the existing M1-T1 tests (14 s each); not marked slow. On the current code: V1 fails `PENDING: su2plaq.evaluate.evaluator has no attribute PRUNE_FRACTION`, V2 fails on $6.25\times10^{-11}\ne3.125\times10^{-11}$ (the right reasons). Against the §4 edits applied to a scratch copy of the package: both pass, and `tests/unit/test_evaluator_unit.py`, `test_sparse_sim_unit.py`, `test_m1_results_script.py` (48 tests) plus the locked `m0/test_evaluator.py` and `m1/test_twelve_circuits.py` pass unchanged. `pytest --collect-only -q tests/acceptance` is clean once the coordinator re-locks (until then the session-start lock check reports the new file as unlocked — expected).

## 8. Do-not-retry

- Dropping the `pruning_bound` rejection entirely (tester option a): rejected by Digonto — keep the 1 % safety net.
- Keeping the fixed $10^{-12}$ cap and raising `PRUNE_REL`/`PRUNE_FRACTION` ad hoc inside the loop to make a candidate pass: forbidden (tolerance changes only through a planner prompt with justification).
- Comparing the per-column maximum against the relative cap while summing the Frobenius bound into the budget (mixed quantities): this is exactly the inconsistency reported in 020 §C.
- A `PRUNE_REL` of 0 as "no pruning": float noise ($\sim10^{-17}$) then produces $6\times10^{7}$ stored amplitudes per batch and exceeds the cap (reports/tests/020 §C).

## 9. Risks and stop conditions

- If `pruning_bound` ever fires on a circuit whose `op_norm_error <= tol_err` (i.e. the safety net is the sole reason) — in particular an exact-angle M2 candidate whose Frobenius pruning bound exceeds $10^{-12}$ — **stop and ask Digonto**; do not raise `PRUNE_FRACTION` or `PRUNE_REL`. Record `dropped_total`, `max_dropped_l2`, `n_blocks`, number of branching gates.
- The max-over-groups aggregation relies on every outer pattern of a group receiving the same simulated $M_r$ (true by construction in `evaluate`). If a future engine simulates per pattern with different pruning, the aggregation must be revisited (the sum would again be the safe fallback).
- Gauss residual pruning error ($\le2\,$`dropped_total`) is not added to the Gauss comparison; under the cap it is $\le2\times10^{-2}$`tol_gauss` — acceptable, documented in METHODS §6; revisit only if `tol_gauss` is ever set far below `tol_err`.

## 10. Expected cost

Builder: ~5 lines in `evaluator.py` + one unit test; < 30 min. Tester: new tests ~20 s; m0+m1 non-slow suite unchanged (~1–2 min with `-n auto`); step-1.9 regeneration `python scripts/m1_results.py` (whatever it took in report 020's step 1.9, dominated by the T tables and the Paulo aer_mps verdict ~84 s). Memory unchanged.

## 11. docs/METHODS.md

§6 evaluator paragraph updated by the planner together with this plan: definition of `dropped_total` (max over outer groups of the per-group Frobenius bound, with the block-diagonal argument), the `pruning_bound` rule with `PRUNE_FRACTION = 1e-2`, the headroom numbers, and the note on the Gauss residual's (unjudged) pruning error. Earlier coordinator/planner edits (aer_mps accuracy, `max_leak` definition, prompts/003 Gauss rule, prompts/004 leak-as-amplitude) kept verbatim.
