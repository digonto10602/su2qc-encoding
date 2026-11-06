# Test report 042 - M2 audit-note fixes (mode `step`)

- Date: 2026-11-06. Commit: `0aca224` plus the builder's uncommitted diff (10 files: `docs/METHODS.md`, `results/compress/twelve/summary.json`, `compress/provenance.py`, `compress/report.py`, `compress/round.py`, `lean/certify.py`, 4 unit-test files). Tester: Sonnet 5.5.
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` (with 003 to 006 addenda; acceptance lock `acceptance-v7`). Audit being answered: `reports/audits/004-m2-compression-lean-audit.md` (N1, N2, N7, N13 in code; N3 to N6, N9, N12 in METHODS). Related: `reports/tests/041-m2-gate-full.md`, benchmark `reports/benchmarks/003-m2-benchmark.md` (job 2, same run).
- Raw numbers: `results/tests/042-m2-audit-notes-fixes.json`.
- Environment: `conda activate coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, 12 logical CPUs (`-n auto` = 12 workers).

## Commands run
```
graphify update . ; graphify affected "_circuit_of" / "cache_path" / "export_certificate"
pytest -n auto tests/unit                                   # 401 passed, 398.07 s
pytest -n auto tests/acceptance/m2                          # 46 passed, 362.38 s (incl. slow)
python tools/check_lock.py ; ~/.claude/bin/acceptance-check # LOCK OK ; PASS (acceptance-v7)
# regression of completed milestones: pytest -n auto tests/acceptance/m0 tests/acceptance/m1 (56 passed, run 3x inside benchmark 003: 198.1 / 199.7 / 201.4 s)
python scratchpad/n2.py, n2b.py, n2c.py   (N2/N13 experiments on a copy of the archive, see below)
```
`graphify affected` listed: `_circuit_of` -> `certify_best`, `run_round`, `main` (all covered by `test_certify_best_refuses_a_program_file_changed_after_evaluation`, `test_circuit_of_raises_on_a_program_sha_mismatch_and_builds_when_it_matches`, `test_round_records_lean_certificate`); `export_certificate` -> `_certify`, `certify_circuit`, `certify_circuit_kind` (covered by `tests/unit/test_lean_cert_unit.py`, `test_lean_round_unit.py`, acceptance `test_round_records_lean_certificate`, `test_lean_theorem_file_general`); `cache_path` has no callers in the graph other than `evaluate_program` (covered by `test_cache_key_changes_with_package_versions` and the cached-evaluation tests).

## Results

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| unit suite | all pass | 401 passed, 0 failed (5 new tests among them: 3 in brief_report, 1 evaluate, 1 lean_round) | 0 failures | PASS |
| acceptance m2 incl. slow | all pass | 46 passed, 0 failed, 0 pending | 0 failures | PASS |
| acceptance m0 + m1 (regression, incl. slow) | all pass | 56 passed x3 (benchmark 003 runs) | 0 failures | PASS |
| `tools/check_lock.py` | LOCK OK | `LOCK OK` | - | PASS |
| `~/.claude/bin/acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v7` | - | PASS |
| evaluator code hash after the fix | unchanged (`provenance.py`, `round.py`, `report.py`, `certify.py` are not in `EVALUATOR_FILES`) | `code_hash()` = `0bd7e7d91d9d...` = `evaluator_sha256` of `r05-F2-005` | exact | PASS |
| N1: Paulo's 1162 only in own column | `T (Paulo, Qiskit CT pass, U_B only, beta=1)` = 1162 | `summary.json` row `paulo34`: that column `1162`; `T_fixed`, `T(1e-6)`, `T_est(1e-6)`, `T(1e-10)` = `-` (old file had 1162 in all four, CX 294, depth 2549 kept) | exact | PASS |
| N1: rendered table equals JSON | same | `report_table("twelve","step")` reproduces `summary.json` byte for byte (sha256 `c8477ffd...` before and after) | exact | PASS |
| N1: note text and numbers | "662 T vs Paulo 1162 T, CX 294 vs 294" | note in `summary.json["notes"]` says exactly that; `results/m1_audit_fixes_n3.json`: ours via Qiskit CT T 662, CX 294; Paulo's pipeline T 1162, CX 294; shipped file T 1162, CX 294 (all `ok`, tol 0) | exact | PASS |
| N1: other rows unchanged | 13 other rows identical to `git show HEAD:...summary.json` after dropping the new empty Paulo column | 13/13 identical; all top-level keys other than `header`, `notes`, `rows` identical (`global_best`, `global_best_key`, lineage, counts) | exact | PASS |
| N2: tampered program | `ProgramShaMismatch` from `_circuit_of` and from `certify_best` | file copy of `005-outer-t2-peephole.py` + one comment line in a scratch root: both raised `ProgramShaMismatch: ... file sha256 c5f0014330c9 != archived program_sha256 4f7fcb1eab11` | raises | PASS |
| N2: untampered copy | builds | `_circuit_of` returned a 31-qubit, 272-operation circuit, no error; without `expected_sha256` the old behaviour is kept | - | PASS |
| N2: certificate provenance | `provenance.program_file_sha256` = sha256 of the program file of `r05-F2-005` | `certify_best` on a copy of the archive (350.4 s, Lean `certified`, 0 axioms): `cert.provenance.program_file_sha256` = `4f7fcb1e...` = file sha = `program_sha256` of the entry; `Entry.lean.program_file_sha256` same; `Entry.lean.gates_sha256` = `cert.gates_sha256` = `ca5c0f1a907a...`; field `program_sha256` gone from the new cert | exact | PASS |
| N2: old certificates still validate | old-format cert (`program_sha256` key) accepted | old `step-o1-ca5c0f1a907a.json`: `_structure_problem` = None; compiled Lean checker status `certified` (325.4 s) | - | PASS |
| N13: relative path written / resolved | `cert_path` relative to repo root; `resolve_cert_path` -> absolute existing file | stored `compress/lean/certs/step-o1-ca5c0f1a907a.json` (persisted in the reloaded archive entry); resolves to the repo file; relative path with `root=None` also resolves | exact | PASS |
| N13: old absolute entries | still read | `resolve_cert_path({"cert_path": "/home/.../step-o1-ca5c...json"})` returns it unchanged; unit test also covers `None` | - | PASS |
| N7: cache key includes versions | path changes when qiskit, aer or pygridsynth version changes | tag `1b9d66c02b1c` for (2.5.2, 0.17.2, 1.2.0); changing qiskit -> `ed750f2ef185`, aer -> `e03acfe5dd48`, pygridsynth -> `ca0447b4a408`; same directory (evaluator sha) | exact | PASS |
| METHODS text vs code (cited lines) | each citation points at what it says | see list below | - | PASS (3 minor off-by-few line numbers) |

