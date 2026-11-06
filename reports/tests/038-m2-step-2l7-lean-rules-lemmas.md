# Tester report 038 — M2 step 2.L7 (Lean rules, lemma files, round hook) + notes N1–N4

- Date: 2026-11-06. Git: `c4a9d2a` plus the uncommitted working tree of step 2.L7 (HEAD = acceptance-v7). Mode: **step**.
- Plan in force: `prompts/006-lean-formal-verification-m2-addendum.md` (step 2.L7); previous report `reports/tests/037-m2-lean-n5-n6-2l6-structure.md`.
- Raw numbers: `results/tests_038_step_2l7.json`. Scratch roots only (never `compress/programs/`, `compress/archive/`, `results/compress/` of the real repo; `git status` of those is unchanged).

## VERDICT: FAIL (one locked acceptance test newly red, caused by the `spec.py` evaluator-hash change; everything else PASS)

## Commands
```
python tools/check_lock.py && ~/.claude/bin/acceptance-check
cd lean && lake build
pytest -n auto tests/unit
pytest -n 4 tests/acceptance/m2 --deselect tests/acceptance/m2/test_lean_formal.py::test_archive_best_lean_status_recorded
pytest -n 4 -m "not slow" tests/acceptance/m0 tests/acceptance/m1
lake env lean <scratch>.lean        # #print axioms; statement coverage
python <scratch>/fuzz.py            # pass-vs-unitary fuzz   (scratchpad: fuzz.py, lem.py, rnd.py, nolean.py, notes.py)
```

## Results

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `check_lock.py`, `acceptance-check` | lock intact | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v7` | exact | PASS |
| `lake build` | success | `Build completed successfully (9095 jobs)` | – | PASS |
| unit suite | all pass | 394 passed (424 s) | – | PASS |
| acceptance m2 (all but the 2.L8 id) | all pass | 44 passed, **1 failed** | – | **FAIL** (below) |
| incl. `test_polish_rules_are_lean_certified`, `test_program_lemma_file_checked`, `test_round_records_lean_certificate` (161 s, certified) | pass | pass | – | PASS |
| m0 + m1, not slow | pass | 54 passed (164 s) | – | PASS |
| `test_archive_best_lean_status_recorded` | PENDING (2.L8) | deselected | – | PENDING |
| `#print axioms` for `cancel_inverse_pairs`, `merge_adjacent_rotations`, `ctrl_mul`, `ctrlRot_merge`, `Rx_merge` | $\{$propext, Classical.choice, Quot.sound$\}$ | exactly those | – | PASS |

### (1) Coverage of `compress/passes.py` by the Lean theorems
`passes.py` cancels (same qubit tuple; for cz/swap/ccz any order): x, z, h, cx, cz, swap, ccx, ccz, ch, rccx (self-inverse) and s·sdg, sdg·s, t·tdg, tdg·t; it merges rz, p, crz, crx, cp (same qubit tuple, angles add). Nothing else is rewritten.

