# Report 425: tester, consolidation 008 step C1, fixer's fix of the replay label mismatch (reports/fixes/001)

- Date: 2026-11-17. Mode: step. Commit: `c7edd38`. Under test, uncommitted: `src/su2plaq/compress/replay.py` (+25 -6) and new `tests/unit/test_compress_replay_duplicate_labels_unit.py`.
- Plan in force: `prompts/008` §7, §10 C1; replay procedure `prompts/204` §6.2. Related: reports/fixes/001, reports/tests/420, 424.
- Raw numbers: `results/tester/425-c1-replay-fix.json`. Scratch copies (`git archive HEAD` exports, never the real tree) and logs in the scratchpad `c1/`.
- Resources: replays each as its own `tools/run-capped` command pinned to one core (twelve core 1, fuzzy_ub core 2, mutations core 4), unit tests `-n 4` on cores 5-8.

## Verdict: PASS

## Results

| check | expected | got | result |
|---|---|---|---|
| 1a repeated labels / program paths / ids in every committed round file (`git archive HEAD`: fuzzy_link 3 rounds 5 cand., fuzzy_ub 14/42, rishon 5/19, spinnet 6/23, twelve 6/22) | fixer: exactly twelve r04 and fuzzy_ub r05 repeat a label; paths and ids unique | repeated labels only in `twelve round-004.json` (`004-clean-frame-inwalk-pa` x2) and `fuzzy_ub round-005.json` (`005-two-swap-single-middle` x2); repeated program paths: none anywhere; repeated ids: none anywhere | PASS (cause confirmed) |
| 1b saved failed runs vs recorded rounds (`should-be-deleted/c1-failed-20261117/{twelve,fuzzy_ub}/results-*` against the HEAD round files), compared by position on (program_path, label, id, valid, reason, key) | no candidate differs | twelve 6 rounds, 22 candidates: 0 differences, 0 count mismatches; fuzzy_ub 14 rounds, 42 candidates: 0 differences, 0 count mismatches. The failed runs had built exactly the recorded candidates; only the comparison raised | PASS |
| 2a mutation, round-0 candidates swapped (fuzzy_link copy, real replay) | raises | `RuntimeError: round 0: ... position 0: recorded (seed/010-general_polish.py, 'general+polish'), replayed (seed/000-general-ue.py, 'general')`, exit 1 | PASS |
| 2b mutation, one recorded label changed | raises | `RuntimeError: round 1: ... position 0: recorded (..., '001-bell_parity_net13_X'), replayed (..., '001-bell_parity_net13')`, exit 1 | PASS |
| 2c mutation, one program_path replaced by another valid program's path | raises | `RuntimeError: round 1: ... position 0: recorded (F2/001-plane_bfs_frame_fusion12.py, '001-bell_parity_net13'), replayed (..., '001-plane_bfs_frame_fusion12')`, exit 1 | PASS |
| 2d mutation, one candidate dropped from round 0 | raises | `RuntimeError: round 0: ... 2 recorded vs 3 replayed; missing [], extra [(seed/qiskit_l3.circuit, 'qiskit_l3')]`, exit 1 | PASS |
| 2e control, no mutation (same copy recipe) | exit 0 | exit 0 in 5 s | PASS |
| 2f the check on the real twelve r4 / fuzzy_ub r5 / twelve r0 / fuzzy_ub r13 candidate lists (direct `_candidate_mismatch`) | identity passes; swap of the first two, one label changed, one path changed, last dropped, one extra: each flagged | all five mutations flagged in all four rounds; identity passes. The swap of the first two candidates would have been accepted by the old label-set rule (`old_rule_accepts_swap` True): the new check is stricter than the old one, in the duplicate-label rounds too | PASS |
| 3a full replay twelve/step on a copy of HEAD, patched tool, own command, core 1, `run-capped` | exit 0, keys equal, lost / key_changed / refused = [], best unchanged r05-F2-005 (111, 912, 1663, 31), logs byte-identical | exit 0, wall 425 s; 22 entries, `key_equal` True 22/22; `lost` [], `newly_valid` [], `key_changed` [], `refused` [], `unreplayed` []; best_old = best_new = `r05-F2-005` (111, 912, 1663, 31); `attempts_unchanged` and `discoveries_unchanged` True; sha256 of `compress/attempts` and `compress/discoveries` files equal before and after | PASS |
| 3b full replay fuzzy_ub/UB, own command, core 2 | same, best r12-F1-012 (83, 638, 1517, 10) | exit 0, wall 53 s; 42 entries, `key_equal` True 41, None 1 (`r00-seed-qiskit_l3`, invalid before and after, so `lost` and `newly_valid` stay empty); `lost` [], `key_changed` [], `refused` [], `unreplayed` []; best_old = best_new = `r12-F1-012` (83, 638, 1517, 10); attempts and discoveries byte-identical (sha256 equal) | PASS |
| 3c the two duplicate-label rounds in those replays | both candidates paired with their own id | fuzzy_ub: `r05-F1-005` and `r05-F3-005` each have `old_id` equal to their own id, `key_equal` True; twelve r4 `r04-F2-004` / `r04-F4-004` likewise (all 22 `key_equal` True) | PASS |
| 3d agreement with the fixer's worktree records (`should-be-deleted/fix-c1-wt/results/compress/{twelve,fuzzy_ub}/replay-008.json`) | same | per entry (id, old side, new key): twelve 22/22 equal, fuzzy_ub 42/42 equal; same best | PASS |
| 4a new unit file + the two replay unit files | pass | 13 passed (135 s) | PASS |
| 4b full unit suite in the main tree (`-n 4`, 513 s) | known red = 4 spinnet-step cases of `test_robust_hooks_unit.py` only | 1132 passed, 4 failed: `test_generic_report_leaves_a_track_summary_unchanged_and_names_the_refresh_command[spinnet-step]`, `test_compute_false_stale_cache_returns_none_without_build_or_write[spinnet-step]`, `test_compute_false_missing_cache_and_refresh[spinnet-step]`, `test_compute_false_fresh_cache_equals_the_hook_and_writes_nothing[spinnet-step]`. Each fails with `FileNotFoundError` for `results/compress/spinnet/summary.json` or `robust.json` (copied from the real tree into `tmp_path`; the uncommitted spinnet C1 replay moved both to `pre-008/`). No other failure | PASS (as expected) |
| 4c the 4 failures have no other cause | pass when the files exist | the same unit file run from a `git archive HEAD` export (files present, same src apart from replay.py): 12 passed, including the 4 spinnet-step cases | PASS |
| 5 six hashes vs the C0 freeze in STATUS | equal | provenance/twelve `99663fa6…e37`, lsh `88e0d76b…1ca`, spinnet `10f5727f…15c`, fuzzy_ub = fuzzy_link `b4bd20fe…7f9`, rishon `5f5decfa…f23`, spinnet loop `f1314a01…3d4`: all equal | PASS |
| 5b `replay.py` in no hash list | none | `python -I`: no registered encoding (twelve, spinnet, fuzzy_ub, fuzzy_link, rishon, lsh) lists a file with "replay" in `evaluator_files`; `SPINNET_CODE_FILES` has none; `git diff --stat -- src` shows only `compress/replay.py`; `check_lock` OK, `acceptance-check` PASS (acceptance-v22) | PASS |
| 6 real spinnet C1 output (read only) | invariants hold | `replay-008.json`: 6 rounds, 23 entries, `key_equal` True 23/23, `lost` [], `newly_valid` [], `refused` [], `unreplayed` [], best `r04-F1-004` (31, 1062, 2173, 17) before and after, `attempts_unchanged` and `discoveries_unchanged` True; `git status` shows no change in `compress/attempts` or `compress/discoveries` (byte-identical to HEAD); `pre-008/` round files and feedback and `compress/archive/spinnet-pre-008` are byte-identical to HEAD | PASS |
| 6b real fuzzy_link C1 output (read only) | invariants hold | 3 rounds, 5 entries, `key_equal` True 4, None 1 (the invalid qiskit seed, invalid before and after), `lost` [], `refused` [], best `r02-F2-001` (12, 644, 1183, 4) before and after, attempts and discoveries unchanged; `pre-008/` and `fuzzy_link-pre-008` archive byte-identical to HEAD | PASS |

