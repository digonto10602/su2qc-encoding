# Research 400 — Loop-string-hadron (LSH) encoding, M7: the model, the register, the Abelian Gauss law, the operators, a general circuit

- Date: 2026-11-10 · Author: planner (Claude Fable 5.2, high) · Git commit at writing: `8822b0b` (branch `merge-desktop-tracks`, host omnicommander)
- Prompt in force: `prompts/002` + addenda `003`–`006` (machinery); `prompts/001` §1, §3 ("M7/M8 — LSH"), §4–§6 (physics and report format). This note feeds `prompts/400-lsh-m7-plan.md` and `docs/METHODS-lsh.md`.
- Related: `reports/research/100-spinnet-m3-encoding-gauge-general-circuit.md` (spin-network encoding, the 4-rotation walk reused here), `reports/research/001` §1 (6j plaquette, the (inner | outer) pairing), `reports/audits/001` N5 (signs are a gauge at $j_{\max}=\tfrac12$), `docs/METHODS.md` §2, §5–§7, §11, `docs/METHODS-spinnet.md` §2–§4.
- Prototypes (every number below was computed by them; nothing is assumed), all run as `PYTHONPATH=src PER_JOB_MEM=4G tools/run-capped taskset -c 16-19 python <file>` in the `coding` env (qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0, numpy 2.5.4, scipy 1.18.1), Lean v4.35.0:
  `scratch/planner/proto_m7_lsh_model.py` (2.3 s), `scratch/planner/proto_m7_lsh_circuit.py` (31 s, peak memory 0.29 GB), `scratch/planner/proto_m7_lsh_rs_pairing.py`, `scratch/planner/proto_m7_lsh_wrap.py`, `scratch/planner/proto_m7_lsh_lean_tables.py`, `scratch/planner/lean/LSHCounts.lean` (10.8 s), `scratch/planner/lean/LSHCircuit.lean` (21 s), and the near-production prototype modules `scratch/planner/m7shim/proto/{lsh_operators,encodings_lsh,lsh_walk,circuits_lsh}.py` with `scratch/planner/m7shim/{shim_plugin,mutation_check}.py`.

Jargon, once. *Loop-string-hadron (LSH) formulation*: a rewriting of SU(2) lattice gauge theory in which every site carries only gauge-invariant integers; for pure gauge theory these are *loop numbers*. *Prepotentials / Schwinger bosons*: two harmonic oscillators at each end of each link, from which the link matrix and the electric field are built. *Point splitting*: replacing a 4-valent lattice site by two 3-valent (*trivalent*) sites joined by a zero-length *virtual link*. *Loop number* $\ell_{ij}$: how many units of flux run through a trivalent site from leg $i$ to leg $j$. *Flux* $N_i$ of a leg: twice its spin, $N_i=2j_i$. *Abelian Gauss law (AGL)*: the rule that the flux of a link read at its two ends is the same. *Site code*: the 3 bits holding the three loop numbers of a site. *'in' site / 'out' site* (our labels): the trivalent site of a corner that holds its two inner links / its two outer links. *Inner code*: the 12 data bits (four 'in' sites). *Bright / dark*: inner codes the plaquette moves / annihilates. *Transcoder* (our label): a short reversible circuit that rewrites the LSH data bits in place into the spin-network data bits. *Frame, flag, phase walk*: as in METHODS-spinnet (CNOT relabelling; ancilla holding a Boolean function; $R_z$ rotations between CNOT toggles).

## 0. Summary

