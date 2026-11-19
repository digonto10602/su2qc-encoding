import Su2PlaqCert.K

/-!
# Su2PlaqCert.Rishon.Laurent3 — Laurent polynomials in three unit-circle variables over `K`

`z_α = e^{iθ_α}`, `z_β = e^{iθ_β}`, `z_γ = e^{iθ_γ}` with `θ_γ = √2 β / d_γ` (prompts/203 §3.2, prompts/204 §2.1).  The same representation as
`Su2PlaqCert.Lp` with a triple of exponents: a sorted list of `(exponent triple, coefficient)` (lexicographic order, no zero coefficients), so
equality of lists is equality of polynomials.  The three variables are treated as formally independent, so an identity of such lists holds for
every real `θ_α, θ_β, θ_γ`, in particular on the curve `θ_γ = √2 θ_β` the circuit angles live on.  Mathlib-free, computable.
-/
namespace Su2PlaqCert.Rishon

abbrev Exp3 := Int × Int × Int
abbrev Lp3 := List (Exp3 × K)

def Exp3.lt (x y : Exp3) : Bool :=
  x.1 < y.1 || (x.1 == y.1 && (x.2.1 < y.2.1 || (x.2.1 == y.2.1 && x.2.2 < y.2.2)))

def Exp3.add (x y : Exp3) : Exp3 := (x.1 + y.1, x.2.1 + y.2.1, x.2.2 + y.2.2)

namespace Lp3

/-- Sum of two sorted polynomials (merge); zero coefficients are removed. -/
def add : Lp3 → Lp3 → Lp3
  | [], q => q
  | p, [] => p
  | (e, c) :: p, (e', c') :: q =>
    if e == e' then
      let s := c + c'
      if s.isZero then add p q else (e, s) :: add p q
    else if Exp3.lt e e' then (e, c) :: add p ((e', c') :: q)
    else (e', c') :: add ((e, c) :: p) q
termination_by p q => p.length + q.length

def scale (k : K) (p : Lp3) : Lp3 :=
  if k.isZero then [] else p.map fun t => (t.1, k * t.2)

def shift (e : Exp3) (p : Lp3) : Lp3 := p.map fun t => (Exp3.add t.1 e, t.2)

/-- Multiply by the monomial `k z^e`. -/
def mulMono (e : Exp3) (k : K) (p : Lp3) : Lp3 :=
  if k.isZero then []
  else if k == K.one then p.map fun t => (Exp3.add t.1 e, t.2)
  else p.map fun t => (Exp3.add t.1 e, k * t.2)

def mul (p q : Lp3) : Lp3 := q.foldl (fun acc t => add acc (mulMono t.1 t.2 p)) []

def const (k : K) : Lp3 := if k.isZero then [] else [(((0 : Int), (0 : Int), (0 : Int)), k)]
def mono (e : Exp3) (k : K) : Lp3 := if k.isZero then [] else [(e, k)]

end Lp3
end Su2PlaqCert.Rishon
