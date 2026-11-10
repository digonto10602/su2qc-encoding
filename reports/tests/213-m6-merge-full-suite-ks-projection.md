# Tester report 213 — full suite on the laptop-milestone-2 merge, and independent check of the rishon -> Kogut-Susskind (KS) projection

- Date: 2026-11-06
- Git commit: `a5d8121` (branch `m5-rishon`, merge of laptop master `5111d69` = tag `milestone-2` into our M5/M5x work + `ec4451d`)
- Prompt in force: `prompts/202-rishon-m5x-wait-robustness.md` (an untracked `prompts/203-rishon-m6-plan.md` and `reports/research/202-*` appeared during the run; ignored as instructed)
- Mode: `full` (part A) plus an independent verification of a side check (part B), tester Claude Sonnet 5.5
- Related: `reports/tests/212-m5x-gate-full.md` (previous full run, before the merge), `reports/tests/207`, `208`; builder's side check `scripts/m5_ks_projection.py`, `results/rishon/ks_projection.json`
- Raw numbers: `results/rishon/tester-213-suite-summary.json`, `results/rishon/tester-213-ks-independent.json` (script `results/rishon/tester-213-ks-independent.py`), `results/rishon/tester-213-ks_projection_rerun.json`

Jargon, once: *KS* = Kogut-Susskind lattice gauge theory (the 12-qubit track). *P* = the projector that, on every spin-0 link, keeps only one combination $|\sigma_\pm\rangle=(|A\rangle\pm|B\rangle)/\sqrt2$ of the two singlet link states $A$ (code 3) and $B$ (code 12) and leaves the four quartet states $Q$ alone; $V$ = the isometry (38 432 x 433) onto the range of $P$ inside the physical space. *Leakage* of an operator $C$ = $\|(1-P)\,C\,V\|$, the norm of the part that leaves the singlet subspace. *Gauge* here = a diagonal $\pm1$ sign matrix $D$ (relabelling of basis phases).

Environment: conda env `su2qc-coding`, `PYTHONPATH=src`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, cores 10-19 (`taskset`), no random numbers anywhere (all suites deterministic; seed field "none").

---

## 1. What was asked

(A) full suite on the merged HEAD: acceptance m0, m1, m2, m5, m5x (slow tests included), unit tests, `acceptance-check`, Lean build of changed targets, with the lock/tag bookkeeping of the merge confirmed. (B) independent verification of the builder's claim that the rishon one-Trotter-step circuit restricted to one singlet combination per spin-0 link does or does not reproduce the KS step.

## 2. Part A — full suite

### 2.1 Commands

```
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update .
cd lean && lake build --no-build                      # replay check (before)
cd lean && taskset -c 10-19 lake build Su2Plaq.Gates Su2Plaq.Rewrites Su2PlaqCert su2plaq_cert   # changed targets
cd lean && taskset -c 10-19 lake build                # picks up Su2Plaq.Rishon.HBLink (depends on the rebuilt Su2PlaqCert)
cd lean && lake build --no-build                      # rc 0 afterwards
taskset -c 10-13 pytest -n 4 -p no:cacheprovider tests/acceptance/m5 --durations=15 -q       # slow tests included
taskset -c 14-19 pytest -n 6 -p no:cacheprovider tests/unit | tests/acceptance/m0 | m1 | m2 | m5x --durations=10 -q   # one after the other
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
```

