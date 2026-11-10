# Tester report 221 - M6 round 4 (kind `step`) second-engine verification and step 6.4b (robust headline rule)

- Date: 2026-11-10 (run interrupted once by a machine crash at 13:49, resumed 14:10; see section 6)
- Git commit: `f4c0c70` at the end of the run (`d744c0a` at the start; the commits in between are spinnet round 4, acceptance-v15 for m9 S1 and `tools/pytest-safe`; `git diff d744c0a HEAD -- src tests/unit tests/acceptance/m6 compress/archive/rishon results/compress/rishon` is empty, so every rishon number below is valid at HEAD). The recorded `commit` fields inside some JSON files (`bf3799a`, `8822b0b`) are the HEAD at the time the script ran.
- Evaluated commits: round 4 `68b8b76` (proposals + evaluation `8cc2940`), step 6.4b built in `1783d38` (never tester-verified before this report).
- Prompt in force: `prompts/203-rishon-m6-plan.md` (rows 6.4b / 6.7, section 13 errata E1-E3). Locked tests: acceptance-v15 (`acceptance-check`: `PASS: tests/acceptance matches acceptance-v15`; `tools/check_lock.py`: `LOCK OK`; `pytest --collect-only -q tests/acceptance`: 255 tests, clean).
- Mode: `step`, track R (rishon), tester Claude Sonnet 5.5, cores 6-13, all heavy jobs under `tools/run-capped` / `tools/pytest-safe`.
- Related: `reports/tests/220-m6-round-003.md` (template and method), 219, 218, 217.
- Raw numbers (commit, parameters, seeds inside): `results/rishon/tester-221-*.json`, `-aer-*.npz`, logs `*.log`, `*.time` (my `tester-221-timed.py` wrapper: wall time and peak RSS; `/usr/bin/time` does not exist on this machine); scripts `results/rishon/tester-221-*.py` (copies of the 220 scripts with the round-4 ids, plus the new `-rank`, `-rank-aggregate`, `-recognise`, `-alias`, `-cache`, `-samecircuit`, `-f4-claims`, `-f4-depth`).

## 1. What was asked

(1) Verify the round-4 entries `r04-F1-004` (F1), `r04-F3-003` (F3), `r04-F4-004` (F4) with my own engine on all 1296 inner codes (the full rishon physical basis of the encoded block; the outer register is untouched, section 3.1), re-derive counts and $T(10^{-6})$, check ranking / headline, the F1/F3 identical-circuit claim and the F4 floor claim. (2) Verify step 6.4b: acceptance ids H1, H2 (slow), K0-K3, E1-E3, S1, S2, R1, R2, L1, L8, G1-G4 (G4 after `python -m su2plaq.rishon.compress.robust report`), L2/L3/L7 expected PENDING (Lean 6.L2); independent sum-$T$ over the 20 seeded pairs, $\rho$ (three-variable angle-linearity) fit, ranking, cache checks. (3) Judge the two builder flags. (4) Rishon unit tests. (5) List what the pending amendments (gamma $\neq0$ layer, prune cap 10 %) would invalidate. Neither amendment was applied; everything is verified at gamma $=0$ as committed.

## 2. Method and commands

```
source ~/miniforge3/etc/profile.d/conda.sh && conda activate coding ; export OMP/OPENBLAS/MKL_NUM_THREADS=1 PYTHONPATH=src
python -m su2plaq.rishon.compress.robust report   (tools/run-capped, taskset -c 9)     # needed by G4; writes results/compress/rishon/summary.json
python results/rishon/tester-221-static.py ; ...-samecircuit.py ; ...-recount.py ; ...-sparse.py <cid>     # own ast walk, same-circuit, recount, own sparse engine
python results/rishon/tester-221-rank.py <ids> ; ...-rank-aggregate.py     # own robust key of ALL 16 valid entries vs production cache and headline()
python results/rishon/tester-221-recognise.py ; ...-alias.py ; ...-cache.py <scratch>    # recognise_angle audit, 2-decimal alias, cache behaviour (tmp root)
python results/rishon/tester-221-archive.py    # 77 consistency checks
python results/rishon/tester-221-synth.py 1e-6 ; ...-prodsynth.py   # Clifford+T re-verification (own gridsynth words) and production verify_synthesised
bash results/rishon/tester-221-aer-all.sh, -aer-f1-alt.sh, -aer-f4-rest.sh ; python ...-aggregate.py   # Aer statevector with liveness reduction
python results/rishon/tester-221-gauge-mutants.py <cid>   # exhaustive single-gate mutants, all 1296 codes
tools/pytest-safe -n 4 -q -rA -m "not slow" tests/acceptance/m6 ;  tools/pytest-safe -n 3 -q -rA -m slow -k "H2 or G1 or L7 or S3" tests/acceptance/m6
tools/pytest-safe -n 4 -q tests/unit/<12 compress/lean files> ;  tools/pytest-safe -n 2 -q tests/unit/<12 other rishon files>
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
```
Targets, block error, leak, Aer reduction exactly as in report 219 section 2 (independent dense targets from `rishon.algebra` + `scipy.linalg.expm`; block error $=\|M-e^{i\varphi}V\|_2$, $M_{ac}=\langle{\rm code}_a|U|{\rm code}_c\rangle$, ancillas required clean).

