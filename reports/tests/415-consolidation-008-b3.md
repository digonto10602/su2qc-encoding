# Report 415: tester, consolidation 008 step B3 (spinnet registry entry and `spinnet/loop.py` facade)

- Date: 2026-11-15. Commit: `7e9bb5d` plus the builder's uncommitted B3 changes (`encodings/registry.py`, `encodings/base.py`, `spinnet/loop.py`, new `compress/specs/spinnet-structure.json`, `tests/unit/test_spinnet_loop_unit.py`, `tests/unit/test_registry_unit.py`) and the planner's uncommitted erratum E1 (`tests/acceptance/m4/test_spinnet_compress.py`, `tests/acceptance/LOCK.json`).
- Plan in force: `prompts/008` §3.3, §8, §10 row B3, §13. Lock in tree: acceptance-v20 plus the unlocked E1. Mode: step. Machine: omnicommander, `tools/pytest-safe`, `taskset` on cores 6-17.
- Related: reports/tests/414 (B2, same red set baseline). Raw numbers: `results/tester/008-b3-step.json`, `results/tester/008-b3-hashes.json`. My scripts: `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/57b28677-d814-4f58-bc95-52ae378eb01f/scratchpad/b3t/` (`t2.py`, `t4.py`, `t4b.py`, `t7.py`, `t_r3.py`).
- Added by me: `tests/unit/test_tester_b3_certify.py` (one test, reproduces failure F1 below; red until F1 is fixed).

## Verdict: FAIL

One real regression caused by B3 (F1): every Lean-certified spinnet circuit that goes through the shared `round._certify` raises `KeyError: 'gates_sha256'`. A locked acceptance test (`m4::test_M4_L2_seed_round_records_certificates`) catches it and is red; it is not on the §8 expected-red list. Everything else checked is correct, including the facade (nothing is replaced), the spec, the structure file, the hashes, and bit-identical spinnet evaluation.

## Commands
1. `tools/pytest-safe -n 8 -m "not slow" -rfEs -q tests/acceptance/{m0,m1,m2,m2c,m3,m3x,m4,m5,m5x,m6,m8,m9,m10}`: 264 passed, 26 failed, 1052.6 s.
2. `tools/pytest-safe -n 4 -m slow -q tests/acceptance/m4`: 4 passed, 3 failed (57 s). Re-run serially: `tools/pytest-safe -m slow -rfEs -q tests/acceptance/m4 tests/acceptance/m3`: 6 passed, 2 failed (43 s).
3. `tools/pytest-safe -n 8 -q tests/unit`: 1005 passed, 1 failed (my added test), 311 s.
4. `PYTHONPATH=src python -m su2plaq.compress.run_candidate compress/programs/spinnet/seed/000-general.py --encoding spinnet --kind step --trial` and `python -m su2plaq.spinnet.loop candidate ... --encoding spinnet --kind step --trial`.
5. My scripts above, run with `python -I`, in fresh interpreters. A reference tree of `HEAD` was made with `git archive HEAD src compress/programs compress/specs compress/archive/spinnet lean/Su2Plaq/SpinNet docs` into the scratchpad (no git metadata touched).
6. `python tools/check_lock.py`, `~/.claude/bin/acceptance-check`, `pytest --collect-only -q tests/acceptance`.

Note: in a fresh shell `python -m su2plaq...` needs `PYTHONPATH=src` (the package is imported through `pythonpath = src` of `pytest.ini`, not installed). Without it: `No module named 'su2plaq'`. Not a B3 effect; the plan's command line assumes it.

