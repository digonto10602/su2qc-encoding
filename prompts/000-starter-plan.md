# 000 — Starter plan: compressed time-evolution circuits for SU(2) on a 2×2 lattice

- Date: 2026-11-02
- Source: chat request from Digonto (verbatim intent below) + decisions taken in chat
- Reference paper: `refs/2610.22367v1-gu-kemeny-yelin-lukin.pdf` (text: `refs/2610.22367v1.txt`),
  A. Gu, A. H. Kemeny, S. F. Yelin, M. D. Lukin, "Discovering state-of-the-art quantum circuits with
  large language models", arXiv:2610.22367. Most relevant: main text "Design principles", Methods
  ("Circuit model and validity", "Validation and statistical guarantees"), and SI V
  ("Nonabelian lattice-gauge simulation", text lines ~2518–2735).

## 1. The request

Take SU(2) lattice gauge theory in 2+1 dimensions (Hamiltonian formulation) on a 2×2 lattice.
Links carry SU(2) gauge fields; vertices may carry fermions and/or charges. Build **time-evolution
circuits** $U(t) \approx e^{-iHt}$ for four physics cases:

| Case | Content |
|---|---|
| C1 | pure gauge |
| C2 | gauge + dynamical fermions |
| C3 | gauge + static color charges |
| C4 | gauge + dynamical fermions + static color charges |

…using every encoding in the list in §3, and for each case find **the most compressed circuit that
produces the same result**. Reason and work through the physics loop (coordinator / builder /
tester / fixer / auditor / planner) defined in `~/.claude/CLAUDE.md`, using the paper's
evaluator-guided search (propose a circuit → independent evaluator verifies exactness and scores
cost → revise) as the method for finding compressed circuits.

## 2. Decisions fixed in chat (2026-11-02) — do not change without asking Digonto

1. **Lattice:** 2×2 *sites*, **periodic** boundary conditions (torus): 4 sites, 8 links,
   4 plaquettes. Staggered fermions (even number of sites) when fermions are present.
2. **Charges (C3, C4):** **static SU(2) color sources** (e.g. spin-1/2 static quark–antiquark pair)
   placed at chosen vertices. They modify Gauss's law at those sites; they do not move.
   The planner chooses the placements to test (at least: no source, one $q\bar q$ pair on
   neighbouring sites, one pair on diagonal sites) and justifies them.
