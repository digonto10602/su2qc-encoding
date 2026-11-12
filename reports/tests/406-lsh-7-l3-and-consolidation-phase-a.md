# Tester report 406: LSH step 7.L3 (native certificate) and consolidation Phase A (prompts/008 A1, A2)

- Date: 2026-11-11. Git: `c34c392` (HEAD; only `notes/STATUS.md` differs from `4733370`), working tree with the uncommitted builder files.
- Plans in force: prompts/400 section 3 and 4 (LSH, step 7.L3); prompts/008 (Phase A). Acceptance lock: acceptance-v18.
- Mode: step. Cores 14-19 (`taskset -c 14-19`, `-n 6`). Related reports: 400-403 (LSH), 404, 405.
- Raw numbers and scripts: `results/lsh_tester/tester-406-{independent,tamper,flaky,structure}.{py,json}`.

## Verdicts

| Scope | Verdict |
|---|---|
| 1. LSH 7.L3 | PASS |
| 2. prompts/008 Phase A (A1, A2) | PASS |

Counts: unit 932 passed / 0 failed; m7 29 passed / 0 failed (including M7-L3); m2 46 passed / 0 failed (including 6 slow); m2c 28 failed, all `PENDING:` (24 "cannot import su2plaq...", 1 "evaluator.evaluate ha...", 3 "evaluator.Verdict has..."), 0 non-PENDING; new failures vs. report 404: none. `pytest --collect-only -q tests/acceptance` clean (341 tests). `tools/check_lock.py` LOCK OK; `acceptance-check` PASS (matches acceptance-v18).

## Commands

```
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
taskset -c 14-19 tools/pytest-safe -n 6 -q tests/acceptance/m7              # 29 passed in 15.7 s
taskset -c 14-19 tools/pytest-safe -n 6 -q tests/unit                       # 932 passed in 627 s
taskset -c 14-19 tools/pytest-safe -n 6 -q tests/acceptance/m2              # 46 passed in 211 s (incl. slow)
taskset -c 14-19 tools/pytest-safe -n 6 -q tests/acceptance/m2c             # 28 PENDING
pytest --collect-only -q tests/acceptance; python tools/check_lock.py; ~/.claude/bin/acceptance-check
cd lean && PER_JOB_MEM=16G ../tools/run-capped taskset -c 14-19 lake build su2plaq_cert_lsh
taskset -c 14-19 tools/run-capped python results/lsh_tester/tester-406-{independent,tamper,structure}.py ; python results/lsh_tester/tester-406-flaky.py
```

## Scope 1: LSH step 7.L3

| Check | Expected | Got | Tolerance | Result |
|---|---|---|---|---|
| `lake build su2plaq_cert_lsh` | builds | "Build completed successfully (42 jobs)" (artifact already up to date, 0.9 s; binary `.lake/build/bin/su2plaq_cert_lsh` present) | - | PASS |
| `sorry`/`admit`/`native_decide`/`axiom`/`unsafe` in `lean/Su2PlaqCert/LSH/*.lean` | none | none (grep) | - | PASS |
| `#print axioms` of `LSH.check`, `LSH.accepts`, `LSH.checkJsonString` | standard only | `[propext, Classical.choice, Quot.sound]`; `Pins.statesSha256`: no axioms | - | PASS |
| Own Laurent evaluation vs dense `scipy.linalg.expm` of `enc.h_magnetic()` / `h_electric()`, 6 angle pairs (3 nominal/alternate + 3 random in $[-3,3]$, seed 406), $U_E$, $U_B$, step o1, step o2 | equal | max $9.1\cdot10^{-16}$ | $10^{-12}$ | PASS |
| Same vs `enc.target` | equal | max $9.1\cdot10^{-16}$ | $10^{-12}$ | PASS |
| Unitarity of the exported Laurent target, $\max\|V^\dagger V-1\|$ | 0 | $\le 8.8\cdot10^{-16}$ | $10^{-12}$ | PASS |
| $H_B$ spectrum (independent `eigvalsh`) | $\{0,\pm\tfrac12,\pm1,\pm2\}$ | exactly these 7 values (9 digits) | $10^{-9}$ | PASS |
| Electric weight $\tfrac34\sum_c N_n(c)$ | equals $H_E$ | $\max\|H_E-\tfrac34 n\|=0$; also $H_E=\sum_{4\ \rm inner}j(j+1)$ from the labels, 0 difference (n range 0..4) | $10^{-12}$ | PASS |
| Bases | (4,4) for UE, UB, step o1; (8,4) for step o2 | `{'UE:1': (4,4), 'UB:1': (4,4), 'step:1': (4,4), 'step:2': (8,4)}` | exact | PASS |
| Certify $U_E$ (24 q, with outer), $U_B$ (31 q), step o1, step o2 at (0.37, 0.61) | `certified` | all `certified`; export+check wall 1.04 s, 0.90 s, 0.34 s, 0.35 s (checker alone 1.02, 0.28, 0.29, 0.29 s); M7-L3 itself far below the 900 s budget | 900 s | PASS |
| Certificate independent of the angle pair (step o1 at (0.91, 0.23), (1.70, 1.00)) | same gate list, certified | same circuit id `lsh-step-o1-ddc1571c27bd`, certified | - | PASS |
| `with_outer=False` d-only step | certified | certified | - | PASS |
| Negative: $U_B$ circuit vs step target | rejected | `rejected: state 0 differs from the target` | - | PASS |
| Negative: $-\beta$ ($U_B(-\beta)$ vs $U_B$; step with $-\beta$) | rejected | rejected (both, state 0) | - | PASS |
| Negative: $\beta(1+10^{-6})$ | `n_a` (`non_linear_angle`) | `n_a: non_linear_angle:rz:-2.135002135` | - | PASS |
| Negative: $\alpha(1+10^{-6})$; $\alpha=0.38$ | `n_a` | `n_a: non_linear_angle:p:...` (both) | - | PASS |
| Negative: o1 circuit vs o2 target, o2 circuit vs o1 target, $U_E$ circuit vs $U_B$ target | rejected | rejected (state 0 differs) | - | PASS |
| `Pins.lean` equals a fresh `render_pins_lean(compute_pins())` | equal | `True`; the Lean `fingerprint` of the states and of the UB / step-o1 / step-o2 targets appear verbatim in `Pins.lean` | exact | PASS |
| m7 acceptance, including `test_M7_L3_native_certificate_general_step` | 29 / 29 | 29 passed (15.7 s) | - | PASS |

