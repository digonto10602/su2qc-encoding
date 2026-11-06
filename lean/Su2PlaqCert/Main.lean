import Su2PlaqCert

/-!
Entry point of the exact certificate checker `su2plaq_cert` (prompts/006 §2, §4).

* `check <cert.json>`: prints exactly one line, `ACCEPT` or `REJECT <reason>`; exit code 0 / 1.
* `eval <cert.json> <input_index>`: exact output of the gate list on the basis state `input_index` (JSON on stdout).
* `structure <structure-cert.json>`: `ACCEPT` / `REJECT <reason>` (step 2.L6).
-/
open Su2PlaqCert

def kJson (k : K) : String :=
  let cs := [k.a, k.b, k.c, k.d, k.e, k.f, k.g, k.h].map fun r => "\"" ++ ratStr r ++ "\""
  "[" ++ ", ".intercalate cs ++ "]"

def lpJson (p : Lp) : String :=
  "[" ++ ", ".intercalate (p.map fun ((ma, mb), k) => s!"[{ma}, {mb}, {kJson k}]") ++ "]"

def stateJson (st : State) : String :=
  "{\"out\": [" ++ ", ".intercalate (st.toList.map fun (key, lp) => s!"\{\"key\": {key}, \"terms\": {lpJson lp}}") ++ "]}"

def verdict (r : Option String) : IO UInt32 :=
  match r with
  | none => do IO.println "ACCEPT"; pure 0
  | some why => do IO.println s!"REJECT {why.replace "\n" " "}"; pure 1

def main (args : List String) : IO UInt32 := do
  match args with
  | ["check", path] =>
    match ← readCert path with
    | .error e => verdict (some e)
    | .ok c => verdict c.check
  | ["eval", path, idx] =>
    match ← readCert path, idx.toNat? with
    | .error e, _ => verdict (some e)
    | _, none => verdict (some "input index must be a natural number")
    | .ok c, some i =>
      match (do for g in c.gates do g.validate c.nQubits : Except String Unit) with
      | .error e => verdict (some e)
      | .ok () =>
        IO.println (stateJson (runGates c.gates #[(i, Lp.const K.one)]))
        pure 0
  | ["sha256", path] => do
    IO.println (Sha256.ofBytes (← IO.FS.readBinFile path)); pure 0
  | ["fingerprint", path] =>
    match ← readCert path with
    | .error e => verdict (some e)
    | .ok c =>
      IO.println s!"states {Sha256.ofString c.statesText}"
      match Pins.targetBase c.kind c.order with
      | some (ta, tb) =>
        match c.targetText (c.dAlpha / ta) (c.dBeta / tb) with
        | .ok t => IO.println s!"target {Sha256.ofString t}"; pure 0
        | .error e => verdict (some e)
      | none => verdict (some "unknown target kind")
  | ["structure", path] => verdict (← checkStructurePath path)
  | _ => verdict (some "usage: su2plaq_cert (check|eval|structure) <file> [index]")
