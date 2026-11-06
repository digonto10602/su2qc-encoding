import Su2PlaqCert.Json

/-!
# Su2PlaqCert.Check — the exact acceptance test of a circuit certificate

`check cert` is `true` iff, for every physical state `ψ_k` (exact `K`-vector over the data|outer integer, ancillas 0),
`U ψ_k = c · ∑_{k'} V[k',k] ψ_{k'}` as sparse vectors with Laurent-`K` coefficients, where `U` is the gate list replayed
exactly, `V` the block-diagonal target and `c = k z_α^a z_β^b` the supplied phase.  An identity of Laurent polynomials
holds for every real pair of angles, so one certificate proves block exactness, zero leak, clean ancillas and Gauss for
all angles.  The circuit's global phase is not part of the gate list (it is absorbed in `c`).
-/
namespace Su2PlaqCert

/-- The state `ψ_k` with constant coefficients. -/
def Cert.stateOf (c : Cert) (k : Nat) : State :=
  State.normalize ((c.states[k]!).map fun (code, a) => (code, Lp.const a))

/-- `(block index, position)` of every state; `none` if some state is not covered exactly once. -/
def Cert.blockOf (c : Cert) : Except String (Array (Nat × Nat)) := do
  let mut pos : Array (Option (Nat × Nat)) := Array.replicate c.states.size none
  for bi in [0:c.blocks.size] do
    let b := c.blocks[bi]!
    for j in [0:b.ks.size] do
      let k := b.ks[j]!
      if k ≥ c.states.size then throw s!"target block refers to state {k} (only {c.states.size} states)"
      if (pos[k]!).isSome then throw s!"state {k} is covered by two target blocks"
      pos := pos.set! k (some (bi, j))
  let mut out : Array (Nat × Nat) := #[]
  for k in [0:c.states.size] do
    match pos[k]! with
    | some p => out := out.push p
    | none => throw s!"state {k} is not covered by any target block"
  pure out

/-- Expected output `c ∑_{i} V[ks i, k] ψ_{ks i}` for state `k` in block `bi`, position `j`. -/
def Cert.expected (c : Cert) (bi j : Nat) : State :=
  let b := c.blocks[bi]!
  let m := b.entries.foldl (init := (∅ : Std.HashMap Nat Lp)) fun acc (i, j', lp) =>
    if j' != j then acc
    else
      (c.states[b.ks[i]!]!).foldl (init := acc) fun acc (code, a) =>
        State.accum acc code (Lp.mul lp (Lp.const a))
  let phase := Lp.mono c.phaseExp c.phaseK
  State.normalize ((State.ofMap m).map fun (code, lp) => (code, Lp.mul phase lp))

/-- Structural validation of the certificate (before any gate is replayed). -/
def Cert.validate (c : Cert) : Except String Unit := do
  if c.nQubits > 62 then throw "more than 62 qubits"
  if c.nData + c.nOuter > c.nQubits then throw "register sizes exceed n_qubits"
  for g in c.gates do g.validate c.nQubits
  for st in c.states do
    for (code, _) in st do
      if code ≥ 2 ^ (c.nData + c.nOuter) then throw "state has support on an ancilla qubit"
  if !c.hasTarget then throw "certificate has no target"
  if c.states.isEmpty then throw "certificate has no states"

/-- `none` if accepted, otherwise the reason of the first violated state. -/
def Cert.check (c : Cert) : Option String :=
  match c.validate with
  | .error e => some e
  | .ok () =>
    match c.blockOf with
    | .error e => some e
    | .ok pos =>
      let rec go (k : Nat) (fuel : Nat) : Option String :=
        match fuel with
        | 0 => none
        | fuel + 1 =>
          if k ≥ c.states.size then none
          else
            let (bi, j) := pos[k]!
            let out := runGates c.gates (c.stateOf k)
            if out == c.expected bi j then go (k + 1) fuel
            else some s!"state {k} differs from the target"
      go 0 (c.states.size + 1)

def Cert.accepts (c : Cert) : Bool := (c.check).isNone

end Su2PlaqCert
