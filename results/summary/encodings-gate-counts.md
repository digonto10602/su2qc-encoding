# Gate counts of the five encodings

Commit 941e2f0. Command: `python scripts/summary_table.py`.

## Table 1. General (uncompressed) circuits

| Encoding | Circuit | Qubits | CX | Rotations | Fixed T | T(1e-6) | Error | Source |
|---|---|---|---|---|---|---|---|---|
| 1. 12-qubit (Paulo) | U_E (electric) | 12 | 0 | 4 | 0 | 256 | 1.2e-13 | results/twelve/UE.json @ a9702e5 |
| 1. 12-qubit (Paulo) | U_B (magnetic) | 34 | 294 | 6 | 312 | 696 | 2.4e-13 | results/twelve/UB.json @ a9702e5 |
| 1. 12-qubit (Paulo) | step, order 1 | 34 | 294 | 10 | 312 | 952 | 2.7e-13 | results/twelve/step.json @ a9702e5 |
| 2. Spin network | U_E (electric) | 8 | 0 | 4 | 0 | 256 | 4.4e-16 | results/spinnet/UE.json @ d82a472 |
| 2. Spin network | U_B (magnetic) | 15 | 54 | 4 | 56 | 310 | 1.1e-14 | results/spinnet/UB.json @ d82a472 |
| 2. Spin network | step, order 1 | 15 | 54 | 8 | 56 | 566 | 1.1e-14 | results/spinnet/step.json @ d82a472 |
| 3. Rishon | U_E (electric) | 16 | 8 | 4 | 0 | 256 | 1.1e-16 | results/rishon/UE.json @ b4c1917 |
| 3. Rishon | U_B (magnetic) | 26 | 10094 | 162 | 10218 | 20394 | 3.4e-13 | results/rishon/UB.json @ b4c1917 |
| 3. Rishon | step, order 1 | 26 | 10102 | 166 | 10218 | 20650 | 4.1e-13 | results/rishon/step.json @ b4c1917 |
| 3. Rishon | U_D (det layer) | 16 | 32 | 8 | 0 | 496 | 2.8e-15 | results/rishon/UD.json @ 6fea036 |
| 3. Rishon | step + det, order 1 | 26 | 10134 | 174 | 10218 | 21146 | 5.0e-13 | results/rishon/step3.json @ 6fea036 |
| 4. Loop-string-hadron | U_E (electric) | 12 | 0 | 8 | 0 | 512 | 4.4e-16 | results/lsh/UE.json @ 76fd221 |
| 4. Loop-string-hadron | U_B (magnetic) | 19 | 94 | 4 | 88 | 342 | 1.4e-14 | results/lsh/UB.json @ 76fd221 |
| 4. Loop-string-hadron | step, order 1 | 19 | 94 | 8 | 88 | 598 | 1.6e-14 | results/lsh/step.json @ 76fd221 |
| 5. Fuzzy | U_E (electric) | 16 | 72 | 24 | 0 | 1584 | 4.3e-16 | results/fuzzy/UE.json @ 8e71c38 (dirty) |
| 5. Fuzzy | U_K (fuzzy kinetic) | 16 | 72 | 16 | 0 | 992 | 1.5e-15 | results/fuzzy/UK.json @ 8e71c38 (dirty) |
| 5. Fuzzy | U_B (magnetic) | 23 | 1718 | 16 | 1826 | 2822 | 3.8e-14 | results/fuzzy/UB.json @ 8e71c38 (dirty) |
| 5. Fuzzy | step, order 1 | 23 | 1862 | 56 | 1826 | 5398 | 1.0e-14 | results/fuzzy/step.json @ 8e71c38 (dirty) |

## Table 2. Compression loops: general vs headline

