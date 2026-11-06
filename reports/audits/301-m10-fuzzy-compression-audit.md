# Audit 301 — M10 fuzzy compression (hook, proposer programs, composed step, Report 10)

Date: 2026-11-06 · Auditor (Claude Opus 5.5) · Branch `m9-fuzzy` · Commit range `milestone-9..54691ea`, plus the hook commit `75ef2e6` (`src/su2plaq/fuzzy/compress_hook.py`, `src/su2plaq/fuzzy/sitehook/sitecustomize.py`, committed before the `milestone-9` tag) · Plan in force: `prompts/302-fuzzy-m10-plan.md` (locked tests `tests/acceptance/m10`, tag `acceptance-v11`, unchanged since the tag) · Methods: `docs/METHODS-fuzzy.md` F9 · Report draft: `docs/report-10-fuzzy-compression.md` · Tester: `reports/tests/302` (a final tester run is in progress at the same time and was not repeated here).

## Independent checks run (scratch only, `taskset -c 0-7`, 1 thread)
Script: `/tmp/claude-1020/-home-digonto-Projects-su2qc-fuzzy-package/bfa57115-624a-4ad1-8042-64ca0dd2e2f1/scratchpad/aud.py`.
- Link best `r02-F2-001`, rebuilt through the laptop worker (`circuit_of_entry`) at 7 points that are not validation points: $(\alpha,\kappa_2)=(0.37,0.185)$ (the step's $r=1$ point), $(0.37,0)$ ($r=0$), $(0,0.5)$, $(2.9,-1.3)$ and 3 random points in $[-3,3]^2$. Compared against `targets.UEK_link` with a dense `Operator`: max error $7.2\times10^{-15}$.
- U_B best `r03-F3-003`, laptop `evaluate_circuit(mode="full")` (all 256 columns, ancilla leak) at $\beta\in\{0.61,-0.8,2.7,10^{-3}\}$ and 2 random values: all valid, error $\le1.1\times10^{-13}$, leak 0, dirty ancilla 0.
- pygridsynth T count of the link unit at the step's angles $(0.37,0.185)$: 644, the same as at the unit's nominal $(0.37,0.61)$. The unit-sum T totals in Report 10 §3.3 therefore hold at the composed step's own angles.

## Checklist

| Item | Verdict | Where / note |
|---|---|---|
| Equations match METHODS F9 term by term | OK | `targets.py:29-36`: $U_{EK}=e^{-i(\frac\alpha2\mathcal K_1+\kappa_2\mathcal K_2)}$, $U_B=e^{+2i\beta\square}$. `compress_hook.py:68,104`: the oracle targets are exactly `tg.UB_row(beta)` and `tg.UEK_link(alpha, kappa2=spec.beta)`, reached through `oracle._target_cached -> get_encoding(enc).target` (oracle.py:31-41). Link angles $\pm\alpha/4$ (=$2\cdot\frac\alpha2\cdot\frac14$) and $\pm2\kappa_2$ match the $\frac14$ and $1$ coefficients of the 10 Z-strings. |
| Time-evolution sign and ordering | OK | `compose_step` (`compress_hook.py:217-225`): inner kinetic, then $U_B$, then outer, as `build_step` (H3 count equality, orders 1 and 2). For order 2 the inner blocks use half angles and the outer blocks full angle once, as in M9. |
| Basis / index conventions | OK | Frame qubit $i$ is circuit qubit `ROW_QUBITS[i]`, so the frame index is $\sum_l(2q_1^l+q_2^l)4^l$, the F1 row index. Evaluator data = positional qubits `range(n)` (`FuzzyBlockEncoding.layout_of`, `verify.py:50-60`), the same positional rule as `compose_step` / `ub_frame_to_full`, so the two views agree. The composed step is checked independently against `targets.apply_step`. |
| Truncation | N/A | Exact units; no cut-off. |
| Normalisation / phases | OK | One global phase per unit (evaluator) and per composed step (`verify_step_samples`). F2 r3 drops the segment `global_phase` and the $e^{-ik\pi/8}$ of the rz→T/S conversion. Both are phases of uncontrolled whole-register segments, so they are global, they do not depend on angle, and the evaluator removes them. |
| Precision | OK | complex128 throughout; errors $10^{-15}$–$10^{-13}$ against tolerance $10^{-10}$. |
| Randomness / seeds | OK | verify seed 20261104, trial seed in spec, transpile `seed_transpiler=0..3` in F2 programs (deterministic). |
| Validity rules preserved by the hook (focus a) | OK, with a note | See A1. No laptop file is edited (`git diff 9b5443d..HEAD -- src/su2plaq/compress src/su2plaq/evaluate` is empty). The patched `EV.evaluate` is picked up because `_one_verdict` imports `evaluate` inside the function (`compress/evaluate.py:173-174`). The patch removes only the Gauss residual. Error, leak, dirty-ancilla and `certified` are unchanged (`evaluator.py:339-470`). Skeleton equality and the alternate-pair checks are laptop code (`compress/evaluate.py:226-243`) and the hook does not touch them. Peak-qubit cap: `TaskSpec.peak_qubit_cap` patch gives 40 (UB) and 4 (link), enforced at `compress/evaluate.py:218`. |
| Link valid for every $\kappa_2/\alpha$ ratio (focus a) | OK, with a note | Alternates (0.91, 0.23) and (1.70, 1.00) plus nominal (0.37, 0.61) give three different ratios (1.65, 0.25, 0.59). The best program is a fixed Clifford skeleton with angles linear in $(\alpha,\kappa_2)$ (`F2/001...py:30-36`). My 7 extra points are exact. A rules-level gap remains: see A2. |
| Emission-time transpile (focus b) | OK | `F2/003...py:244-252` (and F2/002): every `rz`/`crx` (the only β-dependent gates) is emitted directly. Only β-free segments go through `transpile(..., optimization_level=3, seed_transpiler=s)`, so the transpiled output does not depend on β. The rz→{t,s,z,sdg,tdg} rounding acts only on constant angles. The only β-dependence of the skeleton is the `abs(a) > 1e-12` term filter, which matters only at measure-zero β (e.g. β = 0, where the circuit is the identity and still exact). Neither F2 program is used in the composed step. Remaining dependence on the Qiskit version: see A5. |
| Best U_B program is not hard-coded (focus c) | OK | `F3/003-r-fold-sectors-1-5.py`: no oracle import or call. The only angle input is `spec.beta` (`:156`). Angles are $-4\beta s\,2^{|pairs|}$ (`:211`) and an emission-time least-squares fit `group_unsplit` (`:107-123`) whose right-hand side is linear in β, with an exactness assert. `PLAN`/`SUPPORT` are structural constants, the same for every β. There is no branching on angle values. My random-β evaluation confirms the program is exact for general β. |
| No proposer-written src (focus d) | OK | `git diff milestone-9..HEAD --stat -- src scripts tests` is empty. All 5 src commits since the branch point are by `pichka_commander` (coordinator). Proposer output is only under `compress/programs/fuzzy_*`. |
| Tests test the claim | OK | H2/G1 run `evaluate_circuit` / `evaluate_program` (the production path). G3 calls `best_step` + `verify_step_samples` and compares the result to `compressed_step.json`. The composed check is at $\kappa_2=\alpha/2=0.185$, which is not a unit validation point, so it is an independent off-sample test of the link unit. |
| Provenance (focus e) | ISSUE (NON-BLOCKING) | See A3 and A4. All unit table numbers match `results/compress/fuzzy_{ub,link}/summary.json` (`rows`). The composed rows match `compressed_step.json` (295 CX, 148 rot, 118 T_fixed, 53 qubits, err $1.69\times10^{-14}$, Gauss $5.9\times10^{-15}$). Unit sums are consistent: $151+12\cdot12=295$, $28+120=148$, $2822+4\cdot644=5398$, $1902+4\cdot644=4478$, $2822+12\cdot644=10550$, $1902+12\cdot644=9630$. |
| T($10^{-6}$) unit-sum method (focus e) | OK | ε is per rotation (synth bound reported as $n_{\rm rot}\times10^{-6}$, e.g. 28 rotations → $2.8\times10^{-5}$; link `synth_error_bound` $10^{-5}$ for 10 rotations), so the unit counts add at the same per-rotation precision. The total synthesis error of the composed step is $\le148\times10^{-6}$ by the triangle inequality. The link T count is the same at the step angles (644 at $(0.37,0.185)$, measured). |

## Issues

### A1 — `gauss_residual` reported as 0.0 instead of "not checked" (NON-BLOCKING)
`compress_hook.py:436`: `v.gauss_residual = 0.0` after the evaluator ran with `gauss=False`. The physics argument is sound. Both unit targets commute with every $\mathcal T^A$ (audit 300 A1/A3), and full-block exactness on all $2^n$ computational codes gives
$\|G\,U\psi\|\le\|G\,(U-e^{i\varphi}V)\psi\|+\|[G,V]\psi\|\le\|G\|\,\varepsilon$.
So no validity rule is weakened. But the stored verdicts and archive entries show a measured-looking 0.0 that was never computed.
**Fix:** set `float("nan")`, or add `v.extra["gauss"] = "not_checked (F9)"`. Cosmetic.

### A2 — angle-function generality is checked at 3 points only (rules-level, NON-BLOCKING)
The laptop rules (identical skeleton plus exactness at 3 angle pairs) do not stop a program whose angles are a nonlinear function of $(\alpha,\beta)$ that is correct only at the 3 points. For `fuzzy_link` this matters more than for `twelve`, because the step uses the unit at $\kappa_2=r\alpha/2$, which is never a validation point. For the current best entries it is not a problem: both programs are visibly angle-linear, my 7 (link) and 6 (U_B) off-sample points are exact, and G3 tests the link at (0.37, 0.185).
**Suggested test** (for the merge, not this gate): in G1, also evaluate the best entry at 2 seeded random angle pairs (and $\kappa_2=0$ for the link) with the full evaluator.

### A3 — Report 10 commit and provenance inconsistent (NON-BLOCKING)
Report 10 header: "Commit of the numbers: `15a12fa`". But `compressed_step.json` records `git_commit: 7b0e5d0, git_dirty: true`. src is identical across 7b0e5d0..HEAD, so the numbers are reproducible, but the header should name the commit actually recorded.
Two numbers in §3.3 do not come from the cited sources:
- "before, all 12 links: err $1.1\times10^{-14}$": `compressed_step.json` does not verify `general`. The value matches `results/fuzzy/step.json` (op_norm_error $1.05\times10^{-14}$).
- "before, inner only: depth 2690": this is Report 9 Table §3 (`report-9...md:71`). It equals the with-outer depth of `general` in the JSON.

**Fix:** cite `results/fuzzy/step.json` / Report 9 for these cells, and fix the header commit.

### A4 — Report 10 still has placeholders and one wording mismatch (NON-BLOCKING; must be done before the tag)
- `TESTER-VERDICT-LINE` appears twice (intro and §5). Fill it in from the final tester report.
- §3.1, "Qiskit L3, whole circuit": the reported verdict "unverifiable by the exact engine" matches summary.json. The prose "the invalid one is the Qiskit L3 seed, rejected by the pruning bound" refers to the *windowed* L3 row (1629 CX, `invalid: pruning_bound`), which the table does not show. Add that row or reword.
- §3.3 "after, inner only: 21 qubits, depth —": these come from no JSON. The tester's inner-only JSON is for the round-2 units. They are derivable (16 + 5 ancillas), but say so.

### A5 — F2 emission-time transpile depends on the Qiskit version (NON-BLOCKING; already disclosed)
`F2/002`, `F2/003`: the emitted circuit is a function of the Qiskit 2.5.2 level-3 pass manager. It stays valid under any version, because the evaluator re-checks every build. But the archived key (165 CX) may not reproduce after an upgrade, and G1's "key equal" would then fail for those entries. Report 10 §5 states this. Neither entry is the global best, so the composed result does not depend on it.
**Suggestion:** record `qiskit.__version__` in the entry provenance (the JSON provenance already records it at the step level).

## Verdict
**PASS WITH NOTES.** There are no blocking issues:
- The hook keeps every laptop validity rule except the per-unit Gauss check, and dropping that check is justified.
- The targets are the exact `UB_row` / `UEK_link(alpha, kappa2=spec.beta)`.
- The best programs are angle-linear, not hard-coded, and exact at off-sample angles.
- No proposer code is in src.
- The composed step (295 CX, err $1.7\times10^{-14}$) and the unit-sum T totals are sound.

A4 (placeholders) must be resolved before tagging milestone-10.
