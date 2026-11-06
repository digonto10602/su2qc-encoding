# METHODS-fuzzy — fuzzy gauge theory encoding (M9/M10)

Companion to `docs/METHODS.md` (laptop-owned; conventions §1, §6–§8, §11 apply unchanged). Written by the planner for
`prompts/300` (2026-11-06); numbers marked "measured" come from `scratch/planner/proto_fuzzy_*.py`, see
`reports/research/300`. Source: Alexandru, Bedaque, Carosso, Cervia, Murairi, Sheng, arXiv:2308.05253v4 (**P**), Sec. III
Eqs. (22)–(37), Sec. V Eqs. (60)–(64); Bedaque's note `refs/fuzzy/fuzzy-hamiltonian-digonto.pdf` (**N**); Pauli forms
`refs/fuzzy/project1_fuzzy_flux_tube.tex` l.57–97 (**Tex**).

Jargon, once: *fuzzy link* = a link whose wavefunction is a $4\times4$ complex matrix $\Psi$ instead of a function on SU(2);
*row/column index* = the two matrix indices of $\Psi$; *block bit* = the bit selecting the upper/lower $2\times2$ block of an index;
*flavour* $F$ = the operator $\Psi\mapsto\Psi\Gamma_5$.

## F1. Link Hilbert space, qubit map, codec

* One link: $\Psi\in\mathbb C^{4\times4}$, inner product $\mathrm{tr}\,\Psi^\dagger\Phi$, 16 orthonormal states = the matrix units
  $E_{\rm row,col}$. Four qubits per link, 12 links, **48 qubits**, no don't-cares (every computational state is a valid link state).
* Index of a link state (row-major vectorisation): $i=4\,{\rm row}+{\rm col}=8q_1+4q_2+2q_3+q_4$ with ${\rm row}=2q_1+q_2$,
  ${\rm col}=2q_3+q_4$; $q_1,q_3$ block bits (0 = upper block, where $T_R$ lives; 1 = lower block, where $T_L$ lives), $q_2,q_4$ spin bits.
* **Register layout** (little-endian, qubit $k$ = bit $k$, METHODS §1): link $\ell=0..11$ in the order $b,r,t,l,o_0,\dots,o_7$
  occupies qubits $4\ell..4\ell+3$ with $q_4\to4\ell$, $q_3\to4\ell+1$, $q_2\to4\ell+2$, $q_1\to4\ell+3$. Register `d` = qubits
  0–15 (inner links), `o` = 16–47 (outer links), ancillas after. Row qubits of inner link $\ell$: $(4\ell+3,4\ell+2)$.
* Left multiplication $\Psi\mapsto M\Psi$ is $M\otimes1$ (acts on $(q_1,q_2)$), right multiplication $\Psi\mapsto\Psi M$ is
  $1\otimes M^{\mathsf T}$ (acts on $(q_3,q_4)$).

## F2. Link operators (P Eqs. 29–30, 22; Tex Eq. (pauli)) — all identities measured exact

$\Gamma_0=\tfrac12\begin{pmatrix}0&1\\1&0\end{pmatrix}$, $\Gamma_A=\tfrac12\begin{pmatrix}0&i\sigma^A\\-i\sigma^A&0\end{pmatrix}$,
$\Gamma_5=\mathrm{diag}(1,1,-1,-1)$, $T^A_R=\tfrac12\mathrm{diag}(\sigma^A,0)$, $T^A_L=\tfrac12\mathrm{diag}(0,\sigma^A)$,
$\mathbb U_{ab}=\delta_{ab}\Gamma_0-i\sigma^A_{ab}\Gamma_A$.
$$\mathcal T^A_{L,R}\Psi=[T^A_{L,R},\Psi],\qquad \mathcal U_{ab}\Psi=\mathbb U_{ab}\Psi,\qquad
[\mathcal T^A_L,\mathcal U_{ab}]=-\tfrac12(\sigma^A\mathcal U)_{ab},\quad[\mathcal T^A_R,\mathcal U_{ab}]=+\tfrac12(\mathcal U\sigma^A)_{ab}.$$
Pseudo-reality $(\mathcal U_{ab})^\dagger=\epsilon_{ac}\epsilon_{bd}\mathcal U_{cd}$, $\epsilon=i\sigma^2$.
Pauli forms on $(q_1q_2|q_3q_4)$ ($q_1$ most significant in the string; Pauli on $q_k$ acts on qubit $4\ell+4-k$):
$\mathcal U_{ij}=\tfrac12[\delta_{ij}X_1+i\sigma^A_{ij}Y_1\sigma^A_2]$;
$\mathcal T^A_R=\tfrac12[P^{(1)}_0\sigma^A_2-P^{(3)}_0\sigma^{A\mathsf T}_4]$, $\mathcal T^A_L=\tfrac12[P^{(1)}_1\sigma^A_2-P^{(3)}_1\sigma^{A\mathsf T}_4]$;
$$\mathcal K_1=\tfrac32-\tfrac14(X_2X_4-Y_2Y_4+Z_2Z_4)(1+Z_1Z_3),\qquad
\mathcal K_2=-X_1X_3+Y_1X_2Y_3X_4-Y_1Y_2Y_3Y_4+Y_1Z_2Y_3Z_4 .$$
Irreps $2(0,0)\oplus2(\tfrac12,\tfrac12)\oplus(1,0)\oplus(0,1)$; spectra $\mathcal K_1\in\{0^2,\tfrac32^8,2^6\}$,
$\mathcal K_2\in\{-4,-2^4,0^6,2^4,4\}$ ($-4$ on $\Psi=1$, $+4$ on $\Gamma_5$, $\mp2$ on the two flux copies, 0 on the dipoles);
$[\mathcal K_1,\mathcal K_2]=0$; $F=Z_3$ commutes with $\mathcal U,\mathcal T,\mathcal K_1$ and anticommutes with $\mathcal K_2$;
centre $\mathcal Z=Z_1Z_3$ commutes with both kinetic terms and anticommutes with $\mathcal U_{ab}$.

