# Task specification: `rishon` / `step`

## Task

Implement $U=U_B(\beta)\,U_E(\alpha)$ (electric layer first in the circuit) for the SU(2) **quantum link model** (two fermionic rishons per link, 6 link states; Report 5, `docs/METHODS-rishon.md`) on the plaquette with 8 outer links, in the 48-qubit Jordan-Wigner encoding, exactly (up to one global phase) on every one of the 1296 valid inner codes - which certifies all 38432 physical states (METHODS-rishon R6) - at $(\alpha,\beta)=(0.37,0.61)$ and, with the same gate skeleton (gate names and qubits; angles may differ), at (0.91, 0.23), (1.7, 1). Invalid codes are don't-care. Every ancilla must return to $|0\rangle$. Angles must be computed from the spec's `alpha`/`beta` (and the oracle), never typed in.

## Registers

### Encoding `rishon` (16 data + 32 outer qubits)

SU(2) quantum link model, two fermionic rishons per link, Jordan-Wigner with link-contiguous modes. Link l occupies qubits (4l, 4l+1, 4l+2, 4l+3) = (L1, L2, R1, R2); occupation bit 1 = mode occupied; colour 1 = up. Inner links: `b` = qubits (0..3), `r` = qubits (4..7), `t` = qubits (8..11), `l` = qubits (12..15).

| link type | bits L1 L2 R1 R2 | integer |
|---|---|---|
| A (both rishons at the start) | `1100` | 3 |
| B (both at the end) | `0011` | 12 |
| Q (one at each end) | `1010`, `0110`, `1001`, `0101` | 5, 6, 9, 10 |

