# 002 — M0 audit recheck (after prompts/004 and audit-001 fixes)

- Date: 2026-11-04
- Auditor: `auditor` agent (Opus 5.5, high)
- Commit range: `8bab9da..30b38a0` (`git diff 8bab9da..30b38a0 -- src/ docs/METHODS.md prompts/004*`, 11 files, +268/−83)
- Plan in force: `prompts/002-…` + `prompts/003-…` + `prompts/004-leak-amplitude-combined-error-bound.md` (acceptance-v4)
- Related: `reports/audits/001-m0-foundation-audit.md`, `reports/research/003-leak-amplitude-bound.md`, `reports/tests/014-m0-gate-rerun-after-audit.md`

**Verdict: PASS WITH NOTES.**
- The combined bound is implemented as research/003 derives it.
- The aer_mps form is a valid upper bound, checked by hand and numerically.
- N2, N3, N4, N7, N8 and N9 are resolved.
- No new silent error found.
- Two minor notes (R1, R2) are listed below.

Probe scripts are in `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/` (`b1.py`, `b2.py`). They were run with `PYTHONPATH=src python <script>` at commit 30b38a0.

## Combined bound (prompts/004 §2): checks

| Claim | Status | Evidence |
|---|---|---|
| `op_norm_error = block_error + dropped_total + leak_amplitude` | OK | `evaluator.py:457`; `_early` sets all three to $\infty$. |
| Sparse $\|X\|_2=\sqrt{\lambda_{\max}(X^\dagger X)}$ over physical inputs | OK | `evaluator.py:414-419, 454`. $X^\dagger X=\sum_o\big[(X^{\rm anc}_oP_o)^\dagger X^{\rm anc}_oP_o+(X^{\rm inv}_oP_o)^\dagger X^{\rm inv}_oP_o\big]$ is scattered into `ks`. The cross terms vanish for two reasons: different outer patterns are orthogonal because the outer register is never written, and ancilla-set keys are disjoint from invalid-data keys. Result: one `eigvalsh` of the Hermitised 433×433 matrix, clipped at 0. |
| Span leak: $\max_k\|s_k\|\le4\,$`gauss_residual` | OK as a per-state statement (see R1) | Valid argument: corners commute, so $\sum_{c,a}(G^a_c)^2=\sum_c\hat J_c^2$. Its spectrum is $\{\sum_cJ_c(J_c+1)\}$ with smallest non-zero value $\tfrac34$. $\mathcal P$ is the full joint kernel (route A builds every singlet, 433 states). The 12 terms give $\max_{c,a}\|G^a_cs\|\ge\|s\|/4$. Also $G\Psi=0$, and the evaluator's residual is taken on the decoded code-space output (`evaluator.py:460-472`). |
| aer_mps: direct weights | OK | `aer_check.py:99-119`. The first-set-ancilla decomposition is disjoint. I checked the transfer-matrix algebra by hand: left environment $E\to A^{s\dagger}EA^s$, right environment $R\to\bar A^sRA^{s\mathsf T}$, term $\sum_{ij}E_{ij}R_{ij}=\|pv\|^2$. $w^{\rm inv}$ contracts all $2^{12}-625=3471$ invalid data patterns with the pinned qubits at 0. The two sets are disjoint and, together with the code space, complete. No $1-\sum$ subtraction remains in the verdict path (`leak_derived` is a diagnostic only). |
| aer_mps: $\|X\Psi\|_2^2\le\max_oW_o$ | OK, valid upper bound | `evaluator.py:420-424, 450-452`. The Cauchy–Schwarz chain is correct: $\|X_oP_oc\|\le\sum_{i\in{\rm supp}}|(P_oc)_i|\sqrt{w_i}\le\|P_oc\|\sqrt{W_o}$, and $\sum_o\|P_oc\|^2=1$. $W_o$ uses the weights of the read-group circuit that block $o$ actually ran. Numerically (`b2.py`, sparse exact against aer bound): `cry(1e-3)` data→ancilla $5.000\cdot10^{-4}$ against $2.000\cdot10^{-3}$ (ratio 4.000); an ancilla-branch leak spread over m-bits $1.000\cdot10^{-3}$ against $4.123\cdot10^{-3}$ (ratio $4.123=\sqrt{17}$); leak into an invalid code $5\cdot10^{-4}$ against $1\cdot10^{-3}$ (ratio 2). The bound is never below the exact value. Block errors agree ($1.25\cdot10^{-7}$, $5.0\cdot10^{-7}$). |
| Engines cannot mix inside one verdict | OK | `evaluator.py:399`: after the first group the engine is fixed to the one used, so `wa`/`wi` exist exactly when `used == "aer_mps"`. |
| Reason order and failing inputs | OK | Order: `pruning_bound`, then leak reasons (when `leak_amplitude > tol_err`), then `error`, then `gauss`. For leak reasons `failing_inputs` is never empty and is not filtered by the tolerance. |
| `tol_leak` removed everywhere | OK | `evaluate`, `synth_tolerances`, `Verdict.tolerances`, `TaskSpec` (now `tol_gauss=1e-10`). |

