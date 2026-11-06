# Ideation: `spinnet` / `step` (track S, M4)

Proposer ideation session, 2026-11-06, clone `~/Projects/su2qc-spinnet`, branch `m3-spin-network`, HEAD `c9ad8d0`.
Inputs used: `compress/specs/spinnet-step.md` and oracle queries only (no seeds, archive or reference circuit).
Scratch scripts behind every number below: `scratch/proposer/ideation_spinnet_*.py`.

## What the oracle shows (the facts all families build on)

Notation: link bits $y=(y_b,y_r,y_t,y_l)$ = data qubits 0..3, corner bits $c_0..c_3$ = data qubits 4..7,
$B=[c=0]$ (bright), $Z_q=(-1)^{q}$.

1. **$U_E$ costs no CX.** $-\arg(U_E)_{kk}/\alpha = \tfrac34\,(y_b+y_r+y_t+y_l)$ exactly (linear fit residual
   $5\times10^{-15}$; corner and outer bits have coefficient 0). So $U_E$ is four single-qubit phases
   `p(-3*alpha/4)` on qubits 0..3: 0 CX, 4 rotations (`ideation_spinnet_probe.py`).
2. **$K$ does not depend on the outer links.** $K = i\log(U_B)/\beta$ in code space has no outer-link dependence
   (route-B gauge already applied). On bright codes $K = X^{\otimes4}_{\rm links}\,\kappa$ with
   $\kappa(0000\leftrightarrow1111)=-2$, $\kappa(0101\leftrightarrow1010)=-\tfrac12$, $\kappa=+1$ for the other six
   pairs; $K=0$ on dark codes. Outer qubits are never needed, not even as controls.
3. **Dimer frame (my own name for it).** `CX(b->t), CX(r->l), CX(b->r)` maps $X^{\otimes4}\to X_b$ (the *pivot* $q_0=y_b$)
   and puts $e=y_b\oplus y_r$ on $q_1$, $u=y_b\oplus y_t$ on $q_2$, $v=y_r\oplus y_l$ on $q_3$. In this frame
   $$\kappa = 1 - A\left(\tfrac94+\tfrac34 Z_e\right),\qquad A=[u=0]\,[v=0],$$
   so $U_B$ on bright codes is one $X$ rotation of the pivot whose angle depends on $(A,e)$ only.
4. **A 4-input OR of the corners cannot be avoided.** All 16 corner patterns are valid with links 1111, and
   1111 is the partner of the bright vacuum 0000. Any phase polynomial without a corner flag therefore needs all 16
   corner characters (a Walsh lower bound of 16 terms; *character* = one parity $\prod_{k\in T}Z_{c_k}$). Without any
   nonlinear flag the minimal support is about 37 terms (LP, `ideation_spinnet_walsh.py`).
5. **Don't-care freedom that matters.** The pair $0101\leftrightarrow1010$ never has a dark partner, so the entry
   $(B=0,A=1,e=1)$ of the pivot angle is free. Dark sectors also allow any phase on the invalid partner code.
6. **Conservation law I kept hitting.** One relative-phase AND into a clean ancilla costs 3 CX to compute and 3 to
   uncompute, and in every split I tried it saves about 6 phase terms (= about 6 CX of parity network). Every
   flag/term split I tried (flags $B,A$; $a_{01},a_{23},A$; $a_{012},c_3,A$; $B,u,v,e$; a midpoint pivot flip) lands
   at **36 ± 1 CX**. Getting below that needs a new structural idea, not a new flag split.

## F1 — Dimer frame, two flags $(B,A)$, 6-term pivot phase polynomial (most promising)

