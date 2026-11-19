import Su2PlaqCert.Rishon.Check3

/-!
Entry point of the rishon three-angle certificate checker `su2plaq_rishon_cert` (prompts/203 §3.2; copy of `su2plaq_cert`).

* `check <cert.json>`: prints exactly one line, `ACCEPT` or `REJECT <reason>`; exit code 0 / 1.
* `eval <cert.json> <input>`: exact output of the gate list on the basis state with integer `input` (JSON on stdout; Laurent terms
  `[ma, mb, mg, [8 rationals]]`).
* `fingerprint <cert.json>`: SHA-256 of the canonical target text at the certificate's own base ratio to the pinned base (regenerates `Pins3`).
-/
open Su2PlaqCert Su2PlaqCert.Rishon

def kJson (k : K) : String :=
  let cs := [k.a, k.b, k.c, k.d, k.e, k.f, k.g, k.h].map fun r => "\"" ++ ratText r ++ "\""
  "[" ++ ", ".intercalate cs ++ "]"

def lpJson (p : Lp3) : String :=
  "[" ++ ", ".intercalate (p.map fun ((ma, mb, mg), k) => s!"[{ma}, {mb}, {mg}, {kJson k}]") ++ "]"

def stateJson (st : State3) : String :=
  "{\"out\": [" ++ ", ".intercalate (st.toList.map fun (key, lp) => s!"\{\"key\": {key}, \"terms\": {lpJson lp}}") ++ "]}"

def verdict (r : Option String) : IO UInt32 :=
  match r with
  | none => do IO.println "ACCEPT"; pure 0
  | some why => do IO.println s!"REJECT {why.replace "\n" " "}"; pure 1

def main (args : List String) : IO UInt32 := do
  match args with
  | ["check", path] =>
    match ← readCert3 path with
    | .error e => verdict (some e)
    | .ok c => verdict c.firstError
  | ["eval", path, idx] =>
    match ← readCert3 path, idx.toNat? with
    | .error e, _ => verdict (some e)
    | _, none => verdict (some "input index must be a natural number")
    | .ok c, some i =>
      match (do for g in c.gates do g.validate c.nQubits : Except String Unit) with
      | .error e => verdict (some e)
      | .ok () =>
        IO.println (stateJson (runGates3 c.gates #[(i, Lp3.const K.one)]))
        pure 0
  | ["fingerprint", path] =>
    match ← readCert3 path with
    | .error e => verdict (some e)
    | .ok c =>
      match Pins3.targetBase c.kind c.order with
      | some (ta, tb, tg) =>
        match c.targetText (c.dAlpha / ta) (c.dBeta / tb) (c.dGamma / tg) with
        | .ok t => IO.println s!"target {Sha256.ofString t}"; pure 0
        | .error e => verdict (some e)
      | none => verdict (some "unknown target kind")
  | _ => verdict (some "usage: su2plaq_rishon_cert (check|eval|fingerprint) <file> [input]")