## (1) Done-check of row B3

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| m3 not slow (23 tests), m3x (4), m4 not slow (12) | all pass | none of the 26 red ids is in m3, m3x, m4; 39 of 39 pass (collected counts 23 / 4 / 12) | exact | PASS |
| `M4_S2…`, `M4_S7…` with E1 | pass | pass (not in the red list) | exact | PASS |
| same two with the ORIGINAL lines (script, `L.install()` then the old conditions) | red by design (the mechanism is removed) | old S2 line: `False`; old S7 line `set(INSTALLED) >= {"encoding","build_in_subprocess","certify"}`: `False`; E1 S2 line `True`; E1 S7 line `True`; `INSTALLED == {"encoding": True}` | exact | PASS (E1 is needed and is satisfied; the old lines cannot hold in any facade) |
| `run_candidate ... --encoding spinnet --kind step --trial` (fresh shell, `PYTHONPATH=src`) | exit 0 | exit 0; `valid: ok [trial, 3.3 s]`; CX 54, T_fixed 56, N_rot 8, qubits 23; `op_norm_error 1.180e-14`, `span_leak 0`, `total_error 1.180e-14` | exit code | PASS |
| rendered spec vs committed `compress/specs/spinnet-step.md` | byte-identical | `default_spec("spinnet","step").render()`, `loop.render_spec()`, `loop.spec().render()` all equal the committed bytes (9640 B, sha256 `6181133b…da97`); committed file equals `HEAD` | bytes | PASS |
| `acceptance-check` | PASS | `FAIL: tests/acceptance differs from acceptance-v20 … Changed: LOCK.json, m4/test_spinnet_compress.py` | | expected (unlocked E1; the diff against `HEAD` is exactly the two E1 lines and the new sha `7fa28a77…36ca`, which `check_lock.py` accepts: `LOCK OK`) |

## (2) Nothing is replaced (§13), fresh interpreter (`python -I`, `t2.py`)

| check | expected | got | result |
|---|---|---|---|
| `id()` of `evaluate._build_in_subprocess`, `evaluate._worker`, `round._certify`, `baselines.general_circuit`, `TaskSpec.render`, `evaluator.evaluate` before import of `spinnet.loop`, after `install()`, after a second `install()` | all equal | all six equal in all three snapshots; also equal after importing every `su2plaq.*` module | PASS |
| `INSTALLED` | `{}` before, `{"encoding": True}` after | `{}` at import; `{"encoding": True}` after one and after two calls | PASS |
| `_spinnet_shim` attribute on any function (and on class members) in the 101 `su2plaq.*` modules loaded | none | none | PASS |
| `_worker_copy`, `_certify_dispatch`, `_TOOL_REWRITES`, `_rewrite_text`, `_need`, `_finish_brief`, `_SHIM_MARK` | gone | all `hasattr == False` | PASS |
| text search in `src/su2plaq/{spinnet,compress,encodings}` for `_spinnet_shim`, `setattr(`, `importlib.reload`, `sitecustomize`; assignments `X.attr =` into shared modules in `spinnet/loop.py` | none | none | PASS |
| attribute and environment diff of every shared module (`su2plaq.compress.*`, `evaluate.*`, `lean.*`, `encodings.*`) after the facade is installed, one facade at a time (`t_r3.py`) | spinnet: none | spinnet: no changed attribute, environment unchanged. (fuzzy changes `BL.general_circuit`, `BL.import_seed`, `BR.make_brief`, `BR.make_ideation_brief`, `round._certify`, `evaluator.evaluate` and the environment; rishon only adds the submodule attribute `su2plaq.encodings.rishon`. Both are B4/B5.) | PASS (so the `M2C_R3` red is due to the fuzzy facade only) |

## (3) The builder's deviation (`tools=` set instead of `None`)

I re-registered the entry with `tools=None` in-process (`dataclasses.replace`, `register(..., replace=True)`) and rendered the spec and the briefs both ways.

| item | with registered `tools` | with `tools=None` | verdict |
|---|---|---|---|
| M4_S0 lines 171 and 174 (`"python -m su2plaq.spinnet.loop candidate"`/`oracle` in `L.render_spec()`; `"su2plaq.compress.run_candidate"` not in it) | true / true | true / true | the builder's citation of S0 is wrong: `render_spec` (the registry hook) writes its own "Tools" section, so S0 does not depend on `tools=` |
| M4_S4 lines 365-366 (the round brief contains `python -m su2plaq.spinnet.loop candidate` and not `su2plaq.compress.run_candidate`) | true / true | **false / false** | required: `brief.make_brief` and `make_ideation_brief` read `info.tools` only |
| ideation brief names the spinnet oracle | yes | no | same cause |

Conclusion: the deviation is necessary (through M4_S4, not through M4_S0). The brief line `python -m su2plaq.spinnet.loop candidate compress/programs/spinnet/seed/000-general.py --encoding spinnet --kind step --trial` runs and exits 0 (3.1 s, same output as the `run_candidate` call above); the loop CLI also accepts the call without `--encoding/--kind` (exit 0). The registry's `tools` strings carry no `--encoding/--kind`, and the shared brief appends them, which the loop CLI accepts. PASS.

