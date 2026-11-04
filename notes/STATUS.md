# STATUS — su2qc-encoding

Last updated: 2026-11-02 (coordinator)

## Goal
Compressed time-evolution circuits for SU(2) lattice gauge theory on a 2×2 periodic lattice,
cases C1 pure gauge, C2 + fermions, C3 + static charges, C4 + both, across the 23 encodings.
See `prompts/000-starter-plan.md`.

## Plan in force
`prompts/000-starter-plan.md` (starter; planner kickoff pending)

## Current milestone / step
Kickoff — planner to research methods, write the plan and the locked acceptance tests.

## Open failures (attempt counters)
| Check | Builder attempts | Tester rounds w/o progress | Fixer runs | Notes |
|---|---|---|---|---|
| — | — | — | — | — |

## Decisions (from chat, 2026-11-02)
- Lattice: 2×2 sites, periodic (4 sites, 8 links, 4 plaquettes).
- Charges: static SU(2) color sources.
- Cost metric: CNOT count, then depth, then qubits.
- Equivalence: own-model exact + shared observable checks; inapplicable encodings justified.
- Framework: circuits in Qiskit 2.5.2 / Aer 0.17.2 (CPU only); tests in parallel (`pytest -n auto`, pytest-xdist 3.8.0 installed 2026-11-02; joblib process pools).

## Next action
Planner (kickoff) running → on return: `acceptance-lock "prompts/001-..."`, reset counters, start M1 step 1 with `builder`.

## Log
- 2026-11-02: project created, git init, starter plan 000 written.
- 2026-11-02: Digonto: build circuits in Qiskit, test with parallelization → pytest-xdist installed, added to 000 §2.5.
- 2026-11-02: planner kickoff launched.
