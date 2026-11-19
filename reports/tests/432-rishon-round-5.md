# Tester report 432 - rishon compression round 5 (prompts/204 C3, prompts/203 row 6.7)

- Date: 2026-11-19
- Git commit: `a155e59` at the end (HEAD when the round outputs were verified; the round-5 programs are in `bef04cd`; `git diff bef04cd a155e59` touches only `notes/STATUS.md`). The round outputs (archive entries `r05-*`, `round-005.json`, feedback, `index.json`, attempts log, discoveries, `robust.json`) are uncommitted in the working tree and were verified there; none of them was changed by me.
- Prompt in force: `prompts/203-rishon-m6-plan.md` row 6.7 and §2, on top of `prompts/204-rishon-det-term-amendment.md` §6.3 and the headline rule (`prompts/203` §13 E3); locked tests `acceptance-v22`.
- Mode: `step`, track R (rishon), tester Claude Sonnet 5.5.
- Related: `reports/tests/221-m6-round-004-step-6-4b.md` (same method, round 4), `reports/tests/220-m6-round-003.md`, `reports/tests/427-c2-rishon-replay.md`, `reports/tests/428-c3-headline-lean.md` (hash freeze).
- Raw numbers (commit, parameters, seeds inside): `results/tester/432-summary.json` (index of everything), `results/tester/432/432-*.json` and `.log`, scripts `results/tester/432/432-*.py` (copies of the tester-221 scripts with the round-5 ids; engine = `results/rishon/tester-217-engine.py`, my own sparse simulator).

Environment: conda `coding`, `PYTHONPATH=src`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `taskset -c 0-8`, heavy jobs through `tools/run-capped`, at most 9 processes, peak well under 11 GB.

## 1. What was asked

Verify the three round-5 programs (F1 `r05-F1-005` key (226, 846, 1386, 52), parent `r04-F1-004`; F3 `r05-F3-005` key (220, 840, 1389, 53), parent `r04-F3-003`, claimed new best and headline, robust key (220, 16584, 0, 27622, 53); F4 `r05-F4-005` key (274, 1186, 1767, 55), parent `r03-F4-003`) per the nine items of the brief: second engine on all 1296 inner codes at three angle pairs, recount of counts, sha256, `synthesis_verification`, robust keys on a scratch copy, a mutation probe on `r05-F3-005`, locked tests, the stop rule, frozen hashes and `check_lock`.

## 2. Commands

```
python results/tester/432/432-static.py                       # own ast walk, sha256 file = archive = round
python results/tester/432/432-sparse.py <cid>                 # own sparse engine: 1296 codes x 3 spec pairs + (2.6,-0.4); skeleton/linearity over 5 pairs
python results/tester/432/432-recount.py                      # own lowering (transpile level 0) + hand macro table + own pygridsynth, eps 1e-6 and 1e-10
python results/tester/432/432-synth.py 1e-6                   # Clifford+T circuit with my gridsynth words, my engine, 1296 codes; leak as spectral norm
python results/tester/432/432-prodsynth.py                    # production verify_synthesised (read-only call), components
bash   results/tester/432/432-aer-all.sh                      # Aer statevector, all 1296 codes nominal + 80 codes at each alternate pair
python results/tester/432/432-physical.py                     # 72 own-built physical states (own Gauss generators), full 48-bit keys, own Gauss residual
python results/tester/432/432-robust.py                       # 20-pair T / depth recount (seed 20261107)
python results/tester/432/432-gauge-mutants.py <cid>          # every single-gate mutant, my engine, 1296 codes (F3 and F1)
python results/tester/432/432-archive.py                      # 39 consistency checks of archive, round file, attempts, robust.json
python -m su2plaq.rishon.compress.robust headline --root <scratch copy> --refresh        # robust keys recomputed from an empty cache
python -m su2plaq.rishon.compress.run_candidate <mutant>.py --full                       # production evaluator on 11 hand-made mutants of r05-F3-005
python -m su2plaq.rishon.compress.three_layer --root <scratch copy> --out <scratch>      # info: three-layer step of the new headline
tools/pytest-safe -n 4 -m "not slow" -rA tests/acceptance/m5 tests/acceptance/m5x tests/acceptance/m6 tests/acceptance/m2c   # taskset 4-7
tools/pytest-safe -n 1 tests/acceptance/m6/test_rishon_m6_gate.py -k G1                  # slow test, run in addition
tools/pytest-safe -n 4 -q tests/unit
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
```

