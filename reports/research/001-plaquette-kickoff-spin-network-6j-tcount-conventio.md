# Research 001 — Kickoff: spin-network plaquette (6j), T-count rule, conventions for M0–M2, rishon/LSH/fuzzy pointers

Date: 2026-11-04 · Commit: `067a22f` · Prompt in force: `prompts/001-plaquette-five-encodings-plan.md` (this report feeds `prompts/002-m0-m2-foundation-twelve-qubit-compression.md`)
Related: `scratch/design-A-physics.md`, `scratch/design-B-compress.md`, `refs/su2_plaquette_truncations_encodings.md`, prototypes `scratch/planner/proto_m0.py`, `scratch/planner/proto_metrics.py`, `scratch/planner/proto_paulo_check.py`.

All numbers below were produced on this machine in the `coding` conda env (qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0, numpy 2.5.2, scipy 1.18.0, sympy 1.14.0, python 3.12.14) by the prototype scripts named in each section.

---

## 0. Summary of findings

| Question | Answer | Evidence |
|---|---|---|
| Plaquette in the spin-network basis, (inner pair \| outer pair) pairing | Product of **4** recoupling $F$-symbols (one per corner), arguments = corner spin $J_c$ and the two inner spins before/after; outer spins do **not** enter. Paulo's Fig. 2 claim holds in this pairing; the note's "depends on the outer links" is true in other pairings (e.g. the Raychowdhury–Stryker $(+e_1,+e_2)\mid(-e_1,-e_2)$ split at two of the four corners). | §1, `proto_m0.py`: route A $H_B^{\rm phys}$ has zero matrix elements between different outer labels (max $0$) and different $J$ (max $1.5\cdot10^{-16}$); every one of the 128 outer blocks equals the restriction of one $47\times47$ matrix $K$ up to a diagonal $\pm1$ gauge (residual $3.3\cdot10^{-15}$). |
| T-count rule | $T_{\rm tot}(\varepsilon)=T_{\rm fixed}+\sum_{r=1}^{N_{\rm rot}}T_r(\varepsilon)$, $T_r=3\log_2(1/\varepsilon)+O(\log\log(1/\varepsilon))$ (Ross–Selinger). Measured per rotation: 42–44 ($10^{-4}$), 62–64 ($10^{-6}$), 82–86 ($10^{-8}$), 104–106 ($10^{-10}$). | §2, `proto_metrics.py` |
| CG link basis vs Paulo's $\varepsilon$-rule basis | Same wavefunctions up to complex conjugation of $D^{1/2}$; related by the signed permutation $V_P$: $\lvert 0\rangle_P=\lvert0\rangle$, $\lvert mm'\rangle_P=s(m)s(m')\,\lvert\tfrac12,-m,-m'\rangle_{\rm CG}$, $s(\pm)=\pm1$. $V_P=V_P^{\mathsf T}=V_P^{-1}$. | §3.1, residual $2.2\cdot10^{-16}$ |
| Electric step | $U_E(\alpha)$ at $j_{\max}=\tfrac12$ = `p(-3α/4)` on each link's $j$-qubit (Qiskit `p(λ)=diag(1,e^{iλ})`). Paulo's Eq. 35 uses $P(\lambda)=\mathrm{diag}(1,e^{-i\lambda})$ (opposite sign) and his $\alpha_E$. | §3.2 |
| Closed 2×2 block | $\big[\begin{smallmatrix}0&-2/g^2\\-2/g^2&3g^2/2\end{smallmatrix}\big]$ reproduced exactly (Paulo Eq. 37: $\mathrm{Tr}\,\square\lvert0000\rangle=\lvert16\rangle$ with norm 1, and $\mathrm{Tr}\,\square^\dagger\lvert0000\rangle=\lvert16\rangle$ too, so $\langle16\lvert(\mathrm{Tr}\square+\mathrm{h.c.})\rvert0000\rangle=2$). | §3.3 |
| Counts | 433 / closed 2 / 256 link strings / 95 ambiguous / 17 362 far-end weighted — all reproduced by corner singlets, independent of the reference script. 47 inner labels, 16 bright + 31 dark. | §3.4 |
| Macro lowering costs (Qiskit level 0) | `ccx` 6 CX/7 T, `rccx` 3/4, `swap` 3/0, `ch` 1 CX/2 T, `crz` 2 CX + 2 rot, `crx` 2 CX + 2 rot, `cp` 2 CX + 3 rot, `cz` 1 CX. Qiskit's native `mcx` with ≥3 controls lowers to $\pi/8$-type `rz` (15 and 27 "rotations") — **not allowed as a macro**; ≥3-control Toffolis must be built from `rccx`/`ccx` with clean ancillas. | §3.5 |
| Paulo's compiled file | OpenQASM 3, loads with `qiskit.qasm3.load`: 34 qubits, 3207 gates, depth 2549, CX 294, T 1162 (t 1027 + tdg 135), matches `_metadata.json`; QPY loads identically (global phase $2\cdot10^{-14}$). | §3.6 |
| Fuzzy link dimension | **16 states per link (4 qubits)**: the link wavefunction is a $4\times4$ matrix $\Psi$ for $D=4$ (arXiv:2308.05253 Sec. III, Eq. 31; App. B "n = 16" for one plaquette). | §4.3 |

---

## 1. The plaquette operator in the spin-network basis

### 1.1 Setting and the pairing

Diagram: inner links $b=U_1(0,0)$, $r=U_2(1,0)$, $t=U_1(0,1)$, $l=U_2(0,0)$; loop $U_P=U_bU_rU_t^\dagger U_l^\dagger$; corners $c_0=(0,0)$, $c_1=(1,0)$, $c_2=(1,1)$, $c_3=(0,1)$ (counter-clockwise), each with two inner ends and two outer ends. Point-splitting ("spin network on the point-split graph"): each 4-valent corner is cut into two 3-valent sites joined by a *virtual* link carrying the corner spin $J_c$. We pair **the two inner ends** at one site and **the two outer ends** at the other ("(inner \| outer) pairing"). Gauss's law at the corner (total spin 0 of the four ends) is then equivalent to the triangle rules $(j_a, j_b, J_c)$ and $(j_1, j_2, J_c)$ at the two sites, which is exactly the counting rule of the reference note (`n_intertwiners`).

### 1.2 The formula

On the point-split graph the plaquette is a loop through trivalent sites; Zache, González-Cuadra, Zoller (arXiv:2304.02527, PRL 131, 171902 (2023), Eq. (2)) write its non-vanishing matrix elements as a product of one $F$-matrix per site visited (six for their hexagon, because their split lattice is hexagonal). In our pairing the loop $b\to r\to t^\dagger\to l^\dagger$ passes through the **four inner sites only** (the virtual link $J_c$ is the "outer" leg at each visited site), so

$$
\langle \mathbf j',\mathbf J\,|\,\mathcal P\,|\,\mathbf j,\mathbf J\rangle
=\prod_{c=0}^{3} F^{\,J_c\; j_{p(c)}\; j_{n(c)}}_{\;\frac12\;\; j'_{n(c)}\;\; j'_{p(c)}}\,,
\qquad j'_\ell=j_\ell\pm\tfrac12\ \ (\ell\in\{b,r,t,l\}),\quad \mathbf J'=\mathbf J,
$$

with $p(c),n(c)$ the inner links before/after corner $c$ along the loop ($c_0:(l,b)$, $c_1:(b,r)$, $c_2:(r,t)$, $c_3:(t,l)$), and the recoupling coefficient (Edmonds, *Angular Momentum in Quantum Mechanics*, Eq. (6.1.5); Varshalovich–Moskalev–Khersonskii §8.1)

$$
F^{\,j_1 j_2 j_{12}}_{\;j_3\, J\, j_{23}}
\equiv\langle (j_1j_2)j_{12},j_3;J\,|\,j_1,(j_2j_3)j_{23};J\rangle
=(-1)^{j_1+j_2+j_3+J}\sqrt{(2j_{12}+1)(2j_{23}+1)}
\begin{Bmatrix} j_1 & j_2 & j_{12}\\ j_3 & J & j_{23}\end{Bmatrix}.
$$

The $6j$ symbol is evaluated with Racah's closed formula (Edmonds Eq. (6.3.7)). The matrix elements depend only on $(j_b,j_r,j_t,j_l;J_0..J_3)$: **47 inner labels** at $j_{\max}=\tfrac12$ (Σ over the 16 inner spin patterns of $2^{\#\text{corners with both inner spins }1/2}$ = 1+4+8+2+16+16 = 47), and $H_B^{\rm phys}=-(\mathcal P+\mathcal P^{\mathsf T})$ is block-diagonal in the 8 outer spins with every block equal to the restriction of the single $47\times47$ matrix $K=-(\mathcal P+\mathcal P^{\mathsf T})|_{\rm inner}$ to the labels compatible with that outer pattern.

**Phase conventions.** The sign of each $F$ depends on the fusion-tree convention and on the link orientations ($U$ vs $U^\dagger$ on $t,l$). For SU(2) these are all *diagonal* gauge transformations of the basis (a sign per spin-network state), so (i) spectra are convention-independent and (ii) the route-A matrix (electric basis, corner singlets with the skqd "largest component positive" phase) equals the route-B matrix up to a diagonal $\pm1$ matrix $D$. This is what the prototype finds: `gauge_align` residual $3.3\cdot10^{-15}$ with $D$ real.

### 1.3 Why Paulo (Fig. 2) and the note (§4.2) differ

* Paulo's statement "the plaquette can ignore the external links, even as controls" is the statement that $K$ does not depend on $(j_1,j_2)$ at any corner. In the (inner \| outer) pairing this follows from the formula above (and physically from $[\mathcal P, G_c^{\rm outer}]=0$ together with $[\mathcal P, G_c]=0$, which makes $\mathcal P$ an SU(2) scalar on the inner pair and hence independent of how the outer pair is coupled). **Prediction: M0-X5 passes** (verified by the prototype, §3.4).
* The note's "acts through $6j/9j$ coefficients and depends on the outer links" is correct for a *generic* intertwiner pairing: with the pairing (inner $a$, outer $1$ \| inner $b$, outer $2$) the loop passes through both split sites at that corner and the $F$-symbols carry $j_1,j_2$ (this is the situation on a full lattice with the Raychowdhury–Stryker split, arXiv:1912.06133 Sec. V.A, where sites are split by pairing $+e_1,+e_2$ against $-e_1,-e_2$: at corners $(1,0)$ and $(0,1)$ of our plaquette that pairing is *not* (inner \| outer)). With $9j$ symbols one can convert between pairings. Both statements are therefore true in their own basis; the project fixes the (inner \| outer) pairing for all spin-network-type encodings, so Paulo's version is the operative one.

What this means for the **12-qubit (electric-basis) encoding** is a different statement: there $U_B=U_B^{\rm inner}\otimes 1_{\rm outer}$ identically (the operator never touches outer links), but the *physical states* are entangled between inner and outer registers, so an outer-blind circuit must be exact on $\mathrm{span}_o S_o$ (prototype: all 625 inner codes occur in physical states; the rank of the span is measured in M1-O1).

### 1.4 Other candidate formulations considered

| Candidate | Use here | Why / why not |
|---|---|---|
| Zache et al. Eq. (2) (product of $F$ per visited trivalent site) | **chosen** | general, explicit, one symbol per corner, only $\sim20$ distinct $6j$ values with arguments ≤ 1 |
| Ciavarella–Klco–Savage arXiv:2101.10227 Eq. (10) (product of four "9-R"/vertex factors with external links as controls) | cross-reference only | written for 4-valent vertices in the *link-irrep* basis without an intertwiner label, so the external links appear explicitly as controls (their Table I "physical control sectors"); equivalent to ours after resolving the vertex multiplicity by $J$ |
| Direct electric-basis construction (route A: corner singlets, $W$ 625×625) | **reference** | needed anyway for the 12-qubit encoding; the two routes must agree (M0-X4/X6) |

---

## 2. T-count rule

### 2.1 Ross–Selinger

Ross & Selinger, *Optimal ancilla-free Clifford+T approximation of z-rotations*, arXiv:1403.2975 (Quantum Inf. Comput. 16, 901 (2016)). Abstract and Sec. 1: the algorithm finds the shortest ancilla-free Clifford+T word $U$ with $\|U-R_z(\theta)\|\le\varepsilon$ (operator norm, up to the global phase $\omega^k$); in the typical case its T-count is

$$T_r(\varepsilon)=3\log_2(1/\varepsilon)+O(\log\log(1/\varepsilon)),$$

against the information-theoretic lower bound $K+3\log_2(1/\varepsilon)$ (Sec. 1, citing Kliuchnikov–Maslov–Mosca). Their $R_z(\theta)=\mathrm{diag}(e^{-i\theta/2},e^{i\theta/2})$ — identical to Qiskit's `rz`.

**Measured** (`proto_metrics.py`, pygridsynth 1.2.0 `gridsynth_gates(mpf(repr θ), mpf(repr ε))`, six angles 0.37, 0.61, −0.555, 1.7, 1.22, −0.2775):

| $\varepsilon$ | $3\log_2(1/\varepsilon)$ | measured $T_r$ | max word error |
|---|---|---|---|
| $10^{-4}$ | 39.9 | 42–44 | $4.8\cdot10^{-5}$ |
| $10^{-6}$ | 59.8 | 62–64 | $4.6\cdot10^{-7}$ |
| $10^{-8}$ | 79.7 | 82–86 | $4.0\cdot10^{-9}$ |
| $10^{-10}$ | 99.7 | 104–106 | $4.7\cdot10^{-11}$ |

Offsets $+2\ldots+6$. Acceptance band (design B, generous on the upper side for the $O(\log\log)$ term): $3\log_2(1/\varepsilon)-4\le T_r\le 3\log_2(1/\varepsilon)+3\log_2\log_2(1/\varepsilon)+10$.

### 2.2 Why "$T=\#T+3\ln\varepsilon$" is wrong

Three separate errors. **Sign:** $\varepsilon<1$ so $\ln\varepsilon<0$; the formula would *subtract* T gates as precision improves. The correct dependence is on $\log(1/\varepsilon)=-\log\varepsilon>0$. **Base:** the Ross–Selinger constant 3 goes with $\log_2$ (it comes from counting Clifford+T words of a given T-count, $\sim 2^{T}$ candidates, against an $\varepsilon$-net of size $\sim\varepsilon^{-3}$ on the 3-sphere); with the natural log the constant would be $3/\ln 2\approx4.33$. **Multiplicity:** the cost is paid *per rotation*: $T_{\rm total}=T_{\rm fixed}+\sum_{r=1}^{N_{\rm rot}}T_r(\varepsilon)$; a single additive "$3\log$" term would be independent of how many arbitrary-angle gates the circuit has. For Paulo's circuit $T_{\rm fixed}=296$ (56 `rccx`·4 + 8 `ccx`·7 + 16 explicit $T/T^\dagger$) and $1162-296=866$ T came from the rotations at $\varepsilon=10^{-6}$ ($\approx 14$ synthesised rotations after Qiskit's level-3 merging).

