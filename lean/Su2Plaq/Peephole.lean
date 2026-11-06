import Su2Plaq.Bits

/- VENDORED from the sibling project su2qc-skqd/2x4_compression_using_ai_v1/lean/Compress2x4/Peephole.lean
   (git commit 30f84af1 of su2qc-skqd; Mathlib tag v4.35.0).  Only change: namespace `Compress2x4` -> `Su2Plaq`
   (and the cross-references in the header).  Original header follows. -/
/-
Commutation rules of the peephole pass (src/c2x4/peephole.py), in the bit-vector model of Bits.lean
(genie-opus, phase 2, 2026-10-21).  Every statement holds for every register size n.

* `cx_comm_diagonal_of_indep` (R2): a diagonal gate whose phase does not depend on the target bit commutes
  with the CNOT.
* `cxFun_comm` / `cx_comm_cx` (R3): two CNOTs commute when neither one's control is the other's target.
* `cx_comm_flip_target` (R4): an X on the target commutes with the CNOT; hence so does every polynomial in
  that X, in particular Rx on the target (`cx_comm_lincomb_flip_target`).
* C1 (CX CX = 1) is `Su2Plaq.cx_involutive` (Bits.lean); R1 (disjoint supports) is
  `Su2Plaq.kron_disjoint_comm` (Structure/Commute.lean).
-/

open Matrix

namespace Su2Plaq

variable {n : ℕ}

theorem cxE_apply (c t : Fin n) (hct : c ≠ t) (s : Q n) : cxE c t hct s = cxFun c t s := rfl

theorem cxE_symm (c t : Fin n) (hct : c ≠ t) : (cxE c t hct).symm = cxE c t hct := rfl

/-- R2: a phase function that ignores the target bit is invariant under the CNOT relabelling. -/
theorem diag_cx_invariant (c t : Fin n) (d : Q n → ℂ)
    (hd : ∀ s : Q n, ∀ b : Bool, d (Function.update s t b) = d s) (s : Q n) :
    d (cxFun c t s) = d s := by
  have : cxFun c t s = Function.update s t (xor (s t) (s c)) := by
    funext i
    by_cases hi : i = t
    · subst hi; simp [cxFun]
    · simp [cxFun, hi, Function.update_of_ne hi]
  rw [this, hd]

theorem cx_comm_diagonal_of_indep (c t : Fin n) (hct : c ≠ t) (d : Q n → ℂ)
    (hd : ∀ s : Q n, ∀ b : Bool, d (Function.update s t b) = d s) :
    perm (cxE c t hct) * diagonal d = diagonal d * perm (cxE c t hct) := by
  have h := perm_conj_diagonal (cxE c t hct) d
  have hfun : d ∘ (cxE c t hct).symm = d := by
    funext s
    simp only [Function.comp_apply, cxE_symm, cxE_apply]
    exact diag_cx_invariant c t d hd s
  rw [hfun] at h
  calc perm (cxE c t hct) * diagonal d
      = perm (cxE c t hct) * diagonal d * (perm (cxE c t hct).symm * perm (cxE c t hct)) := by
        rw [perm_symm_mul, Matrix.mul_one]
    _ = (perm (cxE c t hct) * diagonal d * perm (cxE c t hct).symm) * perm (cxE c t hct) := by
        simp only [Matrix.mul_assoc]
    _ = diagonal d * perm (cxE c t hct) := by rw [h]

/-- R3 at the level of relabellings. -/
theorem cxFun_comm (c t c' t' : Fin n) (hct : c ≠ t) (hc't' : c' ≠ t') (h1 : c ≠ t') (h2 : c' ≠ t)
    (s : Q n) : cxFun c t (cxFun c' t' s) = cxFun c' t' (cxFun c t s) := by
  funext i
  by_cases hi : i = t <;> by_cases hi' : i = t'
  · subst hi; subst hi'
    simp only [cxFun, ite_true, hct, hc't', ite_false]
    cases s i <;> cases s c <;> cases s c' <;> rfl
  · subst hi
    simp [cxFun, hi', h2, hct, h1]
  · subst hi'
    simp [cxFun, hi, h1, hc't', h2]
  · simp [cxFun, hi, hi']

theorem cx_comm_cx (c t c' t' : Fin n) (hct : c ≠ t) (hc't' : c' ≠ t') (h1 : c ≠ t') (h2 : c' ≠ t) :
    perm (cxE c t hct) * perm (cxE c' t' hc't') = perm (cxE c' t' hc't') * perm (cxE c t hct) := by
  rw [perm_mul, perm_mul]
  congr 1
  ext s : 1
  simp only [Equiv.trans_apply, cxE_apply]
  exact cxFun_comm c t c' t' hct hc't' h1 h2 s

/-- The single-bit flip vector e_t. -/
def unitVec (t : Fin n) : Q n := fun i => decide (i = t)

/-- R4: X on the target commutes with the CNOT. -/
theorem cx_comm_flip_target (c t : Fin n) (hct : c ≠ t) :
    perm (cxE c t hct) * perm (flipE (unitVec t)) = perm (flipE (unitVec t)) * perm (cxE c t hct) := by
  rw [perm_mul, perm_mul]
  congr 1
  ext s i
  simp only [Equiv.trans_apply, cxE_apply, flipE, Equiv.coe_fn_mk, bxor, cxFun, unitVec]
  by_cases hi : i = t
  · subst hi; simp [hct]
  · simp [hi]

/-- Any linear combination a 1 + b X_t (in particular Rx(theta) on the target) commutes with the CNOT. -/
theorem cx_comm_lincomb_flip_target (c t : Fin n) (hct : c ≠ t) (a b : ℂ) :
    perm (cxE c t hct) * (a • (1 : Matrix (Q n) (Q n) ℂ) + b • perm (flipE (unitVec t))) =
      (a • (1 : Matrix (Q n) (Q n) ℂ) + b • perm (flipE (unitVec t))) * perm (cxE c t hct) := by
  rw [Matrix.mul_add, Matrix.add_mul, Matrix.mul_smul, Matrix.smul_mul, Matrix.mul_smul,
    Matrix.smul_mul, cx_comm_flip_target, Matrix.mul_one, Matrix.one_mul]

end Su2Plaq