### Tampered certificates (crafted by me from `results/lsh/certs/lsh-step-o1-ddc1571c27bd.json`; 252 gates, 433 states, 305 target blocks)

The untampered file is ACCEPTed (0.20 s). 40 of 41 tampered variants are REJECTed with the checker's own reason; the one "accept" is benign (below). Excerpt (full list in `tester-406-tamper.json`):

| Tamper | Checker output |
|---|---|
| cx target changed / cx reversed / T to Tdg / H to X / gate removed / X appended on a data, outer or ancilla wire | `REJECT state k differs from the target` |
| rz or p exponent changed | `REJECT rz exponent vector must be even` or `state 164 differs from the target` |
| gate qubit 99; `n_qubits` 30 (ancilla use) | `REJECT gate qubit .. out of range` |
| one state removed (last / middle) | `certificate has 432 states, the physical subspace has 433` / `state index 432 out of range` |
| state code bit flipped, sign flipped, `k` labels swapped, terms swapped between `k` | `states differ from the pinned exact LSH states (SHA-256)` |
| support on an ancilla qubit | `state has support on an ancilla qubit` |
| extra / duplicated state | `duplicate state index 0` |
| target coefficient / exponent changed, entry or block removed, `ks` reversed | `target differs from the pinned exact step target (SHA-256)` |
| target kind label changed to UB | `target differs from the pinned exact UB target` |
| target order label 2 | `base must be a positive multiple of the target's base` |
| phase $m$ or $k$ changed | `state 0 differs from the target` |
| base $d_\beta=8$ / $d_\alpha=3$ | pinned-target mismatch / base error |
| register size: `n_data` 11, `n_outer` 11, 8+8 (spin-network sizes) | `the LSH encoding has 12 data and 12 outer qubits` |
| `n_qubits` 20 / 63 | `register sizes exceed n_qubits` / `more than 62 qubits` |
| wrong schema | `unknown schema su2plaq-cert-2` |
| spin-network certificate in the LSH checker; LSH certificate in the spin-network checker | REJECT in both (register-size messages) |

Benign "accept": swapping the list positions of two state records while keeping their `k` fields (the checker indexes by `k`; the set is identical, and swapping the `k` fields or the terms is rejected). Not a soundness gap.

### Notes on scope 1 (not failures)

