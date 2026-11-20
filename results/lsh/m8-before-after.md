# M8 before / after (LSH step, alpha = 0.37, beta = 0.61, order 1)

Rendered by `scripts/m8_results.py` from the archive; T = pygridsynth T count at eps = 1e-6 per rotation at the nominal pair, T_avg = the same averaged over the 20 fixed random angle pairs (seed 20261107, sha256 769caec1c2738356); depth_CT = depth after Clifford+T synthesis (blank for the counts-only row).

GLOBAL BEST (archive key): r05-F3-005.  HEADLINE (robust key): r05-F3-005.

| row | entry | qubits | CX | T_fixed | N_rot | T(1e-6) | T_avg(1e-6) | T_est(1e-6) | T(1e-10) | depth_CT | verdict | Lean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| general | r00-seed-000 | 31 | 94 | 88 | 8 | 598 | 592.6 | 566.4 | 916 | 880 | valid (err 1.64e-14, leak 0) | not_run |
| general+polish | r00-seed-010 | 31 | 94 | 88 | 8 | 598 | 592.6 | 566.4 | 916 | 880 | valid (err 1.64e-14, leak 0) | not_run |
| qiskit_l3 | r00-seed-qiskit_l3 | 31 | 94 | 88 | 8 | 598 | - | 566.4 | 916 | 880 | valid (err 1.82e-14, leak 0) | not_run |
| qiskit_l3_whole | - | 31 | 94 | 88 | 8 | - | - | 566.4 | - | - | unverifiable: Qiskit's whole-circuit level-3 transpile hoists Hadamards (more than 1e6 amplitudes per input), beyond the exact sparse engine (counts only) | n_a |
| wrap_pairs9 | r00-seed-001 | 27 | 74 | 56 | 13 | 864 | 879.4 | 833.3 | 1408 | 1615 | valid (err 1.08e-14, leak 0) | not_run |
| wrap_flags4 | r00-seed-002 | 27 | 84 | 80 | 8 | 586 | 585.1 | 558.4 | 912 | 888 | valid (err 1.21e-14, leak 0) | not_run |
| wrap_flags5 | r00-seed-003 | 27 | 82 | 72 | 9 | 638 | 641.1 | 610.2 | 1008 | 1027 | valid (err 1.22e-14, leak 0) | not_run |
| wrap_flags6 | r00-seed-004 | 27 | 76 | 64 | 10 | 690 | 697.6 | 661.9 | 1106 | 1139 | valid (err 1.13e-14, leak 0) | not_run |
| wrap_sn_headline | r00-seed-005 | 25 | 71 | 48 | 17 | 1118 | 1124.0 | 1064.5 | 1816 | 2276 | valid (err 8.87e-15, leak 0) | certified |
| wrap_sn_r05F3 | r00-seed-006 | 25 | 72 | 56 | 13 | 864 | 879.4 | 833.3 | 1408 | 1570 | valid (err 9.49e-15, leak 0) | not_run |
| wrap_sn_r02F5 | r00-seed-007 | 25 | 74 | 64 | 10 | 690 | 697.6 | 661.9 | 1106 | 1134 | valid (err 1.09e-14, leak 0) | not_run |
| paulo15_wrapped | - | 31 | 108 | 96 | 4 | 348 | - | 335.2 | 510 | 746 | valid at its own angle (kind UB, beta = -0.05), err 1.32e-14 | n_a |
| best_family_F1 | r02-F1-002 | 25 | 71 | 40 | 17 | 1110 | 1116.0 | 1056.5 | 1808 | 2291 | valid (err 7.21e-15, leak 0) | certified |
| best_family_F2 | r02-F2-002 | 26 | 72 | 44 | 19 | 1242 | 1248.1 | 1180.1 | 2020 | 2614 | valid (err 1.56e-14, leak 0) | not_run |
| best_family_F3 | r05-F3-005 | 24 | 68 | 24 | 22 | 1396 | 1417.4 | 1339.5 | 2312 | 3210 | valid (err 1.44e-14, leak 0) | certified |
| best_family_F4 | r02-F4-002 | 24 | 73 | 24 | 22 | 1396 | 1417.4 | 1339.5 | 2312 | 3218 | valid (err 1.25e-14, leak 0) | not_run |
| best_family_F5 | r05-F5-005 | 24 | 68 | 24 | 22 | 1396 | 1417.4 | 1339.5 | 2312 | 3220 | valid (err 1.27e-14, leak 0) | not_run |
| global_best | r05-F3-005 | 24 | 68 | 24 | 22 | 1396 | 1417.4 | 1339.5 | 2312 | 3210 | valid (err 1.44e-14, leak 0) | certified |
| headline | r05-F3-005 | 24 | 68 | 24 | 22 | 1396 | 1417.4 | 1339.5 | 2312 | 3210 | valid (err 1.44e-14, leak 0) | certified |

## The three numbers

- spin-network headline `r02-F1-002`: 31 CX, T_avg 1092.0
- the same circuit wrapped by the LSH transcoder (+40 CX, +32 T): 71 CX, T_avg 1124.0
- LSH headline `r05-F3-005`: 68 CX, T_avg 1417.4
- native_gain_cx = 3, overhead_cx = 37.  the loop removed 3 of the 40 transcoder CX; the LSH register still costs 37 CX beyond the spin-network optimum.

## CX versus T_avg front (valid entries, CX ascending)

| id | CX | T_avg | family | round | Lean |
|---|---|---|---|---|---|
| r04-F3-004 | 68 | 1417.4 | F3 | 4 | certified |
| r03-F3-003 | 70 | 1354.3 | F3 | 3 | certified |
| r02-F1-002 | 71 | 1116.0 | F1 | 2 | certified |
| r00-seed-006 | 72 | 879.4 | seed | 0 | not_run |
| r00-seed-007 | 74 | 697.6 | seed | 0 | not_run |
| r00-seed-003 | 82 | 641.1 | seed | 0 | not_run |
| r00-seed-002 | 84 | 585.1 | seed | 0 | not_run |

Moving down the table buys fewer T_avg at the price of more CX; the first row is the headline (smallest CX).

## Uniform splitting (structure only)

nnz 400, max 4 per row, 6 sites / 18 qubits touched; circuit: not built (a structure row, not a built circuit: it is not comparable with the rows above).

## Stop record

stop = True, reason = max_sessions, streak = 2, sessions = 20.

## Lean

status: certified; trust: native-certified (native-certified, first-order step when certified); theorem file: lean/certs/lsh-best-step.lean (status: elaborated); axioms: ['Classical.choice', 'Quot.sound', 'lsh_best._native.native_decide.ax_1_1', 'propext'].

## Outer electric row (M7, unchanged by the loop)

the same electric layer with 12 extra phases on the outer-site qubits (include_outer_electric); it reads 12 outer bits and is unchanged by the compression loop (committed M7 result results/lsh/UE.json).  Its exact-angle circuit is verified; its synthesised (Clifford+T) form writes the outer register and is NOT verifiable by this evaluator (audit 303 N5), so only its T cost is reported.
