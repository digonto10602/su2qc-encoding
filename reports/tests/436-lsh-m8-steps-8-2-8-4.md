# Tester report 436: LSH M8 steps 8.2, 8.3, 8.4 (mode step)

- Date: 2026-11-19. Commit at start `9761c72` (HEAD moved to `ec38370` during the run by STATUS and report commits only; `git diff HEAD` touches only `src/su2plaq/lsh/loop.py` and `tests/unit/test_lsh_loop_unit.py`).
- Prompt in force: `prompts/401` (LSH M8), steps 8.2 (hooks, spec), 8.3 (seed round, stop rule), 8.4 (Lean hook, `certify_headline`). Related: `reports/tests/428`, `435` (gate tester running in parallel, not touched), `reports/research/401`.
- Builder files under test (uncommitted): `src/su2plaq/lsh/loop.py`, `tests/unit/test_lsh_loop_unit.py`, new `compress/programs/lsh/seed/000-general.py`, new `compress/specs/lsh-step.md`.
- Raw numbers: `results/tester/436-summary.json`, `436-indep-aer.json`, `436-lean-binding.json`, logs in `results/tester/436-raw/`. Scripts I added: `tests/independent/lsh_m8_436/{indep_check,lean_binding}.py`, `tests/unit/test_lsh_stop_state_tester436.py` (8 tests).
- Resources: `taskset -c 6-8`, `tools/pytest-safe -n 2`, heavy runs under `tools/run-capped`.

## Commands
```
tools/pytest-safe -n 2 -q tests/acceptance/m8 -k "E1 or E2 or S0 or S2 or S5 or L2 or S3 or S4 or H1 or H2 or L1"
env -i ... PYTHONPATH=src python -m su2plaq.compress.run_candidate compress/programs/lsh/seed/000-general.py --encoding lsh --kind step --trial
tools/pytest-safe -n 2 -m "not slow" tests/acceptance/m8 | m7 | m2c ; tests/acceptance/m4 -k S8 ; m6 -k H1
tools/pytest-safe -n 2 -m slow tests/acceptance/m8 ; tools/pytest-safe -n 2 tests/unit -k "lsh or registry"
tools/run-capped python -m su2plaq.lsh.loop seed --no-lean --dry-run --root <tmp>      (and a second one with Lean on)
tools/run-capped python tests/independent/lsh_m8_436/indep_check.py ...   (Aer)
tools/run-capped python tests/independent/lsh_m8_436/lean_binding.py ...
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
```

