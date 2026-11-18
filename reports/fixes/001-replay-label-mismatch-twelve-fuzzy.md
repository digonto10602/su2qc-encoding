# Fix 001 — replay "candidates differ" on twelve round 4 and fuzzy_ub round 5 (duplicate labels)

- Date: 2026-11-17
- Commit: `cd69b32` (= hash freeze `02c499d` + one STATUS line; `src/` identical to the freeze)
- Prompt in force: `prompts/008-merged-repo-consolidation.md`, Phase C step C1 (§10), method §7; replay procedure `prompts/204` §6.2
- Related: reports/tests/420 (B7 replay tool), reports/tests/424 (B7-fix N1/N2); evidence `should-be-deleted/c1-failed-20261117/`
- Work done in the git worktree `should-be-deleted/fix-c1-wt` (detached at `cd69b32`); the real tree was not touched.

## 1. What was asked
C1 replays of `twelve/step` and `fuzzy_ub/UB` (`python -m su2plaq.compress.replay --encoding E --kind K --tag 008`) stopped with
`RuntimeError: round 4 (twelve) / round 5 (fuzzy_ub): the replayed candidates differ from the recorded ones` (replay.py:146).
Find the root cause; decide between (a) the comparison is wrong for a legitimate archive and (b) the current code builds
different candidates.

## 2. Failure
`replay()` re-runs every recorded round, then compares each new round file with the recorded one by **label** (jargon: the label
of a candidate is the file stem of its program, e.g. `004-clean-frame-inwalk-pa`):

```python
nmap = {c["label"]: c for c in new["candidates"]}
if len(nmap) != len(new["candidates"]) or {c["label"] for c in old["candidates"]} != set(nmap):
    raise RuntimeError(...)
```

## 3. Hypotheses and experiments

Scan of every committed round file at HEAD (`git show HEAD:results/compress/*/round-*.json`; inline script, section 3.1), plus
a comparison of the recorded rounds (`moved-results-pre-008/`) with the replayed ones (`results-<enc>/`) in the saved evidence.

| # | Hypothesis | Experiment | Result |
|---|---|---|---|
| H1 | Duplicate labels inside one round | count labels / program paths / ids per round in all committed round files | **Confirmed.** Exactly two rounds in the whole repo have a repeated label, and they are exactly the two failing ones: twelve round 4 (`F2/004-clean-frame-inwalk-pa.py` and `F4/004-clean-frame-inwalk-pa.py`, ids `r04-F2-004`, `r04-F4-004`), fuzzy_ub round 5 (`F1/` and `F3/005-two-swap-single-middle.py`, ids `r05-F1-005`, `r05-F3-005`). Program paths and ids are unique in every round of every encoding. |
| H2 | A recorded candidate failed to build or was dropped (Gauss check, prune cap, timeout, budget) | candidate counts and `(valid, reason)` per round, old vs replayed, in the evidence | Refuted: same counts in every round (twelve 5/4/4/3/3/3, fuzzy_ub 3 each); every candidate has the same `valid` and `reason`. |
| H3 | Label assignment depends on order or state | compare the `(program_path, label)` sequence old vs replayed | Refuted: identical sequences, same order, in all 6 twelve and 14 fuzzy_ub rounds. |
| H4 | Round file written by an older code version with another label scheme | labels old vs replayed | Refuted: labels identical. The label is `pathlib.Path(path).stem` (compress/round.py:189), unchanged. |
| H5 | Nondeterminism | `(id, label, valid, reason, key)` old vs replayed for every candidate | Refuted: twelve 22/22 identical, fuzzy_ub 42/42 identical. |

The rounds of the failed C1 runs were therefore complete and correct; only the comparison after the last round raised. The
duplicate label makes `nmap` one element shorter than the candidate list, so `len(nmap) != len(new["candidates"])` is true even
though nothing differs.

### 3.1 Why it was not seen before
spinnet (23 candidates), fuzzy_link (5) and rishon (19, reports/tests/420) have no repeated stem in any round; the B7 unit tests and
m2c Y1 use fuzzy_link / a twelve seed round only.

## 4. Root cause
Verdict **(a)**: the replay comparison used a non-unique field as a candidate's identity. A label is a program file stem, and two
proposer families may (and did) name their files the same in one round; the ids (`r<round>-<family>-<nnn>`) and the program paths
differ. The current code builds exactly the recorded candidates. Not a regression of the consolidation; no hashed file involved.