### 2.2 Results

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `tests/unit` | all pass | 520 passed, 0 failed (350 s; HEAD hash `a5d8121` contains no "c1", so the known laptop flake could not trigger) | - | PASS |
| `tests/acceptance/m0` | all pass | 34 passed (21 s) | - | PASS |
| `tests/acceptance/m1` (incl. slow) | all pass | 22 passed (156 s) | - | PASS |
| `tests/acceptance/m2` (laptop machinery + Lean checker) | all pass | 46 passed (208 s) | - | PASS |
| `tests/acceptance/m5` (34 tests incl. slow) | all pass | 34 passed, 0 failed (1096 s wall with 4 workers; `T1[UB]` 517.6 s, `T1[step]` 506.0 s) | - | PASS |
| `tests/acceptance/m5x` | all pass | 6 passed (7 s) | - | PASS |
| pending tests (any acceptance test still raising `NotImplementedError`) | none in m0-m2, m5, m5x | 0 | - | PASS |
| `python tools/check_lock.py` | LOCK OK | LOCK OK | - | PASS |
| `~/.claude/bin/acceptance-check` | expected complaint (laptop-approved m2 change) | `FAIL: tests/acceptance differs from acceptance-v9`; changed files: `tests/acceptance/LOCK.json`, `m2/test_compress_machinery.py`, `m2/test_lean_formal.py` | - | FAIL as expected (explained below) |
| m0, m1, m2 byte-identical to laptop-master `5111d69` and to tag `laptop-acceptance-v7` | identical | `git ls-tree -r` blob lists of `tests/acceptance/{m0,m1,m2}` identical to both; `git diff --stat 5111d69 HEAD` on m0/m1/m2/`_api.py`/`conftest.py` empty | exact | PASS |
| m5, m5x, m0, m1 unchanged since our `acceptance-v9` | unchanged | `git diff --stat acceptance-v9 HEAD -- tests/acceptance/{m0,m1,m5,m5x}` empty | exact | PASS |
| LOCK.json change vs `acceptance-v9` | only the two m2 hashes | exactly two lines changed (`test_compress_machinery.py`, `test_lean_formal.py` sha256) | exact | PASS |
| Lean: `lake build --no-build` replays; `Structure/Counts.olean` mtime unchanged; no rebuild of Counts.lean | unchanged | before and after both builds: `2026-11-05 23:54:26.301842497 -0500`; Counts only "Replayed"; `--no-build` rc 0 at the end | exact | PASS |
| Lean: changed targets build | build OK | built `Su2PlaqCert.{K,Sha256,Pins,Laurent,State,Circuit,Gates,...}`, `Su2Plaq.Gates` (3.2 s), `Su2Plaq.Rewrites`, `Su2Plaq.Rishon.HBLink`, `Su2Plaq.Rishon.Bridge`, `Su2Plaq`, exe `su2plaq_cert`; wall 10.5 s and 6.7 s, peak RSS 6.9 GB / 6.8 GB | - | PASS |
| no `native_decide` under `lean/Su2Plaq/` | none | `grep -rn native_decide lean/Su2Plaq` empty | - | PASS |
| Lean checker `lake exe su2plaq_cert check` exercised | runs and accepts/rejects | covered by passing `m2/test_lean_formal.py::test_lean_certificate_general_circuit` (36 s) and `test_lean_structure.py::*` | - | PASS |

### 2.3 Notes for part A

- **A-N1 (formerly pending, now running).** Report 212 listed m2 as "7 pass + 39 pending-expected". On this HEAD all 46 m2 tests run and pass, so the 39 tests that waited for the laptop's checker and compression machinery are no longer pending. No m0-m2, m5 or m5x test is pending.
- **A-N2 (why `acceptance-check` fails).** The lock bookkeeping compares against our tag `acceptance-v9`. The merge brought the laptop's approved change to two m2 test files (a Qiskit 2.5.2 detail: `inst.operation.params[0] = ...` was a silent no-op, now the instruction is rebuilt; see the docstrings in `_perturb_first_rotation` and `_with_first_angle`). Those two files and `LOCK.json` are the only differences; they are byte-identical to the laptop. The coordinator's new acceptance tag clears the complaint. I did not tag or lock anything.
- **A-N3 (test side effect on a tracked file).** The locked laptop test `m2/test_lean_structure.py::test_structure_json_and_spec_section` rewrites `compress/lean/structure.json` (only `provenance.git_commit` 4fa765b -> a5d8121 and `structure_certificate.seconds` change). After a suite run the tree is dirty and every `provenance()` written afterwards records `git_dirty: true`. I restored the file with `git checkout compress/lean/structure.json` so the tree holds only my new untracked files and the planner's untracked files. Laptop-owned behaviour, not a failure.
- **A-N4.** Two benign things from the earlier scratch area: a stale `m5x.log` in the shared scratchpad from an earlier session showed one failure (`test_M5X_O1_outer_row_results_file`); it is not from this run (this run: 6 passed, file times 10:38 vs 14:4x). Nothing to fix.
- **A-N5.** `T1[step]` is still not marked slow (planner item from benchmark F1); in this run it took 506 s with 4 workers and the m5 suite 1096 s wall.
- Failures: none. Laptop-owned vs ours: not applicable (nothing failed), so no scratch worktree on `5111d69` was needed.
- Peak memory: largest single process 6.96 GB (< 10 GB cap); summed over processes 10.85 GB (m5, 4 workers) and 13.66 GB (unit/m1/m2/m5x with 6 workers, run in parallel with the m5 job; the m5 job itself was a separate process tree, so the machine peak was about the sum of the two sampled trees plus the Lean and script jobs). Lean build 6.9 GB.