## 3. Results

### 3.1 Own sparse engine, 1296 codes x 4 angle pairs (`tester-221-sparse-<cid>.json`)

| program | key (CX, T, depth, qubits) | block error at (0.37,0.61) / (0.91,0.23) / (1.7,1.0) / (2.6,-0.4) | leak | ancillas touched | outer qubits touched | max stored amplitudes | my pruning bound (triangle) |
|---|---|---|---|---|---|---|---|
| F1 `r04-F1-004` | 228, 846, 1417, 53 | 2.09 / 2.04 / 2.09 / 2.06 $\times10^{-14}$ | 0 | 5 | none | 37 976 | $1.31$-$1.37\times10^{-13}$ |
| F3 `r04-F3-003` | 228, 846, 1417, 53 | 2.09 / 2.04 / 2.09 / 2.06 $\times10^{-14}$ | 0 | 5 | none | 37 976 | $1.31$-$1.37\times10^{-13}$ |
| F4 `r04-F4-004` | 292, 1210, 1766, 62 | 2.82 / 2.80 / 2.91 / 2.81 $\times10^{-14}$ | 0 | 14 | none | 22 700 | $1.67$-$1.77\times10^{-13}$ |

Global phase $|\varphi|-1=0$ to $10^{-16}$; skeleton identical over 5 pairs; 10 (F1, F3) / 14 (F4) rotation parameters exactly linear and homogeneous in $(\alpha,\beta)$ (least-squares residual $\le1.3\times10^{-15}$, intercept $\le6.7\times10^{-16}$, no constant parameter); F1/F3 coefficients $\{-0.75\alpha\}\cup\{\pm0.5,\pm1.828,\pm3.328\}\beta$. All pruning bounds are $\ge5.6\times$ below the cap $10^{-12}$. 22 to 44 s per program (4 pairs), 0.77 GB peak. All 1296 inner codes valid for all three: the outer register (qubits 16-47) is untouched and the leak is 0, so the circuit acts as $U_{\rm block}\otimes\mathbb 1$ with $\|U_{\rm block}-V\|\le3\times10^{-14}$ and $V$ commutes with the Gauss generators (same argument as reports 218-220; I did not recompute Gauss on physical outer states).

### 3.2 Aer statevector (double precision) (`tester-221-aer-summary.json`)

| program | pair | codes (qubits) | max column error | outside weight | phase |
|---|---|---|---|---|---|
| F1 | nominal (0.37,0.61) | **1296** of 1296 (16-21 q) | $1.11\times10^{-14}$ | $1.1\times10^{-16}$ | $1-7.9\times10^{-15}i$ |
| F1 | (0.91,0.23) / (1.7,1.0) | 80 / 80 | $1.04$ / $1.03\times10^{-14}$ | 0 | $1-8.1\times10^{-15}i$ |
| F4 | nominal | 472 (21-24 q) of 1296 | $1.57\times10^{-14}$ | 0 | $1-7.8\times10^{-15}i$ |
| F4 | (0.91,0.23) / (1.7,1.0) | 80 / 80 | $1.33$ / $1.38\times10^{-14}$ | 0 | $1-8.0\times10^{-15}i$ |
| F4 | 25-26 q class | 8 sampled | $1.59\times10^{-14}$ | 0 | $1-8.2\times10^{-15}i$ |

F3-003 was not run through Aer separately: its gate list is identical to F1-004 (section 3.4), so the Aer result is the same circuit. 1296 + 160 + 472 + 160 + 8 = 2096 Aer runs, about 7500 CPU-s. F4: the 824 codes needing 25 to 30 qubits (above the 10 GB limit) are covered only by my sparse engine (mutation-checked, section 3.5) plus the 8 sampled 25-26 qubit runs (same limitation as N5/N6 of 219/220).

### 3.3 Keys recomputed independently (`tester-221-recount.json`)

Own lowering ($\{$cx,h,s,sdg,t,tdg,x,z,rz$\}$, `transpile` level 0), CX and T counted from the lowered list and cross-added from a hand macro table (ccx 6+7, rccx 3+4, ch 1+2, crx 2 CX + 2 rz, cz 1, cp 2 CX + 3 phase gates), every non-Clifford `rz`/`p` sent to my own `pygridsynth.gridsynth_gates` call.

