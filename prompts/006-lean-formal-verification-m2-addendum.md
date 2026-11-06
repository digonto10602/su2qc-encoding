# 006 — Addendum to prompts/002 (M2): machine-checked proofs in Lean 4 — methods, physics structure, and Lean inside the compression loop

- Date: 2026-11-05 · Author: planner (Claude Fable 5.1) · Git commit at writing: `6cd7179` (milestone-1 + `env/requirements-coding.txt`)
- Plan in force: `prompts/002` + addenda `003`, `004`, `005`, and this file. **M2 steps 2.0–2.8 of prompts/002 §5 stay as written; this addendum inserts steps 2.L1–2.L9 (below) and amends §2.10 (`ProgramResult`, `Entry`, `TaskSpec.render`, `run_round`, `report_table`) and §5 step 2.7 (certification of the best).** Everything not mentioned is unchanged.
- Trigger: Digonto, 2026-11-05 — (i) machine-checked proofs, in Lean 4, of the mathematical methods used in the circuit compression; (ii) same day: use Lean to find and prove the structure of the physics problem and inside the Gu-et-al loop. Research: `reports/research/004-lean-proofs-compression.md` (prototype numbers quoted below come from there).
- Locked tests added: `tests/acceptance/m2/test_lean_formal.py`, `tests/acceptance/m2/test_lean_structure.py` (this run; coordinator re-locks → `acceptance-v6`).

Jargon, once: see `reports/research/004` header (Lean 4, Mathlib, axiom, `decide`, `native_decide`, certificate, operator norm, Laurent polynomial). *Kernel-checked* = proof re-verified by Lean's small kernel with the three standard axioms `propext`, `Classical.choice`, `Quot.sound` only; *native-certified* = the statement was decided by compiled Lean code (adds the per-theorem axiom `<name>._native.native_decide.ax_…`, i.e. trust in the Lean compiler) or by the compiled checker executable (same trust).

## 0. Diagnosis / scope decisions
Nothing failed. The decisions that shape this plan:
1. **Numerical evaluator stays ground truth** (Digonto). Lean adds proofs and exact certificates; a Lean failure never flips a numerical verdict, and a numerical failure is never rescued by Lean.
2. **Three trust levels, always labelled**: kernel-checked theorems (generic methods, counts); native-certified exact facts (per-circuit certificates, exact block structure); numerical (everything else). Reports say which.
3. **Per-circuit certification is exact and angle-free** (Laurent polynomials over $K=\mathbb Q(i,\sqrt2,\sqrt3)$, research §1.2): one certificate proves a circuit for all $(\alpha,\beta)$. It is only possible for *angle-linear* circuits (rotation angles = small rational multiples of $\alpha$ or $\beta$); others get status `n_a`.
4. **Budget**: Lean never slows a round beyond 20 min wall (≤ 1 certificate ≤ 600 s + ≤ 5 proposer lemma files ≤ 120 s each), run after the numerical verdicts.
5. **Decision needed from Digonto** (not blocking the build): accept the compiler-trust axiom for certificates (§8).

## 1. Method (equations, conventions; full detail in `docs/METHODS.md` §11)

Notation as in prompts/004 §2: $\Phi$ (isometry, columns = 433 physical states), $V$ target, $U$ circuit, $U'=U+E$ pruned simulation, $U'\Phi=\Phi A+S+X$. All Lean statements are over finite-dimensional complex inner product spaces (`EuclideanSpace ℂ (Fin n)` or abstract `InnerProductSpace ℂ E`), continuous linear maps `E →L[ℂ] F` with the operator norm, or `Matrix` with the scoped L2 operator norm (`open scoped Matrix.Norms.L2Operator`). Conventions: little-endian qubits; `rz(θ)=diag(e^{−iθ/2},e^{iθ/2})`, `p(λ)=diag(1,e^{iλ})`; $\omega=e^{i\pi/4}=(1+i)/\sqrt2$.

**(M1) Evaluator soundness** (generic, kernel-checked):
$$\|U\Phi-c\,\Phi V\|\le\|A-cV\|+\|E\|+\|X\|+\|S\|,\qquad |c|=1,$$
from $\|E\Phi\|\le\|E\|$, $\|\Phi(A-cV)\|\le\|A-cV\|$ and Pythagoras for the three orthogonal pieces ($\sqrt{a^2+b^2+c^2}\le a+b+c$). With $E=\sum_oP_oEP_o$ (block-diagonal in the outer pattern) $\|E\|\le\max_o\|P_oEP_o\|$ (prompts/005 §2); with $\sum_{i<12}\|G_is\|^2\ge\tfrac34\|s\|^2$ (hypothesis: spectral gap of $\sum(G^a_c)^2$) $\|s\|\le4\max_i\|G_is\|$ (prompts/004 §2); aer_mps: $\|\sum_ia_ix_i\|\le\|a\|_2\sqrt{\sum_i\|x_i\|^2}$.

**(M2) Synthesis** (generic): for $\|U_i\|,\|V_i\|\le1$, $\|U_1\cdots U_N-V_1\cdots V_N\|\le\sum_i\|U_i-V_i\|$; with $W_r=c_rR_r+\Delta_r$ ($|c_r|=1$) $\|\prod_rW_r-(\prod_rc_r)\prod_rR_r\|\le\sum_r\|\Delta_r\|\le N_{\rm rot}\varepsilon$ (prompts/003 §2).

**(M3) Gate identities** (generic): *monomial* matrices $M_{\pi,\phi}e_q=\phi(q)e_{\pi q}$ are unitary when $|\phi|=1$; *sandwich*: if $C$ is unitary with $Ce_{(x,z)}=\phi(x)e_{(x,f(x))}$ and $G=\sum_h|h\rangle\langle h|\otimes W_h$ with $W_h$ never changing $f$ or $\phi$, then $C^\dagger GC\,e_{(x,z)}=\sum_y(W_{f(x)})_{yx}e_{(y,z)}$ — the clean-ancilla compute/uncompute principle; instances: `rccx·crx·rccx = ccrx` (build_UB), `Builder.mcx` chains. $HZH=X$, $HR_zH=R_x$, CNOT/diagonal commutation (vendored bit model).

