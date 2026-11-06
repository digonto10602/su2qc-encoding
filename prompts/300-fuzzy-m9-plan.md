# Plan 300 — M9: fuzzy gauge theory, general one-Trotter-step circuit (48 qubits)

Date: 2026-11-06. Planner (Claude Fable 5.1). Trigger: START_HERE §3 (M9 brief), plan 001 §3 M9/M10, Digonto's decisions of
2026-11-06 (`notes/STATUS.md` Decisions; `scratch/fuzzy-hamiltonian-check.md`). Research: `reports/research/300-fuzzy-m9-research.md`.
Methods: `docs/METHODS-fuzzy.md` (F1–F8). Locked tests: `tests/acceptance/m9/`.

## 0. Decisions in force (one line each; see research 300 §1)
1. Target Hamiltonian = N = P Eqs. 34–37 **with** $\kappa_2\mathcal K_2$; 4 qubits/link, 48 qubits, no 3-qubit reduction (Digonto).
2. Electric normalisation Paulo Eq. 16: $\tfrac{g^2}{4}\sum\mathcal K_1$, $\kappa_1=\alpha/2$ (Digonto).
3. $r=\kappa_2/\kappa_1$ free; nominal $r=1$ ($\kappa_2=\alpha/2$); tests also at $r=0$ (coordinator default, Digonto may override).
4. Plaquette: $H_B^{\rm fz}=-2\square$, $U_B=e^{+2i\beta\square}$ (Eq. 16 factor, KS sign; coordinator default). Daggers per P Eq. 35/37.
5. Gauss orientation per paper (P Eq. 33): $T_L$ on outgoing links; N Eq. 3 is a typo (coordinator default).
6. **$U_B$ target = exact 8-qubit exponential.** The commuting-cluster product is *not* exact (measured error 1.9, even on gauge singlets) and is only a reported row.
7. Outer links: carry the same one-link $U_E,U_K$ blocks (reported as a separate row); $U_B$ reads no outer qubit. Physical set = full Gauss kernel, far ends free; verification is block-wise (F6), never by enumerating the $10^8$ physical states.
8. Assumptions Digonto may override: items 3–5, 7, the closed-sector/observable definitions (F7), and the $g^2$ map $g^2=\sqrt{2\alpha/\beta}$.

## 1. Method (equations: METHODS-fuzzy F1–F5)
* Codec F1 (link $\ell$ at qubits $4\ell..4\ell+3$, $q_1\to4\ell+3$). Operators F2 (Pauli forms, Tex Eq. (pauli), verified exact).
* Step F3: order 1 $=U_B(\beta)\,U_K(\kappa_2)\,U_E(\alpha)$ (kinetic layers first in the circuit); order 2 $=U_E(\tfrac\alpha2)U_K(\tfrac{\kappa_2}2)U_BU_K(\tfrac{\kappa_2}2)U_E(\tfrac\alpha2)$.
* $U_E$ and $U_K$ one-link circuits: $\mathcal K_1=\tfrac32-\tfrac14(X_2X_4-Y_2Y_4+Z_2Z_4)(1+Z_1Z_3)$ — diagonalise the $(q_2,q_4)$ Bell part with CNOT+H (the three terms commute), then phases controlled on $Z_1Z_3$; $\mathcal K_2$ = 4 commuting weight-2/4 strings → simultaneous Clifford diagonalisation then 4 `rz` (all angles linear in $\alpha$, $\kappa_2$). Exactness is required as a 16×16 unitary, not just on a subspace.
* $U_B$: parity/SVD route F5. Builder recipe: (a) 3 CNOTs $q_1^{\ell_k}\leftarrow q_1^b$ (parities $p$); (b) for each $p$: flag ancilla $a_p=[p\text{-pattern}]$ (3-controlled Toffoli, METHODS §7 ladder), apply $C_p$ (f-controlled 4-qubit fixed unitary, controlled additionally on $a_p$), the label-controlled $R_x(-4\beta\sigma_p)$ on $f$, $C_p^\dagger$, uncompute $a_p$; (c) undo (a). **First measure** whether each $\tilde D_p$ (unitary extension of $A_pB_p^\dagger$ with the right-singular vectors mapped to computational labels) can be chosen Clifford (Pauli→Pauli test); if yes the fixed parts are CNOT/H/S networks and the circuit is angle-linear with ≤ 24 rotations; if not, lower each 4-qubit fixed unitary by Qiskit QSD (≤ 100 CX, ≤ 200 fixed rotations) and control it through the flag. Hard cap: $N_{\rm rot}\le4000$ total (T-table feasibility, 0.03 s per pygridsynth call). Any other construction is acceptable if exact and within the cap.
* Verification F6; observables F7; Lean F8. Tolerances §4.