| Loop | Version | Qubits | CX | Rotations | T(1e-6) | Error | Lean | Lean source | Entry | State |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. 12-qubit, step | general | 50 | 294 | 10 | 952 | 2.7e-13 | certified | certificate: results/lean/general_step_certificate.json | r00-seed-000 |  |
|  | headline | 31 | 111 | 13 | 912 | 1.0e-13 | certified | archive: results/compress/twelve/summary.json | r05-F2-005 | stopped after round 5 |
| 2. Spin network, step | general | 23 | 54 | 8 | 566 | 1.2e-14 | certified | archive: results/compress/spinnet/summary.json | r00-seed-000 |  |
|  | headline | 17 | 31 | 17 | 1086 | 5.1e-15 | certified | certificate: results/spinnet/m4-compressed.json | r02-F1-002 | stopped after round 5 |
| 3. Rishon, step (no det) | general | 58 | 10102 | 166 | 20650 | 4.1e-13 | certified | certificate: results/rishon/m6-compressed.json | r00-seed-000 |  |
|  | headline | 52 | 216 | 10 | 832 | 1.3e-13 | certified | certificate: results/rishon/m6-compressed.json | r06-F3-006 | stopped after round 6 |
| 4. Loop-string-hadron, step | general | 31 | 94 | 8 | 598 | 1.6e-14 | certified | certificate: results/lsh/step.json | r00-seed-000 |  |
|  | headline | 24 | 68 | 22 | 1396 | 1.4e-14 | certified | certificate: results/lsh/m8-compressed.json | r05-F3-005 | stopped after round 6 (session limit) |
| 5. Fuzzy, U_B | general | 15 | 1718 | 16 | 2822 | 3.8e-14 | n_a | no exact Lean exporter (plan 302 s0.5) | r00-seed-000 |  |
|  | headline | 10 | 83 | 9 | 638 | 5.4e-14 | n_a | no exact Lean exporter (plan 302 s0.5) | r10-F1-010 | stopped after round 13 (Digonto) |
| 5. Fuzzy, link U_E | general | 4 | 36 | 10 | 644 | 3.4e-15 | n_a | no exact Lean exporter (plan 302 s0.5) | r00-seed-000 |  |
|  | headline | 4 | 12 | 10 | 644 | 5.5e-15 | n_a | archive: results/compress/fuzzy_link/summary.json | r02-F2-001 | finished |
| 5. Fuzzy, full step + outer | general | 55 | 2150 | 136 | - | - | - | - | - |  |
|  | headline composed | 50 | 227 | 129 | - | 1.2e-14 | - | - | U_B r10-F1-010; link r02-F2-001 | headline units (prompts/010) |

## Notes

- CX = CNOT count. Rotations = arbitrary-angle rotations. Fixed T = T gates already in the circuit (Toffoli-type parts).
- T(1e-6) = fixed T + T gates of all rotations synthesised to accuracy 1e-6 each (pygridsynth). Error = largest operator-norm
  difference from the exact target over all Gauss-law states (433 states; rishon on its inner codes).
- Table 1 counts the data register plus helper qubits; Table 2 uses each loop's own register (outer links included), so qubit
  totals differ between the tables. Compare rows within one encoding; the circuits differ (U_B only vs full step) across encodings.
- Table 2 'headline' = the circuit chosen by the robust-key rule (smallest CX, then sum of T(1e-6) over 20 angle pairs; prompts/104,
  203, 008, 010), read from results/compress/<enc>/summary.json; it is not always the nominal-angle archive best:
  2. Spin network, step: headline r02-F1-002 (T mean over the angle set 1092.0); archive best r04-F1-004 (CX, T(1e-6), depth_CT, qubits) = (31, 1062, 2173, 17).
  5. Fuzzy, U_B: headline r10-F1-010 (T mean over the angle set 634.4); archive best r12-F1-012 (CX, T(1e-6), depth_CT, qubits) = (83, 638, 1517, 10).
- Lean: certified = native Lean checker accepted that exact circuit; n_a = no checker for it (fuzzy: no exact exporter);
  not_run = not attempted. Fuzzy general results were made on a dirty tree (8e71c38).
- Lean source: 'certificate: <file>' = status read from that certificate record (general rows: twelve results/lean/general_step_
  certificate.json, LSH results/lsh/step.json extra.lean, rishon results/rishon/m6-compressed.json; headlines: m4/m6/m8 files);
  'archive: <file>' = the archive field of the loop (spin network general); 'no exact Lean exporter' = fuzzy (plan 302 s0.5).
- Fuzzy composed step: units are the headline U_B and link U_E (results/fuzzy/compressed_step_headline.json, prompts/010).
- Generated by `python scripts/summary_table.py` at commit 941e2f0.
