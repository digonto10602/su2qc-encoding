# Audit 305: milestone-2c gate (prompts/008 consolidation), with prompts/010 (fuzzy headline rule) and the M11 cross-check code

- Date: 2026-11-19. Auditor (Opus 5.5, high). Commit audited: `48e5f7f` (`git rev-parse --short HEAD`), branch `merge-desktop-tracks`, clean tree.
- Commit range: `pre-consolidation-008..48e5f7f` (62 commits; 35 files under `src/`, +2702/−889).
- Plans in force: `prompts/008-merged-repo-consolidation.md` (step C5 part 2), `prompts/009-final-cross-encoding-report-spectra-crosscheck.md` (steps 11.0–11.7), `prompts/010-fuzzy-headline-rule-clifford-offsets.md` (H.1–H.3); conventions `docs/METHODS.md` §6, §12, §13. Acceptance tag `acceptance-v22`.
- Related reports: tests 413–430 (gate run: `reports/tests/430-milestone-2c-gate-full.md`, PASS, 26 reds all PENDING stubs), `reports/fixes/001-replay-label-mismatch-twelve-fuzzy.md`, `reports/audits/304-rishon-milestone-5d.md`, research 005, 006, 007.
- Scope: physics and numerics errors that tests can miss. No code was edited. Check scripts: `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/c0852fe6-e8f0-4e38-bdd5-b42d861ef247/scratchpad/hashcov.py` plus inline `python -c` checks (all with `PYTHONPATH=src`, conda env `coding`, `taskset -c 0-8`, `OMP_NUM_THREADS=1`).

## Verdict: PASS WITH NOTES

No blocking issue. Nine notes (N1–N9). N1 (hash coverage) is the most important. It is not blocking because no current number is wrong: the files involved have not changed since long before the archives were built. It should be fixed at the next window that may change hashes anyway.

## 1. What was asked

Audit the 008 consolidation diff, plus the prompts/010 and prompts/009 code that landed in the same commit range. The focus list:
1. registry, provenance and dispatch;
2. the evaluator additions;
3. `compress/robust.py`;
4. `compress/replay.py`;
5. `fuzzy/headline_step.py` and `crosscheck/*`;
6. the fixed `robust.json.tmp` name in two track files.

## 2. Actions taken

- Read STATUS, prompts/008 §2–§7, prompts/010 in full, prompts/009 §1–§6, METHODS §6, §12, §13, and test report 430. I used graphify (`god-nodes`, `query`, `explain get_encoding`) before reading the raw files.
- Read the diffs and the new modules: `encodings/registry.py`, `compress/{provenance,evaluate,archive,round,baselines,report,robust,replay}.py`, `evaluate/evaluator.py`, `rishon/compress/evaluate.py`, `fuzzy/{units,headline_step}.py`, `crosscheck/{ks,embed,limits,report}.py`.
- Independent checks, all run by me:
  - **(a) Hash coverage.** For each registered encoding, which `su2plaq` modules get imported when its factory, its verdict hook and its targets are built? I compared that list with `provenance.evaluator_files(e)` (`hashcov.py`).
  - **(b) Angle sets.** Compared the shared, spinnet and rishon `ANGLE_SET` and their sha256 with the caches committed at `pre-consolidation-008`.
  - **(c) Cache freshness.** Checked every `robust.json` against the current hashes and recomputed the headlines with `compute=False`.
  - **(d) Program files.** Compared every replay record's old and new program sha256, and checked every archived program file against its recorded sha256.
  - **(e) Clifford offset table.** Tested the `CLIFFORD_OFFSET_UNIT` table with Qiskit `Clifford.from_operator`.
  - **(f) Bad angles.** Ran the evaluator on circuits with a NaN or infinite rotation angle.
  - **(g) QR fallback.** Checked whether the rank-deficient (SVD) branch of `_local_basis` is ever taken.
  - **(h) Freeze claim.** Collected every hashed file list in the project (union over all lists).
- Checked by hand the rishon → KS limit coefficient and the closed-block operator extraction (details in §4).

## 3. Checklist

