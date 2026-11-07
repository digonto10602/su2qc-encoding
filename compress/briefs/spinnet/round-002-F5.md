# Brief: `spinnet` / `step`, round 2, family `F5`

**Task.** Rewrite the parent to improve the key; return the complete program.

- Task specification: `compress/specs/spinnet-step.md`
- Proved structure (Lean): the section 'Proved structure (Lean)' of the specification (kernel-checked facts about the spin-network problem; there is no separate structure file)
- Check a draft: `python -m su2plaq.spinnet.loop candidate <program.py> --trial` (seconds), `--full` before you finish (`--order 2` for the second-order step); the oracle: `python -m su2plaq.spinnet.loop oracle ...`

## Parent
- program: `compress/programs/spinnet/F5/001-tlean_7rot.py` (entry `r01-F5-001`, sha256 d1ea45cc83ce)
- feedback: `results/compress/spinnet/feedback/r01-F5-001.json`
- cost: CX 46, T_eps 491, depth_CT 914, qubits 17
- summary: T-lean step with 7 rotations (3 for U_E, 4 for U_B, the minimum for +-1 phase decompositions): U_E = phases on y_b, on the pivot r^t^l and on maj(r,t,l) (one rccx pair onto the pivot); U_B = 4-term pivot walk over B, F, F&~e with B and F&~e toggled onto the pivot by nested rccx pairs and the A flag XORed into corner qubit c3; 17 qubits, angles k*alpha/4 and k*beta/2 (one shifted by -pi/4).

## Archive alternatives (paths and costs only)
- `compress/programs/spinnet/F1/001-dimer-direct-rccx-pivot.py` (entry `r01-F1-001`, family `F1`): CX 32, T_eps 832, depth_CT 1583, qubits 18; dimer frame (pivot = link b) with two clean flags a1=[c0=c2=0], A=[u=v=0] and the third AND a2=[c1=c3=0] toggled straight onto the pivot by two rccx inside the H-frame phase walk (one CZ cancels their leftover sign), plus a 1-CX merge of the last ladder CX with the first walk toggle; 32 CX, 9+4 rotations, all angles k*beta/4 or 3*alpha/4.
- `compress/programs/spinnet/F2/001-aflag_corner_walk.py` (entry `r01-F2-001`, family `F2`): CX 33, T_eps 1380, depth_CT 2852, qubits 17; F2 single-flag corner polynomial: dimer ladder (pivot = link b), one rccx flag A=[u=v=0], and a 22-step closed pivot walk over the raw corner parities (c0..c3, A, e) carrying 18 rz(+-beta/4) terms; the first walk step is fused with the last ladder CX into a 1-CX Clifford; 33 CX, 17 qubits, all angles +-beta/4 or -3*alpha/4.
- `compress/programs/spinnet/seed/001-spinnet_v2_pairs9.py` (entry `r00-seed-001`, family `seed`): CX 34, T_eps 832, depth_CT 1597, qubits 19; the vendored su2qc-trotter spinnet_v2 pairs9 skeleton for U_B (angles solved from K, route-B signs) behind our electric layer; every angle is a linear function of spec.alpha / spec.beta.

## Last 1 attempts of family `F5`
- `r01-F5-001`: valid, key [46, 491, 914, 17]; T-lean step with 7 rotations (3 for U_E, 4 for U_B, the minimum for +-1 phase decompositions): U_E = phases on y_b, on the pivot r^t^l and on maj(r,t,l) (one rccx pair onto the pivot); U_B = 4-term pivot walk over B, F, F&~e with B and F&~e toggled onto the pivot by nested rccx pairs and the A flag XORed into corner qubit c3; 17 qubits, angles k*alpha/4 and k*beta/2 (one shifted by -pi/4).