Targets are my own dense ones (`rishon.algebra` + `scipy.linalg.expm`, $H_E$ off-diagonal 0, $H_B$ Hermitian, $U_B$ unitary to $\sim10^{-15}$); block error $=\|M-e^{i\varphi}V\|_2$ with $M_{ac}=\langle{\rm code}_a|U|{\rm code}_c\rangle$, ancillas required clean.

## 3. Results (check | expected | got | tolerance | verdict)

### 3.1 Second engines, exactness (item 1)

Own sparse engine (my simulator, not `rishon.verify`), 1296 inner codes at three spec pairs $(\alpha,\beta)=(0.37,0.61),(0.91,0.23),(1.70,1.00)$ plus $(2.6,-0.4)$:

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| block error F1 `r05-F1-005`, 4 pairs | $\le10^{-10}$ | $2.07,\,2.11,\,2.10,\,2.06\times10^{-14}$ | $10^{-10}$ | PASS |
| block error F3 `r05-F3-005`, 4 pairs | $\le10^{-10}$ | $2.01,\,1.96,\,2.06,\,2.04\times10^{-14}$ | $10^{-10}$ | PASS |
| block error F4 `r05-F4-005`, 4 pairs | $\le10^{-10}$ | $2.63,\,2.63,\,2.67,\,2.59\times10^{-14}$ | $10^{-10}$ | PASS |
| leak (dirty ancilla / outside code space) all 12 rows | 0 | 0 / 0 | $10^{-10}$ | PASS |
| outer qubits 16..47 touched, all 12 rows | none | none (touched: 20 / 21 / 23 qubits = 16 + 4 / 5 / 7 ancillas) | - | PASS |
| global phase $\lvert\varphi\rvert-1$ | 0 | $\le1.1\times10^{-16}$ | $10^{-10}$ | PASS |
| my triangle-sum pruning bound (nominal) F1 / F3 / F4 | $\le10^{-11}$ | $1.34\times10^{-13}$ / $1.27\times10^{-13}$ / $1.63\times10^{-13}$ | $10^{-11}$ | PASS |

Aer statevector (double precision; qubits not alive in a code are removed by my liveness analysis, gates on dead qubits must reduce to identity or a diagonal phase, otherwise an error is raised; every code needs only 16 to 23 qubits), `results/tester/432/432-aer-summary.json`:

| program | nominal: codes (qubits) | max column error (max-abs / L2) | weight outside code space | alt pairs (0.91,0.23) and (1.7,1.0): codes, max-abs error | verdict |
|---|---|---|---|---|---|
| F1 | **1296** (17-20) | $1.20\times10^{-14}$ / $1.20\times10^{-14}$ | $2.2\times10^{-16}$ | 80 / 80: $1.11$ / $1.15\times10^{-14}$ | PASS |
| F3 | **1296** (16-21) | $1.07\times10^{-14}$ / $1.13\times10^{-14}$ | $1.1\times10^{-16}$ | 80 / 80: $1.04$ / $1.06\times10^{-14}$ | PASS |
| F4 | **1296** (17-23) | $1.57\times10^{-14}$ / $1.61\times10^{-14}$ | $2.2\times10^{-16}$ | 80 / 80: $1.41$ / $1.50\times10^{-14}$ | PASS |

3888 Aer runs at the nominal pair (all codes of all three programs; this time every code of F4 fits, there is no 25-qubit remainder as in round 3) and 480 at the alternate pairs; fitted global phase $1-(7.5\text{ to }8.3)\times10^{-15}i$, i.e. one phase for the whole circuit.

Gauss law on physical states with an independent construction (`432-physical.py`): 72 physical states built from my own end generators and corner kernels (seed 432, random complex combinations, outer register in arbitrary type patterns, norm deviation $4\times10^{-16}$, input Gauss residual $4.8\times10^{-16}$). Because no outer qubit is touched (checked above) the circuit acts as $U_{\rm in}\otimes\mathbb 1_{\rm out}$ and the output is $(M\otimes\mathbb1)\Psi$ with my engine's block $M$:

| quantity (72 states, 3 angle pairs per program) | expected | got (max over pairs) | tolerance | verdict |
|---|---|---|---|---|
| $\lVert(M\otimes1)\Psi-e^{i\varphi}(V\otimes1)\Psi\rVert$ F1 / F3 / F4 | $\le10^{-10}$ | $1.95\times10^{-14}$ / $1.90\times10^{-14}$ / $2.64\times10^{-14}$ | $10^{-10}$ | PASS |
| own Gauss residual of the output state F1 / F3 / F4 | $\le10^{-10}$ | $7.8\times10^{-16}$ / $7.3\times10^{-16}$ / $1.01\times10^{-15}$ | $10^{-10}$ | PASS |
| production Gauss residual (273 states, in the entries) | $\le10^{-10}$ | F1 $7.6$, F3 $8.3$, F4 $8.9\times10^{-16}$ nominal; alternates $\le1.06\times10^{-15}$ | $10^{-10}$ | PASS |

Production evaluator numbers for the same programs (entries, nominal): `op_norm_error` F1 $1.42\times10^{-13}$, F3 $1.36\times10^{-13}$, F4 $1.68\times10^{-13}$ (proposer claim $1.4$ to $1.7\times10^{-13}$), `dropped_total` $1.28$, $1.22$, $1.53\times10^{-13}$ (claim $1.2$ to $1.5\times10^{-13}$, cap $10^{-11}$), all `certified`, engine `sparse`, both alternate pairs `ok` with equal skeleton.

### 3.2 Counts recount (item 2), `432-recount.json`

Own lowering ($\{$cx,h,s,sdg,t,tdg,x,z,rz$\}$, `transpile` level 0), CX and T from the lowered list, cross-added from a hand macro table (ccx 6+7, rccx 3+4, ch 1+2, crx 2+2 rz, cz 1), every non-Clifford `rz`/`p` sent to my own `pygridsynth.gridsynth_gates` call at $\varepsilon=10^{-6}$.

| program | CX rec / recount / hand | $T_{10^{-6}}$ rec / recount | $T_{\rm fixed}$ | $N_{\rm rot}$ | depth$_{CT}$ rec / recount | qubits rec / recount | $T_{10^{-10}}$ rec / recount | verdict |
|---|---|---|---|---|---|---|---|---|
| F1 | 226 / 226 / 226 | 846 / 846 | 210 | 10 | 1386 / 1386 | 52 / 52 | 1242 / 1242 | PASS |
| F3 | 220 / 220 / 220 | 840 / 840 | 196 | 10 | 1389 / 1389 | 53 / 53 | 1228 / 1228 | PASS |
| F4 | 274 / 274 / 274 | 1186 / 1186 | 282 | 14 | 1767 / 1767 | 55 / 55 | 1718 / 1718 | PASS |

All 21 comparisons exact. Against the previous global best $r04$-F1-004 $(228,846,1417,53)$: F3 gives CX $228\to220$ ($-3.5\,\%$), $T$ $846\to840$ ($-0.7\,\%$), depth$_{CT}$ $1417\to1389$ ($-2.0\,\%$), qubits unchanged; F1 gives $(226,846,1386,52)$, also lexicographically below the old best but above F3.

### 3.3 Hash, round file, archive (items 3, 4), `432-static.json`, `432-archive.json`