**(M4) Exact certificates** (native): circuit gates from `sparse_sim._translate` (SIM_BASIS, program order) acting on sparse vectors over the full basis integer (data|outer|ancilla) with coefficients in $K[z_\alpha^{\pm1},z_\beta^{\pm1}]$; $e^{im\theta}\mapsto z^m$, $\cos m\theta\mapsto\tfrac12(z^m+z^{-m})$, $\sin m\theta\mapsto\tfrac1{2i}(z^m-z^{-m})$, base angles $\theta_\alpha=\alpha/d_\alpha$, $\theta_\beta=\beta/d_\beta$. Accept iff for every physical state $U'\psi_k=c\sum_{k'}V_{k'k}\psi_{k'}$ **exactly** with the supplied unit $c=k\,z_\alpha^az_\beta^b$ ($k\in K$, $|k|=1$). This single equality implies block exactness, zero leak, clean ancillas, zero span leak and Gauss for all angles.

**(M5) Structure** (research §2): counts by kernel `decide` from the corner fusion rule $n_c=|T(j_a,j_b)\cap T(j_c,j_d)|$ with the outer-$m$ constraint ($m_c=-m_d$ when both outer spins are $\tfrac12$ and the inner pair is $(0,0)$); exact certificates for the physical basis, $H_B$ blocks, $K_{\rm inner}$, spectrum multiplicities, 12-qubit inner-operator components, symmetries; symbolic $[H_E^{\rm outer},H]=0$.

## 2. Lean subproject layout (builder creates in step 2.L1)
```
lean/
  lean-toolchain                 leanprover/lean4:v4.35.0           (identical to the sibling)
  lakefile.toml                  name = "su2plaq-lean"; [[require]] mathlib git … rev = "v4.35.0";
                                 [[lean_lib]] name = "Su2Plaq"            (Mathlib, theorems)
                                 [[lean_lib]] name = "Su2PlaqCert"  precompileModules = true  (NO Mathlib import; computable checker)
                                 [[lean_exe]] name = "su2plaq_cert"  root = "Su2PlaqCert.Main"
  lake-manifest.json             copied from the sibling (mathlib rev 56a005855ea17e0b0958f73ec801ae140b0a1679 and its 8 dependencies)
  .lake/packages/                copied from the sibling's lean/.lake/packages (6.7 GB olean cache; gitignored) — or `lake exe cache get`
  Su2Plaq.lean                   imports every Su2Plaq.* module
  Su2Plaq/Evaluator.lean  Gauss.lean  Aer.lean  Synthesis.lean  Gates.lean  Bits.lean  Peephole.lean  Rewrites.lean
  Su2Plaq/Structure/Counts.lean  Structure/Commute.lean
  Su2PlaqCert/K.lean  Laurent.lean  State.lean  Gates.lean  Circuit.lean  Check.lean  Structure.lean  Json.lean  Main.lean
  certs/                         generated theorem files for final circuits (committed; see 2.L7)
  AxiomCheck.lean                generated by su2plaq.lean.project.print_axioms (gitignored)
```
`.gitignore` additions: `lean/.lake/`, `lean/AxiomCheck.lean`, `compress/lean/certs/*.json` (large; keep `*.lean` theorem files and `structure.json`). Build commands: `export PATH=$HOME/.elan/bin:$PATH; cd lean && lake build` (all), `lake build Su2PlaqCert` (checker only, Mathlib-free, < 2 min cold), `lake env lean <file>` (one file), `lake exe su2plaq_cert check <cert.json>` → prints exactly one line `ACCEPT` or `REJECT <reason>` and exits 0/1; `lake exe su2plaq_cert eval <cert.json> <input_index>` → JSON of the exact output vector; `lake exe su2plaq_cert structure <structure.json>` → `ACCEPT`/`REJECT <reason>`.

## 3. Theorem statements (Lean sketches; names are LOCKED — the acceptance tests print their axioms)
All in `namespace Su2Plaq`. Prototype proofs that already compile against Mathlib v4.35.0 are in `scratch/planner/lean/P{1,2,3b,4}.lean` (builder: copy and finish them; they are not production code until they live in `lean/`).