- **Registers.** Data 0..7, plus 3 clean ancillas: $a=[c_0=c_1=c_2=0]$, $B=[c=0]$, $A=[u=v=0]$. 19 qubits.
- **Datapath.** $U_E$ (4 `p` gates) → dimer ladder (3 CX) → $A$=`rccx`$(\bar q_2,\bar q_3)$ (3 CX) →
  $a$=rc3x$(\bar c_0,\bar c_1,\bar c_2)$ built from basis gates (6 CX, 8 T) and $B$=`rccx`$(a,\bar c_3)$ (3 CX) →
  `h(q0)` → closed Gray walk on the pivot over the terms $\{1,B,A,BA,e,Ae\}$
  (toggles $+B,+A,-B,+e,-A,-e$: 6 CX, 6 `rz`) → `h(q0)` → uncompute $B,a,A$ in mirror order → inverse ladder.
  Pivot phase coefficients (units of $\beta$, rotation $e^{-i\beta f X_b}$):
  $f = \tfrac18 + \tfrac14 Z_B + \tfrac38 Z_A - \tfrac34 Z_BZ_A - \tfrac38 Z_e + \tfrac38 Z_AZ_e$, with $Z_B=(-1)^B$.
  Checked exactly with ideal flags: max error $2.8\times10^{-16}$ on the 47 valid data codes at
  $\beta\in\{0.61,0.23,1\}$, no leakage (`ideation_spinnet_f1check6.py`).
- **Cost estimate.** CX $=6+6+18+6=36$, about 35 after a frame-boundary peephole: `CX(e->q0')`, `h`, `CX(b->r)` is a
  1-CX Clifford (checked with `TwoQubitBasisDecomposer`). $T_{\rm fixed}=8+24=32$, rotations $6+4=10$, so
  $T_\varepsilon\approx 32+10\times60\approx630$. All angles are $\beta\cdot k/8$ or $3\alpha/4$, so the circuit is
  Lean-certifiable.
- **Why it should beat a generic circuit.** A generic circuit treats $U_B$ as 8 two-level rotations or as a 16-entry
  multiplexor (16+ CX for the multiplexor plus a 4-control flag). Here the corners enter only through one bit, and the
  class structure (fact 3) collapses the multiplexor to 6 terms, using the free entry of fact 5.
- **Variants on the same datapath (try them, but they are not separate families).** Flags $(a_{01},a_{23},A,e)$: 11 terms,
  12-CX walk, 36 CX, 2 extra ancillas instead of 3. Flags $(a_{012},c_3,A,e)$: 10 terms, 36 CX. Midpoint form
  $R_{1/2}(A,e)\,X^{\bar B}\,R_{1/2}(A,e)\,X^{\bar B}$: 36–38 CX, 8 rotations.
- **Risks.** (i) The relative phases of `rccx`/rc3x cancel only if $a,B,A$ and the corners are used purely as controls
  between compute and mirrored uncompute. This holds for the plan (the pivot is never a control of a flag), but a
  merge that moves a pivot toggle across an uncompute breaks it. (ii) rc3x is not a macro, so it has to be emitted
  as `cx/h/t/tdg` (check that its T-count is booked as 8). (iii) Little slack: one extra CX at the frame boundaries
  turns 35 into 37.

## F2 — Single-flag corner polynomial (only $A$; the corners enter as raw parities)

- **Registers.** Data plus one ancilla $A$ (17 qubits). No $B$ tree.
- **Datapath.** Dimer ladder, $A$ flag, `h(q0)`, then a phase polynomial on the pivot over $(c_0..c_3,A,e)$ with exactly
  16 terms, one per corner subset $T$, each $\pm\beta/8$. MILP enumeration found **624** minimal solutions
  (`ideation_spinnet_enum.py`), so 16 terms is optimal by fact 4.
- **Cost estimate.** Best pure pivot walk over the 624 solutions × 2688 Hamiltonian cycles of the 4-cube is 26 CX;
  qiskit GraySynth gives 28. Total $6+6+26=38$ (about 37 with the peephole), so it does **not** beat F1 yet.
  It wins only if the parity network gets to $\le 22$ CX: non-minimal term sets (17–20 terms) with a shorter walk,
  or CX between control qubits to build corner parities. No minimal solution has its $(A,e)$-part affine in $T$
  (checked, `ideation_spinnet_affine.py`), so a plain 16-step Gray code plus 2 relabelling CX is impossible.
  Rotations $16+4=20$ ($T_\varepsilon\approx1200$), $T_{\rm fixed}=8$, all angles $\pm\beta/8$.
