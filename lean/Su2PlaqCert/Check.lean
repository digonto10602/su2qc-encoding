import Su2PlaqCert.Json
import Su2PlaqCert.Sha256
import Su2PlaqCert.Pins

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

def ratStr (r : Rat) : String := if r.den == 1 then toString r.num else s!"{r.num}/{r.den}"

def kStr (k : K) : String :=
  ",".intercalate ([k.a, k.b, k.c, k.d, k.e, k.f, k.g, k.h].map ratStr)

/-- Canonical text of the states (one line per term, states in index order, terms by basis integer). -/
def Cert.statesText (c : Cert) : String :=
  c.states.zipIdx.foldl (init := "") fun acc (st, k) =>
    (st.qsort fun x y => x.1 < y.1).foldl (init := acc) fun acc (code, a) =>
      acc ++ s!"S{k}:{code}:{kStr a}\n"

/-- Canonical text of the target at the target's own base (exponents divided by `(fa, fb)`, exactly), blocks in order,
entries by `(i, j)`, terms by exponent. -/
def Cert.targetText (c : Cert) (fa fb : Nat) : Except String String := do
  let mut out := ""
  for b in c.blocks do
    out := out ++ "B" ++ ",".intercalate (b.ks.toList.map toString) ++ "\n"
    let es := b.entries.qsort fun x y => x.1 < y.1 || (x.1 == y.1 && x.2.1 < y.2.1)
    for (i, j, lp) in es do
      let mut terms : List String := []
      for ((ma, mb), k) in lp do
        if ma % (fa : Int) != 0 || mb % (fb : Int) != 0 then throw "target exponent not divisible by the base ratio"
        terms := terms ++ [s!"({ma / (fa : Int)},{mb / (fb : Int)})={kStr k}"]
      out := out ++ s!"E{i},{j}:" ++ ";".intercalate terms ++ "\n"
  pure out

/-- The states and the target must be the exporter's exact ones: compare SHA-256 fingerprints with `Pins`. -/
def Cert.pinError (c : Cert) : Option String :=
  if Sha256.ofString c.statesText != Pins.statesSha256 then
    some "states differ from the pinned exact physical basis (SHA-256)"
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

/-- Number of physical (Gauss-law) states of the 12-qubit encoding; the certificate must carry exactly these. -/
def physicalDim : Nat := 433

/-- Exact Gram matrix of the supplied states: orthonormal iff every diagonal entry is `1` and every off-diagonal entry is
`0`.  (Together with the exporter-side comparison against the exact physical basis this pins the state set.) -/
def Cert.gramErrorOf (states : Array (Array (Nat × K))) : Option String :=
  let byCode : Std.HashMap Nat (Array (Nat × K)) :=
    (states.zipIdx.foldl (init := (∅ : Std.HashMap Nat (Array (Nat × K)))) fun acc (st, k) =>
      st.foldl (init := acc) fun acc (code, a) =>
        acc.insert code ((acc.getD code #[]).push (k, a)))
  let gram : Std.HashMap Nat K :=
    byCode.fold (init := (∅ : Std.HashMap Nat K)) fun acc _ lst =>
      lst.foldl (init := acc) fun acc (k, a) =>
        lst.foldl (init := acc) fun acc (k', a') =>
          if k ≤ k' then
            let key := k * states.size + k'
            acc.insert key ((acc.getD key K.zero) + K.conj a * a')
          else acc
  let bad := gram.fold (init := (none : Option String)) fun r key v =>
    match r with
    | some _ => r
    | none =>
      let k := key / states.size
      let k' := key % states.size
      if k == k' then (if v == K.one then none else some s!"state {k} is not normalised")
      else (if v.isZero then none else some s!"states {k} and {k'} are not orthogonal")
  match bad with
  | some e => some e
  | none =>
    let diag := (List.range states.size).all fun k => gram.contains (k * states.size + k)
    if diag then none else some "a state has zero norm"

def Cert.gramError (c : Cert) : Option String := Cert.gramErrorOf c.states

/-- Structural validation of the certificate (before any gate is replayed). -/
def Cert.validate (c : Cert) : Except String Unit := do
  if c.nQubits > 62 then throw "more than 62 qubits"
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
  match c.pinError with
  | some e => throw e
  | none => pure ()

/-- Check the states `lo ≤ k < hi`: the reason of the first violated one, or `none`. -/
def Cert.checkRange (c : Cert) (pos : Array (Nat × Nat)) (lo hi : Nat) : Option String :=
  let rec go (k : Nat) (fuel : Nat) : Option String :=
    match fuel with
    | 0 => none
    | fuel + 1 =>
      if k ≥ hi then none
      else
        let (bi, j) := pos[k]!
        let out := runGates c.gates (c.stateOf k)
        if out == c.expected bi j then go (k + 1) fuel
        else some s!"state {k} differs from the target"
  go lo (hi - lo + 1)

/-- `none` if accepted, otherwise the reason of the first (lowest-index) violated state.  The states are independent, so
they are checked in parallel chunks (`Task.spawn`, pure: the result does not depend on the schedule). -/
def Cert.check (c : Cert) : Option String :=
  match c.validate with
  | .error e => some e
  | .ok () =>
    match c.blockOf with
    | .error e => some e
    | .ok pos =>
      let n := c.states.size
      let nChunks := n
      let chunk := (n + nChunks - 1) / nChunks
      let tasks := (List.range nChunks).map fun i =>
        Task.spawn fun _ => c.checkRange pos (i * chunk) (min ((i + 1) * chunk) n)
      tasks.foldl (fun r t => match r with
        | some e => some e
        | none => t.get) none

def Cert.accepts (c : Cert) : Bool := (c.check).isNone

/-- Parse and check a certificate given as JSON text (the statement proved by `lean/certs/*.lean` via `native_decide`). -/
def checkJsonString (s : String) : Bool :=
  match Lean.Json.parse s with
  | .error _ => false
  | .ok j =>
    match parseCert j with
    | .error _ => false
    | .ok c => c.accepts

end Su2PlaqCert
