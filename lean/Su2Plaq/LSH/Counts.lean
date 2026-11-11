/-!
# Su2Plaq.LSH.Counts — kernel-checked counts of the loop-string-hadron register (M7, prompts/400 §1.2, §4)

Core Lean only (no Mathlib).  Every theorem is proved by `decide` (kernel reduction), standard axioms only; no
compiler-trust tactic is used.  The 433 states are re-counted here from the LSH rules alone (flux cap on the physical
legs + Abelian Gauss law on the four inner and four virtual links), independently of `Su2Plaq.card_physical` (the
corner-fusion count): two kernel proofs of 433 by different rules.  Definitions are those of the planner prototype
`scratch/planner/lean/LSHCounts.lean`.

Site code `s < 8`: bit 0 = l_12, bit 1 = l_23, bit 2 = l_31 (legs 1, 2, 3; leg 3 = virtual link).
Inner register `x < 4096`: 'in' site c at bits 3c..3c+2, legs (1,2,3) = (p(c), n(c), v), loop order c0:(l,b) c1:(b,r) c2:(r,t) c3:(t,l).
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.LSH

def bt (x k : Nat) : Nat := (x >>> k) &&& 1
/-- fluxes of a site code: N_1 = l_31 + l_12, N_2 = l_12 + l_23, N_3 = l_23 + l_31 -/
def n1 (s : Nat) : Nat := bt s 2 + bt s 0
def n2 (s : Nat) : Nat := bt s 0 + bt s 1
def n3 (s : Nat) : Nat := bt s 1 + bt s 2
/-- flux cap of the j_max = 1/2 truncation: at most one unit on the two physical legs -/
def siteValid (s : Nat) : Bool := n1 s ≤ 1 && n2 s ≤ 1
def site (x c : Nat) : Nat := (x >>> (3 * c)) &&& 7

def sumOver (f : Nat → Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => sumOver f n + f n

/-- Abelian Gauss law on the four inner links: N_2 of site c equals N_1 of site c+1 -/
def innerAGL (x : Nat) : Bool :=
  n2 (site x 0) == n1 (site x 1) && n2 (site x 1) == n1 (site x 2) && n2 (site x 2) == n1 (site x 3) && n2 (site x 3) == n1 (site x 0)
def allValid (x : Nat) : Bool := siteValid (site x 0) && siteValid (site x 1) && siteValid (site x 2) && siteValid (site x 3)
def innerOK (x : Nat) : Bool := allValid x && innerAGL x
/-- no site carries virtual flux 2 (J = 1) -/
def bright (x : Nat) : Bool := n3 (site x 0) != 2 && n3 (site x 1) != 2 && n3 (site x 2) != 2 && n3 (site x 3) != 2

/-- number of valid 'out' site codes with virtual flux v -/
def outCount (v : Nat) : Nat := sumOver (fun s => if siteValid s && n3 s == v then 1 else 0) 8
def rawOutCount (v : Nat) : Nat := sumOver (fun s => if n3 s == v then 1 else 0) 8
def completions (cnt : Nat → Nat) (x : Nat) : Nat :=
  cnt (n3 (site x 0)) * cnt (n3 (site x 1)) * cnt (n3 (site x 2)) * cnt (n3 (site x 3))

def siteCodes : Nat := sumOver (fun s => if siteValid s then 1 else 0) 8
def innerCodes : Nat := sumOver (fun x => if innerOK x then 1 else 0) 4096
def brightCodes : Nat := sumOver (fun x => if innerOK x && bright x then 1 else 0) 4096
def darkCodes : Nat := sumOver (fun x => if innerOK x && !bright x then 1 else 0) 4096
def totalStates : Nat := sumOver (fun x => if innerOK x then completions outCount x else 0) 4096
def brightStates : Nat := sumOver (fun x => if innerOK x && bright x then completions outCount x else 0) 4096
def rawInner : Nat := sumOver (fun x => if innerAGL x then 1 else 0) 4096
def rawStates : Nat := sumOver (fun x => if innerAGL x then completions rawOutCount x else 0) 4096

theorem card_site_codes : siteCodes = 5 := by decide
theorem site_valid_list : (List.range 8).filter siteValid = [0, 1, 2, 4, 6] := by decide
theorem flux_injective : ∀ s, s < 8 → ∀ t, t < 8 → n1 s = n1 t → n2 s = n2 t → n3 s = n3 t → s = t := by decide
theorem flux_even : ∀ s, s < 8 → (n1 s + n2 s + n3 s) % 2 = 0 := by decide
theorem card_inner_codes : innerCodes = 47 := by decide +kernel
theorem card_bright_codes : brightCodes = 16 := by decide +kernel
theorem card_dark_codes : darkCodes = 31 := by decide +kernel
theorem card_states_lsh : totalStates = 433 := by decide +kernel
theorem card_bright_states : brightStates = 256 := by decide +kernel
theorem card_raw_inner : rawInner = 82 := by decide +kernel
theorem card_raw_states : rawStates = 5920 := by decide +kernel

end Su2Plaq.LSH
