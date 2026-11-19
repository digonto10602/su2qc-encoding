import Su2PlaqCert.Gates
import Su2PlaqCert.Rishon.Laurent3

/-!
# Su2PlaqCert.Rishon.Gates3 — exact action of one gate on a sparse state with three-angle Laurent coefficients

The gate semantics of `Su2PlaqCert.Gate.apply` (Qiskit's matrices for `x z s sdg t tdg h sx rz p cx cz cp swap ccx ccz`, little-endian
qubits) over `Lp3`.  A rotation `p`, `cp` or `rz` carries the exponent triple `m` of its angle `m_α θ_α + m_β θ_β + m_γ θ_γ`; `rz(θ) =
diag(e^{-iθ/2}, e^{iθ/2})` uses the half exponent (`m` must be even in every slot, validated).  Gate kinds, `Gate.matrix1`, `Gate.phase1`
and `Gate.flip` are those of the two-variable checker (reused read-only).
-/
namespace Su2PlaqCert.Rishon
open Su2PlaqCert

structure Gate3 where
  kind : GateKind
  qs : Array Nat
  m : Exp3 := ((0 : Int), (0 : Int), (0 : Int))
  deriving BEq, Repr, Inhabited

abbrev State3 := Array (Nat × Lp3)

namespace State3

def accum (m : Std.HashMap Nat Lp3) (key : Nat) (lp : Lp3) : Std.HashMap Nat Lp3 :=
  match m.get? key with
  | some old => m.insert key (Lp3.add old lp)
  | none => m.insert key lp

/-- Canonical form: drop zero coefficients, sort by basis integer. -/
def normalize (s : State3) : State3 :=
  (s.filter fun t => !t.2.isEmpty).qsort fun x y => x.1 < y.1

def ofMap (m : Std.HashMap Nat Lp3) : State3 :=
  normalize (m.fold (fun acc k v => acc.push (k, v)) #[])

end State3

/-- Structural validity: arity, distinct qubits below `n`, even exponents for `rz`, no angle on angle-free gates. -/
def Gate3.validate (n : Nat) (g : Gate3) : Except String Unit := do
  if g.qs.size != g.kind.arity then throw s!"gate {repr g.kind}: wrong number of qubits"
  for q in g.qs do
    if q ≥ n then throw s!"gate qubit {q} out of range (n = {n})"
  if g.qs.size == 2 && g.qs[0]! == g.qs[1]! then throw "gate with repeated qubit"
  if g.qs.size == 3 && (g.qs[0]! == g.qs[1]! || g.qs[0]! == g.qs[2]! || g.qs[1]! == g.qs[2]!) then
    throw "gate with repeated qubit"
  if g.kind == .rz && (g.m.1 % 2 != 0 || g.m.2.1 % 2 != 0 || g.m.2.2 % 2 != 0) then
    throw "rz exponent vector must be even"
  if !g.kind.hasAngle && g.m != ((0 : Int), (0 : Int), (0 : Int)) then throw "angle exponent on an angle-free gate"

namespace Gate3

/-- Apply a gate (assumed validated) to a state. -/
def apply (g : Gate3) (st : State3) : State3 :=
  let q := g.qs
  let one : Exp3 := ((0 : Int), (0 : Int), (0 : Int))
  match g.kind with
  | .x => st.map fun (k, lp) => (Gate.flip k q[0]!, lp)
  | .cx => st.map fun (k, lp) => (if k.testBit q[0]! then Gate.flip k q[1]! else k, lp)
  | .ccx => st.map fun (k, lp) => (if k.testBit q[0]! && k.testBit q[1]! then Gate.flip k q[2]! else k, lp)
  | .swap => st.map fun (k, lp) =>
      (if k.testBit q[0]! != k.testBit q[1]! then Gate.flip (Gate.flip k q[0]!) q[1]! else k, lp)
  | .z | .s | .sdg | .t | .tdg =>
    let κ := (Gate.phase1 g.kind).getD K.one
    st.map fun (k, lp) => (k, if k.testBit q[0]! then Lp3.mulMono one κ lp else lp)
  | .p => st.map fun (k, lp) => (k, if k.testBit q[0]! then Lp3.mulMono g.m K.one lp else lp)
  | .rz =>
    let h : Exp3 := (g.m.1 / 2, g.m.2.1 / 2, g.m.2.2 / 2)
    let hneg : Exp3 := (-h.1, -h.2.1, -h.2.2)
    st.map fun (k, lp) => (k, Lp3.mulMono (if k.testBit q[0]! then h else hneg) K.one lp)
  | .cz => st.map fun (k, lp) => (k, if k.testBit q[0]! && k.testBit q[1]! then Lp3.mulMono one K.neg1 lp else lp)
  | .cp => st.map fun (k, lp) => (k, if k.testBit q[0]! && k.testBit q[1]! then Lp3.mulMono g.m K.one lp else lp)
  | .ccz =>
    st.map fun (k, lp) =>
      (k, if k.testBit q[0]! && k.testBit q[1]! && k.testBit q[2]! then Lp3.mulMono one K.neg1 lp else lp)
  | .h | .sx =>
    match Gate.matrix1 g.kind with
    | none => st
    | some (m00, m01, m10, m11) =>
      let qb := q[0]!
      let out := st.foldl (init := (∅ : Std.HashMap Nat Lp3)) fun acc (k, lp) =>
        let b := k.testBit qb
        let base := if b then Gate.flip k qb else k
        let (c0, c1) := if b then (m01, m11) else (m00, m10)
        let acc := if c0.isZero then acc else State3.accum acc base (Lp3.mulMono one c0 lp)
        if c1.isZero then acc else State3.accum acc (Gate.flip base qb) (Lp3.mulMono one c1 lp)
      State3.ofMap out

end Gate3

/-- Run a gate list on a state. -/
def runGates3 (gs : Array Gate3) (st : State3) : State3 :=
  State3.normalize (gs.foldl (fun s g => g.apply s) st)

end Su2PlaqCert.Rishon
