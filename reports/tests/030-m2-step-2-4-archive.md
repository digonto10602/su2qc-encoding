# Tester report 030 — M2 step 2.4 (archive, cache, N6)

- Date: 2026-11-05
- Commit: 244f52f (acceptance-v7; working tree dirty: step-2.4 files, 2.5 builder files, Lean files, all uncommitted)
- Plan in force: `prompts/002-…` (+ addenda 003–006), acceptance-v7 (re-locked from v6 while I was running; I re-ran everything after it)
- Mode: step
- Related: reports/tests/027, 029 (step 2.3), 026
- Raw numbers: `results/tester_m2_step2_4_{meta,archive_props,cache,forged,provenance}.json`; scripts `tests/independent/archive_2_4/a1_archive_props.py … a4_provenance.py` (a2, a4 take the tester scratchpad dir as argv[1]; programs `prog/001-ue.py`, `prog/002-bad.py`). Seed 20261105.

## VERDICT: FAIL
All three target acceptance ids pass and nothing regressed. Two independent checks fail:
1. **Cache tampering is trusted** (the brief says: if trusted, FAIL). A cached result edited to `valid=True` is returned without re-evaluation, and `entry_from_result` + `Archive.insert` then accepts it. Scenario below (section 3).
2. **`Archive.insert` accepts a trial-mode (unverified) result** and entries whose own fields contradict "valid".

Counts: m2 acceptance 27 passed / 5 not passed (4 PENDING + 1 genuine AttributeError, see 1) — was 12 / 20 when I started, because the 2.5 builder's `baselines.py` landed during my run; m0+m1 non-slow 54/54; unit (all except the two Lean files) 275 passed; collect 102; LOCK OK; acceptance-check PASS (acceptance-v7). New failures versus report 029: none in the locked suite; 2 new independent failures (above) + 1 genuine non-pending m2 failure that was previously hidden behind a PENDING (item 1b).

## Commands
```
pytest -n auto -q tests/acceptance/m2/test_compress_machinery.py                      # 3 targets + classification
pytest -n auto -q -m "not slow" tests/acceptance/m0 tests/acceptance/m1               # 54 passed, 146 s
pytest -n 6 -q tests/unit --ignore=tests/unit/test_lean_cert_unit.py --ignore=tests/unit/test_lean_project_unit.py   # 275 passed, 206 s
pytest -q tests/unit/test_compress_archive_unit.py tests/unit/test_compress_evaluate_unit.py   # 46 passed
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
python tests/independent/archive_2_4/a1_archive_props.py ; a2_cache.py <scratch> ; a3_forged.py ; a4_provenance.py <scratch>
```
(First attempt of the m0/m1 run hit `ACCEPTANCE LOCK BROKEN` because HEAD moved cb94221 -> 244f52f, v6 -> v7, in the middle of my session; after the re-lock all checks were re-run and are green.)

## 1. Targets and m2 classification

| check | expected | got | PASS/FAIL |
|---|---|---|---|
| `test_archive_roundtrip_and_elites` | PASS | PASS | PASS |
| `test_archive_rejects_invalid` | PASS | PASS | PASS |
| `test_cache_keyed_by_code_hash` | PASS | PASS | PASS |
| `test_entry_has_provenance_fields` | PASS (needs `general_circuit`) | PASS after the 2.5 builder's `general_circuit` landed (was PENDING at the start) | PASS |
| other m2 ids | PENDING only | 4 PENDING + 1 genuine, below | see below |
| m0 + m1 non-slow | green | 54 passed | PASS |
| unit | green | 275 passed | PASS |
| collect / check_lock / acceptance-check | clean / OK / PASS | 102 / LOCK OK / matches acceptance-v7 | PASS |