| gate / rule | Lean statement in `Su2Plaq.cancel_inverse_pairs` / `merge_adjacent_rotations` | status |
|---|---|---|
| x x, z z, h h | `Xm*Xm=1`, `Zm*Zm=1`, `Hd*Hd=1` | covered |
| s sdg, sdg s, t tdg, tdg t | `Sg*Sdg=1`, … (via `Pg_mul`, `Pg_zero`) | covered |
| cx cx | `perm (cxE c t h) * perm (cxE c t h) = 1`, any $n$, $c\ne t$ | covered |
| cz cz, ccz ccz | `diagonal (czDiag a b)` squared; `cczDiag a b c` squared | covered for equal argument order |
| swap swap, ccx ccx | `perm (swapE a b)` squared; `perm (ccxE a b c _ _)` squared | covered for equal argument order |
| ch ch | `cgate Hd * cgate Hd = 1` | covered |
| rccx rccx | `RCCX * RCCX = 1` (RCCX phases read off Qiskit's `RCCXGate`) | covered |
| rz, p, rx-style merges | `Rz a*Rz b=Rz(a+b)`, `Pg`, `Rx` | covered |
| crz, crx, cp | `ctrlRot 1 Rz/Rx/Pg` (block form, `ctrl_mul`) | covered |

Independent semantic check (Qiskit matrices): all 14 cancel pairs (incl. every argument order of cz/swap/ccz) and 5 merges multiply to the claimed result with max error $2.2\times10^{-16}$. Fuzz of `_cancel_and_merge` (seed 20260606, 3000 random 4-qubit circuits of all 19 gate names, with biased inverse/permuted repeats): 10 278 gates cancelled, 2 513 rotations merged, max $\|U_{\rm before}-U_{\rm after}\|_{\max}=8.7\times10^{-16}$.

Gaps found (soundness is not affected, both are statement-level):
- **G1 (strict reading of "covered")**: for cz, swap, ccz the pass also cancels the pair with the qubit order swapped (e.g. `cz(a,b) cz(b,a)`), which is not literally one of the conjuncts (they square `czDiag a b`; the swapped product is `czDiag a b * czDiag b a`). Scratch Lean proofs (`lake env lean`, no errors): `czDiag a b = czDiag b a` (`Bool.and_comm`), `cczDiag a b c = cczDiag a c b` (`Bool.and_assoc`+`and_comm`), so the swapped case follows in one line; I also proved `diagonal (czDiag a b) * diagonal (czDiag b a) = 1`. Suggest adding the symmetry lemmas to the theorem (small builder step). `swap` symmetry (`swapFun a b = swapFun b a`) I did not close in the 5-minute scratch attempt (numerically verified above).
- **G2 (adjacency)**: no theorem states that removing a pair that is adjacent in the dependency order (no gate on any shared qubit in between) preserves the whole-circuit unitary (tensoring with identity + commuting disjoint gates). The theorems are the local product identities only. This is covered numerically by the fuzz and, more importantly, by the end-to-end certificate of the final circuit.

### (2) Lemma-file checker (`lean/lemmas.py`), 25 adversarial files, `lake env lean` ≈ 7–16 s each
good (Nat `decide`, Su2Plaq theorem, Mathlib `omega`, `lemma` keyword, namespace, theorem + `classical`), sorry/admit in a comment only: `proved`. Refused or `failed`: `sorry`, `admit`, `native_decide`, `axiom`, `unsafe`, `@[extern]`, `implemented_by`, `import Lean`, `import Std`, `import Su2PlaqEvil`, `import Mathlibx.Foo`, a false `decide`, a syntax error, `sorryAx` as a term (non-standard axiom list), `open Lean in … ofReduceBool` (unknown identifier), and a 5 s timeout on a heavy `decide` (`timeout after 5.0 s`, 5.1 s wall). No `Lemma_*.lean` temp file is left in `lean/`. In the round test a lemma with `sorry` gives `lean_lemmas.status=failed` while the entry stays `valid` and certified.
Notes (informative-only, do not affect validity):
- **L1** a file with no theorem returns `proved` with `theorems=[]` (nothing is proved). Suggest `failed`/`none` when `names` is empty.
- **L2** `#eval` is not blocked: a lemma file ran `#eval IO.FS.writeFile …` and created the file (arbitrary code execution at check time, same trust level as the Python programs; the proposer guard is documented as not a sandbox).
- **L3** timing: 7–16 s per file, budget 120 s × at most 5 files per round.

### (3) Round hook on scratch roots
| scenario | expected | got |
|---|---|---|
| round 0, worse program (CX 296) with a `sorry` lemma file | new best certified; lemma `failed`; still valid | `best_lean=certified`, `lean_lemmas=failed`, valid; `lean_seconds` 68.6 |
| round 1, better program (CX 294) with a good lemma | new global best certified, lemma `proved` | certified, `proved`; `lean_seconds` 48.7 |
| round 2, program worse than the best | not best, no certificate | `lean=None`, `lean_seconds=0.0`, best unchanged (`r01-seed-002`) |
| CLI `--no-lean` | no certificate, no lemma check | `lean_seconds 0.0`, `lean=None`, `lean_lemmas=None`, valid |
| `--certify-best` | `Entry.lean` stored | `status=certified`, entry still valid |
| certifier raising `RuntimeError` | recorded, not hidden, validity untouched | `{'status':'failed','reason':'RuntimeError: synthetic lean crash'}`, still valid |
Note **R1**: `certify_best` overwrites an existing `certified` status with `failed` on a transient failure (prior certificate lost).

### (4) N1–N4 (reports/tests/037)
- N1: 13 of 13 real mutations (no kind, kind XYZ, order 3, gate `rx`, repeated qubit, `n_qubits` 100, angle on `h`, zero `d_alpha`/`d_beta`, negative base, boolean in phase, no states, wrong program hash) are refused by `write_theorem_file` (`ValueError`) and rejected by `check_certificate`. (My "odd m on rz" case was a no-op, a $U_E$ circuit has no `rz`; ignore.) PASS.
- N2: the Lean checker alone says `REJECT base must be a positive multiple of the target's base` for `d_alpha=0` and `d_beta=0`. PASS.
- N3: the spec renders `note`; `compress/specs/twelve-step.md` contains "NOT dim S_o" twice. PASS.
- N4: default `structure_facts()` runs the compiled checker (39 s once, 1.0 s cached), facts native only after `certified`; unit test with a rejecting checker gives no native fact. PASS.
- Side note **N-a**: the Lean checker alone ACCEPTs a $U_E$ certificate with a changed `program_sha256` or `order=3` (not Lean-pinned; the statement concerns the supplied gate list and $U_E$ ignores `order`). Python rejects both, so no wrong theorem file is possible.

### (5) `spec.py` in the evaluator hash — **not harmless: it fails a locked acceptance test**
- `code_hash` changed `810e86f2640d4f76…` (HEAD, equals the round-000 record and the real archive best's `evaluator_sha256`; recomputed from `git show HEAD:` files) to `0bd7e7d91d9d7bcf…`. Only `spec.py` differs among the hashed files. The spec content hash `spec.sha256()` is unchanged (`ee3ce506db7749c7`, same as round-000), verdict logic unchanged, no archive/loader code compares the hash. So caches (`compress/cache/<hash>/`) are only invalidated; no correctness effect.
- But `tests/acceptance/m2/test_compress_machinery.py::test_archive_best_valid_and_not_worse_than_seed` asserts `best.evaluator_sha256 == code_hash()` for the real archive's best. At HEAD it passes (best evaluated with `810e…`); with this working tree it **fails**: `assert '810e86f2640d…' == '0bd7e7d91d9d…'` (line 476). All its earlier assertions (valid, re-evaluated key equal, not worse than seeds) pass. Any later edit of a file in `EVALUATOR_FILES` has the same effect.
  Guess/remedy (coordinator decision, I changed nothing): the final best must be (re-)evaluated after the last evaluator-file edit (a round-1 best is evaluated with the live hash `0bd7…`, round-1 proposers are running on this tree now), or the rendering change is kept outside `EVALUATOR_FILES`/reverted before the gate. Note that the proposers' round 1 is evaluating under `0bd7…` while round 0 entries carry `810e…`.

## Pending
`tests/acceptance/m2/test_lean_formal.py::test_archive_best_lean_status_recorded` (step 2.L8, needs the loop's final best).

## Failures (one line each)
- `test_archive_best_valid_and_not_worse_than_seed`: expected `best.evaluator_sha256 == code_hash()`, got `810e86… != 0bd7e7…`; guess: editing `spec.py` (a hashed file) after the best was evaluated; no physics effect, needs re-evaluation of the best or a different place for the note rendering.
- Not failures but to fix in 2.L7 follow-up: G1 (symmetric argument order of cz/swap/ccz not literal in the theorem), L1 (empty lemma file "proved"), R1.
