# Tester report 105 — M3 steps 3.L1 + 3.L2: spin-network Lean counts and circuit structure

- Date: 2026-11-06
- Git commit under test: `f4caa19` plus uncommitted changes (list in section "Ownership")
- Prompt in force: `prompts/100-spinnet-m3-plan.md` (§1.8, §3 rows 3.L1/3.L2, §4)
- Related reports: `reports/tests/100`, `101`, `102`, `103`, `104`
- Mode: step. Track S, branch `m3-spin-network`, clone `~/Projects/su2qc-spinnet`.
- Raw data and scripts: `results/spinnet/tester/` (`m3_all.txt`, `unit.txt`, `m0m1.txt`, `compare_results.{py,txt}`, `angle_diff.{py,txt}`, `lean_vs_python_slots.{py,txt}`, `lean_mutations_*.txt`, `structure_counts_olean_before.md5`).

## Verdict: PASS

No failures. L3 is PENDING (the laptop's `Su2PlaqCert/Main.lean` is still the skeleton). Three non-blocking observations about what the Lean theorems do and do not tie together are in "Trust judgement".

## Commands run

```
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1; source ~/.elan/env
graphify update .
cd lean && taskset -c 0-9 lake build Su2Plaq
cd lean && taskset -c 0-9 lake env lean <scratch>/ax.lean              # #print axioms for 17 theorems
taskset -c 0-9 pytest -n 10 tests/acceptance/m3/test_spinnet_lean.py -q -rA
taskset -c 0-9 pytest -n 10 tests/acceptance/m3 -q -rfE
taskset -c 0-9 pytest -n 10 tests/unit -q
taskset -c 0-9 pytest -n 10 -m "not slow" tests/acceptance/m0 tests/acceptance/m1 -q
taskset -c 0-9 pytest --collect-only -q tests/acceptance
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
PYTHONPATH=src taskset -c 0-9 python scripts/m3_results.py --out <scratch>/res2
python results/spinnet/tester/compare_results.py <scratch>/res2 results/spinnet
python results/spinnet/tester/angle_diff.py <HEAD src | working src> <out.json>
lake env lean <scratch>/mut/*.lean                                      # mutation tests
lake env lean <scratch>/ev.lean ; python results/spinnet/tester/lean_vs_python_slots.py <ev.out>
```

## Results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| `test_M3_L1_spinnet_counts_kernel_checked` | pass | pass | exact | PASS |
| `test_M3_L2_general_circuit_structure_kernel_checked` | pass | pass | exact (tables verbatim) | PASS |
| `test_M3_L3_native_certificate_general_step` | PENDING | `PENDING: Su2PlaqCert checker not yet delivered by the laptop` | — | PENDING (expected) |
| all m3 acceptance (24 ids, incl. slow, R1 against committed results) | 23 pass + L3 pending | 23 passed, 1 failed (L3 `PENDING:`) in 9.4 s | — | PASS |
| unit suite | all green | 286 passed in 30.6 s | — | PASS |
| collection | 126 clean | 126 tests collected | — | PASS |
| m0 + m1 `-m "not slow"` | green | 54 passed in 106 s | — | PASS |
| `tools/check_lock.py` | LOCK OK | `LOCK OK` | — | PASS |
| `acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v7` | — | PASS |
| `lake build Su2Plaq` | green, no rebuild of `Structure/Counts` | `Build completed successfully (9060 jobs)`, 2.7 s, 1.0 GB; `Structure.Counts` is "Replayed" (not compiled); `Counts.olean` md5 `8549f678b9de0ac8c0159f35f90235f6` before and after, mtime still 2026-11-05 23:54 | — | PASS |
| Lean peak memory | ≤ 10 GB | 6.8 GB (`lake env lean`, Mathlib import + SpinNet) | 10 GB | PASS |
| `#print axioms` (17 theorems) | standard axioms only | see next table | — | PASS |
| `sorry` / `admit` / `native_decide` / `axiom` in `lean/Su2Plaq/SpinNet/` | none | none (grep) | — | PASS |
| walk.py snapping: rz angle change vs HEAD | $\lesssim 10^{-14}$ | max $|\Delta\theta|$ = 8.3e-17 (β=0.05), 6.7e-16 (0.23), 1.3e-15 (0.61), 3.1e-15 (1.0), 6.2e-15 (2.0); step (0.37, 0.61, 1): 1.3e-15 | — | PASS |
| regenerated `results/spinnet/{UE,UB,step}.json` vs committed | only rounding | no non-numeric difference; no integer-valued field changed (CX, T, rotations, depth, ancillas unchanged); all other numeric differences ≤ 1.2e-15 absolute (verification errors at the 1e-15 level, synthesis `error_measured_sum` ≤ 3.6e-16 absolute) | — | PASS |
| Ownership | only listed files | confirmed (below) | — | PASS |

### Axioms (command: `lake env lean ax.lean`)

| theorem | axioms |
|---|---|
| `card_inner_labels`, `card_bright_labels`, `card_dark_labels`, `card_bright_pairs`, `mult_two`, `mult_half`, `mult_one`, `card_bright_states`, `card_dark_states`, `card_states_spinnet` | `propext` |
| `corner_jbit_injective`, `corner_bit_needs_four_half`, `table_lengths` | none |
| `frame_maps_flip`, `flags_correct`, `walk_slots_match`, `walk_table_exact` | `propext` |
| `Su2Plaq.card_physical` (laptop, reused) | `propext` |

`propext` is one of the three standard axioms. The Python-side `print_axioms` used by the acceptance tests agrees (both L1 and L2 PASS).

## Trust judgement (read each statement against §1.8 / §4)

What is kernel-checked (all by `decide`, i.e. by kernel evaluation of the definitions in the file; no compiler trust):

- `Counts.lean` (definitions on `Nat`/`Bool` lists, reusing the laptop's `fuse`, `bit`, `sumOver`):
  - 47 inner labels, 16 bright, 31 dark, 8 bright pairs: these are real enumerations of triangle-admissible $J$ per corner for the 16 inner patterns. They are not copied from Python.
  - 256 bright + 177 dark = 433 states, counted through the corner enumeration (an independent route from the laptop's `card_physical`; both come out as 433).
  - `corner_bit_needs_four_half` is a real statement: a corner qubit can be 1 only if all four links at the corner are 1/2, for all $2^4$ link choices.
  - `corner_jbit_injective`: at every corner the corner qubit separates the admissible $J$ values. Real, universally quantified over 16 cases.
- `Circuit.lean` (a hand-written Lean model of the classical skeleton of `GENERAL7`, with exported tables):
  - `frame_maps_flip`: for all $x<16$, `frame (x ^^^ 15) = frame x ^^^ 1`. Real identity on the CX frame model.
  - `flags_correct`: for all 256 data codes, the flag chain computes $F$ (all corner bits 0), $G_1=F\wedge[m=000]$, $G_2=F\wedge[m=100]$ from the framed code. Real statement about the Boolean network.
  - `walk_table_exact`: for the 47 valid codes, $\sum_r a_r(-1)^{p_r}=2\cdot(2K)$, where $a_r$ is the integer angle table and $p_r$ the `rz` wire bit obtained by actually running the gate-list model. Real computation (the bits $p_r$ are produced by running `flagOps ++ walkOps`, not tabulated).

What is NOT kernel-checked, and said precisely:

1. The three tables `validInnerCodes`, `couplingTable`, `angleTable` are copied from Python (`lean_export`). Lean proves only that the copy is self-consistent with the Lean circuit model: $\sum_r a_r(-1)^{p_r}=2\cdot\text{couplingTable}$. That the table equals the true $2K$ of the encoding rests on Python (numerical, snapped to half-integers within $10^{-12}$ and tested in the acceptance test L2 and the unit tests).
2. The Lean circuit model (`frame`, `flagOps`, `walkOps`) is hand-written, not generated from the Python circuit. Its fidelity is checked here by an independent run: I evaluated Lean's `slotBits`, `flagChain` and `walkPhase` for all 256 data codes and compared with Python `classical_slots(GENERAL7, y, FRAME)` and the Boolean flag definition: 0 mismatches over 256 codes; `walkPhase` $=2\cdot$`couplingTable` on all 47 rows (`results/spinnet/tester/lean_vs_python_slots.txt`). This is a numerical cross-check; it is not part of the repository's tests.
3. The model reads `rccx` with Toffoli semantics (the relative-phase Toffoli permutes computational states identically, and the phases cancel in the compute/uncompute sandwich). The phase cancellation, the uncompute half, the Hadamards around the target, and the sign/exponent convention $e^{-i\beta K}$ are not in Lean. They are covered numerically by the evaluator (error $\le 1.4\times10^{-14}$, ancilla dirty $\le 10^{-20}$, reports 102–103).
4. The multiplicities `mult_two` = 16, `mult_one` = 96, `mult_half` = 16 are counts of bright states in the pair classes $\{0000,1111\}$, the six other patterns and $\{0101,1010\}$. The identification "class $\mapsto$ $|K|=2,1,\tfrac12$" and hence "spectrum $16/96/16/177/16/96/16$" is not in Lean. The full spectrum list is not claimed by any theorem (plan §1.8 says "given the pair couplings, which are numerical/native"). I checked by reading the exported table that the classes are consistent: `couplingTable` has $2K=-4$ at codes 0 and 15, $-1$ at codes 5 and 10, $2$ at the 12 other bright codes, 0 at the 31 dark codes. No Lean theorem links `pairClass` to `couplingTable`.
5. `innerLabelCount` counts triangle-admissible $J$ per inner pair; the doc comment says "every admissible $J$ has an outer completion". That completion claim is not proved separately. But the 47 total matches the independently determined 47 valid inner codes (`table_lengths`, and `card_states_spinnet` = 433 using outer completions), so the number is not at risk.

Mutation tests (scratch copies in `<scratchpad>/mut/`, outside the repo, run with `lake env lean`; controls compile with zero errors):

| mutation | theorem that fails |
|---|---|
| `couplingTable[1]: 2 → 3` | `walk_table_exact` (decide: false) |
| `angleTable` last entry `3 → 4` | `walk_table_exact` |
| `frame`: `cx 0 2 → cx 0 3` | `frame_maps_flip` and `walk_table_exact` |
| `flagOps`: drop `.x 1` before the $G_2$ Toffoli | `flags_correct` and `walk_table_exact` |
| `validInnerCodes` first two entries swapped | `walk_table_exact` |
| `walkOps`: last pair `cx 14 0 → cx 13 0` | `walk_table_exact` |
| `jbit`: `J=2 → J=1` | `corner_jbit_injective` |
| `cornerJs`: drop the outer filter | all count theorems |
| `brightInner`: filter `≠ 2 → ≠ 1` | count theorems |
| `innerPairs`: first pair `(bit 0, bit 3) → (bit 0, bit 2)` (corner wiring) | count theorems |
| `pairClass`: classes 5/10 → 6/9 | none (still 96) |
| `pairClass`: alternating class = {3,12} | none (still 96) |
| `multAlt` evaluated at $n=6$ instead of 5 | none (still 16) |
| bright-pair representative bit 0 → bit 1 | none (still 8) |

Reading of the last four rows: every bright inner pattern has exactly 16 outer completions, so `mult_two`, `mult_half` and `mult_one` equal 16 times the number of pair representatives in a class and are insensitive to which patterns are assigned to which class. The theorems are true and are exactly what the plan and the locked test name, but they do not pin down the class assignment. That assignment is checked by the table above (numerical), not by Lean. Not a failure; recorded so that Report 3 words it as "pair-class counts" and not as "kernel-checked spectrum".

## Regression of results JSON (item 3)

`scripts/m3_results.py --out <scratch>` (11.1 s) compared with the committed `results/spinnet/{UE,UB,step}.json`:

- UE: 0 non-ignored differences (only timings, paths, provenance).
- UB: 40 numeric differences, largest 1.19e-15 (`spinnet_v2/pairs9/verification/dropped_total`); verification errors stay at $\sim10^{-15}$.
- step: 25 numeric differences, largest 8.4e-16 (`dropped_total`).
- Integer-valued fields (gate counts, T counts, depth, qubits): 0 differences in all three files.
- The `.qpy`/`.qasm3` of UB, step, pairs9, flags4, beta_0_05 and order2 differ byte-wise (the rz angles now come out as exact multiples of $\beta/2$, a $\le 6\times10^{-15}$ change); UE, UE_outer_row and paulo15 are byte-identical. The sha256 fields in the committed JSON therefore describe the old files; R1 passes since it checks the committed files against themselves. If the coordinator regenerates results before Report 3 (plan row 3.7: regenerate on a clean commit), these hashes and the fourth significant digit at $10^{-15}$ will change; nothing physical changes.

## Ownership (item 4)

`git status --short` shows exactly: `M lean/Su2Plaq.lean` (diff: the two lines `import Su2Plaq.SpinNet.Counts`, `import Su2Plaq.SpinNet.Circuit`, nothing else), `M src/su2plaq/spinnet/lean_export.py`, `M src/su2plaq/spinnet/walk.py`, `M tests/unit/test_spinnet_walk_unit.py`, `?? lean/Su2Plaq/SpinNet/` (`Counts.lean`, `Circuit.lean`), `?? tests/unit/test_spinnet_lean_export_unit.py`, plus my `results/spinnet/tester/` files. All are in track S's file list (prompts/100 §0). No acceptance test and no laptop-owned file was touched.

## Problems and assumptions

- Cosmetic, none blocking: `lake build` prints the existing laptop linter warnings (unused simp arguments, `module` hint) for files not under test.
- L3 stays PENDING until the laptop delivers the `Su2PlaqCert` checker.
- The tester's scratch Lean copies and `ev.lean` live in the session scratchpad, not in the repository.
- `LE.certify` and `LE.export_certificate` are still `todo()` stubs (step 3.L3, out of scope).
