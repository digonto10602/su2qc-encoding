/-!
# Su2Plaq.SpinNet.Recoupling -- kernel-checked K from Racah 6j symbols (M3x step W1, prompts/102 section 2)

Mathlib-free (no imports), so every `decide` below elaborates in about 2 GB.  Everything is exact: spins are stored
doubled (`2j`), a number `q * sqrt r` is a pair of unnormalised fractions, rationals are `(num : Int, den : Nat)`
pairs compared by cross-multiplication (no `Rat`, no `Nat.sqrt`).

* `sixj`   : Wigner 6j symbol by Racah's formula (Edmonds 6.3.7), `q * sqrt r` with `q`, `r` rational.
* `fsym`   : F-symbol (Edmonds 6.1.5), argument order and phase as `su2plaq.su2.wigner.f_symbol`.
* `validCodes` : the 47 valid inner codes from the codec (METHODS-spinnet section 1).
* `pAmp`, `kEntry?`, `twoK?` : route-B plaquette amplitude `P[y', y]`, `K = -(P + P^T)`, `2K[y xor 15, y]`.
* `states`, `blockCodes` : the 433 physical states `(y, o)` and the outer blocks (used by `Spectrum.lean`).

Theorems (all by `decide`, standard axioms only):
* `valid_codes_from_codec` : the codec's valid codes are the exported list `exportedCodes`.
* `k_matching`   : `K` is symmetric on the four-link flip and vanishes elsewhere (all 47 x 47 entries).
* `coupling_from_6j` : `2K[y xor 15, y]` from the 6j symbols is the exported coupling table on all 47 codes.
* `k_from_6j_full`   : all 47 x 47 entries of `2K` from the 6j symbols are the matching with the table's couplings.

`exportedCodes` / `exportedTwoK` between the generated markers are written by
`su2plaq.spinnet.lean_export.write_lean_exact_tables` from the Python encoding; never edit them by hand.
Prototype: `scratch/planner/lean/SpinNetExact.lean` (section A).
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.SpinNet

/-! ## A. exact arithmetic -/

/-- unnormalised fraction `num / den`, `den > 0` -/
structure Frac where
  num : Int
  den : Nat
deriving Repr, DecidableEq

namespace Frac
def zero : Frac := ⟨0, 1⟩
def one : Frac := ⟨1, 1⟩
def ofNat (n : Nat) : Frac := ⟨n, 1⟩
def mul (a b : Frac) : Frac := ⟨a.num * b.num, a.den * b.den⟩
def add (a b : Frac) : Frac := ⟨a.num * b.den + b.num * a.den, a.den * b.den⟩
def neg (a : Frac) : Frac := ⟨-a.num, a.den⟩
/-- `a / n` for a positive natural `n` -/
def divNat (a : Frac) (n : Nat) : Frac := ⟨a.num, a.den * n⟩
def beq (a b : Frac) : Bool := a.num * b.den == b.num * a.den
def isZero (a : Frac) : Bool := a.num == 0
/-- reduced numerator (natAbs), denominator -/
def reduce (a : Frac) : Int × Nat :=
  let g := Nat.gcd a.num.natAbs a.den
  if g == 0 then (0, 1) else (a.num / g, a.den / g)
end Frac

def fact : Nat → Nat
  | 0 => 1
  | n + 1 => (n + 1) * fact n

/-- bounded integer square root: `some k` iff `k * k = n` with `k < 2^16` (all numbers here are tiny) -/
def isqrt? (n : Nat) : Option Nat := (List.range 512).find? (fun k => k * k == n)

/-- `q * sqrt r` with `q r : Frac`, `r ≥ 0` -/
structure SR where
  q : Frac
  r : Frac
deriving Repr

namespace SR
def zero : SR := ⟨Frac.zero, Frac.one⟩
def mul (a b : SR) : SR := ⟨a.q.mul b.q, a.r.mul b.r⟩
/-- exact rational value, `none` if `r` is not a rational square -/
def toFrac? (s : SR) : Option Frac :=
  if s.q.isZero then some Frac.zero else
  let (n, d) := s.r.reduce
  match isqrt? n.natAbs, isqrt? d with
  | some a, some b => some (s.q.mul ⟨a, b⟩)
  | _, _ => none
end SR

/-- triangle condition on doubled spins -/
def tri (x y z : Nat) : Bool :=
  (x ≤ y + z) && (y ≤ x + z) && (z ≤ x + y) && ((x + y + z) % 2 == 0)

