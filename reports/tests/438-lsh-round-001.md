# Tester report 438: LSH M8 step 8.7, real round 1 (mode step)

- Date: 2026-11-19. Commit `89c00bc` (HEAD; the five round-1 programs were committed there before evaluation; the round outputs are uncommitted in the tree).
- Plan in force: `prompts/401` on `prompts/400` (LSH M8), step 8.7, paragraph "Tester per round". Related: `reports/tests/437` (round 0), `reports/tests/436`.
- Raw numbers: `results/tester/438/{own_sparse,aer,robust_stop,f3_mutation}.json` (each with the commit; no RNG except the Aer F3 states, seed 20261119). Scripts (mine, not collected as tests): `results/tester/438/{own_sparse,aer,robust_stop,f3_mutation}.py`; the 47-code Aer check reuses `tests/independent/lsh_m8_436/indep_check.py`.
- Resources: `taskset -c 0-1`, all heavy runs through `tools/run-capped` (Aer capped at 4 GB), pytest through `tools/pytest-safe -n 2` (the unit run `-n 1`).

## Commands
```
python results/tester/438/own_sparse.py    # own codes/targets/sparse engine, 433 states x 3 pairs x 5 programs, native + lowered; recount; outer roles
python results/tester/438/aer.py           # Aer: 47 inner codes (F1,F2,F4,F5) x 4 pairs; F3: 12 seeded full 24-qubit states x 3 pairs
python results/tester/438/robust_stop.py   # stock worker rebuild (cache off), robust metrics, own stop-rule re-derivation
python results/tester/438/f3_mutation.py   # negative control on F3's outer control
tools/pytest-safe -n 2 -m "not slow" tests/acceptance/m8
tools/pytest-safe -n 2 tests/acceptance/m8 -k "G3 or L5 or R1" -v -rA
tools/pytest-safe -n 1 tests/unit -k lsh -q
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
```

## Results
Key = (CX, $T_{10^{-6}}$, depth$_{\rm CT}$, qubits). "Pairs" = $(\alpha,\beta)\in\{(0.37,0.61),(0.91,0.23),(1.7,1.0)\}$, plus $(1.13,0.47)$ where stated. Target = $U_BU_E$, op-norm distance up to a global phase.

