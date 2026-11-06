# Report 037 — M2: Lean fixes N5/N6 and step 2.L6 (structure certificate) (tester, mode `step`)

- Date: 2026-11-06
- Git: tested on uncommitted working tree on top of `3576705`; locked tests `acceptance-v7`.
- Plan in force: `prompts/006` (§4, §5, row 2.L6). Related: reports/tests/036 (N5/N6 were notes there), 031, 028.
- Raw numbers: `results/tester_m2_lean_n5n6_2l6.json`; scripts `tests/independent/lean_n5n6_2l6/` (not collected by pytest, seeds inside).
- Machine: 12 cores, load average 10–32 during the run (other agents running), so all wall times are upper bounds.

## VERDICT: PASS (notes N1–N5 below; no failure)

## 1. Commands
```
cd lean && lake build ; lake build Su2PlaqCert su2plaq_cert (after touching Pins.lean)
pytest -n 4 tests/unit
pytest tests/acceptance/m2/test_lean_structure.py tests/acceptance/m2/test_lean_formal.py -rA --durations=12
pytest -n 4 -m "not slow" tests/acceptance/m0 tests/acceptance/m1
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
python tests/independent/lean_n5n6_2l6/{sha_test,n5_n6_attacks,bypass_theorems,struct_tamper,inner625_and_sym,structure_json_check}.py
(+ mkcerts2.py from tests/independent/lean_2l4/r2 to produce the UE/UB/step-1/step-2 certificates; lake env lean on 14 bypass theorem files)
```

## 2. Required checks
| check | expected | got | tolerance | result |
|---|---|---|---|---|
| `test_lean_structure.py` 4 ids (`counts_kernel_checked`, `structure_certificate_accept_reject`, `structure_json_and_spec_section`, `symmetry_candidates_verified`) | pass | 4/4 pass (certificate test 70 s) | – | PASS |
| other Lean ids of `test_lean_formal.py` (project_present, generic_theorems, checker_semantics, small_accept_reject_na, general_circuit, theorem_file_general) | pass | 6/6 pass (theorem_file_general 419 s) | – | PASS |
| `polish_rules`, `program_lemma`, `round_records`, `archive_best` | later steps 2.L7/2.L8 | fail with 2.L7/8 content (`LEAN_RULES` empty, `NotImplementedError: check_program_lemmas`, `lean=None`) | – | PENDING (4) |
| full unit suite | pass | 389 / 389 (869 s) incl. the 60 Lean unit tests (cert + structure + project files) | – | PASS |
| m0 + m1 non-slow | pass | 54 / 54 (161 s) | – | PASS |
| `lake build` | green | green, 9095 jobs | – | PASS |
| `Su2PlaqCert` has no Mathlib | no import | `grep Mathlib lean/Su2PlaqCert*` hits only doc comments; no `import Mathlib` | – | PASS |
| `pytest --collect-only tests/acceptance` | clean | 102 tests collected | – | PASS |
| `tools/check_lock.py` / `acceptance-check` | OK | `LOCK OK` / `PASS: matches acceptance-v7` | – | PASS |

No new failures versus report 036 (same 4 pending ids).

## 3. Independent checks
### 3.1 SHA-256 in Lean vs `hashlib` (`su2plaq_cert sha256`, seed 20261105)
618 messages: every length 0..300 twice (random bytes and constant fill), padding boundaries 511/512/513/1023/1024/4095/4096/65535/65536/65537, and 1 000 000 / 3 000 000 / 5 000 001 bytes (1.1 s for 5 MB), plus the `""` and `"abc"` known answers: **0 mismatches**. PASS.

### 3.2 N5 — fake bases and wrong targets (UE certificate, 44 cases, `n5_n6_attacks.py`)
Each case goes through the bare Lean checker, `check_certificate`, `write_theorem_file`.
| class | cases | Lean alone | `write_theorem_file` |
|---|---|---|---|
| A: 433 orthonormal non-physical states (computational basis; shifted codes); physical pair rotated by 90° | 3 | all REJECT "states differ from the pinned exact physical basis (SHA-256)" | refused 3/3 |
| B: physical states permuted (swap contents of 2 states, swap `k` fields, reverse all, random permutation of all 433) | 4 | all REJECT (SHA-256) | refused 4/4 |
| C: one state altered (copy of another: "not orthogonal"; sign flip of states 0, 50, 200, 432; times i; term deleted: "not normalised"; zero-coefficient term; 432 and 434 states) | 11 | all REJECT | refused 11/11 |
| D: other target (UE blocks labelled UB / step-1 / step-2; UB blocks with kind UE and kind UB; unknown kind; one coefficient changed; two blocks swapped; base doubled without scaling exponents) | 10 | all REJECT (SHA-256 or "base is not a multiple" / "exponent not divisible") | refused 9/10 (see N1: `no kind` writes a file) |
| step certificates (Lean only): step-o1 relabelled order 2, step-o2 relabelled order 1, step-o1 with step-o2 blocks, with UB blocks | 4 | all REJECT | – |
| N6 malformed rationals (`1/0` in state, target, phase; `0/0`; `1/-2`; `"1 /2"`; `1/2/3`; empty; JSON float; zero base) | 10 | all REJECT with a reason, no crash | refused for state/target/denominator ones; see N1 |
| controls (must ACCEPT): unchanged; terms/states shuffled in file; terms rotated; whole certificate rescaled to base (8,4) | 4 | 4/4 ACCEPT, `check_certificate` certified, theorem file written | – |
| accepted although mutated | 2 | `d_beta` tripled / set to 0 on a UE certificate: ACCEPT, which is correct (UE has no β exponent anywhere; the base only relabels an unused variable; theorem file elaborates, N2) | – |