```lean
-- Evaluator.lean  (prototype P2, P4)
theorem norm_sum_sq_of_pairwise_orth (s : Finset ι) (y : ι → F)
    (h : ∀ i ∈ s, ∀ j ∈ s, i ≠ j → ⟪y i, y j⟫_ℂ = 0) : ‖∑ i ∈ s, y i‖ ^ 2 = ∑ i ∈ s, ‖y i‖ ^ 2
theorem opNorm_add_three_le_of_orth (A B C : E →L[ℂ] F) (hAB : ∀ x y, ⟪A x, B y⟫_ℂ = 0)
    (hAC : ∀ x y, ⟪A x, C y⟫_ℂ = 0) (hBC : ∀ x y, ⟪B x, C y⟫_ℂ = 0) :
    ‖A + B + C‖ ≤ Real.sqrt (‖A‖ ^ 2 + ‖B‖ ^ 2 + ‖C‖ ^ 2)
theorem rss_le_sum (a b c : ℝ) (ha : 0 ≤ a) (hb : 0 ≤ b) (hc : 0 ≤ c) : Real.sqrt (a ^ 2 + b ^ 2 + c ^ 2) ≤ a + b + c
theorem pruning_triangle (U U' Ep T Φ : _) (hU' : U' = U + Ep) (hΦ : ‖Φ‖ ≤ 1) :
    ‖(U - T).comp Φ‖ ≤ ‖(U' - T).comp Φ‖ + ‖Ep‖
theorem opNorm_le_of_blockdiag (P : ι → (E →L[ℂ] E)) (T : E →L[ℂ] E) (M : ℝ) (hM : 0 ≤ M)
    (hsum : ∀ x, ∑ i, P i x = x) (hidem : ∀ i x, P i (P i x) = P i x)
    (horth : ∀ i j, i ≠ j → ∀ x y, ⟪P i x, P j y⟫_ℂ = 0) (hblock : ∀ x, T x = ∑ i, P i (T (P i x)))
    (hbound : ∀ i, ‖(P i).comp (T.comp (P i))‖ ≤ M) : ‖T‖ ≤ M
theorem verdict_sound (Φ : E →L[ℂ] F) (hΦ : ∀ x, ‖Φ x‖ = ‖x‖) (U Ep : F →L[ℂ] F) (V A : E →L[ℂ] E)
    (S X : E →L[ℂ] F) (c : ℂ) (hc : ‖c‖ = 1)
    (hdec : (U + Ep).comp Φ = Φ.comp A + S + X)
    (hΦS : ∀ x y, ⟪Φ x, S y⟫_ℂ = 0) (hΦX : ∀ x y, ⟪Φ x, X y⟫_ℂ = 0) (hSX : ∀ x y, ⟪S x, X y⟫_ℂ = 0)
    (b d l s : ℝ) (hb : ‖A - c • V‖ ≤ b) (hd : ‖Ep‖ ≤ d) (hl : ‖X‖ ≤ l) (hs : ‖S‖ ≤ s) :
    ‖U.comp Φ - c • Φ.comp V‖ ≤ b + d + l + s
-- Gauss.lean (P4)
theorem gauss_max_ge (x : Fin 12 → ℝ) (t : ℝ) (ht : 0 ≤ t) (hx : ∀ i, 0 ≤ x i)
    (h : (3/4 : ℝ) * t ^ 2 ≤ ∑ i, (x i) ^ 2) : ∃ i, t / 4 ≤ x i
theorem span_leak_le_four_gauss (G : Fin 12 → E → E) (s : E) (g : ℝ) (hg : ∀ i, ‖G i s‖ ≤ g)
    (hspec : (3/4 : ℝ) * ‖s‖ ^ 2 ≤ ∑ i, ‖G i s‖ ^ 2) : ‖s‖ ≤ 4 * g
-- Aer.lean (P4)
theorem cs_block_bound (s : Finset ι) (a : ι → ℂ) (x : ι → E) :
    ‖∑ i ∈ s, a i • x i‖ ≤ Real.sqrt (∑ i ∈ s, ‖a i‖ ^ 2) * Real.sqrt (∑ i ∈ s, ‖x i‖ ^ 2)
-- Synthesis.lean (P1)  [R : NormedRing, NormOneClass]
theorem norm_list_prod_le_one (L : List R) (h : ∀ u ∈ L, ‖u‖ ≤ 1) : ‖L.prod‖ ≤ 1
theorem prod_sub_prod_le (U V : List R) (hlen : U.length = V.length) (hU : ∀ u ∈ U, ‖u‖ ≤ 1)
    (hV : ∀ v ∈ V, ‖v‖ ≤ 1) : ‖U.prod - V.prod‖ ≤ (List.zipWith (fun u v => ‖u - v‖) U V).sum
theorem synth_bound {n : ℕ} (c : Fin n → ℂ) (R Δ : Fin n → A) (hc : ∀ i, ‖c i‖ = 1) (hR : ∀ i, ‖R i‖ ≤ 1)
    (hW : ∀ i, ‖c i • R i + Δ i‖ ≤ 1) :
    ‖(List.ofFn fun i => c i • R i + Δ i).prod - (∏ i, c i) • (List.ofFn R).prod‖ ≤ ∑ i, ‖Δ i‖
-- Gates.lean (P3b)
noncomputable def e (p : σ × τ) : σ × τ → ℂ := Pi.single p 1
noncomputable def ctrl (W : τ → Matrix σ σ ℂ) : Matrix (σ × τ) (σ × τ) ℂ
noncomputable def mono (π : (σ × τ) ≃ (σ × τ)) (φ : σ × τ → ℂ) : Matrix (σ × τ) (σ × τ) ℂ
theorem ctrl_mulVec_e … ; theorem mono_mulVec_e … ; theorem mono_conjTranspose_mul … (hφ : ∀ q, ‖φ q‖ = 1) : (mono π φ)ᴴ * mono π φ = 1
theorem sandwich (C : Matrix (σ × τ) (σ × τ) ℂ) (hC : Cᴴ * C = 1) (z : τ) (f : σ → τ) (φ : σ → ℂ) (hφ : ∀ x, φ x ≠ 0)
    (hcomp : ∀ x, C *ᵥ e (x, z) = φ x • e (x, f x)) (W : τ → Matrix σ σ ℂ)
    (hWf : ∀ h x y, W h y x ≠ 0 → f y = f x) (hWφ : ∀ h x y, W h y x ≠ 0 → φ y = φ x) (x : σ) :
    (Cᴴ * ctrl W * C) *ᵥ e (x, z) = ∑ y, W (f x) y x • e (y, z)
theorem rccx_crx_rccx_eq_ccrx (θ : ℝ) (x : Fin 2 × Fin 2 × Fin 2) :   -- σ = (a,b,t), τ = Fin 2 (ancilla h), z = 0
    (RCCX * ctrl (crxW θ) * RCCX) *ᵥ e (x, 0) = ∑ y, (ccrx θ) y x • e (y, 0)
    -- RCCX := mono rccxPerm rccxPhase with Qiskit's matrix: controls set → h flips with phase i (0→1) / −i (1→0); |a=1,b=0,h=1⟩ → −1; RCCXᴴ = RCCX
theorem h_z_h : H * Z * H = X ;  theorem h_rz_h (θ : ℝ) : H * Rz θ * H = Rx θ
-- Bits.lean, Peephole.lean: vendored from the sibling (commit 30f84af1), namespace renamed, header cites the source:
theorem cx_involutive … ; theorem perm_conj_diagonal … ; theorem cx_comm_diagonal_of_indep … ; theorem cx_comm_cx … ; theorem ccz_circuit …
-- Rewrites.lean: one theorem per polish rule name (rules.LEAN_RULES); initially cancel_cx_pair := cx_involutive, merge_rz := (Rz a * Rz b = Rz (a+b)), commute_diag_cx := cx_comm_diagonal_of_indep
-- Structure/Counts.lean (P6; plain Lean, decide; `set_option maxRecDepth 100000`, `maxHeartbeats 0` where needed)
theorem card_physical : total = 433 ; theorem card_link_patterns : linkPatterns = 256 ; theorem card_two_or_more : twoOrMore = 95
theorem card_closed : closedCount = 2 ; theorem far_end_weighted : farEndWeighted = 17362
theorem card_supported_outer : supportedOuterM = 3153 ; theorem max_states_per_outer : maxPerOuterM = 17
theorem dont_care_codes : 4 ^ 6 - 5 ^ 4 = 3471 := by decide
-- Structure/Commute.lean
theorem kron_disjoint_comm (A : Matrix m m ℂ) (B : Matrix n n ℂ) : (A ⊗ₖ 1) * (1 ⊗ₖ B) = (1 ⊗ₖ B) * (A ⊗ₖ 1)
theorem outer_electric_commutes (W : Matrix m m ℂ) (d : n → ℂ) : (W ⊗ₖ 1) * (1 ⊗ₖ diagonal d) = (1 ⊗ₖ diagonal d) * (W ⊗ₖ 1)
```
Definitions in `Counts.lean` are exactly those of `scratch/planner/lean/P6_count.lean` (`fuse`, `cornerCount`, `bit`, `patternCount`, `sumOver`/`maxOver` by **structural** recursion, `code`, `ospin`, `cornerM`, `patternCountM`, `innerSumM`, `supportedOuterM`, `maxPerOuterM`) with the geometry of METHODS §1 (corners $c_0:(b,l\,|\,o_0,o_1)$, $c_1:(b,r\,|\,o_2,o_3)$, $c_2:(r,t\,|\,o_4,o_5)$, $c_3:(t,l\,|\,o_6,o_7)$).

