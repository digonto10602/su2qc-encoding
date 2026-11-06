import Su2Plaq.Gates
import Su2Plaq.Peephole

/-!
# Su2Plaq.Rewrites — one theorem per peephole rewrite rule (docs/METHODS.md §11.4)

`su2plaq.lean.rules.LEAN_RULES` maps each rule name the `polish` pass may emit to the theorem proving it sound.
Initial rules (more are added with step 2.L7 when `polish` is built):

* `cancel_cx_pair`  — `CX · CX = 1`                                   (`Su2Plaq.cx_involutive`)
* `merge_rz`        — `Rz(a) · Rz(b) = Rz(a + b)`                      (`Su2Plaq.merge_rz`)
* `commute_diag_cx` — a diagonal gate ignoring the CX target commutes with the CX (`Su2Plaq.cx_comm_diagonal_of_indep`)
* `commute_cx_cx`   — CNOTs whose control is not the other's target commute (`Su2Plaq.cx_comm_cx`)
-/
namespace Su2Plaq
open Matrix

/-- `merge_rz`: consecutive `Rz` rotations on one qubit add their angles. -/
theorem merge_rz (a b : ℝ) : Rz a * Rz b = Rz (a + b) := by
  ext i j
  fin_cases i <;> fin_cases j <;> simp [Rz, Matrix.mul_apply, Fin.sum_univ_two] <;>
    rw [← Complex.exp_add] <;> congr 1 <;> ring

end Su2Plaq
