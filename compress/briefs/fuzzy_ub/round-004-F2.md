# Brief: `fuzzy_ub` / `UB`, round 4, family `F2`

**Task.** Rewrite the parent to improve the key; return the complete program.

- Task specification: `compress/specs/fuzzy_ub-UB.md`
- Proved structure (Lean): `compress/specs/fuzzy-structure.json` (machine-proved facts about the fuzzy units: counts, K1/K2 spectra; the same facts are in the section 'Proved structure (Lean)' of the specification)
- Check a draft: `python scripts/m10_round.py candidate <program.py> --encoding fuzzy_ub --kind UB --trial` (seconds), `--full` before you finish; the oracle: `python scripts/m10_round.py oracle ...`

## Parent
- program: `compress/programs/fuzzy_ub/F2/003-merged-group-fredkin7-resynth.py` (entry `r03-F2-003`, sha256 c6fb176abe10)
- feedback: `results/compress/fuzzy_ub/feedback/r03-F2-003.json`
- cost: CX 165, T_eps 2914, depth_CT 7221, qubits 14
- summary: F1 elite datapath (parity frame, 8 Fredkin frames, final frame refactored to start with (1 2), merged 12-term phase polynomial for t=1 sectors 2,3,6,7 over x=t~l,y=tl,r,w01,w23, r-split one-hot only for t=0) recorded and re-emitted with level-3 resynthesis of every beta-free segment between rotations (7-CX Fredkins, decoder/one-hot CX cancellations); 6 ancillas, 165 CX.

## Archive alternatives (paths and costs only)
- `compress/programs/fuzzy_ub/F3/003-r-fold-sectors-1-5.py` (entry `r03-F3-003`, family `F3`): CX 151, T_eps 1902, depth_CT 4682, qubits 13; r02-F1-002 layout, but a (p_r & ~p_t & ~f)-controlled [Z q2^0 Z q2^1, then Fredkin(q2^0,q2^2)] at start/end maps sectors 1,5 exactly onto 0,4, so r drops out of the t=0 sectors: 6 frame Fredkins (7-CX), no r-split one-hot, 4 middles instead of 6; 151 CX.
- `compress/programs/fuzzy_ub/F1/003-fredkin7-merged-group.py` (entry `r03-F1-003`, family `F1`): CX 164, T_eps 2920, depth_CT 7222, qubits 14; parent r02-F1-002 (frames, merged t=1 group phase polynomial, Bell-decoder/Fredkin CX cancellation) with every one of the 8 f-controlled q2 swaps emitted as the 7-CX Clifford+T Fredkin of r02-F3-002 (its dagger form where the first CX is cancelled against the last Bell-decoder CX); 164 CX.
- `compress/programs/fuzzy_ub/seed/010-general_polish.py` (entry `r00-seed-010`, family `seed`): CX 1596, T_eps 2682, depth_CT 4912, qubits 15; the reference circuit after the deterministic polish passes.

## Last 3 attempts of family `F2`
- `r01-F2-001`: valid, key [268, 1276, 2703, 14]; parity frame, then 8 per-sector sandwiches F_p^dag C^{p,S}R_x(-4 beta sigma_p) F_p with uncontrolled frames (f-controlled q2 permutation + Bell decoders), merged permutations between sectors and Gray-shared rccx ladders.
- `r02-F2-002`: valid, key [172, 2916, 7263, 15]; F1 datapath (parity frame, 8 Fredkin q2-permutation frames, Bell decode) with a partial sector one-hot: (t,l) lines of the same-frame sector pairs {2,3},{6,7} are not split by p_r; each pair is one Walsh-Gray R_x over (line&w23 or line, p_r, w01) with shared Bell-pair ANDs; beta-free segments re-synthesised (7-CX Fredkins).
- `r03-F2-003`: valid, key [165, 2914, 7221, 14]; F1 elite datapath (parity frame, 8 Fredkin frames, final frame refactored to start with (1 2), merged 12-term phase polynomial for t=1 sectors 2,3,6,7 over x=t~l,y=tl,r,w01,w23, r-split one-hot only for t=0) recorded and re-emitted with level-3 resynthesis of every beta-free segment between rotations (7-CX Fredkins, decoder/one-hot CX cancellations); 6 ancillas, 165 CX.

## DISCOVERY notes of all programs (last 20 of at most 30 lines)
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
- r03-F1-003: DISCOVERY: the 7-CX Clifford+T Fredkin combines with the decoder cancellation of r02-F1-002: Fredkin is self-inverse, so its dagger form starts with cx(q2^j -> q2^i) and the -1 CX cancellation still applies (6 CX for that swap), 62 -> 54 CX on the frames.
- r03-F1-003: DISCOVERY: replacing the Toffoli of a Fredkin by rccx (5-CX relative-phase Fredkin) leaves a diagonal residue with >= 3 two/three-body parities (f^a, a^b, f^a^b) whose correction costs >= 3 CX even after cancelling against the Fredkin tail, so it never beats 7 CX; qiskit level-3 resynthesis of the beta-free runs between rz finds nothing further.
- r03-F2-003: DISCOVERY: the F1 merged-group polynomial (-6 CX vs pair Walsh R_x with u-AND) and the F2 segment resynthesis compose: 172 -> 165 CX, 14 qubits; the final-frame (1 2) refactor survives resynthesis.
- r03-F2-003: DISCOVERY: exhaustive frame search (24 f-controlled q2 permutations x all Bell-decoder pair sets, any diagonal R_x angle function) finds no common frame for t=0 sector pairs {0,4},{1,5},{0,1},{4,5}; {0,5} share perm (2,3,0,1) and {1,4} share (0,3,2,1) only with incompatible decoder pairs, so sectors 0,1,4,5 cannot be merged like 2,3,6,7.
- r03-F3-003: DISCOVERY: sectors 1 and 5 are exactly equivalent to 0 and 4 (c=+1) under V=(V0,V1) on q2 with V1=I and V0=SWAP(0,2) Z0 Z1 (Z first) (or V0 = a 3-cycle on wires 0,1,2, no Paulis); no f-uniform signed permutation does it (64 joint solutions, all f-dependent); sectors 3/2 and 7/6 differ in rank (1 vs 4, 4 vs 16) so no r-merge exists there.
- r03-F3-003: DISCOVERY: with 1,5 folded the frame sequence (2 3)(0 1) | (0 2)(1 3)(0 2)=(1 3) | back needs 6 Fredkins instead of 8.

## Output
Write ONE program to `compress/programs/fuzzy_ub/F2/004-<slug>.py` (docstring starting with `SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under `scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.

## Fuzzy hook (M10)

Use `python scripts/m10_round.py candidate <program> --encoding fuzzy_ub --kind UB --trial|--full` instead of `python -m su2plaq.compress.run_candidate`, and `python scripts/m10_round.py oracle ...` instead of the oracle module. Programs import only `su2plaq.compress.{builder,oracle,spec}`, numpy, qiskit. Frame qubits 0..7 are the row qubits (see the specification); ancillas via `Builder.alloc`.
