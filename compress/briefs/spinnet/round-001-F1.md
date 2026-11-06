# Brief: `spinnet` / `step`, round 1, family `F1`

**Task.** Rewrite the parent to improve the key; return the complete program.

- Task specification: `compress/specs/spinnet-step.md`
- Proved structure (Lean): the section 'Proved structure (Lean)' of the specification (kernel-checked facts about the spin-network problem; there is no separate structure file)
- Check a draft: `python -m su2plaq.spinnet.loop candidate <program.py> --trial` (seconds), `--full` before you finish (`--order 2` for the second-order step); the oracle: `python -m su2plaq.spinnet.loop oracle ...`

## Parent
none: write a fresh program for this family (the seeds below are alternatives, not parents).

## Archive alternatives (paths and costs only)
- `compress/programs/spinnet/seed/001-spinnet_v2_pairs9.py` (entry `r00-seed-001`, family `seed`): CX 34, T_eps 832, depth_CT 1597, qubits 19; the vendored su2qc-trotter spinnet_v2 pairs9 skeleton for U_B (angles solved from K, route-B signs) behind our electric layer; every angle is a linear function of spec.alpha / spec.beta.
- `compress/programs/spinnet/seed/004-spinnet_v2_flags6.py` (entry `r00-seed-004`, family `seed`): CX 36, T_eps 658, depth_CT 1120, qubits 19; the vendored su2qc-trotter spinnet_v2 flags6 skeleton for U_B (angles solved from K, route-B signs) behind our electric layer; every angle is a linear function of spec.alpha / spec.beta.
- `compress/programs/spinnet/seed/003-spinnet_v2_flags5.py` (entry `r00-seed-003`, family `seed`): CX 42, T_eps 606, depth_CT 1009, qubits 19; the vendored su2qc-trotter spinnet_v2 flags5 skeleton for U_B (angles solved from K, route-B signs) behind our electric layer; every angle is a linear function of spec.alpha / spec.beta.

## Last 0 attempts of family `F1`
- (none yet)

## DISCOVERY notes of all programs (last 0 of at most 30 lines)
- (none yet)

## Output
Write ONE program to `compress/programs/spinnet/F1/001-<slug>.py` (docstring starting with `SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under `scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.
