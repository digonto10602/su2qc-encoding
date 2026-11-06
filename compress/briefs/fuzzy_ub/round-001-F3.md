# Brief: `fuzzy_ub` / `UB`, round 1, family `F3`

**Task.** Rewrite the parent to improve the key; return the complete program.

- Task specification: `compress/specs/fuzzy_ub-UB.md`
- Proved structure (Lean): `compress/specs/fuzzy-structure.json` (machine-proved facts about the fuzzy units: counts, K1/K2 spectra; the same facts are in the section 'Proved structure (Lean)' of the specification)
- Check a draft: `python scripts/m10_round.py candidate <program.py> --encoding fuzzy_ub --kind UB --trial` (seconds), `--full` before you finish; the oracle: `python scripts/m10_round.py oracle ...`

## Parent
none: write a fresh program for this family (the seeds below are alternatives, not parents).

## Archive alternatives (paths and costs only)
- `compress/programs/fuzzy_ub/seed/010-general_polish.py` (entry `r00-seed-010`, family `seed`): CX 1596, T_eps 2682, depth_CT 4912, qubits 15; the reference circuit after the deterministic polish passes.

## Last 0 attempts of family `F3`
- (none yet)

## DISCOVERY notes of all programs (last 0 of at most 30 lines)
- (none yet)

## Output
Write ONE program to `compress/programs/fuzzy_ub/F3/001-<slug>.py` (docstring starting with `SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under `scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.

## Fuzzy hook (M10)

Use `python scripts/m10_round.py candidate <program> --encoding fuzzy_ub --kind UB --trial|--full` instead of `python -m su2plaq.compress.run_candidate`, and `python scripts/m10_round.py oracle ...` instead of the oracle module. Programs import only `su2plaq.compress.{builder,oracle,spec}`, numpy, qiskit. Frame qubits 0..7 are the row qubits (see the specification); ancillas via `Builder.alloc`.