3. **Cost metric ("most compressed"):** **near-term hardware cost**. Primary: two-qubit gate
   (CNOT) count; secondary: circuit depth; tie-breaker: qubit count. The planner must fix the
   native gate set and the counting procedure (e.g. our own compilation, then Qiskit transpile to
   `{cx, u}` at a stated optimisation level and seed) so counts are reproducible. Toffoli /
   rotation counts and the paper's TQ-cost may be reported as extra columns but do not rank.
   Native-qudit (#18) and qumode (#19) circuits are counted in their own native gate sets and
   flagged as not directly comparable.
4. **"Produces the same result":** **own-model + shared check.**
   - Every circuit must reproduce the exact evolution of *its own* truncated model (same
     Hamiltonian, same truncation) to a stated tolerance in the physical (Gauss-law-obeying)
     subspace.
   - Encodings that describe the *same* truncated model (e.g. Kogut–Susskind at $j_{\max}$,
     gauge-invariant basis, LSH, prepotential at matched truncation) must agree with each other
     on shared observables (plaquette energy, vacuum persistence, electric energy, fermion
     number/string observables) within Trotter + numerical tolerance.
   - Encodings that change the model (q-deformed, discrete subgroups, $S^3$ partitionings,
     fuzzy SU(2), orbifold, light-front, Abelian pilots) are compared on the same observables
     with a *documented expected deviation*, not forced to agree.
   - Encodings that do not apply to 2+1D qubit hardware or to SU(2) (e.g. #12 integrate-out in
     1+1D, #23 Abelian pilots, #19 qumodes) get a written justification instead of a circuit,
     or a circuit for the closest meaningful variant, clearly labelled.

5. **Framework (Digonto, 2026-11-02, mid-kickoff message):** circuits are **built in Qiskit**
   (`qiskit` 2.5.2, `qiskit_aer` 0.17.2) and **tested with parallel execution** to run faster.
   - Every circuit is a `qiskit.QuantumCircuit`; gate counts come from Qiskit transpilation.
   - Tests run in parallel with `pytest -n auto` (pytest-xdist 3.8.0, installed) across the
     12 cores; tests must be independent and seed-deterministic so parallel runs give identical
     results to serial runs.
   - Independent evaluations (case × encoding × parameter sweeps, transpile seeds, many initial
     states) are fanned out with `joblib`/`concurrent.futures` process pools, or with Aer's own
     multithreading (`max_parallel_threads`, `max_parallel_experiments`). Avoid
     oversubscription: when running many processes, set BLAS / Aer threads per process to 1.
   - Aer here is CPU-only (`available_devices() == ('CPU',)`); do not plan on Aer GPU.

## 3. Encoding list (from Digonto, verbatim meaning)

1. Kogut–Susskind electric basis truncated at $j_{\max}$ (link stores $j, m_L, m_R$).
2. Gauge-invariant (intertwiner / spin-network) reduced basis.
3. Rishon / quantum-link model.
4. Loop–String–Hadron (LSH).
5. Prepotential / Schwinger-boson.
6. q-deformed SU(2)$_k$.
7. Discrete-subgroup digitization (binary tetrahedral 24, octahedral 48, icosahedral 120).
8. Partitionings of the SU(2) manifold $S^3$.
9. Fuzzy SU(2).
10. Orbifold lattice.
11. Mixed / dual basis and fully gauge-fixed SU(2).
12. Integrating out the gauge field in 1+1D.
13. Eliminating fermionic matter (Zohar–Cirac).
14. Jordan–Wigner staggered fermions.
15. Bravyi–Kitaev / Verstraete–Cirac / compact fermion encodings.
16. Binary (compact) register, $\lceil \log_2 d \rceil$ qubits.
17. Unary / one-hot and Gray-code registers.
18. Native qudits.
19. Bosonic modes / qumodes.
20. Gauss's law as an error-detecting code (post-selection / flagging).
21. Gauge protection by energy penalty.
22. Light-front / momentum-space formulations.
23. Abelian pilots (rotor, $\mathbb{Z}_M$).

Note (coordinator's reading, for the planner to confirm or revise): these are not 23 parallel
alternatives. They form layers that combine:
- gauge-field representation: 1–11, 22, 23;
- fermion-to-qubit map / matter handling: 12–15;
- register / hardware encoding of each local degree of freedom: 16–19;
- gauge-violation handling: 20–21.
A "circuit" is therefore one combination (representation × fermion map × register × protection).
The plan must say which combinations are built and why the rest are dominated or inapplicable.

## 4. Lessons from the paper to apply (method for compression)

- **Evaluator first.** An independent, cheap, exact evaluator verifies every candidate circuit and
  scores its cost; candidates are revised against that score. Here: exact simulation in the
  physical subspace + gate counting with a fixed transpile pipeline.
- **Specialized representation for frequently updated registers** (SI V: recode links once,
  keep the running product in a form where updates are cheap, restore at the end).
- **Reuse shared partial products** between neighbouring plaquettes instead of rebuilding each
  loop from the identity (SI V, Eq. (86): trace invariance under cyclic rotation and inversion).
- **Read diagonal functions directly** from register bits rather than through lookup tables
  (SI V, "Reading the trace directly").
- **Conditional routing:** replace several controlled copies of an expensive block with cheap
  controlled swaps around one shared block (main text, Eq. (1)).
- **Measurement-based uncomputation and decoding instead of storing history**, where the gate set
  allows.
- **Failure budget:** allow rare, flagged failures (here: Gauss-law post-selection, #20) if they
  buy a large saving, and report the discarded fraction.

## 5. Constraints and resources

- Machine: 12 CPU cores, 62 GB RAM, GTX 1060 6 GB GPU. Python 3.12.14 (conda env `coding`),
  qiskit 2.5.2, qiskit_aer, numpy 2.5.2, scipy 1.18.0, numba, quimb, sympy, pytest.
- Full-register statevectors above ~31 qubits do not fit in RAM; verification must work in the
  physical / reachable subspace, or verify terms separately and compose, or use another exact
  method the planner justifies.
- All physics checks in float64 / complex128. Fixed seeds. Every number traceable to a commit,
  command and parameters (`results/`).

## 6. Suggested milestone outline (planner refines and locks)

- M1: Hamiltonians and exact references for C1–C4 in at least two independent bases
  (e.g. KS electric basis and gauge-invariant basis) that must agree (spectra, dynamics).
- M2: Evaluator: circuit → exact action in the physical subspace, fidelity vs exact evolution,
  fixed CNOT/depth/qubit counting pipeline.
- M3: C1 circuits across all applicable encodings, baseline then compressed.
- M4: C2 (fermions) across applicable encodings and fermion maps.
- M5: C3 (static charges).
- M6: C4 (fermions + static charges).
- M7: Paper-style compression search and the final comparison table
  (case × encoding → qubits, CNOTs, depth, fidelity, observable agreement).
