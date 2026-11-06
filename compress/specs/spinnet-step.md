# Task specification: `spinnet` / `step`

## Task

Implement $U=U_B(\beta)\,U_E(\alpha)$ (electric layer first in the circuit) for the SU(2) plaquette at $j_{\max}=\tfrac12$ in the 8-qubit encoding, exactly (up to one global phase) on every one of the 433 physical states, at $(\alpha,\beta)=(0.37,0.61)$ and, with the same gate skeleton (gate names and qubits; angles may differ), at (0.91, 0.23), (1.7, 1). Unphysical inputs are don't-care. Every ancilla you allocate must be returned to $|0\rangle$ on physical inputs. Angles must be computed from the spec's `alpha`/`beta` (and the oracle), never typed in.

## Registers

### Encoding `spinnet` (8 data + 8 outer qubits, basis encoding)

**Data register `d[0..7]`.** Qubits 0-3 = inner links b, r, t, l (bit 1 <=> j = 1/2, bit 0 <=> j = 0); qubits 4-7 = corner qubits c_0..c_3 (bit 1 <=> J_c = 1, bit 0 <=> J_c in {0, 1/2}).  Code of a label = sum_l [j_l = 1/2] 2^l + sum_c [J_c = 1] 2^(4+c) + sum_k [j_(o_k) = 1/2] 2^(8+k).

**Outer controls `o[0..7]`.** Outer link o_k (METHODS section 1 order) at qubit 8 + k: o0 = qubit 8, o1 = qubit 9, o2 = qubit 10, o3 = qubit 11, o4 = qubit 12, o5 = qubit 13, o6 = qubit 14, o7 = qubit 15.  A circuit may read them (controls), never write them.

**Corner rule.** A corner qubit is meaningful only when all four links at the corner are 1/2: J_c = 1 needs T(1/2, 1/2) = {0, 1} on both the inner and the outer side.  Every corner therefore has a corner bit 1 only with its four links 1/2, the label -> code map is injective, and the admissible J's of a corner never contain both 0 and 1/2.

**Physical states.** 433 gauge-invariant states, each a distinct computational-basis code (unit vectors).  The valid data codes are the 47 inner labels (16 bright: no corner bit; 31 dark); the bright codes are paired by the four-link flip (code ^ 0b1111).  Other data patterns are don't-care; valid-data codes whose outer pattern does not fuse (11 599) are decoded to an orthogonal product state with Gauss residual >= 1/2 so the Gauss check sees any leak.

**Gauge.** The target is route B (6j); route A differs by the real diagonal gauge D = +-1 of `gauge_align` (64 minus signs, residual 2.7e-15); the decoded vector of code k is D_k times the route-A state, so decoded outputs are compared with the route-B target directly.  The sign of beta is a basis-sign convention at j_max = 1/2.

| data code (bits 7..0) | links (b r t l = bits 3..0) | corners (bits 7..4) | class |
|---|---|---|---|
| `00000000` | 0000 | 0000 | bright |
| `00000001` | 0001 | 0000 | bright |
| `00000010` | 0010 | 0000 | bright |
| `00000011` | 0011 | 0000 | bright |
| `00000100` | 0100 | 0000 | bright |
| `00000101` | 0101 | 0000 | bright |
| `00000110` | 0110 | 0000 | bright |
| `00000111` | 0111 | 0000 | bright |
| `00001000` | 1000 | 0000 | bright |
| `00001001` | 1001 | 0000 | bright |
| `00001010` | 1010 | 0000 | bright |
| `00001011` | 1011 | 0000 | bright |
| `00001100` | 1100 | 0000 | bright |
| `00001101` | 1101 | 0000 | bright |
| `00001110` | 1110 | 0000 | bright |
| `00001111` | 1111 | 0000 | bright |
| `00011001` | 1001 | 0001 | dark |
| `00011011` | 1011 | 0001 | dark |
| `00011101` | 1101 | 0001 | dark |
| `00011111` | 1111 | 0001 | dark |
| `00100011` | 0011 | 0010 | dark |
| `00100111` | 0111 | 0010 | dark |
| `00101011` | 1011 | 0010 | dark |
| `00101111` | 1111 | 0010 | dark |
| `00111011` | 1011 | 0011 | dark |
| `00111111` | 1111 | 0011 | dark |
| `01000110` | 0110 | 0100 | dark |
| `01000111` | 0111 | 0100 | dark |
| `01001110` | 1110 | 0100 | dark |
| `01001111` | 1111 | 0100 | dark |
| `01011111` | 1111 | 0101 | dark |
| `01100111` | 0111 | 0110 | dark |
| `01101111` | 1111 | 0110 | dark |
| `01111111` | 1111 | 0111 | dark |
| `10001100` | 1100 | 1000 | dark |
| `10001101` | 1101 | 1000 | dark |
| `10001110` | 1110 | 1000 | dark |
| `10001111` | 1111 | 1000 | dark |
| `10011101` | 1101 | 1001 | dark |
| `10011111` | 1111 | 1001 | dark |
| `10101111` | 1111 | 1010 | dark |
| `10111111` | 1111 | 1011 | dark |
| `11001110` | 1110 | 1100 | dark |
| `11001111` | 1111 | 1100 | dark |
| `11011111` | 1111 | 1101 | dark |
| `11101111` | 1111 | 1110 | dark |
| `11111111` | 1111 | 1111 | dark |

## Circuit model