## 4. Certificate formats (JSON written by Python, read by `Su2PlaqCert.Json`)
**Circuit certificate** `compress/lean/certs/<id>.json`:
```json
{"schema": "su2plaq-cert-1", "circuit_id": "...", "program_sha256": "...", "n_qubits": 34, "n_data": 12, "n_outer": 16,
 "base": {"d_alpha": 4, "d_beta": 2},                      // theta_alpha = alpha/d_alpha, theta_beta = beta/d_beta
 "gates": [{"g": "p", "q": [2], "m": [-3, 0]}, {"g": "cx", "q": [0, 5]}, {"g": "h", "q": [7]}, {"g": "rz", "q": [3], "m": [0, 2]}, ...],
     // program order from sparse_sim._translate; angle given as exponent vector m = (m_alpha, m_beta) of the *gate's own angle*:
     // p/cp/rz/crz…: angle = m_alpha*theta_alpha + m_beta*theta_beta (for rz the matrix uses half the angle; the exporter
     //   therefore requires m to be even for rz-type gates or doubles d); "sx","h","x","z","s","sdg","t","tdg","cx","cz","swap","ccx","ccz" carry no "m"
 "states": [{"k": 0, "label": "...", "terms": [{"code": 123456, "c": [a,b,c,d,e,f,g,h]}, ...]}, ...],   // 433 exact K-vectors over the (data|outer) integer, ancillas 0
 "target": {"blocks": [{"ks": [k1,k2,...], "entries": [[i, j, [[ [ma, mb], [a,...,h] ], ...]], ...]}, ...]},  // V[ks[i], ks[j]] as a Laurent-K polynomial, block-diagonal in the outer pattern
 "phase": {"k": [a,...,h], "m": [a_alpha, a_beta]},        // c = k z^m, |k| = 1
 "provenance": {"git_commit": "...", "exporter_sha256": "...", "alpha_nominal": 0.37, "beta_nominal": 0.61, "float_phase_fit_residual": 1e-13}}
```
`K` element = 8 rationals $(a,b,c,d,e,f,g,h)$ for $a+bi+c\sqrt2+di\sqrt2+e\sqrt3+fi\sqrt3+g\sqrt6+hi\sqrt6$, each rational as `"p/q"` strings. Gate semantics in the checker = Qiskit matrices (`SIM_BASIS` minus `unitary`): `x z s sdg t tdg h sx rz p cx cz cp swap ccx ccz`; `unitary` ⇒ exporter returns `n_a`.

**Structure certificate** `compress/lean/structure-cert.json`: exact `states` (as above, in the CG convention over the electric key), `labels`, exact per-link `U_ij` ($5\times5$, $K$), `k_inner` ($47\times47$ rationals), `gauge` (±1 per state), `bright_pairs` of $K_{\rm inner}$, `dark_rows`, `spectrum` `[[lambda, multiplicity], ...]`, `inner625` (components of $-(W+W^\dagger)$ on the 625 Paulo codes: `dark`, `components` with sizes and edge couplings), `symmetries` `[{"name": "C4", "perm": [...433], "signs": [...]}, ...]`, `corner_kernel_dims` (16 entries). The checker recomputes $H_B^{\rm phys}$ from `states` and `U_ij`, so $H_B$ is not trusted input.

**Proved-structure summary** `compress/lean/structure.json` (for proposers, rendered into the spec): every fact with `value`, `proved_by ∈ {decide, native, numerical}`, `theorem`/`certificate` reference.