`replay.py` is not hashed: `provenance.evaluator_files(e)` for twelve (21 files), spinnet (26), fuzzy_ub (26), fuzzy_link (26),
rishon (31), lsh (27) contains no `replay` file; the spinnet loop hash (`SPINNET_CODE_FILES`) does not either.

## 5. Fix (`src/su2plaq/compress/replay.py`, unhashed)
1. Before anything is moved: every recorded candidate must have a `program_path`, and no path may appear twice in a round,
   else `ValueError` (nothing touched).
2. After the rounds: new helper `_candidate_mismatch(old, new)`; the replayed round must list **the same `(program_path, label)`
   pairs in the same order** as the recorded round, else `RuntimeError` naming the first difference (position, recorded pair,
   replayed pair) or the missing / extra pairs. Old and new candidates are then paired by position.
3. Module docstring updated.

**Justification that this is not a weaker check** (prompts/008 §7, prompts/204 §6.2). §6.2 step 4 re-runs each round with "that
round's program paths in recorded order"; the program path is what the replay feeds the round function, so it is the candidate's
identity. The new condition implies the old one whenever the old one was meaningful (unique labels): equal pair sequences give equal
label sets and unique new labels. It is stricter in three ways: the program path must match, each candidate's label must match
its own recorded candidate (not only the set), and the order must match. Measured: every replay that exists reproduces the
recorded pair sequence exactly in order (spinnet 23, fuzzy_link 5 from C1 in the real tree, read only; rishon 19 in
`should-be-deleted/t420-scratch/{ri,rs}_new`; twelve 22 and fuzzy_ub 42 here). The invariants of the record (nothing lost, keys
equal, best unchanged, attempts and discoveries byte-identical) are computed exactly as before.

Diff: `src/su2plaq/compress/replay.py` +25 −6; new `tests/unit/test_compress_replay_duplicate_labels_unit.py` (79 lines).
Patch: `should-be-deleted/fix-c1-wt/scratch/fix-c1.patch` (`git apply --check` clean against the main tree).

## 6. Regression test
`tests/unit/test_compress_replay_duplicate_labels_unit.py` (fuzzy_link kind UE under `tmp_path`, about 5 s): round 0 (seeds) and
round 1 with the same program written as `F1/001-same-stem.py` and `F2/001-same-stem.py`.
- `test_round_with_duplicate_labels_replays_with_all_invariants`: replay passes; both round-1 entries paired with their own ids,
  `key_equal` true, `lost == []`, best unchanged, logs restored.
- `test_replayed_round_with_other_candidates_is_still_an_error`: a recorded label changed → `RuntimeError` naming position 1.
- `test_recorded_round_naming_a_program_twice_is_refused_before_anything_moves`: repeated program path → `ValueError`, no
  `pre-<tag>` folders created.

Before the fix (HEAD `replay.py`): 3 failed, the first with the exact C1 message `round 1: the replayed candidates differ from the
recorded ones`. After the fix: 3 passed in 4.6 s
(`taskset -c 0-8 tools/pytest-safe -n 3 -q tests/unit/test_compress_replay_duplicate_labels_unit.py`).

## 7. Full replays in the worktree (committed archives at `cd69b32`, no evaluator cache, `lean=False`)
Commands (from the worktree, `PYTHONPATH=src`, one thread each):
`taskset -c 2 tools/run-capped python -m su2plaq.compress.replay --encoding twelve --kind step --tag 008` and the same with
`taskset -c 4 ... --encoding fuzzy_ub --kind UB`. Records: `should-be-deleted/fix-c1-wt/results/compress/{twelve,fuzzy_ub}/replay-008.json`.

