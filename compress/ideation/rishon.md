# Ideation: `rishon` / `step` (proposer, ideation mode)

Spec: `compress/specs/rishon-step.md`, structure facts: `compress/specs/rishon-structure.json`. No seeds or archive entries were read.
The target was studied with the operators behind the oracle (`su2plaq.rishon.operators`, scratch only; programs must use
`su2plaq.compress.spec.get_encoding("rishon").bright_pairs()`). Scripts: `scratch/proposer/rishon_study1.py`, `rishon_study2.py`,
`rishon_frame_check.py`, `rishon_frame_labels.py`, `rishon_tau_fit.py`, `rishon_closed_and_dark.py`, `rishon_closed_flag.py`,
`rishon_flag_affine.py` (run with `PYTHONPATH=src`, each takes a few seconds; the later ones need the `.npy` files written by
`rishon_frame_check.py` and `rishon_closed_and_dark.py`).

## 0. Verified structure of the target (shared by all families)

Labels used below. These are my own names, not standard terms:
- **end**: the two modes (colour 1, colour 2) of one link at one end. The **e-bit** of an end is its colour-1 mode, i.e. qubit
  L1 = $4l$ or R1 = $4l+2$.
- **corner** $c$: the two inner ends that meet at a plaquette vertex. Read off the index contraction in `operators._W`:
  $c_0=(b.L,\,l.L)$, $c_1=(b.R,\,r.L)$, $c_2=(r.R,\,t.R)$, $c_3=(t.L,\,l.R)$. Each corner owns 4 data qubits, and the 4 corners partition the 16.
- **Q-flag** $g_l=L1\oplus L2$ of link $l$. On valid codes $g_l=1$ exactly for a quartet (Q) link. Note that $R1\oplus R2=g_l$ as well.
- **height** $h_l\in\{0,1,2\}$ (A, Q, B on b, r; reversed on t, l; the `heights` fact). A corner is **different** if its two links have
  different Q-flags ($\delta_c=g_X\oplus g_Y=1$) and **equal** otherwise.
- **lower / upper member** of a bright pair: the member with smaller / larger heights. **Sector** = the heights of the lower member.

