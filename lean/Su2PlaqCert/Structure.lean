import Su2PlaqCert.Check
import Std.Data.HashSet

/-!
# Su2PlaqCert.Structure — exact checker of the structure certificate (docs/METHODS.md §11.3, prompts/006 §4)

Everything is recomputed in exact arithmetic over `K` from the supplied data (Mathlib-free, computable):

1. the 433 states are orthonormal; the link generators form `su(2)` and the link operators `U_ij` are covariant
   (`[L_a, U_ij] = -(T_a U)_ij`, `[R_a, U_ij] = (U T_a)_ij`); the Gauss law holds at the four corners; the link spins `j_l`
   and the inner-pair spins `J_c` of every state are those of its label;
2. `H_B^phys = -(Ψ† (W ⊗ 1) Ψ + h.c.)` is recomputed from the exact states and `U_ij` and equals `D K_inner D` inside every
   outer-spin block and `0` between blocks (`K_inner` the supplied 47 × 47 matrix, `D` the supplied ±1 gauge);
3. `K_inner` is symmetric, conserves `J_c`, and is 8 bright 2 × 2 pairs plus 31 dark rows;
4. the spectrum multiplicities of `H_B^phys` (exact ranks of `H_B - λ` per block) and the outer-support numbers;
5. the Paulo adapter relates `U` to Paulo's link operators; the components, edge moduli and spectrum of `-(W + W†)` on the 625
   inner codes are recomputed;
6. the Casimir kernel dimensions of the four corners (16 spin cases each) and that they sum to the 433 states;
7. every listed symmetry is a signed permutation commuting with `H_B^phys` and with the inner electric energy.
-/
namespace Su2PlaqCert
open Lean

abbrev KMat := Array (Array K)

namespace KMat

def zero (n m : Nat) : KMat := Array.replicate n (Array.replicate m K.zero)

def ident (n : Nat) : KMat :=
  (Array.range n).map fun i => (Array.range n).map fun j => if i == j then K.one else K.zero

def rows (A : KMat) : Nat := A.size
def cols (A : KMat) : Nat := if A.isEmpty then 0 else A[0]!.size

def mul (A B : KMat) : KMat :=
  (Array.range A.rows).map fun i =>
    (Array.range B.cols).map fun j =>
      (Array.range A.cols).foldl (init := K.zero) fun acc k => acc + A[i]![k]! * B[k]![j]!

def add (A B : KMat) : KMat :=
  (Array.range A.rows).map fun i => (Array.range A.cols).map fun j => A[i]![j]! + B[i]![j]!

def sub (A B : KMat) : KMat :=
  (Array.range A.rows).map fun i => (Array.range A.cols).map fun j => A[i]![j]! + (-B[i]![j]!)

def scale (k : K) (A : KMat) : KMat := A.map fun r => r.map fun x => k * x

def conjT (A : KMat) : KMat :=
  (Array.range A.cols).map fun j => (Array.range A.rows).map fun i => (A[i]![j]!).conj

def comm (A B : KMat) : KMat := (A.mul B).sub (B.mul A)

def isZero (A : KMat) : Bool := A.all fun r => r.all fun x => x.isZero

end KMat

/-! ### exact rank over `K` through the regular representation over `ℚ` -/

def kBasis : Array K := #[{ a := 1 }, { b := 1 }, { c := 1 }, { d := 1 }, { e := 1 }, { f := 1 }, { g := 1 }, { h := 1 }]

def K.comps (x : K) : Array Rat := #[x.a, x.b, x.c, x.d, x.e, x.f, x.g, x.h]

/-- Rank of a rational matrix (Gaussian elimination). -/
def ratRank (M0 : Array (Array Rat)) : Nat := Id.run do
  let mut M := M0
  let nr := M.size
  let nc := if nr == 0 then 0 else M[0]!.size
  let mut rank := 0
  for c in [0:nc] do
    if rank ≥ nr then break
    let mut piv : Option Nat := none
    for r in [rank:nr] do
      if piv.isNone && M[r]![c]! != 0 then piv := some r
    match piv with
    | none => pure ()
    | some p =>
      let rowP := M[p]!
      M := (M.set! p M[rank]!).set! rank rowP
      let pr := M[rank]!
      for r in [rank + 1:nr] do
        let row := M[r]!
        if row[c]! != 0 then
          let f := row[c]! / pr[c]!
          M := M.set! r (Array.ofFn (n := nc) fun j => row[j.val]! - f * pr[j.val]!)
      rank := rank + 1
  return rank

