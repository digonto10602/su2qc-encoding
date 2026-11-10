# 103 — M3x acceptance-test fixes (track S): exact 6j non-zero count in W1, `SpinNet.labels` interface in W3

- Date: 2026-11-06 · Author: planner (Claude Fable 5.1) · Git commit at writing: `d1e6edc` (branch `m3-spin-network`, working tree with the builder's uncommitted W0+W1 changes: `src/su2plaq/spinnet/lean_export.py`, `lean/Su2Plaq/SpinNet/Recoupling.lean`)
- Plan in force: **`prompts/102-spinnet-m3-wait-lean-structure.md` stays in force unchanged** (method, Lean layout, steps W0–W4, limits). This file only corrects two defects in the locked test file `tests/acceptance/m3x/test_spinnet_lean_exact.py` (acceptance-v8) and records the resulting re-lock. Nothing in `docs/METHODS-spinnet.md` §9 changes except one provenance sentence on the 6j zero pattern.
- Trigger: the builder of prompts/102 steps W0+W1 reported (coordinator brief, 2026-11-06) that W1 fails on `assert 47 >= 50` although Lean's `sixj` and `su2plaq.su2.wigner.six_j` agree on all 729 entries, and that W3's helper `_codes_433` calls `enc.labels()` while `SpinNet.labels` is a list attribute. Digonto's standing instruction (2026-11-06): the planner fixes a stuck loop without asking. Verified independently here: `taskset -c 0-9 pytest -n 1 tests/acceptance/m3x -k W1` on the locked file → `assert 47 >= 50` (the only failing line); `scratch/planner/m3x_test_fix_probe.py` (numbers below).

Jargon, once: *6j symbol* = the Wigner recoupling coefficient $\{a\,b\,c;\,d\,e\,f\}$ of six spins; *triad* = one of the four spin triples $(abc),(aef),(dbf),(dec)$ that must each form a triangle for the symbol to be defined; *triangle rule* = $|a-b|\le c\le a+b$ with $a+b+c$ an integer; *accidental zero* = a 6j symbol that vanishes although all four triads obey the triangle rule; *doubled spin* = the integer $2j$ used to store a spin $j$.

## 1. Defect 1 — W1's "≥ 50 non-zero entries" (wrong number, wrong kind of check)

**What was wrong.** The locked line `assert sum(1 for v in table.values() if abs(v) > TOL_EXACT) >= 50` was meant as a sanity guard ("the table is not trivially zero"); the number 50 was a guess, not derived. The true count on the test's own index set $\{0,\tfrac12,1\}^6$ (729 doubled-spin tuples) is **47**.

**Independent derivation (not the project's Racah code).** `scratch/planner/m3x_test_fix_probe.py` enumerates all 729 tuples with `sympy.physics.wigner.wigner_6j` (exact symbolic values; sympy 1.14.0) and, separately, with the plain triangle rule on the four triads:

| Quantity | Value | Source |
|---|---|---|
| tuples with all four triads triangle-admissible | 47 | triangle rule, pure Python |
| sympy `wigner_6j` $\ne 0$ | 47, **same set** as the admissible tuples | sympy 1.14.0 |
| `su2plaq.su2.wigner.six_j` $\ne 0$ ($>10^{-12}$) | 47, same set | project float Racah |
| Lean `Su2Plaq.SpinNet.sixj` $\ne 0$ ($>10^{-12}$) | 47, same set | `lean_export.lean_sixj_table()` |
| worst $|\text{sympy}-\text{six\_j}|$ over 729 | $0.0$ | probe |
| smallest non-zero $|6j|$ | $1/6$ | sympy |
| distinct non-zero values | $\{-\tfrac{\sqrt2}{2},-\tfrac12,-\tfrac13,\tfrac16,\tfrac13,\tfrac{\sqrt6}{6},\tfrac12,\tfrac{\sqrt3}{3},1\}$ | sympy |
| non-zero tuples by number of spin-$\tfrac12$ entries | 0: 15, 3: 20, 4: 12 | sympy (the 47 = integer-spin tuples in $\{0,1\}^6$ obeying the triangle rule, plus tuples with exactly three or four spin-$\tfrac12$ entries; a triad needs an even number of half-integer spins, so counts 1, 2, 5, 6 are impossible) |

So on this index set the 6j symbol is non-zero **iff** the four triads satisfy the triangle rule: there are no accidental zeros for spins $\le1$, and the count is a derived combinatorial number, not a measured one.

**Change (file `tests/acceptance/m3x/test_spinnet_lean_exact.py`, `test_M3X_W1_recoupling_matches_wigner_and_codec`).** The `>= 50` line is replaced by three stronger assertions, plus a new independent reference:
1. `nonzero == admissible` — the set of Lean entries with $|v|>10^{-12}$ equals the set of triangle-admissible tuples computed in the test by `_sixj_admissible` (triads $(abc),(aef),(dbf),(dec)$, Edmonds 6.3.7) — and `len(admissible) == N_SIXJ_NONZERO == 47`;
2. `table[args] == 0.0` **exactly** on the 682 inadmissible tuples (Lean's exact arithmetic gives $q=0$ there, so `float(Fraction(0, d)) * sqrt(r)` is exactly `0.0`; a float "nearly zero" would be a bug in the exact code);
3. `|table[args] - float(wigner_6j(...).evalf(30))| <= 1e-12` on the 47 admissible tuples — sympy is independent of `su2plaq`, so the Lean table is now tied to an external exact reference, not only to the project's own Racah implementation (which the m0 test `test_M0_A2_six_j_vs_sympy` ties to sympy as well, for spins $\le\tfrac32$).

The original 729-entry comparison with `su2plaq.su2.wigner.six_j` (production code path) is kept unchanged.

**Why this does not weaken the test.** The old check was a one-sided lower bound on a count that was false (so the test could never pass on correct code); the new checks are equalities: exact zero pattern (a set equality on 729 tuples), exact count, exact zeros, and a second, independent value reference. Every case the old line could reject (a table with fewer than 50 non-zeros) is either impossible for a correct table or still rejected (fewer than 47, or a non-zero in the wrong place). The tolerance $10^{-12}$ is unchanged and justified as before (exact $q\sqrt r$ of magnitude $\le1$ evaluated once in float64, $\approx10^{-16}$; sympy `evalf(30)` to float64, $\approx10^{-16}$); the non-zero threshold $10^{-12}$ sits eleven orders below the smallest non-zero value $1/6$, so it cannot mis-classify an entry. Cost: sympy on 47 tuples = 7 ms (measured); W1 wall 4.6 s (was 2.6 s to the failing line).

## 2. Defect 2 — W3's `_codes_433` called `enc.labels()`

**What was wrong.** `SpinNet.labels` (`src/su2plaq/encodings/spinnet.py`, set in `__init__`: `self.labels = labs`) is a **list attribute** of 433 route-B labels `((j_0..j_11), (J_0..J_3))` (floats; inner links $j_0..j_3$ = $b,r,t,l$, outer $j_4..j_{11}$, corners $J_0..J_3$), identical to `enc.basis.labels` used by `tests/acceptance/m3/test_spinnet_codec.py`. Calling it would have raised `TypeError: 'list' object is not callable` once `Spectrum.lean` exists (today W3 stops earlier with `PENDING:` because the file is missing, which is why the defect was invisible at lock time).

**Change.** `for j, J in enc.labels():` → `for j, J in enc.labels:` (docstring notes the interface). The hand-rolled bit formula is kept (it restates METHODS-spinnet §1 independently of `code_of_label`). Verified: the 433 codes from the attribute equal `{code_of_label(l)}`, `enc._codes`, and Lean's `states` (`lean_export.lean_states()`, as $y+256\,o$) — probe output `hand codes 433: 433 == code_of_label set: True == enc._codes: True`, `lean states 433 == hand True`.

**Interface note for prompts/102 §3.** That section lists only `lean_export` functions and is unaffected; the encoding interface used by the m3x tests is the laptop-style one of `encodings/spinnet.py`: `SpinNet().labels` (list attribute), `inner_codes()` (sorted `np.int64` array, 47), `h_magnetic()` ($433\times433$ float), `basis.labels`. No builder action.

## 3. Re-read of W2 and L against the actual code (no further slips found)
- W2: `build_UB(1.0)` has 48 instructions, names `{x: 16, rccx: 14, cx: 12, rz: 4, h: 2}` ⊂ `GATE_NAMES`, 15 qubits, `metadata["beta"] = 1.0`; the four `rz` angles $(-3.5,-1,3,1.5)$ at $\beta=1$ are $(-7,-2,6,3)$ in units of $\beta/2$ = `lean_export.angle_ints(enc)`; `QuantumCircuit.rccx(2, 0, 1)` and `Operator(...).data` (8×8) exist in Qiskit 2.5.2; the tuple layout `("rz", q, a)` matches the test's `g[2]` and `gate[1:]` slicing. The `gate_literal` β-independence check at $\beta=0.61$ relies on `gate_ints`'s $10^{-9}$ integer snap, while the solved angles deviate by $\le4\cdot10^{-15}$ (snapped coupling table, METHODS-spinnet §2) — consistent.
- W3 (rest): `enc.h_magnetic()` is symmetric to $0.0$; `eigvalsh` multiplicities of $2\lambda$ are $16/96/16/177/16/96/16$ at the $10^{-9}$ bin (probe). `lean_states()` reads `states` from `Recoupling.lean` (where prompts/102 §2 puts it) — the W3 test correctly does not need `Spectrum.lean` for that call.
- L: `su2plaq.lean.project.print_axioms(names, timeout=900)` and `no_sorry()` have the signatures the test uses; `_statement` splits on `:= by`, which every theorem in the built `Recoupling.lean` uses (and prompts/102 §2 mandates `by decide`).
- W1 (rest): `Recoupling.lean` has no `import` line (Mathlib-free check passes), contains `racahSum`, `fsym`, `sixj`, the four theorem names, and the generated block with `lean_literals(enc)["codes"|"coupling"]` verbatim — all confirmed by the passing test.

## 4. Lock bookkeeping and done-check
- `tests/acceptance/LOCK.json`: only the entry `tests/acceptance/m3x/test_spinnet_lean_exact.py` changed, `9c823c2a…` → `5b98b796…` (`tools.check_lock.sha`, `json.dumps(lock, indent=1, sort_keys=True) + "\n"`); `python tools/check_lock.py` → `LOCK OK`.
- `pytest --collect-only -q tests/acceptance` → 130 tests (unchanged). `taskset -c 0-9 pytest -n 1 tests/acceptance/m3x` → W1 **passed** (4.60 s); W2, W3, L fail only with `PENDING: … Semantics.lean / Spectrum.lean missing`.
- Coordinator: `~/.claude/bin/acceptance-lock "prompts/103-spinnet-m3x-test-fixes.md"` (tag acceptance-v9) together with the builder's W1 commit; counters for W1 reset to 0; continue with prompts/102 step **W2**. No change to prompts/102's steps, limits, or do-not-retry list.

## 5. Do-not-retry
- Keeping a "≥ N" sanity bound with any N: the exact zero pattern is known and cheap; a bound is strictly weaker.
- Comparing the Lean table with sympy on all 729 tuples: sympy raises `ValueError` on inadmissible triads (no value to compare); the test instead asserts exact `0.0` there.

## 6. Risks / stop condition
None new. If a future `Recoupling.lean` makes an inadmissible entry a non-zero float (not exactly `0.0`) while all other checks pass, that is a defect in the exact arithmetic, not a tolerance question — fixer, not planner.
