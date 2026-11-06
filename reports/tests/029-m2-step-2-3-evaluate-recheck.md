# Tester report 029 — M2 step 2.3 recheck (builder attempt 1: N1, N2, N4, `states=[0.5]`)

- Date: 2026-11-05
- Commit: a2ec571 (working tree with the uncommitted step-2.3 changes on top; Lean files ignored)
- Plan in force: `prompts/002-…` (+ addenda 003–006), acceptance-v6
- Mode: step (recheck)
- Related: reports/tests/027 (first round, FAIL on N1/N2/N4)
- Raw numbers: `results/tester_m2_step2_3_evaluate_recheck.json`; scripts in `tests/independent/evaluate_2_3/` (new: `bypass2.py`, `synth_cache2.py`, `toctou2.py`; they hard-code the tester scratchpad path).

## VERDICT: PASS WITH NOTES
N2, N4 and `states=[0.5]` are fixed. N1 is fixed for every ordinary route (all 3 earlier bypasses and 15 new ones are blocked) but the audit hook is defeated by 4 deliberate in-process attacks (sqlite3, patching `os.path.realpath`, patching `builtins.isinstance`, mutating the hook's closure via `gc`), which the module docstring already says ("NOT a security sandbox"). One new minor defect: a worker that forges `meta.json` and exits makes `evaluate_program` raise `FileNotFoundError` (N6).

Counts: m2 13 passed / 33 not passed (32 PENDING, 1 Lean file missing) / 0 genuine failures (identical to report 027); m0+m1 non-slow 54/54; unit 248 passed (Lean file excluded); collect 102; lock OK; acceptance-check PASS.

## Commands
```
pytest -n 6 tests/acceptance/m2 -q -rp --tb=line
pytest -n 6 -m "not slow" tests/acceptance/m0 tests/acceptance/m1 -q            # 142 s
pytest -n 6 tests/unit --ignore=tests/unit/test_lean_project_unit.py -q          # 58 s
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
python tests/independent/evaluate_2_3/{cases,extra,bypass2,run_cases,synth_cache2,toctou2,states_test,dos2,unverified3,evil}.py
python -m su2plaq.compress.run_candidate <step_program.py> --encoding twelve --kind step --trial|--full
```

## 1. Targets and regression

| check | expected | got | PASS/FAIL |
|---|---|---|---|
| `test_evaluator_rejects_partial`, `test_t_eps_in_ross_selinger_band` x3, `test_t_eps_deterministic`, `test_cache_keyed_by_code_hash` | PASS | PASS (13 m2 ids green incl. oracle, builder x3, 3 Lean) | PASS |
| other m2 ids | PENDING only | 17 `general_circuit`, 4 `Archive.load`, 3 `import_seed`, 2 `general_program_path`, 1 `qiskit_l3`, 5 `lean.certify/structure`, 1 missing `lean/certs/twelve-general-step.lean` (Lean track) | PENDING |
| m0 + m1 non-slow | all pass | 54 passed | PASS |
| unit | all pass | 248 passed | PASS |
| collect / check_lock / acceptance-check | clean / OK / PASS | 102 / LOCK OK / matches acceptance-v6 | PASS |

## 2. N2 — SHA vs evaluated source (TOCTOU), `toctou2.py`
The file is rewritten after `evaluate_program` has read and hashed it, before the worker starts (the build now takes bytes, not a path).

| case | recorded sha == sha(first content) | evaluated content | PASS/FAIL |
|---|---|---|---|
| A = good program, file swapped to cheat B | True | A (valid `ok`) | PASS |
| A = cheat program, file swapped to good B | True | A (invalid `error`) | PASS |

## 3. N4 — synth cache (`synth_cache2.py`, theta = 0.4321, eps = 1e-6; good word has T = 64, error 4.2e-7)
Entry format: JSON `{version, theta, eps, word, sha256}`. In every case the entry was overwritten, `gridsynth_word` called, and the returned word compared with the good word.

| corrupt entry | returned = good word | entry repaired on disk |
|---|---|---|
| garbage text; empty file; truncated JSON; 256 binary bytes; JSON list; wrong types | yes (6/6) | yes |
| word tampered (old checksum); wrong checksum literal | yes (2/2) | yes |
| alphabet violation `HT?SH` with valid checksum; garbage word `HTHT…` with valid checksum; empty word with valid checksum | yes (3/3) | yes |
| valid word of another angle, with valid checksum (error check) / with old checksum | yes (2/2) | yes |
| other version / other eps / other theta field | yes (3/3) | yes |
| old-style `.txt` file next to the key | ignored, recomputed | yes |

17/17 cases PASS (T = 64 returned every time). Keying: after the first word, next-after theta, eps(1+1e-7) and a faked pygridsynth version `9.9.9` gave 1 -> 4 distinct entries. PASS.

## 4. `states=` (`states_test.py` + direct calls)
- Independent dense reference (diagonal circuit, seed 20261105): max deviation 5.1e-16 over 8 subsets (unchanged); full 433: 2.1e-17.
- `[0.5]`, `[1.0]`, `array([0.5,2.0])`, `['3']`, `[True]`, `[1.5,2]`, `array([1.,2.])` now raise `ValueError("states must be integer physical-state indices")`; `[np.int64(3)]` and `(4,5)` accepted (n = 1, 2); `[]`, `[-1]`, `[433]`, `method="inner_span"` still `ValueError`. PASS.

## 5. N1 — write/exec/network blocking and bypass attempts

Previously successful bypasses (report 027), now:

| attack | result | PASS/FAIL |
|---|---|---|
| `np.save` | `build_error: PermissionError … may not write files` | PASS |
| `Builder.__init__.__globals__["__builtins__"]["open"]` (write) | PermissionError | PASS |
| `BB.pathlib.Path(...).write_text` | PermissionError | PASS |

New attacks (each tries to create a marker file or process; `MARKER_*` files checked on disk):

| attack | result | PASS/FAIL |
|---|---|---|
| `io.open` write and append (via builtins dict); `pathlib.io.open` | PermissionError | PASS |
| `os.open(O_WRONLY\|O_CREAT)` (via `pathlib.os`) | PermissionError | PASS |
| `tempfile.mkstemp` / `NamedTemporaryFile` (imported through `bi["__import__"]`) | PermissionError (open in the work dir) | PASS |
| `pickle.dump`, `marshal.dump` to a file | PermissionError | PASS |
| `numpy.memmap(mode="w+")`, `np.lib.format.open_memmap` | PermissionError | PASS |
| `os.system`, `subprocess.run`, `socket.connect`, `os.mkdir`, `os.remove` | PermissionError (`os.system`, `subprocess.Popen`, `socket.__new__`, `os.mkdir`, `os.remove`) | PASS |
| `ctypes.CDLL(None)`, `ctypes.pythonapi.PyRun_SimpleString` | PermissionError (`ctypes.dlopen`, `ctypes.dlsym`) | PASS |
| `sys.modules` pop of `os` + extra `sys.addaudithook` + write | write still blocked (hooks cannot be removed) | PASS |
| reading `/etc/hostname` | allowed (documented: reads not blocked) | as documented |
| **`sqlite3.connect()` + `create table`** (C-level file creation, no `open` audit event) | marker written, program VALID | FAIL (bypass) |
| **patch `os.path.realpath` (reachable as `pathlib.os.path`) to return an allowed path**, then write | marker written, VALID | FAIL (bypass) |
| **patch `builtins.isinstance` to return False** (hook uses it), then write | marker written (build later crashed on the broken `isinstance`) | FAIL (bypass) |
| **`gc.get_objects()` -> hook function -> mutate the `allowed` set in its closure**, then write | marker written, VALID | FAIL (bypass) |

Static scan unchanged: 13/13 `import X` forbidden modules, `open/exec/eval/compile/__import__` names -> `contract`.

## 6. Re-run of the first-round attack suite (all still correct)
Cheat on 16 outside-trial states: trial VALID / full `error` (op-norm 1.0); dirty ancilla, 1e-9 leak: `dirty_ancilla`; 1e-11 leak: valid; angle-specialised: `skeleton`; hard-coded angle: `alt_angles:error`; 8 disguised-gate variants + 6 name-mutation/measure/barrier variants: `disallowed_gate`/`error`/valid-by-class as before; writes_outer; qubit cap via direct QuantumCircuit / alloc / `_n_anc` / `peak_qubits`: `max_qubits`; Builder `_ops` / class-swap / BASIS patch: rejected; infinite loop: `build_timeout`; support blow-up: trial `unsimulable` 8.3 s, full `dirty_ancilla` 23.6 s; `unverified` mapping at tol 8e-10 (aer_mps, err 6.78e-10): `unverified`, at 1e-9: valid certified; parent executes no proposer code (no import/open events in the parent, `sys.modules` clean). The only change: `import numpy.lib.npyio` still passes the scan (harmless now; writing is blocked in the worker).

## 7. New defect N6 (minor)
A program that writes a forged `meta.json` (allowed file) and calls `os._exit(0)` leaves no `out.qpy`; `_build_in_subprocess` then does `open(out,"rb")` and `evaluate_program` raises an uncaught `FileNotFoundError` instead of returning `build_error`. Requires a deliberate attack (an ordinary crash leaves no meta and takes the clean `build_error` path). Guess: missing `out.exists()` check next to `meta.exists()`. Not blocking.

## 8. Timing, `build_step(0.37,0.61)` program (237 gates, 50 qubits), load average 1.4
| command | wall (end-to-end) | budget |
|---|---|---|
| `--trial` x 6 | 4.75–4.84 s (internal 4.3 s) | < 10 s: PASS |
| `--full` x 3 | 16.1–16.4 s (internal 16.0 s) | none |
Result unchanged: valid; op-norm 1.6e-13 (trial), 2.69e-13 / 2.69e-13 / 2.67e-13 (full, three angle pairs), skeleton equal, T_eps 952 (estimate 909.95 in trial), CX 294, depth_CT 1421. Faster than round 1 (5–5.8 s / 17.7–20.5 s) mostly because the machine was less loaded.

## Notes for the coordinator
- N1 now meets "accidental and casual" attempts; do not describe the hook as protection against an adversarial proposer (4 documented-class bypasses above). The audit hook is, by its own docstring, not a sandbox.
- N6 is a one-line guard; N5 (Clifford+T re-verification) remains a TODO(2.5/2.6) as documented in the module docstring.
