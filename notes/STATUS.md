M9 fuzzy: setup done (env, Lean, baseline m0/m1 green), Hamiltonian decisions recorded (K_2 included, g^2/4); planner writing prompts/300 + tests/acceptance/m9; next: lock m9, then build loop.

# STATUS — branch m9-fuzzy (48-core machine, fuzzy encoding M9/M10)

Last updated: 2026-11-06 (coordinator, fuzzy session). Laptop STATUS at branch point: `notes/STATUS-laptop-at-branch-point.md`.
Brief: `/home/digonto/Projects/su2qc-fuzzy-package/START_HERE.md` (6 h hard limit; clock in `~/fuzzy-start.txt`).

## Goal
M9: fuzzy gauge theory (arXiv:2308.05253v4) general one-Trotter-step circuit, verified, CNOT/T counts, Lean. M10 (compression) only if > 2 h remain after M9.

## Plan in force
prompts/001 §3 M9 (until prompts/300 exists).

## Current milestone / step
M9 — planner (prompts/300, docs/METHODS-fuzzy.md, reports/research/300, tests/acceptance/m9).

## Open failures (attempt counters)
| Check | Builder attempts | Tester rounds w/o progress | Fixer runs | Notes |
|---|---|---|---|---|
| — | — | — | — | — |

## Decisions
- Numbers 300+ for prompts/reports on this branch. Branch m9-fuzzy off master 9b5443d.
- 2026-11-06 (Digonto, chat): target = Bedaque note refs/fuzzy/fuzzy-hamiltonian-digonto.pdf = paper Eqs. 34-37 INCLUDING kappa_2 K_2 (own circuit U_K; 48 qubits, no 3-qubit reduction). Electric normalisation g^2/4 on K_1 (Paulo Eq. 16, kappa_1 = alpha/2). Check report: scratch/fuzzy-hamiltonian-check.md (copied to reports/research by planner).
- Coordinator defaults (not yet confirmed by Digonto): kappa_2/kappa_1 not given in the note -> free parameter, nominal kappa_2 = kappa_1, also verify kappa_2 = 0; plaquette coupling per Eq. 16 (alpha_N = -2 beta, KS sign); note Eq. 3 (T_L on incoming) treated as typo -> T_L on outgoing links as in the paper; daggers per paper Eqs. 35/37.
- Env: ~/venvs/coding (uv, CPython 3.12.14), not conda (none on this host). See notes/merge-notes-fuzzy.md.
