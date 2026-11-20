# 402 — LSH erratum: locked gate test M8-G2 (second engine) for a headline that reads outer qubits

- Date: 2026-11-20 · Author: planner · Git commit at writing: `281b073` (branch `merge-desktop-tracks`, host omnicommander; work started at `a183bff`, the commit in between changes only `notes/STATUS.md`).
- Plans amended: `prompts/401-lsh-m8-compression-plan.md` — §9 stop rule (line 220, the clause "the archive best or headline touches the outer register or has more than 14 ancillas (M8-G2 fails by design)"), decision D11 (line 244), table row G2 of §6 (line 194), and the content of the test named in row 8.10 (line 164). **Nothing else in `prompts/401` changes.** No file in `src/`, no other test, no existing tolerance, no hash changes.
- Acceptance test changed: `tests/acceptance/m8/test_lsh_m8_gate.py::test_M8_G2_best_and_headline_second_engine_aer` (same id, new content). The other five tests of the file (`test_M8_G1_…`, `G3`, `G4`, `L5`, `R1`) and every other acceptance file are untouched. Next tag: `acceptance-v23`.
- Decision: Digonto, chat, 2026-11-20: "Planner amends M8-G2" (relayed to the planner by the coordinator; recorded in `notes/STATUS.md` Decisions at `281b073`).
- Related reports: `reports/tests/445-lsh-milestone-8-gate-full.md` (the red), `reports/tests/438`, `441`–`444` (earlier full-register Aer runs by the tester), scripts `results/tester/444/aer.py`, `results/tester/445/aer_headline.py`.
- Planner evidence for this erratum (scratch, gitignored): `scratch/planner/402/` — `amended/test_lsh_m8_gate.py` (the tested copy), `g2-erratum.patch`, `mutants.py/.json/.log`, `w7_reduced.py`, `headline_rows.py/.json`, `full_register_probe.py/.json`, `mem_probe.py`, `probe.py`, `timed.py`. Seeds: 20261120 (the test's `G2_SEED`; also the 12-state probe).

Words used. *Outer register*: the 12 qubits `o[12..23]` that hold the four outer sites; the step must leave them unchanged. *Read / control*: a gate reads an outer qubit when its action on the other qubits depends on that qubit's value but the value itself is never changed. *Write*: a gate that can change the value of the qubit (for example `x`, `h`, or the target of `cx`). *Second engine*: Qiskit Aer's statevector simulator, a simulator independent of the project's own one, used at the gate to re-check the best circuit. *Sector* (my label): the set of physical states that share one value of the outer bits the circuit reads. *Physical codes*: the 433 bit patterns of the 24-qubit register that satisfy the Gauss law; *inner codes*: the 47 allowed patterns of the 12 data qubits. *Reduced register* (my label): the circuit's qubits without the outer qubits that no gate touches.

## 1. Trigger and diagnosis

The LSH loop ended (stop reason `max_sessions`). Archive best = headline = `r05-F3-005` (68 CX, `compress/programs/lsh/F3/005-alpha-early-walk22.py`). It reads the outer qubits 13 and 14 (site 0: $\ell_{2v}$, $\ell_{v1}$) as `cx` controls (3 and 5 times) and touches no other outer qubit. The task specification allows this ("use them as controls only; a program that writes an outer qubit is invalid", `compress/specs/lsh-step.md`).

The locked helper `aer_inner_check` simulates only data + ancilla qubits on the 47 inner codes and asserts that no gate touches the outer register, so `test_M8_G2_best_and_headline_second_engine_aer` fails on a valid circuit (tester 445: the only red of the gate). `prompts/401` named this case in advance (§9, D11). It is a gap of the test, not a physics error: tester 445 measured $2.4\times10^{-15}$ on the full register.

Why the old check cannot simply be extended: its 47-code shortcut is valid only because a circuit that touches no outer qubit acts identically for every outer pattern. A circuit that reads outer bits acts differently in different sectors, so the outer bits must be part of the simulation.

## 2. The amended wording of `prompts/401`

- **§9, stop rule clause** now reads: "the archive best or headline *writes* an outer qubit; or touches no outer qubit and has more than 14 ancillas; or reads outer qubits and has at least one ancilla (M8-G2 fails by design in these three cases)".
- **D11** now reads: "Second engine at the gate = Aer. A circuit that touches no outer qubit: data + ancilla qubits, the 47 inner codes, nominal angles (unchanged). A circuit that reads outer qubits as controls: (a) data + ancilla + read outer qubits, all 433 physical codes, and (b) the full 24-qubit register, 10 seeded physical states; both at the three spec angle pairs. A best circuit that writes an outer qubit, or reads outer qubits and has ancillas, goes back to the planner."
- **§6 table, row G2** now reads:

| Test | What | Tolerance | Justification |
|---|---|---|---|
| G2 (slow) | Aer, best and headline. No outer qubit touched: as before (47 inner codes, data + ancilla qubits, nominal pair). Outer qubits read: static scan (no gate writes an outer qubit); all 433 physical codes on the reduced register; 10 seeded states on the full register; three angle pairs | error $10^{-10}$ after one global phase; thresholded weights $10^{-20}$; outer-pattern probability change $10^{-10}$; $\le26$ qubits (reduced register), $\le24$ qubits (full register) | §3–§5 of this file; measured $\le3.1\times10^{-15}$ (reduced), $\le2.2\times10^{-15}$ (full), weights $0$, probability change $\le8.0\times10^{-17}$ |

- **Row 8.10**: the test id is unchanged; its content is §3 of this file.

## 3. The new check (exact definition)

Notation. $W$ is the unitary of the circuit on data $\otimes$ ancilla $\otimes$ outer qubits. $V=$ `enc.target("step", α, β, 1)` is the exact $433\times433$ step in physical-basis order (the same matrix the shared evaluator uses through `su2plaq.compress.oracle.target`; `prompts/401` §1.1: $V=U_B(\beta)U_E(\alpha)$, inner electric term only). The physical code $c_k$ is the integer `enc.physical_vectors().codes[k][0]`; bit $i<12$ sits on `layout.data[i]`, bit $12+j$ on `layout.outer[j]` (`enc.layout_of`, the evaluator's convention). $R$ is the set of outer qubits the circuit reads. Ancillas start in $|0\rangle$. The three spec angle pairs are $(0.37,0.61)$, $(0.91,0.23)$, $(1.70,1.00)$ (`G2_PAIRS`).

The test rebuilds the entry from its program file through the stock worker (as before) and calls `g2_second_engine`:

### 3.0 Branch
`reads = outer_reads(qc, enc)` on the nominal circuit (§3.1). If `reads` is empty the old code runs, unchanged (§4). Otherwise §3.1–§3.3 run at each of the three pairs.

### 3.1 Static scan: no gate writes an outer qubit (`outer_reads`)
For every gate $g$ that acts on an outer qubit $q$, the gate's own matrix (from `qiskit.quantum_info.Operator`, the gate's qubit $p$ = bit $p$ of the matrix index) must have **exactly zero** entries between the two values of that bit:
$$g=|0\rangle\langle0|_q\otimes A+|1\rangle\langle1|_q\otimes B\qquad\Longleftrightarrow\qquad[g,Z_q]=0 .$$
This is the precise meaning of "the qubit is a control": the gate may depend on the bit, it cannot change it. `cx` control, `ccx`/`rccx` controls, `cz`, `cp`, `crz` and diagonal one-qubit gates pass; `x`, `h`, `swap` and the target of `cx`/`ccx` fail (checked: `scratch/planner/402/probe.py`). Any other gate on an outer qubit raises `AssertionError` ("writes the outer qubit …"): the test fails. The scan returns $R$ with the number of reads per qubit; at each pair the read set must equal the nominal one.

Two remarks. (i) It is the same criterion as the production rule (`su2plaq.evaluate.evaluator._outer_reads`), computed independently (the test does not call it). (ii) A diagonal one-qubit gate on an outer qubit passes the scan (it is a phase controlled by the outer bit, not a write); whether that phase is right is decided by §3.2 (mutant C7 below: it is caught).

### 3.2 All 433 physical codes on the reduced register (`aer_outer_read_check`)
No gate acts on the outer qubits outside $R$, so $W=W_R\otimes\mathbb 1$ on them: the circuit is exactly the identity on an idle qubit. Aer therefore simulates the **unchanged gate list** on the $n=12+a+|R|$ qubits data + ancilla + $R$ ($a$ = number of ancillas). The old helper uses the same reduction for all 12 outer qubits. Limit $n\le26$ (the existing limit; a larger circuit fails with a message).

For every distinct pair $(d,r)$ = (data code, value of the read bits) that occurs among the 433 physical codes, one run from the basis state $|d\rangle|0_a\rangle|r\rangle$. For the physical code $c_k=(d,o)$ the output of the real circuit is that run with the outer pattern $o$ kept. Each output amplitude with modulus above $10^{-13}$ (the threshold of the old helper) falls into exactly one class:

- ancilla not $|0\rangle$ → `ancilla_weight`;
- ancilla $|0\rangle$, read bits $\ne r$ → `outer_weight` (the outer register changed);
- ancilla $|0\rangle$, read bits $=r$, data code $d'$ with $(d',o)$ not a physical code → `leak_weight` of column $k$;
- otherwise → the entry $M_{k'k}$ of a $433\times433$ matrix, $c_{k'}=(d',o)$.

Reported: $\text{error}=\lVert M-e^{i\varphi}V\rVert_2$ with $e^{i\varphi}=\operatorname{tr}(V^\dagger M)/|\operatorname{tr}(V^\dagger M)|$ (operator norm = largest singular value; **one** global phase for the whole matrix, so relative phases between sectors count), and the largest value of each weight (over the runs; for the leak over the 433 columns).

### 3.3 Seeded physical states on the full register (`aer_full_register_check`)
Aer simulates the unchanged gate list on the full register ($24+a$ qubits; limit 24, i.e. no ancillas, §5). Inputs: `G2_STATES = 10` states $\psi_s=\sum_kc_{sk}|c_k\rangle$, with $c_{sk}$ complex Gaussian numbers from `numpy.random.default_rng(G2_SEED = 20261120)` (real parts and imaginary parts drawn as two $10\times433$ normal arrays, in this order), each state normalised. Every state has non-zero weight in every sector (asserted; for the headline the smallest sector weight of any state is $0.112$ (`mutants.json`, `state_sector_weight_min`)). The same 10 states are used at the three pairs.

Reported: $\text{error}=\max_s\lVert P\,W\psi_s-e^{i\varphi}V c_s\rVert_2$ ($P$ = restriction to the 433 physical codes with ancillas $|0\rangle$; one phase $e^{i\varphi}$ from $\sum_s\langle Vc_s|PW\psi_s\rangle$ for all 10 states); `ancilla_weight` and `leak_weight` (amplitudes above $10^{-13}$ with ancilla not $|0\rangle$; with ancilla $|0\rangle$ outside the physical codes); and `outer_weight_change` $=\max_s\max_o|p^{\rm out}_s(o)-p^{\rm in}_s(o)|$, where $p(o)$ is the total probability of the outer pattern $o$ (all 4096 patterns, no threshold).

### 3.4 Assertions and tolerances

| Quantity | Tolerance | Status | Justification |
|---|---|---|---|
| §3.1 static scan | exact zeros | new | a structural fact about the gate list; standard gates have exact zero entries; no numerical tolerance to argue |
| §3.2 `error` | $\le10^{-10}$ | same number, same quantity (operator norm after one global phase), now on $433\times433$ instead of $47\times47$ | exact-angle rule of `prompts/003`–`004`; rounding of $\approx215$ double-precision gates is $\sim10^{-14}$; measured $\le3.1\times10^{-15}$ (margin $3\times10^{4}$) |
| §3.2 `ancilla_weight`, `leak_weight` | $\le10^{-20}$ | same numbers, same definition (thresholded sums) | $=(10^{-10})^2$, the weight rule of `prompts/004`; measured $0$ |
| §3.2 `outer_weight` | $\le10^{-20}$ | new | same definition and number as the other two weights; for a circuit that passes §3.1 the exact value is $0$; measured $0$ |
| §3.3 `error` | $\le10^{-10}$ | new | a state error is bounded by the operator-norm error of §3.2, so the same number is the consistent one; measured $\le2.2\times10^{-15}$ |
| §3.3 `ancilla_weight`, `leak_weight` | $\le10^{-20}$ | new | as above; measured $0$ |
| §3.3 `outer_weight_change` | $\le10^{-10}$ | new | for an output $\psi_o+\delta_o$ in pattern $o$: $|\Delta p(o)|\le2\lVert\psi_o\rVert\lVert\delta_o\rVert+\lVert\delta_o\rVert^2\le2\varepsilon+\varepsilon^2$, so the amplitude tolerance $\varepsilon=10^{-10}$ allows at most $2\times10^{-10}$; $10^{-10}$ is that bound without the factor 2 (slightly stricter). Rounding floor: sums of $\le2^{12}$ squared doubles with total $\le1$, a few $10^{-16}$; measured $\le8.0\times10^{-17}$ in the test and $\le4.3\times10^{-16}$ in the 12-state probe of §7 |
| read set equal at the three pairs | exact | new | one gate skeleton for all angles (the validity rule of `prompts/401` §1.1) |
| `(spec.alpha, spec.beta) == (0.37, 0.61)` | exact | new, outer-reading path only | ties the rebuilt nominal circuit to `G2_PAIRS[0]` |

No existing tolerance is changed. The qubit limit of the reduced register stays 26 (same memory per state as before: $2^{26}$ complex128 = 1.0 GB). The full-register block has its own limit, justified in §5.

## 4. Why this is sound

**Circuits that touch no outer qubit: unchanged path.** `aer_inner_check` is byte-for-byte the old function and the two assertions after it are the old ones. The only code that runs before it is the static scan, which for such a circuit finds no gate on an outer qubit, asserts nothing and returns an empty set. A circuit that touches an outer qubit with a writing gate failed before (in `aer_inner_check`) and fails now (in `outer_reads`).

**Circuits that read outer qubits: at least as strong as the old check was for its class.**
1. Coverage. The old check proves a statement about all 433 states *through* a structure argument (block structure of the step, locked M7-K2/M7-C2). §3.2 needs no such argument: it produces every one of the 433 columns of the circuit and compares the whole $433\times433$ block in operator norm. By linearity this bounds the error on every physical state, not on a sample.
2. Only premise of §3.2: a qubit that no gate acts on is unchanged and factorises. This is exact for a gate list, and the old helper relies on it for all 12 outer qubits. §3.3 removes even this premise for 10 random states that involve all 433 codes and all 305 outer patterns at once.
3. Phases between sectors. One global phase for the whole matrix (§3.2) and for all states (§3.3). A circuit that is right inside each sector but has a wrong relative phase between sectors fails (mutants C7, C8).
4. Outer register. Three independent guards: the static scan (exact), `outer_weight` (§3.2, read bits) and `outer_weight_change` (§3.3, all 4096 outer patterns on the real register).
5. Angles. Three pairs instead of one.
6. The two routines measure the same thing. On the 9 round-0 seed circuits that touch no outer qubit, the new 433-column routine (called with an empty read set, in scratch only) and the old 47-code routine agree: errors $3.0\times10^{-15}$–$5.3\times10^{-15}$ in both, differences $\le1.1\times10^{-16}$ (`scratch/planner/402/mutants.json`, rows `seed …`). This also confirms the block-structure premise of the old path numerically.

What the second engine shares with the first, as before: the target matrix, the list of physical codes and the layout come from the encoding object. The simulator and the bookkeeping are independent.

**Design note (for the coordinator and Digonto).** The brief asked for the full-register run on $\ge10$ seeded states (§3.3). I added §3.2 because a sample of states cannot bound an operator norm on a 433-dimensional space, and the old check was exhaustive; with §3.2 the amended G2 stays exhaustive. §3.2 costs 3 s and 0.25 GB. §3.3 costs about 110 s and 1.6 GB. Both are asserted; neither is optional.

## 5. Limits, cost, memory (measured)

Machine: omnicommander, cores 0–7, 1 thread, `tools/pytest-safe -n 1`. Wall time and memory from `scratch/planner/402/timed.py` (largest resident set size of any descendant process).

| Run | Wall | Peak memory |
|---|---|---|
| §3.1 + §3.2 only (63 runs of $2^{14}$ amplitudes per pair), current archive (best = headline, one circuit); measured on the revision of the file before §3.3 was added | 4.1–5.4 s | 221–232 MiB |
| amended G2 as locked (§3.1–§3.3; adds 30 runs of $2^{24}$ amplitudes), current archive | 114.2 s (test call 113.4 s) | 1621 MiB |

- Reduced register, $n=12+a+|R|\le26$: unchanged limit. Per state $2^{26}\times16$ B = 1.0 GB plus the 0.5 GB threshold scan, as in the old helper (measured on a toy circuit, `mem_probe.py x 26`: 1.78 GB peak).
- Full register, $n=24+a\le24$: **a new limit, set from memory.** A run with a prepared input state holds four copies of the state inside Aer (measured `mem_probe.py set 24`: 1.03 GB above the 0.18 GB baseline for a 0.25 GB state). The complete test peaks at 1.62 GB at 24 qubits. At 25 qubits the same run needs about $0.25+2\times1.37\approx3.0$ GB, above the 2.2 GB acceptance budget of this machine (project `CLAUDE.md`). Hence 24 qubits, i.e. no ancillas. A circuit that reads outer qubits and has ancillas fails with a message (planner decision), as any outer-reading circuit did before. The current best and headline have 24 qubits and no ancilla.
- Number of runs in §3.2: at most $\min(433,\,47\cdot2^{|R|})$ per pair (headline: 63 = 18 + 16 + 16 + 13 for the four sectors with 190, 92, 92, 59 physical states).

## 6. The diff, assertion by assertion

File: `tests/acceptance/m8/test_lsh_m8_gate.py` (393 → 610 lines; patch `scratch/planner/402/g2-erratum.patch`). sha256 (as `tools.check_lock.sha`): old `8aa27c35d1aaacf171ddbc28adf46bda55663277b646361d33f85f860717ba15`, new `522c1f71eae4864dac683b5b03029a4ecf2323dbd923de1f12b3158f564e6843`.

| Change | Why |
|---|---|
| module docstring, G2 paragraph and tolerance paragraph | describe §3; the sentence "a circuit that reads outer qubits … fails here" is no longer true |
| constants `G2_PAIRS`, `G2_SEED`, `G2_STATES` | the three spec pairs; the recorded seed and number of states |
| `aer_inner_check` | **not changed** |
| new `outer_reads` | §3.1 |
| new `aer_outer_read_check` | §3.2 |
| new `g2_states`, `aer_full_register_check` | §3.3 |
| new `g2_second_engine(rebuild, spec, enc, tag)` | the body of the test per entry, so that the same code can be run on mutant circuits; the empty-read branch contains the three old lines verbatim |
| test body: the three lines `res = aer_inner_check(...)`, `assert res["error"] <= TOL`, `assert res["ancilla_weight"] <= 1e-20 and res["leak_weight"] <= 1e-20` are replaced by one call of `g2_second_engine` | the old lines now sit in the empty-read branch; the new assertions are those of §3.4 |
| test docstring | describes both branches |

Interface used (existing public API only, nothing new in `src/`): `su2plaq.compress.spec:get_encoding`, `default_spec`, `TaskSpec.with_angles`; `enc.layout_of`, `enc.physical_vectors`, `enc.target`, `enc.inner_codes`, `enc.inner_target`; `su2plaq.compress.evaluate._build_in_subprocess` (through the existing `_rebuild`); `su2plaq.compress.archive.Archive`, `su2plaq.compress.robust.headline`; Qiskit `Operator`, `transpile`; Aer `AerSimulator`, `QuantumCircuit.set_statevector`.

## 7. Evidence (planner runs, commit `281b073`, amended file sha256 `522c1f71…6843`)

**The exact command of the brief cannot run before the lock**: with the amended file in the tree and `LOCK.json` not updated, every acceptance session stops with `ACCEPTANCE LOCK BROKEN` (seen once at the start of this run; the tree was put back at once). All runs below therefore use a byte-identical copy in `scratch/planner/402/amended/` with a small conftest that provides the `root` fixture: `taskset -c 0-7 tools/pytest-safe -n 1 scratch/planner/402/amended/test_lsh_m8_gate.py -k G2 -m "slow or not slow"` → `1 passed in 114.01s`.

Headline = archive best `r05-F3-005`, read set {13: 3 gates, 14: 5 gates} (`headline_rows.json`, `mutants.json`):

| Pair $(\alpha,\beta)$ | §3.2 error (433 codes, $n=14$, 63 runs) | §3.2 weights (ancilla, leak, outer) | §3.3 error (10 states, $n=24$) | §3.3 outer-pattern probability change | §3.3 weights |
|---|---|---|---|---|---|
| (0.37, 0.61) | $2.98\times10^{-15}$ | 0, 0, 0 | $1.80\times10^{-15}$ | $7.8\times10^{-17}$ | 0, 0 |
| (0.91, 0.23) | $2.59\times10^{-15}$ | 0, 0, 0 | $1.46\times10^{-15}$ | $6.1\times10^{-17}$ | 0, 0 |
| (1.70, 1.00) | $3.10\times10^{-15}$ | 0, 0, 0 | $2.20\times10^{-15}$ | $8.0\times10^{-17}$ | 0, 0 |

Tolerances $10^{-10}$ (errors, probability change), $10^{-20}$ (weights): all pass.

Mutants (`scratch/planner/402/mutants.py`, programs in `scratch/planner/402/mutants/`, none in the archive; each run through `g2_second_engine`, i.e. the code of the test):

| Mutant | Result | Where it fails |
|---|---|---|
| W1 `cx(0→13)` twice (net identity, but writes) | FAIL | static scan: "gate cx on qubits [0, 13] writes the outer qubit 13" |
| W2 `x(13)` twice; W3 `h(14)` twice; W4 `swap(13,14)` twice; W5 `cx(0→13)` once | FAIL | static scan |
| C1 one walk coefficient with the wrong sign (program) | FAIL | §3.2 error $0.152$ |
| C2 reads outer qubit 16 instead of 13 (program) | FAIL | §3.2 error $2.0$ |
| C3 first `cx(13→0)` dropped | FAIL | §3.2 error $2.0$ |
| C4 built at $-\beta$ | FAIL | §3.2 error $1.88$ |
| C5 one `rz` angle shifted by $10^{-8}$ (program) | FAIL | §3.2 error $5.0\times10^{-9}$ |
| C6 one `rz` angle shifted by $10^{-13}$ (program; below tolerance) | PASS | error $5.1\times10^{-14}$: the check resolves errors far below the tolerance |
| C7 extra `rz(0.3)` on outer qubit 13; C8 extra `cz(13,14)` (allowed by the scan: diagonal) | FAIL | §3.2 error $0.195$; $2.0$ (wrong phase between sectors) |
| C9 `x(0)` at the end | FAIL | §3.2 error $1.0$, leak weight $1.0$ |
| A1 ancilla left dirty | FAIL | §3.2 ancilla weight $1.0$ |
| A2 valid variant with one clean ancilla (25 qubits) | FAIL | §3.2 passes ($3.7\times10^{-15}$, $n=15$); §3.3 stops at the 24-qubit limit with its message (§5) |

The dynamic blocks alone, with the static scan bypassed on purpose (helpers called directly):

| Circuit | §3.2 (`aer_outer_read_check`) | §3.3 (`aer_full_register_check`) |
|---|---|---|
| W5 `cx(0→13)` at the end | error $1.0$, `outer_weight` $1.0$ | error $0.557$, leak weight $0.310$, probability change $1.4\times10^{-2}$: fails |
| W6 `cx(0→13)`, `h(13)`, `cx(0→13)` | error $1.71$, `outer_weight` $0.5$ | not run |
| W7 `cx(0→20)` at the end (an outer qubit outside the read set) | with read set {13, 14}: refused, "touches an outer qubit outside the read set"; with qubit 20 added to the read set: error $1.0$, `outer_weight` $1.0$ (`w7_reduced.py`) | error $0.557$, leak weight $0.310$, probability change $1.4\times10^{-2}$: fails |
| C1 walk sign | (above) | error $0.120$, leak weight $1.1\times10^{-2}$: fails |
| C5 `rz` + $10^{-8}$ | (above) | error $3.9\times10^{-9}$: fails |
| C6 `rz` + $10^{-13}$ | (above) | error $3.9\times10^{-14}$: passes |
| C7 `rz(0.3)` on outer 13 | (above) | error $0.146$: fails |

Supporting, not part of the test: `full_register_probe.py` (12 seeded states, 2 inside each of the four sectors + 4 over all codes, seed 20261120, production target): errors $\le2.6\times10^{-15}$, probability change $\le4.3\times10^{-16}$, leak 0, at the three pairs. This is consistent with the tester's table in report 445 ($\le2.4\times10^{-15}$, own target and codes, seed 20261121).

Collection: `python -m pytest --collect-only -q --noconftest tests/acceptance` with the amended file in place → `407 tests collected`, no error (the number before the change; the six tests of this file are among them) (the plain command aborts on the lock until §8 step 2 is done; `--noconftest` for collection is the practice of `prompts/004`).

## 8. Steps for the coordinator (in this order)

State of the tree at hand-over: the amended file **is in place** (`tests/acceptance/m8/test_lsh_m8_gate.py`, sha256 `522c1f71…6843`), `LOCK.json` is **not** updated. Until step 2 is done every acceptance run of every track aborts with `ACCEPTANCE LOCK BROKEN`. Do steps 1–2 first.

1. `sha256sum tests/acceptance/m8/test_lsh_m8_gate.py` → `522c1f71eae4864dac683b5b03029a4ecf2323dbd923de1f12b3158f564e6843`.
2. Update the lock. **`python tools/lock.py m8` will refuse** ("m8 is already locked; ask Digonto before changing locked tests"): it only locks new milestones. As in `prompts/201`, `205`, `301`, replace the one entry of `tests/acceptance/LOCK.json` by hand (`tools.check_lock.sha`, written with `json.dumps(lock, indent=1, sort_keys=True) + "\n"`; the file is in that format now, so the diff is one line):
   ```
   python - <<'EOF'
   import json, pathlib
   from tools.check_lock import sha
   lf = pathlib.Path("tests/acceptance/LOCK.json"); lock = json.loads(lf.read_text())
   rel = "tests/acceptance/m8/test_lsh_m8_gate.py"
   assert lock["files"][rel] == "8aa27c35d1aaacf171ddbc28adf46bda55663277b646361d33f85f860717ba15"
   lock["files"][rel] = sha(pathlib.Path(rel))
   assert lock["files"][rel] == "522c1f71eae4864dac683b5b03029a4ecf2323dbd923de1f12b3158f564e6843"
   lf.write_text(json.dumps(lock, indent=1, sort_keys=True) + "\n")
   EOF
   ```
   (run from the project root with `PYTHONPATH=.`). Then `python tools/check_lock.py` → `LOCK OK`.
3. `pytest --collect-only -q tests/acceptance` → 407 tests, no error.
4. `taskset -c 0-7 tools/pytest-safe -n 1 tests/acceptance/m8 -k G2 -m "slow or not slow"` → 1 passed (about 2 min, 1.6 GB).
5. `~/.claude/bin/acceptance-lock "prompts/402-lsh-m8-g2-erratum.md"` → tag `acceptance-v23` (commit: the test file, `LOCK.json`, this file).
6. Reset the counters in STATUS; resume `prompts/401` row 8.10: tester `full` (at least m8 complete, `check_lock`, `acceptance-check`; the other suites were green in report 445 and are untouched), then auditor, benchmark, `milestone-8`.
7. Wording, by the coordinator (the planner was told to edit only this file and the test): `docs/METHODS-lsh.md` L12, sentence on the second engine → "Second engine at the gate (M8-G2, `prompts/402`): Aer statevector. Programs that touch no outer qubit: 47 inner codes on data + ancilla qubits. Programs that read outer qubits as controls: all 433 physical codes on data + ancilla + read outer qubits (operator norm of the $433\times433$ block after one global phase, $\le10^{-10}$) and 10 seeded states on the full 24-qubit register (seed 20261120), at the three spec angle pairs; headline `r05-F3-005`: $\le3.1\times10^{-15}$." Report 8 draft: fill the G2 placeholder with the table of §7.

## 9. Do not retry

- Extending the 47-inner-code shortcut to outer-reading circuits: wrong, the circuit differs between sectors (§1).
- A sampled full-register run as the *only* check: it cannot bound the operator norm; the old check was exhaustive.
- Dense input states on more than 24 qubits: about 3 GB at 25 qubits (§5).
- Calling the evaluator's `_outer_reads` or `_specialise_ops` from the test: the second engine would then share the first engine's logic for outer bits.
- `python tools/lock.py m8` for a re-lock: it refuses by design.

## 10. Risks and stop condition

- A future best or headline (only possible through a replay; the loop is closed) that reads outer qubits **and** has ancillas fails G2 with the 24-qubit message → planner (options then: basis-state inputs prepared with `x` gates, 0.58 GB at 24 and 1.78 GB at 26 qubits, measured in `mem_probe.py`).
- Cost of §3.2 grows with the read set: up to 433 runs of $2^{12+a+|R|}$ amplitudes per pair. Above about 22 qubits this takes minutes to hours. Stop and ask the planner if G2 exceeds 15 min.
- §3.3 holds 1.6 GB for about 2 min. Under `tools/pytest-safe -n 8` with other heavy slow tests in the same slice this is inside the per-test budget (2.2 GB) but adds to the slice total; report 445 (O2) already notes the 11 GB per-job cap.
- A non-unitary instruction (measure, reset) on an outer qubit makes `Operator` raise: the test errors (not a skip). Programs cannot contain these (task specification).
- Stop and ask Digonto if G2 in the amended form fails on `r05-F3-005` at any step of §8, or if any agent thinks a tolerance of §3.4 is wrong.

## 11. For Digonto / the coordinator to note

1. The amended test contains what was approved (full-register Aer on seeded states, §3.3) **plus** an exhaustive check on all 433 states (§3.2) that the planner added (reason: §4, design note). If only §3.3 is wanted, say so; the planner's recommendation is to keep both.
2. The static rule treats "diagonal in the outer qubit" as a read, as the production evaluator does. This is wider than "control position of a `cx`": for example an `rz` on an outer qubit passes the scan and is then judged by the simulation.
3. A circuit that reads outer qubits and has ancillas still returns to the planner (§5). Not relevant for the present headline.