## DISCOVERY notes of all programs (last 11 of at most 30 lines)
- r01-F1-001: DISCOVERY: two rccx gates targeting the walk pivot leave only the sign (-1)^(l1*dS) (l1 = their first control, dS = parity toggled on the pivot between them), so an AND toggled twice costs 6 CX instead of 6+2 with an ancilla; here dS = a1 and one CZ(c1bar, a1) removes it.
- r01-F1-001: DISCOVERY: CX(a->b) H(a) CX(b->a) = sdg(b) CX(a->b) s(b) s(a) h(a) (1 CX), so the ladder's last CX merges with the first pivot toggle when the walk starts with that ladder qubit and the constant term is rotated at the end of the walk.
- r01-F2-001: DISCOVERY: CX(b->r); H(b); CX(r->b) is a 1-CX Clifford, so a pivot walk that starts or ends with the e-step saves 1 CX per fused end; with the A flag alone, exhaustive IDA* over the 624 minimal 16-term corner sets (<= 5 relabel CX among c0..c3,A,e) shows the walk costs >= 21 CX after fusion, i.e. >= 33 CX in total; annealing over non-minimal term sets also stops at 21 (18-19 terms).
- r01-F2-001: DISCOVERY: Every minimal 16-term solution over (c,A,e) has rotation +-beta/4 per corner subset T and decoration g_A = NOT 1_H(T), g_e = 1_H xor 1_K, where H, K are 4-sets of corner subsets balanced on the dark zero sets {c0,c1,c2,c3,c0c1,c1c2} resp. {c0,c2,c3,c2c3,c0c3} with |H & K| = 1; H can never be a face of the corner 4-cube, so every Gray walk pays about 6 decoration toggles.
- r01-F2-001: DISCOVERY: Dropping the A flag (terms over c0..c3,e,u,v) does not pay: 16 terms are infeasible (MILP), the best support found has 22 terms and annealed pivot walks need >= 30 CX (36 total).
- r01-F3-001: DISCOVERY: the ladder Clifford [CX(0,2) CX(0,1) H(0)] absorbs any pivot preload/unload from span(e,u) for free (3-qubit block CX(e->p) H CX(0,1) CX(0,2) = 2 CX), so the pivot walk may start/end at p, p^e, p^u, p^e^u at no cost.
- r01-F3-001: DISCOVERY: with flags A, NOR(c0,c1), NOR(c2,c3) the minimal pivot polynomial has exactly 9 terms (10 solutions) and needs 9 pivot CX; the pair NOR(c0,c2),NOR(c1,c3) (the pairs9 seed) also reaches 9 with free endpoints.
- r01-F3-001: DISCOVERY: single flag A gives 16 terms, but no parity network below 22 CX was found (beam/TSP/annealing over all 624 minimal sets), so 34 CX is that family's floor in this search.
- r01-F5-001: DISCOVERY: U_E needs only 3 rotations: w(y) = y_b + (y_r^y_t^y_l) + 2 maj(y_r,y_t,y_l), and maj = P ^ OR(t^l, r^l) is one rccx onto the pivot P = r^t^l of the frame (b^r^t^l, t^l, P, r^l); U_B's pivot angle needs 4 rotations: f = -1/4 + 3/4 Z_A + 1/4 Z_B - 3/4 Z_B Z_(A&~e) (B=1 bright; no 3-term +-1 decomposition of {0,1,-2,-1/2} exists, exhaustive search).
- r01-F5-001: DISCOVERY: On dark codes the A flag F only has to satisfy F=1 => t=l (then f=0), so A can be XORed into corner qubit c3 (c3=1 forces t=l=1/2): no A ancilla, 17 qubits.
- r01-F5-001: DISCOVERY: rccx pairs on a non-clean target cancel their relative phase whenever the enclosed walk is closed on that target; cx(a,P)*rccx(a,e,P) fuses to rccx(a,~e,P), and back-to-back rccx on the pivot share their h/t edges (T_fixed 48 -> 45).

## Output
Write ONE program to `compress/programs/spinnet/F5/002-<slug>.py` (docstring starting with `SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under `scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.
