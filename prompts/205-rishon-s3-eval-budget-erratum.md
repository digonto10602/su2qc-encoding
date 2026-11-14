# 205 — Rishon erratum: the round-0 Qiskit L3 seed may be recorded as `eval_budget` (one branch of locked test M6_S3); how to run step C2

Date: 2026-11-13 · Author: planner · Git commit at writing: `77b68ce` (branch `merge-desktop-tracks`) · Track R (rishon, numbers 200–299; `next-num` proposed 402)
Approved by Digonto in chat, 2026-11-13. (Approval of §9 item 1, relayed to the planner by the coordinator; the diff of §4 was then applied by the coordinator and the one `LOCK.json` entry updated by the planner, superseding the "NOT applied" paragraph of §4.)
Plan in force for track R = `prompts/204-rishon-det-term-amendment.md` on `prompts/203-rishon-m6-plan.md`, **as amended by this file**. Everything not mentioned here stays binding. No source file, no tolerance, no validity rule and no hash changes.
Research and all measurements: `reports/research/204-rishon-eval-budget-timing.md`. Methods: `docs/METHODS-rishon.md` R10 (paragraph "Time-limit verdicts"), R15 (expected outcome of the replay).

Words used. *Seed*: a circuit the loop starts from in round 0. *Windowed Qiskit L3*: the general circuit cut into windows of 32 gates, each optimised by Qiskit's level-3 transpiler; the baseline "what a standard compiler gives". *Nominal / alternate pairs*: the three angle pairs at which a candidate must be exact, $(0.37,0.61)$, then $(0.91,0.23)$ and $(1.70,1.00)$. *Verdict*: the evaluator's judgement of one circuit at one pair. *`eval_budget`*: the verdict "not judged within the time limit" (nominal pair 300 s, each alternate pair 120 s, elapsed time). *Replay*: re-running stored rounds under a new evaluator hash (`prompts/204` §6.2). *SMT sibling*: the second logical CPU of the same physical core. *Erratum*: a correction of a locked acceptance test.

## 0. Trigger
Coordinator request, 2026-11-13. The rishon builder rehearsed step C2 on a scratch copy (record: scratchpad `rehearsal_root/results/compress/rishon/replay-204.json`). Result: all 16 valid entries keep their keys, `r00-seed-001` (general-rccx) and `r00-seed-002` (general-mcx) become valid, the best is unchanged, **but `r00-seed-qiskit_l3` is recorded `eval_budget`**. Locked slow test `tests/acceptance/m6/test_rishon_m6_seeds.py::test_M6_S3_round0_recorded` allows only `ok` or `pruning_bound` for that seed, so the real replay would turn it red. The builder changed neither the budget nor the test.

## 1. Diagnosis
1. `prompts/204` §6.2 expected the L3 seed to become valid. That expectation was mine and was untested: under the old 1 % prune cap the seed was rejected at the nominal pair, so its two alternate pairs had never been run or timed.
2. The seed is exact. Measured without a time limit at the three pairs: `ok`, certified, `op_norm_error` $\le4.18\times10^{-12}$ (tolerance $10^{-10}$), `dropped_total` $\le3.84\times10^{-12}$ (cap $10^{-11}$), Gauss residual $\le1.5\times10^{-14}$, identical gate skeleton (`scratch/planner/p205/l3.json`).
3. It is slow: one verdict took 151.8 / 140.0 / 134.7 s (builder, `l3time.log`) and 429.0 / 249.4 / 226.2 s (planner, 30 minutes later, busier machine) for the nominal / first / second alternate pair. Same machine, same code, same circuit: **a factor 1.7 to 2.8 from load alone**. The limits are 300 s and 120 s. The other seeds are far from the limits under the heaviest load measured: `general` 41 / 34 / 38 s, `general-rccx` 59 / 52 / 53 s.
4. So `eval_budget` for this seed is a statement about the machine at that moment, not about the circuit. `S3` was written in the form "recorded as the evaluator judged them", and my list of possible judgements for an exact circuit was incomplete.

## 2. Decision: option (b), narrowed. Options (a) and (c) rejected, with reasons
**(b) Erratum to `M6_S3`: for the label `qiskit_l3` only, `eval_budget` is a third accepted outcome, under five conditions** (§4). No rule and no hashed file changes.

