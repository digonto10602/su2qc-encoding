# Brief: `fuzzy_ub` / `UB`, round 3, family `F3`

**Task.** Rewrite the parent to improve the key; return the complete program.

- Task specification: `compress/specs/fuzzy_ub-UB.md`
- Proved structure (Lean): `compress/specs/fuzzy-structure.json` (machine-proved facts about the fuzzy units: counts, K1/K2 spectra; the same facts are in the section 'Proved structure (Lean)' of the specification)
- Check a draft: `python scripts/m10_round.py candidate <program.py> --encoding fuzzy_ub --kind UB --trial` (seconds), `--full` before you finish; the oracle: `python scripts/m10_round.py oracle ...`

## Parent
- program: `compress/programs/fuzzy_ub/F3/002-fredkin7-dp-onehot-phasepoly.py` (entry `r02-F3-002`, sha256 411f909ae8fa)
- feedback: `results/compress/fuzzy_ub/feedback/r02-F3-002.json`
- cost: CX 192, T_eps 3820, depth_CT 9543, qubits 16
- summary: F1 layout (parity frame, 8 f-controlled Fredkins DP-ordered over sectors, Bell decode, persistent sector one-hot, Gray-code C^3-R_x middles) with each Fredkin emitted as a 7-CX Clifford+T circuit instead of cx+ccx+cx (8 CX); 192 CX.

## Archive alternatives (paths and costs only)
- `compress/programs/fuzzy_ub/F1/002-merged-group-phasepoly.py` (entry `r02-F1-002`, family `F1`): CX 172, T_eps 2904, depth_CT 7206, qubits 14; parent r01-F1-001 frames, but the t=1 sectors 2,3,6,7 (one shared layout) get pair-AND ancillas w01,w23 and ONE merged phase polynomial on f over x=t~l, y=tl, r, w01, w23 (one-hot NOT split by r for t=1: 4 ancillas, 32 CX one-hot round trip); final frame re-factored to start with (1 2) so its CX cancels the last Bell-decoder CX; 172 CX.
- `compress/programs/fuzzy_ub/F2/001-sector-sandwich-gray.py` (entry `r01-F2-001`, family `F2`): CX 268, T_eps 1276, depth_CT 2703, qubits 14; parity frame, then 8 per-sector sandwiches F_p^dag C^{p,S}R_x(-4 beta sigma_p) F_p with uncontrolled frames (f-controlled q2 permutation + Bell decoders), merged permutations between sectors and Gray-shared rccx ladders.
- `compress/programs/fuzzy_ub/seed/010-general_polish.py` (entry `r00-seed-010`, family `seed`): CX 1596, T_eps 2682, depth_CT 4912, qubits 15; the reference circuit after the deterministic polish passes.

## Last 2 attempts of family `F3`
- `r01-F3-001`: valid, key [390, 1392, 2882, 14]; per-sector f-controlled Fredkin routing of q2 spins so each parity sector is X_f (x) (vertex-singlet projector); Bell-decode the singlet pairs into flags and apply one multi-controlled R_x(-4 beta sigma) on f per sector.
- `r02-F3-002`: valid, key [192, 3820, 9543, 16]; F1 layout (parity frame, 8 f-controlled Fredkins DP-ordered over sectors, Bell decode, persistent sector one-hot, Gray-code C^3-R_x middles) with each Fredkin emitted as a 7-CX Clifford+T circuit instead of cx+ccx+cx (8 CX); 192 CX.

