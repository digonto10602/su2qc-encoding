import Mathlib

/-!
# Su2Plaq.Fuzzy.Link — exact link algebra of the fuzzy SU(2) link (docs/METHODS-fuzzy.md F2, F8)

Every identity of the fuzzy link that the production code and the Pauli decompositions rely on, proved over the
Gaussian integers `ℤ[i]` by kernel evaluation (`decide +kernel`, no `native_decide`, no axioms beyond the
standard ones).  Matrices are *integer-scaled* so that all entries are Gaussian integers:

* `g μ = 2 Γ_μ` (μ = 0..3), `g5 = Γ_5`, `tR A = 2 T_R^A`, `tL A = 2 T_L^A`, `u a b = 2 𝕌_ab`  (all 4×4);
* `τ = 2 𝒯 = L(t) − R(t)` where `L(M) = M ⊗ 1` (left multiplication) and `R(M) = 1 ⊗ Mᵀ` (right multiplication),
  row-major vectorisation `Ψ ↦ vec Ψ`, index `8 q1 + 4 q2 + 2 q3 + q4` (METHODS-fuzzy F1);
* `υ_ab = L(u a b) = 2 𝒰_ab`, `k1 = 4 𝒦₁ = Σ τ²`, `s2 = −4 𝒦₂ = Σ (L(u)R(u†) + L(u†)R(u))`.

Equality of matrices `MEq` means equality of all `n × n` entries (a decidable `Bool` check).  The scalar type `Gi`
is a hand-rolled `ℤ[i]` (pairs of integers) so that kernel reduction is cheap.
-/

set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.Fuzzy

/-! ### Gaussian integers -/

/-- `re + im · i` with `re im : ℤ`. -/
structure Gi where
  re : Int
  im : Int
  deriving DecidableEq

namespace Gi
instance : Zero Gi := ⟨⟨0, 0⟩⟩
instance : One Gi := ⟨⟨1, 0⟩⟩
instance : Add Gi := ⟨fun a b => ⟨a.re + b.re, a.im + b.im⟩⟩
instance : Neg Gi := ⟨fun a => ⟨-a.re, -a.im⟩⟩
instance : Sub Gi := ⟨fun a b => ⟨a.re - b.re, a.im - b.im⟩⟩
instance : Mul Gi := ⟨fun a b => ⟨a.re * b.re - a.im * b.im, a.re * b.im + a.im * b.re⟩⟩
/-- The imaginary unit. -/
def I : Gi := ⟨0, 1⟩
/-- Complex conjugate. -/
def conj (a : Gi) : Gi := ⟨a.re, -a.im⟩
/-- Embed an integer. -/
def ofInt (n : Int) : Gi := ⟨n, 0⟩
end Gi

open Gi in
/-! ### Square matrices with Gaussian-integer entries -/

/-- An `n × n` matrix, stored as a function on `Nat` indices (entries outside `[0,n)` are never inspected). -/
structure M (n : Nat) where
  f : Nat → Nat → Gi

/-- Table lookup (entries outside the table are `0`). -/
def lookup (t : List (List Gi)) (i j : Nat) : Gi := (t.getD i []).getD j 0

/-- Matrix backed by a table. -/
def ofTable {n : Nat} (t : List (List Gi)) : M n := ⟨lookup t⟩

/-- Memoising constructor: the entries of `f` on `[0,n)²` are tabulated once, so that later products do not
re-evaluate nested expression trees (this keeps kernel reduction polynomial). -/
def tab (n : Nat) (f : Nat → Nat → Gi) : M n :=
  ofTable ((List.range n).map fun i => (List.range n).map fun j => f i j)

namespace M
variable {n : Nat}

/-- Sum over `k < n` of `g k`. -/
def gsum (n : Nat) (g : Nat → Gi) : Gi := (List.range n).foldl (fun s k => s + g k) 0

