# Task specification: `lsh` / `step`

## Task

Implement $U=U_B(\beta)\,U_E(\alpha)$ (electric layer first in the circuit) for the SU(2) plaquette at $j_{\max}=\tfrac12$ in the 12-qubit encoding, exactly (up to one global phase) on every one of the 433 physical states, at $(\alpha,\beta)=(0.37,0.61)$ and, with the same gate skeleton (gate names and qubits; angles may differ), at (0.91, 0.23), (1.7, 1). Unphysical inputs are don't-care. Every ancilla you allocate must be returned to $|0\rangle$ on physical inputs. Angles must be computed from the spec's `alpha`/`beta` (and the oracle), never typed in.

## Registers

### Encoding `lsh` (12 data + 12 outer qubits, basis encoding)

Loop-string-hadron (LSH) loop numbers on the point-split plaquette (8 trivalent sites, (inner | outer) pairing). **Data register `d[0..11]`**: 'in' site of corner c at qubits 3c, 3c+1, 3c+2 = (l_pn, l_nv, l_vp), loop numbers between the previous inner link p, the next inner link n (loop order b, r, t, l) and the virtual link v. **Outer controls `o[0..11]`**: 'out' site of corner c at qubits 12+3c.. = (l_12, l_2v, l_v1) for its two outer links; read-only.  Fluxes: N_p = l_vp + l_pn, N_n = l_pn + l_nv, N_v = l_nv + l_vp; spin = N/2.

**Validity.** Site codes 000, 001, 010, 100, 110 (bits l_31 l_23 l_12; flux at most 1 on physical links); Abelian Gauss law: the flux of every inner link and every virtual link read from its two ends agrees.  433 physical states, each one computational-basis code; 47 valid data codes (16 bright, 31 dark = a site in 110, i.e. J = 1).  The plaquette moves every bright site 000 <-> 001 or 010 <-> 100 and never reads the outer register.  Other data patterns are don't-care; data-valid codes that break the Abelian Gauss law on a virtual link are decoded to an orthogonal product state with Gauss residual >= 1/2.

**Gauge.** Target = the LSH operator (equal to the 6j route-B operator entry by entry); route A differs by the real diagonal gauge of `gauge_align` (64 minus signs, residual 8.9e-16).

| data code (bits 11..0) | sites c0 c1 c2 c3 (each l_vp l_nv l_pn) | class |
|---|---|---|
| `000000000000` | 000 000 000 000 | bright |
| `000000100010` | 010 100 000 000 | bright |
| `000100001010` | 010 001 100 000 | bright |
| `000100010000` | 000 010 100 000 | bright |
| `000100110010` | 010 110 100 000 | dark |
| `001001001001` | 001 001 001 001 | bright |
| `001001001110` | 110 001 001 001 | dark |
| `001001010100` | 100 010 001 001 | bright |
| `001001110001` | 001 110 001 001 | dark |
| `001001110110` | 110 110 001 001 | dark |
| `001010000100` | 100 000 010 001 | bright |
| `001010100001` | 001 100 010 001 | bright |
| `001010100110` | 110 100 010 001 | dark |
| `001110001001` | 001 001 110 001 | dark |
| `001110001110` | 110 001 110 001 | dark |
| `001110010100` | 100 010 110 001 | dark |
| `001110110001` | 001 110 110 001 | dark |
| `001110110110` | 110 110 110 001 | dark |
| `010000000100` | 100 000 000 010 | bright |
| `010000100001` | 001 100 000 010 | bright |
| `010000100110` | 110 100 000 010 | dark |
| `010100001001` | 001 001 100 010 | bright |
| `010100001110` | 110 001 100 010 | dark |
| `010100010100` | 100 010 100 010 | bright |
| `010100110001` | 001 110 100 010 | dark |
| `010100110110` | 110 110 100 010 | dark |
| `100001001010` | 010 001 001 100 | bright |
| `100001010000` | 000 010 001 100 | bright |
| `100001110010` | 010 110 001 100 | dark |
| `100010000000` | 000 000 010 100 | bright |
| `100010100010` | 010 100 010 100 | bright |
| `100110001010` | 010 001 110 100 | dark |
| `100110010000` | 000 010 110 100 | dark |
| `100110110010` | 010 110 110 100 | dark |
| `110001001001` | 001 001 001 110 | dark |
| `110001001110` | 110 001 001 110 | dark |
| `110001010100` | 100 010 001 110 | dark |
| `110001110001` | 001 110 001 110 | dark |
| `110001110110` | 110 110 001 110 | dark |
| `110010000100` | 100 000 010 110 | dark |
| `110010100001` | 001 100 010 110 | dark |
| `110010100110` | 110 100 010 110 | dark |
| `110110001001` | 001 001 110 110 | dark |
| `110110001110` | 110 001 110 110 | dark |
| `110110010100` | 100 010 110 110 | dark |
| `110110110001` | 001 110 110 110 | dark |
| `110110110110` | 110 110 110 110 | dark |