Remaining non-passing m2 ids (all outside step 2.4):
- PENDING: `test_report_table_from_results` (`report_table is not built yet`), `test_round_dry_run_end_to_end` (`make_brief is not built yet`), `test_archive_best_valid_and_not_worse_than_seed` (empty real archive; needs the loop, 2.7). The Lean files are not in my scope.
- **1b. GENUINE FAILURES (not PENDING)**: `test_metrics_match_qiskit_count_ops` (test line 263) and `test_polish_valid_and_not_worse` (line 360): `AttributeError: module 'su2plaq.compress.metrics' has no attribute 'key'`. The tests call `M.key(m)` / `M.cell(m, 8)` on `su2plaq.compress.metrics`; `key` and `cell` live in `su2plaq.compress.synth`. Guess: step 2.3 never re-exported them in `metrics.py` (previously hidden behind the `general_circuit` PENDING). Not part of 2.4 but will block the 2.5 gate.

## 2. Archive invariants (`a1_archive_props.py`, 300 seeded random insert sequences, 3456 accepted + 2705 refused inserts, brute-force model)

| check | expected | got | tol | result |
|---|---|---|---|---|
| elites = min key (ties: smaller id) per cell | 0 mismatches | 0 / 300 | exact | PASS |
| best = global min key | 0 | 0 / 300 | exact | PASS |
| `family_best` = min key in family | 0 | 0 / 1200 | exact | PASS |
| best is the elite of its cell | always | always | | PASS |
| invalid / unverified / inf-key / NaN-key refused, archive snapshot unchanged | 0 changes | 0 / 2705 | | PASS |
| duplicate id | refused, archive unchanged | `ValueError`, unchanged (counted in the 2705) | | PASS |
| save -> load round trip | identical entries and elites | 0 mismatches | | PASS |
| entry files byte-stable over load -> save -> load | identical bytes | 0 / 300 differ | | PASS |
| `index.json` byte-stable over two saves | n/a | differs (field `written_utc`, re-stamped each save); equal apart from that field | | NOTE |
| atomic write, simulated kill: 16 kill points (partial `.tmp` write at the k-th write, abort before the k-th rename, k = 1..8) | no partial/unparsable final file, load works | 16/16 killed, 0 bad; index always parses; a leftover `*.tmp` is never read | | PASS |
| index vs entries after a kill | | 2/16 cases: a new entry file is complete but `index.json` (written last) still lists the old set; `load` reads `entries/`, not the index, so nothing is lost | | NOTE |

### Insert hardening gaps (`insert_probes`)
`insert` checks only `valid`, `reason == "ok"`, `cell is not None`, finite key.

| entry content | expected | got |
|---|---|---|
| real **trial-mode** result (`mode="trial"`, 64 inputs, nominal angles, T estimate 239.18 not measured), `valid=True`, `reason="ok"` | refused (unverified) | **accepted** (`inserted=True`, key `(0, 239.179, 1, 28)`) — FAIL |
| `valid=True, reason="ok"` but `skeleton_equal=False` | refused | accepted — FAIL |
| `verdict_nominal={"ok": False, "certified": False}` (or `{}`) | refused | accepted — FAIL |
| `cell` inconsistent with `key` (cell `(999, 999)`) | refused | accepted — FAIL (elites then group by the wrong cell) |
| negative CX / T in key | refused | accepted (minor) |
| `numpy.int64` in key | accepted (value is fine) | refused silently as non-finite (`isinstance(x, int)`) — NOTE |
| `id = "../../../escape"` | refused | `save()` writes `<root>/compress/escape.json` outside `entries/` (minor; ids come from `entry_from_result`) |
| `load` of a hand-edited entry file (`valid=False` / a forged better key) | validate or ignore | taken as is; the forged entry becomes `best()` (the 2.7 gate test re-evaluates the best, which would catch it) — NOTE |

Guess: `insert` was written against the acceptance `_fake_entry`, which only varies `valid`; the plan text ("verdict ok, certified, skeleton equal at the alternate angles") is not enforced there.

