# Report 9 — Fuzzy encoding (4 qubits per link): general one-Trotter-step circuit

Date: 2026-11-06 · Branch `m9-fuzzy` · Branch head when drafted: `5669592` · Results committed in `578d28c` (the JSON provenance records `git_commit` = `8e71c38`, `git_dirty` = true, because `scripts/m9_results.py` and `results/fuzzy/` were still untracked when the run started) · Tag: `milestone-9` (see §5 for the gate state) · Plan: `prompts/300` + test amendment `prompts/301` · Conventions: `docs/METHODS-fuzzy.md` (F1 to F8).

Every number below is read from `results/fuzzy/{UE,UK,UB,step,outer_row,shared_observables,splitting}.json`. They were produced by `PYTHONPATH=src python scripts/m9_results.py` (seeds 20261104 for the transpiler and step samples, 12345 for the Clifford+T pass manager; Python 3.12.14, numpy 2.5.4, scipy 1.18.1, qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0; timestamp 2026-11-06T19:12:30Z). Other sources are cited by file. Verification: tester part 1 `reports/tests/300-m9-gate-full-part1.md` (PASS); tester part 2 `reports/tests/301-m9-gate-full-part2.md` (verdict: GATE-PART2-VERDICT); audit `reports/audits/300-m9-fuzzy-audit.md` (PASS WITH NOTES); short benchmark `reports/benchmarks/300-m9-fuzzy-benchmark.md`.

Terms used (defined once; project labels are marked as such).
- **Fuzzy link**: a link whose state is a $4\times4$ complex matrix $\Psi$ instead of a function on SU(2). It has 16 basis states, so 4 qubits. With 12 links this gives 48 qubits and no unused codes (arXiv:2308.05253, Sec. III).
- **Trotter step**: one approximation of the time evolution $e^{-iHt}$ over a short time $dt$ by a product of simpler exponentials.
- **CNOT (CX)**: the two-qubit gate that flips the target qubit if the control qubit is 1. **T gate**: the expensive single-qubit gate of fault-tolerant machines. **Rotation**: a single-qubit gate $R_z(\theta)$ (or a controlled one) with a continuous angle. **Clifford+T**: a gate set made only of H, S, CNOT and T; every rotation must be approximated by a string of these, to an accuracy $\varepsilon$ (here with the program pygridsynth).
- **Work qubit (ancilla)**: extra qubit that starts in $|0\rangle$ and must end in $|0\rangle$.
- **Gauss law, physical state**: the lattice constraint that the total gauge charge at every lattice corner is zero. States obeying it are physical.
- **Plaquette**: the smallest closed loop of four links; it produces the magnetic term of the Hamiltonian.
- **Op-norm error**: largest possible deviation between the circuit's output and the exact output over unit-length inputs, after removing one overall phase. **Leaked amplitude**: weight the circuit puts outside the space it is supposed to act on.
- **Strong-coupling vacuum** $|\Omega\rangle$: the state with every link in $\tfrac12\mathbb 1$. **Closed sector** (project label, F7): the smallest subspace containing $|\Omega\rangle$ that is mapped into itself by the three building blocks of $H$. **Loschmidt echo**: $|\langle\Omega|e^{-iHt}|\Omega\rangle|^2$, the probability of still being in $|\Omega\rangle$ at time $t$. **Outer row** (project label): the electric and $\mathcal K_2$ blocks on the 8 outer links, reported separately.

## 1. What was asked
Build in Qiskit the circuits for one Trotter step of the fuzzy-gauge-theory Hamiltonian of Bedaque's note (`refs/fuzzy/fuzzy-hamiltonian-digonto.pdf`; the paper's Eqs. 34 to 37, **including** the second kinetic term $\kappa_2\mathcal K_2$) for the SU(2) plaquette with 8 outer links. The three factors are the electric layer $U_E(\alpha)$, the second kinetic layer $U_K(\kappa_2)$, and the magnetic layer $U_B(\beta)$. Verify them, count CNOT and T gates, give a first Lean proof of the link algebra and of the physical-state counts, and compare observables with the Kogut–Susskind (KS) theory at $j_{\max}=\tfrac12$ (`prompts/300`, `notes/STATUS.md`).