Why this keeps results reproducible: the L3 verdict can differ between machines or runs (`ok` or `eval_budget`), and nothing else can depend on it:
- it is a circuit-valued baseline without a program file, so it is never a parent of a proposal (`rishon/compress/round.py::_seed_candidates`);
- it has 9 688 CX against 6 874 for the rccx seed, so it is not the round-0 best whether valid or not; the amended test checks this (condition 5);
- `M6_G1`–`G5`, the headline rule and `m2c::test_M2C_G1[rishon-step]` do not need it to be valid. Keys, best id, headline and robust key are identical in both cases.

**(a) Raise the rishon alternate budget — rejected.** (i) It does not make the verdict reproducible: the nominal pair itself measured 429 s against its 300 s limit under load, so any number of seconds can be crossed. (ii) After step B5 of `prompts/008` (locked, acceptance-v18, §3.3) `rishon.compress.evaluate.evaluate_circuit` is the shared function; a rishon-only value would need a new registry field in that locked plan, or a rule change for all five encodings. (iii) It is a rule change in the middle of a loop, for a row that decides nothing.

**(c) Count work instead of seconds — not now.** It is the only option that makes time-limit verdicts reproducible in general. It needs a counter in the shared hashed engine files, a new budget field in the shared `TaskSpec` (the spec text and spec hash of every encoding change), a rule for the second engine (`aer_mps`, which has no such counter), and changes to locked tests of several tracks. That is a cross-track plan change inside the `prompts/008` window for the benefit of one baseline row. Listed in §9 as an optional decision for Digonto; my recommendation is no.

## 3. The rule as it stands (no change; stated once so that reports use the same words)
$$\texttt{eval\_budget}\iff t_{\rm wall}(\text{nominal verdict})>300\ {\rm s}\ \ \text{or}\ \ t_{\rm wall}(\text{an alternate verdict})>120\ {\rm s}.$$
It is an execution verdict: `valid = False`, never cached, no statement about the physics. A row with this reason is reported as "not judged within the time limit", never as "wrong". If the nominal verdict finished, the row carries it (and the gate counts, with the $T$ count as an estimate, `measured: false`).

## 4. Acceptance test changed (one file, one test, no tolerance changed)
`tests/acceptance/m6/test_rishon_m6_seeds.py::test_M6_S3_round0_recorded` (slow). The loop over the three "as judged" labels gains a third branch. For `general-rccx` and `general-mcx` nothing changes (`ok` or `pruning_bound` only). For `qiskit_l3`, reason `eval_budget` is accepted iff all hold:

| # | Condition on the `qiskit_l3` row | Why |
|---|---|---|
| 1 | `valid` is false, `key` is null, `mode == "full"` | an unjudged circuit is never counted as valid |
| 2 | nominal verdict recorded with `ok` true, `certified` true, `op_norm_error` $\le10^{-10}$, `dropped_total` $\le10^{-11}$ | the existing validity tolerances, unchanged; the row still proves the circuit exact at the nominal pair. A timeout at the nominal pair (no verdict, no counts) stays a failure |
| 3 | `skeleton_equal` true; fewer than 2 entries in `alt_ok`, all true | the time ran out at an alternate pair; no finished alternate was wrong |
| 4 | `metrics["cx"]` present | Report 6 quotes the L3 gate counts from this row |
| 5 | `metrics["cx"]` $>$ `best_key[0]` of the round | the unjudged row could not have been the round's best seed; if it could, the round-0 best would depend on machine load and the test must fail |

Justification for accepting the extra outcome (quantitative): §1 item 3 — the wall time of the identical verdict varies by a factor up to 2.8 on this machine, and the seed sits at 1.1–2.1 times the 120 s limit, so a test that demands `ok` tests the machine's load. All numerical tolerances are the ones already locked.

