# Tester report 437: LSH M8 step 8.5, real seed round 0 (mode step)

- Date: 2026-11-19. Commit `7afc110` (HEAD; the round ran on `58e4574`, and `7afc110` differs from it only in `notes/STATUS.md`). Round-0 outputs are uncommitted in the tree.
- Prompt in force: `prompts/401` (LSH M8), step 8.5 and section 1.3. Related: `reports/tests/436` (dry run of steps 8.2-8.4), `reports/tests/428`.
- Raw numbers: `results/tester/437-summary.json`, `437-indep-aer.json`, `437-l3-seed.json`, `437-archive-checks.json`, logs `results/tester/437-raw/`.
- Scripts I added (not collected as tests): `tests/independent/lsh_round0_437/{indep_all,archive_checks,l3_seed}.py`; they reuse `tests/independent/lsh_m8_436/indep_check.py`.
- Resources: `taskset -c 6-8`, `tools/pytest-safe -n 2`, heavy runs under `tools/run-capped`.

## Commands
```
python tests/independent/lsh_round0_437/indep_all.py                 # Aer + recount, 9 program files
python tests/independent/lsh_round0_437/archive_checks.py <scratch>  # archive / round / stop / pins / Lean certificate
python tests/independent/lsh_round0_437/l3_seed.py <scratch>         # circuit-valued seed qiskit_l3
tools/pytest-safe -n 2 -m "not slow or slow" tests/acceptance/m8 -v -rA
tools/pytest-safe -n 2 -m "not slow" tests/acceptance/m7
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
```

## Results
Key = (CX, $T_{10^{-6}}$, depth$_{\rm CT}$, qubits).

