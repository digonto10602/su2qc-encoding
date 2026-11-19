# Tester report 440: LSH M8 step 8.9 build, `scripts/m8_results.py` (mode step)

- Date: 2026-11-19. Commit `df95e14` (HEAD; the tree is dirty: untracked `scripts/m8_results.py`, `tests/unit/test_m8_results_unit.py`, one round-3 proposer file `compress/programs/lsh/F3/003-*.py`, modified spinnet cert).
- Plan in force: `prompts/401` on `prompts/400` (LSH M8), step 8.9 (row "8.9"). Related: `reports/tests/438` (round 1), `reports/tests/439` (round 2).
- Raw numbers/scripts: `results/tester/440/{check_json.py, own_head.py, lean_branch.py, summary.json}` (no RNG; seed null; angle set seed 20261107 is the project's).
- Resources: every run `taskset -c 4-7`, heavy runs through `tools/run-capped`, pytest through `tools/pytest-safe -n 4`. Trial run: 4.0 s wall, 284 MB peak RSS.

## Commands
```
taskset -c 4-7 tools/pytest-safe -n 4 tests/unit/test_m8_results_unit.py
taskset -c 4-7 tools/run-capped python scripts/m8_results.py --out scratch/m8trial440            # trial (theorem file absent)
python results/tester/440/check_json.py                      # 226 independent field checks vs raw archive/round/robust/m4/stop files
taskset -c 4-7 tools/run-capped python results/tester/440/own_head.py   # own sparse engine on the headline, saved .qpy/.qasm3, own recount
# R1 in a temp root (copy of tests/acceptance + copies of the LSH data; acceptance tests NOT edited)
python -m pytest -c pytest.ini tests/acceptance/m8/test_lsh_m8_gate.py::test_M8_R1_results_and_before_after
python results/tester/440/lean_branch.py <temp root>         # Lean branch: bad theorem files must raise
taskset -c 4-7 tools/run-capped python scripts/m8_results.py --root <temp root with theorem file> --out <scratchpad>
taskset -c 4-7 tools/pytest-safe -n 4 tests/unit -k "m8 or lsh"
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
```

## Results

| # | check | expected | got | tolerance | verdict |
|---|---|---|---|---|---|
| 1 | unit tests `test_m8_results_unit.py` | green | 13 passed in 3.5 s (incl. the end-to-end `--quick` run on a copy) | - | PASS |
| 2 | unit tests wrote nothing into `results/` or `compress/` | no change | `find results compress -type f` (path, mtime, size) before = after for 15280 files, `git status` identical; only change was the round-3 proposer file `compress/programs/lsh/F3/003-*.py` (not mine, appeared later) | exact | PASS |
| 3 | trial run (full, not `--quick`) | exit 0, 4 files | exit 0; `m8-compressed.json`, `m8-before-after.md`, `m8-headline-step.{qpy,qasm3}`, no stray `.tmp` files | - | PASS |
| 4 | headline key and id | min robust key over valid archive entries (own recomputation from `results/compress/lsh/robust.json` + entry files) | `r02-F1-002`, robust key (71, 22320, 0, 46684, 25), $\bar T$ = 22320/20 = 1116.0; equals JSON `extra.headline` | exact | PASS |
| 5 | archive best (archive key) | min key over 20 valid entries | `r02-F1-002`, key (71, 1110, 2291, 25); equals `extra.archive_best(_key)` | exact | PASS |
| 6 | ranking | 19 ranked + 1 unrankable | 19 in `robust.json` = `len(extra.ranking)`; unrankable = `r00-seed-qiskit_l3` (Qiskit export), listed in `extra.unrankable` | exact | PASS |
| 7 | before/after rows (19 rows: 12 seed/external rows (10 round-0 candidate labels + external `qiskit_l3_whole`, `paulo15_wrapped`) + 5 family bests + `global_best` + `headline`) | every CX, $T_{\rm fixed}$, $N_{\rm rot}$, T(1e-6), T(1e-10), $T_{\rm est}$, depth$_{\rm CT}$, qubits, $\bar T$, Lean word, entry id (label from round-000 candidates) equal to archive entry / round-000 external record / `robust.json` | all equal (part of the 226 checks, 226/226 PASS); best-of-family ids (F1..F5) equal to my own min over robust keys by family; `general` row (94, 88, 8) equals `results/lsh/step.json` | exact (1e-9 on floats) | PASS |
| 8 | the three numbers | spin network 31 CX (from `results/spinnet/m4-compressed.json`: `r02-F1-002`, key (31, 21840, 0, 46024, 17), $\bar T$ = 1092.0); wrapped = 31 + 40 = 71, $\bar T$ = 1124.0 (= 22480/20 of `r00-seed-005`); LSH headline 71, 1116.0 | `native_gain_cx` = 71 - 71 = 0; `overhead_cx` = 71 - 31 = 40; `native_gain_t_avg` 8.0; `overhead_t_avg` 24.0; `wrapped_minus_spinnet_t_avg` 32.0; all equal to my arithmetic | exact | PASS |
| 9 | transcoder cost | 40 CX, 32 T (M7-V1) | `{"cx": 40, "t_fixed": 32}`, measured by the script from the wrap circuit; unit test also checks it | exact | PASS |
| 10 | CX vs $\bar T$ front | strict front, CX ascending | ids (my own sweep of ranked entries) [r02-F1-002 (71, 1116.0), r00-seed-006 (72, 879.4), r00-seed-007 (74, 697.6), r00-seed-003 (82, 641.1), r00-seed-002 (84, 585.1)] = JSON front | exact | PASS |
| 11 | lineage, rounds, stop record | valid archived candidates with parent; 3 round files; stop = stop.json | 20 lineage rows (ids and parents equal my own walk of the round files); `n_rounds` 3; `extra.stop` (stop False, reason null, streak 0, sessions 11) = `results/compress/lsh/stop.json` and `stop.json` md5 unchanged by the run | exact | PASS |
| 12 | uniform-split row, outer electric row | (400, 4, 6, 18), "not built"; UE.json row | equal to `rs_split.structure()` and `results/lsh/UE.json` `extra.outer_electric_row` (+ file commit 76fd221) | exact | PASS |
| 13 | headline re-verification, own engine (`results/tester/439/own_sparse.py`: own 24-bit codes, own expm target, own dict-sparse gate walk) on all 433 states, 3 pairs | $\le 10^{-10}$ | native/lowered op-norm error: (0.37, 0.61) 1.4e-15 (saved .qpy circuit) / lowered 2.9e-15 range; (0.91, 0.23) 6.8e-16 / 2.7e-15; (1.7, 1.0) 1.9e-15 / 2.9e-15; dirty ancilla, leak, outer-changed, Gauss violation all 0.0; JSON `op_norm_error` 7.2e-15, `n_inputs` 433, `gauss_residual` 5.3e-16 | $10^{-10}$ | PASS |
| 14 | saved circuit files are the headline | same gate list and valid | `.qpy` reloaded: gate list identical to the rebuilt headline, own error 1.4e-15; `.qasm3` reloaded + lowered: 2.2e-15, no dirty/leak/outer/Gauss | $10^{-10}$ | PASS |
| 15 | own recount of CX/T and T($\varepsilon$) table (own lowering + own pygridsynth) | = JSON | CX 71, $T_{\rm fixed}$ 40, $N_{\rm rot}$ 17; $T_{\rm total}$ at $\varepsilon$ = 1e-4, 1e-6, 1e-8, 1e-10: 758, 1110, 1456, 1808 (JSON same, rotation part 718, 1070, 1416, 1768); depth 68; qubits 25 | exact | PASS |
| 16 | locked R1 against the trial output (temp root: copied tests/acceptance + copied LSH data, symlinked src/tools, acceptance tests unedited) | fails only on `git_dirty`, stop not true, theorem file | exactly three assertions fail, in test order: (a) `provenance.git_dirty is False` (True: dirty tree), (b) `st["stop"] is True` (False: loop running), (c) `ex["lean"]["theorem_file"] == "lean/certs/lsh-best-step.lean"` (None: file not written until 8.8). After patching only my temp copy of the JSON for (a), (b), (c) one at a time, R1 PASSES (1 passed), i.e. no other assertion fails (archive, angle set, T table, synth verdicts, rows, 31/71/40, front, uniform split, md names best and headline, cert_sha256 length 64) | - | PASS (3 expected remainders) |
| 17 | Lean branch must raise, not fake (`lean_branch.py`): theorem file with no axioms, with `sorry`, with syntax error | RuntimeError | all three raise `RuntimeError("theorem file ... is not accepted with standard axioms + one native axiom")` with Lean output | - | PASS |
| 18 | Lean branch on a real theorem file written by `write_theorem_file` from the committed cert | status `elaborated`, axioms standard + one native | `elaborated`, axioms [Classical.choice, Quot.sound, propext, lsh_best._native.native_decide.ax_1_1], names headline True, elaboration 1.0 s; full script run on that root exit 0 (all other JSON fields equal to the trial run) | - | PASS |
| 19 | missing theorem file | reported, not faked | `theorem_file: null`, status "missing (step 8.8: ...)" in the trial JSON and md | - | PASS |
| 20 | code review: hard-coded expected numbers/ids | none | none (no 71/31/40/94/108 or entry ids in the script; transcoder, 31, 71 all read/measured). Constants: nominal pair $(\alpha,\beta)=(0.37,0.61)$, label tuple `SEED_ROWS`, `SEEDS["angle_set"] = 20261107`, `THEOREM_NAME` (plan constants) | - | PASS (see note 2) |
| 21 | code review: exceptions, atomic writes, repo writes | no silent swallowing; atomic; nothing written outside `--out` | three `except`: `ValueError` in `rel` (documented fallback), `finally: unlink` of temp files (x2), `QASM3ExporterError` recorded in the JSON (`qasm3_error`), not hidden. JSON, md, qpy, qasm3 all written via temp file + `os.replace`. `RB.headline(compute=False)` does not write; `stop_state` runs on a temp copy (stop.json md5 equal before/after, no `summary.json` created) | - | PASS |
| 22 | `tests/unit -k "m8 or lsh"` | green | 124 passed in 33.9 s | - | PASS |
| 23 | lock | OK | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v22`; 407 tests collected, no errors | - | PASS |

Counts: 23 checks, 23 PASS, 0 FAIL; R1 pending items: 3 (git_dirty, stop, theorem file; all expected before 8.8/final run).

## Observations (not failures)

1. `extra.lean.binding.matches_headline` is `false` and `binding.entry_id` is `null` in the current data. Cause: the committed certificate `results/lsh/certs/lsh-step-o1-0320e89c1271.json` was written by the round loop and carries `program_file_sha256` (equal to the headline's, checked) but no `provenance.entry_id`; `certify-headline` (8.8) writes `entry_id` into the cert. The script only reports the binding (no assertion), the locked L5 test checks it. After 8.8 this must read `true`; check it in the final JSON.
2. `SEEDS["angle_set"] = 20261107` is typed in the script next to `RB.ANGLE_SET_SEED`, which is what the angle-set record uses. Same value today; a duplicate that could diverge.
3. `general` row has 31 qubits (loop circuit with the outer register) while `results/lsh/step.json` says 19 qubits (M7 layout); `check_general_row` compares only CX, $T_{\rm fixed}$, $N_{\rm rot}$ (all equal: 94, 88, 8). Not an error, but the row is not literally the M7 circuit.
4. `read_json` falls back to the repository copy of `results/spinnet/m4-compressed.json` / `results/lsh/{step,UE}.json` when they are missing under `--root`; documented, but note that a temp-root run reads those from the live repo.
5. Spin-network headline id is `r02-F1-002` (spinnet loop) and the LSH headline id is also `r02-F1-002` (LSH loop): same string, different archives. The md "three numbers" section prints both with the same id; readers may confuse them.
6. My mistake, cleaned up: I symlinked the repo `lean/` into my temp root, so my Lean-branch test wrote `lean/certs/lsh-best-step.lean` (untracked, sha256 `5a1c2016...`) into the repo. I deleted it; `git status` now shows only the pre-existing items plus `results/tester/440/` and the round-3 proposer program. The theorem file must be (re)generated by step 8.8 in the clean worktree. Also removed my `results/tester/439/__pycache__`.

## Byproducts

`scratch/m8trial440/` (gitignored; the trial output), `results/tester/440/` (untracked: scripts and `summary.json`), the scratchpad temp root. No `__pycache__` left in `results/`; `results/lsh/`, `results/compress/`, `compress/` (except the proposer's own new file) untouched.
