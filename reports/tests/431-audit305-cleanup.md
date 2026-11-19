# Report 431: tester, clean-up of the non-blocking notes N2 to N7 of audit 305

- Date: 2026-11-19. Mode: step. Commit: `ef3b15a` (a STATUS-only commit on top of `0290a01`; the `src/`, `compress/` and `tests/` changes under test are uncommitted in the working tree).
- Plan in force: `prompts/008` (consolidation), `prompts/204` section M6 (replay / spec hash), audit `reports/audits/305-milestone-2c-consolidation.md`. Related: reports/tests/428, 429, 430.
- Raw numbers: `results/tester/431-audit305-cleanup.json`. Scripts and logs in the scratchpad (not committed).
- Resources: `taskset -c 0-8`, `tools/pytest-safe -n 4`, scratch experiments on cores 6-8.

## Verdict: PASS

All six builder claims hold, the full test runs show only the expected reds, and the frozen hashes are unchanged. Two small observations (O1, O2) are not failures. The N7 wording change does **not** change any recorded `spec_sha256` (check 8): keep it.

## Results

| # | check | expected | got | tolerance | result |
|---|---|---|---|---|---|
| 1 | N2: replay on a scratch copy (`fuzzy_link` UE, 3 rounds, 5 entries), untouched archive | `program_changed == []`, exit 0, field `old_program_sha256` in every entry | `program_changed: []`, exit 0, field present in 5 of 5 entries, `best_old == best_new == r02-F2-001 (12, 644, 1183, 4)` | exact | PASS |
| 2 | N2: same copy, one program file (`compress/programs/fuzzy_link/F1/001-bell_parity_net13.py`) got one appended comment line | flagged, exit 1 | `program_changed: ["r01-F1-001"]`, exit 1, stderr `REPLAY PROBLEM: ... program file sha256 differs from the one recorded in its round: ['r01-F1-001']`; keys and `lost` unchanged (the circuit is the same, only the bytes differ) | exact | PASS |
| 3 | N2: old records without the field | still pass | all five committed `replay-008.json` / `replay-204.json` lack the field; `problems()["program_changed"] == []` and `report()` returns 0 for each | exact | PASS |
| 3b | N2: no false alarm on the real archive (my own check) | every recorded round candidate's program sha equals the sha of the file now on disk | 111 candidates in the five encodings' round files, 0 mismatches (`.circuit` baselines skipped) | exact | PASS |
| 4 | N3: untampered rebuilt headline circuits vs HEAD source (`ks.step_circuit(.., "headline")`; same circuit by operation list with angles to 12 digits) | identical | twelve `r05-F2-005` (95 depth, 31 qubits, 60 CX), spinnet `r02-F1-002` (35 depth, 17 qubits, 19 CX): operation-list sha256 equal to HEAD; scratch copy equals the real tree | exact | PASS |
| 5 | N3: fuzzy `headline_step` untampered vs HEAD | CX 227, depth 151 | CX 227, depth 151, 50 qubits, 129 rotations, 72 fixed T, units `r10-F1-010` + `r02-F2-001`; identical to the HEAD run | exact | PASS |
| 6 | N3: tampered program (one appended comment line) on a scratch copy | raises `ProgramShaMismatch` | twelve `r05-F2-005`: `ProgramShaMismatch ... file sha256 b8129135a85e != archived 4f7fcb1eab11`; spinnet `r02-F1-002`: raised (`bf2538d35593` vs `750151e9ad41`); fuzzy_ub unit `r10-F1-010`: raised through `_cached_unit`; fuzzy_link unit `r02-F2-001` tampered alone: raised | exact | PASS |
| 7 | N4: committed `results/compress/*/robust.json` with `compute=False`, worktree vs HEAD source | same headlines | twelve `r05-F2-005` (111, 18548, 0, 34384, 31) $\bar T$ 927.4; spinnet `r02-F1-002` (31, 21840, 0, 46024, 17) 1092.0; fuzzy_ub `r10-F1-010` (83, 12688, 0, 30902, 10) 634.4; fuzzy_link `r02-F2-001` (12, 12576, 0, 23373, 4) 628.8; rishon `r04-F1-004` (228, 16876, 0, 28328, 53) 843.8. Output byte-identical to the HEAD run. None of the committed files carries the new key | exact | PASS |
| 8 | N4: changed constant on a scratch copy of `fuzzy_link` | stale -> recompute; legacy accepted | legacy cache (no key): loaded (`r02-F2-001`, 0.0 s). `compute=True` rewrites it with the current key. Set `LINEAR_TOL` $10^{-9}\to10^{-8}$: constants sha changes, `compute=False` returns `None` (stale), `compute=True` recomputes (3.4 s) and stores the new key. Setting it back makes the $10^{-8}$ cache stale again. Unit test also covers `OFFSET_TOL` and `CLIFFORD_OFFSET_UNIT` | exact | PASS |
| 9 | N5: no fixed `.json.tmp` name for the robust caches | none in spinnet / rishon / generic robust | `grep` of `src`: none in `spinnet/loop.py` or `rishon/compress/robust.py`; both import the shared `_atomic_write_text` (`mkstemp`, unique name). **Not literally "nowhere in src"**: see O1 | exact | PASS (see O1) |
| 10 | N6: file mode | 0644 under umask 022 | `_atomic_write_text` result `0o644`, no temp file left over | exact | PASS |
| 11 | N5/N6: the changed files in no hash list | none | union of `provenance.evaluator_files` over six registered encodings, `SPINNET_CODE_FILES`, `RISHON_EVALUATOR_FILES` and the registry entries (47 files): `spinnet/loop.py`, `rishon/compress/robust.py`, `compress/replay.py`, `compress/robust.py`, `compress/round.py`, `crosscheck/ks.py`, `fuzzy/headline_step.py` are in none | exact | PASS |
| 12 | six frozen hashes (values of report 428), computed at HEAD source (`git archive`) and in the working tree, before and after all runs | equal | provenance = twelve `99663fa6...3e37`; lsh `88e0d76b...c1ca`; spinnet `10f5727f...e15c`; fuzzy_ub = fuzzy_link `b4bd20fe...87f9`; rishon `5f5decfa...ef23`; spinnet loop `f1314a01...63d4`: all equal in all three computations | exact | PASS |
| 13 | N7: Clifford claim, `Clifford.from_operator(Operator(...))`, $\theta=k\pi/4$, $k=0..8$, eight gates | `rz,p,rx,ry`: Clifford iff $\theta\in\frac\pi2\mathbb Z$; `crz,crx,cry,cp`: iff $\theta\in\pi\mathbb Z$ | exactly that pattern, 0 unexpected out of 72 cases; $\mathrm{cp}(\pi/2)=\mathrm{diag}(1,1,1,i)$ (controlled-$S$) is not Clifford, so it needs T. `CLIFFORD_OFFSET_UNIT` = $\pi/2$ for the four single-qubit gates and $\pi$ for the four controlled ones | exact | PASS |
| 14 | unit tests `tests/unit` (`-n 4`) | all pass | 1155 passed, 0 failed (442 s); includes the new `test_audit305_cleanup_unit.py` and the updated duplicate-labels test | | PASS |
| 15 | `tests/acceptance/m2c`, slow included (`-n 4`) | all pass | 28 passed (27 s) | | PASS |
| 16 | `tests/acceptance` not slow (`-n 4`) | 13 PENDING reds only | 329 passed, 13 failed (1271 s): m6 L2, L3, L9, G6; m8 E2, S0, S2, S3, S4, S5, H1, L2; M11_T2. All 13 print `PENDING:` or the `NotImplementedError` of the LSH step 8.R. No new failure. The m6 spec test (committed `rishon-step.md` equals `render_spec`) passed | | PASS (13 expected PENDING) |
| 17 | `check_lock.py`, `acceptance-check` | OK | `LOCK OK`, `PASS: tests/acceptance matches acceptance-v22` | | PASS |

