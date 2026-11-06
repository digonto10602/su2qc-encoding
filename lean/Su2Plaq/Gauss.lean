import Mathlib

/-!
# Su2Plaq.Gauss — the Gauss-residual bound (docs/METHODS.md §11.1 d)

If `∑_{i<12} x_i² ≥ (3/4) t²` then some `x_i ≥ t/4`; hence `‖s‖ ≤ 4 · gauss_residual` **under the hypothesis**
`∑ ‖G_i s‖² ≥ (3/4) ‖s‖²` (the spectral gap `3/4` is SU(2) representation theory and is not formalised here).
Adapted from `scratch/planner/lean/P4_arith.lean`.  Kernel-checked, standard axioms only.
-/
namespace Su2Plaq

/-- `∑_{i<12} x_i² ≥ (3/4) t²` (`t ≥ 0`, `x_i ≥ 0`) implies some `x_i ≥ t/4`. -/
theorem gauss_max_ge (x : Fin 12 → ℝ) (t : ℝ) (_ht : 0 ≤ t) (hx : ∀ i, 0 ≤ x i)
    (h : (3/4 : ℝ) * t ^ 2 ≤ ∑ i, (x i) ^ 2) : ∃ i, t / 4 ≤ x i := by
  by_contra hcon
  push Not at hcon
  have hlt : ∑ i, (x i) ^ 2 < ∑ _i : Fin 12, (t / 4) ^ 2 := by
    apply Finset.sum_lt_sum_of_nonempty Finset.univ_nonempty
    intro i _
    exact pow_lt_pow_left₀ (hcon i) (hx i) (by norm_num)
  simp only [Finset.sum_const, Finset.card_univ, Fintype.card_fin, nsmul_eq_mul] at hlt
  nlinarith

/-- Span leak: `‖s‖ ≤ 4 · max_i ‖G_i s‖` given `∑ ‖G_i s‖² ≥ (3/4) ‖s‖²` over 12 generators. -/
theorem span_leak_le_four_gauss {E : Type*} [NormedAddCommGroup E] (G : Fin 12 → E → E) (s : E) (g : ℝ)
    (hg : ∀ i, ‖G i s‖ ≤ g) (hspec : (3/4 : ℝ) * ‖s‖ ^ 2 ≤ ∑ i, ‖G i s‖ ^ 2) : ‖s‖ ≤ 4 * g := by
  obtain ⟨i, hi⟩ := gauss_max_ge (fun i => ‖G i s‖) ‖s‖ (norm_nonneg _) (fun i => norm_nonneg _) hspec
  have := hg i
  linarith

end Su2Plaq
