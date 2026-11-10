# Brief: `rishon` / `step`, round 1, family `F2`

**Task.** Rewrite the parent to improve the key; return the complete program.

- Task specification: `compress/specs/rishon-step.md`
- Structure facts: `compress/specs/rishon-structure.json`

## Rishon overrides (these win over `~/.claude/agents/proposer.md`, which describes the `twelve` encoding)
- Commands: `python -m su2plaq.rishon.compress.run_candidate <program.py> --kind step --trial` (seconds) and `--full` (all inner codes, three angle pairs, Gauss sample); the oracle: `python -m su2plaq.rishon.compress.oracle --kind step [--column j] [--element i j] [--codec [--state k]] [--pairs [--closed]] [--block]`. Do NOT use `su2plaq.compress.run_candidate` / `su2plaq.compress.oracle` with `--encoding`.
- **Outer qubits `o[16..47]` may be neither read nor written** (a gate on them is `outer_read_unsupported` / `writes_outer`, invalid). The target acts on the 16 data qubits; the outer register only counts in the key's qubit component.
- **A `--trial` result is not a validity verdict.** Trial checks only a seeded subset of the inner codes at the nominal angles with no Gauss sample; a wrong controlled rotation acting on few codes can pass it (reports/tests/215: most single-gate errors passed it). Only `--full` decides validity (all codes, three angle pairs with an identical skeleton, Gauss sample, prune cap): run it before you finish, and never conclude a design is correct from a trial `valid`.
- The prune cap (`dropped_total` <= 1e-12) is part of validity: see the Correctness section of the specification (prune budget: see Correctness); a program that is exact but over the cap is recorded as `pruning_bound` (invalid).
- Programs import only numpy / maths modules / qiskit / `su2plaq.compress.{oracle,builder,spec}` (`get_encoding("rishon")` gives the pairs, targets and codes); never `su2plaq.rishon.*`. Do not ship `.lean` lemma files (not checked for rishon).
- Structure facts (what Lean proved and what is only numerical): `compress/specs/rishon-structure.json` and the section 'Proved structure (Lean)' of the specification.

## Parent
none: write a fresh program for this family (the seeds below are alternatives, not parents).

## Archive alternatives (paths and costs only)
- `compress/programs/rishon/seed/000-general.py` (entry `r00-seed-000`, family `seed`): CX 10102, T_eps 20650, depth_CT 35639, qubits 58; the reference circuit of the rishon encoding (step) expressed through the Builder; every angle is a linear function of spec.alpha / spec.beta.

## Last 0 attempts of family `F2`
- (none yet)

## DISCOVERY notes of all programs (last 0 of at most 30 lines)
- (none yet)

## Output
Write ONE program to `compress/programs/rishon/F2/001-<slug>.py` (docstring starting with `SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under `scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.
