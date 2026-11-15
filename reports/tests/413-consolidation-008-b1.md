# Report 413: tester, consolidation 008 step B1 + LSH step 8.R (registry, `twelve` + `lsh` entries)

- Date: 2026-11-14. Commit: `bb857c0` plus the builder's uncommitted changes (new `src/su2plaq/encodings/registry.py`, `tests/unit/test_registry_unit.py`; modified `compress/{archive,baselines,brief,evaluate,provenance,report,round,spec}.py`, `encodings/base.py`).
- Plan in force: `prompts/008` §3.1, §3.2, §4, §8, §10 row B1; `prompts/401` §1.4 and row 8.R. Acceptance lock: acceptance-v20 (`acceptance-check` PASS). Mode: step. Machine: omnicommander, cores 14-19, `tools/pytest-safe`.
- Raw numbers: `results/tester/008-b1-consolidation.json`.
- Related: reports/tests/412 (rishon audit-304 fixes), reports/tests/409 (LSH Phase 0).

## Verdict: PASS

Every check below passes; the only red tests are the `prompts/008` §8 expected-red ids and tests that were already PENDING at `bb857c0` (same message at HEAD and now). No new failure.

## Commands (all inside `source ~/miniforge3/etc/profile.d/conda.sh && conda activate coding`, `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src`, `taskset -c 14-19`)
1. `tools/pytest-safe -n 6 -m "not slow" -rfEs tests/acceptance/{m0,m1,m2,m2c,m3,m3x,m4,m5,m5x,m6,m8,m9,m10}` : 260 passed, 30 failed, 1325 s.
2. `tools/pytest-safe -n 6 tests/unit` (separately): 998 passed, 453 s (HEAD collects 968; +30 = the new registry unit tests).
3. HEAD reference tree: `git archive bb857c0 | tar -x -C ../su2qc-head-bb857c0` (no git metadata touched, no `git worktree`/`stash`); moved afterwards to `should-be-deleted/su2qc-head-bb857c0-tester-b1`.
   `python -m pytest --collect-only -q tests/unit tests/acceptance` in that tree and in the working tree.
4. Own scripts (scratchpad `.../scratchpad/b1t/`): `fulleval.py`, `render.py`, hash recompute inline.
5. `python tools/check_lock.py` (LOCK OK); `~/.claude/bin/acceptance-check` (PASS: tests/acceptance matches acceptance-v20); `pytest --collect-only -q tests/acceptance` (374 collected, clean).
6. The four slow expected-red ids run once to confirm the red reason.

## (1) Regression set

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| acceptance not-slow m0 m1 m2 m3 m3x m4 m5 m5x m6 m9 m10 (+ m2c, m8) | green except §8 list and pre-existing PENDING | 260 passed; 30 failed, all of them listed below | none | PASS |
| `tests/unit` | all green | 998 / 998 | none | PASS |
| basename clash `tests/acceptance/m9/test_fuzzy_circuits.py` vs `tests/unit/test_fuzzy_circuits.py` when both dirs are collected in one run | exists at HEAD too | HEAD (`bb857c0` archive copy): `import file mismatch ... 1330 collected, 1 error`; working tree: `1360 collected, 1 error`. Each dir alone collects clean (HEAD 374 + 968; now 374 + 998) | | PASS (pre-existing, not caused by B1) |
| `pytest --collect-only -q tests/acceptance` | clean | 374 collected | | PASS |
| `check_lock.py`, `acceptance-check` | OK | LOCK OK; PASS (v20) | | PASS |

The 30 failing ids (all `Failed: PENDING: ...`, i.e. `NotImplementedError` of a later step, or the unknown-encoding error of an encoding that is not registered before B3-B5):

