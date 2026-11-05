# 004 — Addendum to prompts/002 + 003: leak counted as an amplitude; one combined error bound

Date: 2026-11-04. Planner (Fable 5.1). Git HEAD at writing: `8bab9da` (builder's N2–N4/N7–N9 fixes uncommitted in `src/`).
**prompts/002 stays the plan in force; prompts/003 stays in force except where this addendum amends it (§2 tolerance table, §3 certification rule, §4 interface). This addendum amends prompts/002 §2.7 (evaluator interface), §2.10 (`TaskSpec`), §2.11 (results schema), §6 (tolerance rows that mention leak), and METHODS §6.** Everything not mentioned is unchanged.

## 0. Trigger
`reports/audits/001-m0-foundation-audit.md` note **N1** (stop-and-ask on a tolerance) and **N3** (aer_mps leak is per basis input, not per physical state). The evaluator compared the leak *weight* (probability, $\sum|a|^2$) with `tol_leak = 1e-12` while the operator-norm error (an *amplitude*) was compared with `tol_err = 1e-10`. A leaked amplitude $\delta$ enters the physical-block error only as $O(\delta^2)$, so any error that ends in an ancilla or an invalid code passed as "exact" up to $\delta\approx10^{-6}$. Measured by the auditor (probe `a7.py`) and reproduced here (`scratch/planner/proto_leak_amplitude.py`): `cry(1.9e-6)` from a data $j$-qubit onto an ancilla, target identity → verdict `ok`, `max_leak` $9.0\cdot10^{-13}$, true leaked amplitude $9.5\cdot10^{-7}$.

**Decision (Digonto, 2026-11-04):** count leak as an amplitude. A circuit passes only if
$$\|A-e^{i\varphi}V\|_2+\sqrt{\lambda_{\max}(X^\dagger X)}\le\texttt{tol\_err},$$
with $X$ the leaked (out-of-code-space) part of the output on the physical inputs; synthesised circuits compare the same quantity with $N_{\rm rot}\varepsilon+10^{-9}$. Exact-angle $10^{-10}$ and the prompts/003 Gauss rule are kept.

## 1. Diagnosis
Not a bug — a wrong unit. `op_norm_error` is a norm of amplitudes, `max_leak` a sum of squared amplitudes; a common "$10^{-12}$ because float64 accumulates $10^{-13}$" justification (METHODS §6, old text) silently mixed the two: $10^{-13}$ amplitude noise is $10^{-26}$ in weight. The fix is to put the leak into the same norm as the error and drop the second tolerance, so the mistake cannot recur. The aer_mps engine had a second, independent problem (N3): its leak was derived by subtraction ($1-\sum|M|^2$, noise $\sim10^{-11}$ in weight, i.e. $3\cdot10^{-6}$ in amplitude) and per *basis input*, whereas a physical state is a superposition of up to 16 inner inputs per outer pattern, so a coherent leak can be up to 16× (weight) larger than the reported value.

## 2. Method — definitions and the bound (details and prototype numbers in `reports/research/003-leak-amplitude-bound.md`)

Notation. $\Psi$ = the $2^n\times433$ isometry whose columns are the physical states $\psi_k$ (ancillas $|0\rangle$); $V$ = the 433×433 target; $U$ = the circuit's unitary on the full register; $\mathcal C$ = the **code space** (valid data code, outer register unchanged, every ancilla $|0\rangle$); $\mathcal P=\operatorname{range}\Psi\subset\mathcal C$. Every output splits into three mutually orthogonal pieces
$$U\psi_k=\Psi A_{:,k}+s_k+x_k,\qquad A=\Psi^\dagger U\Psi,\quad s_k\in\mathcal C\cap\mathcal P^\perp\ (\text{span leak}),\quad x_k\in\mathcal C^\perp\ (\text{leak}).$$
Let $S=[s_1\cdots s_{433}]$, $X=[x_1\cdots x_{433}]$ and $\varphi=\arg\operatorname{tr}(V^\dagger A)$ (unchanged). The full output error on the physical inputs is $E=(U-e^{i\varphi}\Psi V\Psi^\dagger)\Psi=\Psi(A-e^{i\varphi}V)+S+X$ with the three terms orthogonal column-wise, hence for every unit $c$
$$\|Ec\|^2=\|(A-e^{i\varphi}V)c\|^2+\|Sc\|^2+\|Xc\|^2\quad\Rightarrow\quad \|E\|_2\le\sqrt{\|A-e^{i\varphi}V\|_2^2+\|S\|_2^2+\|X\|_2^2}\le\|A-e^{i\varphi}V\|_2+\|X\|_2+\|S\|_2 .$$

**Rule (replaces the `leak`/`dirty_ancilla` weight checks).**
$$\texttt{op\_norm\_error}:=\underbrace{\|A-e^{i\varphi}V\|_2}_{\texttt{block\_error}}+\texttt{dropped\_total}+\underbrace{\|X\|_2}_{\texttt{leak\_amplitude}}\ \le\ \texttt{tol\_err},\qquad \|X\|_2=\sqrt{\lambda_{\max}(X^\dagger X)} .$$
The sum is Digonto's form; it is an upper bound on $\|E\|_2$ (minus the span-leak term, next paragraph) and at most $\sqrt2\times$ the root-sum-square (RSS) bound. Exact-angle circuits: `tol_err = 1e-10`. Synthesised circuits: `tol_err = N_rot ε + 1e-9` (unchanged number; see §7 for the $\sqrt2$ caveat).

**Span leak $S$ is controlled by the Gauss check, not by this rule.** $\mathcal P$ is the joint kernel of the 12 Gauss generators $G^a_c$ inside $\mathcal C$ (the circuit never writes the outer register, so outputs keep valid outer codes), and $\sum_{c,a}(G^a_c)^2=\sum_c\hat J_c^2$ has smallest non-zero eigenvalue $\tfrac34$ (one corner at $J=\tfrac12$). Hence for $s\in\mathcal C\cap\mathcal P^\perp$: $\sum_{c,a}\|G^a_cs\|^2\ge\tfrac34\|s\|^2$, so $\max_{c,a}\|G^a_cs\|\ge\|s\|/4$. Since $G^a_c\Psi A=0$, the evaluator's `gauss_residual` $=\max_{c,a,k}\|G^a_c(\Psi A_{:,k}+s_k)\|=\max_{c,a,k}\|G^a_cs_k\|$, therefore
$$\max_k\|s_k\|\le4\cdot\texttt{gauss\_residual}\le4\cdot\texttt{tol\_gauss}$$
rigorously, and in practice the ratio is 1 or 2 (reports/research/002: residual/amplitude $=1.0$ on $m$-type, $0.5$ on $j$-type qubits). This is why `gauss=True` stays mandatory (prompts/003 §3) and why `tol_gauss = tol_err` for both circuit classes. `max_span_leak` (weight, `extra`) stays a diagnostic; it cannot be turned into an amplitude without cancellation ($w_{\rm code}-|A|^2$ subtracts two $O(1)$ numbers).

**Engines.**
* `sparse` (exact COO): $X$ is available row-wise (`Xa` = ancilla-set keys, `Xi` = invalid data codes, already formed per outer block). Outputs of different outer patterns are orthogonal, so $X^\dagger X=\sum_o(X_oP_o)^\dagger(X_oP_o)$ scattered into the state indices `ks` — a 433×433 Hermitian matrix accumulated block by block, then one `eigvalsh`. No subtraction anywhere: `leak_amplitude` is exact to float64 ($\sim10^{-16}$). Per-state weights $w_k=\|X\psi_k\|^2$ (today's `leak`) stay as `max_leak = max_k w_k`, `dirty_ancilla = max_k w_k^{\rm anc}`.
* `aer_mps` (per basis input, amplitudes by contraction): the out-of-code amplitudes are not enumerable, so $X^\dagger X$ is not available; instead compute, **directly and without subtraction**, per inner input $i$ of each read-group $r$:
  $w^{\rm anc}_i=\sum_{q\in{\rm anc}}\langle\Pi_{q=1}\prod_{q'\in{\rm anc},\,q'<q}\Pi_{q'=0}\rangle$ (disjoint "first set ancilla" terms, transfer-matrix contraction with the pinned qubits; outer qubits, never written, may be included among the pinned-to-0 qubits) and $w^{\rm inv}_i=\sum_{c\in\{0,1\}^{n_{\rm data}}\setminus\texttt{codes}}|\langle c,\text{rest}=0|U|i\rangle|^2$ (contract all $2^{n_{\rm data}}-|\texttt{codes}|$ invalid data patterns; 3471 for the 12-qubit encoding; limit $n_{\rm data}\le16$, raise `ValueError` beyond). Then $w_i=w^{\rm anc}_i+w^{\rm inv}_i$ and, for each outer block $o$ with support ${\rm supp}(P_o)=\{i:P_o[i,:]\neq0\}$ (≤ 17 inputs — corrected by coordinator per reports/tests/014: 81 of 3153 outer blocks have 17),
  $$W_o=\sum_{i\in{\rm supp}(P_o)}w_i,\qquad \|X\Psi\|_2^2\le\max_oW_o\quad(\text{Cauchy–Schwarz: }\|X_oP_oc\|\le\sum_i|(P_oc)_i|\sqrt{w_i}\le\|P_oc\|\sqrt{W_o},\ \textstyle\sum_o\|P_oc\|^2=1).$$
  `leak_amplitude = sqrt(max_o W_o)` (a certified upper bound, tight for a coherent leak, up to √17 ≈ 4.12× pessimistic for incoherent leak (corrected, reports/tests/014)), `max_leak = max_o W_o`, `dirty_ancilla = max_o Σ_{supp} w^anc_i`. Measured noise of the direct weights on exact-angle 34-qubit circuits (true leak 0): $\le9.4\cdot10^{-21}$ per input → `leak_amplitude` floor $\le3.9\cdot10^{-10}$ with 16 inputs; the subtraction formulas gave $10^{-15}$–$5\cdot10^{-14}$ (and $1.6\cdot10^{-11}$ in reports/tests/008 on an entangled case). Paulo's compiled circuit (625 inputs, 67 s): $\max_iw_i=4.1\cdot10^{-12}$ (all of it invalid data codes; ancillas $8.8\cdot10^{-20}$), $\max_oW_o=6.2\cdot10^{-11}$, `leak_amplitude` $7.85\cdot10^{-6}$, `block_error` $2.905\cdot10^{-6}$, combined $1.08\cdot10^{-5}$ vs budget $2\cdot10^{-5}$ (M1-P1) and vs $N_{\rm rot}\varepsilon=1.4\cdot10^{-5}$.

**Certification (amends prompts/003 §3).** `certified = engine_accuracy <= min(tol_err, tol_gauss_eff)` (with `gauss=False`: `<= tol_err`). `engine_accuracy` stays 0 (`sparse`) / `MPS_ACCURACY = 2e-10` (`aer_mps`, per amplitude). The aer_mps noise of the combined quantity is $\le2\cdot10^{-10}+3.9\cdot10^{-10}<10^{-9}$, so the certification minimum for aer_mps stays `tol_err ≥ 1e-9` (M0-E5 second clause unchanged at $10^{-9}$).

## 3. Interface change (builder; one small step "0.11 leak as amplitude")
```python
# su2plaq/evaluate/evaluator.py
def evaluate(qc, enc, target, *, tol_err: float = 1e-10, tol_gauss: float | None = None, gauss: bool = True,
             method: str = "auto", engine: str = "auto", cap: int = 5_000_000) -> Verdict
    # tol_leak REMOVED (passing it is a TypeError). tol_gauss None -> TOL_GAUSS = 1e-10 (unchanged).
def synth_tolerances(n_rot: int, eps: float) -> dict
    # == {"tol_err": n_rot*eps + 1e-9, "tol_gauss": n_rot*eps + 1e-9}   (no tol_leak key)
@dataclass class Verdict:
    ok; reason; op_norm_error; max_leak; dirty_ancilla; phase; outer_bits_read; n_blocks; gauss_residual; method; engine;
    seconds; failing_inputs; n_inputs                      # existing positional fields, same order
    dropped_total = 0.0; engine_accuracy = 0.0; certified = True; tolerances = {}   # existing
    block_error: float = float("nan")      # NEW ||A - e^{i phi} V||_2 (method 'inner_span': max(inner-span error, physical error) — audit N2)
    leak_amplitude: float = float("nan")   # NEW ||X||_2 (sparse: exact) / sqrt(max_o W_o) (aer_mps: certified bound)
    extra: dict = {}                       # existing; keeps op_norm_error_physical, max_dropped_l2, max_span_leak
    # op_norm_error == block_error + dropped_total + leak_amplitude  (always; _early verdicts: inf for all three)
    # max_leak / dirty_ancilla: weight DIAGNOSTICS (sparse: max_k ||X psi_k||^2 and its ancilla part; aer_mps: max_o W_o
    #   and its ancilla part). Invariant: max_leak <= leak_amplitude**2 (+1e-30).
    # tolerances == {"tol_err": ..., "tol_gauss": <effective>}
    # reason order: "pruning_bound" -> ("dirty_ancilla" if leak_amplitude > tol_err and ancilla weight >= invalid-code weight,
    #   else "leak" if leak_amplitude > tol_err) -> "error" if op_norm_error > tol_err -> "gauss" -> "ok".
    # failing_inputs for "leak"/"dirty_ancilla": up to 10 (state index k, sqrt(w_k)) [sparse] or
    #   (f"inner_code_index {i}", sqrt(w_i)) [aer_mps], largest first, NOT filtered by the tolerance (the operator norm can
    #   exceed every single-state value); never empty when the reason is a leak reason.
MPS_ACCURACY = 2e-10   # unchanged
# su2plaq/evaluate/aer_check.py
def aer_mps_block(qc, inputs, codes, code_mask, bond_dim=None) -> tuple[np.ndarray, np.ndarray, dict]
    # leak[col] = w_anc[col] + w_inv[col], both DIRECT (no 1 - sum|M|^2); info = {"max_bond_dim", "seconds",
    # "w_anc", "w_inv", "leak_derived" (the old subtraction value, diagnostic only)}. Raises ValueError if n_data > 16.
# su2plaq/compress/spec.py
@dataclass class TaskSpec: ... tol_err: float = 1e-10; tol_gauss: float = 1e-10; eps: float = 1e-6; ...   # tol_leak REMOVED
# su2plaq/compress/evaluate.py: evaluate(..., tol_err=spec.tol_err, tol_gauss=spec.tol_gauss, gauss=True) for exact verdicts;
#   synthesised: **synth_tolerances(n_rot, spec.eps); "ok and not certified" -> "unverified" (prompts/003 §3 unchanged).
# su2plaq/results/store.py: _VERDICT_KEYS += ("block_error", "leak_amplitude"); results/report.py: column "leak amp" (keep "max leak").
```
Unit tests the builder must update (not locked): `tests/unit/test_evaluator_unit.py` (`synth_tolerances` formula, `tolerances` dict, every `tol_leak=` kwarg, certification cases incl. the one that relied on `tol_leak` being the minimum), `tests/unit/test_results_unit.py` (Verdict constructor), any `aer_mps_block` leak-semantics test in `tests/unit/test_sparse_sim_unit.py`. Add unit tests: (i) `aer_mps_block` direct weights on the synthetic exact circuit of `scratch/planner/proto_leak_amplitude.py` are $\le10^{-19}$; (ii) sparse vs aer_mps `leak_amplitude` on `cry(1e-3)` data→ancilla (sparse exact $5\cdot10^{-4}$; aer bound within $[1,4]\times$ of it).

## 4. Milestone / steps (M0 gate reopened for this one step; then benchmark + tag as before)
| Step | What | Done-check (tester) | Acceptance ids that must turn green |
|---|---|---|---|
| 0.11 | §3 interface in `evaluator.py`, `aer_check.py`, `spec.py`, `compress/evaluate.py` (stub-level), `store.py`, `report.py`; unit tests updated | `pytest -n auto tests/unit`; `pytest -n auto -m "not slow" tests/acceptance/m0`; `~/.claude/bin/acceptance-check` | `tests/acceptance/m0/test_evaluator.py::test_M0_E3_sensitivity`, `::test_M0_E5_gauss_of_outputs`, `::test_M0_E6_leak_is_judged_as_amplitude`, `tests/acceptance/m0/test_results.py::test_M0_R1_results_json_and_report` (unchanged, must stay green) |
| then | M0 gate continues: `tester` full (m0), `auditor` recheck of the diff of 0.11 + N2–N4/N7–N9, `tester` benchmark, tag `milestone-0` | per prompts/002 §3 | all m0 |
| M1 | unchanged steps; the amended ids below replace the old assertions | | `m1/test_twelve_circuits.py::*`, `m1/test_twelve_results.py::test_M1_R1_results_files[*]`, `m1/test_twelve_paulo.py::test_M1_P1_paulo_qpy_verifies`, `m1/test_twelve_metrics.py::test_M1_T1_t_table_and_synth_verify[*]` |
| M2 | unchanged steps; `TaskSpec` without `tol_leak`, loop evaluator rejects small ancilla leaks | | `m2/test_compress_machinery.py::test_oracle_matches_exact_step`, `::test_evaluator_accepts_general_circuit`, `::test_evaluator_rejects_small_ancilla_leak` (new) |

## 5. Acceptance tests changed (locked files; coordinator re-locks → `acceptance-v4`)
| Test id | Change | Justification |
|---|---|---|
| `m0/test_evaluator.py::test_M0_E3_sensitivity` | identity: `leak_amplitude <= 1e-14`, `max_leak <= 1e-28`; X-on-ancilla: additionally `leak_amplitude >= 1-1e-12`, `op_norm_error >= leak_amplitude` | an exact identity has leak exactly 0 (sparse, no subtraction): $10^{-14}$ amplitude is $10^{-28}$ weight; a full flip is amplitude 1 |
| `::test_M0_E5_gauss_of_outputs` | `tolerances == {tol_err, tol_gauss}` (both calls); aer clause: `tol_err=1e-9, tol_gauss=1e-9` (no `tol_leak`), `leak_amplitude <= 1e-9`, `max_leak <= leak_amplitude**2 + 1e-30`; swap case: `leak_amplitude <= 1e-12` | $10^{-9}$ stays the aer_mps certification minimum: combined engine noise $\le2\cdot10^{-10}+3.9\cdot10^{-10}$ (research/003 §4); the swap is code-preserving, leak exactly 0 |
| `::test_M0_E6_leak_is_judged_as_amplitude` (**new**) | `cry(θ)` data $q_j$→ancilla, target $I$: $\|X\|_2=\sin(\theta/2)$ within $10^{-3}$ relative; θ = $1.9\cdot10^{-6}$ (auditor's accepted case) and $10^{-8}$ rejected with a leak reason and non-empty `failing_inputs`; θ = $10^{-10}$ (amplitude $5\cdot10^{-11}$) accepted; same θ = $1.9\cdot10^{-6}$ under `synth_tolerances(1, 1e-6)` accepted; leak into an invalid data code (`x; cry(θ, q_j, q_m'); x`) rejected with reason `leak`, `dirty_ancilla <= 1e-30`; `op_norm_error == block_error + leak_amplitude` to $10^{-15}$ (sparse) | $X^\dagger X=\sin^2(\theta/2)\,\Pi_{j_b=1/2}$ exactly (link spins are quantum numbers of the basis states), so the value is analytic; $10^{-3}$ relative leaves room for a bounding implementation; the accepted θ = $10^{-10}$ case pins the threshold at amplitude $10^{-10}$ with a factor-2 margin so the rule is not implemented stricter than decided |
| `m1/test_twelve_circuits.py::test_M1_E1_electric_step[*]`, `::test_M1_B1_magnetic_inner_block`, `::test_M1_B2_physical_states`, `::test_M1_B4_outer_blind_and_clean`, `::test_M1_S1_step_orders[*]` | `max_leak <= 1e-12` / `dirty_ancilla <= 1e-12` → `leak_amplitude <= 1e-10` and weights `<= 1e-20` | exact-angle circuits: weight $=$ amplitude$^2\le(10^{-10})^2$; float64 over $\le3\cdot10^3$ gates gives $\sim10^{-13}$ amplitude, $10^{-26}$ weight, so $10^{-20}$ has a $10^6$ margin and is consistent with the amplitude rule (tightened, never loosened) |
| `m1/test_twelve_results.py::test_M1_R1_results_files[*]` | `verification.leak_amplitude <= 1e-10`, `max_leak <= 1e-20`, `block_error <= op_norm_error` | results JSON carries the new fields; same numbers as above |
| `m1/test_twelve_paulo.py::test_M1_P1_paulo_qpy_verifies` | `tol = {tol_err: 2e-5, tol_gauss: 2e-5}`; asserts `op_norm_error <= 2e-5`, `block_error <= 1.6e-5`, `leak_amplitude <= 2e-5`, `max_leak <= leak_amplitude**2`, `dirty_ancilla <= max_leak` | $\le16$ rotations at $\varepsilon=10^{-6}$ bound block error and leak jointly by $1.6\cdot10^{-5}$ (RSS); the sum may reach $\sqrt2\times$ that $=2.3\cdot10^{-5}$ in the worst case — measured $1.08\cdot10^{-5}$ (margin 1.9 against $2\cdot10^{-5}$), with the aer_mps leak bound at most 4× pessimistic; **this is the one amended test whose margin is below 2 — see §7** |
| `m1/test_twelve_metrics.py::test_M1_T1_t_table_and_synth_verify[*]` | `tol = {tol_err: n_rot ε + 1e-9, tol_gauss: n_rot ε + 1e-9}`; `synth_tolerances == tol`; `leak_amplitude <= tol_err`; `engine == "sparse"` | same budget as before, now covering block error + leak amplitude; the sparse engine is exact (STATUS notes M1-T1 must stay on sparse) |
| `m2/test_compress_machinery.py::test_oracle_matches_exact_step` | `spec.tol_gauss == 1e-10 and not hasattr(spec, "tol_leak")` | audit N1 + N6: one amplitude budget plus the Gauss tolerance in the spec |
| `::test_evaluator_accepts_general_circuit` | `leak_amplitude <= 1e-10`, `certified`, `gauss_residual <= 1e-10` | N6: `gauss=True` mandatory in the loop |
| `::test_evaluator_rejects_small_ancilla_leak` (**new**) | general circuit + `cry(1.9e-6, d[2], fresh ancilla)` → `not valid`, `leak_amplitude >= 9e-7`, `op_norm_error > 1e-10` | the auditor's scenario in the loop: a hard-coded rounded angle in an uncompute step must not be archived as exact |
Nothing was loosened: every weight bound became $\le$ (amplitude bound)$^2$; `tol_err` values are unchanged; M0-E5's aer clause keeps $10^{-9}$. Collection: `PYTHONPATH=. pytest --collect-only -q --noconftest tests/acceptance` → 86 tests, clean. The amended M0 tests currently fail with `AttributeError: 'Verdict' object has no attribute 'leak_amplitude'` (the unimplemented interface), as intended.

## 6. Consequences for M1 / M2
* M1-E1/B1–B4/S1 (exact-angle): leaks are $\sim10^{-30}$ or $O(1)$; no change in outcome, only in what is asserted.
* M1-P1: survives with combined $1.08\cdot10^{-5}$ (aer_mps). If the builder's direct-weight implementation differs from the prototype by more than float noise, compare with `scratch/planner/proto_leak_amplitude_paulo.npz` (`dir_anc`, `dir_inv`, `M` per input).
* M1-T1 (synthesised UE/UB/step at $\varepsilon=10^{-6}$ on the sparse engine): gridsynth words tilt the rotation axis, so part of each $\le\varepsilon$ error becomes leak into invalid codes ($j$-qubit flips with $q_mq_{m'}\neq00$) or span leak (flip to the valid code `100`), caught by Gauss. Expected combined $\lesssim1.3\times$RSS $\approx1.3\sqrt{N_{\rm rot}}\varepsilon$ for random-axis errors, well inside $N_{\rm rot}\varepsilon$ for $N_{\rm rot}\ge4$; worst case $\sqrt2N_{\rm rot}\varepsilon$ (§7).
* M2 loop: `TaskSpec.tol_leak` disappears; proposer briefs/spec text must state the criterion as "block error + leak amplitude ≤ $10^{-10}$, Gauss ≤ $10^{-10}$". A proposer program with a rounded constant ($0.785398$ for $\pi/4$, error $\sim10^{-7}$) now fails as `leak`/`error` instead of being archived.
* `results/` JSON written before this change (none in `results/` yet besides tests) would lack `leak_amplitude`; `save_result` treats the two new keys as optional (M0-R1's fixed dict has none of them).

## 7. Risks and stop conditions
* **$\sqrt2$ band (sum vs RSS).** For a *correct* synthesised circuit the rigorous bound is RSS $\le N_{\rm rot}\varepsilon$, while the adopted sum can reach $\sqrt2N_{\rm rot}\varepsilon$ (each of $\|A-e^{i\varphi}V\|$ and $\|X\|$ individually $\le N_{\rm rot}\varepsilon$). **Stop and ask Digonto** if a synthesised circuit has `block_error ≤ tol_err` and `leak_amplitude ≤ tol_err` but `op_norm_error` in $(\texttt{tol\_err},\ \sqrt2\,\texttt{tol\_err}]$: that is a tolerance-form question (switch to RSS = `hypot(block_error + dropped_total, leak_amplitude)`, a one-line change plus a re-lock of M0-E6's last assertion), not a bug. Do not loosen the budget.
* **aer_mps leak noise on more entangled circuits.** Measured floor $\le3.9\cdot10^{-10}$ (amplitude, 16-input worst case) on bond-dimension-≤16 circuits only. If an exact-angle circuit evaluated through aer_mps shows `leak_amplitude` in $(4\cdot10^{-10},10^{-9}]$ with the sparse engine giving 0, it is engine noise: stop and ask before any change to `MPS_ACCURACY` or the $10^{-9}$ minimum.
* **aer_mps √17 ≈ 4.12× pessimism** (was "4×"; corrected per reports/tests/014). The Cauchy–Schwarz bound can reject a correct synthesised circuit whose true leak amplitude is within budget but whose bound is not (only when the sparse engine is unavailable). Remedy if it happens: compute $(X_o^\dagger X_o)_{ii'}$ with mixed transfer matrices on the ≤16-input supports (exact to MPS accuracy, more code) — planner step, not builder.
* The `inner_span` fast path: `block_error` must be `max(inner-span error, physical error)` (audit N2), never the inner-span error alone.

## 8. Do-not-retry
* A weight tolerance of any kind for leak (`tol_leak = tol_err**2` included): $\max_kw_k\le t^2$ is weaker than $\|X\|_2\le t$ by up to $\sqrt{433}$ for coherent leak, and for aer_mps a subtraction-derived weight has $10^{-11}$ noise.
* Deriving the aer_mps leak as $1-\sum_{\rm codes}|M|^2$ or $1-\langle\Pi_{\rm anc=0}\rangle$ (cancellation; reports/tests/008 and research/003 §4).
* Turning `max_span_leak` into an amplitude via $w_{\rm code}-|A|^2$ (same cancellation); the Gauss residual already bounds it at first order.
* Raising the MPS bond dimension / lowering the truncation threshold to reduce engine noise (prompts/003 §6).

## 9. Expected cost
Sparse: one 433×433 `eigvalsh` (~30 ms) + Gram accumulation per outer block (negligible) → evaluator time unchanged within the 10 % benchmark threshold. aer_mps: + 3471 contracted amplitudes and + (n_anc + n_outer) transfer-matrix contractions per input: Paulo's circuit 67 s for 625 inputs in the prototype (108 s in the current evaluator, which also runs the Gauss decode) — expect ≤ +20 %. Builder: ~60 lines in `evaluator.py`, ~50 in `aer_check.py`, ~10 in `spec.py`/`store.py`/`report.py`, unit-test updates.
