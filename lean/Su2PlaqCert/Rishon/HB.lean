/-!
# Su2PlaqCert.Rishon.HB  (prompts/200 step 5.L3; METHODS-rishon R8)

Computable, Mathlib-free checker for the exact structure of the inner magnetic Hamiltonian
`H_B^in = -(W + W^T)` of the rishon plaquette on the `6^4 = 1296` valid inner codes.

All arithmetic is exact: numbers are integer pairs `(a, b)` meaning `a + b*sqrt 2` (`ZS`), and the
irrationality of `sqrt 2` makes the pair representation unique.  The certificate contains

* the eight sparse `6 x 6` link matrices `U[i][j]`, `Ud[i][j]` (integer entries), from which the checker
  recomputes `W = Tr(U_b U_r U_t^dag U_l^dag)` itself,
* 81 bright pairs `(4 u_p, 4 v_p, kappa_p)` as sparse `Z[sqrt 2]` vectors / a `Z[sqrt 2]` number.

`checkHB` is `true` iff all of the following hold (the claims of the certificate):

1. `16 (W + W^T) = sum_p kappa_p ((4u_p)(4v_p)^T + (4v_p)(4u_p)^T)` entrywise, i.e.
   `16 H_B = -sum_p kappa_p ((4u_p)(4v_p)^T + h.c.)`;
2. the 162 vectors `4u_p, 4v_p` are orthogonal with squared norm 16 (orthonormality of `u_p, v_p`);
3. the multiset of `kappa_p` is `{1 : 32, 2 : 48, 4 sqrt 2 : 1}` (81 pairs);
4. exactly 990 of the 1296 codes lie outside the support of every `u_p, v_p` (dark codes);
5. all indices are in range and the link data have the right shape.

Index convention: code `= sum_l s_l 6^l` with `s_l in {0..5}` the position of the link state in the sorted
two-rishon sector (link 0 least significant); `W[r, c]` is the matrix element `<r| W |c>`.
Link operator order in `linkOps`: `U00, U01, U10, U11, Ud00, Ud01, Ud10, Ud11`, each a list of `(row, col, value)`.
-/

namespace Su2PlaqCert.Rishon

/-- `a + b * sqrt 2` with integer `a`, `b`. -/
structure ZS where
  a : Int
  b : Int
  deriving BEq, Repr, Inhabited

namespace ZS
def zero : ZS := ⟨0, 0⟩
def add (x y : ZS) : ZS := ⟨x.a + y.a, x.b + y.b⟩
def mul (x y : ZS) : ZS := ⟨x.a * y.a + 2 * x.b * y.b, x.a * y.b + x.b * y.a⟩
def smul (k : Int) (x : ZS) : ZS := ⟨k * x.a, k * x.b⟩
def isZero (x : ZS) : Bool := x.a == 0 && x.b == 0
end ZS

/-- Sparse vector over the codes: `(code index, value)`. -/
abbrev SVec := List (Nat × ZS)

structure HBPair where
  kappa : ZS
  u : SVec      -- 4 u_p
  v : SVec      -- 4 v_p
  deriving Inhabited

structure HBCert where
  nCodes : Nat
  linkOps : List (List (Nat × Nat × Int))
  pairs : List HBPair
  deriving Inhabited

/-- Number of codes `6^4`. -/
def nCodes : Nat := 1296

/-- `cols[o][s]` = nonzero `(row, value)` of column `s` of link operator `o`. -/
def opColumns (ops : List (List (Nat × Nat × Int))) : Array (Array (List (Nat × Int))) :=
  ops.toArray.map fun op =>
    (Array.range 6).map fun s =>
      op.filterMap fun (r, c, v) => if c == s then some (r, v) else none

/-- Raw triples `(r * 1296 + c, W[r, c])` of `W = sum_{abcd} U[a][b] x U[b][c] x Ud[d][c] x Ud[a][d]`
(link 0 first), column by column.  Duplicate keys are summed later by `normalize`. -/
def wTriples (cols : Array (Array (List (Nat × Int)))) : Array (Nat × Int) := Id.run do
  let mut out : Array (Nat × Int) := #[]
  for code in [0:1296] do
    let s0 := code % 6
    let s1 := (code / 6) % 6
    let s2 := (code / 36) % 6
    let s3 := (code / 216) % 6
    for a in [0:2] do
      for b in [0:2] do
        for c in [0:2] do
          for d in [0:2] do
            let l0 := cols[2 * a + b]![s0]!
            let l1 := cols[2 * b + c]![s1]!
            let l2 := cols[4 + 2 * d + c]![s2]!
            let l3 := cols[4 + 2 * a + d]![s3]!
            for (r0, v0) in l0 do
              for (r1, v1) in l1 do
                for (r2, v2) in l2 do
                  for (r3, v3) in l3 do
                    let row := r0 + 6 * r1 + 36 * r2 + 216 * r3
                    out := out.push (row * 1296 + code, v0 * v1 * v2 * v3)
  return out

