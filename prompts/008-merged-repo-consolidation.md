# 008 — Consolidation of the merged repo: registry instead of shims, span leak, headline rule, one refresh of every archive

- Date: 2026-11-10. Git commit at planning time: `d65d325` (branch `merge-desktop-tracks` = master; tree dirty with other agents' track files).
- Trigger: coordinator request (cross-track, low number range) after the three merges. Inputs: `notes/merge-notes-spinnet.md` (items 1–3, M4 items 1–8, audit 100 N3, robust-T proposal), `notes/merge-notes-rishon.md` (M6 items 1–7, robust-T proposal), `notes/merge-notes-fuzzy.md` (hook design, laptop diff), `reports/audits/100` N3, `reports/audits/002` R1, `reports/audits/300`, `301` (A1, A2), the flaky unit test, the stale `compress/lean/structure.json`, `notes/STATUS.md` "Known issues", `prompts/400` §9 (planned LSH hook).
- Research note with every number quoted here: `reports/research/005-consolidation-robust-t-span-leak.md`. Methods: `docs/METHODS.md` §6 (amended) and §12 (new).
- Plan in force after this file: `prompts/002` + addenda `003`–`007` for the shared machinery, the track plans (`104`, `203`+`204`, `302`, `400`) for their milestones, **this file for the consolidation milestone "M2c"**. Locked tests: `tests/acceptance/m2c/` (28 tests, new). No existing locked test is changed by this run; two small errata are specified in §9 and are applied later, by the planner, at the step that needs them.

Words: *shim* = a track module that makes the shared compression code (`su2plaq.compress.*`, written for the twelve-qubit encoding) work for another encoding by replacing its functions at run time (*monkey-patching*) or by keeping a parallel copy; *registry* = one table, in the shared code, that says for every encoding which object, files and hooks to use; *dispatch* = the shared function looks the encoding up in the registry and calls its hook; *facade* = a track module that keeps its public names (the locked tests call them) but only forwards to the shared code; *evaluator hash* = sha256 of the source files that decide a verdict, stored in every archive entry; *replay* = re-evaluating the recorded rounds of an archive, in order, under changed code; *window* = the period in which hashed files may change.

## 1. Diagnosis (why this plan exists)

1. **Three different shim styles, all process-global.** Spinnet (`spinnet/loop.py::install`) replaces `compress.evaluate._build_in_subprocess` (by re-compiling its source with another worker command) and `compress.round._certify`, and rewrites the shared spec and brief texts by exact string replacement. Fuzzy (`fuzzy/compress_hook.py::install`) replaces `evaluator.evaluate`, `TaskSpec.render`, `TaskSpec.peak_qubit_cap`, `TaskSpec._structure_section`, `baselines.general_circuit`, `baselines.import_seed`, `round._certify`, `brief.make_brief`, `brief.make_ideation_brief`, sets an environment variable and appends a `sitecustomize` directory to `PYTHONPATH`. Rishon (`rishon/compress/*`) inserts into two shared dicts at import and keeps parallel copies of `evaluate.py`, `round.py`, `baselines.py`, `brief.py`. In one Python process (one pytest worker) the patches stack in import order; each shim checks the *shape* of the shared code textually and raises when it changes. A fourth copy is planned for LSH (`prompts/400` §9).
2. **The evaluator hash is not per encoding.** `provenance.code_hash()` covers the shared files and the twelve-qubit files only. Editing `encodings/spinnet.py` or `fuzzy/verify.py` does not invalidate a cached result or the `evaluator_sha256` of a spinnet/fuzzy entry (spinnet records a second hash in its round files; fuzzy records nothing). Rishon solved it with its own combined list.
3. **Any edit of a shared hashed file makes every archive stale at once** (research 005 §3): the gate tests of m2, m4, m10 compare the best entry's hash with `provenance.code_hash()`; m6 compares every entry and its replay record with `rishon.compress.code_hash()`, whose list contains the shared one.
4. **Evaluator notes that need a hashed-file edit anyway:** audit 100 N3 / audit 002 R1 (span leak missing from the error, controlled only per state), audit 301 A1 (Gauss residual stored as 0.0 when it was not computed), rishon M6-3 (`prune_fraction`), spinnet item 2 (`inner_target`).
5. Not caused by code: `compress/lean/structure.json` is stale (exporter fingerprint) and is rewritten by a locked m2 test on every run; one unit test fails for 2.3 % of commit hashes.

Consequence: do all hashed-file edits in **one window**, then **one replay** of every archive.

## 2. Decisions (with justification)

| # | Question | Decision | Why |
|---|---|---|---|
| 1 | Robust T in the archive key (track S/R proposal) | **Rejected for the archive, adopted as the headline rule of every encoding** (shared `compress/robust.py`; reports quote the robust-key minimum next to the archive best; every brief carries the "Headline rule" paragraph) | research 005 §1: the key is locked in four milestones and 76 entries; CX leads the search, T only breaks ties; on twelve, fuzzy_ub, fuzzy_link the two rankings are identical (0 order flips among 21, 11, 4 entries), on spinnet and rishon the headline rule is already locked; nominal T noise is 12–53 T per program, the 20-pair mean is 4.5 times sharper, which matters for the quoted number, not for the search |
| 2 | Span leak (N3, R1) | **Exact operator norm $\lVert S\rVert_2$, new fields `Verdict.span_leak`, `Verdict.total_error`; validity needs `total_error` $\le$ `tol_err`** (§5). `op_norm_error` keeps its locked three-term definition | METHODS §6 already states the bound with $\lVert S\rVert_2$; the exact value costs $\le1.5$ s per verdict, reproduces the auditor's $3.15\cdot10^{-7}$ and flips no locked verdict (research 005 §2). A separate field keeps the locked identities of M0-E6 / M1-V1 (`op_norm_error == block + dropped + leak` to $10^{-15}$, `leak_amplitude == 0.0`) |
| 3 | A1 | `gauss_residual = NaN` and `extra["gauss"] = "not_checked"` when the encoding is registered with `gauss_in_loop=False`; `"checked"` otherwise | a number that was never computed must not look measured; validity is unchanged (audit 301 A1 proves the Gauss property from block exactness for the fuzzy units) |
| 4 | A2 | Gate test M2C-G4: archive best and headline of every encoding verified at 2 further seeded angle pairs (plus $\kappa_2=0$ and $\kappa_2=\alpha/2$ for the fuzzy link). `TaskSpec.alt_angles` is **not** changed | a change of `alt_angles` changes the spec hash of every entry and adds 2/3 to every evaluation; the two extra points close the gap where it matters (what is reported). For an angle-linear program with fixed skeleton the error is a fixed trigonometric polynomial in $(\alpha,\beta)$, so a point chosen independently of the program detects a non-zero error with probability 1; Lean-certified entries are proved for all angles |
| 5 | Evaluator hash | `evaluator_sha256` keeps its present meaning per encoding (shared hash for twelve, spinnet, fuzzy; combined hash for rishon: the locked gate tests say so). New field `encoding_sha256` = hash of shared + that encoding's files, for every encoding; the result cache is keyed by it | closes diagnosis 2 without touching a locked test |
| 6 | Track module names | Stay, as facades (`spinnet.loop`, `rishon.compress.*`, `fuzzy.compress_hook`); m4, m6, m10 keep calling them | locked interfaces; only two mechanism asserts of m4 need an erratum (§9 E1) |
| 7 | Timing | §8. Window opens after `milestone-4` and after the fuzzy loops are closed; rishon side at the boundary "D7 done, C2 not started" (preferred), else after `milestone-6` | one rishon replay instead of two and no m6 erratum in the preferred case |
| 8 | Lean | Python certify dispatch now (step B1). Per-encoding pin table in `Su2PlaqCert` = optional step B9. **Third base angle in the shared checker: deferred** until `milestone-6` exists | the two-variable Laurent type is the trusted core of two working checkers; the rishon three-angle checker (step 6.L2) is being built now and has not been seen; no gate needs the merge |
| 9 | LSH (M8) | Registers through the registry; no fourth shim. `prompts/400` §9 "copy of `spinnet/loop.py`" is superseded by §3 here once step B1 is committed | — |

## 3. Method: registry and dispatch (interface; the builder creates stubs raising `NotImplementedError` first)

### 3.1 `src/su2plaq/encodings/registry.py` (new; added to `provenance.EVALUATOR_FILES`)
Pure data and lazy lookups; importing it imports no other project module.
```python
@dataclass(frozen=True)
class EncodingInfo:
    name: str
    factory: str                         # "module:attr", attr() -> the encoding object the compression code sees
    kinds: tuple[str, ...] = ("step", "UB", "UE")
    loop_kind: str = "step"              # the kind whose archive exists
    evaluator_files: tuple[str, ...] = ()   # extra files, relative to src/su2plaq, that decide a verdict or a metric of THIS encoding
    stamp: str = "shared"                # "shared": Entry.evaluator_sha256 = provenance.code_hash(); "encoding": = code_hash_for(name)
    gauss_in_loop: bool = True
    prune_fraction: float | None = None  # None -> evaluator.PRUNE_FRACTION
    verdict: str | None = None           # "module:attr"(qc, spec, mode, budget) -> Verdict; None -> the shared evaluator
    worker_warmup: str | None = None     # "module:attr"() run in the build worker BEFORE the audit guard is installed
    general_circuit: str | None = None   # "module:attr"(spec) -> QuantumCircuit
    seed_candidates: str | None = None   # "module:attr"(spec, root) -> [(label, program_path | None, circuit_fn | None)] for round 0
    import_seed: str | None = None       # "module:attr"(spec, source) -> SeedCircuit | reason string
    lean_certify: str | None = None      # "module:attr"(circ, spec, *, timeout, extra_provenance) -> dict; None -> status "n_a"
    lean_na_reason: str = ""
    render_spec: str | None = None       # "module:attr"(spec) -> str; None -> TaskSpec default text
    structure_json: str | None = None    # facts file shown to proposers, relative to the repository root
    tools: tuple[str, str] | None = None # (candidate command, oracle command) for spec and brief text; None -> the stock CLIs
    brief_note: str | None = None        # "module:attr"(encoding, kind) -> text appended to a brief
    headline: str | None = None          # "module:attr"(kind, root, refresh) -> dict; None -> the generic rule of compress/robust.py
    angle_linear: str | None = None      # "module:attr"(circuit, spec) -> (bool, str); None -> the generic linear fit (§6)

def names() -> tuple[str, ...]            # registration order
def info(name) -> EncodingInfo            # ValueError(f"unknown encoding {name!r}; known: {list(names())}")
def lookup(name) -> EncodingInfo | None   # None for a name that is not registered (hand-made test encodings)
def get(name)                             # cached instance of info(name).factory
def resolve(dotted: str)                  # "module:attr" -> object (importlib)
def register(info: EncodingInfo, replace: bool = False) -> None   # in-process only (tests); the build worker sees only the static table
```
The table is a literal in the module (`twelve` in step B1; `spinnet` B3; `fuzzy_ub`, `fuzzy_link` B4; `rishon` B5; `lsh` by the M8 plan). Nominal angles stay in `encodings/base.py::NOMINAL_ANGLES` as a literal dict with one key per registered encoding, all `(0.37, 0.61)`.

### 3.2 Shared modules (default behaviour for `twelve` byte-identical in every result)
- `compress/provenance.py`: `EVALUATOR_FILES` gains `"encodings/registry.py"`; `evaluator_files(encoding) -> list[Path]` (existing shared files in list order, then the encoding's); `code_hash_for(encoding) = code_hash(files=evaluator_files(encoding))`; `stamp_hash(encoding)` = `code_hash_for` if `stamp == "encoding"` else `code_hash()`. `code_hash()` itself is unchanged.
- `compress/spec.py`: `get_encoding(name)` = the `_ENCODINGS` cache (kept, so a hand-inserted object still works), else `registry.get(name)`; `default_spec` unchanged; `TaskSpec.render()` calls `info.render_spec` when set (the default text moves to `TaskSpec._render_default()`); `_structure_section` reads `info.structure_json`; tool commands from `info.tools`; `peak_qubit_cap()` uses `enc.peak_qubit_cap(spec)` when the encoding defines it.
- `compress/evaluate.py`: `_one_verdict` calls `info.verdict` when set, else the shared evaluator with `gauss=info.gauss_in_loop` and `prune_fraction=info.prune_fraction`; `evaluate_circuit` rejects `qc.num_qubits > 62` with reason `engine_qubit_limit` (the sparse engine's hard limit, today only checked by rishon); `_worker` calls `info.worker_warmup` for the encodings of its specs before `_install_audit_guard`; the worker command line stays `python -m su2plaq.compress.evaluate --worker ...`; the cache key uses `code_hash_for(spec.encoding)`. Private names used by locked tests and facades stay: `_build_in_subprocess`, `_scan_source`, `_worker`, `_classify`, `_time_limit`, `_seeds`, `_gate_violations`, `_read_cache`, `_cache_blob`.
- `compress/archive.py`: `Entry.encoding_sha256: str | None = None`; `entry_from_result(..., encoding=None)` stamps `evaluator_sha256 = stamp_hash(encoding)` and `encoding_sha256 = code_hash_for(encoding)`; every caller (shared round, spinnet and rishon rounds) passes the encoding.
- `compress/baselines.py`: `general_circuit`, `import_seed` dispatch on the registry; `qiskit_l3`, `general_polished`, `general_program_path`, `verify_synthesised` work for every encoding through them. `compress/round.py`: `_seed_candidates` uses `info.seed_candidates` when set; `_certify` uses `info.lean_certify` (`None` -> `{"status": "n_a", "reason": info.lean_na_reason}`); the round file gains `encoding_sha256`. `compress/brief.py`: structure pointer, commands and `info.brief_note` from the registry; the headline paragraph of §6 in every round brief. `compress/report.py::_row_external`: prints the row's own `beta` (spinnet M4 item 5). CLIs `run_candidate`, `oracle`, `round`, `report` accept every registered `--encoding`.
- `lean/certify.py::certify_circuit`: unchanged for `twelve`; other encodings are reached only through `round._certify` and the registry.

### 3.3 Facades (what remains in the track modules)
- `spinnet/loop.py`: `install()` only records `INSTALLED = {"encoding": True}` (idempotent); `spec`, `code_hash`, `render_spec` (= `spec.render()`), `write_spec`, seeds, `seed_round`/`run_round` (shared `run_round` plus the spinnet annotations of the round file), briefs, `ANGLE_SET*`, `robust_metrics`, `headline`, `report_table`, `certify_best`, CLI incl. `--worker` (alias of the stock worker) keep their names and results. Deleted: `_worker_copy`, `_certify_dispatch`, `_need`, the string rewrites of spec and brief (`_TOOL_REWRITES`, `_rewrite_text`).
- `fuzzy/compress_hook.py`: `install()` does nothing but set its flag; task classes, `general_circuit`, `compose_step`, `best_step`, `structure_facts`, `write_structure` stay. Deleted: every attribute assignment into a shared module, the environment edits, and the directory `fuzzy/sitehook/`. `scripts/m10_round.py` keeps its commands as aliases of the stock CLIs.
- `rishon/compress/`: `register()` is a no-op kept for callers; `code_hash()` = `provenance.code_hash_for("rishon")` (same file list and order as today: locked M2C-P1); `evaluate.py` keeps `trial_states`, `to_verdict`, the registered verdict function and `main` (worker alias), and re-exports `evaluate_circuit`, `evaluate_program`, `verify_synthesised`, `_build_in_subprocess` from the shared module (the 62-qubit check and the worker are shared now). `round.py`, `baselines.py`, `brief.py`, `oracle.py`, `run_candidate.py`, `robust.py`, `spec.py::render_spec` keep their code (they already only *call* shared helpers); they are not merged further in this plan (D14).

## 4. Method: per-encoding provenance
For encoding $e$ with shared list $F$ and own list $F_e$: `code_hash_for(e)` $=\mathrm{sha256}\big(\Vert_{f\in F\,\Vert\,F_e}\ \text{name}(f)\,\texttt{\\0}\,\text{bytes}(f)\,\texttt{\\0}\big)$ (the existing `code_hash(files=...)`). $F_{\rm twelve}=\varnothing$; $F_{\rm spinnet}\supseteq$ `SPINNET_CODE_FILES`; $F_{\rm rishon}$ = the ten files of `prompts/203` §3.1 in that order; $F_{\rm fuzzy\_ub}=F_{\rm fuzzy\_link}\supseteq$ {`fuzzy/verify.py`, `fuzzy/targets.py`, `circuits/fuzzy.py`, `fuzzy/compress_hook.py`}. Rule: an edit of a file in $F$ needs a replay of every archive; an edit of a file in $F_e$ needs a replay of archive $e$ only (its `encoding_sha256` goes stale; M2C-G1 turns red for $e$ alone).

## 5. Method: evaluator changes (`src/su2plaq/evaluate/evaluator.py`; equations in METHODS §6)

**Span leak.** $U\Psi=\Psi A+S+X$; $\lVert U\Psi-e^{i\varphi}\Psi V\rVert_2\le\lVert A-e^{i\varphi}V\rVert_2+\lVert S\rVert_2+\lVert X\rVert_2$. With, per outer pattern $o$, $P_o=B_oR_o$ (thin QR of the inner components of the $m_o$ states with support on $o$; an SVD basis if a diagonal entry of $R_o$ is below $10^{-12}$; cached in the encoding's evaluation cache), $\Omega_o=M_{r(o)}P_o$, $Y_o=B_o^\dagger\Omega_o$, $C_o=\Omega_o-B_oY_o$, $D_o=Y_o\Pi_o-R_oA_{[o,:]}$:
$$S^\dagger S=\sum_o\Pi_o^{\top}C_o^\dagger C_o\,\Pi_o+\sum_oD_o^\dagger D_o,\qquad \texttt{span\_leak}=\sqrt{\lambda_{\max}\big(S^\dagger S\big)},\qquad \texttt{total\_error}=\texttt{op\_norm\_error}+\texttt{span\_leak}.$$
$C_o^\dagger C_o$ is accumulated inside the existing loop over outer patterns (as `XX` is); the $D_o$ are stacked after $A$ is complete and one Gram matrix is formed. With a state subset (`states=`, trial mode) the columns are the selected inputs, the rows of $A$ all states. Shortcut: if $d=n_{\rm in}\cdot n_{\rm patterns}$ (the physical span is the whole code space: fuzzy units, rishon inner view) `span_leak = 0.0` exactly, nothing is computed. `aer_mps`: the same formula on the MPS block $M$. Never form $S^\dagger S$ as $W-A^\dagger A$ (floor $6\cdot10^{-8}$, research 005). Reference implementation to copy, not to re-derive: `scratch/planner/c008/evaluator_n3.py` (search "N3 prototype").

**Verdict.** New fields `span_leak: float = nan`, `total_error: float = inf` (after the existing ones; `_early` leaves the defaults); `extra["span_leak_max_state"]` = largest column norm of $S$; `extra["max_span_leak"]` stays. Reason order: `pruning_bound`, `dirty_ancilla`/`leak`, `error`, `gauss`, **`span_leak`** (iff `total_error > tol_err`), `ok`. The new reason comes last, so every verdict that failed before fails with the same reason, and only verdicts that passed can change. `results/store.py::_VERDICT_KEYS` and `round._record` gain the two fields; reports print `total_error`. `rishon/compress/evaluate.py::to_verdict` copies `span_leak` from the inner verdict and sets `total_error`.

**Tolerances: none changes.** Exact circuits: `tol_err` $=10^{-10}$ now applies to `total_error`. Synthesised circuits: `synth_tolerances(N_rot, eps)` $=N_{\rm rot}\varepsilon+10^{-9}$ is the triangle-inequality bound on the *whole* distance, of which $S$ is a part, so it needs no extra allowance (measured: $2.50\cdot10^{-6}\le4.0\cdot10^{-6}$, $2.70\cdot10^{-6}\le8.0\cdot10^{-6}$, Paulo $1.0756\cdot10^{-5}\le2\cdot10^{-5}$).

**Other.** `evaluate(..., prune_fraction: float | None = None)`: `None` = `PRUNE_FRACTION`; must be in $(0,1]$ else `ValueError`; `pruning_bound` iff `dropped_total > prune_fraction * tol_err`; the constant is unchanged. `inner_target(enc, ...)`: `enc.inner_target(...)` when the encoding defines it, the built-in operator for `twelve`, else `NotImplementedError`. `extra["gauss"]` = `"checked"` / `"not_checked"`; with `gauss=False` the residual stays `NaN` (the evaluator already does this; only the fuzzy hook overwrote it).

## 6. Method: headline rule for every encoding (`src/su2plaq/compress/robust.py`, new, not hashed)
`ANGLE_SET_SEED = 20261107`, `ANGLE_SET` = `default_rng(seed)`: $\alpha_i\sim U(0.05,2.0)$, 20 draws, then $\beta_i\sim U(0.05,1.2)$, 20 draws (identical to `spinnet.loop.ANGLE_SET` and `rishon.compress.robust.ANGLE_SET`; `angle_set_sha256()` = sha256 of `repr(ANGLE_SET)`). Robust key of a valid entry with a program file:
$$\Big(\mathrm{CX},\ \sum_{i=1}^{20}T_{10^{-6}}(\alpha_i,\beta_i),\ \rho,\ \sum_{i=1}^{20}\mathrm{depth_{CT}}(\alpha_i,\beta_i),\ \mathrm{qubits}\Big),$$
lexicographic; `None` (listed under `unrankable`) if the skeleton changes inside the set; full ties: archive key, then id. $\rho=0$ if the program is angle-linear, else 1: `info.angle_linear` when registered (twelve: the Lean exporter answers anything but `non_linear_angle`, as spinnet does), otherwise the generic test: every rotation angle of the lowered circuit equals $c_\alpha\alpha+c_\beta\beta$ with coefficients fitted by least squares on the 20 pairs and residual $\le10^{-9}$ at the 20 pairs and at the nominal pair.
```python
def robust_metrics(encoding, kind, program_path, root=None) -> dict      # keys as spinnet.loop.robust_metrics
def headline(encoding, kind="step", root=None, refresh=False) -> dict     # {"id","robust_key","t_mean","lean","archive_best","archive_best_robust_key","ranking":[...],"unrankable":[...]}
def report_rows(encoding, kind, root=None) -> list                         # GLOBAL BEST (archive key) and HEADLINE (robust key) rows for compress/report.py
def generality_points(encoding) -> tuple                                   # the pairs of M2C-G4 (seed 20261110; + (0.37, 0.0), (0.37, 0.185) for fuzzy_link)
HEADLINE_RULE_SECTION: str                                                 # the paragraph every round brief carries
```
`headline` delegates to `info.headline` when registered (spinnet: `loop.headline`; rishon: `robust.headline`; their locked definitions of $\rho$ differ and stay). Cache: `results/compress/<enc>/robust.json`, keyed by (id, program sha, angle-set sha, `encoding_sha256`). `summary.json` of every encoding gains `"headline": {"id","robust_key","t_mean","angle_set_sha256"}` (the spinnet format). The stop rule of future loops (LSH) counts rounds without a better robust key, as tracks S and R do.

## 7. Method: replay (`src/su2plaq/compress/replay.py`, new, not hashed)
`replay(encoding, kind, root=None, tag="008", lean=False) -> dict` and `latest_record(encoding, root=None) -> dict | None` (the `replay-*.json` with the latest `written_utc`; file modification time for a record without that field). Procedure = `prompts/204` §6.2 for any encoding: refuse (`ValueError`) if `replay-<tag>.json` or a `pre-<tag>` folder exists; read the round files; move `results/compress/<enc>/{round-*.json, feedback/, robust.json, summary.json}` to `.../pre-<tag>/` and `compress/archive/<enc>/` to `compress/archive/<enc>-pre-<tag>/` (nothing is deleted); re-run round 0 and then every round with its recorded program list in recorded order (the encoding's own round function when it has one: spinnet `loop.run_round`, rishon `round.run_round`); carry the `lean` dict of an old entry over to the new entry when the program sha256 is the same; restore the attempts log and the discoveries file byte for byte; write `replay-<tag>.json` with the 204 schema plus `encoding_sha256` and `written_utc`. A replay is not a round: stop counters and session counts do not move. `rishon.compress.replay.replay(kind, root, tag="204", lean=False)` is this function with `encoding="rishon"` and the extra field `prune_fraction`.

## 8. Timing and safe order

**What may run when.**
- Phase A (now, in parallel with every loop): touches no file that a loop imports from the shared hashed list.
- Phase B (the window) may start when ALL hold: **(P1)** tag `milestone-4` exists (spinnet gate closed; its loop has stopped, so spinnet is the first shim to retire); **(P2)** the fuzzy loops are closed (fuzzy_ub round 4 evaluated and tester-verified, no fuzzy proposer running); **(P3)** rishon stands at a step boundary and its builder is not editing `rishon/compress/*`: either **(c1, preferred)** `prompts/204` step D7 done and C2 not started, or **(c2)** tag `milestone-6` exists; **(P4)** `pgrep -af "su2plaq.*(round|run_candidate|loop|m10_round)"` shows no evaluation or proposer process; LSH may continue M7 (its files are in no hash list) but M8 must not have started a round.
- In case c1 the rishon track pauses between C1 and C2 until step B7 is committed; its own step C2 (replay "204") then *is* the rishon refresh, and rounds 5+ run on the facade. In case c2 rishon is replayed with tag "008" and erratum E2 (§9) is applied first.
- After step B7 (B8, B9 if taken) the hashed files are **frozen**: any later edit of a file in a hash list needs a new replay with a new tag (M2C-G1 says which archive).
- LSH M8 starts after step B1 at the earliest (registry available) and after the freeze at best.

**Expected red during the window (and only these; the tester must not escalate them before Phase C):** `m2::test_archive_best_valid_and_not_worse_than_seed`, `m4::test_M4_G1_archive_best_reverified_from_source`, `m10::test_M10_G1_archive_best_valid_and_not_worse_than_seed[*]`, `m6::test_M6_G1…`, `…G5…`, `…G6…`, `…S3…` (already `PENDING` on the 204 replay), `m2c::test_M2C_G1…G4`. Every other acceptance test must stay green after every step.

Option for the coordinator (not the default): develop Phase B on a branch in a `git worktree` (own directory, `lean/.lake` and `compress/cache` reflink-copied) while the loops finish, and merge when P1–P4 hold. Not the default because the agent guard hooks and the shared memory slice are configured for the main checkout.

## 9. Errata to existing locked tests (NOT applied now; planner applies them at the named step, coordinator re-locks)

**E1 (m4, at step B3).** `tests/acceptance/m4/test_spinnet_compress.py`, two mechanism asserts that require the monkey-patch to exist:
```diff
-    assert callable(L.INSTALLED.get("build_in_subprocess")) and E._build_in_subprocess is not L.INSTALLED["build_in_subprocess"]
+    assert L.INSTALLED.get("encoding") is True and not getattr(E._build_in_subprocess, "_spinnet_shim", False)   # prompts/008: registry, stock worker
```
```diff
-    assert set(L.INSTALLED) >= {"encoding", "build_in_subprocess", "certify"}
+    assert L.INSTALLED.get("encoding") is True                                                                  # prompts/008: nothing is replaced
```
Justification: both lines test *how* the worker learns the encoding, not *that* it does; the behavioural parts of M4-S2 (the worker builds the general program at three angle pairs, an oracle call inside `build` works, the import whitelist and the audit guard hold) and of M4-S7 (twelve still valid) are untouched, and M2C-R2/R3 lock the new mechanism more strictly (fresh interpreter, no attribute of any shared module changes). No tolerance is involved.

**E2 (m6, only in case c2, before step C2).** `test_M6_G1`, `test_M6_G5`, `test_M6_S3` read `replay-204.json` by name. Change: read the latest replay record (`su2plaq.compress.replay.latest_record("rishon", root)`), require `tag in ("204", "008")`, take the `pre-<tag>` paths from the record's tag, and additionally require that `replay-204.json` still exists. Justification: `prompts/204` §6.2 itself says a later hashed edit needs a new replay with a new tag; the invariants tested (nothing lost, keys equal, current hash) are unchanged.

## 10. Milestone M2c — steps

Conventions for every step: environment and memory rules of `CLAUDE.md` / `scratch/agent-common.md` (`tools/pytest-safe`, `tools/run-capped`, assigned cores); orient with graphify (`graphify query`, `graphify affected "<symbol>"`) before reading files and run `graphify update .` after code changes; no number typed into source; no exception swallowed in numerical code. "Regression set" = `tools/pytest-safe -n <k> -m "not slow" tests/acceptance/m0 tests/acceptance/m1 tests/acceptance/m2 tests/acceptance/m3 tests/acceptance/m3x tests/acceptance/m4 tests/acceptance/m5 tests/acceptance/m5x tests/acceptance/m6 tests/acceptance/m9 tests/acceptance/m10` + `tests/unit`, green except the expected-red list of §8 and tests that were `PENDING` before the step.

### Phase A — any time (now)
| Step | Work | Done-check | Acceptance ids turned green |
|---|---|---|---|
| A1 | Flaky unit test `tests/unit/test_results_unit.py::test_render_is_deterministic_and_contains_only_json_numbers`: circuit ids that cannot occur in a hexadecimal hash or a timestamp (e.g. `"zq-first"`, `"zq-second"`), and the negative check made on the id; add a variant that forces the provenance commit to `"c1c1c1c"` | the test and its variant pass; `tools/pytest-safe -n 4 tests/unit/test_results_unit.py` | none (unit only) |
| A2 | `lean/structure.py::write_structure_json`: do not rewrite the file when facts, symmetries, `exporter_sha256`, `checker_sha256` and the certificate status are unchanged (the volatile fields `git_commit`, `seconds` stay as first written). Then regenerate once (`python -m su2plaq.lean.structure --export`) and commit | running `tests/acceptance/m2/test_lean_structure.py::test_structure_json_and_spec_section` twice leaves `git status --short compress/lean/structure.json` empty; the file's `exporter_sha256` equals `certify._exporter_sha()`; `provenance.code_hash()` unchanged (`0bd7e7d9…`) | none yet (M2C-G2 is still `PENDING` on the registry import) |

### Phase B — the window (preconditions P1–P4 of §8)
| Step | Work | Done-check | Acceptance ids turned green |
|---|---|---|---|
| B0 | Coordinator: check P1–P4, `git tag pre-consolidation-008`, record `provenance.code_hash()`, `spinnet.loop.code_hash()`, `rishon.compress.code_hash()` in STATUS | tag exists; hashes in STATUS | — |
| B1 | §3.1, §3.2, §4 with the registry entry `twelve` only (the old shims keep working on top: `_ENCODINGS`, `NOMINAL_ANGLES`, every patched name still exists) | regression set green; a twelve trial + full evaluation of `compress/programs/twelve/seed/000-general.py` gives the same key as the archive entry `r00-seed-000`; unit tests for registry, provenance, dispatch defaults | none yet (R1, P1 need all five entries: B5; P2 needs the fuzzy entry: B4) |
| B2 | §5 (span leak, `Verdict` fields, reason, `prune_fraction`, `inner_target`, `extra["gauss"]`) | regression set green **including slow** `m0`, `m1` (M0-E5 `aer_mps`, M1-P1 Paulo, M1-V1 prune, M1-T1) and `m3`; span leak of the twelve general step $\le10^{-12}$ | `m2c/test_consolidation_evaluator.py::test_M2C_E1_span_leak_exact_against_dense_reference`, `::test_M2C_E3_span_leak_decides_validity`, `::test_M2C_E4_prune_fraction_keyword`, `::test_M2C_E6_inner_target_dispatch` |
| B3 | Planner applies E1; coordinator re-locks. Registry entry `spinnet`; `spinnet/loop.py` becomes the facade of §3.3 | all of `tests/acceptance/m4` not slow, `m3`, `m3x` green; `python -m su2plaq.compress.run_candidate compress/programs/spinnet/seed/000-general.py --encoding spinnet --kind step --trial` exits 0 in a fresh shell; rendered spec byte-identical to the committed `compress/specs/spinnet-step.md` | none new (m4 stays green with E1) |
| B4 | Registry entries `fuzzy_ub`, `fuzzy_link`; `fuzzy/compress_hook.py` facade; delete `fuzzy/sitehook/`; `scripts/m10_round.py` aliases | `tests/acceptance/m10` not slow and `m9` not slow green; stock CLI trial of both fuzzy seed programs exits 0 | `m2c/…evaluator.py::test_M2C_E2…`, `::test_M2C_E5_gauss_not_checked_is_reported_as_such`, `m2c/…registry.py::test_M2C_P2_shared_round_stamps_both_hashes` |
| B5 | Registry entry `rishon`; `rishon/compress` facade of §3.3 (c1: after rishon step C1, before C2; c2: after `milestone-6`) | `tests/acceptance/m5`, `m5x`, `m6` not slow green except those `PENDING` on the replay; `rishon.compress.code_hash() == provenance.code_hash_for("rishon")`; rendered spec byte-identical to `compress/specs/rishon-step.md` | `m2c/…registry.py::test_M2C_R1_registry_content`, `::test_M2C_R2_fresh_process_and_stock_worker_know_every_encoding`, `::test_M2C_R3_track_facades_patch_nothing`, `::test_M2C_P1_code_hash_per_encoding` |
| B6 | §6 `compress/robust.py`; headline paragraph in every round brief; `report.py` prints GLOBAL BEST and HEADLINE rows | unit tests (angle set equal to both track sets; generic $\rho$ on a linear and on a shifted-angle toy program; ranking on a three-entry toy archive); `m4::test_M4_S8…`, `m6::test_M6_H1…` still green | none yet (G3 needs Phase C) |
| B7 | §7 `compress/replay.py` (+ `rishon/compress/replay.py` as the wrapper, if rishon step C1 has not built it, else that module is turned into the wrapper) | unit test: dry replay of a kind-`UE` twelve seed round under a temporary root | `m2c/test_consolidation_gate.py::test_M2C_Y1_replay_on_a_copy_of_the_link_archive` |
| B8 (optional; skip if any of B1–B7 needed a fixer) | `metrics/cliffordt.py::synthesize` carries `qc.metadata["layers"]` remapped to the new instruction ranges (fuzzy merge note) | `m9` slow T1[step] passes and its wall time is reported (was 27 min); T counts of every existing result unchanged | — |
| B9 (optional, Lean builder; must end or be abandoned before C3) | `Su2PlaqCert/Check.lean`: `validate`/`check` take a pin set (register sizes, `physicalDim`, state and target fingerprints) chosen by the certificate field `"encoding"` (absent = twelve); `SpinNet/Check.lean` becomes a thin alias; both executables keep their names | `lake build` clean; `m2::test_lean_certificate_small_accept_reject_na`, `m2::test_lean_checker_semantics_match_sparse_sim`, `m4::test_M4_L1_certificate_general_and_seeds` green; the mutation hunts of reports/tests/037 and 109 re-run by the tester with zero accepted mutants | — |

### Phase C — one refresh, then the gate
| Step | Work | Done-check | Acceptance ids turned green |
|---|---|---|---|
| C0 | Coordinator: clean commit, declare the hash freeze in STATUS with the three hashes | `git status --short src` empty | — |
| C1 | Replays in the background on quiet, separate cores: `tools/run-capped python -m su2plaq.compress.replay --encoding E --kind K --tag 008` for `twelve/step`, `spinnet/step`, `fuzzy_ub/UB`, `fuzzy_link/UE`. Tester (mode `step`): record invariants, keys and best ids equal to before, attempts and discoveries byte-identical | four `replay-008.json`, `lost == []`; best id and key of each archive equal to the ones recorded before the replay (`best_old` in the record) | `m2c/…gate.py::test_M2C_G1_archive_replayed_under_current_code[twelve-step]`, `[spinnet-step]`, `[fuzzy_ub-UB]`, `[fuzzy_link-UE]`; `m2::test_archive_best_valid_and_not_worse_than_seed`; `m4::test_M4_G1_archive_best_reverified_from_source`; `m10::test_M10_G1_archive_best_valid_and_not_worse_than_seed[*]` |
| C2 | Rishon: c1 → `prompts/204` step C2 as written (tag "204"); c2 → planner applies E2, then replay with tag "008" | as `prompts/204` C2 | `m2c/…gate.py::test_M2C_G1…[rishon-step]`; `m6::test_M6_G1…`, `::test_M6_G5_replay_record`, `::test_M6_S3_round0_recorded` (and `G6` after rishon step C5) |
| C3 | Lean and headline: `--certify-best` for the archive best and the headline of twelve and spinnet (fuzzy `n_a`; rishon per its plan); `robust.headline(E, K, refresh=True)` and the report tables for all five; regenerate the track result files that quote the headline on a clean commit (`scripts/m4_results.py`, the M10 compressed-step file, rishon per its plan) | `summary.json` of all five has `headline`; twelve and fuzzy headlines reported next to the archive best (expected to coincide, research 005 §1; if not, both rows are reported and STATUS notes it) | `m2c/…gate.py::test_M2C_G3_headline_rule_on_every_archive[*]`, `::test_M2C_G4_best_and_headline_valid_at_unseen_angles[*]`; `m2::test_archive_best_lean_status_recorded`; `m4::test_M4_L5…`, `::test_M4_R1…`; `m10::test_M10_G3…` |
| C4 | Regenerate `compress/lean/structure.json`, `compress/specs/*.md`, structure files of the tracks, briefs of open loops; commit | `git status` clean after a second run of the m2/m4/m6/m10 spec tests | `m2c/…gate.py::test_M2C_G2_structure_json_is_current` |
| C5 | Gate: tester `full` (all of `tests/acceptance` incl. slow and m2c, `tests/unit`, `python tools/check_lock.py && ~/.claude/bin/acceptance-check`); auditor on `pre-consolidation-008..HEAD`; benchmark against `reports/benchmarks/003` and the track benchmarks; `git tag milestone-2c`; short report | all green; benchmark deltas explained by §12 only | all of m0–m10 and m2c |

## 11. Acceptance tests added (none changed) and tolerances

`tests/acceptance/m2c/` — 28 tests, all collect and fail with `PENDING:` today (checked: `tools/pytest-safe -n 2 -q tests/acceptance/m2c` → 28 failed, 28 `PENDING:` messages, 0.8 s; `pytest --collect-only -q tests/acceptance` → 341 tests).

| File :: ids | What | Tolerance | Justification |
|---|---|---|---|
| `test_consolidation_registry.py` :: `R1`, `R2`, `R3`, `P1`, `P2` | registry content; every encoding known to the plain shared code and the stock worker in a fresh interpreter; the facades change no shared attribute and no environment variable; hash composition; a shared dry round stamps both hashes | exact (identities, shapes, hashes); `(0.37, 0.61)` exact | definitions |
| `test_consolidation_evaluator.py` :: `E1` | `span_leak`, `leak_amplitude` against a dense $256\times256$ reference built in the test (spin network, $U_E$ synthesised at $10^{-6}$ and $10^{-4}$) | $\lvert\Delta\rvert\le$ `dropped_total` $+10^{-12}$ | the evaluator's certified pruning bound plus float64 rounding of $\sim10^3$ gate products on numbers $\le1$; measured $6\cdot10^{-16}$ and $1.2\cdot10^{-15}$ |
| `E2` | exact circuits (spinnet, twelve; full and 64-state trial): `span_leak` $\le10^{-12}$; fuzzy unit: exactly 0.0 | $10^{-12}$ | direct residual: measured $3.3\cdot10^{-15}$; a difference-of-Grams implementation gives $6\cdot10^{-8}$ and fails |
| `E1`, `E2` identities | `total_error = op_norm_error + span_leak`; `op_norm_error = block + dropped + leak` | $10^{-15}$ | same as the locked M1-V1 / M0-E6 |
| `E3` | `span_leak` decides validity; older reasons keep priority | thresholds built from the measured verdict (midpoint, factor 2, $1+10^{-6}$) | rule test, deterministic |
| `E4` | `prune_fraction` keyword on the locked M1-V1 construction (`dropped_total` $=3.125\cdot10^{-11}$) | $10^{-6}$ relative on `dropped_total` (as M1-V1); caps exact | prompts/005 |
| `E5`, `E6` | Gauss "not_checked" as NaN; `inner_target` dispatch | exact | definitions |
| `test_consolidation_gate.py` :: `Y1` | replay tool on a copy of the fuzzy_link archive | exact | schema of prompts/204 §6.2 |
| `G1[5]` | every real archive replayed; every entry and round file at the current hashes; nothing lost; keys equal | exact | goal 5 of the trigger |
| `G2` | `structure.json` fingerprints current | exact | — |
| `G3[5]` (slow) | headline rule on every archive; equal to the track headline for spinnet, rishon | exact integers | §6 |
| `G4[5]` (slow) | best and headline valid at unseen angle pairs | `total_error` $\le10^{-10}$, certified | the loop's exact-angle tolerance (prompts/004) |

## 12. Expected cost

| Item | Wall time | Source |
|---|---|---|
| Replay twelve (22 entries, 6 rounds) | $\approx16$ min evaluation (938 s) on a quiet machine; largest entry 242 s of the 300 s budget | round files (research 005 §3) |
| Replay spinnet / fuzzy_ub / fuzzy_link | 44 s / 30 s / 5 s | round files |
| Replay rishon | 30 min by the round files; 45–110 min budgeted by `prompts/204` | round files, prompts/204 §10 |
| Lean `--certify-best` twelve | 351 s (spinnet $\approx1$ s) | round-005 |
| Headline refresh (20 pairs incl. depth) | estimate $\le15$ min twelve, $\le5$ min each other; T-only measured 82 s (twelve), 63 s (fuzzy_ub), 8 s (fuzzy_link) | `proto_robust_t_all.log`; depth part is an estimate |
| Span leak per verdict | $+0.4$–$1.5$ s twelve (a few % of a verdict that reads outer bits, up to 30 % of a 1 s verdict), $+0.05$ s spinnet, 0 fuzzy/rishon | research 005 §2 — **a planned change of the benchmark "evaluator time per circuit"**, not a regression |
| Builder calls | A1, A2: 1 each; B1: 2–3; B2: 1–2; B3–B5: 1–2 each; B6, B7: 1 each; B9: 1–2 | estimate |
| M2c tests | not slow $\approx1$–2 min; `G3`, `G4` $\approx10$–20 min (headline cache warm: $\approx5$ min) | estimate; each worker $<2.5$ GB |
| Memory | span leak $\le0.2$ GB extra on twelve; replays $\le2.5$ GB each | prototype, CLAUDE.md |

## 13. Do-not-retry list
- A fourth shim (copying `spinnet/loop.py` for LSH), or any new assignment into an attribute of `su2plaq.compress.*`, `su2plaq.evaluate.*`, `su2plaq.lean.*` from a track module; `sitecustomize` / `PYTHONPATH` / environment hooks for the worker (fragile, process-global, invisible in a fresh interpreter).
- Editing archive entries in place to give them a new hash; replaying into an existing tag; counting a replay as a round.
- Putting every encoding's files into the one shared `EVALUATOR_FILES` list (any LSH edit would make four archives stale).
- Computing the span leak as $W-A^\dagger A$ or from per-state weights (floor $6\cdot10^{-8}$); using $4\cdot$`gauss_residual` or the Gauss operator-norm bound as the span-leak term (loose by 1.6–7, and undefined for encodings without a Kogut–Susskind decoder).
- Folding $S$ into `leak_amplitude` or `op_norm_error` (breaks the locked identities of M0-E6 and M1-V1 on exact twelve circuits, where $S\approx3\cdot10^{-15}\neq0$).
- Changing the archive key or `TaskSpec.alt_angles` (new spec hash and new key for 76 entries).
- Satisfying the two m4 asserts of E1 by storing some other callable under `INSTALLED["build_in_subprocess"]` (meets the letter, defeats the test).
- Hashed-file edits outside the window, however small.

## 14. Risks and stop conditions
- **A previously valid entry is lost in a replay** (`lost != []`). Possible causes: evaluation budget under machine load (reason `eval_budget`; re-run that archive alone on idle cores — a timeout is never cached), or a real span leak above $10^{-10}$ (reason `span_leak`). The second is a finding about the entry, not a tool failure: stop that archive, send the entry to the tester for an independent check, report to the planner. Do not loosen anything.
- **Benchmark:** span-leak time on twelve above $+1.5$ s per verdict, or any other task $>10$ % slower → fixer (profile the per-pattern loop; the stacked Gram is one BLAS call).
- **A facade step breaks a locked track test for a reason other than the E1 lines** → builder once, then fixer; if the test pins a mechanism this plan removes, stop and return to the planner (an erratum must be written and justified, never improvised).
- **Case c1 slips** (rishon reaches C2 before B7 is committed): do not hold rishon longer than one working session; switch to c2.
- Stop and ask the planner when: two replays of the same archive disagree on a key; `M2C-R3` reports a changed attribute that no facade assigns (an import-time side effect elsewhere); step B9 changes the verdict of any existing certificate.
- For Digonto's review afterwards (autonomous defaults, §15): decisions 1, 2, 7, 8 of §2.

## 15. Defaults taken in this run (autonomy grant of 2026-11-10)
D1 robust T = headline rule for all encodings, archive key unchanged. D2 span leak exact, separate field, validity on `total_error`, reason last. D3 A1 = NaN + `"not_checked"`. D4 A2 = gate/headline check at 2 unseen seeded pairs (seed 20261110) + two link points; rule of the loop unchanged. D5 static registry table with lazy `"module:attr"` strings; `NOMINAL_ANGLES` a literal for all encodings. D6 `evaluator_sha256` meaning unchanged, new `encoding_sha256`, cache keyed per encoding. D7 track modules stay as facades. D8 window after `milestone-4` + fuzzy closure, rishon boundary c1 preferred, c2 fallback with E2. D9 errata E1/E2 specified here, applied later by the planner. D10 Lean: Python dispatch now, pin table optional (B9), third base angle deferred past `milestone-6`. D11 LSH M8 uses the registry. D12 `synthesize` layer metadata optional (B8). D13 replay tags "008" (rishon "204" in case c1); Lean dicts carried over, best and headline re-certified. D14 rishon de-duplication limited to `evaluate.py`. D15 the 62-qubit engine check moves to the shared code. D16 file numbers 008 / 005 as the coordinator named them (low cross-track range), not the `next-num` proposal 401.