## (4) Spinnet behaviour unchanged

Seed `compress/programs/spinnet/seed/000-general.py`, `evaluate_program(..., cache=False)`, new tree vs the `HEAD` tree (shim installed) vs the committed archive entry `compress/archive/spinnet/entries/r00-seed-000.json` (`t4.py`):

| quantity | expected | got | tolerance | result |
|---|---|---|---|---|
| key, full mode | `[54, 566, 861, 23]` (archive entry and HEAD tree) | `[54, 566, 861, 23]` | exact | PASS |
| key, trial mode | HEAD tree: `[54, 534.3576456637802, 67, 23]` | identical | exact | PASS |
| `op_norm_error` nominal, full | entry `1.229760974694126e-14` | `1.229760974694126e-14` (bit-identical) | bitwise | PASS |
| `op_norm_error` alt angles | entry `1.143136891868367e-14`, `1.5769971861959752e-14` | bit-identical | bitwise | PASS |
| `op_norm_error` trial | HEAD tree `1.1799226524067892e-14` | bit-identical | bitwise | PASS |
| other verdict fields (`gauss_residual`, `block_error`, `leak_amplitude`, `dropped_total`, `max_leak`, `dirty_ancilla`, `n_inputs`) | equal to HEAD tree | equal (only the B2 fields `span_leak = 0.0`, `total_error` are new) | exact | PASS |
| `spec_sha256`, `program_sha256`, `skeleton_equal` | equal | `f85f9693…` and `b608b9b2…` equal to the entry; `skeleton_equal` True | exact | PASS |
| `lean_certify` hook alone (`loop.lean_certify(circ, spec)`) | status certified, fields of the old dict | `LeanCert(status='certified', reason='', cert_path=…, seconds=2.66, checker_sha256='ec00aa45…', theorem_path=None, axioms=[])`: same field set as the archive `lean` dicts (`axioms, cert_path, checker_sha256, reason, seconds, status, theorem_path`, plus `program_file_sha256` on the later entries); `checker_sha256` equals the archive value `ec00aa45fafa…5de5` | field names | PASS |
| **`round._certify(circ, spec, program_file_sha256)` (the shared dispatcher; this is the path every loop function uses)** | dict with the same fields | **`KeyError: 'gates_sha256'`**, raised at `src/su2plaq/compress/round.py:338` | | **FAIL (F1)** |

### F1: failure detail

`round._certify` (unchanged shared code, `round.py` lines 336-338) does, after the registry hook returns a certificate with a `cert_path`:
`d["gates_sha256"] = json.loads(Path(d["cert_path"]).read_text())["gates_sha256"]`.
The spin-network exporter (`spinnet/lean_export.py`) writes the gate-list hash under `program_sha256` and has no `gates_sha256` key (keys of the real certificate file: `schema, circuit_id, program_sha256, n_qubits, n_data, n_outer, base, gates, states, target, phase, provenance`). `KeyError` is not among the exceptions caught by `_certify` (`NotImplementedError`, `ImportError`, `OSError`, `ValueError`, `RuntimeError`, `SubprocessError`), so it propagates after Lean has already certified the circuit. The old shim built its own dict and never read the file; the twelve-qubit and LSH exporters write `gates_sha256`. Affected callers in the facade: `loop.seed_round(lean=True)` (line 648), `loop.certify_best` (line 897) and the shared `round.run_round(lean=True)` (line 238, 384).

Evidence: (i) my script `t4b.py` and `R._certify(circ, sp, "abc")` raise it on the general seed circuit; (ii) locked `m4::test_M4_L2_seed_round_records_certificates` fails with the same `KeyError` through `loop.py:642 seed_round -> round.py:238 run_round -> round.py:338`; (iii) the added unit test `tests/unit/test_tester_b3_certify.py` fails identically.
Guess at the cause (label: guess): the registry design moved the dict building into the shared `_certify`, which was written for exporters that emit `gates_sha256`; the builder's facade only tested `lean_certify` with a mocked exporter (`test_lean_certify_hook_is_dispatched_by_the_shared_round`). Two possible fixes (not mine to make): make `round._certify` read `gates_sha256` with a fallback to `program_sha256` (as `lean/certify.py:451` already does for old certificates), or have the spin-network exporter write `gates_sha256` too (would change the certificate files and the checker input).