instance : Add (M n) := ⟨fun A B => tab n fun i j => A.f i j + B.f i j⟩
instance : Sub (M n) := ⟨fun A B => tab n fun i j => A.f i j - B.f i j⟩
instance : Neg (M n) := ⟨fun A => tab n fun i j => -A.f i j⟩
instance : Mul (M n) := ⟨fun A B => tab n fun i j => gsum n (fun k => A.f i k * B.f k j)⟩
instance : Zero (M n) := ⟨⟨fun _ _ => 0⟩⟩
instance : One (M n) := ⟨⟨fun i j => if i = j then 1 else 0⟩⟩

/-- Multiplication by a Gaussian integer. -/
def sc (c : Gi) (A : M n) : M n := ⟨fun i j => c * A.f i j⟩
/-- Integer scalar. -/
def isc (c : Int) (A : M n) : M n := sc (Gi.ofInt c) A
/-- Transpose (no conjugation). -/
def tr (A : M n) : M n := ⟨fun i j => A.f j i⟩
/-- Conjugate transpose. -/
def dag (A : M n) : M n := ⟨fun i j => Gi.conj (A.f j i)⟩
/-- Trace. -/
def trace (n : Nat) (A : M n) : Gi := gsum n (fun i => A.f i i)
/-- Commutator. -/
def comm (A B : M n) : M n := A * B - B * A
/-- Anticommutator. -/
def acomm (A B : M n) : M n := A * B + B * A

/-- Entrywise equality check on `[0,n)²`. -/
def meqb (n : Nat) (A B : M n) : Bool :=
  (List.range n).all fun i => (List.range n).all fun j => decide (A.f i j = B.f i j)

/-- Matrix equality (all `n²` entries agree). -/
def MEq (A B : M n) : Prop := meqb n A B = true

instance (A B : M n) : Decidable (MEq A B) := inferInstanceAs (Decidable (meqb n A B = true))

theorem MEq_iff (A B : M n) : MEq A B ↔ ∀ i < n, ∀ j < n, A.f i j = B.f i j := by
  unfold MEq meqb
  simp [List.all_eq_true]

/-- Kronecker product `A ⊗ B` where `B` is `m × m` (`A` is `a × a`, result `(a m) × (a m)`). -/
def kron (m : Nat) {a : Nat} (A : M a) (B : M m) : M (a * m) :=
  ⟨fun i j => A.f (i / m) (j / m) * B.f (i % m) (j % m)⟩

/-- `2×2` block matrix `[[A,B],[C,D]]` of `2×2` blocks. -/
def block (A B C D : M 2) : M 4 :=
  ⟨fun i j =>
    if i < 2 then (if j < 2 then A.f i j else B.f i (j - 2))
    else (if j < 2 then C.f (i - 2) j else D.f (i - 2) (j - 2))⟩

/-- Build a `2×2` matrix from its four entries. -/
def mk2 (a b c d : Gi) : M 2 :=
  ⟨fun i j => match i, j with
    | 0, 0 => a | 0, 1 => b | 1, 0 => c | 1, 1 => d | _, _ => 0⟩

end M

open M Gi

/-! ### Pauli matrices and the Gamma matrices -/

/-- `σ^1, σ^2, σ^3` and the identity (index 3); `sig A` for `A : Nat`, `A ≥ 3` gives the identity. -/
def sx : M 2 := mk2 0 1 1 0
def sy : M 2 := mk2 0 (-Gi.I) Gi.I 0
def sz : M 2 := mk2 1 0 0 (-1)
def i2 : M 2 := 1
def i4 : M 4 := 1
def i16 : M 16 := 1
/-- `σ^A`, `A = 0,1,2` for `σ^1, σ^2, σ^3`. -/
def sig : Nat → M 2
  | 0 => sx | 1 => sy | _ => sz
/-- Entry `σ^A_{ab}`. -/
def sigE (A a b : Nat) : Gi := (sig A).f a b

/-- `g 0 = 2Γ_0 = [[0,1],[1,0]]` (blocks), `g (A+1) = 2Γ_A = [[0,iσ^A],[−iσ^A,0]]`. -/
def g : Nat → M 4
  | 0 => block 0 1 1 0
  | A + 1 => block 0 (sc Gi.I (sig A)) (sc (-Gi.I) (sig A)) 0
