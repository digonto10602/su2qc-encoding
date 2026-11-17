## Table 1. Gate counts of the first-order inner step (source: gate-table.json)

Blocks: A = Kogut-Susskind j_max = 1/2 (same 433 states, like for like); B = SU(2) quantum link model + det term; C = fuzzy gauge theory. Rows of blocks B and C are a different model: compare within the row only.

| block | encoding | model | qubits | general CX | general rot | general fixed T | general T(1e-6) | headline entry | headline qubits | headline CX | headline T nominal | headline T_avg | angle-linear | Lean | CX general/headline | T general/T_avg | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | twelve | Kogut-Susskind, j_max = 1/2 | 34 | 294 | 10 | 312 | 952 | pending | - | - | - | - | - | - | - | - | pending: no cached headline for twelve: no cache file results/compress/twelve/robust.json; waits for prompts/008 Phase C replay (M2c gate) |
| A | spinnet | Kogut-Susskind, j_max = 1/2 | 15 | 54 | 8 | 56 | 566 | pending | - | - | - | - | - | - | - | - | pending: no cached headline for spinnet: results/compress/spinnet/robust.json is present but stale for the current code hash; waits for prompts/008 Phase C replay (M2c gate) |
| A | lsh | Kogut-Susskind, j_max = 1/2 | 19 | 94 | 8 | 88 | 598 | pending | - | - | - | - | - | - | - | - | pending: no cached headline for lsh: the lsh archive has no ranked valid entry; waits for the LSH loop (M8 phases 1-2, prompts/401) |
| B | rishon | SU(2) quantum link model + det term (different model) | 26 | 10134 | 174 | 10218 | 21146 | pending | - | - | - | - | - | - | - | - | pending: no cached headline for rishon: results/compress/rishon/robust.json is present but stale for the current code hash; waits for prompts/008 Phase C replay and Report 6 (prompts/204-205); results/compress/rishon/three-layer.json missing (prompts/204 step C5; Report 6) |
| C | fuzzy | fuzzy gauge theory, K1 + r K2, r = 1 (different model) | 23 | 1862 | 56 | 1826 | 5398 | pending | - | - | - | - | - | - | - | - | pending: no cached headline for fuzzy_ub: no cache file results/compress/fuzzy_ub/robust.json; waits for prompts/008 Phase C replay (M2c gate) and prompts/010 step H.2; no cached headline for fuzzy_link: no cache file results/compress/fuzzy_link/robust.json; waits for prompts/008 Phase C replay (M2c gate) and prompts/010 step H.2 |

Ratios between blocks are not efficiency statements: the rows describe different theories on the same lattice.

Rishon three-layer step with det layer: pending; general two-layer step (results/rishon/step.json): CX 10102.
Fuzzy unit fuzzy_ub: pending
Fuzzy unit fuzzy_link: pending

## Table 2. CX first against T first (source: gate-table.json; figure results/crosscheck/tradeoff.pdf)

| encoding | headline (CX, T_avg) | T-first pick (entry, CX, T_avg) | general (CX, T(1e-6)) | Pareto points (CX, T_avg) |
|---|---|---|---|---|
| twelve | pending | pending | 294, 952 | pending |
| spinnet | pending | pending | 54, 566 | pending |
| lsh | pending | pending | 94, 598 | pending |
| rishon | pending | pending | 10134, 21146 | pending |
| fuzzy | pending | pending | 1862, 5398 | pending |

The project ranks CX first (prompts/001 §1).

## Table 3. Spectra cross-check (source: spectra.json)

### 3a. Same model (twelve, spinnet, LSH)

Largest level difference between the three Kogut-Susskind encodings: g^2 = 0.5: 2.8e-14, g^2 = 1.0: 1.2e-14, g^2 = 2.0: 2.7e-14; largest transported-target difference 3.0e-15.

