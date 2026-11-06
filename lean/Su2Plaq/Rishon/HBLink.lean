import Su2Plaq.Rishon.JW
import Su2PlaqCert.Rishon.HBData

/-!
# Su2Plaq.Rishon.HBLink -- the H_B certificate's link matrices are the Jordan-Wigner link operators (M5x step W1)

prompts/202 section 1 (W1), docs/METHODS-rishon.md R9.  Mathlib-free; every proof is `decide +kernel`.

* `hb_link_ops_from_jw`: the eight sparse 6x6 matrices of the certificate (`Su2PlaqCert.Rishon.HBData`, order
  `U00, U01, U10, U11, Ud00, Ud01, Ud10, Ud11`) equal `Uop i j` / `Udop i j` of `JW.lean` restricted to the two-rishon
  sector (as sets of `(row, col, value)`), the `Ud` lists are the transposes of the `U` lists, and both operators keep
  the sector.
* `det_u_identity`: `U11 U22 - U12 U21 = 2 U11 U22` as an operator identity on all 16 states of the link space
  (Banerjee-Chandrasekharan-Wiese, hep-th/9704106, Eq. 4.6).
* `u_commute`: all `U_ij` commute pairwise.
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0
set_option synthInstance.maxSize 10000
set_option synthInstance.maxHeartbeats 200000

namespace Su2Plaq.Rishon

open Su2PlaqCert.Rishon (rishonHBCert)

/-- position of `s` in a list (`99` if absent) -/
def idxIn : List Nat → Nat → Nat
  | [], _ => 99
  | x :: xs, s => if x == s then 0 else idxIn xs s + 1

/-- entries `(row, col, value)` of a sparse operator restricted to the sector (positions in `sector`) -/
def sectorEntries (A : SOp) : List (Nat × Nat × Int) :=
  sector.flatMap fun s => (A s).map fun p => (idxIn sector p.1, idxIn sector s, p.2)

/-- equal as sets: same length and mutual containment -/
def sameSet (a b : List (Nat × Nat × Int)) : Bool :=
  a.length == b.length && a.all (fun e => b.contains e) && b.all (fun e => a.contains e)

/-- `U_ij^dagger = c_{R,j} c^dagger_{L,i}` -/
def Udop (i j : Nat) : SOp := comp (mode false 4 (2 + j)) (mode true 4 i)

/-- the eight link matrices of the certificate, verbatim -/
def linkOpsData : List (List (Nat × Nat × Int)) := rishonHBCert.linkOps

/-- certificate link lists = `Uop` / `Udop` on the sector, `Ud` = transpose of `U`, sector preserved. -/
theorem hb_link_ops_from_jw : (List.range 2).all (fun i => (List.range 2).all (fun j =>
    sameSet (linkOpsData.getD (2 * i + j) []) (sectorEntries (Uop i j)) &&
    sameSet (linkOpsData.getD (4 + 2 * i + j) []) (sectorEntries (Udop i j)) &&
    sameSet (linkOpsData.getD (4 + 2 * i + j) []) ((linkOpsData.getD (2 * i + j) []).map (fun e => (e.2.1, e.1, e.2.2))) &&
    sector.all (fun s => (Uop i j s).all (fun p => sector.contains p.1) && (Udop i j s).all (fun p => sector.contains p.1))))
    = true := by
  decide +kernel

theorem hb_link_ops_count : linkOpsData.length = 8 := by decide +kernel

/-- `U11 U22 - U12 U21 = 2 U11 U22 = det U` on all 16 states of one link. -/
theorem det_u_identity :
    OpEq 4 (add (comp (Uop 0 0) (Uop 1 1)) (smul (-1) (comp (Uop 0 1) (Uop 1 0)))) detU := by
  decide +kernel

/-- the link operators `U_ij` commute pairwise -/
theorem u_commute : ∀ i < 2, ∀ j < 2, ∀ k < 2, ∀ l < 2,
    OpEq 4 (comp (Uop i j) (Uop k l)) (comp (Uop k l) (Uop i j)) := by
  decide +kernel

end Su2Plaq.Rishon
