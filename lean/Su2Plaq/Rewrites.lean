import Su2Plaq.Gates
import Su2Plaq.Peephole

/-!
# Su2Plaq.Rewrites — one theorem per peephole rewrite rule (docs/METHODS.md §11.4)

`su2plaq.lean.rules.LEAN_RULES` maps each rule name the `polish` pass may emit to the theorem proving it sound.
Initial rules (more are added with step 2.L7 when `polish` is built):

* `cancel_inverse_pairs`      — the inverse-pair table of `compress.passes.polish` (x x, z z, h h, s sdg, t tdg, cx cx, cz cz,
  swap swap, ccx ccx, ccz ccz, ch ch, rccx rccx): `Su2Plaq.cancel_inverse_pairs`
* `merge_adjacent_rotations`  — `Rz(a) Rz(b) = Rz(a+b)` and likewise `p`, `rx`, and the controlled versions `crz`, `crx`, `cp`:
  `Su2Plaq.merge_adjacent_rotations`
* (also used by the peephole documentation) `merge_rz`, `cx_involutive`, `cx_comm_diagonal_of_indep`, `cx_comm_cx`.

The matrices are over the gate's own qubits; multi-qubit identities hold in the bit model of `Bits.lean` or in the
control/target block form `ctrl` of `Gates.lean` (control = second tensor factor).
-/
namespace Su2Plaq
open Matrix

/-- `merge_rz`: consecutive `Rz` rotations on one qubit add their angles. -/
theorem merge_rz (a b : ℝ) : Rz a * Rz b = Rz (a + b) := by
  ext i j
  fin_cases i <;> fin_cases j <;> simp [Rz, Matrix.mul_apply, Fin.sum_univ_two] <;>
    rw [← Complex.exp_add] <;> congr 1 <;> ring


/-! ## single-qubit gates -/

noncomputable def Pg (l : ℝ) : Matrix (Fin 2) (Fin 2) ℂ := !![1, 0; 0, Complex.exp ((l : ℂ) * Complex.I)]
noncomputable def Sg : Matrix (Fin 2) (Fin 2) ℂ := Pg (Real.pi / 2)
noncomputable def Sdg : Matrix (Fin 2) (Fin 2) ℂ := Pg (-(Real.pi / 2))
noncomputable def Tg : Matrix (Fin 2) (Fin 2) ℂ := Pg (Real.pi / 4)
noncomputable def Tdg : Matrix (Fin 2) (Fin 2) ℂ := Pg (-(Real.pi / 4))

theorem Pg_mul (a b : ℝ) : Pg a * Pg b = Pg (a + b) := by
  ext i j
  fin_cases i <;> fin_cases j <;> simp [Pg, Matrix.mul_apply, Fin.sum_univ_two]
  rw [← Complex.exp_add]; congr 1; push_cast; ring

theorem Pg_zero : Pg 0 = 1 := by
  ext i j
  fin_cases i <;> fin_cases j <;> simp [Pg]

theorem Hd_mul_self : Hd * Hd = 1 := by
  have h := sqrt2_mul_inv'
  ext i j
  fin_cases i <;> fin_cases j <;> simp [Hd, Matrix.mul_apply, Fin.sum_univ_two, Matrix.vecHead, Matrix.vecTail] <;>
    linear_combination (2 : ℂ) * h

theorem Xm_mul_self : Xm * Xm = 1 := by
  ext i j
  fin_cases i <;> fin_cases j <;> simp [Xm, Matrix.mul_apply, Fin.sum_univ_two]

theorem Zm_mul_self : Zm * Zm = 1 := by
  ext i j
  fin_cases i <;> fin_cases j <;> simp [Zm, Matrix.mul_apply, Fin.sum_univ_two]

theorem Rx_merge (a b : ℝ) : Rx a * Rx b = Rx (a + b) := by
  rw [← h_rz_h a, ← h_rz_h b, ← h_rz_h (a + b), ← merge_rz a b]
  calc Hd * Rz a * Hd * (Hd * Rz b * Hd) = Hd * Rz a * (Hd * Hd) * Rz b * Hd := by simp only [Matrix.mul_assoc]
    _ = Hd * (Rz a * Rz b) * Hd := by rw [Hd_mul_self, Matrix.mul_one]; simp only [Matrix.mul_assoc]

/-! ## controlled gates in block form -/

section Controlled
variable {σ τ : Type*} [Fintype σ] [DecidableEq σ] [Fintype τ] [DecidableEq τ]

theorem ctrl_apply (W : τ → Matrix σ σ ℂ) (p q : σ × τ) :
    ctrl W p q = if p.2 = q.2 then W q.2 p.1 q.1 else 0 := rfl

