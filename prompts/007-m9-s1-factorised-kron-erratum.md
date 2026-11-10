# 007 — Erratum to prompts/300 + 301 (M9, fuzzy): `test_M9_S1_step_orders` applies the four-link product factor by factor

- Date: 2026-11-10
- Author: planner (Claude Fable 5.2)
- Git commit at writing: d744c0a (branch `merge-desktop-tracks`), plus this erratum's uncommitted changes (§3, §5).
- Plan in force: unchanged. This file amends only the cost note of `prompts/301-fuzzy-m9-test-amendment.md` §3 and one locked
  test of milestone M9 (`prompts/300-fuzzy-m9-plan.md` §4 M9-S1). No method, interface, tolerance, milestone or step changes.
- Trigger: `notes/STATUS.md` line 129 (2026-11-10, session crashes diagnosed) and `tools/pytest-safe` (header).
- Decision: Digonto, chat, 2026-11-10, recorded in `notes/STATUS.md` "Decisions" (line 27, item 1): *approve planner erratum for
  m9 `test_M9_S1_step_orders`: apply the 4-link UEK/H kron factor by factor (same math, same 1e-10 tolerance), re-lock.*
- Research report: none (no new method; a tensor-product identity, verified numerically in §4). Prototype scripts:
  `scratch/planner/kron4_equiv_007.py` (equivalence), `scratch/planner/run_s1_measured_007.py` (time/memory of the test).
- Numbering: this is a cross-track item, so it takes the low range (007) as the coordinator asked; `next-num prompts` would have
  given 303.

## 1. Problem

`tests/acceptance/m9/test_fuzzy_circuits.py::test_M9_S1_step_orders` (4 parametrizations: `order` $\in\{1,2\}$, $r\in\{1,0\}$;
locked, not marked slow) checked the production `su2plaq.fuzzy.targets.apply_step` against an independently composed reference.
For that reference it built

```python
UEK4 = np.kron(np.kron(np.kron(UEK, UEK), UEK), UEK)      # 65536 x 65536 complex128
H    = np.kron(np.kron(np.kron(h, h), h), h)              # order 2 only: a second one
```

Each matrix has $65536^2 \times 16$ bytes $= 68.7$ GB ($64$ GiB); order 2 holds two at once ($137$ GB). The test was written on a
48-core large-memory host (134.8 GB peak, as quoted in `docs/report-9-fuzzy-general-circuit.md` line 189). On omnicommander (31 GiB RAM, 62 GiB swap) it can never run, and
`pytest -n 16 -m "not slow" tests/acceptance` filled RAM and swap twice, so `systemd-oomd` killed the whole desktop session
(2026-11-09 23:50 and 2026-11-10 12:17). Since then `tools/pytest-safe` deselects the test unless `PYTEST_BIGMEM=1`, which means
the M9-S1 reference check has not been run on this machine at all.

The dense matrix was never needed: the test only ever multiplies it into a vector.

## 2. Change (one test function; same inputs, seeds, assertions, tolerance)

The matrix-vector products $U_{EK}^{\otimes 4}\psi$ and $h^{\otimes 4}\psi$ are now applied one 16x16 factor at a time on the
`(16,16,16,16)` reshape of the 65536-vector. Everything else in the function is untouched: `NOMINAL`, `ALTS[1]`, `SEED`, the
random vector `psi`, `apply_UB`, the `verify_step_samples` calls, every assertion, and the tolerance
`np.linalg.norm(out - ref) <= 1e-10`. No other test and no other file under `tests/acceptance/` changed except the one hash in
`LOCK.json` (§5).

**Convention.** For 16x16 matrices $F_0,\dots,F_3$, `np.kron(np.kron(np.kron(F0, F1), F2), F3)` has entries

$$K_{(a b c d),(i j k l)} = (F_0)_{ai}\,(F_1)_{bj}\,(F_2)_{ck}\,(F_3)_{dl}, \qquad (abcd) \equiv 4096\,a + 256\,b + 16\,c + d ,$$

so the FIRST factor of `np.kron` acts on the MOST significant base-16 digit. A C-order `v.reshape(16,16,16,16)` has that digit
on axis 0, hence $F_m$ contracts with axis $m$:

$$(K v)_{abcd} = \sum_{ijkl} (F_0)_{ai}(F_1)_{bj}(F_2)_{ck}(F_3)_{dl}\; v_{ijkl}.$$