/-- Rank over `K` of a `K`-matrix: the rank of its regular representation over `ℚ` divided by `[K : ℚ] = 8`. -/
def kRank (M : KMat) : Nat :=
  let nr := M.rows
  let nc := M.cols
  let big : Array (Array Rat) :=
    (Array.range (8 * nr)).map fun ri =>
      (Array.range (8 * nc)).map fun cj =>
        (((M[ri / 8]![cj / 8]!) * kBasis[cj % 8]!).comps)[ri % 8]!
  ratRank big / 8

/-! ### sparse vectors over the electric basis -/

abbrev SV := Array (Nat × K)

namespace SV

def ofMap (m : Std.HashMap Nat K) : SV :=
  ((m.fold (fun acc k v => if v.isZero then acc else acc.push (k, v)) #[]).qsort fun x y => x.1 < y.1)

def accum (m : Std.HashMap Nat K) (key : Nat) (v : K) : Std.HashMap Nat K :=
  match m.get? key with
  | some old => m.insert key (old + v)
  | none => m.insert key v

def add (u v : SV) : SV :=
  ofMap (v.foldl (init := u.foldl (init := (∅ : Std.HashMap Nat K)) fun m (k, x) => accum m k x) fun m (k, x) => accum m k x)

def scale (c : K) (v : SV) : SV := ofMap (v.foldl (init := (∅ : Std.HashMap Nat K)) fun m (k, x) => accum m k (c * x))

def isZero (v : SV) : Bool := v.all fun t => t.2.isZero

/-- Apply the 5×5 matrix `M` to the base-5 digit `i` of the key. -/
def applyLink (M : KMat) (i : Nat) (v : SV) : SV :=
  let p := 5 ^ i
  ofMap (v.foldl (init := (∅ : Std.HashMap Nat K)) fun m (key, c) =>
    let s := (key / p) % 5
    let base := key - s * p
    (List.range 5).foldl (init := m) fun m r =>
      let x := M[r]![s]!
      if x.isZero then m else accum m (base + r * p) (c * x))

end SV

/-- `W = ∑_{abce} U_l†(e,a) U_t†(c,e) U_r(b,c) U_b(a,b)` applied to `v` (links 0..3 = b r t l; `U[i][j]` are 5×5 matrices). -/
def applyW (U : Array (Array KMat)) (v : SV) : SV := Id.run do
  let mut out : SV := #[]
  for a in [0:2] do
    for b in [0:2] do
      for c in [0:2] do
        for e in [0:2] do
          let v1 := SV.applyLink (U[a]![b]!) 0 v
          let v2 := SV.applyLink (U[b]![c]!) 1 v1
          let v3 := SV.applyLink ((U[e]![c]!).conjT) 2 v2
          let v4 := SV.applyLink ((U[a]![e]!).conjT) 3 v3
          out := SV.add out v4
  return out

/-! ### parsing -/

structure SCert where
  corners : Array (Array (Nat × Nat))
  spinHalf : Array KMat
  gensL : Array KMat
  gensR : Array KMat
  uLink : Array (Array KMat)
  uPaulo : Array (Array KMat)
  vPaulo : KMat
  states : Array (Array (Nat × K))
  labelJ : Array (Array Nat × Array Nat)
  innerLabels : Array (Array Nat × Array Nat)
  kInner : KMat
  gauge : Array Int
  brightPairs : Array (Nat × Nat × K)
  darkRows : Array Nat
  spectrum : Array (Rat × Nat)
  outerKeys : Nat
  outerMax : Nat
  i6Edges : Nat
  i6Moduli : Array Rat
  i6Sizes : Array (Nat × Nat)
  i6Spectrum : Array (Rat × Nat)
  cornerDims : Array (Nat × Array Nat × Nat)
  symmetries : Array (String × Array Nat × Array Int)
  deriving Inhabited

def jsonRat (j : Json) : Except String Rat :=
  match j with
  | .str s => parseRat s
  | .num n => pure (mkRat n.mantissa (10 ^ n.exponent))
  | _ => throw "expected a number or a rational string"

def field (j : Json) (k : String) : Except String Json := j.getObjVal? k

def natArr (j : Json) : Except String (Array Nat) := do (← j.getArr?).mapM (·.getNat?)

def parseKMat (j : Json) : Except String KMat := do
  (← j.getArr?).mapM fun row => do (← row.getArr?).mapM parseK

def parseKMats (j : Json) : Except String (Array KMat) := do (← j.getArr?).mapM parseKMat

def parseLabel (j : Json) : Except String (Array Nat × Array Nat) := do
  pure (← natArr (← field j "j2"), ← natArr (← field j "J2"))

def parseSCert (j : Json) : Except String SCert := do
  let schema ← (← field j "schema").getStr?
  if schema != "su2plaq-structure-1" then throw s!"unknown schema {schema}"
  let corners ← (← (← field j "corners").getArr?).mapM fun c => do
    (← c.getArr?).mapM fun e => do
      let ea ← e.getArr?
      pure (← ea[0]!.getNat?, ← ea[1]!.getNat?)
  let spinHalf ← parseKMats (← field j "spin_half")
  let gens ← field j "gens"
  let gensL ← parseKMats (← field gens "L")
  let gensR ← parseKMats (← field gens "R")
  let uLink ← (← (← field j "u_link").getArr?).mapM parseKMats
  let uPaulo ← (← (← field j "u_paulo").getArr?).mapM parseKMats
  let vRows ← (← (← field j "v_paulo").getArr?).mapM fun r => do (← r.getArr?).mapM fun x => do
    let i ← x.getInt?
    pure (if i == 1 then K.one else if i == -1 then K.neg1 else K.zero)
  let sts ← (← (← field j "states").getArr?).mapM parseState
  let mut states : Array (Array (Nat × K)) := Array.replicate sts.size #[]
  let mut seen : Array Bool := Array.replicate sts.size false
  for (k, ts) in sts do
    if k ≥ sts.size then throw s!"state index {k} out of range"
    if seen[k]! then throw s!"duplicate state index {k}"
    seen := seen.set! k true
    states := states.set! k ts
  let labelJ ← (← (← field j "labels").getArr?).mapM parseLabel
  let innerLabels ← (← (← field j "inner_labels").getArr?).mapM parseLabel
  let kInner ← (← (← field j "k_inner").getArr?).mapM fun row => do
    (← row.getArr?).mapM fun x => do pure ({ a := ← jsonRat x } : K)
  let gauge ← (← (← field j "gauge").getArr?).mapM (·.getInt?)
  let brightPairs ← (← (← field j "bright_pairs").getArr?).mapM fun p => do
    let pr ← natArr (← field p "pair")
    pure (pr[0]!, pr[1]!, ({ a := ← jsonRat (← field p "coupling") } : K))
  let darkRows ← natArr (← field j "dark_rows")
  let parseSpec (x : Json) : Except String (Array (Rat × Nat)) := do
    (← x.getArr?).mapM fun t => do
      let ta ← t.getArr?
      pure (← jsonRat ta[0]!, ← ta[1]!.getNat?)
  let spectrum ← parseSpec (← field j "spectrum")
  let os ← field j "outer_support"
  let i6 ← field j "inner625"
  let i6Moduli ← (← (← field i6 "edge_moduli").getArr?).mapM jsonRat
  let i6Sizes ← (← (← field i6 "component_sizes").getArr?).mapM fun t => do
    let ta ← t.getArr?
    pure (← ta[0]!.getNat?, ← ta[1]!.getNat?)
  let cornerDims ← (← (← field j "corner_kernel_dims").getArr?).mapM fun t => do
    pure (← (← field t "corner").getNat?, ← natArr (← field t "j2"), ← (← field t "dim").getNat?)
  let symmetries ← (← (← field j "symmetries").getArr?).mapM fun s => do
    pure (← (← field s "name").getStr?, ← natArr (← field s "perm"), ← (← (← field s "signs").getArr?).mapM (·.getInt?))
  pure { corners, spinHalf, gensL, gensR, uLink, uPaulo, vPaulo := vRows, states, labelJ, innerLabels, kInner, gauge,
         brightPairs, darkRows, spectrum, outerKeys := ← (← field os "n_keys").getNat?,
         outerMax := ← (← field os "max_states").getNat?, i6Edges := ← (← field i6 "n_edges").getNat?, i6Moduli, i6Sizes,
         i6Spectrum := ← parseSpec (← field i6 "spectrum"), cornerDims, symmetries }

/-! ### the checks (each returns the first violated statement) -/

def Ki : K := K.I

/-- First (lowest-index) failure of `f 0, …, f (n-1)`, evaluated in parallel (pure tasks: schedule-independent). -/
def parFind (n : Nat) (f : Nat → Option String) : Option String :=
  ((List.range n).map fun k => Task.spawn fun _ => f k).foldl (fun r t => match r with
    | some e => some e
    | none => t.get) none
def firstSome (l : List (Option String)) : Option String := l.foldl (fun r x => match r with | some _ => r | none => x) none

/-- Lie-algebra relations `[X_x, X_y] = i X_z` (cyclic) for a triple of matrices. -/
def suRel (X : Array KMat) : Bool :=
  X.size == 3
    && ((KMat.comm X[0]! X[1]!).sub (X[2]!.scale Ki)).isZero
    && ((KMat.comm X[1]! X[2]!).sub (X[0]!.scale Ki)).isZero
    && ((KMat.comm X[2]! X[0]!).sub (X[1]!.scale Ki)).isZero

def checkAlgebra (c : SCert) : Option String :=
  if !suRel c.spinHalf then some "spin-1/2 matrices do not satisfy [S_x,S_y] = i S_z"
  else if !suRel c.gensL then some "left generators do not satisfy the su(2) relations"
  else if !suRel c.gensR then some "right generators do not satisfy the su(2) relations"
  else if !((List.range 3).all fun a => (List.range 3).all fun b => (KMat.comm c.gensL[a]! c.gensR[b]!).isZero) then
    some "left and right generators do not commute"
  else if c.uLink.size != 2 || c.uPaulo.size != 2 then some "link operators must be 2 x 2 arrays of 5 x 5 matrices"
  else
    let bad := (List.range 3).any fun a => (List.range 2).any fun i => (List.range 2).any fun j =>
      let u := c.uLink[i]![j]!
      let lhs := KMat.comm c.gensL[a]! u
      let rhsL := (List.range 2).foldl (fun acc k => acc.add (c.uLink[k]![j]!.scale (-(c.spinHalf[a]![i]![k]!)))) (KMat.zero 5 5)
      let lhsR := KMat.comm c.gensR[a]! u
      let rhsR := (List.range 2).foldl (fun acc k => acc.add ((c.uLink[i]![k]!).scale (c.spinHalf[a]![k]![j]!))) (KMat.zero 5 5)
      !((lhs.sub rhsL).isZero) || !((lhsR.sub rhsR).isZero)
    if bad then some "link operators are not covariant: [L_a,U_ij] = -(T_a U)_ij or [R_a,U_ij] = (U T_a)_ij fails" else none

/-- Paulo's operators are the CG ones in the signed-permutation basis `V`: `V U_ij V^T = U^Paulo_ij`. -/
def checkPaulo (c : SCert) : Option String :=
  let v := c.vPaulo
  let isPerm := (List.range 5).all fun i =>
    ((List.range 5).filter fun j => !(v[i]![j]!).isZero).length == 1
  if v.rows != 5 || v.cols != 5 || !isPerm || !((v.mul v.conjT).sub (KMat.ident 5)).isZero then
    some "the Paulo adapter is not a signed permutation matrix"
  else if (List.range 2).any fun i => (List.range 2).any fun j =>
      !(((v.mul c.uLink[i]![j]!).mul v.conjT).sub c.uPaulo[i]![j]!).isZero then
    some "Paulo's link operators are not V U V^T"
  else none

def digit (key i : Nat) : Nat := (key / 5 ^ i) % 5

def genOp (c : SCert) (a : Nat) (role : Nat) : KMat := if role == 0 then c.gensL[a]! else c.gensR[a]!

/-- Gauss law at every corner and a, and the link spins j_l of the labels. -/
def gaussState (c : SCert) (k : Nat) : Option String :=
  let psi : SV := (c.states[k]!).qsort fun x y => x.1 < y.1
  let lab := c.labelJ[k]!
  let spinBad := psi.any fun (key, _) => (List.range 12).any fun i =>
    (if digit key i == 0 then 0 else 1) != lab.1[i]!
  if spinBad then some s!"state {k}: link spins differ from its label"
  else
    (List.range c.corners.size).findSome? fun ci =>
      let ends := c.corners[ci]!
      (List.range 3).findSome? fun a =>
        let tot := ends.foldl (init := (#[] : SV)) fun acc (link, role) =>
          SV.add acc (SV.applyLink (genOp c a role) link psi)
        if SV.isZero tot then none else some s!"state {k}: Gauss law fails at corner {ci}"

def checkGaussAndSpins (c : SCert) : Option String := parFind c.states.size (gaussState c)

/-- Inner-pair spin of every corner: `Ĵ² ψ = J (J+1) ψ`. -/
def innerSpinState (c : SCert) (k : Nat) : Option String :=
  let psi : SV := (c.states[k]!).qsort fun x y => x.1 < y.1
  let lab := c.labelJ[k]!
  (List.range c.corners.size).findSome? fun ci =>
    let ends := c.corners[ci]!
    let pair := #[ends[0]!, ends[1]!]
    let cas := (List.range 3).foldl (init := (#[] : SV)) fun acc a =>
      let v1 := pair.foldl (init := (#[] : SV)) fun s (link, role) => SV.add s (SV.applyLink (genOp c a role) link psi)
      let v2 := pair.foldl (init := (#[] : SV)) fun s (link, role) => SV.add s (SV.applyLink (genOp c a role) link v1)
      SV.add acc v2
    let J2 := lab.2[ci]!
    let lam : Rat := mkRat ((J2 * (J2 + 2) : Nat) : Int) 4
    let diff := SV.add cas (SV.scale ({ a := -lam } : K) psi)
    if SV.isZero diff then none else some s!"state {k}: inner-pair spin at corner {ci} differs from its label"

def checkInnerSpins (c : SCert) : Option String := parFind c.states.size (innerSpinState c)

/-- Index of the inner label of every state, or an error; also checks that `innerLabels` lists exactly the inner labels in use. -/
def innerIndex (c : SCert) : Except String (Array Nat) := do
  let mut map : Std.HashMap (List Nat) Nat := ∅
  for i in [0:c.innerLabels.size] do
    let (j, J) := c.innerLabels[i]!
    let key := j.toList ++ J.toList
    if map.contains key then throw "duplicate inner label"
    map := map.insert key i
  let mut idx : Array Nat := #[]
  let mut used : Array Bool := Array.replicate c.innerLabels.size false
  for k in [0:c.states.size] do
    let (j, J) := c.labelJ[k]!
    match map.get? ((j.toList.take 4) ++ J.toList) with
    | some i => idx := idx.push i; used := used.set! i true
    | none => throw s!"state {k}: inner label is not in the list"
  if !(used.all id) then throw "an inner label is not carried by any state"
  pure idx

/-- Exact `H_B^phys = -(A + A†)`, `A[k',k] = ⟨ψ_k'| W ψ_k⟩`, as a hash map keyed by `k' * n + k`. -/
def computeHB (c : SCert) : Std.HashMap Nat K :=
  let n := c.states.size
  let inv : Std.HashMap Nat (Array (Nat × K)) :=
    c.states.zipIdx.foldl (init := ∅) fun acc (st, k) =>
      st.foldl (init := acc) fun acc (key, a) => acc.insert key ((acc.getD key #[]).push (k, a))
  let A : Std.HashMap Nat K := (List.range n).foldl (init := ∅) fun acc k =>
    let w := applyW c.uLink ((c.states[k]!).qsort fun x y => x.1 < y.1)
    w.foldl (init := acc) fun acc (key, val) =>
      (inv.getD key #[]).foldl (init := acc) fun acc (k', a') => SV.accum acc (k' * n + k) (a'.conj * val)
  A.fold (init := (∅ : Std.HashMap Nat K)) fun H key v =>
    let k' := key / n
    let k := key % n
    SV.accum (SV.accum H (k' * n + k) (-v)) (k * n + k') (-(v.conj))

def outerKey (c : SCert) (k : Nat) : List Nat := (c.labelJ[k]!.1.toList.drop 4)

def checkHB (c : SCert) (idx : Array Nat) (H : Std.HashMap Nat K) : Option String :=
  let n := c.states.size
  if c.gauge.size != n || !(c.gauge.all fun g => g == 1 || g == -1) then some "gauge must be +-1 on every state"
  else if c.kInner.rows != c.innerLabels.size || c.kInner.cols != c.innerLabels.size then some "K_inner has the wrong size"
  else
    let expected (k l : Nat) : K :=
      if outerKey c k == outerKey c l then
        ({ a := ((c.gauge[k]! * c.gauge[l]! : Int) : Rat) } : K) * c.kInner[idx[k]!]![idx[l]!]!
      else K.zero
    let groups : Std.HashMap (List Nat) (Array Nat) :=
      (List.range n).foldl (init := ∅) fun acc k => acc.insert (outerKey c k) ((acc.getD (outerKey c k) #[]).push k)
    let badGroup := groups.fold (init := (none : Option String)) fun r _ ks =>
      match r with
      | some _ => r
      | none =>
        ks.findSome? fun k => ks.findSome? fun l =>
          if H.getD (k * n + l) K.zero == expected k l then none
          else some s!"H_B[{k},{l}] differs from D K_inner D inside an outer block"
    match badGroup with
    | some e => some e
    | none =>
      H.fold (init := none) fun r key v =>
        match r with
        | some _ => r
        | none =>
          let k := key / n
          let l := key % n
          if v == expected k l then none else some s!"H_B[{k},{l}] is nonzero between outer blocks or differs from D K D"

def checkKInner (c : SCert) : Option String :=
  let m := c.innerLabels.size
  let sym := (List.range m).all fun a => (List.range m).all fun b => c.kInner[a]![b]! == c.kInner[b]![a]!
  if !sym then some "K_inner is not symmetric"
  else
    let nz := (List.range m).foldl (init := 0) fun acc a =>
      acc + ((List.range m).filter fun b => !(c.kInner[a]![b]!).isZero).length
    let pairsOk := c.brightPairs.all fun (i, j, k) =>
      i < j && j < m && !k.isZero && c.kInner[i]![j]! == k && c.kInner[j]![i]! == k
    let rowsOf := c.brightPairs.foldl (init := ([] : List Nat)) fun acc (i, j, _) => i :: j :: acc
    let distinct := (rowsOf.eraseDups).length == rowsOf.length
    let darkOk := c.darkRows.all fun r => r < m && (c.kInner[r]!).all (·.isZero)
    let jOk := (List.range m).all fun a => (List.range m).all fun b =>
      (c.kInner[a]![b]!).isZero || c.innerLabels[a]!.2 == c.innerLabels[b]!.2
    if !pairsOk then some "a bright pair does not match K_inner"
    else if nz != 2 * c.brightPairs.size then some "K_inner has entries outside the bright pairs"
    else if !distinct then some "bright pairs overlap"
    else if !darkOk then some "a dark row of K_inner is not zero"
    else if c.darkRows.size + 2 * c.brightPairs.size != m || ((c.darkRows.toList ++ rowsOf).eraseDups).length != m then
      some "bright pairs and dark rows do not partition the inner labels"
    else if !jOk then some "K_inner does not conserve J_c"
    else none

/-- Connected components of an undirected graph on `0..n-1` given by an edge list. -/
def components (n : Nat) (edges : List (Nat × Nat)) : Array (Array Nat) := Id.run do
  let mut parent : Array Nat := Array.range n
  for (a, b) in edges do
    let mut ra := a
    for _ in [0:n] do
      if parent[ra]! != ra then ra := parent[ra]!
    let mut rb := b
    for _ in [0:n] do
      if parent[rb]! != rb then rb := parent[rb]!
    if ra != rb then parent := parent.set! ra rb
  let mut groups : Std.HashMap Nat (Array Nat) := ∅
  for v in [0:n] do
    let mut r := v
    for _ in [0:n] do
      if parent[r]! != r then r := parent[r]!
    groups := groups.insert r ((groups.getD r #[]).push v)
  return (groups.fold (fun acc _ g => acc.push g) #[]).qsort fun x y => x[0]! < y[0]!

def lambdaSet : List Rat := [-2, -1, -1/2, 0, 1/2, 1, 2]

/-- Multiplicities of the eigenvalues in `lambdaSet` of a Hermitian matrix given by block structure and entries. -/
def spectrumOf (n : Nat) (entry : Nat → Nat → K) (edges : List (Nat × Nat)) : List (Rat × Nat) :=
  let comps := components n edges
  lambdaSet.map fun lam =>
    let mult := comps.foldl (init := 0) fun acc ks =>
      let blk : KMat := ks.map fun k => ks.map fun l => entry k l + (if k == l then ({ a := -lam } : K) else K.zero)
      acc + (ks.size - kRank blk)
    (lam, mult)

def checkSpectrum (c : SCert) (H : Std.HashMap Nat K) : Option String :=
  let n := c.states.size
  let edges := H.fold (init := ([] : List (Nat × Nat))) fun acc key _ =>
    let k := key / n
    let l := key % n
    if k < l then (k, l) :: acc else acc
  let got := spectrumOf n (fun k l => H.getD (k * n + l) K.zero) edges
  let claimed := c.spectrum.toList
  if got != claimed then some s!"spectrum multiplicities differ: recomputed {got.map (fun (l, m) => (ratStr l, m))}"
  else if (got.foldl (fun a (_, m) => a + m) 0) != n then some "the spectrum is not contained in {0, +-1/2, +-1, +-2}"
  else none

def checkOuterSupport (c : SCert) : Option String :=
  let m : Std.HashMap Nat (Std.HashSet Nat) :=
    c.states.zipIdx.foldl (init := ∅) fun acc (st, k) =>
      st.foldl (init := acc) fun acc (key, _) => acc.insert (key / 625) ((acc.getD (key / 625) ∅).insert k)
  let mx := m.fold (fun a _ s => max a s.size) 0
  if m.size != c.outerKeys || mx != c.outerMax then
    some s!"outer support differs: {m.size} patterns, max {mx} states"
  else none

/-- The 625 × 625 inner operator `-(W + W†)` in Paulo's basis. -/
def checkInner625 (c : SCert) : Option String :=
  let n := 625
  let M : Std.HashMap Nat K :=
    (List.range n).foldl (init := ∅) fun acc col =>
      (applyW c.uPaulo #[(col, K.one)]).foldl (init := acc) fun acc (row, w) =>
        SV.accum (SV.accum acc (row * n + col) (-w)) (col * n + row) (-(w.conj))
  let M := M.filter fun _ v => !v.isZero
  let herm := M.fold (init := true) fun ok key v =>
    ok && M.getD ((key % n) * n + key / n) K.zero == v.conj
  let edgeList := M.fold (init := ([] : List (Nat × Nat))) fun acc key _ =>
    if key / n < key % n then (key / n, key % n) :: acc else acc
  let sq := edgeList.map fun (i, j) => let v := M.getD (i * n + j) K.zero; v * v.conj
  let sqOk := sq.all fun s => s.isRat
  let claimedSq := (c.i6Moduli.toList.map fun r => r * r)
  let gotSq := (sq.map fun s => s.a).eraseDups
  let comps := components n edgeList
  let sizes := (comps.toList.map (·.size)).eraseDups.map fun s => (s, (comps.toList.filter fun g => g.size == s).length)
  if !herm then some "inner operator is not Hermitian"
  else if !sqOk then some "an edge modulus of the inner operator is not rational"
  else if edgeList.length != c.i6Edges then some s!"inner operator has {edgeList.length} edges, claimed {c.i6Edges}"
  else if (gotSq.toArray.qsort (· < ·)).toList != (claimedSq.toArray.qsort (· < ·)).toList then
    some "edge moduli of the inner operator differ from the claim"
  else if (sizes.toArray.qsort fun x y => x.1 < y.1).toList != c.i6Sizes.toList then
    some s!"component sizes of the inner operator differ: {sizes}"
  else
    let got := spectrumOf n (fun k l => M.getD (k * n + l) K.zero) edgeList
    if got != c.i6Spectrum.toList then some s!"inner operator spectrum differs: {got.map (fun (l, m) => (ratStr l, m))}"
    else if (got.foldl (fun a (_, m) => a + m) 0) != n then some "inner operator spectrum leaves {0, +-1/2, +-1, +-2}"
    else none

/-- Kernel dimension of the corner Casimir on the product of the spin-1/2 ends (those with `j2 = 1`). -/
def cornerKernelDim (c : SCert) (ends : Array (Nat × Nat)) (j2 : Array Nat) : Nat :=
  let half := (List.range 4).filter fun e => j2[e]! == 1
  let nh := half.length
  let dim := 2 ^ nh
  let bitOf (i p : Nat) : Nat := (i / 2 ^ p) % 2
  let embed (op : KMat) (p : Nat) : KMat :=
    (Array.range dim).map fun i => (Array.range dim).map fun j =>
      if (List.range nh).all fun q => q == p || bitOf i q == bitOf j q then op[bitOf i p]![bitOf j p]! else K.zero
  let cas := (List.range 3).foldl (init := KMat.zero dim dim) fun acc a =>
    let tot := (half.zipIdx).foldl (init := KMat.zero dim dim) fun t (e, p) =>
      let s := c.spinHalf[a]!
      -- an 'out' end carries L = -S^T (plain transpose), an 'in' end R = S
      let gT := if (ends[e]!).2 == 0 then
          (Array.range 2).map fun i => (Array.range 2).map fun j => -(s[j]![i]!)
        else s
      t.add (embed gT p)
    acc.add (tot.mul tot)
  dim - kRank cas

def checkCorners (c : SCert) : Option String :=
  if c.corners.size != 4 then some "expected four corners"
  else
    let bad := c.cornerDims.findSome? fun (ci, j2, d) =>
      if ci ≥ 4 || j2.size != 4 then some "malformed corner dimension entry"
      else if cornerKernelDim c c.corners[ci]! j2 != d then
        some s!"corner {ci}: Casimir kernel dimension differs from the claim"
      else none
    match bad with
    | some e => some e
    | none =>
      let table : Std.HashMap (Nat × List Nat) Nat :=
        c.cornerDims.foldl (init := ∅) fun m (ci, j2, d) => m.insert (ci, j2.toList) d
      let total := (List.range 4096).foldl (init := 0) fun acc code =>
        let spin (l : Nat) : Nat := (code / 2 ^ l) % 2
        acc + (List.range 4).foldl (init := 1) fun p ci =>
          let key := (c.corners[ci]!).toList.map fun (link, _) => spin link
          p * table.getD (ci, key) 0
      if total != c.states.size then some s!"corner kernel dimensions give {total} states, not {c.states.size}" else none

def checkSymmetries (c : SCert) (H : Std.HashMap Nat K) : Option String :=
  let n := c.states.size
  let eIn (k : Nat) : Nat := (c.labelJ[k]!.1.toList.take 4).foldl (fun a j => a + j * (j + 2)) 0
  c.symmetries.findSome? fun (name, perm, signs) =>
    let isPerm := perm.size == n && (perm.toList.eraseDups).length == n && perm.all (· < n)
    if !isPerm || signs.size != n || !(signs.all fun s => s == 1 || s == -1) then some s!"symmetry {name}: not a signed permutation"
    else if !((List.range n).all fun k => eIn (perm[k]!) == eIn k) then some s!"symmetry {name} does not preserve the inner electric energy"
    else
      let ok := H.fold (init := true) fun ok key v =>
        ok && (let k := key / n; let l := key % n
               H.getD (perm[k]! * n + perm[l]!) K.zero == ({ a := ((signs[k]! * signs[l]! : Int) : Rat) } : K) * v)
      if !ok then some s!"symmetry {name} does not commute with H_B"
      else if (H.fold (init := 0) fun a key _ => a + (if H.contains ((perm[key / n]!) * n + perm[key % n]!) then 1 else 0)) != H.size then
        some s!"symmetry {name} does not map the support of H_B into itself"
      else none

/-- The checks in order, with names (used for timing and for the first-failure report). -/
def SCert.steps (c : SCert) : List (String × (Unit → Option String)) :=
  let shared : Thunk (Except String (Array Nat × Std.HashMap Nat K)) := Thunk.mk fun _ =>
    match innerIndex c with
    | .error e => .error e
    | .ok idx => .ok (idx, computeHB c)
  let idxH : Unit → Except String (Array Nat × Std.HashMap Nat K) := fun _ => shared.get
  [("count", fun _ => if c.states.size != physicalDim then some s!"expected {physicalDim} states, found {c.states.size}"
                       else if c.labelJ.size != c.states.size then some "one label per state is required"
                       else if c.states.any (·.isEmpty) then some "empty state" else none),
   ("gram", fun _ => Cert.gramErrorOf c.states),
   ("algebra", fun _ => checkAlgebra c),
   ("paulo", fun _ => checkPaulo c),
   ("gauss", fun _ => checkGaussAndSpins c),
   ("inner-spins", fun _ => checkInnerSpins c),
   ("H_B", fun _ => match idxH () with
                    | .error e => some e
                    | .ok (idx, H) => checkHB c idx H),
   ("K_inner", fun _ => checkKInner c),
   ("spectrum", fun _ => match idxH () with
                         | .error e => some e
                         | .ok (_, H) => checkSpectrum c H),
   ("outer-support", fun _ => checkOuterSupport c),
   ("inner625", fun _ => checkInner625 c),
   ("corners", fun _ => checkCorners c),
   ("symmetries", fun _ => match idxH () with
                           | .error e => some e
                           | .ok (_, H) => checkSymmetries c H)]

def SCert.check (c : SCert) : Option String :=
  firstSome (c.steps.map fun (_, f) => f ())

def checkStructurePath (path : String) : IO (Option String) := do
  try
    let txt ← IO.FS.readFile path
    match Json.parse txt with
    | .error e => pure (some s!"json: {e}")
    | .ok j =>
      match parseSCert j with
      | .error e => pure (some e)
      | .ok c =>
        -- sequential, stop at the first violated statement; SU2PLAQ_TIMING=1 prints the wall time of every step to stderr
        let timing := (← IO.getEnv "SU2PLAQ_TIMING").isSome
        let mut result : Option String := none
        for (name, f) in c.steps do
          if result.isNone then
            let t0 ← IO.monoMsNow
            let r := f ()
            let r ← IO.lazyPure fun _ => r
            let t1 ← IO.monoMsNow
            if timing then IO.eprintln s!"[structure] {name}: {t1 - t0} ms {if r.isNone then "ok" else "FAILED"}"
            result := r
        pure result
  catch e => pure (some s!"cannot read {path}: {e}")

end Su2PlaqCert
