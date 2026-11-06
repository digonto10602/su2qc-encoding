import Su2PlaqCert.State

/-!
# Su2PlaqCert.Circuit — gate list of a certificate

Gate semantics are Qiskit's matrices (`SIM_BASIS` minus `u`, `unitary`), little-endian qubits:
`x z s sdg t tdg h sx rz p cx cz cp swap ccx ccz`.  Rotation angles are `m.1 * θ_α + m.2 * θ_β` with the base angles
of the certificate; `rz(θ) = diag(e^{-iθ/2}, e^{iθ/2})` therefore needs an even exponent vector (validated).
-/
namespace Su2PlaqCert

inductive GateKind where
  | x | z | s | sdg | t | tdg | h | sx | rz | p | cx | cz | cp | swap | ccx | ccz
  deriving BEq, Repr, Inhabited

def GateKind.ofString? : String → Option GateKind
  | "x" => some .x | "z" => some .z | "s" => some .s | "sdg" => some .sdg
  | "t" => some .t | "tdg" => some .tdg | "h" => some .h | "sx" => some .sx
  | "rz" => some .rz | "p" => some .p | "cx" => some .cx | "cz" => some .cz
  | "cp" => some .cp | "swap" => some .swap | "ccx" => some .ccx | "ccz" => some .ccz
  | _ => none

def GateKind.arity : GateKind → Nat
  | .x | .z | .s | .sdg | .t | .tdg | .h | .sx | .rz | .p => 1
  | .cx | .cz | .cp | .swap => 2
  | .ccx | .ccz => 3

def GateKind.hasAngle : GateKind → Bool
  | .rz | .p | .cp => true
  | _ => false

structure Gate where
  kind : GateKind
  qs : Array Nat
  m : Int × Int := (0, 0)
  deriving BEq, Repr, Inhabited

/-- Structural validity: arity, distinct qubits below `n`, even exponent for `rz`, no angle on angle-free gates. -/
def Gate.validate (n : Nat) (g : Gate) : Except String Unit := do
  if g.qs.size != g.kind.arity then throw s!"gate {repr g.kind}: wrong number of qubits"
  for q in g.qs do
    if q ≥ n then throw s!"gate qubit {q} out of range (n = {n})"
  if g.qs.size == 2 && g.qs[0]! == g.qs[1]! then throw "gate with repeated qubit"
  if g.qs.size == 3 && (g.qs[0]! == g.qs[1]! || g.qs[0]! == g.qs[2]! || g.qs[1]! == g.qs[2]!) then
    throw "gate with repeated qubit"
  if g.kind == .rz && (g.m.1 % 2 != 0 || g.m.2 % 2 != 0) then throw "rz exponent vector must be even"
  if !g.kind.hasAngle && g.m != (0, 0) then throw "angle exponent on an angle-free gate"

end Su2PlaqCert