/-- Block-diagonal families multiply blockwise. -/
theorem ctrl_mul (W V : τ → Matrix σ σ ℂ) : ctrl W * ctrl V = ctrl (fun h => W h * V h) := by
  ext ⟨x, h⟩ ⟨y, h'⟩
  simp only [Matrix.mul_apply, ctrl_apply, Fintype.sum_prod_type]
  by_cases hh : h = h'
  · subst hh
    simp [Matrix.mul_apply]
  · simp [hh]

theorem ctrl_one : ctrl (fun _ : τ => (1 : Matrix σ σ ℂ)) = 1 := by
  ext ⟨x, h⟩ ⟨y, h'⟩
  simp only [ctrl_apply, Matrix.one_apply, Prod.mk.injEq]
  by_cases hh : h = h' <;> by_cases hx : x = y <;> simp [hh, hx]

end Controlled

/-- Controlled rotation: the block of the control value `1` is `R θ`, the block of `0` is the identity. -/
noncomputable def ctrlRot {σ τ : Type*} [Fintype σ] [DecidableEq σ] [Fintype τ] [DecidableEq τ] (one : τ)
    (R : ℝ → Matrix σ σ ℂ) (θ : ℝ) : Matrix (σ × τ) (σ × τ) ℂ :=
  ctrl (fun h : τ => if h = one then R θ else 1)

theorem ctrlRot_merge {σ τ : Type*} [Fintype σ] [DecidableEq σ] [Fintype τ] [DecidableEq τ] (one : τ)
    (R : ℝ → Matrix σ σ ℂ) (hR : ∀ a b, R a * R b = R (a + b)) (a b : ℝ) :
    ctrlRot one R a * ctrlRot one R b = ctrlRot one R (a + b) := by
  unfold ctrlRot
  rw [ctrl_mul]
  congr 1
  funext h
  by_cases hh : h = one <;> simp [hh, hR]

/-- Controlled gate from a single-qubit gate `G` (control value 1). -/
noncomputable def cgate (G : Matrix (Fin 2) (Fin 2) ℂ) : Matrix (Fin 2 × Fin 2) (Fin 2 × Fin 2) ℂ :=
  ctrl (fun h : Fin 2 => if h = 1 then G else 1)

theorem cgate_mul_self_of (G : Matrix (Fin 2) (Fin 2) ℂ) (hG : G * G = 1) : cgate G * cgate G = 1 := by
  unfold cgate
  rw [ctrl_mul, ← ctrl_one]
  congr 1
  funext h
  by_cases hh : h = 1 <;> simp [hh, hG]

/-! ## the bit-model gates (swap, ccx, cz, ccz) -/

section BitModel
variable {n : ℕ}

theorem perm_sq (σ : Q n ≃ Q n) (h : ∀ s, σ (σ s) = s) : perm σ * perm σ = 1 := by
  rw [perm_mul]
  have : σ.trans σ = Equiv.refl _ := Equiv.ext h
  rw [this, perm_one]

def swapFun (a b : Fin n) (s : Q n) : Q n := fun i => if i = a then s b else if i = b then s a else s i

theorem swapFun_swapFun (a b : Fin n) (s : Q n) : swapFun a b (swapFun a b s) = s := by
  funext i
  by_cases ha : i = a <;> by_cases hb : i = b <;> simp [swapFun, ha, hb] <;> subst_vars <;> simp_all

def swapE (a b : Fin n) : Q n ≃ Q n where
  toFun := swapFun a b
  invFun := swapFun a b
  left_inv := swapFun_swapFun a b
  right_inv := swapFun_swapFun a b

def ccxFun (a b c : Fin n) (s : Q n) : Q n := fun i => if i = c then xor (s c) (s a && s b) else s i

theorem ccxFun_ccxFun (a b c : Fin n) (hac : a ≠ c) (hbc : b ≠ c) (s : Q n) :
    ccxFun a b c (ccxFun a b c s) = s := by
  funext i
  by_cases hi : i = c
  · subst hi; simp [ccxFun, hac, hbc]
  · simp [ccxFun, hi]

def ccxE (a b c : Fin n) (hac : a ≠ c) (hbc : b ≠ c) : Q n ≃ Q n where
  toFun := ccxFun a b c
  invFun := ccxFun a b c
  left_inv := ccxFun_ccxFun a b c hac hbc
  right_inv := ccxFun_ccxFun a b c hac hbc

/-- Diagonal sign gates: CZ and CCZ. -/
def czDiag (a b : Fin n) : Q n → ℂ := fun s => if s a && s b then -1 else 1
def cczDiag (a b c : Fin n) : Q n → ℂ := fun s => if s a && s b && s c then -1 else 1

