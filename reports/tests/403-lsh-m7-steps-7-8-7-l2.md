# Tester report 403: LSH M7 steps 7.8 - 7.10, 7.L1, 7.L2

- Date: 2026-11-10 (tester, mode `step`)
- Git commit: `6d9bae8` (HEAD); the builder's work is UNCOMMITTED (dirty tree). Builder results in `results/lsh/` carry `git_commit 6beb713, git_dirty True`.
- Plan in force: `prompts/400-lsh-m7-plan.md` §3 steps 7.8, 7.9, 7.10, 7.L1, 7.L2; methods `docs/METHODS-lsh.md`
- Related reports: `reports/tests/400`, `401`, `402`
- Cores used: 14-19 only (`taskset -c 14-19`, pytest `-n 4`); all heavy jobs through `tools/run-capped` / `tools/pytest-safe`.

## Verdict: PASS

All named tests green, every builder-claimed number reproduced independently, Lean builds, all 12 relevant mutants either caught or shown to be equivalent. M7-L3 is PENDING only because step 7.L3 is not built (message: `PENDING: lean/Su2PlaqCert/LSH/Main.lean missing`). `acceptance-check` fails only because of the untracked `tests/acceptance/m2c/` (another planner), as predicted.

## Commands run

```
source ~/miniforge3/etc/profile.d/conda.sh && conda activate coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update .
taskset -c 14-19 tools/pytest-safe -n 4 -q tests/acceptance/m7                 # 28 pass, 1 PENDING (L3)
taskset -c 14-19 tools/pytest-safe -n 4 -q tests/unit                          # 922 passed, 580 s
pytest --collect-only -q tests/acceptance                                      # 341 collected, clean
python tools/check_lock.py                                                     # LOCK OK
~/.claude/bin/acceptance-check                                                 # FAIL: only untracked tests/acceptance/m2c/*
cd lean && PER_JOB_MEM=12G ../tools/run-capped taskset -c 14-19 lake build Su2Plaq   # Build completed successfully (9111 jobs)
tools/run-capped taskset -c 14-19 python results/lsh_tester/tester-403-wrap-exact.py 0.61 0.23 1.0
tools/run-capped taskset -c 14-19 python results/lsh_tester/tester-403-recount.py ; ...tester-403-compare-json.py
tools/run-capped taskset -c 14-19 python results/lsh_tester/tester-403-step-exact.py
results/lsh_tester/tester-403-mutants.sh, tester-403-mutants2.sh              # mutants on a COPY of the tree (scratchpad), never on src/
lake env lean <mutated Circuit.lean copies>                                    # Lean-side mutants
```

## Acceptance (m7), by id

| id | result |
|---|---|
| M7-V1[general7], [pairs9], [flags4] | PASS |
| M7-R1[UE], [UB], [step] | PASS (on the dirty-tree results, see note 1) |
| M7-L1 (counts) | PASS |
| M7-L2 (circuit structure) | PASS |
| the 20 earlier m7 tests (A1, K1, K2, X1, C1, C2, B1 x4, B2, B3, E1 x2, G1, S1 x2, T1 x3) | PASS |
| M7-L3 | PENDING (only reason: step 7.L3 not built; `lean/Su2PlaqCert/LSH/Main.lean` missing) |

Totals: 28 passed, 1 pending, 0 failed. Unit suite 922 passed, 0 failed. Collection clean (341 tests). `check_lock.py`: LOCK OK.

## Independent checks (own code in `results/lsh_tester/tester-403-*`)

