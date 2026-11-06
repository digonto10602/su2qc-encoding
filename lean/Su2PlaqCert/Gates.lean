import Su2PlaqCert.Circuit

/-!
# Su2PlaqCert.Gates — exact action of one gate on a sparse state
-/
namespace Su2PlaqCert

namespace Gate

/-- Matrix `M[out][in]` of a branching single-qubit gate as `(M00, M01, M10, M11)`. -/
def matrix1 : GateKind → Option (K × K × K × K)
  | .h => some (K.invSqrt2, K.invSqrt2, K.invSqrt2, K.neg K.invSqrt2)
  | .sx =>
    let p : K := { a := 1/2, b := 1/2 }
    let q : K := { a := 1/2, b := -1/2 }
    some (p, q, q, p)
  | _ => none

/-- Phase `κ` picked up on `|1⟩` by a diagonal Clifford+T single-qubit gate. -/
def phase1 : GateKind → Option K
  | .z => some K.neg1 | .s => some K.I | .sdg => some K.negI
  | .t => some K.omega | .tdg => some K.omegaBar
  | _ => none

def flip (key q : Nat) : Nat := key ^^^ (1 <<< q)

/-- Apply a gate (assumed validated) to a state. -/
def apply (g : Gate) (st : State) : State :=
  let q := g.qs
  match g.kind with
  | .x => st.map fun (k, lp) => (flip k q[0]!, lp)
  | .cx => st.map fun (k, lp) => (if k.testBit q[0]! then flip k q[1]! else k, lp)
  | .ccx => st.map fun (k, lp) => (if k.testBit q[0]! && k.testBit q[1]! then flip k q[2]! else k, lp)
  | .swap => st.map fun (k, lp) =>
      (if k.testBit q[0]! != k.testBit q[1]! then flip (flip k q[0]!) q[1]! else k, lp)
  | .z | .s | .sdg | .t | .tdg =>
    let κ := (phase1 g.kind).getD K.one
    st.map fun (k, lp) => (k, if k.testBit q[0]! then Lp.mulMono (0, 0) κ lp else lp)
  | .p => st.map fun (k, lp) => (k, if k.testBit q[0]! then Lp.mulMono g.m K.one lp else lp)
  | .rz =>
    let h : Exp := (g.m.1 / 2, g.m.2 / 2)
    let hneg : Exp := (-h.1, -h.2)
    st.map fun (k, lp) => (k, Lp.mulMono (if k.testBit q[0]! then h else hneg) K.one lp)
  | .cz => st.map fun (k, lp) => (k, if k.testBit q[0]! && k.testBit q[1]! then Lp.mulMono (0, 0) K.neg1 lp else lp)
  | .cp => st.map fun (k, lp) => (k, if k.testBit q[0]! && k.testBit q[1]! then Lp.mulMono g.m K.one lp else lp)
  | .ccz =>
    st.map fun (k, lp) =>
      (k, if k.testBit q[0]! && k.testBit q[1]! && k.testBit q[2]! then Lp.mulMono (0, 0) K.neg1 lp else lp)
  | .h | .sx =>
    match matrix1 g.kind with
    | none => st
    | some (m00, m01, m10, m11) =>
      let qb := q[0]!
      let out := st.foldl (init := (∅ : Std.HashMap Nat Lp)) fun acc (k, lp) =>
        let b := k.testBit qb
        let base := if b then flip k qb else k
        let (c0, c1) := if b then (m01, m11) else (m00, m10)
        let acc := if c0.isZero then acc else State.accum acc base (Lp.mulMono (0, 0) c0 lp)
        if c1.isZero then acc else State.accum acc (flip base qb) (Lp.mulMono (0, 0) c1 lp)
      State.ofMap out

end Gate

/-- Run a gate list on a state. -/
def runGates (gs : Array Gate) (st : State) : State :=
  State.normalize (gs.foldl (fun s g => g.apply s) st)

end Su2PlaqCert
