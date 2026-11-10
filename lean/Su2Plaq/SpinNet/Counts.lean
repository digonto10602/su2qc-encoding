import Su2Plaq.Structure.Counts

/-!
# Su2Plaq.SpinNet.Counts — kernel-checked counts of the spin-network encoding (M3, prompts/100 §1.8)

Reuses the laptop's definitions `fuse`, `bit`, `sumOver` from `Su2Plaq.Structure.Counts` (read-only import).
Inner pattern `n ∈ [0,16)`: bit 0..3 = `j_b j_r j_t j_l`; outer pattern `o ∈ [0,256)`: bit `k` = `j` of outer link `o_k`.
Corners: `c0 (b,l | o0,o1)`, `c1 (b,r | o2,o3)`, `c2 (r,t | o4,o5)`, `c3 (t,l | o6,o7)`.
Contents: 47 inner labels = 16 bright + 31 dark, 8 bright pairs; the multiplicities of `H_B` as pair-class counts over
the 433 labels (16 vacuum-pair states, 96 coupling-1, 16 alternating, 177 dark); the 16-bit code is injective per
corner; a corner bit can be 1 only when all four links at the corner are 1/2.  Every theorem is proved by `decide`
(kernel reduction, standard axioms only); no compiler-trust tactic is used.  The 433 count itself is the laptop's
`Su2Plaq.card_physical`; `card_states_spinnet` re-counts it through the spin-network corner enumeration.
Definitions are those of the planner prototype `scratch/planner/lean/SpinNetCounts.lean`.
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.SpinNet
open Su2Plaq

/-- admissible corner spins J (coded 0, 1, 2 for 0, 1/2, 1) given inner pair and outer pair -/
def cornerJs (ia ib oc od : Bool) : List Nat := (fuse ia ib).filter (fun J => (fuse oc od).contains J)
/-- corner qubit of a label: 1 iff J = 1 -/
def jbit (J : Nat) : Nat := if J = 2 then 1 else 0

def innerPairs (n : Nat) : List (Bool × Bool) :=
  [(bit n 0, bit n 3), (bit n 0, bit n 1), (bit n 1, bit n 2), (bit n 2, bit n 3)]
def outerPairs (o : Nat) : List (Bool × Bool) :=
  [(bit o 0, bit o 1), (bit o 2, bit o 3), (bit o 4, bit o 5), (bit o 6, bit o 7)]

/-- number of inner labels ((j_b j_r j_t j_l), (J_0..J_3)) of inner pattern n: every triangle-admissible J has an outer completion -/
def innerLabelCount (n : Nat) : Nat := ((innerPairs n).map (fun p => (fuse p.1 p.2).length)).foldl (· * ·) 1
def innerLabels : Nat := sumOver innerLabelCount 16
/-- bright inner labels: all J ∈ {0, 1/2} -/
def brightInner (n : Nat) : Nat := ((innerPairs n).map (fun p => ((fuse p.1 p.2).filter (· ≠ 2)).length)).foldl (· * ·) 1
def brightLabels : Nat := sumOver brightInner 16
def darkLabels : Nat := innerLabels - brightLabels
/-- bright pairs: a bright label and its four-link flip (n ↔ 15 - n); count the member with j_b = 0 -/
def brightPairs : Nat := sumOver (fun n => if bit n 0 = false then brightInner n else 0) 16
/-- coupling class of the pair of inner pattern n: 2 = vacuum pair (0000/1111, |K| = 2), 1 = alternating (0101/1010, |K| = 1/2), 0 = the six others (|K| = 1) -/
def pairClass (n : Nat) : Nat := if n = 0 ∨ n = 15 then 2 else if n = 5 ∨ n = 10 then 1 else 0

/-- states of (inner n, outer o): ∏_c |cornerJs|; bright states: ∏_c |cornerJs ∩ {0,1/2}| -/
def stateCount (n o : Nat) : Nat :=
  (List.zipWith (fun p q => (cornerJs p.1 p.2 q.1 q.2).length) (innerPairs n) (outerPairs o)).foldl (· * ·) 1
def brightCount (n o : Nat) : Nat :=
  (List.zipWith (fun p q => ((cornerJs p.1 p.2 q.1 q.2).filter (· ≠ 2)).length) (innerPairs n) (outerPairs o)).foldl (· * ·) 1

def multVac : Nat := sumOver (fun o => brightCount 0 o) 256
def multAlt : Nat := sumOver (fun o => brightCount 5 o) 256
def multOne : Nat := sumOver (fun o => sumOver (fun n => if pairClass n = 0 ∧ bit n 0 = false then brightCount n o else 0) 16) 256
def brightStates : Nat := sumOver (fun o => sumOver (fun n => brightCount n o) 16) 256
def darkStates : Nat := sumOver (fun o => sumOver (fun n => stateCount n o - brightCount n o) 16) 256
def totalStates : Nat := sumOver (fun o => sumOver (fun n => stateCount n o) 16) 256

theorem card_inner_labels : innerLabels = 47 := by decide
theorem card_bright_labels : brightLabels = 16 := by decide
theorem card_dark_labels : darkLabels = 31 := by decide
theorem card_bright_pairs : brightPairs = 8 := by decide
theorem mult_two : multVac = 16 := by decide
theorem mult_half : multAlt = 16 := by decide
theorem mult_one : multOne = 96 := by decide
theorem card_bright_states : brightStates = 256 := by decide
theorem card_dark_states : darkStates = 177 := by decide
theorem card_states_spinnet : totalStates = 433 := by decide
/-- the corner qubit (J = 1 ↦ 1, else 0) separates the admissible J's of every corner: the 16-bit code is injective -/
theorem corner_jbit_injective : ∀ ia ib oc od : Bool, ((cornerJs ia ib oc od).map jbit).Nodup := by decide
/-- a corner qubit can be 1 only when all four links at the corner are 1/2 -/
theorem corner_bit_needs_four_half : ∀ ia ib oc od : Bool, (cornerJs ia ib oc od).contains 2 → ia ∧ ib ∧ oc ∧ od := by decide

end Su2Plaq.SpinNet