/-- Sort by key, add equal keys, drop zeros. -/
def normalize (xs : Array (Nat × ZS)) : List (Nat × ZS) := Id.run do
  let s := xs.qsort (fun x y => x.1 < y.1)
  let mut out : Array (Nat × ZS) := #[]
  for (k, z) in s do
    if out.size > 0 && (out[out.size - 1]!).1 == k then
      let (k0, z0) := out[out.size - 1]!
      out := out.set! (out.size - 1) (k0, z0.add z)
    else
      out := out.push (k, z)
  return (out.filter fun (_, z) => !z.isZero).toList

/-- `16 (W + W^T)` as normalised sparse triples, with `W` recomputed from the link matrices. -/
def lhsTriples (c : HBCert) : List (Nat × ZS) :=
  let w := wTriples (opColumns c.linkOps)
  let t : Array (Nat × ZS) := w.foldl (init := #[]) fun acc (k, v) =>
    let r := k / 1296
    let col := k % 1296
    (acc.push (k, ZS.smul 16 ⟨v, 0⟩)).push (col * 1296 + r, ZS.smul 16 ⟨v, 0⟩)
  normalize t

/-- `sum_p kappa_p ((4u_p)(4v_p)^T + (4v_p)(4u_p)^T)` as normalised sparse triples. -/
def rhsTriples (c : HBCert) : List (Nat × ZS) := Id.run do
  let mut t : Array (Nat × ZS) := #[]
  for p in c.pairs do
    for (i, x) in p.u do
      for (j, y) in p.v do
        let z := p.kappa.mul (x.mul y)
        t := (t.push (i * 1296 + j, z)).push (j * 1296 + i, z)
  return normalize t

def identityOK (c : HBCert) : Bool := lhsTriples c == rhsTriples c

def densify (v : SVec) : Array ZS := Id.run do
  let mut a : Array ZS := Array.replicate 1296 ZS.zero
  for (i, z) in v do
    a := a.set! i (a[i]!.add z)
  return a

def dot (x : SVec) (yd : Array ZS) : ZS :=
  x.foldl (fun acc (i, z) => acc.add (z.mul yd[i]!)) ZS.zero

/-- The 162 vectors `4u_p, 4v_p` are orthogonal with `<x, x> = 16`. -/
def orthoOK (c : HBCert) : Bool := Id.run do
  let vs : Array SVec := (c.pairs.flatMap fun p => [p.u, p.v]).toArray
  let ds := vs.map densify
  for i in [0:vs.size] do
    for j in [0:vs.size] do
      let want : ZS := if i == j then ⟨16, 0⟩ else ZS.zero
      if dot vs[i]! ds[j]! != want then
        return false
  return true

def kappaCount (c : HBCert) (k : ZS) : Nat := (c.pairs.filter fun p => p.kappa == k).length

/-- `{1 : 32, 2 : 48, 4 sqrt 2 : 1}`, 81 pairs in total. -/
def kappaOK (c : HBCert) : Bool :=
  kappaCount c ⟨1, 0⟩ == 32 && kappaCount c ⟨2, 0⟩ == 48 && kappaCount c ⟨0, 4⟩ == 1 && c.pairs.length == 81

def indicesOK (c : HBCert) : Bool :=
  c.pairs.all fun p => p.u.all (fun (i, _) => i < 1296) && p.v.all (fun (i, _) => i < 1296)

def linkShapeOK (c : HBCert) : Bool :=
  c.linkOps.length == 8 && c.linkOps.all fun op => op.all fun (r, s, _) => r < 6 && s < 6

/-- Number of codes outside the support of all `u_p, v_p`. -/
def darkCount (c : HBCert) : Nat := Id.run do
  let mut seen : Array Bool := Array.replicate 1296 false
  for p in c.pairs do
    for (i, z) in p.u do
      if !z.isZero then seen := seen.set! i true
    for (i, z) in p.v do
      if !z.isZero then seen := seen.set! i true
  return (seen.filter fun b => !b).size

def checkHBParts (c : HBCert) : List (String × Bool) :=
  let shape := c.nCodes == nCodes && linkShapeOK c && indicesOK c
  if shape then
    [("shape", true), ("kappa", kappaOK c), ("dark", darkCount c == 990),
     ("ortho", orthoOK c), ("identity", identityOK c)]
  else
    [("shape", false)]

/-- The certificate check: `true` iff every claim of the module header holds. -/
def checkHB (c : HBCert) : Bool := (checkHBParts c).all (·.2)

end Su2PlaqCert.Rishon