## 5. Interface (Python; the builder creates stubs raising `NotImplementedError` first)
```python
# src/su2plaq/lean/project.py
LEAN_DIR: pathlib.Path            # <root>/lean ;  TOOLCHAIN = "leanprover/lean4:v4.35.0" ; MATHLIB_REV = "v4.35.0"
STANDARD_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})
GENERIC_THEOREMS: tuple[str, ...]   # the full names of §3 (Su2Plaq.norm_sum_sq_of_pairwise_orth, …, Su2Plaq.outer_electric_commutes) — LOCKED list in tests
COUNT_THEOREMS: tuple[str, ...]     # Su2Plaq.card_physical, card_link_patterns, card_two_or_more, card_closed, far_end_weighted, card_supported_outer, max_states_per_outer, dont_care_codes
def lake(args: list[str], timeout: float = 1800.0) -> subprocess.CompletedProcess   # PATH += ~/.elan/bin; cwd = LEAN_DIR
def build(target: str | None = None, timeout: float = 1800.0) -> dict            # {"ok": bool, "seconds": float, "stdout": str, "stderr": str}
def print_axioms(names: list[str], timeout: float = 600.0) -> dict[str, frozenset[str]]  # writes lean/AxiomCheck.lean (`import Su2Plaq` + one `#print axioms` per name), runs `lake env lean`, parses; an unknown constant maps to frozenset({"<unknown>"})
def is_native_axiom(ax: str) -> bool     # ax.endswith-matches r"\._native\.native_decide\.ax_\d+(_\d+)*$" or ax == "Lean.ofReduceBool"
def no_sorry(paths: list[pathlib.Path] | None = None) -> list[str]   # lines containing `sorry`/`admit` outside comments in lean/Su2Plaq, lean/Su2PlaqCert, lean/certs; [] when clean
# src/su2plaq/lean/exact.py          (exact arithmetic; no floats except for recognition and cross-checks)
class KNum: a,b,c,d,e,f,g,h: Fraction; __add__/__mul__/__neg__/conj/__eq__; to_complex() -> complex; to_json() -> list[str]; @staticmethod recognise(z: complex, tol: float = 1e-12) -> "KNum | None"   # lattice search over denominators 2^a 3^b ≤ 48
class Laurent: dict[(int,int), KNum] ; arithmetic ; evaluate(theta_alpha, theta_beta) -> complex ; to_json()
def rational_multiple(theta: float, base: float, max_den: int = 64, tol: float = 1e-12) -> Fraction | None
def exact_corner_singlets(js, roles) -> list[list[KNum]]                        # sympy nullspace, same ordering/phase rule as exact.physical.corner_singlets
def exact_physical_basis(convention: str = "cg") -> list[dict]                 # 433 × {"label", "keys": int64[], "amps": KNum[]}; cross-checks |exact − float| ≤ 1e-12 per entry, raises otherwise
def exact_link_U() -> list[list[list[list[KNum]]]]                             # 5×5 per (i,j), CG convention; cross-check ≤ 1e-12
def exact_target_blocks(kind: str, order: int) -> list[dict]                    # per outer block: ks, Laurent-K entries with base (d_alpha, d_beta) = (4, 2) (U_E: z_alpha^{-3n}; U_B: Σ_λ P_λ z_beta^{-2λ}); cross-check vs operators.target at (0.37,0.61) ≤ 1e-12
# src/su2plaq/lean/certify.py
@dataclass class LeanCert: status: str; reason: str; cert_path: str | None; seconds: float; checker_sha256: str; theorem_path: str | None = None; axioms: list = field(default_factory=list)
    # status ∈ {"certified", "rejected", "n_a", "failed", "not_run"}; "n_a" reasons: "non_linear_angle:<gate>:<theta>", "unitary_gate", "phase_not_in_K", "too_many_qubits" (> 62)
def export_certificate(qc, enc, kind: str, alpha: float, beta: float, order: int, out_path, *, verdict_phases: list[complex] | None = None) -> pathlib.Path | str   # str = n_a reason
def export_raw_circuit(qc, out_path, *, alpha: float, beta: float) -> pathlib.Path | str   # gates + base only (no states/target); for `checker_eval` semantics tests; str = n_a reason
def check_certificate(path, timeout: float = 900.0) -> LeanCert           # `lake exe su2plaq_cert check <path>`
def certify_circuit(qc, spec, out_dir=None, timeout: float = 900.0) -> LeanCert    # export (nominal + alt angle phases via evaluate) + check; out_dir default <root>/compress/lean/certs
def certify_circuit_kind(qc, enc, kind: str, alpha: float, beta: float, order: int, out_dir=None, timeout: float = 900.0) -> LeanCert   # same without a TaskSpec (UE/UB/step at given angles; alt angles = ALT_ANGLES)
def write_theorem_file(cert_path, theorem_name: str, out_path) -> pathlib.Path   # lean/certs/<id>.lean: `import Su2PlaqCert` + the certificate as a Lean literal + `theorem <name> : Su2PlaqCert.check cert = true := by native_decide` + `#print axioms <name>`
def checker_eval(cert_path, input_index: int, timeout: float = 900.0) -> list[tuple[int, "Laurent"]]  # `lake exe su2plaq_cert eval`
# src/su2plaq/lean/structure.py
def export_structure_certificate(out_path) -> pathlib.Path                      # §4 structure certificate (exact), symmetries from symmetry_candidates
def check_structure(path, timeout: float = 900.0) -> LeanCert                    # `lake exe su2plaq_cert structure <path>`
def symmetry_candidates(basis=None) -> list[dict]   # exactly 16 candidates (D4 × charge conjugation), each {"name" ("identity", "C4", "C4^2", "C4^3", "reflect_x", …, "cc", "C4*cc", …), "commutes_HB": bool, "commutes_HE": bool, "residual": float, "perm": list[int] (433, a permutation) , "signs": list[±1]}; perm/signs filled for the commuting ones (residual ≤ 1e-10)
def structure_facts() -> dict      # {"facts": [{"name", "value", "proved_by": "decide"|"native"|"numerical", "theorem"|"certificate", "note"}, …], "symmetries": [{"name", "perm", "signs"}, …], "provenance": {...}}
    # required fact names: card_physical, card_link_patterns, card_two_or_more, card_closed, far_end_weighted, card_supported_outer, max_states_per_outer (decide);
    # spectrum_multiplicities (value [[λ, m], …] for λ = −2,−1,−½,0,½,1,2 → 16,96,16,177,16,96,16; native), k_inner_bright_pairs, k_inner_dark_rows, inner625_components, dark_labels, dont_care_codes (decide), outer_support_table (native)
