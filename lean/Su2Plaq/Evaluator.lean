import Mathlib

/-!
# Su2Plaq.Evaluator — operator-norm bounds behind the compression evaluator (docs/METHODS.md §11.1 a-c)

Pythagoras for pairwise orthogonal vectors, the combined bound
`‖A+B+C‖ ≤ √(‖A‖²+‖B‖²+‖C‖²) ≤ ‖A‖+‖B‖+‖C‖`, the pruning triangle inequality, the block-diagonal
max rule and the evaluator's verdict inequality chain.  Kernel-checked, standard axioms only.
Adapted from the planner prototype `scratch/planner/lean/P2_blockdiag.lean` (Mathlib v4.35.0).
-/
namespace Su2Plaq
open scoped InnerProductSpace
variable {E F : Type*} [NormedAddCommGroup E] [InnerProductSpace ℂ E] [NormedAddCommGroup F] [InnerProductSpace ℂ F]

/-- Pythagoras for a finite family of pairwise orthogonal vectors. -/
theorem norm_add_sq_of_inner_eq_zero' (x y : F) (h : ⟪x, y⟫_ℂ = 0) : ‖x + y‖ ^ 2 = ‖x‖ ^ 2 + ‖y‖ ^ 2 := by
  rw [pow_two, pow_two, pow_two]; exact norm_add_sq_eq_norm_sq_add_norm_sq_of_inner_eq_zero x y h

