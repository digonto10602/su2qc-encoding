M9 fuzzy: setup done (env, Lean, baseline m0/m1 green); planner run for M9 plan + locked tests in progress; next: lock m9, then build loop.

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
- Env: ~/venvs/coding (uv, CPython 3.12.14), not conda (none on this host). See notes/merge-notes-fuzzy.md.
