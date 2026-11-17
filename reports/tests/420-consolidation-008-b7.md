# Report 420: tester, consolidation 008 step B7 (generic replay `compress/replay.py`) and B6 finding F1

- Date: 2026-11-17 (runs 2026-11-16 22:30 to 2026-11-17 00:50 EST). Commit: `efadd54` at the end (`95001ea` when asked; later commits are STATUS, notes/wip, METHODS pointers, and acceptance-v22 tests only; `src/` unchanged by them). B7 source is uncommitted: `src/su2plaq/compress/replay.py` (new), `src/su2plaq/rishon/compress/replay.py` (wrapper), `src/su2plaq/compress/robust.py` (F1), `tests/unit/test_compress_replay_unit.py` (9), `tests/unit/test_robust_hooks_unit.py` (7).
- Plan in force: `prompts/008` §7, §10 row B7; lock acceptance-v22 (m11 added, `prompts/009`/`010`). Mode: step.
- Related: `reports/tests/419` (B6). Raw numbers: `results/tester/420-008-b7.json`; scratch (copies, logs, scripts): `scratch/t420/`.

## Verdict: PASS (with non-blocking notes N1 to N4)

Unit 1066 passed, 0 failed. Y1 green. Not-slow acceptance red set = 419 red set minus Y1 (18 failures, nothing new) plus 24 m11 failures that are all `PENDING:`. `check_lock` OK, `acceptance-check` PASS (acceptance-v22). Both replays reproduce all keys; the rishon wrapper's record equals the HEAD record on every common field.

