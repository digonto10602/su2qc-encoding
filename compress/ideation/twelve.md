# Ideation: `twelve` / `step` (proposer, ideation mode)

Spec: `compress/specs/twelve-step.md`. No seeds or archive entries were read. The oracle was used to study the target.
The analysis scripts are in `scratch/proposer/` (`twelve_study1..4.py`, `wcorner.py`, `inner_only_check.py`, `gadget_check.py`).

## 0. Verified structure of the target (shared by all families)

Terms used below (my own labels):
- **corner**: one of the 4 plaquette vertices.
- **leg**: the label qubit $q_m$ or $q_{m'}$ of an inner link at one of its two ends. Each corner holds exactly two inner legs.
- **same / diff corner**: the two inner links at the corner have equal / different $j$. Gauss's law gives
  $j_A\oplus j_B = e_A\oplus e_B$, where $e$ is the outer $q_j$ bit. This bit is called the corner type
  $t_c$. It stays the same when all $j$ are flipped together.
- **bright pair / dark state**: a 2-dimensional block / a 1-dimensional block of $H_B$.

| corner | legs (start/end) | outer links | inner "bond" (both legs active) | diff relation (label moves leg A to leg B) |
|---|---|---|---|---|
| c0 (0,0) | $b_m$=q1, $l_m$=q10 (start, start) | o0, o1 | $(\lvert10\rangle-\lvert01\rangle)/\sqrt2$ (odd parity) | copy |
| c1 (1,0) | $b_{m'}$=q0, $r_m$=q4 (end, start) | o2, o3 | $(\lvert00\rangle+\lvert11\rangle)/\sqrt2$ (even parity) | NOT, plus a sign on the end leg |
| c2 (1,1) | $r_{m'}$=q3, $t_{m'}$=q6 (end, end) | o4, o5 | odd | copy |
| c3 (0,1) | $t_m$=q7, $l_{m'}$=q9 (start, end) | o6, o7 | even | NOT, plus a sign on the end leg |

Facts. Each was checked numerically; the script is named in brackets.
1. **Block structure** [`twelve_study1.py`, `twelve_study3.py`]. The 433 physical states form **128 bright pairs + 177 dark states**.
   Each pair is a state and its partner with **all four inner $j$ flipped** (pattern complement); the outer register is unchanged.
   The coupling is $\pm 2\cdot 2^{-n_1/2}$, where $n_1\in\{0,2,4\}$ is the number of diff corners.
   Pairs per class: 16 ($n_1=0$, $\pm2$), 96 ($n_1=2$, $\pm1$), 16 ($n_1=4$, $\pm\tfrac12$).
   A state is **dark iff some corner with both outer links active has both inner links active with the inner pair in the
   triplet ($J=1$)**. Dark states occur only for $n_1\in\{0,2\}$ (65 + 112).
2. **$W$ factorises over corners** [`wcorner.py`]. $W=\tfrac14 X_{j}^{\otimes4}\otimes\prod_c K_c$, and every matrix element is $\pm\tfrac14$.
   At each corner $K_c$ either creates a bond from two empty legs, annihilates a bond, or moves the label from one leg to
   the other. $W$ and $W^\dagger$ add up constructively on every pair.
3. **The outer register never needs to be read** [`inner_only_check.py`, max deviation $4.4\times10^{-16}$ on 60 random
   physical states]. $U_B = e^{-i\beta H_W}\otimes 1_{\rm outer}$ with $H_W=-(W+W^\dagger)$ acting on the 625 inner codes.
   $U_E$ is inner-only too, so both factors can be built on the 12 data qubits alone. Outer reads remain an option.
4. **$U_E$ costs 0 CX.** It is $\exp(-i\tfrac34\alpha\sum_l j_l)$, i.e. four $R_z$ gates on q2, q5, q8, q11. That is 4 rotations, about 4×60 T.
   Inside a pair the mean of $n_j$ is always 2, so for bright states $U_E$ is a relative $Z$ phase plus the common factor $e^{-3i\alpha/2}$.
5. **Convention obstruction** [`gadget_check.py`]. At every corner, "bond parity odd" holds exactly when "diff relation = copy". As a result,
   no corner can have both an even bond and a copy relation. With the vacuum legs at $\lvert00\rangle$, a leg-only involution
   that reproduces the diff move exists **only at copy corners**. **Fix: relabel the two NOT legs**. Apply
   CX(q2→q0) and CX(q11→q9) at the start and undo them at the end (4 CX in total). After that every corner is "odd bond + copy".
   The two partner leg states at each same-type corner (vacuum $\lvert00\rangle$ and the bond) are then **orthogonal**, so the
   partner map is a Clifford involution at every corner. This was derived by hand from the corner table. The next proposer
   should re-check it with the oracle (one line per corner).
6. Negative result. The per-corner template "CX(a→b) · CCX(j,leg→leg) · CCH(j_A,j_B→leg)", padded with Paulis or with
   single-control Pauli fixes at 3 positions, has **no** solution at corner 0 (exhaustive search over 35,152 placements,
   `gadget_search3.py`). The plain-Pauli version also has no solution at corners 0 and 1 (`gadget_check.py`). Making the legs canonical with $j$-controlled gates therefore needs at least 2 two-control gates per corner plus fixes.

The common skeleton for every family is $U = R^\dagger\, D^\dagger\, \mathcal R\, D\, R\, U_E$, where:
- $R$ is the relabel (fact 5);
- $D$ is a corner frame change;
- $\mathcal R$ is the rotation of one flip qubit $F$. $F$ is obtained by a GHZ fold of the four $q_j$ (3 CX each way):
  $F=j_b$ and $r_i=j_i\oplus j_b$. The bits $r_i$ stay the same when all $j$ flip, and they determine the $t_c$ and $n_1$.

The **bottleneck shared by all families** is the rotation angle $\theta=\beta c(n_1)\cdot[\text{not dark}]$: it needs a "bright" flag,
which is an AND over four corners.

---

## F1 — Involution frame: one multiplexed Pauli-string rotation, no $j$-controlled Toffolis in the frame (most promising)

**Datapath.**
1. $U_E$ as 4 $R_z$ gates. Relabel $R$ (2 CX). GHZ fold of the $q_j$ onto $F$ (3 CX).
2. Per corner, apply a **type-controlled Clifford diagonaliser** $W_c(t_c)$ on the two legs. Use $t_c=r_A\oplus r_B$, made into
   single qubits for 3 corners with 1–2 CX; the 4th corner uses the outer parity $e_A\oplus e_B$ as control.
   Choose involutions $N_c(t)$ on the legs: $N_{\rm same}$ swaps vacuum $\leftrightarrow$ bond, $N_{\rm diff}$ swaps
   $(x,0)\leftrightarrow(0,x)$, with $(2,2)$ eigenvalue multiplicities. Then on bright pairs the magnetic generator is
   exactly $H_B=-c\,X_F\otimes\prod_c N_c(t_c)$. Pick $W_c$ so that $W_c N_c W_c^\dagger = Z_{a_c}$.
   No gate in the frame is controlled by $F$ or by $j_A, j_B$; $t_c$ does not change under the flip.
   Rough sketch for an odd/copy corner: CX(a→b), then a $b$-controlled $H$ for diff and a $b$-controlled $HX$ for same,
   selected by $t_c$. That is about 3–5 CX per corner per direction.
3. Rotation $e^{-i\theta X_F Z_{a_0}Z_{a_1}Z_{a_2}Z_{a_3}}$: accumulate the parity of the four $a_c$ into $F$ in the $H_F$ frame
   (4+4 CX). Multiplex the angle with a few flags. With $y=(r_r,\,r_r\oplus r_t,\,r_r\oplus r_l)$:
   - $n_1=0\Leftrightarrow y=000$, $n_1=4\Leftrightarrow y=100$;
   - $z=[y_2=y_3=0]$ (1 rccx in, 1 out);
   - $g$ = bright flag.
   The angle $g+gz-\tfrac32 zy_1$ (the coefficient is free on the never-occurring input $g=0,z=y_1=1$) has 5 Walsh terms
   plus a constant. That gives 6 rotations and about 6 CX for the Gray-code walk.
4. Dark flag $g$: per corner $d_c=[t_c=0]\wedge j_A\wedge[\text{legs}\ne\text{singlet}]$, i.e. a Bell test of the legs plus about one
   rccx. Then $g=\mathrm{NOR}(d_0..d_3)$ with 3 rccx in and 3 out. Flags may depend on $F$, because $g=1$ on both partners
   and $g=0$ only on dark states, which do not rotate.
   A cheaper variant uses outer reads: $d_c = e_Ae_B\wedge(\text{outer pair parallel} \vee \text{inner }\Psi^+)$ needs no $j$.
   It still needs one AND per corner.

**Cost (estimate):** frame 2×(4×~4) ≈ 32, plus GHZ 6, relabel 4, Pauli string 8, class multiplexing ~12, dark flags ~30–45, giving
**≈ 90–110 CX**. T: 4 ($U_E$) + 6 ($U_B$) rotations ≈ 600, plus about 60–100 T from the rccx gates.

**Why it beats a generic circuit.** The 433-dimensional problem reduces to one qubit rotating under a 5-body Pauli string.
The frame is Clifford and is controlled only by quantities that do not change under the flip. Every non-Clifford cost sits in the angle selection.

**Main risk.** The dark flag. Distinguishing singlet from triplet needs $j$ or a type2 gate (two outer bits) per corner, which is about 1 Toffoli per corner each way.
Secondary risk: the type-controlled $W_c$ must send $N_{\rm same}$ and $N_{\rm diff}$ to $Z$ on the **same** leg qubit. A naive choice lands them on different qubits (b vs a), which costs an extra swap.
Build the four $W_c$ with a small exhaustive search on 4 qubits $(t, a, b, \text{scratch})$ before writing the program.
The coupling signs ($\pm$ within the $n_1=2,4$ classes) must come out of the $N_c$ phases. Check them on the oracle `--block` outputs.

## F2 — Pair frame: $j$-controlled corner disentanglers, dark flag left in a leg

**Datapath.** Same skeleton, but $D$ makes the legs canonical. Per corner, the gadget is controlled by $(j_A, j_B)$:
1. Move the diff label onto one fixed leg: CX(a→b) then rccx($j_A$,b→a). The rccx relative phases fall on inputs that never occur.
2. Uncreate the bond on same corners: a CCH($j_A,j_B$→a), or one AND ancilla $y=j_A\wedge j_B$ used by a CH and the parity-fix CX.
   After relabel $R$ every bond is odd, so the parity fix is uniform.
3. On dark states the gadget leaves a single leg bit $a_c=1$. Then $g=\mathrm{NOR}(a_0..a_3)$ directly (18 CX in and out).
4. GHZ fold, then the multiplexed $R_x$ on $F$ as in F1 (no Pauli string needed).

**Variant (padded frame).** Spend the don't-care codes 001/010/011 (a $j=0$ link carrying labels) by **filling** the empty legs
(bond on vacuum corners, copied label on the inactive diff leg) instead of emptying the full ones. The partner map then becomes
$X^{\otimes4}$ on the four $q_j$ exactly. It has the same gadget cost (mirror image) and a different dark-flag geometry.

**Cost (estimate):** about 10–12 CX per corner per direction, giving ≈ 80–95 for $D$ and $D^\dagger$. Total **≈ 115–135 CX**. T is similar to F1 plus 8 CCH (about 4–7 T each).
**Why it should beat a generic circuit.** It is fully local (4-qubit gadgets), and the dark and class flags come out cheaply.
**Main risk.** Fact 6 says the gadget needs at least 2 two-control gates per corner. If the search does not find something better than about 10 CX per corner, F2 loses to F1.

## F3 — Outer-classical precompute + F1/F2 core (the "branch history from the outer register" datapath)

**Datapath.** Every flip-invariant selector can be computed **once** from the read-only outer register into clean ancillas
at the start of the step and uncomputed at the very end. This covers:
- $t_c=e_A\oplus e_B$ (2 CX each);
- type2$_c=e_Ae_B$ (rccx);
- "outer pair parallel" (2 CX + rccx);
- $n_1$-class flags $z$, $y_1$.

These selectors are then shared by $D$, the rotation, and $D^\dagger$ instead of being recomputed from $r$ on each side. The dark flag
becomes $d_c=\text{type2}_c\wedge(\text{parallel}_c\vee \text{inner }\Psi^+_c)$ with no $j$ dependence, so it commutes with the whole frame.
**Cost:** it saves about one third of the flag CX of F1, at the price of up to 8–12 extra ancilla qubits (well under the 60 limit).
Estimated **≈ 80–100 CX**.
**Risk.** Each type2 AND (two outer bits) still costs a Toffoli-class gate. The saving is real only if the flags are reused at least twice.
Treat this as an implementation choice on top of F1. It is listed separately because its main datapath is different:
the classical outer precompute, not the corner frame, carries the flags.

## F4 — Exact interpolation on the discrete spectrum (QSVT style, no flags) (low priority, structurally different)

**Datapath.** The spectrum of $H_W$ on the inner space is $\{0,\pm\tfrac12,\pm1,\pm2\}$ (7 points). A polynomial of degree about 6
interpolates $e^{-i\beta\lambda}$ exactly on these points. Because $|e^{-i\beta\lambda}|=1$, the block-encoded result is unitary
on the physical space, so the signal ancilla returns to $|0\rangle$ deterministically. Exactness is preserved without postselection.
Dark states (eigenvalue 0) and the classes are handled **automatically**, with no flags.
Block-encode $W/4$ from the corner factorisation (fact 2): one dilation ancilla per corner for the non-unitary $K_c$, plus the
$X^{\otimes4}$ on the $q_j$.
**Cost:** about 6–8 queries × (4 controlled corner dilations ≈ 20–40 CX) ≈ **150–300 CX**. It loses to F1 unless the block-encoding is much cheaper than estimated.
**Risk.** A degree-6 polynomial with $|p|\le1$ on all of $[-1,1]$ may not exist at the given subnormalisation, which forces a higher degree.
The angles depend on $\beta$ (fine, computed at emission). The skeleton is identical across angle pairs only if the degree is fixed.

---

### Notes for any proposer
- Do $U_E$ first as 4 $R_z$ on q2, q5, q8, q11 (0 CX). They commute with $R$ and with the GHZ fold.
- The rotation needs only the bright flag and 3 class bits. Dark never coexists with $n_1=4$; spend that don't-care in the multiplexer.
- rccx/Margolus relative phases are free whenever they land on unused codes (a $j=0$ link with nonzero legs) or on the triplet
  legs of same-type corners. Check this with `run_candidate --trial`.
- Fully gauge-invariant derivations use the corner table above (oracle-derived; reproduce with `scratch/proposer/twelve_study4.py`).