### 2.3 Tools (verified in the installed packages)

* `pygridsynth 1.2.0` (`/home/digimonk/anaconda3/envs/coding/lib/python3.12/site-packages/pygridsynth`): `from pygridsynth.gridsynth import gridsynth_gates`; signature `gridsynth_gates(theta: int|float|mpf, epsilon: int|float|mpf, cfg: GridsynthConfig|None = None, **kwargs) -> str`; returns a word over `H,S,T,X,W` with the **leftmost letter acting last**; `W` is the global phase $e^{i\pi/4}$. Pass `mpmath.mpf(repr(x))`. The package exposes no `__version__`; `pip show pygridsynth` gives 1.2.0.
* Qiskit 2.5.2 (`/home/digimonk/anaconda3/envs/coding/lib/python3.12/site-packages/qiskit`): `qiskit.transpiler.generate_preset_clifford_t_pass_manager(optimization_level=2, target=None, basis_gates=None, coupling_map=None, initial_layout=None, approximation_degree=1.0, seed_transpiler=None, unitary_synthesis_method='default', unitary_synthesis_plugin_config=None, hls_config=None, dt=None, qubits_initially_zero=True, rz_synthesis_config=None) -> StagedPassManager` with `rz_synthesis_config={"rz_synthesis_error": ε, "rz_cache_error": ε/10}` (Paulo's settings: `basis_gates=["cx","h","s","sdg","t","tdg"]`, level 3, `seed_transpiler=12345`); `qiskit.synthesis.gridsynth_rz(angle: float, epsilon: float = 1e-10) -> QuantumCircuit` (Rust port `rsgridsynth`, cites arXiv:1403.2975).
* Measured on a lone `rz(θ)`: Qiskit CT PM gives 62/64/63 T at $10^{-6}$ and 101/103/105 at $10^{-10}$ for θ = 0.37/0.61/−0.555 (pygridsynth: 62/64/64 and 104/104/106) — within ±6 — and is deterministic for a fixed seed (two runs, identical `count_ops`).

---

## 3. Conventions that M0–M2 depend on (verified)

### 3.1 CG link basis vs Paulo's $\varepsilon$-rules; the adapter $V_P$

* **Master basis** (su2qc-skqd `su2.py`, copied): $\lvert j,m_L,m_R\rangle$ with wavefunction $\sqrt{2j+1}\,D^j_{m_Lm_R}(U)$; $U_{ij}$ ($i,j\in\{+\tfrac12,-\tfrac12\}$, index 0 ↔ $+\tfrac12$) is multiplication by $D^{1/2}_{ij}(U)$ projected to $j\le j_{\max}$: $\langle j'm_L'm_R'\lvert U_{ij}\rvert j m_Lm_R\rangle=\sqrt{\tfrac{2j+1}{2j'+1}}\,C^{j'm_L'}_{\frac12 i,\,j m_L}\,C^{j'm_R'}_{\frac12 j,\,j m_R}$; generators $L_a=-J_a^{\mathsf T}$ on $m_L$, $R_a=+J_a$ on $m_R$; verified $[L_a,U_{ij}]=-(T_aU)_{ij}$, $[R_a,U_{ij}]=+(UT_a)_{ij}$, $\sum L_a^2=\sum R_a^2=j(j+1)$ to $4.4\cdot10^{-16}$ at $j_{\max}=\tfrac12$ and 1.
* **Paulo's basis** (notes Eqs. 22–28): wavefunction coefficient of $D^{j*}$ (Eq. 22: $\Psi[U]=\sum\Psi^j_{mm'}D^{j*}_{mm'}(U)$), so $\lvert mm'\rangle_P\propto D^{1/2*}_{mm'}=\sum_{ab}\epsilon_{ma}D^{1/2}_{ab}\epsilon_{m'b}=s(m)s(m')D^{1/2}_{\bar m\bar m'}$ with $\epsilon=i\sigma^2$, $\epsilon_{+-}=1$. Hence the per-link signed permutation
  $$V_P:\ \lvert0\rangle_P=\lvert0\rangle_{\rm CG},\quad \lvert mm'\rangle_P=s(m)s(m')\,\lvert\tfrac12,-m,-m'\rangle_{\rm CG},\qquad s(\pm)=\pm1 .$$
  In the CG order $[0,(\tfrac12,\tfrac12,\tfrac12),(\tfrac12,\tfrac12,-\tfrac12),(\tfrac12,-\tfrac12,\tfrac12),(\tfrac12,-\tfrac12,-\tfrac12)]$ and Paulo order $[0,++,+-,-+,--]$ the brute-force search over all $5!\cdot2^5$ signed permutations finds exactly this one ($V_P U^{\rm CG}_{ij}V_P^{\mathsf T}=\tilde U_{ij}$ for all $i,j$ with residual $2.2\cdot10^{-16}$; $V_P$ is symmetric and an involution).