| program | CX rec / recount / hand | $T_{10^{-6}}$ rec / recount | depth$_{CT}$ rec / recount | qubits | $N_{\rm rot}$ | $T_{\rm fixed}$ | $T_{10^{-10}}$ rec / recount |
|---|---|---|---|---|---|---|---|
| F1 `r04-F1-004` | 228 / 228 / 228 | 846 / 846 | 1417 / 1417 | 53 / 53 | 10 / 10 | 210 | 1242 / 1242 |
| F3 `r04-F3-003` | 228 / 228 / 228 | 846 / 846 | 1417 / 1417 | 53 / 53 | 10 / 10 | 210 | 1242 / 1242 |
| F4 `r04-F4-004` | 292 / 292 / 292 | 1210 / 1210 | 1766 / 1766 | 62 / 62 | 14 / 14 | 306 | 1742 / 1742 |

All 21 comparisons exact. Against the previous best $(232,1090,2037,53)$: CX $232\to228$ ($-1.7$ %), $T$ $1090\to846$ ($-22.4$ %), depth$_{CT}$ $2037\to1417$ ($-30.4$ %), qubits 53 $\to$ 53: strictly better in every component. Rank by key: F1 = F3 $<$ F4; the index tie F1/F3 is broken by id (`r04-F1-004`), as `Archive.best()` and `index.json` say.

### 3.4 F1/F3 identical-circuit claim (`tester-221-samecircuit.json`)

`r04-F1-004` (sha256 `9d5ed8b4...`) and `r04-F3-003` (`17d0d35d...`) are different programs but build **the same circuit**: 378 macro gates, 53 qubits, name + qubit tuple + parameters compared exactly, equal at four pairs (0.37,0.61), (0.91,0.23), (1.7,1.0), (0.5,0.3) with maximum parameter difference 0.0 and no differing index. The claim is confirmed. Consequence: `r04-F3-003` adds no new circuit; it is a second route to the same gate list, and the F1/F3 families share the best for this round (the F1 program was derived from the F3 frame, `PARENT = "r03-F3-002"`, a cross-family parent, which the archive accepts).

### 3.5 Mutant battery, my sparse engine, all 1296 codes, nominal pair (`tester-221-gauge-mutants-<cid>.json`)

Every gate of the macro circuit: drop, $t\leftrightarrow t^\dagger$, $s\leftrightarrow s^\dagger$, `rccx` $\to$ `ccx`, `rz`/`p` $+10^{-6}$ and sign flip, 12 random `cx` swaps (seed 220 as in 220). Detected: block error $>10^{-9}$ or leak $>10^{-9}$ or engine exception. Baseline $2.1\times10^{-14}$ (F1) and $2.8\times10^{-14}$ (F4).

| program | mutants | detected | survivors | smallest `drop` error | smallest drop of an S/Sdg/T/Tdg/Z/CZ/CCZ gate (count) | `angle` $+10^{-6}$ min error | smallest `rccx2ccx` |
|---|---|---|---|---|---|---|---|
| F1 `r04-F1-004` (= F3-003) | 536 | 536 | **0** | 0.0761 (a T) | 0.0761 (102 gauge-type gates) | $5.0\times10^{-7}$ | 1.047 |
| F4 `r04-F4-004` | 844 | 844 | **0** | 0.0761 | 0.0761 (218) | $5.0\times10^{-7}$ | 0.791 |

Wall 1210 s and 1580 s, 0.4 GB each. 1380 mutants, 0 survivors: every gate of both programs is load-bearing at the tolerance of the engine.

### 3.6 F4 claims (`tester-221-f4-claims.json`, `tester-221-f4-depth.json`)

- Floor claim ("estimated F4 floor $\ge244$ CX $>232$"): this is a proposer **estimate**, not a proof. What I can check: (a) the combinatorial sub-claim holds: the per-corner predicate $(a\oplus b)(c\lor w)$ has weight 6 on the 16 labels, and $R\oplus(l_1 l_2)$ with $R$ any affine function of the four bits (or constant) and $l_1,l_2$ literals reaches only the weights $\{4,8,12\}$ (exhaustive, 16 x 2 x 6 x 4 cases), so weight 6 is unreachable by a single `rccx` test; (b) the numbers are consistent: the actual F4 CX is 292, above the claimed floor 244, and 244 is also above the new best 228 (the claim would still say F4 cannot win). The "$\ge7$ CX per corner and side vs 3" arithmetic and the exhaustive GF(2)/Z4 solves over 80 couplings were not reproduced (no script of the proposer is in the repo). Verdict: plausible, unverified beyond (a); it is labelled an estimate in the program.
- **F4-004 vs its parent r03-F4-003:** the docstring says the balanced `rccx` tree "lowers the depth at equal CX and T". The gate lists differ in 12 `rccx` entries (indices 266-271 and 302-307), but the gate-name multiset is identical and **the evaluator's depth is unchanged**: macro depth 215 $\to$ 215, depth$_{CT}$ 1766 $\to$ 1766, key $(292,1210,1766,62)$ identical and the 20-pair robust key identical $(292,23872,0,34554,62)$. So the round-4 F4 entry is a no-op for every number the loop ranks; the depth saving is not visible in the metric (the critical path is elsewhere). It is valid and exact but should not be counted as an improvement.