## 3. Cache (`a2_cache.py`; real evaluations of a 4-rotation $U_E$ program, full mode 25 s first call)

| check | expected | got | result |
|---|---|---|---|
| miss, then hit with no re-evaluation | 1 eval, 0 evals | 1 / 0; second call 0.002 s vs 24.99 s; 1 cache file | PASS |
| same bytes, other file path | hit | hit | PASS |
| one program byte added | miss | miss | PASS |
| each of the 15 `TaskSpec` fields (alpha, beta, order, alt_angles, tol_err, tol_gauss, eps, eval_budget_s, support_cap, max_qubits, cell_k, trial_inputs, trial_seed, kind, encoding) edited | spec sha changes | 15/15 change; end-to-end miss for `eps` and `tol_err` | PASS |
| edit one byte of **each** of the 20 files in `EVALUATOR_FILES` (in a copy of `src/su2plaq`) | code hash changes | 20/20; `evaluate_program` then misses; restoring the file hits the old entry | PASS |
| every `su2plaq` module imported during a real full evaluation is in `EVALUATOR_FILES` | all | all except `compress/provenance.py` (cache-key logic) and empty `__init__.py`s | NOTE |
| trial result cached | never | `cache=True` with `mode="trial"`: re-evaluated each time, 0 new files; all cache files have `mode == "full"` | PASS |
| cached result vs fresh | same | same key, cell, verdict; only `metrics["t_estimate"]` has `str` keys (`'1e-06'`) instead of `float` keys after the JSON round trip | NOTE |
| malformed cache file (11 variants: truncated, empty, list, null, missing key, verdict as string/list, bad phase, bad failing_inputs, `verdicts_alt=None`, binary) | re-evaluate, no exception | 11/11 re-evaluate and return the right result | PASS |
| **cache JSON edited to `valid=True, reason="ok"`** | detected or ignored | **returned as is, no re-evaluation** | **FAIL** |
| cache JSON edited to `metrics = {cx: 0, t_eps: 0, …}` | detected or ignored | returned as is (`cx=0, t_eps=0`) | **FAIL** |
| cache file of program A copied to the slot of program B | detected (`program_sha256` / `spec_sha256` in the file must equal the requested ones) | **returned A's result for B**: `valid=True`, `program_sha256 = 423c6159cb62` while 'dc2040857faf' was requested | **FAIL** |

FAIL scenario (exact): evaluate `compress/programs/…/002-bad.py` (sign flipped; `valid=False, reason=error`, op-norm error 1.28) with `cache=True`; edit the one file under `compress/cache/<code_hash>/` to `"valid": true, "reason": "ok"`; call `evaluate_program(..., cache=True)` again -> `valid=True, reason="ok"`, no evaluation. `entry_from_result` then yields an entry with `verdict_nominal["ok"] = False` but `valid=True`, key `(0, 239.18, 1, 28)`, and `Archive.insert` returns True (combines with the insert gaps in section 2). The project already re-validates its other cache (`gridsynth`: checksum + re-computed error on every read, report 029 N4); the result cache has neither. Mitigations that exist: the cache directory is gitignored and not proposer-writable by the guard hook, and the 2.7 gate re-evaluates the best entry from source. Guess for the fix: store a checksum with the result and require `program_sha256 == sha` and `spec_sha256 == spec.sha256()` on every read; make `insert` require `mode == "full"`, `skeleton_equal`, `verdict_nominal["ok"]`/`["certified"]`, and cell == f(key).

## 4. N6 and forged worker output (`a3_forged.py`, 15 programs x {trial, full} = 30 evaluations; none raised, none valid except the benign one)

