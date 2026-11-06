# Research 300 — Fuzzy gauge theory (arXiv:2308.05253v4) on the 12-link plaquette: link algebra, counts, plaquette structure, verification strategy

Date: 2026-11-06. Planner run for M9 (branch `m9-fuzzy`). Prototype scripts: `scratch/planner/proto_fuzzy_m9.py`
(algebra, spectra, plaquette, clusters, isolated-plaquette Gauss kernel), `proto_fuzzy_count.py` (physical counts by two
routes), `proto_fuzzy_ub.py` (plaquette block structure, pygridsynth timing). All numbers below are measured there
(`~/venvs/coding`, numpy 2.5.2, scipy 1.18) unless marked "paper".

Sources. **P** = Alexandru, Bedaque, Carosso, Cervia, Murairi, Sheng, "Fuzzy gauge theory for quantum computers",
arXiv:2308.05253v4 (PRD 109, 094502 (2024)), Sec. III Eqs. (22)–(37), Sec. V Eqs. (60)–(64) and App. B. **N** = Bedaque's one-page
note `refs/fuzzy/fuzzy-hamiltonian-digonto.pdf` (Eqs. N1–N4). **Tex** = `refs/fuzzy/project1_fuzzy_flux_tube.tex` l.57–97
(Pauli forms). **Check** = `scratch/fuzzy-hamiltonian-check.md` (2026-11-06, N vs P vs plan; essentials copied in §1).

## 1. Essentials of the Hamiltonian check (N vs P vs the project plan)

