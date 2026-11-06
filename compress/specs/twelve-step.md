# Task specification: `twelve` / `step`

## Task

Implement $U=U_B(\beta)\,U_E(\alpha)$ (electric layer first in the circuit) for the SU(2) plaquette at $j_{\max}=\tfrac12$ in the 12-qubit encoding, exactly (up to one global phase) on every one of the 433 physical states, at $(\alpha,\beta)=(0.37,0.61)$ and, with the same gate skeleton (gate names and qubits; angles may differ), at (0.91, 0.23), (1.7, 1). Unphysical inputs are don't-care. Every ancilla you allocate must be returned to $|0\rangle$ on physical inputs. Angles must be computed from the spec's `alpha`/`beta` (and the oracle), never typed in.

## Registers

### Encoding `twelve` (12 data + 16 outer qubits)

**Data register `d[0..11]`.** Inner link l in {b, r, t, l} occupies qubits (3l, 3l+1, 3l+2) = (q_m', q_m, q_j) (`b` = qubits (0, 1, 2), `r` = qubits (3, 4, 5), `t` = qubits (6, 7, 8), `l` = qubits (9, 10, 11)). Codes are written as bits q_j q_m q_m' (q_m' is bit 0 of the link code):

| Paulo state | q_j q_m q_m' | meaning |
|---|---|---|
| `0` | 000 | (j=0) |
| `++` | 111 | ++ |
| `+-` | 110 | +- |
| `-+` | 101 | -+ |
| `--` | 100 | -- |

The codes 001, 010, 011 are unused (don't-care). 625 valid inner codes (5^4 = 625); the inner register is the Paulo basis |m m'> = s(m)s(m')|1/2,-m,-m'>_CG.

**Outer controls `o[0..15]`.** Outer link k (0..7) occupies qubits (12+2k, 13+2k) = (q_m, q_j): j = 0 -> 00; j = 1/2 -> q_j = 1 and q_m = 1 for m_near = +, 0 for m_near = - (m_near is the first Paulo label for a link that starts at its corner, the second for one that ends there; the far-end label is fixed to -). o0: (12, 13) near end `R`, o1: (14, 15) near end `R`, o2: (16, 17) near end `L`, o3: (18, 19) near end `R`, o4: (20, 21) near end `L`, o5: (22, 23) near end `L`, o6: (24, 25) near end `R`, o7: (26, 27) near end `L`. The target never changes the outer register; a circuit may read it (diagonal gates on those qubits only), never write it.

**Physical states.** 433 Gauss-law (gauge-invariant) states, superpositions of inner codes entangled with the outer register; unphysical inputs are don't-care. Ancillas must return to |0> on physical inputs.

## Circuit model

Gates `cx cz h p rz s sdg t tdg x z` and macros `ccx ccz ch cp crx crz rccx swap` with costs (CX, T, rotations): ccx (6, 7, 0), rccx (3, 4, 0), ccz (6, 7, 0), swap (3, 0, 0), ch (1, 2, 0), crz (2, 0, 2), crx (2, 0, 2), cp (2, 0, 3), cz (1, 0, 0). `Builder.alloc/free` for clean ancillas; `Builder.mcx` for 3 or more controls (native mcx, mcrx, cu, unitary and measurement are rejected); at most 60 qubits in total; emission-time classical computation (including oracle queries) is allowed.

## Correctness

The combined error bound `op_norm_error` = block error + leak amplitude (+ certified simulator pruning bound) must be at most 1e-10 on the physical block after one global phase, and the Gauss residual of the outputs at most 1e-10; the skeleton must be identical at the three angle pairs; evaluation wall at most 300 s and at most 5000000 stored amplitudes. The circuit you submit is exact-angle; its Clifford+T synthesis (pygridsynth at $\varepsilon=1e-06$) is re-verified separately with both tolerances $N_{\rm rot}\varepsilon+1e-09$ (the triangle inequality over the $N_{\rm rot}$ synthesised rotations). The simulator's certified pruning bound (`dropped_total`) must be at most 0.01 times the error tolerance (programs that keep hundreds of tiny amplitudes alive are rejected as `pruning_bound`). The evaluator is ground truth.

## Cost

Key $(\mathrm{CX},\,T_{\varepsilon},\,\mathrm{depth}_{\rm CT},\,\mathrm{qubits})$, lexicographic. $T_\varepsilon=T_{\rm fixed}+\sum_r T_r$ with each rotation $T_r$ measured with pygridsynth at $\varepsilon=1e-06$; estimate $3\log_2(1/\varepsilon)$ per rotation. MAP-Elites cells $(\lfloor8\log_2(\mathrm{CX}+1)\rfloor,\lfloor8\log_2(T_\varepsilon+1)\rfloor)$.

## Proved structure (Lean)

pending: `compress/lean/structure.json` has not been generated yet.

## Tools

`python -m su2plaq.compress.run_candidate <program.py> --encoding twelve --kind step --trial` (seconds; 64 physical inputs, nominal angles, T estimate) or `--full`.
`python -m su2plaq.compress.oracle --encoding twelve --kind step [--column j] [--element i j] [--codec] [--block o]` prints the exact target (matrix column, element, codec, outer block); programs may call `su2plaq.compress.oracle` and `numpy`, nothing else from the project.

Program contract: write ONE file `compress/programs/<encoding>/<family>/NNN-slug.py` whose docstring starts with `SUMMARY: ...` followed by at most 3 `DISCOVERY: ...` lines, with `FAMILY = "..."`, `PARENT = "..." | None` and `def build(spec) -> Builder`.