## 3. Part B — independent check of the KS projection

### 3.1 The builder's claim and the question

Digonto's question: does the rishon step circuit, restricted to one singlet combination per spin-0 link, reproduce the KS step? Builder's claims: rank of $P$ is 433; $PH_EP=H_E^{KS}$; $PH_BP=H_B^{KS}$ up to a $\pm1$ gauge with scale $c=1$; leakage $\|(1-P)H_BP\|=\sqrt{28}\approx5.2915$ against $\|PH_BP\|=2$; at $(\alpha,\beta)=(0.37,0.61)$ leakage 0.8615 and gauge-minimised distance to the KS step 1.990; at small $\beta$ leakage $\propto\beta$ ($\to5.27\beta$) and mismatch $\propto\beta^2$ ($\to13.97\beta^2$, predicted $\tfrac12\cdot28=14$).

### 3.2 (1) Rerun of the script on the clean HEAD

Command: `PYTHONPATH=src taskset -c 10-19 python scripts/m5_ks_projection.py --out results/rishon/tester-213-ks_projection_rerun.json` (I used a separate output file so the tracked `ks_projection.json` is not touched).

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| numeric leaves of rerun vs committed `ks_projection.json` (457 numbers) | equal | largest relative difference over entries with $|v|>10^{-6}$: $4.0\times10^{-12}$; 80 rounding-level entries ($\le4.1\times10^{-13}$ in magnitude) differ at most at that level; same keys | $10^{-10}$ | PASS |
| rerun `provenance.git_dirty` | false | false (commit `a5d8121`) | exact | PASS |
| committed `ks_projection.json` provenance | clean | **commit `9583d4d`, `git_dirty: true`, command string names the old script `scripts/rx_ks_projection.py`** | - | NOTE (B-N1) |