* Paulo's Eq. 25 writes $\langle U\lvert mm'\rangle=\sqrt2\,D^{1/2}_{mm'}(U)$ without the conjugate that Eq. 22 implies; the integral in Eq. 25 only gives $\tfrac1{\sqrt2}\delta_{ma}\delta_{m'b}$ with the conjugate. This is a typo in Eq. 25, not an error in the rules (Eq. 28 is consistent with Eq. 22 and with $V_P$ above).
* The notebook's numpy check uses colour index 0 ↔ $-$, 1 ↔ $+$ (opposite of the notes' "1,2 ↔ +,−"); harmless, but the builder must not mix the two.

### 3.2 Electric step and the $(g,dt)\to(\alpha,\beta)$ map

Paulo Eq. 16 with $a=1$, $g_s=g_t=g$: $\mathbb H=\tfrac{g^2}{4}\sum_l(\mathbb T_L^2+\mathbb T_R^2)-\tfrac{2}{g^2}\sum_p\mathrm{Re\,Tr}\,\square_p=\tfrac{g^2}{2}H_E+\tfrac1{g^2}H_B$ with $H_E=\sum_\ell j_\ell(j_\ell+1)$, $H_B=-\sum_P(\mathrm{Tr}U_P+\mathrm{Tr}U_P^\dagger)$. $U_E(\alpha)=e^{-i\alpha H_E}$, $\alpha=g^2dt/2$; $U_B(\beta)=e^{-i\beta H_B}=e^{+i\beta(\mathrm{Tr}U_P+{\rm h.c.})}=e^{+i\,2\beta\,\mathrm{Re\,Tr}U_P}$, $\beta=dt/g^2$. Paulo's notebook implements $e^{+i\alpha_P\mathrm{Re\,Tr}\square}$ with $\alpha_P=2dt/(g_sg_ta)$ ⇒ $\alpha_P=2\beta$; his file has $dt=g=1$ ⇒ $\beta=1$. On a bright pair with coupling $g\in\{1,\tfrac12,\tfrac14\}$ (eigenvalue of $\mathrm{Re\,Tr}\square$ restricted to the pair) the notebook applies `rx(-2 α_P g)` $=e^{+i\alpha_Pg\sigma_x}$ ✓.
Electric: $j=\tfrac12$ link ⇒ $e^{-i\alpha\cdot3/4}$ on the $j=1$ codeword ⇒ `p(-3α/4)` on the $j$-qubit with Qiskit `p(λ)=diag(1,e^{iλ})`. Paulo's Eq. 35 "$P(3\alpha/2)$" uses $P(\lambda)=\mathrm{diag}(1,e^{-i\lambda})$ and $\alpha_E=g^2/4$ per $\mathbb T_L^2+\mathbb T_R^2=2j(j+1)$ — same physics, opposite sign convention for the gate; the acceptance test M1-E1 checks the phase $e^{-3i\alpha/4}$ numerically.

