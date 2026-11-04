# METHODS — su2qc-encoding

Every numerical method in use, its equations, conventions and source (arXiv ID / DOI / URL).
Maintained by the planner; builders cite sections here (e.g. "METHODS §2.3").
Plain-English definitions are given the first time a term appears.

Last updated: 2026-11-02 (planner, plan 001). Research notes: `reports/research/001-su2-2x2-encodings-survey.md`.

## 1. Lattice, Hilbert space, conventions

### 1.1 Lattice
- 2×2 sites with periodic boundary conditions (a torus): sites $\mathbf n=(n_x,n_y)\in\{0,1\}^2$,
  site index $s = 2n_y + n_x$. Links $\ell=(\mathbf n,\mu)$, $\mu\in\{x,y\}$ ($\mu$ index 0,1), oriented
  from $\mathbf n$ ("start", left end) to $\mathbf n+\hat\mu \bmod 2$ ("end", right end).
  Link index $i = 2s+\mu$. There are 8 links and 4 plaquettes. Note: because $L=2$, the two
  $x$-links of a row connect the *same* pair of sites in opposite directions (a doubled edge); the
  code must index links by $(\mathbf n,\mu)$, never by the unordered site pair.
- Plaquette at $\mathbf n$ (counter-clockwise), as an ordered list of (link, orientation):
  $$\hat\Box_{\mathbf n}=\mathrm{Tr}\big[U_x(\mathbf n)\,U_y(\mathbf n+\hat x)\,U_x^\dagger(\mathbf n+\hat y)\,U_y^\dagger(\mathbf n)\big].$$
- Lattice spacing $a=1$; all energies in units of $1/a$.

### 1.2 Hamiltonian (Kogut–Susskind, SU(2), 2+1D)
Source: Klco–Stryker–Savage, arXiv:1908.06935, Phys. Rev. D 101, 074512 (2020), Eqs. (1)–(2);
Byrnes–Yamamoto quant-ph/0510027 Eq. (27); Zache–González-Cuadra–Zoller arXiv:2304.02527 Eq. (1).
$$H = \frac{g^2}{2}\sum_{\ell}\hat E_\ell^2\;-\;\frac{1}{2g^2}\sum_{p}\big(\hat\Box_p+\hat\Box_p^\dagger\big)
\;+\; m\sum_{\mathbf n}(-1)^{n_x+n_y}\,\psi^\dagger_{\mathbf n}\psi_{\mathbf n}
\;+\; t\sum_{\mathbf n,\mu}\eta_\mu(\mathbf n)\Big[\psi^\dagger_{\mathbf n}\,U_\mu(\mathbf n)\,\psi_{\mathbf n+\hat\mu}+\mathrm{h.c.}\Big].$$
- $\hat E^2_\ell$: quadratic Casimir ("electric energy") of link $\ell$, eigenvalue $j(j+1)$.
- Staggered-fermion phases (Zohar–Cirac arXiv:1805.05347 Sec. II A; Raychowdhury–Stryker
  arXiv:1912.06133 Sec. V): $\eta_x(\mathbf n)=1$, $\eta_y(\mathbf n)=(-1)^{n_x}$. Mass sign
  $(-1)^{n_x+n_y}$. $\psi_{\mathbf n}=(\psi_{\mathbf n,\uparrow},\psi_{\mathbf n,\downarrow})$ is a colour doublet;
  $\psi^\dagger U\psi=\sum_{\alpha\beta}\psi^\dagger_\alpha U_{\alpha\beta}\psi_\beta$.
- Default parameters (plan 001): $g^2=1$, $m=0.5$, $t=0.5$ (i.e. $1/2a$), total time $T=1$.
- Pure-gauge cases: drop the $m$ and $t$ terms. Static sources: extra spin-$\tfrac12$ registers that
  enter only Gauss's law (§1.4); the Hamiltonian acts as identity on them.
- For SU(2) the plaquette trace is real as a function, and $\hat\Box^\dagger_p$ is the reversed loop;
  on the physical subspace $\hat\Box_p$ is Hermitian (checked numerically), so
  $-\frac{1}{2g^2}(\hat\Box+\hat\Box^\dagger)=-\frac{1}{g^2}\hat\Box$ there. Code always uses the
  symmetric form so that the full-space operator is Hermitian by construction.

### 1.3 Electric (representation) basis of a link — encoding #1
Per link, states $|j,m_L,m_R\rangle$, $j\in\{0,\tfrac12,\dots,j_{\max}\}$, $m_{L,R}\in\{-j,\dots,j\}$;
$d_{\rm link}(j_{\max})=\sum_j(2j+1)^2$ ($=5$ at $j_{\max}=\tfrac12$, $14$ at $j_{\max}=1$).
Ordering: $j$ ascending, then $m_L$ ascending, then $m_R$ ascending. $|j m_L m_R\rangle$ corresponds to
the wavefunction $\sqrt{2j+1}\,D^j_{m_L m_R}(U)$ (Wigner D-matrix).

