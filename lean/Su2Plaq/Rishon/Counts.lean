import Su2Plaq.Structure.Counts

/-!
# Su2Plaq.Rishon.Counts — kernel-checked counts of the rishon (two-rishon-per-link) encoding (M5, prompts/200 §2.9)

Reuses the laptop's `bit`, `patternCount`, `sumOver` from `Su2Plaq.Structure.Counts` (read-only import).
In the two-rishon link representation the link types `A`, `B` have end spins `(0, 0)` and the quartet type `Q` has end
spins `(1/2, 1/2)`.  Gauss's law at a corner only sees the end spins, so the Kogut–Susskind corner count `patternCount`
applies to the spin pattern `n ∈ [0, 4096)` (bit `i` = link `i` carries `j = 1/2`; links 0..3 = b r t l, 4..11 = o0..o7).
A link with `j = 0` has two singlets (`A` and `B`), a link with `j = 1/2` has one (the quartet `Q` colour state), hence
the weight `2 ^ zeros n`, with `zeros n` the number of links with `j = 0` (docs/METHODS-rishon.md R3, R8).
Closed sector: all eight outer links are singlets (outer bits 0), i.e. only the inner patterns `n ∈ [0, 16)` contribute
and every outer link contributes the factor 2.
Both theorems are proved by `decide +kernel` (kernel reduction only; no compiler-trust tactic, no axioms beyond the
standard ones).
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq

/-- Number of links of the 12-link spin pattern `n` (bit `i` = link `i`) with `j = 0`. -/
def zeros (n : Nat) : Nat := (List.range 12).foldl (fun acc k => if bit n k then acc else acc + 1) 0

/-- `∑_{n<4096} patternCount n · 2^{zeros n}`: physical rishon states of the plaquette with outer legs. -/
def rishonTotal : Nat := sumOver (fun n => patternCount n * 2 ^ zeros n) 4096

/-- Closed sector: all outer links singlets (outer bits 0), inner patterns `n < 16`, weight `2^{zeros n}` (outer links
contribute `2^8`). -/
def rishonClosed : Nat := sumOver (fun n => patternCount n * 2 ^ zeros n) 16

theorem card_rishon_physical : rishonTotal = 38432 := by decide +kernel
theorem card_rishon_closed : rishonClosed = 4352 := by decide +kernel

end Su2Plaq