### 3.7 Step 6.4b: robust headline, independent re-derivation (`tester-221-rank-*.json`, `tester-221-rank-summary.json`)

For all 16 valid archive entries I rebuilt the program at the 20 pairs of my own generator (`rng = default_rng(20261107)`; `alpha = rng.uniform(0.05, 2.0, 20)` then `beta = rng.uniform(0.05, 1.2, 20)`), recounted CX / $T$ / depth$_{CT}$ / qubits with my own lowering + own `pygridsynth` call at each pair, and computed $\rho$ by my own fit: least squares in $(\alpha,\beta)$ over the 20 pairs (note: $\beta$ and $\sqrt2\beta$ are collinear over any pair set, so the split $m_\beta+\sqrt2 m_\gamma$ is identified only through the rational/irrational decomposition of the coefficient, which I do by brute force over $d\le64$, $|m|\le128$), residual $\le10^{-9}$.

| entry | CX | $\sum T$ (20 pairs) | $\rho$ | $\sum$ depth | qubits | mine = production cache (all 20 $T$, 20 depths, key, angle fit) |
|---|---|---|---|---|---|---|
| `r04-F1-004` | 228 | **16 876** | 0 | 28 328 | 53 | yes |
| `r04-F3-003` | 228 | 16 876 | 0 | 28 328 | 53 | yes |
| `r03-F3-002` | 232 | 21 936 | 0 | 41 904 | 53 | yes |
| `r03-F1-003` | 240 | 17 356 | 0 | 27 008 | 55 | yes |
| `r02-F3-001` | 252 | 22 536 | 0 | 41 624 | 54 | yes |
| `r02-F1-002` / `r02-F2-002` | 252 | 22 692 | 0 | 40 678 | 57 | yes / yes |
| `r01-F1-001` | 256 | 20 290 | 0 | 34 110 | 58 | yes |
| `r03-F4-003` / `r04-F4-004` | 292 | 23 872 | 0 | 34 554 | 62 | yes / yes |
| `r02-F4-002` | 326 | 24 436 | 0 | 34 730 | 62 | yes |
| `r01-F2-001` | 354 | 35 692 | **1** | 70 313 | 62 | yes (not angle-linear) |
| `r01-F4-001` | 390 | 25 752 | 0 | 36 672 | 62 | yes |
| `r01-F5-001` | 492 | 34 860 | 0 | 62 668 | 51 | yes |
| `r00-seed-000` / `r00-seed-010` | 10 102 | 412 404 | 0 | 712 112 | 58 | yes / yes |

16 of 16 robust keys equal (all $16\times20$ $T$ values, all depths, all angle fits). My lexicographic ranking (key, then laptop key, then id) equals the production `headline()["ranking"]` order for all 16 entries; headline `r04-F1-004` with $k_{\rm rob}=(228,16876,0,28328,53)$, $\bar T=843.8$ (nominal 846, $-0.26$ %); `archive_best` = headline. `r04-F3-003` has the identical key (same circuit) and is second by the id tie-break. Notable: `r03-F1-003` has a smaller $\sum T$ than `r03-F3-002` (17 356 vs 21 936) but ranks below it because CX decides first (232 < 240); this is the rule as written, not a bug. $\pi/4$ angle shifts: none (all parameters exactly $\pm$ rational multiples of $\alpha$, $\beta$, $\sqrt2\beta$ with small $d$).

`python -m su2plaq.rishon.compress.robust report` (0.4 s, from cache) prints GLOBAL BEST = HEADLINE = `r04-F1-004`, best of family F1/F3 both 228 / 843.80 / 1416.4 depth, F2 `r02-F2-002`, F4 `r03-F4-003` (1193.60), F5 `r01-F5-001`, seed `r00-seed-000`; writes `results/compress/rishon/summary.json` (untracked); `results/compress/rishon/robust.json` is unchanged (`git diff` empty).

**Cache checks** (`tester-221-cache.json`, tmp root, real files untouched): (a) unchanged cache: 0.05 s, keys equal to cache; (b) wrong `program_sha256` for one entry: that entry alone recomputed (6.5 s), correct key restored; (d) wrong `evaluator_sha256` or wrong angle-set sha: all 16 entries recomputed (107 s / 91 s), all restored, new sha stored; (f) `refresh=True`: 93 s, all 16 keys and all $T$ lists equal to the original cache (so the committed `robust.json` reproduces from scratch). (c) **limitation, not a failure:** a cache record with the right program/evaluator/angle-set sha but a falsified number is trusted (a falsified `t_sum` entered the ranking in 0.01 s). The cache is a performance cache keyed by hashes, not a verified record. Also note that `robust.py` / `lean_cert.py` are not in `RISHON_EVALUATOR_FILES`, so editing `recognise_angle` does not invalidate cached $\rho$ values.