Exact diff (also at `scratch/planner/p205/s3-erratum.patch`, sha256 `e4feda6455d33281ebffd188e538f95b9568b323519d386a918da169c7d6c249`; `git apply --check` passes on `77b68ce`; sha256 of the resulting test file `f21a2042ae12f1fd53083f9bca5bd113f147ca062fb5f86861ae3d4bfec3c503`):
```diff
--- i/tests/acceptance/m6/test_rishon_m6_seeds.py
+++ w/tests/acceptance/m6/test_rishon_m6_seeds.py
@@ -78,7 +78,9 @@ def test_M6_S2_polish_and_l3_trial():
 def test_M6_S3_round0_recorded(root):
     """The real round 0 (results/compress/rishon/round-000.json, step 6.5): five labelled seed rows, the external sources
     with reasons, valid rows satisfy the tolerances, the two ladder variants are recorded as the evaluator judged them
-    (ok or pruning_bound: both are physically exact, research 202 §3), and the archive best is the cheapest valid seed."""
+    (ok or pruning_bound: both are physically exact, research 202 §3), the windowed Qiskit L3 baseline likewise (ok,
+    pruning_bound, or eval_budget at an alternate pair with an exact nominal verdict: prompts/205), and the archive best is the
+    cheapest valid seed."""
     f = root / "results" / "compress" / ENC / "round-000.json"
     if not f.exists():
         pytest.fail("PENDING: results/compress/rishon/round-000.json missing (step 6.5)", pytrace=False)
@@ -102,16 +104,28 @@ def test_M6_S3_round0_recorded(root):
     # R11).  Under the rishon cap of prompts/204 (10 % = 1e-11; measured dropped_total 3.8e-12, 2.9e-12, 2.7e-12) they are expected
     # valid; the test keeps the "recorded as the evaluator judged them" form: a rejection must carry that reason, a bound above the
     # cap in force and its true error, never another one.
+    # prompts/205 (erratum): `eval_budget` is the evaluator's wall-clock verdict (nominal pair <= 300 s, each alternate pair <= 120 s,
+    # METHODS-rishon R10).  It says nothing about the physics and depends on the machine's load: the same verdict of the windowed
+    # Qiskit L3 circuit measured 135-152 s and 226-429 s per pair on this machine within one hour (research 204), against 34-59 s
+    # for the three ladder seeds.  For that one circuit-valued baseline (no program, never a parent) it is accepted as a third
+    # "as judged" outcome, under conditions that keep the row harmless and informative: the budget ran out at an alternate pair,
+    # the nominal verdict is recorded and exact, every alternate that finished is ok, the gate counts are recorded, and the row
+    # could not have been the round's best (more CX than the best valid seed).  The ladder seeds keep the two outcomes of prompts/204.
     for lab in ("qiskit_l3", "general-rccx", "general-mcx"):
         c = by[lab]
-        assert c["reason"] in ("ok", "pruning_bound"), (lab, c["reason"])
+        allowed = ("ok", "pruning_bound", "eval_budget") if lab == "qiskit_l3" else ("ok", "pruning_bound")
+        assert c["reason"] in allowed, (lab, c["reason"])
         assert c["valid"] == (c["reason"] == "ok") and c["mode"] == "full"
         v = c["verdict"]
         if c["reason"] == "ok":
             assert v["op_norm_error"] <= 1e-10 and v["certified"] and c["skeleton_equal"] and all(c["alt_ok"])
             assert v["dropped_total"] <= 1e-11, (lab, v)
-        else:
+        elif c["reason"] == "pruning_bound":
             assert v["block_error"] + v["leak_amplitude"] <= 1e-10 and v["dropped_total"] > 1e-11, (lab, v)
+        else:
+            assert v["ok"] is True and v["certified"] is True and v["op_norm_error"] <= 1e-10 and v["dropped_total"] <= 1e-11, (lab, v)
+            assert c["skeleton_equal"] is True and len(c["alt_ok"]) < len(_spec().alt_angles) and all(c["alt_ok"]), (lab, c["alt_ok"])
+            assert c["key"] is None and c["metrics"]["cx"] > d["best_key"][0], (lab, c["metrics"].get("cx"), d["best_key"])
     ext = {x["source"]: x for x in d["external"]}
     assert set(ext) == EXTERNAL
     for s in ("paulo34", "lean22", "lean22_v2", "spinnet15"):
```
**The diff is NOT applied in the tree.** With the test file changed and `tests/acceptance/LOCK.json` not updated, every acceptance run of every track aborts (`ACCEPTANCE LOCK BROKEN`); the permission system did not let the planner edit `LOCK.json` in this run. The tree is at the locked state (`python tools/check_lock.py` → `LOCK OK`). Applying it is §8.

