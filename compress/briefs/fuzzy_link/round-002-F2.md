# Brief: `fuzzy_link` / `UE`, round 2, family `F2`

**Task.** Rewrite the parent to improve the key; return the complete program.

- Task specification: `compress/specs/fuzzy_link-UE.md`
- Proved structure (Lean): `compress/specs/fuzzy-structure.json` (machine-proved facts about the fuzzy units: counts, K1/K2 spectra; the same facts are in the section 'Proved structure (Lean)' of the specification)
- Check a draft: `python scripts/m10_round.py candidate <program.py> --encoding fuzzy_link --kind UE --trial` (seconds), `--full` before you finish; the oracle: `python scripts/m10_round.py oracle ...`

## Parent
none: write a fresh program for this family (the seeds below are alternatives, not parents).

## Archive alternatives (paths and costs only)
- `compress/programs/fuzzy_link/F1/001-bell_parity_net13.py` (entry `r01-F1-001`, family `F1`): CX 13, T_eps 644, depth_CT 1161, qubits 4; pair-Bell frame cx(q1,q3) cx(q2,q4) h(q1) h(q2) (2 CX each side) around a BFS-optimal 9-CX I->I parity network carrying the 10 Z-string phases as rz(-alpha/4) (6 K1 strings) and rz(-2 kappa2) (4 K2 strings); 13 CX, 10 rotations.
- `compress/programs/fuzzy_link/seed/010-general_polish.py` (entry `r00-seed-010`, family `seed`): CX 30, T_eps 644, depth_CT 1511, qubits 4; the reference circuit after the deterministic polish passes.
- `compress/programs/fuzzy_link/seed/000-general-ue.py` (entry `r00-seed-000`, family `seed`): CX 36, T_eps 644, depth_CT 1515, qubits 4; the reference circuit of the fuzzy_link encoding (UE) expressed through the Builder; every angle is a linear function of spec.alpha / spec.beta.

## Last 0 attempts of family `F2`
- (none yet)

## DISCOVERY notes of all programs (last 2 of at most 30 lines)
- r01-F1-001: DISCOVERY: in the frame (qubit bits b0..b3 after cx(3,1) cx(2,0) h(3) h(2)) H = const - alpha/8 * sum Z_s over s in {0001,0011,0100,0101,0110,0111} - kappa2 * sum Z_s over s in {1000,1011,1110,1111}; signs are constant, so every angle is -alpha/4 or -2 kappa2.
- r01-F1-001: DISCOVERY: the 9-CX network cx(0,1) cx(0,2) cx(3,1) cx(2,1) cx(0,1) cx(0,2) cx(3,1) cx(0,1) cx(2,1) returns to identity and visits all 7 weight>1 parities (BFS over GL(4,2) x coverage, minimum).

## Output
Write ONE program to `compress/programs/fuzzy_link/F2/001-<slug>.py` (docstring starting with `SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under `scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.

## Fuzzy hook (M10)

Use `python scripts/m10_round.py candidate <program> --encoding fuzzy_link --kind UE --trial|--full` instead of `python -m su2plaq.compress.run_candidate`, and `python scripts/m10_round.py oracle ...` instead of the oracle module. Programs import only `su2plaq.compress.{builder,oracle,spec}`, numpy, qiskit. `spec.beta` is kappa2; `alloc` is not allowed (more than 4 qubits is rejected).
