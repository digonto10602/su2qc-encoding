# Tester report 433 - rishon compression round 6, the last round (prompts/204 C3, prompts/203 row 6.7)

- Date: 2026-11-19
- Git commit: `360d54f` at the end (HEAD while verifying; the round-6 programs are in `7cfe759`; `git diff 7cfe759 360d54f` touches only `notes/STATUS.md`). The round outputs (archive entries `r06-*`, `round-006.json`, feedback, `index.json`, attempts log, discoveries, `robust.json`, regenerated `summary.json`) are uncommitted in the working tree and were verified there; none was changed by me (sha256 before = after, `results/tester/433-sha-before-tests.txt`).
- Prompt in force: `prompts/203-rishon-m6-plan.md` row 6.7 and section 2, with `prompts/204-rishon-det-term-amendment.md` section 6.3 and the headline rule; locked tests `acceptance-v22`.
- Mode: `step`, track R (rishon), tester Claude Sonnet 5.5.
- Related: `reports/tests/432-rishon-round-5.md` (same method; scripts copied with the round-6 ids), `reports/tests/221-m6-round-004-step-6-4b.md`, `reports/tests/428-c3-headline-lean.md` (hash freeze).
- Raw numbers (commit, parameters, seeds inside): `results/tester/433-summary.json` (index), `results/tester/433/433-*.json` and `.log`, scripts `results/tester/433/433-*.py`, `runmut.sh`; mutant programs in `results/tester/433/mutant-programs/` (not collected by pytest). Engine = `results/rishon/tester-217-engine.py` (my sparse simulator, independent of `rishon.verify`).

Environment: conda `coding`, `PYTHONPATH=src`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `taskset -c 0-8`, heavy jobs through `tools/run-capped`, peak far below 11 GB.

## 1. What was asked

Verify the two round-6 programs: F3 `r06-F3-006` (key $(216,832,1350,52)$, parent `r05-F3-005`; new best and headline, robust key $(216,16596,0,26988,52)$, mean $T=829.8$) and F1 `r06-F1-006` (key $(218,840,1358,52)$, parent `r05-F1-005`). Items 1 to 10 of the brief: two independent engines on all 1296 inner codes at three angle pairs, recount of counts, sha256, `synthesis_verification`, robust keys from an empty cache, mutation probes (including the new trick of F3), locked tests, the stop rule, frozen hashes and lock, three-layer preview.

## 2. Commands

```
python results/tester/433/433-static.py                       # own ast walk, sha256 file = archive = round
python results/tester/433/433-archive.py                      # 31 own consistency checks (archive, round, attempts, robust.json)
python results/tester/433/433-sparse.py <cid>                 # own sparse engine: 1296 codes x 3 spec pairs + (2.6,-0.4); skeleton / linearity over 5 pairs
bash   results/tester/433/433-aer-all.sh                      # Aer statevector, all 1296 codes nominal + 80 codes at each alternate pair
python results/tester/433/433-recount.py                      # own lowering (transpile level 0) + hand macro table + own pygridsynth, eps 1e-6 and 1e-10
python results/tester/433/433-synth.py 1e-6                   # Clifford+T circuit with my gridsynth words, my engine, 1296 codes
python results/tester/433/433-prodsynth.py                    # production verify_synthesised (read-only), components
python results/tester/433/433-physical.py                     # 72 own-built physical states, own Gauss generators
python results/tester/433/433-robust.py ; python results/tester/433/433-robust-compare.py   # 20-pair recount (seed 20261107)
python -m su2plaq.rishon.compress.robust headline --root <scratch copy> --refresh            # empty cache, scratch copy only
results/tester/433/runmut.sh <dir> 8                          # production run_candidate --full on 12 hand-made mutants of r06-F3-006 (+ unmutated control)
python results/tester/433/433-gauge-mutants.py <cid>          # every single-gate mutant, my engine, 1296 codes (F3 and F1)
python results/tester/433/433-symdel.py r06-F3-006 <k> 3      # new: mirror-pair deletions (gate j and its mirror N-1-j), 3 shards
python results/tester/433/433-xpairs.py                       # production metrics with the surviving X-X pairs removed
python -m su2plaq.rishon.compress.three_layer --root <scratch copy> --out <scratch>/three-layer-433.json   # info for C5
tools/pytest-safe -n 4 -m "not slow" -rA tests/acceptance/m5 tests/acceptance/m5x tests/acceptance/m6 tests/acceptance/m2c   # taskset 0-3
tools/pytest-safe -n 1 tests/acceptance/m6/test_rishon_m6_gate.py -k G1      # slow test, in addition
tools/pytest-safe -n 4 -q tests/unit
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
```

