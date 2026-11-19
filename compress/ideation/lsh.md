# Ideation: `lsh` / `step` (prompts/401 step 8.6, §1.7)

Date 2026-11-19, git `aaa802e`, brief `compress/briefs/lsh/ideation.md`, spec `compress/specs/lsh-step.md` +
`compress/specs/lsh-structure.json`. Spec-only session (no archive, no seeds). Scratch scripts:
`scratch/proposer/lsh-ideation/*.py` (run with `PYTHONPATH=src python scratch/proposer/lsh-ideation/<file>.py`).

Reference points: best known 71 CX (spin-network core between the per-site transcoder `cx, cx, rccx` and its inverse;
transcoder pair = 40 CX = 16 linear CX + 4 `rccx` pairs); general circuit 94 CX, 598 T at $\varepsilon=10^{-6}$.

## Facts checked in scratch (all on the 47 inner codes; numerical, not Lean)

Notation per site $c$: $f_c=\ell_{pn}\oplus\ell_{nv}$ (flux of the next inner link), $w_c=\ell_{nv}\oplus\ell_{vp}$ (virtual
flux mod 2), $p=\bigoplus_c \ell_{nv}(c)$, $D$ = number of dark sites (site code 110).

1. **Bright sector = four link-flux bits.** A bright site is the one-hot code of $(f_{c-1},f_c)$: 00→000, 11→001,
   01→010, 10→100. The move complements all four $f_c$; $w_c=f_{c-1}\oplus f_c$ is invariant (`checks.py`).
2. **Move = (flip all four $f_c$) × $\prod_c \mathrm{SWAP}(\ell_{nv},\ell_{vp})$**, a fixed operator: SWAP is the
   identity on every $w=0$ site (000, 001, 110), so no state-dependent control is needed in the $f$ frame (`checks.py`).
3. **Class bit is linear in raw bits.** On bright codes $k$ is a function of $(p, w_0)$ only: $p=1\Rightarrow k=+1$;
   $p=0,w_0=0\Rightarrow k=-2$; $p=0,w_0=1\Rightarrow k=-1/2$ (`checks.py`; consistent with the Lean y-parity fact).
4. **Dark count identity:** $2D = 2\,\#\ell_{nv} - \#w$ on all 47 codes, so $D \bmod 2 = p\oplus[\#w=2]$ (`checks.py`).
5. **Nonlinearity budget.** The bright flag $b=[D=0]$ has GF(2) degree exactly 4 on the physical codes even with all
   don't-cares, so it needs at least 3 AND gates; it is not a product of affine functions (dark codes lie in the affine
   span of the bright codes) (`degree.py`, `affine.py`). With $D$-parity handled elsewhere, the "even-$D$ dark" flag has
   degree 3 (≥ 2 ANDs); no 1-AND formula exists, and no 2-AND formula of the form $(AB\oplus C)F\oplus L$ with $A,B,F$
   supported on ≤ 2 raw bits exists (`eflag.py`, `eflag2.py`, `e2and.py`).
6. **Cleaning needs only three products.** Under the move, $\Delta\ell_{nv}(c)=f_0\,w_c$ in the frame where $f_0$ is
   the moving bit; because $\sum_c w_c\equiv 0$, three Toffolis $f_0w_1, f_0w_2, f_0w_3$ clean all four $\ell_{nv}$ and
   the fourth coordinate ($p$) is invariant (`f0frame.py`: move = X on one qubit for all 16 bright codes, frame = 14 CX +
   3 Toffoli per side).
7. **Walsh-only (multiplexer) gating is too expensive.** With no AND flags the gated rotation needs ≥ 20 Walsh terms in
   every frame tried (spin-network frame ≈ 23, swap-diagonal frame ≈ 36–40, three-product frame ≈ 16–20; HiGHS MILP,
   time-limited, so these are upper bounds on the optimum but the LP relaxations show no sparse solution) (`mux_sn.py`,
   `mux_s.py`, `f0mux.py`, `f0mux2.py`).

Takeaway: the per-site `rccx` of the transcoder is efficient because one AND both cleans $\ell_{nv}$ and yields the dark
flag $y_c$. Natives must either reuse ANDs in the same way or cut the AND count below the ~7 relative-phase ANDs per side
that "recode + NOR($y$)" needs.