In the test's qubit layout (link $l$ on qubits $4l..4l+3$, amplitude index $\sum_l (\text{link } l)\,16^l$, METHODS-fuzzy F1)
axis 0 is link 3 (`l`) and axis 3 is link 0 (`b`). In this test all four factors are the same matrix, so the operator is
invariant under any permutation of the factors and the ordering cannot change the result; it is nevertheless written in the
`np.kron` order and was verified with four distinct factors (§4, E1/E2/E4), where a wrong ordering gives an error of 1.4.

**Why `einsum` and not the production route.** `targets._apply_kinetic` uses `np.tensordot` + `np.moveaxis`. The test keeps its
"independent composition" by spelling the index contraction out with `np.einsum`, one factor per line, and by keeping its own
gather/scatter `apply_UB` (unchanged).

**Floating point.** The operator is identical; the summation order differs, so `ref` changes at the rounding level:
$\lVert \mathrm{ref_{old}} - \mathrm{ref_{new}}\rVert \le 4.5\times10^{-16}$ on the test's own inputs (§4, E5), five orders of
magnitude below the unchanged tolerance $10^{-10}$. The tolerance is not loosened and needs no new justification.

## 3. Exact diff (`git diff tests/acceptance/m9/test_fuzzy_circuits.py`, against d744c0a)

```diff
--- i/tests/acceptance/m9/test_fuzzy_circuits.py
+++ w/tests/acceptance/m9/test_fuzzy_circuits.py
@@ -168,7 +168,16 @@ def test_M9_S1_step_orders(order, r):
     psi = rng.normal(size=65536) + 1j * rng.normal(size=65536)
     psi /= np.linalg.norm(psi)
     UEK = tg.UEK_link(alpha, k2)
-    UEK4 = np.kron(np.kron(np.kron(UEK, UEK), UEK), UEK)
+    def kron4(A, v):
+        # np.kron(np.kron(np.kron(A, A), A), A) @ v applied factor by factor (prompts/007): the same operator, never formed as
+        # the dense 65536x65536 matrix (68.7 GB, twice for order 2; this supersedes the file-header cost note for this test).
+        # np.kron puts its FIRST factor on the MOST significant index = axis 0 of the C-order (16,16,16,16) reshape.
+        t = v.reshape(16, 16, 16, 16)
+        t = np.einsum("ai,ijkl->ajkl", A, t)
+        t = np.einsum("bj,ajkl->abkl", A, t)
+        t = np.einsum("ck,abkl->abcl", A, t)
+        t = np.einsum("dl,abcl->abcd", A, t)
+        return t.reshape(65536)
     rows = np.arange(65536)
     row_idx = sum((((rows >> (4 * l + 2)) & 3) << (2 * l)) for l in range(4))
     col_idx = sum((((rows >> (4 * l)) & 3) << (2 * l)) for l in range(4))
@@ -178,11 +187,10 @@ def test_M9_S1_step_orders(order, r):
         M[row_idx, col_idx] = v
         return (UB @ M)[row_idx, col_idx]
     if order == 1:
-        ref = apply_UB(UEK4 @ psi)
+        ref = apply_UB(kron4(UEK, psi))
     else:
         h = tg.UEK_link(alpha / 2, k2 / 2)
-        H = np.kron(np.kron(np.kron(h, h), h), h)
-        ref = H @ apply_UB(H @ psi)
+        ref = kron4(h, apply_UB(kron4(h, psi)))
     out = tg.apply_step(psi, alpha, beta, k2, order)
     assert np.linalg.norm(out - ref) <= 1e-10
     # order mismatch
```

Not changed, on purpose (the approval covers this one function only): the module docstring of the file (lines 5-6) still says
the two M9_S1 tests form a dense kron and should run with `pytest -n 1`. That note is now obsolete for
`test_M9_S1_step_orders` (and was never true for `test_M9_S1_outer_row_and_gauss_on_outputs`, which forms no kron); the new
in-function comment says so. Correcting the header is a second re-lock of the same file and needs Digonto's word (§8).

## 4. Equivalence evidence (measured before the test was edited)

Command (0.63 GB peak RSS, about 1 min, cores 14-15):

```
PER_JOB_MEM=4G tools/run-capped taskset -c 14-15 python scratch/planner/kron4_equiv_007.py
```