| # | check | expected | got | tolerance | verdict |
|---|---|---|---|---|---|
| 1 | archive: 5 entries valid, key in entry = key in round file = key re-measured by the stock worker (fresh `evaluate_program`, cache off, full mode, fresh process) | F1 (73,1056,2125,25), F2 (80,1176,2423,26), F3 (76,1338,3056,24), F4 (74,1396,3218,24), F5 (73,1442,3159,25) | identical for all five (three ways); `reason ok`, skeleton equal, `alt_ok` = [true, true] for all; fresh `op_norm_error` 7.7e-15 / 1.6e-14 / 1.2e-14 / 1.3e-14 / 7.3e-15; certified, engine sparse | exact | PASS |
| 2 | program sha256: file on disk = archive entry = round file = fresh result | equal | equal for all five | exact | PASS |
| 3 | hashes: `evaluator_sha256 = encoding_sha256 = code_hash_for("lsh")` in round file, 5 entries, `robust.json` | `88e0d76bce7b3af635fc895b469d9b2db38c34a69d6ea86c3049f3f9526ec1ca` | equal everywhere (round, 5 entries, robust.json both fields); spec sha `a16c8a0a…` | exact | PASS |
| 4 | own sparse engine (own 24-bit codes from the 433 spin-network labels, own expm target, own gate walk, circuit as built with native `rccx`/`ch`), ALL 433 states $\times$ 3 pairs | $\le10^{-10}$ | max over 15 runs $6.4\cdot10^{-15}$ (F4); per program max: F1 $1.8\cdot10^{-15}$, F2 $5.6\cdot10^{-15}$, F3 $5.9\cdot10^{-15}$, F4 $6.4\cdot10^{-15}$, F5 $1.7\cdot10^{-15}$ | $10^{-10}$ | PASS |
| 5 | same engine on the FULLY LOWERED circuit (qiskit `decompose` to cx/h/s/sdg/t/tdg/x/z/rz/p/u/u1/u2/u3; rccx and ch expanded) | $\le10^{-10}$ and equal to 4 | max $6.4\cdot10^{-15}$; per program $2.8\cdot10^{-15}$ (F1), $2.9\cdot10^{-15}$ (F2), $5.9\cdot10^{-15}$, $6.4\cdot10^{-15}$, $2.7\cdot10^{-15}$ (F5) | $10^{-10}$ | PASS |
| 6 | wrong-sign control: same output block vs target at $-\beta$ | must disagree | 1.878, 0.888, 1.819 at the three pairs, for all five programs | $O(1)$ | PASS |
| 7 | unitarity of the 433$\times$433 block, $\|B^\dagger B-1\|_2$ | $\le10^{-10}$ | max $1.3\cdot10^{-14}$ (F2/F4 order $10^{-14}$, F1/F5 $\le2.2\cdot10^{-15}$) | $10^{-10}$ | PASS |
| 8 | dirty ancilla, leak out of the 433 codes, outer-register-changed weight, inner Abelian-Gauss-law violation (own Gauss operator: five valid site patterns and $N_n(c)=N_p(c+1)$ on the four inner links, asserted on the 433 input codes), worst column, 3 pairs $\times$ 2 forms | 0 | exactly 0.0 in all 5 programs $\times$ 3 pairs $\times$ native/lowered | $10^{-20}$ | PASS |
| 9 | Aer statevector on data + ancilla qubits for the 47 inner codes (own target from the L13 rules, own inner-code set via the Abelian Gauss law, outer register not simulated and asserted untouched by any gate) for F1, F2, F4, F5, 4 pairs incl. unused $(1.13,0.47)$ | $\le10^{-10}$ | op-norm error max: F1 $3.2\cdot10^{-15}$, F2 $4.1\cdot10^{-15}$, F4 $3.4\cdot10^{-15}$, F5 $3.2\cdot10^{-15}$; at the unused pair $\le3.4\cdot10^{-15}$; ancilla leak $\le4.5\cdot10^{-31}$; data weight outside the 47 codes 0; wrong sign $1.878$ | $10^{-10}$ | PASS |
| 10 | F3 reads outer qubit 13, so the inner-code Aer check is not sufficient: Aer on 12 seeded full 24-qubit random physical states (own 433 codes; 4 pure with bit 13 = 0, 4 pure bit 13 = 1, 4 mixed; sets of 151 / 282 states with bit 13 = 1 / 0), 3 pairs, expected $V\psi$ | $\le10^{-10}$ | max error $1.9\cdot10^{-15}$, $1.5\cdot10^{-15}$, $2.5\cdot10^{-15}$; weight outside the 433 codes $\le4.9\cdot10^{-15}$ (rounding); change of the outer-register weight distribution $\le4.0\cdot10^{-16}$; inner Gauss-law violation 0 | $10^{-10}$ | PASS |
| 11 | outer qubits are never written (all five): scan of the lowered gate list; Margolus/`rccx` claim | no gate other than a CX control touches 12..23 | F1, F2, F4, F5: no gate on qubits 12..23 at all. F3: only qubit 13, six gates, all CX with qubit 13 as control, no diagonal/other gate. Dynamic confirmation: outer-changed weight 0.0 on all 433 states (check 8) and $\le4\cdot10^{-16}$ on the random full states (check 10) | exact | PASS |
| 12 | F3 negative control (can the check fail?): delete the six `cx(13,0)`; or replace control 13 by data qubit 1 | must fail | error 0.180 and 0.601 against $5.8\cdot10^{-15}$ for the original; leak out of the physical codes 0.33 | $\gg10^{-10}$ | PASS |
| 13 | CX/T recount (own lowering by `decompose`, own pygridsynth $\varepsilon=10^{-6}$, multiples of $\pi/4$ counted as fixed, `u`-gate phases handled) vs archive | = archive | all five equal: (CX, $T_{\rm fixed}$, $N_{\rm rot}$, $T$, qubits) = F1 (73,40,16,1056,25), F2 (80,44,18,1176,26), F3 (76,24,21,1338,24), F4 (74,24,22,1396,24), F5 (73,40,22,1442,25) | exact | PASS |
| 14 | counts vs Qiskit `count_ops` | native + CX of `rccx` (3 each) + `ch` (1 each) = reported CX | F1 43+10$\cdot$3=73; F2 66+4$\cdot$3+2$\cdot$1=80; F3 76; F4 74; F5 43+10$\cdot$3=73; lowered `count_ops['cx']` equals 73/80/76/74/73; the $T_{\rm fixed}$ of check 13 comes from the same lowered lists | exact | PASS |
| 15 | depth$_{\rm CT}$ | = archive key | not independently recounted (its definition lives in `compress/metrics.py`); the fresh stock rebuild reproduces 2125 / 2423 / 3056 / 3218 / 3159 | exact | PASS (stock only) |
| 16 | robust keys: fresh `robust.robust_metrics("lsh","step",…)` (20 pairs, stock worker) vs `results/compress/lsh/robust.json`; angle-linear | equal | F1 (73,21088,0,43561,25); F2 (80,23692,0,50485,26); F3 (76,27086,0,60373,24); F4 (74,28348,0,63538,24); F5 (73,28626,0,62872,25); all equal, `angle_linear` True, `export_status ok` for all | exact | PASS |
| 17 | round file | 5 valid, 0 invalid, best key (71,1118,2276,25) = `r00-seed-005`, no external rows, synthesis verification null | exactly that; `lean_seconds` 0.0; wall 7.0 s | exact | PASS |
| 18 | stop record, own re-derivation (comparator from the stop-rule text; own session count $=$ 5 distinct (round, family) + 1 ideation; headline recomputed as the lexicographic minimum of the robust keys of all valid entries of rounds 0, 1) | headline r00-seed-005 (71,22480,0,46384,25), round 1 `improved` false, streak 1, sessions 6, `stop` false, reason null; `max_rounds` 8, `no_gain_rounds` 3, `max_sessions` 20 | file = own derivation in every field; `compress/ideation/lsh.md` exists | exact | PASS |
| 19 | proposer did not touch source: `git log -- src tests` since round 0 | no proposer commit | commit `89c00bc` changes five files, all `compress/programs/lsh/F*/001-*.py`; the only `src`/`tests` commit after `70ab721` is `2b7c68d` (audit 307, `rishon/lean_cert.py` + a rishon unit test), unrelated; no `src`/`tests` edit in the working tree | exact | PASS |
| 20 | provenance, informational: `git_dirty` | | round file True; entries F1 False, F2-F5 True (entries all carry commit `89c00bc`). Same pattern as the committed rishon/spinnet/fuzzy/twelve rounds: round files always True, entries mostly True, with an occasional False for the first entry (rishon r05, r06; LSH r01-F1). Cause: the loop writes tracked files (index, attempts, robust.json, earlier entries) during the round | | INFO |
| 21 | m8 acceptance, `-m "not slow"`, `-n 2` | green | 22 passed, 0 failed in 76.5 s (E1, E2, S0, S1$\times$8, S2, S3, S4, S5, H1, H3, U1, A1, A2, A4, L2); the PENDING tests are marked slow, so they are not in this selection | | PASS |
| 22 | m8 slow tests expected PENDING, run on purpose with `-k "G3 or L5 or R1"` | PENDING for G3 (stop reason), L5 (8.8), R1 (8.9/8.10) | all three fail on a missing later artefact: G3 passes the attempts, ideation, budget, contiguity, lineage, `sv["ok"]`, sessions ($6=5+1$), `improved` flags and streak assertions and fails only at `st["stop"] is True` (loop not finished: streak 1, stop false); L5: `lean/certs/lsh-best-step.lean` missing (step 8.9); R1: "PENDING: results/lsh/m8-compressed.json missing (step 8.10)" | | 3 PENDING |
| 23 | unit tests touching lsh, `tests/unit -k lsh` | green | 111 passed in 59 s | | PASS |
| 24 | lock: `check_lock.py`, `acceptance-check`, collection | OK | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v22`; 407 tests collected | | PASS |
| 25 | tree side effects | no tracked file changed by me; certs unchanged | `git status` before/after differs only by untracked `results/tester/438/`; `results/lsh/certs/` listing unchanged | | PASS |

## Verdict
PASS. 0 failed checks; 3 PENDING locked tests (M8-G3, M8-L5, M8-R1), each waiting for a later step; no new failure compared with report 437.

Counts: tester checks 24 PASS, 0 FAIL, 1 INFO; m8 not-slow 22 passed; m8 pending-by-design 3; unit lsh 111 passed.

Physics statement: all five round-1 programs reproduce the exact one-step target $U_BU_E$ on all 433 physical states to $\le6.4\cdot10^{-15}$ at three angle pairs (and the 47 inner codes to $\le4.1\cdot10^{-15}$ in Aer, also at a fourth unused pair), against $10^{-10}$ allowed, with no outer-register change, no ancilla residue, and no Gauss-law leak; the wrong-sign target is 0.89-1.88 away, and removing or re-pointing F3's outer control gives errors 0.18 and 0.60, so the checks can fail. None of the five beats the headline 71 CX (they cost 73, 80, 76, 74, 73), so the best stays `r00-seed-005`, streak 1.

## Observations (non-blocking)
- **O1.** Check 14 detail: the claimed F2/F3/F4 "real-phase Margolus instead of `rccx`" is true for F3 and F4 (no `rccx` in their gate list, 3 CX each in the lowered list); F2 still uses 4 `rccx` and 2 `ch`.
- **O2.** F3 is the only program with outer-dependent action: evaluator `method physical`, `outer_bits_read 1`, `n_blocks 2`; the 433-state sparse and full-state Aer checks cover that correctly. The inner-code (47) Aer check of the plan is not applicable to F3, so the seeded full-state check (check 10) replaced it, as the plan's rule says.
- **O3.** The proposers' DISCOVERY lines are claims; I confirmed only what is numeric above (Margolus exactness inside the circuits, class bit via raw parity not tested separately).
- **O4.** `index.json` elites: five new entries but four new cells, because F4 and F5 share the cell (49,83) and F5 (73 CX) displaces F4 (74 CX) there; F4 stays the best of its family (`families.F4.best`). Consistent with the entries' `cell` fields (checked).
- **O5.** pygridsynth emits float-angle `UserWarning`s in my scripts; harmless, same as earlier reports.
- Byproducts: `results/tester/438/` (4 scripts, 4 JSON, `__pycache__`); scratch logs in the session scratchpad; `compress/cache/` (gitignored) may have been refreshed by the stock `evaluate_program` calls only with `cache=False` (none written by me); nothing in `src/`, `tests/acceptance/`, archive or `results/lsh/certs/` was modified.