### 3.3 Closed-plaquette block

Route A at $g^2=1$: $\big[\begin{smallmatrix}0&-2\\-2&1.5\end{smallmatrix}\big]$ in the basis $\{\lvert0000\rangle,\lvert16\rangle\}$ (the two closed states, labels $(j=0^{12};J=0^4)$ and $(j=\tfrac12^4,0^8;J=0^4)$). Also $K[\text{vac},\cdot]$ has a single non-zero, $-2$, at the all-$\tfrac12$, all-$J=0$ label: Paulo's Eq. 37 ($\square\lvert0000\rangle=\lvert16\rangle$, norm 1) ✓, and $\square^\dagger\lvert0000\rangle=\lvert16\rangle$ as well.

### 3.4 Counts and structure (route A, `proto_m0.py`, 22 s)

433 physical states (Gram deviation $3\cdot10^{-15}$, max Gauss residual $5\cdot10^{-16}$), closed 2, 256 distinct link-spin strings, 95 strings with more than one state, far-end-weighted dimension 17 362; route B enumerates 433 labels; spectra of $\tfrac{g^2}{2}H_E+\tfrac1{g^2}H_B$ agree to $1.3\cdot10^{-14}$ at $g^2\in\{0.5,1,2\}$; $W$ leaves the physical space invariant (leak $1.3\cdot10^{-15}$); 47 inner labels, 31 dark ($K$ row zero: any corner with $J=1$); 3153 of the $3^8=6561$ outer computational patterns carry physical support; the inner support of a pattern has 1–17 codes; all 625 inner codes occur.

