# Research 002 — Gauss-law tolerance for synthesised circuits; engine certification

- Date: 2026-11-04. Planner (Fable 5.1). Commit: `5c5f567` + uncommitted step-0.8 work.
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md`, amended by `prompts/003-gauss-tolerance-synthesised-circuits-engine-policy.md` (this run's output).
- Related: `reports/tests/009-m0-step-0-8-evaluator.md` (F2, F3, F4), `reports/tests/008-m0-step-0-7-sparse-sim-recheck.md` (Aer MPS accuracy), `reports/research/001-…` §3.6 (Paulo's circuit 2.9e-6).
- Prototype: `scratch/planner/proto_gauss_ratio.py` (production evaluator, 12-qubit encoding, 16 cases, ~25 s).

## 1. Question
How large may the Gauss residual $\max_{c,a,k}\|G^a_c U\psi_k\|$ of a *correct* circuit whose rotations were synthesised to precision $\varepsilon$ be, and is Digonto's rule (Gauss budget = error budget $N_{\rm rot}\varepsilon+10^{-9}$) sound?

## 2. Analysis (no external source needed; linear algebra on the project's own definitions)
$U_{\rm ex}$ = the circuit with exact angles; for a correct design $U_{\rm ex}\psi_k=e^{i\varphi}V\psi_k$ and $G^a_cV\psi_k=0$. Each gridsynth word is a unitary within $\varepsilon$ (operator norm, up to phase; Ross–Selinger arXiv:1403.2975, METHODS §7) of its rotation, so by the triangle inequality over the product of unitaries $\|U-U_{\rm ex}\|_2\le N_{\rm rot}\varepsilon$ on the whole register. Then
$$\|G^a_cU\psi_k\|=\|G^a_c(U-U_{\rm ex})\psi_k\|\le\|G^a_c\|_{\rm op}\,N_{\rm rot}\varepsilon .$$
$G^a_c$ is the sum of the four spin-½ generators at a corner ($J=\sigma/2$ convention, `LinkSpace(0.5).generators()`); its largest eigenvalue is 2 (computed: 2.000000 for $\sum L_z$, $\sum R_z$, $\sum L_x$). Rigorous worst case therefore $2N_{\rm rot}\varepsilon$.

## 3. Prototype numbers (`python scratch/planner/proto_gauss_ratio.py`)
Exact $U_E(\alpha=0.37)$ (four `p(-3α/4)`) plus one gauge-breaking `rx(δ)` or `ry(δ)` on a data qubit; full-space error $\|E\|=\sin(\delta/2)$; evaluator `method="physical"`, default tolerances.

| perturbation | $\|E\|$ | physical-block `op_norm_error` | `gauss_residual` | ratio residual/$\|E\|$ |
|---|---|---|---|---|
| rx/ry(1e-5) on $q_{m'}$ or $q_m$ (links b, r) | 5.000e-6 | 1.250e-11 | 5.000e-6 | 1.000 |
| rx/ry(1e-5) on $q_j$ (link b) | 5.000e-6 | 1.250e-11 | 2.500e-6 | 0.500 |
| rx/ry(1e-7) on $q_{m'}$ or $q_m$ | 5.000e-8 | 4.3e-15 | 5.000e-8 | 1.000 |
| rx/ry(1e-7) on $q_j$ | 5.000e-8 | 4.3e-15 | 2.500e-8 | 0.500 |

Max ratio over 16 cases: 1.000 (to $2\cdot10^{-15}$). Two conclusions:
1. The physical-block op-norm error sees a gauge-breaking amplitude only at **second** order ($1.25\cdot10^{-11}=(5\cdot10^{-6})^2/2$), the Gauss residual at **first** order — the quantitative form of tester finding F3; `gauss=True` is mandatory.
2. A single-qubit error flips one end of a corner: it changes $G^a_c$'s action by one spin-½ unit, ratio ≤ 1. Reaching the rigorous factor 2 needs errors on all four ends of one corner adding coherently.

Paulo's compiled circuit (reports/tests/009 §3(6)): residual $1.16\cdot10^{-10}$ with $N_{\rm rot}=14$, $\varepsilon=10^{-6}$ → budget $1.4\cdot10^{-5}$, margin $10^5$; the residual is at the `aer_mps` engine floor ($\le2\cdot10^{-10}$ per amplitude, reports/tests/008), i.e. the synthesis error of that circuit is almost entirely gauge-covariant (angle errors, not axis tilts).

## 4. Recommendation (adopted in prompts/003)
* `tol_gauss` becomes a parameter of `evaluate` (default `None` → $10^{-10}$, exact-angle circuits unchanged); synthesised circuits pass $N_{\rm rot}\varepsilon+10^{-9}$ = their error budget (Digonto's rule), via one production helper `synth_tolerances(n_rot, eps)`.
* Honest caveat recorded as a stop condition: a correct circuit could in principle show a residual in $(N_{\rm rot}\varepsilon,\,2N_{\rm rot}\varepsilon]$; if that happens, ask Digonto rather than loosen.
* Certification: `certified = engine_accuracy ≤ min(tol_err, tol_leak, tol_gauss)`; `aer_mps` ($2\cdot10^{-10}$) can certify only budgets ≥ $10^{-9}$. M0-E5's engine cross-check moves to $10^{-9}$ (5× the measured floor) and asserts `certified`; its sparse clause stays at $10^{-10}$.