Decisions in force (all from `notes/STATUS.md`, 2026-11-06):
- $\mathcal K_2$ is included (Digonto). It has its own circuit $U_K$ and removes the 3-qubit-per-link reduction, so the encoding is 4 qubits per link, 48 qubits.
- Electric normalisation $\tfrac{g^2}{4}\mathcal K_1$ (Paulo's Eq. 16; $\kappa_1=\alpha/2$) (Digonto).
- Coordinator defaults, **not yet confirmed by Digonto**: $r=\kappa_2/\kappa_1$ is not given in the note, so nominal $r=1$ (and $r=0$ always tested too); plaquette term $H_B^{\rm fz}=-2\square$ with the KS sign; Gauss orientation of the paper (the generator $\mathcal T_L$ on outgoing links; Eq. 3 of the note is treated as a typo).

## 2. What was done
- **Exact reference** (`src/su2plaq/fuzzy/{link,plaquette,targets,gauss}.py`, `docs/METHODS-fuzzy.md` F2 to F5).
  - Link operators from the paper's matrices. All algebra identities hold to residual 0 in floating point (research 300 §2).
  - With $g^2$ the gauge coupling,
    $$H^{\rm fz}=\frac{g^2}{4}\sum_{\ell=1}^{12}\big(\mathcal K_1(\ell)+r\,\mathcal K_2(\ell)\big)-\frac{2}{g^2}\,\square ,$$
    and the step angles are $\alpha=g^2dt/2$, $\beta=dt/g^2$, $\kappa_2=r\alpha/2$. Here $\square$ is the plaquette operator, a Hermitian $256\times256$ matrix on the 8 "row" qubits of the 4 inner links (spectrum $\{0^{174},\pm1^{16},\pm2^{24},\pm4\}$, research 300 §3).
  - Because $[\mathcal K_1,\mathcal K_2]=0$, the electric and second kinetic layers combine exactly.
- **Circuits** (`src/su2plaq/circuits/fuzzy.py`).
  - $U_E$ and $U_K$: one 4-qubit block per link. A fixed Clifford basis change diagonalises the Pauli strings, then one $R_z$ per string inside a CNOT ladder. Angles are linear in $\alpha$ or $\kappa_2$.
  - $U_B=e^{+2i\beta\square}$ is the exact exponential of the plaquette operator, built by a parity/singular-value route (F5): three CNOTs expose the three conserved parities, eight sectors are selected by a flag work qubit, and the fixed 4-qubit unitaries of each sector are Clifford (measured, so no generic synthesis was needed). The only angle-dependent gates are 8 controlled $R_x(-4\beta\sigma)$, each worth 2 rotations. It touches no column qubit and no outer qubit, and uses 7 work qubits, all clean at the end.
  - Trotter steps: order 1 is $U_BU_KU_E$ (kinetic layers first in the circuit); order 2 is $U_E(\alpha/2)U_K(\kappa_2/2)\,U_B\,U_K(\kappa_2/2)U_E(\alpha/2)$. The outer-link blocks commute with everything, so they are applied once at full angle and reported as the separate outer row.
- **Checker** (`src/su2plaq/fuzzy/verify.py`, F6).
  - The 16-qubit-wide inner circuits are checked as complete unitaries (link: $16\times16$; plaquette: the full $256\times256$ block with work qubits at $|0\rangle$), through the laptop evaluator on an adapter encoding in which every computational state is physical.
  - The assembled step is checked by its layers: each layer block is certified, and their composition is compared with the exact step on seeded random product states plus physical states (40 inputs, seed 20261104). The Gauss residual of the outputs is computed on seeded physical states.
  - A circuit passes if the op-norm error plus leaked amplitude is at most $10^{-10}$ for exact angles, or at most $N_{\rm rot}\varepsilon+10^{-9}$ after Clifford+T synthesis, with $N_{\rm rot}$ the number of rotations.
  - The physical set (101 197 218 states with fixed far ends) is never enumerated: exactness as a full unitary on the data space implies exactness on every physical state.
- **T count**: $T=T_{\rm fixed}+\sum_{\rm rot}T_r(\varepsilon)$, each rotation synthesised by pygridsynth (Ross–Selinger) and every synthesised circuit re-verified.
- **Lean** (`lean/Su2Plaq/Fuzzy/{Link,Counts}.lean`): see §3.7.
- **Observables** (`src/su2plaq/fuzzy/observables.py`, F7): the shared table against KS (§3.5).

## 3. Results at $(\alpha,\beta)=(0.37,0.61)$, $r=1$ ($\kappa_2=0.185$)

### 3.1 Exactness, with the scope of each check
Keys: `results/fuzzy/<circuit>.json`, `verification` and `extra.verification_scope`. All errors are op-norm after one global phase; all circuits are checked at exact angles with tolerance $10^{-10}$.

| circuit | verification scope (label) | op-norm error | leaked amplitude | Gauss residual of outputs | certified? |
|---|---|---|---|---|---|
| $U_E$ | `full_unitary_link`: one complete $16\times16$ link unitary, plus the check that the layer is four such blocks | $4.3\times10^{-16}$ | 0 | not applicable (target commutes with the generators) | yes |
| $U_K$ | `full_unitary_link` | $1.5\times10^{-15}$ | 0 | not applicable | yes |
| $U_B$ | `full_unitary_row_block`: complete $256\times256$ row block, 256 inputs; `touches_column` = false | $3.8\times10^{-14}$ | 0 (weight outside row space $1.1\times10^{-16}$) | not applicable | yes |
| step, order 1 | `blocks_certified_composition_sampled`: layer blocks certified, composition sampled on 40 inputs | $1.0\times10^{-14}$ | 0 | $5.2\times10^{-15}$ | **no** (sampled) |
| step, order 2 | same | $1.7\times10^{-14}$ | 0 | $5.2\times10^{-15}$ | **no** (sampled) |

- Alternate angles $(0.91,0.23)$ and $(1.70,1.00)$ (and $r=0$ for $U_K$ and the step) give errors of at most $3.9\times10^{-14}$ over all alternates in the four files (`extra.alternates`).
- Independent second-engine checks by the tester (Aer statevector, `reports/tests/300`): $\lVert M-U_B\rVert_2=2.6\times10^{-14}$ over all 256 columns; step, both orders and $r\in\{0,1\}$, at most $7.5\times10^{-15}$ on 4 random states. The auditor simulated the order-2 step as a whole circuit with the layer metadata removed: error $1.2\times10^{-14}$ (audit 300, A9).
- **Honest scope.** The step is not a fully certified unitary equality. Its layers are certified, but the composition is sampled; the whole $2^{16}$-dimensional inner space cannot be handled densely. This is the label `blocks_certified_composition_sampled` and `certified` = false in `step.json`.
- Audit note NB-1 (the step checker used to trust the layer ranges without checking that they cover the circuit; a tampered circuit passed) and NB-2 (wrong, unused outer entries in an orientation table) were fixed in commit `530dc1a`, with unit tests (`tests/unit/test_fuzzy_verify.py`, `tests/unit/test_fuzzy_gauss.py`).

### 3.2 Gates
Keys: `metrics.logical` and `metrics.macro_counts` of each file. "Qubits" counts the inner data qubits (16) plus work qubits; the 32 outer qubits appear only in the outer row.

| circuit | CNOT | rotations | fixed T | depth | qubits |
|---|---|---|---|---|---|
| $U_E$ (4 inner links) | 72 | 24 | 0 | 23 | 16 |
| $U_K$ (4 inner links) | 72 | 16 | 0 | 22 | 16 |
| $U_B$ | 1718 | 16 | 1826 | 2646 | 23 (16 + 7 work) |
| step, order 1 | 1862 | 56 | 1826 | 2690 | 23 |
| step, order 2 | 2006 | 96 | 1826 | 2734 | 23 |
| outer row (8 links; `outer_row.json`) | 288 | 80 | 0 | not reported | +32 outer data qubits ($16+32+7=55$ in total: registers `d` = 16 inner data, `o` = 32 outer data, `w` = 7 work qubits of `build_step(with_outer=True)`; the M10 composer reports 55 qubits / 7 ancillas) |

**Outer links are acted on (unlike the KS encodings).** In the fuzzy model $\mathcal K_1$ and $\mathcal K_2$ are not diagonal in the computational basis, so every outer link gets a real 4-qubit block $U_K(\kappa_2)U_E(\alpha)$ (once, full angles), not a phase. $U_B$ never reads or changes an outer qubit (nor a column qubit). For like-for-like comparisons with other encodings use the inner-only rows above and the outer row separately.

- Per outer link (`outer_row.json`, `per_link`): $U_E$ has 18 CX, 6 rotations, depth 23; $U_K$ has 18 CX, 4 rotations, depth 22. Eight links give $8\times(18+18)=288$ CX and $8\times(6+4)=80$ rotations, and `build_step(with_outer=True)` adds exactly those increments (`consistency_with_build_step_with_outer`: `matches_totals` = true, largest commutator with the Gauss generators $1.0\times10^{-16}$).
- Consistency of the sums: $1862=72+72+1718$ CX; $56=24+16+16$ rotations; order 2 has $2\cdot72+2\cdot72+1718=2006$ CX and $2\cdot24+2\cdot16+16=96$ rotations.
- $U_B$ in macro gates: 246 Toffoli (`ccx`), 158 CX, 52 controlled-H, 16 CZ, 8 controlled-$R_x$, 8 phase gates (Clifford angles, no T), 176 X. The tester recounted by hand: CX $=158+6\cdot246+52+16+2\cdot8=1718$; fixed T $=7\cdot246+2\cdot52=1826$. This is a design count after Qiskit's level-0 lowering (Toffoli = 7 T, controlled-H = 2 T-type gates); an optimising compiler could lower it. Reducing it is the subject of M10.

### 3.3 T count after Clifford+T synthesis (pygridsynth; every synthesised circuit re-verified)
Keys: `metrics.t_table[*].t_total` (= `t_fixed` + `t_rot_pygridsynth`); order 2 is `extra.order2.metrics.t_table`; outer row is `outer_row.json` `totals.t_table`.

| circuit | $\varepsilon=10^{-4}$ | $10^{-6}$ | $10^{-8}$ | $10^{-10}$ |
|---|---|---|---|---|
| $U_E$ | 912 | 1584 | 2016 | 2448 |
| $U_K$ | 672 | 992 | 1344 | 1664 |
| $U_B$ (incl. 1826 fixed) | 2498 | 2822 | 3150 | 3494 |
| step, order 1 | 4082 | **5398** | 6510 | 7606 |
| step, order 2 | 5922 | **7782** | 9486 | 11846 |
| + outer row (8 + 8 blocks, separate) | +3168 | +5152 | +6720 | +8224 |

- Check of the sum for order 1 at $\varepsilon=10^{-6}$: $1826+(1584+992+996)=5398$, where 996 is the rotation part of $U_B$.
- Each further factor 100 in accuracy costs about 18 to 22 T per rotation at the fine end (for example $U_E$: $1584/24=66$, $2016/24=84$, $2448/24=102$).
- Qiskit's own Clifford+T pass manager (seed 12345) at $\varepsilon=10^{-6}$ gives (`t_qiskit`): $U_E$ 1560, $U_K$ 992, $U_B$ 2626, step order 1 5178, step order 2 7586, outer row 5104. For order 1 it is within about 4 % of the pygridsynth sum; the pygridsynth sums are the numbers reported above.
- Measured synthesis error against its budget $N_{\rm rot}\varepsilon$ (`synth.verdict.op_norm_error` over `synth.error_bound_sum`): between 0.017 and 0.36 for all circuits and all $\varepsilon$. Example: step order 1 at $10^{-6}$ has error $7.6\times10^{-6}$ against a budget of $5.6\times10^{-5}$, with output Gauss residual $2.7\times10^{-6}$ (also inside the budget). Every table row has `ok` = true.
- Order 1 and order 2 at the same $\varepsilon$ are not at the same total accuracy (budgets $56\varepsilon$ and $96\varepsilon$).

### 3.4 Comparison with the KS 12-qubit step (Report 1), same nominal angles, $\varepsilon=10^{-6}$
Numbers for KS are from `docs/report-1-twelve-qubit-general-circuit.md` §3.2 and §3.3.

| step, order 1 | CNOT | rotations | fixed T | T total |
|---|---|---|---|---|
| KS, 12-qubit encoding ($j_{\max}=\tfrac12$) | 294 | 10 | 312 | 952 |
| fuzzy, 4 qubits per link, with $\mathcal K_2$ | 1862 | 56 | 1826 | 5398 |

The fuzzy step costs about $6.3\times$ the CNOTs and $5.7\times$ the T gates. This is not an efficiency comparison of two methods: the two circuits implement different Hamiltonians (the fuzzy one has a 16-state link, the extra $\mathcal K_2$ layer, and an exact 8-qubit plaquette exponential rather than a 3-qubit-per-link block). Outer row at $\varepsilon=10^{-6}$: fuzzy 5152 T (80 rotations) against KS 512 T (8 rotations).

### 3.5 Shared observables against KS (`results/fuzzy/shared_observables.json`)
Definitions in F7. Coupling from the angles: $g^2=\sqrt{2\alpha/\beta}=1.101414887$ (key `g2`), $dt=\beta g^2$. "Fuzzy $r=1$" and "fuzzy $r=0$" are the rows `fuzzy_r1` and `fuzzy_r0`; "KS" is the row `ks` (the $2\times2$ closed-sector block of Report 1 / METHODS §4).

Electric energy per link (`electric_per_link`), in units where $g^2=1.1014$:

| row | values | meaning |
|---|---|---|
| fuzzy ($r=0$ and $r=1$) | $0,\ 0.41303,\ 0.55071$ | $0,\ \tfrac38g^2,\ \tfrac12g^2$ |
| KS | $0,\ 0.41303$ | $0,\ \tfrac38g^2$ |

The flux-link value $\tfrac38g^2$ agrees with KS $j=\tfrac12$ to all digits stored. The third fuzzy value is a link with left and right spins different (representation $(1,0)$ or $(0,1)$); KS at $j_{\max}=\tfrac12$ has no state with that energy.

Closed sector (`closed_sector_dim`, `closed_sector_spectrum`; inner links only, see §5):

| row | dimension | lowest | highest |
|---|---|---|---|
| fuzzy $r=1$ | 12 | $-5.8393$ | $9.0509$ |
| fuzzy $r=0$ | 9 | $-5.6454$ | $8.9448$ |
| KS | 2 | $-1.16885$ | $2.82097$ |

Observation (not in the plan): the fuzzy $r=0$ spectrum contains both KS eigenvalues to $2\times10^{-15}$ (fuzzy $-1.1688509494558617$ and $2.8209732804959406$; KS $-1.1688509494558612$ and $2.8209732804959424$). This has not been investigated, so it must not be quoted as a theorem. The dynamics are not the same: the closed sector has dimension 9, not 2, and the echo differs (table below).

Plaquette $\langle\mathrm{Re\,Tr}\,U_P\rangle$ at time $t=\beta g^2$ (`plaquette_vs_beta`, 7 values of $\beta$, same grid in all rows):

| $\beta$ | fuzzy $r=1$ | fuzzy $r=0$ | KS |
|---|---|---|---|
| 0.10 | 0.1619 | 0.0351 | 0.0358 |
| 0.25 | 0.5444 | 0.1821 | 0.2055 |
| 0.40 | 0.4809 | 0.3352 | 0.4470 |
| 0.61 | 0.6569 | 0.4259 | 0.7145 |
| 0.80 | 1.1498 | 0.4491 | 0.7278 |
| 1.00 | 1.1469 | 0.4793 | 0.4947 |
| 1.50 | 1.4977 | 0.2477 | 0.0178 |

Loschmidt echo (`loschmidt`, 21 values on $t\in[0,4]$ in steps of 0.2; five shown):

| $t$ | fuzzy $r=1$ | fuzzy $r=0$ | KS |
|---|---|---|---|
| 0 | 1.0000 | 1.0000 | 1.0000 |
| 1 | 0.6117 | 0.2412 | 0.3118 |
| 2 | 0.5279 | 0.3931 | 0.5338 |
| 3 | 0.5829 | 0.2978 | 0.9284 |
| 4 | 0.4642 | 0.5149 | 0.1845 |

What this means:
- The plaquette values of the fuzzy rows can exceed 1 because $\square$ has eigenvalues up to 4, while the KS operator $\mathrm{Re\,Tr}\,W$ has eigenvalues $\pm1$. The two operators are defined by the same rule in F7, but they do not have the same scale, so only trends and the small-$\beta$ end are comparable.
- At the smallest $\beta=0.10$ the $r=0$ fuzzy value $0.0351$ is within 2 % of KS $0.0358$. They separate quickly as $\beta$ grows (at $\beta=0.61$: $0.4259$ against $0.7145$).
- $r=1$ (with $\mathcal K_2$) is far from KS everywhere: the vacuum is pulled to lower energy and the plaquette is larger.
- Shared exact identity (tested at $r=1$ and $r=0$): after one first-order step $U_BU_KU_E$ from $|\Omega\rangle$, $\langle\mathrm{Re\,Tr}\,U_P\rangle=0$ to $10^{-10}$ in both theories, because the kinetic layers only add phases to $|\Omega\rangle$ and $U_B$ commutes with the plaquette. For the order-2 step it is nonzero and scales as $O(\alpha\beta)$ (ratio between $(0.05,0.05)$ and $(0.025,0.025)$ in $[3,5]$, `prompts/301` §1.1).

### 3.6 Splitting-error rows (`results/fuzzy/splitting.json`)
Both numbers are operator 2-norms, so 2 is the largest possible value for two unitaries.

| row | value | what it says |
|---|---|---|
| commuting-cluster product against $e^{2i\beta\square}$, $\beta=0.61$ | 1.989 | the product of 4 commuting clusters of the plaquette (Tex Result 3) is not a good substitute for the exact plaquette exponential |
| same, $\beta=0.23$ | 0.851 | not small even at the smaller angle |
| same, $\beta=1.00$ | 1.974 | |
| order 1 against order 2, nominal angles, restricted to the 50 gauge-singlet states of the isolated plaquette (`trotter_order1_vs_order2`) | 1.477 | the two step formulas differ strongly at these large angles. This is the distance between the two formulas, not the error against exact evolution. |

Checks on the same row: the 50-state basis has Gauss residual $1.7\times10^{-14}$, orthonormality error $2.0\times10^{-15}$, and the outputs of both orders keep Gauss residual $1.7\times10^{-14}$.

### 3.7 Lean (`lean/Su2Plaq/Fuzzy/Link.lean`, `Counts.lean`)
- `Link.lean` (18 theorems) proves, by kernel evaluation (`decide +kernel`) over exact Gaussian-integer matrices: the Clifford and $\Gamma_5$ relations (`clifford`, `gamma5_rel`), the su(2) relations of the generators (`su2_4x4`, `su2_link`), the transformation law $[\mathcal T,\mathcal U]$ (`transformation_law`), pseudo-reality (`pseudo_reality`), the Pauli forms of $\mathcal U$, $\mathcal T$, $\mathcal K_1$, $\mathcal K_2$ (`pauli_U`, `pauli_T`, `pauli_K`), Hermiticity (`K_hermitian`), $[\mathcal K_1,\mathcal K_2]=0$ (`K1_K2_commute`), the spectra (`K1_spectrum`, `K2_spectrum`, `K2_extremal`), and the flavour and centre relations (`flavour`, `centre_rel`), plus `MEq_iff` and `MEq_discriminates` (the equality test is not vacuous). The two spectrum theorems prove a minimal polynomial plus traces; the multiplicities then follow from Hermiticity and a short argument written outside Lean (as the file's own docstring says). Axioms (`#print axioms`, reported by the Lean builder): `[propext]` only for the `Link` theorems, `[propext, Quot.sound]` for the helper `MEq_iff`.
- `Counts.lean` (5 theorems): `count_isolated_plaquette` = 50, `count_outer_vacuum` = 12 800, `count_fixed_far_end` = 101 197 218, `count_far_end_weighted` = 6 767 266 914, plus `nsinglet_checks`; no axioms. **Scope (audit NB-4):** these are the corner-rule counts verified by kernel evaluation. That the corner rule gives the true dimension of the Gauss-law kernel is a Clebsch–Gordan argument (F4) that is not proved in Lean. Python agrees by two independent routes (corner counting and a Haar-character integral), and the auditor confirmed 50 by a direct kernel computation (audit A4).
- No `sorry`, no `native_decide`, no declared axioms in either file. `Link.lean` takes about 6 min to build.
- Per-circuit Lean certificates (plan step 9L3, optional) were not built. The circuits are verified numerically (§3.1), not by a Lean certificate.

## 4. Physics findings along the way
- **The plaquette exponential is affordable only in the parity form.** The 8-qubit plaquette operator conserves three parities of the block bits, splits into 8 sectors, and in each sector the fixed unitaries are Clifford. The whole $U_B$ then has only 16 angle-dependent rotations (research 300 §3, F5). A generic synthesis of the same $256\times256$ matrix was estimated at about 31 000 CNOT and 37 000 rotations (research 300 §6) and was rejected.
- **Tex Result 3 (cluster factorisation) is contradicted.** The product of 4 commuting plaquette clusters has operator-norm error 1.989 at $\beta=0.61$ (§3.6; 1.9 also on the 50 gauge singlets in research 300 §3). The exact exponential is the target; the cluster product is only a reported row.
- **Order-2 plaquette after one step is not zero.** Plan 300 and the locked test originally asserted zero for both orders. Only order 1 gives zero; order 2 gives $O(\alpha\beta)$ (`prompts/301`, approved by Digonto).
- **Physical-state counts** (two routes; Lean kernel for the corner rule): isolated plaquette 50; outer-vacuum sector 12 800; 12 links with fixed far ends 101 197 218; far-end weighted 6 767 266 914 (F4, research 300 §4).
- **$\mathcal K_2$ breaks the flavour symmetry.** $F=Z_3$ commutes with $\mathcal K_1$ but anticommutes with $\mathcal K_2$, so the physical set is the full Gauss kernel (both flavour sectors) and 4 qubits per link are required.
- **The orientation of Gauss's law is not a free convention.** The plaquette commutes with all four corner generators with the paper's orientation (exactly 0 on the full 65 536-dimensional inner space) and fails (commutator 1.0) if the arrows of Eq. 3 of the note are used literally (audit A1, A2).

## 5. Problems and assumptions
- **Assumptions awaiting Digonto** (coordinator defaults, `notes/STATUS.md`): $r=\kappa_2/\kappa_1=1$ nominal (the note gives no value); plaquette sign and factor $H_B^{\rm fz}=-2\square$; Gauss orientation of the paper. If Digonto overrides, only the angle map `kappa2_of`, the sign of $U_B$ and the nominal JSON files change. The map $g^2=\sqrt{2\alpha/\beta}$ is also an assumption. The audit notes that the centre $Z_1Z_3$ on one inner link maps $\square\to-\square$ and keeps Gauss's law, so the sign changes only the sign of $\langle\square\rangle$, not the spectra.
- **The closed-sector Hamiltonian covers the 4 inner links only (audit NB-3).** `closed_sector_spectrum` is the spectrum of $H$ restricted to the inner links. The 8 outer links add the constant $8\cdot\tfrac{g^2}{4}\,r\,(-4)=-8rg^2$ on $|\Omega\rangle$. So every eigenvalue in the fuzzy $r=1$ row sits $+8rg^2=+8.811$ above the 12-link $H$ of F3 (for example the lowest, $-5.839$, corresponds to about $-14.65$ in the 12-link $H$). For $r=0$ the shift is 0. The Loschmidt echo and the plaquette are unaffected. The JSON rows do not carry this label; this sentence is the label.
- **Step verification is sampled, not complete** (§3.1). The tester part 1 whole-circuit statevector check and the auditor's A9 check support the delivered circuit independently of the layer metadata.
- **Cost of the tests**: the locked C1 test takes about 18 minutes; each S1 test needs 68 to 135 GB and must run with `-n 1` (peak 134.8 GB measured in part 1, 284 s for all five S1 tests). T1[step] takes about 27 min because the laptop's `cliffordt.synthesize` drops the layer metadata (suggested laptop diff in `notes/merge-notes-fuzzy.md`).
- **Provenance flag.** The JSON files carry `git_commit` `8e71c38` with `git_dirty` = true. The run itself is deterministic (`scripts/m9_results.py`, fixed seeds), but a re-run on a clean tree has not been done.
- **Not done in M9**: per-circuit Lean certificates (9L3), a fully certified (not sampled) step equality, and any reduction of the $U_B$ cost (1718 CX, 1826 fixed T). The compression loop of M10 works on the $U_B$ and one-link units (`prompts/302`, Report 10).