- The plan asks for the electric weight, bases and pins, which all agree. There is no per-circuit Lean theorem file for LSH (spinnet has `lean/certs/spinnet-best-step.lean` using `native_decide`); prompts/400 7.L3 does not require one, so "`#print axioms` of the cert theorem" was applied to the checker functions instead (standard axioms only).
- `test_lean_sources_hygiene` (builder) scans only `Counts.lean` and `Circuit.lean` for `sorry`/`admit`/`native_decide`, not the three new `Su2PlaqCert/LSH` files; I grepped them manually (clean). Cosmetic: `Main.lean` header says "copy of `su2plaq_cert_lsh`" (should read `su2plaq_cert_spinnet`).
- The untracked `results/lsh/certs/lsh-step-o1-ddc1571c27bd.json` (147 KB, 252 gates, circuit id = gate-list hash, so one stable file name). Recommendation: COMMIT it, as spinnet commits its 7 certificates (`results/spinnet/certs/`, 106-145 KB each); it is the replayable evidence for the Report 7 "native-certified" row and it re-checks with `su2plaq_cert_lsh check` in 0.2 s. Churn caveat: the L3 test rewrites it on every run with a new `provenance.git_commit` and `export_seconds` (same as spinnet), so a committed copy will show as modified after test runs; `git checkout -- results/lsh/certs` restores it. The scratch certificates I generated are under `scratch/tester406certs/` (gitignored) only.

## Scope 2: prompts/008 Phase A

| Check | Expected | Got | Result |
|---|---|---|---|
| `compress.provenance.code_hash()` (shared) | `0bd7e7d9...` unchanged vs HEAD | `0bd7e7d91d9d7bcfc78641d1a14bb87f0f82f932c41c601fb991d30de13a0582` working tree and `git archive HEAD` | PASS |
| `spinnet.loop.code_hash()` | `7f5bb7f8...` | `7f5bb7f8e65f39c89eca59abae352c3f36433e00523ae3321f9b6e59e54d0ed5` both | PASS |
| `rishon.compress.code_hash()` | `055b2107...` | `055b21078b487a47468b23e96413f5f86ba4d732b78da16dbb3a34016d5f165c` both | PASS |
| Why unchanged | `lean/structure.py` and `lsh/lean_export.py` are not in `EVALUATOR_FILES` / `SPINNET_CODE_FILES`; `git diff HEAD --stat -- src` shows only those two files | consistent | PASS |
| Flaky test cannot fail for any hex commit | argued from code and measured | `render()` prints only static headers, numbers, `circuit_id` and `git_commit (+ "*")`; `zq-second` contains `z` and `q` (not hex), so it cannot appear from a hexadecimal commit hash. Stress: 305 commits (`c1c1c1c`, `c0c0c0c`, `0000000`, `fffffff`, 300 random 7-hex, seed 406): new test body 0 failures; the OLD test (ids `c0`/`c1`) fails for 9 of the same 305 commits (about 3 %), so the fix is real. Also `test_results_unit.py` 3 x 6 passed | PASS |
| `write_structure_json` second run byte-identical | identical | fresh file: identical; copy of the working-tree `compress/lean/structure.json`: identical after the run (so it is current with the present exporter hash) | PASS |
| Changing only `git_commit`, only `seconds`, both | no rewrite | not rewritten (3 / 3) | PASS |
| Changing a fact value, dropping a fact, a symmetry, certificate `status`, `checker_sha256` | rewritten | rewritten (5 / 5); corrupt (non-JSON) file also rewritten | PASS |
| The regenerated `compress/lean/structure.json` vs HEAD | only provenance changed | `facts` and `symmetries` equal; provenance diff keys `git_commit`, `exporter_sha256`, `structure_certificate.seconds`. The HEAD version is rewritten by a run because `exporter_sha256` is stale (the exporter file `lean/structure.py` changed); after all my test runs the working-tree file is still byte-identical to the builder's version | PASS |
| m2 acceptance, all 46 incl. 6 slow | green | 46 passed in 211 s (`tests/acceptance/m2`) | PASS |
| m2c | fail only as PENDING | 28 failed, all `PENDING:` (list above) | PASS (pending) |
| Unit suite | green | 932 passed in 627 s (`--collect-only` also gives 932; the commit message of 89752b4 quoted 932 too, so the count in the repo at HEAD may already have included the builder's new tests, or the quoted figure was taken after them) | PASS |

Observation: `exporter_sha256` is part of the stable content (a hashed exporter edit forces one rewrite, as intended), `git_commit` is intentionally not.

## Files touched by my runs

Created: `results/lsh_tester/tester-406-{independent,tamper,flaky,structure}.{py,json}`, this report; scratch only: `scratch/tester406certs/`, `scratch/tester406tamper/`, `scratch/tester406struct/`, `scratch/tester406-m2*.{log,txt}`. Tests rewrote `results/lsh/certs/lsh-step-o1-ddc1571c27bd.json` (same name, new provenance). `results/spinnet/certs/*` and `compress/lean/structure.json` show no diff vs the state I found (checked with `git diff --stat`), so nothing had to be restored. No source, acceptance test or tolerance edited.

## Overall

Both scopes PASS; no failures. The three minor notes (no LSH theorem file, hygiene test covers only two Lean files, `Main.lean` header typo) are suggestions for the builder, not blockers.
