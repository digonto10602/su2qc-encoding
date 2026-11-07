# Ideation brief: `rishon` / `step`

Read the task specification `compress/specs/rishon-step.md` and the structure facts `compress/specs/rishon-structure.json`; nothing else about previous solutions (no seeds, no archive).

Write `compress/ideation/rishon.md`: at most 5 families (`## F1`, ... headings), one datapath idea each (what the registers hold, which gates carry the weight, why it should beat a generic circuit), most promising first. Write scratch files only under `scratch/proposer/`. Do not write programs in this session.

## Rishon overrides (these win over `~/.claude/agents/proposer.md`, which describes the `twelve` encoding)
- Commands: `python -m su2plaq.rishon.compress.run_candidate <program.py> --kind step --trial` (seconds) and `--full` (all inner codes, three angle pairs, Gauss sample); the oracle: `python -m su2plaq.rishon.compress.oracle --kind step [--column j] [--element i j] [--codec [--state k]] [--pairs [--closed]] [--block]`. Do NOT use `su2plaq.compress.run_candidate` / `su2plaq.compress.oracle` with `--encoding`.
- **Outer qubits `o[16..47]` may be neither read nor written** (a gate on them is `outer_read_unsupported` / `writes_outer`, invalid). The target acts on the 16 data qubits; the outer register only counts in the key's qubit component.
- **A `--trial` result is not a validity verdict.** Trial checks only a seeded subset of the inner codes at the nominal angles with no Gauss sample; a wrong controlled rotation acting on few codes can pass it (reports/tests/215: most single-gate errors passed it). Only `--full` decides validity (all codes, three angle pairs with an identical skeleton, Gauss sample, prune cap): run it before you finish, and never conclude a design is correct from a trial `valid`.
- The prune cap (`dropped_total` <= 1e-12) is part of validity: see the Correctness section of the specification (prune budget: see Correctness); a program that is exact but over the cap is recorded as `pruning_bound` (invalid).
- Programs import only numpy / maths modules / qiskit / `su2plaq.compress.{oracle,builder,spec}` (`get_encoding("rishon")` gives the pairs, targets and codes); never `su2plaq.rishon.*`. Do not ship `.lean` lemma files (not checked for rishon).
- Structure facts (what Lean proved and what is only numerical): `compress/specs/rishon-structure.json` and the section 'Proved structure (Lean)' of the specification.
