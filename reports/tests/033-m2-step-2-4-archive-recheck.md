# Tester report 033 — M2 step 2.4 recheck (builder attempt 1, fixes for report 030)

- Date: 2026-11-05
- Commit: 7a2be3d at the start of the independent scripts a1, a2, a5; 51aca3d (moved under me, Lean/other commits) for a3, a4 and the pytest runs. Working tree dirty (step 2.4 fix, 2.5/2.6 files, Lean).
- Plan in force: `prompts/002-…` (+ addenda 003–006), acceptance-v7
- Mode: step (recheck)
- Related: reports/tests/030 (FAIL), 026–029
- Raw numbers: `results/tester_m2_step2_4_recheck_{meta,archive_props,cache,forged,forged_cache_gate,provenance}.json`; scripts `tests/independent/archive_2_4/a1…a5` (adapted to the new API; a2, a4, a5 take the tester scratchpad dir as argv[1]). Seed 20261105.

## VERDICT: PASS WITH NOTES
Both FAILs of report 030 are fixed (cache tampering; insert accepting trial/contradictory entries) and the genuine `compress.metrics.key` failure is gone. A cache entry that is forged with a recomputed checksum is trusted by design; I confirmed the archive then accepts it (it is only a consistency check) and the gate's fresh re-evaluation from source catches it (numbers below). Notes: a trailing-newline id passes the id regex; `{"ok": true}` without a `certified` field counts as certified; `Archive(n_alt=0)` default skips the alt-count rule (real path always passes it, see 2.4).

Counts: m2 acceptance 31 passed / 1 not passed (`test_archive_best_valid_and_not_worse_than_seed`, empty real archive = loop step 2.7, PENDING); 4/4 step-2.4 targets (`roundtrip_and_elites`, `rejects_invalid`, `keyed_by_code_hash`, `entry_has_provenance_fields`); m0+m1 non-slow 54/54; unit (non-Lean) 318 passed + 1 flaky failure (below); collect 102; LOCK OK; acceptance-check PASS (acceptance-v7). Compared with report 030: m2 27 -> 31 passed (steps 2.5/2.6 files landed), 0 new failures in the locked suite.

## Commands
```
pytest -n auto -q tests/acceptance/m2/test_compress_machinery.py ; ... -k "roundtrip_and_elites or rejects_invalid or keyed_by_code_hash or entry_has_provenance"
pytest -n 6 -q -m "not slow" tests/acceptance/m0 tests/acceptance/m1                    # 54 passed, 153 s
pytest -n 6 -q tests/unit --ignore=tests/unit/test_lean_cert_unit.py --ignore=tests/unit/test_lean_project_unit.py   # 318 passed, 1 failed, 200 s
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
python tests/independent/archive_2_4/a1_archive_props.py ; a2_cache.py <scratch> ; a3_forged.py ; a4_provenance.py <scratch> ; a5_forged_cache_to_gate.py <scratch>
```

## 1. Regression and classification

| check | expected | got | result |
|---|---|---|---|
| 4 step-2.4 target ids | PASS | PASS (4 passed, 4.7 s) | PASS |
| other m2 ids | pass or PENDING | 31 passed; the one non-pass is `test_archive_best_valid_and_not_worse_than_seed` (`best is None`: real archive empty until step 2.7) -> PENDING | PASS |
| `compress.metrics.key/cell` (report 030, item 1b) | present | `test_metrics_match_qiskit_count_ops`, `test_polish_valid_and_not_worse` now pass | fixed |
| m0 + m1 non-slow | 54 | 54 passed | PASS |
| unit (non-Lean) | all pass | 318 passed; `test_brief_points_at_files_and_follows_the_template` failed once during the full run (`test_compress_brief_report_unit.py:77`); in isolation 6/6 pass (34 s). `compress/brief.py` is being edited concurrently by the 2.6 builder | NOTE (guess: file in flux, not 2.4) |
| collect / check_lock / acceptance-check | clean / OK / PASS | 102 / LOCK OK / acceptance-v7 | PASS |

## 2. Archive invariants and attacks (`a1`, adapted: entries now carry full metrics, certified verdicts and 2 alt verdicts, `n_alt=2`)

Random sequences: 300 seeded insert sequences (3456 accepted, 2705 refused inserts) vs a brute-force model.

| check | expected | got | result |
|---|---|---|---|
| elites = min key per cell (ties: smaller id); best = global min; `family_best` | 0 mismatches | 0 / 300; 0 / 300; 0 / 1200 | PASS |
| refused inserts (invalid, unverified, inf key, NaN key, duplicate id) leave the archive unchanged | 0 changes | 0 / 2705 | PASS |
| save -> load round trip; entry files byte-stable (load -> save) | identical | 0 / 300 mismatches, 0 / 300 byte differences; no `*.tmp` left | PASS |
| atomic write, 16 simulated kills (partial `.tmp` write at the k-th write / abort before the k-th rename) | no partial final file, load works | 16/16 killed, 0 bad; in 2/16 the new entry file is complete but `index.json` still lists the old set (load reads `entries/`, nothing lost) | PASS |