/-- `Γ_5 = diag(1,1,−1,−1)`. -/
def g5 : M 4 := block 1 0 0 (-1)
/-- `t R A = 2 T_R^A = diag(σ^A, 0)`. -/
def tR (A : Nat) : M 4 := block (sig A) 0 0 0
/-- `t L A = 2 T_L^A = diag(0, σ^A)`. -/
def tL (A : Nat) : M 4 := block 0 0 0 (sig A)
/-- `u a b = 2 𝕌_ab = δ_ab · 2Γ_0 − i σ^A_ab · 2Γ_A`. -/
def u (a b : Nat) : M 4 :=
  (if a = b then g 0 else 0) - sc Gi.I (sc (sigE 0 a b) (g 1) + sc (sigE 1 a b) (g 2) + sc (sigE 2 a b) (g 3))

/-- Levi-Civita symbol on `{0,1,2}`. -/
def eps (A B C : Nat) : Int :=
  if (A, B, C) = (0, 1, 2) ∨ (A, B, C) = (1, 2, 0) ∨ (A, B, C) = (2, 0, 1) then 1
  else if (A, B, C) = (0, 2, 1) ∨ (A, B, C) = (2, 1, 0) ∨ (A, B, C) = (1, 0, 2) then -1 else 0

/-- `ε = iσ² = [[0,1],[−1,0]]` entries. -/
def epsE (a b : Nat) : Int := if (a, b) = (0, 1) then 1 else if (a, b) = (1, 0) then -1 else 0

/-! ### Gamma-matrix relations (4×4) -/

/-- Clifford algebra: `{2Γ_μ, 2Γ_ν} = 2 δ_μν` for μ,ν = 0..3. -/
theorem clifford : ∀ μ ν : Fin 4, MEq (acomm (g μ) (g ν)) (isc (if μ = ν then 2 else 0) i4) := by
  decide +kernel

/-- `Γ_5² = 1`, `{Γ_5, Γ_μ} = 0`, and `(2Γ_0)(2Γ_1)(2Γ_2)(2Γ_3) = Γ_5`. -/
theorem gamma5_rel :
    MEq (g5 * g5) i4 ∧ (∀ μ : Fin 4, MEq (acomm g5 (g μ)) 0) ∧ MEq (g 0 * g 1 * g 2 * g 3) g5 := by
  decide +kernel

/-! ### su(2) algebra of `T_L`, `T_R` (4×4 and 16×16) -/

/-- `[2T^A, 2T^B] = 2i ε_ABC (2T^C)` for both chiralities; `T_L T_R = T_R T_L = 0`. -/
theorem su2_4x4 :
    (∀ A B : Fin 3, MEq (comm (tL A) (tL B))
        (sc (Gi.ofInt 2 * Gi.I) (isc (eps A B 0) (tL 0) + isc (eps A B 1) (tL 1) + isc (eps A B 2) (tL 2)))) ∧
    (∀ A B : Fin 3, MEq (comm (tR A) (tR B))
        (sc (Gi.ofInt 2 * Gi.I) (isc (eps A B 0) (tR 0) + isc (eps A B 1) (tR 1) + isc (eps A B 2) (tR 2)))) ∧
    (∀ A B : Fin 3, MEq (tL A * tR B) 0 ∧ MEq (tR B * tL A) 0) := by
  decide +kernel

/-- Left multiplication `L(M) = M ⊗ 1₄`. -/
def Lm (A : M 4) : M 16 := kron 4 A i4
/-- Right multiplication `R(M) = 1₄ ⊗ Mᵀ`. -/
def Rm (A : M 4) : M 16 := kron 4 i4 (tr A)
/-- `τ_L^A = 2 𝒯_L^A = L(2T_L) − R(2T_L)`. -/
def tauL (A : Nat) : M 16 := Lm (tL A) - Rm (tL A)
/-- `τ_R^A = 2 𝒯_R^A`. -/
def tauR (A : Nat) : M 16 := Lm (tR A) - Rm (tR A)
/-- `υ_ab = 2 𝒰_ab = L(u a b)`. -/
def ups (a b : Nat) : M 16 := Lm (u a b)

