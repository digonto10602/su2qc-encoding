# 003 — Addendum to prompts/002: Gauss-law tolerance for synthesised circuits, engine-certification policy

Date: 2026-11-04. Planner (Fable 5.1). **prompts/002 stays the plan in force; this addendum amends only its §2.7 (evaluator interface), §2.11 (results schema), §6 (tolerances) and the engine policy of METHODS §6.** Everything not mentioned here is unchanged.

## 0. Trigger
`reports/tests/009-m0-step-0-8-evaluator.md` finding F2: the evaluator applies a fixed Gauss-law tolerance `TOL_GAUSS = 1e-10` to every circuit. Paulo's compiled circuit (rotations synthesised at $\varepsilon=10^{-6}$, op-norm error $2.9\cdot10^{-6}$, accepted under the synthesised-circuit budget $N_{\rm rot}\varepsilon+10^{-9}$) has Gauss residual $1.16\cdot10^{-10}$, so `test_M1_P1_paulo_qpy_verifies` (asserts `v.ok`) would fail on a circuit that is correct within its rounding. Related: F3 (gauge-breaking errors are first order in the Gauss residual but second order in the physical-block op-norm error), F4 (`ok=True, certified=False` hazard), reports/tests/008 (Aer MPS accuracy ~$2\cdot10^{-10}$).

**Decision (Digonto, 2026-11-04):** the Gauss tolerance of a synthesised circuit scales with its rounding — same allowance as the error tolerance, $N_{\rm rot}\varepsilon+10^{-9}$; exact-angle circuits keep $10^{-10}$.

## 1. Diagnosis
Not a bug in the Gauss check — a missing degree of freedom. The evaluator has three tolerances but only two were parameters. For an exact-angle circuit the output of a correct circuit is gauge invariant to float64 rounding ($\sim10^{-13}$), so $10^{-10}$ is right. For a synthesised circuit each rotation is replaced by a Clifford+T word within $\varepsilon$ of it (operator norm, up to phase), so the circuit's unitary differs from the exact one by $\|U-U_{\rm ex}\|_2\le N_{\rm rot}\varepsilon$ on the **whole** space (triangle inequality over unitaries). That error has a component outside the gauge-invariant subspace which the Gauss residual sees at **first** order while the op-norm error on the physical block sees it only at second order (prototype in `reports/research/002-gauss-tolerance-synthesised.md`: an `rx(δ)` on a data qubit gives Gauss residual $\sin(\delta/2)$ but physical-block error $\sin^2(\delta/2)$). Hence the Gauss residual of a correct synthesised circuit is legitimately of order $N_{\rm rot}\varepsilon$ and must have that budget.

## 2. Method: tolerances (replaces the "Tolerances:" sentence of METHODS §6 and the rows of prompts/002 §6 named below)

Let $\psi_k$ be a physical state, $V$ the target, $U$ the circuit's unitary on the full register, $U_{\rm ex}$ the same circuit with exact rotation angles (so $U_{\rm ex}\psi_k=e^{i\varphi}V\psi_k$ for a correct design), and $G^a_c=\sum_{\text{ends }e\in c}J^a_e$ the Gauss generator of corner $c$ (four spin-½ ends, $\|G^a_c\|_{\rm op}=2$, computed). Since $G^a_c V\psi_k=0$,
$$\|G^a_c\,U\psi_k\| \;=\; \|G^a_c\,(U-U_{\rm ex})\psi_k\| \;\le\; \|G^a_c\|_{\rm op}\,\|U-U_{\rm ex}\|_2 \;\le\; 2\,N_{\rm rot}\,\varepsilon .$$
The evaluator's `gauss_residual` is $\max_{c,a,k}\|G^a_c U\psi_k\|$ (METHODS §4, unnormalised, $J=\sigma/2$ convention).

| Circuit class | `tol_err` | `tol_leak` | `tol_gauss` | Justification |
|---|---|---|---|---|
| exact-angle (M1-E1, B1–B4, S1; M2 loop circuits) | $10^{-10}$ | $10^{-12}$ | $10^{-10}$ (default) | float64 over $\le10^4$ gates accumulates $\sim10^{-13}$; unchanged |
| synthesised at precision $\varepsilon$ with $N_{\rm rot}$ rotations (M1-T1; M1-P1 with $N_{\rm rot}\varepsilon\to$ the budget $2\cdot10^{-5}$ of its docstring) | $N_{\rm rot}\varepsilon+10^{-9}$ | $(N_{\rm rot}\varepsilon)^2+10^{-12}$ | $N_{\rm rot}\varepsilon+10^{-9}$ **(new)** | Digonto's rule: the same rounding budget as the error. The rigorous worst case is $\|G^a_c\|\,N_{\rm rot}\varepsilon=2N_{\rm rot}\varepsilon$; the measured ratio residual$/\|U-U_{\rm ex}\|$ is $1.0$ for an error on an $m$-type qubit, $0.5$ on a $j$-type qubit (16 cases, research/002), and the ratio can only exceed 1 if the synthesis errors of several rotations add coherently at all four ends of one corner. Paulo's circuit: residual $1.16\cdot10^{-10}$ vs budget $1.4\cdot10^{-5}$ ($N_{\rm rot}=14$). The $+10^{-9}$ floor covers the `aer_mps` engine noise ($\le2\cdot10^{-10}$ per amplitude) and float64. |
| `aer_mps` engine, exact-angle circuit used only as an engine cross-check (M0-E5 second clause) | $10^{-9}$ | $10^{-9}$ | $10^{-9}$ | the engine floor is $2\cdot10^{-10}$ (reports/tests/008), so no `aer_mps` verdict can be certified at $10^{-10}/10^{-12}$; $10^{-9}$ is $5\times$ the measured worst engine error. The sparse-engine assertions of M0-E5 stay at $10^{-10}$. |