How the amended test was checked (research 204 §5): called on the builder's rehearsal root and on 14 mutated copies of its `round-000.json` with `scratch/planner/p205/check_s3_erratum.py`: 4 cases that must pass do (as rehearsed; L3 `ok`; timeout after one finished alternate; L3 `pruning_bound`), 11 that must fail do, each at the intended assertion (nominal timeout, two alternates recorded, a failed alternate, nominal error $10^{-9}$, not certified, bound above the cap, L3 cheaper than the best, reason `error`, rccx `eval_budget`, general `eval_budget`, `valid: true`). On the real tree the test is `PENDING` on the replay, as before. Unchanged on purpose: `M6_G5` and `m2c::test_M2C_G1` (both already hold for either outcome), `general` and `general+polish` (must be `ok`), every tolerance.

## 5. Interface
No new or changed production name. `su2plaq.rishon.compress.evaluate`, `replay`, `round` stay as built. No stub needed.

## 6. Steps (amendments to `prompts/204` §6.2 and §7)

**Text of `prompts/204` replaced.** §6.2 "Expected outcome": the 16 valid entries keep their keys; `r00-seed-001` and `r00-seed-002` become valid; `r00-seed-qiskit_l3` becomes valid **or** is recorded `eval_budget` at an alternate pair; round-0 best `r00-seed-001` $(6874,17694,31954,58)$ (rehearsal value); global best and headline unchanged. §12 second bullet gains: "`eval_budget` for `qiskit_l3` at an alternate pair is allowed by S3 (`prompts/205`); report the row".

| Step | Who | What | Done-check | Acceptance ids |
|---|---|---|---|---|
| E0 | coordinator | Digonto's approval (§9 item 1), then §8: apply the diff, update the one `LOCK.json` entry, lock, commit | `python tools/check_lock.py` → `LOCK OK`; `pytest --collect-only -q tests/acceptance` clean; `S3` still `PENDING` on the replay | — |
| C2 (amended) | coordinator, then tester | The replay of `prompts/204` step C2, in the `prompts/008` window as its rishon refresh (case c1) if that is how it is scheduled; run conditions below. Tester report (mode `step`) as in `prompts/204`, with the two changes below | `replay-204.json` as `prompts/204` §6.2; `lost == []`; the 16 keys identical; `r00-seed-001`, `r00-seed-002` in `newly_valid`; `r00-seed-qiskit_l3` either in `newly_valid` or `eval_budget` with a recorded exact nominal verdict; best and headline unchanged | `tests/acceptance/m6/test_rishon_m6_seeds.py::test_M6_S3_round0_recorded` (slow), `tests/acceptance/m6/test_rishon_m6_three_layer.py::test_M6_G5_replay_record`, `tests/acceptance/m6/test_rishon_m6_gate.py::test_M6_G1_archive_best_valid_and_not_worse_than_seed` (slow), `::test_M6_G2_best_synthesised_reverified`, `::test_M6_G3_best_touches_no_outer_qubit`, `::test_M6_G4_summary_and_budgets`, H1, H2 (slow) — the list of `prompts/204`, unchanged |

**Run conditions for the real replay (they matter only for the timed verdicts of round 0).**
1. One fast physical core for the replay alone: logical CPUs come in sibling pairs $(0,1),(2,3),\dots,(14,15)$; pin to one of a pair (`taskset -c 2`) and keep the other free. Never CPUs 16–19 (slower cores).
2. No evaluation, proposer or acceptance job on the machine until round 0 has finished (the first 40 minutes); this is precondition P4 of `prompts/008` §8 anyway.
3. Pre-flight, on the same CPU, immediately before: time the nominal verdict of the L3 seed. Start the replay only if it takes at most 200 s (two thirds of the 300 s limit; the rehearsal ran at 152 s). Command: `taskset -c <cpu> tools/run-capped python scratch/planner/p205/time_seed_pairs.py qiskit_l3 <out.json>` and read the first printed row (stop it after that row), or the same six lines as the builder's `l3time.py`.
4. Command as in `prompts/204`: `taskset -c <cpu> tools/run-capped python -m su2plaq.rishon.compress.replay --kind step`, background, on a clean commit.

**Tester additions for C2.** (i) If the L3 row is `eval_budget`: verify the L3 seed without a time limit at the alternate pairs with the tester's own script (the circuit is `baselines.qiskit_l3(spec.with_angles(a, b), seed=12345)`): `ok`, certified, `op_norm_error` $\le10^{-10}$, `dropped_total` $\le10^{-11}$, Gauss $\le10^{-10}$, skeleton equal; report the wall times and the load average. Planner values to compare: research 204 §2. (ii) Report which of the two outcomes the committed round file has.

