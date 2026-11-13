# Tester report 410 — rishon step C1 (three_layer module, replay tool) and the `leaving_weight` residual fix

Date: 2026-11-13 · Git commit: raw numbers recorded at `77b68ce` (HEAD moved to `13a35ab` while I worked; the builder files were committed meanwhile; the tested content is the working tree I read) · Prompt in force: `prompts/204-rishon-det-term-amendment.md` §5, §6.1, §6.2, §7 step C1 (acceptance-v19) · Mode: **step** · Cores 6–11
Related: `reports/tests/405-rishon-d3-d6-det-circuits.md` (my previous rishon report; note 1 there is the `leaving_weight` artefact), `docs/METHODS-rishon.md` R13–R16. My raw-number files are named `tester-409-*` because I started under that number; 409 was then taken by another agent's report.

Symbols: $T=U_BU_DU_E$ is the first-order three-layer step, $P$ the $38432$-column isometry onto the SU(2)-Gauss space, $\eta=\lambda_D\,dt$ the det angle.

## 0. Verdict: **PASS**

All checks of C1 pass. Two points the coordinator must know before C2 (not C1 failures):

1. **The real replay must run on a quiet machine.** In my scratch replay (rounds 0–1) the Qiskit-L3 seed (`r00-seed-qiskit_l3`, 9558 raw CX) was judged `eval_budget` (nominal evaluation $>300$ s), not `ok`, exactly as the builder saw. Measured cause: alone on one core it needs $138$ s, `ok`, certified, $\mathrm{dropped\_total}=3.788\times10^{-12}$ (matches the planned $3.8\times10^{-12}$); my replay ran together with a 5-worker pytest and other agents' jobs, and round 0 took 2147 s (recorded round 0 of the real archive: 1317 s). If the final replay is judged `eval_budget`, the locked slow test `test_M6_S3_round0_recorded` fails (it allows only `ok` / `pruning_bound` for that seed) and `prompts/204` §6.2's expected outcome ("three seeds become valid") is not met. Run C2 with nothing else on the machine, or ask the planner how an `eval_budget` verdict from a loaded machine should be treated.
2. `docs/METHODS-rishon.md` is modified in the working tree by someone else (not me; not hashed). `prompts/204` §2.2 / §8 still quote "$5.8\times10^{-11}$" for the old leaving weight; harmless (the bound $\le10^{-9}$ still holds), a wording item for the planner.

## 1. Commands run

```
source ~/miniforge3/etc/profile.d/conda.sh && conda activate coding; cd /home/digimonk/Projects/su2qc-encoding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src
graphify update . ; graphify query "three_layer verify_three_layer det layer"
taskset -c 6-10 tools/pytest-safe -n 5 -q tests/unit                                                       # 949 passed, 714 s
taskset -c 6-10 tools/pytest-safe -n 5 -m "not slow" -q -rfEs tests/acceptance/m5 tests/acceptance/m5x tests/acceptance/m6   # 81 passed, 5 failed (all PENDING), 925 s
taskset -c 11 tools/run-capped python <scratch>/sector.py                       # production det_sector_structure
taskset -c 11 tools/run-capped python results/rishon/tester-409-leaving-sanity.py
taskset -c 11 tools/run-capped python results/rishon/tester-409-three-layer-independent.py --out results/rishon/tester-409-three-layer-independent.json
taskset -c 11 tools/run-capped python -m su2plaq.rishon.compress.three_layer --out <scratch>/three-layer.json   # 336 s
taskset -c 11 tools/run-capped python -m su2plaq.rishon.compress.replay --kind step --root <scratch>/replay_root   # scratch copy, rounds 0-1 only, 2254 s
taskset -c 11 tools/run-capped python results/rishon/tester-409-l3-seed-time.py --out results/rishon/tester-409-l3-seed-time.json
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
git diff --stat src/su2plaq/evaluate src/su2plaq/compress ; python -c "from su2plaq.compress.provenance import code_hash; print(code_hash())"
```
Scratch root: `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/57b28677-d814-4f58-bc95-52ae378eb01f/scratchpad/t/replay_root` (copy of `compress/{archive,attempts,discoveries,programs,specs,cache,briefs,ideation}` and `results/compress/rishon`, round files 2–4 removed). The repo's own `results/compress/rishon/three-layer.json` and `replay-204.json` were **not** created.

