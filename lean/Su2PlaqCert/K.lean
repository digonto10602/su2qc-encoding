/-!
# Su2PlaqCert.K — the exact coefficient field `K = ℚ(i, √2, √3)` (docs/METHODS.md §11.2)

Mathlib-free and computable.  An element is `a + b i + c √2 + d i√2 + e √3 + f i√3 + g √6 + h i√6`, all coefficients
rational (`Rat` of Lean core).  Clifford+T entries lie in `ℤ[1/√2, i]`; corner singlets of spin-1/2 ends have
coefficients in `ℚ(√2, √3)` (measured).
-/
namespace Su2PlaqCert

structure K where
  a : Rat := 0
  b : Rat := 0
  c : Rat := 0
  d : Rat := 0
  e : Rat := 0
  f : Rat := 0
  g : Rat := 0
  h : Rat := 0
  deriving BEq, Repr, Inhabited

namespace K

def zero : K := {}
def one : K := { a := 1 }
def neg1 : K := { a := -1 }
def I : K := { b := 1 }
def negI : K := { b := -1 }
/-- `ω = e^{iπ/4} = (√2 + i√2)/2`. -/
def omega : K := { c := 1/2, d := 1/2 }
/-- `ω̄ = e^{-iπ/4}`. -/
def omegaBar : K := { c := 1/2, d := -1/2 }
def invSqrt2 : K := { c := 1/2 }

def add (x y : K) : K :=
  ⟨x.a + y.a, x.b + y.b, x.c + y.c, x.d + y.d, x.e + y.e, x.f + y.f, x.g + y.g, x.h + y.h⟩
def neg (x : K) : K := ⟨-x.a, -x.b, -x.c, -x.d, -x.e, -x.f, -x.g, -x.h⟩
def sub (x y : K) : K := add x (neg y)
def smul (r : Rat) (x : K) : K :=
  ⟨r * x.a, r * x.b, r * x.c, r * x.d, r * x.e, r * x.f, r * x.g, r * x.h⟩

/-- Product in `ℚ(i, √2)` with basis `(1, i, √2, i√2)`; `i² = -1`, `(√2)² = 2`. -/
def mulG (a b c d a' b' c' d' : Rat) : Rat × Rat × Rat × Rat :=
  ( a * a' - b * b' + 2 * (c * c' - d * d'),
    a * b' + b * a' + 2 * (c * d' + d * c'),
    a * c' + c * a' - b * d' - d * b',
    a * d' + d * a' + b * c' + c * b' )

/-- No component besides the rational part. -/
def isRat (x : K) : Bool :=
  x.b == 0 && x.c == 0 && x.d == 0 && x.e == 0 && x.f == 0 && x.g == 0 && x.h == 0

/-- No `√3` component (the element lies in `ℚ(i, √2)`). -/
def noSqrt3 (x : K) : Bool := x.e == 0 && x.f == 0 && x.g == 0 && x.h == 0

/-- Product, writing `x = P + Q√3`, `y = P' + Q'√3` with `P, Q ∈ ℚ(i,√2)`: `xy = PP' + 3QQ' + (PQ' + QP')√3`. -/
def mulGen (x y : K) : K :=
  let (pa, pb, pc, pd) := mulG x.a x.b x.c x.d y.a y.b y.c y.d
  let (qa, qb, qc, qd) := mulG x.e x.f x.g x.h y.e y.f y.g y.h
  let (ra, rb, rc, rd) := mulG x.a x.b x.c x.d y.e y.f y.g y.h
  let (sa, sb, sc, sd) := mulG x.e x.f x.g x.h y.a y.b y.c y.d
  ⟨pa + 3 * qa, pb + 3 * qb, pc + 3 * qc, pd + 3 * qd, ra + sa, rb + sb, rc + sc, rd + sd⟩

/-- Product with fast paths for rational factors and for elements without `√3` (same result as `mulGen`). -/
def mul (x y : K) : K :=
  if y.isRat then smul y.a x
  else if x.isRat then smul x.a y
  else if x.noSqrt3 && y.noSqrt3 then
    let (pa, pb, pc, pd) := mulG x.a x.b x.c x.d y.a y.b y.c y.d
    ⟨pa, pb, pc, pd, 0, 0, 0, 0⟩
  else mulGen x y

instance : Add K := ⟨add⟩
instance : Mul K := ⟨mul⟩
instance : Neg K := ⟨neg⟩

def isZero (x : K) : Bool := x == zero

end K
end Su2PlaqCert