## F3. Hamiltonian, Trotter step, angle map (decisions of 2026-11-06)

$$H^{\rm fz}=\frac{g^2}{4}\sum_{\ell=1}^{12}\big(\mathcal K_1(\ell)+r\,\mathcal K_2(\ell)\big)+\frac1{g^2}H_B^{\rm fz},\qquad
H_B^{\rm fz}=-(\square+\square^\dagger)=-2\square,$$
$$\square=\sum_{abcd}\mathcal U_{ab}(b)\,\mathcal U_{bc}(r)\,(\mathcal U_{dc}(t))^\dagger\,(\mathcal U_{ad}(l))^\dagger\quad\text{(P Eq. 35; loop }[b^+,r^+,t^-,l^-]\text{, METHODS §1)}.$$
Electric normalisation = Paulo Eq. 16 literally ($\tfrac{g^2}{4}\mathcal K_1$ equals $\tfrac{g^2}{2}j(j+1)$ on flux links; a flux
link costs $\tfrac38g^2$ as in KS). $r=\kappa_2/\kappa_1$ is **not fixed by N**: nominal $r=1$, and $r=0$ (the $\mathcal K_1$ theory)
is always tested too (assumption Digonto may override). Step angles $\alpha=g^2dt/2$, $\beta=dt/g^2$, and
$$U_E(\alpha)=\bigotimes_\ell e^{-i\frac{\alpha}{2}\mathcal K_1(\ell)},\qquad U_K(\kappa_2)=\bigotimes_\ell e^{-i\kappa_2\mathcal K_2(\ell)},\ \kappa_2=r\,\alpha/2,\qquad
U_B(\beta)=e^{-i\beta H_B^{\rm fz}}=e^{+2i\beta\square}.$$
$U_E$ phases on a link: $e^{-i\alpha\{0,3/4,1\}}$ (flux link $e^{-3i\alpha/4}$ = KS $j=\tfrac12$). $U_K$ eigenphases
$e^{-i\kappa_2\{-4,-2,0,2,4\}}$. Since $[\mathcal K_1,\mathcal K_2]=0$, $U_{EK}:=U_KU_E=e^{-i(\frac\alpha2\mathcal K_1+\kappa_2\mathcal K_2)}$ exactly.
Step orders: order 1 $=U_B\,U_K\,U_E$ (kinetic layers first in the circuit); order 2 $=U_E(\alpha/2)U_K(\kappa_2/2)\,U_B(\beta)\,U_K(\kappa_2/2)U_E(\alpha/2)$,
error $O(dt^3)$ per step. Outer-link kinetic factors commute with everything (they act on other links) ⇒
$e^{-iHt}=\big[\bigotimes_{\rm outer}U_{EK}\big]\,e^{-i(H^{\rm inner}_{EK}+H_B)t}$ exactly; the 8 outer $U_E$ and 8 outer $U_K$ blocks are
reported as a separate row. Nominal $(\alpha,\beta)=(0.37,0.61)$, alternates $(0.91,0.23)$, $(1.70,1.00)$ (METHODS §2).
N's magnetic coupling "$\alpha$" is $\alpha_N=-2\beta$; the symbol is not used in code.

