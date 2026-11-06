# Brief: `twelve` / `step`, round 2, family `F4`

**Task.** Rewrite the parent to improve the key; return the complete program.

- Task specification: `compress/specs/twelve-step.md`
- Proved structure (Lean): `compress/lean/structure.json` (machine-proved facts about the problem; the same facts are in the section 'Proved structure (Lean)' of the specification)
- Check a draft: `python -m su2plaq.compress.run_candidate <program.py> --encoding twelve --kind step --trial` (seconds), `--full` before you finish; the oracle: `python -m su2plaq.compress.oracle ...`

## Parent
- program: `compress/programs/twelve/F4/001-spectral-frame.py` (entry `r01-F4-001`, sha256 15d0709c4cc2)
- feedback: `results/compress/twelve/feedback/r01-F4-001.json`
- cost: CX 126, T_eps 1254, depth_CT 2579, qubits 34
- summary: Spectral frame: 2-CX corner frames + type-controlled CH + padding put every bright pair on one flip qubit F (H_B = kappa(t) g X_F), outer-AND dark bits, pairwise NOR flags, 14-term exact Walsh phase polynomial of the 7-point spectrum on F.

## Archive alternatives (paths and costs only)
- `compress/programs/twelve/F2/001-pair-frame-2cx.py` (entry `r01-F2-001`, family `F2`): CX 126, T_eps 738, depth_CT 1226, qubits 36; F2 pair frame: per corner a 2-CX leg frame + type-selected C_{jA}(X) makes both partners of every bright pair equal except the flip bit F=j_b; one rccx per corner leaves the bright flag; U_B = one (g, z, t)-multiplexed X rotation of F (6 Rz), U_E = 4 phases.
- `compress/programs/twelve/F3/001-flag-gadget.py` (entry `r01-F3-001`, family `F3`): CX 132, T_eps 1130, depth_CT 2210, qubits 35; per-corner 10-CX gadget (two Margolus + CX + 2 CH, partner map X on one leg, dark flag left in a corner ancilla), 5-CX fold that exposes the corner types t_c as qubits, 4-input AND of the bright flags, 12-term Walsh multiplexed Rx on j_b (CX 132).
- `compress/programs/twelve/F1/001-involution-frame.py` (entry `r01-F1-001`, family `F1`): CX 146, T_eps 754, depth_CT 1168, qubits 36; F1 involution frame: per-corner frame CH(t->A).H_A.CX.CH.CX (4 CX) turns every bright pair into X_F (x) prod_c Z_{A_c}; dark flag from the frame marker B_c gated by t_c-bar plus one outer m-AND per corner (reads only the 8 outer m bits); one 6-term multiplexed Rz on F (gzu/t flags).

## Last 1 attempts of family `F4`
- `r01-F4-001`: valid, key [126, 1254, 2579, 34]; Spectral frame: 2-CX corner frames + type-controlled CH + padding put every bright pair on one flip qubit F (H_B = kappa(t) g X_F), outer-AND dark bits, pairwise NOR flags, 14-term exact Walsh phase polynomial of the 7-point spectrum on F.

