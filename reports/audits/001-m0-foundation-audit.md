# 001 — M0 foundation audit

- Date: 2026-11-04
- Auditor: `auditor` agent (Opus 5.5, high)
- Commit range: `3de134f..8bab9da` (`git diff 3de134f..HEAD -- src/ tools/ pytest.ini pyproject.toml docs/METHODS.md`, 48 files, +3045/−1)
- Plan in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` + addendum `prompts/003-gauss-tolerance-synthesised-circuits-engine-policy.md`
- Conventions: `docs/METHODS.md`
- Related reports: `reports/tests/001…013` (013 = M0 gate, full PASS), `reports/research/001`, `reports/research/002`

**Verdict: PASS WITH NOTES.** I found no code that gets the M0 physics wrong. One note (N1) is about how a locked tolerance is defined: the leak tolerance is applied to probability, so it is $10^4$ times looser in amplitude than the error tolerance. Under the "stop and ask" rule, Digonto or the planner must decide on this before the M2 loop. It is not a code bug for the fixer.

Probe scripts (run with `PYTHONPATH=src python <script>` in the `coding` env, commit 8bab9da) are in
`/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/` (`a1.py` … `a9.py`).

## Checklist

| Item | Status | Where / evidence |
|---|---|---|
| $H=\frac{g^2}{2}H_E+\frac1{g^2}H_B$, $H_E=\sum j(j+1)$, $H_B=-(W+W^\dagger)$ | OK | `exact/operators.py:55-94`. Paulo Eq. 16 normalisation is documented in METHODS §2 (twice the common $-\frac1{2g^2}$ form). Results quoted against $g$ must say which normalisation they use. |
| $U_P=U_bU_rU_t^\dagger U_l^\dagger$ orientation vs geometry | OK | `operators.py:34-44`: $W=\sum U^b_{ab}U^r_{bc}(U^t_{ec})^\dagger(U^l_{ae})^\dagger$ with link 0 least significant (`kron(Ul,kron(Ut,kron(Ur,Ub)))`). Gauge covariance checked by hand: $g_{00}(\cdot)g_{00}^\dagger$. The measured physical leak of $W$, $10^{-15}$ (reports/tests/005), confirms that the orientation and the Gauss generators agree. |
| $U_B(\beta)=e^{-i\beta H_B}$, sign; $\alpha_P=2\beta$ | OK | `operators.py:117`, `evaluator.py:503` ($e^{+i\beta(W+W^\dagger)}$). Independent confirmation: Paulo's compiled circuit ($dt=g=1\Rightarrow\beta=1$) verifies to $2.9\cdot10^{-6}$ against `target("UB",β=1)` (M1-P1, reports/tests/011). |
| Electric step `p(-3α/4)`, $H_E^{\rm inner}$ only | OK | `operators.py:97-101`; `evaluator.py:496` (0.75 on $p\neq0$). Note: $p(\lambda)={\rm diag}(1,e^{i\lambda})$, so $\lambda=-\tfrac34\alpha$ gives $e^{-i\alpha j(j+1)}$. |
| Trotter order | OK | `operators.py:123-127`: order 1 = `UB @ UE` (electric layer acts first); order 2 = `UEh @ UB @ UEh`. |
| CG / $U_{ij}$ matrix elements | OK | `su2/algebra.py:228-248`: $\sqrt{(2j+1)/(2j'+1)}\,C^{j'm_L'}_{\frac12 i;jm_L}C^{j'm_R'}_{\frac12 j;jm_R}$, as in METHODS §3. |
| Generators $L=-J^{\mathsf T}$, $R=+J$; Gauss $G_c=\sum_{\rm start}L+\sum_{\rm end}R$ | OK | `algebra.py:250-272`, `physical.py:43-45, 199-208`, `geometry.py:72-79`. Check: $e^{i\theta L}Ue^{-i\theta L}=e^{-i\theta T}U$ and $e^{i\theta R}Ue^{-i\theta R}=Ue^{i\theta T}$, i.e. $U\to g_xUg_y^\dagger$. Outer links: o0, o1, o3, o6 end at their corner (`in`, $R$); o2, o4, o5, o7 start there (`out`, $L$). This is correct. |
| Far-end fixing | OK | `physical.py:140-148`: the far index is set to the first $m$ value and no generator acts on it. In Paulo labels the $V_P$ sign factorises as $s(m_{\rm near})s(m_{\rm far})$, so the far end contributes only a constant sign. The spectator argument holds. |
| Paulo adapter $V_P$, Eq. 25 conjugate typo | OK | `algebra.py:309-323` follows from $D^{*}=\epsilon D\epsilon^{\mathsf T}$ (checked by hand: $D^*_{+-}=-D_{-+}$). Matches Eq. 28 (M0-A3, $2\cdot10^{-16}$). |
| 12-qubit codec (`encodings/twelve.py`) | OK | `twelve.py:83-176`: inner codes as in METHODS §3.2. Outer near label = 1st Paulo character for $L$, 2nd for $R$, far label `-`. `decode_state` applies $\psi_{\rm CG}[cg(p)]=s\,\psi_P[p]$, the correct inverse of `to_convention`. The chain $V_P$ → codec → Paulo's circuit is closed by M1-P1. |
| Route B: 6j, F-symbol phase, argument map | OK at $j_{\max}=\tfrac12$ | `su2/wigner.py:345-376` (Racah formula; phase $(-1)^{j_1+j_2+j_3+J}$ as Edmonds 6.1.5). `spinnet.py:199` gives `f_symbol(J_c,j_p,j_n,½,j'_n,j'_p)` = METHODS §5. Independent of route A (imports only geometry and wigner). See N5 on signs. |
| Evaluator: global phase | OK | `evaluator.py:412-416`: one phase $\arg{\rm tr}(V^\dagger A)$. Pattern-dependent phases from specialising outer reads are carried through `global_phase`, which `run_batch` applies (`sparse_sim.py:200`) and Aer applies too (probe `a4.py`: $2.8\cdot10^{-16}$). |
| Evaluator: leak definition | ISSUE (N1, N3) | `evaluator.py:423-433`; tolerance semantics, see N1. |
| Evaluator: `inner_span` method | ISSUE (N2, minor) | `evaluator.py:417-420, 287-294` |
| Outer-control block structure, canonical relabelling | OK | `evaluator.py:345-410`: specialisation of cz/ccz/cp/cx/ccx and matrix gates checked line by line; `r_of_o` bit map is consistent with the canonical frame; outputs for different outer patterns are orthogonal, so summing weights over $o$ is correct. |
| Certified pruning bound | OK | `sparse_sim.py:52-82`: per-column $\sqrt{\text{dropped weight}}$ summed (triangle inequality). `dropped_total` = Frobenius bound, added to the error; reject if > $10^{-12}$. |
| Engine certification policy (prompts/003) | OK, with N3 | `evaluator.py:450-451`; `MPS_ACCURACY = 2e-10`. |
| `gauss=True` where it matters (F3) | OK for now | Default `gauss=True` (`evaluator.py:329`). `gauss=False` appears only in `tests/unit/test_evaluator_unit.py`. Locked M1 tests use the default. The compression evaluator is still a stub, see N6. |
| Tolerances per prompts/003 | OK | `synth_tolerances` (`evaluator.py:220-224`) = prompts/003 §2; `Verdict.tolerances` recorded. |
| mcx / clean-ancilla transpile hole | OK, with N4 | `sparse_sim.py:132-148` rejects; root cause identified, see N4. |
| Metrics: T-count, π/4 handling, Ross–Selinger, Qiskit CT | OK | `metrics/logical.py:34-57`: $T_{\rm fixed}$ = t+tdg+rz at odd multiples of $\pi/4$; $N_{\rm rot}$ excludes multiples of $\pi/4$. `cliffordt.py:83` gives $R_z(k\pi/4)=T^k$ up to phase. Word order: H, S, T, X, W are all symmetric, so a reversed word is the transpose, which approximates the diagonal $R_z$ equally well. The order convention therefore cannot cause an error, and it cannot be tested this way either. Estimate $3N_{\rm rot}\log_2(1/\varepsilon)$; CT settings = METHODS §7 (seed 12345). |
| Hard-coded expected numbers in `src/` | OK | Only physics constants (0.75 = $j(j+1)$), policy constants (`MPS_ACCURACY`, tolerances) and docstrings. |
| Silently caught exceptions | OK (note N7) | `evaluator.py:355` turns any `ValueError` into the verdict `disallowed_gate` (not silent: verdict not ok, message kept; fails closed). |
| float64 / complex128 | OK | All arrays complex128/float64; no GPU path. |
| Seeds | OK | transpile seeds 20261104 / 12345; there is no randomness in M0 `src/`. |
| Truncation $j_{\max}$ | N/A | $j_{\max}=\tfrac12$ is the problem definition (no convergence claim). |
| Tests exercise production code | OK | Acceptance tests import production names through `tests/acceptance/_api.py`. Route B and route A are independent. |
| Provenance | OK (minor N8) | `metrics/provenance.py`, `results/store.py`: commit, dirty flag, versions, seeds, UTC. |
| Basis reproducibility (corner singlet phase) | ISSUE (N9, minor) | `physical.py:58-61` |

## Issues

### N1 — Leak tolerance is in probability, error tolerance in amplitude: exact-angle "ok" allows $10^{-6}$ ancilla errors (NON-BLOCKING for the code; STOP-AND-ASK on the tolerance)
`evaluator.py:431-457` compares `max_leak` and `dirty_ancilla` (a weight $\sum|a|^2$) with `tol_leak = 1e-12`. `op_norm_error` (an amplitude) is compared with `tol_err = 1e-10`. For a physical input $\psi$,
$$\|U\psi-V\psi\|^2=\|P_{\rm code}(U-V)\psi\|^2+\mathrm{leak}(\psi),$$
so a leaked amplitude $\delta$ enters the reported error only as $O(\delta^2)$ and the leak test only rejects $\delta>10^{-6}$. Measured (probe `a7.py`: `cry(θ)` from a data $j$-qubit onto an ancilla, target identity, defaults):

| θ (rad) | verdict | `op_norm_error` | `max_leak` (weight) | true leaked amplitude |
|---|---|---|---|---|
| $1.0\cdot10^{-6}$ | ok | $3.4\cdot10^{-13}$ | $2.5\cdot10^{-13}$ | $5.0\cdot10^{-7}$ |
| $1.9\cdot10^{-6}$ | ok | $6.2\cdot10^{-13}$ | $9.0\cdot10^{-13}$ | $9.5\cdot10^{-7}$ |
| $2.1\cdot10^{-6}$ | `dirty_ancilla` | $7.1\cdot10^{-13}$ | $1.1\cdot10^{-12}$ | $1.05\cdot10^{-6}$ |

So "exact to $10^{-10}$" really means "exact to $10^{-6}$" for any error that ends up in ancillas. The METHODS §6 justification ("leak ≤ $10^{-12}$ (float64 over ≤ $10^4$ gates accumulates ~$10^{-13}$)") describes an amplitude: amplitude noise of $10^{-13}$ is a weight of about $10^{-26}$. For the analytic M1 circuits this does not matter, because their leaks are either about $10^{-30}$ or $O(1)$. In the M2 loop it does matter: a proposer program that hard-codes a rounded angle in an uncompute step (`0.785398` instead of $\pi/4$, an error of about $10^{-7}$) would pass as "exact". The code does what the locked tests and METHODS specify, so the fixer cannot change it. Per the hard rules this is a "tolerance believed wrong", so the coordinator must stop and ask Digonto.
Suggested fix (planner decision, re-lock): add a full-isometry criterion
$$\varepsilon_{\rm iso}=\|A-e^{i\varphi}V\|_2+\sqrt{\lambda_{\max}(X^\dagger X)}\le{\rm tol\_err},$$
with $X$ the stacked out-of-code outputs (`Xa@P`, `Xi@P` per outer block, already formed in `evaluator.py:400-403`). For sparse exact-angle circuits this costs nothing and breaks no current test. For aer_mps the leak noise of about $1.6\cdot10^{-11}$ in weight ($4\cdot10^{-6}$ in amplitude) would fail the M0-E5 aer clause at $10^{-9}$, which is why the planner has to decide. Test to add: the `a7.py` cases must be rejected at θ = $10^{-8}$.

### N2 — `inner_span` replaces the physical error instead of bounding it (NON-BLOCKING)
`evaluator.py:417-420`: when no outer bit is read, `err` is the inner-span error alone; `err_phys` is computed but only stored in `extra`. The inner-span error bounds the physical error only if the target can be realised by an operator on the inner links alone ($V_{\rm in}Z=Z\,V_{\rm bd}$ consistent). If the target depends on the outer spins (for example `include_outer_electric=True`), $V_{\rm in}$ is a least-squares fit. In my probes (`a1.py`) this was still caught (inner-span error 0.92 against physical 1.18 for the outer-electric target; 1.84 against 2.0 for a pure outer phase), but nothing guarantees it. On a valid target the two agree ($2.9\cdot10^{-13}$ against $3.3\cdot10^{-15}$; span singular values in $[0.111, 4.0]$, well conditioned).
Fix: `err = max(err_inner_span, err_phys)`, one line, never looser.

### N3 — aer_mps leak and dirty-ancilla weight are per basis input, not per physical state (NON-BLOCKING)
`evaluator.py:425-428`, `aer_check.py:129-130`: `max_leak` = max over the 625 inner basis inputs of $1-\sum|M|^2$. A physical state has up to 16 inner components per outer pattern (probe `a6.py`: $\max(\|c\|_1/\|c\|_2)^2=16.0$), so coherent leak can be up to 16 times the reported value. `certified=True` is still set when the tolerances are at least $2\cdot10^{-10}$. METHODS calls this leak "approximate, uncertified", but the `certified` flag does not reflect that.
Fix: in the aer path also compute ${\rm leak}_k=\max(0,1-w_{\rm code}[k])$ (where `w_code` is already accumulated from `M@P`) and report the maximum of both.

### N4 — Root cause of the mcx hole is `qubits_initially_zero=True` (NON-BLOCKING, hardening)
`sparse_sim.py:174,184`, `metrics/logical.py:27`. Qiskit 2.5.2 `transpile` assumes by default that untouched qubits are $|0\rangle$ and uses them as clean ancillas. Probe `a8.py`: `MCXGate(4)` on 8 qubits gives $\max|U-U_{\rm transpiled}|=1.00$ with the default and $1.3\cdot10^{-15}$ with `qubits_initially_zero=False`. The name-based rejection works today: mcp, mcrz, mcry, mcrx and c3sx translate exactly (`a3.py`, ≤ $1.4\cdot10^{-15}$), and MCMT / `.control(3)` are rejected (`a9.py`). Passing `qubits_initially_zero=False` in every `transpile` call that sees data qubits would remove the whole class of problems; keep the rejection for the T-count policy.

### N5 — Route-B signs are pure gauge at $j_{\max}=\tfrac12$; no sign check exists for later use (NON-BLOCKING, M3 note)
$K$ is a matching (8 disjoint 2×2 pairs), so its non-zero pattern has no cycles and every sign can be removed by a diagonal $D$. The 6j phase convention therefore has no physical consequence at $j_{\max}=\tfrac12$, and no test can see it. For M3 the risks are:
- (a) A spin-network encoding whose physical vectors are matched to route-A states by label without the gauge $D$ from `gauge_align` will fail the evaluator on signs. This is loud, not silent: build its `target` as $D^\dagger V_A D$ or define its vectors through $D$.
- (b) Any use of route B at $j_{\max}=1$ (cycles appear) has no independent sign check. Before relying on it, add a gauge-invariant test, for example a $j_{\max}=1$ spectrum or ${\rm tr}\,(P+P^{\mathsf T})^{n}$ against an independent route.

### N6 — Compression evaluator must hard-wire `gauss=True` and Gauss tolerances (NON-BLOCKING, M2 note)
`compress/evaluate.py` and `compress/spec.py` are stubs. `TaskSpec` has `tol_err`, `tol_leak`, `eps` but no `tol_gauss`. The `trial` mode uses a seeded subset of inputs. When M2 is built: always pass `gauss=True` (F3: a span-leak amplitude $\delta$ is seen only as $\delta^2$ otherwise), use `synth_tolerances` for synthesised verdicts, and add a unit test that rejects the `crx(1e-5)` circuit from reports/tests/009 F3 through `evaluate_program`.

### N7 — `except ValueError` maps every ValueError to `disallowed_gate` (NON-BLOCKING)
`evaluator.py:355`: layout errors from `_canonical_perm` and any ValueError raised inside `_translate`/`_outer_reads` are reported as `disallowed_gate`. The verdict is still not ok and keeps the message, so it fails closed. Suggest separate reasons (`bad_layout`) so that loop statistics are not misleading.

### N8 — Minor documentation and provenance (NON-BLOCKING)
- `evaluator.py:14` docstring says leak includes "code-space weight outside the physical span". The code (correctly, as in METHODS) does not include it. Update the docstring.
- `results/store.py:68,95-99`: `verdict_to_dict` drops `Verdict.extra` (`max_span_leak`, `op_norm_error_physical`, `max_dropped_l2`). Persist it.

### N9 — Corner-singlet sign fixed by an argmax over tied moduli (NON-BLOCKING, reproducibility)
`physical.py:58-61`: "largest $|$component$|$ positive" uses `np.argmax` on vectors with exactly or nearly tied moduli. Probe `a5.py` finds 32 tied singlets. Example: corner 0, all $j=\tfrac12$, $J=0$, components $(0.5,0.5,-0.5,-0.5)$ with a gap of $2.2\cdot10^{-16}$ between the largest two moduli, so floating-point rounding (BLAS/LAPACK build, thread count) decides the sign of the basis state. Verdicts and every locked test are invariant under such diagonal $\pm1$ changes (all tests compare moduli or gauge-invariant norms). Any persisted object written in the 433-state basis (stored targets, import maps, failing-input amplitudes) could differ between machines, for example laptop against cluster.
Fix: deterministic tie-break, `p = np.flatnonzero(np.abs(vec) >= np.abs(vec).max() - 1e-10)[0]`, plus a unit test that the basis is bitwise identical with `OMP_NUM_THREADS` set to 1 and to 8.

## Things checked and found correct (no action)
- Specialisation of outer reads: `rz` phase $\pm\theta/2$, `p` $\lambda v$, cz/ccz/cp reduction, cx/ccx control removal, matrix-gate sub-block with little-endian `qs` order (`evaluator.py:113-169`).
- Leak of a superposition is computed coherently (`Xa @ P`, not a sum of per-input leaks) in the sparse path (`evaluator.py:400-403`).
- Aer MPS contraction and global phase agree with the sparse engine ($2.8\cdot10^{-16}$).
- Gauss residual in Paulo convention uses $V_PGV_P^{\mathsf T}$; the evaluator decodes to CG and uses CG generators (consistent).
- Closed sector $[\begin{smallmatrix}0&-2/g^2\\-2/g^2&3g^2/2\end{smallmatrix}]$ follows from $\langle\chi_{1/2}|W|0\rangle=\langle0|W|\chi_{1/2}\rangle=1$ (Haar orthonormality of characters).
- `_schedule` respects per-qubit order (exact reordering only of disjoint gates); `_coalesce` packing bound is correct.
