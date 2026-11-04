# 001 — Research notes: SU(2) on the 2×2 torus, encodings, baselines, verification method

- Date: 2026-11-02
- Git commit: 4108afa (kickoff; no code yet)
- Prompt in force: `prompts/000-starter-plan.md` (this note feeds `prompts/001-m1-m3-spine-su2-2x2.md`)
- Related: `refs/2610.22367v1.txt` (Gu–Kemeny–Yelin–Lukin, SI V), `docs/METHODS.md`
- Prototype used for the numbers below: `scratch/planner/proto_m1.py`, `proto_counts.py`,
  `proto_qiskit.py` (planner scratch, not production code).

All sources were opened and read (PDF → `pdftotext`) unless marked "abstract only".

## 1. Hamiltonian and conventions (sources read)

**Kogut–Susskind SU(2) Hamiltonian** (Klco–Stryker–Savage, arXiv:1908.06935, PRD 101, 074512,
Eqs. (1)–(2); Byrnes–Yamamoto quant-ph/0510027 Eq. (27); Zache–González-Cuadra–Zoller
arXiv:2304.02527 Eq. (1)), lattice units $a=1$:
$$H_{\rm g} = \frac{g^2}{2}\sum_{\ell}\hat E_\ell^2 \;-\; \frac{1}{2g^2}\sum_{p}\big(\hat\Box_p+\hat\Box_p^\dagger\big),
\qquad \hat\Box_p = \mathrm{Tr}\big(U_{x}(\mathbf n)\,U_{y}(\mathbf n+\hat x)\,U_{x}^\dagger(\mathbf n+\hat y)\,U_{y}^\dagger(\mathbf n)\big).$$

**Electric (representation) basis** per link $|j,m_L,m_R\rangle$, $j\le j_{\max}$,
$\hat E^2|j m_L m_R\rangle = j(j+1)|j m_L m_R\rangle$. Link operator (fundamental rep) — KSS Eq. (5),
Zohar–Burrello arXiv:1409.3085 Eq. (42) (Wigner–Eckart / Clebsch–Gordan series):
$$\langle J,M_L,M_R|\,\hat U_{\alpha\beta}\,|j,m_L,m_R\rangle
 = \sqrt{\frac{2j+1}{2J+1}}\;\langle j\,m_L;\tfrac12\,\alpha|J\,M_L\rangle\,\langle j\,m_R;\tfrac12\,\beta|J\,M_R\rangle,
 \quad J=j\pm\tfrac12,\ M_{L,R}=m_{L,R}+\alpha,\beta .$$
Truncation at $j_{\max}$ is a projection: the product of link-truncated operators equals
$P\,\hat\Box\,P$ because operators on different links commute (planner derivation, checked
numerically in the prototype). This is the "naive cutoff" of Zache et al. / Hayata–Hidaka.

