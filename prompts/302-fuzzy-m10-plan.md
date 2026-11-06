# Plan 302 — M10: compression of the fuzzy one-Trotter-step circuit (Gu-et-al loop on two units)

Date: 2026-11-06. Planner (Claude Fable 5.1), short run. Trigger: START_HERE §4 (M10 brief), M9 nearly gated
(`reports/tests/300` PASS, `reports/audits/300` PASS WITH NOTES). Loop protocol: prompts/001 §4; machinery and gate tests:
prompts/002 §5, prompts/006 (Lean). Methods: `docs/METHODS-fuzzy.md` F9 (new). Locked tests: `tests/acceptance/m10/`.
Prototype numbers below: `scratch/planner/m10_hook_proto.py` (+ `.log`). **Session hard stop 5 h 15 min: every step has a
"skip if" rule.** No research report (no new method; parity-network / phase-polynomial synthesis is standard, see F9).

## 0. Decisions
1. **Two compression units, not the 48-qubit step.** There is no dense step target ($2^{48}$; `FuzzyEncoding.physical_vectors`
   is a sample of ~$10^8$ states, plan 300 §5), so the laptop evaluator cannot score a step program. The step factorises exactly
   (F3): $U = [\bigotimes_{\rm outer}U_{EK}]\,U_B\,[\bigotimes_{\rm inner}U_{EK}]$ with $U_{EK}=U_KU_E$ one-link blocks (they
   commute). Units: **`fuzzy_ub`** (kind `UB`): $e^{+2i\beta\square}$ on the 8 row qubits, exact $256\times256$; **`fuzzy_link`**
   (kind `UE`): $U_{EK}(\alpha,\kappa_2)=e^{-i(\frac\alpha2\mathcal K_1+\kappa_2\mathcal K_2)}$, exact $16\times16$, with
   **`spec.beta` playing $\kappa_2$** so that the three angle pairs are three independent $(\alpha,\kappa_2)$ points (a valid
   program is bilinear-exact, works for every $r$ incl. $r=0$, and the step uses it at $\kappa_2=r\alpha/2$).
   Why merged $U_{EK}$ and not $U_E$, $U_K$ separately: the $U_K$ Clifford frame `cx(q1,q3) cx(q2,q4) h(q1) h(q2)` diagonalises
   $\mathcal K_1$ too ($Z_1Z_3\to Z_3$), so $U_{EK}$ = one Clifford frame + 10 $Z$-string rotations: a single parity network
   (≤ 14 CX for 10 parities on 4 qubits, Gray-code bound $2^4-2$) instead of two ladders (36 CX). Separate units could not merge.
2. **Step score = composed count.** `compress_hook.compose_step` places the link unit on the 12 links (inner first, then
   $U_B$ on the inner row qubits + its ancillas, then the 8 outer blocks; order 2 = half-angle link blocks on both sides),
   each link block with its own ancillas (kinetic unit: none allowed, §3), and writes `metadata['layers']`. The composed circuit
   is measured by `logical_metrics` (CX, $T_{\rm fixed}$, $N_{\rm rot}$, depth, qubits) and **re-verified by M9's
   `verify_step_samples`** (blocks certified on a complete basis, composition sampled — the same trust label as M9, F6).
3. **Validity = laptop rules unchanged** (prompts/001 §4): allowed gates; exact $\le10^{-10}$ on the full block after one
   global phase at nominal AND the two alternate pairs with identical skeleton; clean ancillas (leak $\le10^{-10}$ amplitude);
   peak qubits $\le$ data + 32 (UB: 40; link: **4, no ancillas**); wall $\le300$ s. Gauss: not re-checked per unit — every
   computational state is physical for the unit, and both targets commute with all $\mathcal T^A$ (audit 300 A1/A3), so full
   block exactness implies Gauss preservation; the composed step's Gauss residual is checked by `verify_step_samples`.
4. **Score key** $(\mathrm{CX},T_{10^{-6}},\mathrm{depth}_{CT},\mathrm{qubits})$ per unit (laptop `metrics.key`), MAP-Elites
   cells as the laptop. Composed step reported as (CX, $T_{\rm est}(10^{-6})$, depth, qubits) of the composed circuit.
