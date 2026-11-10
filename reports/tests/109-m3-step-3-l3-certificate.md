# Tester report 109 — M3 step 3.L3: native Lean certificate of the spin-network step circuit (track S, mode `step`)

- Date: 2026-11-06
- Commit: `7e5cfbe` (branch `m3-spin-network`) + uncommitted builder work for step 3.L3 (`src/su2plaq/spinnet/lean_export.py`, `lean/Su2PlaqCert/SpinNet/{Pins,Check,Main}.lean`, `lean/lakefile.toml` append, `tests/unit/test_spinnet_lean_cert_unit.py`, `results/spinnet/certs/`, `notes/merge-notes-spinnet.md`)
- Prompt in force: `prompts/104-spinnet-m4-plan.md` (highest number); the step is from `prompts/100-spinnet-m3-plan.md` (row 3.L3, interface line 102, budget line 149)
- Related: `reports/tests/108-m4-merge-full-suite.md` (the FAIL that this step answers), `reports/tests/107-m3x-lean-exact-w0-w4.md`
- Raw numbers and scripts: `results/spinnet/tester/3L3_*.json`, `results/spinnet/tester/3L3/*.txt`, `results/spinnet/tester/probe_*.py`
- Filename note: the numbering hook requires lowercase, so this is `109-m3-step-3-l3-certificate.md` (the brief wrote `3-L3`).

## Verdict: PASS

All required suites are green, the soundness probes found no way to make the checker accept a wrong circuit, and no laptop-owned file was edited. One probe of mine came out "certified" against my own expectation. It is correct behaviour (a phase on a clean ancilla is a global phase) and is explained under "Probe notes".

## Plain-English summary

The new Lean program `su2plaq_cert_spinnet` takes a JSON certificate: the circuit's gate list, the 433 physical basis states, and the exact target matrix written as Laurent polynomials in $z_\alpha=e^{i\alpha/4}$ and $z_\beta=e^{i\beta/4}$ with coefficients in $K=\mathbb{Q}(i,\sqrt2,\sqrt3)$. It replays the gates exactly on each of the 433 states and checks $U\psi_k = c\sum_{k'}V_{k'k}\psi_{k'}$. The checker pins the states and the target by SHA-256 against `Pins.lean`. I tried to break it with about 100 wrong circuits that I built myself and with 19 tampered certificates. Every wrong circuit that is physically different was rejected, and the checker named the offending state.

## Commands run (all in `~/Projects/su2qc-spinnet`, env `su2qc-coding`)

```
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd lean && taskset -c 0-9 lake build su2plaq_cert_spinnet                         # up to date, 0.41 s, 0.83 GB
taskset -c 0-9 pytest -p no:cacheprovider -q tests/acceptance/m3/test_spinnet_lean.py        # L3 alone
taskset -c 0-9 pytest -n 10 -p no:cacheprovider -q tests/acceptance/{m3,m3x,m0,m1,m2}        # one call per suite
taskset -c 0-9 pytest -n 10 -p no:cacheprovider -q tests/unit
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
taskset -c 10-19 python results/spinnet/tester/probe_{pins_independent,soundness,single_state,tampered_json,states_independent,export_semantics}.py ...
```
Slow tests included (no `-m "not slow"`). Scripts: `results/spinnet/tester/run_suites_3L3.sh`, `run_reg_3L3.sh`. Cores 0-9 for suites, 10-19 for probes.

