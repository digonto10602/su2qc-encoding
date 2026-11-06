# Brief: `fuzzy_ub` / `UB`, round 2, family `F3`

**Task.** Rewrite the parent to improve the key; return the complete program.

- Task specification: `compress/specs/fuzzy_ub-UB.md`
- Proved structure (Lean): `compress/specs/fuzzy-structure.json` (machine-proved facts about the fuzzy units: counts, K1/K2 spectra; the same facts are in the section 'Proved structure (Lean)' of the specification)
- Check a draft: `python scripts/m10_round.py candidate <program.py> --encoding fuzzy_ub --kind UB --trial` (seconds), `--full` before you finish; the oracle: `python scripts/m10_round.py oracle ...`

## Parent
- program: `compress/programs/fuzzy_ub/F3/001-fredkin-singlet-sandwich.py` (entry `r01-F3-001`, sha256 babd37752a9b)
- feedback: `results/compress/fuzzy_ub/feedback/r01-F3-001.json`
- cost: CX 390, T_eps 1392, depth_CT 2882, qubits 14
- summary: per-sector f-controlled Fredkin routing of q2 spins so each parity sector is X_f (x) (vertex-singlet projector); Bell-decode the singlet pairs into flags and apply one multi-controlled R_x(-4 beta sigma) on f per sector.

## Archive alternatives (paths and costs only)
- `compress/programs/fuzzy_ub/F1/001-fredkin-dp-onehot-phasepoly.py` (entry `r01-F1-001`, family `F1`): CX 200, T_eps 3804, depth_CT 9501, qubits 16; parity frame + f-controlled qubit-permutation frames (8 Fredkins total, DP-optimal over sector order) + Bell decode + per-sector Gray-code C^3-R_x phase polynomials on a persistent sector one-hot; 200 CX.
- `compress/programs/fuzzy_ub/F2/001-sector-sandwich-gray.py` (entry `r01-F2-001`, family `F2`): CX 268, T_eps 1276, depth_CT 2703, qubits 14; parity frame, then 8 per-sector sandwiches F_p^dag C^{p,S}R_x(-4 beta sigma_p) F_p with uncontrolled frames (f-controlled q2 permutation + Bell decoders), merged permutations between sectors and Gray-shared rccx ladders.
- `compress/programs/fuzzy_ub/seed/010-general_polish.py` (entry `r00-seed-010`, family `seed`): CX 1596, T_eps 2682, depth_CT 4912, qubits 15; the reference circuit after the deterministic polish passes.

## Last 1 attempts of family `F3`
- `r01-F3-001`: valid, key [390, 1392, 2882, 14]; per-sector f-controlled Fredkin routing of q2 spins so each parity sector is X_f (x) (vertex-singlet projector); Bell-decode the singlet pairs into flags and apply one multi-controlled R_x(-4 beta sigma) on f per sector.

## DISCOVERY notes of all programs (last 6 of at most 30 lines)
- r01-F1-001: DISCOVERY: every parity sector p of fuzzy_ub becomes sigma*c*X_f (x) (Bell projectors) under some f-controlled permutation of the four q2 wires; a DP over sector order and (branch0, branch1) layouts gives 8 Fredkins total (sectors 4,6,2,3,7 share one layout).
- r01-F1-001: DISCOVERY: keep a 6-ancilla one-hot of the parity p alive for the whole circuit (partly in place on the p_t/p_l wires, 24 CX each way); each rank-4 sector then is a 3-control R_x = 8-CX Gray-code phase polynomial with angles +-beta (Lean-friendly).
- r01-F2-001: DISCOVERY: every parity sector p of fuzzy_ub becomes sigma_p X_f (x) |1_S><1_S| after one f-controlled permutation of the four q2 qubits plus 0/1/2 CX+H Bell decoders; perm (3,0,1,2) (q2^i -> pi[i]) serves sectors 2,3,4,6,7 at once.
- r01-F2-001: DISCOVERY: sector frames need no parity control (the middle rotation is identity off-sector), so consecutive frames merge to f-controlled transposition chains; ordered 0,1,2,3,4,6,7,5 only 8 Fredkins (64 CX) are needed in total.
- r01-F3-001: DISCOVERY: with f-controlled swaps of q2 (control q1^b) every parity sector becomes exactly sigma X_f (x) |S><S|_pairs (x) I: p0 (b r)(t l)->rt, p1 (r t)(r l)->br, p2 (b r)(r t)->tl, p3 (b t)->br&tl sigma 4, p4 (b r)(r l)->rt, p5 (b l)(r t)->br, p6 (b r)(r t)(t l)->identity sigma 1, p7 (b t)(t l)->br.
- r01-F3-001: DISCOVERY: no product of <=3 raw-q1-controlled q2 swaps brings all 8 sectors into that normal form simultaneously.

## Output
Write ONE program to `compress/programs/fuzzy_ub/F3/002-<slug>.py` (docstring starting with `SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under `scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.

## Fuzzy hook (M10)

Use `python scripts/m10_round.py candidate <program> --encoding fuzzy_ub --kind UB --trial|--full` instead of `python -m su2plaq.compress.run_candidate`, and `python scripts/m10_round.py oracle ...` instead of the oracle module. Programs import only `su2plaq.compress.{builder,oracle,spec}`, numpy, qiskit. Frame qubits 0..7 are the row qubits (see the specification); ancillas via `Builder.alloc`.
