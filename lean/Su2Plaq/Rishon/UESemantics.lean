import Su2Plaq.Rishon.JW

/-!
# Su2Plaq.Rishon.UESemantics -- exact gate semantics of `build_UE` (M5x step W3)

prompts/202 section 1 (W3), docs/METHODS-rishon.md R9.  Mathlib-free; every proof is `decide +kernel`.

Coefficient ring `Z[i][z, z^-1]` with `z = e^{i alpha/4}`: `Lau` is a sorted list of `(exponent, re, im)` (a Laurent
polynomial with Gaussian-integer coefficients), `Vec` a sorted list of `(basis index, Lau)`.  Gates are Qiskit's
`x`, `cx` (little-endian permutation) and `p q a` = `PhaseGate(a alpha/4) = diag(1, z^a)`; `build_UE` uses `a = -3`.
The gate lists `ueGates` (the 16-qubit inner step, 12 gates) and `ueOuterGates` (the 48-qubit variant with the outer
electric row, 36 gates) are rendered from the Qiskit circuits by `su2plaq.rishon.lean_export.write_lean_ue_gates`
between the BEGIN/END markers below; nothing in that block is typed in.

* `ue_gadget_sector`: the three-gate gadget on one link acts on each of the six sector codes as the phase `z^-3` on the
  quartet `linkQ` and `z^0` on the two other codes (the parity trick is checked, not assumed).
* `ue_gates_structure`, `ue_outer_gates_structure`: the rendered lists are 4 resp. 12 consecutive gadgets.
* `ue_exact_all_codes`: for all 1296 inner codes `y`, running `ueGates` on `|y>` gives exactly `z^(-3 #Q(y))|y>`
  (all `alpha` at once).
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0
set_option synthInstance.maxSize 10000
set_option synthInstance.maxHeartbeats 200000

namespace Su2Plaq.Rishon

abbrev Lau := List (Int × Int × Int)

def Lau.insert (t : Int × Int × Int) : Lau → Lau
  | [] => if t.2.1 == 0 && t.2.2 == 0 then [] else [t]
  | (u :: us) =>
    if t.1 < u.1 then (if t.2.1 == 0 && t.2.2 == 0 then u :: us else t :: u :: us)
    else if t.1 == u.1 then
      let re := t.2.1 + u.2.1
      let im := t.2.2 + u.2.2
      if re == 0 && im == 0 then us else (t.1, re, im) :: us
    else u :: Lau.insert t us
def Lau.add (a b : Lau) : Lau := a.foldl (fun acc t => acc.insert t) b
def Lau.unit (m : Int) (re im : Int) (a : Lau) : Lau :=
  a.map fun t => (t.1 + m, t.2.1 * re - t.2.2 * im, t.2.1 * im + t.2.2 * re)

abbrev Vec := List (Nat × Lau)
def Vec.insert (i : Nat) (c : Lau) : Vec → Vec
  | [] => if c.isEmpty then [] else [(i, c)]
  | (u :: us) =>
    if i < u.1 then (if c.isEmpty then u :: us else (i, c) :: u :: us)
    else if i == u.1 then
      let s := Lau.add c u.2
      if s.isEmpty then us else (i, s) :: us
    else u :: Vec.insert i c us

def bitOf (i q : Nat) : Nat := (i / 2 ^ q) % 2

inductive Gate where
  | x (q : Nat)
  | cx (c t : Nat)
  | p (q : Nat) (a : Int)     -- PhaseGate(a * alpha / 4) = diag(1, z^a)
  deriving DecidableEq, BEq, Repr

def applyBasis (g : Gate) (i : Nat) (c : Lau) : List (Nat × Lau) :=
  match g with
  | .x q => [(i ^^^ (1 <<< q), c)]
  | .cx a t => [(if bitOf i a == 1 then i ^^^ (1 <<< t) else i, c)]
  | .p q a => [(i, if bitOf i q == 1 then c.unit a 1 0 else c)]

def applyGate (g : Gate) (v : Vec) : Vec :=
  v.foldl (fun acc (p : Nat × Lau) => (applyBasis g p.1 p.2).foldl (fun acc' (q : Nat × Lau) => acc'.insert q.1 q.2) acc) []
def runGates (gs : List Gate) (v : Vec) : Vec := gs.foldl (fun acc g => applyGate g acc) v

def one : Lau := [(0, 1, 0)]

/-- the per-link gadget of METHODS-rishon R7 on qubits (4l, 4l+1) -/
def gadget (l : Nat) : List Gate := [.cx (4 * l) (4 * l + 1), .p (4 * l + 1) (-3), .cx (4 * l) (4 * l + 1)]

-- BEGIN generated exact (su2plaq.rishon.lean_export.write_lean_ue_gates; do not edit by hand)
def ueGates : List Gate := [.cx 0 1, .p 1 (-3), .cx 0 1, .cx 4 5, .p 5 (-3), .cx 4 5, .cx 8 9, .p 9 (-3), .cx 8 9, .cx 12 13, .p 13 (-3), .cx 12 13]
def ueOuterGates : List Gate := [.cx 0 1, .p 1 (-3), .cx 0 1, .cx 4 5, .p 5 (-3), .cx 4 5, .cx 8 9, .p 9 (-3), .cx 8 9, .cx 12 13, .p 13 (-3), .cx 12 13, .cx 16 17, .p 17 (-3), .cx 16 17, .cx 20 21, .p 21 (-3), .cx 20 21, .cx 24 25, .p 25 (-3), .cx 24 25, .cx 28 29, .p 29 (-3), .cx 28 29, .cx 32 33, .p 33 (-3), .cx 32 33, .cx 36 37, .p 37 (-3), .cx 36 37, .cx 40 41, .p 41 (-3), .cx 40 41, .cx 44 45, .p 45 (-3), .cx 44 45]
-- END generated exact

def linkCode (y l : Nat) : Nat := (y / 16 ^ l) % 16
def innerCodes : List Nat :=
  sector.flatMap fun a => sector.flatMap fun b => sector.flatMap fun c => sector.map fun d => a + 16 * b + 256 * c + 4096 * d
def nQ (y : Nat) : Nat := (List.range 4).foldl (fun n l => if linkQ.contains (linkCode y l) then n + 1 else n) 0
def ueTarget (y : Nat) : Vec := [(y, [(-3 * (nQ y : Int), 1, 0)])]

theorem card_inner_codes : innerCodes.length = 1296 := by decide +kernel

/-- gadget on one link: every sector code is an eigenvector, phase z^{-3} exactly on the quartet -/
theorem ue_gadget_sector : sector.all (fun s =>
    runGates (gadget 0) [(s, one)] == [(s, [(if linkQ.contains s then -3 else 0, 1, 0)])]) = true := by
  decide +kernel

theorem ue_gates_structure : ueGates = (List.range 4).flatMap gadget := by decide +kernel
theorem ue_outer_gates_structure : ueOuterGates = (List.range 12).flatMap gadget := by decide +kernel

/-- build_UE maps every valid inner code exactly to z^{-3 #Q}|y>, for all alpha -/
theorem ue_exact_all_codes : innerCodes.all (fun y => runGates ueGates [(y, one)] == ueTarget y) = true := by
  decide +kernel

end Su2Plaq.Rishon