- m2c G1 x5 (`twelve-step`, `spinnet-step`, `rishon-step`, `fuzzy_ub-UB`, `fuzzy_link-UE`): `cannot import su2plaq.compress.replay` (B7). §8 expected red.
- m2c Y1: replay module (B7). m2c E1-E4, E6: `Verdict` has no `span_leak`/`total_error`, no `prune_fraction` keyword, `inner_target` (B2). m2c E5, P1, P2: `unknown encoding 'fuzzy_link'/'spinnet'` (B3/B4). m2c R1, R2, R3: registry lacks spinnet / rishon / fuzzy entries (B3-B5), facades still patch (B5). All PENDING before B1 as well (HEAD: same 17 of the 18 m2c ids; the 18th, G2, turned green).
- m6 G5 (`replay-204.json missing`, C2), G6 (`three-layer.json missing`, C5): §8 expected red. m6 L2, L3 (`Laurent3.lean missing`, step 6.L2), L9 (`rishon.lean_cert has no attribute recognise_angle_single`): pre-existing PENDING, identical message in the HEAD tree.
- m8 E2, S0, S2, S3, S4, S5, H1, L2: `NotImplementedError su2plaq.lsh.loop.<hook>: prompts/401 step 8.2/8.3` or `No module named su2plaq.compress.robust` (B6). Pending on later LSH steps; in the HEAD tree the same 8 are red (plus E1, see (3)).
- Slow expected-red (deselected by `-m "not slow"`, run explicitly): `m2::test_archive_best_valid_and_not_worse_than_seed`, `m4::test_M4_G1_archive_best_reverified_from_source`, `m10::test_M10_G1_archive_best_valid_and_not_worse_than_seed[fuzzy_ub-UB, fuzzy_link-UE]`: 4 failed, all with exactly `assert '0bd7e7d9...' == '1b38431d...'` (archive stamp vs new `code_hash()`), nothing else. Expected until the Phase C refresh. (m6 G1/S3 are slow and were not run; they are on the §8 list.)

## (2) `twelve` default behaviour unchanged

Full evaluation (`evaluate_program(..., "full", cache=False)`, default spec `twelve/step`) of `compress/programs/twelve/seed/000-general.py`, new tree vs HEAD tree vs the committed archive entry `r00-seed-000`:

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| key (CX, T(1e-6), depth_CT, qubits) | (294, 952, 1421, 50) | (294, 952, 1421, 50), valid, `ok` | exact | PASS |
| `op_norm_error` | 2.68813143571731e-13 | 2.68813143571731e-13 (bit-identical) | bitwise | PASS |
| all verdict/metric/Lean/synthesis fields, flattened (about 200 leaf values), new vs HEAD | equal except volatile timings | 0 differences in the `ProgramResult`; the `Entry` differs only in the two stamp fields below | bitwise | PASS |
| new `Entry` vs archive `r00-seed-000` | equal except provenance | differs only in `evaluator_sha256` (810e86f2 old stamp vs 1b38431d), new field `encoding_sha256`, and package versions (numpy 2.5.4 vs 2.5.2, scipy 1.18.1 vs 1.18.0, python 3.12.16 vs 3.12.14) | | PASS |
| `spec.sha256()` | ee3ce506... (archive) | ee3ce506db77...caaa5d, equal HEAD and archive | exact | PASS |
| rendered twelve spec vs committed `compress/specs/twelve-step.md` | byte-identical | identical (8434 chars), identical to the HEAD render | byte | PASS |
| twelve ideation brief and round briefs F1-F4 (round 6, on a temp root copy of `compress/` + `results/compress`), new vs HEAD | identical | all 5 byte-identical (742 / 16285 / 17447 / 17424 / 17791 chars) | byte | PASS |
| `report_table("twelve","step")` and its `summary.json`, new vs HEAD | identical | byte-identical | byte | PASS |
| report tables and summaries of rishon, fuzzy_ub, fuzzy_link, new vs HEAD | identical | byte-identical | byte | PASS |
| report table and summary of spinnet | identical except the beta text | exactly one line differs: `valid at its own angle (beta = 1, kind UB)` -> `(beta = 0.05, kind UB)` for `paulo15` (plan §3.2, see (5)) | | PASS |

Why the `Entry` differs: B1 replaces the stamp, as the plan says (`evaluator_sha256 = stamp_hash("twelve") = code_hash()`, new `encoding_sha256 = code_hash_for("twelve")`, equal to each other). Metrics are untouched. A legacy `Entry` with `encoding_sha256 = None` serialises without that key (older entry files stay byte-identical when rewritten).

## (3) Registry content and m2c / m8 state changes

