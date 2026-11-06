/-!
# Su2Plaq.Rishon.JW — Jordan–Wigner facts of the rishon encoding (M5, prompts/200 §2.9, docs/METHODS-rishon.md R2, R8)

Self-contained (core Lean only, no Mathlib).  Fermion operators on `n` modes are represented on the computational
basis `s ∈ [0, 2^n)` (little-endian: bit `k` of `s` = occupation of mode `k` = qubit `k`):

* `FOp`  — a monomial operator ("signed partial permutation"): basis state ↦ `none` or `(image, ±1)`.
* `SOp`  — a general sparse operator: basis state ↦ list of `(image, coefficient)` (sums of monomials).
  `OpEq n A B` compares two operators on all `s < 2^n` after normalisation (merge equal images, drop zeros, sort).

Jordan–Wigner: `c_k = (∏_{m<k} Z_m) σ⁻_k`, `σ⁻ = |0⟩⟨1|`, `Z|1⟩ = -|1⟩`; `c_k†` the transpose.  The link `ℓ` has the
four modes `(L₁, L₂, R₁, R₂) = (4ℓ, 4ℓ+1, 4ℓ+2, 4ℓ+3)`; link codes `A = 3 (1100)`, `B = 12 (0011)`, the quartet
`Q = {5, 6, 9, 10}`; `U_ij = c_{L,i} c†_{R,j}`; `det U = 2 c_{L1} c†_{R1} c_{L2} c†_{R2}` (BCW Eq. 4.6).

All statements are quantified over finite ranges and proved by `decide +kernel` (kernel reduction only, no
compiler-trust tactics, no axioms).
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0
set_option synthInstance.maxSize 10000
set_option synthInstance.maxHeartbeats 200000

namespace Su2Plaq.Rishon

/-! ### Basis states and operators -/

/-- occupation of mode `k` in basis state `s` -/
def occ (s k : Nat) : Bool := (s / 2 ^ k) % 2 == 1

/-- number of occupied modes among the first `n` -/
def weight (n s : Nat) : Nat := (List.range n).foldl (fun a m => if occ s m then a + 1 else a) 0

/-- sparse vector: list of `(basis index, coefficient)` -/
abbrev SVec := List (Nat × Int)

/-- monomial operator on the basis (signed partial permutation) -/
abbrev FOp := Nat → Option (Nat × Int)
/-- general sparse operator -/
abbrev SOp := Nat → SVec

/-- Jordan–Wigner string sign of mode `k` on state `s`: `∏_{m<k} Z_m` -/
def jwSign (s k : Nat) : Int := (List.range k).foldl (fun a m => if occ s m then -a else a) 1

/-- annihilation operator `c_k` on `n` modes: needs mode `k` occupied -/
def jwC (n k : Nat) : FOp := fun s =>
  if k < n ∧ occ s k then some (s - 2 ^ k, jwSign s k) else none
/-- creation operator `c_k†` on `n` modes: needs mode `k` empty -/
def jwCdag (n k : Nat) : FOp := fun s =>
  if k < n ∧ !occ s k then some (s + 2 ^ k, jwSign s k) else none

def ofF (f : FOp) : SOp := fun s => match f s with
  | none => []
  | some (t, c) => [(t, c)]

/-- `c_k` (`dag = false`) or `c_k†` (`dag = true`) as a sparse operator -/
def mode (dag : Bool) (n k : Nat) : SOp := ofF (if dag then jwCdag n k else jwC n k)

/-! ### Sparse algebra -/

/-- insert a term into a sorted, duplicate-free, zero-free list -/
def insertTerm (p : Nat × Int) : SVec → SVec
  | [] => if p.2 = 0 then [] else [p]
  | q :: qs =>
    if p.1 = q.1 then
      (if p.2 + q.2 = 0 then qs else (p.1, p.2 + q.2) :: qs)
    else if p.1 < q.1 then
      (if p.2 = 0 then q :: qs else p :: q :: qs)
    else q :: insertTerm p qs

/-- normal form: sorted by index, equal indices merged, zero coefficients dropped -/
def normalize (v : SVec) : SVec := v.foldl (fun acc p => insertTerm p acc) []

/-- operator product `A ∘ B` (apply `B` first) -/
def comp (A B : SOp) : SOp := fun s =>
  normalize ((B s).flatMap (fun p => (A p.1).map (fun q => (q.1, p.2 * q.2))))

def add (A B : SOp) : SOp := fun s => normalize (A s ++ B s)
def smul (c : Int) (A : SOp) : SOp := fun s => normalize ((A s).map (fun p => (p.1, c * p.2)))
def zeroOp : SOp := fun _ => []
/-- identity if `k = l`, else `0` (the Kronecker `δ_kl` times the identity) -/
def delta (k l : Nat) : SOp := fun s => if k = l then [(s, 1)] else []
def anticomm (A B : SOp) : SOp := add (comp A B) (comp B A)

/-- equality of two operators on the `n`-mode basis -/
abbrev OpEq (n : Nat) (A B : SOp) : Prop := ∀ s < 2 ^ n, normalize (A s) = normalize (B s)

/-- an operator `A` on the `w` modes `pos .. pos+w-1`, tensored with the identity on all other modes -/
def embedAt (w pos : Nat) (A : SOp) : SOp := fun s =>
  let base := 2 ^ pos
  let loc := s / base % 2 ^ w
  (A loc).map (fun p => (s - loc * base + p.1 * base, p.2))