Link operator in the fundamental representation (Wigner–Eckart / Clebsch–Gordan series),
KSS Eq. (5), Zohar–Burrello arXiv:1409.3085 Eq. (42):
$$\langle J,M_L,M_R|\hat U_{\alpha\beta}|j,m_L,m_R\rangle=\sqrt{\frac{2j+1}{2J+1}}\,
\langle j\,m_L;\tfrac12\,\alpha\,|\,J\,M_L\rangle\,\langle j\,m_R;\tfrac12\,\beta\,|\,J\,M_R\rangle,$$
$J=j\pm\tfrac12$, $M_L=m_L+\alpha$, $M_R=m_R+\beta$, $\alpha,\beta\in\{+\tfrac12,-\tfrac12\}$
(matrix index 0 ↔ $+\tfrac12$, 1 ↔ $-\tfrac12$). Components with $J>j_{\max}$ are dropped
(**truncation = projection**: because operators on different links commute, the product of
link-truncated operators equals $P\hat\Box P$ with $P$ the global projector — planner derivation,
verified in `scratch/planner/proto_m1.py`). Clebsch–Gordan coefficients: Condon–Shortley phase
(`sympy.physics.wigner.clebsch_gordan`, converted to float64 and cached).

$\hat U^\dagger$ as an operator: $(\hat U^\dagger)_{\alpha\beta}=(\hat U_{\beta\alpha})^\dagger$ (matrix transpose
and operator adjoint).