### Do the real spinnet and fuzzy_link outputs stay valid after the fix?

Yes. They were made with the pre-fix `replay.py`, whose pass condition (unique labels, same label set, per-label pairing) is implied by the new one whenever labels are unique. Neither archive has a repeated label (check 1a). I ran the patched `_candidate_mismatch` on every round, recorded round (HEAD) against replayed round (the real tree): spinnet 6/6 rounds and fuzzy_link 3/3 rounds list the same (program_path, label) pairs in the same order (all "ok"). The record fields are computed by the same code path as before, so the post-fix tool would produce the same records. They do not need to be redone. (The `provenance` of those records names the pre-fix source state; the numbers do not depend on it.)

## Review of the change against prompts/008 §7 and prompts/204 §6.2

- §6.2 step 4 feeds each round "that round's program paths in recorded order"; the program path is the input of the replay and a unique key in every committed round, so it is the right identity. A label is only the file stem (`pathlib.Path(path).stem`, `compress/round.py`).
- The new rule is at least as strict as the old one: equal (path, label) sequences imply equal label sets; it adds three conditions: same program path, each candidate's label equal to its own recorded one (not only the set), same order. Demonstrated: the swap of two candidates passes the old rule and fails the new one (2f).
- Nothing else changed in the invariants: nothing lost, keys equal, best unchanged, attempts and discoveries restored in a `finally` and compared by bytes (the logs were byte-identical in all my runs).
- A recorded round with a missing or repeated `program_path` is refused with `ValueError` before anything is moved (the fixer's unit test covers it; on all committed rounds the precondition holds).
- No `try`/`except` added; the error message names the first difference (position and both pairs, or the length and the missing/extra pairs).

## Observations (not failures)

- O1: the full unit suite in the main tree rewrote `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json` (provenance commit only, as in reports 420 and 424); I restored it with `git checkout --`. A check of all 137 modified or untracked files under `compress/` and `results/` against the sha256 list taken before the run passed, and `git status` is identical to before; no real archive or results file was written by me.
- O2: the 4 red unit cases will turn green once `results/compress/spinnet/{summary,robust}.json` exist again (the post-C1 headline refresh writes them, or the coordinator's commit of the moved state); they test the report and cache code, which the replay fix does not touch.
- O3: twelve replay wall time 425 s on one pinned core (not slowed by the two parallel jobs).

## Counts

passed: 13 targeted unit + 1132 of 1136 full unit + 6 mutation/direct checks + 2 full replays; failed: 4 (known, cause confirmed); new failures: none.