5. **Lean**: the laptop certificate exporter is twelve-specific (433 states, `exact_target_blocks`); the hook records
   `Entry.lean = {"status": "n_a", "reason": "fuzzy: no exact exporter (plan 302)"}` so the report column renders `n_a`.
   M9's kernel-checked link algebra / counts stay the Lean content of Report 10. Rounds run with `--no-lean` semantics via the hook.
6. **Audit NB-1** (layer coverage in `verify_step_samples`) must be fixed before 10.3 (it is being fixed; `compose_step` writes
   contiguous covering layers anyway, test H3 asserts it).

## 1. Method (equations; F9)
* Units as in §0.1; conventions F1–F3 unchanged (row index $\sum_l(2q_1^l+q_2^l)4^l$; unit frame qubit $2l=q_2^l$, $2l+1=q_1^l$,
  i.e. frame qubit $i$ = circuit qubit `ROW_QUBITS[i]`; link frame qubits $(0,1,2,3)=(q_4,q_3,q_2,q_1)$).
* Baseline counts (prototype, nominal): link $U_{EK}$ (36, 644, 1515, 4) → polish (30, …); $U_B$ (1718, 2822, 4924, 15)
  → polish (1596, …). Composed step with outer links: CX $=1718+12\cdot36=2150$, $N_{\rm rot}=16+120=136$.
* Compression levers (for the ideation brief, not prescriptions): $U_{EK}$ parity network over the 10 strings
  $\{Z_2,Z_2Z_4,Z_4,Z_2Z_3,Z_2Z_3Z_4,Z_3Z_4\}$ ($\mathcal K_1$) and $\{Z_1,Z_1Z_2Z_3,Z_1Z_2Z_3Z_4,Z_1Z_3Z_4\}$ ($\mathcal K_2$) in the
  $U_K$ frame; or a label-computation using the 5 joint eigenphases ($(\mathcal K_1,\mathcal K_2)\in\{(0,\mp4),(\tfrac32,\mp2),(2,0)\}$).
  $U_B$: `rccx` instead of `ccx` in compute/uncompute pairs (3 vs 6 CX), one unary decode of the 3 parity bits into 8 flags
  (7 ancillas, shared by all sectors) instead of 8 three-controlled ANDs, Gray ordering of sectors, uncontrolled Clifford frames
  where the sector flag makes the control redundant, merging the $(c_0,c_1)$ flag pairs.
* References: Gu et al. arXiv:2610.22367 (loop structure); Amy–Maslov–Mosca, IEEE TCAD 33 (2014) 1476, arXiv:1303.2042
  (phase-polynomial / parity-network synthesis of $\{{\rm CNOT},R_z\}$ circuits); Maslov, PRA 93 (2016) 022311, arXiv:1508.03273
  (relative-phase Toffoli, `rccx`); Gidney, Quantum 2 (2018) 74, arXiv:1709.06648 (AND-ladder uncompute). All as in METHODS §7/§9.

