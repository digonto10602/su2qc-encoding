import Mathlib

/-!
# Su2Plaq.Structure.Counts — kernel-checked counts of the gauge-invariant subspace (docs/METHODS.md §11.3 a)

Spins on the 12 links of one plaquette-with-outer-legs at `j_max = 1/2` (`Bool`: `false` = 0, `true` = 1/2).
Links 0..3 = b r t l (inner), 4..11 = o0..o7 (outer).  Corner `c` couples two inner and two outer ends
(METHODS §1): `c0: (b,l | o0,o1)`, `c1: (b,r | o2,o3)`, `c2: (r,t | o4,o5)`, `c3: (t,l | o6,o7)`.
Gauss law at a corner admits `n_c = |T(j_a,j_b) ∩ T(j_c,j_d)|` singlets (`fuse`), and the outer-`m` rule: both
outer links at `j = 1/2` with inner pair `(0,0)` force `m_c = -m_d` (`cornerM`).

Definitions are those of the planner prototype `scratch/planner/lean/P6_count.lean`.  Every count is proved by
`decide` (kernel reduction, no axioms).  No compiler-trust tactic is used here.
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq

/-- Admissible total spins `J ∈ {0, 1/2, 1}` (coded 0,1,2) of a pair of spins in `{0, 1/2}`. -/
def fuse (a b : Bool) : List Nat :=
  match a, b with
  | false, false => [0]
  | false, true  => [1]
  | true,  false => [1]
  | true,  true  => [0, 2]

/-- Number of singlets at a corner = `|fuse(inner) ∩ fuse(outer)|`. -/
def cornerCount (ia ib oc od : Bool) : Nat :=
  ((fuse ia ib).filter (fun J => (fuse oc od).contains J)).length

def bit (n k : Nat) : Bool := (n / 2 ^ k) % 2 = 1

/-- Spin pattern `n ∈ [0, 4096)`: bit `i` = spin of link `i`. -/
def patternCount (n : Nat) : Nat :=
  cornerCount (bit n 0) (bit n 3) (bit n 4) (bit n 5) *
  cornerCount (bit n 0) (bit n 1) (bit n 6) (bit n 7) *
  cornerCount (bit n 1) (bit n 2) (bit n 8) (bit n 9) *
  cornerCount (bit n 2) (bit n 3) (bit n 10) (bit n 11)

/-- `∑_{i<n} f i` by structural recursion on `n` (kernel-reducible). -/
def sumOver (f : Nat → Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => sumOver f n + f n

def total : Nat := sumOver patternCount 4096
def linkPatterns : Nat := sumOver (fun n => if patternCount n ≥ 1 then 1 else 0) 4096
def twoOrMore : Nat := sumOver (fun n => if patternCount n ≥ 2 then 1 else 0) 4096

/-- Far-end weighted: `∑ count · ∏_outer (2j+1)`. -/
def outerWeight (n : Nat) : Nat :=
  (List.range 8).foldl (fun acc k => acc * (if bit n (4 + k) then 2 else 1)) 1
def farEndWeighted : Nat := sumOver (fun n => patternCount n * outerWeight n) 4096

/-- States for a fixed outer spin pattern (`outer ∈ [0, 256)`), summed over the 16 inner patterns. -/
def innerSum (outer : Nat) : Nat := sumOver (fun inner => patternCount (inner + 16 * outer)) 16

/-- Maximum of `f` over `[0, n)` by structural recursion. -/
def maxOver (f : Nat → Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => max (maxOver f n) (f n)

/-- Closed plaquette: all outer spins 0. -/
def closedCount : Nat := innerSum 0

/-- Outer `m`-pattern coded in base 3 (`0` = spin 0, `1,2` = `m = ±1/2`). -/
def code (o k : Nat) : Nat := (o / 3 ^ k) % 3
def ospin (o k : Nat) : Bool := code o k ≠ 0

/-- A corner admits the outer `m`-pattern unless both outer links carry `j = 1/2` while the inner pair can only
fuse to `J = 0` (both inner spins 0): then the two outer `m`'s must be opposite. -/
def cornerM (ia ib : Bool) (cc cd : Nat) : Bool :=
  if cc ≠ 0 ∧ cd ≠ 0 ∧ ia = false ∧ ib = false then cc ≠ cd else true

def patternCountM (inner o : Nat) : Nat :=
  let b := bit inner 0; let r := bit inner 1; let t := bit inner 2; let l := bit inner 3
  (if cornerM b l (code o 0) (code o 1) ∧ cornerM b r (code o 2) (code o 3) ∧
      cornerM r t (code o 4) (code o 5) ∧ cornerM t l (code o 6) (code o 7) then 1 else 0) *
  cornerCount b l (ospin o 0) (ospin o 1) * cornerCount b r (ospin o 2) (ospin o 3) *
  cornerCount r t (ospin o 4) (ospin o 5) * cornerCount t l (ospin o 6) (ospin o 7)

def innerSumM (o : Nat) : Nat := sumOver (fun inner => patternCountM inner o) 16

/-- Number of supported outer `m`-patterns (those with at least one state), out of `3^8 = 6561`. -/
def supportedOuterM : Nat := sumOver (fun o => if innerSumM o ≥ 1 then 1 else 0) 6561
/-- Maximum number of states sharing one outer `m`-pattern. -/
def maxPerOuterM : Nat := maxOver innerSumM 6561

theorem card_physical : total = 433 := by decide +kernel
theorem card_link_patterns : linkPatterns = 256 := by decide +kernel
theorem card_two_or_more : twoOrMore = 95 := by decide +kernel
theorem card_closed : closedCount = 2 := by decide +kernel
theorem far_end_weighted : farEndWeighted = 17362 := by decide +kernel
theorem card_supported_outer : supportedOuterM = 3153 := by decide +kernel
theorem max_states_per_outer : maxPerOuterM = 17 := by decide +kernel
/-- Don't-care inner codes: `4^6 - 5^4` of the 4096 base-4 codes are not among the 625 physical-link patterns. -/
theorem dont_care_codes : 4 ^ 6 - 5 ^ 4 = 3471 := by decide

end Su2Plaq