/-- `Δ(xyz)^2` on doubled spins (Edmonds 6.3.7) -/
def delta2 (x y z : Nat) : Frac :=
  ⟨fact ((x + y - z) / 2) * fact ((x - y + z) / 2) * fact ((y + z - x) / 2), fact ((x + y + z) / 2 + 1)⟩

/-- Racah sum `Σ_z (-1)^z (z+1)! / [(z-t1)! (z-t2)! (z-t3)! (z-t4)! (q1-z)! (q2-z)! (q3-z)!]` -/
def racahSum (t1 t2 t3 t4 q1 q2 q3 : Nat) : Frac :=
  let zmin := max (max t1 t2) (max t3 t4)
  let zmax := min (min q1 q2) q3
  let term (z : Nat) : Frac :=
    let sgn : Int := if z % 2 == 0 then 1 else -1
    ⟨sgn * fact (z + 1), fact (z - t1) * fact (z - t2) * fact (z - t3) * fact (z - t4) *
                         fact (q1 - z) * fact (q2 - z) * fact (q3 - z)⟩
  let rec go (k : Nat) (acc : Frac) : Frac :=
    match k with
    | 0 => acc
    | k + 1 => go k (acc.add (term (zmin + k)))
  if zmin ≤ zmax then go (zmax + 1 - zmin) Frac.zero else Frac.zero

/-- Wigner 6j `{a b c; d e f}` on doubled spins as `q * sqrt r` -/
def sixj (a b c d e f : Nat) : SR :=
  if tri a b c && tri a e f && tri d b f && tri d e c then
    ⟨racahSum ((a + b + c) / 2) ((a + e + f) / 2) ((d + b + f) / 2) ((d + e + c) / 2)
              ((a + b + d + e) / 2) ((a + c + d + f) / 2) ((b + c + e + f) / 2),
     (delta2 a b c).mul ((delta2 a e f).mul ((delta2 d b f).mul (delta2 d e c)))⟩
  else SR.zero

/-- F-symbol `F^{j1 j2 j12}_{j3 J j23} = (-1)^{j1+j2+j3+J} sqrt((2j12+1)(2j23+1)) {j1 j2 j12; j3 J j23}` (Edmonds 6.1.5),
doubled spins; the phase uses integer division as `su2plaq.su2.wigner.f_symbol` -/
def fsym (j1 j2 j12 j3 J j23 : Nat) : SR :=
  let s := sixj j1 j2 j12 j3 J j23
  let ph : Int := if ((j1 + j2 + j3 + J) / 2) % 2 == 0 then 1 else -1
  ⟨⟨ph * s.q.num, s.q.den⟩, s.r.mul (Frac.ofNat ((j12 + 1) * (j23 + 1)))⟩

/-! ## A. codec and K -/

def bitOf (x k : Nat) : Nat := (x >>> k) &&& 1
/-- corner `c` visits inner links `(p, n)`: c0 (l,b), c1 (b,r), c2 (r,t), c3 (t,l); links b r t l = bits 0..3 -/
def cornerP : Nat → Nat | 0 => 3 | 1 => 0 | 2 => 1 | _ => 2
def cornerN : Nat → Nat | 0 => 0 | 1 => 1 | 2 => 2 | _ => 3
/-- doubled corner spin `J_c` decoded from code `y`: bit `4+c` ⇒ 1; else the unique admissible `J ∈ {0, 1/2}` -/
def Jc (y c : Nat) : Nat :=
  if bitOf y (4 + c) == 1 then 2 else if bitOf y (cornerP c) == bitOf y (cornerN c) then 0 else 1
/-- a corner bit may be set only when both inner links at the corner are 1/2 (`J = 1` admissible for the inner pair) -/
def validCode (y : Nat) : Bool :=
  y < 256 && (List.range 4).all fun c => bitOf y (4 + c) == 0 || (bitOf y (cornerP c) == 1 && bitOf y (cornerN c) == 1)
def validCodes : List Nat := (List.range 256).filter validCode

