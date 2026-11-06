# Audit 004: M2 milestone gate — compression machinery, loop results, Lean track

- Date: 2026-11-06
- Auditor: auditor agent (Opus 5.5, high)
- Git commit audited: a8e60e2 (HEAD; the last code/result commit is 5111d69, a8e60e2 only touches `notes/STATUS.md`)
- Commit range: `milestone-1` (5906103) .. HEAD — `src/`, `lean/`, `scripts/`, `docs/METHODS.md`, `prompts/`, plus `compress/archive/twelve/`, `results/compress/twelve/`, `compress/programs/twelve/*`, `compress/lean/certs/`
- Plan in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` §5 + addenda `prompts/003`–`006` (incl. 006 §12); locked tests `acceptance-v7`
- Related: tester reports `reports/tests/024`–`041` (041 = full gate PASS); earlier audits `reports/audits/001`–`003`

## Verdict: PASS WITH NOTES

No blocking issue. The physics of the compressed circuit, the validity rules of the loop, the cost key and the Lean certificate are correct. There are 13 non-blocking notes. N1 (Paulo's T count shown in columns where it does not belong) must be fixed before Report 2 is written. N2 and N3 are provenance and documentation precision.

## What I did

1. Oriented with graphify (`god-nodes`, `query "compress evaluate validity skeleton trial full cache"`, `explain certify_circuit`, `query "load_program callers"`). Then I read `compress/evaluate.py`, `archive.py`, `round.py`, `metrics.py`, `synth.py`, `spec.py`, `provenance.py`, `report.py`, the subset diff of `evaluate/evaluator.py`, `lean/certify.py`, `lean/lemmas.py`, `lean/structure.py` (count facts), `lean/Su2PlaqCert/Check.lean`, `Pins.lean`, the theorem statements in `Su2Plaq/{Evaluator,Gauss,Synthesis}.lean` and `Structure/Counts.lean`, and the best program `compress/programs/twelve/F2/005-outer-t2-peephole.py`.
2. Tabulated all 22 archive entries: `n_inputs` = 433 at the nominal pair and at both alternate pairs, all `sparse` engine and `certified`, evaluator sha, commit, dirty flag, `measured`, Lean status and parent. I also tabulated the 6 round JSONs (synthesis re-verification of every round best: ok; T of the synthesised circuit = key T).
3. `git diff --stat a4c28a6..HEAD` over `EVALUATOR_FILES` returns only `compress/spec.py` (+3/−1, the rendered text). So the round-0 seeds' older evaluator hash does not change any verdict or metric. No `src/` change since 84a20af (round 1).
4. Inspected the best circuit's certificate `compress/lean/certs/step-o1-ca5c0f1a907a.json`:
   - 31 qubits, 432 gates, base $(d_\alpha,d_\beta)=(4,8)$, phase $c=i$, target `step` order 1, 433 states.
   - Angle exponents $\{(-3,0),(0,\pm2),(0,-4),(0,\pm6)\}$.
5. Re-derived the best circuit's physics at the level of the argument (section B).

## Checklist

| Item | Status | Where / evidence |
|---|---|---|
| Equations match METHODS (couplings, factors $\tfrac12$, Casimir $j(j+1)$, signs) | OK | Electric layer $p(-\tfrac34\alpha)$ on the four $q_j$ bits = $e^{-i\alpha\,j(j+1)}$ with $j(j+1)=\tfrac34$ (best program L158–159). Exact target $U_B=\sum_\lambda P_\lambda z_\beta^{-2\lambda}$, $z_\beta=e^{i\beta/2}$ ⇒ $e^{-i\beta H_B}$; $U_E$: $z_\alpha^{-3n}$, $z_\alpha=e^{i\alpha/4}$; step order 1 multiplies column $j$ by $z_\alpha^{-3n_j}$ = $U_BU_E$ (`lean/exact.py:850–883`). |
| Time-evolution sign and ordering | OK | Spec "electric layer first in the circuit", $U=U_B(\beta)U_E(\alpha)$ (`spec.py:_operator_text`). Walk: $r_z(2\beta c_S)=e^{-i\beta c_SZ}$ ⇒ $e^{-i\beta\kappa X_F}$ in the $H$ frame. Relabel gates placed before the electric phases commute with them (CX controlled by $q_j$, $Z$ on $m$ legs). |
| Basis / index conventions (endianness, corner and link labels) | OK | Corners $c_0:(b,l|o_0,o_1)$, $c_1:(b,r|o_2,o_3)$, $c_2:(r,t|o_4,o_5)$, $c_3:(t,l|o_6,o_7)$ (prompts/006 L116). Outer $j$ bits $13+2k$ ⇒ $t_0=q_{13}\oplus q_{15}$, $t_2=q_{21}\oplus q_{23}$. Cert frame data $i\to i$, outer $\to12+j$, ancilla $\to28+k$ (`certify.py:_perm_of`). |
| Truncation ($j_{\max}=\tfrac12$, prune cap) | OK | Unchanged from M1. `PRUNE_FRACTION`·`tol_err` cap enforced in `evaluator.evaluate`; dropped-total $\le3\times10^{-14}$ in tester 041. |
| Normalisation; expectation values real | OK | Lean checker verifies the exact Gram matrix = identity and 433 states (`Check.lean:96–150`). Float verdicts unchanged. |
| Precision (float64 reference, lower-precision paths) | OK | Sparse engine complex128. aer_mps never certifies at $10^{-10}$ ⇒ `unverified` ⇒ never valid (`compress/evaluate.py:188–195`). |
| Randomness / seeds | OK | Trial subset `default_rng(spec.trial_seed=0)`, transpiler 20261104, CT pass manager 12345; recorded per entry (`seeds`) and per round (`provenance`). |
| Tests exercise the production path | OK | The loop, the acceptance tests and `run_candidate` all go through `evaluate_program` → `_build_in_subprocess` → `evaluate_circuit` → `evaluator.evaluate`. Tester 041 used an independent engine and Aer on top. |
| Hard-coded expected numbers in `src/` | OK (note N10) | `lean/structure.py:417–424` `_COUNT_FACTS` types in the Lean theorem values. They are transcriptions of kernel-checked statements, tied to `Counts.lean` by the locked `test_lean_counts_kernel_checked`. `Check.lean:92 physicalDim=433` is part of the checker's specification. |
| Silent excepts in numerical code | OK | New handlers either return a typed failure reason or are I/O-only (cache writes). `evaluate.py:249` `except ValueError: met=None` cannot produce an archive entry: `entry_problem` refuses "metrics incomplete". |
| Provenance (commit, params, seed) | OK (notes N2, N8, N13) | Every entry: program, evaluator and spec sha, commit + dirty flag, versions, seeds, machine. The certificate-to-program link is weak (N2). |
| Compression validity (433 states × 3 angle pairs, skeleton, trial vs full, cache, unverified, prune cap, leak) | OK (note N5) | See section A. |
| Proposer code never runs in the parent | OK | `load_program` is called only from `_worker` (graphify: single caller `evaluate.py:488`). The parent loads QPY and re-checks gate classes itself (`_gate_violations`, `is_standard_gate`). `round._circuit_of` rebuilds in the worker too. |
| Cost key as METHODS §7/§9 | OK (note N6) | `synth.key = (cx, t_eps, depth_ct, qubits)`. In full mode `t_eps = t_fixed + Σ pygridsynth T(θ, 1e-6)` over the non-Clifford `rz` of the level-0 lowering; `depth_ct` = depth of the pygridsynth-synthesised circuit; `qubits = qc.num_qubits`. Cell $\lfloor8\log_2(\cdot+1)\rfloor$. |
| Like-for-like comparison with Paulo / lean22 | lean22: OK; Paulo: ISSUE N1 | Section C. |
| Lean generic theorems (26) + counts (8) | OK (notes N3, N4) | Section D. |
| Per-circuit certificate certifies "circuit = $U_{\rm step}$ on 433 states for all $\alpha,\beta$" | OK with scope note (N3) | Section D. |
| Trust boundaries stated in METHODS §11 | ISSUE (non-blocking) N3 | Section D. |
| Lemma checker "sandbox" claim | ISSUE (non-blocking) N9 | `lean/lemmas.py:20–25` |

## A. Can an invalid program be archived as valid?

I traced every route into `Archive.insert` and found none that bypasses exactness on all 433 states at all three angle pairs.

- **Skeleton rule.** `evaluate_circuit` (`compress/evaluate.py:226–243`):
  - It compares (name, qubits) of every instruction of the nominal circuit with the circuits built at both alternate pairs.
  - Each alternate circuit is then evaluated at its own angles with the full verdict (`ok and certified`, gate whitelist).
  - `_build_in_subprocess` refuses a wrong number of circuits.
- **Trial vs full.**
  - Trial verdicts (64 seeded inputs, `states=` subset) carry `mode="trial"`. `entry_problem` refuses any `mode != "full"` (`archive.py:91–92`).
  - `run_round` always calls `evaluate_program(..., "full")`.
  - All archived verdicts have `n_inputs = 433` (checked for all 22 entries, nominal and both alternates).
- **Cache.**
  - Only full-mode results are stored or read.
  - The key is (evaluator code sha, program sha, spec sha).
  - A checksum guards the blob; it is not a MAC, which is documented.
  - `_consistent` re-checks `ok ∧ certified ∧ skeleton ∧ metrics`.
  - `eval_budget` and `build_timeout` results are never cached.
  - Proposers cannot write `compress/cache/` (guard allowlist).
  - The key does not include package versions (N7).
- **Unverified.** `ok` but not `certified` ⇒ reason `unverified` ⇒ invalid (`evaluate.py:191–192`). With strict archives (`round.py` uses `strict=True, n_alt=len(spec.alt_angles)`), a verdict that lacks `certified: True` is refused (`archive.py:96–103`).
- **Prune cap and leak as amplitude.** Unchanged evaluator logic from M1: `op_norm_error = block + dropped_total + ‖X‖₂ ≤ 10^{-10}`, Gauss ≤ $10^{-10}$, `gauss=True` forced in `_one_verdict`.
- **Key integrity.** `entry_problem` recomputes key and cell from `metrics_raw` and refuses a mismatch or a non-finite value.

Residual gap (N5): the validity rule does not require angle-linearity, and the T key is measured only at the nominal pair. Consider a program whose angles are nonlinear in $(\alpha,\beta)$ and happen to land on multiples of $\pi/4$ at $(0.37,0.61)$: it would be scored with fewer rotations than it has at generic angles. This is not exploited by any archived entry: tester 041 §2d found all 9 recent entries exactly linear, $\theta_i=a_i\alpha+b_i\beta$ with denominators ≤ 8, and the Lean exporter independently recovers the same exponents for the best.

## B. Physics of the final best `r05-F2-005` (CX 111, T 912, depth_CT 1663, 31 qubits)

I checked the program's argument against route A/B physics from M0 (METHODS §5, structure facts). Everything is consistent.

1. **Bright pairs and $n_1$.** $H_B^{\rm phys}$ is block-diagonal in the outer spins. Every block is $DK_{\rm sub}D$ with 8 bright $2\times2$ pairs of couplings $2,1(\times6),\tfrac12$ and 31 dark labels.
   - Let $t_c\in\{0,1\}$ be "corner $c$ has $J_c=\tfrac12$". Gauss law at a corner with spin-$\{0,\tfrac12\}$ legs gives $t_c=j_A\oplus j_B$ (inner legs) $=j_{o_A}\oplus j_{o_B}$ (outer legs), because $T(0,\tfrac12)=\{\tfrac12\}$ and $T(0,0),T(\tfrac12,\tfrac12)\ni$ integer spins.
   - Hence $\sum_ct_c$ is even, and $n_1=\#\{c:t_c=1\}\in\{0,2,4\}$ with $\binom40,\binom42,\binom44=1,6,1$ bright pairs. This matches the coupling multiplicities $1,6,1$.
   - Each $J_c=\tfrac12$ corner contributes a factor $2^{-1/2}$, so $|\kappa|=2\cdot2^{-n_1/2}=2,1,\tfrac12$.
   - Spectrum multiplicities: $\pm2$: $2^4=16$ outer completions (each corner with $J=0$: both outer spins 0 or a singlet); $\pm1$: $6\cdot16=96$; $\pm\tfrac12$: $16$ (each $J=\tfrac12$ corner: outer pair $(0,\tfrac12)$ or $(\tfrac12,0)$, $m$ fixed by the corner singlet). This matches the certified $16,96,16$.
2. **$\kappa$ values $2,\;-(-1)^{t_2},\;-\tfrac12$.**
   - The program computes $z=[t_1=t_2=t_3]$. Since $t_0=t_1\oplus t_2\oplus t_3$: $z=1,t_2=0\Rightarrow n_1=0$; $z=1,t_2=1\Rightarrow n_1=4$; $z=0\Rightarrow n_1=2$.
   - The moduli match K. The signs are frame/gauge-dependent (M0 audit 001 N5: signs are gauge at $j_{\max}=\tfrac12$), so they are fixed by the program's frame, not by K.
   - The "never occurs" point (dark with $n_1=4$) is right. All-$J=\tfrac12$ forces alternating inner spins (2 configurations), which $W$ maps onto each other: exactly one bright pair and no dark label.
3. **Parity relabel.** With $c_0=(l,b)$, $c_1=(b,r)$, $c_2=(r,t)$, $c_3=(t,l)$:
   - $q_2\leftarrow j_b\oplus j_t=t_1\oplus t_2$, then $\oplus\tau_0=t_3$ ✓.
   - $q_{11}\leftarrow j_r\oplus j_l=t_2\oplus t_3$, then $\oplus\tau_0=t_1$ ✓.
   - $q_8\leftarrow j_t\oplus j_r=t_2$ ✓.
   - $W$ flips all four inner $j$ bits, so all parities are invariant and only $F=q_5$ ($j_r$) flips. The bright $2\times2$ pair becomes a single $X_F$, as claimed.
4. **Walsh walk.** The toggle sequence `t,pb,pa,pb,z,pb,pa,pb+t,z` visits every element of `SUPP` exactly once ($0000\to0001\to0101\to1101\to1001\to1011\to1111\to0111\to0010\to0000$, closed). It applies $e^{-i\beta\sum_Sc_S(-1)^{S\cdot x}Z_F}$ in the $H$ frame, i.e. $e^{-i\beta\kappa(x)X_F}$. That gives 9 magnetic + 4 electric = 13 rotations, matching $N_{\rm rot}=13$.
5. **In-walk RCCX + CZ.** RCCX (METHODS §11.1 g) flips the target with phase $i(-1)^{f}$ when both controls are set, and gives a $-1$ on $|a{=}1,b{=}0,h{=}1\rangle$.
   - Between the two `pa` toggles the net extra toggle is $z$, so $F$'s value at the second RCCX is $f\oplus1\oplus z$ if $b_0b_1=1$, and $f\oplus z$ if $b_0=1,b_1=0$.
   - Products of the phases:
     $$b_0b_1=1:\;i(-1)^f\cdot i(-1)^{f\oplus1\oplus z}=(-1)^z,\qquad b_0=1,b_1=0:\;(-1)^f(-1)^{f\oplus z}=(-1)^z,\qquad b_0=0:\;1.$$
   - The residual is $(-1)^{b_0z}$, independent of $f$, and is removed by `cz(tau0, z)` with $\tau_0=b_0$ ✓.
6. **$t_2$ from the outer register.** $t_2=q_{21}\oplus q_{23}$ (outer $j$ bits of $o_4,o_5$) holds on every physical state by the Gauss-law identity in item 1. This is a read-only use of outer bits as CX controls, allowed by Digonto's 2026-11-04 decision. The evaluator confirms there is no `writes_outer`; tester 041 confirms 0 non-control outer operations.
7. **Independent confirmations.**
   - Evaluator: op-norm error $1.0\times10^{-13}$ at all 3 pairs.
   - Tester engines A and Aer: ≤ $1.5\times10^{-14}$.
   - Lean exact certificate ACCEPT (re-run by tester 041).
   - Synthesised Clifford+T: $3.73\times10^{-6}\le1.30\times10^{-5}$.

## C. Comparisons

- **lean22 / lean22_v2 seeds** (162/660, 210/704): like-for-like. They are evaluated through the same pipeline, as the step operator with our `build_UE` prepended (audit 003 N4 respected).
- **Paulo row: not like-for-like in T (N1).** `results/compress/twelve/summary.json` puts Paulo's 1162 in the columns `T_fixed`, `T(1e-6)`, `T_est(1e-6)` and `T(1e-10)`. That number differs from our rows in three ways:
  1. It is $U_B$ alone; our rows are the step, which includes 4 electric rotations ≈ 256 T at $10^{-6}$ (M1 table).
  2. It comes from Qiskit's Clifford+T pass manager at Paulo's synthesis settings, not from pygridsynth at $\varepsilon=10^{-6}$ per rotation.
  3. It is at $\beta=1$, not $\beta=0.61$.

  The CX column (294) is comparable, because $U_E$ costs 0 CX. The like-for-like T comparison already exists in audit 003: our general $U_B$ 662 T vs Paulo 1162 T, both through the same Qiskit CT pass at $\beta=1$, $\varepsilon=10^{-6}$.

## D. Lean

- **Generic theorems.** The statements read are correct and are the ones the evaluator relies on:
  - `pruning_triangle`, `opNorm_le_of_blockdiag` (the max-over-groups rule), `opNorm_add_three_le_of_orth`, `rss_le_sum`.
  - `synth_bound`: $\|\prod W_i-(\prod c_i)\prod R_i\|\le\sum\|\Delta_i\|$, which justifies $N_{\rm rot}\varepsilon$.
  - `span_leak_le_four_gauss`, with the spectral-gap hypothesis explicit.

  Precision point (N3): `verdict_sound` proves $\|U\Phi-c\Phi V\|\le b+d+l+s$, including the span-leak norm $s$. The evaluator's `op_norm_error` $=b+d+l$ omits $s$ by design: $s$ is bounded per state by $4\cdot$`gauss_residual` (audit 002 R1). METHODS §11.1(c) calls `verdict_sound` "the evaluator's inequality chain" without that caveat.
- **Counts (N4).**
  - `max_states_per_outer : maxPerOuterM = 17` is true, but `innerSumM` over-counts on 1952 of the 3153 supported patterns (tester 028 N1). The docstring (`Counts.lean:86`, "Maximum number of states sharing one outer m-pattern") and the `structure.json` fact (`proved_by: decide`) therefore overstate what the kernel proved. The real value 17 is native-certified by `outer_support_table`.
  - `dont_care_codes : 4^6 − 5^4 = 3471` is integer arithmetic, not a fact derived from the encoding.
- **Per-circuit certificate.** `Check.lean` accepts iff, for each of exactly 433 states, $U\psi_k=c\sum_{k'}V_{k'k}\psi_{k'}$ as exact sparse Laurent vectors over the full register. The expected vector has no ancilla support and the states' codes are $<2^{28}$. This proves block exactness, zero leak and clean ancillas, for all real angles, of the gate list. Before that, it checks:
  - the exact Gram matrix = identity;
  - every state is covered by exactly one target block;
  - the SHA-256 of the canonical states text and target text equal the pins in `Pins.lean`.

  The certificate is sound against misclassified angles: a wrong exponent cannot produce ACCEPT, only REJECT.

  Scope (N3):
  1. "For every $(\alpha,\beta)$" holds for the angle-linear gate family that the exporter reads off the nominal circuit (`certify.py:_classify_angle`, `_gate_records`). That family coincides with the program's output at the three evaluated pairs; the program code itself is not proved for other angles.
  2. States and target are Python-generated exact data pinned by hash. Their equality with $e^{-i\beta H_B}e^{-i\alpha H_E}$ on Gauss-law states rests on:
     - the exporter's float cross-check ($\le10^{-12}$ per entry at one angle pair, `exact.py:885–`);
     - the structure certificate, which verifies $H_B$ structure and Gauss law in the CG electric-key convention, not the projectors $P_\lambda$ nor the Paulo-code states used by the circuit certificate.
- **Trust statement in METHODS §11.**
  - Stated: native_decide / compiled-checker trust.
  - Not stated:
    - that the pins are Python-generated;
    - that the target $P_\lambda$ is not derived inside Lean;
    - the extracted-family scope above.
- **Lemma checker (N9).**
  - `_FORBIDDEN_RE` is a regex deny-list, and `lake env lean` then runs with the user's privileges.
  - The module docstring says constructs are "refused before Lean runs". It is not a sandbox, and METHODS §11.4 does not say so (contrast the explicit "NOT a security sandbox" in `compress/evaluate.py:23`).
  - No proposer shipped a `.lean` file in M2 (`find compress/programs -name '*.lean'`: none), and results are informative only.

## Issues (all NON-BLOCKING)

**N1 — Paulo's T in the wrong columns of the compression table.**
- Where: `src/su2plaq/compress/report.py:52–62` (`_row_external`), visible in `results/compress/twelve/summary.json`, row `paulo34`.
- Why wrong: $T_{\rm total}(\varepsilon)=T_{\rm fixed}+\sum_rT_r(\varepsilon)$ with pygridsynth $T_r$ (METHODS §7) is not what 1162 is: it is Qiskit-CT on $U_B(\beta{=}1)$. Read off the table, "912 vs 1162" looks like a 21 % T saving. That is not established. The like-for-like numbers are 662 vs 1162 for the general circuit (audit 003).
- Fix: print `-` in `T(1e-6)` / `T_est` / `T(1e-10)` for fixed-angle externals and add the column "T (Qiskit CT, own settings)". Optionally add one like-for-like row: the best circuit's $U_B$ part at $\beta=1$ through `ct_compile` with Paulo's settings. Must be done before Report 2.

**N2 — Certificate ↔ program link.**
- Where: `src/su2plaq/compress/round.py:322–336` (`_circuit_of`) and `src/su2plaq/lean/certify.py:385–388`.
- Why: the Lean certificate and the Clifford+T re-verification are made from a rebuild of the file at `program_path`, with no check that its sha256 equals the archived `program_sha256`. Proposers can write `compress/programs/`, so an edit between evaluation and certification would certify a different circuit under the entry's name. The certificate's `program_sha256` field is the gate-list hash (known issue 2.L8). Tester 041 closed the gap for `r05-F2-005` by a gate-by-gate comparison.
- Fix:
  - In `_circuit_of`, read the bytes once, assert `sha256 == entry.program_sha256`, and build from those bytes.
  - Rename the certificate field to `gates_sha256`.
  - Add `program_file_sha256` to the certificate provenance and to `Entry.lean`.

**N3 — METHODS §11 trust boundaries and scope.**
- Where: `docs/METHODS.md` §11.1(c), §11.2.
- Fix: add three sentences.
  1. "The checker trusts the 433 exact states and the exact target blocks produced by `su2plaq.lean.exact`; they are pinned by SHA-256 in the generated `Pins.lean` and cross-checked against the float code (≤ 1e-12 per entry, one angle pair); the projectors $P_\lambda$ are not derived inside Lean."
  2. "'For all $(\alpha,\beta)$' refers to the angle-linear gate family read off the circuit at the nominal angles (angles rational multiples of $\alpha$ or $\beta$, denominator ≤ 64); its agreement with the program at other angles is the numerical skeleton + alternate-pair check."
  3. "`verdict_sound` includes the span-leak term $s$, which `op_norm_error` omits (bounded per state by 4·gauss_residual)."

**N4 — Count facts overstated.**
- Where: `lean/Su2Plaq/Structure/Counts.lean:86,96–97` and `src/su2plaq/lean/structure.py:423–424`.
- Fix:
  - Re-word `maxPerOuterM` as "upper-bound model whose maximum equals the true maximum 17", and cite the native `outer_support_table` for the exact meaning.
  - Label `dont_care_codes` as arithmetic ($2^{12}-5^4$).
  - No number changes.

**N5 — Validity does not require angle-linearity; T measured only at the nominal pair.**
- Where: `src/su2plaq/compress/evaluate.py:226–251`, `metrics.py`.
- Why: METHODS §9 does not require it, but a program could gain T by landing on Clifford angles only at $(0.37,0.61)$. Not exploited (041 §2d).
- Fix (planner decision): record per-pair $N_{\rm rot}$ in the result and refuse if it differs, or add the exporter's linearity check as a recorded field.

**N6 — `depth_CT` convention undocumented and decisive.**
- Where: METHODS §7.
- Why: the global best among five CX 111 / T 912 entries is decided by depth_CT 1663 vs 1664, i.e. 1 level, under the convention $X\to HSSH$ in gridsynth words (`metrics/cliffordt.py:synthesize`). With $X$ counted as one gate it would be 1642 (tester 041). The ranking of the plateau entries may change under another convention.
- Fix: state the convention in METHODS §7 and in Report 2, and present the five plateau entries as tied in (CX, T).

**N7 — Result-cache key omits package versions.**
- Where: `src/su2plaq/compress/evaluate.py:338–346`, `provenance.py`.
- Why: qiskit lowering and pygridsynth T counts enter the cached metrics; an upgrade would serve stale counts.
- Fix: include `qiskit`, `qiskit-aer` and `pygridsynth` versions in the cache path or meta.

**N8 — Cosmetic provenance items.** Not blocking.
- The round-0 seeds carry evaluator sha `810e86f2…`. I verified that the only evaluator-file change since round 0 is the rendered text in `compress/spec.py` (+3/−1), so the seed numbers are unaffected. Refresh them or state this in Report 2.
- Round-1 entries have `parent None` because the four round-1 programs declare `PARENT = None` (checked). The record is truthful; if the proposers started from a seed, the brief should require declaring it.

**N9 — Lemma checker is a deny-list, not a sandbox.**
- Where: `src/su2plaq/lean/lemmas.py:1–8,20–25`.
- Fix: write "not a sandbox" in the docstring and in METHODS §11.4, as for the program guard. Optionally run `lake env lean` under the same OS-level restrictions you would use for untrusted code.

**N10 — Count values transcribed in source.**
- Where: `src/su2plaq/lean/structure.py:417–424` (`_COUNT_FACTS`).
- Why: allowed in spirit, since the values are tied to the Lean statements by the locked test.
- Fix: parse the right-hand side of each `theorem … = N` from `Counts.lean` instead of typing it.

**N11 — Loop stopping rule.**
- Where: METHODS §9: stop at R = 6 rounds for the first encoding, 3 rounds without a better key, or 20 proposer sessions.
- Why: none of these fired at round 5. Round 5 improved the key on depth_CT and qubits; there were 17 proposer sessions plus ideation. The stop was a coordinator judgement ("plateau").
- Fix: record it as a decision (Digonto) in STATUS and Report 2.

**N12 — Wall-time rule vs implementation.**
- Where: `compress/evaluate.py:221,236` vs METHODS §9 "wall ≤ 300 s".
- Why: the implementation allows nominal ≤ 300 s, each alternate ≤ 120 s, and build ≤ 120 s. Heavy F1-style circuits need about 240 s at the nominal pair, so a load-dependent timeout at an alternate can reject a correct program (a false negative only).
- Fix: document the actual budgets in METHODS §9.

**N13 — Absolute certificate path in archive entries.**
- Where: `Entry.lean.cert_path = /home/digimonk/...`.
- Why: it breaks in the desktop bundle.
- Fix: store it relative to the repository root (as `round._rel` does for programs).

## Assumptions

- I did not re-run the evaluator, the Lean checker or `lake build`; I relied on tester 041 for execution evidence.
- My physics check of the best circuit is at the level of the argument; exactness itself is established by three engines and the exact Lean checker.