## 1. Required suites

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `m3/test_spinnet_lean.py::test_M3_L3_native_certificate_general_step` | status `certified`, tampered `rejected`/`n_a` | passed; test call 0.92 s (export 0.29 s, check 0.30 s per circuit) | $\le 900$ s | PASS |
| `tests/acceptance/m3` (24, incl. slow) | 24 pass | 24 passed, 8.8 s | – | PASS |
| `tests/acceptance/m3x` | 4 pass | 4 passed, 7.2 s | – | PASS |
| regression `m0` / `m1` / `m2` | all pass | 34 / 22 / 46 passed (19 s / 234 s / 147 s) | – | PASS |
| `tests/unit` | all pass | 510 passed, 168 s (report 108: 489, +21 new tests) | – | PASS |
| `tools/check_lock.py` | LOCK OK | `LOCK OK` (exit 0) | – | PASS |
| `~/.claude/bin/acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v10` (exit 0) | – | PASS |
| pending (later-step) acceptance tests | – | 0 (nothing raises `NotImplementedError`; the m4 tests are not in this step's scope) | – | – |

Counts: passed 24 + 4 + 34 + 22 + 46 + 510 = 640, failed 0, errors 0, skipped 0, xfail 0, pending 0. New failures versus report 108: none (report 108 had L3 failing and `acceptance-check` exit 1; both are fixed). The laptop's flaky `test_results_unit` passed because `7e5cfbe` has no "c1".

## 2. Soundness of the new checker

### 2a. Reading `Check.lean` (not just the docstrings)

- `SpinNet.check` first runs `validate`. It demands 8 data + 8 outer qubits, every gate valid, no state supported on an ancilla, exactly `physicalDim = 433` states, none empty or with a repeated basis code, a target present, the exact Gram matrix equal to the identity (`gramError`), and `pinError`.
- `pinError` demands the SHA-256 of `statesText` to equal `Pins.statesSha256`. The target text is rendered at the target's own base, and its SHA-256 must equal `Pins.targetSha256 kind order`. Unknown kinds are rejected, and the cert base must be a positive multiple of the target base.
- `check` then spawns one `Task` per state: `List.range n |>.map (fun i => Task.spawn (c.checkRange pos i (min (i+1) n)))` with $n=433$. Each task calls `runGates c.gates (c.stateOf k)` and tests `== c.expected bi j`. These are the laptop's `Cert.stateOf`, `expected`, `checkRange` and `runGates` (exact $K$-Laurent arithmetic, structural equality), reused read-only. The fold returns the first failing state in index order.
- Only `validate` and `pinError` differ from the laptop's `Cert.check`: the register sizes and the pins. No twelve-qubit pins are used.
- Empirical confirmation that all 433 states are replayed: a sign flip on exactly one input state (multi-controlled Z on the 16 data/outer qubits, placed before the circuit) was rejected with `state k differs from the target` for $k\in\{0,1,2,100,216,300,431,432\}$ (8 of 8, `3L3_single_state.json`). The last state, 432, is therefore checked.

### 2b. Wrong-but-plausible circuits built by me (exporter + checker, `probe_soundness.py`)

Base circuit: `build_step(0.37, 0.61, 1, with_outer=True)` (52 instructions, 164 exported gates). 103 probes in total: 93 rejected, 1 `n_a`, 9 certified, of which 8 are controls or valid equivalences and 1 is a correct global-phase case (see "Probe notes"). Full list: `3L3_probes.json`, `3L3/probe_soundness.log`.

| probe | expected | got | verdict |
|---|---|---|---|
| baseline step order 1 | certified | certified | PASS |
| $\beta$-sign flip on each single `rz` (4 gates) | rejected | 4 of 4 rejected (state 0) | PASS |
| all 4 `rz` flipped ($\beta\to-\beta$) | rejected | rejected | PASS |
| all 4 `p` (U_E) flipped ($\alpha\to-\alpha$) | rejected | rejected | PASS |
| one `rz` angle doubled (still linear in $\beta$), 2 gates | rejected | 2 of 2 rejected | PASS |
| one `rz` angle times $(1+10^{-10})$ | rejected or `n_a` | `n_a` (`non_linear_angle:rz:-2.1350000002134997`) | PASS |
| one `rz` angle times $(1+10^{-13})$ | within exporter tolerance | certified (see notes) | PASS |
| each of the 12 `cx` reversed, one at a time | rejected | 12 of 12 rejected | PASS |
| every single instruction dropped (52 probes: 4 `p` electric phases on the corner and link qubits, `h`, `x`, `cx`, `rccx`, `rz`) | rejected | 52 of 52 rejected | PASS |
| `global_phase += 0.3` | certified (global phase is absorbed in $c$ by design) | certified | PASS |
| `rz(0.3)` on a clean ancilla | n_a or rejected, my expectation | certified (explained below; my expectation was wrong) | NOTE |
| `rz(β/2)` on a clean ancilla | global phase, certified | certified | PASS |
| `p(0.3)` / `p(β)` on a data qubit (relative phase) | rejected | rejected, rejected | PASS |
| extra X on a clean ancilla at the end (dirty ancilla) | rejected | rejected | PASS |
| extra H on data qubit 0 (leak) | rejected | rejected | PASS |
| order-1 circuit claimed order 2 | rejected | rejected | PASS |
| order-2 circuit claimed order 1 | rejected | rejected | PASS |
| order-2 circuit claimed order 2 (control) | certified | certified | PASS |
| kind confusions: UB claimed step, UE claimed step, step claimed UB, step claimed UE, UB claimed UE | rejected | 5 of 5 rejected | PASS |
| UB and UE controls | certified | certified | PASS |
| wrong claimed angles: $(0.74,0.61)$, $(0.37,1.22)$, $(0.61,0.37)$; circuit built at $(0.61,0.37)$ claimed $(0.37,0.61)$ | rejected | 4 of 4 rejected | PASS |
| compose $U_B$ then $U_E$ vs the step target $U_BU_E$ (wrong product order) | rejected | rejected | PASS |
| compose $U_E$ then $U_B$ (this is $U_BU_E$ in operator order) | certified | certified | PASS |

### 2c. Tampered certificates (19 probes, `probe_tampered_json.py`, `3L3_tampered_json.json`)

All 19 behaved as expected:
- Valid control: `ACCEPT`.
- The laptop's twelve-qubit `su2plaq_cert` on the spin-network certificate: `REJECT` (states differ from its pinned basis), so the two checkers are not interchangeable.
- Pins, structure and Gram checks fire as designed: swapped states (SHA pin), 432 states, ancilla support, duplicate code (`states 5 and 6 are not orthogonal`), non-normalised state, changed or extra target term (target SHA), kind UB attached to a step target, order 2 with an order-1 target, base doubled without rescaling, `n_data = 12`, no target, wrong schema.
- Replay catches a wrong phase exponent, a wrong phase $\omega$, an empty gate list and a dropped last gate (state 0 differs).

### 2d. Pins versus an independent recomputation (`probe_pins_independent.py`, `3L3_pins_independent.json`)

I parsed the certificate JSON with my own $K$ and Laurent reader, without `su2plaq.lean.exact`. I evaluated the target blocks at 5 angle pairs, including $(0,0)$ and a negative $\beta$: $(0.37,0.61), (0.91,0.23), (1.70,1.00), (2.9,-0.77), (0,0)$. The reference is `scipy.linalg.expm` of the route-B $H_B^{6j}$ from `su2plaq.exact.spinnet.h_magnetic_phys_6j`, not from `lean_export`. For UB I also compared with route A via $D^\dagger V_A D$ (`exact.operators.target`).

| target | max entry difference vs expm of $H_B^{6j}$ | vs route A | tolerance | verdict |
|---|---|---|---|---|
| UE | $1.6\times10^{-16}$ | – | $10^{-12}$ | PASS |
| UB | $1.5\times10^{-15}$ | $1.2\times10^{-15}$ | $10^{-12}$ | PASS |
| step, order 1 (base 4,4) | $1.8\times10^{-15}$ | – | $10^{-12}$ | PASS |
| step, order 2 (base 8,4) | $1.8\times10^{-15}$ | – | $10^{-12}$ | PASS |

- The independently computed SHA-256 of the canonical states text is `2a8bc36e…65c4`, equal to `Pins.statesSha256`.
- `su2plaq_cert_spinnet fingerprint` on the four certificates gives target SHA-256 equal to the four constants in `Pins.lean` (UE `521639b6…`, UB `5d4917d9…`, step-1 `b0bd6c78…`, step-2 `c4bfd129…`), and all four are `ACCEPT`.
- The 433 state codes equal my own enumeration of the physical codes: an even number of $j=\tfrac12$ links at each of the four 4-valent corners, and an extra $J$ bit when all four are $\tfrac12$ (`probe_states_independent.py`: count 433, sets equal).

### 2e. Exported gate list versus the Qiskit circuit (`probe_export_semantics.py`)

The exporter lowers `rccx` into `h/t/tdg/cx`. I rebuilt a Qiskit circuit from the cert JSON gates, with $\theta=m_\alpha\alpha/d_\alpha+m_\beta\beta/d_\beta$, and compared it with `build_step` on 12 basis states plus one random 5-state superposition (23-qubit `Statevector`). For both order 1 and order 2, $\max\,|\,1-|\langle a|b\rangle|\,| = 5.7\times10^{-15}$ and the overlap phase is $\le 3.6\times10^{-16}$. The gate list the Lean checker replays is therefore the same operator as the circuit, with no relative phase.

### 2f. Rules (START_HERE §0 rules 4-6) and Lean hygiene

| check | expected | got | verdict |
|---|---|---|---|
| tracked changes vs HEAD | only owned or allowed files | `docs/METHODS-spinnet.md` (M4 planner), `lean/lakefile.toml` (allowed append), `notes/STATUS.md`, `notes/merge-notes-spinnet.md`, `src/su2plaq/spinnet/lean_export.py` | PASS |
| untracked | owned | `lean/Su2PlaqCert/SpinNet/` (new files, allowed), `results/spinnet/certs/`, `tests/unit/test_spinnet_lean_cert_unit.py` | PASS |
| diff vs tag `milestone-2` on `tools`, `tests/acceptance/m0-m2`, `conftest`, `_api`, `docs/METHODS.md`, `src/su2plaq/{lean,evaluate,exact}`, existing `lean/Su2Plaq*/*.lean` | no laptop file changed | only `lean/Su2Plaq.lean` (+3 import lines, allowed) and new `lean/Su2Plaq/SpinNet/*.lean` | PASS |
| `lean/lakefile.toml` diff | one appended `lean_exe` stanza | exactly that, and listed in the merge notes | PASS |
| `native_decide` under `lean/Su2Plaq/`, `lean/Su2PlaqCert/SpinNet/` | 0 | 0 (grep); `sorry` 0 | PASS |
| `Structure/Counts.olean` mtime | unchanged | 2026-11-05 23:54:26.30 (same as in report 108) | PASS |

## Probe notes

1. `rz(0.3)` on a clean ancilla is certified. I expected `n_a`. The exporter recognises $0.3=\tfrac{30}{37}\alpha$ within $10^{-12}$ (denominator $\le64$), so it counts as linear. On an ancilla in $|0\rangle$ an `rz` is only the global phase $e^{-i\theta/2}$. The Laurent identity holds for all angles up to a monomial phase $c$, so the verdict is mathematically correct: the physical block action is unchanged. This is a limitation of what "certified" means, not a bug: the certificate proves $U=cV$ on the 433 states up to a global monomial phase. The global phase itself is only cross-checked in floating point by the evaluator.
2. A relative angle error of $10^{-13}$ on one rotation is certified, and $10^{-10}$ gives `n_a`. The exporter's angle recognition tolerance is $10^{-12}$ absolute (`exact.rational_multiple`), as in the laptop's design. Sub-$10^{-12}$ perturbations are certified as the ideal circuit.
3. The Lean checker is a compiled executable (computable code), not a kernel proof. `axioms: []` in `certify`'s result means "no kernel axioms involved", not "kernel-checked". Its trust is the program itself. The checker was not mutation-tested by editing Lean (production code, off limits). The behaviour probes above are the substitute.
4. Pins rest on trusting the Python exporter, as in the laptop's design. Section 2d is the independent cross-check.

## Resources

- Peak RSS: pytest suites 6.82 GB (the xdist workers mapping Mathlib for the Lean-calling tests); the spin-network checker alone 78 MB, 0.30 s on the step certificate; `lake build` 0.83 GB. All below the 10 GB limit.
- Wall time: L3 test 6.5 s (file of 3 tests, 6.82 GB); full verification session about 45 min, including the 23-qubit statevector probe of about 17 min on cores 10-14.
- Seeds: `probe_export_semantics.py` uses `np.random.default_rng(20261106)`. The other probes are deterministic.

## Observations

- The m2 laptop test rewrote `compress/lean/structure.json` (only `git_commit` `4fa765b` to `7e5cfbe` and `structure_certificate.seconds`), as in report 108. It is not reverted by the tester. The coordinator can run `git checkout compress/lean/structure.json` before committing.
- `acceptance-check` now passes because `acceptance-v10` covers the merge; nothing for the coordinator to do there.

## Failures

None.