| # | check | expected | got | tolerance | verdict |
|---|---|---|---|---|---|
| 1a | 10 archive entries valid, keys vs prompts/401 section 1.3 (and the 436 dry run) | general (94,598,880,31); pairs9 (74,864,1615,27); flags4 (84,586,888,27); flags5 (82,638,1027,27); flags6 (76,690,1139,27); sn_headline (71,1118,2276,25); r05F3 (72,864,1570,25); r02F5 (74,690,1134,25); polish and qiskit_l3 (94,598,880,31) | 10 valid, 0 invalid; archive key = round key = expected for all ten; $N_{\rm rot}/T_{\rm fixed}$ equal the plan column (8/88, 13/56, 8/80, 9/72, 10/64, 17/48, 13/56, 10/64) | exact | PASS |
| 1b | evaluator verdicts of the archive | ok at nominal and both alternates | all ten `ok`, `alt_ok` = [true, true]; archive op-norm error from $8.9\cdot10^{-15}$ (headline) to $1.8\cdot10^{-14}$ (qiskit_l3) | $\sim10^{-10}$ | PASS |
| 2a | own Aer statevector (target from the L13 rules, own 47 inner codes, outer register verified untouched, ancillas traced) on all 9 program files at $(0.37,0.61)$, $(0.91,0.23)$, $(1.7,1.0)$ | op-norm error $\le10^{-10}$ | max over 27 runs $6.3\cdot10^{-15}$ (flags4 at (1.7,1.0)); headline $3.15, 3.24, 3.81\cdot10^{-15}$; ancilla leak probability $\le6.5\cdot10^{-31}$; data weight outside the 47 codes 0 | $10^{-10}$ | PASS |
| 2b | headline at an unused pair $(1.13,0.47)$ | $\le10^{-10}$ | $2.84\cdot10^{-15}$, ancilla leak $3.8\cdot10^{-31}$ | $10^{-10}$ | PASS |
| 2c | wrong-sign control: same circuits against the target at $-\beta$ | must disagree | $1.878$ for all 9 programs (a genuine $O(1)$ separation) | | PASS |
| 2d | circuit-valued seed `qiskit_l3` (no program file), rebuilt through `seed_candidates` in a scratch root, Aer at 3 pairs | exact | $5.4, 5.2, 5.8\cdot10^{-15}$, leak $\le6\cdot10^{-31}$ | $10^{-10}$ | PASS |
| 3 | own CX/T recount (decompose, pygridsynth $\varepsilon=10^{-6}$, multiples of $\pi/4$ counted fixed) | = archive keys | all nine program files: (CX, $T$) = (94,598), (74,864), (84,586), (82,638), (76,690), (71,1118), (72,864), (74,690), (94,598); headline $T_{\rm fixed}=48$, $N_{\rm rot}=17$, $T_{\rm rot}=1070$; qubit counts 31/27/25 equal | exact | PASS |
| 4a | program sha256: file on disk = archive entry = round file (9 program files) | equal | equal for all nine (`005`: `01effa8d…`) | exact | PASS |
| 4b | regenerated seed programs (fresh `seed_candidates` in a scratch root) vs committed files | byte-equal | 9/9 identical; `qiskit_l3` has no file (empty sha in the entry, `program_path` points to a non-existent `qiskit_l3.circuit`, by design 1.3) | | PASS (see O2) |
| 4c | hashes | `evaluator_sha256 = encoding_sha256 = code_hash_for("lsh")` in round file, 10 entries and robust.json | all `88e0d76bce7b3af635fc895b469d9b2db38c34a69d6ea86c3049f3f9526ec1ca`; `git_dirty` false, commit `58e4574` in the entries | exact | PASS |
| 5a | Lean certificate `results/lsh/certs/lsh-step-o1-975e51bd4fed.json`, re-check with the compiled `su2plaq_cert_lsh` | ACCEPT | `certified` (0.88 s), checker sha `16b3278f…` equals the archive's | | PASS |
| 5b | binding: `provenance.program_file_sha256` = sha256 of `005-wrap_sn_headline.py` = archive `program_sha256` | equal | `01effa8d…` three ways; `gates_sha256` (`975e51bd4fed…`) = sha256 of the gate list = file-name suffix; 433 states, kind `step`, 25 qubits, 175 gates; provenance `git_dirty` false | exact | PASS |
| 5c | independent re-export of the certificate from the program file (fresh build, scratch dir) | same data | gates, target, states, phase and `gates_sha256` all equal; the re-export also `certified` | exact | PASS |
| 5d | negative control: swap control and target of the first CX in the gate list | `rejected` | `rejected` | | PASS |
| 6a | `round-000.json`: external rows | `paulo15_wrapped` valid, 108 CX, kind `UB`, $\beta=-0.05$ | valid, certified, 108 CX, $N_{\rm rot}=4$, $T_{\rm fixed}=96$, total error $1.3\cdot10^{-14}$; other rows `qiskit_l3_whole` (counts only, unverifiable) and the `spinnet15` redirect string | | PASS |
| 6b | pinned-source record `lsh.wrapped_sources` | pins of 1.3 | 3 sources; file sha256 = pin = spinnet archive `program_sha256` for `r02-F1-002`, `r05-F3-005`, `r02-F5-002` (`750151e9…`, `43605421…`, `734a62fe…`); the three files are unmodified against `HEAD` | exact | PASS |
| 6c | `round-000.json` synthesis verification | ok | `r00-seed-005`: $T=1118$, 17 rotations, certified, op-norm error $4.6\cdot10^{-6}\le1.7\cdot10^{-5}$ | | PASS |
| 6d | `stop.json` first record | headline `r00-seed-005`, robust key $(71,22480,0,46384,25)$, improved true, streak 0, sessions 0 | exactly that; also `stop` false, `max_rounds` 8, `no_gain_rounds` 3, `max_sessions` 20 | exact | PASS |
| 6e | `robust.json` (written) | all nine program seeds with $\rho=0$ | headline key $(71,22480,0,46384,25)$; others e.g. general (94,11852,0,17325,31), r05F3 (72,17588,0,33585,25); hashes `88e0d76b…`; 20-pair angle set seed 20261107. `summary.json` not written (belongs to the end of the loop) | | PASS |
| 7a | m8 acceptance, all (slow too), `-n 2` | G1-G4, L5, R1 now find the archive | 30 passed, 3 failed (below). G1 (re-verify from source) PASS, G2 (second engine Aer) PASS, G4 (unseen angles) PASS | | see 7b |
| 7b | m8 failures | later-step artefacts only | G3: `compress/ideation/lsh.md` missing (ideation file, being produced in parallel; the test also needs the stop-rule outcome of the finished loop); L5: `lean/certs/lsh-best-step.lean` missing (step 8.8); R1: `results/lsh/m8-compressed.json` missing (step 8.9/8.10, message "PENDING"). All three fail on a missing later artefact, not on round-0 content; the earlier assertions in G3 (attempts file, round budget) pass | | 3 PENDING (later steps) |
| 7c | m8 remaining 30 (E1, E2, S0-S5, S1 x8, H1-H3, L1-L3, A1-A4, U1, G1, G2, G4) | green | all pass | | PASS |
| 7d | m7 not slow | green | 28 passed | | PASS |
| 7e | `check_lock.py`, `acceptance-check`, collection | OK | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v22`; 407 tests collected | | PASS |
| 7f | six frozen hashes | unchanged | twelve `99663fa6`, lsh `88e0d76b`, spinnet `10f5727f`, fuzzy_ub = fuzzy_link `b4bd20fe`, rishon `5f5decfa`, spinnet loop `f1314a01` | exact | PASS |
| 7g | tree side effects | no tracked file rewritten, no new file in `results/lsh/certs/` | `git status` shows only untracked round-0 outputs and my `437` files; `certs/` listing identical before and after (`…975e51bd4fed.json` = the round's, `…ddc1571c27bd.json` tracked) | | PASS |

## Verdict
PASS. 0 failed checks; 3 PENDING locked tests (M8-G3, M8-L5, M8-R1), each waiting for a later step; no new failure compared with report 436.

Counts: tester checks 24 PASS, 0 FAIL; m8 acceptance 30 passed / 3 pending; m7 not slow 28 passed.

Physics statement: all ten round-0 programs reproduce the exact one-step target $U_B U_E$ on the 47 inner codes (433 physical states) to $\le6.3\cdot10^{-15}$ at four angle pairs, against $10^{-10}$ allowed, and the wrong-sign target is $1.878$ away, so the check can fail. The round-0 best is the wrapped spin-network headline at 71 CX, i.e. the recoding cost (transcoder $+40$ CX) was not reduced in round 0, as the plan expects.

## Observations (non-blocking)
- **O1.** The task text said "robust.json/summary.json if written"; only `robust.json` exists (round 0), as expected.
- **O2.** The archive entry `r00-seed-qiskit_l3` carries `program_path = compress/programs/lsh/seed/qiskit_l3.circuit`, a path that does not exist, with an empty `program_sha256`. This follows 1.3 (circuit-valued seed), but a later replay or a test that opens `program_path` for every entry would fail on it. G1, G2, G4 (best/headline only) are unaffected.
- **O3.** The Lean certificate of the best entry carries `program_file_sha256` but no `entry_id` (that appears only in the 8.8 `certify_headline` certificate). Consistent with report 436 O1/O2; the compiled checker never reads the provenance block, so the binding is checked by data comparison (5b) and by M8-L5 later.
- **O4.** M8-G3 will need the ideation file at `compress/ideation/lsh.md`; the parallel ideation run currently writes `compress/briefs/lsh/ideation.md` (untracked), which is a different path. Guess: coordinator copies or the ideation step is expected to write it later; not a round-0 defect.
- Wall time of the real round 25 s (round file `wall_s` 15.2 s, Lean 1.03 s). No benchmark requested.
