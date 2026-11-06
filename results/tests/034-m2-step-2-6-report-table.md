### Compression result: `twelve` / `step`

| row | qubits | CX | T_fixed | N_rot | T(1e-6) | T_est(1e-6) | T(1e-10) | depth_CT | verdict | Lean | entry / commit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| general | 50 | 294 | 312 | 10 | 952 | 909.947 | 1352 | 1421 | valid (err 2.68813e-13, leak 0) | not_run | r00-seed-000 @ a1449ea |
| general + polish | 50 | 294 | 312 | 10 | 952 | 909.947 | 1352 | 1421 | valid (err 2.68813e-13, leak 0) | not_run | r00-seed-010 @ a1449ea |
| Qiskit L3 (windows of 32) | 50 | 290 | 302 | 10 | 918 | 899.947 | 1310 | 1387 | valid (err 3.6113e-13, leak 0) | not_run | r00-seed-qiskit_l3 @ a1449ea |
| seed lean22_v2 | 35 | 162 | 160 | 8 | 660 | 638.358 | 986 | 1029 | valid (err 2.13877e-13, leak 0) | not_run | r00-seed-001 @ a1449ea |
| seed lean22 | 38 | 210 | 192 | 8 | 704 | 670.358 | 1026 | 1148 | valid (err 2.96008e-13, leak 0) | not_run | r00-seed-002 @ a1449ea |
| Qiskit L3 (whole circuit; counts only, unverifiable) | 50 | 290 | 294 | 10 | 891.947 | 891.947 | 1290.58 | 268 | unverifiable: Qiskit's whole-circuit level-3 transpile hoists Hadamards (more than 1e6 amplitudes per input), beyond the exact sparse engine | n_a | - |
| paulo34 (fixed angle; Clifford+T up to a global phase) | 50 | 294 | 1162 | 0 | 1162 | 1162 | 1162 | 2549 | valid at its own angle (beta = 1, kind UB), err 1.07559e-05 | n_a | - |
| spinnet15 (not applicable) | - | - | - | - | - | - | - | - | spinnet15 is Paulo's 15-qubit spin-network circuit: it acts on route-B labels (a different encoding), not on the 12-qubit electric-basis codes; it is handled by the spin-network encoding (M3) | n_a | - |
| best of family F1 | 38 | 210 | 184 | 8 | 696 | 662.358 | 1018 | 1148 | valid (err 3.04595e-13, leak 0) | not_run | r01-F1-001 @ a1449ea |
| best of family F2 | 35 | 162 | 160 | 8 | 660 | 638.358 | 986 | 1029 | valid (err 2.13877e-13, leak 0) | not_run | r01-F2-001 @ a1449ea |
| best of family seed | 35 | 162 | 160 | 8 | 660 | 638.358 | 986 | 1029 | valid (err 2.13877e-13, leak 0) | not_run | r00-seed-001 @ a1449ea |
| GLOBAL BEST | 35 | 162 | 160 | 8 | 660 | 638.358 | 986 | 1029 | valid (err 2.13877e-13, leak 0) | not_run | r00-seed-001 @ a1449ea |

Every exact-angle circuit is the target up to ONE global phase; Clifford+T circuits (synthesised) are equal to their exact-angle design up to the synthesis error and one global phase. T(1e-6), T(1e-10): T_fixed + pygridsynth T of every rotation (measured); T_est: T_fixed + 3 N_rot log2(1/eps). Key = (CX, T(1e-6), depth_CT, qubits), lexicographic.
Round 0: Clifford+T re-verification of `r00-seed-001`: ok (eps 1e-06, 8 rotations, T 660, error 2.98895e-06 <= 8.001e-06)