## 2. Interface (public API the locked tests import; builder creates stubs raising `NotImplementedError` first)
```
su2plaq.fuzzy.link:      GAMMA0, GAMMA (list of 3), GAMMA5, T_L, T_R (lists of 3; 4x4 complex ndarrays)
                         U_link(a,b)->4x4; lmul(M)->16x16; rmul(M)->16x16; calT_L(A)->16x16; calT_R(A)->16x16; U_op(a,b)->16x16
                         K1()->16x16; K2()->16x16; flavour()->16x16 (=rmul(GAMMA5)); centre()->16x16
                         pauli_K1()/pauli_K2()/pauli_U(a,b) -> qiskit SparsePauliOp on 4 qubits (little-endian: q_k on qubit 4-k)
                         irreps() -> list of (jL, jR, multiplicity) sorted; casimirs() -> (CL, CR) 16x16
su2plaq.fuzzy.plaquette: plaquette_row()->256x256 (row qubits; index sum_l (2 q1^l + q2^l) 4^l, l=b,r,t,l=0..3)
                         plaquette_pauli()->SparsePauliOp on 8 qubits; block_structure()->dict{p:(rows,cols,D_p,sing_vals)}
                         cluster_product(beta, order=None)->256x256 (greedy 4-cluster product, for the splitting row)
su2plaq.fuzzy.targets:   UE_link(alpha)->16x16; UK_link(kappa2)->16x16; UEK_link(alpha,kappa2)->16x16; UB_row(beta)->256x256
                         kappa2_of(alpha, r)->float ; apply_step(psi, alpha, beta, kappa2, order)->psi (65536-vectors, 16 inner qubits)
su2plaq.fuzzy.gauss:     corner_generator_apply(c, A, keys, amps)->(keys, amps) on 48-qubit COO; gauss_residual(keys, amps)->float
                         corner_singlet_dim(j1,j2,j3,j4)->int; physical_count(far_weighted: bool)->int (route A)
                         physical_count_characters(far_weighted: bool)->float (route B); isolated_plaquette_count()->int
                         sample_physical_states(n, seed, max_components=4096)->list[(keys, amps)] (route-A corner tensors, unit norm)
su2plaq.fuzzy.verify:    FuzzyBlockEncoding(n_data, data_qubits=None)  # adapter: all 2^n codes physical, n_outer=0, basis=None
                         verify_link(qc, V16)->Verdict ; verify_plaquette(qc, V256)->Verdict (+ .extra['touches_column']=False)
                         verify_step_samples(qc, alpha, beta, kappa2, order, n_random=32, n_phys=8, seed=20261104)->dict(err, gauss)
                         gauss_residual_outputs(qc, states)->float
su2plaq.fuzzy.observables: g2_of(alpha,beta)->float; closed_sector(g2, r)->(H, dim); electric_spectrum(g2)->list
                         plaquette_at_time(t, g2, r)->float; loschmidt(ts, g2, r)->ndarray; ks_closed_sector(g2)->2x2
                         shared_table(alpha=0.37, beta=0.61)->dict (schema in test O1)
su2plaq.encodings.fuzzy: FuzzyEncoding: name='fuzzy', n_data=16, n_outer=32, is_basis_encoding=True, basis=None,
                         registers{'d','o','link_b','link_r','link_t','link_l','outer_0'..'outer_7','row_b',...}
                         inner_codes()->arange(65536); decode(code)->code; layout_of(qc)->Layout (as twelve);
                         physical_vectors(n_sample=64, seed=20261104)->EncodedBasis (seeded SAMPLE, documented);
                         target(kind, alpha, beta, order=1, r=1.0)-> 16x16 ('UE','UK','UEK'), 256x256 ('UB'); 'step' raises ValueError
                         describe()->str ; import_map(source)->dict|str
su2plaq.circuits.fuzzy:  link_UE(alpha)->QuantumCircuit(4); link_UK(kappa2)->QuantumCircuit(4)
                         build_UE(alpha, with_outer=False); build_UK(kappa2, with_outer=False); build_UB(beta)
                         build_step(alpha, beta, kappa2=None, order=1, with_outer=False)   # kappa2 None -> r=1
                         registers: 'd' (16), 'o' (32, only if with_outer), ancillas after; allowed gates = M1 ALLOWED set
scripts/m9_results.py    -> results/fuzzy/{UE,UK,UB,step}.json (store.save_result schema), results/fuzzy/outer_row.json,
                            results/fuzzy/shared_observables.json, results/fuzzy/splitting.json
```
Additional signatures the locked tests call (exact names):
```
su2plaq.fuzzy.gauss.physical_count(far_weighted: bool, outer_vacuum: bool = False) -> int   # outer_vacuum: both outer links of every corner in a (0,0) copy -> 12 800
su2plaq.fuzzy.verify.verify_link(qc, V16, tol_err=1e-10) / verify_plaquette(qc, V256, tol_err=1e-10) -> Verdict
     (verify_plaquette: Verdict.extra['touches_column'] = False iff no gate acts on a column qubit {4l, 4l+1}; data = the 8 row qubits,
      every other qubit (column qubits, work qubits) is an ancilla that must stay |0>)
su2plaq.fuzzy.verify.verify_step_samples(...) -> {'err': float, 'gauss': float, 'n_inputs': int}
su2plaq.fuzzy.observables.one_step_plaquette(alpha, beta, r, order) -> float   # <Omega|U^dag ReTrU_P U|Omega> after one step (= 0 exactly)
su2plaq.fuzzy.observables.ks_loschmidt(ts, g2) -> ndarray                      # from the 2x2 KS closed sector
shared_observables.json: {"g2": float, "rows": {"fuzzy_r1","fuzzy_r0","ks": {"electric_per_link": [...], "closed_sector_dim": int,
     "closed_sector_spectrum": [...], "plaquette_vs_beta": [[beta, value], ...] with value = plaquette_at_time(t = beta * g2, g2, r) (>= 5 betas, same grid in all rows),
     "loschmidt": [[t, value], ...]}}, "provenance": provenance()}
results/fuzzy/<kind>.json extra: {"verification_scope": "full_unitary_link" | "full_unitary_row_block" | "blocks_certified_composition_sampled", "order": 1 (step), "outer_row": {...} (step)}
results/fuzzy/outer_row.json: {"n_outer_links": 8, "per_link": {"UE": logical_metrics, "UK": logical_metrics}, "totals": {...}, "provenance": ...}
results/fuzzy/splitting.json: {"cluster_product_vs_exact": [{"beta": b, "error": e}, ...] (b in {0.61, 0.23, 1.0}),
     "trotter_order1_vs_order2": {"alpha": 0.37, "beta": 0.61, "r": 1.0, "error": e, "space": "isolated_plaquette_singlets_50"}}
build_step(..., with_outer=True): for each outer link, exactly one link_UE(alpha) and one link_UK(kappa2) block at the FULL angles,
     once, regardless of order (they commute with everything); the inner part is unchanged.  FuzzyEncoding.describe() mentions "q_1" and "48".
```
Builder must not edit laptop-owned files; the evaluator is reused through `FuzzyBlockEncoding` with `gauss=False`.

