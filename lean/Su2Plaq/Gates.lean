import Mathlib

/-!
# Su2Plaq.Gates — gate semantics and the clean-ancilla sandwich lemma (docs/METHODS.md §11.1 g)

* `mono π φ`: monomial matrix `e q ↦ φ q • e (π q)` (unitary for `‖φ‖ = 1`), `ctrl W`: ancilla-controlled family
  `∑_h |h⟩⟨h| ⊗ W h`.
* `sandwich`: for unitary `C` with `C e(x,z) = φ x • e(x, f x)` and middle blocks `W h` that change neither `f` nor `φ`,
  `Cᴴ (ctrl W) C e(x,z) = ∑_y (W (f x))_{yx} e(y,z)` (compute / use / uncompute with a clean ancilla).
* `rccx_crx_rccx_eq_ccrx`: Qiskit's relative-phase Toffoli `RCCX` (controls a,b, target = ancilla h) around a controlled-`Rx`
  from `h` onto `t` equals the doubly controlled `Rx` on the clean-ancilla subspace `h = 0`.
* `h_z_h`, `h_rz_h`: `H Z H = X`, `H Rz(θ) H = Rx(θ)`.
Adapted from `scratch/planner/lean/P3b_sandwich.lean` (sandwich formulation; brute-force 16x16 `fin_cases` is a dead end).
Kernel-checked, standard axioms only.
-/
namespace Su2Plaq
open Matrix
section Generic
variable {σ τ : Type*} [Fintype σ] [DecidableEq σ] [Fintype τ] [DecidableEq τ]

/-- Computational basis vector of the (register, ancilla) label p. -/
noncomputable def e (p : σ × τ) : σ × τ → ℂ := Pi.single p 1

/-- Ancilla-controlled family: G = Σ_h |h⟩⟨h| ⊗ W h (block-diagonal in the ancilla value). -/
noncomputable def ctrl (W : τ → Matrix σ σ ℂ) : Matrix (σ × τ) (σ × τ) ℂ :=
  Matrix.of fun p q => if p.2 = q.2 then W q.2 p.1 q.1 else 0