## DISCOVERY notes of all programs (last 14 of at most 30 lines)
- r01-F1-001: DISCOVERY: every parity sector p of fuzzy_ub becomes sigma*c*X_f (x) (Bell projectors) under some f-controlled permutation of the four q2 wires; a DP over sector order and (branch0, branch1) layouts gives 8 Fredkins total (sectors 4,6,2,3,7 share one layout).
- r01-F1-001: DISCOVERY: keep a 6-ancilla one-hot of the parity p alive for the whole circuit (partly in place on the p_t/p_l wires, 24 CX each way); each rank-4 sector then is a 3-control R_x = 8-CX Gray-code phase polynomial with angles +-beta (Lean-friendly).
- r01-F2-001: DISCOVERY: every parity sector p of fuzzy_ub becomes sigma_p X_f (x) |1_S><1_S| after one f-controlled permutation of the four q2 qubits plus 0/1/2 CX+H Bell decoders; perm (3,0,1,2) (q2^i -> pi[i]) serves sectors 2,3,4,6,7 at once.
- r01-F2-001: DISCOVERY: sector frames need no parity control (the middle rotation is identity off-sector), so consecutive frames merge to f-controlled transposition chains; ordered 0,1,2,3,4,6,7,5 only 8 Fredkins (64 CX) are needed in total.
- r01-F3-001: DISCOVERY: with f-controlled swaps of q2 (control q1^b) every parity sector becomes exactly sigma X_f (x) |S><S|_pairs (x) I: p0 (b r)(t l)->rt, p1 (r t)(r l)->br, p2 (b r)(r t)->tl, p3 (b t)->br&tl sigma 4, p4 (b r)(r l)->rt, p5 (b l)(r t)->br, p6 (b r)(r t)(t l)->identity sigma 1, p7 (b t)(t l)->br.
- r01-F3-001: DISCOVERY: no product of <=3 raw-q1-controlled q2 swaps brings all 8 sectors into that normal form simultaneously.
- r02-F1-002: DISCOVERY: sectors 2,3,6,7 are exactly the t=1 parity sectors and share one frame; on that frame their four C^k-R_x merge into one 12-term phase polynomial (16-CX closed walk) over x=t&~l, y=t&l, r, w01=fl0&fl1, w23=fl2&fl3, fitted exactly on the reachable domain (x,y exclusive), so the one-hot needs no r-split for t=1 (saves 16 CX).
- r02-F1-002: DISCOVERY: in that merged polynomial the bare w01, w23 and constant Walsh terms of sectors 2,3,7,6 cancel exactly (angles 8b,-16b,8b,-4b), the merge is lossless.
- r02-F1-002: DISCOVERY: the last frame (0 3)(1 3)(2 3) equals (1 2)(0 3)(1 3) (time order); starting it with cswap(2,1) cancels the final Bell-decoder CX(q2^r->q2^t) against the Fredkin's first CX (-2 CX).
- r02-F2-002: DISCOVERY: sectors {2,3} and {6,7} differ only in p_r and share the frame rho=(3,0,1,2) with decoded pairs (0,1),(2,3); leaving their (t,l) one-hot lines unsplit by p_r (-16 CX) and doing one Walsh-Gray R_x per pair over (line&w23 | line, p_r, w01) costs 16 CX rotations + 18 CX ANDs for all four sectors.
- r02-F2-002: DISCOVERY: exhaustive DP over sector order and relative f-controlled q2 permutations (2 valid rho per sector, 8 for p3, 1 for p6) shows 8 Fredkins is minimal, also with the {2,3,6,7} block forced; no rho is shared by sectors 0&1 or 4&5.
- r02-F2-002: DISCOVERY: level-3 resynthesis of the beta-free segments saves 1 CX per Fredkin (8->7); 4-CX relative-phase Toffolis in paired same-wire Fredkins do not cancel (error ~1).
- r02-F3-002: DISCOVERY: no global routing exists for fuzzy_ub with <=4 controlled q2 swaps even when controls may be any GF(2)-linear function of (f, p_r, p_t, p_l) and uncontrolled relabels are free (exhaustive BFS over 12.7M distinct routings); the condition per sector is only on the relative element g0^-1 g1, whose allowed set R_p has 2 elements (8 for p3, 1 for p6).
- r02-F3-002: DISCOVERY: a Fredkin costs 7 CX (Clifford+T, 9 T) rather than the 8 of cx+ccx+cx; it applies to every f-controlled q2 swap of the routing families.

## Output
Write ONE program to `compress/programs/fuzzy_ub/F3/003-<slug>.py` (docstring starting with `SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under `scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.

## Fuzzy hook (M10)

Use `python scripts/m10_round.py candidate <program> --encoding fuzzy_ub --kind UB --trial|--full` instead of `python -m su2plaq.compress.run_candidate`, and `python scripts/m10_round.py oracle ...` instead of the oracle module. Programs import only `su2plaq.compress.{builder,oracle,spec}`, numpy, qiskit. Frame qubits 0..7 are the row qubits (see the specification); ancillas via `Builder.alloc`.