### 3.8 Builder flags

**Flag 1: `render_spec` wrapped in `compress/__init__.py` (spec.py untouched). Judgement: acceptable.** Checked: `code_hash()` = `43ae85b452e0...` (= rounds 2, 3, 4 and my own recomputation in the archive script), `spec_sha256` `bb0b575b...` unchanged in all rounds, so G1's evaluator-hash comparison keeps working; `spec.render_spec(spec)` equals `compress/specs/rishon-step.md` byte for byte (10 323 chars), contains the section exactly once, before `## Tools`; `write_spec` inside spec.py resolves `render_spec` through the module global at call time, so it picks up the wrapper; the wrapper is idempotent (`with_headline_section(render_spec) is render_spec`); `grep render_spec` finds no consumer that binds the unwrapped function earlier. Risks (minor): it is a monkey-patch applied on package import (loading `spec.py` by file path would give the old text), and the headline section is not covered by the evaluator hash, which is the intended trade-off. K2 and R2 pass.

**Flag 2: `recognise_angle` refuses alpha/beta combinations without $\sqrt2\beta$. Judgement: correct and necessary for the locked L2, but not a complete fix, and the residual risk matters for step 6.L2 (`tester-221-recognise.json`).** At the rational nominal pair $(0.37,0.61)$ any combination $m_\alpha\alpha+m_\beta\beta$ is a multiple of $0.01$, so without the refusal every 2-decimal angle fits; with it, $0.123\to$ None as L2 demands. Audit: the locked examples are right ($8\sqrt2\beta\to(0,0,8,1)$, $-0.75\alpha\to(-3,0,0,4)$, $0.5\beta\to(0,1,0,2)$, 0.123 and $-0.123\to$ None, 0 $\to(0,0,0,1)$). 300 random true expressions per family, soundness judged by value equality at the 20 locked pairs: $\alpha$ only 293/293 correct, $\beta,\sqrt2\beta$ 300/300, $\alpha,\sqrt2\beta$ 298/298, $\beta$ only 291/291, $\alpha,\beta$ without $\sqrt2\beta$: 239 None, 23 correct, **38 wrong aliases**; all three variables: 270 correct, **21 wrong aliases**, 9 None. Examples: true $(10\alpha-\beta)/3$ returns $103\alpha/37$; true $(-7\alpha+11\beta+8\sqrt2\beta)/26$ returns $(27\alpha-13\beta+4\sqrt2\beta)/13$. Also: any angle with $\le2$ decimals is returned as $m\alpha/37$ ($-1.58\to(-158,0,0,37)$; 56 of 400 random 3-decimal angles). These are inherent to a single rational nominal pair, not a coding error. **Where it is safe:** `robust_metrics` re-checks the fitted expression at all 20 pairs to $10^{-9}$; I verified it end to end (`tester-221-alias.json`): a free ancilla with $p(0.12)/p(-0.12)$ (returned $(12,0,0,37)$) gives `angle_linear False`, $\rho=1$; $p(0.123)\to$ False; $p(0.75\alpha)$ and $p(0.5\beta)$ $\to$ True, $\rho=0$. So $\rho$ is sound (a legitimate mixed expression is demoted, never an illegitimate one promoted). All 16 archive circuits have identical fits from the function and from my 20-pair fit (section 3.7). **Where it is not safe:** a Lean certificate that trusts `recognise_angle` at the nominal pair alone (step 6.L2/6.L3 exporter) could certify an alias such as $12\alpha/37$ as if it were the true symbolic angle; the exporter must apply the same multi-pair refit (or a second pair) before emitting exponents. I recommend the planner state this in the 6.L2 row. Real rishon rotations use $d\le4$ and the smallest-$d$ search returns them before any alias ($d\ge37$ for $\alpha$ aliases).

### 3.9 Clifford+T re-verification of the headline (`tester-221-synth-1e-06.json`, `tester-221-prodsynth.json`)

Circuit lowered to Clifford+T with my own gridsynth words, my engine on all 1296 codes; budget $N_{\rm rot}\varepsilon+10^{-9}$:

| program | gates (T, CX) | block error | leak column / spectral | block + leak(spectral) | production op-norm error (`verify_synthesised`) | difference | budget | ratio |
|---|---|---|---|---|---|---|---|---|
| F1 `r04-F1-004` (headline) | 2331 (846, 228) | $2.5445\times10^{-6}$ | $4.61\times10^{-7}$ / $4.87\times10^{-7}$ | $3.03150\times10^{-6}$ | $3.03152\times10^{-6}$ (round JSON: same) | $2\times10^{-11}$ (= its dropped bound) | $1.0001\times10^{-5}$ | 0.254 |
| F3 `r04-F3-003` | identical to F1 | identical | identical | $3.03150\times10^{-6}$ | $3.03152\times10^{-6}$ | $2\times10^{-11}$ | $1.0001\times10^{-5}$ | 0.254 |
| F4 `r04-F4-004` | 3208 (1210, 292) | $3.2375\times10^{-6}$ | $1.71\times10^{-6}$ / $2.22\times10^{-6}$ | $5.45514\times10^{-6}$ | $5.45516\times10^{-6}$ | $2\times10^{-11}$ | $1.4001\times10^{-5}$ | 0.231 |

Block error equals production's to $7\times10^{-16}$; $T$ counts equal the keys; no outer qubit touched. Production Gauss residual (synthesised): $1.45\times10^{-6}$ (F1/F3), $1.69\times10^{-6}$ (F4) $\le$ tolerance $1.0$ and $1.4\times10^{-5}$. Round JSON `synthesis_verification`: entry `r04-F1-004`, ok, certified, $\varepsilon=10^{-6}$, $N_{\rm rot}=10$, $T=846$, error $3.0315\times10^{-6}\le1.0001\times10^{-5}$.

### 3.10 Archive and static consistency (`tester-221-archive.json`: **77 of 77 PASS**; `tester-221-static.json`)

Static (own `ast` walk): all three programs import only `math` and `su2plaq.compress.builder`; no forbidden name; sha256 file = archive = round JSON. Round JSON: round 4, kind step, entries F1, F3, F4 in order, 3 valid, 0 invalid, `external` [], `n_pruning_bound` 0, `best_key` $(228,846,1417,53)$, evaluator `43ae85b4...` (rounds 2-4 equal; rounds 0-1 `d45ffb31...`, unchanged from before), spec `bb0b575b...`. Entries: keys = metrics, cells $\lfloor8\log_2(\cdot+1)\rfloor$ recomputed, nominal and two alternate verdicts ok/certified with dropped $\le10^{-12}$, `max_leak` 0, DISCOVERY lines in `discoveries/rishon.md` and no extras, feedback equals entry, Lean field only on the round best (`not_run`, stub 6.L3), seeds and versions recorded. Attempts: 19 lines, first 16 byte-identical to `50ea6c7`. Index: 16 entries = 16 files, best `r04-F1-004`, elites recomputed by me equal the index, `Archive.load` 16 entries 0 rejections, 20 random insertion orders give identical best and elites. Old entries, round 0-3 JSON, old programs unchanged since `50ea6c7`. Observations: round-4 `provenance.git_dirty` true (same class as N4 of 220); `round-004.json` has no `headline` field (round 4 was evaluated before 6.4b; `run_round` now adds it from round 5 on).

### 3.11 Acceptance and unit tests

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `tools/check_lock.py` | LOCK OK | `LOCK OK` | - | PASS |
| `acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v15` | - | PASS |
| `pytest --collect-only -q tests/acceptance` | clean | 255 tests, 0.40 s | - | PASS |
| m6 not slow (19 collected) | 17 PASS + L2, L3 PENDING | 17 passed, 2 failed with `PENDING: lean/Su2PlaqCert/Rishon/Laurent3.lean missing (step 6.L2)` (L2, L3), 154 s | - | PASS (2 expected PENDING) |
| m6 `H1` (angle set, robust_metrics, 3-variable rule) | PASS | PASS | - | PASS |
| m6 `K0 K1 K2 K3` | PASS | PASS (K2 now green: headline section, "robust key", "pi/4") | - | PASS |
| m6 `E1 E2 E3` | PASS | PASS | - | PASS |
| m6 `S1 S2`, `R1 R2` | PASS | PASS (R2: brief contains the section) | - | PASS |
| m6 `L1`, `L8` | PASS | PASS | - | PASS |
| m6 `G2 G3 G4` | PASS | PASS (G4 after `robust report`: `summary["headline"]` = `headline()`, ranking sorted) | - | PASS |
| m6 slow `H2` (dry seed round, headline selection, report) | PASS | PASS | - | PASS |
| m6 slow `G1`, `S3` | PASS | PASS | - | PASS |
| m6 slow `L7` (best has Lean status) | PENDING | PENDING (`Laurent3.lean missing (step 6.L2)`) | - | PENDING (expected) |
| m6 `L2 L3` | PENDING | PENDING | - | PENDING (expected) |
| m6 slow `E4 R3 L4 L5 L6` | not asked | not run (as in 218-220; L4-L6 are Lean 6.L3) | - | not run |
| unit: 12 compress / lean-round files (`test_rishon_robust_unit`, `..._compress_{stubs,spec,loop,evaluate,baselines,ladders}`, `test_compress_{brief_report,evaluate,archive}`, `test_lean_cert`, `test_lean_round`) | PASS | **189 passed**, 193 s | - | PASS |
| unit: 12 other rishon files (algebra, circuits, encoding, ks_projection, lean_exact, lean_export, observables, operators, physical, results, stubs, verify) | PASS | **113 passed**, 240 s | - | PASS |

