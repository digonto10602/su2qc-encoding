# Report 416: tester, consolidation 008 step B3 recheck (F1 and O1 fixes)

- Date: 2026-11-15. Commit: `1e31938` plus the builder's uncommitted B3 changes with the F1/O1 fixes (`compress/round.py` `_certify`, `tests/unit/test_spinnet_loop_unit.py`) and the planner's unlocked erratum E1.
- Plan in force: `prompts/008` §3.3, §8, §10 row B3. Lock in tree: acceptance-v20 plus the unlocked E1. Mode: step. `tools/pytest-safe`, `taskset` on cores 6-17.
- Related: reports/tests/415 (first B3 round, FAIL on F1), 414 (B2). Raw numbers: `results/tester/008-b3-recheck.json`, `results/tester/008-b3-recheck-hashes.json`. Scripts (scratchpad `.../scratchpad/b3t/`): `f1.py`, `mutplug.py`, `fakecert.py`, `t7.py`.
- The test I had added in round one (`tests/unit/test_tester_b3_certify.py`) was deleted by the builder; the reproducer now lives only as the scratchpad script `f1.py`.

## Verdict: PASS

F1 is fixed, the restored unit tests are not vacuous, nothing else moved. Red sets equal to reports 414/415 (only §8 items). Only `acceptance-check` is red, because E1 is not re-locked (expected).

## Commands
1. `python -I f1.py {spinnet,twelve}` (real `round._certify` with the compiled checker); mock-exporter check for an LSH-style certificate (`fakecert.py`); archive comparison.
2. `tools/pytest-safe -n 8 -m "not slow" -rfEs -q tests/acceptance/{m0,m1,m2,m2c,m3,m3x,m4,m5,m5x,m6,m8,m9,m10}`.
3. `tools/pytest-safe -n 1 -m slow -rfEs -q tests/acceptance/m4 tests/acceptance/m3`.
4. `tools/pytest-safe -n 8 -q tests/unit`.
5. Mutation check: `PYTHONPATH=<scratchpad> pytest -p mutplug tests/unit/test_spinnet_loop_unit.py -k "certificate or gates_sha256 or certify_best or seed_round"`; `mutplug.py` re-creates the old line `d["gates_sha256"] = json.loads(...)["gates_sha256"]` in memory only (no file edited).
6. Own sha256 loop (`t7.py`), `pytest --collect-only -q tests/acceptance`, `tools/check_lock.py`, `acceptance-check`.

## (1) F1 re-verified independently

The builder's change (`round.py` lines 336-340): the certificate file is read, and `gates_sha256` is copied only `if "gates_sha256" in cert_file`.

| check | expected | got | result |
|---|---|---|---|
| real spinnet certificate (general seed, `loop.spec()`, `baselines.general_circuit`) through `round._certify(circ, spec, program_file_sha256)` | no exception, `status == "certified"` | no exception; `certified`, 3.1 s | PASS |
| key set of the returned dict vs archive `r02-F1-002` `lean` | equal | `{axioms, cert_path, checker_sha256, program_file_sha256, reason, seconds, status, theorem_path}`, equal | PASS |
| same vs `r00-seed-000` `lean` | equal apart from `program_file_sha256` | difference is exactly `{program_file_sha256}` (older entries predate that field; the shared code adds it by design) | PASS |
| `checker_sha256` | `ec00aa45…` (archive) | equal to both archive entries | PASS |
| `axioms` | `[]` | `[]`, equal | PASS |
| `status`, `reason`, `theorem_path`, certificate file name | `certified`, `''`, `None`, `spinnet-step-o1-b0a415d9322f.json` | same | PASS |
| `gates_sha256` in the spinnet dict | absent (certificate file does not name it) | absent; certificate file has no `gates_sha256` | PASS |
| twelve: real `_certify` on the twelve general seed (115 s) | dict contains `gates_sha256`, same key set as an archive entry that has it (`r05-F2-005`) | key set equal; `gates_sha256 = 46d99155…edb` equals the certificate file's value (it differs from `r05-F2-005`'s hash only because that is another circuit); `checker_sha256`, `axioms` equal | PASS |
| LSH: real certificate not available (`lsh.loop.general_circuit` is `NotImplementedError`, M8) | | covered with a mock exporter that writes an LSH-style file (`gates_sha256 == program_sha256`): dict keeps `gates_sha256` and has the same key set as the twelve dict | PASS (mock, labelled so) |

## (2) Is "no fallback to `program_sha256`" right?

Yes. Facts:
- Nothing downstream reads `gates_sha256` from the stored `lean` dict for spinnet. Search of `src/`, `tests/`, `scripts/`, `tools/`: the only readers are `tests/unit/test_lean_round_unit.py` (twelve entries), `tests/acceptance/m8/test_lsh_m8_followups.py` (reads LSH certificate FILES, not the dict), and `lean/certify.py` line 451, which reads the certificate FILE and already falls back to `program_sha256` itself. `compress/report.py`, `compress/archive.py` (`_store_lean`, `_relativise_cert_path`), the m2c tests and the not-yet-written `replay` do not use it.
- Of the committed archive `lean` dicts, 4 of 5 twelve entries and all certified spinnet entries lack `gates_sha256`, so no consumer can require it.
- A fallback would add a new key to every future spinnet `lean` dict, so it would no longer have "the same fields as before" (task check 4 of round one).
- Only cosmetic observation: the `_certify` docstring (line 318) still says the dict carries `gates_sha256`; for spinnet it does not (the program file is tied through `program_file_sha256`).