Totals: 38 mutations rejected by Lean alone, 4 controls accepted, 2 benign accepts. Python `check_certificate` agreed with Lean in all 44 cases (no exception escaped).

**Bypass test (Lean's pins as the only defence).** With `_exporter_mismatch` monkeypatched out in my own process, 14 theorem files were written and elaborated with `lake env lean`: 11 mutated ones (fake states, swapped states, state 50 sign flip, state 50 times i, UE blocks as UB, UB blocks as UE, one target coefficient, no kind, `1/0` in phase, `1/0` in a state, huge exponent in a gate) all fail with "`native_decide` evaluated that the proposition ... is false"; the 3 true ones (unchanged, rescaled base, d_beta tripled) elaborate with `#print axioms` = `[propext, Classical.choice, Quot.sound, <name>._native.native_decide.ax_1_1]`. So the pins really are checked inside the compiled `native_decide` (SHA-256 evaluated in Lean). 20–70 s per file under load.

**Positive controls on all four targets.** Honest certificates of $U_E$ (4 gates, 3.4 s), $U_B$ (233 gates, 113 s), step order 1 (237 gates, 139 s) and step order 2 (241 gates, 134 s) are ACCEPTed by the bare checker with the pins active (`certify_circuit_kind`: all `certified`).

**`Pins.lean` regenerates identically**: `render_lean(compute_pins())` equals the file byte for byte; the Lean `fingerprint` command on the UE/UB certificates prints exactly the pinned states/UE/UB hashes (states `45be4cd3…58fe3b`, UE `521639b6…78160d`, UB `f8dcc062…3a94`).

### 3.3 Structure certificate (`su2plaq_cert structure`, 90 s on the exact certificate under load)
76 single-field cases (`struct_tamper.py`): **72 tampers REJECTED, 4 controls ACCEPTED** (unchanged, `states` list shuffled with `k` kept, all gauge signs flipped, spectrum untouched copy). Each tamper was rejected for a matching reason:
| group | cases (all rejected) | typical reason |
|---|---|---|
| $K_{\rm inner}$ | bright 2→1 (consistent and K only), ½→1, sign flip, asymmetric entry, dark rows 4,8 made bright (consistent and K only), dark row removed/duplicated, bright row listed dark, pair dropped/duplicated/re-indexed, gauge flip on one state, gauge 0 | "H_B[0,352] differs from D K_inner D", "K_inner does not conserve J_c", "partition", "gauge must be ±1" |
| spectrum | −2: 16→17; 0 and ½ shifted; two swapped; label −½→−¾; entry dropped; +2: 16→15 | "spectrum multiplicities differ: recomputed (−2,16)(−1,96)(−½,16)(0,177)(½,16)(1,96)(2,16)" |
| symmetries | sign flip in identity/C4/identity on a bright state; two perm entries swapped; duplicate entry; sign 0; truncated; out of range; cc replaced by a swap | "does not commute with H_B" / "not a signed permutation" |
| states/Gauss/labels | one term sign-flipped, one digit changed, term deleted, state replaced by copy, state removed, coefficient 1/3, state replaced by a non-Gauss basis vector, m shifted; label $J$ wrong (corner 0, corner 3), label $j$ wrong, inner label wrong/removed | "Gauss law fails at corner 3", "not normalised", "not orthogonal", "inner-pair spin differs from its label" |
| outer support | 3153→3152; 17→16, 17→18, 17→9 | "outer support differs: 3153 patterns, max 17 states" |
| inner 625 | edges 128→127; modulus ½→1; extra modulus; component 17→16; count 464→465; spectrum 543/24 and ±2 altered; $U^{\rm Paulo}$ entry; $V$ sign flip; $V$ not a permutation | matching reason each |
| corners | dim changed (0→1, 1→2), entry dropped ("give 315 states, not 433"), role flipped, link changed | "Casimir kernel dimension differs", "Gauss law fails" |
| algebra / schema | $U_{ij}$, $L$, $R$, $S$ entry changed; wrong schema; missing field | "not covariant", "su(2) relations" |
| N6 | `x/0` in a state, in $U$, in $K_{\rm inner}$, in the spectrum | "zero denominator in …" |

Independent facts behind the accepted claims (numpy, own code, `inner625_and_sym.py`; project float route A for $H_B$):
| quantity | expected (reports/tests/006, 020, 004) | got | result |
|---|---|---|---|
| $H_B$ spectrum multiplicities of $-2,-1,-\tfrac12,0,\tfrac12,1,2$ | 16, 96, 16, 177, 16, 96, 16 (sum 433) | 16, 96, 16, 177, 16, 96, 16 (sum 433) | PASS |
| $K_{\rm inner}$ | 8 bright pairs, couplings 2, 1×6, ½; 31 dark | $H_B$ graph has max degree 1, 128 edges with moduli 2×16, 1×96, ½×16 (= 16+96+16 states pairs), 177 isolated states; $\big||H_B[k,l]|-|K[\iota_k,\iota_l]|\big|\le 8.9\times10^{-16}$ with the certificate's $K$ and labels; $H_B$ only joins equal $J_c$; diag 0 | PASS |
| outer support | 3153 patterns, max 17 | 3153, 17 | PASS |
| states per outer pattern vs $\dim S_o$ | not to be conflated | the two histograms (1:976, 2:1073, 3:392, 4:320, 5:280, 8:64, 9:32, 17:16) happen to coincide numerically; the facts file claims only the two numbers 3153 and 17, and its note says "NOT dim S_o" | PASS (see N3) |
| 625-code inner operator $-(W+W^\dagger)$ (own $U^{\rm Paulo}$, Kronecker products) | 128 edges, all modulus ½, spectrum ±2(1) ±1(24) ±½(16) 0(543) | 128 edges, no diagonal, modulus {0.5}, Hermitian err 0, components 1×464, 2×16, 4×8, 5×16, 17×1, spectrum −2:1, −1:24, −½:16, 0:543, ½:16, 1:24, 2:1 (no eigenvalue outside the set); equals every claim in the certificate | PASS |
| 16 symmetries on the 433 states (signed permutation $S$, $S H = H S$) | commute with $H_B$ and $H_E$ | max $\lVert[S,H_B]\rVert_\infty=8.9\times10^{-16}$, $\lVert[S,H_E^{\rm inner}]\rVert_\infty=0$, outer electric energy invariant, $S^TS=1$ to 0; each induces a link permutation preserving the corner incidence structure and mapping inner links to inner links; negative controls (one sign flipped, two states swapped) give 4.0 and 2.0 | PASS |
| certificate labels vs project labels | same | identical (433 labels, order) | PASS |

### 3.4 `structure.json` schema and downgrade
- On disk: facts `card_physical … dont_care_codes` (8, `decide`) with theorem name `Su2Plaq.<name>` whose statement in `Counts.lean` carries the same number (433, 256, 95, 2, 17362, 3153, 17, 3471); 6 `native` facts with a certificate reference; provenance `structure_certificate: certified`; recorded `checker_sha256` equals the sha256 of the current binary (`60d47ce3…`); every fact has `name,value,proved_by,note`; 16 symmetries.
- With `check_structure` forced to return `rejected` (and to `failed`), `write_structure_json` writes all six native facts as `numerical`, records the status and reason, and the rendered spec then lists only the 8 `decide` facts (numerical ones are skipped). With the real file the spec section shows all 14. PASS.

## 4. Notes (non-blocking, nothing failed)
- **N1** `write_theorem_file` only compares states and a target that carries a `kind`; for a certificate whose target has no `kind` (or a wrong gate list, bad phase) it still writes the file. Lean's own pins and checks then fail at `native_decide` (verified for no-kind, `1/0` in phase, huge gate exponent), so no wrong theorem can be obtained; the refuse-early behaviour is just not complete. Guess: `_exporter_mismatch` skips the target comparison when `"kind"` is missing.
- **N2** Base value 0 for a variable that never occurs (`d_beta=0` on a $U_E$ certificate) is accepted (Lean `x % 0 = x`, `x / 0 = 0`); the statement stays true, but a base of 0 is meaningless. Suggest rejecting zero bases in `pinError`.
- **N3** The spec renders `name = value (proved by …)` but not the fact's `note`, so the warning "NOT dim S_o" on `max_states_per_outer` / `card_supported_outer` is in `structure.json` only. The numbers are correct; the two histograms agree here, so no wrong statement results.
- **N4** `structure_facts()` with its default `certified=None` labels the native facts `native` without having run the checker (the acceptance test calls it that way). The persisted `structure.json` is made by `write_structure_json`, which checks first. Minor.
- **N5** The 16 "geometric × charge conjugation" candidates are only 8 distinct signed permutations (charge conjugation fixes all labels, so `X*cc` equals `X`; the file's own note says so). All 16 are listed. Trust boundary: the pinned qubit-code basis is tied to the Lean-verified electric-key basis of the structure certificate through the Python exporter's conversion (not re-derived here); the two bases cannot be compared term by term (different encodings).
- Timing: structure check 90 s (limit 900 s), UE 3.4 s, UB 113 s, step 139 s, all under load 10–32.

## 5. Verdict
PASS. Counts: 10 acceptance Lean ids passed (4 of `test_lean_structure.py`, 6 of `test_lean_formal.py`), 4 PENDING (2.L7/2.L8), 0 failed; 389 unit, 54 m0+m1 non-slow, lock OK; new failures vs report 036: none.