Targets are my own dense ones (`rishon.algebra` + `scipy.linalg.expm`; $H_E$ off-diagonal 0, $H_B$ Hermitian, $U_B$ unitary to $\sim10^{-15}$). Block error $=\|M-e^{i\varphi}V\|_2$ with $M_{ac}=\langle{\rm code}_a|U|{\rm code}_c\rangle$, ancillas required clean.

## 3. Results (check | expected | got | tolerance | verdict)

### 3.1 Two independent engines, exactness (item 1)

Own sparse engine, 1296 inner codes, spec pairs $(\alpha,\beta)=(0.37,0.61),(0.91,0.23),(1.70,1.00)$ plus $(2.6,-0.4)$:

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| block error F3 `r06-F3-006`, 4 pairs | $\le10^{-10}$ | $1.98,\,2.01,\,2.02,\,1.99\times10^{-14}$ | $10^{-10}$ | PASS |
| block error F1 `r06-F1-006`, 4 pairs | $\le10^{-10}$ | $2.01,\,1.99,\,2.07,\,2.05\times10^{-14}$ | $10^{-10}$ | PASS |
| leak (dirty ancilla / outside code space), all 8 rows | 0 | 0 / 0 | $10^{-10}$ | PASS |
| outer qubits 16..47 touched | none | none (touched 20 qubits = 16 inner + ancillas 48..51 only) | - | PASS |
| global phase $\lvert\varphi\rvert-1$ | 0 | $0$ to $10^{-16}$ | $10^{-10}$ | PASS |
| my triangle-sum pruning bound (nominal) F3 / F1 | $\le10^{-11}$ | $1.27\times10^{-13}$ / $1.24\times10^{-13}$ | $10^{-11}$ | PASS |
| production `dropped_total` (entries, nominal) F3 / F1 | $\le10^{-11}$ (claim $\approx1.2\times10^{-13}$) | $1.212\times10^{-13}$ / $1.200\times10^{-13}$ | $10^{-11}$ | PASS |
| production `op_norm_error` (nominal) F3 / F1 | claim $\approx1.34\times10^{-13}$ | $1.348\times10^{-13}$ / $1.336\times10^{-13}$ (alternates $\le1.39\times10^{-13}$, both `ok`, skeleton equal) | $10^{-10}$ | PASS |
| production Gauss residual (273 states) F3 / F1 | $<10^{-15}$ claim, cap $10^{-10}$ | $7.4\times10^{-16}$ / $8.8\times10^{-16}$ | $10^{-10}$ | PASS |

Aer statevector (double precision; qubits not alive in a code are removed by my liveness analysis, gates on dead qubits must reduce to identity or a diagonal phase, otherwise an error is raised; 17 to 20 qubits per code), `433-aer-summary.json`:

| program | nominal: codes (qubits) | max column error (max-abs / L2) | weight outside code space | alt pairs (0.91,0.23), (1.7,1.0): codes, max-abs error | verdict |
|---|---|---|---|---|---|
| F3 | **1296** (17-20) | $1.18\times10^{-14}$ / $1.19\times10^{-14}$ | $1.1\times10^{-16}$ | 80 / 80: $1.08$ / $1.13\times10^{-14}$ | PASS |
| F1 | **1296** (17-20) | $1.18\times10^{-14}$ / $1.18\times10^{-14}$ | $2.2\times10^{-16}$ | 80 / 80: $1.11$ / $1.15\times10^{-14}$ | PASS |

2592 Aer runs nominal and 320 at the alternate pairs; fitted global phase $1-7.6\times10^{-15}i$, i.e. one phase for the whole circuit; no leaks.