## Circuit model

Gates `cx cz h p rz s sdg t tdg x z` and macros `ccx ccz ch cp crx crz rccx swap` with costs (CX, T, rotations): ccx (6, 7, 0), rccx (3, 4, 0), ccz (6, 7, 0), swap (3, 0, 0), ch (1, 2, 0), crz (2, 0, 2), crx (2, 0, 2), cp (2, 0, 3), cz (1, 0, 0). `Builder.alloc/free` for clean ancillas; `Builder.mcx` for 3 or more controls (native mcx, mcrx, cu, unitary and measurement are rejected); at most 56 qubits in total; emission-time classical computation (including oracle queries) is allowed.

## Correctness

The combined error bound `op_norm_error` = block error + leak amplitude (+ certified simulator pruning bound) must be at most 1e-10 on the physical block after one global phase, and the Gauss residual of the outputs at most 1e-10; the skeleton must be identical at the three angle pairs; evaluation wall at most 300 s and at most 5000000 stored amplitudes. The circuit you submit is exact-angle; its Clifford+T synthesis (pygridsynth at $\varepsilon=1e-06$) is re-verified separately with both tolerances $N_{\rm rot}\varepsilon+1e-09$ (the triangle inequality over the $N_{\rm rot}$ synthesised rotations). The simulator's certified pruning bound (`dropped_total`) must be at most 0.01 times the error tolerance (programs that keep hundreds of tiny amplitudes alive are rejected as `pruning_bound`). The evaluator is ground truth.

## Cost

Key $(\mathrm{CX},\,T_{\varepsilon},\,\mathrm{depth}_{\rm CT},\,\mathrm{qubits})$, lexicographic. $T_\varepsilon=T_{\rm fixed}+\sum_r T_r$ with each rotation $T_r$ measured with pygridsynth at $\varepsilon=1e-06$; estimate $3\log_2(1/\varepsilon)$ per rotation. MAP-Elites cells $(\lfloor8\log_2(\mathrm{CX}+1)\rfloor,\lfloor8\log_2(T_\varepsilon+1)\rfloor)$.

## LSH register and rules

The register is `d[0..11]` (the four 'in' sites, `d[3c], d[3c+1], d[3c+2]` = ($\ell_{pn}$, $\ell_{nv}$, $\ell_{vp}$) of corner $c$, written `l_pn`, `l_nv`, `l_vp`), `o[12..23]` (the read-only outer sites: use them as controls only; a program that writes an outer qubit is invalid) and the ancillas you allocate. A site holds one of the five codes 000, 001, 010, 100, 110 (bit order `l_vp l_nv l_pn`); a state is physical when all four 'in' sites are valid and the Abelian Gauss law holds on the four inner links (`l_pn xor l_nv` at one site equals `l_pn xor l_vp` at the next): 47 data codes, 433 physical states with the outer pattern. Target: $U=U_B(\beta)\,U_E(\alpha)$ at $(\alpha,\beta)=(0.37,0.61)$; $U_B=e^{-i\beta K}$ with $K$ the real symmetric coupling of the 47 inner codes (zero on dark codes), identity structure in the outer pattern; $U_E=e^{-i\alpha H_E}$ is diagonal: $H_E=\tfrac34\sum_c N_n(c)$ with $N_n=\ell_{pn}+\ell_{nv}$ at each site, i.e. the phase $-3\alpha/4$ per set `l_pn` or `l_nv` bit (the two never are both set on a physical site). A final state that breaks the Abelian Gauss law or the flux cap on a physical input makes the program invalid; intermediate states are unrestricted. `rccx` (relative-phase Toffoli, 3 CX) is available where an exact `ccx` (6 CX) is not needed.

## Proved structure (Lean)

Machine-checked facts about the problem (Lean 4, kernel-checked by `decide`, standard axioms only); the numerical evaluator remains ground truth. Facts marked *measured* are numbers read off the Python encoding, not proved.