| circuit | target | kind | entry | alpha, beta | ok | certified | total error | rejected mutant (beta + 1e-6) block error |
|---|---|---|---|---|---|---|---|---|
| twelve | lsh | general | None | 0.37, 0.61 | True | True | 2.7e-13 | 2.0000e-06 (ok=False) |
| spinnet | twelve | general | None | 0.37, 0.61 | True | True | 1.1e-14 | 2.0000e-06 (ok=False) |
| lsh | spinnet | general | None | 0.37, 0.61 | True | True | 1.6e-14 | 2.0000e-06 (ok=False) |
| twelve | spinnet | headline | pending | - | - | - | - | no cache file results/compress/twelve/robust.json; waits for prompts/008 Phase C replay (M2c gate) |
| spinnet | lsh | headline | pending | - | - | - | - | results/compress/spinnet/robust.json is present but stale for the current code hash; waits for prompts/008 Phase C replay (M2c gate) |
| lsh | twelve | headline | pending | - | - | - | - | the lsh archive has no ranked valid entry; waits for the LSH loop (M8 phases 1-2, prompts/401) |

### 3b. The KS link is a compression of the model link

| model | largest residual (isometry, U, L, R, H_E, plaquette) | squared leak U | squared leak plaquette |
|---|---|---|---|
| rishon_plus | 4.7e-16 | 0.5 | 15 |
| rishon_minus | 4.7e-16 | 0.5 | 15 |
| fuzzy_one | 3.1e-16 | 0.5 | 4.125 |
| fuzzy_gamma5 | 3.1e-16 | 0.5 | 4.125 |
| fuzzy_fplus | 4.7e-16 | 1 | 4 |
| fuzzy_fminus | 4.7e-16 | 1 | 4 |

### 3c. Limits

Rishon model -> Kogut-Susskind limit (c_E = g^2/2 - 8L/3, c_B = 1/g^2, lam_D = -L; our derivation, error ~ 1/L):

| g^2 | L | L x max level deviation (433 lowest levels) | gap to the next band |
|---|---|---|---|
| 0.5 | 64 | 7.0814 | 246.48 |
| 0.5 | 128 | 7.0947 | 502.47 |
| 1.0 | 64 | 2.1988 | 248.75 |
| 1.0 | 128 | 2.1972 | 504.74 |
| 2.0 | 64 | 0.7487 | 246.41 |
| 2.0 | 128 | 0.7465 | 502.40 |

Physical-state projection: 305 blocks, largest 4352; dropped code images H_B/H_D: 0/0 (weight 0.0e+00/0.0e+00).

Fuzzy model, K1 only: 2 of 16 flavour sectors reproduce the KS 2 x 2 closed block; isolated-plaquette gap exponent 7.0004 (K2 only), 7.0286 (r = 1); strong-coupling gap / 2g^2 = 0.9999973 at g^2 = 16.

### 3d. Closed-sector levels side by side -- different models: these numbers are not expected to agree

- g^2 = 0.5: KS 2 levels, lowest -3.6425; rishon 17 levels, lowest -10.9449 (lam_D = 0); fuzzy 9 (r = 0) / 12 (r = 1) levels, lowest -15.2530 / -15.2638.
- g^2 = 1.0: KS 2 levels, lowest -1.3860; rishon 17 levels, lowest -4.9564 (lam_D = 0); fuzzy 9 (r = 0) / 12 (r = 1) levels, lowest -6.5251 / -6.6389.
- g^2 = 2.0: KS 2 levels, lowest -0.3028; rishon 17 levels, lowest -1.7016 (lam_D = 0); fuzzy 9 (r = 0) / 12 (r = 1) levels, lowest -1.2941 / -8.0692.

### 3e. Not comparable (different models)

- State counts: 433 (Kogut-Susskind) / 38432 (rishon) / 101197218 (fuzzy, fixed far ends).
- Spectra at equal g^2 outside the limits of 3b-3c; one-step unitaries and the shared observables of Reports 5 and 9; gate counts across blocks; any continuum-limit claim.
- Rishon step at operator-norm distance 1.990 from the KS step (results/rishon/ks_projection.json: variants.plus.check3_step.circuit_rishon.vs_KS_exact_nominal.op_norm_after_gauge).

Sources: results/crosscheck/gate-table.json, results/crosscheck/spectra.json.