### METHODS citations checked against the code
Correct: `metrics.py:23-26` (T and `depth_ct` from `synthesize`), `evaluate.py:236` (alternate verdict, `min(120, eval_budget_s)`), `evaluate.py:53` (`BUILD_TIMEOUT_S = 120`), `evaluate.py:23` ("NOT a security sandbox"), `evaluate.py:221` nominal `eval_budget_s` = 300 (`spec.py:46`), `evaluate.py` timeout at an alternate -> `eval_budget`, never cached (`reason not in ("eval_budget","build_timeout")`), `exact.py:885` (float cross-check), `exact.py:6` (`<= 1e-12 per entry`), `certify.py:_classify_angle` L77 and `_gate_records` L101, `Evaluator.lean:121` (`verdict_sound` with `b+d+l+s`), `structure.py:423/424`, `Counts.lean:96-97` (`dont_care_codes : 4 ^ 6 - 5 ^ 4 = 3471`), `Pins.lean` pins SHA-256 of states and targets, key `(CX, T_1e-6, depth_CT, qubits)`, `round.py:_circuit_of` raising `ProgramShaMismatch`, `round.resolve_cert_path`.
Imprecise (cosmetic, do not block): `lean/lemmas.py:20-25` - `_FORBIDDEN_RE` is at lines 22-27 (20-21 are import regexes); `Counts.lean:86-91` - the def of `maxPerOuterM` is at 86-87, the theorem `max_states_per_outer` is at line 95; `evaluate.py:247-251` - the metrics call is at 245-251. The numbers quoted in METHODS (1663 vs 1664, 1642 with X as one gate, 1952 of 3153 patterns) are copied from the audit and tester 028/041, not re-derived here.

## Observations (not failures)
1. The tests leave side effects in the work tree: `compress/programs/twelve/seed/000-general-ue.py` (untracked, generated on first use by `baselines.general_program_path` for kind `UE`; created 12:31 during the unit run) and a rewrite of `compress/lean/structure.json` (provenance only: `git_commit` 4fa765b -> 0aca224, `exporter_sha256`, `seconds`). I restored `structure.json` with `git restore` (twice: after the m2 run and after the benchmark unit runs). The untracked file is left for the coordinator (commit or delete; it is harmless).
2. The certificate of the archived best `r05-F2-005` that the committed archive points to (`compress/lean/certs/step-o1-ca5c0f1a907a.json`, git-ignored) still has the OLD format (no `program_file_sha256`, key `program_sha256`). I generated the new-format certificate on a COPY of the archive and then restored the original file (sha256 `885cc9c7...` before and after), so nothing in the repo changed. To get the new provenance into the real archive and the Report-2 numbers, run `python -m su2plaq.compress.round --certify-best` once (about 350 s) - a coordinator decision.
3. Switching to the new cache path means all existing `compress/cache/<evaluator>/<program>-<spec>.json` entries are no longer hit (the file name gained `-<versions_tag>`); this is intended by N7 and costs one re-evaluation per program on the next cached run.
4. Acceptance m2 `test_report_table_from_results` and the archive-best gate tests passed with the changed report layout.

## Verdict
**PASS** - 401 unit + 46 m2 acceptance + 56 m0/m1 regression tests pass, lock and acceptance-check PASS, 0 pending, 0 new failures versus report 041 (which had 396 unit and 102 acceptance tests; 5 new unit tests, 0 new acceptance tests). N1, N2, N7, N13 verified independently; METHODS N3 to N6, N9, N12 text agrees with the code up to the three cosmetic line references above.
