# STATUS — su2qc-encoding

Last updated: 2026-11-04 (coordinator)

## Goal
Study truncations and qubit encodings of one SU(2) plaquette with 8 outer links
(12 links, 4 four-valent corners), following `refs/su2_plaquette_truncations_encodings.md`:
verify its counts, build the plaquette operator in the spin-network basis, then circuits
and gate counts per encoding. See `prompts/000-plaquette-starter-plan.md`.

## Plan in force
`prompts/000-plaquette-starter-plan.md` (starter; planner kickoff pending)

## Current milestone / step
Kickoff — planner to research methods, write plan 001 and the locked M1 acceptance tests.

## Open failures (attempt counters)
| Check | Builder attempts | Tester rounds w/o progress | Fixer runs | Notes |
|---|---|---|---|---|
| — | — | — | — | — |

## Decisions
- 2026-11-04 (Digonto): restart from the plaquette note; old 2×2-lattice work archived (tag `archive-2x2-lattice`), reference paper kept in `refs/`.
- 2026-11-04 (Digonto): reference script `refs/su2_plaquette_encodings.py` supplied by Digonto.
- Carried over, to confirm: Qiskit 2.5.2 / Aer 0.17.2 CPU; `pytest -n auto`; cost metric CNOT > depth > qubits.

## Known issues
- Note §5 register table: q-deformed row (16 at $j_{\max}=1/2$) contradicts its own bullet (12); spin-network row 20 vs bullet 16.
  The script's register sizes are a simple upper bound, not the minimum. See starter plan §5.

## Next action
Launch planner (kickoff) → on return: `acceptance-lock "prompts/001-..."`, reset counters, start M1 step 1 with `builder`.

## Log
- 2026-11-04: old work archived (commits 30acd44, 92a5b67, tag `archive-2x2-lattice`) and removed from the tree.
- 2026-11-04: `python3 -I refs/su2_plaquette_encodings.py` (numpy 2.5.2, 0.7 s): every number in note §5 reproduced.
