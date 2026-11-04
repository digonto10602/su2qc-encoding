# Tester report 001: M0 step 0.1 (scaffold, stubs, lock tools, refs/paulo)

- Date: 2026-11-04
- Git commit: c48e549 (step 0.1 files are uncommitted in the working tree)
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` (§3 row 0.1, §2 Interface)
- Mode: step
- Related: none (first tester report). Raw numbers: `results/tester/001-m0-step-0-1.json`

## Commands
```
conda activate coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update .
pytest --collect-only -q tests/acceptance
pytest -n auto -m "not slow" tests/acceptance/m0 --junitxml=...
pytest -n auto tests/acceptance --junitxml=...        # classify every failure message
pytest -n auto tests/unit
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
cmp / sha256sum of refs/paulo/* vs /home/digimonk/Projects/su2qc-paulo-code/...
python (inspect-based walk over every su2plaq module: signatures, constants, call each stub)
```

## Results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| collect acceptance | 84 collected, 0 errors | 84 collected, 0 errors | exact | PASS |
| m0 `-m "not slow"` | all failures PENDING/NotImplementedError | 32 failed, 32 PENDING (messages `Failed: PENDING: NotImplementedError: <name> is not built yet`), 0 Import/Attribute/TypeError | 0 non-PENDING | PASS |
| whole acceptance dir (junit classification) | m1/m2 all PENDING except known R1 | 84 failed = 81 PENDING (m0 33, m1 17, m2 31) + 3 `test_M1_R1_results_files[UE,UB,step]` AssertionError "missing results/twelve/*.json" | 0 other | PASS (R1 classified PENDING for step 0.1) |
| stub signatures vs §2 | names, arg names, defaults match | all ~150 public callables/classes in §2.1–2.10 present; arg names/defaults/dataclass fields match for every name checked (Link, Corner, SplitGraph, PhysicalBasis, Layout, EncodedBasis, Batch, Verdict, ProgramResult, Entry, SeedCircuit, TaskSpec, Builder methods, evaluate(), run_round(), corner_singlets, target(), t_table, save_result, ...); module constants (SIGMA, PAULO_ORDER, SIM_BASIS, LOGICAL_BASIS, SEED=20261104, NOMINAL_ANGLES, ALT_ANGLES, BASIS, MACROS, MACRO_COST, INVALID_KEY, SCHEMA_VERSION, RESULT_KEYS, TwelveQubit.LINK_CODE/n_data=12/n_outer=16/is_basis_encoding=False) equal the spec | 0 mismatches | PASS |
| every stub callable raises NotImplementedError | all | 148 raise it; exceptions are Protocol-body methods of `Encoding` (return None by design, concrete `TwelveQubit` overrides do raise) and `PhysicalBasis.inner_key/outer_key`, which are real implementations (`% 625`, `// 625`) as §2.3 specifies | n/a | PASS |
| unit tests | pass | 42 passed (1.2 s) | none | PASS |
| `tools/check_lock.py` | LOCK OK | LOCK OK | none | PASS |
| `acceptance-check` | PASS | PASS: matches acceptance-v2 | none | PASS |
| refs/paulo copies | byte-identical, SOURCE.md sha256 correct | 5/5 `cmp` identical; sha256sum of all 5 equals the table in SOURCE.md | exact | PASS |

## Notes
- `pytest -m "not slow"` over all of `tests/acceptance` gives 81 failures (78 PENDING + 3 R1); the 3 slow-marked tests are deselected.
- Nothing numerical was computed in this step; PASS here means only that the scaffold imports, collects, and fails in the intended PENDING way.
- Observation (not a failure): `tests/unit` has only `test_import.py`; unit coverage of `tools/lock.py` / `tools/check_lock.py` beyond running them was not added.

## Failures
None. Pending (expected, later steps): 81 acceptance tests (m0 33, m1 17, m2 31) plus 3 `M1_R1_results_files` (results absent).
