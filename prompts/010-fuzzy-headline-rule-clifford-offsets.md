# 010 — The fuzzy headline rule: constant terms that are multiples of $\pi/2$ in rotation angles (decision, code spec, tests)

- Date: 2026-11-16. Git commit at planning time: `8f61336` (branch `merge-desktop-tracks`; other agents' step-B7 files uncommitted in the tree).
- Trigger: open question of `prompts/008` §6, tester finding F2 in `reports/tests/419-consolidation-008-b6.md`, STATUS "RESTART HERE" item 4 ("fuzzy headline rule (§6 silent; fuzzy_ub best has rho=1 from pi/2-multiple rz offsets)").
- Research note with every number quoted here: `reports/research/007-fuzzy-headline-rule-clifford-offsets.md`. Methods: `docs/METHODS.md` §12.4 (amended in this run).
- Plan in force after this file: `prompts/008` stays in force for the consolidation; **this file settles its §6 for the fuzzy units and adds steps H.1–H.4**, which belong to milestone M11 (`prompts/009`). Locked tests: `tests/acceptance/m11/test_headline_rule.py` (4 tests, new). **No existing locked test is changed** (checked: m2c G3/G4, m10 G1–G3; research 007 §4).

Words used (each once). *Headline* = the valid archive entry with the smallest *robust key* $(\mathrm{CX},\sum_{i=1}^{20}T_i,\rho,\sum_i\mathrm{depth}_i,\mathrm{qubits})$ over the 20 locked angle pairs; *archive key* = $(\mathrm{CX},T,\mathrm{depth_{CT}},\mathrm{qubits})$ at the nominal pair; *$\rho$* = 0 for an angle-linear program, else 1; *Clifford gate* = a gate that needs no T gate; *affine* = linear plus a constant; *offset class* (our label) = the classification of §3.

## 1. Diagnosis

The generic test of `compress/robust.py` sets $\rho=0$ only if every rotation angle is $c_\alpha\alpha+c_\beta\beta$. In the `fuzzy_ub` archive 11 of 41 valid entries (rounds 9–13, the archive best `r12-F1-012` among them) write rotations as $R_z(\theta-k\pi/2)$ followed by $S^k$, $k\in\{2,3,6\}$; their angles are affine with a constant, so $\rho=1$. Measured (research 007 §1): every constant is a multiple of $\pi/2$ on a plain `rz` (affine residual $\le1.2\times10^{-14}$); the per-pair T counts are unchanged (identical lists for `r12-F1-012` and `r10-F1-010`); the offsets were chosen at the nominal $\beta=0.61$ to shorten `depth_CT` there (1546 → 1517), and that gain vanishes over the 20 pairs ($\sum$ depth 30 908 against 30 902). `prompts/008` and research 005 assumed "0 order flips" for fuzzy_ub; that was true of the 11-entry, T-only measurement of 2026-11-10 and is obsolete.

Identity used: with Qiskit's $R_z(\varphi)=\mathrm{diag}(e^{-i\varphi/2},e^{i\varphi/2})$ and $S=\mathrm{diag}(1,i)$,
$$R_z\!\big(\theta+k\tfrac\pi2\big)=e^{-ik\pi/4}\,R_z(\theta)\,S^k ,\qquad p\!\big(\theta+k\tfrac\pi2\big)=p(\theta)\,S^k ,$$
a Clifford factor. For singly controlled rotations only multiples of $\pi$ are Clifford ($\mathrm{cp}(\pi)=CZ$, $\mathrm{crz}(\pi)=S^\dagger_{\rm control}\,CZ$; $\mathrm{cp}(\pi/2)$ and $\mathrm{crz}(\pi/2)$ are not).

## 2. Decision

**Keep the rule.** $\rho=0$ only for angles without a constant term. **Add an informative classification of the constants** (no effect on any key). **Quote the headline, not the archive best, for the fuzzy units and for the composed fuzzy step.**

| Question | Answer |
|---|---|
| fuzzy_ub headline | `r10-F1-010`, robust key $(83,12688,0,30902,10)$, $\bar T=634.4$, nominal $T=638$, archive key $(83,638,1546,10)$ |
| the same under the alternative rule (Clifford offsets counted as linear) | yes: the same entry and key (first three entries tie at depth sum 30 902; `r12-F1-012` has 30 908) |
| fuzzy_link headline | `r02-F2-001` = archive best, $(12,12576,0,23373,4)$, $\bar T=628.8$ |
| order inversions robust against archive ranking, 41 fuzzy_ub entries | 34 (kept rule); it would be 30 with the alternative; never 0 |
| effect on the Lean angle-linearity requirement (METHODS §11.2) | none: exporters keep answering `non_linear_angle` for a constant term; no exporter changes; the headline `r10-F1-010` has no constants |
| locked tests | none changes |

Why (research 007 §2, §3): (1) the choice cannot change a reported number — both rules give the same headline; (2) "angle-linear" keeps one meaning for all five encodings, namely "the Lean exporter takes the program as written" (the registered tests of twelve, spinnet and LSH are their exporters, and they reject a constant term); (3) extending the rule needs a gate-by-gate table of which constants are Clifford, and a wrong table would silently reward a hidden T gate; (4) the one defect of keeping — a T-free program labelled "not angle-linear" — is removed by the classification below.

## 3. Method (spec of the classification)

For circuits $q_1,\dots,q_{21}$ of one program (equal skeletons; the 20 pairs of `ANGLE_SET` first, the nominal pair last) and each numeric gate parameter $\theta_p$ (order of `rotation_angles`), fit by least squares on the first 20 pairs
$$\theta_p(\alpha,\beta)\approx c_{\alpha,p}\alpha+c_{\beta,p}\beta\quad(\text{linear}),\qquad\theta_p(\alpha,\beta)\approx c_{\alpha,p}\alpha+c_{\beta,p}\beta+c_{0,p}\quad(\text{affine}),$$
and take the largest absolute residuals $r_{\rm lin}$, $r_{\rm aff}$ over all 21 pairs and parameters. With $\tau=$ `LINEAR_TOL` $=10^{-9}$ and the table $u(\text{gate})$: $\pi/2$ for `rz`, `p`, `rx`, `ry`; $\pi$ for `crz`, `crx`, `cry`, `cp`; undefined otherwise:

| class | condition |
|---|---|
| `linear` | $r_{\rm lin}\le\tau$ (exactly the existing $\rho=0$ test) |
| `non_affine` | $r_{\rm lin}>\tau$ and $r_{\rm aff}>\tau$ |
| `clifford_offset` | $r_{\rm lin}>\tau$, $r_{\rm aff}\le\tau$, and for every parameter with $|c_{0,p}|>\tau$: $u$ is defined for its gate and $|c_{0,p}-u\,\mathrm{round}(c_{0,p}/u)|\le\tau$ |
| `non_clifford_offset` | $r_{\rm lin}>\tau$, $r_{\rm aff}\le\tau$, otherwise |

`offset_units[p]` = $\mathrm{round}(c_{0,p}/(\pi/2))$ if $|c_{0,p}-\tfrac\pi2\mathrm{round}(\cdot)|\le\tau$, else `None`. A circuit without parameters is `linear`. Tolerance $10^{-9}$: the locked value of the linearity test (prompts/104 §11 E3); measured residuals of real programs $\le1.2\times10^{-14}$, and a hidden $\pi/4$ is $0.79$ away from the nearest multiple.

## 4. Interface and exact code changes (no hashed file is touched)

### 4.1 `src/su2plaq/compress/robust.py` (not in a hash list; stays so)
```python
OFFSET_TOL = 1e-9
CLIFFORD_OFFSET_UNIT = {"rz": pi/2, "p": pi/2, "rx": pi/2, "ry": pi/2, "crz": pi, "crx": pi, "cry": pi, "cp": pi}
def angle_offsets(circuits, pairs) -> dict
    # {"class": "linear" | "clifford_offset" | "non_clifford_offset" | "non_affine", "affine_residual": float,
    #  "offsets": [c_0 per gate parameter, rad], "offset_units": [int | None per gate parameter], "gates": [gate name per parameter]}
```
- `generic_angle_linear` is **unchanged** (same return values for every input; the tester compares old and new on the toys of reports/tests/419 check 3).
- `robust_metrics(...)`: when the skeleton is equal, call `angle_offsets([*circuits, nominal], [*ANGLE_SET, (spec.alpha, spec.beta)])` for every encoding (also those with a registered `angle_linear` hook) and add `"offset_class"` and `"offset_units"` to the returned dict; `None` for both when the skeleton changes. `"angle_linear"`, `"export_status"` and `"robust_key"` are computed exactly as now.
- `headline(...)`: every ranking row gains `"offset_class": rec.get("offset_class")`. For an encoding **without** a registered `headline` hook (twelve, fuzzy_ub, fuzzy_link) a cached record without the key `"offset_class"` counts as missing (recomputed when `compute=True`; `None` returned when `compute=False`). For an encoding **with** a hook (spinnet, rishon; later lsh) the track's own cache is read as it is, the value may be `None`, and nothing in those tracks changes.
- `report_rows`: the angle-linear cell is `"yes"` if `angle_linear`, `"no (Clifford offsets)"` if `offset_class == "clifford_offset"`, else `"no"`. `headline_note` gains one sentence when a ranked entry has that class: "Entries marked 'no (Clifford offsets)' differ from an angle-linear program only by $R_z(\theta+k\pi/2)=R_z(\theta)S^k$; this costs no T gate and is not rewarded."
- `HEADLINE_RULE_SECTION`: unchanged (it already tells proposers to put multiples of $\pi/2$ into separate `s`/`sdg`/`z` gates).
- Module docstring: replace the sentence "Nothing in §6 prescribes another rho for the fuzzy units, so they use the generic fit." by a reference to this plan.

### 4.2 Headline caches of the fuzzy units
`robust.headline("fuzzy_ub", "UB")` and `robust.headline("fuzzy_link", "UE")` with `compute=True` write `results/compress/<enc>/robust.json` and the `headline` block of `summary.json` (this is what prompts/008 Phase C does for M2C-G3; after H.1 the records carry the offset class). Expected: ids and keys of §2.

### 4.3 `src/su2plaq/fuzzy/headline_step.py` (new; **not** added to `registry._FUZZY_FILES`; `fuzzy/compress_hook.py` is hashed and is not edited)
```python
def headline_step(root=None, order=1, with_outer=True) -> tuple[QuantumCircuit, dict]
    # compose_step(entry_fn(link headline), entry_fn(U_B headline), 0.37, 0.61, None, order, with_outer) with the entries
    # robust.headline(enc, kind, root=root, compute=False)["id"]; FileNotFoundError if a headline is not cached.
    # info = {"units": {enc: {"entry", "key", "robust_key", "t_mean"}}, "metrics": compress_hook._metrics_dict(qc)}
def write_headline_step(root=None, out=None, order=1, with_outer=True) -> dict
    # verify_step_samples(qc, 0.37, 0.61, 0.185, order, n_random=32, n_phys=8, seed=20261104); writes results/fuzzy/compressed_step_headline.json
```
File keys: `rule` = "headline", `order`, `with_outer`, `units`, `composed` (metrics with outer rows), `inner` = {`cx`,`n_rot`,`t_fixed`,`depth`,`qubits` of the step with `with_outer=False`, `t_mean` = $\bar T_{U_B}+4\bar T_{\rm link}$, `t_nominal` = nominal sum}, `general`, `verification` {`err`,`gauss`,`n_inputs`,`seed`,`mode`,`leak`}, `provenance`. Command: `python scripts/m10_round.py headline-step` (new sub-command beside `best-step`). `best_step`, `write_compressed_step` and `results/fuzzy/compressed_step.json` (locked by M10-G3 to the archive-best units) are left as they are.

Expected numbers (prototype, research 007 §3): err $1.2\times10^{-14}$, Gauss $5.9\times10^{-15}$; with outer rows 227 CX, 129 rotations, 72 fixed T, depth 151, 50 qubits; inner 131 CX, 49 rotations, 72 fixed T, 18 qubits, $\bar T=3149.6$, nominal 3214 (general inner step: 1862 CX, 56 rotations, 1826 fixed T, $T(10^{-6})=5398$).

## 5. Acceptance tests added (none changed) and tolerances

| `tests/acceptance/m11/test_headline_rule.py` :: id | What | Tolerance | Justification |
|---|---|---|---|
| `test_M11_H1_generic_rho_is_homogeneous_and_offsets_are_classified` | seven synthetic circuit families: `generic_angle_linear` unchanged (constant $\pi/2$, $-\pi$, $\pi/4$, product $\alpha\beta$ ⇒ not linear; $+10^{-10}$ ⇒ linear); `angle_offsets` classes, units and offsets, including `crz` with $+\pi$ (Clifford) and with $+\pi/2$ (not) | angles $10^{-9}$; classes and units exact | `LINEAR_TOL`; the nearest wrong class is 0.79 rad away |
| `test_M11_H2_fuzzy_headline_does_not_depend_on_the_offset_rule[fuzzy_ub-UB]`, `[fuzzy_link-UE]` (slow) | on the real archives: headline = minimum of the ranking; `angle_linear` ⇔ $\rho=0$ ⇔ class `linear`; every other entry is `clifford_offset`; the alternative rule gives the same headline; headline and archive best have the same CX and $\sum T$ | exact | statements of §2; validated on the tester's cache copy (research 007 §1.5) |
| `test_M11_H3_fuzzy_step_composed_from_the_headline_units` (slow) | `headline_step` uses the two headlines; M9 sampled composition check; CX = $U_B$ + 12 links (with outer) and + 4 links (inner) $\le$ general; file content | err, Gauss $\le10^{-10}$ (the call of the locked M10-G3; METHODS-fuzzy F6); counts exact; $\bar T$ to $10^{-9}$ | measured $1.2\times10^{-14}$, $5.9\times10^{-15}$ |

H2 and H3 read the cached headlines with `compute=False` (they write nothing into tracked files) and are `PENDING` until step H.2. The ids of §2 are **not** typed into the tests: they are properties of an archive that the Phase C replay re-creates; the tests check the rule, the plan states the expected ids.

## 6. Steps (part of milestone M11; they touch no hashed file and can run inside the consolidation window)

| Step | Builds | Done-check | Acceptance ids |
|---|---|---|---|
| H.1 | §4.1 + unit tests (`tests/unit/test_robust_unit.py`: the classes, the unchanged `generic_angle_linear` on the toys of report 419, the report cell, a cached record without the class is recomputed) | `tools/pytest-safe -n 4 tests/unit -q` green; `python -I` check that `provenance.evaluator_files` of no encoding lists `compress/robust.py`; all six hashes of report 419 unchanged by this step | `test_headline_rule.py::test_M11_H1_generic_rho_is_homogeneous_and_offsets_are_classified` |
| H.2 | §4.2 (after prompts/008 Phase C has replayed the fuzzy archives; before that only on a scratch copy) | tester: headline ids and keys of §2; 11 entries `clifford_offset`, 30 `linear` (fuzzy_ub); 4 `linear` (fuzzy_link); T-first pick `r13-F3-013`, $(89,10400,1,25084,10)$, $\bar T=520.0$ | `::test_M11_H2_…[fuzzy_ub-UB]`, `[fuzzy_link-UE]` |
| H.3 | §4.3, `results/fuzzy/compressed_step_headline.json` on a clean commit | numbers of §4.3; `results/fuzzy/compressed_step.json` byte-identical; `M10_G3` still green | `::test_M11_H3_fuzzy_step_composed_from_the_headline_units` |
| H.4 | Report 10 update (coordinator, from the files): (a) Table 3.1 gains the rows GLOBAL BEST `r12-F1-012` (angle-linear: "no (Clifford offsets)") and HEADLINE `r10-F1-010`; (b) the composed step is quoted from the headline units (depth 151 instead of 150; all other counts equal); (c) one paragraph: what the offsets are, that they cost no T, that the nominal depth gain does not survive the 20-pair average, 34 order inversions; (d) the T-first alternative `r13-F3-013` (inner step 137 CX, $\bar T=3035.2$); (e) Lean: `n_a` (no fuzzy exporter); (f) the rule is a default not reviewed by Digonto | auditor reads the paragraph against research 007 | — |

## 7. Do-not-retry list
- Making $\rho$ depend on the offset class (rule E of research 007): changes no headline and splits the meaning of "angle-linear" between encodings.
- Rewriting programs or exporter input to absorb the offsets (rule N): touches hashed exporter code and judges a circuit that was not submitted.
- Editing `fuzzy/compress_hook.py::best_step` to use the headline (hashed file; breaks the locked M10-G3 file pin).
- Treating a constant on a controlled rotation as Clifford when it is a multiple of $\pi/2$ only (hidden controlled-$S$).
- Re-opening the fuzzy loop to "fix" the 11 entries: the loop is closed (Digonto 2026-11-14) and the headline is already an entry without constants.

## 8. Risks, stop conditions, defaults
- If, after the Phase C replay, the fuzzy_ub headline is not `r10-F1-010` or H2 finds an entry of class `non_clifford_offset` / `non_affine`: do not adjust anything; send the entry to the tester (independent affine fit) and return to the planner.
- If `M2C_G4` fails for `r10-F1-010` at the unseen angle pairs: that is a finding about the entry (never evaluated there before); stop, tester, planner.
- Stop and ask Digonto if an agent believes the kept rule is wrong for a reason not listed in research 007 §2.
- Expected cost: H.1 one builder call; `angle_offsets` adds $<0.1$ s per entry; H.2 about 5–10 min for 41 entries (builds at 21 pairs, measured 0.6–80 s per entry, most 1–2 s, plus the T tables); H.3 about 2–3 min (prototype 71 s per composed verification); memory $<1$ GB.
- **Defaults, not reviewed by Digonto:** (1) keep the rule, classify instead of reward; (2) the table of Clifford offset units (§3), including $\pi$ for singly controlled rotations; (3) the report wording "no (Clifford offsets)"; (4) a separate headline step file instead of changing the locked `compressed_step.json`; (5) the composed fuzzy step of the final report uses the headline units; (6) the classification is computed for every encoding that goes through `robust_metrics` (twelve, fuzzy units), is informative everywhere, and coincides with $\rho$ only where the generic test decides $\rho$ (the fuzzy units; twelve, spinnet, rishon and LSH keep their registered tests).