Gauss law on physical states, independent construction (`433-physical.py`): 72 states built from my own end generators and corner kernels (seed 433, random complex combinations, outer register in arbitrary type patterns, norm deviation $4.4\times10^{-16}$, input Gauss residual $5.3\times10^{-16}$). No outer qubit is touched, so the circuit acts as $U_{\rm in}\otimes\mathbb 1_{\rm out}$ and the output is $(M\otimes\mathbb1)\Psi$ with my block $M$:

| quantity (72 states, 3 angle pairs) | expected | got (max over pairs) | tolerance | verdict |
|---|---|---|---|---|
| $\lVert(M\otimes1)\Psi-e^{i\varphi}(V\otimes1)\Psi\rVert$ F3 / F1 | $\le10^{-10}$ | $1.99\times10^{-14}$ / $1.92\times10^{-14}$ | $10^{-10}$ | PASS |
| own Gauss residual of the output state F3 / F1 | $\le10^{-10}$ | $8.6\times10^{-16}$ / $7.5\times10^{-16}$ | $10^{-10}$ | PASS |

### 3.2 Counts recount (item 2), `433-recount.json`

Own lowering ($\{$cx,h,s,sdg,t,tdg,x,z,rz$\}$, `transpile` level 0), CX and T from the lowered list and cross-added from a hand macro table (ccx 6+7, rccx 3+4, ch 1+2, crx 2+2 rz, cz 1), every non-Clifford `rz`/`p` sent to my own `pygridsynth.gridsynth_gates` call at $\varepsilon=10^{-6}$.

| program | CX rec / recount / hand | $T_{10^{-6}}$ rec / recount | $T_{\rm fixed}$ | $N_{\rm rot}$ | depth$_{CT}$ rec / recount | qubits rec / recount | $T_{10^{-10}}$ rec / recount | verdict |
|---|---|---|---|---|---|---|---|---|
| F3 | 216 / 216 / 216 | 832 / 832 | 196 | 10 | 1350 / 1350 | 52 / 52 | 1228 / 1228 | PASS |
| F1 | 218 / 218 / 218 | 840 / 840 | 196 | 10 | 1358 / 1358 | 52 / 52 | 1228 / 1228 | PASS |

All 14 comparisons exact. Against the previous global best `r05-F3-005` $(220,840,1389,53)$: F3 gives CX $220\to216$ ($-1.8\,\%$), $T$ $840\to832$ ($-1.0\,\%$), depth$_{CT}$ $1389\to1350$ ($-2.8\,\%$), qubits $53\to52$; F1 gives $(218,840,1358,52)$, also below the old best but above F3.

### 3.3 Hash, round file, archive (items 3 and 4), `433-static.json`, `433-archive.json`

| check | expected | got | verdict |
|---|---|---|---|
| program sha256: file = archive entry = round JSON = HEAD blob | equal | equal for both (F1 `b4ec4b4d...`, F3 `78c86d8d...`) | PASS |
| imports (own ast walk) | only `math`, `su2plaq.compress.builder` | exactly that; no forbidden name | PASS |
| `round-006.json` `synthesis_verification` (best `r06-F3-006`) | `ok` True | `ok` True, certified, $\varepsilon=10^{-6}$, $N_{\rm rot}=10$, $T=832$, op error $3.0297\times10^{-6}$ against tolerance $1.0001\times10^{-5}$ | PASS |
| my Clifford+T re-verification of F3 (my gridsynth words, my engine, 1296 codes) | within budget $N_{\rm rot}\varepsilon+10^{-9}$ | block $2.5691\times10^{-6}$ + leak (spectral norm) $4.605\times10^{-7}$ $=3.0296\times10^{-6}$ (production $3.0297\times10^{-6}$), ratio to budget 0.257 for the block alone | PASS |
| same for F1 | within budget | $3.5825\times10^{-6}+7.25\times10^{-7}=4.3074\times10^{-6}$ (production $4.3074\times10^{-6}$) | PASS |
| no outer qubit touched in the synthesised circuits | none | none | PASS |
| archive and round consistency (31 own checks: claimed keys, cells $\lfloor8\log_2(\cdot+1)\rfloor$, family, parents exist and valid, `evaluator_sha256` = frozen `5f5decfa...`, spec hash equal to round 5, feedback = entry, all `DISCOVERY:` lines in the discoveries file, `Archive.load(strict)` best and family bests, best = argmin of the key, old entry files byte-identical to HEAD, attempts log = HEAD prefix + 2 lines, discoveries = HEAD prefix + new text, old `robust.json` records unchanged) | 31 / 31 | 31 / 31 | PASS |