Wall time 255 s (script's own clock), peak RSS 3.12 GB (script) / 3.20 GB (`/usr/bin/time -v`), CPU contended by the test jobs.

### 3.3 (2) Independent recomputation (does not import the script)

Method (all in `results/rishon/tester-213-ks-independent.py`, 151 s, 0.82 GB):

- Rishon link operators from a bit-level Jordan-Wigner (own code), $U_{ij}=c_{L,i}c^\dagger_{R,j}$ restricted to the six two-rishon states $[3,5,6,9,10,12]$; $H_B^R=-(W+W^{\mathsf T})$ with $W=\mathrm{Tr}(U_bU_rU_t^\dagger U_l^\dagger)$ on the 1296 inner codes, $H_E^R=\tfrac34\times(\#Q\text{ inner links})$. Matches the library's `rops.h_magnetic_inner()` / `h_electric_inner()` with difference 0.0 and 0.0.
- The 433 columns $V$: each rishon basis state of `rishon_basis()` is assigned to its KS label (type $Q\to j=\tfrac12$, $A,B\to j=0$), weight $w_s=\prod_{\text{spin-0 links}}(1\text{ or }\pm1)/\sqrt2$ (renormalised per label), $V_g=\sum_s w_s\psi_s$; reductions $V^\dagger(O\otimes\mathbb 1)V$ summed over all 32 256 outer patterns, with my own block assembly.
- KS $H_B$ from `su2plaq.exact.spinnet.h_magnetic_phys_6j` (route B); KS $H_E$ from the labels. KS step $=e^{-i\beta cH_B^{KS}}e^{-i\alpha H_E^{KS}}$ built by me with `scipy.linalg.expm` (route A and B spectra agree to $2.7\times10^{-15}$).
- Gauge $D$: my own breadth-first sign propagation over the 305 components of the KS $H_B$ graph (ratios $H^R_{ij}/(cH^{KS}_{ij})$ all exactly real $\pm1$).
- Leakage: (i) from $\lambda_{\max}(V^\dagger H^2V-(V^\dagger HV)^2)$ and from $\sigma(W)$, and (ii) by an explicit residual $R=CV-V(V^\dagger CV)$, assembled per outer pattern, whose largest singular value is the leakage.
- Closure identity (the reason $P$ preserves the group span and has rank 433): flipping the nibble $A\leftrightarrow B$ on a spin-0 link maps each basis vector exactly onto the basis vector of the flipped label. Checked on all 307 520 (state, spin-0 link) pairs.

| check | expected | got (independent) | builder's value | tolerance | verdict |
|---|---|---|---|---|---|
| groups: 433, sizes $2^{n_0}$, total 38 432 | yes | yes | yes | exact | PASS |
| closure identity, 307 520 flips: key sets equal and amplitudes equal | max diff 0 | 0.0 | (not checked this way) | $10^{-10}$ | PASS |
| rank of $P$ on the physical space: $\sum_s\langle\psi_s|P|\psi_s\rangle=\sum_s2^{-n_0(s)}$, and $V^\dagger V=\mathbb 1$ | 433 and $<10^{-10}$ | 433.0000 and $3.2\times10^{-15}$ | 433, $4.6\times10^{-14}$ | $10^{-10}$ | PASS |
| $PH_EP$ diagonal, difference to KS $H_E$ and off-diagonal | 0 | $9.3\times10^{-15}$ and $3.7\times10^{-16}$ | $9.3\times10^{-15}$ and $4.1\times10^{-16}$ | $10^{-10}$ | PASS |
| $c$ (least squares of $|PH_BP|$ on $|H_B^{KS}|$), `plus` and `minus` | 1 | 0.9999999999999991 (both signs) | 1.0 | $10^{-10}$ | PASS |
| supports of $PH_BP$ and $H_B^{KS}$ equal; all entry ratios real $\pm1$ | yes | yes (imaginary part of ratios 0.0) | yes | exact | PASS |
| gauge residual $\max|PH_BP-cDH_B^{KS}D|$ | $\le10^{-10}$ | $4.4\times10^{-16}$ (both signs) | $1.8\times10^{-15}$ | $10^{-10}$ | PASS |
| $\|PH_BP\|$, $\|H_B^{KS}\|$ | 2, 2 | 2.0000000000000004, 2.0000000000000018 | 2.0, 2.0 | $10^{-10}$ | PASS |
| $\|(1-P)H_BP\|$ (Gram route) | $\sqrt{28}=5.29150$ | 5.291502622129188 ($\lambda_{\max}=28.000000000000064$) | 5.291502622129 | $10^{-10}$ | PASS |
| $\|(1-P)H_BP\|$ (explicit residual route) | 5.29150 | 5.291502622129187 | - | $10^{-10}$ | PASS |
| leakage of $U(\alpha,\beta{=}0.61)$: Gram / explicit residual | 0.8615 | 0.8615137089541051 / 0.861513708954105 | 0.8615137089541056 | $10^{-10}$ | PASS |
| leakage at $\beta=0.03$: Gram / explicit residual | - | 0.15805561816988 / 0.15805561816986 | (table) | $10^{-10}$ | PASS |
| gauge-minimised distance to KS step at $\beta=0.61$ | 1.990 | 1.9904120121517461 (ungauged: 1.7959856) | 1.9904120121517452 | $10^{-10}$ | PASS |
| small-$\beta$ leakage coefficient leak$/\beta$ at 0.03 | $\to\sqrt{28}=5.2915$ | 5.2685 (0.43 % below) | 5.27 | 2 % | PASS |
| small-$\beta$ mismatch coefficient mismatch$/\beta^2$ at 0.03 | $\to\tfrac12\cdot28=14$ | 13.968 (0.23 % below); at 0.1: 13.646 (2.5 % below, outside the window, still outside the asymptotic regime) | 13.97 | 2 % at $\beta=0.03$ | PASS |
| local log-log slopes (0.1 to 0.03): leak, mismatch | 1, 2 | 0.963, 1.981 | 0.963, 1.981 | scaling | PASS |
| `minus` sign gives the same numbers as `plus` | same | identical to all printed digits | same | - | PASS |
| control variant "$A$ only" ($P_Q+|A\rangle\langle A|$) | should NOT match | $c=0.195$, supports differ, modulus residual 1.80; leakage norm 5.657 ($=4\sqrt2$); mismatch/$\beta^2$ at 0.03 = 60 | same | - | PASS (control behaves as the builder says) |
| unitary exactness used above (dense `expm` vs eigendecomposition vs `expm_multiply`, $\beta=0.03,0.61$) | agree | $2.0\times10^{-15}$, $\le4.2\times10^{-16}$; unitarity $\le8.9\times10^{-16}$ | - | $10^{-10}$ | PASS |

Full step table (variant `plus`, $\alpha=0.37$):

| $\beta$ | leakage $\|(1-P)U V\|$ | $\sigma_{\min}(V^\dagger UV)$ | gauged mismatch $\|W-DU^{KS}D\|$ | mismatch$/\beta^2$ | $\tfrac12\cdot28\beta^2$ |
|---|---|---|---|---|---|
| 0.61 | 0.8615 | 0.5077 | 1.9904 | 5.349 | 5.209 |
| 0.30 | 0.9999 | 0.0148 | 0.9987 | 11.10 | 1.260 |
| 0.10 | 0.5040 | 0.8637 | 0.1365 | 13.65 | 0.140 |
| 0.03 | 0.1581 | 0.9874 | 0.01257 | 13.968 | 0.01260 |

### 3.4 (3) The analytic claims

- **Second-order coefficient.** $E_K$ denotes $e^{-i\alpha H_E^{KS}}$. Because $H_E$ is constant on each $A/B$ group, $U_EV=VE_K$, so $W-U^{KS}=(V^\dagger e^{-i\beta H_B}V-e^{-i\beta M})E_K$ with $M=V^\dagger H_BV$. Expanding, the $O(\beta)$ terms cancel, and the $\beta^2$ term is $-\tfrac{\beta^2}{2}(V^\dagger H_B^2V-M^2)E_K$. The matrix $V^\dagger H_B^2V-M^2=R^\dagger R$ is the Gram matrix of $R=(1-P)H_BV$, so its operator norm is $\|(1-P)H_BP\|^2$. Hence mismatch $=\tfrac12\|(1-P)H_BP\|^2\beta^2+O(\beta^3)=14\beta^2$. Numerically 13.968 at $\beta=0.03$ (0.23 % low; the $O(\beta^3)$ correction is the cause). The leakage to first order is $\beta\|(1-P)H_BP\|=5.29\beta$ (5.2685 at 0.03). Both claims hold within the 2 % tolerance.
- **Closed pair.** The rishon inner $H_B$ has a unique top eigenvalue $4\sqrt2=5.656854$ (multiplicity 1) with partner $-4\sqrt2$; KS $\|H_B\|=2.0000$. The state $\tilde Q=(\psi_++\psi_-)/\sqrt2$ lives entirely on all-quartet inner codes (weight 1.0000), is fixed by the inner projector ($\|P\tilde Q-\tilde Q\|=4\times10^{-16}$), and $H_B\tilde Q=4\sqrt2\,\varphi$ with $\varphi=(\psi_+-\psi_-)/\sqrt2$. Numbers: $\|H_B\tilde Q\|^2=32.0000$, $\|PH_B\tilde Q\|^2=4.0000$ (that is the KS coupling $2^2$), $\|(1-P)H_B\tilde Q\|^2=28.0000$, $\|P\varphi\|^2=0.125$. So the closed pair attains the global maximum leakage 28, and the projected coupling $\sqrt{32\cdot\tfrac18}=2$ equals KS only because the overlap is exactly $1/(2\sqrt2)$. The closed block rotates by $\theta=4\sqrt2\beta=3.4507$ rad at $\beta=0.61$ (more than $\pi$), while the KS block rotates by $2\beta=1.220$ rad. One U_B on $\tilde Q$ leaks $|\sin\theta|\sqrt{1-\|P\varphi\|^2}=0.28454$ (numerical $0.28454$). The two block angles agree only at first order after projection ($4\sqrt2\beta\cdot\tfrac1{2\sqrt2}=2\beta$), not beyond.

### 3.5 (4) Over-claims and extra facts (the answer to Digonto's question is in B-N2)

- **B-N1 (provenance).** The committed `results/rishon/ks_projection.json` was written from commit `9583d4d` with a dirty tree and a command string naming `scripts/rx_ks_projection.py`, a file that no longer exists. The rerun on clean `a5d8121` reproduces every number (relative $4\times10^{-12}$). The `provenance.command` string in the script is a hard-coded text, not the actual `argv`. Recommend the coordinator replace the committed file with `tester-213-ks_projection_rerun.json` (or have the builder regenerate it on the commit that will be tagged).
- **B-N2 (the answer).** The numbers confirm that the Hamiltonian blocks agree ($PH_EP=H_E^{KS}$ and $PH_BP=H_B^{KS}$ up to a $\pm1$ gauge, $c=1$) but the step does NOT reproduce the KS step. $[P,H_B]\ne0$: $\|(1-P)H_BP\|=\sqrt{28}$ is 2.6 times $\|PH_BP\|=2$. At the nominal angles the circuit loses amplitude 0.86 out of the subspace, the projected block has $\sigma_{\min}=0.51$, and the gauge-minimised distance to the KS step is 1.990 out of a maximum 2. Agreement of $PHP$ with KS is a first-order statement only. Any wording like "reproduces the KS Hamiltonian" must be restricted to the projected block, not the dynamics.
- **B-N3 (what "mismatch $\propto\beta^2$" does and does not mean).** It is the mismatch of the projected one-step block; the leakage is first order ($5.29\beta$) and it does not shrink with finer Trotter steps at fixed evolution time. The deviation of exact evolution $\|PU_R(t)V-e^{-itM}\|\approx14t^2$ and leaked amplitude $\approx5.29t$ are properties of $H_B^R$ itself, independent of the Trotter angle. So the $\beta^2$ behaviour must not be read as convergence to KS as the step is refined. (At $\beta=0.3$ a single step already has mismatch 0.9987; the table above.)
- **B-N4 (extra check, mine, stronger than the builder's).** The spectrum of the KS $H_B$ (433 physical states, route A and B agree to $2.7\times10^{-15}$) is $\{\pm2\ (16),\ \pm1\ (96),\ \pm\tfrac12\ (16),\ 0\ (177)\}$. The rishon inner $H_B$ spectrum is $\{\pm4\sqrt2\ (1),\ \pm2\ (48),\ \pm1\ (32),\ 0\ (1134)\}$ and the physical-space spectrum is a subset of it (H_B acts on the inner links only). The eigenvalues $\pm\tfrac12$ do not occur on the rishon side. Therefore no subspace of any kind that is invariant under $H_B^R$ can carry the KS $H_B$ unitarily, so the failure is not a poor choice of the singlet combination: it cannot be repaired by choosing different $\sigma$'s, only by a different embedding or a different rishon Hamiltonian. (Scope: exact invariant-subspace embedding of $H_B$; I did not examine approximate or time-dependent embeddings.)
- **B-N5.** The builder's "variant A" control is correct as a control (it fails, as it should) but its gauge fit has no meaning there (supports differ); in the JSON the numbers for A are not part of the claim. The builder counts 305 components of the KS graph and so do I for the `plus`/`minus` variants (my count for A is 417 because the support differs).
- **B-N6.** Nothing wrong found in the builder's numbers; all agree with the independent route to at least 12 digits where comparable. The only over-claim risk is wording (B-N2, B-N3). Dependencies shared with the builder (the physical basis vectors from `rishon_basis()`, KS labels, `h_magnetic_phys_6j`, and the plaquette formula $W=\mathrm{Tr}(U_bU_rU_t^\dagger U_l^\dagger)$ of METHODS-rishon) are validated by the exact match of $PH_BP$ with $H_B^{KS}$ to $4\times10^{-16}$ and by the Gauss-law checks done in reports 201-203.

## 4. Verdicts

- **Part A: PASS.** 662 tests passed (unit 520, m0 34, m1 22, m2 46, m5 34, m5x 6), 0 failed, 0 pending, 0 new failures. `acceptance-check` fails only for the explained reason (lock still at `acceptance-v9` while the merge brought the laptop-approved m2 change); m0-m2 are byte-identical to laptop-master `5111d69` and to `laptop-acceptance-v7`.
- **Part B: PASS** (the builder's claims reproduce and are independently confirmed, with the wording caveats B-N1 to B-N3). Physics result: the rishon step restricted to one singlet combination per spin-0 link does not reproduce the KS step.

Wall time of the whole run about 25 min (suites ran partly in parallel); the longest single job was `m5` at 1096 s. Peak RSS: 6.96 GB largest single process, 10.85 GB and 13.66 GB summed per sampled process tree, Lean build 6.9 GB, rerun script 3.2 GB, independent script 0.82 GB.