- `card_site_codes` = 5 (proved by decide, Su2Plaq.LSH.card_site_codes) -- valid loop-number codes of one site (the flux cap: virtual spin at most 1)
- `card_inner_codes` = 47 (proved by decide, Su2Plaq.LSH.card_inner_codes) -- inner codes: four valid sites obeying the Abelian Gauss law on the four inner links
- `card_bright_codes` = 16 (proved by decide, Su2Plaq.LSH.card_bright_codes) -- inner codes on which the plaquette coupling is non-zero
- `card_dark_codes` = 31 (proved by decide, Su2Plaq.LSH.card_dark_codes) -- inner codes on which the plaquette coupling is zero
- `card_states_lsh` = 433 (proved by decide, Su2Plaq.LSH.card_states_lsh) -- physical states = valid data codes with a valid outer-site pattern
- `card_bright_states` = 256 (proved by decide, Su2Plaq.LSH.card_bright_states) -- physical states whose inner code is bright
- `site_valid_list` = [0, 1, 2, 4, 6] (proved by decide, Su2Plaq.LSH.site_valid_list) -- the five valid site codes (bit 0 = l_pn, bit 1 = l_nv, bit 2 = l_vp)
- `inner_codes_from_rules` = True (proved by decide, Su2Plaq.LSH.inner_codes_from_rules) -- the 47 inner codes are exactly the codes cut out by the flux cap and the Abelian Gauss law
- `coupling_zero_iff_dark` = True (proved by decide, Su2Plaq.LSH.coupling_zero_iff_dark) -- the coupling is zero exactly on dark codes
- `dark_site_is_and` = True (proved by decide, Su2Plaq.LSH.dark_site_is_and) -- a site is dark iff l_nv AND l_vp are both set (one AND of raw bits)
- `coupling_by_y_weight` = {'0': -4, '1': 2, '2': -1} (proved by decide, Su2Plaq.LSH.coupling_by_y_weight) -- on bright codes 2K depends only on the number of set l_nv bits: {number of set l_nv bits: 2K}
- `link_bit_two_ways` = True (proved by decide, Su2Plaq.LSH.link_bit_two_ways) -- every inner link bit is readable at two sites: l_pn xor l_nv at one site = l_pn xor l_vp at the next
- `move_per_site` = {'w0': 1, 'w1': 6} (proved by decide, Su2Plaq.LSH.move_per_site) -- the plaquette move flips l_pn where w = l_nv xor l_vp is 0 and l_nv, l_vp where w is 1; value: the site XOR pattern {w=0, w=1}
- `y_parity_invariant` = True (proved by decide, Su2Plaq.LSH.y_parity_invariant) -- the parity of the four l_nv bits is unchanged by the move and equals [2K = +2]
- `eight_differences` = 8 (proved by decide, Su2Plaq.LSH.eight_differences) -- the eight difference vectors (code XOR partner) of the move are pairwise different: no CNOT-only frame exists
- `transcode_into_spinnet` = True (proved by decide, Su2Plaq.LSH.transcode_into_spinnet) -- the per-site transcoder maps the 47 LSH inner codes onto valid spin-network codes
- `coupling_matches_spinnet` = True (proved by decide, Su2Plaq.LSH.coupling_matches_spinnet) -- the LSH coupling table equals the spin-network coupling on the transcoded codes
- `n_outer_site_patterns` = 305 (measured, not proved) -- distinct outer-site patterns (the 12 read-only outer qubits take 305 values on the physical states); measured, not proved
- `transcoder_overhead` = {'cx': 40, 't_fixed': 32} (measured, not proved) -- CX and fixed T of the per-site transcoder and its inverse around a spin-network circuit; measured on the circuit

## Headline rule

The archive key counts T at the nominal angle pair; the number reported for this loop (the headline) is the valid entry with the smallest robust key (CX, T summed over 20 fixed random angle pairs, angle-linear first, depth_CT summed over the same pairs, qubits). Offsetting a rotation by $\pm\pi/4$ with a compensating `t`/`tdg` costs +1 T at every angle and saves nothing on average: it will not count. Offsets that are multiples of $\pi/2$ on `rz`/`p`/`rx`/`ry` belong in separate `s`/`sdg`/`z` gates (for `crz`/`crx`/`cry`/`cp` only multiples of $\pi$ are Clifford: $\mathrm{cp}(\pi/2)$ is a controlled-$S$ and costs T) so that every rotation angle stays a linear function of the two task angles alpha and beta (angle-linear programs rank first and can be certified for all angles). A program whose gate skeleton changes with the angles has no robust key. Fewer CX, fewer rotations, smaller rotation counts and shared rotations are what move the headline.

## Tools

`python -m su2plaq.compress.run_candidate <program.py> --encoding lsh --kind step --trial` (seconds; 64 physical inputs, nominal angles, T estimate) or `--full`.
`python -m su2plaq.compress.oracle --encoding lsh --kind step [--column j] [--element i j] [--codec] [--block o]` prints the exact target (matrix column, element, codec, outer block); programs may call `su2plaq.compress.oracle` and `numpy`, nothing else from the project.

Program contract: write ONE file `compress/programs/<encoding>/<family>/NNN-slug.py` whose docstring starts with `SUMMARY: ...` followed by at most 3 `DISCOVERY: ...` lines, with `FAMILY = "..."`, `PARENT = "..." | None` and `def build(spec) -> Builder`.
