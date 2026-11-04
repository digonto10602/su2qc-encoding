<!-- prompts/001 — chat-derived plan approved by Digonto on 2026-11-04 (coordinator session). Source: ~/.claude/plans/we-are-going-to-witty-noodle.md. The planner turns this into prompts/002 with researched formulas, METHODS and locked acceptance tests. -->

# Plan — SU(2) plaquette with 8 outer links: one-Trotter-step circuits in five encodings, then Gu-et-al-style compression

Date: 2026-11-04 · Project: `/home/digimonk/Projects/su2qc-encoding` (commit 3b16585, no source code yet)
Supersedes `prompts/000-plaquette-starter-plan.md`.

## Context

Digonto wants to study the plaquette drawn earlier (4 inner links b, r, t, l; 8 outer links, two per corner; 4 four-valent corners; $L=12$) at truncation $j_{\max}=1/2$, in five qubit encodings, **one at a time, in this order**:

1. **12-qubit** — Paulo's definition (notes Sec. IV.A): 3 qubits per inner link holding $(j, m, m')$, 12 data qubits. The circuit changes only these 12 qubits but **may read the outer links as controls** ("12-qubit circuit whose change depends on the outer links").
2. **Spin network** — Paulo's Sec. IV.B: one qubit per link ($j=0\to|0\rangle$, $\tfrac12\to|1\rangle$) + one intertwiner qubit per corner.
3. **Rishon** (quantum link model).
4. **Loop-string-hadron (LSH)**.
5. **Fuzzy** gauge theory.

For each encoding: (a) build in Qiskit 2.5.2 / Aer 0.17.2 the circuits for one Trotter step, $U_E(\alpha)=e^{-i\alpha H_E}$ and $U_B(\beta)=e^{-i\beta H_B}$ of the Kogut–Susskind Hamiltonian; verify on **every** Gauss-law state $G^a_x|\psi\rangle=0$; count CNOTs and T gates; **report**. (b) Compress that circuit with the loop structure of Gu, Kemeny, Yelin, Lukin (arXiv:2610.22367) — LLM proposes circuit-building programs, an independent evaluator verifies and scores, an archive keeps the best per cost cell — with **Claude Code agents in this session as the proposer**; **report** before/after.

Sources on disk: Paulo's notes `/home/digimonk/Projects/su2qc-paulo-code/hamiltonian-gauge-theories-circuits.pdf` (12-qubit: pp. 4–7, Eqs. 23–39; spin network: pp. 7–10, Eqs. 40–44, Table I), his circuits (`SU2_plaquette_12qubit_encoding/*.ipynb|.qasm|.qpy|_metadata.json`: 34 qubits, CX 294, T 1162 at $\varepsilon=10^{-6}$; `spin_network_plaquette3.gates.txt`: 15 qubits, 68 CX, 64 T, 4 rotations), Digonto's note `refs/su2_plaquette_truncations_encodings.md` + script, Gu et al. `refs/2610.22367v1.txt`. Paulo has no rishon/LSH material and only one handwritten fuzzy page; those three need planner research (sources: note §4.3–4.5).

---

## 1. Physics fixed for the whole project (goes into `docs/METHODS.md`)