/-- `[𝒯^A, 𝒯^B] = i ε_ABC 𝒯^C` (as `[τ^A,τ^B] = 2i ε τ^C`) for L and R, and `[𝒯_L,𝒯_R] = 0`, on the 16-dim link space. -/
theorem su2_link :
    (∀ A B : Fin 3, MEq (comm (tauL A) (tauL B))
        (sc (Gi.ofInt 2 * Gi.I) (isc (eps A B 0) (tauL 0) + isc (eps A B 1) (tauL 1) + isc (eps A B 2) (tauL 2)))) ∧
    (∀ A B : Fin 3, MEq (comm (tauR A) (tauR B))
        (sc (Gi.ofInt 2 * Gi.I) (isc (eps A B 0) (tauR 0) + isc (eps A B 1) (tauR 1) + isc (eps A B 2) (tauR 2)))) ∧
    (∀ A B : Fin 3, MEq (comm (tauL A) (tauR B)) 0) := by
  decide +kernel

/-- Transformation law (P Eqs. 24–25): `[𝒯_L^A, 𝒰_ab] = −½ (σ^A 𝒰)_ab`, `[𝒯_R^A, 𝒰_ab] = +½ (𝒰 σ^A)_ab`
(scaled: `[τ_L^A, υ_ab] = −Σ_c σ^A_ac υ_cb`, `[τ_R^A, υ_ab] = +Σ_c υ_ac σ^A_cb`). -/
theorem transformation_law :
    (∀ (A : Fin 3) (a b : Fin 2), MEq (comm (tauL A) (ups a b))
        (-(sc (sigE A a 0) (ups 0 b) + sc (sigE A a 1) (ups 1 b)))) ∧
    (∀ (A : Fin 3) (a b : Fin 2), MEq (comm (tauR A) (ups a b))
        (sc (sigE A 0 b) (ups a 0) + sc (sigE A 1 b) (ups a 1))) := by
  decide +kernel

/-- Pseudo-reality `(𝒰_ab)† = ε_ac ε_bd 𝒰_cd` (on the 4×4 matrices `u`, hence on `L(u)`). -/
theorem pseudo_reality :
    ∀ a b : Fin 2, MEq (dag (u a b))
      (isc (epsE a 0 * epsE b 0) (u 0 0) + isc (epsE a 0 * epsE b 1) (u 0 1) +
       isc (epsE a 1 * epsE b 0) (u 1 0) + isc (epsE a 1 * epsE b 1) (u 1 1)) := by
  decide +kernel

/-! ### Pauli forms (qubits `q1 q2 | q3 q4`, `q1` most significant) -/

/-- Pauli string `a ⊗ b ⊗ c ⊗ d` on `(q1,q2,q3,q4)` as a 16×16 matrix. -/
def pk (a b c d : M 2) : M 16 := kron 8 (a : M 2) (kron 4 b (kron 2 c d))

/-- `𝒰_ij` Pauli form: `2𝒰_ij = δ_ij X_1 + i σ^A_ij Y_1 σ^A_2` (on the 4×4 `(q1,q2)` space). -/
theorem pauli_U :
    ∀ a b : Fin 2, MEq (u a b)
      ((if (a : Nat) = b then kron 2 sx i2 else 0) +
        sc Gi.I (sc (sigE 0 a b) (kron 2 sy sx) + sc (sigE 1 a b) (kron 2 sy sy) + sc (sigE 2 a b) (kron 2 sy sz))) := by
  decide +kernel

/-- `2τ_R^A = (1+Z)_1 σ^A_2 − (1+Z)_3 (σ^A)ᵀ_4` and `2τ_L^A = (1−Z)_1 σ^A_2 − (1−Z)_3 (σ^A)ᵀ_4`
(i.e. `𝒯_{R,L} = ½[P⁰¹ σ_2 − P^{0,1}_3 σᵀ_4]`, `P⁰ = (1+Z)/2`, `P¹ = (1−Z)/2`). -/
theorem pauli_T :
    (∀ A : Fin 3, MEq (sc (Gi.ofInt 2) (tauR A))
      (pk i2 (sig A) i2 i2 + pk sz (sig A) i2 i2 - pk i2 i2 i2 (tr (sig A)) - pk i2 i2 sz (tr (sig A)))) ∧
    (∀ A : Fin 3, MEq (sc (Gi.ofInt 2) (tauL A))
      (pk i2 (sig A) i2 i2 - pk sz (sig A) i2 i2 - pk i2 i2 i2 (tr (sig A)) + pk i2 i2 sz (tr (sig A)))) := by
  decide +kernel