| Question (coordinator brief) | Answer | Evidence |
|---|---|---|
| Exact LSH model for this plaquette | Pure-gauge LSH on the point-split diagram of plan 001 §3: 8 trivalent sites, (inner \| outer) pairing at every corner, three loop numbers per site, physical-link flux capped at 1 ($j_{\max}=\tfrac12$), virtual-link flux up to 2 ($J\le1$), no matter sites. | §2; Raychowdhury–Stryker arXiv:1912.06133 Sec. V |
| Registers: 24 qubits, circuit touches 12? | **Confirmed.** 1 qubit per loop number (rule $N=\lceil\log_2(\bar j+1)\rceil=1$ of arXiv:1812.07554), 3 per site, 24 in total; the plaquette acts on the four 'in' sites (12 qubits) and never reads the 12 outer-site qubits. 5 of the 8 site codes are valid. | §2, §4, §5 |
| Abelian validity and the 433 states | Site-valid (flux cap) + AGL on 4 inner and 4 virtual links ⇔ one of the 433 route-B labels; the map is $\ell_{12}=j_1+j_2-j_3$ etc. per site. Brute force over $5^8=390\,625$ site-valid register states: exactly **433** AGL-valid, equal to the label codes. | §2.3 |
| $H_E$, $H_B$ in LSH variables | $H_E=\sum_{\rm links}\tfrac{N}{2}(\tfrac N2+1)$ with $N$ = sum of two loop numbers; $H_B=-(\mathrm{Tr}\,U_P+{\rm h.c.})$, $\mathrm{Tr}\,U_P$ = trace of four site-local vertex-factor matrices of normalised loop ladder operators. | §3 |
| Cross-check with routes A/B | $K_{\rm LSH}=K_{6j}$ **entry by entry** ($1.8\cdot10^{-15}$, no sign gauge needed); $H_B^{\rm LSH}$ vs route A: diagonal $\pm1$ gauge, residual $8.9\cdot10^{-16}$ (64 minus signs); spectra of $\tfrac{g^2}2H_E+\tfrac1{g^2}H_B$ agree to $1.0\cdot10^{-14}$ (A) and $3.6\cdot10^{-15}$ (B) at $g^2\in\{0.5,1,2\}$. | §3.3 |
| Are the ladder factors really the 6j F-symbols? | Moduli equal on all cases ($2.2\cdot10^{-16}$); one corner factor differs in sign, the product with the vertex-factor signs is equal. The LSH factors themselves were verified against the oscillator Fock space ($1.2\cdot10^{-15}$). | §3.1, §3.2 |
| General circuit | Transcoder (20 CX) + the spin-network 4-rotation walk on the transcoded wires (54 CX) + transcoder inverse (20 CX): **94 CX, 4 rotations, 88 fixed T, 7 ancillas, depth 87**; $T(10^{-6})=342$ ($U_B$), 598 (step). Exact to $2.6\cdot10^{-14}$; Gauss $5.4\cdot10^{-16}$. | §5 |
| Price of LSH vs spin network | Exactly the transcoder: **+40 CX, +32 T**, +4 data qubits (+4 outer), same rotations and ancillas. | §5.3 |

## 1. Sources (read, and what was taken from each)