## Audit-001 notes

| Note | Status | Evidence |
|---|---|---|
| N1 leak as amplitude | RESOLVED | As above; tester 014 shows the `cry(1.9e-6)` case is rejected (M0-E6). |
| N2 inner_span | RESOLVED | `evaluator.py:439-446`: `block_error = max(inner_span, physical)`; both errors are kept in `extra`. |
| N3 aer per-input leak | RESOLVED | Direct weights plus the per-block bound above. |
| N4 `qubits_initially_zero` | RESOLVED | `sparse_sim.py:174,185`, `logical.py:28`, `cliffordt.py:79`, `aer_check.py:34`. Side-effect check (`b1.py`): `ct_compile` on Paulo's uncompiled circuit gives CX 294, T 1162, depth 2549 with both `False` and the default, so his counts are unchanged (needed by M1-P2). |
| N5 route-B signs | DEFERRED (M3) | by design |
| N6 loop `gauss=True` | DEFERRED (M2) | by design; `TaskSpec.tol_gauss` added |
| N7 ValueError mapping | RESOLVED | `evaluator.py:353-357`: layout errors now give `bad_layout`. Errors raised during gate translation still give `disallowed_gate`; that is acceptable. |
| N8 docstring and `extra` | RESOLVED | Module docstring rewritten; `verdict_to_dict` persists `extra`; `_VERDICT_KEYS` include `block_error`, `leak_amplitude`. |
| N9 sign tie-break | RESOLVED | `physical.py:28-36`: the first index within $10^{-10}$ of the maximum modulus is chosen. Distinct modulus levels in these singlets are $O(0.1)$ apart, so the choice is deterministic. Tester 014 found the basis identical between 1 and 8 BLAS threads and under $10^{-13}$ noise. |

## New notes (NON-BLOCKING)

### R1 — The span-leak bound is per state; the full-error statement over superpositions is not
The Gauss residual is a maximum over basis states $k$. The quantity that enters $\|E\|_2$ (research/003 Eq. 1) is the operator norm $\|S\|_2$, which can exceed $\max_k\|s_k\|$ by up to $\sqrt{433}\approx20.8$ when the span leak is coherent. Example: an error of rank one in the direction of a uniform superposition of physical states, $\Delta U=\delta|v\rangle\langle w|$ with $w=\sum_k\psi_k/\sqrt{N}$, gives each state only $\|s_k\|=\delta/\sqrt N$ but $\|S\|_2=\delta\|Qv\|$, where $Q$ projects onto the span-leak space (code space minus physical span). This is the same per-state versus operator-norm gap that prompts/004 §8 rejects for $X$. Tester 014 found $X^\dagger X$ diagonal to $10^{-18}$ for local (single-qubit-type) errors, so realistic circuit errors are unlikely to reach this case. METHODS and research/003 state the bound correctly as per-state, but "Span leak S is controlled by the Gauss check" should not be read as an operator-norm guarantee.
Cheap fix if wanted (planner): use an operator-norm residual, $\|S\|_2\le\sqrt{\tfrac43\,\lambda_{\max}\big(\sum_{c,a}(G^a_cY)^\dagger(G^a_cY)\big)}$, where $Y$ is the matrix of decoded outputs. This is one 433×433 Gram matrix accumulated over 12 $(c,a)$ pairs, which `gauss_residuals_coo` almost forms already. Then $\|E\|_2\le$ `op_norm_error` $+\|S\|_2$ is rigorous.

### R2 — The `certified` flag for aer_mps is below the documented minimum
`evaluator.py:475` certifies when `MPS_ACCURACY (2e-10) <= min(tol_err, tol_gauss)`. METHODS §6 and prompts/004 §2 say the combined aer_mps noise is $\le2\cdot10^{-10}+3.9\cdot10^{-10}$ and that $10^{-9}$ is the smallest certifiable aer_mps tolerance. An aer_mps verdict at `tol_err` in $[2\cdot10^{-10},10^{-9})$ is therefore marked `certified=True` against the documented policy. No current test or call uses that range (M0-E5 uses $10^{-9}$; Paulo uses $2\cdot10^{-5}$).
Fix: compare against a combined aer accuracy of about $6\cdot10^{-10}$ (or require `tol_err >= 1e-9` for aer_mps), plus a unit test at `tol_err=5e-10`.
