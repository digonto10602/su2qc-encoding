# Tester report 016 — M1 step 1.1 codec (describe, import_map, audit 002 R2)

- Date: 2026-11-04
- Git commit: 7743b18 (milestone-0) + uncommitted step files `src/su2plaq/encodings/twelve.py`, `src/su2plaq/evaluate/evaluator.py`, `tests/unit/test_twelve_encoding_unit.py`, `tests/unit/test_evaluator_unit.py` (builder's parallel step 1.2 changes in `src/su2plaq/circuits/twelve.py` ignored; M1-E1 not judged here)
- Prompt in force: `prompts/004-leak-amplitude-combined-error-bound.md` (over `prompts/002`, `prompts/003`); plan 002 §4 row 1.1; `docs/METHODS.md` §3.2
- Mode: step
- Related: reports/tests/014 (M0 gate rerun), reports/audits/002 (R2)
- Raw numbers: `results/m1_step_1_1_codec_independent.json`; independent script `tests/independent/codec_1_1/check_codec.py`

## Commands
```
pytest -n auto tests/unit                                     # 143 passed in 58.9 s
pytest -n auto tests/acceptance/m1/test_twelve_codec.py       # 1 passed
pytest -n auto tests/acceptance/m0                            # 34 passed (incl. slow), 41.5 s, 0 skip/xfail
pytest -n auto tests/acceptance/m1                            # 4 passed, 16 pending (see below)
python tools/check_lock.py                                    # LOCK OK
~/.claude/bin/acceptance-check                                # PASS: matches acceptance-v4
PYTHONPATH=src:. python tests/independent/codec_1_1/check_codec.py results/m1_step_1_1_codec_independent.json
graphify update . ; graphify affected "evaluate"              # callers covered: M0-E3/E4/E5/E6 (m0, all run), M1-B*/E1/S1/T1/P1 (pending/other step)
```

## Results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| M1-C1 `test_M1_C1_codec_and_vectors` | pass | pass | locked | PASS |
| M0 acceptance incl. slow | 34 pass | 34 passed | - | PASS |
| unit tests | all pass | 143 passed | - | PASS |
| check_lock / acceptance-check (v4) | OK | LOCK OK / PASS | - | PASS |
| (1) `LINK_CODE` vs Paulo Eq. 31 (PDF p. 6): $\|0\rangle\to000$, $\|{+}{+}\rangle\to111$, $\|{+}{-}\rangle\to110$, $\|{-}{+}\rangle\to101$, $\|{-}{-}\rangle\to100$ | equal | equal; also rebuilt from bit definitions ($q_j$=bit 2, $q_m$=bit 1, $q_{m'}$=bit 0) | exact | PASS |
| (1) notebook `LINK_CODE=[0,4,5,6,7]` (notebook colour index = bit value) | = $[0,{-}{-},{-}{+},{+}{-},{+}{+}]$ codes | equal | exact | PASS |
| (1) don't-care codes | 001, 010, 011 | $\{1,2,3\}$ | exact | PASS |
| (1) registers: link $l$ = qubits $(3l,3l+1,3l+2)$, outer $k$ = $(12+2k,13+2k)$ | as METHODS §3.2 | equal | exact | PASS |
| (1) `near_end` per outer link, from independent geometry (end at corner site -> R, start -> L) | R R L R L L R L | R R L R L L R L | exact | PASS |
| (1) outer 2-qubit code $(q_m,q_j)$: $j=0\to00$; $j=\frac12$: $q_j=1$, $q_m=1$ iff $m_{\rm near}=+$, far label $-$; own table vs class, all 8 links x 5 labels; $01$ invalid | equal | equal | exact | PASS |
| (2) own decode (own tables + $s(m)s(m')|{-}m,{-}m'\rangle_{CG}$) vs `decode` on 625 inner codes | equal | equal, 625 distinct keys | exact | PASS |
| (2) decode∘encode = identity on 625 keys; encode∘decode = identity on 625 codes | identity | identity | exact | PASS |
| (2) remaining inner codes decode to `None` | 3471 (= 4096 − 625) | 3471, all `None` | exact | PASS |
| (2) 433 vectors: $\max\|\,\|\psi\|-1\|$ | 0 | $1.6\times10^{-15}$ | $10^{-12}$ | PASS |
| (2) full 433x433 Gram, $\max\|G-\mathbb 1\|$ (not a sample) | 0 | $3.0\times10^{-15}$ | $10^{-12}$ | PASS |
| (2) Gauss residual, own decode + own spin-1/2 generators (L = $-J^T$ on $m_L$ for 'out', $J$ on $m_R$ for 'in'), 4 corners x 3 gens x 433 | $\le10^{-10}$ | $5.4\times10^{-16}$ | $10^{-10}$ | PASS |
| (2) own decode = repo `decode_state` incl. signs, all 433 | equal | equal ($<10^{-14}$) | - | PASS |
| (3) `describe()` numbers (12/16/28 qubits, 625, 433, near ends, codes, qubit tuples) | derivable | all derived from the class (`n_data`, `n_outer`, `inner_codes()`, `basis.labels`, `_near`, `LINK_CODE`); the only literals are "5^4" and "001, 010, 011", both correct | - | PASS |
| (3) `import_map` registers: paulo34 = 34 = 12 data + 22 anc (qpy registers d,p,e,w,g,tmp,h = 12+4+4+7+3+3+1; metadata 294 CX, 1162 T) | match | 34 qubits, qpy regs equal, metadata equal | exact | PASS |
| (3) lean22 = 12+10 = 22, lean22_v2 = 12+7 = 19 (su2qc-trotter docs) | match | match | exact | PASS |
| (3) qubit maps injective, data 0..11 identity, ancillas ≥ 28 | yes | injective for all 3 sources, min ancilla 28, max 49 | exact | PASS |
| (3) `spinnet15` returns a reason string; unknown source raises `ValueError` | yes | yes (not exercised by me beyond printing) | - | PASS |
| (4) R2: aer_mps, tol 5e-10 / 5e-10 | `certified=False`, `ok` | ok, False | - | PASS |
| (4) R2: aer_mps, 9.99e-10 | False | False | - | PASS |
| (4) R2: aer_mps, 1e-9 / 1e-9 | True | True | - | PASS |
| (4) R2: mixed (tol_err 1e-9, tol_gauss 5e-10) and (5e-10, 1e-9) | False (min < 1e-9) | False, False | - | PASS |
| (4) R2: aer_mps 1e-6; 1e-10 | True; False | True; False | - | PASS |
| (4) R2: sparse at 5e-10, 1e-10, 1e-12 | True (acc = 0) | True x3 | - | PASS |
| (4) R2: `gauss=False`, aer_mps tol_err 5e-10 / 9.9e-10 / 2e-9 | False / False / True | False / False / True | - | PASS |
| `engine_accuracy` unchanged | $2\times10^{-10}$ | $2\times10^{-10}$ (M0-E5 still green) | - | PASS |

## Pending (not failures; step 1.2+ not built or later steps)
M1 acceptance in this tree: 4 passed (C1, E1[0.37], E1[0.91], T1[UE]); 16 raise "not built yet"/fail for later steps, listed by cause:
- `build_UB is not built yet`: B1 (0.4, 1.0, 2.0), B2, B3, B4, S1[1], S1[2], T1[UB], P1 (partly: `paulo_logical`/`paulo_circuit`), P2
- `build_step is not built yet`: T1[step] and S1
- results files `results/twelve/{UE,UB,step}.json` missing: R1 x3 (step 1.9)
- `test_M1_O1_outer_dont_care_table`: `3153 == 6561` (known, STATUS: s_o_dims full table, fix in step 1.8)
- M1-P1/P2 need `paulo_logical`/`paulo_circuit` (step 1.6).

PASS counts for M1 are therefore not claimed beyond C1 (E1[*], T1[UE] passed incidentally and belong to step 1.2).

## Notes (not failures)
- Paulo's PDF text says "4096 − 625 = 3470 don't care states"; the true count is 3471 (verified: 3471 inner codes decode to `None`). Paper typo, harmless.
- `describe()` and `import_map()` assert two things I cannot verify at this step: the lean22/lean22_v2 angle map ($\alpha_P=2\beta$, electric phase $p(-3\alpha/4)$ on each $q_j$) and that the outer register is read-only for circuits. Both are used by locked M2 tests and M1-B4; re-check when step 1.2/1.5 and M2 import land. For paulo34, $\alpha_P=2$ i.e. $\beta=1$ is consistent with Paulo's metadata ($dt=a=g_s=g_t=1$, $\alpha=2dt/(g_sg_ta)$).
- `describe()` has an unused local variable `inv` (cosmetic).
- Added (not under `tests/acceptance`): `tests/independent/codec_1_1/check_codec.py`; its output `results/m1_step_1_1_codec_independent.json` (commit 7743b18, deterministic, no random numbers).

## Failures
None.

VERDICT: PASS
