import Lean.Data.Json
import Su2PlaqCert.Gates

/-!
# Su2PlaqCert.Json — certificate data and its JSON reader (prompts/006 §4)

Only `Lean.Data.Json` (part of the Lean distribution, not Mathlib) is used.  Rationals are strings `"p/q"` or `"p"`.
-/
namespace Su2PlaqCert
open Lean

structure Block where
  ks : Array Nat
  /-- `(i, j, V[ks i, ks j])` -/
  entries : Array (Nat × Nat × Lp)
  deriving Inhabited

structure Cert where
  nQubits : Nat
  nData : Nat
  nOuter : Nat
  gates : Array Gate
  /-- the exact physical states: terms `(basis integer, coefficient)`, indexed by `k` -/
  states : Array (Array (Nat × K))
  blocks : Array Block
  phaseK : K
  phaseExp : Exp
  hasTarget : Bool

def parseRat (s : String) : Except String Rat :=
  match s.splitOn "/" with
  | [p] => match p.toInt? with
    | some n => pure (n : Rat)
    | none => throw s!"bad rational {s}"
  | [p, q] => match p.toInt?, q.toNat? with
    | some n, some d => if d == 0 then throw s!"zero denominator in {s}" else pure (mkRat n d)
    | _, _ => throw s!"bad rational {s}"
  | _ => throw s!"bad rational {s}"

def parseK (j : Json) : Except String K := do
  let arr ← j.getArr?
  if arr.size != 8 then throw "K element must have 8 components"
  let r (i : Nat) : Except String Rat := do parseRat (← (arr[i]!).getStr?)
  pure ⟨← r 0, ← r 1, ← r 2, ← r 3, ← r 4, ← r 5, ← r 6, ← r 7⟩

def parseExp (j : Json) : Except String Exp := do
  let arr ← j.getArr?
  if arr.size != 2 then throw "exponent must be [m_alpha, m_beta]"
  pure (← (arr[0]!).getInt?, ← (arr[1]!).getInt?)

def parseLp (j : Json) : Except String Lp := do
  let arr ← j.getArr?
  let mut out : Lp := []
  for t in arr do
    let ta ← t.getArr?
    if ta.size != 2 then throw "Laurent term must be [[ma,mb],[8 rationals]]"
    let e ← parseExp ta[0]!
    let k ← parseK ta[1]!
    out := Lp.add out (Lp.mono e k)
  pure out

def parseGate (j : Json) : Except String Gate := do
  let name ← (← j.getObjVal? "g").getStr?
  let kind ← match GateKind.ofString? name with
    | some k => pure k
    | none => throw s!"unsupported gate {name}"
  let qs ← (← j.getObjVal? "q").getArr?
  let qs ← qs.mapM (·.getNat?)
  let m ← match j.getObjVal? "m" with
    | .ok mj => parseExp mj
    | .error _ => pure (0, 0)
  pure { kind, qs, m }

def parseState (j : Json) : Except String (Nat × Array (Nat × K)) := do
  let k ← (← j.getObjVal? "k").getNat?
  let terms ← (← j.getObjVal? "terms").getArr?
  let ts ← terms.mapM fun t => do
    let code ← (← t.getObjVal? "code").getNat?
    let c ← parseK (← t.getObjVal? "c")
    pure (code, c)
  pure (k, ts)

def parseBlock (j : Json) : Except String Block := do
  let ks ← (← (← j.getObjVal? "ks").getArr?).mapM (·.getNat?)
  let es ← (← j.getObjVal? "entries").getArr?
  let entries ← es.mapM fun e => do
    let ea ← e.getArr?
    if ea.size != 3 then throw "block entry must be [i, j, laurent]"
    pure (← ea[0]!.getNat?, ← ea[1]!.getNat?, ← parseLp ea[2]!)
  pure { ks, entries }

def parseCert (j : Json) : Except String Cert := do
  let schema ← (← j.getObjVal? "schema").getStr?
  if schema != "su2plaq-cert-1" then throw s!"unknown schema {schema}"
  let nQubits ← (← j.getObjVal? "n_qubits").getNat?
  let nData ← (← j.getObjVal? "n_data").getNat?
  let nOuter ← (← j.getObjVal? "n_outer").getNat?
  let gates ← (← (← j.getObjVal? "gates").getArr?).mapM parseGate
  let hasTarget := (j.getObjVal? "target").isOk
  let sts ← match j.getObjVal? "states" with
    | .ok s => do (← s.getArr?).mapM parseState
    | .error _ => pure #[]
  let mut states : Array (Array (Nat × K)) := Array.replicate sts.size #[]
  let mut seen : Array Bool := Array.replicate sts.size false
  for (k, ts) in sts do
    if k ≥ sts.size then throw s!"state index {k} out of range"
    if seen[k]! then throw s!"duplicate state index {k}"
    seen := seen.set! k true
    states := states.set! k ts
  let blocks ← match j.getObjVal? "target" with
    | .ok t => do (← (← t.getObjVal? "blocks").getArr?).mapM parseBlock
    | .error _ => pure #[]
  let (phaseK, phaseExp) ← match j.getObjVal? "phase" with
    | .ok p => do pure (← parseK (← p.getObjVal? "k"), ← parseExp (← p.getObjVal? "m"))
    | .error _ => pure (K.one, ((0 : Int), (0 : Int)))
  pure { nQubits, nData, nOuter, gates, states, blocks, phaseK, phaseExp, hasTarget }

def readCert (path : String) : IO (Except String Cert) := do
  try
    let txt ← IO.FS.readFile path
    match Json.parse txt with
    | .error e => pure (.error s!"json: {e}")
    | .ok j => pure (parseCert j)
  catch e => pure (.error s!"cannot read {path}: {e}")

end Su2PlaqCert