Factors: Haar-random 16x16 unitaries $F_0..F_3$ (all different, `np.random.default_rng(7)`, unitarity defect $8.9\times10^{-16}$),
random normalised complex vectors. "Factorised" is the contraction pattern of §2 with $F_m$ on axis $m$; with all factors equal
it is the test's `kron4` bit for bit (`np.array_equal` is `True`). All errors are 2-norms of the difference of the two output
vectors of unit norm.

| id | instance | dense reference | $\lVert$dense $-$ factorised$\rVert$ | wrong factor order |
|---|---|---|---|---|
| E1 | 2 factors, dim 256 | `np.kron(F0, F1) @ v` | $4.7\times10^{-16}$ | 1.43 (swapped) |
| E2 | 3 factors, dim 4096 | `np.kron(np.kron(F0, F1), F2) @ v` (268 MB) | $8.1\times10^{-16}$ | 1.413 to 1.417 (all 5 other permutations) |
| E2' | same | explicit index formula of §2 (`einsum`, one call) vs dense | $8.2\times10^{-16}$ | |
| E3 | 3 factors | rows $256 i_0 + 16 i_1 + [0,16)$ of the dense matrix vs `np.kron(np.kron(F0[i0:i0+1], F1[i1:i1+1]), F2)`, 3 blocks | $0$ exactly (max abs entry difference) | |
| E4 | 4 factors, full size 65536 | ALL 65536 rows of `np.kron(np.kron(np.kron(F0, F1), F2), F3) @ v`, formed with `np.kron` in 256 row blocks of 256 x 65536 (268 MB each; row-block identity = E3) | $8.7\times10^{-16}$ | 1.410 to 1.415 (3 permutations) |

All are $\le 10^{-13}$ as required (by a factor of more than 100). E4 is a complete check of the full-size operator: every row
of the dense matrix is formed by `np.kron` itself and multiplied into the vector; only the 68.7 GB are never held at once.

E5, the test's own inputs (`SEED = 20261104`, `NOMINAL = (0.37, 0.61)`, the same `psi`): `ref_old` is the old reference with its
dense matvecs done in the 256 `np.kron` row blocks of E4; `ref_new` is the new code; `out = tg.apply_step(...)`.

| order | $r$ | $\lVert \mathrm{ref_{old}} - \mathrm{ref_{new}}\rVert$ | $\lVert \mathrm{out} - \mathrm{ref_{old}}\rVert$ | $\lVert \mathrm{out} - \mathrm{ref_{new}}\rVert$ (asserted $\le 10^{-10}$) |
|---|---|---|---|---|
| 1 | 1.0 | $3.4\times10^{-16}$ | $3.5\times10^{-16}$ | $3.2\times10^{-16}$ |
| 2 | 1.0 | $4.4\times10^{-16}$ | $4.5\times10^{-16}$ | $4.0\times10^{-16}$ |
| 1 | 0.0 | $2.2\times10^{-16}$ | $2.2\times10^{-16}$ | $1.9\times10^{-16}$ |
| 2 | 0.0 | $2.9\times10^{-16}$ | $2.9\times10^{-16}$ | $2.4\times10^{-16}$ |

So the asserted quantity is the same number as before to within float64 rounding, and the old test would have passed with the
same margin on a machine that could hold the matrix.

## 5. Lock

`tools/lock.py` refuses to re-lock m9, so, following the precedent in `notes/merge-notes-fuzzy.md` (prompts/301, acceptance-v9),
the single entry was replaced by hand in `tests/acceptance/LOCK.json` (in-place string substitution; no entry added, removed or
reordered, milestone list untouched, 60 files as before):

```
"tests/acceptance/m9/test_fuzzy_circuits.py":
  old a09df390cf3e464d4f0753c13055e3199ec82cb122341a6c48772b0af83907d2
  new 5c0d63ed6e230111944abbafbf749c9ef459823db0db18cd0fcf338c2819b38a
```

`python tools/check_lock.py` printed `LOCK OK` right after. The coordinator commits both files, tags the next acceptance
version and runs the lock tools once the concurrent m7 lock is in.

## 6. Measured cost of the test after the change

Command (step 3 of the task; `PYTEST_BIGMEM=1` is still needed only to switch off the default deselect of `tools/pytest-safe`;
`PYTEST_MEM_MAX=4G` set the scope cap to the stop limit, so a regression would have killed one worker, not the desktop):

