# Task specification: `fuzzy_ub` / `UB`

## Task

Implement $U_B(\beta)=\exp(+2i\beta\,\square)$ of the fuzzy-gauge-theory plaquette (arXiv:2308.05253; METHODS-fuzzy F5) exactly (up to one global phase) on the 8 row qubits, i.e. a $256\times256$ unitary on all 256 computational codes (all are physical), at $\beta=0.61$ and, with the same gate skeleton, at the alternate pairs. Every ancilla must return to $|0\rangle$. Unphysical inputs do not exist: every code is physical.

## Registers

FUZZY unit `fuzzy_ub` (fuzzy gauge theory, arXiv:2308.05253, METHODS-fuzzy F1-F5): the row block of the plaquette operator of the 4-link plaquette. Data register `d` = 8 row qubits; frame qubit 2l = q2 and 2l+1 = q1 of link l (l = 0,1,2,3 = b, r, t, l), registers `row_b=[1,0]`, `row_r=[3,2]`, `row_t=[5,4]`, `row_l=[7,6]` (most significant first). Row index of a code is sum_l (2 q1^l + q2^l) 4^l. The target is the exact 256 x 256 unitary exp(+2 i beta square) with `spec.beta` = beta (`spec.alpha` is unused). Only the row qubits carry data: the column qubits (q3, q4) are not touched by the plaquette. The known structure: parity frame (3 CNOTs q1^b -> q1^{r,t,l}); the operator splits into 8 parity sectors, each Clifford-conjugate to a rotation R_x(-4 beta sigma) with singular values {16, 0^12}, {4, 0^15} or {1^16}; the baseline spends ~1700 CX on one 3-controlled AND and Clifford frames per sector. Ancillas: up to 32 clean ancillas, `Builder.alloc/free`.
Proposer commands (the fuzzy hook is installed by these wrappers; the plain `python -m su2plaq.compress.*` modules do not know the fuzzy units, so use the script): `python scripts/m10_round.py candidate <program.py> --encoding fuzzy_ub --kind UB --trial|--full` (wraps `su2plaq.compress.run_candidate`), `python scripts/m10_round.py oracle --encoding fuzzy_ub --kind UB [--column j] [--element i j]`. Programs import only `su2plaq.compress.{builder,oracle,spec}` and numpy. Background: docs/METHODS-fuzzy.md F5, F9.

## Circuit model

Gates `cx cz h p rz s sdg t tdg x z` and macros `ccx ccz ch cp crx crz rccx swap` with costs (CX, T, rotations): ccx (6, 7, 0), rccx (3, 4, 0), ccz (6, 7, 0), swap (3, 0, 0), ch (1, 2, 0), crz (2, 0, 2), crx (2, 0, 2), cp (2, 0, 3), cz (1, 0, 0). `Builder.alloc/free` for clean ancillas; `Builder.mcx` for 3 or more controls (native mcx, mcrx, cu, unitary and measurement are rejected); at most 40 qubits in total; emission-time classical computation (including oracle queries) is allowed.

## Correctness

The combined error bound `op_norm_error` = block error + leak amplitude (+ certified simulator pruning bound) must be at most 1e-10 on the physical block after one global phase, (no per-unit Gauss check: every code is physical and the targets commute with the Gauss generators); the skeleton must be identical at the three angle pairs; evaluation wall at most 300 s and at most 5000000 stored amplitudes. The circuit you submit is exact-angle; its Clifford+T synthesis (pygridsynth at $\varepsilon=1e-06$) is re-verified separately with both tolerances $N_{\rm rot}\varepsilon+1e-09$ (the triangle inequality over the $N_{\rm rot}$ synthesised rotations). The simulator's certified pruning bound (`dropped_total`) must be at most 0.01 times the error tolerance (programs that keep hundreds of tiny amplitudes alive are rejected as `pruning_bound`). The evaluator is ground truth.

## Cost

Key $(\mathrm{CX},\,T_{\varepsilon},\,\mathrm{depth}_{\rm CT},\,\mathrm{qubits})$, lexicographic. $T_\varepsilon=T_{\rm fixed}+\sum_r T_r$ with each rotation $T_r$ measured with pygridsynth at $\varepsilon=1e-06$; estimate $3\log_2(1/\varepsilon)$ per rotation. MAP-Elites cells $(\lfloor8\log_2(\mathrm{CX}+1)\rfloor,\lfloor8\log_2(T_\varepsilon+1)\rfloor)$.

## Proved structure (Lean)

Machine-checked facts about the problem (Lean 4); the numerical evaluator remains ground truth.

- `card_isolated_plaquette` = 50 (proved by decide, Su2Plaq.Fuzzy.count_isolated_plaquette) -- physical states of the isolated fuzzy plaquette
- `card_outer_vacuum` = 12800 (proved by decide, Su2Plaq.Fuzzy.count_outer_vacuum) -- outer-vacuum sector
- `card_fixed_far_end` = 101197218 (proved by decide, Su2Plaq.Fuzzy.count_fixed_far_end) -- twelve links, far end of each outer link fixed
- `card_far_end_weighted` = 6767266914 (proved by decide, Su2Plaq.Fuzzy.count_far_end_weighted) -- far-end weighted count
- `K1_spectrum` = {0^2, (3/2)^8, 2^6} (proved by decide, Su2Plaq.Fuzzy.K1_spectrum) -- link kinetic operator K1 (fuzzy_link unit)
- `K2_spectrum` = {-4, (-2)^4, 0^6, 2^4, 4} (proved by decide, Su2Plaq.Fuzzy.K2_spectrum) -- link kinetic operator K2 (fuzzy_link unit); [K1, K2] = 0 (K1_K2_commute)

## Tools

`python scripts/m10_round.py candidate <program.py> --encoding fuzzy_ub --kind UB --trial` (seconds; 64 physical inputs, nominal angles, T estimate) or `--full`.
`python scripts/m10_round.py oracle --encoding fuzzy_ub --kind UB [--column j] [--element i j] [--codec] [--block o]` prints the exact target (matrix column, element, codec, outer block); programs may call `su2plaq.compress.oracle` and `numpy`, nothing else from the project.

Program contract: write ONE file `compress/programs/<encoding>/<family>/NNN-slug.py` whose docstring starts with `SUMMARY: ...` followed by at most 3 `DISCOVERY: ...` lines, with `FAMILY = "..."`, `PARENT = "..." | None` and `def build(spec) -> Builder`.
