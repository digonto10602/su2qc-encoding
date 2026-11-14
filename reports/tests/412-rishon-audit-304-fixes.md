# Tester report 412 — rishon audit-304 fixes (N2, N4, N5) in the working tree

Date: 2026-11-13. Git commit: `7a2ed3b` + UNCOMMITTED builder changes (7 files, see §0). Mode: step.
Prompt in force: `prompts/205` (on 204, 203); acceptance-v20. Related: `reports/audits/304-rishon-milestone-5d.md` (N2, N4, N5), `reports/tests/410-rishon-c1-three-layer-replay.md` (my earlier leaving-operator check), `reports/tests/411-rishon-milestone-5d-full.md`.

## 0. What was verified
Uncommitted: `src/su2plaq/rishon/physical.py` (N2), `src/su2plaq/circuits/rishon.py` and `src/su2plaq/rishon/compress/three_layer.py` (N4), `src/su2plaq/rishon/compress/replay.py` (N5), and three unit-test files. Of these only `circuits/rishon.py` and `physical.py` are in `RISHON_EVALUATOR_FILES`. `git diff HEAD -- src/su2plaq/compress src/su2plaq/evaluate src/su2plaq/encodings` is empty (checked; `encodings/registry/base` untouched).

Cores 14–19 only; all pytest through `tools/pytest-safe`, all other jobs through `tools/run-capped`.

## 1. Commands
```
graphify update . ; graphify affected "det_sector_structure" ; graphify affected "prepend_det_layer"
git archive HEAD src | tar -x -C <scratch>/head                      # HEAD copy of src for the old-vs-new comparison
taskset -c 14 tools/run-capped <scratch>/run1.sh {src|<scratch>/head/src} {work|head}   # results/rishon/tester-412-leaving-mutants.py
taskset -c 14 tools/run-capped <scratch>/verr.sh                       # ValueError matrix, results/rishon/tester-412-valueerrors.json
python <scratch>/replay_exit.py                                        # replay.main exit codes, results/rishon/tester-412-replay-exit.json
taskset -c 15 tools/run-capped <scratch>/cli.sh   # python -m su2plaq.rishon.compress.three_layer --entry r04-F1-004 --out <scratch>/three-layer.json
taskset -c 14,16-19 tools/pytest-safe -n 5 -q tests/unit
taskset -c 14-19 tools/pytest-safe -n 6 -q -m "not slow" -rs -rx tests/acceptance/{m5,m5x,m6}
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
```

## 2. Results

