M9 and M10 fuzzy DONE (tags milestone-9, milestone-10; Reports 9 and 10): step 1862->199 CX inner-only (2150->295 with outer links), U_B 1718->151, link 36->12; unfinished: more U_B rounds (still improving), Lean per-circuit certificates (n_a), audit notes A1/A2; next: merge bundle on laptop per notes/merge-notes-fuzzy.md.

# STATUS — branch m9-fuzzy (48-core machine, fuzzy encoding M9/M10)

Last updated: 2026-11-06 (coordinator, fuzzy session). Laptop STATUS at branch point: `notes/STATUS-laptop-at-branch-point.md`.
Brief: `/home/digonto/Projects/su2qc-fuzzy-package/START_HERE.md` (6 h hard limit; clock in `~/fuzzy-start.txt`).

## Goal
M9: fuzzy gauge theory (arXiv:2308.05253v4) general one-Trotter-step circuit, verified, CNOT/T counts, Lean. M10 (compression) only if > 2 h remain after M9.

## Plan in force
prompts/300-fuzzy-m9-plan.md (locked acceptance-v8).

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
- 2026-11-06 (Digonto, chat): approved two locked-test fixes -> prompts/301: (1) O1 one-step plaquette = 0 only for order 1 (order 2 is O(alpha beta), 0.0348 at nominal r=0); (2) K1 electric dense 65536^2 check -> seeded-state check, tol 1e-10 unchanged.
- Known test costs: C1 ~18 min (test's own reference Gauss on 4^12 vacuum); S1 needs 68-135 GB per test -> run with -n 1.
- M10 ideation split into two proposers (one per unit: fuzzy_ub, fuzzy_link) because plan 302 has two compression units; family cap 4 kept across both.
- Env: ~/venvs/coding (uv, CPython 3.12.14), not conda (none on this host). See notes/merge-notes-fuzzy.md.