| check | expected | got | verdict |
|---|---|---|---|
| program sha256: file = archive entry = round JSON = `git HEAD` blob, three programs | equal | equal for all three (F1 `fddee9b3...`, F3 `0f30af2b...`, F4 `0ad5dfa3...`) | PASS |
| imports (own ast walk) | only `math`, `su2plaq.compress.builder` | exactly that; no forbidden name | PASS |
| `round-005.json` `synthesis_verification` (best `r05-F3-005`) | `ok` True | `ok` True, certified, $\varepsilon=10^{-6}$, $N_{\rm rot}=10$, $T=840$, op error $4.3246\times10^{-6}$ against tolerance $1.0001\times10^{-5}$ | PASS |
| my Clifford+T re-verification (my gridsynth words, my engine, 1296 codes) F3 | within budget $N_{\rm rot}\varepsilon+10^{-9}$ | block $3.5825\times10^{-6}$ + leak (spectral norm) $7.42\times10^{-7}$ = $4.3246\times10^{-6}$ (production $4.3246\times10^{-6}$), ratio to budget 0.358 (block alone) | PASS |
| same for F1 / F4 | within budget | F1 $3.0051\times10^{-6}$ (prod $3.0051\times10^{-6}$), budget $1.0001\times10^{-5}$; F4 $5.2055\times10^{-6}$ (prod $5.2055\times10^{-6}$), budget $1.4001\times10^{-5}$ | PASS |
| no outer qubit touched in the synthesised circuits | none | none | PASS |
| archive and round consistency (39 own checks: keys, cells $\lfloor8\log_2(\cdot+1)\rfloor$, families, parents exist and valid, `evaluator_sha256` = frozen `5f5decfa...`, spec hash unchanged, feedback = entry, all `DISCOVERY:` lines in the discoveries file, `Archive.load(strict)` best and family bests, best = argmin of key, old entry files byte-identical to HEAD, attempts log = HEAD prefix + 3 lines, discoveries = HEAD prefix + new text, old `robust.json` records unchanged) | 39 / 39 | 39 / 39 | PASS |

### 3.4 Robust keys and angle linearity (item 5), `432-headline-scratch.json`, `432-robust*.json`

Scratch copy of the archive and programs (`root/compress/{archive,programs}`, empty `robust.json`), `robust headline --root <copy> --refresh` (21 entries recomputed from nothing):

| check | expected | got | verdict |
|---|---|---|---|
| headline id and robust key (cx, $T$ sum over 20 pairs, $\rho$, depth sum, qubits) | `r05-F3-005`, (220, 16584, 0, 27622, 53) | `r05-F3-005`, (220, 16584, 0, 27622, 53), $\bar T=829.2$ | PASS |
| `r05-F1-005` | (226, 16876, 0, 27708, 52) | (226, 16876, 0, 27708, 52) | PASS |
| `r05-F4-005` | (274, 23392, 0, 34574, 55) (claim: not stated) | (274, 23392, 0, 34574, 55) | info |
| old best `r04-F1-004` | (228, 16876, 0, 28328, 53) | same (ranks 3rd with its twin `r04-F3-003`) | PASS |
| committed `robust.json` entries (21) vs scratch recomputation | identical | 21 / 21 identical, `evaluator_sha256` current | PASS |
| $\rho=0$ (angle-linear) for the new entries | `angle_linear` True | True for all three | PASS |
| my own angle fit: skeleton equal at 5 pairs, all rotation parameters (4 `p`, 6 or 10 `rz`) homogeneous linear in $(\alpha,\beta)$, no constant parameter | residual $\lesssim10^{-14}$ | residual $\le2.7\times10^{-15}$, intercept $\le1.4\times10^{-15}$, 0 constants | PASS |
| coefficients: $U_E$ angles $-\tfrac34\alpha$; others $\beta(m_\beta+m_\gamma\sqrt2)/d$ | recognisable | brute-force decomposition found for every coefficient with $d\le2$ (F3: $\pm(1+2\sqrt2)$, $\pm(-\tfrac12+2\sqrt2)$, $\pm\tfrac12$; F1: $\pm(\tfrac12+2\sqrt2)$, $\pm(2\sqrt2-1)$, $\pm\tfrac12$; F4: $\pm(1+\sqrt2)$, $\pm\sqrt2$, $\pm(\sqrt2-\tfrac12)$, $\pm\tfrac12$), equal to the production `angle_fit` | PASS |
| my 20-pair recount (own lowering + own gridsynth; seed 20261107, same pairs as the locked set) vs production robust record | $T$ and depth list equal | equal at all 20 pairs for all three programs ($\sum T$ 16876 / 16584 / 23392, $\sum$ depth 27708 / 27622 / 34574) | PASS |
| my $T$ statistics, $\varepsilon=10^{-6}$, 20 pairs (nominal) | - | F3 mean 829.2 (nominal 840, min 812, max 844, std 8.6); F1 843.8 (846, 814-858, std 9.8); F4 1169.6 (1186, 1142-1194, std 15.0) | info |
| any rotation parameter within $10^{-9}$ of a multiple of $\pi/4$ (the $\pm\pi/4$ trick) | none | none (nearest: F3 0.027, F1 0.35, F4 0.098 in units of $\pi/4$) | PASS |

