import Mathlib

/- VENDORED from the sibling project su2qc-skqd/2x4_compression_using_ai_v1/lean/Compress2x4/Bits.lean
   (git commit 30f84af1 of su2qc-skqd; Mathlib tag v4.35.0).  Only change: namespace `Compress2x4` -> `Su2Plaq`
   (and the cross-references in the header).  Original header follows. -/
/-
The computational-basis ("bit-vector") model of the gadgets used by the CF1/CF2 constructions
(genie-opus, phase 2, 2026-10-21).

An n-qubit basis label is `s : Fin n → Bool` (bit i = qubit i, the package's little-endian convention is a
relabelling of the same set).  X-type gates (X, CX, CNOT networks) act by permutations of the labels;
Z-type gates (Z, CZ, controlled phases, Rz on basis states) act by diagonal phases.

Proved here, for every n:
* `perm_mul`, `perm_one`: permutation matrices compose like the permutations.
* `perm_conj_diagonal`: P_sigma diag(d) P_sigma^-1 = diag(d o sigma^-1)  (moving a phase through a CNOT network).
* `xorLinear_conj_flip`: for an xor-linear relabelling L (any CNOT network),
  P_L X_v P_L^-1 = X_{L v}.  With L the corner CX(p_a -> p_b) and the ladder CX(p_1 -> p_c) this is the
  statement that the plaquette's simultaneous flip of eight link bits becomes the flip of one qubit.
* `cx_xorLinear`, `cx_involutive`: a CNOT is xor-linear and its own inverse (CX CX = 1).
* `ccz_phase`: pi/2 (b c - (a xor b) c + a c) = pi a b c on bits -- the identity behind the 3 CP + 2 CX
  doubly-controlled Z used for sign corrections (`ccz` in src/c2x4/plaqfactor.py), and `ccz_circuit`, the
  same statement for the diagonal operators of the circuit.
-/

open Matrix

namespace Su2Plaq

/-- Basis labels of an n-qubit register. -/
abbrev Q (n : ℕ) := Fin n → Bool

/-- Bitwise xor of two labels. -/
def bxor {n : ℕ} (s t : Q n) : Q n := fun i => xor (s i) (t i)

/-- The flip of the bits in `v` (the X-string X_v) as a permutation of the labels. -/
def flipE {n : ℕ} (v : Q n) : Q n ≃ Q n where
  toFun s := bxor s v
  invFun s := bxor s v
  left_inv s := by funext i; simp [bxor]
  right_inv s := by funext i; simp [bxor]

/-- Permutation matrix: `perm σ` sends the basis vector of `j` to the basis vector of `σ j`. -/
noncomputable def perm {n : ℕ} (σ : Q n ≃ Q n) : Matrix (Q n) (Q n) ℂ :=
  Matrix.of fun i j => if i = σ j then 1 else 0

theorem perm_apply {n : ℕ} (σ : Q n ≃ Q n) (i j : Q n) :
    perm σ i j = if i = σ j then 1 else 0 := rfl

theorem mul_perm_apply {n : ℕ} (M : Matrix (Q n) (Q n) ℂ) (τ : Q n ≃ Q n) (i j : Q n) :
    (M * perm τ) i j = M i (τ j) := by
  simp only [Matrix.mul_apply, perm_apply]
  rw [Finset.sum_eq_single (τ j)]
  · simp
  · intro b _ hb
    simp [hb]
  · intro h
    exact absurd (Finset.mem_univ _) h

theorem perm_mul {n : ℕ} (σ τ : Q n ≃ Q n) : perm σ * perm τ = perm (τ.trans σ) := by
  ext i j
  rw [mul_perm_apply]
  simp only [perm_apply, Equiv.trans_apply]
  by_cases h : i = σ (τ j) <;> simp [h]

theorem perm_one {n : ℕ} : perm (Equiv.refl (Q n)) = 1 := by
  ext i j
  simp only [perm_apply, Equiv.refl_apply, Matrix.one_apply]
  by_cases h : i = j <;> simp [h]

theorem perm_mul_symm {n : ℕ} (σ : Q n ≃ Q n) : perm σ * perm σ.symm = 1 := by
  rw [perm_mul]
  simp [perm_one]

theorem perm_symm_mul {n : ℕ} (σ : Q n ≃ Q n) : perm σ.symm * perm σ = 1 := by
  rw [perm_mul]
  simp [perm_one]

/-- Moving a diagonal (phase) operator through a permutation (a CNOT network). -/
theorem perm_conj_diagonal {n : ℕ} (σ : Q n ≃ Q n) (d : Q n → ℂ) :
    perm σ * diagonal d * perm σ.symm = diagonal (d ∘ σ.symm) := by
  ext i j
  rw [mul_perm_apply, Matrix.mul_diagonal, perm_apply, Matrix.diagonal_apply, Function.comp_apply,
    Equiv.apply_symm_apply]
  by_cases h : i = j
  · subst h; simp
  · simp [h]

/-- A relabelling is xor-linear if it respects bitwise xor (true for any CNOT network). -/
def XorLinear {n : ℕ} (L : Q n ≃ Q n) : Prop := ∀ s t : Q n, L (bxor s t) = bxor (L s) (L t)

