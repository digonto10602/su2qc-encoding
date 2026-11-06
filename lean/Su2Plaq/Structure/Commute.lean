import Mathlib

/-!
# Su2Plaq.Structure.Commute — disjoint-support commutation (docs/METHODS.md §11.1 h, §2)

`(A ⊗ 1)(1 ⊗ B) = (1 ⊗ B)(A ⊗ 1)`; in particular the outer electric term `1 ⊗ diag d` commutes with any operator
`W ⊗ 1` acting on the inner register, i.e. `[H_E^outer, H] = 0`.  Kernel-checked, standard axioms only.
-/
open Matrix
open scoped Kronecker

namespace Su2Plaq

variable {m n : Type*} [Fintype m] [Fintype n] [DecidableEq m] [DecidableEq n]

theorem kron_disjoint_comm (A : Matrix m m ℂ) (B : Matrix n n ℂ) :
    (A ⊗ₖ (1 : Matrix n n ℂ)) * ((1 : Matrix m m ℂ) ⊗ₖ B) = ((1 : Matrix m m ℂ) ⊗ₖ B) * (A ⊗ₖ (1 : Matrix n n ℂ)) := by
  rw [← Matrix.mul_kronecker_mul, ← Matrix.mul_kronecker_mul]
  simp

theorem outer_electric_commutes (W : Matrix m m ℂ) (d : n → ℂ) :
    (W ⊗ₖ (1 : Matrix n n ℂ)) * ((1 : Matrix m m ℂ) ⊗ₖ diagonal d) =
      ((1 : Matrix m m ℂ) ⊗ₖ diagonal d) * (W ⊗ₖ (1 : Matrix n n ℂ)) :=
  kron_disjoint_comm W (diagonal d)

end Su2Plaq