**Stop condition added:** a circuit that passes `error` and `leak` but fails `gauss` with residual in $(\text{tol\_gauss},\,2\,\text{tol\_gauss}]$ is a tolerance question (the factor $\|G^a_c\|\le2$), not a bug — stop and ask Digonto; do not loosen.

## 3. Engine-certification policy (confirms reports/tests/008 and the `engine_accuracy` / `certified` fields)
* `engine_accuracy` = 0 for `sparse` (exact COO to float64, certified pruning bound included in `op_norm_error`), `MPS_ACCURACY = 2e-10` for `aer_mps` (measured worst per-amplitude error, reports/tests/008).
* `certified = engine_accuracy <= min(tol_err, tol_leak, tol_gauss_eff)` where `tol_gauss_eff` is the Gauss tolerance actually applied (the default $10^{-10}$ when `tol_gauss=None`); when `gauss=False` the minimum runs over `tol_err, tol_leak` only. `certified` is therefore `False` for every `aer_mps` verdict at the exact-angle tolerances — including the `auto` fallback — and `True` for synthesised-circuit budgets $\ge10^{-9}$.
* Consumers: every acceptance test that asserts `v.ok` also asserts `v.certified` (done in M0-E5, M1-P1, M1-T1); `compress/evaluate.py` treats `ok and not certified` as **unverified** (status `"unverified"`, never archived as valid; the round report lists it); results JSON stores `engine`, `engine_accuracy`, `certified`, `tolerances`.
* `gauss=True` is mandatory for acceptance and loop verdicts (F3: without it a gauge-breaking amplitude $\delta$ is seen only as $\delta^2$ in the op-norm error).

## 4. Interface change (builder; step 0.8 recheck, tiny)
```python
# su2plaq/evaluate/evaluator.py
TOL_GAUSS = 1e-10                      # default Gauss tolerance (exact-angle circuits) — unchanged
def evaluate(qc, enc, target, *, tol_err=1e-10, tol_leak=1e-12, tol_gauss: float | None = None,
             gauss=True, method="auto", engine="auto", cap=5_000_000) -> Verdict
    # tol_gauss None -> TOL_GAUSS. The 'gauss' reason and its failing_inputs use the effective value.
def synth_tolerances(n_rot: int, eps: float) -> dict
    # == {"tol_err": n_rot*eps + 1e-9, "tol_leak": (n_rot*eps)**2 + 1e-12, "tol_gauss": n_rot*eps + 1e-9}
    # the ONE place the synthesised-circuit rule lives; M1 steps 1.7/1.9 and compress/metrics pass **synth_tolerances(...)
@dataclass class Verdict: ...existing fields...; dropped_total; engine_accuracy; certified;
    tolerances: dict = field(default_factory=dict)   # {"tol_err","tol_leak","tol_gauss"} actually applied (tol_gauss = effective value)
    extra: dict
```
* `certified` computed as in §3. `_early(...)` verdicts also fill `tolerances`.
* `su2plaq/compress/spec.py::TaskSpec` gains `tol_gauss: float = 1e-10`; `compress/evaluate.py` passes `tol_gauss=spec.tol_gauss` and maps `ok and not certified` → `"unverified"`.
* §2.11 results `verification{…}` gains `engine, engine_accuracy, certified, tolerances` (M0-R1's fixed dict has none of them: they are optional keys, `save_result` must accept both).
* Callers that evaluate synthesised circuits in production (`metrics.cliffordt.synthesize` re-verification in step 1.7, results in 1.9) call `evaluate(synth, enc, V, **synth_tolerances(n_rot, eps))`.

## 5. Acceptance tests changed (locked files; coordinator re-locks with `acceptance-lock`)
| Test id | Change |
|---|---|
| `tests/acceptance/m0/test_evaluator.py::test_M0_E5_gauss_of_outputs` | sparse clause: additionally asserts `certified`, `engine_accuracy == 0`, `tolerances == {1e-10, 1e-12, 1e-10}`. `aer_mps` clause: tolerances $10^{-9}/10^{-9}/10^{-9}$ (was default $10^{-10}/10^{-12}$, uncertifiable), asserts `certified`, `0 < engine_accuracy <= 2e-10`, `gauss_residual <= 1e-9`; new third call: `aer_mps` at default tolerances is `not certified`. |
| `tests/acceptance/m1/test_twelve_paulo.py::test_M1_P1_paulo_qpy_verifies` | `tol_gauss=2e-5` (= `tol_err`) on both evaluate calls; asserts `gauss_residual <= 2e-5`, `certified`, `engine_accuracy <= 1e-9`, `tolerances == tol`. |
| `tests/acceptance/m1/test_twelve_metrics.py::test_M1_T1_t_table_and_synth_verify[UE/UB/step]` | `tol_gauss = n_rot·eps + 1e-9`; asserts `synth_tolerances(n_rot, eps) == tol`, `certified`, `tolerances == tol`. |
No m2 test evaluates a synthesised circuit (m2 uses pygridsynth T-counts only) — unchanged. Nothing was loosened for exact-angle circuits.

## 6. Do-not-retry
* Making `TOL_GAUSS` a module-level constant that callers mutate; a fixed Gauss tolerance tied to `tol_err` implicitly (callers must pass it; the default stays the exact-angle value).
* Certifying `aer_mps` verdicts at $10^{-10}$ by raising the MPS bond dimension or lowering the truncation threshold — the error is independent of the threshold (reports/tests/008).

## 7. Cost
Builder: ~20 lines in `evaluator.py` (+ `TaskSpec` field, `compress/evaluate.py` mapping, `save_result` keys). M0-E5 gains one `aer_mps` run (~5 s). No other runtime change.
