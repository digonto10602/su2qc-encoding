import Su2Plaq.Rishon.JW

/-!
# Su2Plaq.Rishon.CornerKernel -- the Gauss kernel at a corner has the SU(2) fusion dimension (M5x step W2)

prompts/202 section 1 (W2), docs/METHODS-rishon.md R9.  Mathlib-free; the proof is `decide +kernel`.

A corner has four link ends `e = 0..3` on the qubits `(2e, 2e+1)` = (colour 1, colour 2) (bit 0 = colour 1).  An end is
empty (`00`), full (`11`) or carries one rishon (`01` or `10`), so a configuration `m = sum_e m_e 3^e` allows
`D = 2^(number of one-rishon ends)` basis states.  On the 8 modes the generators built from the Jordan-Wigner operators of
`JW.lean` are
`2 G^z = sum_e (n_{e,1} - n_{e,2})`, `G^+ = sum_e c^dagger_{e,1} c_{e,2}`, `G^- = sum_e c^dagger_{e,2} c_{e,1}`
(`G^x = (G^+ + G^-)/2`, `G^y = (G^+ - G^-)/(2i)`), so the joint kernel of the three is the SU(2)-singlet space.
`kerDim m` is `D` minus the rank of the stacked integer matrices (fraction-free elimination, no division;
Bareiss, Math. Comp. 22 (1968) 565-578).  `corner_kernel_dims` states that for all 81 configurations the three operators
keep the subspace and `kerDim` equals the fusion count of the end spins (`cornerCountR`, a Mathlib-free copy of
`Su2Plaq.cornerCount`; the agreement with the original is proved in `Bridge.lean`, step W4).
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0
set_option synthInstance.maxSize 10000
set_option synthInstance.maxHeartbeats 200000

namespace Su2Plaq.Rishon


/-- end configuration: 0 = empty (00), 1 = full (11), 2 = one rishon (01 or 10) -/
def endOK (m : Nat) (v : Nat) : Bool :=
  match m with
  | 0 => v == 0
  | 1 => v == 3
  | _ => v == 1 || v == 2

/-- basis states (8 bits, end `e` on bits `2e, 2e+1`) of the corner subspace with end configuration `m < 81` -/
def cornerBasis (m : Nat) : List Nat :=
  (List.range 256).filter fun s =>
    (List.range 4).all fun e => endOK ((m / 3 ^ e) % 3) ((s / 2 ^ (2 * e)) % 4)

/-- `2 G^z_e = n_{e,1} - n_{e,2}`, `G^+_e = c†_{e,1} c_{e,2}`, `G^-_e = c†_{e,2} c_{e,1}` on 8 modes, summed over the four ends -/
def nOp (k : Nat) : SOp := comp (mode true 8 k) (mode false 8 k)
def gz : SOp := (List.range 4).foldl (fun acc e => add acc (add (nOp (2 * e)) (smul (-1) (nOp (2 * e + 1))))) zeroOp
def gp : SOp := (List.range 4).foldl (fun acc e => add acc (comp (mode true 8 (2 * e)) (mode false 8 (2 * e + 1)))) zeroOp
def gm : SOp := (List.range 4).foldl (fun acc e => add acc (comp (mode true 8 (2 * e + 1)) (mode false 8 (2 * e)))) zeroOp

/-- the operator keeps the corner subspace (no image outside the basis) -/
def invariant (A : SOp) (basis : List Nat) : Bool :=
  basis.all fun s => (A s).all fun p => basis.contains p.1

/-- row `t` of the matrix of `A` on `basis`: entries `<t|A|s>` for `s` in `basis` -/
def matRow (A : SOp) (basis : List Nat) (t : Nat) : List Int :=
  basis.map fun s => ((A s).find? (fun p => p.1 == t)).map (·.2) |>.getD 0

def matrixOf (A : SOp) (basis : List Nat) : List (List Int) := basis.map (matRow A basis)

/-- fraction-free elimination: rank of an integer matrix given as rows -/
def elimRow (piv : List Int) (p : Int) (c : Nat) (row : List Int) : List Int :=
  let a := row.getD c 0
  List.zipWith (fun x y => p * x - a * y) row piv

/-- rank by column sweep: `cols` columns, `rows` the remaining rows -/
def rankSweep : Nat → Nat → List (List Int) → Nat → Nat
  | 0, _, _, acc => acc
  | fuel + 1, c, rows, acc =>
    match rows.find? (fun r => r.getD c 0 != 0) with
    | none => rankSweep fuel (c + 1) rows acc
    | some piv =>
      let p := piv.getD c 0
      let rest := (rows.erase piv).map (elimRow piv p c)
      rankSweep fuel (c + 1) rest (acc + 1)

def rank (rows : List (List Int)) (ncols : Nat) : Nat := rankSweep ncols 0 rows 0

def kerDim (m : Nat) : Nat :=
  let b := cornerBasis m
  b.length - rank (matrixOf gz b ++ matrixOf gp b ++ matrixOf gm b) b.length

/-- SU(2) fusion count of four spins in {0, 1/2}: |fuse(a,b) ∩ fuse(c,d)| (as `Su2Plaq.cornerCount`, re-defined here
Mathlib-free) -/
def fuseR (a b : Bool) : List Nat :=
  match a, b with
  | false, false => [0]
  | false, true  => [1]
  | true,  false => [1]
  | true,  true  => [0, 2]
def cornerCountR (ia ib oc od : Bool) : Nat :=
  ((fuseR ia ib).filter (fun J => (fuseR oc od).contains J)).length

def isQ (m e : Nat) : Bool := (m / 3 ^ e) % 3 == 2

theorem corner_kernel_dims : (List.range 81).all (fun m =>
    invariant gz (cornerBasis m) && invariant gp (cornerBasis m) && invariant gm (cornerBasis m) &&
    kerDim m == cornerCountR (isQ m 0) (isQ m 1) (isQ m 2) (isQ m 3)) = true := by
  decide +kernel

end Su2Plaq.Rishon
