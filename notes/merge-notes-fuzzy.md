# Merge notes — branch m9-fuzzy (fuzzy encoding, 48-core machine)

Base: master 9b5443d. Numbers: prompts/reports 300+.

## Environment / activation
```
source ~/venvs/coding/bin/activate     # uv-made venv, CPython 3.12.14 (no conda on this host)
source ~/.elan/env; export PATH=$HOME/tools/gitenv/bin:$PATH   # git 2.56 needed by lake (system git 2.25 lacks --filter)
cd ~/Projects/su2qc-fuzzy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
```
- env/requirements-coding.txt has 139 `pkg @ file:///home/conda/...` lines (conda-built); installed those unpinned from PyPI. Pinned core versions verified: qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0, numpy 2.5.4, scipy 1.18.1.
- Package installed editable (`uv pip install --no-deps -e .`).
- `lake build -j 24` is not accepted by this lake (unknown option -j); used `LEAN_NUM_THREADS=24 lake build`.

## Shared-file appends (to merge by hand)
- `lean/Su2Plaq.lean`: appended `import Su2Plaq.Fuzzy.Counts` and `import Su2Plaq.Fuzzy.Link`.
- `tests/acceptance/LOCK.json`: m9 added via `python tools/lock.py m9` (acceptance-v8); then hashes of m9/test_fuzzy_circuits.py and m9/test_fuzzy_observables.py updated BY HAND (tools/lock.py refuses re-lock) after Digonto approved prompts/301 (acceptance-v9; v10 = same content, JSON indent restored to 1). Tags acceptance-v8..v10 exist on this branch only — they will collide with laptop/desktop acceptance-vN numbering: rename on merge (e.g. acceptance-fuzzy-v8..v10).
- Lean `Su2Plaq/Fuzzy/Link.lean` takes ~6 min to build (kernel decide on 16x16 Gaussian-integer matrices).

## Laptop-owned files that would need changes (diffs)
(none yet)

## Other
- notes/STATUS.md on this branch is the fuzzy session's; the laptop's copy at branch point is preserved as notes/STATUS-laptop-at-branch-point.md (drop on merge).
- Repo-local git identity set to master's author (pichka_commander <mdhabibeislam.digonto@gmail.com>); host had no global git identity.
- Digonto's uploaded `fuzzy-hamiltonian.pdf` saved as refs/fuzzy/fuzzy-hamiltonian-digonto.pdf; being checked against the paper/plan before the planner run.

## M10 laptop diff (from prompts/302 §2, verbatim)
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

- Suggested laptop diff (cliffordt.synthesize should carry qc.metadata['layers'] remapped to new instruction ranges; would cut T1[step] from 27 min to seconds) — see builder note in STATUS/Report 9.

## Tags on this branch (rename on merge if they collide)
- acceptance-v8 (m9 lock), v9 (prompts/301 test fixes, approved by Digonto), v10 (LOCK.json indent restored), v11 (m10 lock).
- milestone-9 (M9 gate: tests 300/301, audit 300), milestone-10 (M10 gate: tests 302/303, audit 301).
## Open items for the laptop
- Audit 301 A1 (hook records per-unit Gauss residual 0.0 when not computed -> 'not checked'), A2 (random-angle validity check in G1).
- Suggested laptop diff: cliffordt.synthesize should carry qc.metadata['layers'] (T1[step] 27 min -> seconds).
- results/compress/twelve/summary.json is rewritten by m2 tests as a side effect (left untracked here).