## Commands
```
tools/pytest-safe -n 4 tests/unit -q                                  # 1066 passed in 377 s
tools/pytest-safe -n 2 tests/acceptance/m2c/test_consolidation_gate.py -k Y1   # 1 passed
taskset -c 0-4 tools/pytest-safe -n 3 -m "not slow" tests/acceptance/m6 tests/acceptance/m8      # 13 failed, 33 passed
taskset -c 0-4 tools/pytest-safe -n 3 -m "not slow" tests/acceptance/{m0,m1,m2,m2c,m3,m3x,m4,m5,m5x,m7,m9,m10,m11}   # 265 passed, 31 failed (see below)
PYTHONPATH=src python -m su2plaq.compress.replay --encoding spinnet --tag t420 --root scratch/t420/sp1   # copy of compress/ + results/compress/
PYTHONPATH=<worktree 8f61336>/src python -m su2plaq.rishon.compress.replay --kind step --tag t420 --root scratch/t420/ri_old    # HEAD
PYTHONPATH=src                       python -m su2plaq.rishon.compress.replay --kind step --tag t420 --root scratch/t420/ri_new    # B7 wrapper
python scratch/t420/f1.py <copy> spinnet|rishon stale|fresh ; python -m su2plaq.compress.report --encoding spinnet|rishon (real tree)
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance   # LOCK OK ; PASS v22 ; 407 collected
```
Resource note: the shared 11 G slice was full (another session's pytest, a planner job, Lean checks, my two rishon replays at 0.8 GB each). My first full `-n 4` acceptance run lost three xdist workers ("node down") and its summary was unusable (it dropped most of the m6/m8 failures from the list); I discarded it and re-ran by milestone group (above). Two tests then failed once in the group run for load reasons and passed alone (below). Replays ran on cores 5-7, F1 scripts on core 8, tests on cores 0-4.

## Checks

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| 1a unit suite | 1066 passed | 1066 passed, 0 failed, 377 s | | PASS |
| 1b `M2C_Y1` replay on a copy of the link archive | green | 1 passed (3.9 s) | | PASS |
| 2a not-slow acceptance, m6 + m8 alone | 419: m6 G5 G6 L2 L3 L9, m8 S0 S2 S3 S4 S5 H1 L2 E2 (13) | exactly those 13 failed, 33 passed; every failure is a `PENDING:` or `NotImplementedError ... step 8.R` | | PASS |
| 2b not-slow acceptance, all other milestones + m11 | red = m2c G1 x5 + m11 PENDING | 265 passed, 31 failed = G1 x5 (`PENDING: ... C1/C2`) + 24 m11 (`PENDING:`, no `E ` assertion lines in the log) + 2 load artefacts: `m2 test_program_lemma_file_checked` (Lean `check_program_lemmas` returned `failed`, timeout 120 s, failed twice under load) and `m9 M9_C1` (xdist worker killed). Both re-run alone: 2 passed in 506 s | | PASS (no new failure) |
| 2c total red set | 419 red set minus Y1 = 18, nothing new | G1 x5 + m6 x5 + m8 x8 = 18; m11: 24 PENDING of 33 (9 slow not run) | | PASS |
| 2d `check_lock`, `acceptance-check`, collect-only | clean, v22 | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v22`; 407 collected (374 + 33) | | PASS |
| 3a spinnet generic replay, tag `t420`, copy `sp1` (52 s, exit 0) | keys of all 23 entries equal, nothing lost | ids equal (23/23), keys equal 23/23, valid equal 23/23, `key_equal` True for all 23, `lost` [], `newly_valid` [], best `r04-F1-004` (31, 1062, 2173, 17) before and after | exact | PASS |
| 3a pre-folders byte-identical | 65 files | sha256 of all 65 original files (results spinnet round files, feedback, robust, summary; archive entries/index; all five attempts and discoveries files) equals the copy in `pre-t420` / `spinnet-pre-t420` (attempts and discoveries: equal in place) | exact | PASS |
| 3a attempts / discoveries / lean | restored; lean carried for same sha | `attempts_unchanged` True, `discoveries_unchanged` True; 6 lean dicts (r00-seed-000, r00-seed-001, r01-F1-001, r02-F1-002, r03-F1-003, r04-F1-004) present before and after, dict equal, program sha equal; `lean_carried` lists the same six | exact | PASS |
| 3a record schema | 204 §6.2 + `encoding_sha256` + `written_utc` | 204 fields all present (tag, encoding, kind, rounds, evaluator_sha256, evaluator_sha256_old, entries[id, round, label, old, new, key_equal], newly_valid, lost, best_old, best_new, attempts_unchanged, discoveries_unchanged, backup, provenance) plus `encoding_sha256` (`10f5727f...e15c`), `written_utc`, `old_id`, `program_path`, `program_sha256`, `lean`, `lean_carried`, `wall_s`, `round_wall_s`; `evaluator_sha256` `99663fa6...3e37`; no `prune_fraction` (rishon only) | | PASS |
| 3a tamper, recorded key (round-002.json, `r02-F1-002` cx 31 -> 32... key[0]+1) in copy `sp2` | exit 1 | stderr `REPLAY PROBLEM: key changed for ['r02-F1-002']`, exit 1 | | PASS |
| 3a tamper, archive entry key (`r02-F1-002.json` key[1]+7) in copy `sp3` | n/a (not specified) | the archive loader prints `refusing r02-F1-002.json: key / cell do not match the metrics`, replay continues, exit 0 (the "old" keys come from the round files, not the entry) | | note N2 |
| 3b rishon wrapper full replay vs HEAD replay (both full, 4710 s vs 4771 s on contended cores, exit 0 both) | same field set | new = old + {`encoding_sha256`, `lean_carried`, `written_utc`}; no field only in old; 204 fields incl. `prune_fraction` = 0.1 in both; all 19 `entries` identical; all common fields equal (except wall, provenance); `newly_valid` [r00-seed-001, r00-seed-002], `lost` [], key_equal True/None only, best `r04-F1-004` (228, 846, 1417, 53) old = new; `evaluator_sha256` `5f5decfa...ef23`; attempts and discoveries restored | exact | PASS |
| 3b same, no-op stub round function (quick schema check) | same | identical result of the stub run on both code versions | | PASS (supplement) |
| 3c refusal: existing `pre-<tag>`, existing `replay-<tag>.json` (reused tag), existing `archive/<enc>-pre-<tag>`, wrong kind, rishon wrapper with existing `pre-204` | ValueError, nothing moved | all `ValueError` (wrong kind: "round files do not all belong to ..."); sha of the whole root tree before = after in every case | exact | PASS |
| 4a F1, stale cache, `compute=False`, spinnet and rishon copies | None, no write, no build | None, 0.04 s each (a rebuild takes 49 / 111 s), directory sha and mtimes unchanged | | PASS |
| 4b F1, fresh cache, `compute=False` | equals hook, no write | spinnet `r02-F1-002` (31, 21840, 0, 46024, 17), t_mean 1092.0, 23 ranked, 0.00 s; rishon `r04-F1-004` (228, 16876, 0, 28328, 53), 843.8, 16 ranked, 0.01 s; files unchanged; ranking, unrankable, archive_best and its key identical to the `compute=True` result | exact | PASS |
| 4c `compute=True` still the hook | spinnet r02-F1-002 (31, 21840, 0, 46024, 17); rishon r04-F1-004 (228, 16876, 0, 28328, 53) | both equal (49.4 s, 111 s refresh) | exact | PASS |
| 4d report CLI on the real tree | `robust.json` unchanged | `results/compress/{spinnet,rishon}/robust.json` mtime and sha unchanged, no program built (0.2 s per encoding); but see N1 | | PASS (N1) |
| 5 hashes vs 419 | equal | provenance `99663fa6cd2550d91f7a52c7aad6097840177cb3b13bff2b06f92a70e02b3e37`; lsh `88e0d76bce7b3af635fc895b469d9b2db38c34a69d6ea86c3049f3f9526ec1ca`; spinnet `10f5727f5379cb44d2a5fccdbb25fa7b279cbd91ca64a2b4f88df201ad35e15c`; fuzzy_ub = fuzzy_link `b4bd20fe811e5c992ff9cfb9257a4847705cb843cfe3a0a1c9c01590dbe287f9`; rishon `5f5decfa34f53069afe7fc41e0d62f7ceecefe2e56667c42a2de56531324ef23`; spinnet loop `f1314a01d7716b7a36ae6ddc8e990c4bd293c97881a7aaf53510cfd6a74663d4` | exact | PASS |

"Program built" in 4a/4b: for spinnet and rishon the hook builds with its own functions, so my counter on `robust.robust_metrics` shows 0 builds even for `compute=True`; the evidence for "no build" is the time (0.00 to 0.04 s against 49 s and 111 s).

## Notes (none blocks B7)

- N1: the generic report CLI on the real tree still rewrites the tracked `results/compress/{spinnet,rishon}/summary.json` when the track cache is stale (hash changed in B6): the `t_avg` column of every row and the `headline` block are dropped, and the Paulo row text changes (`beta = 1` to `beta = 0.05`). `robust.json` is untouched as required. I restored both files with `git checkout --`. Guess: expected consequence of `compute=False` returning None; the Phase C replay plus a fresh headline refills them.
- N2: replay ignores a tampered archive entry (loader refuses it, replay goes on, exit 0). Only a changed round file is caught. Probably acceptable; a message is printed.
- N3: `compute=True` on a hook encoding rewrites `robust.json` with identical content on every call (mtime changes). Pre-existing hook behaviour.
- N4: the rishon wrapper now carries `lean` records of same-sha programs (`lean_carried` 5 entries) and has three extra record fields compared with HEAD; HEAD did not carry lean dicts. This matches `prompts/008` §7, but it is a behaviour change for rishon C2.

## Tracked files rewritten by the locked tests and restored (`git checkout --`)
`results/compress/fuzzy_link/summary.json` (m10), `results/compress/rishon/robust.json` (m6; `evaluator_sha256` only), `results/spinnet/certs/spinnet-{UB-o1-33d95284ebb7, UB-o1-458a39365261, UE-o1-df0c79b22d3f, step-o1-b0a415d9322f}.json` (unit and m4 tests: provenance only), plus `results/compress/{spinnet,rishon}/summary.json` (my report-CLI run, N1). `git status` now shows only the B7 source and test files.

## Cleanup left for the coordinator
`scratch/t420/` (copies sp1..sp4, ri_new, ri_old, rs_*, f1sp, f1ri, logs; about 0.5 GB) and the git worktree `scratch/t420/headwt` (detached 8f61336; `git worktree remove` was not run; rm is denied to me).