## 2. Hook (our file `src/su2plaq/fuzzy/compress_hook.py`) and the laptop diff
Monkey-patch, nothing in `src/su2plaq/compress/*` edited. `install()` (idempotent):
```
spec._ENCODINGS["fuzzy_ub"/"fuzzy_link"] = FuzzyUBTask()/FuzzyLinkTask(); spec.get_encoding = evaluate.get_encoding = baselines.get_encoding = oracle.get_encoding = wrapper
base.NOMINAL_ANGLES[...] = (0.37, 0.61)
evaluator.evaluate = wrapper: for FuzzyBlockEncoding targets force gauss=False, set gauss_residual=0.0; for FuzzyLinkTask refuse num_qubits > 4 (Verdict reason "max_qubits" via evaluator._early)
baselines.general_circuit = dispatch (fuzzy_ub: build_UB remapped to the 8-qubit frame + 'anc'(7), p(-pi) -> z [exact; _fit_angles needs angle-linear gates]; fuzzy_link: link_UE(alpha) + link_UK(spec.beta))
baselines.import_seed = reason strings for fuzzy encodings ("not applicable to the fuzzy encoding"); qiskit_l3_whole works through general_circuit
round._certify = returns {"status": "n_a", ...} for fuzzy specs
spec.STRUCTURE_JSON = ROOT/"compress/specs/fuzzy-structure.json" (written by the hook: M9 Lean facts — counts 50/12800/101197218/6767266914, K1/K2 spectra, square spectrum/blocks; proved_by "decide"/"numerical")
os.environ["SU2PLAQ_FUZZY_HOOK"]="1"; os.environ["PYTHONPATH"] += ":" + ROOT/"src/su2plaq/fuzzy/sitehook"   # the evaluate worker subprocess (python -m su2plaq.compress.evaluate --worker) inherits os.environ and imports sitehook/sitecustomize.py, which calls install() when the variable is set — so Builder(spec) resolves the fuzzy encodings inside the sandbox
```
Verified in the prototype (all but the sitehook and `_certify` lines): trial/full/polish/render/perturbation behave as for `twelve`.
`FuzzyUBTask` / `FuzzyLinkTask` subclass `verify.FuzzyBlockEncoding` and add `name`, `registers` (`d` + `row_b..row_l` for UB),
`basis` (labels `code0..`), `target(kind, alpha, beta, order)`, `describe()` (states the fuzzy operator, the frame, "spec.beta =
kappa2" for the link, and the proposer commands via `scripts/m10_round.py`), `import_map -> "n_a"`.

**Diff the laptop needs (coordinator copies to `notes/merge-notes-fuzzy.md`)** — replaces the monkey-patches by hooks:
```
spec.py:     _ENCODING_FACTORIES: dict[str, callable] = {"twelve": lambda: TwelveQubit()}; def register_encoding(name, factory); get_encoding uses it
             TaskSpec.render(): task sentence from enc.task_text(kind, order) when the encoding defines it; n_phys from len(enc.basis.labels) only if basis else 2**n_data
             STRUCTURE_JSON -> enc.structure_json (attribute, default the twelve file)
evaluate.py: _one_verdict: gauss=getattr(enc, "gauss_in_loop", True); max_qubits from enc.peak_qubit_cap(spec) when defined
baselines.py: general_circuit / import_seed dispatch on getattr(enc, "compress_general", None) / getattr(enc, "compress_seeds", None)
round.py:    _certify: skip with status n_a when not getattr(enc, "lean_certifiable", True)
             worker: `python -m su2plaq.compress.evaluate --worker` imports the modules named in env SU2PLAQ_COMPRESS_HOOKS before load_program
base.py:     NOMINAL_ANGLES["fuzzy_ub"] = NOMINAL_ANGLES["fuzzy_link"] = (0.37, 0.61)
```

## 3. Interface (locked tests call exactly these; builder creates stubs raising NotImplementedError first)
```
su2plaq.fuzzy.compress_hook:
  ENCODINGS = ("fuzzy_ub", "fuzzy_link"); UNITS = {"fuzzy_ub": "UB", "fuzzy_link": "UE"}
  class FuzzyUBTask(FuzzyBlockEncoding): name="fuzzy_ub", n_data=8, n_outer=0, registers{"d":[0..7],"row_b":[1,0],"row_r":[3,2],"row_t":[5,4],"row_l":[7,6]}, basis.labels (256), target("UB",a,b)->UB_row(b)
  class FuzzyLinkTask(FuzzyBlockEncoding): name="fuzzy_link", n_data=4, registers{"d":[0,1,2,3]}, basis.labels (16), target("UE",a,b)->UEK_link(a, kappa2=b)
  install() -> None                      # idempotent; §2
  general_circuit(spec) -> QuantumCircuit         # fuzzy_ub: regs 'd'(8)+'anc'(7), 15 qubits; fuzzy_link: 'd'(4)
  general_link_fn(alpha, kappa2) -> QuantumCircuit(4)      ; general_ub_fn(beta) -> QuantumCircuit (8-frame + ancillas)
  ub_frame_to_full(qc8) -> QuantumCircuit        # 8-frame -> registers d(16) [+ancillas], frame qubit i -> ROW_QUBITS[i]
  compose_step(link_fn, ub_fn, alpha, beta, kappa2=None, order=1, with_outer=True) -> QuantumCircuit   # regs d, [o], w; metadata['layers'] (kinds "UE" for link blocks, "UB", "outer"); kappa2 None -> alpha/2
  step_metrics(link_fn, ub_fn, with_outer=True, order=1) -> dict   # logical_metrics of compose_step at nominal (0.37, 0.61, r=1) + "t_estimate"
  circuit_of_entry(entry, spec, root=None) -> QuantumCircuit        # rebuild an archive entry's program at spec's angles (laptop worker)
  entry_fn(entry, spec, root=None) -> callable                      # (alpha, kappa2) or (beta) -> circuit, for compose_step
  best_step(root=None, order=1, with_outer=True) -> (QuantumCircuit, info)   # info={"units": {enc: {"entry": id|"general", "key": [...]}}, "metrics": {...}}
scripts/m10_round.py  <sub> ...  : sub in {seed, round, candidate, oracle, brief, ideation, report, best-step}; installs the hook, forwards argv to the laptop CLIs
                                   (`seed --encoding fuzzy_ub`, `round --encoding fuzzy_ub --round r --evaluate`, `candidate <prog> --encoding fuzzy_ub --kind UB --trial|--full`,
                                    `oracle --encoding fuzzy_link --kind UE ...`, `brief --encoding E --round r --family F`, `ideation --encoding E`, `report --encoding E`,
                                    `best-step` -> results/fuzzy/compressed_step.json)
results/fuzzy/compressed_step.json: {"order":1,"with_outer":true,"units":{"fuzzy_ub":{"entry","key"},"fuzzy_link":{...}},"composed":logical_metrics+t_estimate,"general":same,
                                    "verification":{"err","gauss","n_inputs","seed":20261104,"mode"},"provenance":provenance()}
docs/report-10-fuzzy-compression.md: before/after table per unit (rows general, general+polish, Qiskit L3, best per family, GLOBAL BEST; columns of report_table incl. Lean) + composed-step row (general vs best) + link to compressed_step.json.
```
Allowed write set for this milestone (coordinator enforces): `src/su2plaq/fuzzy/*` (incl. `sitehook/sitecustomize.py`), `scripts/m10_*.py`,
`compress/{specs,programs,archive,briefs,ideation}/fuzzy*`, `compress/attempts/fuzzy*.jsonl`, `compress/discoveries/fuzzy*.md`,
`results/compress/fuzzy*/`, `results/fuzzy/compressed_step.json`, `results/benchmarks/fuzzy-*`, `docs/report-10-*`.

## 4. Steps (times are wall; "skip if" = hard-stop rule)
| Step | Who / does | Done-check | Turns green |
|---|---|---|---|
| 10.0 hook + seeds (≈ 35 min) | builder: `compress_hook.py`, `sitehook/sitecustomize.py`, `scripts/m10_round.py`, `compress/specs/fuzzy-structure.json`; unit test for the sitehook (worker builds a `Builder(spec)` program for `fuzzy_ub`); then coordinator runs `python scripts/m10_round.py seed --encoding fuzzy_ub` and `... --encoding fuzzy_link` | round-0 JSON for both units with ≥ 2 valid entries each (general, general+polish, qiskit_l3); `pytest -n 4 -m "not slow" tests/acceptance/m10` → H1, H2, H3 green | `test_fuzzy_compression.py::test_M10_H1_*`, `::test_M10_H2_*[fuzzy_ub]`, `[fuzzy_link]`, `::test_M10_H3_*` |
| 10.1 ideation (≈ 15 min, parallel with 10.0's seeding) | coordinator: `brief ideation` for both units → ONE proposer, ≤ 4 families total (suggested split: 3 for `fuzzy_ub`, 1 for `fuzzy_link`) → `compress/ideation/fuzzy_ub.md`, `fuzzy_link.md` | files exist, each family one datapath | — |
| 10.2 round 1 (≈ 30 min) | ≤ 4 proposers in parallel (one per family, `taskset` 2 cores each, ≤ 8 cores total); `round --round 1 --evaluate` per unit; tester spot-check: best of each unit re-run `candidate --full` + Aer `Statevector` of the UB best on 15 qubits vs `UB_row` (1e-10) | archive best per unit; commit `compress fuzzy round 1` | `test_M10_G2_*` (fast) |
| 10.3 round 2 (≈ 30 min; skip if < 60 min remain) | as 10.2, parents = family elites | commit | — |
| 10.4 round 3 (skip if < 60 min remain) | as 10.2 (migration round: global best offered) | commit | — |
| 10.5 report (≈ 20 min, always) | `scripts/m10_round.py best-step` (compose + `verify_step_samples` + JSON); `report --encoding fuzzy_ub/fuzzy_link`; `docs/report-10-fuzzy-compression.md`; tester runs the gate | G1 (slow, ≈ 3 min), G3 (slow, ≈ 5 min), R1 green | `test_M10_G1_*[fuzzy_ub]`, `[fuzzy_link]`, `::test_M10_G3_*`, `::test_M10_R1_*` |

Proposer brief additions (coordinator, `~/.claude/agents/proposer.md` unchanged; brief text): use `python scripts/m10_round.py candidate …`
instead of `python -m su2plaq.compress.run_candidate` (the hook); programs import only `su2plaq.compress.{builder,oracle,spec}`;
angles from `spec.alpha` / `spec.beta` (link: `spec.beta` is $\kappa_2$); `fuzzy_link` programs must not `alloc`.

## 5. Acceptance tests (`tests/acceptance/m10/test_fuzzy_compression.py`, 10 ids; all seeds fixed; no dense 16-qubit unitary)
| Id | Checks | Tolerance / why |
|---|---|---|
| H1 | hook idempotent; both specs render with fuzzy wording; oracle target == production target; Builder registers; caps (UB 40) | 1e-12: same code path, no arithmetic; exact otherwise |
| H2[enc] | general unit valid (trial + full, skeleton equal), counts == M9 circuit's; angle error 1e-6 rejected (> 1e-8); sign flip rejected (> 1e-3); dirty ancilla rejected; link ancilla → `max_qubits`; `program_source` works | 1e-10 as F6 (float64 over ≤ 2k gates ≲ 1e-12); 1e-6 angle error gives ~7.5e-7 (measured) |
| H3 | `compose_step` (general units) == `build_step` counts for orders 1, 2 and $r\in\{1,0\}$; layers cover; `verify_step_samples` err and Gauss ≤ 1e-10 (40 inputs); `step_metrics` qubits 55 | 1e-10 (M9 S1 rule; measured 7.5e-15 in M9) |
| G1[enc] (slow) | archive best re-evaluates full from source, key equal, ≤ best seed key, evaluator hash current, Lean status ∈ {None, certified, n_a, not_run} | exact |
| G2[enc] | best's key reproduced by `count_ops` / depth of the lowered rebuilt circuit | exact |
| G3 (slow) | composed best step: `verify_step_samples` ≤ 1e-10; CX and $T_{\rm est}$ ≤ general composed; `compressed_step.json` equals recomputation | 1e-10; counts exact |
| R1 | `report_table` for both units with Lean column; summary.json; report-10 doc with before/after + Lean + composed row | exact |
Collection: `pytest --collect-only -q tests/acceptance/m10` → 10 tests (checked). Before the hook exists every test fails `PENDING:` (api import).

## 6. Do-not-retry
Enumerating physical states for `evaluate()` (plan 300 §5); editing `src/su2plaq/compress/*` on this branch; a `step`-kind fuzzy spec;
ancillas in the link unit (breaks the layered composition verifier); generic QSD of $U_B$ (plan 300 §5); `program_source` on a circuit
with constant-angle `p` gates (fails `_fit_angles`; emit `z/s/sdg/t/tdg` instead); Lean certificates for fuzzy circuits in this session.

## 7. Risks, stop conditions, cost
* Worker sandbox does not pick up `sitecustomize` (e.g. `-S`/`-I` flags added by the laptop): symptom `unknown encoding 'fuzzy_ub'` in
  `build_error`; fallback = patch `evaluate._build_in_subprocess` in the hook to launch `python -c "import su2plaq.fuzzy.compress_hook as H; H.install(); from su2plaq.compress.evaluate import _worker; _worker(*sys.argv[1:])"` (10 lines, same env).
* `run_round` crashes on a fuzzy spec in a code path not covered by the prototype (seed program for `qiskit_l3`, `verify_synthesised`,
  Lean lemma files): fix in the hook; if > 20 min, run rounds with `proposals=[...]` explicitly via `scripts/m10_round.py round --programs …`.
* No valid proposer program after round 1: Report 10 shows the polish-only improvement (already ≥ 7 % CX on both units) — honest result.
* Stop and ask Digonto only if a *valid* unit program composes into a step that fails `verify_step_samples` (that would contradict F3/F6).
* Cost: unit evaluation full mode ≈ 1 s (link) / 2 s (UB) + pygridsynth T measurement ≈ 0.03 s × $N_{\rm rot}$; round wall ≈ 1–3 min per
  unit; composed-step verification ≈ 1–2 min, 0.5 GB; G1/G3 ≈ 10 min total. Memory < 2 GB everywhere.