| Item | Verdict | Detail |
|---|---|---|
| Link space | same | $\Psi\in\mathbb C^{4\times4}$, 16 states, 4 qubits/link, 48 qubits (P Sec. III after Eq. 31; N; plan 001 §3). |
| $\mathbb U_{ab}$, $T_{L,R}$ | same | N Eq. 2 = P Eqs. 29–30 entry by entry; generators act by commutator, links by left multiplication (P Eq. 22, text under Eq. 36). |
| Electric term | same operator | $\mathcal K_1=(\mathcal T^L)^2+(\mathcal T^R)^2$ (P Eq. 36); spectrum $\{0^{2},\tfrac32^{8},2^{6}\}$. Coefficient is a convention: **decision (Digonto 2026-11-06): Paulo Eq. 16, $\tfrac{g^2}{4}\sum\mathcal K_1$, $\kappa_1=\alpha/2$.** |
| $\mathcal K_2$ | N has it | $\mathcal K_2\Psi=-\sum_{ab}(\mathbb U_{ab}\Psi\mathbb U_{ab}^\dagger+\mathbb U_{ab}^\dagger\Psi\mathbb U_{ab})$ (P Eq. 37); spectrum $\{-4,-2^{4},0^{6},2^{4},4\}$; $[\mathcal K_1,\mathcal K_2]=0$; $\{F,\mathcal K_2\}=0$ with $F=\Psi\mapsto\Psi\Gamma_5=Z_3$ ⇒ the 3-qubit reduction is lost. **Decision: include it, own circuit $U_K$, 48 qubits.** |
| Plaquette | same operator | $\square=\sum_{abcd}\mathbb U_{ab}(b)\mathbb U_{bc}(r)(\mathbb U_{dc}(t))^\dagger(\mathbb U_{ad}(l))^\dagger$ (P Eq. 35 index order; N's $\mathbb U^\dagger_{cd}$ must be read as $(\mathbb U_{dc})^\dagger$ — the other reading breaks gauge invariance at 3 corners). $\square$ is Hermitian (pseudo-reality $(\mathbb U_{ab})^\dagger=(\epsilon\mathbb U\epsilon^{\mathsf T})_{ab}$, residual 0), so $\square+\square^\dagger=2\square$. **Coordinator default: $H_B^{\rm fz}=-2\square$, $U_B(\beta)=e^{+2i\beta\square}$, $\beta=dt/g^2$ (KS sign).** |
| Gauss law | same up to orientation | N Eq. 3 puts $T_L$ on incoming links; with N's own matrices $T_L$ rotates the row index and the loop contracts column($\ell_1$) with row($\ell_2$), so $T_L$ belongs to **outgoing** links (P Eqs. 2, 15, 33; METHODS §3). **Default: N Eq. 3 is a typo; paper orientation.** Verified: $\square$ commutes with all 4 corner generators (residual $2\cdot10^{-14}$ on the Gauss kernel). |
| Outer links | gap in N and plan | settled in §5 below. |

## 2. Link algebra (all residuals exactly 0 in float64)

$\Gamma_0=\tfrac12\begin{pmatrix}0&1\\1&0\end{pmatrix}$, $\Gamma_A=\tfrac12\begin{pmatrix}0&i\sigma^A\\-i\sigma^A&0\end{pmatrix}$, $\Gamma_5=\mathrm{diag}(1,1,-1,-1)$,
$T^A_R=\tfrac12\mathrm{diag}(\sigma^A,0)$, $T^A_L=\tfrac12\mathrm{diag}(0,\sigma^A)$, $\mathbb U_{ab}=\delta_{ab}\Gamma_0-i\sigma^A_{ab}\Gamma_A$ (P Eqs. 29–30).
Row-major vectorisation $|{\rm row},{\rm col}\rangle$: left multiplication $M\otimes1$, right multiplication $1\otimes M^{\mathsf T}$;
$\mathcal T^A_{L,R}=[T^A_{L,R},\cdot]$, $\mathcal U_{ab}=\mathbb U_{ab}\cdot$ (16×16).
Verified: $[\mathcal T^A,\mathcal T^B]=i\epsilon_{ABC}\mathcal T^C$ for L and R, $[\mathcal T^A_L,\mathcal T^B_R]=0$,
$[\mathcal T^A_L,\mathcal U_{ab}]=-\tfrac12(\sigma^A\mathcal U)_{ab}$, $[\mathcal T^A_R,\mathcal U_{ab}]=+\tfrac12(\mathcal U\sigma^A)_{ab}$ (P Eqs. 24–25).
Irreps under $SU(2)_L\times SU(2)_R$: $2(0,0)\oplus2(\tfrac12,\tfrac12)\oplus(1,0)\oplus(0,1)$ (joint Casimir eigenvalues $(0,0)^{2},(\tfrac34,\tfrac34)^{8},(2,0)^{3},(0,2)^{3}$).
Pauli forms (Tex Eq. (pauli), qubits $(q_1q_2|q_3q_4)$ = (row block, row spin | col block, col spin), $q_1$ most significant) reproduce the matrices exactly:
$\mathcal U_{ij}=\tfrac12[\delta_{ij}X_1+i\sigma^A_{ij}Y_1\sigma^A_2]$,
$\mathcal K_1=\tfrac32-\tfrac14(X_2X_4-Y_2Y_4+Z_2Z_4)(1+Z_1Z_3)$,
$\mathcal K_2=-X_1X_3+Y_1X_2Y_3X_4-Y_1Y_2Y_3Y_4+Y_1Z_2Y_3Z_4$ (= P Eqs. 63–64), $F=Z_3$, centre $\mathcal Z=Z_1Z_3$.

## 3. Plaquette operator on the 8 row qubits (measured)

* $\square$ acts by left multiplication only ⇒ on the 8 row qubits $(q_1,q_2)$ of $b,r,t,l$, identity on the 8 column qubits.
* 256×256, Hermitian, spectrum $\{0^{174},\pm1^{16},\pm2^{24},\pm4^{1}\}$; 64 Pauli strings with coefficients $\pm\tfrac18$ (40 plus, 24 minus), weights 4 (1), 6 (18), 7 (24), 8 (21) — Tex Result 3 up to its factor 2 ($\square+\square^\dagger=2\square$).
* **Block structure (new, exact).** Let $z=(q_1^b,q_1^r,q_1^t,q_1^l)$. $\square$ only connects $z\to\bar z$ (all four block bits flipped; 0 violating entries), so $Z_1^bZ_1^r$, $Z_1^bZ_1^t$, $Z_1^bZ_1^l$ are conserved (commutator 0). With $f=q_1^b$ and parities $p=(q_1^b\oplus q_1^r,q_1^b\oplus q_1^t,q_1^b\oplus q_1^l)$:
  $$\square=\sum_{p\in\{0,1\}^3}\Pi_p\otimes\big(|1\rangle\langle0|_f\otimes D_p+|0\rangle\langle1|_f\otimes D_p^\dagger\big),$$
  $D_p$ 16×16 on the four row-spin qubits. Singular values: $p\in\{0,1,2,4,5,7\}$: $\{2^{4},0^{12}\}$; $p=3$: $\{1^{16}\}$ ($D_3$ unitary); $p=6$: $\{4,0^{15}\}$. Hence per block $\square|_p^3=\sigma_p^2\,\square|_p$ and
  $$e^{2i\beta\square|_p}=1+(\cos2\beta\sigma_p-1)\,Q_p+i\,\frac{\sin2\beta\sigma_p}{\sigma_p}\,\square|_p,\qquad Q_p=\square|_p^2/\sigma_p^2\ \text{(projector)}.$$
  Equivalently, with $D_p=A_p\Sigma_pB_p^\dagger$ and $C_p=|0\rangle\langle0|_f\otimes B_p+|1\rangle\langle1|_f\otimes A_p$: $e^{2i\beta\square|_p}=C_p\,e^{2i\beta X_f\otimes\Sigma_p}\,C_p^\dagger$ — the only $\beta$-dependence is $R_x(-4\beta\sigma_p)$ on $f$ controlled on the singular-value label: **angle-linear**.
* **Commuting-cluster product is NOT exact.** Greedy colouring gives 4 clusters of 16 commuting strings (as in Tex), $\max\|[H_c,H_{c'}]\|_\infty=2$. At $\theta=0.61$: $\|e^{2i\theta\square}-\prod_c e^{2i\theta H_c}\|_2=1.99$ on the full row space and **1.91 on the 50 gauge-singlet states of the isolated plaquette** (Gauss kernel of $\sum_{c,A}G_A^{(c)2}$ on $16^4$, dimension 50 = Tex Table count). Tex Eq. (factor) ("deviation $<10^{-15}$ on every gauge-invariant state") is contradicted by this measurement (with the greedy clustering; the Tex clustering is not specified). **Decision: target $U_B=e^{+2i\beta\square}$ exactly; the cluster product is reported as a separate splitting-error row, never as the target.**

## 4. Physical-state counts (two independent routes agree exactly)

Geometry METHODS §1 (corners $c_0..c_3$, inner $b,r,t,l$, outer $o_0..o_7$ with their orientations). A link in irrep $(j_L,j_R)$ contributes $j_L$ at its tail corner (outgoing, $T_L$) and $j_R$ at its head (incoming, $T_R$); the far end of an outer link carries the other spin with no constraint.
* Route A (corner-factorised Clebsch–Gordan count): singlets in $j_1\otimes j_2\otimes j_3\otimes j_4$ = $|T(j_1,j_2)\cap T(j_3,j_4)|$; sum over the 6 irrep copies per link; far-end multiplicity $2j_{\rm far}+1$ when weighted.
* Route B (Haar character integral over the 4 corner group elements, Weyl measure $\tfrac2\pi\sin^2\theta\,d\theta$, $\chi_j=\sin((2j+1)\theta)/\sin\theta$, Gauss–Legendre 80 points — exact for the trigonometric polynomial).

| Set | Route A | Route B |
|---|---|---|
| 12 links, far end of outer links fixed (one state per irrep copy) | **101 197 218** | 101 197 218.0 |
| 12 links, far end free (weighted) | **6 767 266 914** | 6 767 266 914.000001 |
| outer links all in a $(0,0)$ copy ("outer-vacuum sector") | 12 800 = 50 × 2⁸ | — |
| isolated plaquette (2-valent corners) | 50 | 50 (sparse kernel, 65536-dim) |

Consequence: the physical set cannot be enumerated or used as the evaluator's `physical_vectors()`; verification must be block-wise (§5). With $\mathcal K_2$ included, Gauss's law is unchanged ($[\mathcal K_2,\mathcal T^A_{L,R}]=0$), the flavour $F$ is no longer superselected, so "physical" = the full Gauss kernel over both $F$ sectors; no further sector restriction.

## 5. Verification strategy and outer links (settled)

* Every link state is a valid code (16 states ↔ 4 qubits, no don't-cares). $U_E,U_K$ are tensor products of one-link 16×16 unitaries; $U_B$ is a 256×256 unitary on the row qubits ⊗ identity. **Exactness as full unitaries on the data space implies exactness on every physical state** (and Gauss preservation, since the targets commute with the generators). So the certified statement is: one-link blocks equal their 16×16 targets (op-norm after one phase ≤ 1e-10), the plaquette block equals the 256×256 target with the column qubits untouched and ancillas clean. The assembled 48-qubit step is checked by (i) gate-list structure and (ii) seeded sample states on the 16 inner qubits (dense statevector) plus Gauss residual of outputs on seeded physical states (COO application of the corner generators).
* Outer links: $U_B$ reads nothing outside the 4 inner links (no outer controls at all; `outer_bits_read = 0`). $U_E^{\rm outer}$, $U_K^{\rm outer}$ are the same one-link blocks on the 8 outer links; they commute with the far-end index (they commute with $\mathcal T_L,\mathcal T_R$), so the KS far-end-spectator argument transfers: fixed-far-end correctness ⇒ far-end-free correctness; here the one-link blocks are verified as full unitaries anyway. They are reported as the separate "outer-link electric/K₂ row" (8 blocks each of $U_E$ and $U_K$).
* The laptop evaluator (`su2plaq.evaluate.evaluator.evaluate`) is reused through a tiny adapter encoding (`FuzzyBlockEncoding`, all computational codes physical, `n_outer=0`, `gauss=False`), which yields a genuine `Verdict` (method `inner_span`/`physical` on a complete basis = full-unitary check). Its Gauss branch is KS-specific (`enc.basis`), so the fuzzy Gauss residual is computed in our own module.
* Cost: pygridsynth 0.029 s per call (this machine) ⇒ a T-table over 4 ε values costs ≈ 0.12 s per rotation; a 4000-rotation circuit ≈ 8 min (slow test).

## 6. Candidate circuit constructions for $U_B$ (compared)

| Route | Exact? | Angles | CX / rotations (estimate) | Fit |
|---|---|---|---|---|
| Qiskit `UnitaryGate` + QSD on 8 qubits (Shende–Bullock–Markov, quant-ph/0406176) | yes (numerical) | non-linear in β | ≈ 31k CX, ≈ 37k rz | T-table infeasible (hours), no Lean; **rejected** |
| Commuting-cluster product (Tex Result 3) | **no** (error 1.9) | linear | ≈ 1k CX | rejected as target; reported as a row |
| Parity/SVD block route (§3) | yes | linear ($R_x(-4\beta\sigma_p)$) | 8 flag ladders + 16 controlled 4-qubit fixed unitaries; if the $\tilde D_p$ are Clifford: ≈ 1–2k CX, ≤ 20 β-rotations; else ≤ 16k CX, ≤ 7k fixed-angle rotations | **chosen**; builder must measure whether the $\tilde D_p$ are Clifford (Pauli→Pauli test) |

The parity/SVD route is exact by construction (algebraic identity in §3); the builder verifies it numerically at every angle used.
