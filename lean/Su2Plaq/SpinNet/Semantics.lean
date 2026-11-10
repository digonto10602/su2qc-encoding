import Su2Plaq.SpinNet.Recoupling

/-!
# Su2Plaq.SpinNet.Semantics -- exact gate semantics of the 48-gate `build_UB` (M3x step W2, prompts/102 section 1)

Mathlib-free.  Qubits are little-endian (basis index `i = sum_q b_q 2^q`), 15 wires (data `0..7`, ancillas `8..14`).
Amplitudes live in `Z[i][z, z^-1]` with `z = e^{i beta/4}` (`Lau`, sorted `(exponent, re, im)` lists), so one
computation is exact for all `beta`.  The Hadamards contribute a global `(1/sqrt 2)^h` that is kept as the count `h`.
Gate matrices are Qiskit's: `x`, `cx` permutations, `h`, `rz(theta) = diag(e^{-i theta/2}, e^{i theta/2})` with
`theta = a beta / 2` (`diag(z^{-a}, z^{a})`), and `rccx` = `RCCXGate` (relative-phase Toffoli: `i` for `t: 0 -> 1`,
`-i` for `t: 1 -> 0` when both controls are 1; `-1` on `|a=1, b=0, t=1>`).  The gate semantics are tied to Qiskit's
matrices in the locked test `test_M3X_W2_semantics_gate_list_and_qiskit_matrices` (via `lean_gate_images`).

* `ub_h_count` : the circuit has two Hadamards, so `runGates ubGates` is `2 e^{-i beta K}` on the data.
* `ub_exact_all_codes` : for every valid inner code `y` (ancillas 0), `runGates ubGates |y>` equals
  `(z^{4k} + z^{-4k})|y> - (z^{4k} - z^{-4k})|y xor 15>` (`4k = 2 (2K)`; dark codes: `2|y>`) exactly, with `2K` from the
  6j symbols (`twoK?`).  This one equality gives block exactness, zero leakage, clean ancillas and the sign convention
  `e^{-i beta K}` for all `beta`.

`ubGates` between the generated markers is rendered from `build_UB(1.0)` by
`su2plaq.spinnet.lean_export.write_lean_exact_tables`; never edit it by hand.
Prototype: `scratch/planner/lean/SpinNetExact.lean` (section C).
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.SpinNet

/-! ## C. exact gate semantics -/

/-- Laurent polynomial in `z` with Gaussian-integer coefficients: sorted list of `(exponent, re, im)`, no zeros -/
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
/-- multiply by the unit `c * z^m`, `c ∈ {1, -1, i, -i}` given as `(re, im)` -/
def Lau.unit (m : Int) (re im : Int) (a : Lau) : Lau :=
  a.map fun t => (t.1 + m, t.2.1 * re - t.2.2 * im, t.2.1 * im + t.2.2 * re)

/-- sparse state vector: sorted `(basis index, coefficient)`; global factor `(1/√2)^h` kept as `h` -/
abbrev Vec := List (Nat × Lau)

def Vec.insert (i : Nat) (c : Lau) : Vec → Vec
  | [] => if c.isEmpty then [] else [(i, c)]
  | (u :: us) =>
    if i < u.1 then (if c.isEmpty then u :: us else (i, c) :: u :: us)
    else if i == u.1 then
      let s := Lau.add c u.2
      if s.isEmpty then us else (i, s) :: us
    else u :: Vec.insert i c us

inductive Gate where
  | x (q : Nat)
  | cx (c t : Nat)
  | rccx (a b t : Nat)
  | h (q : Nat)
  | rz (q : Nat) (a : Int)   -- angle a * beta / 2

