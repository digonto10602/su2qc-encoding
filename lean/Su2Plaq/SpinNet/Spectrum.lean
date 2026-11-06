import Su2Plaq.SpinNet.Recoupling

/-!
# Su2Plaq.SpinNet.Spectrum -- the 433 states and an explicit eigenbasis of `H_B` (M3x step W3, prompts/102 section 1)

Mathlib-free, integer arithmetic only.  `H_B = (+)_o K|_o` is block-diagonal in the outer pattern `o` (route B); inside a
block the only non-zero entries are the four-link flips `K[y xor 15, y]`.  `2K[y xor 15, y]` is `twoKlit` (the exported
table, tied to the Racah 6j symbols by `coupling_from_6j` / `k_from_6j_full` in `Recoupling.lean`).

For a bright code `y` with partner `y' = y xor 15`, `H_B (e_y +- e_y') = +- k (e_y +- e_y')`; dark: `H_B e_y = 0`.
One vector per state (`+` if bit 0 of `y` is clear, `-` if set, dark alone) gives 433 pairwise orthogonal eigenvectors,
hence an orthogonal eigenbasis; `eig_blocks` checks `(2 H_B v)_t = 2 lambda v_t` for every vector `v` and every row `t`
of its block (dense inside the block).

* `card_states_exact` : 433 states.  * `blocks_cover` : the non-empty outer blocks cover them.
* `eig_blocks` : every candidate is an eigenvector of `2 H_B`, and its partner is in the block.
* `eig_count`  : 433 eigenvectors.  * `eig_mult` : multiplicities of `2 lambda` in `[-4,-2,-1,0,1,2,4]`: 16/96/16/177/16/96/16.
Prototype: `scratch/planner/lean/SpinNetExact.lean` (section B).
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.SpinNet

theorem card_states_exact : states.length = 433 := by decide

/-- `2 H_B[t, s]` on the states (route B): block-diagonal in the outer pattern, the matching `K` inside -/
def hb2 (t s : Nat × Nat) : Int := if t.2 == s.2 && t.1 == s.1 ^^^ 15 then twoKlit s.1 else 0

/-- the outer blocks: `(o, codes y with (y, o) a state)`, non-empty ones -/
def blocks : List (Nat × List Nat) :=
  (List.range 256).filterMap fun o => let b := blockCodes o; if b.isEmpty then none else some (o, b)

/-- eigenvector candidates of block `o`: `(y, σ, 2λ)` for `e_{(y,o)} + σ e_{(y^^^15,o)}` (σ = 0: `e_{(y,o)}`) -/
def eigsOf (b : List Nat) : List (Nat × Int × Int) :=
  b.filterMap fun y =>
    let k := twoKlit y
    if k == 0 then some (y, 0, 0) else if bitOf y 0 == 0 then some (y, 1, k) else some (y, -1, -k)
def vecAt (e : Nat × Int × Int) (y : Nat) : Int :=
  (if y == e.1 then 1 else 0) + e.2.1 * (if y == e.1 ^^^ 15 then 1 else 0)
def hvAt (o : Nat) (e : Nat × Int × Int) (t : Nat) : Int :=
  hb2 (t, o) (e.1, o) + e.2.1 * hb2 (t, o) (e.1 ^^^ 15, o)

theorem blocks_cover : (blocks.map (fun ob => ob.2.length)).sum = 433 := by decide

/-- in every block, every candidate is an eigenvector of `2 H_B` with eigenvalue `2λ` (dense check on the block),
and the partner is in the block when σ ≠ 0 -/
theorem eig_blocks :
    blocks.all (fun ob => (eigsOf ob.2).all (fun e =>
      (e.2.1 == 0 || ob.2.contains (e.1 ^^^ 15)) &&
      ob.2.all (fun t => hvAt ob.1 e t == e.2.2 * vecAt e t))) = true := by
  decide

theorem eig_count : (blocks.map (fun ob => (eigsOf ob.2).length)).sum = 433 := by decide
/-- multiplicities of `2λ ∈ {-4, -2, -1, 0, 1, 2, 4}` -/
theorem eig_mult :
    [-4, -2, -1, 0, 1, 2, 4].map (fun l =>
      (blocks.map (fun ob => ((eigsOf ob.2).filter (fun e => e.2.2 == l)).length)).sum) =
      [16, 96, 16, 177, 16, 96, 16] := by decide

end Su2Plaq.SpinNet