## (3) Restored unit tests

`tests/unit/test_spinnet_loop_unit.py`: 46 test functions now (HEAD 39). By AST comparison with `HEAD`: 28 unchanged, 3 adapted (`test_render_spec_has_our_commands_and_facts`, `test_seed_round_writes_labels_external_rows_and_our_key`, `test_briefs_name_our_commands_and_the_spec_file_is_ours`), 8 gone (all shim mechanics: `…four_overrides`, `test_certify_dispatch…`, `test_worker_copy…`, `test_need…`, `test_brief_rewrite…`, `test_certify_best_goes_through_the_laptop_with_the_shim`, the old worker CLI test and one brief test), and 15 new. All 11 behaviour tests I listed in report 415 (CLI oracle/candidate/brief, `ANGLE_SET`, the three `headline` tests, report annotation, `certify_best` different headline, spec headline section) exist unchanged with their old bodies; the round-brief headline test is replaced by `test_round_brief_points_to_the_spec_that_carries_the_headline_rule`.

Mutation check (non-vacuity): with the old strict line put back in memory, `test_real_spinnet_certificate_goes_through_the_shared_certify` and `test_certify_records_gates_sha256_when_the_certificate_names_it` both FAIL with `KeyError: 'gates_sha256'`; the 3 other selected tests (the stubbed `certify_best` / `seed_round` ones) pass, as expected, because they stub the exporter. So the real-certificate test is the one that guards F1, and it does.

## (4) Regression

| set | expected | got | result |
|---|---|---|---|
| `tests/unit` | green | 1019 passed, 0 failed (287 s) | PASS |
| not slow: m0 m1 m2 m2c m3 m3x m4 m5 m5x m6 m8 m9 m10 | red set = reports 414/415 (26 ids, §8 / PENDING) | 264 passed, 26 failed; `diff` of the sorted FAILED lists against the report-415 run: identical; none in m3, m3x, m4 | PASS |
| slow m4 + m3, `-n 1` | only `M4_G1` red (§8) | 7 passed, 1 failed = `M4_G1_archive_best_reverified_from_source` (`0bd7e7d9…0582` vs current `4b665716…1f08`, the stale archive hash) | PASS; `M4_L2` is green again, `M4_G3` green serially |

The 26 red ids (unchanged from 415): m2c `E2`, `E5`, `Y1`, `G1` x5, `R1`, `R2`, `R3`, `P1`, `P2`; m6 `G5`, `G6`, `L2`, `L3`, `L9`; m8 `E2`, `S0`, `S2`, `S3`, `S4`, `S5`, `H1`, `L2`.

## (5) Hashes, collect, lock

| quantity | builder's claim | got (own loop; project functions equal) | result |
|---|---|---|---|
| provenance `code_hash()` | `4b665716…1f08` | `4b6657169787aec981b96e18f65d174c9cff55370d4e6417bdd4437e9e9a1f08` | PASS (unchanged; `round.py` is not in a hash list) |
| `code_hash_for("lsh")` | `c28d3d79…3425` | `c28d3d7921fc…23425` | PASS |
| `spinnet.loop.code_hash()` | `e4f1ff1d…9f34` | `e4f1ff1d5a43…f9f34` | PASS |
| `rishon.compress.code_hash()` | `3af33130…d418a` | `3af33130e35e…d418a` | PASS |
| `code_hash_for("spinnet")` | `8f9ada78…1c6e` | `8f9ada7824d7…1c6e` | PASS |
| `pytest --collect-only -q tests/acceptance` | clean | 374 collected | PASS |
| `tools/check_lock.py` | OK | `LOCK OK` | PASS |
| `acceptance-check` | flags E1 | `FAIL: tests/acceptance differs from acceptance-v20 … Changed: LOCK.json, m4/test_spinnet_compress.py` | expected |

## Restored byproducts (`git checkout --`)
`results/compress/fuzzy_link/summary.json`, `results/compress/rishon/robust.json`, `results/compress/spinnet/robust.json`, `results/compress/spinnet/summary.json`, `results/spinnet/certs/spinnet-UB-o1-33d95284ebb7.json`, `…/spinnet-UB-o1-458a39365261.json`, `…/spinnet-UE-o1-df0c79b22d3f.json`, `…/spinnet-step-o1-066f66922ff8.json`, `…/spinnet-step-o1-b0a415d9322f.json`; and `results/tester/008-b3-hashes.json` (my hash script had rewritten report 415's raw file; the recheck copy is `results/tester/008-b3-recheck-hashes.json`). The twelve certificate run left no tracked change. Untracked files of mine: `results/tester/008-b3-recheck.json`, `results/tester/008-b3-recheck-hashes.json`.