## 2. Results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| (1a) `det_sector_structure` blocks | `lam0` 31870, `inner_det` 4976, `full_det` 305 | 31870 / 4976 / 305 | exact | PASS |
| (1b) other outputs (dim, u1_sectors, max_block, ref_block_dim, ref_block_u1_sectors, charge_change_rank, reference_state) | identical to the old output | 38432, 431, {3,17,4352}, {3,17,4352}, {1,15,431}, {0,3,4}, 2341: identical | exact | PASS |
| (1c) `leaving_weight` | $\le10^{-24}$ (report 405: $1.6\times10^{-25}$) | $1.601319485313107\times10^{-25}$ (before the fix: $2^{-32}=2.3283\times10^{-10}$) | $\le10^{-20}$ (unit test), $\le10^{-9}$ (M5_DT5) | PASS |
| (1d) residual form $\|(1-PP^\dagger)TP\|_F^2$ is the right quantity: $O(\text{columns})$ for an operator that does leave | number of leaving columns | bit-0 flip: $38432.000$; nibble $3\to5$ flip: $12808.000$ (the old difference gives the same there, so the new form hides nothing) | $10^{-6}$ relative | PASS |
| (1e) own independent residual (own JW operators, report 405 method) | per-term $\sim10^{-26}$ | $9.9\times10^{-27}$ ($H_B$), $1.5$–$2.0\times10^{-26}$ per det link; production $1.6\times10^{-25}$ is the largest over its inner / outer det sums | — | PASS |
| (2a) CLI `verify_three_layer` on `r04-F1-004` | `ok`, certified at 3 triples | all three `ok`, `certified`, reason `ok` | `tol_err` $10^{-10}$ | PASS |
| (2b) `op_norm_error` at the three triples | $1.6$–$1.7\times10^{-13}$ | $1.644\times10^{-13}$, $1.668\times10^{-13}$, $1.691\times10^{-13}$ (block $1.6\times10^{-14}$, leak $0$, dropped $1.48$–$1.53\times10^{-13}$) | $\le10^{-10}$; dropped $\le10^{-11}$ | PASS |
| (2c) Gauss residual | $\le1.2\times10^{-15}$ | $1.18\times10^{-15}$, $1.03\times10^{-15}$, $8.4\times10^{-16}$ | $10^{-10}$ | PASS |
| (2d) three-layer key | $(260,1342,1743,53)$ | $(260,1342,1743,53)$ | exact | PASS |
| (2e) det key | $(32,496,326,48)$ | $(32,496,326,48)$ | exact | PASS |
| (2f) angle-averaged $T$ (unit 843.8 + det) | 1344.6 | det mean $500.8$ (20-$\eta$ set, own pygridsynth, seed 20261110, $\varepsilon=10^{-6}$; own nominal values 496, 496, 512 for $\eta=0.29,0.53,1.07$); $843.8+500.8=1344.6$ | exact | PASS |
| (2g) **independent** composition: own JW $U_BU_DU_E$ vs the headline unit with `prepend_det_layer`; own sparse simulator using qiskit `Operator` matrices for every gate (`rccx`, `ccz`, `ch` are not hand-typed); 64 of 1296 inputs, one global phase | $\le10^{-10}$ | max column error $1.27\times10^{-14}$, $1.30\times10^{-14}$, $1.68\times10^{-14}$; leak out of the code space $\le4.1\times10^{-16}$; distance to the unit-only target $1.0$–$1.75$ and to the wrong order $U_DU_BU_E$ $0.71$–$1.75$ (the check discriminates) | $10^{-10}$ | PASS |
| (2h) CX added by the det layer; qubits; outer touched | 32; 53; no | 32 (raw `cx` 116 → 148, `rz` +8; lowered key 228 → 260); 53 qubits; `outer_touched` False; `skeleton_equal` True | exact | PASS |
| (3a) replay refusal paths | `ValueError`, nothing touched | wrong kind (`UE` vs recorded `step`) refused and the scratch tree unchanged; the unit tests cover replay twice, wrong kind with another tag (no `pre-205` created), empty root | — | PASS |
| (3b) replay never deletes | moves only | read the code: rounds, feedback, robust, summary go to `pre-<tag>/`, archive to `rishon-pre-<tag>`; the only `unlink` removes a log that did not exist before the replay (created by `run_round`). Scratch run: `pre-204` holds all 5 backups; attempts log and discoveries file byte-identical (`md5sum -c` OK) | — | PASS |
| (3c) replay on scratch copy, rounds 0–1 (optional) | valid keys unchanged, `lost = []` | `lost = []`; `r00-seed-000`/`010` $(10102,20650,35639,58)$, `r01-F1-001` $(256,1020,1714,58)$, `r01-F2-001` $(354,1818,3557,62)$, `r01-F4-001` $(390,1304,1871,62)$, `r01-F5-001` $(492,1739,3142,51)$ all `key_equal`; `r00-seed-001` $(6874,17694,31954,58)$ and `r00-seed-002` $(7360,18180,32428,58)$ newly valid (dropped $2.91$, $2.69\times10^{-12}$); `attempts_unchanged`, `discoveries_unchanged` true; new hash `a4dbd16c…`, old `d45ffb31…` | exact | PASS |
| (3d) `r00-seed-qiskit_l3` becomes valid (prompts/204 §6.2) | valid | `eval_budget` in the loaded replay; alone: 138 s, `ok`, certified, dropped $3.788\times10^{-12}$ | — | NOTE (load), see §0 point 1 |
| (4a) `M6_H3`, `M6_H4` | green | pass (inside the 81 passed; not in the failure list) | locked | PASS |
| (4b) m5 / m5x / m6 not-slow | only PENDING | 5 failed, all `PENDING:` (`L2`, `L3`, `L9`: Lean 6.L2 / `recognise_angle_single` missing; `G5`: `replay-204.json` missing (C2); `G6`: `three-layer.json` missing (C5)); 81 passed | — | PASS |
| (5a) `provenance.code_hash()` | `0bd7e7d9…` | `0bd7e7d91d9d7bcfc78641d1a14bb87f0f82f932c41c601fb991d30de13a0582` | exact | PASS |
| (5b) `git diff` of `src/su2plaq/evaluate`, `src/su2plaq/compress` | empty | empty | — | PASS |
| (5c) rishon evaluator hash | `a4dbd16c…` | `a4dbd16ca363770eeb5e25e959154fac2e1d12916febe2fa5b657cb76ed431d6`; `three_layer.py` and `replay.py` are not in `RISHON_EVALUATOR_FILES` | — | PASS |
| unit suite | all pass | 949 passed (714 s) | — | PASS |
| `pytest --collect-only -q tests/acceptance` | clean | 374 collected | — | PASS |
| `tools/check_lock.py`, `acceptance-check` | PASS | LOCK OK; PASS: tests/acceptance matches acceptance-v19 | — | PASS |