## 3. Milestones and steps (builder time ≈ 2.5 h; P = parallelisable on disjoint files)
| Step | Files | Done-check | Turns green |
|---|---|---|---|
| 9.0 stubs | all modules of §2 raising `NotImplementedError`; `pytest --collect-only -q tests/acceptance/m9` clean; m9 tests fail PENDING | collect clean | — |
| 9.1 link ops (P) | `fuzzy/link.py`, `tests/unit/test_fuzzy_link.py` | residuals 0 for F2 identities; Pauli forms match | `m9/test_fuzzy_link.py::test_M9_D1_link_algebra` |
| 9.2 irreps/spectra/plaquette structure (P after 9.1) | `fuzzy/plaquette.py`, `fuzzy/targets.py` | spectra F2/F5; block structure; cluster product error | `test_M9_D2_irreps_spectra_plaquette` |
| 9.3 codec, Gauss, counts (P) | `encodings/fuzzy.py`, `fuzzy/gauss.py` | counts 50 / 12 800 / 101 197 218 / 6 767 266 914 both routes; sampled states Gauss ≤ 1e-10 | `test_fuzzy_codec_gauss.py::test_M9_C1_*` |
| 9.4 verify adapter | `fuzzy/verify.py` | `verify_link` on `link_UE` stub returns Verdict | (used by K1/B1/S1) |
| 9.5a kinetic circuits (P) | `circuits/fuzzy.py` (`link_UE`, `link_UK`, `build_UE`, `build_UK`) | 16×16 exact ≤ 1e-10, angles linear | `test_fuzzy_circuits.py::test_M9_K1_*` |
| 9.5b plaquette circuit | `circuits/fuzzy.py` (`build_UB`) | 256×256 exact ≤ 1e-10; columns untouched; $N_{\rm rot}\le4000$ | `test_M9_B1_*` |
| 9.5c step | `build_step` | both orders; sampled step error ≤ 1e-10; Gauss ≤ 1e-10; outer row | `test_M9_S1_*` |
| 9.6 observables (P) | `fuzzy/observables.py` | shared table; one-step identity | `test_fuzzy_observables.py::test_M9_O1_*` |
| 9.7 metrics, results, report | `scripts/m9_results.py`, `results/fuzzy/*.json`, `docs/report-9-fuzzy-general-circuit.md` | T tables + re-verify; JSON schema | `test_M9_T1_*` (slow), `test_M9_R1_*` |
| 9L1 Lean link algebra (P) | `lean/Su2Plaq/Fuzzy/Link.lean` + root import | `lake build`; `#print axioms` standard only | reported in R1 extra (`lean`) |
| 9L2 Lean counts (P) | `lean/Su2Plaq/Fuzzy/Counts.lean` | the four counts by `decide` (or `native_decide` labelled) | idem |
| 9L3 Lean per-circuit cert (optional) | `lean/Su2PlaqCert/Fuzzy/` | only if $U_B$ fixed parts ∈ K; else `n_a` | — |