New failures versus report 220: none. `test_M6_G4`, H1, K2, R2 (PENDING in 220) are now PASS; L2, L3 (and L7) remain PENDING for step 6.L2 as announced. At the milestone gate these PENDING count as FAIL.

## 4. What the two pending amendments would invalidate or require re-running

Not applied; listed from what I saw in the code and the committed data.

**(a) A determinant term ($\gamma\ne0$) as a third Trotter layer.** The step target, its dense reference and every number derived from it change.
- Target and spec: `operators.inner_target` / `h_det`-style term (`operators.py` line 316 says "gamma = 0 in M5: defined, not used"), the M5/M5x acceptance numbers (step counts, 1620 rccx / 54 ccx ladders, `results/rishon/step.json`, `step.qasm3/qpy`, `step_order2.*`, `observables.json`), `rishon_spec` and hence `spec_sha256` (`bb0b575b...`), `code_hash()` / `evaluator_sha256` (`43ae85b4...`), `compress/specs/rishon-step.md`, `rishon-structure.json`, the oracle target.
- Every archived verdict: all 16 entries (and rounds 0-4, the round JSONs, `feedback/`, `attempts`, the elites and family bests in `index.json`, `discoveries`) are valid only for the $\gamma=0$ two-layer target; none of the programs contains a determinant layer, so all would become invalid or need a new seed (G1 compares the best's `evaluator_sha256` with the current hash and will fail). The keys $(228,846,1417,53)$, the $\sum T$ values, `robust.json` (keyed by evaluator sha, so it would be recomputed, but its headline `r04-F1-004` would be meaningless) and the first-three-round discussion of F1/F3/F4 families all restart.
- Locked tests that bake in the $\gamma=0$ numbers: H1 (`angle_fit == [(-3,0,0,4)]*4`, key $(8,\sum T,0,\sum{\rm depth},48)$ for the $U_E$ seed, `kind UE` unaffected only if the new layer is a separate kind), S1/S2/S3 (seed keys $(10102,20650,35639,58)$, `general-rccx`/`general-mcx` reasons), E1-E4, G1-G4, K0 (ladder counts), R1-R3.
- **Name collision:** `lean_cert.recognise_angle`, `robust.py`, the plan ("three-variable rule") and `Laurent3.evaluate(theta_alpha, theta_beta, theta_gamma)` all use $m_\gamma$/$\theta_\gamma$ for the coefficient of $\sqrt2\beta$. A det-term coupling called $\gamma$ would be a different, fourth angle: the rule becomes four-variable (or the coupling must be given another name), `recognise_angle`'s support search and the Lean `Laurent3`/`Check3` (step 6.L2, not yet built) must be designed for it, and `ANGLE_SET` should be extended with a third random coordinate (changing `angle_set_sha256`, `robust.json`, and the cross-track comparability with spinnet, which uses the same $(\alpha,\beta)$ set). The alias analysis of section 3.8 gets worse with a third rational coupling at the nominal pair.
- Seed, brief and spec texts that say the step is $U_EU_B$; the proposers' F1-F5 families (their frames assume two layers; the 10 rotations of the best, the $\beta$-coefficients $\pm0.5,\pm1.828,\pm3.328$ and the $-0.75\alpha$ phases would gain a third class).

**(b) Prune cap raised to 10 % of `tol_err`.** The cap is an evaluator constant (a verdict rule in the hashed evaluator files), so `code_hash()` changes and every cached `evaluator_sha256` goes stale exactly as in (a), but the physics of the programs does not. Concretely: (i) E2 / S3 (`test_M6_S3_round0_recorded`, the windowed Qiskit L3 seed recorded as `pruning_bound` with `dropped_total` $3.79\times10^{-12}$ $>10^{-12}$) is in the locked tests and would flip from rejected to valid unless the planner changes the test; (ii) `n_pruning_bound` bookkeeping and the `pruning_bound` reason in every round JSON; (iii) round-0 `external`/invalid reasons (`general-rccx`, `general-mcx`, windowed seed) need re-evaluation; (iv) the margin statement of my reports (bounds $\le1.8\times10^{-13}$, a factor $\ge5.6$ below $10^{-12}$) is replaced by a factor $\ge56$ below $10^{-11}$ (assuming $tol_{err}=10^{-10}$); the Clifford+T synthesised verification also uses `dropped_total` inside `tol_err` and must be re-run for the headline. Nothing in the 16 entries would be newly invalid under a looser cap. Both amendments together: one full re-evaluation of seeds and all archive programs under the new hash, new tester round.

## 5. Verdict

**PASS** for round 4 (step 6.7) and for step 6.4b.
- Round 4: all three entries are exact on all 1296 inner codes at the three spec pairs plus one extra (my engine $2.0$-$2.9\times10^{-14}$; Aer $1.0$-$1.6\times10^{-14}$ over 2096 runs, 100 % code coverage for F1), global phase 1, ancillas clean, outer register untouched, keys recomputed exactly (21 of 21), pruning bound $\le1.8\times10^{-13}$, angles linear with zero intercept, Clifford+T re-verification of the headline matches production to $2\times10^{-11}$ at 25 % of the budget, archive 77 of 77. 1380 single-gate mutants, 0 survivors. The new best $(228,846,1417,53)$ beats the previous $(232,1090,2037,53)$ in every component; `r04-F3-003` is the same circuit; `r04-F4-004` is a no-op against its parent in every ranked metric.
- Step 6.4b: independent $\sum T$ over the 20 seeded pairs, $\rho$ and the full 16-entry ranking agree with production (16 of 16 keys, 320 $T$ values); headline `r04-F1-004` $(228,16876,0,28328,53)$; cache behaves as designed (with one documented non-verification); H1, H2, K0-K3, E1-E3, S1, S2, R1, R2, L1, L8, G1-G4 all pass; L2, L3, L7 PENDING for 6.L2 (expected). Rishon unit tests: 302 passed. Counts: passed 3 slow + 17 fast m6 + acceptance-check/lock + 302 unit; failed 0; pending 3 (L2, L3, L7).

## 6. Notes (none blocking)

- N1 (recogniser alias, for 6.L2): see 3.8. `recognise_angle` alone is unsound at a rational nominal pair for the Lean exporter; `robust_metrics` is safe because of its 20-pair refit.
- N2 (cache trusts values): 3.7 (c). `robust.py` / `lean_cert.py` are outside the evaluator hash.
- N3 (F4-004 no-op, F3-003 duplicate): the archive now holds two entries for the same circuit and one for a no-op. The headline and the stop-rule counter are unaffected (stop rule: round 4 improved the robust key, counter 0).
- N4 (provenance): `round-004.json` `git_commit` `68b8b76`, `git_dirty` true; `results/compress/rishon/summary.json` is untracked (written by my `robust report`).
- N5 (coverage): Aer does not cover the 824 F4 codes needing 25 to 30 qubits; 8 sampled 25-26 qubit codes pass and my sparse engine (844 of 844 mutants caught) covers them.
- N6 (crash): the machine rebooted at 13:49 (GParted kernel fault). Kept from before the crash (complete, verified by log/JSON): sparse x3, recount, static, same-circuit, rank x16, cache, archive (re-run later), recognise, f4 claims/depth, both pytest runs (`m6-fast`, `m6-slow`), unit-compress, F1 Aer nominal. Re-run after the crash: Aer F4 nominal/alt/big and F1 alt, both mutant batteries, Clifford+T synth, production synth, the rest of the rishon unit tests, the alias test. `/tmp` was cleared, so the scratch directory was recreated. During the restart I edited the Aer launcher twice by sed (first edit also dropped the F1 alternate loop; it was re-run through `tester-221-aer-f1-alt.sh`).

## 7. Files touched by my runs

New (untracked, all mine): `results/rishon/tester-221-*` (scripts, logs, `.time`, JSON, npz). Untracked byproduct: `results/compress/rishon/summary.json` (written by `robust report` and by the m6 tests; G4 needs it). Gitignored: `scratch/t221*` temporary roots of the cache and alias tests (two leftover directories; the cache one is removed by the script, `t221alias...` could not be removed). No tracked file modified (`git status` shows only untracked files from me; `robust.json`, `round-004.json`, the archive and `compress/specs` are byte-identical; `tests/acceptance/LOCK.json` / m9 changes seen earlier were the planner's, now committed as acceptance-v15). Other untracked paths in the tree (`src/su2plaq/lsh/`, `tests/unit/test_lsh_*`, `scratch/*`) belong to other agents.

## 8. Resources

Active wall time about 1 h 40 min over two sessions. Largest process: m6 non-slow pytest (4 workers, about 3 GB RSS each at peak, no process above 4 GB), Aer F4 nominal 1518 s wall (4 workers, 5870 CPU-s), mutant batteries 0.4 GB, my sparse engine 0.77 GB, production `verify_synthesised` 1.06 GB (148 s), robust cache full recompute 91 to 107 s per scenario.