Margin note (not a defect): F3's nominal $T=840$ is $1.3\,\%$ above its 20-pair mean 829.2; the CX count (220 against 226) decides the headline first, so the ranking does not depend on this.

### 3.5 Mutation probe on `r05-F3-005` (item 6)

(a) Hand-made single mutants of the program text, evaluated with the production `run_candidate --full` (all 1296 codes, three pairs, Gauss sample). Unmutated control: `valid ok`, op error $1.36\times10^{-13}$, Gauss $8.3\times10^{-16}$. Log: `results/tester/432/432-mutation-probe-fullevaluator.log`, programs `results/tester/432/mutant-programs/`.

| mutant | what changes | verdict | op-norm error (block / leak) | Gauss residual |
|---|---|---|---|---|
| M1 drop the CS fix pair | `T(q13)` and `Tdg(q13)` around the first `CX(Z->q13)` removed (forward and inverse copies) | invalid `error` | 0.430 (0.430 / 0) | $7.9\times10^{-16}$ |
| M1b drop `T` only | | invalid `error` | 0.719 | $7.9\times10^{-16}$ |
| M1c drop `Tdg` only | | invalid `error` | 0.719 | $7.1\times10^{-16}$ |
| M1d swap `T`, `Tdg` | | invalid `error` | 0.608 | $8.0\times10^{-16}$ |
| M2 closed Walsh sign flipped | $v_c=+4\sqrt2\to-4\sqrt2$ | invalid `error` | 0.608 | $7.6\times10^{-16}$ |
| M2b closed Walsh coefficient negated | `Z`-term $(v_c-1)/2\to-(v_c-1)/2$ | invalid `error` | 1.977 | $8.3\times10^{-16}$ |
| M3a drop first `CX(Z->q13)` | | invalid `leak` | 2.984 (1.984 / 0.9997) | 0.807 |
| M3b drop second `CX(Z->q13)` | | invalid `leak` | 2.280 (1.976 / 0.304) | 1.604 |
| M4 drop the closed-dark `rccx(Z, q3 -> e1c0)` | | invalid `error` | 1.976 | 1.604 |
| M5 drop the `CZ(q3,q4)` Margolus gauge | | invalid `error` | 1.878 | 0.939 |
| M6 drop the `Z(e1c3)` gauge | | invalid `error` | 1.878 | 0.939 |

11 of 11 rejected by the full evaluator. The T/Tdg pair is not decorative: without it the closed-sector coupling turns imaginary on the loop sector (block error 0.43 to 0.72, Gauss residual still $\sim10^{-15}$, i.e. the fault is a pure phase/coupling error that only the exact block comparison sees), which is what the proposer's claim states. The two `CX(Z->q13)` deletions break Gauss's law (0.81, 1.60) and leak amplitude (1.0, 0.30), so the toggling pair is what keeps the c0 corner Hadamard off the closed sector.

(b) Exhaustive battery, my engine, all 1296 codes at the nominal pair, on the compiled macro circuit (`432-gauge-mutants-<cid>.json`): every gate deleted; $t\leftrightarrow t^\dagger$; $s\leftrightarrow s^\dagger$; every `rccx` made an exact Toffoli; every `rz`/`p` angle $+10^{-6}$ and sign-flipped; 12 random `cx` control/target swaps (seed 220). Detected means block error or leak $>10^{-9}$ or engine exception.

| program | mutants | detected | survivors | smallest error among deletions of S/Sdg/T/Tdg/Z/CZ | `angle` $+10^{-6}$ min error |
|---|---|---|---|---|---|
| F3 `r05-F3-005` | 522 | 522 | **0** | 0.0761 (a `T`) | $5.0\times10^{-7}$ |
| F1 `r05-F1-005` | 590 | 590 | **0** | 0.0761 | $5.0\times10^{-7}$ |

Named gates of F3: the four `CX(52,13)` (gate indices 120, 138, 233, 251; ancilla 52 = $Z$) each give block error 1.000 and leak 1.000; the T/Tdg pairs on qubit 13 (gates 119/121 and 250/252): 0.524 / 0.405 / 0.405 / 0.524; the `CZ(q3,q4)` gauge and both `Z` gates: 2.00. Baseline $2.0\times10^{-14}$. Result: PASS.

### 3.6 Locked tests (item 7)