**Gauge generators.** Left end: $\hat L^a$ acts on $m_L$ as the spin-$j$ matrix $J^a$; right end:
$\hat R^a$ acts on $m_R$ as $-(J^a)^*$ (conjugate representation, because
$D^j_{mn}(U g^\dagger)=\sum_{n'}D^j_{mn'}(U)D^j_{nn'}(g)^*$). Gauss law at vertex $v$:
$\hat G^a_v=\sum_{\ell:\,v=\mathrm{start}}\hat L^a_\ell+\sum_{\ell:\,v=\mathrm{end}}\hat R^a_\ell+\hat Q^a_v$,
with $\hat Q^a_v$ the matter/static charge. Prototype check: $\|[\hat H_E,\hat G^a_v]\|=\|[\hat H_B,\hat G^a_v]\|=0$
exactly (machine zero) on the full $5^8$-dimensional space — this fixes the relative convention
between the $U$ matrix elements and the generators (a wrong conjugation on the right end breaks
the commutator).

**Staggered fermions in 2+1D** (Zohar–Cirac arXiv:1805.05347 Sec. II A; Raychowdhury–Stryker
arXiv:1912.06133 Sec. V): two-colour fermion $\psi_{\mathbf n,\alpha}$ per site,
$$H_{\rm m} = m\sum_{\mathbf n}(-1)^{n_x+n_y}\psi^\dagger_{\mathbf n}\psi_{\mathbf n}
+ t\sum_{\mathbf n,\mu}\eta_\mu(\mathbf n)\big[\psi^\dagger_{\mathbf n}\,U_{\mu}(\mathbf n)\,\psi_{\mathbf n+\hat\mu}+\text{h.c.}\big],
\quad \eta_x=1,\ \eta_y(\mathbf n)=(-1)^{n_x},\ t=\tfrac{1}{2a}.$$
Charge $\hat Q^a_{\mathbf n}=\psi^\dagger_{\mathbf n}\frac{\sigma^a}{2}\psi_{\mathbf n}$.
Static source at $\mathbf n$: an extra spin-$\tfrac12$ register with $\hat Q^a=S^a$; for SU(2)
$\bar{\mathbf 2}\cong\mathbf 2$, so a "quark–antiquark pair" is two such doublets.

## 2. Gauge-invariant (spin-network / LSH) basis and the 6j plaquette operator

- Point-split each 4-valent site into two trivalent vertices joined by a virtual link
  (Raychowdhury–Stryker 1912.06133 Sec. V A, Fig. 4; Zache et al. 2304.02527 Fig. 1b). Pairing used:
  outgoing $(+x,+y)$ legs at $v_{\rm out}$, incoming $(-x,-y)$ legs at $v_{\rm in}$.
  Basis: $j$ on 8 real links ($\le j_{\max}$) and on 4 virtual links (triangle rule at all 8
  trivalent vertices; virtual $j$ up to $2j_{\max}$).
- A plaquette loop is a hexagon through 6 trivalent vertices (4 real + 2 virtual edges inside).
  Plaquette matrix element = product of six F-symbols, one per hexagon vertex (Zache et al.
  Eq. (2), (9); same object as the LSH loop operators of 1912.06133 Sec. V):
  $$\langle j'|\hat\Box|j\rangle=\prod_{i=1}^{6}F^{\,j_{o_i}\;j_{e_{i-1}}\;j_{e_i}}_{\;\frac12\;\;j'_{e_i}\;\;j'_{e_{i-1}}},\qquad
  F^{j_1 j_2 j_{12}}_{j_3 j_4 j_{23}}=(-1)^{j_1+j_2+j_3+j_4}\sqrt{(2j_{12}+1)(2j_{23}+1)}
  \begin{Bmatrix} j_1&j_2&j_{12}\\ j_3&j_4&j_{23}\end{Bmatrix},$$
  with $e_i$ the inner (loop) edges, $o_i$ the third ("outer") edge at vertex $i$, and
  $j'_{e}=j_e\pm\tfrac12$ (components with a real link above $j_{\max}$ dropped).
- **Prototype result (independent check):** spectrum of $H_{\rm g}$ in the 63-dimensional physical
  subspace at $j_{\max}=\tfrac12$, $g^2=1$: full-KS-with-intertwiners vs spin-network-6j agree to
  $\max|E_A-E_B| = 1.6\times10^{-14}$ (`proto_m1.py`). Lowest levels
  $E_0=-1.60859$, $E_{1,2}=-0.522527$, $E_3=-0.232051$, $E_4=0.5$.
- q-deformed SU(2)$_k$ (Hayata–Hidaka arXiv:2305.05950, JHEP09(2023)126; Zache et al.
  2304.02527 Eqs. (10)–(15)): same basis with $j\le k/2$, fusion rule $j_1+j_2+j_3\le k$,
  $[n]=\sin(\pi n/(k+2))/\sin(\pi/(k+2))$, $d_j=[2j+1]$, electric term $\propto$ q-Casimir, F-symbols → q-6j.
  Matched truncation: $k=2j_{\max}$; the $k=1$ model has a *smaller* intertwiner space than KS at
  $j_{\max}=\tfrac12$ (virtual $j=1$ forbidden), so it is model-changing.

## 3. Encodings: what the literature gives for each item of the list

| # | Encoding | Source read | Status for 2×2 torus |
|---|---|---|---|
| 1 | KS electric basis $|j m_L m_R\rangle$ | KSS 1908.06935; Byrnes–Yamamoto 0510027; Zohar–Burrello 1409.3085 | **build** (baseline). 5 states/link at $j_{\max}=\tfrac12$ → 3 qubits/link, 24 qubits (C1). |
| 2 | Gauge-invariant spin-network basis | KSS Eq. (6); Zache 2304.02527 Eq. (2) | **build** (local SN register and compact register). |
| 3 | Rishon / quantum-link model | Banerjee et al. 1211.2242; Murairi et al. 2208.11789 (4-dim link model) | **build later (M7)**: model-changing; 4-state link (2 qubits). Published cost: 180 CNOT/plaquette/step. |
| 4 | LSH | Raychowdhury–Stryker 1912.06133 Sec. V (2D) | same physical basis as #2 at matched truncation; LSH labels = SN labels with the $(12)(\bar1\bar2)$ splitting. **build** = #2 with LSH labelling; fermion vertex factors in M4. |
| 5 | Prepotential / Schwinger boson | Mathur hep-lat/0403029 (abstract only); 1912.06133 Sec. III | gauge-invariant sector ≡ LSH; **not built separately (dominated: same states as #4, larger register)**. |
| 6 | q-deformed SU(2)$_k$ | Hayata–Hidaka 2305.05950; Zache 2304.02527 | **build** ($k=1$) reusing the SN machinery; model-changing. |
| 7 | Discrete subgroups BT/BO/BI | Lamm–Lawrence–Yamauchi 1903.08807 (primitive gates, kinetic term $H_K=-\log T_K$); Gustafson et al. 2208.12309 (BT gates: $U_\times$ 22 CNOT, $U_{-1}$ 31 CNOT, $U_F$ 1025 CNOT); Ji–Lamm–Zhu 2005.14221 | **build BT in M7** (group-register, 5 qubits/link = 40 qubits; magnetic layer diagonal → paper SI V techniques apply). BO/BI: cost by scaling + justification. |
| 8 | $S^3$ partitionings | Hartung et al. 2212.09496 (Fibonacci/linear/volleyball) | **justify**: no group closure → not gauge-invariant; no physical subspace; optional own-model build in M7. |
| 9 | Fuzzy SU(2) | Alexandru et al. 2308.05253 | **justify/optional M7**: model-changing; same universality class claim; link space finite irrep. |
| 10 | Orbifold lattice | Buser et al. 2011.06576 Sec. 2.3, 3.1 | **justify**: non-compact bosons, $\ge 8$ oscillators per link, Fock cutoff $\Lambda$; $8\cdot 8\cdot\log_2\Lambda$ qubits ≫ verifiable. |
| 11 | Mixed/dual basis, fully gauge-fixed | Grabowska–Kane–Bauer 2409.10610 (maximal tree, rods, mixed basis); Froland–Grabowska–Li 2512.22782 (2 open plaquettes, Pauli-truncation circuits) | **build matched-truncation maximal-tree gauge fixing in the electric basis** (5 physical links, global singlet). Mixed-basis variant: justification (needs a 2×2-torus derivation not in literature). |
| 12 | Integrate out gauge field (1+1D) | — | **inapplicable** in 2+1D (needs open chain); #11 is the 2+1D analogue. |
| 13 | Zohar–Cirac fermion elimination | 1805.05347 (works for SU(2N) fundamental in any d) | **M4 candidate** (derive for 2×2 torus; spectrum test). |
| 14 | Jordan–Wigner | standard | **build** (M4). |
| 15 | Bravyi–Kitaev / VC / compact | Derby–Klassen 2003.06939 (abstract only) | **build BK (M4)**; VC/compact: justify as dominated at 8 modes (JW string ≤ 7). |
| 16 | Binary register | Sawaya et al. 1909.12847 | **build** (default). |
| 17 | Unary / Gray | Sawaya et al. 1909.12847 Sec. II A | **build Gray** (3 qubits/link); unary (5 qubits/link, 40 qubits) via sparse evaluator, `slow`. |
| 18 | Native qudits | Calajò et al. 2402.07987 (6-level ion qudits, SU(2) 1+1D) | **justify**: no qudit simulator; report "two-qudit gate" count (entangling ops between link registers) as an extra column. |
| 19 | Qumodes | Crane et al. 2409.03747 (not read) | **justify**: no CV simulator; U(1)/Z2 only in literature. |
| 20 | Gauss law as error detection | Stryker 1812.01617 (oracles, $O(1)$ ancillas, few CNOT); Rajput–Roggero–Wiebe 2112.05186 | **build one representative on KS-C1 in M7**: acts trivially on the physical subspace; cost overhead + optional noisy run. |
| 21 | Energy penalty | Halimeh et al. 2007.00668 (single-body, $\sim(\lambda/V)^2$), Stannigel 1308.0528 (not read) | same as #20: identity on physical subspace; overhead only. |
| 22 | Light-front | — | **inapplicable** (different quantisation surface; no 2×2 spatial torus comparison). |
| 23 | Abelian pilots | — | **$\mathbb Z_2$ pilot in M2** to exercise the evaluator (8 qubits, labelled "pilot", not SU(2)). |

## 4. Published circuit-cost baselines (for the comparison table)

- Murairi–Cervia–Kumar–Bedaque–Alexandru, arXiv:2208.11789: SU(2) one Trotter step,
  4-dim link model (QLM-like) **180 CNOT per plaquette**; 5-dim link model (KS $j_{\max}=\tfrac12$)
  **17,168 CNOT** per plaquette per step (Pauli-string compilation).
- Rahman–Lewis–Mendicelli–Powell, arXiv:2205.09247 (PRD 106, 074502): 1D chain of plaquettes at
  $j_{\max}=\tfrac12$, one qubit per plaquette after solving Gauss's law; **4 CNOT per 2nd-order
  Trotter step** for 2 plaquettes (Eqs. (2),(6)–(8)); hundreds of CNOTs total for a run.
- Klco–Stryker–Savage 1908.06935 Fig. 2–3: single plaquette operator at $\Lambda_j=\tfrac12$, 5-qubit
  (reduced to 3-qubit) circuits.
- Gustafson et al. 2208.12309 (BT): $U_\times$ 22 CNOT (39 on hardware), $U_{-1}$ 31 (49), $U_{\rm Tr}$
  from Eq. (27), $U_F$ 1025 CNOT (Qiskit transpiler); per-link gate counts Table IV.
- Froland–Grabowska–Li 2512.22782: two open plaquettes, 3 qubits/plaquette, CNOT bound
  $\sum_P 2(w(P)-1)$ (Eq. (71)), scaling $O(2^{2n_q+1})$.
- Gu et al. 2610.22367 SI V (template): group-register magnetic layer, specialised running-product
  representation (146 → 35 Toffoli per update), loop reuse (5.4 vs 6–10 multiplications/loop),
  direct trace readout (478 → 76 Toffoli).

## 5. Verification method chosen (fits 62 GB)

- Physical-subspace dimensions on the 2×2 torus (vertex-intertwiner counting, `proto_counts.py`):
  see table in the plan §3 (filled from the prototype run).
- Full KS tensor-product space is only used at $j_{\max}=\tfrac12$ for C1 (dim $5^8=390{,}625$)
  and C3 (×4): sparse operators, explicit generators. For C2/C4 and $j_{\max}=1$ the physical
  subspace is built block-wise from vertex intertwiners (block = ⊗ over vertices of leg spaces) and
  matrix elements by tensor contraction — never the full space.
- Circuit exactness: apply the circuit to each physical basis state (Aer statevector, ≤ 26 qubits)
  or to the state with a sparse support-tracking simulator (> 26 qubits), compare the restricted
  unitary with the target. The paper's trajectory-sampling bound (Methods, Eqs. (17)–(20)) is used
  for the group-register (BT) magnetic layer, which is diagonal.

## 6. Prototype numbers (Trotter error, transpile pipeline)

Filled from `proto_counts.py` / `proto_qiskit.py` — see plan §3 and §5 (numbers copied there with
the command that produced them).