/-- one basis vector `|i⟩` with coefficient `c` through a gate; Qiskit matrices: `rccx` = relative-phase Toffoli
(`|a=1,b=1,t⟩ ↦ i^{±1}|a,b,¬t⟩`: phase `i` for t=0→1, `-i` for t=1→0; `|a=1,b=0,t=1⟩ ↦ -|…⟩`), `h`, `rz(θ) = diag(e^{-iθ/2}, e^{iθ/2})` with θ = aβ/2, z = e^{iβ/4} -/
def applyBasis (g : Gate) (i : Nat) (c : Lau) : List (Nat × Lau) :=
  match g with
  | .x q => [(i ^^^ (1 <<< q), c)]
  | .cx a t => [(if bitOf i a == 1 then i ^^^ (1 <<< t) else i, c)]
  | .rccx a b t =>
    if bitOf i a == 1 && bitOf i b == 1 then
      (if bitOf i t == 0 then [(i ^^^ (1 <<< t), c.unit 0 0 1)] else [(i ^^^ (1 <<< t), c.unit 0 0 (-1))])
    else if bitOf i a == 1 && bitOf i b == 0 && bitOf i t == 1 then [(i, c.unit 0 (-1) 0)]
    else [(i, c)]
  | .h q =>
    let i0 := if bitOf i q == 1 then i ^^^ (1 <<< q) else i
    let i1 := i ||| (1 <<< q)
    if bitOf i q == 0 then [(i0, c), (i1, c)] else [(i0, c), (i1, c.unit 0 (-1) 0)]
  | .rz q a => [(i, if bitOf i q == 0 then c.unit (-a) 1 0 else c.unit a 1 0)]

def applyGate (g : Gate) (v : Vec) : Vec :=
  v.foldl (fun acc (p : Nat × Lau) => (applyBasis g p.1 p.2).foldl (fun acc' (q : Nat × Lau) => acc'.insert q.1 q.2) acc) []

def runGates (gs : List Gate) (v : Vec) : Vec := gs.foldl (fun acc g => applyGate g acc) v

-- BEGIN generated exact (su2plaq.spinnet.lean_export.write_lean_exact_tables; do not edit by hand)
/-- `build_UB(1.0)` gate list rendered from the Qiskit circuit (rz angles in units of `beta / 2`) -/
def ubGates : List Gate := [.cx 1 3, .cx 0 1, .cx 0 2, .h 0, .x 4, .x 5, .x 6, .x 7, .rccx 4 5 8, .rccx 6 7 9, .rccx 8 9 10, .x 2, .x 3, .rccx 2 3 11, .rccx 10 11 12, .x 1, .rccx 12 1 13, .x 1, .rccx 12 1 14, .rz 0 (-7), .cx 10 0, .rz 0 (-2), .cx 10 0, .cx 13 0, .rz 0 6, .cx 13 0, .cx 14 0, .rz 0 3, .cx 14 0, .rccx 12 1 14, .x 1, .rccx 12 1 13, .x 1, .rccx 10 11 12, .rccx 2 3 11, .x 3, .x 2, .rccx 8 9 10, .rccx 6 7 9, .rccx 4 5 8, .x 7, .x 6, .x 5, .x 4, .h 0, .cx 0 2, .cx 0 1, .cx 1 3]
-- END generated exact

/-- number of `h` gates (global factor `(1/√2)^h`; here 2, so the exact output is `run / 2`) -/
def hCount (gs : List Gate) : Nat := gs.foldl (fun n g => match g with | .h _ => n + 1 | _ => n) 0

/-- `2 · e^{-iβK}|y⟩ = (z^{4k} + z^{-4k})|y⟩ − (z^{4k} − z^{-4k})|y ^^^ 15⟩`, `4k = 2 · (2K)`; dark: `2|y⟩` -/
def target (y : Nat) (twoK : Int) : Vec :=
  let m := 2 * twoK
  if m == 0 then [(y, [(0, 2, 0)])]
  else
    let diag : Lau := Lau.insert (m, 1, 0) (Lau.insert (-m, 1, 0) [])
    let off : Lau := Lau.insert (m, -1, 0) (Lau.insert (-m, 1, 0) [])
    Vec.insert y diag (Vec.insert (y ^^^ 15) off [])

theorem ub_h_count : hCount ubGates = 2 := by decide

/-- the 48-gate circuit maps every valid inner code (ancillas 0) exactly to `e^{-i beta K}` of it, for all `beta` -/
theorem ub_exact_all_codes :
    validCodes.all (fun y => runGates ubGates [(y, [(0, 1, 0)])] == target y ((twoK? y).getD 999)) = true := by
  decide

end Su2Plaq.SpinNet