## Families (most promising first)

### 1. Recode–gate fusion (kind: transcoding)
- **Idea.** Keep the per-site `cx(nv→pn)`, `cx(nv→vp)`, `rccx` recoding (AND-optimal per site, fact above), but fuse the
  core into it: (a) take the class bit from the raw $\ell_{nv}$ parity (fact 3) instead of from the flux pattern, folded into
  the $\ell_{vp}$ slot of site 0 (its $w_0$ is Gauss-redundant, $w_0=g_3$): replace `cx(nv0→vp0)` by `cx` from all four
  $\ell_{nv}$, giving $w_0\oplus p$ (invariant); site 0's Toffoli then uses controls $(\lnot f_3, f_0)$ instead of
  $(w_0,f_0)$ ($\ell_{nv}(0)\oplus\bar f_3f_0$ is 0 on bright, 1 on a dark site 0); (b) build $b=\mathrm{NOR}(y)$ as an all-`rccx` chain
  (it only feeds controls, so no exact `ccx`); (c) one rotation block on the collapsed moving bit with 4 parities
  ($Z_q$, $Z_qZ_b$, $Z_qZ_p$, …) and $p$ / $w_0$ as the only class controls; (d) order collapse CX next to the recoding CX so
  peephole cancellation can act.
- **Why it might win.** Removes the class logic of the core (≈ 1 AND = 6 CX) for 6 CX of parity folding (3 extra CX per
  side), so the gain comes from (b)–(d): any exact Toffoli left in the core (−3 CX each) and cancelled CX pairs.
- **Main risk.** The 31-CX core may already do (b)–(d); the net gain may be 0–4 CX.
- **Rough cost.** 67–71 CX; rotations 4 ($U_E$) + 4 ($U_B$). Safest family, small gain.

### 2. Swap-diagonal frame (kind: native)
- **Idea.** Per site `cx(nv→pn)` ($f_c$), `cx(nv→vp)` ($w_c$), `ch(vp→nv)`; collapse $f_1..f_3$ onto $f_0$; `h` on $f_0$;
  accumulate the four $\ell_{nv}$ into $f_0$. Fact 2 makes the move a fixed operator, and in this frame $U_B$ is **exactly
  diagonal** on all 47 codes (checked with `try_ch.py`). The circuit becomes: frame → one diagonal phase block → inverse
  frame. Inside a diagonal sandwich every AND may be `rccx` and gates commute freely. Dark flags of $w=0$ sites are the
  untouched $\ell_{nv}$ bits (still in the computational basis). Gating: the raw parity $p$ (linear) kills odd-$D$ dark
  states through the class multiplexer; a flag $E=[\#\ell_{nv}\ge 2]$ kills even $D$; the gated rotation is then a
  multiplexer over $(s,w_0,p,E)$ with exactly 8 Walsh terms ($s=[w_0=w_1=w_2]$, 1 AND; MILP optimum, `n1mux.py`).
- **Why it might win.** Never holds the spin-network code (no $y$ flags); cleaning costs 1 CX per site (`ch`) instead of
  3 (`rccx`); frame + moving parity = 38 CX against 46 for recoder + collapse; class is linear.
- **Main risk.** $E$ needs ≥ 2 ANDs (fact 5), $p$ costs 8 CX unless it can be folded into the moving-parity register;
  `ch` adds 2 T each.
- **Rough cost.** 38 + 8 ($p$) + 6 ($s$) + 12–18 ($E$) + 8 (multiplexer) ≈ 72–78 CX; it beats 71 only if $E$ and $s$ share
  ANDs or $p$ is free. Rotations 4 + 8, T ≈ 12·60 + fixed.

### 3. Minimal-AND synthesis (kind: native)
- **Idea.** Treat the whole job as a search for a reversible CX+Toffoli frame on the raw 12 bits with as few ANDs as
  possible that (i) puts the move on one qubit for the 16 bright codes and (ii) exposes $b$ and the class as functions of
  move-invariant bits; unphysical codes are the free "failure budget". Search space: XOR-AND graphs with 5–6 ANDs on the
  47 points (SAT, or the GF(2) linear-algebra screen of `e2and.py` extended to all affine inputs). Lower bounds from the
  facts: cleaning ≥ 3 products (fact 6), $b$ ≥ 3 ANDs (fact 5); the known design uses about 7 per side.
- **Why it might win.** Each AND removed saves ≈ 6 CX (an `rccx` pair); 5 ANDs instead of 7 would land near 55–60 CX.
- **Main risk.** The bounds may be loose (the products that clean are $f_0w_c$, the ones that flag darkness are
  $\ell_{nv}\ell_{vp}$; sharing them failed in my quick checks: in the three-product frame $b$ still has degree 4,
  `f0deg.py`). The search may be too large without a SAT solver.
- **Rough cost.** 55–65 CX if a 5-AND frame exists, otherwise ≈ 70.

### 4. Three-product cleaning with free class bit (kind: native)
- **Idea.** Frame `cx(nv→pn)`, `cx(nv→vp)`, fold $\ell_{nv}(1..3)$ into site 0's $\ell_{nv}$ (it becomes $p$, invariant and
  equal to $[k=+1]$ on bright), three Toffolis $(f_0,w_c\to\ell_{nv}(c))$ for $c=1,2,3$, collapse. Move = X on $f_0$
  (verified, `f0frame.py`). Dark flags: $y_1=\ell'_{nv}(1)\oplus w_1$ (linear), $y_2=\ell'_{nv}(2)\oplus\bar w_1w_2$,
  $y_3=\ell'_{nv}(3)\oplus w_3w_0$, $y_0$ from $p$ and $D$-parity; then gate as in family 1.