## Results
| # | check | expected | got | tolerance | verdict |
|---|---|---|---|---|---|
| 1a | m8 ids E1 E2 S0 S2 S5 L2 S3 S4 H1 H2 L1 (+ the two S1 cases the `-k` also selects) | all green | 13 passed, 129 s | exact | PASS |
| 1b | fresh-shell `run_candidate 000-general.py --trial` | exit 0, valid, total error $\sim10^{-14}$, CX 94, 31 qubits | exit 0; valid; `total_error` $1.626\cdot10^{-14}$ (block $4.9\cdot10^{-15}$, pruning $1.1\cdot10^{-14}$), Gauss $5.1\cdot10^{-16}$; CX 94, $T_{\rm fixed}$ 88, $N_{\rm rot}$ 8, qubits 31; 4.6 s | $10^{-10}$ | PASS |
| 1c | m8 not slow | none red | 22 passed, 0 failed, 125 s | | PASS |
| 1d | m8 slow (rest) | A2, A3, L3 green; G1-G4, L5, R1 belong to steps 8.5-8.9 | 5 passed (A2, A3, H2, L1, L3); 6 PENDING: `compress/archive/lsh missing (prompts/401 step 8.6: round 0)` (G1-G4, L5, R1) | | PASS, 6 PENDING (later steps) |
| 1e | m7 not slow / m4 `S8` / m6 `H1` / m2c not slow | unchanged | 28 / 1 / 1 / 18 passed | | PASS |
| 1f | unit `-k "lsh or registry"` | green | 144 passed, 53 s | | PASS |
| 1g | collection | clean | 407 tests collected, no error | | PASS |
| 2a | dry seed round (own temp root, Lean off), 10 keys $(\mathrm{CX},T_{10^{-6}},\mathrm{depth}_{\rm CT},\text{qubits})$ | prompts/401 section 1.3 | general (94,598,880,31); wrap_pairs9 (74,864,1615,27); wrap_flags4 (84,586,888,27); wrap_flags5 (82,638,1027,27); wrap_flags6 (76,690,1139,27); wrap_sn_headline (71,1118,2276,25); wrap_sn_r05F3 (72,864,1570,25); wrap_sn_r02F5 (74,690,1134,25); general+polish and qiskit_l3 (94,598,880,31). 10 valid, 0 invalid, best 71 CX | exact | PASS (all ten equal to the plan) |
| 2b | robust headline key of round 0 | $(71,22480,0,46384,25)$, research 401 | `r00-seed-005`, $(71,22480,0,46384,25)$, $\rho=0$, $N_{\rm rot}=17$, $T_{\rm fixed}=48$ | exact | PASS |
| 2c | external rows | `paulo15_wrapped` valid, 108 CX | valid, certified, 108 CX; also `qiskit_l3_whole` (94 CX counts only) and a `spinnet15` string row | | PASS |
| 2d | hashes in the round | `evaluator_sha256 == encoding_sha256 == code_hash_for("lsh")` | both `88e0d76b…` | exact | PASS |
| 2e | `000-general.py` in the repo equals the one the dry round generates | same bytes | sha256 `70d0f552…` both | exact | PASS |
| 2f | own Aer statevector, headline (`005`, 13 simulated qubits: 12 data + 1 ancilla, outer untouched), own target from the L13 rules (47 codes from the Abelian Gauss law, $K$ from the $\sum\ell_{nv}$ rule, electric phase $\tfrac34\sum_c(\ell_{pn}+\ell_{nv})$), after one global phase | error $\le10^{-10}$ at $(0.37,0.61)$, $(0.91,0.23)$, $(1.7,1.0)$ | op-norm error $3.15\cdot10^{-15}$, $3.24\cdot10^{-15}$, $3.81\cdot10^{-15}$; ancilla leak probability $\le3.2\cdot10^{-31}$; data weight outside the 47 codes $0$; against the target at $-\beta$: $1.878$ (rejected) | $10^{-10}$ | PASS |
| 2g | same, general (`000`, 19 qubits), also `006` r05F3 and `002` flags4 | as above | general $5.2,5.2,5.8\cdot10^{-15}$; r05F3 $3.9,3.9,4.1\cdot10^{-15}$; flags4 $5.3,5.1,6.3\cdot10^{-15}$; $-\beta$ gives $1.878$ for all; ancilla leak $\le6.5\cdot10^{-31}$ | $10^{-10}$ | PASS |
| 2h | no outer write, ancillas clean | no gate on `o` | no gate touches any `o[12..23]` qubit in the four programs (script asserts it, also as a control) | exact | PASS |
| 2i | own recount (decompose to CX + `rz`/`p`/T, pygridsynth $\varepsilon=10^{-6}$, rotations that are multiples of $\pi/4$ counted as fixed) | the archive keys | headline CX 71, $T_{\rm fixed}$ 48, $N_{\rm rot}$ 17, $T_{\rm rot}$ 1070, total 1118; general 94, 88, 8, 510, 598; r05F3 72, 56, 13, 808, 864; flags4 84, 80, 8, 506, 586 | exact | PASS |
| 3 | `stop_state` on synthetic `stop.json` + attempts (8 new unit tests) | streak, band, sessions, caps as the rule text | all 8 pass: round 0 improves; streak counts 1, 2, 3 and stops with `no_gain` at 3; an improvement resets the streak; the $20N_{\rm rot}$ band is measured against the last improving record, not the previous round (no drift); band edge exactly 20 is a tie, 21 improves; a changed $T_{\rm fixed}$ or CX counts through the plain comparison; ties are decided by $\rho$ then qubits; sessions = distinct (round$\ge1$, family) + 1 for the ideation file, round-0 rows not counted; 20 sessions give `max_sessions`, 19 not; last round 8 gives `max_rounds`, 7 not; empty root is safe | exact | PASS |
| 4a | Lean: general step and wrapped headline through `lean_certify` with binding | `certified`, binding fields inside | both `certified` (6.0 s and 1.2 s); `entry_id` and `program_file_sha256` in `provenance`, the latter equals the sha256 of the program file on disk; `gates_sha256 == program_sha256`; 433 states, kind `step`; recomputed `gates_sha256` = sha256 of `json.dumps(gates)` | exact | PASS |
| 4b | $-\beta$ circuit | `rejected` | `rejected`, "state 0 differs from the target" | | PASS |
| 4c | non-linear angle | `n_a` | `n_a`, `non_linear_angle:p:-0.1545`; `angle_linear` hook returns `(False, 'non_linear_angle:…')`; general `(True, 'ok')` | | PASS |
| 4d | tamper: one CX of the gate list swapped | checker rejects | `rejected`, "state 16 differs from the target" (both programs) | | PASS |
| 4e | tamper: program file changed by one comment, archived sha unchanged | mismatch raised | `ProgramShaMismatch` raised out of `round._circuit_of` (loud, not swallowed) | | PASS |
| 4f | tamper: `entry_id` or `program_file_sha256` edited inside the JSON | binding mismatch detectable | my comparison flags the mismatch; the compiled checker still answers `certified` (it never reads the provenance block: the binding is data that the theorem file embeds and the locked test M8-L5 compares) | | PASS with note O2 |
| 4g | Lean-on dry seed round (own temp root, `lean=True`) | best certified and bound to its program | `r00-seed-005` `certified` (1.03 s), `program_file_sha256` `01effa8d…` = sha256 of its program file, `gates_sha256` stored | | PASS with note O1 |
| 5a | six frozen hashes | unchanged | twelve `99663fa6`, lsh `88e0d76b`, spinnet `10f5727f`, fuzzy_ub = fuzzy_link `b4bd20fe`, rishon `5f5decfa`, spinnet loop `f1314a01` | exact | PASS |
| 5b | `lsh/loop.py` in no hash list | not listed | `provenance.evaluator_files` of twelve, lsh (27 files), spinnet, fuzzy_ub, fuzzy_link, rishon names no `loop.py` and no `lean_export.py`; `git diff HEAD --name-only` = the two builder files; so no archive goes stale. Acceptable by prompts/401 section 1.4 and 4.3: `loop.py` decides no verdict and no archive metric (it writes briefs, stop records, ranks the headline through `angle_linear` and certifies); after an edit that can move $\rho$, run `robust.headline("lsh","step",refresh=True)` and note it in STATUS | | PASS |
| 5c | `tools/check_lock.py`, `acceptance-check` | OK | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v22` | | PASS |
| 6 | `compress/specs/lsh-step.md` | stock render, names no seed, headline section, correct LSH rules | file equals `spec.render()` byte for byte (12355 characters); contains no seed label, no `wrap_`, no archive entry id, no program name; has "LSH register and rules", "Proved structure (Lean)" (19 facts: 17 proved by `decide`, 2 measured) and "Headline rule" before "Tools". Rules agree with METHODS-lsh and with my independent Aer check: valid site codes 000/001/010/100/110, Abelian Gauss law $N_n(c)=N_p(c+1)$, $H_E=\tfrac34\sum_cN_n$ with $N_n=\ell_{pn}+\ell_{nv}$, 47/433/16/31, $k$ from $\sum\ell_{nv}$ (2K = -4, 2, -1), move XOR pattern 1 / 6, transcoder 40 CX and 32 T. No physics constant is typed that disagrees with METHODS-lsh | | PASS with note O3 |

## Verdict
PASS. 0 failed. Counts: m8 not slow 22 passed; m8 slow 5 passed, 6 pending (G1-G4, L5, R1, wait for the round-0 archive of step 8.5-8.8); named ids 13 passed; m7 28, m4 S8 1, m6 H1 1, m2c 18, unit 144 (+8 new) passed. No new failure compared with the last LSH report (`reports/tests/428`).

## Observations (non-blocking)
- **O1 (guess: shared design, not LSH code).** The shared `round._certify` calls the hook with no `out_dir`, so a seed round with Lean on in a temporary root writes its certificate into the repository `results/lsh/certs/` (my run left `lsh-step-o1-975e51bd4fed.json`; I moved a copy to `results/tester/436-raw/round-lean-cert-seed005.json` and removed it from the tree). The same happens for the real round (intended there). Also the per-round certificate carries only `program_file_sha256` (provenance `git_dirty` true in a dirty tree); `entry_id` appears only in the `certify_headline` certificate (step 8.8, clean worktree). This matches plan section 1.9 but should be stated in the step 8.5 brief.
- **O2.** The compiled checker does not read the provenance block; entry and program binding is enforced by the rebuild with the sha256 check (4e) and by test M8-L5 at the gate, not by the checker. A forged `entry_id` certifies; that is by design (Lean never changes validity).
- **O3.** The first sentence of the task text says "in the 12-qubit encoding" (shared default wording); the register section below it describes the 12 data + 12 outer layout, so the text is not wrong, only generic. `angle_linear` returns True for an exactly linear but wrong-sign circuit ($-\beta$, 4c): $\rho$ measures linearity only, validity is the evaluator's job.
- **O4.** HEAD moved from `9761c72` to `ec38370` by commits that touch STATUS and `reports/tests/435` only (gate tester); `src` and `tests/acceptance` were unchanged during my runs, hashes re-read after.
- Byproducts of my runs: temp roots under the session scratchpad (`root436`, `root436b`, `lb`), `results/tester/436-*`, my added scripts/tests (not collected by acceptance). Tracked files unchanged by the tests (`git status` shows only the builder's files and mine).
