# Task specification: `fuzzy_link` / `UE`

## Task

Implement the one-link kinetic block $U_{EK}(\alpha,\kappa_2)=\exp[-i(\tfrac\alpha2\mathcal K_1+\kappa_2\mathcal K_2)]$ of the fuzzy gauge theory (arXiv:2308.05253; METHODS-fuzzy F2, F9) exactly (up to one global phase) as a $16\times16$ unitary on the 4 link qubits, at $(\alpha,\kappa_2)=(0.37,0.61)$ and, with the same gate skeleton, at the alternate pairs. **`spec.beta` is $\kappa_2$** (the Trotter step uses $\kappa_2=r\alpha/2$; the three angle pairs are three independent $(\alpha,\kappa_2)$ points). No ancilla: do not call `alloc` (more than 4 qubits is rejected). Unphysical inputs do not exist: every code is physical.

## Registers

FUZZY unit `fuzzy_link` (fuzzy gauge theory, arXiv:2308.05253, METHODS-fuzzy F1-F2, F9): one link. Data register `d` = frame qubits (0,1,2,3) = (q4, q3, q2, q1) of the link. Target exp(-i(alpha/2 K1 + kappa2 K2)) with `spec.alpha` = alpha and **`spec.beta` = kappa2** (the Trotter step applies it to 12 links with kappa2 = r alpha/2). K1 = 3/2 - 1/4 (X2X4 - Y2Y4 + Z2Z4)(1 + Z1Z3), K2 = -X1X3 + Y1X2Y3X4 - Y1Y2Y3Y4 + Y1Z2Y3Z4 (qubit k = q_k), [K1, K2] = 0. In the Clifford frame cx(q1,q3) cx(q2,q4) h(q1) h(q2) both are diagonal sums of Z-strings (10 strings in total; see F9), so the block is one frame plus a phase polynomial; the baseline uses two CNOT ladders (36 CX). No ancilla.
Proposer commands (the fuzzy hook is installed by these wrappers; the plain `python -m su2plaq.compress.*` modules do not know the fuzzy units, so use the script): `python scripts/m10_round.py candidate <program.py> --encoding fuzzy_link --kind UE --trial|--full` (wraps `su2plaq.compress.run_candidate`), `python scripts/m10_round.py oracle --encoding fuzzy_link --kind UE [--column j] [--element i j]`. Programs import only `su2plaq.compress.{builder,oracle,spec}` and numpy.

## Circuit model

Gates `cx cz h p rz s sdg t tdg x z` and macros `ccx ccz ch cp crx crz rccx swap` with costs (CX, T, rotations): ccx (6, 7, 0), rccx (3, 4, 0), ccz (6, 7, 0), swap (3, 0, 0), ch (1, 2, 0), crz (2, 0, 2), crx (2, 0, 2), cp (2, 0, 3), cz (1, 0, 0). `Builder.alloc/free` for clean ancillas; `Builder.mcx` for 3 or more controls (native mcx, mcrx, cu, unitary and measurement are rejected); at most 4 qubits in total; emission-time classical computation (including oracle queries) is allowed.

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

`python scripts/m10_round.py candidate <program.py> --encoding fuzzy_link --kind UE --trial` (seconds; 64 physical inputs, nominal angles, T estimate) or `--full`.
`python scripts/m10_round.py oracle --encoding fuzzy_link --kind UE [--column j] [--element i j] [--codec] [--block o]` prints the exact target (matrix column, element, codec, outer block); programs may call `su2plaq.compress.oracle` and `numpy`, nothing else from the project.

Program contract: write ONE file `compress/programs/<encoding>/<family>/NNN-slug.py` whose docstring starts with `SUMMARY: ...` followed by at most 3 `DISCOVERY: ...` lines, with `FAMILY = "..."`, `PARENT = "..." | None` and `def build(spec) -> Builder`.