```
python scratch/planner/run_s1_measured_007.py
  = PYTEST_BIGMEM=1 PYTEST_MEM_MAX=4G taskset -c 14-15 tools/pytest-safe -n 2 -q -rA --durations=0 \
        tests/acceptance/m9/test_fuzzy_circuits.py -k S1_step_orders
```

Result: **4 passed in 236.57 s** (wall 236.8 s, CPU 453.4 s, 2 workers on cores 14-15; other agents' jobs were running on the
other cores), omnicommander, 2026-11-10 13:40-13:44 local.

| test id | result | call time |
|---|---|---|
| `test_M9_S1_step_orders[1.0-1]` (r = 1, order 1) | PASSED | 80.9 s |
| `test_M9_S1_step_orders[1.0-2]` (r = 1, order 2) | PASSED | 154.8 s |
| `test_M9_S1_step_orders[0.0-1]` (r = 0, order 1) | PASSED | 70.9 s |
| `test_M9_S1_step_orders[0.0-2]` (r = 0, order 2) | PASSED | 147.8 s |

Memory (polled every 0.2 s, 1180 samples, by the wrapper script):

| quantity | value |
|---|---|
| cgroup `memory.peak` of the run's systemd scope (pytest main + 2 workers, page cache included) | 1.995 GB |
| largest per-process `VmHWM` (one xdist worker) | 1.040 GB |
| `RUSAGE_CHILDREN` `ru_maxrss` | 1.040 GB |
| before the change (large-memory host, figure quoted in `docs/report-9-fuzzy-general-circuit.md` line 189) | 134.8 GB peak |

Both are below the 4 GB stop limit. The reference part changed here holds only 1 MB vectors and 16x16 / 256x256 matrices (the
equivalence script of §4, which also builds 268 MB row blocks, peaked at 0.63 GB in total); the roughly 1 GB per worker and
the run time therefore come from the rest of the test (the `build_step` / `verify_step_samples` calls), which this erratum does
not touch. That attribution was not measured separately. At 70-155 s per parametrization the test is not fast; it is left
unmarked (not `slow`) exactly as locked.

Byproducts: the run wrote no tracked or untracked file in the repository (`git status` shows only the three files of this
erratum from this planner).

## 7. Follow-ups for the coordinator (not done by the planner)

1. `tools/pytest-safe`: the default `--deselect tests/acceptance/m9/test_fuzzy_circuits.py::test_M9_S1_step_orders` and the
   `PYTEST_BIGMEM` switch can be removed (keep the memory-capped scope itself). After that the test runs in every normal
   acceptance run again.
2. Stale cost notes that say S1 needs 68-135 GB / `-n 1`: `CLAUDE.md` line 17, `scratch/agent-common.md` ("MEMORY RULE"),
   `notes/STATUS-fuzzy-m9-m10.md` line 27, `docs/report-9-fuzzy-general-circuit.md` line 189. `prompts/301` §3 is superseded by
   this file for `test_M9_S1_step_orders` (prompts are not edited after the fact).
3. Commit `tests/acceptance/m9/test_fuzzy_circuits.py` + `tests/acceptance/LOCK.json` + this file; next acceptance tag.
4. `docs/METHODS.md` / `docs/METHODS-fuzzy.md`: no change (no method or convention changed; F1 and F3 already state the index
   convention used here).

## 8. Risks, stop condition, do-not-retry

- Do not retry: forming any $65536^2$ dense operator in a test or in production code (68.7 GB each). Apply link blocks on the
  `(16,16,16,16)` reshape, or check dense rows in blocks as in §4 E4.
- Risk: none for correctness (same operator, §4). The test stays about as slow as its `verify_step_samples` part (§6).
- For Digonto (optional, not needed for anything to run): allow a comment-only fix of the obsolete header note in
  `tests/acceptance/m9/test_fuzzy_circuits.py` lines 5-6 (one more hand re-lock of the same file).
- Stop condition: if any of the four parametrizations fails or the run's peak memory exceeds 4 GB on this machine, stop and
  report; do not touch the tolerance.

## 9. Done-check (tester)

```
python tools/check_lock.py                                                    # LOCK OK
PYTEST_BIGMEM=1 PYTEST_MEM_MAX=4G taskset -c <2 cores> tools/pytest-safe -n 2 -q \
    tests/acceptance/m9/test_fuzzy_circuits.py -k S1_step_orders              # 4 passed (PYTEST_BIGMEM only until follow-up 1)
```