**Report 6.** The L3 row reads, if `eval_budget`: "windowed Qiskit L3: 9 688 CX; exact at the nominal angles (error $4.1\times10^{-12}$, certified); the alternate-angle checks need 135–250 s each on this machine and exceed the loop's 120 s limit, so the loop records the row as not judged in time; verified exact at all three pairs outside the loop (tester report)". Baselines for the compression ratio stay the ccx general circuit (10 102 CX) and the cheapest valid seed (rccx, 6 874 CX).

## 7. Do-not-retry (additions)
- Raising, removing or bypassing the time limits for one seed or one encoding (a rishon-only budget, a larger `eval_budget_s`, calling the verdict with another budget inside the round): rule change, hashed file, undone by `prompts/008` B5.
- Editing the `qiskit_l3` row of a round file or of the replay record by hand, or inserting the seed into the archive after an untimed check.
- Re-running only round 0 into an existing `replay-204` record, or a second replay with the same tag.
- Accepting `eval_budget` for `general`, `general+polish`, `general-rccx`, `general-mcx` or any archived program: their margins are at least 2 under the heaviest load measured; a timeout there means the machine was unfit for the run.
- Moving the L3 seed to the external (counts-only) rows: S3 requires the label among the candidates, and the nominal verdict would be lost.

## 8. Coordinator: how to apply and lock (after §9 item 1)
```
git apply scratch/planner/p205/s3-erratum.patch          # or apply the diff of section 4 by hand
sha256sum tests/acceptance/m6/test_rishon_m6_seeds.py    # must print f21a2042ae12f1fd53083f9bca5bd113f147ca062fb5f86861ae3d4bfec3c503
# tests/acceptance/LOCK.json: replace the value of "tests/acceptance/m6/test_rishon_m6_seeds.py"
#   9307f1c42667025b30c20faf53ef9296852bd2d25fca2854c4a39d575b6dcaaf  ->  f21a2042ae12f1fd53083f9bca5bd113f147ca062fb5f86861ae3d4bfec3c503
python tools/check_lock.py                               # LOCK OK
~/.claude/bin/acceptance-lock "prompts/205-rishon-s3-eval-budget-erratum.md"
```
Then: counters in STATUS need no reset for running steps (no step was failing); record §9 under Decisions / For Digonto; continue with C1 → (008 window) → C2.

## 9. Risks, stop conditions, decisions for Digonto
- **The erratum changes a locked test.** Global rule: an agent believing a locked test wrong stops the loop until Digonto agrees. Item 1 below must be answered before §8.
- **L3 times out at the nominal pair in the real replay** (the row has no verdict and no counts; S3 red at the new branch), or **a previously valid entry or a ladder seed comes out `eval_budget`** (`lost != []` or S3 red): the machine was too busy. Do not commit. Restore the tracked files of `results/compress/rishon`, `compress/archive/rishon`, `compress/attempts/rishon.jsonl`, `compress/discoveries/rishon.md` from the clean commit, move the untracked replay output (`results/compress/rishon/pre-204`, `replay-204.json`, `compress/archive/rishon-pre-204`) out of the tree into a new folder (nothing deleted, no history rewritten), and run again under the conditions of §6. Twice in a row → ask the planner.
- **Any reason other than `ok` / `pruning_bound` / `eval_budget` for a seed, or an L3 nominal verdict that is not exact:** physics or code problem → `fixer`, as before.
- `prompts/008`: no change needed. Case c1 runs C2 as written here. Case c2 (its erratum E2) edits other lines of the same test (the replay-record lookup); the two changes do not overlap.

Decisions for Digonto:
1. **Needed now:** approve this erratum to locked test `M6_S3` (accept `eval_budget` for the Qiskit L3 baseline seed under the five conditions of §4). Default if not approved: C2 cannot pass S3 on a busy machine; the alternatives are (a) or (c) of §2.
2. Optional, my recommendation is no: replace the seconds limits by a deterministic work count for all encodings (option (c)), as an addition to `prompts/008`.
3. For information: the committed round-0 file may show the L3 row as `ok` or as `eval_budget` depending on machine load during the replay; no key, best entry or headline depends on it.

## 10. Expected cost
E0: minutes. Pre-flight: 3–8 min. Replay: 47 min measured in the rehearsal (2 822 s; round 0 2 220 s), peak 2.2 GB. Tester: one report; the untimed L3 check adds 5–15 min, peak 2.0 GB. No builder call.