`tools/pytest-safe -n 4 -m "not slow" -rA tests/acceptance/m5 m5x m6 m2c` (cores 4-7, 802 s): **99 passed, 5 failed** of 104 (slow ones deselected).

| id | result | reason |
|---|---|---|
| `m6` L2 `test_M6_L2_cert3_builds_and_semantics` | PENDING | `lean/Su2PlaqCert/Rishon/Laurent3.lean missing (step 6.L2)` (expected) |
| `m6` L3 `test_M6_L3_cert3_accept_reject_na` | PENDING | `Laurent3.lean missing (step 6.L2)` (expected) |
| `m6` L9 `test_M6_L9_det_layer_certificate` | PENDING | `lean_cert has no attribute recognise_angle_single` (expected) |
| `m6` G6 `test_M6_G6_three_layer_summary` | PENDING | `results/compress/rishon/three-layer.json missing (prompts/204 step C5)` (expected) |
| `m6` **G4** `test_M6_G4_summary_and_budgets` | **FAIL (real assertion, not PENDING)** | `assert summary["global_best"] == best.id`: `results/compress/rishon/summary.json` is the committed file from `9a98bbf` and still names `r04-F1-004` (228, 846, 1417, 53); the archive best is now `r05-F3-005`. The round command does not rewrite `summary.json` |

Behaviour of the tests tied to the old best: `M6_H4` (headline + det layer = three-layer step at the three triples) **passes** with the new headline; `M6_G5` (replay record, uses `replay-204.json`) **passes**; `M6_H1`, `M6_G2` (best synthesised re-verified), `M6_G3` (best touches no outer qubit), `M6_K2`, `M6_E3`, `M6_R2`, `M6_H3` pass; the slow `M6_G1` (archive best valid and not worse than seed), run by me separately, **passes** (26.6 s). m5, m5x, m2c: all pass, no PENDING. `m6` `three_layer`/`G4` are the only ones that look at the best/headline and summary.

Verified that G4 is only stale state: on a scratch copy of the archive (programs, round 0-5 files, attempts, discoveries, ideation; no `summary.json`), `report_table('rishon','step', root=copy)` writes a `summary.json` with `global_best` `r05-F3-005` (220, 840, 1389, 53) and `headline` `r05-F3-005` (220, 16584, 0, 27622, 53); calling the locked test function `test_M6_G4_summary_and_budgets(root=copy)` then **passes**. So the coordinator only has to regenerate `results/compress/rishon/summary.json` (e.g. `python -m su2plaq.rishon.compress.robust report`, or the `report_table` call used by the round tooling) before the commit; I did not touch the tracked file. Information for C5: `three_layer --root <copy>` on the new headline gives `ok` True, unit key (220, 840, 1389, 53), det layer (32, 496, 326, 48), three-layer key **(252, 1336, 1715, 53)** with `op_norm_error` $1.54$, $1.60$, $1.60\times10^{-13}$ at the three $(\alpha,\beta,\eta)$ triples (`432-three-layer-scratch.json`; the old best gave 260 CX, 1342 T).

Other gates: `tools/pytest-safe -n 4 -q tests/unit`: **1155 passed**, 545 s. `python tools/check_lock.py`: `LOCK OK`. `~/.claude/bin/acceptance-check`: `PASS: tests/acceptance matches acceptance-v22`. `pytest --collect-only -q tests/acceptance`: 407 tests, clean.

### 3.7 Stop rule and budget (item 8)

| check | expected | got | verdict |
|---|---|---|---|
| round-5 best key below the previous best key | $(220,\dots)<(228,\dots)$ | $(220,840,1389,53)<(228,846,1417,53)$; robust key $(220,16584,\dots)<(228,16876,\dots)$ | PASS (counter stays 0) |
| proposer sessions | 18 of 20 | attempts log: 22 lines = 5 round-0 seeds + 17 proposer programs + the ideation session (`compress/ideation/rishon.md`, 1) = 18 sessions | PASS |