| Item | Status | Where / evidence |
|---|---|---|
| Span-leak equation vs METHODS §6 / 008 §5, term by term ($P_o=B_oR_o$, $Y_o$, $C_o$, $D_o$, $S^\dagger S$) | OK | `evaluate/evaluator.py:345-357, 430-475, 523-546`. $C_o$ and $D_o$ are formed directly as residuals; $W-A^\dagger A$ is never used. The unselected-pattern rows in trial mode (`:464-467`) are handled. Tester 414 matched a dense reference to $\le6.7\cdot10^{-16}$, also on the aer_mps path |
| Identities `op_norm_error = block + dropped + leak`, `total_error = op_norm_error + span_leak` | OK | `evaluator.py:522` and `:547`; the Verdict stores `op_norm_error=err_total` (`:595`). Every `ok` verdict has `total_error ≤ tol_err`, because the span_leak reason is last (`:575-576`) and `total_error ≥ err_total` |
| The bound is a true upper bound | OK | $\|U\Psi-e^{i\varphi}\Psi V\|_2\le\|D\|_2+\|S\|_2+\|X\|_2$ holds because the three ranges are orthogonal. The outer pattern is preserved because `writes_outer` is checked. Pruning is added once (prompts/005). The SVD fallback for rank-deficient $P_o$ is approximate (dropped directions $\le10^{-12}s_0$), but it is never taken: smallest $\lvert R_{ii}\rvert$ is 0.0278 (twelve) and 1.0 (spinnet, lsh) |
| Shortcut `span_leak = 0` when the physical span is the whole code space | OK | `evaluator.py:430`. Correct when the physical states are orthonormal and number $n_{\rm in}\,n_{\rm patterns}$ (fuzzy units, rishon inner view) |
| Gauss "not_checked" reported as NaN | OK | `evaluator.py:549, 603`. The fuzzy hook no longer overwrites the value (no attribute assignment into shared modules is left in `src/`; grep) |
| Early verdicts: `total_error = inf`, never NaN | OK | Defaults in `Verdict`. Rishon `to_verdict` (`rishon/compress/evaluate.py:52-54`) now gives `inf` (the B5 carry-over item is closed) |
| NaN safety | OK | Adversarial check: `rz(nan)` and `rz(inf)` appended to the general twelve and spinnet steps → `LinAlgError` (loud), not `ok` |
| `prune_fraction` | OK | Range check $(0,1]$ and the cap `pf * tol_err` (`evaluator.py:367-370, 567`). No registry entry sets it; rishon keeps its own cap inside its verdict function |
| Registry dispatch (verdict, Gauss flag, target, tolerances per encoding) | OK | `compress/evaluate.py:180-203` dispatches `info.verdict` or the shared evaluator with `gauss=info.gauss_in_loop`. The result cache is keyed by `code_hash_for(spec.encoding)` (`:361`). `_phys_data` is cached per encoding object (`evaluator.py:250-253`). `get_encoding` checks `_ENCODINGS` first, but nothing in `src/` writes to it any more |
| Code hashes cover the files that decide verdicts | **ISSUE (N1)** | `encodings/registry.py:58` (spinnet) and `:66` (fuzzy) |
| Angle set (seed 20261107, 20 pairs) identical across tracks | OK | `compress/robust.py:33-56`; spinnet and rishon now import this one definition. Its sha256 `769caec1…cbb2` equals the sha in the `pre-consolidation-008` spinnet and rishon caches, and m4/m6 compare it with an independent recomputation |
| Robust key and ρ; offset classes | OK (N4, N7) | `robust.py:118-231`. Tables in §4 |
| `_atomic_write_text`, file mode 0600 | OK (N6) | `robust.py:244-265` |
| Replay: order, duplicates, nothing lost | OK (N2) | `compress/replay.py:108-176, 237-257` |
| Fuzzy headline step (prompts/010 H.3) | OK (N3, N8) | `fuzzy/headline_step.py`. Inner CX $131=83+4\cdot12$; err $1.2\cdot10^{-14}$, Gauss residual $5.9\cdot10^{-15}$ (`results/fuzzy/compressed_step_headline.json` @ `cd468e2`, clean) |
| KS operators, gauge signs, transported targets, cross-verdicts | OK (N3, N9) | `crosscheck/ks.py`. The comparisons use the full signed matrices, and a negative control ($\beta+10^{-6}$) is included (§4) |
| Link isometries | OK | `crosscheck/embed.py`. All residuals are complex max-entry differences (signs included), not moduli |
| Rishon → KS limit, coefficient $\tfrac{13}{4g^4}$ | OK | `crosscheck/limits.py:15-25, 162-171`, `report.py:161-170`. Derivation re-done (§4) |
| Fuzzy flavour sectors, isolated plaquette | OK | `limits.py:250-330`. `_herm` is harmless because $\square$ is Hermitian (METHODS-fuzzy F3) |
| Time-evolution sign / Trotter order | N/A (unchanged) | Targets come from the encodings' own `target`; nothing in the diff touches them |
| Qubit order / endianness | OK | `embed._kron4` and `limits._flavour_blocks` put link b in the least significant position, matching `exact.operators._build_W`. The m11 E1/F1 numbers ($\le5\cdot10^{-16}$) would fail otherwise |
| Truncation | N/A | $j_{\max}=\tfrac12$ throughout; nothing changed |
| Precision | OK | No float32/complex64 in the diff (grep); complex128 throughout |
| Randomness | OK | Seeds 20261107 (angle set), 20261110 (generality points) and 20261104 (step samples) are recorded in the outputs |
| Tests exercise the production path | OK | m2c and m11 call the production functions. The cross-verdicts use the production `evaluate`. The headline ids are not typed into tests (prompts/010 §5) |
| Provenance | OK (N2, N3, N4) | Results carry commit, dirty flag, versions and seeds. The gaps are listed in the notes |
| Fixed `robust.json.tmp` name (focus item 6) | NOTE (N5) | Neither file is hashed, so it can be fixed without touching any hash |