- **Why it might win.** One AND fewer for cleaning and the class bit for free; the Toffolis can be relative-phase if the
  phase is real: a relative phase $(-1)^{f_0\phi(\text{inv})}$ conjugating $R_X(\theta)$ on $f_0$ only flips the sign of
  $\theta$, which the multiplexer absorbs.
- **Main risk.** The two extra quadratic $w$-terms for $y_2,y_3$ give back the saved AND; Qiskit's `rccx` has $\pm i$ phases
  on the both-controls-set states, which do not cancel when an odd number of $w_1,w_2,w_3$ are 1 — use a real-phase
  (Margolus) Toffoli from `h`/`t`/`cx` (3 CX, 4 T) or exact `ccx` on one site.
- **Rough cost.** 46 (frame, same as recoder + collapse) + 12 ($y_2,y_3$) + 18 (NOR) + 6 ≈ 76–82 CX; competitive only in
  combination with family 3.

### 5. Dead-syndrome multiplexer (kind: transcoding)
- **Idea.** After recoding, the four $w$ bits are Gauss-redundant with the collapsed fluxes; XOR each $y_c$ into its $w$
  slot so every dark code lands on a control pattern no bright code uses, drop the NOR tree, and implement the gated
  rotation as a Walsh-sparse uniformly controlled $R_X$ with don't-cares (Gray-code order, 1 CX per term). Hybrid: one
  partial flag (e.g. $y_0\lor y_2$, 1 AND) plus a smaller multiplexer.
- **Why it might win.** Replaces the NOR tree (≈ 18 CX for 3 `rccx` pairs) by ≈ 16–23 CX of multiplexer; the hybrid may
  land a few CX below.
- **Main risk.** Fact 7: the minimum Walsh support is ≈ 20 terms, so CX is at best level and T roughly triples
  (≈ 20 rotations).
- **Rough cost.** 64–74 CX, T 1200–1500.

## Notes for proposers
- $U_E$ is 4 angle-linear `p(-3α/4)` on the $f_c$ qubits once `cx(nv→pn)` has run (8 rotations and 0 CX on raw `pn`, `nv`
  otherwise).
- Outer qubits give $w_c=\ell_{2v}\oplus\ell_{v1}$ and dark$_c=\ell_{2v}\land\ell_{v1}$ as read-only invariant controls;
  this saves no AND, but flags computed from them commute with every data gate.
- Relative-phase rule used above: any diagonal phase left by a Toffoli whose dependence on the moving bit is
  $(-1)^{f_0\phi}$ with invariant $\phi$ turns $R_X(\theta)$ into $R_X(\pm\theta)$; absorb it in the multiplexer angles.
