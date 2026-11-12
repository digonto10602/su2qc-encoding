import Su2PlaqCert.LSH.Check
import Su2PlaqCert.Json

/-!
Entry point of the LSH certificate checker `su2plaq_cert_lsh` (prompts/400 step 7.L3; copy of `su2plaq_cert_spinnet`).

* `check <cert.json>`: prints exactly one line, `ACCEPT` or `REJECT <reason>`; exit code 0 / 1.
* `fingerprint <cert.json>`: SHA-256 of the canonical states / target text (to regenerate `Pins.lean`).
-/
open Su2PlaqCert

def verdict (r : Option String) : IO UInt32 :=
  match r with
  | none => do IO.println "ACCEPT"; pure 0
  | some why => do IO.println s!"REJECT {why.replace "\n" " "}"; pure 1

def main (args : List String) : IO UInt32 := do
  match args with
  | ["check", path] =>
    match ← readCert path with
    | .error e => verdict (some e)
    | .ok c => verdict (LSH.check c)
  | ["fingerprint", path] =>
    match ← readCert path with
    | .error e => verdict (some e)
    | .ok c =>
      IO.println s!"states {Sha256.ofString c.statesText}"
      match LSH.Pins.targetBase c.kind c.order with
      | some (ta, tb) =>
        match c.targetText (c.dAlpha / ta) (c.dBeta / tb) with
        | .ok t => IO.println s!"target {Sha256.ofString t}"; pure 0
        | .error e => verdict (some e)
      | none => verdict (some "unknown target kind")
  | _ => verdict (some "usage: su2plaq_cert_lsh (check|fingerprint) <file>")
