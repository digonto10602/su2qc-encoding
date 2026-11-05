# Research 003 — leak as an amplitude: the combined output-error bound and its aer_mps form

- Date: 2026-11-04. Planner (Fable 5.1). Commit: `8bab9da` (builder's audit-note fixes uncommitted in `src/`).
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` + `prompts/003-…` + `prompts/004-leak-amplitude-combined-error-bound.md` (this run's output).
- Related: `reports/audits/001-m0-foundation-audit.md` (N1, N3), `reports/tests/008-…` (Aer MPS accuracy, subtraction-leak noise $1.6\cdot10^{-11}$), `reports/tests/011-…` (Paulo QPY: error $2.905\cdot10^{-6}$, subtraction leak $4.19\cdot10^{-12}$), `reports/research/002-…` (Gauss residual is first order in a gauge-breaking amplitude).
- Prototype: `scratch/planner/proto_leak_amplitude.py` (production `evaluator._simulate`, 12-qubit encoding; `python … ` ≈ 25 s, `python … paulo` 67 s + setup; outputs in `scratch/planner/proto_leak_amplitude_paulo.log`, `.npz`).

Jargon, once: *leak* = output amplitude outside the code space (an ancilla not back in $|0\rangle$, or a data pattern that encodes no link state); *span leak* = output inside the code space but orthogonal to all physical (Gauss-law) states; *operator norm* $\|M\|_2$ = largest factor by which $M$ stretches any unit vector; *Gram matrix* $X^\dagger X$ = the matrix of all inner products of the columns of $X$; *isometry* = a map that preserves lengths.

## 1. Question
The evaluator's verdict compared a leak **weight** ($\sum|a|^2$) with $10^{-12}$ and an error **amplitude** (operator norm) with $10^{-10}$. Digonto decided to judge leak as an amplitude in one combined bound. What exactly is the quantity, why does it bound the full output error, what does the aer_mps engine (which never sees the out-of-code amplitudes) report instead, and do the locked M0/M1 circuits still pass?

## 2. The bound (linear algebra on the project's own definitions; only textbook facts are used: triangle inequality and submultiplicativity of the operator norm, $\|M\|_2\le\|M\|_F$, Cauchy–Schwarz — Horn & Johnson, *Matrix Analysis*, 2nd ed., Ch. 5)
$\Psi$ ($2^n\times433$, columns $\psi_k$, ancillas $|0\rangle$) is an isometry; $V$ is the 433×433 target; $U$ the circuit. Decompose each output into orthogonal pieces
$$U\psi_k=\Psi A_{:,k}+s_k+x_k,\qquad A=\Psi^\dagger U\Psi,\qquad s_k\in\mathcal C\cap\mathcal P^\perp,\qquad x_k\in\mathcal C^\perp,$$
($\mathcal C$ code space, $\mathcal P=\operatorname{range}\Psi$). With $S=[s_k]$, $X=[x_k]$ and the evaluator's phase $\varphi$, the error on the physical inputs is $E=(U-e^{i\varphi}\Psi V\Psi^\dagger)\Psi=\Psi(A-e^{i\varphi}V)+S+X$, three column-wise orthogonal terms, so for every unit $c\in\mathbb C^{433}$
$$\|Ec\|^2=\|(A-e^{i\varphi}V)c\|^2+\|Sc\|^2+\|Xc\|^2 .$$
Taking the maximum over $c$ of each term separately,
$$\|E\|_2\le\sqrt{\|A-e^{i\varphi}V\|_2^2+\|S\|_2^2+\|X\|_2^2}\le\|A-e^{i\varphi}V\|_2+\|X\|_2+\|S\|_2 . \tag{1}$$
The adopted criterion is the sum of the first two terms (plus the certified pruning bound `dropped_total`, which bounds the error of the sparse engine's own output, triangle inequality again):
$$\texttt{op\_norm\_error}=\|A-e^{i\varphi}V\|_2+\texttt{dropped\_total}+\|X\|_2\le\texttt{tol\_err},\qquad\|X\|_2=\sqrt{\lambda_{\max}(X^\dagger X)} .$$
It is an upper bound on the true error $\|E\|_2$ up to the span-leak term, and it is at most $\sqrt2$ times the root-sum-square (RSS) form (for two non-negative numbers $a+b\le\sqrt2\sqrt{a^2+b^2}$). Both are valid upper bounds; the sum is Digonto's choice. For exact-angle circuits the difference is immaterial (leak is 0 or $O(1)$); for synthesised circuits see §5.

**Why a weight tolerance was wrong.** With $U$ unitary, $\|Ac\|^2=1-\|Sc\|^2-\|Xc\|^2$, so a leaked amplitude $\delta$ reduces $\|Ac\|$ by $\approx\delta^2/2$: the block error sees it at second order. Judging the weight $\delta^2$ against $10^{-12}$ therefore allowed $\delta\le10^{-6}$ while the block error was held to $10^{-10}$. Measured (prototype part 1, `cry(θ)` from the $j$-qubit of link $b$ onto a fresh ancilla, target identity, sparse engine):

| θ | block error $\|A-e^{i\varphi}I\|_2$ | $\|X\|_2$ (computed) | $\sin(\theta/2)$ (analytic) | max per-state weight | old verdict | new verdict (combined vs $10^{-10}$) |
|---|---|---|---|---|---|---|
| $1.9\cdot10^{-6}$ | $4.5\cdot10^{-13}$ | $9.500\cdot10^{-7}$ | $9.500\cdot10^{-7}$ | $9.0\cdot10^{-13}$ | ok | **reject** |
| $10^{-6}$ | $1.3\cdot10^{-13}$ | $5.000\cdot10^{-7}$ | $5.000\cdot10^{-7}$ | $2.5\cdot10^{-13}$ | ok | reject |
| $10^{-8}$ | $3.4\cdot10^{-15}$ | $5.000\cdot10^{-9}$ | $5.000\cdot10^{-9}$ | $2.5\cdot10^{-17}$ | ok | reject |
| $2\cdot10^{-10}$ | $3.4\cdot10^{-15}$ | $1.000\cdot10^{-10}$ | $1.000\cdot10^{-10}$ | $10^{-20}$ | ok | reject (combined $1.00003\cdot10^{-10}$) |
| $10^{-10}$ | $3.4\cdot10^{-15}$ | $5.000\cdot10^{-11}$ | $5.000\cdot10^{-11}$ | $2.5\cdot10^{-21}$ | ok | accept |

$X^\dagger X=\sin^2(\theta/2)\Pi_{j_b=1/2}$ exactly (link spins are quantum numbers of the route-A basis states), so $\|X\|_2=\sin(\theta/2)$ is analytic; the computed values agree to all printed digits. This is the content of the new locked test M0-E6.

## 3. Span leak is bounded by the Gauss residual (why $S$ needs no new check)
The code space with the outer register untouched (the circuit never writes it) is the 12-link electric space with far ends fixed; $\mathcal P$ is the joint kernel of the 12 generators $G^a_c$ in it (route A constructs *all* singlets). $\sum_{c,a}(G^a_c)^2=\sum_c\hat J_c^2$ has eigenvalues $\sum_cJ_c(J_c+1)$; the smallest non-zero one is $\tfrac34$ (a single corner at $J=\tfrac12$: e.g. one spin-½ end and three $j=0$ ends). For $s\in\mathcal C\cap\mathcal P^\perp$ therefore $\sum_{c,a}\|G^a_cs\|^2\ge\tfrac34\|s\|^2$, and since there are 12 terms, $\max_{c,a}\|G^a_cs\|\ge\|s\|/4$. The evaluator's residual is computed on the decoded code-space output $\Psi A_{:,k}+s_k$, and $G^a_c\Psi=0$, so
$$\|s_k\|\le4\,\texttt{gauss\_residual}\le4\,\texttt{tol\_gauss}\quad\text{(rigorous)};$$
measured ratios are 1 and 2 (research/002: residual/amplitude $=1.0$ on $m$-type, $0.5$ on $j$-type qubits). With `tol_gauss = tol_err` the span-leak amplitude per state is thus within $4\times$ the error budget without a separate number. It cannot be computed as an amplitude from the existing weights: $w_{\rm code}-|A|^2$ subtracts two $O(1)$ quantities (noise $10^{-16}$ in weight $=10^{-8}$ in amplitude). `max_span_leak` stays a weight diagnostic.

## 4. aer_mps: directly contracted weights and the per-physical-state bound (audit N3)
The MPS engine contracts amplitudes only on requested codes; the out-of-code sector ($2^{34}-625\cdot2^{16}$ patterns for Paulo's circuit) cannot be enumerated, so $X^\dagger X$ is unavailable. Two things are available **directly** (no $O(1)-O(1)$ subtraction):
1. $w^{\rm anc}_i=\sum_{q\in{\rm anc}}\langle\,\Pi_{q=1}\prod_{q'<q}\Pi_{q'=0}\rangle$ — "first set ancilla is $q$", a disjoint decomposition of "some ancilla is set"; each term is one transfer-matrix contraction with pinned qubits (the existing `_outside_weight` generalised to arbitrary pattern sets).
2. $w^{\rm inv}_i=\sum_{c\notin{\rm codes}}|\langle c,{\rm anc}=0|U|i\rangle|^2$ — contract all $2^{n_{\rm data}}-|{\rm codes}|=3471$ invalid data patterns with the same `_contract` routine (vectorised; cost comparable to the 625 code amplitudes already computed).

Noise floor, exact-angle circuits with true out-of-code weight 0, 24 inner inputs each (prototype part 2):

| circuit | subtraction $1-\sum|M|^2$ | subtraction $1-\langle\Pi_{\rm anc=0}\rangle$ | direct $w^{\rm anc}$ | direct $w^{\rm inv}$ | amplitude bound with 16 inputs |
|---|---|---|---|---|---|
| $U_E(0.37)$, 12 qubits | 0 | 0 | 0 | 0 | 0 |
| $U_E$ + 22 idle ancillas, 34 q | 0 | 0 | 0 | 0 | 0 |
| synthetic exact, 34 q, 180 gates (ch/cx/ccx/crz/cp compute–uncompute, seed 20261104) | $1.1\cdot10^{-15}$ | $2.0\cdot10^{-15}$ | 0 | $9.0\cdot10^{-21}$ | $3.8\cdot10^{-10}$ |
| synthetic exact, 34 q, 24 layers (seed 7) | $5.1\cdot10^{-14}$ | $5.3\cdot10^{-14}$ | 0 | $9.4\cdot10^{-21}$ | $3.9\cdot10^{-10}$ |

The direct weights sit at the square of the per-amplitude MPS accuracy ($\sim(10^{-10})^2$), the subtraction values $10^5$–$10^9$ above. (Sparse engine on the same synthetic circuit: $\|X\|_2=0$ exactly.)

**Per-physical-state bound.** A physical state has up to 16 inner components per outer pattern (audit N3: $\max\|c\|_1^2/\|c\|_2^2=16$). For outer block $o$ with inner-component matrix $P_o$ (625 × $n_o$) and any unit $c$,
$$\|X_oP_oc\|=\Big\|\sum_i(P_oc)_i\,X_oe_i\Big\|\le\sum_{i\in{\rm supp}P_o}|(P_oc)_i|\sqrt{w_i}\le\|P_oc\|\sqrt{W_o},\qquad W_o:=\sum_{i\in{\rm supp}P_o}w_i$$
(Cauchy–Schwarz over the support). Outputs of different outer patterns are orthogonal and $\sum_o\|P_oc\|^2=\|c\|^2=1$, so
$$\|X\Psi\|_2^2=\max_c\sum_o\|X_oP_oc\|^2\le\max_oW_o .$$
`leak_amplitude := sqrt(max_o W_o)` is a certified upper bound: tight when the leaked vectors of the support inputs are parallel and in phase with the state's coefficients (coherent leak), up to $\sqrt{16}=4$ pessimistic for mutually orthogonal leaks.

**Paulo's compiled circuit** (34 qubits, 3207 gates, $N_{\rm rot}=14$ at $\varepsilon=10^{-6}$; all 625 inputs, 67 s; prototype part 3):
$\max_iw^{\rm anc}_i=8.8\cdot10^{-20}$ (ancillas effectively clean), $\max_iw^{\rm inv}_i=4.11\cdot10^{-12}$ (the synthesis error on data qubits produces invalid codes; the subtraction value $4.19\cdot10^{-12}$ agrees here because the true leak dominates the noise), median $w_i=2.0\cdot10^{-12}$; $\max_oW_o=6.16\cdot10^{-11}$ → `leak_amplitude` $=7.85\cdot10^{-6}$; block error $2.905\cdot10^{-6}$; **combined (sum) $1.076\cdot10^{-5}$**, RSS $8.37\cdot10^{-6}$; M1-P1 budget $2\cdot10^{-5}$ (margin 1.9), rigorous synthesis bound $N_{\rm rot}\varepsilon=1.4\cdot10^{-5}$.

## 5. Synthesised circuits: what the rule can and cannot guarantee
Each Clifford+T word is within $\varepsilon$ of its rotation (operator norm, up to phase; Ross–Selinger arXiv:1403.2975), so $\|U-e^{i\chi}U_{\rm ex}\|_2\le N_{\rm rot}\varepsilon$ for some phase $\chi$ and, by (1) with $S=0$ for the exact design, $\sqrt{\|A-e^{i\varphi}V\|_2^2+\|S\|_2^2+\|X\|_2^2}\le N_{\rm rot}\varepsilon$ (the evaluator's $\varphi$ is the trace-optimal phase, which can only lower the first term relative to $\chi$ up to second-order effects). The **sum** can therefore legitimately reach $\sqrt2N_{\rm rot}\varepsilon$ for a correct circuit while the budget is $N_{\rm rot}\varepsilon+10^{-9}$. How likely: a word error $\delta\vec n\cdot\vec\sigma$ with random axis splits into $|n_z|\delta$ (phase → block error) and $\sqrt{1-n_z^2}\,\delta$ (axis tilt → leak into invalid codes or span leak), $\langle|n_z|+\sqrt{1-n_z^2}\rangle=\tfrac12+\tfrac\pi4\approx1.29$ for a uniform axis, and errors of different rotations add like a random walk ($\sqrt{N_{\rm rot}}\varepsilon$) rather than $N_{\rm rot}\varepsilon$; Paulo's circuit measures sum/RSS $=1.29$ and RSS $=0.6\,N_{\rm rot}\varepsilon$ (with the ≤4× aer_mps slack inside). So the $\sqrt2$ band is unlikely to bite, but it is a tolerance-form question if it does — recorded as a stop condition in prompts/004 §7 (the RSS alternative `hypot(block_error + dropped_total, leak_amplitude)` is rigorous and a one-line change).

## 6. Recommendation (adopted in prompts/004)
* One amplitude budget: `op_norm_error = block_error + dropped_total + leak_amplitude ≤ tol_err`; `tol_leak` removed from `evaluate`, `synth_tolerances`, `Verdict.tolerances`, `TaskSpec`; `certified = engine_accuracy ≤ min(tol_err, tol_gauss)`.
* `leak_amplitude`: sparse $=\sqrt{\lambda_{\max}(X^\dagger X)}$ with $X^\dagger X=\sum_o(X_oP_o)^\dagger(X_oP_o)$ (exact); aer_mps $=\sqrt{\max_oW_o}$ from directly contracted $w^{\rm anc}_i+w^{\rm inv}_i$ (certified bound). Weight diagnostics `max_leak`, `dirty_ancilla` kept (per state / per $W_o$), never judged.
* Span leak: no new number; bounded by $4\,$`gauss_residual` per state (§3); `gauss=True` stays mandatory.
* Certification minimum for aer_mps stays $10^{-9}$: combined engine noise $\le2\cdot10^{-10}+3.9\cdot10^{-10}$.
* Locked tests: weight assertions → amplitude assertions (weights $\le$ amplitude$^2$); new M0-E6 (auditor's case rejected, threshold pinned at amplitude $10^{-10}$) and M2 `test_evaluator_rejects_small_ancilla_leak`.