/-! ### 1. Canonical anticommutation relations -/

/-- CAR on 4 modes (one link): `{c_k, c_l†} = δ_kl`, `{c_k, c_l} = 0`, `{c_k†, c_l†} = 0`. -/
theorem car_4 : ∀ k < 4, ∀ l < 4,
    OpEq 4 (anticomm (mode false 4 k) (mode true 4 l)) (delta k l) ∧
    OpEq 4 (anticomm (mode false 4 k) (mode false 4 l)) zeroOp ∧
    OpEq 4 (anticomm (mode true 4 k) (mode true 4 l)) zeroOp := by
  decide +kernel

/-- CAR on 8 modes (two links). -/
theorem car_8 : ∀ k < 8, ∀ l < 8,
    OpEq 8 (anticomm (mode false 8 k) (mode true 8 l)) (delta k l) ∧
    OpEq 8 (anticomm (mode false 8 k) (mode false 8 l)) zeroOp ∧
    OpEq 8 (anticomm (mode true 8 k) (mode true 8 l)) zeroOp := by
  decide +kernel

/-! ### 2. String-freeness of the link bilinears -/

/-- Bilinears of the modes of one link are string-free: on 8 modes (two links) the product of two modes of the upper
link (modes 4..7, any mix of `c`, `c†`) equals the same product on 4 modes acting on qubits 4..7 with identity on qubits
0..3; the same for the lower link on qubits 0..3 (the JW strings of the other link cancel). -/
theorem bilinear_string_free_8 : ∀ d1 : Bool, ∀ d2 : Bool, ∀ k < 4, ∀ l < 4,
    OpEq 8 (comp (mode d1 8 (k + 4)) (mode d2 8 (l + 4))) (embedAt 4 4 (comp (mode d1 4 k) (mode d2 4 l))) ∧
    OpEq 8 (comp (mode d1 8 k) (mode d2 8 l)) (embedAt 4 0 (comp (mode d1 4 k) (mode d2 4 l))) := by
  decide +kernel

/-! ### 3. The two-rishon sector of one link -/

/-- the two-rishon sector: 4-mode basis states of weight 2 -/
def sector : List Nat := (List.range 16).filter (fun s => weight 4 s == 2)

/-- six states: `A = 3`, `B = 12` and the quartet `Q = 5, 6, 9, 10`. -/
theorem sector_card : sector.length = 6 ∧ sector = [3, 5, 6, 9, 10, 12] := by
  decide +kernel

/-! ### 4. The link operators `U_ij` (A → Q → B → 0) -/

/-- `U_ij = c_{L,i} c†_{R,j}` on one link (`i, j ∈ {0, 1}`; `L_i` = mode `i`, `R_j` = mode `2 + j`) -/
def Uop (i j : Nat) : SOp := comp (mode false 4 i) (mode true 4 (2 + j))

def linkA : List Nat := [3]
def linkB : List Nat := [12]
def linkQ : List Nat := [5, 6, 9, 10]

/-- `U_ij` maps `A` to a single `Q` state (the four images are distinct), `Q` into `B` or `0`, and `B` to `0`. -/
theorem u_ladder : ∀ i < 2, ∀ j < 2,
    (∀ s ∈ linkA, (Uop i j s).length = 1 ∧ ∀ p ∈ Uop i j s, p.1 ∈ linkQ ∧ (p.2 = 1 ∨ p.2 = -1)) ∧
    (∀ s ∈ linkQ, ∀ p ∈ Uop i j s, p.1 ∈ linkB ∧ (p.2 = 1 ∨ p.2 = -1)) ∧
    (∀ s ∈ linkB, Uop i j s = []) ∧
    ((List.range 4).map (fun m => (Uop (m / 2) (m % 2) 3).map Prod.fst)).Nodup := by
  decide +kernel

/-- `det U = 2 c_{L1} c†_{R1} c_{L2} c†_{R2} = 2 U_11 U_22`. -/
def detU : SOp := smul 2 (comp (Uop 0 0) (Uop 1 1))

/-- On the two-rishon sector `det U = 2 |B⟩⟨A|`: `A ↦ 2 B` (coefficient `+2`) and every other sector state ↦ 0. -/
theorem det_u_sector :
    detU 3 = [(12, 2)] ∧ ∀ s ∈ sector, s ≠ 3 → detU s = [] := by
  decide +kernel

/-! ### 5. Locality of the end bilinears -/

/-- End bilinears are 2-qubit local: on 8 modes (four ends `e = 0..3` of two qubits each, qubits `2e, 2e+1`) every
product of two modes of one end (any mix of `c`, `c†`) equals the 2-mode product acting on qubits `2e, 2e+1` with
identity elsewhere (the JW strings of all other modes cancel). -/
theorem end_bilinear_local : ∀ d1 : Bool, ∀ d2 : Bool, ∀ e < 4, ∀ a < 2, ∀ b < 2,
    OpEq 8 (comp (mode d1 8 (2 * e + a)) (mode d2 8 (2 * e + b)))
      (embedAt 2 (2 * e) (comp (mode d1 2 a) (mode d2 2 b))) := by
  decide +kernel

end Su2Plaq.Rishon
