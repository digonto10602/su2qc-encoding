import Su2Plaq.SpinNet.Counts

/-!
# Su2Plaq.SpinNet.Circuit — kernel-checked structure of the general spin-network circuit (M3, prompts/100 §1.5, §1.8)

Model of the classical skeleton of `build_UB` (`src/su2plaq/spinnet/walk.py`, `GENERAL7`) on bit patterns
(computational-basis codes, `Nat` with bit operations).  Wires: data `0..7` (bits `0..3` = `j_b j_r j_t j_l`, bits
`4..7` = corner bits `c0..c3`), ancillas `8..14` = `(A, B, F, P, Q, G1, G2)`.  The relative-phase Toffolis (`rccx`)
are read with Toffoli semantics on bits: the segment between compute and uncompute is diagonal (`Su2Plaq.sandwich`).

* `frame_maps_flip` : the CX frame `cx(1,3); cx(0,1); cx(0,2)` maps the four-link flip to `X` on the target wire 0.
* `flags_correct`   : the flag chain computes `F` (all corner bits 0), `G1 = F ∧ [m = 000]`, `G2 = F ∧ [m = 100]`
  (`m = (m1, m2, m3)` = bits 1..3 of the framed code, `m1` the most significant).
* `walk_table_exact`: the integer Walsh angle table (units of `beta / 2`, `rz` slots of the walk on the frame
  target) reproduces `2 · (2 K)` on all 47 valid inner codes.

The tables `validInnerCodes`, `couplingTable`, `angleTable` between the generated markers are written by
`su2plaq.spinnet.lean_export.write_lean_tables` from the Python objects; never edit them by hand.
Every theorem is proved by `decide` (standard axioms only).
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.SpinNet

-- BEGIN generated (su2plaq.spinnet.lean_export.write_lean_tables; do not edit by hand)
/-- the 47 valid inner codes (bits 0..3 = j_b j_r j_t j_l, bits 4..7 = corner bits), sorted -/
def validInnerCodes : List Nat := [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 25, 27, 29, 31, 35, 39, 43, 47, 59, 63, 70, 71, 78, 79, 95, 103, 111, 127, 140, 141, 142, 143, 157, 159, 175, 191, 206, 207, 223, 239, 255]
/-- `2 K[partner, code]` for the codes of `validInnerCodes` -/
def couplingTable : List Int := [-4, 2, 2, 2, 2, -1, 2, 2, 2, 2, -1, 2, 2, 2, 2, -4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
/-- `rz` angles of the phase walk in units of `beta / 2`, in gate order -/
def angleTable : List Int := [-7, -2, 6, 3]
-- END generated

/-- bit `k` of `x` as `0`/`1` -/
def bt (x k : Nat) : Nat := (x >>> k) &&& 1

/-- `cx(c, t)` on a bit pattern -/
def cxN (x c t : Nat) : Nat := x ^^^ (bt x c <<< t)

/-- the CX frame `cx(1,3); cx(0,1); cx(0,2)` of `build_walk` -/
def frame (x : Nat) : Nat := cxN (cxN (cxN x 1 3) 0 1) 0 2

/-- the frame turns the four-link flip into an `X` on the target wire (bit 0) -/
theorem frame_maps_flip : ∀ x, x < 16 → frame (x ^^^ 15) = frame x ^^^ 1 := by decide

/-- classical steps of the skeleton: `x q`, `cx c t`, Toffoli `ccx a b t` (for `rccx`), `rz q` (records wire `q`) -/
inductive Op where
  | x (q : Nat)
  | cx (c t : Nat)
  | ccx (a b t : Nat)
  | rz (q : Nat)

/-- one step on (state, recorded `rz`-wire bits) -/
def step (s : Nat × List Nat) : Op → Nat × List Nat
  | .x q => (s.1 ^^^ (1 <<< q), s.2)
  | .cx c t => (cxN s.1 c t, s.2)
  | .ccx a b t => (if bt s.1 a = 1 ∧ bt s.1 b = 1 then s.1 ^^^ (1 <<< t) else s.1, s.2)
  | .rz q => (s.1, s.2 ++ [bt s.1 q])

/-- run a step list from a start state; the second component lists the wire bit at every `rz` -/
def run (init : Nat) (ops : List Op) : Nat × List Nat := ops.foldl step (init, [])

/-- flag computation of `GENERAL7`: ancillas `A=8, B=9, F=10, P=11, Q=12, G1=13, G2=14` -/
def flagOps : List Op :=
  [.x 4, .x 5, .x 6, .x 7, .ccx 4 5 8, .ccx 6 7 9, .ccx 8 9 10, .x 2, .x 3, .ccx 2 3 11, .ccx 10 11 12,
   .x 1, .ccx 12 1 13, .x 1, .ccx 12 1 14]

/-- the phase walk on the frame target: `rz`, then `rz` conjugated by `cx(F,·)`, `cx(G1,·)`, `cx(G2,·)` -/
def walkOps : List Op :=
  [.rz 0, .cx 10 0, .rz 0, .cx 10 0, .cx 13 0, .rz 0, .cx 13 0, .cx 14 0, .rz 0, .cx 14 0]

/-- start state: the code through the frame, target bit cleared (ancillas 0) -/
def start (y : Nat) : Nat := (frame y >>> 1) <<< 1

/-- `(F, G1, G2)` read off the ancillas after the flag chain -/
def flagChain (y : Nat) : Bool × Bool × Bool :=
  let s := (run (start y) flagOps).1
  (bt s 10 == 1, bt s 13 == 1, bt s 14 == 1)

/-- bright flag: all four corner bits are 0 -/
def flagF (y : Nat) : Bool := y >>> 4 == 0

/-- `m = (m1, m2, m3)` = bits 1..3 of the framed code, `m1` most significant -/
def m (y : Nat) : Nat := 4 * bt (frame y) 1 + 2 * bt (frame y) 2 + bt (frame y) 3

theorem flags_correct : ∀ y, y < 256 → flagChain y = (flagF y, flagF y && (m y == 0), flagF y && (m y == 4)) := by
  decide

/-- wire bits at the four `rz` slots of the walk, for input code `y` -/
def slotBits (y : Nat) : List Nat := (run (start y) (flagOps ++ walkOps)).2

/-- `∑_r angleTable[r] · (-1)^{p_r(y)}`, in units of `beta / 2` -/
def walkPhase (y : Nat) : Int :=
  (List.zipWith (fun b a => if b = 0 then a else -a) (slotBits y) angleTable).sum

/-- every input has exactly one slot bit per tabulated angle (so `zipWith` truncates nothing) -/
theorem walk_slots_match : ∀ y, y < 256 → (slotBits y).length = angleTable.length := by decide

/-- the three tables describe the 47 valid inner codes -/
theorem table_lengths : validInnerCodes.length = 47 ∧ couplingTable.length = 47 := by decide

/-- the integer Walsh table reproduces `2 · (2K)` (phase `2 β K` in units of `β / 2` is `4 K = 2 · couplingTable`) -/
theorem walk_table_exact : ∀ i, i < 47 → walkPhase (validInnerCodes.getD i 0) = 2 * couplingTable.getD i 0 := by
  decide

end Su2Plaq.SpinNet