def write_structure_json(path=None) -> pathlib.Path   # compress/lean/structure.json (§4); CLI: python -m su2plaq.lean.structure --export [--certificate]
# structure certificate JSON keys read by the tests: "states" (433), "k_inner" (47×47 rationals as "p/q" strings), "bright_pairs" ([{"pair": [i, j], "coupling": "p/q"}] ×8),
#   "dark_rows" (31 indices), "spectrum" ([[λ, m], …]), "gauge", "labels", "u_link", "inner625", "symmetries" ([{"name", "perm", "signs"}], ≥ 2 incl. identity), "corner_kernel_dims"
# src/su2plaq/lean/rules.py
LEAN_RULES: dict[str, str]        # polish rule name -> "Su2Plaq.<theorem>"; every rule name that passes.polish can emit in its log must be a key
# src/su2plaq/lean/lemmas.py
def lemma_file_for(program_path) -> pathlib.Path | None                          # <program>.lean next to the program, if it exists
def check_program_lemmas(program_path, timeout: float = 120.0) -> dict           # {"status": "none"|"proved"|"failed", "file", "theorems": [names], "axioms_ok": bool, "seconds", "message"}; `lake env lean <file>` with cwd lean/; a file importing anything but Su2Plaq/Su2PlaqCert/Mathlib → "failed"
# amendments to prompts/002 §2.10
ProgramResult.lean_lemmas: dict | None = None      # from check_program_lemmas (mode "full" only)
Entry.lean: dict | None = None                     # asdict(LeanCert) or None (default keeps the locked _fake_entry constructor valid)
TaskSpec.render(): adds the section "Proved structure (Lean)" from compress/lean/structure.json when present (facts with proved_by != numerical, one line each)
run_round(...): after evaluation, if the round produced a new global best (or round == 0: the general seed), certify_circuit(best, spec) within the budget and store Entry.lean; never changes validity; total Lean wall per round ≤ 1200 s (hard timeout → status "failed", recorded); the returned dict gains "lean_seconds" (float, Lean wall of the round)
report_table(...): new column "Lean" with values kernel+native-certified → "certified", else "n_a"/"failed"/"not_run"
passes.polish(qc, spec) -> (qc, log): every log line starts with a rule name from rules.LEAN_RULES
```
`su2plaq.lean` imports nothing from `su2plaq.compress` (the dependency goes the other way).

## 6. Steps (one builder call each; tester verifies the listed ids). Steps 2.L1–2.L3 can start now (before 2.1); 2.L4+ after 2.5.
| Step | Builds | Done-check (tester) | Acceptance ids that must turn green |
|---|---|---|---|
| 2.L1 | `lean/` skeleton (§2) with toolchain, lakefile, manifest copied from the sibling, `.lake/packages` copied (or `lake exe cache get`); `Su2Plaq.lean` importing empty modules; `Su2PlaqCert` skeleton with `Main.lean` printing `REJECT unimplemented`; `src/su2plaq/lean/` stubs (§5) raising `NotImplementedError`; `.gitignore`; `project.lake/build/print_axioms/no_sorry` implemented | `cd lean && lake build` exits 0 in ≤ 1800 s (Mathlib from cache: no Mathlib compilation!); `python -c "from su2plaq.lean import project; print(project.build()['ok'])"` → True; `pytest --collect-only -q tests/acceptance` clean; m2 Lean tests fail only `PENDING:` | `test_lean_formal.py::test_lean_project_present_and_builds_checker` |
| 2.L2 | `Evaluator.lean`, `Gauss.lean`, `Aer.lean`, `Synthesis.lean` (finish P1/P2/P4 prototypes; add `pruning_triangle`, `verdict_sound`, `synth_bound`) | all names in `GENERIC_THEOREMS` ∩ these files exist; axioms ⊆ standard; no `sorry` | `::test_lean_generic_theorems_standard_axioms` (partial: the test lists every name, so it turns green only after 2.L3; the tester checks the subset here) |
| 2.L3 | `Gates.lean` (finish P3b; `RCCX`, `crxW`, `ccrx`, `rccx_crx_rccx_eq_ccrx`, `h_z_h`, `h_rz_h`), vendored `Bits.lean`, `Peephole.lean`, `Rewrites.lean`, `Structure/Commute.lean`, `Structure/Counts.lean` (P6; `decide`; 433/256/95/2/17362 ≈ 1 min each; 3153/17 with `maxHeartbeats 0`, expected ≤ 30 min — if > 60 min, restructure the sum over the 256 outer spin patterns; `native_decide` is NOT acceptable here) | `lake build` green; `print_axioms(GENERIC_THEOREMS + COUNT_THEOREMS)` all ⊆ standard | `::test_lean_generic_theorems_standard_axioms`, `test_lean_structure.py::test_lean_counts_kernel_checked` |
| 2.L4 | `Su2PlaqCert/{K,Laurent,State,Gates,Circuit,Check,Json,Main}.lean` (computable, Mathlib-free; `precompileModules`); `exact.py` (`KNum`, `Laurent`, `rational_multiple`, exact basis/U/targets with float cross-checks); `certify.py` | `lake exe su2plaq_cert check` on the exported certificate of `build_UE(0.37, with_outer=True)` → ACCEPT in ≤ 120 s; a tampered one → REJECT; semantics test: exact output of a seeded 40-gate random SIM_BASIS circuit (angles $k\alpha/4$, $k\beta/2$) evaluated at the nominal angles agrees with `run_batch` to 1e-12 | `test_lean_formal.py::test_lean_checker_semantics_match_sparse_sim`, `::test_lean_certificate_small_accept_reject_na` |
| 2.L5 | certificate of the **general step circuit** (`compress/programs/twelve/seed/000-general.py` via `baselines.general_circuit`, with outer register) end to end; `write_theorem_file`; `lean/certs/twelve-general-step.lean` built with `lake env lean` | ACCEPT ≤ 900 s; theorem file elaborates, `#print axioms` = standard ∪ one `…native_decide.ax_…` | `::test_lean_certificate_general_circuit` (slow), `::test_lean_theorem_file_general` (slow) |
| 2.L6 | `structure.py` + `Su2PlaqCert/Structure.lean` (exact $H_B$ recomputation, block/J/gauge/$K_{\rm inner}$/spectrum/inner-625/symmetry checks); `compress/lean/structure.json`; `TaskSpec.render` section | `check_structure` ACCEPT ≤ 900 s; tampered coupling → REJECT; `symmetry_candidates` lists the commuting ones; spec text contains "Proved structure (Lean)" | `test_lean_structure.py::test_lean_structure_certificate_accept_reject` (slow), `::test_structure_json_and_spec_section`, `::test_symmetry_candidates_verified` |
| 2.L7 | loop integration: `rules.LEAN_RULES` + `passes.polish` log discipline; `lemmas.check_program_lemmas` + `ProgramResult.lean_lemmas`; `Entry.lean`; `run_round` certification of the best with the budget; `report_table` column | dry round under `tmp_path` with the general program: `Entry.lean.status == "certified"`, round wall ≤ 1200 s; a lemma file with `sorry` → `failed`, a valid one → `proved` | `test_lean_formal.py::test_polish_rules_are_lean_certified`, `::test_program_lemma_file_checked`, `::test_round_records_lean_certificate` (slow) |
| 2.L8 | M2 step 2.7 amendment: when the loop ends, certify the final best (status recorded; if `n_a` because of non-linear angles, report it — Digonto decides whether to require angle-linearity, §8) | gate test | `::test_archive_best_lean_status_recorded` (slow, runs with the existing gate test) |
| 2.L9 | METHODS §11 cross-check (planner wrote it; builder adds measured times), `graphify update .`, STATUS (coordinator) | — | — |