| | twelve / step | fuzzy_ub / UB |
|---|---|---|
| exit code | 0 | 0 |
| wall time | 433 s (rounds 57, 189, 26, 22, 20, 119 s; the unit suite ran on other cores at the same time) | 92 s |
| rounds | 0–5 | 0–13 |
| entries / valid before and after / `key_equal` true | 22 / 22 / 22 | 42 / 41 / 41 (the one invalid entry is invalid before and after, same reason) |
| `key_changed`, `lost`, `newly_valid`, refused, unreplayed | all `[]` | all `[]` |
| `best_old` = `best_new` | `r05-F2-005`, key $(111, 912, 1663, 31)$ | `r12-F1-012`, key $(83, 638, 1517, 10)$ |
| `id == old_id` for all entries; same `(valid, reason)` | yes | yes |
| attempts / discoveries unchanged (flag and `git status` clean) | yes / yes | yes / yes |
| Lean records carried | 5 | 12 |
| `evaluator_sha256` (new) / `encoding_sha256` | `99663fa6…` / `99663fa6…` | `99663fa6…` / `b4bd20fe…` |
| old evaluator hashes | `810e86f2…`, `0bd7e7d9…` | `0bd7e7d9…` |
| duplicate-label entries handled | round 4: `r04-F2-004`, `r04-F4-004` | round 5: `r05-F1-005`, `r05-F3-005` |

## 8. Hashes (worktree source vs the C0 freeze in STATUS)
All six equal: provenance/twelve `99663fa6cd2550d9…`, lsh `88e0d76bce7b3af6…`, spinnet `10f5727f5379cb44…`,
fuzzy_ub = fuzzy_link `b4bd20fe811e5c99…`, rishon `5f5decfa34f53069…`, spinnet loop `f1314a01d7716b7a…` (full values checked
by string equality against STATUS).

## 9. Unit suite
Worktree, after both replays: `taskset -c 0,1,5-8 tools/pytest-safe -n 4 -q tests/unit` → **1121 passed, 15 failed** (485 s);
rerun `--lf -rf` gives the same 15. None of them imports `compress.replay`. All 15 come from the worktree, not from the fix:
- 14 Lean tests (`test_lean_project_unit` ×4, `test_lean_round_unit` ×1, `test_rishon_lean_exact_unit` ×3,
  `test_spinnet_lean_exact_unit` ×6): a fresh worktree has no built Lean packages (`lean/.lake` holds only `build/`, `config/`).
  In the main tree the same files pass (Lean built).
- `test_robust_hooks_unit.py::test_generic_report_keeps_an_existing_headline_block_and_writes_otherwise`: it copies the real
  `results/compress/twelve/` and reads `summary.json`, which the worktree twelve replay moved to `pre-008/` (as §7 prescribes).
  It passes in the main tree, where twelve is at HEAD.

The new regression file and `tests/unit/test_compress_replay_unit.py` pass in the full run.

**Hazard found while checking (main tree, not caused by this fix):** in the main tree
`tools/pytest-safe -n 4 -q -rf tests/unit/test_robust_hooks_unit.py` → 4 failed, 8 passed: the four `[spinnet-step]` cases
(`…leaves_a_track_summary_unchanged…`, `…compute_false_stale_cache…`, `…compute_false_fresh_cache…`, `…compute_false_missing_cache…`).
They read the real `results/compress/spinnet/{summary,robust}.json`, which the uncommitted spinnet C1 replay moved to
`pre-008/`. After the twelve C1 replay the twelve case above fails in the same way. These unit tests stay red until C3 rewrites
`summary.json`/`robust.json`, or until they are made self-contained (copy from `git show HEAD:` or a synthetic tree). That
change is for the builder, not part of this fix.

## 10. Verdict
**FIXED.** Root cause: `replay()` identified candidates by their label (program file stem), which is not unique within a round;
twelve round 4 and fuzzy_ub round 5 each contain two programs from different families with the same stem. The replayed
candidates were identical to the recorded ones. Fix in the unhashed `compress/replay.py`; the freeze holds.

Notes for the coordinator:
- Apply `should-be-deleted/fix-c1-wt/scratch/fix-c1.patch` to the main tree, run `graphify update .` there (the worktree has no
  `graphify-out/`), and send to the tester; then redo the twelve and fuzzy_ub C1 replays in the real tree.
- The evidence twelve and fuzzy_ub replays (in `should-be-deleted/c1-failed-20261117/`) are already correct in content; they can
  not be reused as is because the tool raised before writing `replay-008.json`; re-run with the fixed tool.
- Expect the 4 spinnet (now) and 1 twelve (after its real replay) robust-hooks unit tests to be red until C3 (section 9); do not
  count them against this fix.
- Side observation (not part of this fix): a two-job `( … ) & ( … ) & wait` line run through the agent shell started only the first
  job; launch each replay as its own command.
