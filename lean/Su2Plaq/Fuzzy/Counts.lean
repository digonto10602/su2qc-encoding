import Mathlib

/-!
# Su2Plaq.Fuzzy.Counts — physical-state counts of the fuzzy 12-link diagram (docs/METHODS-fuzzy.md F4, F8)

Route A of F4 (corner-factorised Clebsch–Gordan count).  The fuzzy link decomposes as
`2(0,0) ⊕ 2(½,½) ⊕ (1,0) ⊕ (0,1)` under `SU(2)_L × SU(2)_R`; spins are stored doubled (`2j ∈ ℕ`).  At a corner
the number of Gauss singlets of the four incident spins is `|T(j₁,j₂) ∩ T(j₃,j₄)|`, `T(j,j') = {|j−j'|,…,j+j'}`.
A link leaving a corner contributes its `SU(2)_L` spin there, a link entering it contributes its `SU(2)_R` spin
(P Eq. 33 orientation); the far end of an outer link carries the opposite chirality and, in the weighted count, the
multiplicity `2j_far + 1`.  Geometry (METHODS §1, `tests/acceptance/m9/_fz.py` `CORNERS`):

* `c0: b out, l out | o0 in, o1 in`;  `c1: b in, r out | o2 out, o3 in`;
  `c2: r in, t in | o4 out, o5 out`;  `c3: t out, l in | o6 in, o7 out`.

Counts proved (all by `decide +kernel`, i.e. kernel reduction; **no `native_decide`**, only the standard axioms):
isolated plaquette `50`, outer-vacuum sector `12 800`, far ends fixed `101 197 218`, far-end weighted `6 767 266 914`.
-/

set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.Fuzzy

/-- Irreps of the fuzzy link as `(2 j_L, 2 j_R)`; the two `(0,0)` and two `(½,½)` copies are listed separately. -/
def irreps : List (Nat × Nat) := [(0, 0), (0, 0), (1, 1), (1, 1), (2, 0), (0, 2)]

/-- Doubled spin `2j` seen at a corner by an irrep: `out = true` (link leaves the corner) sees `j_L`, else `j_R`. -/
def near (i : Nat × Nat) (out : Bool) : Nat := if out then i.1 else i.2
/-- Doubled spin at the far end of the link. -/
def far (i : Nat × Nat) (out : Bool) : Nat := if out then i.2 else i.1

/-- `T(j,j')` in doubled spins: `{a+b, a+b−2, …, |a−b|}`. -/
def tri (a b : Nat) : List Nat := (List.range (min a b + 1)).map fun k => a + b - 2 * k

/-- Number of singlets of four spins (doubled): `|T(a,b) ∩ T(c,d)|`. -/
def nsinglet (a b c d : Nat) : Nat := ((tri a b).filter fun x => (tri c d).contains x).length

/-- Sum over a list of irreps. -/
def sumL (l : List (Nat × Nat)) (f : Nat × Nat → Nat) : Nat := l.foldl (fun s i => s + f i) 0

/-- Weight of the far end (`2j_far + 1`) if `w`, else 1. -/
def wt (w : Bool) (i : Nat × Nat) (out : Bool) : Nat := if w then far i out + 1 else 1

/-- One corner: inner near-spins `(a,b)`, outer links with roles `(o1,o2)`, outer irreps drawn from `os`. -/
def corner (os : List (Nat × Nat)) (w : Bool) (a b : Nat) (o1 o2 : Bool) : Nat :=
  sumL os fun i1 => sumL os fun i2 =>
    nsinglet a b (near i1 o1) (near i2 o2) * (wt w i1 o1 * wt w i2 o2)

/-- Total count: sum over irreps of the four inner links (b,r,t,l) of the product of the four corner factors. -/
def count (os : List (Nat × Nat)) (w : Bool) : Nat :=
  sumL irreps fun ib => sumL irreps fun ir => sumL irreps fun it => sumL irreps fun il =>
    corner os w (near ib true) (near il true) false false *
    corner os w (near ib false) (near ir true) true false *
    corner os w (near ir false) (near it false) true true *
    corner os w (near it true) (near il false) false true

/-- Isolated plaquette (2-valent corners): no outer links; the outer pair is replaced by a single trivial spin-0 pair,
so each corner factor is `nsinglet a b 0 0 = [a = b]`. -/
def isolatedPlaquette : Nat := count [(0, 0)] false

/-- Outer-vacuum sector: every outer link in one of its two `(0,0)` copies. -/
def outerVacuum : Nat := count [(0, 0), (0, 0)] false

/-- Twelve links, far end of each outer link fixed (all six irreps allowed on the outer links). -/
def fixedFarEnd : Nat := count irreps false

/-- Far-end weighted count (each outer link weighted by `2 j_far + 1`). -/
def farEndWeighted : Nat := count irreps true

/-- Sanity checks of the corner rule (`corner_singlet_dim` of the production code). -/
theorem nsinglet_checks :
    nsinglet 1 1 1 1 = 2 ∧ nsinglet 0 0 0 0 = 1 ∧ nsinglet 2 0 1 1 = 1 ∧ nsinglet 2 2 2 2 = 3 ∧ nsinglet 1 0 0 0 = 0 := by
  decide +kernel

theorem count_isolated_plaquette : isolatedPlaquette = 50 := by decide +kernel
theorem count_outer_vacuum : outerVacuum = 12800 := by decide +kernel
theorem count_fixed_far_end : fixedFarEnd = 101197218 := by decide +kernel
theorem count_far_end_weighted : farEndWeighted = 6767266914 := by decide +kernel

end Su2Plaq.Fuzzy