| case | result |
|---|---|
| forged `meta.json` + `os._exit(0)`, no `out.qpy` (N6; 3-circuit and 1-circuit meta) | `build_error`, "exited (code 0) without writing the circuits" — PASS |
| meta not JSON / meta a list / `discoveries` of wrong type + `_exit` | `build_error` (3 messages: unreadable, malformed, missing circuits) — PASS |
| meta 5 MB `error` string | `build_error`, message truncated (2000 chars) — PASS |
| meta `{"error", "kind":"contract"}` forged | `contract` (invalid either way) — PASS |
| `out.qpy` garbage bytes / empty file + valid meta | `build_error` "unreadable circuit file" — PASS |
| no files, exit 0 / exit 3 | `build_error` — PASS |
| `os.remove(meta)` | `build_error` (audit hook, PermissionError) — PASS |
| forged `out.qpy` with the wrong number of circuits | `build_error` "wrong number of circuits" — PASS |
| forged `out.qpy` with 4-control native `MCXGate` x3, full mode | `disallowed_gate` — PASS |
| forged `out.qpy` with empty 40-qubit circuits x3, full mode | `error` (not the unitary) — PASS |
| legitimate circuit, then program overwrites `meta.json` with `{"error":"x"}` | valid: the worker rewrites meta at the end, so the forged text is replaced — PASS (benign) |

Earlier forged-output cases (`bypass2.py` `h_overwrite_result_files_then_exit`, unit `test_forged_meta_and_exit…`, `test_worker_output_checks`: missing circuits, meta not JSON, meta not dict, corrupt qpy) all give `build_error` — PASS. The sqlite3 / `os.path.realpath` / `isinstance` / `gc` in-process bypasses of report 029 are known and unchanged (not a sandbox).

## 5. Provenance (`a4_provenance.py`, real full result of the $U_E$ program, `family=F9, round=2, parent=r01-F9-001`)

| field | expected | got | result |
|---|---|---|---|
| id | `r02-F9-001` | `r02-F9-001` | PASS |
| program_sha256 | sha256 of the file | equal | PASS |
| evaluator_sha256 | `code_hash()` | equal | PASS |
| spec_sha256 | `spec.sha256()` | equal | PASS |
| git_commit | `git rev-parse --short HEAD` | `244f52f` = HEAD | PASS |
| git_dirty | dirty (tracked changes) | True | PASS |
| versions | installed | qiskit 2.5.2, qiskit_aer 0.17.2, numpy 2.5.2, scipy 1.18.0, pygridsynth 1.2.0, python 3.12.14 = `importlib.metadata` | PASS |
| seeds | code constants | trial 0, transpiler 20261104 (= `logical.SEED`), Clifford+T pass manager 12345, gridsynth 0 | PASS |
| machine, wall_s, written_utc | non-empty | `pichkaCommander x86_64 cpus=12`, 25.5 s, ISO UTC | PASS |
| key / cell / synthesis | `(0, 256, 167, 28)`, `(0, 64)`, measured True | same; cell = (⌊8 log2(0+1)⌋, ⌊8 log2(257)⌋) = (0, 64) | PASS |
| verdict_nominal / alt verdicts | ok, certified, 2 alt | ok True, certified True, engine sparse, op-norm 1.2e-13, Gauss 5.3e-16, 2 alts, skeleton equal | PASS |
| entry from a cached result | same provenance, current code hash | seeds, spec, evaluator hash right, key equal; `wall_s` is the original 18.7 s | PASS |
| invalid result -> entry | key $(\infty)^4$, cell None, refused | as expected | PASS |

## Notes for the coordinator
- Item 1b (`compress.metrics.key/cell` missing) is a one-line re-export but it belongs to step 2.3/2.5, not to this step.
- The trial-mode insert (section 2) is the more serious of the two archive findings: nothing in the archive layer stops a trial result (estimated T, 64 inputs, no alternate-angle check) from becoming an elite. Check how `run_round` (2.6) calls it; the archive should defend itself anyway.
- Cache key does not include library versions (qiskit, numpy, pygridsynth); a library change with unchanged evaluator source would hit old entries. Not tested further.