## 3. Review of `replay.py` against `prompts/204` §6.2 (no failures)

- Step 1 (refuse if `replay-<tag>.json` or `pre-<tag>` exists) plus extra checks (no round files, round numbers not contiguous from 0, kind / encoding mismatch) all raise `ValueError` before anything is moved.
- Steps 3–6 as specified; the append-only logs are restored in a `finally`, so they return to their bytes even if a round raises.
- Minor, recorded only: if a round raises midway, `pre-<tag>` and the moved archive stay where they are (nothing lost, but a second call is refused until the folders are moved back by hand). Extra fields beyond §6.2 (`old_id`, `program_path`, `program_sha256`, `wall_s`, `round_wall_s`, `lean`) are harmless. Exit code is 1 if any entry is `lost`.

## 4. Files touched by my runs

New, all under `results/rishon/` (none under `src/` or `tests/acceptance/`): `tester-409-sector-structure-prod.json`, `tester-409-leaving-sanity.{py,json}`, `tester-409-three-layer-independent.{py,json}`, `tester-409-three-layer-cli.json` (copy of the scratch CLI output), `tester-409-replay-rounds01-scratch.json`, `tester-409-l3-seed-time.{py,json}`. Seeds: `20261110` (inputs, eta set), `12345` (L3 seed). Byproducts of the unit suite, `results/compress/rishon/robust.json` and `results/lsh/certs/lsh-step-o1-ddc1571c27bd.json`, were restored with `git checkout`; `results/spinnet/certs` was unchanged.

## 5. Failures

None. Only the observation of §0 point 1 (guess: `eval_budget` is a wall-time verdict, so it depends on machine load).