| # | check | expected | got | tolerance | verdict |
|---|---|---|---|---|---|
| 1a | production `leaving_weight` (working tree) | $\approx1.6\times10^{-25}$ | $1.601319485313107\times10^{-25}$ (bit-identical to report 410 and to HEAD) | $\le10^{-20}$ (unit), $\le10^{-9}$ (M5_DT5) | PASS |
| 1b | blocks lam0 / inner_det / full_det | 31870 / 4976 / 305 | 31870 / 4976 / 305 (HEAD identical) | exact | PASS |
| 1c | charge-change ranks | 0 / 3 / 4 | 0 / 3 / 4 (HEAD identical) | exact | PASS |
| 2a | mutant B: $H_B$ + nibble-0 $3\to5$ flip (amplitude 1) on the 1296 inner codes | large (report 410: 12808 for the same flip) | **work 12807.999999999998**; HEAD $1.6\times10^{-25}$ (silently missed) | $>1$ | PASS (old code blind, new detects) |
| 2b | mutant D: $H_B$ + nibble-0 $6\to9$ flip | large ($=$ number of columns with that nibble) | **work 3204.000**; HEAD $1.6\times10^{-25}$ | $>1$ | PASS |
| 2c | mutant C: $H_B$ + every inner code $\to$ one fixed inner code | large | **work 26585.38**; HEAD 603.56 (only the part whose image lies inside the code union) | $>1$ | PASS |
| 2d | mutant det nibble pairs (5,10), (6,9), (3,5) instead of (3,12), all 12 links, `closed_indices` frozen | large | **work 204800.0** for all three; HEAD $9.9\times10^{-27}$, $9.9\times10^{-27}$, $8.0\times10^{-26}$ | $>1$ | PASS |
| 3a | `prepend_det_layer(build_step(order 1))` | works (58 qubits) | works | — | PASS |
| 3b | `prepend_det_layer` on order-2 step, `UE`, `UB`, `UD` units (metadata present) | ValueError | ValueError ("order is 2" / "kind is 'UE'/'UB'/'UD'") | — | PASS |
| 3c | `prepend_det_layer` with empty metadata (program-built unit) / wrong first register | accepted / ValueError | accepted (58 qubits) / ValueError (`d[16]`) | — | PASS |
| 3d | `verify_three_layer(kind=UE, UB, step2, unit)` | ValueError before touching the archive | ValueError "supports kind='step' ... only" (all four) | — | PASS |
| 3e | `verify_three_layer(kind="step", ...)` | goes past the kind check | reaches the archive lookup (ValueError "not a valid entry") | — | PASS |
| 3f | CLI `three_layer --entry r04-F1-004` | `ok`, all 3 triples certified | `ok: True`, all three `ok`, `certified`, reason `ok`; op_norm_error $1.64$–$1.69\times10^{-13}$, leak 0, gauss_residual $\le1.2\times10^{-15}$; keys unit $(228,846,1417,53)$, det $(32,496,326,48)$, three-layer $(260,1342,1743,53)$ | $10^{-10}$ | PASS |
| 3g | m5 `test_rishon_det` (DT1–DT7) and m6 three-layer H3/H4 | pass | pass (inside the m5 / m6 runs below) | locked | PASS |
| 4 | `replay.main` exit code, 7 cases (fake `replay`, subprocess) | 0 only if no `key_equal is False` and no `lost` | `[True,None]`, `[None,None]`, `[]`: 0; `[True,False]`: 1 (stderr "key changed for ['e1']"); `[False]`: 1; lost=`['x']`: 1; both: 1 | exact | PASS |
| 5a | unit suite `tests/unit` | all pass | **968 passed**, 488.6 s | — | PASS |
| 5b | m5 `-m "not slow"` | all pass | **54 passed**, 657 s | locked | PASS |
| 5c | m5x `-m "not slow"` | all pass | **8 passed**, 6.6 s | locked | PASS |
| 5d | m6 `-m "not slow"` | 19 pass, 5 PENDING (G5, G6, L2, L3, L9) | **19 passed, 5 PENDING exactly G5 (replay-204.json missing, C2), G6 (three-layer.json missing, C5), L2, L3 (Laurent3.lean missing), L9 (`recognise_angle_single` missing)**; 0 real failures | locked | PASS |
| 5e | `pytest --collect-only -q tests/acceptance` | clean | 374 tests collected, no errors | — | PASS |
| 5f | `tools/check_lock.py` / `acceptance-check` | OK | `LOCK OK` / `PASS: tests/acceptance matches acceptance-v20` | — | PASS |
| 6a | new rishon evaluator hash `code_hash()` | `1ddae8a6…` | working tree `1ddae8a6edfc6449fb761c72324912f76252b5db23ee5e7e7364e7b0ad530234` (also in the CLI output file `evaluator_sha256`); HEAD gives `a4dbd16ca363770eeb5e25e959154fac2e1d12916febe2fa5b657cb76ed431d6` | exact | PASS |
| 6b | untouched: `src/su2plaq/compress`, `evaluate`, `encodings` (registry, base) | no diff | no diff against HEAD | — | PASS |
| 6c | `three_layer.py`, `replay.py` not in `RISHON_EVALUATOR_FILES` | not hashed | confirmed (list in `rishon/compress/__init__.py`); only `circuits/rishon.py` and `physical.py` changed the hash | — | PASS |

## 3. Notes (no failures)
1. My bit-0-flip operator of report 410 §1 cannot be injected through `det_sector_structure` (its operators are the 1296 inner codes and the nibble flip), so I used the equivalents the function can take: extra $H_B$ columns (nibble-0 flips, one-to-one and all-to-one) and wrong det nibble pairs, by monkeypatching in the test process (no source edit). Mutant B reproduces exactly the 12 808 of report 410 for the $3\to5$ flip. The old code returned $1.6\times10^{-25}$ for it, so the audit's N2 ("dropped silently") is confirmed on HEAD and fixed in the working tree.
2. N2 detail: for mutant C the HEAD value 603.56 is only the share whose image lies inside the code union; the new value 26 585.38 includes the dropped images, so the two parts add as the docstring says.
3. The rishon evaluator hash changes ($a4dbd16c\to1ddae8a6$), as the coordinator announced. Archive entries carrying `a4dbd16c…` are stale until the C2 replay (prompts/204 §6.2); not tested here (M6 G1/G5 pending or green per the m6 run above).
4. The unit suite and m6 runs rewrote `results/compress/rishon/robust.json` (byproduct); restored with `git checkout`. No other tracked file changed (`git status`: only the 7 builder files). Other agents' untracked `compress/programs/fuzzy_ub/F*/012-*.py` are not mine.
5. Not run: the full 3-entry CLI (336 s, done in report 410); `--entry r04-F1-004` only here. M6 G5/G6 stay PENDING until C2/C5.

## 4. Files touched by me
New, all under `results/rishon/`: `tester-412-leaving-mutants.py`, `tester-412-leaving-mutants-work.json`, `tester-412-leaving-mutants-head.json`, `tester-412-valueerrors.json`, `tester-412-replay-exit.json` (commit `7a2ed3b` + dirty tree; no randomness, no seeds). Scratch-only: HEAD copy of `src`, `three-layer.json` (CLI output). Nothing under `src/` or `tests/`.

**VERDICT: PASS** (0 failed; 5 PENDING in m6 as expected; no new failures vs report 411).