- **Why it could win.** It removes the 18-CX $B$ compute/uncompute entirely. It is the fewest-qubit design and sits in
  a different MAP-Elites cell (higher T, lower fixed T).
- **Risks.** The network synthesis is the whole game; the obvious syntheses give 26–28 CX. Higher T than F1.

## F3 — Numerical don't-care synthesis of the corner-controlled block

- **Datapath.** Keep $U_E$ and the dimer ladder fixed. Replace "flags + network" by a fixed CX skeleton (search over
  skeletons with 20–30 CX on data qubits 0..7, optionally one ancilla) with free single-qubit gates. Optimise only the
  47-column isometry on valid codes (dark columns → identity, bright pairs → $e^{-i\beta\kappa X_b}$), at emission
  time from the oracle, then Newton-polish to $<10^{-12}$. Re-solve the angles at each $(\alpha,\beta)$ pair with the
  same skeleton by continuation.
- **Why it could win.** It is the only family that is not bound by the flag/term conservation law of fact 6: the
  optimiser may find nonlinear corner logic shared with the pivot rotation.
- **Risks.** Generic `u3` angles make about 3 rotations per single-qubit gate, so $T_\varepsilon\sim10^4$ (fine for a
  CX-first key, bad for cells). Emission-time optimisation must fit the 300 s wall. Angles are not $k\beta/64$, so it
  is not Lean-certifiable. The skeleton must stay valid at all three angle pairs. The success probability below 34 CX
  is low to moderate.

## F4 — In-place dark re-encoding (conditional routing into invalid codes)

- **Datapath.** A reversible map $V$ on the 8 data qubits, injective on the 47 valid codes and fixing the bright codes.
  $V$ sends every dark code to a code with a marker qubit (for example $c_3$) equal to 1, using the 209 invalid data
  patterns as room. The 7 dark codes in row 1111 with $c_3=0$ must move to link patterns that are invalid for their
  corners, because only 8 marker=1 slots exist in that row. Then the F1 network uses $c_3$ instead of $B$, followed by
  $V^\dagger$.
- **Why it could win.** It uses no $B$ ancilla and no intermediate ancilla (17 qubits with $A$, or 16 if $A$ is also
  stored in a corner, which is clean on bright codes). If $V$ can reuse the link bits as Toffoli targets, it might
  share gates with the ladder.
- **Risks.** $V$ must realise a degree-4 corner function (fact 4), so it needs at least about 3 AND-type gates each way,
  which is at least about 18 CX, the same as the $B$ tree. In practice it is a qubit-key improvement (4th key), not a
  CX one. $V$ must not touch the pivot, or the relative phases stop cancelling.

## F5 — T-lean phasing on top of F1 (MAP-Elites cell filler)

- **Datapath.** F1 unchanged, plus weighted-sum phasing: compute $\sum_l y_l$ (the $U_E$ phases are four equal angles)
  and the three $\pm\tfrac38\beta$ pivot terms into small counter registers with relative-phase adders, then rotate the
  counter bits (angles $2^j\theta$).
- **Effect.** Rotations go from 10 to about 7, so $T_\varepsilon$ drops by about 150–200, at a cost of about 10–20 more CX.
- **Risks.** It does not improve the lexicographic key (CX first). It is only worth doing for the low-T cells after
  F1 exists.

## Recommendation

Build F1 first: expected about 35–36 CX, 10 rotations, 19 qubits, exact closed-form angles. F2 is the cheap
second try if a parity network of at most 22 CX can be found. F3 is the only real attempt to break the 36-CX plateau.
