# Tester report 011 — M0 step 0.8 evaluator, final recheck (mode: step)

- Date: 2026-11-04
- Commit: `05f0391` (acceptance-v3) + uncommitted step-0.8 working tree
- Plans in force: `prompts/002-…` + addendum `prompts/003-gauss-tolerance-synthesised-circuits-engine-policy.md`
- Related: reports/tests/009, 010
- Raw numbers: `results/evaluator_0_8_final_*.json` (seed 20261104); scripts `tests/independent/evaluator_0_8/` (new: `adv10_sparse_proxy.py`, `adv11_tol.py`, `adv12_paulo_p1.py`)

## VERDICT: PASS (no failures; the only open item is a risk for M1-T1/UB, section 5)

## 1. Step checks (all run in place)
| check | expected | got | result |
|---|---|---|---|
| `check_lock.py` / `acceptance-check` | pass | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v3` | PASS |
| `pytest --collect-only -q tests/acceptance` | clean, 84 | 84 collected, no errors | PASS |
| unit tests (`-n auto`) | all pass | 103 passed, 37.8 s | PASS |
| `pytest -n auto -m "not slow" tests/acceptance/m0` | only step 0.9/0.10 PENDING | 26 passed, 6 PENDING, 0 real failures | PASS |
| E3, E4, E5 (E5 = amended v3 version: `certified`, `engine_accuracy`, `tolerances`, aer_mps at 1e-9, uncertified aer_mps at defaults) | pass | all pass | PASS |
PENDING, by message: `logical_metrics is not built yet` → M0-M1 (macro costs); `pygridsynth_word is not built yet` ×3 → M0-M2 `[1e-4, 1e-6, 1e-8]`; `ct_compile is not built yet` → M0-M3; `save_result is not built yet` → M0-R1. All belong to steps 0.9/0.10.

## 2. Spot checks of prompts/003 §4 (`adv11_tol.py`, 26 checks, all PASS)
- `synth_tolerances(n_rot, eps)` equals $\{N\varepsilon+10^{-9},\ (N\varepsilon)^2+10^{-12},\ N\varepsilon+10^{-9}\}$ exactly, with key order, for (14,1e-6) → (1.4001e-5, 1.97e-10, 1.4001e-5), (4,1e-6), (18,1e-6) → (…, 3.25e-10, …), (16,1e-4), (0,1e-6). `TOL_GAUSS = 1e-10`.
- `Verdict.tolerances` is filled on every exit: `writes_outer` (default and custom tolerances, e.g. 3e-5/2e-9/7e-6 returned verbatim), `disallowed_gate` with `tol_gauss=None` → `tol_gauss=1e-10`, `unsimulable`, and ok verdicts; `tol_gauss=3e-7` is recorded as given.
- The Gauss reason uses the effective tolerance: `crx(ε)` on a data $q_m$ with a trivial outer read (physical method, so op-norm error is second order, $3\cdot10^{-15}$) has residual exactly $\varepsilon/2$: for ε=2e-8 the residual is $1.000\cdot10^{-8}$: default tolerance → `gauss`; `tol_gauss=2e-7` → ok; `2e-9` → `gauss`; at the edge `r(1+10^{-6})` → ok, `r(1-10^{-6})` → `gauss`. Same pattern for ε=2e-9 (residual $1.000\cdot10^{-9}$). `failing_inputs` names the states with the residual.
- `certified` (aer_mps, $U_E$): tol 1e-9/1e-9 with default Gauss tol → False; 1e-9 ×3 → True; 1e-9/1e-9 with `gauss=False` → True; default tolerances → False; `synth(14,1e-6)` → False; `synth(18,1e-6)` → True; `synth(4,1e-6)` → False; P1's dict 2e-5/1e-9/2e-5 → True; sparse at `synth(14,1e-6)` → True. All as the formula $\text{acc}\le\min(\text{tol\_err},\text{tol\_leak},\text{tol\_gauss}_{\rm eff})$ predicts (acc $=2\cdot10^{-10}$).

## 3. Regression of the known-verdict list
adv1–adv8 and the 24-order register fuzz: identical results to report 010 (same numbers: $U_E$ $1.2\cdot10^{-13}$/$3.3\cdot10^{-15}$, 12-qubit $U_B$ ok, oracles ≤ $4.4\cdot10^{-15}$, `specialise` worst $4.2\cdot10^{-15}$, layout probes rejected/accepted correctly, fuzz spread 0). The FAIL lines are the same known ones (my own check errors; `id` on outer; the `inf−inf` printing in the `writes_outer` fuzz; vacuous Gauss-sign controls). One changed line: the old adv6 check "aer_mps `tol_err=tol_leak=1e-8` is certified" now gives `certified=False`, because the effective Gauss tolerance defaults to $10^{-10}<2\cdot10^{-10}$ — the new policy of prompts/003 §3, not a regression (with `tol_gauss=1e-8` or `gauss=False` it is True).
Paulo's QPY with the amended M1-P1 conditions (`adv12_paulo_p1.py`, engine auto → aer_mps, 107.7 s): `ok=True`, op-norm error $2.905\cdot10^{-6}$ (≤ 2e-5), leak $4.19\cdot10^{-12}$ (≤ 1e-9), dirty $1.1\cdot10^{-13}$, Gauss $1.160\cdot10^{-10}$ (≤ 2e-5), `certified=True`, `engine_accuracy=2e-10` (≤ 1e-9), `tolerances == {2e-5, 1e-9, 2e-5}`; the inverse target is rejected (err 1.819). So M1-P1 is passable by the evaluator once `circuits.twelve.paulo_circuit` exists.

## 4. Builder's note: is the aer_mps floor above the synthesised leak tolerance? Yes — confirmed
Certification needs $2\cdot10^{-10}\le\text{tol\_leak}=(N\varepsilon)^2+10^{-12}$, i.e. $N\varepsilon\ge1.41\cdot10^{-5}$, i.e. $N_{\rm rot}\ge15$ at $\varepsilon=10^{-6}$. Table at $\varepsilon=10^{-6}$ (tol_leak and certifiable with aer_mps):
| circuit | $N_{\rm rot}$ | tol_leak | aer_mps certified? |
|---|---|---|---|
| M1-T1 `UE` | 4 | $1.7\cdot10^{-11}$ | no |
| M1-T1 `UB` | 14 (M1-P2 asserts `n_rot == 14` for the logical circuit) | $1.97\cdot10^{-10}$ | no — misses by 1.5 % (acc $2.0\cdot10^{-10}$) |
| M1-T1 `step` | ≈ 18 | $3.25\cdot10^{-10}$ | yes |
| M1-P1 Paulo | tolerance dict is explicit | $10^{-9}$ | yes (measured) |

M1-T1 calls `evaluate(synth, enc, V, **tol)` with the default `engine="auto"` and then asserts `v.certified`. Hence for UE and UB the **sparse** engine must finish under its cap (5e6 amplitudes); a fallback to aer_mps would make the locked test unpassable (`certified` False) even for a correct circuit. No locked test is unpassable by construction: sparse is exact and certified at any tolerance.

Can the sparse engine do it? Proxy (`adv10_sparse_proxy.py`, real pygridsynth words at $10^{-6}$, 14 words each as `ccx; h; word; h; ccx` on random data controls, 625 inputs, ~2300 gates): stored amplitudes at the end are $2^k$ per input where $k$ = number of **distinct qubits** hosting a rotation word, not $N_{\rm rot}$: 14 words on 3 target qubits → 5000 amplitudes (8 per input), 0.8 s; on 4 target qubits → 10 000, 1.3 s; on 14 distinct target qubits → `SimCapExceeded` after 53 s. So: UE (4 rotations, 4 distinct qubits $q_j$ of the links): fine (16 per input). UB passes sparse if its rotations sit on ≲ 13 distinct qubits; Paulo-style circuits keep rotations on a few work qubits, so this is probable but I cannot confirm until the M1 circuit exists. Risk: the M1 UB builder must keep the 14 rotation targets on few distinct qubits (or reuse them), otherwise `auto` would fall back to aer_mps and M1-T1[UB] cannot certify (leak tolerance $1.97\cdot10^{-10}<2\cdot10^{-10}$). Mitigation at the planner level, not by me: none needed if the sparse cap holds; if it does not, `cap` in `evaluate` can be raised by the caller only by changing the test (locked), so the circuit design must be the lever.

## 5. Counts
passed 26 (m0 acceptance) + 103 (unit) + 26 (adv11) ; failed 0 ; pending 6 (steps 0.9/0.10) ; new failures vs report 010: 0.
