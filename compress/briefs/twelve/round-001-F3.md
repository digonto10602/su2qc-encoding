# Brief: `twelve` / `step`, round 1, family `F3`

**Task.** Rewrite the parent to improve the key; return the complete program.

- Task specification: `compress/specs/twelve-step.md`
- Proved structure (Lean): `compress/lean/structure.json` (machine-proved facts about the problem; the same facts are in the section 'Proved structure (Lean)' of the specification)
- Check a draft: `python -m su2plaq.compress.run_candidate <program.py> --encoding twelve --kind step --trial` (seconds), `--full` before you finish; the oracle: `python -m su2plaq.compress.oracle ...`

## Parent
none: write a fresh program for this family (the seeds below are alternatives, not parents).

## Archive alternatives (paths and costs only)
- `compress/programs/twelve/seed/001-lean22_v2.py` (entry `r00-seed-001`, family `seed`): CX 162, T_eps 660, depth_CT 1029, qubits 35; su2qc-trotter lean22_v2 plaquette (vendored, plaquette only) behind our electric layer.
- `compress/programs/twelve/seed/002-lean22.py` (entry `r00-seed-002`, family `seed`): CX 210, T_eps 704, depth_CT 1148, qubits 38; su2qc-trotter lean22 plaquette (vendored, plaquette only) behind our electric layer.
- `compress/programs/twelve/seed/000-general.py` (entry `r00-seed-000`, family `seed`): CX 294, T_eps 952, depth_CT 1421, qubits 50; the reference circuit of the twelve encoding (step) expressed through the Builder; every angle is a linear function of spec.alpha / spec.beta.

## Last 0 attempts of family `F3`
- (none yet)

## DISCOVERY notes of all programs (last 0 of at most 30 lines)
- (none yet)

## Output
Write ONE program to `compress/programs/twelve/F3/001-<slug>.py` (docstring starting with `SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under `scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.