### 3.5 Macro-gate lowering costs (`proto_metrics.py`, `transpile(basis_gates=["cx","h","s","sdg","t","tdg","x","z","rz"], optimization_level=0, seed_transpiler=20261104)`)

| macro | CX | $T_{\rm fixed}$ | $N_{\rm rot}$ | citation for optimality |
|---|---|---|---|---|
| `ccx` | 6 | 7 | 0 | 7 T is optimal ancilla-free: Gosset–Kliuchnikov–Mosca–Russo arXiv:1308.4134; decomposition Amy–Maslov–Mosca–Roetteler arXiv:1206.0758 (T-depth 3), Nielsen–Chuang Fig. 4.9 |
| `rccx` (Margolus, relative phase) | 3 | 4 | 0 | Maslov arXiv:1508.03273 (relative-phase Toffoli, 4 T, 3 CNOT); Selinger arXiv:1210.0974 (T-depth) |
| `ccz` | 6 | 7 | 0 | = `ccx` conjugated by `h` |
| `swap` | 3 | 0 | 0 | standard |
| `ch` | 1 | 2 | 0 | exact: $S^\dagger H T^\dagger\,\mathrm{CX}\,T H S$ (Paulo's notebook cell 5) |
| `crz(θ)` | 2 | 0 | 2 | standard $R_z(\theta/2)\,\mathrm{CX}\,R_z(-\theta/2)\,\mathrm{CX}$ |
| `crx(θ)` | 2 | 0 | 2 | `crz` conjugated by `h` |
| `cp(λ)` | 2 | 0 | 3 | $R_z(\lambda/2)$ on both + $R_z(-\lambda/2)$ between CXs |
| `cz` | 1 | 0 | 0 | |
| native `mcx` (3 / 4 controls) | 14 / 36 | 0 / 22 | 15 / 27 `rz` at $\pi/8$-type angles | **not Clifford+T exact — excluded**; k-control Toffolis go through $k-2$ clean ancillas: $(k-2)$ `rccx` + 1 `ccx` + $(k-2)$ `rccx` = $6+6(k-2)$ CX, $7+8(k-2)$ T (Gidney arXiv:1709.06648 temporary-AND would give 4 T per AND with measurement; out of scope v1) |

### 3.6 Paulo's circuit files

`SU2_plaquette_jmax_half_CT.qasm` is OpenQASM 3 (`include "stdgates.inc"`, registers `d[12] p_0[4] e[4] w[7] g[3] tmp[3] h_1[1]`); `qiskit.qasm3.load` and `qiskit.qpy.load` give the same circuit: 34 qubits, 3207 gates, depth 2549, `{'h':1155,'t':1027,'s':504,'cx':294,'tdg':135,'sdg':92}`, T = 1162, CX = 294 — identical to `_metadata.json`. The notebook's pre-synthesis counts: 56 `rccx`, 8 `ccx`, 8 `t`, 8 `tdg`, 54 `cx`, 10 `cz`, 6 `cu` (from 2 `mcrx`), 1 `crx`, 50 `x`, 16 `h`, 8 `s`, 8 `sdg`, 4 `z` ⇒ $T_{\rm fixed}=296$; Qiskit level-0 to `[rz,sx,x,h,s,sdg,t,tdg,cx]` gives 294 CX and 60 `rz`. The spin-network gate file `spin_network_plaquette3.gates.txt` uses qubit indices q[0..3] (inner links), q[12..15] (corner intertwiners, after 8 untouched outer-link slots q[4..11]) and q[16..22] (7 ancillas): 68 CX, 32 T + 32 T†, 34 H, 12 X, 4 `p` rotations (0.025, 0.05, 0.1, −0.2 at $\alpha_P=0.1$) — consistent with Table I (15 qubits touched, 64 fixed T, 4 rotations). A direct check of the 34-qubit QASM against $e^{+i\beta(\mathrm{Tr}W+{\rm h.c.})}$, $\beta=1$, in Paulo's basis/codec is running (`proto_paulo_check.py`); its result is recorded in §6.

---

## 4. Rishon, LSH, fuzzy — model definitions for later planner runs

### 4.1 Rishon / quantum link model (M5–M6)

Brower, Chandrasekharan, Wiese, *QCD as a quantum link model*, hep-th/9704106, Phys. Rev. D 60, 094502 (1999). Per link the operators $U_{ij}$, $L_a$, $R_a$ (and $T$) generate SU(2N) (their Eq. (2.12)–(2.15); for SU(2): SU(4)); the Hamiltonian (Eq. (2.5)/(2.20)) is $H=J\sum\mathrm{Tr}[UUU^\dagger U^\dagger]+J'\sum(\det U+\det U^\dagger)$ (+ electric term $\propto\sum(L^2+R^2)$ in later papers), with the determinant term breaking U(N) to SU(N). Rishon representation (Sec. 4, Eqs. (4.2)–(4.4)): fermions $c^i_{x,\pm\mu}$ at each link end, colour $i=1..N$, $(U_{x,\mu})_{ij}=c^i_{x,+\mu}c^{j\dagger}_{x+\hat\mu,-\mu}$, $L^a_{x,\mu}=\sum c^\dagger_{x,+\mu}\lambda^a c_{x,+\mu}$, $R^a_{x,\mu}=\sum c^\dagger_{x+\hat\mu,-\mu}\lambda^ac_{x+\hat\mu,-\mu}$; the rishon number $N_{x,\mu}$ per link is conserved, and with exactly $N$ fermionic rishons per link the determinant is non-zero (Eq. (4.6)) and the link space has $\binom{2N}{N}$ states (Eq. (4.7)): **6 for SU(2)**, decomposing under SU(2)$_L\times$SU(2)$_R$ as $(0,0)\oplus(0,0)\oplus(\tfrac12,\tfrac12)$ (two rishons at the same end: singlet; one at each end: $\tfrac12\otimes\tfrac12$) — this confirms the note's derived count. Register: 4 modes/link ⇒ 4 qubits/link by Jordan–Wigner with link-contiguous modes (48 qubits), as in plan 001 §8.5. The later planner run must fix: (i) the SU(2) QLM Hamiltonian normalisation (the SO(5)-based SU(2) model of Chandrasekharan–Wiese hep-th/9609042 vs the U(2)+det model), (ii) the electric operator ($\sum L^2+R^2$ in the 6-state space has eigenvalues 0 and $\tfrac32$ as in KS $j_{\max}=\tfrac12$ but with a doubled singlet), (iii) the Gauss-law states on this diagram (count by a transfer sum over corners), (iv) JW signs through the plaquette term (Eq. (4.8): product of four end-bilinears, each colour-neutral, string-free when modes are link-contiguous).

### 4.2 Loop-string-hadron (M7–M8)

Raychowdhury & Stryker, arXiv:1912.06133, Phys. Rev. D 101, 114502 (2020). Sec. V.A: point-splitting of a 2D site into two trivalent gluonic sites $x',\bar x'$ with one virtual link (their choice: $+e_1,+e_2$ together and $-e_1,-e_2$ together; for pure gauge no matter site is needed). Sec. V.B: at a trivalent site the SU(2) invariants are the loop operators $\mathcal L^{\sigma\sigma'}_{ij}$ (Eqs. (67a–d)) built from Schwinger-boson doublets $a(i)$ on the three legs; the on-site basis is labelled by three loop numbers $l_{pq},l_{qr},l_{rp}$ with $N_{pq}=\tfrac12(N_p+N_q-N_r)$ (Eq. (85)); the flux on leg $p$ is $N_p=l_{pq}+l_{rp}$, i.e. $j_p=(l_{pq}+l_{rp})/2$. Normalised ladder operators $\hat\Lambda^\pm_{ij}=\mathcal L^{\pm\pm}_{ij}/\sqrt{(N_{ij}+1)(N_\Sigma+1)}$ (Eq. (87)), $N_\Sigma=l_{pq}+l_{qr}+l_{rp}+1$ (Eq. (86)); Abelian Gauss law = flux read from both ends of every (real and virtual) link agrees (Eq. (41) in 1D, "just another Abelian Gauss law for virtual links" in Sec. V.A). Plaquette: Eq. (83) with the sign function $\eta_p^{(2D)}$ (Eq. (82)) — a product over the visited trivalent sites of vertex-factor matrices (Eqs. (70)–(73)) with $1/\sqrt{N+1}$ normalisations. **Pairing caveat:** RS pair $(+e_1,+e_2)\mid(-e_1,-e_2)$, which coincides with our (inner \| outer) pairing at corners $(0,0)$ and $(1,1)$ but not at $(1,0)$ and $(0,1)$ — on a single plaquette we are free to choose the (inner \| outer) pairing at all four corners (any pairing is a valid point-splitting; RS call theirs "notationally convenient"), which makes the LSH basis literally the route-B spin-network basis with $l_{ab}$ fixed by $(j_a,j_b,J)$: $l_{ab}=j_a+j_b-J$, $l_{aJ}=j_a+J-j_b$, $l_{bJ}=j_b+J-j_a$. The later planner run must verify that the LSH site factors reproduce the $F$-symbols (expected: equal up to the diagonal gauge), and fix the 24-qubit codec (3 loop bits per site; at $j_{\max}=\tfrac12$ each $l\in\{0,1\}$).

### 4.3 Fuzzy gauge theory (M9–M10)

Alexandru, Bedaque, Carosso, Cervia, Murairi, Sheng, *Fuzzy gauge theory for quantum computers*, arXiv:2308.05253 (v4), Phys. Rev. D 109, 094502 (2024). Sec. III: each link matrix element $U_{ij}$ is promoted to a $D\times D$ matrix $\mathscr U_{ij}$ (built from SO(5)/Spin(5) gamma matrices for the $D=4$ example, Eq. (30)); the link Hilbert space is the space of $D\times D$ matrices $\Psi$ with $\langle\Psi\lvert\Phi\rangle=\mathrm{tr}[\Psi^\dagger\Phi]$ — **dimension $D^2=16$ for $D=4$, i.e. 4 qubits per link** ("This example forms a 16-dimensional Hilbert space (per link)"; Eq. (31) expands $\Psi$ in the 16 Clifford-algebra basis elements; App. B: $n=16$ qubits for one plaquette). Paulo's handwritten $4\times4$ objects are the operators $\mathscr U$, $T^{L/R}$, not states. Kinetic terms: $\mathcal K_1=[T^L_a,[T^L_a,\bullet]]+[T^R_a,[T^R_a,\bullet]]$ (Eq. (36), Casimir of the left/right actions) and $\mathcal K_2=-\mathscr U_{ij}\bullet\mathscr U_{ij}^\dagger-\mathscr U_{ij}^\dagger\bullet\mathscr U_{ij}$ (Eq. (37)); $\mathcal K_1$ leaves a two-fold ground-state degeneracy on one plaquette which $\mathcal K_2$ lifts; which one gives the right continuum limit is left open by the paper. Plaquette $\square(P)=\mathscr U_{ij}(\ell_1)\mathscr U_{jk}(\ell_2)\mathscr U_{lk}(\ell_3)^\dagger\mathscr U_{il}(\ell_4)^\dagger$ (Eq. (35)), $\mathsf a\mathcal H=\tfrac{\eta g^2}{2}\sum\mathcal K\pm\tfrac{\eta}{2g^2}\sum(\square+{\rm h.c.})$ (Eq. (34)), link operators acting by left multiplication. The design-A observation that $\mathcal K_1$ superselects one bit per link (3 qubits/link) comes from the project's own tex note, not from the paper — the later planner run must re-derive it. **Decision kept: 4 qubits/link (48), $\mathcal K_1$ default, cluster-product $U_B$ declared as the target** (plan 001 §8.6).

---

## 5. Decisions taken for prompts/002 (and the reasons)

1. **Phase gauge is not fixed between route A and route B.** Corner singlets use the "largest component positive" phase (skqd); route B uses the $F$-symbol formula as written. Tests compare up to a diagonal unitary found by `gauge_align` (M0-X5/X6) and compare spectra (M0-X4). Fixing a common gauge would cost a derivation (CG coupling with conjugate representations on the $m_L$ ends) and buy nothing: every encoding's target is built from the same `PhysicalBasis` object.
2. **Macro set** = `{ccx, rccx, ccz, swap, ch, crz, crx, cp, cz}`; `mcx` with ≥3 controls only through the `Builder.mcx` library routine (ancilla chain) — Qiskit's native lowering is not Clifford+T-exact (§3.5).
3. **M0-X5 asserts** block-diagonality in outer labels (exact zeros), $J$ conservation (≤ $10^{-12}$), and block = $K$ up to diagonal gauge (≤ $10^{-10}$, elementwise $|{\rm block}|=|K|$ ≤ $10^{-12}$) — design A's "all blocks identical" is only true up to the gauge, as the prototype shows (max $|{\rm block}-K|=2$ without gauge).
4. **M1-P1 tolerance** for Paulo's synthesised circuit: op-norm error ≤ $2\cdot10^{-5}$, leak ≤ $10^{-9}$. Justification: $866$ rotation-T at ≥ 54 T per rotation ($3\log_2 10^6-6$) ⇒ at most 16 synthesised rotations, each within $10^{-6}$ ⇒ triangle-inequality error ≤ $1.6\cdot10^{-5}$; leak probability ≤ $(1.6\cdot10^{-5})^2=2.6\cdot10^{-10}$.
5. **M2 gate test** re-evaluates the archived global best from its program source and requires key ≤ round-0 best (design B §6).
6. **sympy cross-check of $6j$** restricted to admissible (triangle-satisfying) arguments; sympy raises `ValueError` otherwise.

## 6. Addendum — Paulo's 34-qubit circuit vs the exact operator

`scratch/planner/proto_paulo_mps_full.py` (qiskit-aer `matrix_product_state`, truncation threshold 0, `max_memory_mb=2e8` to bypass Aer's statevector-sized memory estimate, amplitudes by contracting `save_matrix_product_state`; 4 threads): all 625 inner codes in **139 s**, max bond dimension 16, minimum column norm on the code space 0.999999999998 (leak ≤ 2·10⁻¹²). Against $V=e^{+i\beta(\mathrm{Tr}W_P+{\rm h.c.})}$ in Paulo's basis/codec after one global phase:

| target | $\beta=0.5$ | $\beta=1$ | $\beta=2$ |
|---|---|---|---|
| $e^{+i\beta(\mathrm{Tr}W+{\rm h.c.})}$ | 0.96 | **2.9·10⁻⁶** | 1.68 |
| $e^{-i\beta(\mathrm{Tr}W+{\rm h.c.})}$ | 2.0 | 1.82 | 2.0 |

So Paulo's compiled file implements $U_B(\beta=1)$ with the project's conventions ($\alpha_P=2\beta$, Eq. 31 codec, $V_P$) to $2.9\cdot10^{-6}$ — consistent with ≈ 3 of its ~14 synthesised rotations contributing at the $10^{-6}$ level, and well inside the M1-P1 bound $2\cdot10^{-5}$. Two engine findings for the builder: (i) the pure-Python dict simulator and the batched COO simulator in the circuit's own gate order both blow up (peak $2^{21}$ amplitudes per input) because Qiskit's level-3 schedule hoists the opening Hadamards of all 22 relative-phase Toffolis to the front; a DAG-reordering heuristic may fix this but was not confirmed in the time available; (ii) Aer MPS refuses the circuit unless `max_memory_mb` is raised (its estimate is the $2^{34}$ statevector, 17 TB), and `save_amplitudes` with MPS returns wrong values (0.17 instead of 1.0 for the vacuum column) — contract the saved MPS instead. The plan therefore gives the evaluator an `engine` argument (`sparse` | `aer_mps` | `auto`).