## 4. Physics checks in detail

**Clifford offsets and the T count (focus item 3).** The unit table `robust.py:40-41` is right, as is the rule that a constant equal to a multiple of the unit is Clifford.
- Checked with Qiskit `Clifford.from_operator`: $k\,u$ is Clifford for $k=1,2,3$ for all eight gates; $u/2$ is not Clifford for any of them.
- The offset factorises: $U(\theta+u)=U(\theta)\,U(u)$ was confirmed with `Operator.equiv` for rz, rx, crz and cp. Concretely,
  $$R_z(\theta+k\tfrac\pi2)=e^{-ik\pi/4}R_z(\theta)S^k,\qquad \mathrm{cp}(\theta+\pi)=\mathrm{cp}(\theta)\,\mathrm{CZ},\qquad \mathrm{crz}(\theta+\pi)=\mathrm{crz}(\theta)\,(S^\dagger_c\,\mathrm{CZ}).$$
- For singly controlled rotations, $\pi/2$ is correctly **not** treated as Clifford, because $\mathrm{cp}(\pi/2)$ is controlled-$S$.

The classification cannot affect the T accounting:
- $T$ is measured at each of the 20 pairs from the actual lowered angles with pygridsynth.
- The class enters neither $\rho$ nor any key (`robust.py:225-230`).
- Measured on the caches: fuzzy_ub has 30 entries of class `linear` and 11 of class `clifford_offset`; no entry is `non_clifford_offset` or `non_affine`. Twelve and fuzzy_link are all `linear`, and ρ agrees with the class in every cached record.

**Rishon → KS limit coefficient.**
- Electric/det part, per link: $-2L$ in $P_+$, $\tfrac38g^2-2L$ in the quartet, $+2L$ in $P_-$. The shift is $+24L$ for 12 links (`limits.py:168`) and $+8L$ for the 4 inner links of the closed block (`report.py:166`). After the shift the quartet costs $\tfrac38 g^2=\tfrac{g^2}{2}\,j(j+1)$ at $j=\tfrac12$, as in KS.
- Second-order shift: the loop couples with $2c_B$ to six vacuum combinations at $8L$ and one at $16L$, so
  $$\Delta E_{\rm loop}\simeq-(2c_B)^2\Big(\frac{6}{8L}+\frac{1}{16L}\Big)=-\frac{13\,c_B^2}{4L}=-\frac{13}{4g^4L}.$$