theorem ctrl_mulVec_e (W : τ → Matrix σ σ ℂ) (x : σ) (h : τ) :
    (ctrl W) *ᵥ e (x, h) = ∑ y, W h y x • e (y, h) := by
  ext ⟨y', h'⟩
  simp only [e, Matrix.mulVec_single, ctrl, Matrix.of_apply, mul_one, Finset.sum_apply, Pi.smul_apply,
    Pi.single_apply, Prod.mk.injEq, smul_eq_mul]
  by_cases hh : h' = h
  · subst hh
    simp [Finset.sum_ite_eq']
  · simp [hh]

/-- Generic sandwich: if the unitary C maps |x, z⟩ ↦ φ x |x, f x⟩, and the middle gate is block-diagonal in the
ancilla with blocks W h that neither change f nor φ, then Cᴴ (Σ_h |h⟩⟨h| ⊗ W h) C acts on |x, z⟩ as W (f x) with the
ancilla returned to z. -/
theorem sandwich (C : Matrix (σ × τ) (σ × τ) ℂ) (hC : Cᴴ * C = 1)
    (z : τ) (f : σ → τ) (φ : σ → ℂ) (hφ : ∀ x, φ x ≠ 0)
    (hcomp : ∀ x, C *ᵥ e (x, z) = φ x • e (x, f x))
    (W : τ → Matrix σ σ ℂ)
    (hWf : ∀ h x y, W h y x ≠ 0 → f y = f x)
    (hWφ : ∀ h x y, W h y x ≠ 0 → φ y = φ x) (x : σ) :
    (Cᴴ * ctrl W * C) *ᵥ e (x, z) = ∑ y, W (f x) y x • e (y, z) := by
  have hCH : ∀ y, Cᴴ *ᵥ e (y, f y) = (φ y)⁻¹ • e (y, z) := by
    intro y
    have h1 : Cᴴ *ᵥ (C *ᵥ e (y, z)) = e (y, z) := by rw [Matrix.mulVec_mulVec, hC, Matrix.one_mulVec]
    rw [hcomp, Matrix.mulVec_smul] at h1
    calc Cᴴ *ᵥ e (y, f y) = (φ y)⁻¹ • (φ y • (Cᴴ *ᵥ e (y, f y))) := by
          rw [smul_smul, inv_mul_cancel₀ (hφ y), one_smul]
      _ = (φ y)⁻¹ • e (y, z) := by rw [h1]
  rw [← Matrix.mulVec_mulVec, ← Matrix.mulVec_mulVec, hcomp, Matrix.mulVec_smul, ctrl_mulVec_e,
    Matrix.mulVec_smul, Matrix.mulVec_sum, Finset.smul_sum]
  apply Finset.sum_congr rfl
  intro y _
  rw [Matrix.mulVec_smul]
  by_cases hW : W (f x) y x = 0
  · simp [hW]
  · have hf := hWf _ _ _ hW
    have hp := hWφ _ _ _ hW
    rw [show e (y, f x) = e (y, f y) by rw [hf], hCH y, hp, smul_smul, smul_smul]
    congr 1
    field_simp [hφ x]

/-- Monomial (permutation-with-phase) matrix: e q ↦ φ q • e (π q). -/
noncomputable def mono (π : (σ × τ) ≃ (σ × τ)) (φ : σ × τ → ℂ) : Matrix (σ × τ) (σ × τ) ℂ :=
  Matrix.of fun p q => if p = π q then φ q else 0

theorem mono_mulVec_e (π : (σ × τ) ≃ (σ × τ)) (φ : σ × τ → ℂ) (q : σ × τ) :
    mono π φ *ᵥ e q = φ q • e (π q) := by
  ext p
  simp [mono, e, Matrix.mulVec_single, Pi.single_apply]

theorem mono_conjTranspose_mul (π : (σ × τ) ≃ (σ × τ)) (φ : σ × τ → ℂ) (hφ : ∀ q, ‖φ q‖ = 1) :
    (mono π φ)ᴴ * mono π φ = 1 := by
  ext p q
  simp only [Matrix.mul_apply, Matrix.conjTranspose_apply, mono, Matrix.of_apply, Matrix.one_apply]
  have hsum : ∀ r, (star (if r = π p then φ p else 0)) * (if r = π q then φ q else 0)
      = if r = π p ∧ p = q then star (φ p) * φ p else 0 := by
    intro r
    by_cases h1 : r = π p <;> by_cases h2 : r = π q <;> by_cases h3 : p = q <;> simp_all
  simp_rw [hsum]
  rw [Finset.sum_ite, Finset.sum_const_zero, add_zero]
  by_cases h3 : p = q
  · subst h3
    simp only [and_true]
    rw [Finset.filter_eq' Finset.univ (π p)]
    simp only [Finset.mem_univ, ite_true, Finset.sum_singleton]
    have := hφ p
    rw [Complex.star_def, Complex.conj_mul', this]
    simp
  · simp [h3]


/-- A monomial matrix whose permutation is an involution and whose phases satisfy `φ (π q) = conj (φ q)` is Hermitian. -/
theorem mono_isHermitian (π : (σ × τ) ≃ (σ × τ)) (φ : σ × τ → ℂ) (hπ : π.symm = π)
    (hφ : ∀ q, φ (π q) = star (φ q)) : (mono π φ)ᴴ = mono π φ := by
  have hππ : ∀ q, π (π q) = q := fun q => by
    have := π.apply_symm_apply q
    rwa [hπ] at this
  ext p q
  simp only [Matrix.conjTranspose_apply, mono, Matrix.of_apply]
  by_cases h : q = π p
  · subst h
    have h' : p = π (π p) := (hππ p).symm
    simp only [eq_self_iff_true, ite_true, ← h', hφ, star_star]
  · have h' : ¬ p = π q := fun h' => h (by rw [h', hππ])
    simp only [h, h', ite_false, star_zero]

end Generic

/-! ## Single-qubit matrices -/
section OneQubit

/-- Hadamard. -/
noncomputable def Hd : Matrix (Fin 2) (Fin 2) ℂ := ((Real.sqrt 2 : ℝ) : ℂ)⁻¹ • !![1, 1; 1, -1]
def Zm : Matrix (Fin 2) (Fin 2) ℂ := !![1, 0; 0, -1]
def Xm : Matrix (Fin 2) (Fin 2) ℂ := !![0, 1; 1, 0]
/-- `Rz(θ) = diag(e^{-iθ/2}, e^{iθ/2})`. -/
noncomputable def Rz (θ : ℝ) : Matrix (Fin 2) (Fin 2) ℂ :=
  !![Complex.exp (((-(θ / 2) : ℝ) : ℂ) * Complex.I), 0; 0, Complex.exp (((θ / 2 : ℝ) : ℂ) * Complex.I)]
/-- `Rx(θ) = exp(-iθX/2)`. -/
noncomputable def Rx (θ : ℝ) : Matrix (Fin 2) (Fin 2) ℂ :=
  !![(Real.cos (θ / 2) : ℂ), -Complex.I * Real.sin (θ / 2); -Complex.I * Real.sin (θ / 2), (Real.cos (θ / 2) : ℂ)]

theorem sqrt2_mul_inv' : ((Real.sqrt 2 : ℝ) : ℂ)⁻¹ * ((Real.sqrt 2 : ℝ) : ℂ)⁻¹ = 1 / 2 := by
  have h : ((Real.sqrt 2 : ℝ) : ℂ) * ((Real.sqrt 2 : ℝ) : ℂ) = 2 := by
    rw [← Complex.ofReal_mul, Real.mul_self_sqrt (by norm_num)]; norm_num
  rw [← mul_inv, h, one_div]

theorem h_z_h : Hd * Zm * Hd = Xm := by
  have h := sqrt2_mul_inv'
  ext i j
  fin_cases i <;> fin_cases j <;>
    simp [Hd, Zm, Xm, Matrix.mul_apply, Fin.sum_univ_two, Matrix.vecHead, Matrix.vecTail] <;>
    linear_combination (2 : ℂ) * h

theorem h_rz_h (θ : ℝ) : Hd * Rz θ * Hd = Rx θ := by
  have h := sqrt2_mul_inv'
  have e1 : Complex.exp (((-(θ / 2) : ℝ) : ℂ) * Complex.I) = Real.cos (θ / 2) - Real.sin (θ / 2) * Complex.I := by
    rw [Complex.exp_mul_I, ← Complex.ofReal_cos, ← Complex.ofReal_sin, Real.cos_neg, Real.sin_neg]
    push_cast; ring
  have e2 : Complex.exp (((θ / 2 : ℝ) : ℂ) * Complex.I) = Real.cos (θ / 2) + Real.sin (θ / 2) * Complex.I := by
    rw [Complex.exp_mul_I, ← Complex.ofReal_cos, ← Complex.ofReal_sin]
  have hRz : Rz θ = !![(Real.cos (θ / 2) : ℂ) - Real.sin (θ / 2) * Complex.I, 0;
      0, (Real.cos (θ / 2) : ℂ) + Real.sin (θ / 2) * Complex.I] := by
    unfold Rz; rw [e1, e2]
  rw [hRz]
  unfold Rx
  generalize (Real.cos (θ / 2) : ℂ) = c
  generalize (Real.sin (θ / 2) : ℂ) = s
  ext i j
  fin_cases i <;> fin_cases j <;>
    simp [Hd, Matrix.mul_apply, Fin.sum_univ_two, Matrix.vecHead, Matrix.vecTail] <;>
    first
    | linear_combination (2 * c) * h
    | linear_combination (-2 * s * Complex.I) * h
    | linear_combination (2 * s * Complex.I) * h
end OneQubit

/-! ## RCCX · CRX · RCCX = CCRX on the clean-ancilla subspace -/
section Rccx

/-- Data register `(a, b, t)`; the ancilla `h` is the second component of a basis label `(x, h)`. -/
abbrev Reg := Fin 2 × Fin 2 × Fin 2

/-- RCCX permutation: with controls `a = b = 1` the ancilla `h` flips (`h + a * b` in `Fin 2`). -/
def rccxFun (p : Reg × Fin 2) : Reg × Fin 2 := (p.1, p.2 + p.1.1 * p.1.2.1)

def rccxPerm : (Reg × Fin 2) ≃ (Reg × Fin 2) where
  toFun := rccxFun
  invFun := rccxFun
  left_inv := by intro p; revert p; decide
  right_inv := by intro p; revert p; decide

/-- RCCX phases, read off Qiskit's `RCCXGate().to_matrix()` (qubits `a, b, h`, little-endian index `a + 2b + 4h`):
controls set: `h : 0 → 1` with phase `i`, `h : 1 → 0` with phase `-i`; `|a=1, b=0, h=1⟩ ↦ -|·⟩`; otherwise `1`. -/
noncomputable def rccxPhase (p : Reg × Fin 2) : ℂ :=
  if p.1.1 = 1 ∧ p.1.2.1 = 1 then (if p.2 = 0 then Complex.I else -Complex.I)
  else if p.1.1 = 1 ∧ p.1.2.1 = 0 ∧ p.2 = 1 then -1 else 1

/-- Qiskit's relative-phase Toffoli on `(a, b; h)`, identity on `t`. -/
noncomputable def RCCX : Matrix (Reg × Fin 2) (Reg × Fin 2) ℂ := mono rccxPerm rccxPhase

/-- Controlled `Rx(θ)` with control `h`, target `t`, as ancilla-indexed blocks acting on `(a, b, t)`. -/
noncomputable def crxW (θ : ℝ) (h : Fin 2) : Matrix Reg Reg ℂ :=
  Matrix.of fun y x =>
    if h = 0 then (if y = x then 1 else 0)
    else if y.1 = x.1 ∧ y.2.1 = x.2.1 then Rx θ y.2.2 x.2.2 else 0

/-- Doubly controlled `Rx(θ)` (controls `a, b`, target `t`). -/
noncomputable def ccrx (θ : ℝ) : Matrix Reg Reg ℂ :=
  Matrix.of fun y x =>
    if x.1 = 1 ∧ x.2.1 = 1 then (if y.1 = x.1 ∧ y.2.1 = x.2.1 then Rx θ y.2.2 x.2.2 else 0)
    else if y = x then 1 else 0

theorem rccxPhase_norm (q : Reg × Fin 2) : ‖rccxPhase q‖ = 1 := by
  obtain ⟨⟨a, b, t⟩, h⟩ := q
  fin_cases a <;> fin_cases b <;> fin_cases h <;> simp [rccxPhase]

theorem RCCX_isHermitian : RCCXᴴ = RCCX := by
  apply mono_isHermitian rccxPerm rccxPhase rfl
  intro q
  obtain ⟨⟨a, b, t⟩, h⟩ := q
  fin_cases a <;> fin_cases b <;> fin_cases h <;> simp [rccxPhase, rccxPerm, rccxFun]

theorem RCCX_unitary : RCCXᴴ * RCCX = 1 := mono_conjTranspose_mul _ _ rccxPhase_norm

/-- `RCCX · CRX(h → t) · RCCX = CCRX(a, b → t)` on the clean-ancilla subspace `h = 0` (via the sandwich lemma). -/
theorem rccx_crx_rccx_eq_ccrx (θ : ℝ) (x : Fin 2 × Fin 2 × Fin 2) :
    (RCCX * ctrl (crxW θ) * RCCX) *ᵥ e (x, 0) = ∑ y, (ccrx θ) y x • e (y, 0) := by
  have hsupp : ∀ h y x, crxW θ h y x ≠ 0 → (y.1 = x.1 ∧ y.2.1 = x.2.1) := by
    intro h y x hne
    unfold crxW at hne
    simp only [Matrix.of_apply] at hne
    by_cases h0 : h = 0
    · rw [if_pos h0] at hne
      by_cases hyx : y = x
      · subst hyx; exact ⟨rfl, rfl⟩
      · rw [if_neg hyx] at hne; exact absurd rfl hne
    · rw [if_neg h0] at hne
      by_cases hc : y.1 = x.1 ∧ y.2.1 = x.2.1
      · exact hc
      · rw [if_neg hc] at hne; exact absurd rfl hne
  have hcomp : ∀ x : Reg, RCCX *ᵥ e (x, 0) = rccxPhase (x, 0) • e (x, x.1 * x.2.1) := by
    intro x
    rw [RCCX, mono_mulVec_e]
    simp [rccxPerm, rccxFun]
  have hnz : ∀ x : Reg, rccxPhase (x, 0) ≠ 0 := by
    intro x
    have := rccxPhase_norm (x, 0)
    intro h0; rw [h0] at this; simp at this
  have key := sandwich RCCX RCCX_unitary 0 (fun x : Reg => x.1 * x.2.1)
    (fun x => rccxPhase (x, 0)) hnz hcomp (crxW θ)
    (fun h x y hne => by
      obtain ⟨h1, h2⟩ := hsupp h y x hne
      simp [h1, h2])
    (fun h x y hne => by
      obtain ⟨h1, h2⟩ := hsupp h y x hne
      simp [rccxPhase, h1, h2]) x
  rw [RCCX_isHermitian] at key
  rw [key]
  refine Finset.sum_congr rfl fun y _ => ?_
  congr 1
  obtain ⟨a, b, t⟩ := x
  obtain ⟨a', b', t'⟩ := y
  fin_cases a <;> fin_cases b <;> simp [crxW, ccrx]
end Rccx
end Su2Plaq