| check | expected | got | result |
|---|---|---|---|
| importing `su2plaq.encodings.registry` (plus `names()`, `info`, `lookup`) in a fresh process | imports no other project module | `sys.modules` project entries: `su2plaq`, `su2plaq.encodings`, `su2plaq.encodings.registry` only (checked by me and by the builder's unit test); resolving the lsh entry's strings imports nothing; `get_encoding("lsh")` builds the encoding without importing `su2plaq.lsh.loop` | PASS |
| table content | `twelve`, `lsh`, in that order | `names() = ('twelve', 'lsh')` | PASS |
| lsh entry vs `prompts/401` §1.4 | field by field | identical: factory `su2plaq.encodings.lsh:LSH`, kinds, `loop_kind="step"`, six `evaluator_files` in the stated order, `stamp="encoding"`, `gauss_in_loop=True`, the seven `su2plaq.lsh.loop:` hooks, `structure_json="compress/specs/lsh-structure.json"`, `tools=None`, `headline=None`; every other field default | PASS |
| `NOMINAL_ANGLES` | `lsh` = (0.37, 0.61) | `{'twelve': (0.37, 0.61), 'lsh': (0.37, 0.61)}` | PASS |
| `registry.py` in `EVALUATOR_FILES` | yes | present; 21 of 21 shared files exist | PASS |
| m8 `test_M8_E1_registry_entry_lsh` | green | PASS | PASS |
| m2c `test_M2C_G2_structure_json_is_current` | green | PASS | PASS |

State changes of the m2c and m8 not-slow ids between HEAD (`bb857c0` archive copy) and now (40 ids each): exactly two turned green and nothing turned red.

| id | HEAD | now |
|---|---|---|
| `m2c::test_M2C_G2_structure_json_is_current` | FAIL (PENDING: cannot import `su2plaq.encodings.registry`) | PASS |
| `m8::test_M8_E1_registry_entry_lsh` | FAIL (PENDING: same) | PASS |

(Two further m8 ids, `M8_A1_lean_tables_tied_to_rules` and `M8_A2_committed_certificate_clean_provenance`, are red in the archive copy of HEAD only because `git archive` has neither `.git` history nor `lean/.lake`; in the real working tree they are green both before and after, so they are not state changes.) Other 11 PASS (m8 A1, A2, A4, H3, S1 x8, U1) and 25 FAIL ids are unchanged.

## (4) Hashes (recomputed independently, not through `provenance.py`)

Formula per `prompts/008` §4: $\mathrm{sha256}\big(\Vert_{f\in F\Vert F_e}\ \mathrm{name}(f)\,\texttt{\textbackslash0}\,\mathrm{bytes}(f)\,\texttt{\textbackslash0}\big)$, name = file base name, files in list order, shared list first.

| quantity | expected | got | result |
|---|---|---|---|
| `provenance.code_hash()` | `1b38431d...` | `1b38431d7995acef61c55d32e480545212f97a109a1d5e511777cbdd3805605c`; my own sha256 loop over the 21 files gives the same | PASS |
| `code_hash_for("lsh")` | `bcdd4e4e...` | `bcdd4e4ea37d77608d138659a3809fa4bceefb9ec0cbecfa058a2258e3feaebb`; own loop (21 shared + the six lsh files) gives the same | PASS |
| `spinnet.loop.code_hash()` | `f61b82b2...` | `f61b82b2d2a2937b6fd78b5888b3f53a47b180cc5fc0bd17fa1799b355ce7172` | PASS |
| `rishon.compress.code_hash()` | `2b6fbaa2...` | `2b6fbaa2b1871934dbbb813c9e727720f054433cd9f3dfa2c2056a75d232bec7` | PASS |
| HEAD tree (control) | B0 values in STATUS | `0bd7e7d9...0582`, `7f5bb7f8...0ed5`, `1ddae8a6...0234` (match the STATUS B0 line exactly) | PASS |
| `code_hash_for("twelve")`, unregistered names, `None` | equal `code_hash()` | equal | PASS |
| `stamp_hash("twelve")` = `code_hash()`; `stamp_hash("lsh")` = `code_hash_for("lsh")` | yes | yes | PASS |

The three changed track hashes (spinnet, rishon, shared) change because the shared list gained `encodings/registry.py` and `encodings/base.py` was edited; this is the expected effect and equals the "one shared hashed edit" of 401 §1.4. `code_hash_for("spinnet"/"rishon"/"fuzzy_*")` still equals the shared hash because those names are not registered before B3-B5.

## (5) The builder's four ambiguity calls

1. `twelve` registered with `lean_certify="su2plaq.lean.certify:certify_circuit"` (explicit string). Plan §3.1 says `lean_certify=None` gives status `n_a`, so `None` for `twelve` would silently switch Lean off for the twelve archive; §3.2 says `certify_circuit` stays "unchanged for twelve". Explicit string reproduces the old call (`timeout=1200.0`, `extra_provenance`) and the same `asdict(LeanCert)` result. Does not contradict the plan. ACCEPT.
2. `tools` read as two command prefixes (candidate, oracle), text templates keep `<program.py> --encoding X --kind Y --trial`. Plan §3.1 comment: "(candidate command, oracle command) for spec and brief text". Only `None` is exercised by B1 (twelve and lsh both `None`, output byte-identical to HEAD, see (2)). Note for B3: the retired spinnet shim emitted `python -m su2plaq.spinnet.loop candidate <program.py> --trial` (no `--encoding/--kind`); if spinnet gets `tools` set, the template would append `--encoding spinnet --kind step`, which `spinnet.loop candidate` may not accept. Plan §3.3 deletes the string rewrites and 401 §1.7 uses the stock commands, so the likely B3 choice is `tools=None`. Not a B1 contradiction. ACCEPT with that note.
3. `brief_note` text appended at the end of the round brief (after "Output") and of the ideation brief, as lines. 401 §1.7: "appended by the shared brief code to the ideation brief and to every round brief". Matches. Nothing is appended for `twelve` (verified byte-identical). ACCEPT.
4. `report._row_external` prints the row's own `beta`. Plan §3.2 says exactly this ("prints the row's own `beta` (spinnet M4 item 5)"). 0.05 is the correct spinnet value: docs/METHODS-spinnet.md (Paulo 15-qubit file paragraph, line 47) describes Paulo's 15-qubit file as $e^{+i\alpha_P\mathrm{Re\,Tr}\,U_P}$ at $\alpha_P=0.1$, i.e. $\beta=0.05$ ($\alpha_P=2\beta$), the comparison table row is "Paulo 15-qubit file ($\alpha_P=0.1$) | 0.05", and §10.3 says "($\beta=0.05$, $U_B$ only)". The stored round record `results/compress/spinnet/round-000.json` has `beta: 0.05` for `paulo15`; research 102 and tests 111 N2 flagged the hard-coded "beta = 1" as wrong. Fallback `"1"` when `beta` is absent keeps twelve identical: the stored twelve `paulo34` record has no `beta` and a freshly built one carries `1.0`, which `:g` prints as `1`. Verified: all other reports and summaries byte-identical, spinnet differs in that one line only. ACCEPT; no contradiction with the plan.

No call contradicts the plan.

## Observations (not failures)

- The three track hashes are no longer the B0 values recorded in STATUS (expected, see (4)); the coordinator should record the new ones (`code_hash` 1b38431d..., lsh bcdd4e4e..., spinnet.loop f61b82b2..., rishon 2b6fbaa2...) as the 8.R/B1 line.
- `evaluate_circuit` places the new `engine_qubit_limit` (62) check after the `max_qubits` check; twelve's cap is 60, so it cannot trigger for twelve; rishon's cap (80) can reach it, which is the point of the plan.
- In `compress/evaluate.py::_worker` the audit guard is now installed after the spec JSON is parsed (needed so `worker_warmup` runs before it). No behavioural change visible in m0-m10; the sandbox tests of m2/m4/m5/m9/m10 pass.
- `m6` G5/G6/L2/L3/L9 and `m8` E2, S0, S2-S5, H1, L2 stay PENDING, unchanged by B1.

## Failures
None attributable to B1.

## Byproducts and files touched
- Tracked byproducts produced by the test runs and restored with `git checkout --`: `results/compress/fuzzy_link/summary.json`, `results/compress/rishon/robust.json`, `results/spinnet/certs/spinnet-UB-o1-33d95284ebb7.json`, `results/spinnet/certs/spinnet-UB-o1-458a39365261.json`, `results/spinnet/certs/spinnet-UE-o1-df0c79b22d3f.json`, `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json`. `git status` shows no tracked `results/` change afterwards. (`results/compress/{twelve,spinnet,rishon,fuzzy_ub}/summary.json` were not modified; my own report renders wrote to a temp root, never the repo.)
- New by me: `reports/tests/413-consolidation-008-b1.md`, `results/tester/008-b1-consolidation.json`. No source, test or acceptance file edited.
- HEAD reference copy moved to `should-be-deleted/su2qc-head-bb857c0-tester-b1`.