/-! ### The kinetic operators `𝒦₁`, `𝒦₂` -/

/-- `k1 = 4 𝒦₁ = Σ_A (τ_L^A)² + Σ_A (τ_R^A)²`  (`𝒦₁ = (𝒯_L)² + (𝒯_R)²`, P Eq. 36). -/
def k1 : M 16 := tauL 0 * tauL 0 + tauL 1 * tauL 1 + tauL 2 * tauL 2 + tauR 0 * tauR 0 + tauR 1 * tauR 1 + tauR 2 * tauR 2

/-- `s2 = Σ_ab (L(u_ab) R(u_ab†) + L(u_ab†) R(u_ab)) = −4 𝒦₂`  (P Eq. 37). -/
def s2 : M 16 :=
  Lm (u 0 0) * Rm (dag (u 0 0)) + Lm (dag (u 0 0)) * Rm (u 0 0) +
  Lm (u 0 1) * Rm (dag (u 0 1)) + Lm (dag (u 0 1)) * Rm (u 0 1) +
  Lm (u 1 0) * Rm (dag (u 1 0)) + Lm (dag (u 1 0)) * Rm (u 1 0) +
  Lm (u 1 1) * Rm (dag (u 1 1)) + Lm (dag (u 1 1)) * Rm (u 1 1)

/-- Pauli form of `4 𝒦₁ = 6 − (X_2X_4 − Y_2Y_4 + Z_2Z_4)(1 + Z_1Z_3)`. -/
def k1P : M 16 :=
  isc 6 i16 - (pk i2 sx i2 sx - pk i2 sy i2 sy + pk i2 sz i2 sz) * (i16 + pk sz i2 sz i2)

/-- Pauli form of `𝒦₂ = −X_1X_3 + Y_1X_2Y_3X_4 − Y_1Y_2Y_3Y_4 + Y_1Z_2Y_3Z_4`. -/
def k2P : M 16 := -pk sx i2 sx i2 + pk sy sx sy sx - pk sy sy sy sy + pk sy sz sy sz

/-- Pauli forms of the kinetic terms: `4𝒦₁ = k1P`, `−4𝒦₂ = Σ_ab(…)` (so `𝒦₂ = k2P`). -/
theorem pauli_K : MEq k1 k1P ∧ MEq s2 (isc (-4) k2P) := by
  decide +kernel

/-- Hermiticity of the Pauli forms (so `𝒦₁`, `𝒦₂` are Hermitian). -/
theorem K_hermitian : MEq (dag k1P) k1P ∧ MEq (dag k2P) k2P := by
  decide +kernel

/-- `[𝒦₁, 𝒦₂] = 0`. -/
theorem K1_K2_commute : MEq (comm k1P k2P) 0 := by
  decide +kernel

/-- Spectrum of `𝒦₁` = `{0², (3/2)⁸, 2⁶}`: with `k = 4𝒦₁`, the minimal-polynomial relation `k (k−6)(k−8) = 0`
(so eigenvalues ⊂ {0, 3/2, 2}) and the traces `tr 1 = 16`, `tr k = 96`, `tr k² = 672` which force the multiplicities
`n₀ + n₃/₂ + n₂ = 16`, `6 n₃/₂ + 8 n₂ = 96`, `36 n₃/₂ + 64 n₂ = 672`, i.e. `(2, 8, 6)`. -/
theorem K1_spectrum :
    MEq (k1P * (k1P - isc 6 i16) * (k1P - isc 8 i16)) 0 ∧
    trace 16 i16 = Gi.ofInt 16 ∧ trace 16 k1P = Gi.ofInt 96 ∧ trace 16 (k1P * k1P) = Gi.ofInt 672 := by
  decide +kernel

