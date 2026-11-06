import Su2PlaqCert.K

/-!
# Su2PlaqCert.Laurent — Laurent polynomials in two unit-circle variables over `K`

`z_α = e^{iθ_α}`, `z_β = e^{iθ_β}`.  A polynomial is a list of `(exponent pair, coefficient)` sorted by exponent
(lexicographic) with no zero coefficients, so equality of lists is equality of polynomials.  Because `z_α, z_β` are
algebraically independent over `K` as formal variables, an identity of such lists implies the identity of functions
for every real `θ_α, θ_β`.
-/
namespace Su2PlaqCert

abbrev Exp := Int × Int
abbrev Lp := List (Exp × K)

def Exp.lt (x y : Exp) : Bool := x.1 < y.1 || (x.1 == y.1 && x.2 < y.2)

namespace Lp

/-- Sum of two sorted polynomials (merge); zero coefficients are removed. -/
def add : Lp → Lp → Lp
  | [], q => q
  | p, [] => p
  | (e, c) :: p, (e', c') :: q =>
    if e == e' then
      let s := c + c'
      if s.isZero then add p q else (e, s) :: add p q
    else if Exp.lt e e' then (e, c) :: add p ((e', c') :: q)
    else (e', c') :: add ((e, c) :: p) q
termination_by p q => p.length + q.length

def scale (k : K) (p : Lp) : Lp :=
  if k.isZero then [] else p.map fun t => (t.1, k * t.2)

def shift (e : Exp) (p : Lp) : Lp := p.map fun t => ((t.1.1 + e.1, t.1.2 + e.2), t.2)

/-- Multiply by the monomial `k z^e`. -/
def mulMono (e : Exp) (k : K) (p : Lp) : Lp :=
  if k.isZero then []
  else if k == K.one then p.map fun t => ((t.1.1 + e.1, t.1.2 + e.2), t.2)
  else p.map fun t => ((t.1.1 + e.1, t.1.2 + e.2), k * t.2)

def mul (p q : Lp) : Lp := q.foldl (fun acc t => add acc (mulMono t.1 t.2 p)) []

def const (k : K) : Lp := if k.isZero then [] else [((0, 0), k)]
def mono (e : Exp) (k : K) : Lp := if k.isZero then [] else [(e, k)]

end Lp
end Su2PlaqCert