Builder brief must include: graphify-first rule; "copy the prototypes from `scratch/planner/lean/`, do not re-derive"; `export PATH=$HOME/.elan/bin:$PATH`; never `pip`/`elan` upgrades; the checker library must not import Mathlib; no `native_decide` outside `lean/certs/`; no `sorry` anywhere in `lean/`.

## 7. Acceptance tests added (locked with this plan) and their limits (why each number)
Files: `tests/acceptance/m2/test_lean_formal.py`, `tests/acceptance/m2/test_lean_structure.py`. Everything Lean checks is **exact**, so the only numbers are time limits and the float cross-check tolerances.

| Test id | Checks | Limit | Justification |
|---|---|---|---|
| `test_lean_project_present_and_builds_checker` | `lean/lean-toolchain` == `leanprover/lean4:v4.35.0`; lakefile pins Mathlib `v4.35.0`; `lake build Su2PlaqCert` ok | 600 s | Mathlib-free library, ≤ 10 files; measured plain-Lean elaboration of the prototype checker core 2.5 s; 600 s covers a cold `.lake` |
| `test_lean_generic_theorems_standard_axioms` | every name in the LOCKED list exists; axioms ⊆ `{propext, Classical.choice, Quot.sound}`; `no_sorry() == []` | 900 s | one `lake env lean` of the generated `AxiomCheck.lean` importing `Su2Plaq`: Mathlib import 5–10 s + the compiled oleans; 900 s allows a stale olean rebuild of a few files |
| `test_lean_counts_kernel_checked` | `COUNT_THEOREMS` exist; axioms ⊆ standard (a `decide` proof typically shows none) | 900 s | same mechanism |
| `test_lean_checker_semantics_match_sparse_sim` | seeded (20261104) 40-gate SIM_BASIS circuit on 6 qubits, angles $k\alpha/4$, $k\beta/2$; `checker_eval` vs `run_batch`: max abs diff ≤ 1e-12 | 1e-12; 300 s | exact arithmetic vs float64 over 40 gates (~1e-15); 300 s = JSON round trip + one `lake exe` |
| `test_lean_certificate_small_accept_reject_na` | `build_UE(0.37, with_outer=True)` → `certified`; same with `p(-3α/4)` replaced by `p(-α/2)` on one qubit → `rejected`; with `p(0.123)` → `n_a` starting `non_linear_angle` | 300 s total | 4-gate circuit, 433 inputs: milliseconds in the checker; 300 s absorbs process start-ups |
| `test_lean_certificate_general_circuit` (slow) | general step circuit → `certified`; `cert_path` exists with `schema == su2plaq-cert-1` | 900 s | research §1.2 estimate: $10^7$–$10^8$ exact operations compiled ≈ seconds–minutes; 900 s = 3× margin on the pessimistic end |
| `test_lean_theorem_file_general` (slow) | `lean/certs/twelve-general-step.lean` exists; `lake env lean` on it exits 0; `#print axioms` lists standard axioms plus exactly one native axiom | 1800 s | the Lean literal is ~1 MB (433 states × ≤17 terms × 8 rationals + ~1500 gates); elaboration of big literals is slow (estimate 1–10 min); builder records the time |
| `test_polish_rules_are_lean_certified` | `LEAN_RULES` non-empty; every rule name the polish log emits on the general circuit ∈ `LEAN_RULES`; the mapped theorems exist with standard axioms | 900 s | as above |
| `test_program_lemma_file_checked` | temp program copy + `.lean` with `theorem t : (2:ℕ)+2 = 4 := by decide` → `proved`, `axioms_ok`; with `sorry` → `failed`; without file → `none` | 120 s each | one Mathlib import per file (5–10 s measured) |
| `test_round_records_lean_certificate` (slow) | dry round 0 with the general program: `Entry.lean["status"] == "certified"`; `info["lean_seconds"] ≤ 1200` | 1200 s | §0 budget |
| `test_archive_best_lean_status_recorded` (slow) | real archive best has `lean` with status ∈ {certified, n_a}; if `n_a`, reason starts with `non_linear_angle` or `phase_not_in_K` | — | definition |
| `test_lean_structure_certificate_accept_reject` (slow) | `export_structure_certificate` → `check_structure` ACCEPT; copy with one $K_{\rm inner}$ coupling changed 2 → 1 → REJECT | 900 s each | exact $433\times433$ via ≤17-blocks: small; 900 s = margin for the exact basis build in sympy (first run, cached) |
| `test_structure_json_and_spec_section` | `structure.json` has the 7 count facts with `proved_by == "decide"` and values 433/256/95/2/17362/3153/17, the spectrum fact with `proved_by == "native"`; `spec.render()` contains "Proved structure (Lean)" and "433" | — | exact |
| `test_symmetry_candidates_verified` | 16 candidates returned; at least the identity and one non-trivial element commute with $H_B$ and $H_E$ (residual ≤ 1e-10); every commuting one is listed in the structure certificate | 1e-10 | float64 433×433 commutator of exact-valued matrices (~1e-14) |