Gates `cx cz h p rz s sdg t tdg x z` and macros `ccx ccz ch cp crx crz rccx swap` with costs (CX, T, rotations): ccx (6, 7, 0), rccx (3, 4, 0), ccz (6, 7, 0), swap (3, 0, 0), ch (1, 2, 0), crz (2, 0, 2), crx (2, 0, 2), cp (2, 0, 3), cz (1, 0, 0). `Builder.alloc/free` for clean ancillas; `Builder.mcx` for 3 or more controls (native mcx, mcrx, cu, unitary and measurement are rejected); at most 48 qubits in total; emission-time classical computation (including oracle queries) is allowed.

## Correctness

The combined error bound `op_norm_error` = block error + leak amplitude (+ certified simulator pruning bound) must be at most 1e-10 on the physical block after one global phase, and the Gauss residual of the outputs at most 1e-10; the skeleton must be identical at the three angle pairs; evaluation wall at most 300 s and at most 5000000 stored amplitudes. The circuit you submit is exact-angle; its Clifford+T synthesis (pygridsynth at $\varepsilon=1e-06$) is re-verified separately with both tolerances $N_{\rm rot}\varepsilon+1e-09$ (the triangle inequality over the $N_{\rm rot}$ synthesised rotations). The simulator's certified pruning bound (`dropped_total`) must be at most 0.01 times the error tolerance (programs that keep hundreds of tiny amplitudes alive are rejected as `pruning_bound`). The evaluator is ground truth.

## Cost

Key $(\mathrm{CX},\,T_{\varepsilon},\,\mathrm{depth}_{\rm CT},\,\mathrm{qubits})$, lexicographic. $T_\varepsilon=T_{\rm fixed}+\sum_r T_r$ with each rotation $T_r$ measured with pygridsynth at $\varepsilon=1e-06$; estimate $3\log_2(1/\varepsilon)$ per rotation. MAP-Elites cells $(\lfloor8\log_2(\mathrm{CX}+1)\rfloor,\lfloor8\log_2(T_\varepsilon+1)\rfloor)$.

## Proved structure (Lean)

Machine-checked facts about the problem (Lean 4, kernel-checked by `decide`); the numerical evaluator remains ground truth. Here K is the real symmetric coupling of the 47 admissible data codes, U_B = exp(-i beta K) acts on the data register, and a code is *bright* when its four corner bits are 0, *dark* otherwise.

- `card_inner_labels` = 47 (proved by decide, Su2Plaq.SpinNet.card_inner_labels) -- number of inner labels = admissible data codes (4 link bits + 4 corner bits)
- `card_bright_labels` = 16 (proved by decide, Su2Plaq.SpinNet.card_bright_labels) -- inner labels with no corner bit set (the codes K acts on)
- `card_dark_labels` = 31 (proved by decide, Su2Plaq.SpinNet.card_dark_labels) -- inner labels with a corner bit set (K = 0 on them)
- `card_bright_pairs` = 8 (proved by decide, Su2Plaq.SpinNet.card_bright_pairs) -- bright codes come in pairs y <-> y xor 0b1111 (K couples only the two members)
- `card_states_spinnet` = 433 (proved by decide, Su2Plaq.SpinNet.card_states_spinnet) -- physical states = distinct computational-basis codes y + 256 o
- `mult_two` = 16 (proved by decide, Su2Plaq.SpinNet.mult_two) -- states of the vacuum pair 0000 <-> 1111, |K| = 2 (multiplicity of the eigenvalues -2 and +2)
- `mult_one` = 96 (proved by decide, Su2Plaq.SpinNet.mult_one) -- states of the six pairs with |K| = 1 (multiplicity of the eigenvalues -1 and +1)
- `mult_half` = 16 (proved by decide, Su2Plaq.SpinNet.mult_half) -- states of the alternating pair 0101 <-> 1010, |K| = 1/2 (multiplicity of -1/2 and +1/2)
- `spectrum_multiplicities` = {-2: 16, -1: 96, -0.5: 16, 0: 177, 0.5: 16, 1: 96, 2: 16} (eigenvalue: multiplicity) (proved by decide, Su2Plaq.SpinNet.eig_mult) -- multiplicity of each eigenvalue of H_B (= the spectrum of K block by block) on the 433 states, as [eigenvalue, multiplicity]
- `couplings_2k` = {2K = -4: 1, 2K = 2: 6, 2K = -1: 1, 2K = 0: 31} (proved by decide, Su2Plaq.SpinNet.coupling_from_6j) -- 2K from the Racah 6j symbols on all 47 inner codes; the map is 2K -> number of bright pairs with that coupling ('0': number of dark codes, K = 0). K = -2 (0000<->1111), -1/2 (0101<->1010), +1 (six pairs)
- `ub_exact_semantics` = True (proved by decide, Su2Plaq.SpinNet.ub_exact_all_codes) -- the exact semantics of the 48-gate U_B circuit equals exp(-i beta K) of every valid inner code, for all beta

## Tools

`python -m su2plaq.spinnet.loop candidate <program.py> --trial` (seconds; 64 physical inputs, nominal angles, T estimate) or `--full` (`--order 2` for the second-order step).
`python -m su2plaq.spinnet.loop oracle [--column j] [--element i j] [--codec] [--block o]` prints the exact target (matrix column, element, codec, outer block); programs may call `su2plaq.compress.oracle` and `numpy`, nothing else from the project.

Program contract: write ONE file `compress/programs/<encoding>/<family>/NNN-slug.py` whose docstring starts with `SUMMARY: ...` followed by at most 3 `DISCOVERY: ...` lines, with `FAMILY = "..."`, `PARENT = "..." | None` and `def build(spec) -> Builder`.