### 3.4 Robust keys and angle linearity (item 5), `433-headline-scratch.json`, `433-robust-compare.json`

Scratch copy of `compress/archive/rishon` and `compress/programs/rishon` under a fresh directory (no `robust.json` at all, checked by `find`), `robust headline --root <copy> --refresh`:

| check | expected | got | verdict |
|---|---|---|---|
| headline id and robust key (cx, $\sum T$ over 20 pairs, $\rho$, $\sum$ depth, qubits) | `r06-F3-006`, $(216,16596,0,26988,52)$, $\bar T=829.8$ | `r06-F3-006`, $(216,16596,0,26988,52)$, $\bar T=829.8$; archive best = same | PASS |
| `r06-F1-006` | $(218,16584,0,27002,52)$ (second in the ranking; third `r05-F3-005` $(220,16584,0,27622,53)$) | $(218,16584,0,27002,52)$, $\bar T=829.2$ | PASS |
| committed `robust.json` (23 entries) vs scratch recomputation | identical | 23 / 23 identical | PASS |
| $\rho=0$ (angle-linear) new entries | `angle_linear` True | True for both | PASS |
| my own angle fit: skeleton equal at 5 pairs, 10 rotation parameters (4 `p`, 6 `rz`) homogeneous linear in $(\alpha,\beta)$, no constant parameter | residual $\lesssim10^{-14}$ | residual $\le2.7\times10^{-15}$, intercept $\le1.3\times10^{-15}$, 0 constants | PASS |
| coefficients: $U_E$ angle $-\tfrac34\alpha$; others $\beta(m+n\sqrt2)/d$ | recognisable | F3: $\pm\tfrac12$, $\pm(\sqrt2\cdot2-1)=\pm1.828$, $\pm(\tfrac12+2\sqrt2)=\pm3.328$; F1: $\pm\tfrac12$, $\pm(2\sqrt2-\tfrac12)=\pm2.328$, $\pm(1+2\sqrt2)=\pm3.828$; equal to the production `angle_fit` | PASS |
| my 20-pair recount (own lowering + own gridsynth; seed 20261107) vs production robust record | $T$ and depth lists equal | equal at all 20 pairs for both ($\sum T$ 16596 / 16584, $\sum$ depth 26988 / 27002) | PASS |
| my $T$ statistics, 20 pairs | - | F3 mean 829.8 (nominal 832, min 800, max 844, std 9.8); F1 mean 829.2 (840, 812 to 844, std 8.6) | info |
| any rotation parameter within $10^{-9}$ of a multiple of $\pi/4$ | none | none (nearest F3 0.353, F1 0.027 in units of $\pi/4$) | PASS |

Margin note (not a defect): F1 has the lower robust $\sum T$ (16584 against 16596) and the same mean $T$ within the spread, but the headline order is CX first, so F3 wins on $216<218$.

### 3.5 Mutation probes on `r06-F3-006` (item 6)

(a) Hand-made single mutants of the program text of F3, evaluated by the production `run_candidate --full` (all 1296 codes, three pairs, Gauss sample). Unmutated control: `valid ok`, op error $1.348\times10^{-13}$, Gauss $7.4\times10^{-16}$. Log `433-mutation-probe-fullevaluator.log`.

