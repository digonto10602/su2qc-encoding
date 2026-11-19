# Brief: `lsh` / `step`, round 1, family `F5`

**Task.** Rewrite the parent to improve the key; return the complete program.

- Task specification: `compress/specs/lsh-step.md`
- Proved structure (Lean): `compress/specs/lsh-structure.json` (machine-proved facts about the problem; the same facts are in the section 'Proved structure (Lean)' of the specification)
- Check a draft: `python -m su2plaq.compress.run_candidate <program.py> --encoding lsh --kind step --trial` (seconds), `--full` before you finish; the oracle: `python -m su2plaq.compress.oracle ...`

## Parent
none: write a fresh program for this family (the seeds below are alternatives, not parents).

## Archive alternatives (paths and costs only)
- `compress/programs/lsh/seed/005-wrap_sn_headline.py` (entry `r00-seed-005`, family `seed`): CX 71, T_eps 1118, depth_CT 2276, qubits 25; round-0 seed: spin-network program compress/programs/spinnet/F1/002-dimer-linear-corner-walk.py (archive entry r02-F1-002, sha256 750151e9ad417de7d52e4c59a203f1dc493bdea3be5742aa331533170a0ec650) between the LSH transcoder and its inverse.
- `compress/programs/lsh/seed/006-wrap_sn_r05F3.py` (entry `r00-seed-006`, family `seed`): CX 72, T_eps 864, depth_CT 1570, qubits 25; round-0 seed: spin-network program compress/programs/spinnet/F3/005-angle-linear-walk.py (archive entry r05-F3-005, sha256 43605421051ce5e26b85b1b5241eb02638fc5f8ad7c6297a67e7dd0e96fd22e4) between the LSH transcoder and its inverse.
- `compress/programs/lsh/seed/007-wrap_sn_r02F5.py` (entry `r00-seed-007`, family `seed`): CX 74, T_eps 690, depth_CT 1134, qubits 25; round-0 seed: spin-network program compress/programs/spinnet/F5/002-bright_flag_6rot.py (archive entry r02-F5-002, sha256 734a62fe58f316d6deb59561fb90cedcb04e5854f260f4d78e680eb688428f81) between the LSH transcoder and its inverse.

## Last 0 attempts of family `F5`
- (none yet)

## DISCOVERY notes of all programs (last 0 of at most 30 lines)
- (none yet)

## Output
Write ONE program to `compress/programs/lsh/F5/001-<slug>.py` (docstring starting with `SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under `scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.


## Headline rule

The archive key counts T at the nominal angle pair; the number reported for this loop (the headline) is the valid entry with the smallest robust key (CX, T summed over 20 fixed random angle pairs, angle-linear first, depth_CT summed over the same pairs, qubits). Offsetting a rotation by $\pm\pi/4$ with a compensating `t`/`tdg` costs +1 T at every angle and saves nothing on average: it will not count. Offsets that are multiples of $\pi/2$ on `rz`/`p`/`rx`/`ry` belong in separate `s`/`sdg`/`z` gates (for `crz`/`crx`/`cry`/`cp` only multiples of $\pi$ are Clifford: $\mathrm{cp}(\pi/2)$ is a controlled-$S$ and costs T) so that every rotation angle stays a linear function of the two task angles alpha and beta (angle-linear programs rank first and can be certified for all angles). A program whose gate skeleton changes with the angles has no robust key. Fewer CX, fewer rotations, smaller rotation counts and shared rotations are what move the headline.

**LSH note (prompts/401).** The target is the step on the full 24-qubit LSH register (12 data loop-number qubits, 12 read-only outer qubits). You are free to recode the sites or not: nothing requires the spin-network code to appear. For orientation: the cheapest known circuit is a spin-network circuit between the per-site transcoder (`cx`, `cx`, `rccx`) and its inverse; the transcoder pair alone costs 40 CX and 32 T, of which 24 CX and 32 T are four relative-phase Toffoli pairs. This loop asks how much of that is needed. Families are of two kinds: *transcoding* (a spin-network-style walk after recoding all four sites; gains come from merging or thinning the recoding) and *native* (work on the raw loop-number bits and never hold the complete spin-network code of all four sites). An ideation file must contain at least two native families. Facts you may rely on (kernel-checked, see the structure file): a code is dark iff some site has `l_nv = l_vp = 1`; on bright codes the coupling depends only on the number of set `l_nv` bits (0, 1, 2 give k = -2, +1, -1/2) and the parity of the four `l_nv` bits is unchanged by the plaquette move; every inner link bit can be read at two sites (Abelian Gauss law: `l_pn xor l_nv` at one site equals `l_pn xor l_vp` at the next); the move flips `l_pn` where `w = l_nv xor l_vp` is 0, and `l_nv`, `l_vp` where `w` is 1. A final state that breaks the Abelian Gauss law or the flux cap on a physical input makes the program invalid; intermediate states are unrestricted. Outer qubits may be used as controls only.