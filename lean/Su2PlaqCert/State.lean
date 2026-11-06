import Su2PlaqCert.Laurent
import Std.Data.HashMap

/-!
# Su2PlaqCert.State — sparse exact states

A state is an array of `(basis integer, Laurent coefficient)`; the basis integer has bit `q` = qubit `q`
(little-endian, as `sparse_sim`).
-/
namespace Su2PlaqCert

abbrev State := Array (Nat × Lp)

namespace State

/-- Add `lp` to the coefficient of `key` in a hash map. -/
def accum (m : Std.HashMap Nat Lp) (key : Nat) (lp : Lp) : Std.HashMap Nat Lp :=
  match m.get? key with
  | some old => m.insert key (Lp.add old lp)
  | none => m.insert key lp

/-- Canonical form: drop zero coefficients, sort by basis integer. -/
def normalize (s : State) : State :=
  (s.filter fun t => !t.2.isEmpty).qsort fun x y => x.1 < y.1

def ofMap (m : Std.HashMap Nat Lp) : State :=
  normalize (m.fold (fun acc k v => acc.push (k, v)) #[])

def bit (key q : Nat) : Bool := key.testBit q

end State
end Su2PlaqCert