| mutant | what changes | verdict | op-norm error (block / leak) | Gauss residual |
|---|---|---|---|---|
| N1 | restore `rccx(Z, !q3 -> q13)` becomes plain `CX(Z -> q13)` | invalid `error` | 1.976 | 1.604 |
| N2 | the rccx restore removed entirely | invalid `error` | 1.976 | $7.6\times10^{-16}$ |
| N2b | rccx with the literal $q_3$ instead of $\lnot q_3$ | invalid `error` | 1.976 | 1.604 |
| N3 | closed Walsh coefficient un-negated (the table of the parent) | invalid `error` | 0.608 | $7.7\times10^{-16}$ |
| N3b | $v_c=+4\sqrt2\to-4\sqrt2$ (same table as N3: identical numbers) | invalid `error` | 0.608 | $7.7\times10^{-16}$ |
| N4 | `H(q3)` moved back after the c0 skip (to the old position) | invalid `error` | 1.397 | 0.984 |
| N5 | `T(q13)`, `Tdg(q13)` around the first `CX(Z -> q13)` removed | invalid `error` | 0.430 | $7.2\times10^{-16}$ |
| N6 | `S(q3)` of the merged `CZ(q3,q2)`-gauge removed | invalid `error` | 1.397 | 0.984 |
| N6b | `S`, `Sdg` and gauge replaced by a plain `CX(q3 -> q2)` | invalid `error` | 1.878 | 0.939 |
| N7 | `Z(q8)` gauge of the kappa=1 fold removed | invalid `error` | 1.878 | 0.939 |
| N8 | $U_E$ phase on $g_l$ (q13) removed | invalid `error` | 0.185 | $7.2\times10^{-16}$ |
| N9 | first `T` of the Maslov RC3X removed | invalid `dirty_ancilla` | 0.990 (0.289 / 0.700) | 0.138 |