## The spec text change and `spec_sha256` (the extra check)

- **What `spec_sha256` is.** It is `TaskSpec.sha256()` in `src/su2plaq/compress/spec.py`: the sha256 of the JSON dump of the dataclass fields (encoding, kind, $\alpha$, $\beta$, order, alternate angles, tolerances, $\varepsilon$, budget, caps, trial inputs and seed). It does not read any markdown file and does not hash the rendered text.
- **Where it is recorded.** (a) every archive entry (`Entry.spec_sha256`, `compress/archive/<enc>/entries/*.json`); (b) every round file (`results/compress/<enc>/round-*.json`, key `spec_sha256`); (c) every result-cache key and blob (`compress/evaluate.py`, lines 387 to 425, `cache_path(evaluator_sha, program_sha, spec_sha, ...)`) and `Result.spec_sha256`. Briefs record only the parent program's sha256 (first 12 hex), no spec hash. `replay.py` and the stop rule do not compare it with anything. The only tests that touch it compare it with `default_spec(...).sha256()`.
- **Measured.** `default_spec(enc, kind).sha256()` computed with the HEAD source and with the working tree: identical for all six pairs (twelve `ee3ce506...`, spinnet `f85f9693...`, rishon `bb0b575b...`, fuzzy_ub `5d7f1f94...`, fuzzy_link `fc43837d...`, lsh `a16c8a0a...`). The recorded values equal these: 22 / 23 / 18 / 41 / 4 archive entries (twelve / spinnet / rishon / fuzzy_ub / fuzzy_link) all carry the current hash; round files 6 / 6 / 5 / 14 / 3 likewise.
- **Result.** The one-line N7 text change makes **no** recorded `spec_sha256` stale, does not touch the result cache keys, does not break a replay, and the rishon round-5 brief records no spec hash. Consistent with `prompts/204` section M6 ("`spec_sha256` not invalidated").
- **What the text change does affect.** The committed `compress/specs/rishon-step.md` must equal `render_spec` (locked test `m6/test_rishon_m6_spec.py`, line 162): that test passes with the new `.md`, and would fail if the `.md` were reverted while the source wording stays. The spinnet `.md` is checked only by `render_spec()` round trips in m4 (passed). The spinnet round-5 briefs (`compress/briefs/spinnet/round-005-F{1,2,3}.md`) still carry the old wording; round 5 of spinnet did run (`results/compress/spinnet/round-005.json` exists), so those briefs are a record of what the proposers saw and rightly were not re-rendered. The rishon round-5 briefs have no round file (round not run), so re-rendering them is consistent.
- **Recommendation: keep the N7 spec text** (both specs, the source constants, and the three re-rendered rishon briefs). Reverting would require reverting the source wording as well (otherwise the locked rishon spec test fails) and would buy nothing.