Insert rules (each case tried on a fresh archive with `n_alt=2` unless noted; result = inserted?; the control entry inserts):

| entry | expected | got |
|---|---|---|
| trial mode; `skeleton_equal=False`; nominal verdict `{ok: False}`, `{ok: True, certified: False}`, `{}` | refused | refused, each with its own reason in `.rejected` |
| alt verdict not ok / not certified / `{}`; alt count 0, 1, 3 with `n_alt=2` | refused | refused (6/6) |
| cell inconsistent with key; key `(0,0,0,0)` with other metrics | refused | refused ("key / cell do not match the metrics") |
| metrics missing a field / empty / string values / negative / bool | refused | refused (5/5) |
| `numpy.int64/float64/int32` in key and metrics | accepted | accepted (2/2) |
| ids `../../../escape`, `…/../../x`, space, empty, 200 chars, absolute, uppercase `R01`, `r1-`, `..`, NUL, non-ASCII, non-str | refused | refused (12/12) |
| id `"r01-F1-001\n"` (trailing newline) | refused | **accepted** (regex `$` matches before a final newline; would save as `r01-F1-001\n.json` inside `entries/`) — NOTE; id `r01-F1-001.json` also accepted (file `….json.json`, harmless) |
| nominal verdict `{"ok": True}` with no `certified` field | refused or documented | accepted (rule is `certified is False`) — NOTE; real verdicts always carry `certified` |
| 0 alt verdicts with default `n_alt=0` | accepted by design | accepted (as the locked tests require) |
| `save()` of an entry put into `_entries` directly with id `../../../escape`, or with a lowered key, or mutated in place after insert (`verdict_nominal={"ok": False}`) | refuse | `ValueError` (3/3); nothing written outside `entries/` | PASS |

Load-time attacks (hand-edited entry file in a saved archive, `n_alt=2`):

| edit | got |
|---|---|
| none (control) | loaded, best = it |
| `valid=False`; key lowered only; file name != id; id with `../`; mode `trial`; alt verdicts removed; nominal verdict flipped; garbage file; missing field; metrics changed without key | all refused, logged in `Archive.rejected` with the reason (10/10); best = None |
| alt verdicts removed, `n_alt=0` (default) | **loaded** (alt count not checked when n_alt=0) |
| a new file with metrics, key, cell all zero and a consistent id | loaded, becomes `best()` — not detectable without authentication; the gate (section 4) re-evaluates |

Does real code always pass `n_alt`? grep of `src/`, `scripts/`, `tools/` for `Archive`: the only user is `src/su2plaq/compress/round.py:90` `A.Archive.load(encoding, root=root, n_alt=len(spec.alt_angles))`, which is the object that inserts and saves. Locked tests use the default `n_alt=0` on their own fake entries; fine. Residual: later consumers (report, gate test) that call `Archive.load(ENC, root)` without `n_alt` skip the alt-count rule on load, but the entry files they read were validated with `n_alt=2` by `round.py` before saving.

## 3. Result cache (`a2`; real evaluations of a 4-rotation $U_E$ program, first full call 15.2 s, hit 0.003 s)

Keying, unchanged from 030 (all PASS): miss then hit (1 / 0 evaluations); same bytes at another path hit; one program byte -> miss; 15/15 `TaskSpec` fields change the spec sha and `eps`, `tol_err` miss end to end; editing one byte of each of the 20 `EVALUATOR_FILES` changes the code hash (20/20) and `evaluate_program` misses, restoring hits the old entry; trial results never cached (0 new files, all cached payloads `mode == "full"`); 12 malformed-file variants (truncated, empty, list, null, no payload, payload string/list, bad verdict, bad phase, `verdicts_alt=None`, meta list, binary; resealed where relevant) all re-evaluate, none raise. Cached `t_estimate` keys are `str` after the JSON round trip (NOTE, unchanged). `compress/provenance.py` itself is not in the hash (NOTE, unchanged).

New file format `{meta, payload, checksum}`. Tamper cases on a cached result of the wrong program (honest result: `valid=False, reason=error`, op-norm error 1.28):