## (5) `compress/specs/spinnet-structure.json`

| check | expected | got | result |
|---|---|---|---|
| counts vs `lean/Su2Plaq/SpinNet/Counts.lean` theorem statements (read by me with grep) | `card_inner_labels 47`, `card_bright_labels 16`, `card_dark_labels 31`, `card_bright_pairs 8`, `card_states_spinnet 433`, `mult_two 16`, `mult_one 96`, `mult_half 16` | all eight equal | PASS |
| `spectrum_multiplicities` vs `Spectrum.lean::eig_mult` (`2λ ∈ [-4,-2,-1,0,1,2,4]`, multiplicities `[16,96,16,177,16,96,16]`) | eigenvalues $\lambda=-2,-1,-\tfrac12,0,\tfrac12,1,2$ with the same multiplicities (sum 433) | `[[-2.0,16],[-1.0,96],[-0.5,16],[0.0,177],[0.5,16],[1.0,96],[2.0,16]]` | PASS |
| `couplings_2k` vs the table `exportedCodes`/`exportedTwoK` in `Recoupling.lean` (the Lean theorem `coupling_from_6j` says the table equals $2K$ from the 6j symbols) | 8 bright pairs: one with $2K=-4$, six with $2$, one with $-1$; 31 dark codes with 0 | `{"-4":1,"2":6,"-1":1,"0":31}` (my own count from the 47-entry table: pairs 1/6/1, dark 31) | PASS |
| `ub_exact_semantics` vs `Semantics.lean::ub_exact_all_codes` (proved by `decide`) | True | True | PASS |
| provenance: sha256 of the four Lean files | `sha256sum` | `3aca1237…0460`, `d5cbf69e…ef62`, `17e7cb3b…7d7d`, `6775778b…1ee1b` equal to the file's `provenance.lean_files` | PASS |
| regenerate (`loop.write_structure()` twice to the repo path, twice to scratch) | identical, unchanged file not rewritten | bytes identical every time (sha256 `a606ca9d…`), mtime unchanged | PASS (idempotent) |
| equals the old loop's `structure_facts()` (HEAD tree) serialised with `indent=1` | identical | identical | PASS |

## (6) Regression

| set | expected | got | result |
|---|---|---|---|
| `tests/unit` | green | 1005 passed; 1 failed = my added test (F1). B2 baseline was 1012; the builder net removed 7 (see observation O1) | FAIL only through F1 |
| not slow: m0 m1 m2 m2c m3 m3x m4 m5 m5x m6 m8 m9 m10 | red set equal to report 414 (26 ids, all §8 / PENDING) | 264 passed, 26 failed; the 26 ids are identical to report 414 (listed below); none in m3, m3x, m4 | PASS (no new red) |
| slow m3 (`M3_L3_native_certificate_general_step`) | green | passed (serial run) | PASS |
| slow m4, parallel `-n 4` | | `M4_G1` (§8), `M4_L2` (F1), `M4_G3_loop_budget_and_lineage` red | see below |
| slow m4, serial | `M4_G1` red (§8); rest green | 5 passed, `M4_G1` red, **`M4_L2` red** | **FAIL (F1)** |
| `pytest --collect-only -q tests/acceptance` | clean | 374 collected | PASS |
| `python tools/check_lock.py` | OK | `LOCK OK` | PASS |
| `~/.claude/bin/acceptance-check` | PASS | FAIL, "differs from acceptance-v20", changed files `LOCK.json`, `m4/test_spinnet_compress.py` | expected (E1 not yet re-locked) |

Red ids of the not-slow run (same as report 414): m2c `E2`, `E5`, `Y1`, `G1` x5, `R1`, `R2`, `R3`, `P1`, `P2`; m6 `G5`, `G6`, `L2`, `L3`, `L9`; m8 `E2`, `S0`, `S2`, `S3`, `S4`, `S5`, `H1`, `L2`. Their reasons moved on with B3: `M2C_R1` now misses only `fuzzy_*` and `rishon`; `M2C_P1` fails at `unknown encoding 'rishon'` (the spinnet part passed); `M2C_R3` lists only fuzzy attributes (spinnet checked clean above).