1. I. Raychowdhury, J. R. Stryker, "Loop, string, and hadron dynamics in SU(2) Hamiltonian lattice gauge theories", arXiv:1912.06133, Phys. Rev. D 101, 114502 (2020). Read from the arXiv v2 TeX source (2026-11-10). Used: Sec. III Eq. (22) (Abelian Gauss law), Eqs. (24)–(25) ($U=U_LU_R$ in Schwinger bosons); Sec. V "Loop-string-hadron formulation: Multiple dimensions": "Virtual point splitting: Two dimensions" (4-valent site → two trivalent sites; "the flux through [virtual links] is not counted toward $\hat H_E$"; the matter subdivision "is not needed for pure gauge theory"), "SU(2) invariants: Loop operators at gluonic vertices" ($\mathcal L^{\sigma\sigma'}_{ij}$), "Vertex factors and contractions" (the four vertex-factor matrices RL, LR, RR, LL), "The 2D Hamiltonian" ($H_E$ in flux numbers; plaquette as a product of vertex factors), "2D dynamics on an orthonormal basis" (loop basis $|\ell_{pq},\ell_{qr},\ell_{rp}\rangle$ with normalisation $[\ell_{pq}!\ell_{qr}!\ell_{rp}!(\ell_{pq}+\ell_{qr}+\ell_{rp}+1)!]^{-1/2}$, number operators, normalised ladder operators $\Lambda^\pm_{ij}$, Table "Factorization of all SU(2) singlet operators at a gluonic site", and the 2D Abelian Gauss laws). The printed equation numbers of Sec. V could not be confirmed from the HTML rendering; the items are cited by subsection title and were all re-derived numerically (§3).
2. I. Raychowdhury, J. R. Stryker, "Solving Gauss's law on digital quantum computers with loop-string-hadron digitization", arXiv:1812.07554, Phys. Rev. Research 2, 033039 (2020). Used: Sec. II "Truncation and binary representation": $N=\lceil\log_2(\bar j+1)\rceil$ qubits per gluonic loop number for cutoff $\bar j$ ("choose a maximum flux saturation strength and require links to have matching flux on either side"); flux numbers $n_1=\ell_{31}+\ell_{12}$, $n_2=\ell_{12}+\ell_{23}$, $n_3=\ell_{23}+\ell_{31}$; AGL-check circuits (not needed in M7).
3. I. Raychowdhury, "Low energy spectrum of SU(2) lattice gauge theory: an alternate proposal via loop formulation", arXiv:1804.01304, Eur. Phys. J. C 79, 235 (2019) — pure-gauge point splitting (honeycomb), loop states "exact and orthonormal" (abstract checked).
4. R. Anishetty, I. Raychowdhury, "SU(2) lattice gauge theory: local dynamics on nonintersecting electric flux loops", arXiv:1408.6331, Phys. Rev. D 90, 114503 (2014) — background on local loop operators (section list checked; not used for formulas).
5. Z. Davoudi, I. Raychowdhury, A. Shaw, "Search for efficient formulations for Hamiltonian simulation of non-Abelian lattice gauge theories", arXiv:2009.11802, Phys. Rev. D 104, 074505 (2021) — 1+1D with matter; LSH compared with angular-momentum, fermionic, bosonic formulations (abstract checked). No 2+1D pure-gauge plaquette circuit.
6. Z. Davoudi, A. F. Shaw, J. R. Stryker, "General quantum algorithms for Hamiltonian simulation with applications to a non-Abelian lattice gauge theory", arXiv:2212.14030, Quantum 7, 1213 (2023) — LSH circuits in 1+1D by singular-value diagonalisation of the ladder terms (abstract checked). Same idea as our frame + diagonal walk: diagonalise the off-diagonal term, apply a diagonal phase, undo.
7. S. V. Kadam, I. Raychowdhury, J. R. Stryker, arXiv:2212.04490, Phys. Rev. D 107, 094513 (2023) (SU(3), 1+1D); S. V. Kadam, A. Naskar, I. Raychowdhury, J. R. Stryker, arXiv:2407.19181, Phys. Rev. D 111, 074516 (2025) (SU(3) trivalent vertex, the "beyond 1D" building block). Not needed for the SU(2) plaquette: at an SU(2) trivalent vertex the loop basis is orthonormal with no multiplicity label (item 1).
8. Z.-X. Yang, H. Matsuda, X.-G. Huang, K. Kashiwa, "Quantum simulation of QC2D on a 2-dimensional small lattice", arXiv:2503.20828 (LSH in 2+1D with fermions mapped to spins; abstract checked); F. Ilčić et al., arXiv:2602.18080 (1+1D LSH hadron dynamics on IBM hardware; title checked). Web search (2026-11-10) found **no published gate-level circuit for the 2+1D pure-gauge LSH plaquette**; the circuit of §5 is our construction.
9. Project sources: `refs/su2_plaquette_truncations_encodings.md` §4.4, §5 (LSH row: 24 qubits at $j_{\max}=\tfrac12$); `refs/su2_plaquette_encodings.py` (register rule `8 * 3 * qubits_binary(2 jmax + 1)`).

## 2. The model (prototype `proto_m7_lsh_model.py`, part P3)

### 2.1 Geometry and point splitting
The diagram is METHODS §1 (inner links $b,r,t,l$ = 0..3; outer links $o_0..o_7$ = 4..11; corners $c_0..c_3$; loop $U_P=U_bU_rU_t^\dagger U_l^\dagger$). Each corner $c$ is split into the 'in' site with legs $(1,2,3)=(p(c),n(c),v)$ and the 'out' site with legs $(1,2,3)=$ (outer 1, outer 2, $v$): $p(c)$/$n(c)$ = the previous/next inner link along the loop $b\to r\to t\to l$, i.e. $(p,n)=(l,b),(b,r),(r,t),(t,l)$ at $c_0..c_3$; the outer legs are $(o_0,o_1),(o_2,o_3),(o_4,o_5),(o_6,o_7)$ (`Diagram.corners` order); $v$ is the virtual link of the corner. This is `geometry.point_split` and the (inner \| outer) pairing of METHODS §5.

Raychowdhury–Stryker split every site of a periodic lattice by pairing the $+e_1,+e_2$ legs against the $-e_1,-e_2$ legs. That equals our pairing at corners $(0,0)$ and $(1,1)$ but pairs one inner with one outer link at $(1,0)$ and $(0,1)$. §6 quantifies the difference; the plan 001 §3 pairing is kept (decision D1).

### 2.2 Site Hilbert space, truncation, register
A trivalent site has an orthonormal basis $|\ell_{12},\ell_{23},\ell_{31}\rangle$, $\ell_{ij}\in\{0,1,2,\dots\}$, with leg fluxes
$$N_1=\ell_{31}+\ell_{12},\qquad N_2=\ell_{12}+\ell_{23},\qquad N_3=\ell_{23}+\ell_{31},\qquad j_i=N_i/2,$$
equivalently $\ell_{12}=j_1+j_2-j_3$, $\ell_{23}=j_2+j_3-j_1$, $\ell_{31}=j_3+j_1-j_2$: the loop numbers are the unique solution of the triangle rule, so (loop numbers) ↔ (admissible spin triple) is a bijection (checked for all 8 one-bit codes: the map to $(N_1,N_2,N_3)$ is injective and $N_1+N_2+N_3$ is even).

Truncation $j_{\max}=\tfrac12$ on the 12 physical links, virtual spin $J\le1$ (needed to reproduce the 433 Kogut–Susskind states; note §7 "intertwiner cutoff"): every loop number is 0 or 1 ⇒ **1 qubit per loop number, 3 per site, 24 qubits**. Site code $s=\ell_{12}+2\ell_{23}+4\ell_{31}$. The flux cap $N_1\le1,N_2\le1$ leaves **5 valid site codes** of 8:

| code $s$ (bits $\ell_{31}\ell_{23}\ell_{12}$) | $(j_1,j_2,J)$ | meaning at an 'in' site |
|---|---|---|
| `000` | $(0,0,0)$ | empty |
| `001` | $(\tfrac12,\tfrac12,0)$ | one line $p\to n$ |
| `010` | $(0,\tfrac12,\tfrac12)$ | one line $n\to v$ |
| `100` | $(\tfrac12,0,\tfrac12)$ | one line $v\to p$ |
| `110` | $(\tfrac12,\tfrac12,1)$ | two lines through the virtual link ($J=1$) |

(`011`, `101`, `111` put $N=2$, i.e. $j=1$, on a physical leg.) Register: data `d[0..11]`, 'in' site $c$ at qubits $3c,3c+1,3c+2=(\ell_{pn},\ell_{nv},\ell_{vp})$; outer `o[0..11]`, 'out' site $c$ at $12+3c,..=(\ell_{12},\ell_{2v},\ell_{v1})$.

### 2.3 Abelian Gauss law and the count 433
AGL: for each inner link, $N_n(\text{in},c)=N_p(\text{in},c+1)$ (4 conditions); for each virtual link, $N_v(\text{in},c)=N_v(\text{out},c)$ (4 conditions). The far ends of the outer links are not sites (METHODS §3: spectator index), so outer links carry no condition.

Map to the 433 Gauss-law states: label $((j_0..j_{11}),(J_0..J_3))$ ↦ site codes by §2.2 (`code_of_label`); conversely an AGL-valid register state defines one spin per link and one $J_c$ per corner obeying the triangle rule at all 8 trivalent sites, which is the route-B label set (METHODS §5), itself in bijection with the corner-singlet basis of route A (M0-X1/X4).

Measured (brute force, `p3_register`):

| Quantity | Value |
|---|---|
| site-valid register states | $5^8=390\,625$ |
| of those AGL-valid | **433**, equal as a set to the 433 label codes (injective) |
| inner register: site-valid / AGL on the 4 inner links | $5^4=625$ / **47** (= the 47 inner labels) |
| bright (no site in `110`) / dark | **16 / 31** |
| distinct outer-site patterns among the 433 states | **305** of 625 (spin network: 128 outer-link patterns), each with 1 or 2 states |
| raw register (all $2^{24}$ bit strings, no flux cap): inner AGL-valid / all AGL-valid | 82 of 4096 / **5920** |

The last row shows that the AGL alone does not select the $j_{\max}=\tfrac12$ space: the raw register also holds $j=1$ links; the flux cap (5 valid site codes) is part of the validity rule. Kernel-checked in Lean (§7): 5, 47, 16, 31, 433, 256 (bright states), 82, 5920.

## 3. Operators in LSH variables

### 3.1 Site-local loop operators, verified against the oscillators (P1)
With doublets $a_\alpha(i)$ at the three legs and $\tilde a_\alpha=\epsilon_{\alpha\beta}a_\beta$: $\mathcal L^{++}_{ij}=a^\dagger(i)\!\cdot\!\tilde a^\dagger(j)$, $\mathcal L^{+-}_{ij}=a^\dagger(i)\!\cdot\!a(j)$, $\mathcal L^{-+}_{ij}=a(i)\!\cdot\!a^\dagger(j)$, $\mathcal L^{--}_{ij}=a(i)\!\cdot\!\tilde a(j)$. On the loop basis (source 1, factorisation table; $S=\ell_{12}+\ell_{23}+\ell_{31}$, pair $(ij)=(12)$, third leg 3):
$$\mathcal L^{++}_{12}|\ell\rangle=\sqrt{(\ell_{12}+1)(S+2)}\,|\ell_{12}{+}1\rangle,\qquad \mathcal L^{--}_{12}|\ell\rangle=\sqrt{\ell_{12}(S+1)}\,|\ell_{12}{-}1\rangle,$$
$$\mathcal L^{+-}_{12}|\ell\rangle=-\sqrt{(\ell_{31}+1)\ell_{23}}\,|\ell_{31}{+}1,\ell_{23}{-}1\rangle,\qquad \mathcal L^{-+}_{12}|\ell\rangle=-\sqrt{\ell_{31}(\ell_{23}+1)}\,|\ell_{31}{-}1,\ell_{23}{+}1\rangle .$$
Check: in the Fock space of 6 oscillator modes cut at 4 quanta (dimension 15 625) the 17 loop states with $S\le3$ are orthonormal ($6.7\cdot10^{-16}$), are eigenstates of the flux numbers ($4.4\cdot10^{-16}$), and the four formulas hold on 120 matrix columns with residual $\le1.1\cdot10^{-15}$.

### 3.2 Vertex factors and the plaquette (P2, P4)
$U=U_LU_R$ with $U_L=\tfrac1{\sqrt{N_L+1}}\begin{pmatrix}a_2^\dagger&a_1\\-a_1^\dagger&a_2\end{pmatrix}$, $U_R=\begin{pmatrix}a_1^\dagger&a_2^\dagger\\-a_2&a_1\end{pmatrix}\tfrac1{\sqrt{N_R+1}}$ (source 1, Eqs. (24)–(25)). Going round $U_bU_rU_t^\dagger U_l^\dagger$, the two link-end matrices that meet at a corner multiply to a $2\times2$ matrix of site-local operators (incoming leg $p$, outgoing leg $n$), all of the form $\pm(N_n+1)^{-1/2}\mathcal L^{\sigma_p\sigma_n}_{pn}(N_p+1)^{-1/2}$:

| corner | legs $(p,n)$ | type | vertex-factor matrix (rows: index shared with the previous corner) |
|---|---|---|---|
| $c_0$ | $(l,b)$ | LL: $U_L^\dagger(l)U_L(b)$ | $\begin{pmatrix}\mathcal L^{-+}&-\mathcal L^{--}\\ \mathcal L^{++}&\mathcal L^{+-}\end{pmatrix}$ |
| $c_1$ | $(b,r)$ | RL: $U_R(b)U_L(r)$ | $\begin{pmatrix}\mathcal L^{++}&\mathcal L^{+-}\\-\mathcal L^{-+}&\mathcal L^{--}\end{pmatrix}$ |
| $c_2$ | $(r,t)$ | RR: $U_R(r)U_R^\dagger(t)$ | $\begin{pmatrix}\mathcal L^{+-}&-\mathcal L^{++}\\ \mathcal L^{--}&\mathcal L^{-+}\end{pmatrix}$ |
| $c_3$ | $(t,l)$ | LR: $U_L^\dagger(t)U_R^\dagger(l)$ | $\begin{pmatrix}-\mathcal L^{--}&-\mathcal L^{-+}\\ \mathcal L^{+-}&-\mathcal L^{++}\end{pmatrix}$ |

$$\mathrm{Tr}\,U_P=\mathrm{tr}\big(\mathcal V_{c_0}\mathcal V_{c_1}\mathcal V_{c_2}\mathcal V_{c_3}\big),\qquad H_B=-\big(\mathrm{Tr}\,U_P+\mathrm{Tr}\,U_P^\dagger\big),\qquad H_E=\sum_{\ell=1}^{12}\tfrac{N_\ell}{2}\big(\tfrac{N_\ell}{2}+1\big).$$
The type of a corner follows from the loop orientation (arrive along $+$link: its R end; along $-$link: its L end with $U^\dagger$; leave along $+$link: L end; along $-$link: R end). The four matrices were verified as operator identities on 81 Fock states (two doublets, $\le2$ quanta per mode): residual $1.1\cdot10^{-16}$ each. Each of the 16 terms of the trace moves the four inner links by $\pm\tfrac12$ and keeps every $J_c$ and every outer leg: the plaquette acts on the four 'in' sites only. With the flux cap, on the 5 valid site codes the non-zero dressed ladder factors are

| site (bits $\ell_{31}\ell_{23}\ell_{12}$) | move $(\sigma_p,\sigma_n)$ | LSH factor | 6j $F$ of route B |
|---|---|---|---|
| `000` → `001` | $(+,+)$ | $+1$ | $+1$ |
| `001` → `000` | $(-,-)$ | $+1$ | $+1$ |
| `010` → `100` | $(+,-)$ | $-1$ | $+1$ |
| `100` → `010` | $(-,+)$ | $-\tfrac12$ | $-\tfrac12$ |
| `110` → — | $(-,-)$ | $0$ | $0$ |

(moduli equal to $2.2\cdot10^{-16}$; the sign difference in the third row is compensated by the vertex-factor signs).

### 3.3 Result and cross-checks (P4)
On the 47 inner codes $P=\mathrm{Tr}\,U_P$ is real symmetric with 16 non-zero entries and $K_{\rm LSH}=-(P+P^{\mathsf T})$ satisfies

| Check | Measured |
|---|---|
| $\max|K_{\rm LSH}-K_{6j}|$ under the label map (raw signs, no gauge) | $1.8\cdot10^{-15}$ (`gauge_align` finds 0 minus signs) |
| structure | matching of 8 bright pairs; partner = per-site flip `000`↔`001`, `010`↔`100`; couplings $-2$ (all $w_c=0$), $-\tfrac12$ (all $w_c=1$), $+1$ (the six classes with two $w_c=1$), $w_c=N_v\bmod2=[J_c=\tfrac12]$; 31 dark rows |
| 433 states: `gauge_align`$(H_B^{\rm LSH},H_B^{6j})$ / $(H_B^{A},H_B^{\rm LSH})$ | $1.8\cdot10^{-15}$ (0 minus) / $8.9\cdot10^{-16}$ (64 minus) |
| spectrum of $H_B$ | $-2(16),-1(96),-\tfrac12(16),0(177),\tfrac12(16),1(96),2(16)$ |
| spectra of $\tfrac{g^2}2H_E+\tfrac1{g^2}H_B$, LSH vs A / vs B | $g^2=0.5$: $1.0\cdot10^{-14}$ / $3.6\cdot10^{-15}$; $1$: $5.3\cdot10^{-15}$ / $1.8\cdot10^{-15}$; $2$: $7.1\cdot10^{-15}$ / $5.0\cdot10^{-16}$ |
| $H_E$ from fluxes vs $\sum j(j+1)$ of the labels | $0$ (exact) |
| closed sector (all 'out' sites empty), $g^2=1$ | $\begin{pmatrix}0&-2\\-2&\tfrac32\end{pmatrix}$ (Paulo Eq. 37) |

Targets in our normalisation (METHODS §2): $U_E(\alpha)=e^{-i\alpha H_E^{\rm inner}}$ (diagonal, $\tfrac34$ per inner link with $N=1$), $U_B(\beta)=e^{-i\beta H_B}$; on a bright pair $U_B=e^{-i\beta kX}$ with $k\in\{-2,-\tfrac12,1\}$, identity on dark codes. $\max|U_B^{\rm LSH}-D^\dagger U_B^{A}D|=5.0\cdot10^{-16}$ ($\beta=0.61$), $3.3\cdot10^{-16}$ (0.23), $1.1\cdot10^{-15}$ (1.0); outer-electric target vs route A: 0.

## 4. Encoding object for the unchanged evaluator (`m7shim/proto/encodings_lsh.py`)
Same shape as `SpinNet`: `n_data = n_outer = 12`, 433 unit codes, `inner_codes()` = the 47 inner codes, target = the LSH operator in label order (identical to the spin-network target: the two encodings share one $433\times433$ target), `gauge` from `gauge_align(H_A, H_B^{LSH})`, `decode_state`: physical code $k$ ↦ `gauge[k]` × route-A state.

Codes that are data-valid and outer-site-valid but break the AGL on a virtual link ($47\cdot625-433=$ **28 942**) must decode to something the Gauss check can see (prompts/004: span leak is bounded by the Gauss residual). Rule: single electric basis state in which every spin-$\tfrac12$ end at corner $c$ is a $G^z$ eigenstate, inner ends $+\tfrac12$ if $J_{\rm in}\ne1$ else $-\tfrac12$, outer ends $-\tfrac12$ if $J_{\rm out}\ne1$ else $+\tfrac12$, far ends $m=+\tfrac12$. A corner whose two sites disagree on $J$ then has total $G^z\ne0$ (odd number of spin-$\tfrac12$ ends, or $(J_{\rm in},J_{\rm out})=(0,1)\to+1$ or $+2$, $(1,0)\to-1$ or $-2$). Measured on **all** 28 942 codes: electric keys pairwise distinct (isometry), disjoint from the support of every physical state (orthogonality), Gauss residual in $[0.5,2.0]$; the 433 physical decodes have Gauss residual $5.4\cdot10^{-16}$.

Through the real evaluator (identity target, 433 inputs): `swap`$(\ell_{nv},\ell_{vp})$ on a site → `leak` 1; the site map `001`↔`110` → no leak, span leak 1, Gauss ≥ ½; `x` on an ancilla → `dirty_ancilla`; `x` on an outer qubit → `writes_outer`; `cz(o[0],d[0])` → `error` 2; `cz(o[1],d[0])` → **accepted**: $\ell_{2v}$ of the 'out' site and $\ell_{pn}$ of the 'in' site of the same corner are never both 1 because of the AGL on the virtual link (a small demonstration of the don't-care space the AGL creates; relevant to M8).

## 5. General circuit (`proto_m7_lsh_circuit.py`, `m7shim/proto/lsh_walk.py`)

### 5.1 Why a non-linear frame is unavoidable
The plaquette move on a bright site is `000`↔`001` if $w=0$ and `010`↔`100` if $w=1$: $s\mapsto s\oplus(1,0,0)\oplus w(s)\,(1,1,1)$, an affine map whose linear part is not the identity. The 8 pair classes have 8 different 12-bit difference vectors, so no CNOT-only frame maps the move to $X$ on one qubit. One Toffoli-type gate per site is needed and sufficient:

**Transcoder** (per 'in' site, qubits $(x,y,z)=(\ell_{pn},\ell_{nv},\ell_{vp})$): `cx(y,z)` ($z\leftarrow w=N_v\bmod2$); `cx(y,x)` ($x\leftarrow N_n=2j_n$); `rccx(z,x,y)` ($y\leftarrow[J=1]$). After it the 12 data wires hold the spin-network data code (links $j_b,j_r,j_t,j_l$ on wires 0, 3, 6, 9; corner bits on 1, 4, 7, 10) plus $w_c=j_{p}\oplus j_{n}$ on wires 2, 5, 8, 11 (verified for all 433 labels; kernel-checked, §7). Cost per site 5 CX, 4 T (`rccx` = 3 CX, 4 T; METHODS §7). The relative phases of `rccx` are harmless: on valid codes the transcoder differs from the exact Toffoli version only by the phase $(-i)$ on site state `010`, and both members of every bright pair contain the same number of sites in `010` (1 for the six $k=1$ classes, 2 for the alternating class, 0 for the vacuum class), so the phase commutes with $U_B$; measured: exact with either control order.

### 5.2 Candidates

| Candidate | CX | rot | $T_{\rm fixed}$ | anc | $T(10^{-6})$ | Notes |
|---|---|---|---|---|---|---|
| **G: transcoder + spin-network walk `general7`** (chosen) | **94** | **4** | **88** | **7** | **342** | error $1.4$–$2.6\cdot10^{-14}$ at $\beta=0.4,0.61,1,2$; angles $(-\tfrac72,-1,3,\tfrac32)\beta$ solved from $K_{\rm LSH}$ (residual $<10^{-9}$ asserted); only `cx`, `x`, `h`, `rccx`, `rz`; Lean reuse of the spin-network walk theorems |
| transcoder + `pairs9` (su2qc-trotter, vendored in M3) | 74 | 9 | 56 | 3 | 608 | exact ($9.8\cdot10^{-15}$); best CX; comparison row and M8 seed |
| transcoder + `flags4` | 84 | 4 | 80 | 3 | 330 | exact ($1.1\cdot10^{-14}$); uses `rc3x`; comparison row and M8 seed |
| transcoder + `flags5` / `flags6` | 82 / 76 | 5 / 6 | 72 / 64 | 3 | 382 / 434 | exact |
| transcoder + Paulo's 15-qubit file ($\beta=0.05$ fixed) | 108 | 4 | 96 | 7 | — | equals $U_B(-0.05)$ in the LSH sign gauge (error $1.3\cdot10^{-14}$), i.e. $U_B(+0.05)$ up to the pair-sign gauge of METHODS-spinnet §2 |
| one multi-controlled rotation per bright pair directly on the 12 LSH qubits | not prototyped | 8 | — | — | — | each pair needs its own flag over ≥ 8 bits; strictly more Toffolis than one transcoder + one shared walk; rejected on cost |

G is chosen as the "general" circuit for the same reason as in M3 (most transparent 4-rotation design, project macros only) and so that Report 7 can state the LSH overhead like for like. The cheaper wrapped skeletons are reported as comparison rows and become round-0 seeds of M8 (decision D4).

### 5.3 Measured numbers of G (nominal $(\alpha,\beta)=(0.37,0.61)$)

| Circuit | CX | rot | $T_{\rm fixed}$ | depth | anc | error | Gauss | $T(\varepsilon)$ at $10^{-4},10^{-6},10^{-8},10^{-10}$ (pygridsynth; Qiskit) |
|---|---|---|---|---|---|---|---|---|
| $U_E$ stand-alone (8 `p`: $N_n=\ell_{pn}+\ell_{nv}$, never both 1) | 0 | 8 | 0 | 1 | 0 | $4.4\cdot10^{-16}$ | $5.3\cdot10^{-16}$ | 352, 512, 656, 832 (344, 472, 656, 760) |
| $U_B$ | 94 | 4 | 88 | 87 | 7 | $1.4\cdot10^{-14}$ | $5.4\cdot10^{-16}$ | 262, 342, 428, 500 (257, 340, 421, 494) |
| step order 1 (electric layer inside the transcoded frame: 4 `p` on the link wires) | 94 | 8 | 88 | 87 | 7 | $1.6\cdot10^{-14}$ | $5.5\cdot10^{-16}$ | 438, 598, 756, 916 (429, 574, 749, 874) |
| step order 2 | 94 | 12 | 88 | 87 | 7 | $1.6\cdot10^{-14}$ | $5.5\cdot10^{-16}$ | 598, 870, 1100, 1332 (593, 860, 1069, 1302) |
| $U_E$ + outer electric row (12 more `p`; reads 12 outer qubits, 305 blocks) | 0 | 20 | 0 | 1 | 0 | $7.7\cdot10^{-16}$ | — | — |

Same skeleton at the three angle pairs; the other order's target is rejected (0.515), the target at $-\beta$ is rejected (1.878; a gauge pin as in M3). With the outer register (31 qubits) the `physical` method runs all 433 states in 0.5 s: `outer_bits_read 0`, 1 block, sparse engine, certified. Synthesised circuits (sparse engine, `synth_tolerances`): $U_B$ $1.0\cdot10^{-4}$ / $1.3\cdot10^{-6}$ / $7.4\cdot10^{-11}$ against $4\cdot10^{-4}$ / $4.0\cdot10^{-6}$ / $1.4\cdot10^{-9}$ at $\varepsilon=10^{-4},10^{-6},10^{-10}$; step 1: $1.7\cdot10^{-4}$ / $2.0\cdot10^{-6}$ / $1.2\cdot10^{-10}$ against $8\cdot10^{-4}$ / $8.0\cdot10^{-6}$ / $1.8\cdot10^{-9}$; step 2 and $U_E$ likewise within 0.1–0.3 of the budget; Gauss residual of all synthesised outputs $\le6\cdot10^{-16}$ (every rotation acts inside the code space).

Electric layer: a stand-alone $U_E$ needs 8 rotations (or 4 rotations + 8 CX); inside the step the layer is applied after the transcoder, where each link is one wire, so the step has 4 electric rotations per layer at no CX cost. Spin network for comparison (METHODS-spinnet §8): $U_B$ 54 CX / 4 rot / 56 T; step 54 / 8 / 56 ⇒ LSH = spin network + 40 CX + 32 T.

## 6. What the Raychowdhury–Stryker pairing would cost (`proto_m7_lsh_rs_pairing.py`)
Rotating route A's $H_B$ into the basis in which corners $(1,0)$ and $(0,1)$ are paired as (inner, outer \| inner, outer):

| | (inner \| outer) everywhere (ours) | RS pairing at corners 1, 3 |
|---|---|---|
| non-zero entries of $H_B$ (433×433) | 256 | 400 |
| max non-zeros per row | 1 (a matching) | 4 |
| rows with a non-zero | 256 | 324 |
| distinct $|$matrix elements$|$ | $\tfrac12,1,2$ | $\tfrac14,\tfrac{\sqrt3}4,\tfrac12,\tfrac34,\tfrac{\sqrt3}2,1,\tfrac32,\sqrt3,2$ |
| depends on the outer spins | no | yes (16 of 47 inner patterns) |
| sites the plaquette acts on | 4 (12 qubits) | 6 (18 qubits), changes two virtual fluxes |

Spectrum identical ($3.3\cdot10^{-15}$): same theory, different basis. The uniform RS splitting is the natural one on a periodic lattice (every plaquette then looks the same); on this single plaquette the (inner \| outer) splitting is strictly cheaper and is what plan 001 fixed.

## 7. Lean prototypes
`scratch/planner/lean/LSHCounts.lean` (core Lean, no Mathlib; `decide` / `decide +kernel`; 10.8 s wall): `card_site_codes = 5`, `site_valid_list = [0,1,2,4,6]`, `flux_injective`, `flux_even`, `card_inner_codes = 47`, `card_bright_codes = 16`, `card_dark_codes = 31`, `card_states_lsh = 433`, `card_bright_states = 256`, `card_raw_inner = 82`, `card_raw_states = 5920`; `#print axioms`: `[propext]`.
`scratch/planner/lean/LSHCircuit.lean` (imports `Su2Plaq.SpinNet.Circuit`; 21 s wall incl. the Mathlib import): `transcode_into_spinnet`, `transcode_injective` (the transcoder maps the 47 LSH inner codes one-to-one onto the 47 spin-network codes), `transcode_w`, `coupling_matches_spinnet`, `pre_maps_partner_to_x` (transcoder + frame turn the plaquette move into $X$ on wire 0), `walk_slots_match`, `walk_table_exact` (integer Walsh table $=2\cdot2K$ on all 47 codes), `ancillas_clean`; axioms `[propext]`. The per-circuit native certificate needs a checker pinned to the LSH states: a copy of `lean/Su2PlaqCert/SpinNet/{Check,Main,Pins}.lean` with register sizes 12 + 12 (≈ 150 lines); the exporter of `su2plaq/spinnet/lean_export.py` is generic in the encoding except for `N_DATA`, `N_OUTER` and the per-code electric weight.

## 8. Validation of the locked tests
`tests/acceptance/m7/` (29 tests): `pytest --collect-only` clean; without production code all 29 fail with `PENDING:`; with the prototype modules served under the production names (`PYTHONPATH=scratch/planner/m7shim tools/pytest-safe -p shim_plugin -n 4 tests/acceptance/m7`) 23 pass in 14.6 s (longest test 4.9 s) and the 6 Lean/results tests stay `PENDING:`. Mutation check (`m7shim/mutation_check.py`): a flipped vertex sign, an undressed ladder, a $J$-blind fallback, a transcoder without `rccx`, a flipped electric sign in the step and in $U_E$ are each rejected by the named tests.

## 9. Decisions taken by default (for Digonto) — see prompts/400 §10
D1 pairing (inner \| outer) at all corners (not RS's uniform split). D2 register = raw loop numbers, 1 qubit each (24 qubits), bit order $(\ell_{12},\ell_{23},\ell_{31})$ per site; the "solved-constraint" LSH variant (half the registers, arXiv:1812.07554 Sec. IV) not used. D3 virtual flux up to 2 ($J\le1$), flux cap only on physical links. D4 general circuit = transcoder + `general7`; cheaper wrapped skeletons as comparison rows / M8 seeds. D5 stand-alone $U_E$ with 8 phases and no CX; in the step the electric layer sits inside the transcoded frame (4 phases). D6 outer electric row = 12 phases on the 12 outer-site qubits. D7 target/gauge convention = LSH signs (equal to route B); route A by `gauge_align`.

## 10. Files touched by this run
Written: this report, `prompts/400-lsh-m7-plan.md`, `docs/METHODS-lsh.md`, `tests/acceptance/m7/*` (8 files), `scratch/planner/proto_m7_*`, `scratch/planner/lean/LSH*.lean`, `scratch/planner/m7shim/*`. Not touched: `tests/acceptance/LOCK.json`, `notes/STATUS.md`, `src/`. Test runs wrote only `__pycache__` folders.