theorem norm_sum_sq_of_pairwise_orth {ι : Type*} [DecidableEq ι] (s : Finset ι) (y : ι → F)
    (h : ∀ i ∈ s, ∀ j ∈ s, i ≠ j → ⟪y i, y j⟫_ℂ = 0) :
    ‖∑ i ∈ s, y i‖ ^ 2 = ∑ i ∈ s, ‖y i‖ ^ 2 := by
  induction s using Finset.induction_on with
  | empty => simp
  | insert a s ha ih =>
    rw [Finset.sum_insert ha, Finset.sum_insert ha]
    have horth : ⟪y a, ∑ i ∈ s, y i⟫_ℂ = 0 := by
      rw [inner_sum]
      apply Finset.sum_eq_zero
      intro i hi
      exact h a (Finset.mem_insert_self _ _) i (Finset.mem_insert_of_mem hi) (fun hai => ha (hai ▸ hi))
    rw [norm_add_sq_of_inner_eq_zero' _ _ horth]
    congr 1
    exact ih (fun i hi j hj hij => h i (Finset.mem_insert_of_mem hi) j (Finset.mem_insert_of_mem hj) hij)

/-- T1: three maps with mutually orthogonal ranges: ‖A+B+C‖ ≤ √(‖A‖²+‖B‖²+‖C‖²) ≤ ‖A‖+‖B‖+‖C‖. -/
theorem opNorm_add_three_le_of_orth (A B C : E →L[ℂ] F)
    (hAB : ∀ x y, ⟪A x, B y⟫_ℂ = 0) (hAC : ∀ x y, ⟪A x, C y⟫_ℂ = 0) (hBC : ∀ x y, ⟪B x, C y⟫_ℂ = 0) :
    ‖A + B + C‖ ≤ Real.sqrt (‖A‖ ^ 2 + ‖B‖ ^ 2 + ‖C‖ ^ 2) := by
  apply ContinuousLinearMap.opNorm_le_bound _ (Real.sqrt_nonneg _)
  intro x
  have h1 : ⟪A x + B x, C x⟫_ℂ = 0 := by rw [inner_add_left, hAC, hBC, add_zero]
  have hsq : ‖(A + B + C) x‖ ^ 2 = ‖A x‖ ^ 2 + ‖B x‖ ^ 2 + ‖C x‖ ^ 2 := by
    simp only [add_apply]
    rw [norm_add_sq_of_inner_eq_zero' _ _ h1, norm_add_sq_of_inner_eq_zero' _ _ (hAB x x)]
  have hb : ‖(A + B + C) x‖ ^ 2 ≤ (‖A‖ ^ 2 + ‖B‖ ^ 2 + ‖C‖ ^ 2) * ‖x‖ ^ 2 := by
    rw [hsq]
    have ha := A.le_opNorm x; have hb := B.le_opNorm x; have hc := C.le_opNorm x
    nlinarith [norm_nonneg (A x), norm_nonneg (B x), norm_nonneg (C x), norm_nonneg A, norm_nonneg B, norm_nonneg C, norm_nonneg x]
  calc ‖(A + B + C) x‖ = Real.sqrt (‖(A + B + C) x‖ ^ 2) := (Real.sqrt_sq (norm_nonneg _)).symm
    _ ≤ Real.sqrt ((‖A‖ ^ 2 + ‖B‖ ^ 2 + ‖C‖ ^ 2) * ‖x‖ ^ 2) := Real.sqrt_le_sqrt hb
    _ = Real.sqrt (‖A‖ ^ 2 + ‖B‖ ^ 2 + ‖C‖ ^ 2) * ‖x‖ := by
      rw [Real.sqrt_mul (by positivity), Real.sqrt_sq (norm_nonneg _)]

/-- T3: if E preserves an orthogonal decomposition {P_i} (E = Σ P_i E P_i) and each block has norm ≤ M,
    then ‖E‖ ≤ M. -/
theorem opNorm_le_of_blockdiag {ι : Type*} [Fintype ι] [DecidableEq ι] (P : ι → (E →L[ℂ] E)) (T : E →L[ℂ] E) (M : ℝ)
    (hM : 0 ≤ M)
    (hsum : ∀ x, ∑ i, P i x = x)
    (hidem : ∀ i x, P i (P i x) = P i x)
    (horth : ∀ i j, i ≠ j → ∀ x y, ⟪P i x, P j y⟫_ℂ = 0)
    (hblock : ∀ x, T x = ∑ i, P i (T (P i x)))
    (hbound : ∀ i, ‖(P i).comp (T.comp (P i))‖ ≤ M) : ‖T‖ ≤ M := by
  apply ContinuousLinearMap.opNorm_le_bound _ hM
  intro x
  have hx : ‖x‖ ^ 2 = ∑ i, ‖P i x‖ ^ 2 := by
    conv_lhs => rw [← hsum x]
    exact norm_sum_sq_of_pairwise_orth Finset.univ (fun i => P i x) (fun i _ j _ hij => horth i j hij x x)
  have hT : ‖T x‖ ^ 2 = ∑ i, ‖P i (T (P i x))‖ ^ 2 := by
    rw [hblock x]
    exact norm_sum_sq_of_pairwise_orth Finset.univ _ (fun i _ j _ hij => horth i j hij _ _)
  have hterm : ∀ i, ‖P i (T (P i x))‖ ^ 2 ≤ M ^ 2 * ‖P i x‖ ^ 2 := by
    intro i
    have h := ((P i).comp (T.comp (P i))).le_opNorm (P i x)
    simp only [ContinuousLinearMap.comp_apply, hidem] at h
    have h2 : ‖P i (T (P i x))‖ ≤ M * ‖P i x‖ :=
      h.trans (mul_le_mul_of_nonneg_right (hbound i) (norm_nonneg _))
    calc ‖P i (T (P i x))‖ ^ 2 ≤ (M * ‖P i x‖) ^ 2 := by gcongr
      _ = M ^ 2 * ‖P i x‖ ^ 2 := by ring
  have hsq : ‖T x‖ ^ 2 ≤ (M * ‖x‖) ^ 2 := by
    calc ‖T x‖ ^ 2 = ∑ i, ‖P i (T (P i x))‖ ^ 2 := hT
      _ ≤ ∑ i, M ^ 2 * ‖P i x‖ ^ 2 := Finset.sum_le_sum (fun i _ => hterm i)
      _ = M ^ 2 * ∑ i, ‖P i x‖ ^ 2 := by rw [Finset.mul_sum]
      _ = (M * ‖x‖) ^ 2 := by rw [← hx]; ring
  exact le_of_sq_le_sq (by simpa using hsq) (by positivity)


/-- Root-sum-square is at most the sum, for nonnegative reals. -/
theorem rss_le_sum (a b c : ℝ) (ha : 0 ≤ a) (hb : 0 ≤ b) (hc : 0 ≤ c) :
    Real.sqrt (a ^ 2 + b ^ 2 + c ^ 2) ≤ a + b + c := by
  rw [Real.sqrt_le_left (by positivity)]
  nlinarith [mul_nonneg ha hb, mul_nonneg ha hc, mul_nonneg hb hc]

section Verdict
/-- Pruning triangle inequality: replacing `U` by `U' = U + Ep` moves `‖(U - T) Φ‖` by at most `‖Ep‖` when `‖Φ‖ ≤ 1`. -/
theorem pruning_triangle (U U' Ep T : F →L[ℂ] F) (Φ : E →L[ℂ] F) (hU' : U' = U + Ep) (hΦ : ‖Φ‖ ≤ 1) :
    ‖(U - T).comp Φ‖ ≤ ‖(U' - T).comp Φ‖ + ‖Ep‖ := by
  have h1 : (U - T).comp Φ = (U' - T).comp Φ - Ep.comp Φ := by
    subst hU'
    ext x
    simp only [ContinuousLinearMap.comp_apply, sub_apply, add_apply]
    abel
  have h2 : ‖Ep.comp Φ‖ ≤ ‖Ep‖ := by
    calc ‖Ep.comp Φ‖ ≤ ‖Ep‖ * ‖Φ‖ := ContinuousLinearMap.opNorm_comp_le _ _
      _ ≤ ‖Ep‖ * 1 := mul_le_mul_of_nonneg_left hΦ (norm_nonneg _)
      _ = ‖Ep‖ := mul_one _
  calc ‖(U - T).comp Φ‖ = ‖(U' - T).comp Φ - Ep.comp Φ‖ := by rw [h1]
    _ ≤ ‖(U' - T).comp Φ‖ + ‖Ep.comp Φ‖ := norm_sub_le _ _
    _ ≤ ‖(U' - T).comp Φ‖ + ‖Ep‖ := by linarith

/-- Composing with an isometry on the left does not increase the operator norm. -/
theorem opNorm_isometry_comp_le (Φ : E →L[ℂ] F) (hΦ : ∀ x, ‖Φ x‖ = ‖x‖) {G : Type*} [NormedAddCommGroup G]
    [NormedSpace ℂ G] (B : G →L[ℂ] E) (b : ℝ) (hb : ‖B‖ ≤ b) : ‖Φ.comp B‖ ≤ b := by
  refine ContinuousLinearMap.opNorm_le_bound _ ((norm_nonneg _).trans hb) fun x => ?_
  rw [ContinuousLinearMap.comp_apply, hΦ]
  exact (B.le_opNorm x).trans (mul_le_mul_of_nonneg_right hb (norm_nonneg _))

/-- Verdict soundness: the evaluator's inequality chain.  If `(U + Ep) Φ = Φ A + S + X` with `Φ` an isometry,
`‖A - c V‖ ≤ b`, `‖Ep‖ ≤ d`, `‖X‖ ≤ l`, `‖S‖ ≤ s` then `‖U Φ - c Φ V‖ ≤ b + d + l + s`.
(The orthogonality hypotheses give the sharper root-sum-square bound, see `opNorm_add_three_le_of_orth`;
the sum bound used by the evaluator does not need them.) -/
theorem verdict_sound (Φ : E →L[ℂ] F) (hΦ : ∀ x, ‖Φ x‖ = ‖x‖) (U Ep : F →L[ℂ] F) (V A : E →L[ℂ] E)
    (S X : E →L[ℂ] F) (c : ℂ) (hc : ‖c‖ = 1)
    (hdec : (U + Ep).comp Φ = Φ.comp A + S + X)
    (_hΦS : ∀ x y, ⟪Φ x, S y⟫_ℂ = 0) (_hΦX : ∀ x y, ⟪Φ x, X y⟫_ℂ = 0) (_hSX : ∀ x y, ⟪S x, X y⟫_ℂ = 0)
    (b d l s : ℝ) (hb : ‖A - c • V‖ ≤ b) (hd : ‖Ep‖ ≤ d) (hl : ‖X‖ ≤ l) (hs : ‖S‖ ≤ s) :
    ‖U.comp Φ - c • Φ.comp V‖ ≤ b + d + l + s := by
  have _ := hc
  have hEp : ‖Ep.comp Φ‖ ≤ d := by
    calc ‖Ep.comp Φ‖ ≤ ‖Ep‖ * ‖Φ‖ := ContinuousLinearMap.opNorm_comp_le _ _
      _ ≤ ‖Ep‖ * 1 := mul_le_mul_of_nonneg_left (ContinuousLinearMap.opNorm_le_bound _ zero_le_one
          (fun x => by rw [hΦ, one_mul])) (norm_nonneg _)
      _ ≤ d := by rw [mul_one]; exact hd
  have hAV : ‖Φ.comp (A - c • V)‖ ≤ b := opNorm_isometry_comp_le Φ hΦ _ b hb
  have hsplit : U.comp Φ - c • Φ.comp V = Φ.comp (A - c • V) + S + X - Ep.comp Φ := by
    have h : U.comp Φ = (U + Ep).comp Φ - Ep.comp Φ := by ext x; simp
    rw [h, hdec]
    ext x
    simp
    abel
  rw [hsplit]
  calc ‖Φ.comp (A - c • V) + S + X - Ep.comp Φ‖
      ≤ ‖Φ.comp (A - c • V) + S + X‖ + ‖Ep.comp Φ‖ := norm_sub_le _ _
    _ ≤ (‖Φ.comp (A - c • V)‖ + ‖S‖ + ‖X‖) + ‖Ep.comp Φ‖ := by
        gcongr; exact norm_add₃_le
    _ ≤ b + d + l + s := by linarith
end Verdict

end Su2Plaq