## F4. Gauss's law and the physical set

Corner generator $G^A_c=\sum_{\ell\ {\rm out\ of}\ c}\mathcal T^A_L(\ell)+\sum_{\ell\ {\rm into}\ c}\mathcal T^A_R(\ell)$ (P Eq. 33 with the
paper's orientation; N Eq. 3 treated as a typo). Physical: $G^A_c\psi=0$, $c=0..3$, $A=1..3$; far ends of outer links free.
All three terms of $H^{\rm fz}$ commute with every $G^A_c$ (measured: $\square$ on the 50-dim isolated-plaquette kernel, residual
$2\cdot10^{-14}$; $\mathcal K_{1,2}$ commute with $\mathcal T$ exactly). With $\mathcal K_2$ the flavour $F$ is not conserved, so the
physical set is the full Gauss kernel (both $F$ sectors). Counts (two routes, research 300 §4): isolated plaquette 50;
outer-vacuum sector $12\,800$; 12 links with fixed far ends **101 197 218**; far-end weighted **6 767 266 914**.
Counting rule (route A): $N=\sum_{\rm inner\ irreps}\prod_{c}\Big[\sum_{\rm outer\ irreps\ at\ c}|T(j_1,j_2)\cap T(j_3,j_4)|\prod_{\rm outer}(2j_{\rm far}+1)^{[w]}\Big]$,
$T(j,j')=\{|j-j'|,\dots,j+j'\}$. Route B: $N=\int\prod_c dg_c\prod_{\rm inner}\chi_\ell(g_{\rm tail},g_{\rm head})\prod_{\rm outer}\chi^{\rm out}_\ell(g_c)$,
$\chi_\ell(g,h)=\sum_{(j_L,j_R)}\chi_{j_L}(g)\chi_{j_R}(h)$.

## F5. Plaquette operator structure and the $U_B$ construction (measured, research 300 §3)

$\square$ acts on the 8 row qubits only. Spectrum $\{0^{174},\pm1^{16},\pm2^{24},\pm4\}$; 64 Pauli strings, coefficients $\pm\tfrac18$.
With $f=q_1^b$ and parities $p_k=q_1^b\oplus q_1^{\ell_k}$ ($\ell_k=r,t,l$; three CNOTs), $Z_1^bZ_1^{\ell_k}$ are conserved and
$$\square=\sum_{p}\Pi_p\otimes\big(|1\rangle\langle0|_f\otimes D_p+{\rm h.c.}\big),\quad D_p=A_p\Sigma_pB_p^\dagger,\quad
\Sigma_p=\{2^4,0^{12}\}\ (p\ne3,6),\ \{1^{16}\}\ (p=3),\ \{4,0^{15}\}\ (p=6).$$
$$e^{2i\beta\square}=C_{\rm par}^\dagger\Big[\prod_p\Pi_p\!\cdot\! C_p\,e^{2i\beta X_f\otimes\Sigma_p}\,C_p^\dagger\Big]C_{\rm par},\qquad
C_p=|0\rangle\langle0|_f\otimes B_p+|1\rangle\langle1|_f\otimes A_p,$$
where $e^{2i\beta X_f\otimes\Sigma_p}=\prod_{k:\sigma_k\neq0}\big(|k\rangle\langle k|\otimes R_x(-4\beta\sigma_k)\big)+\ldots$, i.e. $R_x(-4\beta\sigma_p)$
on $f$ controlled on the singular-value labels ($R_x(\theta)=e^{-i\theta X/2}$). **Target = the exact exponential.** The
commuting-cluster product of Tex Result 3 is not exact (op-norm error 1.9 at $\theta=0.61$, also on gauge singlets) and is only a
reported splitting-error row. Generic 8-qubit QSD (≈ 31k CX, ≈ 37k non-linear rotations) is rejected (T-table infeasible).

## F6. Verification (what is certified)

* One-link circuits ($U_E$, $U_K$, $U_{EK}$): full 16×16 unitary equality (op-norm after one global phase ≤ $10^{-10}$) through the
  laptop evaluator on the adapter `FuzzyBlockEncoding(4)` (all 16 codes physical, `gauss=False`). This certifies exactness on every
  physical state (every link state is a code) and Gauss preservation (the target commutes with $\mathcal T$).
* $U_B$: the circuit touches no column qubit (gate-list check) and its 256×256 block on the row qubits with ancillas $|0\rangle$ equals
  $e^{2i\beta\square}$ (≤ $10^{-10}$; adapter `FuzzyBlockEncoding(8)`, ancillas = column qubits + work qubits, clean ≤ $10^{-20}$ in weight).
* Step (48 qubits): gate-list partition into the three layers; dense statevector check on the 16 inner data qubits (+ ≤ 8 ancillas) for
  seeded inputs (≥ 32 random product states and ≥ 8 physical states), error ≤ $10^{-10}$; Gauss residual of outputs on seeded physical
  COO states ≤ $10^{-10}$ (exact angles) or $N_{\rm rot}\varepsilon+10^{-9}$ (synthesised, prompts/003–004). Trust label: blocks
  *certified* (complete basis), composition *sampled*.
* Tolerances: $10^{-10}$ exact angles (float64 over ≤ $3\cdot10^4$ gates accumulates ≲ $10^{-12}$); synthesised
  $N_{\rm rot}\varepsilon+10^{-9}$; weights $10^{-20}$ (= $(10^{-10})^2$); integer counts exact; algebra residuals $10^{-12}$.

## F7. Shared observables vs KS (definitions)

At coupling $g^2$ (nominal $g^2=2\alpha/dt$ with $dt=\sqrt{2\alpha\beta}$ ⇒ $g^2=\sqrt{2\alpha/\beta}$; nominal $g^2=1.1015$):
1. Electric energy per link: $\tfrac{g^2}{4}\mathcal K_1$ spectrum $\{0,\tfrac38g^2,\tfrac12g^2\}$ vs KS $\tfrac{g^2}{2}j(j+1)\in\{0,\tfrac38g^2\}$ at $j_{\max}=\tfrac12$ (and $g^2$ at $j=1$).
2. Closed-sector spectrum: eigenvalues of $H$ restricted to the cyclic (Krylov) subspace generated from the strong-coupling vacuum
   $|\Omega\rangle=\bigotimes_\ell\tfrac12\mathbb 1$ (all outer links in the $\Psi=\tfrac12\mathbb 1$ copy) by $H$; KS: the 2×2 block
   $\begin{pmatrix}0&-2/g^2\\-2/g^2&3g^2/2\end{pmatrix}$ (METHODS §4).
3. $\langle\mathrm{Re\,Tr}\,U_P\rangle(t)=\langle\Omega|e^{iHt}\,\tfrac12(\square+\square^\dagger)\,e^{-iHt}|\Omega\rangle$ (fuzzy: $\square$; KS: $\mathrm{Re\,Tr}\,W$)
   at $t=dt$, tabulated against $\beta$ at fixed $g^2$. (After one **first-order** Trotter step $U_BU_KU_E$ from the vacuum both
   theories give exactly $\langle\mathrm{Re\,Tr}U_P\rangle=\langle\Omega|{\rm ReTr}U_P|\Omega\rangle=0$ because $U_B$ commutes with
   the plaquette and the kinetic layers act as phases on the vacuum — a shared identity, tested at $r=1$ and $r=0$. For the
   symmetric order-2 step the outer kinetic half-layers act on $U_B|\Omega\rangle$ and the value is $O(\alpha\beta)$, not zero:
   measured $0.0348$ ($r=0$) / $-0.362$ ($r=1$) at nominal, $0.0147\to0.0037$ ($r=0$) under $(0.05,0.05)\to(0.025,0.025)$,
   ratio $\approx4$; tested as nonzero with ratio in $[3,5]$ — prompts/301.)
   Closed-sector facts (verified numerically, prompts/301): basis vector 0 is $\Omega$, $\dim=12$ ($r=1$), $9$ ($r=0$);
   $\langle\Omega|H|\Omega\rangle=-4rg^2$ (four inner links, $-rg^2$ each from $\kappa_2\mathcal K_2$); $E_0=-5.839<-4g^2$ at $r=1$.
4. Loschmidt echo $L(t)=|\langle\Omega|e^{-iHt}|\Omega\rangle|^2$ on a $t$ grid, computed in the closed sector.
Fuzzy rows at $r=1$ and $r=0$; KS row from the 2×2 block.

## F8. Lean (new files under `lean/Su2Plaq/Fuzzy/`)

Link algebra over $\mathbb Z[i]$ (matrices scaled by 2 and 4 so that entries are Gaussian integers): the su(2) relations, the
transformation law, $[\mathcal K_1,\mathcal K_2]=0$, $\mathcal K_1$ and $\mathcal K_2$ Pauli forms, $F=Z_3$ (anti)commutation — kernel
`decide` on 16×16 matrix identities. Physical counts 50, 12 800, 101 197 218, 6 767 266 914 by `decide` from the corner rule of F4.
Per-circuit native certificates: only if the fixed unitaries $C_p$ lie in $K=\mathbb Q(i,\sqrt2,\sqrt3)$ (METHODS §11.2); otherwise
reported as `n_a` with the reason.

## F9. M10 compression units, composed score and hook (prompts/302)

* **Units.** The step factorises exactly (F3): $U=[\bigotimes_{\rm outer}U_{EK}]\,U_B\,[\bigotimes_{\rm inner}U_{EK}]$ with
  $U_{EK}(\alpha,\kappa_2)=U_K(\kappa_2)U_E(\alpha)=e^{-i(\frac\alpha2\mathcal K_1+\kappa_2\mathcal K_2)}$ ($[\mathcal K_1,\mathcal K_2]=0$).
  Compression runs the Gu-et-al loop (METHODS §9) on two units through the laptop machinery: `fuzzy_ub` (kind `UB`, target
  `UB_row(beta)`, $256\times256$ on the 8 row qubits; unit frame qubit $2l=q_2^l$, $2l+1=q_1^l$ = circuit qubit `ROW_QUBITS[i]`; up to
  32 ancillas) and `fuzzy_link` (kind `UE`, target `UEK_link(alpha, kappa2)` with **`spec.beta` $=\kappa_2$**, $16\times16$ on
  $(q_4,q_3,q_2,q_1)$ = frame qubits 0..3, no ancillas). Validity = the laptop rules (exact $\le10^{-10}$ after one phase at the
  nominal and both alternate angle pairs with identical skeleton, clean ancillas, allowed gates, wall $\le300$ s). Gauss is not
  re-checked per unit: all unit codes are physical and both targets commute with every $\mathcal T^A$ (audit 300 A1/A3), so full
  block exactness implies Gauss preservation. Key $(\mathrm{CX},T_{10^{-6}},\mathrm{depth}_{CT},\mathrm{qubits})$ per unit.
* **Composed score.** `compress_hook.compose_step(link_fn, ub_fn, alpha, beta, kappa2, order, with_outer)` builds the step from the
  unit circuits (order 1: 4 inner $U_{EK}$ blocks, $U_B$, 8 outer blocks; order 2: half-angle $U_{EK}$ blocks on both sides) with
  `metadata['layers']`; its `logical_metrics` are the reported step counts and it is re-verified with `verify_step_samples`
  (F6: blocks certified on a complete basis, composition sampled, seed 20261104, $10^{-10}$).
* **In the $U_K$ Clifford frame** `cx(q1,q3) cx(q2,q4) h(q1) h(q2)` both kinetic terms are diagonal:
  $\mathcal K_1\to\tfrac32-\tfrac14(Z_2-Z_2Z_4+Z_4)(1+Z_3)$, $\mathcal K_2\to-Z_1+Z_1Z_2Z_3-Z_1Z_2Z_3Z_4+Z_1Z_3Z_4$ (10 $Z$-strings,
  $Z_1Z_3\to Z_3$ under the frame), so $U_{EK}$ is one Clifford frame plus a phase polynomial; parity-network synthesis
  (Amy–Maslov–Mosca, arXiv:1303.2042) bounds the CNOT count by $2^4-2=14$ for all parities, against 36 CX for the two M9 ladders.
  $U_B$ levers: `rccx` compute/uncompute pairs (Maslov arXiv:1508.03273), one unary decode of the three parity bits into eight
  sector flags, Gray-ordered sectors, uncontrolled Clifford frames where the flag makes the control redundant.
* **Hook.** `su2plaq.fuzzy.compress_hook.install()` registers the two units in the laptop `spec`/`evaluate`/`baselines`/`round`
  modules by attribute patching (no laptop file edited; the clean diff is in prompts/302 §2 and `notes/merge-notes-fuzzy.md`),
  forces `gauss=False` for fuzzy block encodings, replaces `build_UB`'s constant `p(-pi)` by `z` in the general seed (the laptop
  program generator requires angle-linear gates), records Lean status `n_a` (no fuzzy exporter), and exports
  `SU2PLAQ_FUZZY_HOOK=1` + `PYTHONPATH+=src/su2plaq/fuzzy/sitehook` so that the sandboxed build worker installs the hook too.
  Prototype (`scratch/planner/m10_hook_proto.py`): link full key (36, 644, 1515, 4), polish → 30 CX; $U_B$ (1718, 2822, 4924, 15),
  polish → 1596 CX; composed general step with outer links CX 2150, $N_{\rm rot}=136$.