/-- route-B plaquette amplitude `P[y', y] = Π_c F(J_c, j_p, j_n; 1/2, j'_n, j'_p)` with every inner link shifted by
±1/2 (at j_max = 1/2: flipped) and the corner labels unchanged; 0 otherwise (`su2plaq.exact.spinnet.plaquette_P`) -/
def pAmp (y' y : Nat) : SR :=
  if (y' &&& 15) == ((y &&& 15) ^^^ 15) && (List.range 4).all (fun c => Jc y' c == Jc y c) then
    (List.range 4).foldl (fun acc c =>
      acc.mul (fsym (Jc y c) (bitOf y (cornerP c)) (bitOf y (cornerN c)) 1 (bitOf y' (cornerN c)) (bitOf y' (cornerP c))))
      ⟨Frac.one, Frac.one⟩
  else SR.zero

/-- `K[y', y] = -(P[y', y] + P[y, y'])`, exact; `none` if an amplitude is not rational -/
def kEntry? (y' y : Nat) : Option Frac :=
  match (pAmp y' y).toFrac?, (pAmp y y').toFrac? with
  | some a, some b => some (a.add b).neg
  | _, _ => none

/-- `2 K[y ^^^ 15, y]` as an integer (`none` if not an integer) -/
def twoK? (y : Nat) : Option Int :=
  match kEntry? (y ^^^ 15) y with
  | some k =>
    let (n, d) := (⟨2 * k.num, k.den⟩ : Frac).reduce
    if d == 1 then some n else none
  | none => none

-- BEGIN generated exact (su2plaq.spinnet.lean_export.write_lean_exact_tables; do not edit by hand)
/-- the 47 valid inner codes (bits 0..3 = j_b j_r j_t j_l, bits 4..7 = corner bits), sorted -/
def exportedCodes : List Nat := [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 25, 27, 29, 31, 35, 39, 43, 47, 59, 63, 70, 71, 78, 79, 95, 103, 111, 127, 140, 141, 142, 143, 157, 159, 175, 191, 206, 207, 223, 239, 255]
/-- `2 K[partner, code]` for the codes of `exportedCodes` -/
def exportedTwoK : List Int := [-4, 2, 2, 2, 2, -1, 2, 2, 2, 2, -1, 2, 2, 2, 2, -4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
-- END generated exact

/-- `2K[y xor 15, y]` read from the exported table (tied to the 6j symbols by `coupling_from_6j`) -/
def twoKlit (y : Nat) : Int := exportedTwoK.getD (exportedCodes.findIdx (· == y)) 0

theorem valid_codes_from_codec : validCodes = exportedCodes := by decide

/-- K is symmetric on every valid pair and vanishes off the four-link flip (checked on all 47 x 47 entries) -/
theorem k_matching :
    validCodes.all (fun y => validCodes.all (fun y' =>
      if y' == y ^^^ 15 then kEntry? y' y == kEntry? y y' else (pAmp y' y).q.isZero)) = true := by
  decide

/-- the exported coupling table is `2K` from the 6j symbols on every valid code -/
theorem coupling_from_6j :
    (List.range 47).all (fun i => twoK? (exportedCodes.getD i 0) == some (exportedTwoK.getD i 0)) = true := by
  decide

/-- all 47 x 47 entries: `2 K[y', y]` from the 6j symbols equals the matching with the table's couplings -/
theorem k_from_6j_full :
    validCodes.all (fun y => validCodes.all (fun y' =>
      match kEntry? y' y with
      | some k => (⟨2 * k.num, k.den⟩ : Frac).beq ⟨(if y' == y ^^^ 15 then twoKlit y else 0), 1⟩
      | none => false)) = true := by
  decide

/-! ## the 433 states and the outer blocks -/

/-- `fuse(a, b)` of two outer links (doubled): `{0, 1} -> [0, 2]` if both are 1/2, `[0]` if both 0, else `[1]` -/
def fuseN (a b : Nat) : List Nat := if a == b then (if a == 1 then [0, 2] else [0]) else [1]

/-- outer pattern `o`: bit `k` = spin of outer link `o_k`; corner `c` has outer links `(2c, 2c+1)` -/
def stateOK (y o : Nat) : Bool :=
  validCode y && (List.range 4).all fun c => (fuseN (bitOf o (2 * c)) (bitOf o (2 * c + 1))).contains (Jc y c)

/-- the physical states `(y, o)` in Lean order (codes ascending, then outer patterns ascending) -/
def states : List (Nat × Nat) :=
  validCodes.flatMap fun y => (List.range 256).filterMap fun o => if stateOK y o then some (y, o) else none

/-- the codes `y` of the outer block `o` -/
def blockCodes (o : Nat) : List Nat := validCodes.filter (fun y => stateOK y o)

end Su2Plaq.SpinNet
