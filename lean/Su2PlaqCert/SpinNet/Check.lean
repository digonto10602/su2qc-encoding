import Su2PlaqCert.Check
import Su2PlaqCert.SpinNet.Pins

/-!
# Su2PlaqCert.SpinNet.Check — exact acceptance test of a circuit certificate for the 16-qubit spin-network encoding

Same statement as `Su2PlaqCert.Cert.check` (every physical state `ψ_k`: `U ψ_k = c ∑ V[k',k] ψ_k'` as exact Laurent-`K`
vectors; the gate replay, target expansion and per-state comparison are `Cert.stateOf`, `Cert.expected`, `Cert.checkRange`
of the laptop's checker, reused read-only), but the pinned data are the spin-network ones (`Su2PlaqCert.SpinNet.Pins`: 433
unit codes of the data|outer register = 8 + 8 qubits, route-B targets at base `(d_alpha, d_beta) = (4, 4)`), not the
twelve-qubit ones.  Only `validate` differs from the laptop's: no twelve-qubit pins, register sizes 8 + 8.
-/
namespace Su2PlaqCert.SpinNet

/-- Pin check against `Su2PlaqCert.SpinNet.Pins` (states, then target at its own base). -/
def pinError (c : Cert) : Option String :=
  if Sha256.ofString c.statesText != Pins.statesSha256 then
    some "states differ from the pinned exact spin-network states (SHA-256)"
  else
    match Pins.targetBase c.kind c.order with
    | none => some s!"unknown target kind '{c.kind}' (order {c.order})"
    | some (ta, tb) =>
      if ta == 0 || tb == 0 || c.dAlpha == 0 || c.dBeta == 0 || c.dAlpha % ta != 0 || c.dBeta % tb != 0 then
        some "base must be a positive multiple of the target's base"
      else
        match c.targetText (c.dAlpha / ta) (c.dBeta / tb) with
        | .error e => some e
        | .ok t =>
          if some (Sha256.ofString t) == Pins.targetSha256 c.kind c.order then none
          else some s!"target differs from the pinned exact {c.kind} target (SHA-256)"

def physicalDim : Nat := 433

/-- Structural validation (before any gate is replayed): the laptop's `Cert.validate` with the spin-network register sizes
and pins. -/
def validate (c : Cert) : Except String Unit := do
  if c.nQubits > 62 then throw "more than 62 qubits"
  if c.nData != 8 || c.nOuter != 8 then throw "the spin-network encoding has 8 data and 8 outer qubits"
  if c.nData + c.nOuter > c.nQubits then throw "register sizes exceed n_qubits"
  for g in c.gates do g.validate c.nQubits
  for st in c.states do
    for (code, _) in st do
      if code ≥ 2 ^ (c.nData + c.nOuter) then throw "state has support on an ancilla qubit"
  if !c.hasTarget then throw "certificate has no target"
  if c.states.size != physicalDim then
    throw s!"certificate has {c.states.size} states, the physical subspace has {physicalDim}"
  for k in [0:c.states.size] do
    let st := c.states[k]!
    if st.isEmpty then throw s!"state {k} is empty"
    let sorted := (st.map (·.1)).qsort (· < ·)
    if sorted.zipIdx.any (fun (x, i) => i > 0 && x == sorted[i-1]!) then
      throw s!"state {k} lists a basis state twice"
  for b in c.blocks do
    if b.ks.isEmpty then throw "empty target block"
    for (i, j, _) in b.entries do
      if i ≥ b.ks.size || j ≥ b.ks.size then throw s!"target entry index ({i}, {j}) outside a block of size {b.ks.size}"
  match c.gramError with
  | some e => throw e
  | none => pure ()
  match pinError c with
  | some e => throw e
  | none => pure ()

/-- `none` if accepted, otherwise the reason of the first violated state (states checked in parallel, as the laptop's). -/
def check (c : Cert) : Option String :=
  match validate c with
  | .error e => some e
  | .ok () =>
    match c.blockOf with
    | .error e => some e
    | .ok pos =>
      let n := c.states.size
      let tasks := (List.range n).map fun i => Task.spawn fun _ => c.checkRange pos i (min (i + 1) n)
      tasks.foldl (fun r t => match r with
        | some e => some e
        | none => t.get) none

end Su2PlaqCert.SpinNet