(Per round in the log: round 0: 5, round 1: 4, round 2: 4, round 3: 3, round 4: 3, round 5: 3; sessions = 4+4+3+3+3 = 17 proposers + 1 ideation = 18.) `MAX_ROUNDS` 8: round 5 is the 5th round after round 0; the non-seed program files number 17 $\le20$ (G4's own budget assertions pass in the scratch run).

### 3.8 Frozen hashes and lock (item 9), `432-hashes.json`

| hash | frozen (reports/tests/428) | got | verdict |
|---|---|---|---|
| `provenance.code_hash` = twelve | `99663fa6...3e37` | `99663fa6cd2550d9...2b3e37` equal | PASS |
| lsh | `88e0d76b...c1ca` | equal | PASS |
| spinnet | `10f5727f...e15c` | equal | PASS |
| fuzzy_ub = fuzzy_link | `b4bd20fe...87f9` | equal | PASS |
| rishon (`rishon.compress.code_hash`) | `5f5decfa...ef23` | `5f5decfa34f53069...531324ef23` equal; same as `round-005.json` | PASS |
| `spinnet.loop.code_hash` | `f1314a01...63d4` | equal | PASS |
| `check_lock.py`, `acceptance-check` | OK | `LOCK OK`, `PASS v22` | PASS |

### 3.9 Working tree after my runs

`git status` outside `results/tester/432*`: exactly the round-5 outputs listed in the brief, same bytes (sha256 of `index.json`, `robust.json`, `round-005.json` before and after the tests equal). The unit run rewrote `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json` (provenance only); restored with `git checkout --`. No `summary.json`, no `tc_opts.pkl`, nothing under `src`, `tests`, `compress/programs`. My scratch copy and mutant programs live under the session scratchpad; copies of the 11 mutants are in `results/tester/432/mutant-programs/` (not collected by pytest).

## 4. Verdict

**PASS** for the three round-5 programs. All are exact on all 1296 inner codes at three angle pairs (my engine $2.0$ to $2.7\times10^{-14}$; Aer $1.1$ to $1.6\times10^{-14}$ over 3888 nominal and 480 alternate-pair runs, complete code coverage for all three), global phase 1, ancillas clean, outer register untouched, Gauss residual of the output $\le1.0\times10^{-15}$ on 72 independently built physical states, counts recomputed exactly (21 of 21), the claimed keys and robust key reproduced, F3 `r05-F3-005` is the new global best and the robust headline (220, 16584, 0, 27622, 53) with $\rho=0$, the Clifford+T re-verification agrees with production to $\lesssim10^{-14}$ (error $4.32\times10^{-6}$ against a budget of $1.0\times10^{-5}$), 1112 single-gate mutants of F3 and F1 plus 11 production-evaluator mutants of F3 all rejected (0 survivors), hashes frozen, lock intact.

Counts: passed 99 acceptance (not slow) + 1 slow (G1) + 1155 unit + 39 archive checks + all numerical checks above; failed 1 (G4, stale `summary.json`, see below); pending 4 (L2, L3, L9, G6, all expected); new failures against the last rishon round report (221): G4 is new (it passed with the old best; cause is not a bug in the programs).

## 5. Notes

- N1 (action for the coordinator, blocks the next green m6 run, not the programs): regenerate `results/compress/rishon/summary.json` after round 5 (it still names `r04-F1-004`). I verified on a scratch copy that the regenerated file names `r05-F3-005` and that G4 then passes. Guess: the `round` CLI writes `summary.json` only in the report step, which was not run after round 5.
- N2: `r04-F1-004` and `r04-F3-003` had identical keys and robust keys (twin circuits, report 221); the new F1/F3 programs are different circuits (CX 226 vs 220).
- N3: `git_dirty` is true in the round-5 entries' provenance (programs and outputs uncommitted at evaluation time), as in rounds 1 to 4.
- N4: F4 `r05-F4-005` $(274,1186,1767,55)$ is valid but not competitive (CX 274 against 220); it improves its family best (292 CX in round 4 $\to$ 274).
- N5: the Aer check uses a liveness reduction (dead ancillas removed, gates on dead qubits must reduce to identity or a diagonal phase); the unreduced 53-qubit circuits cannot be simulated densely. The reduction is validated by my sparse engine (which simulates the full circuit) and by agreement of the two engines to $\sim10^{-14}$.
- N6: the "no outer qubit touched" and "Gauss on physical states" arguments for full states use the spectator argument (the circuit acts as $U_{\rm in}\otimes\mathbb1$); the production Gauss sample (273 states) is the direct check on 48-bit keys.
