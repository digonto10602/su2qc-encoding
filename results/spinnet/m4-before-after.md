# M4 before / after (spin-network step, alpha = 0.37, beta = 0.61, order 1)

Rendered by `scripts/m4_results.py` from the archive; T = pygridsynth T count at eps = 1e-6 per rotation at the nominal pair, T_avg = the same averaged over the 20 fixed random angle pairs (seed 20261107, sha256 769caec1c2738356); depth_CT = depth after Clifford+T synthesis. T(1e-6) at the nominal pair can depend on pygridsynth's word length at those angles (see the NOTE); T_avg does not.

GLOBAL BEST (laptop key): r04-F1-004.  HEADLINE (robust key): r02-F1-002.

| row | entry | qubits | CX | T_fixed | N_rot | T(1e-6) | T_avg(1e-6) | T_est(1e-6) | T(1e-10) | depth_CT | verdict | Lean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| general | r00-seed-000 | 23 | 54 | 56 | 8 | 566 | 560.6 | 534.4 | 884 | 861 | valid (err 1.23e-14, leak 0) | certified |
| general+polish | r00-seed-010 | 23 | 54 | 56 | 8 | 566 | 560.6 | 534.4 | 884 | 861 | valid (err 1.23e-14, leak 0) | not_run |
| qiskit_l3 | r00-seed-011 | 23 | 54 | 56 | 8 | 566 | 560.6 | 534.4 | 884 | 861 | valid (err 1.67e-14, leak 0) | not_run |
| qiskit_l3_whole | - | 23 | 54 | 56 | 8 | - | - | 534.4 | - | - | unverifiable (counts only): unverifiable: Qiskit's whole-circuit level-3 transpile hoists Hadamards (more than 1e6 amplitudes per input), beyond the exact sparse engine | n_a |
| spinnet_v2_pairs9 | r00-seed-001 | 19 | 34 | 24 | 13 | 832 | 847.4 | 801.3 | 1376 | 1597 | valid (err 7.9e-15, leak 0) | certified |
| spinnet_v2_flags4 | r00-seed-002 | 19 | 44 | 48 | 8 | 554 | 553.1 | 526.4 | 880 | 869 | valid (err 9.28e-15, leak 0) | not_run |
| spinnet_v2_flags5 | r00-seed-003 | 19 | 42 | 40 | 9 | 606 | 609.1 | 578.2 | 976 | 1009 | valid (err 8.79e-15, leak 0) | not_run |
| spinnet_v2_flags6 | r00-seed-004 | 19 | 36 | 32 | 10 | 658 | 665.6 | 629.9 | 1074 | 1120 | valid (err 8.02e-15, leak 0) | not_run |
| paulo15 | - | 23 | 68 | 64 | 4 | 316 | - | 303.2 | 478 | 726 | valid at its own angle (beta = 0.05), err 9.61e-15 | n_a |
| best_family_F1 | r02-F1-002 | 17 | 31 | 16 | 17 | 1086 | 1092.0 | 1032.5 | 1784 | 2258 | valid (err 5.13e-15, leak 0) | certified |
| best_family_F2 | r05-F2-005 | 17 | 31 | 16 | 17 | 1086 | 1092.0 | 1032.5 | 1784 | 2262 | valid (err 4.99e-15, leak 0) | not_run |
| best_family_F3 | r05-F3-005 | 17 | 32 | 24 | 13 | 832 | 847.4 | 801.3 | 1376 | 1552 | valid (err 5.59e-15, leak 0) | not_run |
| best_family_F5 | r02-F5-002 | 17 | 34 | 32 | 10 | 658 | 665.6 | 629.9 | 1074 | 1116 | valid (err 6.86e-15, leak 0) | not_run |
| best_family_seed | r00-seed-001 | 19 | 34 | 24 | 13 | 832 | 847.4 | 801.3 | 1376 | 1597 | valid (err 7.9e-15, leak 0) | certified |
| global_best | r04-F1-004 | 17 | 31 | 24 | 17 | 1062 | 1092.0 | 1040.5 | 1752 | 2173 | valid (err 7.35e-15, leak 0) | n_a |
| headline | r02-F1-002 | 17 | 31 | 16 | 17 | 1086 | 1092.0 | 1032.5 | 1784 | 2258 | valid (err 5.13e-15, leak 0) | certified |

NOTE: the nominal-pair T(1e-6) of an entry whose rotations are emitted as rz(theta + pi/4) . tdg (or with other shifted angle forms) can be smaller than its T_avg because pygridsynth's word is cheaper at the nominal angles; T_avg is the robust cost. Structural gains are the CX and N_rot columns.
