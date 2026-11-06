# Ideation brief: `fuzzy_ub` / `UB`

Read the task specification `compress/specs/fuzzy_ub-UB.md` and nothing else about previous solutions (no seeds, no archive).
Proved structure (Lean): `compress/specs/fuzzy-structure.json` (machine-proved facts about the fuzzy units: counts, K1/K2 spectra; the same facts are in the section 'Proved structure (Lean)' of the specification).

Write `compress/ideation/fuzzy_ub.md`: at most 5 families, one datapath idea each (what the registers hold, which gates carry the weight, why it should beat a generic circuit), most promising first. Use the oracle (`python scripts/m10_round.py oracle --encoding fuzzy_ub --kind UB ...`) to look at the target; write scratch files only under `scratch/proposer/`. Do not write programs in this session.

## Fuzzy hook (M10)

Use `python scripts/m10_round.py candidate <program> --encoding fuzzy_ub --kind UB --trial|--full` instead of `python -m su2plaq.compress.run_candidate`, and `python scripts/m10_round.py oracle ...` instead of the oracle module. Programs import only `su2plaq.compress.{builder,oracle,spec}`, numpy, qiskit. Frame qubits 0..7 are the row qubits (see the specification); ancillas via `Builder.alloc`.