theorem diag_sq_of (d : Q n → ℂ) (h : ∀ s, d s * d s = 1) : diagonal d * diagonal d = 1 := by
  rw [Matrix.diagonal_mul_diagonal]
  have : (fun s => d s * d s) = fun _ => (1 : ℂ) := funext h
  rw [this]; exact Matrix.diagonal_one

theorem cz_cz (a b : Fin n) : diagonal (czDiag a b) * diagonal (czDiag a b) = 1 :=
  diag_sq_of _ fun s => by unfold czDiag; split_ifs <;> norm_num

theorem ccz_ccz (a b c : Fin n) : diagonal (cczDiag a b c) * diagonal (cczDiag a b c) = 1 :=
  diag_sq_of _ fun s => by unfold cczDiag; split_ifs <;> norm_num

end BitModel

/-- The self-inverse part of the polish pass: every gate pair that `compress.passes.polish` cancels multiplies to the identity
(`x x`, `z z`, `h h`, `s sdg`, `sdg s`, `t tdg`, `tdg t`, `cx cx`, `cz cz`, `swap swap`, `ccx ccx`, `ccz ccz`, `ch ch`, `rccx rccx`). -/
theorem cancel_inverse_pairs :
    (Xm * Xm = 1 ∧ Zm * Zm = 1 ∧ Hd * Hd = 1 ∧ Sg * Sdg = 1 ∧ Sdg * Sg = 1 ∧ Tg * Tdg = 1 ∧ Tdg * Tg = 1)
    ∧ (∀ {n : ℕ} (c t : Fin n) (h : c ≠ t), perm (cxE c t h) * perm (cxE c t h) = 1)
    ∧ (∀ {n : ℕ} (a b : Fin n), diagonal (czDiag a b) * diagonal (czDiag a b) = 1)
    ∧ (∀ {n : ℕ} (a b : Fin n), perm (swapE a b) * perm (swapE a b) = 1)
    ∧ (∀ {n : ℕ} (a b c : Fin n) (hac : a ≠ c) (hbc : b ≠ c), perm (ccxE a b c hac hbc) * perm (ccxE a b c hac hbc) = 1)
    ∧ (∀ {n : ℕ} (a b c : Fin n), diagonal (cczDiag a b c) * diagonal (cczDiag a b c) = 1)
    ∧ cgate Hd * cgate Hd = 1
    ∧ RCCX * RCCX = 1 := by
  refine ⟨⟨Xm_mul_self, Zm_mul_self, Hd_mul_self, ?_, ?_, ?_, ?_⟩, fun c t h => cx_involutive c t h,
    fun a b => cz_cz a b, fun a b => perm_sq _ (swapFun_swapFun a b),
    fun a b c hac hbc => perm_sq _ (ccxFun_ccxFun a b c hac hbc), fun a b c => ccz_ccz a b c,
    cgate_mul_self_of _ Hd_mul_self, ?_⟩
  · simp only [Sg, Sdg, Pg_mul, add_neg_cancel, Pg_zero]
  · simp only [Sg, Sdg, Pg_mul, neg_add_cancel, Pg_zero]
  · simp only [Tg, Tdg, Pg_mul, add_neg_cancel, Pg_zero]
  · simp only [Tg, Tdg, Pg_mul, neg_add_cancel, Pg_zero]
  · have h := RCCX_unitary
    rwa [RCCX_isHermitian] at h

/-- The merge part of the polish pass: adjacent rotations of one kind on the same qubits add their angles
(`rz`, `p`, `rx`; controlled: `crz`, `crx`, `cp`). -/
theorem merge_adjacent_rotations :
    (∀ a b : ℝ, Rz a * Rz b = Rz (a + b)) ∧ (∀ a b : ℝ, Pg a * Pg b = Pg (a + b)) ∧ (∀ a b : ℝ, Rx a * Rx b = Rx (a + b))
    ∧ (∀ a b : ℝ, ctrlRot (1 : Fin 2) Rz a * ctrlRot (1 : Fin 2) Rz b = ctrlRot (1 : Fin 2) Rz (a + b))
    ∧ (∀ a b : ℝ, ctrlRot (1 : Fin 2) Rx a * ctrlRot (1 : Fin 2) Rx b = ctrlRot (1 : Fin 2) Rx (a + b))
    ∧ (∀ a b : ℝ, ctrlRot (1 : Fin 2) Pg a * ctrlRot (1 : Fin 2) Pg b = ctrlRot (1 : Fin 2) Pg (a + b)) :=
  ⟨merge_rz, Pg_mul, Rx_merge, ctrlRot_merge 1 Rz merge_rz, ctrlRot_merge 1 Rx Rx_merge, ctrlRot_merge 1 Pg Pg_mul⟩

end Su2Plaq
