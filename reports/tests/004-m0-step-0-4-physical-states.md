# Test report 004 — M0 step 0.4, physical states (route A)

- Date: 2026-11-04
- Commit: 893cd3e (step files uncommitted: `src/su2plaq/exact/physical.py`, `src/su2plaq/exact/spinnet.py`, `tests/unit/test_import.py`, `tests/unit/test_physical_unit.py`)
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md`, §2 Interface (physical), §3 row 0.4; method `docs/METHODS.md` §4
- Mode: step
- Related: `reports/tests/003-m0-step-0-3-algebra.md`
- Raw numbers: `results/independent_check_physical_0_4.json` (seed 20261104, commit 893cd3e); independent script `tests/independent/check_physical_0_4.py` (not collected by pytest, added by the tester)

## Commands

```
source ~/anaconda3/etc/profile.d/conda.sh && conda activate coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify query "physical_basis corner_singlets gauss_residual to_convention" ; graphify affected "physical_basis"
pytest -n auto tests/unit -q
pytest -n auto -m "not slow" tests/acceptance/m0 -q          # + plain run to classify failures
pytest tests/acceptance/m0/test_physical.py -q --durations=0  # includes slow C6
pytest -n auto tests/acceptance/m1 tests/acceptance/m2 -q
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
grep -rnE "\b(433|256|95|17362|17 362|65250|65 250)\b" src/
python tests/independent/check_physical_0_4.py                # ~20 s
```

`graphify affected physical_basis` lists only `tests/unit/test_physical_unit.py` (6 tests); all of them ran and pass.

## Verdict: PASS

## Test results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| unit tests | all pass | 61 passed, 6.4 s | - | PASS |
| M0-C1 dimension, labels = route B, Paulo round trip + Gauss | pass | pass, 2.5-2.9 s | exact / 1e-14 / 1e-10 | PASS |
| M0-C2 closed | 2 | pass | exact | PASS |
| M0-C3 link strings | 256 | pass | exact | PASS |
| M0-C4 ambiguous | 95 | pass | exact | PASS |
| M0-C5 far-end weighted | 17 362 | pass | exact | PASS |
| M0-X1 Gauss and Gram | 1e-10 / 1e-12 | pass, 2.3 s | - | PASS |
| M0-C6 jmax=1 (slow) | 65 250 labels, 3 closed | pass, 2.8 s | exact | PASS |
| regression m0: A1 (x2), A2, A3, G1, G2 | pass | pass | - | PASS |
| acceptance m0 non-slow overall | - | 12 passed, 20 PENDING (NotImplementedError only: `TwelveQubit` 3, `h_magnetic_phys` 8, `pygridsynth_word` 3, `run_batch` 2, `ct_compile`, `h_electric_inner`, `logical_metrics`, `save_result`), 0 real failures | - | OK |
| m1 + m2 | PENDING | 51 not passing: 48 PENDING + 3 known M1-R1 `missing results/twelve/{UB,UE,step}.json` | - | as expected |
| `tools/check_lock.py`, `acceptance-check`, collect-only | pass | LOCK OK; "matches acceptance-v2"; 84 collected | - | PASS |
| grep hard-coded 433/256/95/17362/65250 in `src/` | none | none | - | PASS |

Counts: passed 12 (m0) + 61 (unit) + C6; failed 0; pending 20 (m0) + 48 (m1/m2) + 3 known M1-R1; new failures vs report 003: none.

## Independent physics (own script; geometry, Casimirs, generators, Gram, Paulo basis built from scratch)

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| (1) route-independent count, product over 4 corners of numerically diagonalised total-Casimir singlet dimension, 4096 spin assignments: dim | 433 | 433 | exact | PASS |
| closed | 2 | 2 | exact | PASS |
| link strings | 256 | 256 | exact | PASS |
| ambiguous | 95 | 95 | exact | PASS |
| far-end-weighted | 17 362 | 17 362 | exact | PASS |
| builder's per-string multiplicity (Counter of `labels[k][0]`) = independent per-string product | equal | equal for all 256 strings | exact | PASS |
| `python3 -I refs/su2_plaquette_encodings.py` | 2 / 433 / 17362 / 256 / 95 | same | - | PASS |
| (2) Gauss, own L = -J^T on m_L, R = +J on m_R, all 4 corners, a = 1..3, 60 random states | <= 1e-10 | 5.2e-16 | 1e-10 | PASS |
| negative control, one sign flipped on the 1296-component state | residual >> 1e-10 | 0.056 | - | PASS |
| Gram of all 433, own sparse matrix | <= 1e-12 | $\max\lvert G-1\rvert = 7.3\times10^{-15}$ | 1e-12 | PASS |
| keys unique per state; max components; Im part; far-end index fixed to $+\tfrac12$ (own derivation from link directions) | 1296; 0; 0 violations | 1296; 0.0; 0 | - | PASS |
| completeness: for 18 sampled spin strings (4 ambiguous) the nullity of own $\sum_{c,a}(G^a_c)^\dagger G^a_c$ on the far-fixed subspace (dim $\le 2048$) equals the number of basis states | equal | equal for all 18 | exact | PASS |
| (3) own Paulo generators (from $V_P$) vs Paulo Eq. 28 $\tilde U$: $[L_a,\tilde U_{ij}]=-(T_a\tilde U)_{ij}$, $[R_a,\tilde U_{ij}]=+(\tilde UT_a)_{ij}$ | 0 | 0.0 | 1e-12 | PASS |
| `to_convention(cg->paulo)` equals my own signed permutation, 60 states | 0 | 0.0 | 1e-14 | PASS |
| round trip CG -> Paulo -> CG on all 433 (amplitudes, keys, labels) | identity | max diff 0.0 | 1e-14 | PASS |
| Gauss with Paulo-basis generators on Paulo states, 60 samples | <= 1e-10 | 5.2e-16 | 1e-10 | PASS |
| (4) `s_o_dims` table: entries with support, own SVD rank per outer key | agree | 3153 = 3153, all equal | rank tol $10^{-9}$ | PASS |
| closed pattern (outer key 0) dim $S_o$ | 2 | 2 | exact | PASS |
| rank of $\mathrm{span}_oS_o$ (`inner_span`) | report | **625** (own SVD: 625; builder `inner_span` shape (625, 625); smallest kept singular value 0.111, next 0) | - | reported |
| all inner components lie in `inner_span` | 0 | $1.3\times10^{-15}$ relative | - | PASS |

Histogram of $\dim S_o$ over the 3153 outer patterns with support (of $3^8=6561$ possible; the other 3408 are empty, so the builder's table has 3153 entries, "zeros allowed" per plan):

| dim $S_o$ | 1 | 2 | 3 | 4 | 5 | 8 | 9 | 17 |
|---|---|---|---|---|---|---|---|---|
| number of outer patterns | 976 | 1073 | 392 | 320 | 280 | 64 | 32 | 16 |

(sum 3153.) Maximum 17.

## What this means for plan claim (i) (§ risk list: "inner-span rank < 625")

The measured rank is the full 625: the union over outer patterns of inner supports spans the whole 625-dimensional inner code space. So there is no extra inner-register don't-care freedom beyond the per-outer-pattern structure: an outer-blind circuit must act correctly on all of $\mathbb C^{625}$ restricted per pattern to $S_o$ only if it reads the outer bits; the outer-conditioned freedom is the table above (e.g. 976 patterns have 1-dimensional $S_o$, 16 have 17).

## Caveats

1. The "Gauss law preserved under `to_convention`" check cannot discriminate conventions by itself. In my script even dropping the signs $s(m)s(m')$, or dropping the permutation, leaves the Gauss residual at 2.6e-16 with Paulo-basis generators. Reason (my analysis): these maps are products of per-corner global rotations / conjugation, which map singlets to singlets. The discriminating evidence for the convention is therefore (a) exact equality with my own transform built from METHODS §3.1 (0.0 deviation) and (b) the Paulo-basis generators obeying the Eq. 28 commutator identities (0.0). Acceptance test C1 has the same blind spot (no defect in the code).
2. The independent completeness check covers 18 of 256 spin strings (those with a far-fixed subspace of dimension $\le 2048$; larger ones, up to 65 536, were skipped for cost); the global count check (1) covers all 256.
3. The independent script reads the COO (`keys`, `amps`, `labels`) of the object under test by construction; everything else is independent.
4. Wall times: `physical_basis` build 0.29 s (cached across the process; tests re-use `lru_cache`), C1 2.5-2.9 s, X1 2.3 s, C6 2.8 s, whole `test_physical.py` 8.1 s serial.

## Failures

None.