`M4_G1` (expected red, §8): `'0bd7e7d9…0582' == '4b665716…1f08'`, i.e. the archive best still carries the old shared hash; the current shared hash is the builder's claimed `4b665716`.

`M4_G3` is not a B3 failure: under `-n 4` two workers call `loop.headline`, which writes the fixed name `results/compress/spinnet/robust.json.tmp` inside a per-entry loop (`os.replace` -> `FileNotFoundError`); the code is identical to `HEAD` (`git show HEAD:src/su2plaq/spinnet/loop.py`), and the test passes serially. The shared hash changed in B1/B2/B3, so the cache is rebuilt in every run, which makes the race likelier now. Do not run the slow m4 set with `-n > 1`.

## (7) Hashes (my own sha256 loop over the file lists, `t7.py`; file names read from the source text, not through `provenance.py`)

| quantity | builder's claim | got | result |
|---|---|---|---|
| `provenance.code_hash()` (21 existing shared files incl. `encodings/registry.py`) | `4b665716…1f08` | `4b6657169787aec981b96e18f65d174c9cff55370d4e6417bdd4437e9e9a1f08` | PASS |
| `code_hash_for("lsh")` | `c28d3d79…3425` | `c28d3d7921fc6715153d24849a0d259a7a5e21ef08645b0133f5e82a55823425` | PASS |
| `spinnet.loop.code_hash()` (sha256 of the hex string of the shared hash, then name/content of the 5 `SPINNET_CODE_FILES`) | `e4f1ff1d…9f34` | `e4f1ff1d5a435db9ca3fe27ba941cb7301feea3e75a99edfe15dc63f47db9f34` | PASS |
| `rishon.compress.code_hash()` (shared + ten rishon files) | `3af33130…d418a` | `3af33130e35e96f3f1852498ac097e433fb2e595aa8f8a64a2cfd8e5b68d418a` | PASS |
| `code_hash_for("spinnet")` (shared + the 5 registry files in registry order) | `8f9ada78…1c6e` | `8f9ada7824d7722ecde3a567da5ee04c33039897e55f5c74a18cd2e42cc31c6e` | PASS |
| project functions equal to my loop (all five) | | yes | PASS |

Hashes at B2 (report 414) were provenance `c4e357e9…`, spinnet `914e5711…`; they changed because `encodings/base.py` and `registry.py` (both shared files) were edited. The rishon hash changed for the same reason. Note: `code_hash_for("rishon")` is still not the rishon hash (rishon is registered only in B5).

## Observations (non-blocking)

- O1: the builder removed 12 unit tests of `tests/unit/test_spinnet_loop_unit.py` that tested behaviour which remains in the facade, e.g. `test_certify_best_also_certifies_a_different_headline`, `test_angle_set_is_the_locked_seeded_set`, `test_headline_*` (3), `test_report_and_run_round_one_annotation`, `test_cli_oracle_and_usage_errors`, `test_cli_candidate_trial_on_the_general_program`, `test_cli_brief_ideation_report_and_seed_dispatch`, `test_spec_carries_the_headline_rule_before_the_tools_section`, `test_round_brief_gets_the_headline_rule…` (39 tests down to 32, +5 new in other files). Nothing in the remaining set exercises the real certificate through `round._certify`, which is how F1 got through the builder's unit run.
- O2: the builder's note that `tools=` is needed for M4_S0 lines 171/174 is wrong; it is needed for M4_S4 only (section 3).
- O3: a fresh-shell command needs `PYTHONPATH=src` (plan text omits it).
- Restored after the runs (`git checkout --`): `results/compress/fuzzy_link/summary.json`, `results/compress/rishon/robust.json`, `results/compress/spinnet/robust.json`, `results/compress/spinnet/summary.json`, `results/spinnet/certs/spinnet-UB-o1-33d95284ebb7.json`, `…/spinnet-UB-o1-458a39365261.json`, `…/spinnet-UE-o1-df0c79b22d3f.json`, `…/spinnet-step-o1-066f66922ff8.json`, `…/spinnet-step-o1-b0a415d9322f.json`. No untracked byproducts. Untracked files that are mine on purpose: `results/tester/008-b3-step.json`, `results/tester/008-b3-hashes.json`, `tests/unit/test_tester_b3_certify.py`.