| tamper | expected | got |
|---|---|---|
| 1 payload `valid=True` (stale checksum) | re-evaluate | re-evaluated, `valid=False`, file overwritten with the fresh result |
| 2 payload metrics zeroed (stale checksum) | re-evaluate | re-evaluated, file overwritten |
| 3 `valid=True` with checksum recomputed but verdict still not ok | re-evaluate (consistency check) | re-evaluated, file overwritten |
| 4 garbage checksum; 5 checksum removed | re-evaluate | re-evaluated (2/2) |
| 6 meta program sha edited (stale checksum) | re-evaluate | re-evaluated |
| 7 payload mode `trial`, resealed | re-evaluate | re-evaluated |
| 8 meta evaluator sha changed, resealed | re-evaluate | re-evaluated |
| program A's file copied verbatim into B's slot | re-evaluate | re-evaluated, `valid=False`, `program_sha256` = B's |
| A's file with meta retargeted to B and resealed (payload still A) | re-evaluate | re-evaluated |
| 9 `valid=True`, nominal verdict ok+certified, alt verdicts removed, resealed | by design trusted (consistent forgery) | trusted (returns valid, 0 alt verdicts) |
| 10 fully consistent forgery: `valid=True`, nominal and 2 alt verdicts ok+certified, skeleton equal, metrics $(0,1,1,1)$, resealed | by design trusted | trusted; likewise A's verdict for B with meta and payload sha retargeted and resealed |

Result: every tamper that does not recompute the checksum **and** keep the payload self-consistent is detected (8/8 detected, 7/7 corrupt-file variants re-evaluated). Anyone who can write the cache and recompute the sha256 can still plant a result, as documented in `_cache_blob`.

## 4. Consistent forgery -> archive -> gate (`a5`)
Scenario: cached result of the wrong program forged as in tamper 10, with 2 copies of the nominal verdict as alt verdicts so it satisfies `n_alt=2`.

| step | got |
|---|---|
| `evaluate_program(cache=True)` | returns `valid=True`, metrics $(\mathrm{CX},T_\varepsilon,\mathrm{depth}_{\rm CT},q)=(0,1,1,1)$, 2 alt verdicts |
| forged case 9 (no alt verdicts) -> `Archive(n_alt=2).insert` | refused ("expected 2 alternate-angle verdicts, got 0") — the archive's own rule is a second line |
| forged case 10 -> `entry_from_result` -> `insert` | **accepted** (`entry_problem` is None); an unauthenticated consistent entry cannot be told apart |
| gate: reload archive, `best()`, re-evaluate its program from source with `cache=False` | `valid=False, reason=error`; fresh key $(0, 239.18, 1, 28)$ vs recorded $(0,1,1,1)$ -> the gate predicate (valid and key equal) fails; caught |

So the claim holds: forging with a recomputed checksum succeeds by design; the archive rules reject the inconsistent variants; the gate (re-evaluation from source, uncached) catches the consistent one.

## 5. N6 and forged worker outputs (`a3`, 15 programs x {trial, full} = 30 evaluations, unchanged)
Forged `meta.json` + `os._exit(0)`, garbage/list meta, wrong `discoveries` type, 5 MB error string, garbage/empty `out.qpy`, no files (exit 0 / 3), `os.remove(meta)`, wrong circuit count, forged native `MCXGate` circuits (full: `disallowed_gate`) and empty circuits (full: `error`): 0 exceptions raised, every case `build_error`/`contract`/`disallowed_gate`/`error`; the only valid case is the legitimate circuit whose forged `{"error": ...}` meta write is overwritten by the worker's final write. PASS.

## 6. Provenance (`a4`, real full result, `round=2, family=F9, parent=r01-F9-001`)
id `r02-F9-001`; program, evaluator and spec sha256 equal the recomputed ones; `git_commit` 51aca3d = HEAD at the time, `git_dirty` True; versions qiskit 2.5.2, qiskit_aer 0.17.2, numpy 2.5.2, scipy 1.18.0, pygridsynth 1.2.0, python 3.12.14 (= installed); seeds trial 0, transpiler 20261104 (= `logical.SEED`), Clifford+T pass manager 12345, gridsynth 0; machine `pichkaCommander x86_64 cpus=12`; wall 13.7 s; key $(0,256,167,28)$, cell $(0,64)$; cached-result entry keeps seeds, spec and evaluator hashes with equal key; trial-mode entry -> refused ("mode 'trial' is not 'full'", was accepted in 030); invalid -> key $\infty^4$, refused; the full entry inserts into `Archive(n_alt=2)`. PASS.

## Notes for the coordinator
- Use `re.fullmatch` (or `\Z`) in the id regex; require `certified is True` when the field is present-or-not decision is made by the coordinator (real verdicts always have it). Both minor.
- `n_alt=0` default: acceptable because the only real user (`round.py`) passes it; consider making `n_alt` required once the locked tests stop depending on it.
- Flaky unit `test_brief_points_at_files_and_follows_the_template`: passes alone; re-run after the 2.6 builder finishes.
