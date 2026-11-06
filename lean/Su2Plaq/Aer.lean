import Mathlib

/-!
# Su2Plaq.Aer — Cauchy–Schwarz block bound (docs/METHODS.md §11.1 e)

`‖∑ a_i x_i‖ ≤ ‖a‖₂ · √(∑ ‖x_i‖²)`, the bound used for the `aer_mps` check.
Adapted from `scratch/planner/lean/P4_arith.lean`.  Kernel-checked, standard axioms only.
-/
namespace Su2Plaq

theorem cs_block_bound {E : Type*} [NormedAddCommGroup E] [NormedSpace ℂ E] {ι : Type*} (s : Finset ι)
    (a : ι → ℂ) (x : ι → E) :
    ‖∑ i ∈ s, a i • x i‖ ≤ Real.sqrt (∑ i ∈ s, ‖a i‖ ^ 2) * Real.sqrt (∑ i ∈ s, ‖x i‖ ^ 2) := by
  calc ‖∑ i ∈ s, a i • x i‖ ≤ ∑ i ∈ s, ‖a i • x i‖ := norm_sum_le _ _
    _ = ∑ i ∈ s, ‖a i‖ * ‖x i‖ := by simp [norm_smul]
    _ ≤ _ := Real.sum_mul_le_sqrt_mul_sqrt s _ _

end Su2Plaq