Facts, each checked numerically (script in brackets):
1. **Corner picture** [`rishon_study1.py`]. $W$ has 256 nonzero entries, all $\pm1$. It raises all four heights by one and conserves every corner charge
   $N_c$ (the number of fermions in the corner's 4 modes). Each corner has exactly 8 local transitions:
   - $N_c\in\{1,3\}$: one fermion (or hole) moves between the two ends and keeps its colour;
   - $N_c=2$: empty+full $\to$ singlet $\to$ full+empty, with factor $\sqrt2$ per step; the triplets are dark at the corner;
   - $N_c\in\{0,4\}$: frozen.

   By hand: $W=\bigotimes_c K_c$, with $K_c$ acting on the 4 qubits of corner $c$. Each corner contributes a singular value of 1 (different corner, rank 2)
   or $\sqrt2$ (equal corner, rank 1). This explains the $\kappa$ multiset: 16 sectors $h\in\{0,1\}^4$, giving
   2 sectors ($h=0101,1010$, $n_d=4$ different corners) $\times16$ pairs with $\kappa=1$; 12 sectors ($n_d=2$) $\times4$ pairs with $\kappa=2$;
   and the chain $h=0000\to1111\to2222$, which is the closed 3×3 block with $\kappa=4\sqrt2$. Census output: 16+16 / 12×4 / 1.
   The sign factorisation of $K_c$ was **not** machine-checked.
2. **Partner map in link variables** [`rishon_study2.py`, 0 violations over all 80 non-closed pairs]. Going from one member to the other:
   - every $g_l$ flips;
   - at a **different** corner the two e-bits are **swapped**. The Q end's colour moves to the other link. The non-Q end bit equals $[N_c=3]$ and does not change.
   - at an **equal** corner, the non-Q member has e-bits $(\bar b, b)$ ($b=1$ iff the corner is a singlet in the lower member).
     The Q member has the singlet, with relative sign $a_{01}a_{10}<0$ in all 160 occurrences.

   For the 32 $\kappa=1$ pairs, "flip $g$ + swap e-bits at all corners" maps $u$ to $v$ exactly, with coupling sign $+1$ for all 32.
3. **A CX/CCX frame sends 80 of the 81 pairs to computational basis states** [`rishon_frame_check.py`]. Frame $D$:
   1. Link prep: per link, CX(L1→L2), CX(R1→R2), CX(L2→R2). After this, L2 $=g_l$ and R2 $=0$ on **all 1296** valid images.
   2. Per corner, with e-bits $(e_1,e_2)$ of links $(X,Y)$ = c0 (q0,q12; b,l), c1 (q2,q4; b,r), c2 (q6,q10; r,t), c3 (q8,q14; t,l):
      CX($e_1\to e_2$), then CCX($g_X,e_2\to e_1$).
   3. Per corner, a controlled H on $e_1$ with controls $g_X\wedge g_Y$. It only fires at an equal corner whose two links are Q.
   4. GHZ fold: CX($g_b\to g_r,g_t,g_l$), with $F:=g_b$ (q1) and $r=(r_r,r_t,r_l)$ on (q5, q9, q13).

   Result: both members of every non-closed pair become single basis states. The partner map flips $F$ (44 pairs), or $F$ plus the $e_1$ of
   1 or 2 equal corners (36 pairs). I write this as $P=X_F\prod_c X_{e_{1,c}}^{\tau_c}$, where $\tau_c\neq0$ only at equal corners.
   The bright labels are all distinct (80).
4. **Coupling sign depends only on $r$** [`rishon_frame_labels.py`]. In the frame,
   $H_B=-\kappa\,\varepsilon(r)\,(|x_u\rangle\langle x_v|+{\rm h.c.})$ with
   $\varepsilon(r)=(-1)^{1+r_r+r_t+r_rr_t+r_tr_l}$. This is a GF(2) quadratic, and no linear fit exists. $\kappa=1$ ($r=101$) has $\varepsilon=+1$.
5. **$\tau_c$ is flip-invariant** [`rishon_tau_fit.py`]. It is a function of $r$ and of the two $e_1$ bits at the different corners.
   Those two bits are the corner charges $[N_c=3]$ and are always complementary in a bright pair. In effect $\tau_c$ is the
   $[N=3]$ bit of a neighbouring different corner, possibly negated depending on $r$ (tables printed by the script).
6. **Closed pair** [`rishon_closed_flag.py`]. After the frame, $u=(|a\rangle+|b\rangle)/\sqrt2$ where $a,b$ differ only in the four $e_1$,
   and $v=-|c\rangle$ (with $F=1$). Add an e1 fan-out CX($e_{1,c0}\to e_{1,c1},e_{1,c2},e_{1,c3}$) and an H on $e_{1,c0}$ controlled by $[r=000]\wedge\bar F$.
   Then $u\mapsto|a\rangle$ and $v\mapsto-|c\rangle$, and the 80 other pairs stay single basis states. The closed partner map is
   $X_F X_{e_1}^{\otimes4}$, which is just $\tau=1111$.
   The fan-out changes the $\tau$ / flag tables of the other sectors. Re-derive them with the scripts.
7. **Flag structure** [`rishon_flag_affine.py`]. For each $r$, the bright images are an affine subspace in $(F,e_1,e_2)$, intersected with the valid image span.
   This holds exactly for $r\in\{110,101,011\}$. The other four $n_d=2$ patterns need one extra 2-literal clause (e.g. $(\bar F\vee e_{1,c0})$).
   For $\kappa=1$ the checks are $e_{1,c}\oplus e_{1,c+1}=1$ (the corner charges alternate), with $e_2$ free (the 4 colour labels).
   Isolating the closed pair inside $r=000$ needs 8 parity checks.
8. **Free workspace.** The four R2 qubits (q3, q7, q11, q15) are $|0\rangle$ on every valid image after link prep.
   Invalid codes are don't-care, so they act as 4 clean ancillas. Many families need **no** `alloc`, which keeps the qubit count at 48.
9. **$U_E$ costs no CX.** After link prep, $U_E=\prod_l P(-\tfrac34\alpha)$ on the four L2 qubits (4 rotations, Lean-friendly $d=4$).
   This uses fact `ue_exact_all_codes` and $\#Q=\sum_l g_l$. Insert it after link prep and before the rest of $D$.
   This is exact because link prep is a permutation.

Prune-cap check for the families below: CCX/CCZ (free), C²H as CCZ conjugated by fixed $R_y(\pm\pi/4)$ (2 h each), and up to about 40 rccx
add up to about 150 branching gates. That is well under the 909 cap. Exact `ccx`/`ccz` should be used wherever a control or target flips under the pair map.
An rccx's relative phase cancels only if all its qubits are flip-invariant between its compute and uncompute.

---

## F1 — Link-flag GHZ frame, Pauli-support rotation on one flip qubit (most promising)

**Datapath** (registers as in fact 3; the flip qubit is $F=g_b$; the labels are $r$, $e_1$, $e_2$; the R2 qubits are scratch):
1. Link prep (12 CX), then $U_E$ as 4 phase gates on L2.
2. Corner canonicaliser: 4× [CX + CCX] (28 CX), then 4× C²H($g_X,g_Y;e_1$) = CCZ between $R_y(\pm\pi/4)$ (24 CX).
   Different corners end with $(e_1,e_2)=([N_c{=}3],\,\text{colour}\oplus[N_c{=}3])$. Equal corners end with $e_2=1$ when bright.
3. GHZ fold (3 CX). Closed gadget (fact 6): 3 CX fan-out, plus a CH on $e_{1,c0}$ controlled by $(\bar r_r,\bar r_t,\bar r_l,\bar F)$
   (rccx ladder in/out inside $D$, about 13 CX).
4. Rotation stage, using flip-invariant ancillas (all rccx are allowed here because every input is invariant on bright states):
   - $\tau_c$ bits (fact 5, about 4 rccx);
   - a sign bit $\sigma=q(r)\oplus\sum_c\tau_c e_{1,c}$, evaluated after $H$ on the four $e_1$. This turns $X^{\tau}$ into $Z^{\tau}$, so $P$ becomes the phase
     $(-1)^{\sum\tau_c e_{1,c}}X_F$. Compute the flags **before** these $H$ gates (see below).
   - the bright flag $B$ (fact 7: per corner "$\delta_c\vee e_{2,c}$", the charge-alternation parities, and the extra clause);
   - two class bits from $r$ ($[r=101]$, $[r=000]$).

   Then apply $e^{i\beta\kappa X_F}$ as a 2-control uniformly controlled $R_x$ on $F$. The 4 angles are $0,\beta,2\beta,4\sqrt2\beta$
   (all Lean-certifiable), and $F$ is conjugated by CZ($\sigma$, F). Uncompute and apply $D^\dagger$.

   Flags may read $F$ and $e_1$ (e.g. $F\oplus e_{1,c0}\oplus e_{1,c3}$). Their *values* are the same on both members of a bright pair.
   Compute such parities with CX into the free R2 qubits.

**Cost (estimate):** $D$ ≈ 12+28+24+3+16 ≈ 83 CX per side, so ≈ 166 for $D$ and $D^\dagger$. Rotation stage ≈ 60 (flag) + 24 ($\tau$) + 36 ($\sigma$) + 6 ≈ 130.
Total **≈ 250–300 CX**, with an obvious target of about 200 after merging (see risks).
T: 8 synthesised rotations (4 $U_E$ + 4 UCR) ≈ 480, plus about 16 CCX/CCZ (112), plus about 40 rccx (160). Total **≈ 750 T**.
Qubits 48 (+0–2).

**Why it beats a generic circuit.** All 81 rotations become one multiplexed single-qubit rotation. Facts 3 and 6 show the frame is exact on every pair:
80 pairs map to basis states, and the closed pair does after a 16-CX gadget. Only 8 rotations are synthesised.

**Main risks / first things to try.**
(a) The flag. Push its literals into corner-local checks stored in the 4 free R2 qubits, then use one AND of about 5 bits. Search for this with don't-cares on the 64,240 invalid images.
(b) The 8 corner Toffolis. Look for a merged per-corner gadget with one CCX-class gate. On dark images the frame may do anything unitary, so the C²H may act arbitrarily on the triplet states $T_\pm$ ($e_2=0$).
(c) Recompute the $\tau$ tables after the closed fan-out.
Build order: $\kappa=1$ only (no C²H, no $\tau$, $\varepsilon=+1$), then $\kappa=2$, then closed. Run `--full` at each stage.

## F2 — Explicit direction qubit and controlled lowering map (height-shift frame)

**Datapath.** Compute the true direction $f=[\text{member is upper}]$ into a free R2 qubit. On bright states, $f$ is the height-2 indicator of any non-Q link
(the $\bar L1$ of b, r; the L1 of t, l), and it also equals $g_{\rm recv(c)}\oplus[N_c{=}3]$ at any different corner.
A priority select over 3 links is valid because every non-closed bright member has at least one non-Q link (about 3 exact Toffolis).
Then apply $g_l\mathrel{\oplus}=f$ (4 CX), which leaves the **sector heights explicit and flip-invariant**. Then apply an $f$-controlled corner-local lowering map $\Pi_c$:
- different corner: a Fredkin on the e-bits;
- equal corner: top$\to$singlet and singlet$\to$bottom. This is a fixed Givens on span$\{|01\rangle,|10\rangle\}$ selected by $h_X$. Note it is **not** needed on states that are never upper members.

After this, both members are the lower member $|u\rangle$, and only $f$ differs. Flags read the explicit sector $h$ and a Bell test at the corners
that are singlets in the lower member. The rotation is $R_x$ on $f$. There is no $\tau$ and no GHZ fold. The closed chain needs the F1-style gadget.

**Cost (estimate):** $f$ ≈ 18–24 CX, $\Pi$ ≈ 4×8 (Fredkins) + equal-corner Givens with 2–3 controls (≈ 4×12). That is ≈ 100–110 per side,
so **≈ 280–360 CX** in total. T is similar to F1 plus more CCX.

**Why.** The rotation stage is simpler: flags are a direct function of $(h,\text{Bell bits})$, and there are no sign or $\tau$ tables.

**Risk.** The $h_X$- and $\bar\delta_c$-selected equal-corner map is triply controlled. Unitarity forces the singlet-sign convention: work it out on
`oracle --pairs` first (a naive $M$ with $MS=-|01\rangle$ is not unitary). F2 only wins if the equal-corner map gets down to about 6 CX.

## F3 — Controlled partner involution (Hadamard-test identity, no frame)

**Datapath.** Choose an involution $\Pi$ on the bright space with $\Pi u_p=v_p$:
- $X$ on the four $g_l$;
- SWAP of the e-bits at different corners;
- at equal corners, the $b_c$-selected exchange $(\bar b,b)\leftrightarrow$ singlet.

Use $e^{i\theta Z_a\Pi}=H_a\,c\text{-}\Pi\,e^{i\theta X_a}\,c\text{-}\Pi\,H_a$ with one clean ancilla $a$ (a free R2 qubit). The angle multiplexing reads $\Pi$-invariant flags.
Because $a$ starts in $|0\rangle$, the result is $e^{i\theta\Pi}$ on the data, and $a$ returns to $|0\rangle$ exactly.

**Cost (estimate):** $c$-$\Pi$ needs 4 CX on $g$, plus a doubly controlled swap per different corner (≈14 CX each), plus a triply controlled singlet map per equal corner.
That is ≈ 100–120 CX per $c$-$\Pi$, so **≈ 250–350 CX** in total with flags.

**Why.** It is conceptually the shortest route: there is no basis change, and $\Pi$ is corner-local.

**Risk.** $\Pi$ is an involution only with $b_c$ as a control. This is the same sector-information problem as F1's $\tau_c$, but here it is paid twice per corner.
Use it as a cross-check of F1's $\tau$ tables rather than as the main line.

## F4 — Exact spectral interpolation on the block encoding $W=\bigotimes_c K_c$ (structurally different, low priority)

**Datapath.** The spectrum of $H_B^{\rm in}$ is $\{0,\pm1,\pm2,\pm4\sqrt2\}$ (7 points; 990 + 144 zero modes). A degree-6 polynomial can interpolate
$e^{-i\beta\lambda}$ exactly on these points, and dark states and classes are then handled with **no flags**.
Block-encode $W/(4\sqrt2)$-like operators from the corner factorisation (fact 1): one dilation ancilla per corner for the non-unitary $K_c$ (singular values $1,\sqrt2$).
Use QSVT-style phases computed at emission time.

**Cost (estimate):** 6–8 queries × (4 controlled corner dilations ≈ 30–50 CX) gives **≈ 200–400 CX**, and about 6–8 extra rotations.

**Why.** No dark-state bookkeeping, no closed-sector special case.

**Risk.** A bounded polynomial with $|p|\le1$ on $[-1,1]$ through 7 unimodular points may need a higher degree. The phases depend on $\beta$, which is fine.
The skeleton is identical across the three angle pairs only if the degree is fixed. The QSVT phases are not Lean-certifiable (status `n_a`).

## F5 — Sector-batched Givens with affine-support Clifford maps (safe fallback)

**Datapath.** There are 15 sectors (14 non-closed plus the closed chain; facts 1 and 7). For each sector, a Clifford map (CX + H on the affine directions of the supports, as in fact `pair_supports`)
sends all of that sector's pairs to $|0,\lambda\rangle,|1,\lambda\rangle$ on a common qubit. Then apply one multi-controlled $R_x$, whose controls are the sector
pattern ($r$ plus charge bits, about 6–8 controls), and undo the map.

**Cost (estimate):** about 15 × (≈ 25 Clifford CX + ≈ 20 CX ladder) ≈ **600–700 CX**. Rotations: about 15 × 2.
Uses mostly free mcx/ccx in the prune count, with about 30 rccx and about 30 h.

**Why.** It is mechanical, every step can be checked per sector with `--trial` on that sector's codes, and it is likely already far below the generic reference.

**Risk.** T-count (about 30 rotations, ≈ 1800 T). It is only useful as an early valid entry or as a sector-by-sector debugging scaffold for F1.