## DISCOVERY notes of all programs (last 12 of at most 30 lines)
- r01-F1-001: DISCOVERY: After the per-link relabel (legs ^= j on corners 0,2 legs; q0 ^= j_b, q9 ^= j_l for corners 1,3) the corner frame C0 = H_A CX_AB CH_BA CX_AB maps (vac, bond) to Z_A-partners with B=0, and CH(t->A) C0 does the same for the diff pair: the same-vs-diff frames differ by one t-controlled Hadamard (anticommuting partner involutions), so the frame costs 4 CX per corner.
- r01-F1-001: DISCOVERY: The pair-relation sign of the frame differs from the true coupling sign only on the n1=2 patterns t=(001),(110) (u=t0^t1=0, v=t1^t2=1); folding that sign into the angle gives a 6-term Walsh multiplexer on (g, z, t1, u) with no constant term (8 CX).
- r01-F1-001: DISCOVERY: A leg-only (outer-linear) marker cannot flag all dark corners: vac and one parallel triplet share the leg code, so each corner needs one AND of its two outer m bits (literal pattern (1,1) for corners 0,2, (1,0)/(0,1) for corners 1,3).
- r01-F2-001: DISCOVERY: the leg map |00>->|00>, Psi- -> |10>, Psi+ -> |01>, |11> -> -|11> (equal to CX(a,b) CH(b,a) CX(a,b) on all bright legs) has Weyl point (pi/8, pi/8, 0) and the 2-CX, 2-T circuit S_a (HSdgH)^2 CX(a,b) (HTH_a, T_b) CX(a,b) (HSH)^2 S_a: one CX less per corner and side.
- r01-F2-001: DISCOVERY: in that frame same-type bright legs are |00>, dark legs are basis states != |00>, and with C_t(H) CX(jA,a) C_t(YH) the diff legs never hit |01>, so bright_c = t ^ (~a)(~b ^ t) costs 1 CX + 1 rccx; a CX-only flag is impossible (the frame images of |00>, Psi-, Psi+, |11> are four basis states with XOR 0).
- r01-F2-001: DISCOVERY: an X on leg a of corner 0 between the frame and the type gates flips only the diff partner sign there, so kappa = -1 for every n1=2 pair (2 for n1=0, 1/2 for n1=4, 0 dark) and the Walsh mux over (g, z=[all types equal], t) needs 6 CX; a chain fold q11=t3, q8=t2, q5=t1 gives three corner types without outer reads.
- r01-F3-001: DISCOVERY: A 10-CX corner gadget [rccx(jA,jB->a), cx(A->B), ch(B->A), cx(a->B), rccx(A,~B->a), ch(t->A)] maps every bright pair to a partner differing by X on leg A only and leaves a=1 exactly on dark corners; corners 1,3 need cx(jA->A)+z(A) first.
- r01-F3-001: DISCOVERY: The fold j_b->j_r, j_l->j_t, j_b->j_l, j_r->j_t, j_t->j_l (5 CX) exposes all four corner types t_c for the t-controlled H and leaves (t1, t1^t3, t2); in that encoding the rotation (angle g*2*beta*h*s, one free point at n1=4,g=0) has an 11-term Walsh support walked with 12 CX.
- r01-F3-001: DISCOVERY: Outer reads do not pay here: t_c from the j-fold is cheaper than eA^eB, and every dark flag needs inner Bell structure plus j (E-par dark legs equal the vacuum legs), so no flag can be precomputed once; in the 3-CX partner frames (cx, ch, ch(t)) no single-AND dark flag exists (exhaustive check).
- r01-F4-001: DISCOVERY: A 2-CX corner frame U=[HSH_A,HS_B; CX(B>A); THS_A,HTH_B; CX(B>A); S,H_B] maps the same-type partner map to X_A and the diff-type one to Z_A; with CH(t->A) and padding CX(j_B->A) interleaved with the chain fold, H_B = kappa(t)*g*X_F exactly on all 433 states, kappa=-2 (n1=0), (-1)^t0 (n1=2), +1/2 (n1=4).
- r01-F4-001: DISCOVERY: In that padded frame a same-type corner's dark (inner J=1) codes are 10/11/01 vs bright 00; one AND of the two outer q_m bits (the parallel branch) makes dark a single leg bit A, so dark_c = (not t_c) and A_c (4 corners -> 2 pairwise NORs a,b).
- r01-F4-001: DISCOVERY: The eigenphase beta*kappa(t)*a*b over (a,b,t1,t2,t0) has minimum Walsh support 14 (MILP over the free values), Gray-walked with 20 CX.

## Output
Write ONE program to `compress/programs/twelve/F4/002-<slug>.py` (docstring starting with `SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under `scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.
