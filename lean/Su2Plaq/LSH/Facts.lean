import Su2Plaq.LSH.Counts
import Su2Plaq.LSH.Circuit

/-!
# Su2Plaq.LSH.Facts — the exported tables are the counted codes; raw-bit facts for the M8 proposers (prompts/401 step 8.A1)

Every theorem is proved by
`decide` (kernel reduction, standard axioms only).  Site bits of 'in' site c: x = l_pn (bit 3c), y = l_nv (3c+1), z = l_vp (3c+2).
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.LSH

/-- audit 303 N1: the exported list of inner codes IS the set cut out by the LSH rules (flux cap + Abelian Gauss law) -/
theorem inner_codes_from_rules : lshInnerCodes = (List.range 4096).filter innerOK := by decide +kernel

def xb (x c : Nat) : Nat := bt x (3 * c)
def yb (x c : Nat) : Nat := bt x (3 * c + 1)
def zb (x c : Nat) : Nat := bt x (3 * c + 2)
def ySum (x : Nat) : Nat := yb x 0 + yb x 1 + yb x 2 + yb x 3
def zSum (x : Nat) : Nat := zb x 0 + zb x 1 + zb x 2 + zb x 3
def innerCode (i : Nat) : Nat := lshInnerCodes.getD i 0
def twoK (i : Nat) : Int := lshCoupling.getD i 0

/-- a code is dark (coupling 0) exactly when some site holds virtual flux 2 (site code 110) -/
theorem coupling_zero_iff_dark : ∀ i, i < 47 → (twoK i == 0) = !bright (innerCode i) := by decide
/-- dark site <-> both l_nv and l_vp set (one AND of raw bits per site) -/
theorem dark_site_is_and : ∀ i, i < 47 → ∀ c, c < 4 → (n3 (site (innerCode i) c) == 2) = (yb (innerCode i) c == 1 && zb (innerCode i) c == 1) := by decide
/-- on bright codes 2K is a function of the number of set l_nv bits alone: 0 -> -4, 1 -> +2, 2 -> -1 -/
theorem coupling_by_y_weight : ∀ i, i < 47 → bright (innerCode i) = true →
    twoK i = (if ySum (innerCode i) = 0 then -4 else if ySum (innerCode i) = 1 then 2 else -1) ∧ ySum (innerCode i) ≤ 2 ∧ ySum (innerCode i) = zSum (innerCode i) := by decide
/-- link bit read at either end (Abelian Gauss law as a parity): x_c xor y_c = x_{c+1} xor z_{c+1} -/
theorem link_bit_two_ways : ∀ i, i < 47 → ∀ c, c < 4 →
    (xb (innerCode i) c + yb (innerCode i) c) % 2 = (xb (innerCode i) ((c + 1) % 4) + zb (innerCode i) ((c + 1) % 4)) % 2 := by decide
/-- the plaquette move per site: flip l_pn if w = 0, flip l_nv and l_vp if w = 1 (w = l_nv xor l_vp) -/
theorem move_per_site : ∀ i, i < 47 → twoK i ≠ 0 → ∀ c, c < 4 →
    site (innerCode i ^^^ lshPartner.getD i 0) c = (if (yb (innerCode i) c + zb (innerCode i) c) % 2 = 0 then 1 else 6) := by decide
/-- the parity of the four l_nv bits is unchanged by the move and equals [2K = +2] -/
theorem y_parity_invariant : ∀ i, i < 47 → twoK i ≠ 0 →
    ySum (lshPartner.getD i 0) % 2 = ySum (innerCode i) % 2 ∧ ((ySum (innerCode i) % 2 == 1) = (twoK i == 2)) := by decide
/-- the eight difference vectors of the move are pairwise different (no CNOT-only frame) -/
theorem eight_differences :
    ((((List.range 47).filter (fun i => twoK i != 0)).map (fun i => innerCode i ^^^ lshPartner.getD i 0)).eraseDups).length = 8 := by decide

end Su2Plaq.LSH