- The prediction in `report.py:163` is $-\tfrac{13}{4}g_2^{-2}\,|v_{\rm loop}|^2$ with `g2` $=g^2$, i.e. exactly this formula weighted by $w_k$.
- The vacuum $(A+B)^{\otimes4}$ receives no shift because $H_B$ maps it only onto the loop state. This is why the prediction is proportional to $w_k$.
- The extraction of the three closed-block operators from `closed_block_full` at $(g^2,\lambda)=(1,0),(2,0),(1,1)$ inverts correctly: $H_B=(4f_1-2f_2)/3$, $H_E=(4f_2-2f_1)/3$, $H_D=f(1,1)-f_1$.
- The numerical comparison (m11 E2: 1 % at $L=256$; a coefficient of $\tfrac{12}{4}$ or $\tfrac{14}{4}$ would be off by 7.7 %) uses an analytic prediction independent of the production block, so it is not circular.
- `rishon_levels` uses $P^\dagger TP$. Dropping the images that land outside the physical keys is exact for that product, and the size of what is dropped is recorded (`rishon_dropped_images`).

**Comparisons that could pass for wrong physics (focus item 5).**
- K1 (spectra) alone would not see a sign error that amounts to a gauge choice.
- K2 and K3/K4 compare full signed matrices and circuit verdicts, so they would.
- The gauges come from `gauge_align` against route A. That makes K2 partly true by construction. The independent evidence is the cross-verdict of delivered circuits, plus the $\beta+10^{-6}$ mutant rejected with block error $2.0\cdot10^{-6}$.
- E1: the isometry and compression identities compare complex entries with signs. The plaquette check compares against route-A `plaquette_W`.
- F1: $H_{00}=0$ plus both KS eigenvalues fixes the $2\times2$ block up to the sign of the second Krylov vector. That sign is a basis choice, not physics.
- Spectral claims cannot detect a reflection of the link order. That is harmless here, because a reflection with orientation reversal is a symmetry of the plaquette.

## 5. Issues (all NON-BLOCKING)

**N1. The per-encoding hash misses the files that define the spinnet and fuzzy targets.**
- Where: `encodings/registry.py:58` (spinnet) and `:66` (`_FUZZY_FILES`).
- What is missing: `hashcov.py` imports each factory and verdict hook and builds every target; the `su2plaq` modules loaded that are not in `evaluator_files(e)` (package `__init__`s and `provenance.py` excluded) include:
  - spinnet: `exact/spinnet.py` (`h_magnetic_phys_6j`, `h_electric_6j`, `K_inner`, i.e. the route-B target) and `exact/compare.py` (`gauge_align`, which fixes the sign gauge of the decoded states);
  - fuzzy_ub and fuzzy_link: `fuzzy/link.py` ($\mathcal K_1$, $\mathcal K_2$, $\mathcal U$) and `fuzzy/plaquette.py` (`plaquette_row` $=\square$), both imported by the hashed `fuzzy/targets.py`.
- Failure scenario: someone flips a sign in `fuzzy/link.py::K2`. Then $U_{EK}=e^{-i(\frac\alpha2\mathcal K_1+\kappa_2\mathcal K_2)}$ changes, but `code_hash_for("fuzzy_link")` does not. `evaluate_program` hits its result cache (keyed by `code_hash_for`, program sha and spec sha; `compress/evaluate.py:361`) and returns the old "valid" verdict. M2C-G1 stays green and the archive looks current while it no longer matches the target. The same holds for `exact/spinnet.py` and the spinnet archive.
- Why it is not blocking:
  - The spinnet list is the same as before 008 (`SPINNET_CODE_FILES`), so this is not a regression. For fuzzy, 008 added an own list but left it incomplete.
  - The four files last changed at `06ea6bc` (M0) and `1fdfb26` (M9), long before every archive and every 008 replay. All current verdicts were computed with today's file contents.
  - Fixing it changes `code_hash_for` for spinnet and fuzzy, which forces a replay of those archives.
