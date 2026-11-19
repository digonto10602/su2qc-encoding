# M6 before / after (rishon step, alpha = 0.37, beta = 0.61, eta = 0.29, order 1)

Rendered by `scripts/m6_results.py` from the archive; T = pygridsynth T count at eps = 1e-6 per rotation at the nominal pair, T_avg = the same averaged over the 20 fixed random angle pairs (seed 20261107, sha256 769caec1c2738356; the det layer over its 20 eta values, seed 20261110); depth_CT = depth after Clifford+T synthesis.  `unit` = U_B U_E (the compression unit), `det` = U_D, `three_layer` = U_B U_D U_E (one first-order Trotter step of the model), `outer` = the separate 12-link rows.

GLOBAL BEST (laptop key): r06-F3-006.  HEADLINE (robust key): r06-F3-006.

| row | layer | entry | qubits | CX | T_fixed | N_rot | T(1e-6) | T_avg(1e-6) | T_est(1e-6) | T(1e-10) | depth_CT | verdict | Lean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| general | unit | r00-seed-000 | 58 | 10102 | 10218 | 166 | 20650 | 20620.2 | 20143.9 | 27482 | 35639 | valid (err 4.13e-13, leak 0) | certified |
| cheapest_valid_seed | unit | r00-seed-001 | 58 | 6874 | 7262 | 166 | 17694 | 17664.2 | 17187.9 | 24526 | 31954 | valid (err 3.29e-12, leak 0) | certified |
| seed_002 | unit | r00-seed-002 | 58 | 7360 | 7748 | 166 | 18180 | 18150.2 | 17673.9 | 25012 | 32428 | valid (err 3.03e-12, leak 0) | not_run |
| seed_010 | unit | r00-seed-010 | 58 | 10102 | 10218 | 166 | 20650 | 20620.2 | 20143.9 | 27482 | 35639 | valid (err 4.13e-13, leak 0) | not_run |
| best_family_F1 | unit | r06-F1-006 | 52 | 218 | 196 | 10 | 840 | 829.2 | 793.9 | 1228 | 1358 | valid (err 1.34e-13, leak 0) | not_run |
| best_family_F2 | unit | r02-F2-002 | 57 | 252 | 250 | 14 | 1150 | 1134.6 | 1087.1 | 1678 | 2073 | valid (err 1.46e-13, leak 0) | not_run |
| best_family_F3 | unit | r06-F3-006 | 52 | 216 | 196 | 10 | 832 | 829.8 | 793.9 | 1228 | 1350 | valid (err 1.35e-13, leak 0) | certified |
| best_family_F4 | unit | r05-F4-005 | 55 | 274 | 282 | 14 | 1186 | 1169.6 | 1119.1 | 1718 | 1767 | valid (err 1.68e-13, leak 0) | not_run |
| best_family_F5 | unit | r01-F5-001 | 51 | 492 | 483 | 20 | 1739 | 1743.0 | 1678.9 | 2563 | 3142 | valid (err 1.77e-13, leak 0) | not_run |
| global_best | unit | r06-F3-006 | 52 | 216 | 196 | 10 | 832 | 829.8 | 793.9 | 1228 | 1350 | valid (err 1.35e-13, leak 0) | certified |
| headline | unit | r06-F3-006 | 52 | 216 | 196 | 10 | 832 | 829.8 | 793.9 | 1228 | 1350 | valid (err 1.35e-13, leak 0) | certified |
| det_layer | det | - | 48 | 32 | 0 | 8 | 496 | 500.8 | 478.4 | 816 | 326 | valid (results/rishon/UD.json, eta = 0.29) | certified |
| general+det | three_layer | r00-seed-000 | 58 | 10134 | 10218 | 174 | 21146 | 21121.0 | 20622.3 | 28298 | 35965 | unit valid; det layer in front (U_D commutes with U_E) | certified |
| cheapest_valid_seed+det | three_layer | r00-seed-001 | 58 | 6906 | 7262 | 174 | 18190 | 18165.0 | 17666.3 | 25342 | 32280 | unit valid; det layer in front (U_D commutes with U_E) | certified |
| global_best+det | three_layer | r06-F3-006 | 52 | 248 | 196 | 18 | 1328 | 1330.6 | 1272.3 | 2044 | 1676 | verified on the 1296 codes at 3 triples (three-layer.json) | certified |
| headline+det | three_layer | r06-F3-006 | 52 | 248 | 196 | 18 | 1328 | 1330.6 | 1272.3 | 2044 | 1676 | verified on the 1296 codes at 3 triples (three-layer.json) | certified |
| outer_electric_row | outer | - | 48 | 24 | 0 | 12 | 768 | - | 717.5 | 1248 | 169 | certified per link (UE_outer_row_certified.json, commit 59e863d) | n_a |
| outer_det_row | outer | - | 48 | 96 | 0 | 24 | 1488 | - | 1435.1 | 2448 | 326 | certified per link (UD_outer_row_certified.json, commit 6fea036) | n_a |

NOTE: the nominal-pair T(1e-6) can depend on pygridsynth's word length at those angles; T_avg is the robust cost.  The structural gains are the CX and N_rot columns.  Lean words: `certified` = the three-angle checker (METHODS-rishon R12) accepted the exact certificate; the general-circuit rows are certified by lean/certs/rishon-general-step.lean.