12 of 12 rejected. Observations on the new trick: the conditional restore is not decorative (plain CX or no restore gives block error 1.98 and breaks Gauss's law by 1.6 in the CX case), the negated rccx literal matters (N2b), the closed Walsh coefficient sign is checked by the block comparison only (error 0.61, Gauss residual stays at $10^{-15}$: a pure coupling-sign fault, as the proposer states), and moving `H(q3)` back kills both the block and Gauss.

(b) Exhaustive battery, my engine, all 1296 codes at the nominal pair, on the compiled macro circuit (`433-gauge-mutants-<cid>.json`): every gate deleted; $t\leftrightarrow t^\dagger$; $s\leftrightarrow s^\dagger$; every `rccx` made an exact Toffoli; every `rz`/`p` angle $+10^{-6}$ and sign-flipped; 12 random `cx` control/target swaps (seed 220). Detected = block error or leak $>10^{-9}$ or engine exception.

| program | mutants | detected | survivors | smallest error among deletions of S/Sdg/T/Tdg/Z | `angle` $+10^{-6}$ min error |
|---|---|---|---|---|---|
| F3 `r06-F3-006` | 578 | 578 | **0** | 0.0761 (a `T`) | $5.0\times10^{-7}$ |
| F1 `r06-F1-006` | 576 | 576 | **0** | 0.0761 | $5.0\times10^{-7}$ |

Baseline errors $2.0\times10^{-14}$. Every deletion of a `cx`, `rccx`, `ch`, `h`, `x` is detected (smallest $0.29$).

(c) Added test (not in the brief): **mirror-pair deletions** on F3, `433-symdel.py`. The circuit is $F\,M\,H\,M^{-1}F'^{-1}$; I align the first half with the reversed second half (difflib on (gate, qubits), inverse names allowed) and delete a gate together with its mirror, 186 pairs. This tests the proposer's claim "no single symmetric gate deletion of the 216-CX circuit stays exact".

| result | got |
|---|---|
| pairs deleted / detected | 186 / 182 |
| non-`x` pairs (`cx` 60, `h` 30, `t`/`tdg` 38, `s`/`sdg` 19, `rccx` 13, `rz` 2, `z` 1, `ch` 1) | 164 / 164 detected, smallest error 0.289 |
| survivors | 4 pairs of `x`: gates (70, 339) on q7, (184, 216) on q12, (143, 266) on q3, (69, 340) on q11, error equal to baseline $2.0\times10^{-14}$ |

The four surviving pairs are cancelling $X\,X$ on a qubit that is not used in between. They cost no CX and no T; removing any one of them leaves the production key unchanged (`433-xpairs.json`: $(216,832,1350,52)$ and depth 275 in every case). So the claim holds for every gate that costs something; the four $X$ pairs are cosmetic redundancy (observation O1, not a defect).

### 3.6 Locked tests (item 7)

`tools/pytest-safe -n 4 -m "not slow" -rA tests/acceptance/m5 m5x m6 m2c` (cores 0-3, 845 s): **103 passed, 1 failed** of 104.

| id | result | reason |
|---|---|---|
| `m6` G6 `test_M6_G6_three_layer_summary` | PENDING (reported as FAILED by pytest) | `results/compress/rishon/three-layer.json missing (prompts/204 step C5)`; expected |
| `m6` L2, L3, L9 | **passed** (expected PENDING) | see note N1: uncommitted Lean (C4) work was in the working tree while the run was in progress |
| `m6` G4 `test_M6_G4_summary_and_budgets` | passed | `summary.json` regenerated by the coordinator: round 5's red is gone |
| `m6` H4, G5, G2, G3, H1, K2, E3, R2, H3 | passed | G2 re-verifies the new best synthesised, G3 the new best touches no outer qubit, H4 headline + det layer |
| slow `M6_G1` (archive best valid and not worse than seed), run separately | passed | 41 s, `results/tester/433/433-pytest-G1.log` |
| m5, m5x, m2c | all pass | no PENDING |

Other gates: `tools/pytest-safe -n 4 -q tests/unit`: **1168 passed, 1 failed** (1079 s); the failure is `tests/unit/test_lean_project_unit.py::test_program_lemma_files` (a Lean `lake env lean` call returned `failed`, `axioms_ok` False); it **passes alone** (12.6 s, rerun by me), so it was a transient failure while a Lean build was running concurrently (N1); not related to round 6. `python tools/check_lock.py`: `LOCK OK`. `~/.claude/bin/acceptance-check`: `PASS: tests/acceptance matches acceptance-v22`. `pytest --collect-only -q tests/acceptance`: 407 tests, clean.

### 3.7 Stop rule and budget (item 8)

| check | expected | got | verdict |
|---|---|---|---|
| round-6 best key below the previous best | $(216,\dots)<(220,\dots)$ | $(216,832,1350,52)<(220,840,1389,53)$, robust $(216,16596,\dots)<(220,16584,\dots)$ by the CX component first; counter of rounds without gain stays 0 | PASS |
| proposer sessions | 20 of 20 | attempts log: 24 lines = 5 round-0 seeds + 19 proposer programs (per round 1 to 6: 4, 4, 3, 3, 3, 2) + 1 ideation session = **20 sessions** | PASS |

**Stop condition met: the 20-proposer-session limit of prompts/203 section 2 ("at 20 proposer sessions (ideation counts)").** The other two conditions are not the reason: $R=8$ is not reached (6 rounds done) and the three-consecutive-rounds-without-gain rule is not triggered (round 6 improved the key). The loop stops after this round.

### 3.8 Frozen hashes and lock (item 9), `results/tester/433-hashes.json`

| hash | frozen (reports/tests/428) | got | verdict |
|---|---|---|---|
| `provenance.code_hash` = twelve | `99663fa6...3e37` | `99663fa6cd2550d9...` equal | PASS |
| lsh | `88e0d76b...c1ca` | equal | PASS |
| spinnet | `10f5727f...e15c` | equal | PASS |
| fuzzy_ub = fuzzy_link | `b4bd20fe...87f9` | equal | PASS |
| rishon (`rishon.compress.code_hash`) | `5f5decfa...ef23` | `5f5decfa34f53069...` equal; same as `round-006.json` | PASS |
| `spinnet.loop.code_hash` | `f1314a01...63d4` | equal | PASS |
| `check_lock.py`, `acceptance-check` | OK | `LOCK OK`, `PASS v22` | PASS |

The hashes were also re-read after the concurrent edits listed in N1 (`round.py`, `lean_cert.py` are in no hash list): unchanged.

### 3.9 Three-layer preview of `r06-F3-006` (item 10, for C5), `433-three-layer-scratch.json`

`three_layer --root <scratch copy>`: `ok` True; unit key $(216,832,1350,52)$, det layer $(32,496,326,48)$, **three-layer key $(248,1328,1676,52)$**, mean $T$ over the 20 $\eta$ values (seed 20261110): unit 829.8, det 500.8, three-layer 1330.6; `op_norm_error` at the three $(\alpha,\beta,\eta)$ triples $1.54,\,1.59,\,1.57\times10^{-13}$; Gauss residual $\le1.1\times10^{-15}$; skeleton equal; outer register untouched. Round 5's headline gave $(252,1336,1715,53)$ and the round-4 best $(260,1342,\dots)$.

### 3.10 Working tree after my runs

The eight round-6 output files are byte-identical before and after (sha256 list `results/tester/433-sha-before-tests.txt`). The unit run rewrote `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json` (provenance only); restored with `git checkout --`. I did not touch `src`, `tests`, `compress/programs`, `lean`.

## 4. Verdict

**PASS** for both round-6 programs. Both are exact on all 1296 inner codes at three angle pairs (my engine $2.0$ to $2.1\times10^{-14}$; Aer $1.1$ to $1.2\times10^{-14}$ over 2592 nominal and 320 alternate-pair runs), global phase 1, ancillas clean, outer register untouched, Gauss residual of the output $\le1.0\times10^{-15}$ on 72 independently built physical states, counts recomputed exactly (14 of 14), the claimed keys and the robust key reproduced from an empty cache, F3 `r06-F3-006` is the new global best and robust headline $(216,16596,0,26988,52)$ with $\rho=0$, the Clifford+T re-verification agrees with production to $2\times10^{-11}$ (error $3.03\times10^{-6}$ against a budget of $1.0\times10^{-5}$), 1154 single-gate mutants of F3 and F1 plus 12 production-evaluator mutants of F3 all rejected (0 survivors), 164 of 164 costly mirror-pair deletions rejected, hashes frozen, lock intact. The 20-proposer-session stop condition is met.

Counts: passed 103 acceptance (not slow) + 1 slow (G1) + 1168 unit + 31 archive checks + all numerical checks above; failed 0 real (the pytest red `M6_G6` is the expected PENDING; one transient unit failure that passes alone); pending 1 (G6; L2, L3, L9 green only because of the concurrent Lean work); new failures against report 432: none (round 5's G4 red is gone).

## 5. Notes

- N1 (action for the coordinator): while this verification ran, another agent (the Lean step C4) was changing the working tree: `src/su2plaq/rishon/lean_cert.py`, `src/su2plaq/rishon/compress/round.py`, `tests/unit/test_rishon_compress_stubs_unit.py`, `tests/unit/test_rishon_lean_cert_unit.py` (new), `lean/lakefile.toml` and new files `lean/Su2PlaqCert/Rishon/{Check3,Gates3,Laurent3,Main,Pins3}.lean`, `lean/certs/rishon-general-step.lean`. These were not in the `git status` at the start. They explain (guess) that `M6_L2`, `L3`, `L9` passed instead of PENDING and the one transient unit failure `test_program_lemma_files` (passes alone). Those files are not part of the round-6 verification and I did not verify them. They are in no hash list; the six frozen hashes are unchanged. Commit the round-6 outputs without them (or verify them separately).
- N2: `r06-F3-006` has `git_dirty` True and `r06-F1-006` False in the entry provenance (programs and outputs were uncommitted at evaluation time for F3; as in rounds 1 to 5, informational).
- N3: the synthesised block error of each program equals that of the round-5 program with the same rotation-coefficient set (F1-006 equals r05-F3-005 to $4\times10^{-16}$: block $3.5825\times10^{-6}$; F3-006 equals r05-F1-005: leak $2.12\times10^{-13}$), as expected: the error of the Clifford+T word depends on the set of rotation angles; the circuits themselves differ (CX 216/218 against 220/226).
- N4: N3 and N3b of the mutant table are the same circuit (identical coefficient table), listed for the two ways the sentence "un-negate the closed Walsh coefficient" can be written.
- N5: the Aer check uses a liveness reduction (dead ancillas removed, gates on dead qubits must reduce to identity or a diagonal phase); it is validated by my sparse engine (which simulates the full 52-qubit circuit) and by agreement of the two engines to $\sim10^{-14}$.
- N6: "no outer qubit touched" plus "Gauss on physical states" uses the spectator argument (the circuit acts as $U_{\rm in}\otimes\mathbb1$); the production Gauss sample (273 states) checks 48-bit keys directly.
- O1: four $X\,X$ pairs in F3 (q3, q7, q11, q12) are cancelling and removable at no cost to the key (CX, $T$, depth$_{CT}$, depth all unchanged); the loop is over, so this is only for the record.
