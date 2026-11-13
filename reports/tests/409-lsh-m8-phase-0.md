# Tester report 409: LSH M8 Phase 0 (steps 8.0, 8.A1, 8.A2, 8.1, 8.U, 8.L), mode `step`

- Date: 2026-11-13. Git commit at run time: `a2d847a` (working tree dirty, the builder's uncommitted files under test; HEAD moved e873737 -> 9aa0320 -> a2d847a during the run through unrelated fuzzy commits).
- Prompt in force: `prompts/401-lsh-m8-compression-plan.md` (acceptance-v19, `tests/acceptance/m8`); methods `docs/METHODS-lsh.md` L10, L12-L16; audit 303 notes N1, N2, N4, N8.
- Related: reports/tests/406 (M7 LSH tamper/independent), 407 (M7 gate), results/lsh_tester/tester-403-*.
- Cores 14-19 only, all pytest via `tools/pytest-safe`, Lean via `tools/run-capped`.

**VERDICT: PASS** (one workflow risk for the coordinator, see "Risks").

## Commands
```
tools/pytest-safe -n 3 -q tests/unit                                        # cores 14-16
tools/pytest-safe -n 3 -q -rfE tests/acceptance/m8                          # cores 17-19, slow ones included
tools/pytest-safe -n 3 -q tests/acceptance/m7
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
tools/run-capped taskset -c 17 bash -c 'cd lean && lake env lean ../scratch/tester/Axioms.lean'   # #print axioms
tools/run-capped taskset -c 17 python results/lsh_tester/tester-408-{structure-facts,certify-norewrite,dirty-trap,stoprule}.py
tools/run-capped taskset -c 17,18 python results/lsh_tester/tester-408-seeds.py
```
Raw numbers (commit, parameters): `results/lsh_tester/tester-408-*.json` (scripts next to them). Seeds: stop-rule fuzz seed 408; angle pair for the Aer check $(\alpha,\beta)=(0.83,0.29)$, nominal $(0.37,0.61)$.

## Results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| unit suite `tests/unit` | all green | 961 passed, 715 s | - | PASS |
| `pytest --collect-only tests/acceptance` | clean | 374 collected, no errors | - | PASS |
| `check_lock.py`, `acceptance-check` | LOCK OK, matches acceptance-v19 | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v19` | - | PASS |
| m8 must-be-green (A1, A2 certify-binding, A3, A4, S1 x8, H3, U1, L3) | pass | 15 passed (the brief says 14; the list has 1+1+1+1+8+1+1+1 = 15) | - | PASS |
| m8 registry-dependent (E1, E2, S0, S2, S5, S3, S4, H1, H2, L1, L2, G1-G4, L5, R1) | PENDING only | 17 failed, every message `PENDING: cannot import su2plaq.encodings.registry` | - | PENDING (expected) |
| `M8_A2_committed_certificate_clean_provenance` | PENDING | `PENDING: results/lsh/step.json has no extra.lean` | - | PENDING (expected) |
| m8 total | 15 pass + 18 pending | `18 failed, 15 passed`; 18 of 18 failure texts contain `PENDING`, none a real assertion | - | as expected |
| m7 | 29/29 | 29 passed (25 s) | - | PASS |
| new unit files (`test_lsh_loop_unit`, `test_lsh_lean_m8_unit`, `test_lsh_lean_export_unit`) | green | 31 passed | - | PASS |
| (e) `provenance.code_hash()` | `0bd7e7d9...` | `0bd7e7d91d9d7bcfc78641d1a14bb87f0f82f932c41c601fb991d30de13a0582` | exact | PASS |
| (e) `spinnet.loop.code_hash()` | `7f5bb7f8...` | `7f5bb7f8e65f39c89eca59abae352c3f36433e00523ae3321f9b6e59e54d0ed5` | exact | PASS |
| (e) `git diff HEAD` of `src/su2plaq/compress`, `evaluate`, `encodings/{registry,base}.py` | empty | 0 lines (`registry.py` does not exist yet: step 8.R) | exact | PASS |

### (a) `lean/Su2Plaq/LSH/Facts.lean`
- `inner_codes_from_rules : lshInnerCodes = List.filter innerOK (List.range 4096)` (as printed by `#check`), proof `decide +kernel`; the other 7 theorems `by decide`. `grep` finds no `sorry`, `native_decide`, `axiom`, `ofReduceBool`.
- Source elaborated stand-alone: `lake env lean Su2Plaq/LSH/Facts.lean` OK in 11.3 s; `Facts.olean` present in `.lake` (built after the last edit, same mtime second).
- `#print axioms` (all 8): `inner_codes_from_rules`, `dark_site_is_and`, `coupling_by_y_weight`, `link_bit_two_ways`, `move_per_site`: `[propext]`; `coupling_zero_iff_dark`, `y_parity_invariant`, `eight_differences`: `[propext, Classical.choice, Quot.sound]`. Standard only, no `Lean.ofReduceBool`. PASS.
- `innerOK` is the definition from Counts.lean (flux cap and Abelian Gauss law per site), not a table: the statement ties the exported table to the rules (audit 303 N1).

### (b) the raw-bit facts, own enumeration (`tester-408-structure-facts.py`)
Inner codes enumerated from scratch (site bits $\ell_{pn}=$ bit 0, $\ell_{nv}=$ bit 1, $\ell_{vp}=$ bit 2; $N_1=\ell_{vp}+\ell_{pn}$, $N_2=\ell_{pn}+\ell_{nv}$; flux cap $N_1,N_2\le1$; $N_2(c)=N_1(c{+}1)$ round the loop); coupling and partner read from the production $H_B$ off-diagonals (433x433), not from the Lean tables.

| fact (json name) | expected | got |
|---|---|---|
| 47 inner codes = production = Lean list | equal | equal (47) |
| site valid list | [0,1,2,4,6] | [0,1,2,4,6] |
| bright / dark | 16 / 31 | 16 / 31 |
| dark iff some site has $\ell_{nv}\wedge\ell_{vp}$ | all 47 | all 47 (31 dark by the rule) |
| bright coupling by number of set $\ell_{nv}$ bits | depends on it alone; $k=(-2,+1,-\tfrac12)$, json $2K=(-4,2,-1)$ | one value per weight, $k=(-2.0,1.0,-0.5)$ exactly (ratio to pattern $1,1,1$); $\sum\ell_{nv}=\sum\ell_{vp}\le2$ |
| parity of $\ell_{nv}$ bits move-invariant, equals $[2K=+2]$ | all 16 bright | all 16 |
| link bit readable at two sites | all 47 x 4 links | all |
| move flips pattern | w=0: 1, w=1: 6 | w=0: {1}, w=1: {6} |
| distinct difference vectors | 8 | 8 |
| 433 states; 305 outer patterns | 433; 305 | 433; 305 |
| json provenance SHA-256 of Counts/Facts/Circuit | equal to files | all 3 match |
PASS.

### (c) certify no-rewrite (`tester-408-certify-norewrite.py`, temp dir)
- M7-L3 run twice (real `results/lsh/certs`): run 1 rewrote the committed certificate once (committed file is the old schema: no `gates_sha256`, no `git_dirty`; diff is only these keys plus volatile provenance), run 2: md5 and mtime identical. Expected one-off.
- Temp dir: certify the same circuit twice: both `certified`, bytes and mtime identical, no `*pending*` file left. A genuinely different circuit (original + `x(0); x(0)`) gets its own file `lsh-step-o1-210d8def80c5.json`, `certified`, old file untouched. A wrong circuit (extra `x(1)`) is `rejected` ("state 0 differs from the target"). Changing `extra_provenance` (`entry_id`) rewrites the file with the new field; same extra twice: no rewrite. A certificate tampered on disk (phase exponent +1, same name) is replaced by the fresh one and certified.
- `_same_up_to_volatile`: considered equal (kept) only for changes in `git_commit`, `git_dirty`, `export_seconds`, and `float_phase_spread` shifted by $10^{-10}$ (tolerance $10^{-9}$). Considered different (rewrite): float residual shifted by $10^{-8}$; `float_phase_cross_check` None -> 0; phase exponent; first CX control/target swapped; first rotation exponent $+1$; `gates_sha256`, `program_sha256`, `entry_id`, a dropped extra key, a state-term code, a target-block entry, `n_qubits`, `alpha_nominal`, `encoding`. The $10^{-9}$ tolerance applies only to the two float residual fields of the provenance block; gates, states, target, phase and binding fields are compared exactly, so it cannot hide a gate change. PASS.

### (d) seeds and stop rule
Own Aer statevector check (`tester-408-seeds.py`): each wrapped seed at $(\alpha,\beta)=(0.83,0.29)$ on all 433 physical states vs the route-B 6j target $U_6(\beta)\,U_E(\alpha)$ (inner electric); outer qubits are never touched and dropped from the simulation; the `general` seed touches the outer register and was not re-simulated here (covered by M8-S1[general] and tester-403 step-exact).

| seed | CX | $N_{\rm rot}$ | $T_{\rm fixed}$ | $T_{10^{-6}}$ | qubits | op-norm err | unitarity dev | leaks (anc / invalid / span) |
|---|---|---|---|---|---|---|---|---|
| wrap_pairs9 | 74 | 13 | 56 | 864 | 27 | 3.0e-15 | 6.2e-15 | <1e-30 |
| wrap_flags4 | 84 | 8 | 80 | 586 | 27 | 5.3e-15 | 1.1e-14 | <1e-30 |
| wrap_flags5 | 82 | 9 | 72 | 638 | 27 | 4.4e-15 | 8.9e-15 | <1e-30 |
| wrap_flags6 | 76 | 10 | 64 | 690 | 27 | 3.5e-15 | 7.3e-15 | <1e-30 |
| **wrap_sn_headline** | **71** | 17 | 48 | **1118** | **25** | 2.5e-15 | 5.2e-15 | <1e-30 |
| wrap_sn_r05F3 | 72 | 13 | 56 | 864 | 25 | 3.2e-15 | 6.4e-15 | <1e-30 |
| wrap_sn_r02F5 | 74 | 10 | 64 | 690 | 25 | 3.5e-15 | 7.0e-15 | <1e-30 |

Control (compare with $U_6(\beta)$ without the electric layer): error 1.41 for every seed, so the check discriminates. CX, $T_{10^{-6}}$, $N_{\rm rot}$, $T_{\rm fixed}$, qubits agree with plan section 1.3 for all seven. The depth column of the plan key (2276 etc.) is the evaluator's depth after synthesis and cannot be reproduced here before the registry entry exists; my `t_table` depth differs (2228 for the headline) because it is a different measure. It is not used by the stop rule. The key $(71,1118,\cdot,25)$ is confirmed in its CX/T/qubit components; the depth component is unchecked until 8.R.

Stop rule (`tester-408-stoprule.py`): `improves` agrees with my own transcription of plan 1.6 on 19 hand edge cases and 20 000 random record pairs (seed 408, 0 mismatches). Edge cases: $|\Delta\sum T|=20N_{\rm rot}=340$ is a tie (False if $(\rho,q)$ equal), 341 is not (lexicographic); tie decided by $\rho$ then qubits in both directions; changed $N_{\rm rot}$ or $T_{\rm fixed}$ switches the band off; CX decides first; depth change alone is ignored (`stop_key` = $({\rm CX},\sum T,\rho,{\rm qubits})$); `None` handling (first record improves, missing never). Constants 8 / 3 / 20 and 20 pairs correct. No pair of records improves each other in my 9-pair antisymmetry sample. PASS.

## Risks and notes (not failures)
1. **Clean-worktree regeneration trap (step 8.A2 workflow).** The no-rewrite rule ignores `git_dirty`, so an existing certificate written from a dirty tree is NOT refreshed by a regeneration in a clean worktree: `tester-408-dirty-trap.py` certifies with `git_dirty=True`, then again with `git_dirty=False` over the same file: result `git_dirty: True`. `M8_A2_committed_certificate_clean_provenance` would then fail with a dirty certificate. Safe path: the committed certificate must be the old-schema one (no `gates_sha256`, it is then rewritten), or delete `results/lsh/certs/lsh-step-o1-ddc1571c27bd.json` in the worktree before running `scripts/m7_results.py`. Do not commit the working-tree copy that M7-L3 rewrote (I restored it with `git checkout`, so the tree is now the old-schema committed one).
2. `M7-L3` rewrites the committed certificate exactly once (schema upgrade), as designed.
3. Pending ids all need `su2plaq.encodings.registry` (step 8.R) and the clean-worktree certificate.
4. Count correction: the brief says 14 must-be-green m8 tests; the listed ids are 15 (all pass).

## Files touched
Created: `reports/tests/409-lsh-m8-phase-0.md`; `results/lsh_tester/tester-408-{structure-facts,certify-norewrite,dirty-trap,seeds,stoprule}.{py,json}`; scratch only: `scratch/tester/*`. The runs rewrote `results/lsh/certs/lsh-step-o1-ddc1571c27bd.json` (restored by `git checkout -- results/lsh/certs results/spinnet/certs`; md5 of all cert files identical to the start). No `src/`, `tests/`, `lean/` edits.