- LSH's list already contains `exact/spinnet.py` and `exact/compare.py`.
- Fix:
  - At the next window that changes hashes, add `exact/spinnet.py` and `exact/compare.py` to the spinnet entry and `fuzzy/link.py` and `fuzzy/plaquette.py` to `_FUZZY_FILES` (planner decision, then a replay).
  - Add a unit test: for each registered encoding, the `su2plaq` modules imported by `factory()`, `target()` for every kind, and `verdict` must be a subset of `evaluator_files(e)`, apart from an explicit allow-list (package `__init__`s, `provenance.py`, seed-only modules). The script above is a ready prototype.

**N2. A replay does not flag a changed program file.**
- Where: `compress/replay.py:167-176, 237-243`.
- `entries` records the new `program_sha256` only, and `problems()` never compares it with the recorded one.
- Failure scenario: a file under `compress/programs/` is edited after its round (proposers can write there), or a round-0 seed program is regenerated with different content because the general-circuit code changed. The replay evaluates the new file under the old id. The record only flags it if the entry stops being valid or its key changes. An edit that keeps the key, or a previously invalid entry that becomes valid, passes silently.
- Checked now:
  - in all five replay records (111 entries), old and new sha256 are equal for every entry;
  - all 107 archived program files match their recorded sha256.
- Fix: `problems()` gains `"program_changed": [e["id"] for e in res["entries"] if e["program_sha256"] != <old candidate's program_sha256>]` (store the old sha in `entries[i]["old"]`), and `report()` exits 1 on it.

**N3. Rebuilding a headline circuit does not check the program sha.**
- Where: `crosscheck/ks.py:90`, and `fuzzy/compress_hook.py:228-230` (`circuit_of_entry`, used by `headline_step`).
- Both read `entry.program_path` and rebuild without comparing the file's sha256 with `entry.program_sha256`, yet `ks.step_circuit` returns `entry.program_sha256` in its info. A modified file would be cross-verified, or composed, under the archived identity.
- Same mitigation as N2: all files match today.
- Fix: compare the shas and raise `round.ProgramShaMismatch`, as `round._circuit_of` already does.

**N4. The `robust.json` cache key does not include the code of `compress/robust.py`.**
- Where: `robust.py:268-287` (`_load_cache`), `:333-334`.
- Records are reused while the stamp and encoding hashes, the angle set and the program sha are unchanged. But $\rho$ and `offset_class` are computed by `generic_angle_linear` and `angle_offsets` in this unhashed module.
- Failure scenario: someone edits `LINEAR_TOL` or the offset table. Every `compute=False` reader (m11 H2/H3, `headline_step`, `crosscheck.report.gate_table`) keeps using the old ρ and classes. This affects reports only, never verdicts, and ρ only breaks ties after CX and $\sum T$.
- Fix: store `robust_code_sha256` (sha256 of `compress/robust.py`) in the cache and check it in `_load_cache`. The file stays out of the verdict hash lists, as prompts/008 §6 requires.

**N5. Fixed temporary name `robust.json.tmp` (focus item 6): it can be fixed now, and doing so breaks no hash freeze.**
- Where: `spinnet/loop.py:782-784`, `rishon/compress/robust.py:177-180`.
- The premise of the brief is wrong:
  - I took the union of `evaluator_files(e)` for all six encodings, `RISHON_EVALUATOR_FILES` and `SPINNET_CODE_FILES`. It contains no `loop.py`, `robust.py`, `replay.py`, `headline_step.py` or `crosscheck/*`.
  - `spinnet.loop.code_hash()` (the "spinnet loop" hash of reports 428/430) hashes `provenance.code_hash()` and `SPINNET_CODE_FILES` only (`loop.py:64-74`), not `loop.py` itself.
  - No locked test pins the bytes of either file.
