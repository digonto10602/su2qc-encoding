import Su2PlaqCert.Json
import Su2PlaqCert.Sha256
import Su2PlaqCert.Rishon.Gates3
import Su2PlaqCert.Rishon.Pins3

/-!
# Su2PlaqCert.Rishon.Check3 — the exact acceptance test of a three-angle certificate of a rishon inner circuit (prompts/203 §3.2)

`check c` is `true` iff, for every one of the 1296 valid inner codes `k` (each link nibble in `{3, 5, 6, 9, 10, 12}`; the checker
generates this list itself and compares it with the certificate's `states`), the gate list replayed exactly on the basis state
`|code_k⟩` (ancillas 0, outer register not present) gives `c_ph · Σ_i V[i,k] |code_i⟩` as a sparse vector with Laurent-`K`
coefficients in `(z_α, z_β, z_γ)`: block exactness, zero leak and clean ancillas in one identity, for all angles.  `V` is the target
of the certificate, pinned by SHA-256 of its canonical text at its own base against `Pins3` (the exporter's exact data); `c_ph = k
z^m` is the supplied global phase.  The circuit's global phase is not part of the gate list (absorbed in `c_ph`).
-/
namespace Su2PlaqCert.Rishon
open Lean Su2PlaqCert

structure Cert3 where
  nQubits : Nat
  nData : Nat
  nOuter : Nat
  gates : Array Gate3
  /-- the inner codes, in state-index order -/
  states : Array Nat
  /-- `(i, j, V[i, j])`, sparse -/
  entries : Array (Nat × Nat × Lp3)
  phaseK : K
  phaseExp : Exp3
  hasTarget : Bool
  kind : String := ""
  order : Nat := 1
  dAlpha : Nat := 1
  dBeta : Nat := 1
  dGamma : Nat := 1

/-! ## the inner codes -/

def sectorCodes : List Nat := [3, 5, 6, 9, 10, 12]

/-- The 1296 inner codes `∑_l s_l 2^{4l}`, `s_l` in the link sector, sorted. -/
def innerCodes : Array Nat := Id.run do
  let mut out : Array Nat := #[]
  for a in sectorCodes do
    for b in sectorCodes do
      for c in sectorCodes do
        for d in sectorCodes do
          out := out.push (a + 16 * b + 256 * c + 4096 * d)
  return out.qsort (· < ·)

/-! ## canonical text of the target (the pinned object) -/

def ratText (r : Rat) : String := if r.den == 1 then toString r.num else s!"{r.num}/{r.den}"

def kText (k : K) : String :=
  ",".intercalate ([k.a, k.b, k.c, k.d, k.e, k.f, k.g, k.h].map ratText)

/-- Entries sorted by `(i, j)`, one line each, terms by exponent, exponents divided exactly by the base ratio `(fa, fb, fg)`. -/
def Cert3.targetText (c : Cert3) (fa fb fg : Nat) : Except String String := do
  let es := c.entries.qsort fun x y => x.1 < y.1 || (x.1 == y.1 && x.2.1 < y.2.1)
  let mut out := ""
  let mut prev : Option (Nat × Nat) := none
  for (i, j, lp) in es do
    if prev == some (i, j) then throw s!"target entry ({i}, {j}) listed twice"
    prev := some (i, j)
    let mut terms : List String := []
    for ((ma, mb, mg), k) in lp do
      if ma % (fa : Int) != 0 || mb % (fb : Int) != 0 || mg % (fg : Int) != 0 then
        throw "target exponent not divisible by the base ratio"
      terms := terms ++ [s!"({ma / (fa : Int)},{mb / (fb : Int)},{mg / (fg : Int)})={kText k}"]
    out := out ++ s!"E{i},{j}:" ++ ";".intercalate terms ++ "\n"
  pure out

def Cert3.pinError (c : Cert3) : Option String :=
  match Pins3.targetBase c.kind c.order with
  | none => some s!"unknown target kind '{c.kind}' (order {c.order})"
  | some (ta, tb, tg) =>
    if ta == 0 || tb == 0 || tg == 0 || c.dAlpha == 0 || c.dBeta == 0 || c.dGamma == 0
        || c.dAlpha % ta != 0 || c.dBeta % tb != 0 || c.dGamma % tg != 0 then
      some "base must be a positive multiple of the target's base"
    else
      match c.targetText (c.dAlpha / ta) (c.dBeta / tb) (c.dGamma / tg) with
      | .error e => some e
      | .ok t =>
        if some (Sha256.ofString t) == Pins3.targetSha256 c.kind c.order then none
        else some s!"target differs from the pinned exact {c.kind} target (SHA-256)"

/-! ## structural validation and the check -/

def Cert3.validate (c : Cert3) : Except String Unit := do
  if c.nQubits > 62 then throw "more than 62 qubits"
  if c.nData != 16 || c.nOuter != 0 then throw "the certificate must have 16 data qubits and no outer register"
  if c.nData > c.nQubits then throw "register sizes exceed n_qubits"
  for g in c.gates do g.validate c.nQubits
  if c.states != innerCodes then throw "states differ from the 1296 inner codes"
  if !c.hasTarget then throw "certificate has no target"
  for (i, j, _) in c.entries do
    if i ≥ c.states.size || j ≥ c.states.size then throw s!"target entry index ({i}, {j}) out of range"
  match c.pinError with
  | some e => throw e
  | none => pure ()

/-- Target columns: for state `j` the terms `(code_i, V[i,j])`. -/
def Cert3.columns (c : Cert3) : Array (Array (Nat × Lp3)) :=
  c.entries.foldl (init := Array.replicate c.states.size #[]) fun acc (i, j, lp) =>
    acc.modify j fun col => col.push (c.states[i]!, lp)

/-- Expected output of state `k`: `c_ph · ∑_i V[i,k] |code_i⟩`. -/
def Cert3.expected (c : Cert3) (col : Array (Nat × Lp3)) : State3 :=
  let phase := Lp3.mono c.phaseExp c.phaseK
  State3.normalize (col.map fun (code, lp) => (code, Lp3.mul phase lp))

def Cert3.checkState (c : Cert3) (cols : Array (Array (Nat × Lp3))) (k : Nat) : Option String :=
  let out := runGates3 c.gates #[(c.states[k]!, Lp3.const K.one)]
  if out == c.expected cols[k]! then none else some s!"state {k} differs from the target"

/-- `none` if accepted, otherwise the reason of the first (lowest-index) violated state.  The states are independent, so they are
checked in parallel tasks (pure: the result does not depend on the schedule). -/
def Cert3.firstError (c : Cert3) : Option String :=
  match c.validate with
  | .error e => some e
  | .ok () =>
    let cols := c.columns
    let tasks := (List.range c.states.size).map fun k => Task.spawn fun _ => c.checkState cols k
    tasks.foldl (fun r t => match r with
      | some e => some e
      | none => t.get) none

def check (c : Cert3) : Bool := (c.firstError).isNone

/-! ## JSON -/

def parseExp3 (j : Json) : Except String Exp3 := do
  let arr ← j.getArr?
  if arr.size != 3 then throw "exponent must be [m_alpha, m_beta, m_gamma]"
  pure (← (arr[0]!).getInt?, ← (arr[1]!).getInt?, ← (arr[2]!).getInt?)

def parseLp3 (j : Json) : Except String Lp3 := do
  let arr ← j.getArr?
  let mut out : Lp3 := []
  for t in arr do
    let ta ← t.getArr?
    if ta.size != 2 then throw "Laurent term must be [[ma,mb,mg],[8 rationals]]"
    let e ← parseExp3 ta[0]!
    let k ← parseK ta[1]!
    out := Lp3.add out (Lp3.mono e k)
  pure out

def parseGate3 (j : Json) : Except String Gate3 := do
  let name ← (← j.getObjVal? "g").getStr?
  let kind ← match GateKind.ofString? name with
    | some k => pure k
    | none => throw s!"unsupported gate {name}"
  let qs ← (← (← j.getObjVal? "q").getArr?).mapM (·.getNat?)
  let m ← match j.getObjVal? "m" with
    | .ok mj => parseExp3 mj
    | .error _ => pure ((0 : Int), (0 : Int), (0 : Int))
  pure { kind, qs, m }

def schema3 : String := "su2plaq-rishon-cert3-1"

def parseCert3 (j : Json) : Except String Cert3 := do
  let schema ← (← j.getObjVal? "schema").getStr?
  if schema != schema3 then throw s!"unknown schema {schema}"
  let nQubits ← (← j.getObjVal? "n_qubits").getNat?
  let nData ← (← j.getObjVal? "n_data").getNat?
  let nOuter ← (← j.getObjVal? "n_outer").getNat?
  let gates ← (← (← j.getObjVal? "gates").getArr?).mapM parseGate3
  let states ← match j.getObjVal? "states" with
    | .ok s => do (← s.getArr?).mapM (·.getNat?)
    | .error _ => pure #[]
  let hasTarget := (j.getObjVal? "target").isOk
  let (kind, order, entries) ← match j.getObjVal? "target" with
    | .ok t => do
      let k ← match t.getObjVal? "kind" with
        | .ok kj => kj.getStr?
        | .error _ => pure ""
      let o ← match t.getObjVal? "order" with
        | .ok oj => oj.getNat?
        | .error _ => pure 1
      let es ← (← (← t.getObjVal? "entries").getArr?).mapM fun e => do
        let ea ← e.getArr?
        if ea.size != 3 then throw "target entry must be [i, j, laurent3]"
        pure (← ea[0]!.getNat?, ← ea[1]!.getNat?, ← parseLp3 ea[2]!)
      pure (k, o, es)
    | .error _ => pure ("", 1, #[])
  let (phaseK, phaseExp) ← match j.getObjVal? "phase" with
    | .ok p => do pure (← parseK (← p.getObjVal? "k"), ← parseExp3 (← p.getObjVal? "m"))
    | .error _ => pure (K.one, ((0 : Int), (0 : Int), (0 : Int)))
  let (dAlpha, dBeta, dGamma) ← match j.getObjVal? "base" with
    | .ok b => do
      pure (← (← b.getObjVal? "d_alpha").getNat?, ← (← b.getObjVal? "d_beta").getNat?, ← (← b.getObjVal? "d_gamma").getNat?)
    | .error _ => pure (1, 1, 1)
  pure { nQubits, nData, nOuter, gates, states, entries, phaseK, phaseExp, hasTarget, kind, order, dAlpha, dBeta, dGamma }

def readCert3 (path : String) : IO (Except String Cert3) := do
  try
    let txt ← IO.FS.readFile path
    match Json.parse txt with
    | .error e => pure (.error s!"json: {e}")
    | .ok j => pure (parseCert3 j)
  catch e => pure (.error s!"cannot read {path}: {e}")

/-- Parse and check a certificate given as JSON text (the statement proved by `lean/certs/rishon-*.lean` via `native_decide`). -/
def checkJsonString (s : String) : Bool :=
  match Json.parse s with
  | .error _ => false
  | .ok j =>
    match parseCert3 j with
    | .error _ => false
    | .ok c => check c

end Su2PlaqCert.Rishon