Target for (a): the route-B 6j operator `exact.spinnet.h_magnetic_phys_6j` in label order with codes from `code_of_label` (NOT the encoding's own `target`). Circuits simulated with Aer statevector on every one of the 433 computational-basis inputs (data part; outer register idle), 19 qubits for general7 and 15 for the others. Error = $\|M - e^{i\varphi}T\|_2$ with $\varphi=\arg\mathrm{Tr}(T^\dagger M)$; leak = probability outside (ancilla $=0$, data in the 47 inner codes, state in the right outer block).

### (a) wrap_spinnet exact on all 433 states (`tester-403-wrap-exact.json`)

| check | expected | got (worst of 15 = 5 variants x $\beta\in\{0.61,0.23,1.0\}$) | tolerance | result |
|---|---|---|---|---|
| operator-norm error vs $e^{-i\beta H_B^{6j}}$ | 0 | $7.3\times10^{-15}$ | $10^{-10}$ | PASS |
| unitarity $\|M^\dagger M-1\|_2$ on the 433 states | 0 | $1.04\times10^{-14}$ | $10^{-10}$ | PASS |
| ancilla leak probability (max over inputs) | 0 | $6.3\times10^{-31}$ | $10^{-20}$ | PASS |
| data leak outside the 47 inner codes (prob.) | 0 | $2.0\times10^{-30}$ | $10^{-20}$ | PASS |
| span leak (inner code not physical in this outer block) | 0 | $2.1\times10^{-31}$ | $10^{-20}$ | PASS |
| gates on outer register (with_outer=True) | 0 | 0 | 0 | PASS |

Variants: general7, pairs9, flags4, flags5, flags6. Sensitivity controls (same runs): error against the identity $\ge 0.456$, against $U(-\beta)$ $\ge 0.888$, against $U(\beta/2)$ $\ge 0.229$ (so the check can fail). Also saved $U_B$, step o1 (target $U_BU_E$) and step o2 ($U_E(\alpha/2)U_BU_E(\alpha/2)$) QPY files simulated the same way (`tester-403-step-exact.json`): errors $5.7\times10^{-15}$, $5.6\times10^{-15}$, $5.8\times10^{-15}$ (controls 1.15, 0.68, 0.42). $U_E$ (8 `p` gates) and the outer row (20 `p`) phases equal $e^{-i\alpha h_E}$ from the 6j diagonal: $0$ and $1.3\times10^{-15}$ rad (`tester-403-UE-check.txt`).

### (b) counts recomputed from the saved `.qpy` files (`tester-403-recount.json`, `tester-403-compare-json.py`)

rccx lowered by Qiskit's own definition (3 CX, 4 T), T from `pygridsynth` per rotation (own call, not project code).

| quantity | builder claim | got (QPY) | JSON | result |
|---|---|---|---|---|
| U_E CX / rot / fixed T | 0 / 8 / 0 | 0 / 8 / 0 | same | PASS |
| U_E T(1e-4,1e-6,1e-8,1e-10) | | 352/512/656/832 | same | PASS |
| U_E outer row rot, T(1e-6) | 12 extra | 20 rot, 1280 | same | PASS |
| U_B CX / rot / fixed T / qubits | 94 / 4 / 88 / 19 | 94 / 4 / 88 / 19 | same | PASS |
| U_B T(eps) | 262/342/428/500 | 262/342/428/500 | same | PASS |
| step o1 CX / rot | 94 / 8 | 94 / 8 | same | PASS |
| step o1 T(eps) | 438/598/756/916 | 438/598/756/916 | same | PASS |
| step o2 (extra) | | 94 CX / 12 rot, T 598/870/1100/1332 | same | PASS |
| wrapped general7 CX/rot/Tfix/T(1e-6) | 94/4/88/342 | 94/4/88/342 | same | PASS |
| wrapped pairs9 | 74/9/56/608 | 74/9/56/608 | same | PASS |
| wrapped flags4 | 84/4/80/330 | 84/4/80/330 | same | PASS |
| wrapped flags5, flags6 | 82/5/72, 76/6/64 | 82/5/72 (T 382), 76/6/64 (T 434) | same | PASS |
| overhead of wrapping | +40 CX, +32 T | 94-54, 88-56 etc. for all 5 skeletons | | PASS |
| transcoder alone | 20 CX / 16 T / 0 anc | 4 sites x (2 CX + rccx) = 20 / 16 / 0 | same | PASS |
| max $|K_{LSH}-K_{6j}|$ (47x47) | 1.8e-15 | $1.78\times10^{-15}$ (and 433x433 $H_B$: $1.78\times10^{-15}$) | $10^{-12}$ | PASS |

### (c) Lean

| check | expected | got | result |
|---|---|---|---|
| `Circuit.lean` generated block vs `write_lean_tables` into a scratch copy | identical | `diff` empty | PASS |
| tables vs my own derivation (47 codes from route-B inner labels, $2K[\text{partner},c]$ from the 6j $K$, partner codes) | equal | all three lists equal | PASS |
| `lshAngles` $=[-7,-2,6,3]$ vs rz angles of `build_UB($\beta$)` | rz $=\beta\cdot a/2$ | ratios $-3.5,-1,3,1.5$ at $\beta=0.61,0.23$ | PASS |
| Lean `transOps+frameOps+flagOps+walkOps(+mirrors)` vs gate list of `UB.qpy` (H removed, rccx $\to$ ccx) | equal | 70 = 70 ops, equal | PASS |
| `lake build Su2Plaq` (12 GB cap, cores 14-19) | success | `Build completed successfully (9111 jobs)` | PASS |
| `sorry/admit/native_decide/axiom/unsafe` in `lean/Su2Plaq/LSH/*` | none | only the word "axioms" in a header comment | PASS |
| `#print axioms` of all 19 theorems (8 count, 4 site rules, 7+ structure) | standard only | `table_lengths` none; all others `[propext]` | PASS |

### (d) Mutants (run on a copy of the tree in the session scratchpad; real `src/`, `lean/` untouched, SHA-256 of all 11 builder files identical before and after)

| mutant | unit tests | acceptance | Lean | result |
|---|---|---|---|---|
| M1 drop the inverse transcoder | `test_wrap_spinnet_structure_and_overhead` FAIL | V1 x3 FAIL | | caught |
| M2 drop the forward transcoder | FAIL (same) | V1 x3 FAIL | | caught |
| M10 uncompute with forward T instead of inverse | FAIL | V1 x3 FAIL | | caught |
| M11 corner bits mapped to $w$ wires | FAIL | V1 x3 FAIL | | caught |
| M4 ancilla offset ignores outer register | 21 pass (not caught by unit) | V1 x3 FAIL | | caught by acceptance only |
| M12 `with_outer` ignored in wrap | FAIL | V1 x3 FAIL | | caught |
| M3 corner-bit wires cyclically permuted | pass | pass | | survives, EQUIVALENT (see note 2) |
| M9 link wires cyclically permuted | pass | pass | | survives, EQUIVALENT (see note 2) |
| M5 swap two `lshCoupling` entries (Lean file) | `test_generated_block_equals_python` FAIL | L2 FAIL | 3 `decide` errors | caught by all three |
| M6 one `lshAngles` int changed | same test FAIL | L2 FAIL | `decide` error | caught |
| M8 swap two `lshPartner` entries | same test FAIL | L2 FAIL | `decide` error | caught |
| M7 exporter `angle_ints` wrong order | `test_integer_tables`, `test_generated_block` FAIL | L2 FAIL | | caught |
| unmutated `Circuit.lean` via `lake env lean` | | | 0 errors | control OK |

## Notes and issues (none blocking)

1. Results in `results/lsh/` are from a DIRTY tree (`git_commit 6beb713`, `git_dirty True`; HEAD is now `6d9bae8`). M7-R1 passes on them, but prompts/400 step 7.10 says R1 must be green on a clean commit: regenerate `python scripts/m7_results.py` after committing (script wall time 10.5 s, peak 281 MB; plan estimated 1-2 min).
2. M3/M9 are equivalent mutants, not test gaps: at $j_{\max}=\tfrac12$ the 47-code coupling table $K$ takes the values $-2$ (all links 0), $-\tfrac12$ (all links $\tfrac12$), $1$ (two of four, 6 patterns), a symmetric function of the link bits, and the corner-flag logic is an AND over the four corners; the circuits are therefore invariant under permutations of link wires and of corner wires. Mixing link and corner wires (M11) is caught.
3. M4 (wrong ancilla offset with `with_outer=True`) is caught by the acceptance V1 test but NOT by the new unit test `test_wrap_spinnet_structure_and_overhead` (it checks register sizes and one `with_outer` register layout, not that the compose lands on the ancilla qubits). Suggest the builder add an evaluate call on `wrap_spinnet(sn, with_outer=True)` to the unit test.
4. `tests/unit/test_lsh_lean_export_unit.py::test_certificate_functions_are_stubs` asserts that `certify` / `write_pins` raise `NotImplementedError`; it will turn red on step 7.L3 and must be replaced then.
5. Unit suite ran while other agents edited rishon files (not my scope); 922 passed regardless.
6. `acceptance-check` message: `tests/acceptance differs from acceptance-v17`, untracked `tests/acceptance/m2c/{test_consolidation_evaluator,test_consolidation_gate,test_consolidation_registry}.py`; `git status --short tests/acceptance` shows only `?? tests/acceptance/m2c/`; no modified locked file; `check_lock.py` LOCK OK.

## Files my runs touched

Created: `/home/digimonk/Projects/su2qc-encoding/results/lsh_tester/` (`tester-403-wrap-exact.{py,json}`, `-recount.{py,json}`, `-compare-json.py`, `-step-exact.{py,json}`, `-K-check.txt`, `-UE-check.txt`, `-lakebuild.log`, `-mutants.sh`, `-mutants2.sh`, `-mutants.log`, `-mutants2.log`), this report, and scratch files under the session scratchpad (`.../scratchpad/mut/` copy of the tree, `Circuit.regen.lean`, `leanmut_*.lean`, `axioms.lean`, `baseline.*`). `lake build` refreshed `lean/.lake/build` (no source change). The pytest runs may have rewritten test byproducts (`results/*/certs`, `compress/lean/structure*.json`, `compress/cache/gridsynth/*`); I did not inspect which. No file under `src/`, `lean/` sources, `tests/` or `scripts/` was edited (builder files verified by SHA-256 before and after).
