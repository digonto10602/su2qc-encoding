import Su2PlaqCert
open Su2PlaqCert Lean

def getK (j : Json) : K := match parseK j with | .ok k => k | .error e => panic! e

def rawLp (j : Json) : Lp :=
  match j.getArr? with
  | .error _ => panic! "arr"
  | .ok a => a.toList.map fun t =>
      match t.getArr? with
      | .ok ta => ((match parseExp ta[0]! with | .ok e => e | .error _ => panic! "e"), getK ta[1]!)
      | .error _ => panic! "t"

def main (args : List String) : IO UInt32 := do
  let txt ← IO.FS.readFile args[0]!
  let j := match Json.parse txt with | .ok j => j | .error e => panic! e
  let ks := (j.getObjVal? "k").toOption.get!.getArr?.toOption.get!
  let mut bad := 0
  let mut n := 0
  for t in ks do
    let g (nm : String) := getK (t.getObjVal? nm).toOption.get!
    let x := g "x"; let y := g "y"
    n := n + 1
    if !((x + y) == g "sum") then bad := bad + 1; IO.println s!"add bad {repr x} {repr y}"
    if !((x * y) == g "prod") then bad := bad + 1; IO.println s!"mul bad"
    if !(K.mulGen x y == g "prod") then bad := bad + 1; IO.println s!"mulGen bad"
    if !((-x) == g "neg") then bad := bad + 1; IO.println s!"neg bad"
    if !(K.conj (x * y) == K.conj x * K.conj y) then bad := bad + 1; IO.println "conj mult bad"
    if !((K.conj x * x).isReal) then bad := bad + 1; IO.println "norm not real"
    if !(K.conj (K.conj x) == x) then bad := bad + 1
    if !(K.sub x y == x + (-y)) then bad := bad + 1
    -- equality semantic: eq flag
    let eqf := (t.getObjVal? "eq").toOption.get!.getBool?.toOption.get!
    if (x == y) != eqf then bad := bad + 1; IO.println "eq bad"
  let ls := (j.getObjVal? "lp").toOption.get!.getArr?.toOption.get!
  let mut nl := 0
  for t in ls do
    nl := nl + 1
    let get (nm : String) := (t.getObjVal? nm).toOption.get!
    let norm (l : Lp) : Lp := (l.filter fun t => !t.2.isZero).mergeSort fun a b => Exp.lt a.1 b.1 || a.1 == b.1
    let p : Lp := norm (rawLp (get "p")); let q : Lp := norm (rawLp (get "q"))
    let es : Lp := rawLp (get "sum"); let ep : Lp := rawLp (get "prod")
    if !(Lp.add p q == es) then bad := bad + 1; IO.println "lp add bad"
    if !(Lp.mul p q == ep) then bad := bad + 1; IO.println "lp mul bad"
    if !(Lp.mul q p == ep) then bad := bad + 1; IO.println "lp mul comm bad"
    -- distributivity / scale
    let kk := K.omega
    if !(Lp.scale kk (Lp.add p q) == Lp.add (Lp.scale kk p) (Lp.scale kk q)) then bad := bad + 1; IO.println "scale bad"
    -- mulMono vs mul with mono
    if !(Lp.mulMono (1, -2) kk p == Lp.mul p (Lp.mono (1, -2) kk)) then bad := bad + 1; IO.println "mulMono bad"
  IO.println s!"K cases {n}, Lp cases {nl}, bad {bad}"
  pure (if bad == 0 then 0 else 1)