| Item | Definition |
|---|---|
| Hamiltonian (Paulo Eq. 16, $a=1$, $g_s=g_t=g$) | $H=\frac{g^2}{2}\,H_E+\frac{1}{g^2}\,H_B$, with $H_E=\sum_{\ell=1}^{12} j_\ell(j_\ell+1)$ and $H_B=-\sum_P\big(\mathrm{Tr}\,U_P+\mathrm{Tr}\,U_P^\dagger\big)$, $U_P=U_bU_rU_t^\dagger U_l^\dagger$. (Standard KS texts use half this magnetic coefficient; only the $(g,dt)\to(\alpha,\beta)$ map changes.) |
| Trotter step | $U_E(\alpha)=e^{-i\alpha H_E}$, $U_B(\beta)=e^{-i\beta H_B}$; $\alpha=g^2dt/2$, $\beta=dt/g^2$. First order $U_1=U_B(\beta)\,U_E(\alpha)$ (electric layer first in the circuit); second order $U_2=U_E(\alpha/2)U_B(\beta)U_E(\alpha/2)$. Paulo/su2qc-trotter use $e^{+i\alpha_P\,\mathrm{Re\,Tr}\,U_P}$: $\alpha_P=2\beta$. |
| Nominal angles | $\alpha=0.37$, $\beta=0.61$; alternates $(0.91, 0.23)$, $(1.70, 1.00)$ — generic, not multiples of $\pi/4$. |
| Electric step at $j_{\max}=\tfrac12$ | $j(j+1)=\tfrac34$ per $j=\tfrac12$ link ⇒ one phase gate `p(−3α/4)` per link $j$-qubit (Qiskit `p(λ)=diag(1,e^{iλ})`; sign tested, not assumed). |
| Outer links | Never changed by $U_P$; $H_E^{\rm outer}$ commutes with everything, so $e^{-iHt}=e^{-iH_E^{\rm outer}t}\,e^{-i(H_E^{\rm inner}+H_B)t}$ exactly. Main gate counts = inner step; "+ outer electric" (8 phase gates = 8 rotations) reported as a separate row for every encoding. |
| Far ends of outer links | Spectator index (no operator touches it) ⇒ fixed. Physical subspace = **433** states (note §5); correctness on it implies correctness on the 17,362-dim far-end-free space. Outer-link reference register: 2 qubits $(j, m_{\rm near})$. |
| Physical states | Built from corner singlets (kernel of $\sum_a(\sum_{\rm ends}G^a)^2$, labelled by the inner-pair spin $J\in\{0,\tfrac12,1\}$), never from a $5^{12}$ dense space. |
| "Exact" per encoding | 12-qubit, spin network, LSH: the KS operator on the 433 states (same theory, two independent constructions must agree to $10^{-10}$). Rishon and fuzzy are *different* theories: "exact" = that model's own $e^{-i\beta H_B}$ on that model's own Gauss-law states; comparison with KS only through shared observables (electric energy per link, $\langle\mathrm{Re\,Tr}\,U_P\rangle$ after one step, closed-sector spectrum). |
| T-count (answers the "check this" request) | $T_{\rm total}(\varepsilon)=T_{\rm fixed}+\sum_{r=1}^{N_{\rm rot}}T_r(\varepsilon)$, $T_r(\varepsilon)\approx 3\log_2(1/\varepsilon)+O(\log\log(1/\varepsilon))$ (Ross–Selinger, arXiv:1403.2975; Paulo's footnote 4 states the same with "log"). The proposed "$\#T+3\ln\varepsilon$" has the wrong sign, base and multiplicity. $T_r$ is **measured** with pygridsynth 1.2.0 (Ross–Selinger implementation; measured here: 60–64 at $10^{-6}$ vs estimate 59.8) and cross-checked with Qiskit's `generate_preset_clifford_t_pass_manager` (Paulo's tool); the estimate is reported beside it. Loop uses $\varepsilon=10^{-6}$; reports give $\varepsilon\in\{10^{-4},10^{-6},10^{-8},10^{-10}\}$. |
| Cost order | CNOT, then $T_{\rm total}(10^{-6})$, then depth, then qubits (lexicographic). |
| Two claims to settle numerically, not assume | (i) 12-qubit: $U_B=U_B^{\rm inner}\otimes 1_{\rm outer}$ in the electric basis, so an outer-blind circuit correct on all 625 inner codes is correct on all 433 states; outer-reading circuits need only be right on the inner subspace $S_o$ compatible with each outer pattern $o$ (closed pattern: $\dim S_o=2$) — the don't-care budget the compression loop may exploit. (ii) Spin network: in the (inner pair \| outer pair) pairing the plaquette preserves the corner spin $J$, so its matrix elements depend only on inner spins and $J$ (Paulo's Fig. 2 claim); Digonto's note says "depends on the outer links" (true in other pairings). Test M0-X5 decides. |

---

## 2. What gets built (`src/su2plaq/`)

```
src/su2plaq/
  geometry.py          Diagram (12 links, 4 corners, loop [b+, r+, t−, l−]), point_split() → 8 trivalent sites
  su2/algebra.py       LinkSpace(jmax), clebsch_gordan, generators L/R      ← copy su2qc-skqd/src/skqd/su2.py
  su2/wigner.py        six_j (Racah, cached), f_symbol                      ← archive proto_m1.F
  exact/physical.py    corner_singlets, physical_basis (433, sparse COO), gauss_residuals, counts, s_o_dims
  exact/operators.py   plaquette_W (625×625), h_electric, h_magnetic_phys, target(kind, α, β, order)
  exact/spinnet.py     route B: labels (j_1..12, J_1..4), K_inner (47×47 from 6j), h_magnetic_phys_6j
  exact/compare.py     gauge_align, spectra_match, outer_block_structure
  encodings/base.py    Encoding protocol: name, layout (data/outer/ancilla), codec, physical_vectors, target, describe
  encodings/{twelve,spinnet,rishon,lsh,fuzzy}.py
  circuits/<enc>.py    build_UE(α), build_UB(β), build_step(α, β, order) → QuantumCircuit (registers d, o, a*)
  evaluate/sparse_sim.py   batched sparse simulator (independent of Aer; cap 5·10⁶ amplitudes)
  evaluate/evaluator.py    evaluate(qc, enc, target, tol) → Verdict (block-diagonal in outer controls, leak, ancilla, Gauss, one global phase)
  evaluate/aer_check.py    Aer statevector cross-check ≤ 24 qubits (never save_amplitudes with MPS — Aer 0.17.2 bug)
  metrics/logical.py       cx, depth, n_rot, t_fixed, qubits after transpile(LOGICAL_BASIS, opt 0, seed)
  metrics/cliffordt.py     ct_compile (Qiskit CT pass manager, Paulo's settings), pygridsynth_tcount, t_table(eps grid)
  results/store.py, results/report.py, metrics/provenance.py   JSON (+git commit, versions, seeds, machine) → Markdown
  compress/  spec.py builder.py oracle.py run_candidate.py archive.py brief.py round.py report.py passes.py
tools/lock.py, tools/check_lock.py        ← copy su2qc-qcadvantage/tools (SHA-256-locked acceptance tests)
tests/acceptance/{conftest.py, m0/, m1/, …}  LOCKED (planner)      tests/unit/  (builder)
refs/paulo/            copies of Paulo's notebook, qasm, qpy, metadata, gate file
compress/{specs,ideation,briefs,programs/<enc>/<family>/NNN-slug.py,attempts,discoveries,archive/<enc>/,cache/}
results/<enc>/*.json   results/compress/<enc>/round-rrr.json, summary.json
```

Design rules: Qiskit `QuantumCircuit` is the single circuit representation (no separate IR); allowed gate set for all circuits and proposals = `{x,z,h,s,sdg,t,tdg,rz,p,cx,cz}` ∪ macros `{ccx, rccx, swap, ch, crz, crx, cp, mcx≤4}` with their lowered CX/T costs recorded once in METHODS; counts always from our level-0 lowering with a fixed seed. One evaluator (`evaluate/evaluator.py`) serves acceptance tests and the compression loop; the tester's independent check is Aer statevector on ≤ 24-qubit specialised circuits. Deterministic polish passes (vendored from `su2qc-trotter/src/su2trotter/compress/`) are optional post-processing, not the core.

Evaluator algorithm: translate to the simulator basis at optimisation level 0; every gate touching an outer qubit must be diagonal there (else `invalid: writes outer`); for each pattern of the outer bits actually read, specialise the circuit and run all compatible inner codes in one batched sparse run (ancillas in $|0\rangle$); assemble $A_{k'k}=\langle\psi_{k'}|U_{\rm circ}|\psi_k\rangle$ on the 433 physical states; one global phase for the whole operator; `op_norm_error = ‖A − e^{iφ}V‖₂ ≤ 1e-10`, leak (outside physical span, or any ancilla ≠ 0) `≤ 1e-12`; Gauss residual `max‖G^a_x U|ψ⟩‖ ≤ 1e-10`. Synthesised (Clifford+T) circuits: error `≤ N_rot·ε + 1e-9`, leak `≤ (N_rot ε)² + 1e-12`. Fast path when no outer bit is read: check the 625×625 inner block on the inner span.

---

## 3. Milestones (each ends with the gate: tester full → auditor → benchmark → tag)

### M0 — Foundation (geometry, exact reference, evaluator, metrics)

| Step | Builds | Done-check | Acceptance ids |
|---|---|---|---|
| 0.1 | scaffold: `pyproject`, `pytest.ini` (`pythreads=1`, `-n auto`), `tools/lock.py`, `tests/acceptance/conftest.py` (SEED=20261104), `refs/paulo/` copies, METHODS §1–3 | `pytest -n auto` collects; `check_lock` OK | — |
| 0.2 | `geometry.py` | counts/roles match note §1 | M0-G1, G2 |
| 0.3 | `su2/algebra.py` (+ `paulo_adapter` $V_P$: signed permutation mapping the CG link basis to Paulo's Eq. 25–28 ε-rules), `su2/wigner.py` | commutators 1e-12; $V_P$ residual 1e-14; 6j vs sympy 1e-13 | M0-A1, A2, A3 |
| 0.4 | `exact/physical.py` route A | 433 states; Gauss ≤ 1e-10; counts 2 / 256 / 95 / 17 362 reproduced independently of `refs/su2_plaquette_encodings.py` | M0-C1..C5, X1; C6 (slow: $j_{\max}=1$ → 65 250) |
| 0.5 | `exact/operators.py` | $H_B^{\rm phys}$ hermitian, physical leak 0, closed 2×2 block $[[0,-2/g^2],[-2/g^2,3g^2/2]]$ (Paulo Eq. 37) | M0-X2, X3, X7 |
| 0.6 | `exact/spinnet.py` + `compare.py` route B | spectra A vs B 1e-10 at $g^2\in\{0.5,1,2\}$; **block structure in outer labels, J conserved (settles claim (ii))** | M0-X4, X5, X6 |
| 0.7 | `evaluate/sparse_sim.py` | vs Aer / dense `Operator` 1e-12 | M0-E1, E2 |
| 0.8 | `evaluate/evaluator.py`, `aer_check.py` | rejects: X on ancilla, Z on data, CX inner→outer, block-dependent phase; accepts: identity, CZ(outer, inner) | M0-E3, E4, E5 |
| 0.9 | `metrics/*` | `ccx` = 6 CX / 7 T; pygridsynth T in $[3\log_2(1/\varepsilon)-6,\,+8]$ with word error ≤ ε; Qiskit CT PM within ±6 and deterministic under seed | M0-M1, M2, M3 |
| 0.10 | `results/*`, provenance | JSON schema, commit recorded, report idempotent | M0-R1 |
| 0.11 | METHODS §4–8, STATUS, `graphify update .` | reviewed | — |

### M1 — 12-qubit encoding, general circuit → **Report 1**

| Step | Builds | Done-check | Ids |
|---|---|---|---|
| 1.1 | `encodings/twelve.py`: Eq. 31 codec (`0→000, (+,+)→111, (+,−)→110, (−,+)→101, (−,−)→100`; `001/010/011` don't-care), outer 2-bit codec, `physical_vectors` (433 vectors on 12+16 qubits via $V_P$), `inner_codes` (625) | bijection; norms; Gauss via decode | M1-C1 |
| 1.2 | `circuits/twelve.build_UE(α)`: 4 `p` gates | ≤ 1e-10 at two α; single-link phase $e^{-3i\alpha/4}$ | M1-E1 |
| 1.3 | `circuits/twelve.build_UB(β)`: port Paulo's notebook (registers d12 p4 e4 w7 g3 tmp3 h1; $\alpha_P=2\beta$) | exact on 625 inner codes, β ∈ {0.4, 1, 2}; fallback: solve the sign layer from the operator (41 bright pairs, couplings 1, ½, ¼) | M1-B1 |
| 1.4 | physical verification with the outer register | 433 states ≤ 1e-10, leak ≤ 1e-12, ancillas clean, Gauss ≤ 1e-10, `outer_bits_read = 0` | M1-B2, B3, B4 |
| 1.5 | `build_step(α, β, order)` | orders 1, 2 | M1-S1 |
| 1.6 | Paulo cross-checks: his `.qpy` (β = 1) through our evaluator; our port compiled with his settings vs `_metadata.json` | error ≤ N_rot·1e-6 + 1e-9; counts within 5 % (exact match expected) | M1-P1, P2 |
| 1.7 | metrics + T(ε) table for $U_E$, $U_B$, step; synthesised circuits re-verified | bound holds; pygridsynth vs Qiskit within 10 % | M1-T1 |
| 1.8 | outer-control analysis: $\dim S_o$ for all 6561 outer patterns, inner-span rank (**settles claim (i)**) | rank reported (expect 625) | M1-O1 |
| 1.9 | `reports/…` Report 1 from JSON | — | M1-R1 |

### M2 — Compression machinery + 12-qubit compression → **Report 2**

| Step | Builds | Done-check | Ids (`test_compress_machinery.py::`) |
|---|---|---|---|
| 2.0 | **Coordinator (me), outside the repo:** create `~/.claude/agents/proposer.md` (frontmatter like `builder.md`: `name: proposer`, `model: claude-opus-5-5`, `effort: high`, `tools: Read, Grep, Glob, Bash, Write, Edit`; body = Gu-et-al rewrite-agent instructions: read the brief, iterate with `run_candidate --trial`, query the oracle, submit ONE program with `SUMMARY:`/`DISCOVERY:` lines, never touch `src/`, tests, prompts, reports); add `"proposer": ["compress/programs/", "scratch/"]` to `WRITE_ALLOW` in `~/.claude/hooks/guard.py` (line 22–26; without it an unknown role may write anywhere except the deny list); add the proposer row to the roles table in `~/.claude/CLAUDE.md`. Note `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` in `~/.claude/settings.json`: proposers cannot delegate subtasks (Gu et al. allowed it; not needed). | guard denies a proposer `Write` to `src/x.py` and allows `compress/programs/twelve/F1/001-test.py` (checked by piping a fake PreToolUse JSON into `guard.py`) | — |
| 2.1 | `compress/spec.py` (TaskSpec: encoding, kind, α, β, alternates, tolerances, ε, budgets, `render()` → `compress/specs/<enc>.md`), `oracle.py` (target matrix, column, element, codec, outer block; CLI) | oracle column = `exact` column | `test_oracle_matches_exact_step` |
| 2.2 | `builder.py`: proposer-facing wrapper around `QuantumCircuit` with `alloc/free` of clean ancillas, allowed-gate check, `discover()`; program contract `build(spec) -> Builder` + `SUMMARY:`/`DISCOVERY:` docstring lines; program files immutable once evaluated (sha256) | round-trip; disallowed gate → error | `test_builder_gateset`, `test_macro_costs` |
| 2.3 | `run_candidate.py` CLI (`--trial`: 64 seeded physical inputs, nominal angles, T estimate, < 10 s; `--full`: all 433, 3 angle pairs, identical skeleton required, pygridsynth) | general circuit valid; wrong circuits rejected with the right reason (dirty ancilla, angle off by 1e-6, missing $U_E$ factor, control changed) | `test_evaluator_*` (7 cases) |
| 2.4 | `archive.py` (entries with program sha, evaluator-code sha, spec sha, commit, versions, seeds; MAP-Elites cells over $(\lfloor 8\log_2(\mathrm{CX}+1)\rfloor,\lfloor 8\log_2(T_\varepsilon+1)\rfloor)$; lexicographic key; invalid never inserted), cache keyed by code hash (fixes skqd's stale-cache bug) | round-trip; elites = min key per cell | `test_archive_*`, `test_cache_keyed_by_code_hash` |
| 2.5 | `passes.py` (optional polish, vendored trotter passes; kept only if strictly better and still valid), `round.py --seed`: round 0 = general circuit, general+polish, Qiskit L3 (seed 12345), Paulo's 34-qubit circuit (fixed angle, not a parent), `su2qc-trotter/designs/lean22_v2` via `import_map` | all seeds evaluated, verdicts recorded | `test_polish_valid_and_not_worse`, `test_qiskit_l3_baseline_valid` |
| 2.6 | `brief.py` (ideation brief; round briefs: parent program path + feedback, 2–3 archive alternatives with costs, last 5 attempt summaries, DISCOVERY notes ≤ 30 lines, "rewrite the parent to improve the key"), `round.py --evaluate`, `report.py` (before/after table + lineage in the (CX, T) plane) | dry round with the general program as "proposal" end to end | `test_round_dry_run_end_to_end`, `test_report_table` |
| 2.7 | **Run the loop on the 12-qubit $U_B$ / step** (protocol §4) | archive best valid, key ≤ round-0 best, tester re-verifies with Aer | gate test `test_archive_best_valid_and_not_worse_than_seed` |
| 2.8 | Report 2 | — | — |

### M3/M4 — Spin network: general → Report 3; compression → Report 4
3.1 `encodings/spinnet.py` (16 qubits = 12 link + 4 corner; 433 computational codes; 47 inner labels; target from route B) · 3.2 confirm outer independence (M0-X5) and check Paulo's 15-qubit gate file (α_P = 0.1) through our evaluator on the **open** 433 states (M3-P1: expected valid if claim (ii) holds) · 3.3 `build_UE` · 3.4 `build_UB` from `K_inner` (frame + flags + phase walk; angles solved from the operator, cf. `su2qc-trotter/designs/spinnet_v2.py`) · 3.5 step + verification (ancillas clean) · 3.6 metrics, T(ε) · 3.7 Report 3 · 4.x loop (round 0 seeds: general, Paulo's 15-qubit file, trotter `spinnet_v2`) → Report 4. Ids M3-C1, K1, P1, E1, B1..B3, S1, T1, R1; M4 gate test.

### M5/M6 — Rishon (QLM): general → Report 5; compression → Report 6
Planner research first (Brower–Chandrasekharan–Wiese hep-th/9704106; note §4.3): exact model (SU(2) vs U(2) QLM, electric operator, det-term), link = 4 fermion modes (2 colours × 2 ends), Jordan–Wigner with link-contiguous modes (48 qubits; circuit touches 16), fixed 2 rishons per link (6 states: 2 singlets + one (½,½) quartet), Gauss's law as the local fermion-number-type rule. Steps: 5.1 model in METHODS · 5.2 link algebra + tests of its commutation relations · 5.3 physical basis (corner singlets over link labels), count by two routes, Gauss · 5.4 $H_E$, $H_B$ on the physical span; closed-sector spectrum; shared-observable table vs KS · 5.5 JW codec, `physical_vectors` · 5.6 `build_UE` (diagonal in occupation), `build_UB` (Pauli-string exponentials or Givens on the physical inner span) · 5.7 verification (fast path + seeded sampled physical states if the set is large), metrics, Report 5 · 6.x loop → Report 6. Ids M5-D1, C1, X1, B1, S1, T1, O1, R1.

### M7/M8 — LSH: general → Report 7; compression → Report 8
Point-split diagram (8 trivalent sites, 24 qubits = 3 loop-number bits per site; circuit touches the 4 inner sites = 12 qubits); validity = Abelian link checks (flux read from both ends agrees); target = route B on the split graph (LSH ≅ spin network for pure gauge; ladder factors must equal the 6j F-symbols — Raychowdhury–Stryker arXiv:1912.06133, planner cites the 2+1D plaquette form or derives it). Steps 7.1 codec + checks · 7.2 site operators vs 6j · 7.3 target · 7.4 circuits · 7.5 verification on 433 codes, metrics, Report 7 · 8.x loop → Report 8. Ids M7-C1, K1, B1, S1, T1, R1. (LSH reuses M3 machinery; can be moved before rishon at no cost if preferred.)

### M9/M10 — Fuzzy: general → Report 9; compression → Report 10
Planner settles from arXiv:2308.05253 the link dimension (design analysis: the wavefunction is a 4×4 matrix per link ⇒ 16 states ⇒ 4 qubits/link, 48 total; Paulo's handwritten 4×4 objects are the *operators*; the `K_1` theory superselects one bit ⇒ 3 qubits/link), the kinetic term ($\mathcal K_1$ vs $\mathcal K_2$), and the definition of $U_B$ (exact 8-qubit exponential vs product over commuting clusters — declare the product as the target and report its splitting error). Steps 9.1 link operators from the Pauli forms (`/home/digimonk/Downloads/su2qc_project_docs_sources (1)/.../project1_fuzzy_flux_tube.tex` l.57–97) + algebra tests · 9.2 irreps/spectra · 9.3 physical basis, count, Gauss · 9.4 targets · 9.5 circuits · 9.6 block-wise exact verification, shared observables · 9.7 metrics, Report 9 · 10.x loop → Report 10. Ids M9-D1, D2, C1, B1, S1, T1, O1, R1.

---

## 4. Compression loop protocol (Gu et al. structure on the physics-loop roles)

| Role | Does |
|---|---|
| planner | writes the compression prompt + spec hand-text + locked `tests/acceptance/m<N>/`; sets budgets |
| builder | implements `src/su2plaq/compress/*`; never writes proposal programs |
| coordinator (me) | `round.py` (deterministic), briefs via `brief.py` (paths, not pasted content), spawns proposers, commits per round, STATUS |
| **proposer** (new role, created by me in step 2.0: `~/.claude/agents/proposer.md`, Opus 5.5 high, write access limited by the guard hook to `compress/programs/` and `scratch/`) | one fresh agent per (round, family): reads the brief, iterates locally with `run_candidate --trial`, may query the oracle, submits ONE program under `compress/programs/<enc>/<family>/NNN-slug.py` with `SUMMARY:` and ≤ 3 `DISCOVERY:` lines. Writes nowhere else. |
| tester | after each round re-verifies new elites with Aer (second engine), cross-checks counts vs Qiskit `count_ops`; at the gate re-evaluates the whole archive from source |
| auditor | gate: evaluator physics, `git log -- src/su2plaq/compress` shows no proposer commits, provenance of every table number |

Rounds per encoding: **round 0** seeds (general, general+polish, Qiskit L3 fixed seed, external seeds) → **ideation** (one proposer, spec only, ≤ 5 architecture families, one datapath each → `compress/ideation/<enc>.md`) → **rounds 1…R**: one proposer per active family (≤ 5 in rounds 1–2, best 3 after; a family with no valid program after round 2 is dropped), parent = family elite, every 3rd round the global best is offered as an alternative parent (migration); coordinator evaluates (`--full`), polishes, archives, writes `results/compress/<enc>/round-rrr.json`, appends `compress/attempts/<enc>.jsonl` and `compress/discoveries/<enc>.md`; tester verifies; commit `compress <enc> round rrr`. **Stop** when: R = 8 rounds (6 for the first encoding), or 3 consecutive rounds without a better global key, or the proposer-session cap (20 per encoding). Validity (all required): allowed gates only; peak qubits ≤ data + 32; exact on all physical states at the nominal angles **and** at the two alternates with identical gate skeleton (prevents fixed-angle tricks); clean ancillas; one global phase; evaluation wall ≤ 300 s. Score: key (CX, $T_{10^{-6}}$, depth, qubits); invalid ⇒ ∞.

---

## 5. Reports ("report back")

Each report (`reports/<kind>/NNN-slug.md`, numbered with `~/.claude/bin/next-num`, rendered from results JSON only) and the chat summary follow: (1) what was asked, (2) actions, (3) what the result means, (4) problems/assumptions. Table rows: general | general + polish | Qiskit L3 | each external seed | best per family | global best. Columns: qubits (data + ancilla) | CX | $T_{\rm fixed}$ | $N_{\rm rot}$ | $T(10^{-6})$ measured | $T_{\rm est}(10^{-6})$ | $T(10^{-10})$ | depth | verdict (error, leak) | entry id / commit. Plus the "+ outer electric" row and, for rishon/fuzzy, the shared-observable table vs KS.

---

## 6. Verification (end to end)

- Fast: `pytest -n auto tests/unit`; acceptance per milestone: `pytest -n auto tests/acceptance/mN`; `python tools/check_lock.py`; `~/.claude/bin/acceptance-check`.
- Physics: route A vs route B spectra (1e-10); Gauss residuals on every circuit output (1e-10); Paulo's circuits through our evaluator (M1-P1, M3-P1); our port compiled with his settings reproduces his counts (M1-P2).
- Independence: counts from our lowering vs Qiskit `count_ops`; pygridsynth vs Qiskit Clifford+T synthesis; sparse simulator vs Aer statevector (≤ 24 qubits) vs dense `Operator` (≤ 10 qubits).
- Loop: evaluator sensitivity tests (M2 step 2.3); dry round end to end; gate test re-evaluates the archive best from source.
- Reproduce any report number: `python -m su2plaq.results.report <json>`; every JSON carries commit, parameters, seeds, versions, machine.

---

## 7. Execution in the physics loop (after approval)

1. Coordinator: write this plan as `prompts/001-plaquette-five-encodings-plan.md` (plan in force), update `notes/STATUS.md`, commit.
2. Planner (kickoff): research + `prompts/002-…` with the exact formulas/citations (6j plaquette form, Ross–Selinger citation, rishon/LSH/fuzzy operators), `docs/METHODS.md`, and the **locked** `tests/acceptance/m0/`, `m1/`, `m2/` (later milestones' tests are written when reached). Then `~/.claude/bin/acceptance-lock "prompts/002-…"`.
3. Build loop per step (builder → tester → commit), escalation rules as in `~/.claude/CLAUDE.md`; `graphify update .` after each builder step. Before M2 step 2.1: step 2.0 (proposer agent + guard-hook entry + CLAUDE.md row, done by me).
4. Milestone gates; Report after M1, M2, M3, … in chat + `reports/`.
5. Stop and ask when: a planner plan fails twice; an agent believes a locked test or tolerance is wrong; a physics result contradicts established physics with no bug found.

---

## 8. Decisions and assumptions for Digonto (defaults used unless changed)

1. **Proposer role**: I create it myself (step 2.0): `~/.claude/agents/proposer.md`, the `WRITE_ALLOW` entry in `~/.claude/hooks/guard.py`, and the roles-table row in `~/.claude/CLAUDE.md`. These are the only edits outside the repo; I will show the diff in Report 2.
2. Hamiltonian convention = Paulo Eq. 16 (§1). Nominal angles (0.37, 0.61).
3. $\varepsilon=10^{-6}$ in the loop; full grid in reports.
4. Loop budget: ≤ 8 rounds (6 for 12-qubit), ≤ 5 proposers/round, stop after 3 rounds without improvement.
5. Rishon register: 4 qubits/link Jordan–Wigner (48), circuit touches 16; the 3-qubit "6-state codeword" variant reported only as a register-size row.
6. Fuzzy: 4 qubits/link per the paper (planner confirms); $\mathcal K_1$ kinetic term unless the planner argues otherwise.
7. Main counts exclude the 8 outer electric phase gates (separate row).

---

## 9. Reuse map (copy/adapt; vendor with source commit, never import across projects)

| Need | Path |
|---|---|
| Link algebra, CG | `/home/digimonk/Projects/su2qc-skqd/src/skqd/su2.py` |
| Corner singlets (any valence) | `/home/digimonk/Projects/su2qc-skqd/src/skqd/vertex.py` (`vertex_tensors`, matter fixed to 0) |
| 6j plaquette (route B), Gauss projector pattern | `git show archive-2x2-lattice:scratch/planner/proto_m1.py` |
| Exact encoded-block check, leakage | `/home/digimonk/Projects/su2qc-trotter/src/su2trotter/sim.py`, `problem.py` |
| Gridsynth wrapper, T-count, metrics | `/home/digimonk/Projects/su2qc-trotter/src/su2trotter/synth.py`, `compress/cliffordt.py`, `compress/common.py` |
| Deterministic polish passes | `/home/digimonk/Projects/su2qc-trotter/src/su2trotter/compress/__init__.py` (+ package) |
| All-columns sparse run, certified rounding | `/home/digimonk/Projects/su2qc-skqd/2x4_compression_using_ai_v1/src/c2x4/evaluate.py` |
| Proposal registry / round / archive shape | `.../c2x4/proposals.py`, `scripts/loop_select.py`; manual `MANUAL_lgt_circuit_compression.md` |
| Paulo's circuits | `/home/digimonk/Projects/su2qc-paulo-code/SU2_plaquette_12qubit_encoding/*`, `spin_network_plaquette3.gates.txt`; trotter `designs/lean22_v2.py`, `designs/spinnet_v2.py`, `spinnet.py` |
| Locked acceptance tests, results JSON | `/home/digimonk/Projects/su2qc-qcadvantage/tools/{lock,check_lock}.py`, `tests/acceptance/*`; `/home/digimonk/Projects/su2qc-skqd/src/skqd/report.py` |
| Qiskit-native Trotter builder pattern | `/home/digimonk/Projects/su2qc-qcadvantage/su2torus/trotter.py` |
| Gu et al. loop and brief format | `refs/2610.22367v1.txt` lines 742–781 (Methods), 935–990 (Extended Data Fig. 1) |

Environment: `coding` env has qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0 (install with `--no-deps`), sympy 1.14, pytest-xdist.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| Reference space size (625 × 3⁸ ≈ 4·10⁶ states, 28+ qubits) | sparse COO physical states (~5·10⁴ components); block-diagonality in outer patterns; inner-span fast path; hard cap with an explicit "unsimulable" verdict |
| Aer cannot do 34–50 qubits | sparse simulator is the workhorse (validated vs Aer/`Operator` on small cases); Aer only ≤ 24-qubit specialised circuits |
| Paulo-vs-note outer-link conflict | decided by M0-X5 and M1-O1; both statements recorded in METHODS with pairing assumptions |
| Sign/phase conventions (CG basis vs Paulo's ε-rules vs 6j gauge) | $V_P$ adapter derived and tested; `gauge_align`; ported circuit verified against the operator with a sign-solve fallback |
| Fuzzy link dimension, missing LSH 2+1D plaquette formula, rishon model variants | planner research with citations before building; LSH fallback = route B on the split graph |
| Proposer over-fitting / fixed-angle tricks / dirty ancillas / tampering | 3 angle pairs + identical skeleton; leak and ancilla checks; evaluator-code hash in every entry; `git log` audit |
| Qiskit version drift, nondeterminism | pinned versions and seeds in every JSON; counts from our own lowering; M0-M3 determinism test |
| Proposer context limits | briefs carry paths, cost tables, ≤ 30 DISCOVERY lines; programs ≤ ~400 lines |