## Observations (no failure)

- O1: the builder's claim "no fixed `.tmp` name left anywhere in src" is true for the robust caches (N5) but not for all of `src`. Three places still write to a fixed `.tmp` suffix: `compress/archive.py:185` (`Archive._write`, name derived from the entry or index file), `compress/synth.py:55` (synthesis word cache, name derived from angle and $\varepsilon$) and `compress/evaluate.py:371` (result cache, name derived from program, spec and versions). All three are in `EVALUATOR_FILES`, so editing them would change every hash; the temp name is unique per target file, so two writers collide only when they write the same entry or the same cache key at once (identical content in the last two cases). Out of scope for N5; a future hash-changing step could move them to `_atomic_write_text`.
- O2: `_atomic_write_text` reads the umask by calling `os.umask(0)` and restoring it. Between the two calls, another thread of the same process that creates a file would get mode 0666 and one that creates a directory 0777. No thread in this code base does this (xdist workers are processes); a more careful version would compute the mode once at import or read `/proc`. Not a defect today.
- O3: the m2c tests (`M2C_G3`, `M2C_G4`) call `headline(compute=True)` on the real tree; with the new code they rewrote `results/compress/{twelve,fuzzy_ub,fuzzy_link}/robust.json`, adding exactly one line, `"robust_constants_sha256": "d5ac3d7f..."` (3 insertions, 0 deletions in total; entries unchanged). I restored these three files, so the committed caches still have no key (legacy, accepted). The coordinator may want to commit them with the key so that the stale-constant check is live; that changes no number.
- O4: `M11_T2` shows the stale pre-C1 text from the committed `results/crosscheck/gate-table.json` (as in report 428, check 5d); not a regression.
- O5: also rewritten by the tests and restored with `git checkout --`, one by one: `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json`, `spinnet-UB-o1-33d95284ebb7.json`, `spinnet-UB-o1-458a39365261.json`, `spinnet-UE-o1-df0c79b22d3f.json` (provenance only), plus the three `robust.json` files of O3. A transient untracked `lean/Lemma_*.lean` appeared during the acceptance run and had disappeared when it finished. The builder's and coordinator's working-tree changes were not touched (`git diff --stat`: 13 files, +65 / -30, same as at the start).

## Commands

```
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify query/affected ...
taskset -c 0-5 tools/pytest-safe -n 4 tests/unit
taskset -c 0-8 tools/pytest-safe -n 4 -m "not slow or slow" tests/acceptance/m2c
taskset -c 0-8 tools/pytest-safe -n 4 -m "not slow" tests/acceptance -rf
python tools/check_lock.py && ~/.claude/bin/acceptance-check
# scratch experiments (copies of compress/ and results/compress/ under the scratchpad): replay (fuzzy_link UE) untouched / tampered,
# ks.step_circuit + fuzzy headline_step untampered / tampered, robust cache with a changed LINEAR_TOL, Clifford table with qiskit,
# hash lists, default_spec(...).sha256() at HEAD (git archive) and in the working tree
```

## Counts

passed: 1155 unit + 28 m2c + 329 acceptance not slow = 1512; failed: 13 (all PENDING, expected, none new); new failures against report 430: none.
