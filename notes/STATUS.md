# STATUS — su2qc-encoding

Last updated: 2026-11-04 (coordinator)

## Goal
One SU(2) plaquette with 8 outer links (12 links, 4 four-valent corners), $j_{\max}=1/2$.
For each of five encodings, in order — (1) Paulo's 12-qubit, (2) spin network, (3) rishon,
(4) loop-string-hadron, (5) fuzzy — build in Qiskit 2.5.2 / Aer 0.17.2 the one-Trotter-step
circuits $U_E(\alpha)=e^{-i\alpha H_E}$, $U_B(\beta)=e^{-i\beta H_B}$, verify on every Gauss-law
state (433 physical states), count CNOT and T gates → report; then compress with a
Gu-et-al-style LLM loop (in-session proposer agents, deterministic evaluator) → report.
Full plan: `prompts/001-plaquette-five-encodings-plan.md`.

## Plan in force
`prompts/001-plaquette-five-encodings-plan.md` (approved by Digonto 2026-11-04; chat-derived).
Planner kickoff → `prompts/002-…` with researched formulas, `docs/METHODS.md`, locked
`tests/acceptance/m0/ m1/ m2/`.

## Current milestone / step
Kickoff — planner running (research + prompts/002 + METHODS + locked M0–M2 acceptance tests).

## Open failures (attempt counters)
| Check | Builder attempts | Tester rounds w/o progress | Fixer runs | Notes |
|---|---|---|---|---|
| — | — | — | — | — |

## Decisions
- 2026-11-04 (Digonto): restart from the plaquette note; old 2×2-lattice work archived (tag `archive-2x2-lattice`), reference paper kept in `refs/`.
- 2026-11-04 (Digonto): "12-qubit" = Paulo's definition (3 qubits per inner link, $(j,m,m')$); the circuit changes only the 12 inner qubits but may read the outer links as controls; correctness on all 433 physical states. NOT the note's one-label-per-link register.
- 2026-11-04 (Digonto): order of work = per encoding (general circuit → report → compress → report), 12-qubit first.
- 2026-11-04 (Digonto): compression proposer = Claude Code agents in-session; coordinator creates the `proposer` agent role and guard-hook entry in `~/.claude` itself (plan §3 step 2.0).
- Plan §1/§8 defaults: Paulo Eq. 16 normalisation; nominal angles $(\alpha,\beta)=(0.37,0.61)$ + alternates; $\varepsilon=10^{-6}$ in the loop; cost order CNOT > T > depth > qubits; `pytest -n auto`; outer electric phases reported as a separate row.
- T-count rule: $T_{\rm total}=T_{\rm fixed}+\sum_{\rm rot}T_r(\varepsilon)$, $T_r\approx3\log_2(1/\varepsilon)$ (Ross–Selinger), measured with pygridsynth; the "$+3\ln\varepsilon$" form was wrong (sign, base, multiplicity).

## Known issues
- Note §5 register table vs its bullets (q-deformed 16 vs 12; spin network 20 vs 16): the script's register sizes are upper bounds. Not blocking (q-deformed not in scope).
- Paulo (Fig. 2) vs note §4.2 on whether the spin-network plaquette depends on the outer links: settled numerically by acceptance test M0-X5 (expected: Paulo right in the (inner|outer) pairing).

## Next action
Planner (kickoff) running since 2026-11-04 → on return: review `prompts/002-…`, run
`~/.claude/bin/acceptance-lock "prompts/002-…"`, reset counters, start M0 step 0.1 with `builder`.

## Log
- 2026-11-04: old work archived (commits 30acd44, 92a5b67, tag `archive-2x2-lattice`) and removed from the tree.
- 2026-11-04: `python3 -I refs/su2_plaquette_encodings.py` (numpy 2.5.2, 0.7 s): every number in note §5 reproduced.
- 2026-11-04: exploration of Paulo's notes, Gu et al., and sibling projects (su2qc-trotter, su2qc-skqd, su2qc-paulo-code, su2qc-qcadvantage); plan 001 designed and approved.