- Race consequence: two `compute=True` runs on the same encoding share the temporary file. The outcome is either a `FileNotFoundError` from the second `replace` or a truncated `robust.json` that later raises `JSONDecodeError`. Both are loud. Every record is computed independently and keyed by id and program sha, so the race cannot produce a silently wrong number.
- Recommendation: replace both blocks with `compress.robust._atomic_write_text` before the next `compute=True` run, in an ordinary builder step. It is not needed before the tag. (In rishon's loop the write sits inside the per-entry loop; moving it after the loop, as `compress/robust.py:350-352` does, also stops the many rewrites.)

**N6. Files written by `_atomic_write_text` are mode 0600 (tester 429 O1). This does not matter for correctness.**
- Where: `robust.py:255-259`. `mkstemp` creates the file 0600 and `os.replace` keeps that mode.
- Git stores only `100644` or `100755`, so nothing changes in the repository. I checked: the committed `robust.json` files are `100644` in the index and 0644 on disk.
- The only effect: another OS user or service account on the machine could not read a freshly written file. This is a single-user desktop.
- Optional one-line fix: `os.chmod(tmp, 0o644)` (or `0o666 & ~umask`) before `os.replace`.

**N7. Proposer-brief wording about offsets.**
- Where: `robust.py:71` (`HEADLINE_RULE_SECTION`).
- It tells proposers that multiples of $\pi/2$ belong in separate `s`/`sdg`/`z` gates. That is correct for `rz` and `p`. For singly controlled rotations only multiples of $\pi$ are Clifford (prompts/010 §1 and its do-not-retry list).
- No count is affected, because T is measured from the actual angles. But a proposer could read the sentence as permission to treat a $\pi/2$ offset on `crz`/`cp` as free.
- Suggested addition: "(for `crz`/`crx`/`cry`/`cp` only multiples of $\pi$; $\mathrm{cp}(\pi/2)$ is a controlled-$S$ and costs T)". This file is not hashed.

**N8. What $\bar T$ of the composed fuzzy step means.**
- Where: `fuzzy/headline_step.py:77`, `crosscheck/report.py:286-289`.
- $\bar T_{\rm step}=\bar T_{U_B}+4\bar T_{\rm link}$ is a sum of per-unit 20-pair means:
  - the link unit is averaged over independent random $(\alpha,\kappa_2)$ pairs, while the composed step uses $\kappa_2=\alpha/2$;
  - $U_B$ is averaged over $\beta$ only.
- So it is not the T count of the composed step averaged over one common angle set. prompts/010 §4.3 defines it this way and it is not a physics error (T per rotation varies by only a few units). Reports 10 and 11 should state the definition in one sentence.
- The gate table sums the unit CX instead of reading the composed file. The two agree ($131$), but a cross-check `row["headline"]["cx"] == compressed_step_headline.json["inner"]["cx"]` would catch a future drift.

**N9. Bauer–Fike sentence in METHODS §13.1.**
- "A passing verdict certifies the step's eigenphases" should read "up to the common global phase $\varphi$".
- The theorem places every eigenvalue $\mu$ of $A$ within $\|A-e^{i\varphi}V\|_2$ of an eigenvalue of $e^{i\varphi}V$. All eigenphases are therefore fixed only relative to $\varphi$, which the evaluator chose.
- This is wording only (planner/coordinator edit of METHODS).

## 6. What this means

- **Evaluator.** The consolidation does what prompts/008 asks without silent physics errors. The new span-leak term implements the METHODS equation exactly, is a true part of a rigorous upper bound, and is only ever added to the judged quantity.
- **Dispatch.** Every encoding reaches its own verdict function, target, Gauss setting and cache key, and no module patches shared code any more.
- **Headline rule and replays.** The angle set is one definition and equals the pre-008 set. The headline caches are current, and their headlines match prompts/010 §2 (fuzzy_ub `r10-F1-010` $(83,12688,0,30902,10)$, fuzzy_link `r02-F2-001` $(12,12576,0,23373,4)$). The replays lost nothing and changed no key or program.
- **Cross-checks.** The M11 code uses signed comparisons where signs matter, and its one analytic coefficient ($\tfrac{13}{4g^4}$) checks out by hand.
- **Remaining gaps.** These are provenance gaps that a future edit could exploit (N1–N4), not errors in today's numbers.

## 7. Problems and assumptions

- I did not re-run the acceptance suite. I rely on `reports/tests/430` for the pass/fail state and on `reports/tests/414` for the dense-reference span-leak comparison. My own runs were the targeted checks listed in §2.
- The hash-coverage scan (N1) sees only modules imported while building the factory, verdict hook and targets in one process. A lazily imported module used only on a path I did not trigger (for example the aer_mps engine) would not appear. The scan therefore gives a lower bound on what is missing.
- I did not audit `compress/brief.py` or the CLI wrappers beyond checking that they decide no verdict.