Collection: both files import the project only through `tests/acceptance/_api.py::api`, and call `pytest.fail("PENDING: …")` when `lean/lakefile.toml` is missing. Checked: `pytest --collect-only -q tests/acceptance` collects (see the planner's return message for the count).

## 8. Decisions for Digonto (none blocks 2.L1–2.L4)
1. **Compiler-trust axiom.** Per-circuit and structure certificates are native-certified (one `…native_decide.ax_…` axiom per theorem, or the equivalent trust in the compiled checker). Alternative (no extra axiom): no per-circuit certificates at all — kernel `decide` is infeasible (research §1.1). Plan assumes "accepted"; the tests label the two levels separately.
2. **Angle-linearity of the final best.** If the loop's best circuit uses non-linear emission-time angles it cannot be Lean-certified (`n_a`). Require angle-linearity for the final best (and tell proposers so in the spec), or accept `n_a` with numerical verification only? Plan default: report `n_a`, do not reject.
3. **Proposer agent edits** (coordinator edits `~/.claude/agents/proposer.md`): add a paragraph "Lean": (a) `compress/lean/structure.json` and the spec section "Proved structure (Lean)" list exactly proved facts (dark labels, bright pairs, don't-care codes, outer-pattern support, symmetries) you may rely on; (b) you MAY add `NNN-<slug>.lean` next to your program (imports `Su2Plaq`/`Su2PlaqCert`/Mathlib only; checked by `cd lean && lake env lean <file>`, 120 s budget; informative, not part of validity); (c) rotation angles that are small rational multiples of α or β (denominator ≤ 64) make your circuit Lean-certifiable for all angles — prefer them; (d) validity is decided by `run_candidate` only. Guard hook: no change (`compress/programs/` already allowed; `.lean` files there are fine). The proposer's tool list already includes Bash (for `lake env lean`).

## 9. Do-not-retry
- Kernel `decide` for anything with `Rat`/`Float` or for whole-circuit checks (P5: stuck at `Rat.mul`; cost $\ge10^9$ steps).
- Brute-force `fin_cases` on 16×16 symbolic matrices (P3: timeout at 200 000 heartbeats) — use the `mono`/`ctrl`/`sandwich` formulation (P3b).
- `native_decide` inside `lean/Su2Plaq/` (generic theorems must be kernel-checked) or for the counts.
- Importing Mathlib into `Su2PlaqCert` (kills `precompileModules` build time and the Mathlib-free trust base).
- Building Mathlib from source (2–3 h): copy the sibling's `.lake/packages` or use `lake exe cache get`.
- Making Lean part of validity, or letting a certificate time-out block a round.
- Symbolic SU(2) recoupling / 6j theory or the spectral gap $\tfrac34$ in Mathlib (out of budget; keep as hypotheses, verify exactly).

## 10. Risks and stop conditions
- Builder cannot close a generic proof after 2 attempts → `fixer`; after a `fixer` NOT FIXED → planner (the statements may need weakening — allowed only through a planner prompt).
- `decide` for the 3153/17 counts exceeds 60 min even after restructuring → stop and ask (option: `native` label for those two, which changes `test_structure_json_and_spec_section`'s `proved_by` expectation — a planner change).
- Certificate of the general circuit REJECTs while the numerical verdict is `ok`: first suspect the exporter (angle recognition, base angles, phase fit, exact target); compare `checker_eval` with `run_batch` on the failing input. If the exact check still rejects with the semantics test green, **stop and ask Digonto** (exact vs float disagreement is a physics/implementation finding, never a tolerance question).
- Elaboration of the ~1 MB theorem file > 1800 s: fall back to the executable path only (theorem files become optional) — planner change to `test_lean_theorem_file_general`.
- Measured structure numbers differ from the coordinator's "41 bright pairs with couplings 1, ½, ¼" (research §2.2 measured 128 edges of modulus ½ on the 625 codes): the plan certifies what the exporter computes; report the discrepancy, do not hard-code.

## 11. Expected cost
Builder: 2.L1 ≈ 1 h (copying 6.7 GB cache ≈ 1–2 min); 2.L2 ≈ 2 h (prototypes exist); 2.L3 ≈ 3–4 h (Gates + vendoring + counts, build ≈ 10–40 min for the counts file once); 2.L4 ≈ 1 day (checker ≈ 400 lines Lean + exact.py ≈ 400 lines); 2.L5 ≈ 2 h; 2.L6 ≈ 1 day; 2.L7 ≈ 3 h; 2.L8 ≈ 1 h. Disk: `lean/.lake` ≈ 7 GB (gitignored). Runtime: `lake build` cold ≤ 15 min (plus the counts file), incremental seconds; m2 Lean fast tests ≈ 2–4 min; slow ones ≈ 10–30 min. Memory: Lean elaboration of Mathlib files ≈ 2–4 GB.

## 12. Fix recorded 2026-11-05 (approved by Digonto): tampering of circuits in locked m2 tests
Qiskit 2.5.2 stores standard gates natively and `CircuitInstruction.operation` returns a fresh object on every access, so the pattern `inst.operation.params[0] = …` is a silent no-op (verified: `Operator` of the "tampered" circuit equals the original). Affected locked tests, rewritten to rebuild the instruction (`op = inst.operation.copy(); op.params = [new]; qc.data[i] = CircuitInstruction(op, inst.qubits, inst.clbits)`) with an assertion that the new angle landed and the original is untouched; no assertion was changed or loosened:
- `tests/acceptance/m2/test_lean_formal.py::test_lean_certificate_small_accept_reject_na` (helper `_with_first_angle`; wrong multiple → `rejected`, `p(0.123)` → `n_a`, correct → `certified`).
- `tests/acceptance/m2/test_compress_machinery.py::_perturb_first_rotation` (used by `test_evaluator_rejects_angle_error`): previously compared the general circuit with itself and could only pass by accident of a different failure.
No other locked test (m0, m1, m2) uses the pattern (`grep -n "operation.params\[0\] =" tests/acceptance/m*/*.py`). Builder/tester note: never mutate `inst.operation` in place in Qiskit ≥ 2.