## 4. Acceptance tests and tolerances (all in `tests/acceptance/m9/`)
| Id | Test | Tolerance and justification |
|---|---|---|
| M9-D1 | link algebra, Pauli forms, pseudo-reality, flavour/centre | residual ≤ 1e-12: entries are multiples of 1/4, products of ≤ 3 16×16 matrices in float64 round at ≤ 1e-15 |
| M9-D2 | irreps, $\mathcal K_{1,2}$ spectra, $[\mathcal K_1,\mathcal K_2]=0$, $\square$ spectrum/Pauli count/block structure, cluster product error ≥ 0.5 | eigenvalues rounded to 1e-8 (eigh on 256×256: 1e-13); integer multiplicities exact |
| M9-C1 | codec/registers, counts (two routes, exact integers; route B within 1e-3 of the integer: quadrature exact, float sum of ≤ 4e7 terms ≈ 1e-6 relative at worst… see test), seeded physical states Gauss ≤ 1e-10 | corner tensors from `eigh` on ≤ 81×81 → 1e-13 |
| M9-K1 | `link_UE`, `link_UK`, `build_UE`, `build_UK` exact (16×16 and 48-qubit layout) | op-norm ≤ 1e-10 after one phase (M1 rule: float64 over ≤ 3e4 gates ≲ 1e-12); weights ≤ 1e-20 |
| M9-B1 | `build_UB` exact 256×256; column qubits untouched; ancillas clean; $N_{\rm rot}\le4000$; reversed sign rejected | idem |
| M9-S1 | both step orders, nominal + alternate angles, $r\in\{1,0\}$; sampled dense check; Gauss of outputs; order mismatch detected; outer row | ≤ 1e-10 (exact angles); mismatch > 1e-3 (orders differ at $O(\alpha\beta)$) |
| M9-T1 (slow) | T(ε) tables (pygridsynth band, Qiskit ±10 %), synthesised circuit re-verifies | $N_{\rm rot}\varepsilon+10^{-9}$ (prompts/003 §2, 004: triangle inequality over $N_{\rm rot}$ rotations each within ε; the Gauss residual shares the budget) |
| M9-O1 | shared-observable JSON vs recomputation; KS 2×2 reference; one-step identity | 1e-10 (closed-sector `eigh` ≤ 50-dim) |
| M9-R1 | results JSON schema/provenance, render | exact keys |

## 5. Do-not-retry
* Commuting-cluster product as the $U_B$ target (not exact; error 1.9). * Generic 8-qubit QSD `UnitaryGate` for $U_B$ (31k CX, 37k non-linear rotations; T-table infeasible). * Enumerating physical states for `evaluate()` ($10^8$ states). * 3-qubit-per-link reduction ($\{F,\mathcal K_2\}=0$). * Using the laptop evaluator's Gauss branch (KS-specific `enc.basis`).

## 6. Risks and stop condition
* $U_B$ fixed unitaries not Clifford ⇒ up to ~7k fixed rotations: T-table slow (≈ 15 min) but within the cap; Lean cert `n_a`. Stop and ask Digonto only if no exact construction with $N_{\rm rot}\le4000$ is found within 60 min of builder time (then raise the cap in a plan amendment, never silently).
* $r$ and the plaquette sign are coordinator defaults; if Digonto overrides, only `kappa2_of`, `UB_row` sign and nominal JSONs change (tests parametrise $r$).
* Memory: dense step samples on 16+≤8 qubits (≤ 2^24 amplitudes, 256 MB); keep ancillas ≤ 8 in `build_UB`.
* Cost per step: 9.1–9.4 seconds each; 9.5b minutes (QSD of 16 four-qubit unitaries); T1 ≈ 0.12 s × $N_{\rm rot}$ per circuit; counts route B ≈ 2.5 min (80⁴ grid; the test uses 40 points ≈ 10 s — the integrand degree is ≤ 2·(2·1+1)·… < 80, so 40 Gauss points stay exact).