theorem xorLinear_trans {n : ℕ} {L M : Q n ≃ Q n} (hL : XorLinear L) (hM : XorLinear M) :
    XorLinear (L.trans M) := by
  intro s t
  simp [hL s t, hM (L s) (L t)]

/-- Conjugating an X-string by a CNOT network gives the X-string of the transformed flip vector. -/
theorem xorLinear_conj_flip {n : ℕ} (L : Q n ≃ Q n) (hL : XorLinear L) (v : Q n) :
    perm L * perm (flipE v) * perm L.symm = perm (flipE (L v)) := by
  rw [perm_mul, perm_mul]
  congr 1
  ext s : 1
  simp only [Equiv.trans_apply]
  change L (bxor (L.symm s) v) = bxor s (L v)
  rw [hL, Equiv.apply_symm_apply]

/-- The CNOT with control c and target t, as a relabelling. -/
def cxFun {n : ℕ} (c t : Fin n) (s : Q n) : Q n := fun i => if i = t then xor (s t) (s c) else s i

theorem cxFun_cxFun {n : ℕ} (c t : Fin n) (hct : c ≠ t) (s : Q n) : cxFun c t (cxFun c t s) = s := by
  funext i
  by_cases hi : i = t
  · subst hi; simp [cxFun, hct]
  · simp [cxFun, hi]

/-- CX as a permutation (it is its own inverse: CX CX = 1). -/
def cxE {n : ℕ} (c t : Fin n) (hct : c ≠ t) : Q n ≃ Q n where
  toFun := cxFun c t
  invFun := cxFun c t
  left_inv := cxFun_cxFun c t hct
  right_inv := cxFun_cxFun c t hct

theorem cx_involutive {n : ℕ} (c t : Fin n) (hct : c ≠ t) :
    perm (cxE c t hct) * perm (cxE c t hct) = 1 := by
  rw [perm_mul]
  convert perm_one (n := n)
  ext s i
  simp [cxE, cxFun_cxFun c t hct]

theorem cx_xorLinear {n : ℕ} (c t : Fin n) (hct : c ≠ t) : XorLinear (cxE c t hct) := by
  intro s u
  funext i
  simp only [cxE, Equiv.coe_fn_mk, cxFun, bxor]
  by_cases hi : i = t
  · subst hi; simp; cases s i <;> cases u i <;> cases s c <;> cases u c <;> rfl
  · simp [hi]

/-- The phase identity behind the doubly-controlled Z built from three controlled phases and two
CNOTs: pi/2 (b c - (a xor b) c + a c) = pi a b c for bits a, b, c. -/
theorem ccz_phase (a b c : Bool) :
    ((b.toNat * c.toNat : ℤ) - ((xor a b).toNat * c.toNat : ℤ) + (a.toNat * c.toNat : ℤ)) =
      2 * (a.toNat * b.toNat * c.toNat : ℤ) := by
  cases a <;> cases b <;> cases c <;> decide

/-- The controlled-phase gate CP(phi) on qubits (a, b) as a diagonal operator. -/
noncomputable def cpDiag {n : ℕ} (a b : Fin n) (φ : ℝ) : Q n → ℂ :=
  fun s => Complex.exp (φ * (((s a).toNat * (s b).toNat : ℕ) : ℝ) * Complex.I)

/-- The CCZ decomposition at the level of operators: conjugating CP(-pi/2)(b,c) by CX(a,b) and
multiplying by CP(pi/2)(b,c) CP(pi/2)(a,c) gives the doubly-controlled Z, diag((-1)^{abc}). -/
theorem ccz_circuit {n : ℕ} (a b c : Fin n) (hab : a ≠ b) (hbc : b ≠ c) :
    diagonal (cpDiag b c (Real.pi / 2)) *
      (perm (cxE a b hab) * diagonal (cpDiag b c (-(Real.pi / 2))) * perm (cxE a b hab).symm) *
      diagonal (cpDiag a c (Real.pi / 2)) =
      diagonal (fun s => Complex.exp (Real.pi *
        (((s a).toNat * (s b).toNat * (s c).toNat : ℕ) : ℝ) * Complex.I)) := by
  rw [perm_conj_diagonal, Matrix.diagonal_mul_diagonal, Matrix.diagonal_mul_diagonal]
  congr 1
  funext s
  simp only [Function.comp_apply, cpDiag]
  rw [← Complex.exp_add, ← Complex.exp_add]
  congr 1
  have hsym : (cxE a b hab).symm s = cxFun a b s := rfl
  rw [hsym]
  have hb : cxFun a b s b = xor (s b) (s a) := by simp [cxFun]
  have hc : cxFun a b s c = s c := by simp [cxFun, Ne.symm hbc]
  rw [hb, hc, Bool.xor_comm]
  have keyC := congrArg (fun z : ℤ => (z : ℂ)) (ccz_phase (s a) (s b) (s c))
  push_cast at keyC
  push_cast
  linear_combination (Real.pi / 2 * Complex.I) * keyC

end Su2Plaq