/-- Spectrum of `𝒦₂` = `{−4, −2⁴, 0⁶, 2⁴, 4}`: minimal-polynomial relation `K (K²−4)(K²−16) = 0` and the traces
`tr K^p = 16, 0, 64, 0, 640` (p = 0..4); the Vandermonde system on the five admissible eigenvalues then fixes the
multiplicities `(1, 4, 6, 4, 1)`. -/
theorem K2_spectrum :
    MEq (k2P * (k2P * k2P - isc 4 i16) * (k2P * k2P - isc 16 i16)) 0 ∧
    trace 16 i16 = Gi.ofInt 16 ∧ trace 16 k2P = 0 ∧ trace 16 (k2P * k2P) = Gi.ofInt 64 ∧
    trace 16 (k2P * k2P * k2P) = 0 ∧ trace 16 (k2P * k2P * k2P * k2P) = Gi.ofInt 640 := by
  decide +kernel

/-- Extremal eigenvectors of `𝒦₂`: `Ψ = 1` (vec `E_00 + E_11 + E_22 + E_33`... entries `|0000⟩+|0101⟩+|1010⟩+|1111⟩`)
has eigenvalue `−4`, `Ψ = Γ_5` (`|0000⟩+|0101⟩−|1010⟩−|1111⟩`) has `+4`; both are `𝒦₁`-eigenvalue `0`. -/
def vecOne : Nat → Gi := fun i => if i = 0 ∨ i = 5 ∨ i = 10 ∨ i = 15 then 1 else 0
def vecG5 : Nat → Gi := fun i => if i = 0 ∨ i = 5 then 1 else if i = 10 ∨ i = 15 then -1 else 0
def apply (A : M 16) (v : Nat → Gi) : Nat → Gi := fun i => gsum 16 (fun k => A.f i k * v k)
def veq (v w : Nat → Gi) : Prop := (List.range 16).all (fun i => decide (v i = w i)) = true
instance (v w : Nat → Gi) : Decidable (veq v w) := inferInstanceAs (Decidable (_ = true))

theorem K2_extremal :
    veq (apply k2P vecOne) (fun i => Gi.ofInt (-4) * vecOne i) ∧
    veq (apply k2P vecG5) (fun i => Gi.ofInt 4 * vecG5 i) ∧
    veq (apply k1P vecOne) (fun _ => 0) ∧ veq (apply k1P vecG5) (fun _ => 0) := by
  decide +kernel

/-! ### Flavour and centre -/

/-- Flavour `F = R(Γ_5) = Z_3`; commutes with `𝒦₁`, anticommutes with `𝒦₂`, commutes with `𝒯_{L,R}` and with `𝒰`. -/
def flav : M 16 := Rm g5
def centre : M 16 := pk sz i2 sz i2

theorem flavour :
    MEq flav (pk i2 i2 sz i2) ∧ MEq (comm flav k1P) 0 ∧ MEq (acomm flav k2P) 0 ∧
    (∀ A : Fin 3, MEq (comm flav (tauL A)) 0 ∧ MEq (comm flav (tauR A)) 0) ∧
    (∀ a b : Fin 2, MEq (comm flav (ups a b)) 0) := by
  decide +kernel

/-- Centre `𝒵 = Z_1 Z_3` commutes with both kinetic terms and anticommutes with every `𝒰_ab`. -/
theorem centre_rel :
    MEq (comm centre k1P) 0 ∧ MEq (comm centre k2P) 0 ∧ (∀ a b : Fin 2, MEq (acomm centre (ups a b)) 0) := by
  decide +kernel

/-- Non-vacuity of `MEq`: it rejects unequal matrices (`𝒦₁ ≠ 𝒦₂`, `𝒵` does not commute with `𝒰`, `F` does not commute with `𝒦₂`). -/
theorem MEq_discriminates :
    ¬ MEq k1P k2P ∧ ¬ MEq (comm centre (ups 0 0)) 0 ∧ ¬ MEq (comm flav k2P) 0 := by
  decide +kernel

end Su2Plaq.Fuzzy