### 1.4 Gauge generators and Gauss's law
Spin matrices $J^a$ ($a=x,y,z$) in the standard $|j,m\rangle$ basis with $J^\pm$ real.
- Left generator $\hat L^a_\ell$ acts on $m_L$ as $J^a$; right generator $\hat R^a_\ell$ acts on $m_R$
  as $-(J^a)^*$ (conjugate representation: $D^j_{mn}(Ug^\dagger)=\sum_{n'}D^j_{mn'}(U)D^j_{nn'}(g)^*$).
- Gauss's law at vertex $v$:
  $$\hat G^a_v=\sum_{\ell:\ \mathrm{start}(\ell)=v}\hat L^a_\ell+\sum_{\ell:\ \mathrm{end}(\ell)=v}\hat R^a_\ell+\hat Q^a_v,
  \qquad \hat Q^a_v=\psi^\dagger_v\tfrac{\sigma^a}{2}\psi_v\ (+\,S^a_v\ \text{for a static source}).$$
  Physical subspace $\mathcal H_{\rm phys}=\{|\psi\rangle:\hat G^a_v|\psi\rangle=0\ \forall v,a\}$ =
  null space of $\sum_{v,a}(\hat G^a_v)^2$.
- Consistency check (acceptance test): $[\hat H_{\rm term},\hat G^a_v]=0$ for every term and vertex,
  to machine precision. In the planner prototype this holds exactly (0.0) for $\hat H_E$, $\hat H_B$.
- For SU(2), $\bar{\mathbf 2}\cong\mathbf 2$: a static "antiquark" is also a spin-$\tfrac12$ leg.

### 1.5 Physical-subspace construction without the full space (vertex intertwiners)
Fix the link representations $\{j_\ell\}$ and the matter occupations. The block
$\bigotimes_\ell(V_{j_\ell}\otimes V^*_{j_\ell})\otimes\bigotimes_v\mathcal F_v$ regroups as $\bigotimes_v\mathcal H_v$
(every link end belongs to exactly one vertex), and $\hat G_v$ acts only on $\mathcal H_v$, so
$$\mathcal H_{\rm phys}=\bigoplus_{\{j_\ell\},\{n_v\}}\ \bigotimes_v \mathrm{Inv}(\mathcal H_v),$$
where $\mathrm{Inv}(\mathcal H_v)$ (an "intertwiner" = SU(2)-singlet subspace at the vertex) is the null
space of $\sum_a(\hat G^a_v)^2$ on $\mathcal H_v$ (dimension ≤ 81·4 at $j_{\max}=1$ with matter).
Matrix elements of Hamiltonian terms between such product states are tensor contractions of small
vertex tensors with the link matrices — this is "reference C" of plan 001 and scales to C2/C4.
Dimension counting: multiplicity of total spin 0 in $\bigotimes_{\rm legs}V_{j}$.

### 1.6 Spin-network (gauge-invariant) basis and the 6j plaquette operator — encodings #2, #4
Source: Zache–González-Cuadra–Zoller arXiv:2304.02527 Eqs. (2), (9) (Supplement);
Raychowdhury–Stryker arXiv:1912.06133 Sec. V (LSH in 2D, point splitting, Fig. 4–5);
Klco–Stryker–Savage 1908.06935 Eq. (6).
- Point splitting: site $\mathbf n$ → $v_{\rm out}$ (legs: $x$-link out, $y$-link out, virtual) and
  $v_{\rm in}$ (legs: $x$-link in, $y$-link in, virtual), joined by a virtual link $j_{v}\le 2j_{\max}$.
  Basis states: labels on 8 real + 4 virtual edges obeying the triangle rule
  $|j_1-j_2|\le j_3\le j_1+j_2$, $j_1+j_2+j_3\in\mathbb Z$ at all 8 trivalent vertices. Electric
  term diagonal, $\sum_{\ell\ \rm real}j_\ell(j_\ell+1)$ (virtual links carry no electric energy).
- Plaquette $\mathbf n$ is a hexagon through
  $(v_{\rm out}(\mathbf n), v_{\rm in}(\mathbf n+\hat x), v_{\rm out}(\mathbf n+\hat x), v_{\rm in}(\mathbf n+\hat x+\hat y), v_{\rm out}(\mathbf n+\hat y), v_{\rm in}(\mathbf n+\hat y))$
  with inner edges $(x(\mathbf n),\ \mathrm{virt}(\mathbf n+\hat x),\ y(\mathbf n+\hat x),\ x(\mathbf n+\hat y),\ \mathrm{virt}(\mathbf n+\hat y),\ y(\mathbf n))$.
  $$\langle j'|\hat\Box_{\mathbf n}|j\rangle=\prod_{i=1}^{6}F^{\,j_{o_i}\;j_{e_{i-1}}\;j_{e_i}}_{\;\frac12\;\;j'_{e_i}\;\;j'_{e_{i-1}}},\qquad
  F^{j_1 j_2 j_{12}}_{j_3 j_4 j_{23}}=(-1)^{j_1+j_2+j_3+j_4}\sqrt{(2j_{12}+1)(2j_{23}+1)}
  \begin{Bmatrix} j_1&j_2&j_{12}\\ j_3&j_4&j_{23}\end{Bmatrix},$$
  $j'_e=j_e\pm\tfrac12$ on the six inner edges; $o_i$ = third edge at vertex $i$; components with a
  real link above $j_{\max}$ dropped. 6j symbols from `sympy.physics.wigner.wigner_6j` (float64, cached).
- Validation: identical spectrum to §1.3–1.5 on the 2×2 torus at $j_{\max}=\tfrac12$
  ($\max|\Delta E|=1.6\times10^{-14}$, 63 states; planner prototype). Basis-state phases are
  convention-dependent; only gauge-invariant observables and spectra are compared across bases.
- q-deformation (#6, Hayata–Hidaka arXiv:2305.05950; Zache et al. Eqs. (10)–(15)):
  $q=e^{2\pi i/(k+2)}$, $[n]=\sin\frac{\pi n}{k+2}/\sin\frac{\pi}{k+2}$, $d_j=[2j+1]$, admissible
  triples additionally need $j_1+j_2+j_3\le k$, 6j → q-6j, Casimir $j(j+1)\to$ q-Casimir
  (to be specified in the M7 planner run; not needed for M1–M3 tests).

## 2. Time evolution and product formulas
- Target operation of a circuit (plan 001 §4): the **second-order (symmetric) Trotter step** with a
  fixed term order
  $$U_2(\delta t)=e^{-i\frac{\delta t}{2}H_E}\Big[\prod_{p=1}^{4}e^{-i\frac{\delta t}{2}h_p}\Big]\Big[\prod_{p=4}^{1}e^{-i\frac{\delta t}{2}h_p}\Big]e^{-i\frac{\delta t}{2}H_E},
  \quad h_p=-\tfrac{1}{2g^2}(\hat\Box_p+\hat\Box_p^\dagger),$$
  (fermion cases insert the mass layer and the hopping layers, order fixed in plan 001 §4).
  Error: $\|U_2(\delta t)-e^{-iH\delta t}\|=O(\delta t^3)$; after $N=T/\delta t$ steps
  $\|U_2^N-e^{-iHT}\|\le N\|U_2-e^{-iH\delta t}\|$ (telescoping, unitarity).
  Source: Suzuki, J. Math. Phys. 32, 400 (1991); Childs et al. arXiv:1912.08854 (Trotter error theory).
- "Exact-step" circuits implement $e^{-iH\delta t}$ directly (unitary synthesis in the compact
  gauge-invariant register); their per-step error is the synthesis tolerance only.
- Accuracy currency: $N_\star(\varepsilon_\star)=\min\{N:\ N\,\|U_{\rm step}(T/N)-e^{-iHT/N}\|_{\rm phys}\le\varepsilon_\star\}$,
  CNOT$_\star=N_\star\times$ CNOT per step. Norms are spectral norms on $\mathcal H_{\rm phys}$,
  computed from the restricted matrices (dimension ≤ a few thousand).

## 3. Circuit cost pipeline (fixed for reproducibility)
- Qiskit 2.5.2, qiskit-aer 0.17.2 (CPU). `transpile(circuit, basis_gates=["cx","u"],
  optimization_level=3, seed_transpiler=20261102)`; no coupling map (all-to-all).
  Ranking: `count_ops()["cx"]`, then `depth()` of the transpiled circuit, then number of qubits
  (including ancillas). Reported extra columns: `u` count, Toffoli count before transpilation when
  the circuit is built from Toffolis, "two-qudit" count (entangling gates between distinct link
  registers), and the paper's $TQ$-cost (Toffoli × qubits) for group-register circuits.
- Reproducibility test: two transpile runs with the same seed give identical (`cx`, depth).

## 4. Exactness evaluator (plan 001, module `su2qc.evaluator`)
- Encoding API maps every physical basis state $|b\rangle\in\mathcal H_{\rm phys}$ to a register state
  (computational-basis state, or a superposition for compact/gauge-invariant registers).
- Restricted unitary $U^{\rm circ}_{\rm phys}=\Phi^\dagger U_{\rm circ}\Phi$ with $\Phi$ the isometry from
  $\mathcal H_{\rm phys}$ to the register (ancillas in $|0\rangle$). Computed column by column:
  statevector simulation of the circuit on $\Phi|b\rangle$ (Aer `statevector`, double precision,
  1 thread per worker, joblib process pool) for ≤ 26 qubits; a sparse support-tracking simulator
  (exact complex128, state stored as (index array, amplitude array), gates applied by bit
  manipulation; abort if support exceeds a cap) above 26 qubits.
- Metrics: $\varepsilon_{\rm phys}=\|U^{\rm circ}_{\rm phys}-e^{i\phi}U_{\rm target}\|_2$ minimised over
  the global phase $\phi$ (closed form: $\phi=\arg\mathrm{Tr}(U_{\rm target}^\dagger U^{\rm circ}_{\rm phys})$),
  leakage $\|(1-\Phi\Phi^\dagger)U_{\rm circ}\Phi\|_2$, ancilla-return error
  $\|(1-|0\rangle\langle0|_{\rm anc})U_{\rm circ}\Phi\|_2$.
- Sampling variant (large physical dimension, e.g. group registers): $k$ seeded random states in
  $\mathcal H_{\rm phys}$; bound from Gu et al. 2610.22367 Methods Eqs. (17)–(20):
  all $k$ tests passing ⇒ failure probability $\varepsilon\le\ln(1/\delta)/k$ at confidence $1-\delta$.
- Cross-encoding agreement: for encodings of the same truncated model, the restricted step
  unitaries are compared after mapping both to the common physical basis of §1.5 (they must agree
  to the evaluator tolerance since the Trotter step is basis-independent).

## 5. Fermion-to-qubit maps (M4; #14, #15) — specified now, tested in a later planner run
- Mode ordering: site-major, colour-minor: mode $2s+\alpha$, $\alpha\in\{0\ (\uparrow),1\ (\downarrow)\}$.
- Jordan–Wigner: $\psi_k=\big(\prod_{l<k}Z_l\big)\frac{X_k+iY_k}{2}$ (Jordan–Wigner, Z. Phys. 47, 631 (1928)).
- Bravyi–Kitaev: Seeley–Richard–Love arXiv:1208.5986 (8 modes). Both must reproduce the fermionic
  anticommutators $\{\psi_k,\psi^\dagger_l\}=\delta_{kl}$ (unit test) and the same physical spectrum.

## 6. Group-register (discrete subgroup) formulation (M7; #7) — specified at the M7 planner run
Lamm–Lawrence–Yamauchi arXiv:1903.08807 (Secs. II–III: G-register, inversion, multiplication,
trace, Fourier gates; $H_K=-\log T_K$, Eq. (19)); Gustafson et al. arXiv:2208.12309 (binary
tetrahedral group BT, 24 elements, 5 qubits/link, gate costs); Gu et al. 2610.22367 SI V (magnetic
layer compilation template). Details and tests to be written when M7 starts.