The other 10 of 16 link patterns are unused (don't-care). 1296 valid inner codes (6^4 = 1296).

**Outer controls `o[0..31]`.** Outer link k occupies qubits (16+4k..19+4k); the near end (at the plaquette corner) is free (empty, full, colour 1, colour 2), the far end is fixed by the link type (A/B: empty/full; Q: colour 1). o0: (16..19) near end `R`, o1: (20..23) near end `R`, o2: (24..27) near end `L`, o3: (28..31) near end `R`, o4: (32..35) near end `L`, o5: (36..39) near end `L`, o6: (40..43) near end `R`, o7: (44..47) near end `L`. The target never changes the outer register; a circuit may neither write it nor read it (the evaluator rejects an outer read as `outer_read_unsupported`, METHODS-rishon R6, R10).

**Physical states.** 38432 Gauss-law (SU(2)) states: products of corner singlet tensors over the 48-qubit occupation basis; closed sector 4352; unphysical inputs are don't-care. Ancillas must return to |0>.

**State indexing.** Inner codes 0..1295 in sorted code order (the 6^4 = 1296 valid inner codes are the single-code input states of the evaluator, outer bits 0); `oracle --codec --state k` prints the code of state k and the link types of b, r, t, l.

**The outer register may be neither read nor written** (reading is not supported by the evaluator: `outer_read_unsupported`; writing is `writes_outer`); it is in the register because the machinery fixes `d` + `o`, and it counts in the key's qubit component (48 + ancillas).

## Target structure (exact)

$U_E^{\rm in}=\mathrm{diag}(e^{-i\frac{3}{4}\alpha\,\#Q})$ with $\#Q$ the number of inner links in a quartet state (`1010`, `0110`, `1001`, `0101`); $U_B^{\rm in}=\prod_{p=1}^{81}\exp\big(i\beta\kappa_p(|u_p\rangle\langle v_p|+{\rm h.c.})\big)$ with $\kappa\in\{1\ (\times32), 2\ (\times48), 4\sqrt2\ (\times1)\}$, 990 dark codes, real pair vectors with amplitudes in $\{\pm1, \pm\tfrac1{\sqrt2}, \pm\tfrac1{2}, \pm\tfrac1{4}\}$ supported on affine GF(2) subspaces; the 81 blocks commute. `get_encoding("rishon").bright_pairs()` returns them; `python -m su2plaq.rishon.compress.oracle --pairs`. The facts of `structure_facts()` with their trust level are listed in the proved-structure section below.

## Circuit model

Gates `cx cz h p rz s sdg t tdg x z` and macros `ccx ccz ch cp crx crz rccx swap` with costs (CX, T, rotations) from the builder table: ccx (6, 7, 0), rccx (3, 4, 0), ccz (6, 7, 0), swap (3, 0, 0), ch (1, 2, 0), crz (2, 0, 2), crx (2, 0, 2), cp (2, 0, 3), cz (1, 0, 0). `Builder.alloc/free` for clean ancillas; `Builder.mcx` for 3 or more controls ((k-2) rccx + ccx + (k-2) rccx; native mcx, mcrx, cu, unitary and measurement are rejected); at most 80 qubits in total; no measurement; emission-time classical computation is allowed (`su2plaq.compress.oracle`, `su2plaq.compress.spec.get_encoding("rishon")`, numpy).

## Correctness

`op_norm_error` = block error + leak amplitude + certified pruning bound must be at most 1e-10 after one global phase; `dropped_total` must be at most 1e-12 (**prune cap** = 0.01 x tolerance; measured on this task the sparse engine's pruning bound grows by about 2.1e-16 per `ccx` and 1.4e-15 per `rccx`, so the cap allows roughly 4800 `ccx` or 710 `rccx`; the uncompressed general circuit with `rccx` ladders is rejected as `pruning_bound` by this rule alone); Gauss residual of the outputs on 273 sampled physical states (17 closed + 256 seeded) at most 1e-10; identical skeleton at the three angle pairs; evaluation wall at most 300 s and at most 5000000 stored amplitudes; synthesised re-verification of the round's best at $\varepsilon=1e-06$ with $N_{\rm rot}\varepsilon+1e-09$. The evaluator is ground truth.

## Cost

Key $(\mathrm{CX},\,T_{\varepsilon},\,\mathrm{depth}_{\rm CT},\,\mathrm{qubits})$, lexicographic. $T_\varepsilon=T_{\rm fixed}+\sum_r T_r$ with each rotation $T_r$ measured with pygridsynth at $\varepsilon=1e-06$; estimate $3\log_2(1/\varepsilon)$ per rotation. MAP-Elites cells $(\lfloor8\log_2(\mathrm{CX}+1)\rfloor,\lfloor8\log_2(T_\varepsilon+1)\rfloor)$. Reference (round 0, measured by the evaluator, not typed here): the general circuit's row.

## Lean

Rotation angles of the form $(m_\alpha\alpha+m_\beta\beta+m_\gamma\sqrt2\beta)/d$, $d\le64$, make the circuit certifiable for all angles by the rishon three-angle checker (status `certified`); other emission-time angles give `n_a`. Informative only: Lean never changes validity.

## Proved structure (Lean)

Machine-checked facts about the problem; the numerical evaluator remains ground truth. Trust levels: `decide` = kernel-checked Lean theorem, `native` = compiled exact-arithmetic certificate, `numerical` = computed from the operators (not a Lean statement).

- `card_rishon_physical` = 38432 (proved by decide, Su2Plaq.card_rishon_physical) -- number of Gauss-law (SU(2)) states of the plaquette with 8 outer links
- `card_rishon_closed` = 4352 (proved by decide, Su2Plaq.card_rishon_closed) -- states with every outer link a singlet
- `card_inner_codes` = 1296 (proved by decide, Su2Plaq.Rishon.card_inner_codes) -- valid inner codes (6 link states on each of the 4 inner links)
- `jw_string_free` = True (proved by decide, Su2Plaq.Rishon.bilinear_string_free_8) -- Jordan-Wigner strings of other links cancel in every link bilinear: link operators act on their own 4 qubits only
- `corner_kernel_dims` = 81 (proved by decide, Su2Plaq.Rishon.corner_kernel_dims) -- for all corner end configurations the Gauss kernel dimension equals the SU(2) fusion count
- `ue_exact_all_codes` = True (proved by decide, Su2Plaq.Rishon.ue_exact_all_codes) -- the 12 electric gates map every valid inner code exactly to z^{-3 #Q}|code> for all alpha (exact Laurent arithmetic)
- `hb_bright_pairs` = {"n_pairs": 81, "kappa_multiset": {"1": 32, "2": 48, "4*sqrt2": 1}, "dark_codes": 990, "vectors": 162} (proved by native, lean/certs/rishon-hb-structure.lean) -- H_B^in = -sum_p kappa_p (|u_p><v_p| + h.c.) over commuting bright pairs; the other codes are dark (exact integer pairs a + b sqrt2)

Numerical structure (not proved in Lean):

- `heights_raising`: W (the plaquette trace) raises all four link heights by one; W^3 = 0
- `pair_supports`: supports of u and v: sizes 2^d on GF(2) affine subspaces of dimension d (all affine: True); largest support 16
- `amplitude_alphabet`: absolute amplitudes of the pair vectors: 1, 1/sqrt2, 1/2, 1/4
- `closed_bright_block`: the kappa = 4 sqrt2 pair is u = (vac_A + vac_B)/sqrt2, v = loop ~ W vac_A (checked: True); the closed 3x3 block lives on (vac_A, loop, vac_B)
- `inner_span_rank`: 1296 -- the inner components of the physical states span all 1296 inner codes (R6 item 1: inner-block soundness)
- `u1_sectors`: 431 -- distinct U(1) charge sectors of the physical states (corner occupation quartets)
- `prune_rates`: growth of the sparse engine's certified pruning bound per AND gate: ccx 2.1e-16, rccx 1.4e-15

## Tools

`python -m su2plaq.rishon.compress.run_candidate <program.py> --kind step --trial` (seconds; 64 inner codes, nominal angles, T estimate) or `--full`.
`python -m su2plaq.rishon.compress.oracle --kind step [--column j] [--element i j] [--codec [--state k]] [--pairs [--closed]] [--block]` prints the exact target (matrix column, element, codec, bright pairs, closed 3x3 block).

Program contract: ONE file `compress/programs/rishon/<family>/NNN-slug.py` whose docstring starts with `SUMMARY: ...` followed by at most 3 `DISCOVERY: ...` lines, with `FAMILY = "..."`, `PARENT = "..." | None` and `def build(spec) -> Builder`; imports: numpy, standard maths modules, qiskit and `su2plaq.compress.{oracle,builder,spec}` only.
