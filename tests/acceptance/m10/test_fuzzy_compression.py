"""M10 — compression of the fuzzy one-Trotter-step circuit (prompts/302; METHODS-fuzzy F9).

Two compression units, each run through the laptop loop (`su2plaq.compress.*`, READ ONLY) via the hook
`su2plaq.fuzzy.compress_hook` (ours):
  * `fuzzy_ub`   / kind "UB": exp(+2 i beta square) on the 8 row qubits (frame: qubit 2l = q2^l, 2l+1 = q1^l), 256x256 exact;
  * `fuzzy_link` / kind "UE": the one-link kinetic block U_K(kappa2) U_E(alpha) = exp(-i (alpha/2 K1 + kappa2 K2)), 16x16 exact,
    with spec.beta playing the role of kappa2 (so the three angle pairs are three independent (alpha, kappa2) points).
Validity = the laptop rules (exact 1e-10 after one global phase at the nominal AND the two alternate angle pairs with an
identical skeleton, clean ancillas, allowed gates, peak qubits <= data + 32, wall <= 300 s); the step is scored as the
COMPOSED circuit (`compose_step`) and re-verified with the M9 sampled composition check (`verify_step_samples`, seed 20261104).
Tolerances: 1e-10 (exact angles, METHODS-fuzzy F6), counts exact.  Run notes: G-tests are slow (minutes); nothing here forms a
dense 16-qubit unitary.
"""
from __future__ import annotations

import functools
import json
import pathlib

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from tests.acceptance._api import api

SEED = 20261104
UNITS = (("fuzzy_ub", "UB"), ("fuzzy_link", "UE"))
TOL = 1e-10


@functools.lru_cache(maxsize=None)
def _hook():
    H = api("su2plaq.fuzzy.compress_hook")
    H.install()
    return H


@functools.lru_cache(maxsize=None)
def _spec(enc, kind):
    _hook()
    return api("su2plaq.compress.spec:default_spec")(enc, kind)


def _lm(qc):
    return api("su2plaq.metrics.logical:logical_metrics")(qc)


# ---------------------------------------------------------------------------------------------------- 10.0 hook + seeds
def test_M10_H1_hook_installs_and_specs_render():
    """install() is idempotent; both units are known to the laptop spec / oracle / Builder; the rendered spec names the fuzzy
    operator and conventions; the oracle target equals the M9 production target (1e-12: same code path, no arithmetic)."""
    H = _hook()
    H.install()                                                        # second call: no error, no double patching
    S = api("su2plaq.compress.spec")
    oracle = api("su2plaq.compress.oracle")
    B = api("su2plaq.compress.builder")
    tg = api("su2plaq.fuzzy.targets")
    base = api("su2plaq.encodings.base")
    assert tuple(H.ENCODINGS) == ("fuzzy_ub", "fuzzy_link") and H.UNITS == {"fuzzy_ub": "UB", "fuzzy_link": "UE"}
    for enc, kind in UNITS:
        assert base.NOMINAL_ANGLES[enc] == (0.37, 0.61)
        spec = _spec(enc, kind)
        assert spec.encoding == enc and spec.kind == kind and (spec.alpha, spec.beta) == (0.37, 0.61) and spec.order == 1
        assert tuple(spec.alt_angles) == ((0.91, 0.23), (1.70, 1.00)) and spec.tol_err == 1e-10 and spec.eps == 1e-6
        e = S.get_encoding(enc)
        assert e.name == enc and e.n_outer == 0 and e.basis is not None and len(e.basis.labels) == 2 ** e.n_data
        text = spec.render()
        for needle in ("fuzzy", "2308.05253", "run_candidate", "DISCOVERY", "1e-10"):
            assert needle in text, needle
        V = oracle.target(spec)
        if enc == "fuzzy_ub":
            assert e.n_data == 8 and spec.peak_qubit_cap() == 40 and B.Builder(spec).reg("d") == list(range(8))
            assert V.shape == (256, 256) and np.abs(V - tg.UB_row(0.61)).max() <= 1e-12
            assert "row" in text and e.registers["row_b"] == [1, 0]
        else:
            assert e.n_data == 4 and B.Builder(spec).reg("d") == list(range(4))
            assert V.shape == (16, 16) and np.abs(V - tg.UEK_link(0.37, 0.61)).max() <= 1e-12
            assert "kappa" in text.lower()
        assert np.abs(V.conj().T @ V - np.eye(len(V))).max() <= 1e-10
        assert e.import_map("spinnet15") == "n_a"
    # unit targets at the alternate pairs are what the alternate verdicts use
    assert np.abs(oracle.target(_spec("fuzzy_link", "UE").with_angles(1.70, 1.00)) - tg.UEK_link(1.70, 1.00)).max() <= 1e-12


@pytest.mark.parametrize("enc,kind", UNITS)
def test_M10_H2_general_seed_valid_counts_and_sensitivity(enc, kind):
    """The general unit circuit (from the M9 production circuits, remapped to the unit frame) is valid in trial and full mode
    (three angle pairs, identical skeleton); its counts equal the M9 circuit's; a wrong angle, a wrong sign and a dirty
    ancilla are rejected; the link unit refuses ancillas (plan 302 §3: no ancilla in the kinetic unit so that the composed
    step keeps link-local kinetic layers)."""
    H = _hook()
    spec = _spec(enc, kind)
    E = api("su2plaq.compress.evaluate")
    M = api("su2plaq.compress.metrics")
    C = api("su2plaq.circuits.fuzzy")
    qc = H.general_circuit(spec)
    ref = C.build_UB(spec.beta) if enc == "fuzzy_ub" else C.link_UE(spec.alpha).compose(C.link_UK(spec.beta))
    a, b = _lm(qc), _lm(ref)
    assert (a["cx"], a["t_fixed"], a["n_rot"]) == (b["cx"], b["t_fixed"], b["n_rot"])
    if enc == "fuzzy_ub":
        assert qc.num_qubits == 15 and a["cx"] > 1000 and a["n_rot"] == 16
    else:
        assert qc.num_qubits == 4 and a["n_rot"] == 10
    r = E.evaluate_circuit(qc, spec, mode="trial")
    assert r.valid and r.reason == "ok" and r.verdict.certified and r.verdict.op_norm_error <= TOL and r.verdict.leak_amplitude <= TOL
    alts = [H.general_circuit(spec.with_angles(x, y)) for x, y in spec.alt_angles]
    rf = E.evaluate_circuit(qc, spec, mode="full", alt_circuits=alts)
    assert rf.valid and rf.skeleton_equal and len(rf.verdicts_alt) == 2 and all(v.ok and v.certified for v in rf.verdicts_alt)
    key = M.key(rf.metrics)
    assert key[0] == a["cx"] and key[1] >= a["t_fixed"] and key[3] == qc.num_qubits
    # sensitivity: angle error 1e-6 -> error ~1e-6 >> 1e-10
    wrong = H.general_circuit(spec.with_angles(spec.alpha + 1e-6, spec.beta + 1e-6))
    rw = E.evaluate_circuit(wrong, spec, mode="trial")
    assert not rw.valid and rw.verdict is not None and rw.verdict.op_norm_error > 1e-8
    # sign: the circuit at -beta (UB) / -alpha,-beta (link) is the inverse target -> O(1) error
    rs = E.evaluate_circuit(H.general_circuit(spec.with_angles(-spec.alpha, -spec.beta)), spec, mode="trial")
    assert not rs.valid and rs.verdict.op_norm_error > 1e-3
    # dirty ancilla / ancilla on the link unit
    out = qc.copy()
    anc = QuantumRegister(1, "anc_dirty")
    out.add_register(anc)
    out.cx(0, anc[0])
    rd = E.evaluate_circuit(out, spec, mode="trial")
    assert not rd.valid
    if enc == "fuzzy_link":
        clean = qc.copy()
        clean.add_register(QuantumRegister(1, "anc_clean"))
        rc = E.evaluate_circuit(clean, spec, mode="trial")
        assert not rc.valid and rc.reason == "max_qubits"
    # the program image of the general circuit round-trips through the laptop program generator
    BL = api("su2plaq.compress.baselines")
    src = BL.program_source(H.general_circuit, spec, summary="general")
    assert src.lstrip().startswith('"""SUMMARY:') and "Builder(spec)" in src


def test_M10_H3_compose_step_general_matches_m9_and_verifies():
    """compose_step with the general units reproduces the M9 step (same CX / T_fixed / N_rot as build_step with outer links,
    orders 1 and 2), carries layer metadata covering every instruction, and passes verify_step_samples at 1e-10 (err and
    Gauss; seed 20261104, 32 random + 8 physical inputs) at nominal r = 1 and at r = 0."""
    H = _hook()
    C = api("su2plaq.circuits.fuzzy")
    vs = api("su2plaq.fuzzy.verify:verify_step_samples")
    for order in (1, 2):
        for kappa2 in (None, 0.0):
            qc = H.compose_step(H.general_link_fn, H.general_ub_fn, 0.37, 0.61, kappa2=kappa2, order=order, with_outer=True)
            ref = C.build_step(0.37, 0.61, kappa2=kappa2, order=order, with_outer=True)
            a, b = _lm(qc), _lm(ref)
            assert (a["cx"], a["t_fixed"], a["n_rot"]) == (b["cx"], b["t_fixed"], b["n_rot"]), (order, kappa2)
            assert [r.name for r in qc.qregs][:2] == ["d", "o"] and qc.num_qubits == 48 + 7
            layers = qc.metadata["layers"]
            assert layers[0][1] == 0 and layers[-1][2] == len(qc.data) and all(layers[i][2] == layers[i + 1][1] for i in range(len(layers) - 1))
            k2 = 0.5 * 0.37 if kappa2 is None else kappa2
            v = vs(qc, 0.37, 0.61, k2, order, n_random=32, n_phys=8, seed=SEED)
            assert v["err"] <= TOL and v["gauss"] <= TOL and v["n_inputs"] == 40 and v["mode"] == "layers", (order, kappa2, v)
    m = H.step_metrics(H.general_link_fn, H.general_ub_fn, with_outer=True)
    assert m["cx"] == _lm(C.build_step(0.37, 0.61, order=1, with_outer=True))["cx"] and m["qubits"] == 55 and "t_estimate" in m


# ---------------------------------------------------------------------------------------------------- gate (10.2-10.5)
@pytest.mark.slow
@pytest.mark.parametrize("enc,kind", UNITS)
def test_M10_G1_archive_best_valid_and_not_worse_than_seed(enc, kind, root):
    """After the loop: the global best of each unit archive re-evaluates from its program source as valid (full mode: three
    angle pairs, identical skeleton) with the recorded key; key <= the best round-0 (seed) key; evaluator hash current."""
    _hook()
    spec = _spec(enc, kind)
    A = api("su2plaq.compress.archive"); E = api("su2plaq.compress.evaluate"); M = api("su2plaq.compress.metrics")
    arch = A.Archive.load(enc, root=root, n_alt=len(spec.alt_angles), strict=True)
    best = arch.best()
    assert best is not None and best.valid and arch.rejected == []
    r = E.evaluate_program(str(root / best.program_path), spec, mode="full")
    assert r.valid and r.skeleton_equal and r.verdict.op_norm_error <= TOL and all(v.ok for v in r.verdicts_alt)
    assert tuple(M.key(r.metrics)) == tuple(best.key)
    seeds = [e for e in arch.entries() if e.round == 0 and e.valid]
    assert seeds and tuple(best.key) <= min(tuple(e.key) for e in seeds)
    assert best.evaluator_sha256 == api("su2plaq.compress.provenance:code_hash")()
    assert best.lean is None or best.lean.get("status") in ("certified", "n_a", "not_run")


@pytest.mark.parametrize("enc,kind", UNITS)
def test_M10_G2_best_counts_match_qiskit_count_ops(enc, kind, root):
    """The archived key of the best entry is reproduced by Qiskit count_ops / depth on the lowered circuit rebuilt from source."""
    H = _hook()
    spec = _spec(enc, kind)
    A = api("su2plaq.compress.archive"); M = api("su2plaq.compress.metrics")
    lower = api("su2plaq.metrics.logical:lower")
    arch = A.Archive.load(enc, root=root, n_alt=len(spec.alt_angles), strict=True)
    best = arch.best()
    assert best is not None
    qc = H.circuit_of_entry(best, spec, root=root)
    low = lower(qc)
    m = M.metrics(qc, spec, measured=False)
    assert m["cx"] == low.count_ops().get("cx", 0) == best.key[0] and m["qubits"] == qc.num_qubits == best.key[3]
    assert m["t_fixed"] == best.metrics_raw["t_fixed"] and m["n_rot"] == best.metrics_raw["n_rot"]


@pytest.mark.slow
def test_M10_G3_composed_step_from_best_verifies_and_is_recorded(root):
    """The step composed from the best unit programs (order 1, outer links, nominal angles, r = 1) passes the M9 sampled
    composition check at 1e-10 (err and Gauss), has CX and T_est(1e-6) <= the general composed step, and
    results/fuzzy/compressed_step.json records exactly these numbers with provenance."""
    H = _hook()
    vs = api("su2plaq.fuzzy.verify:verify_step_samples")
    qc, info = H.best_step(root=root, order=1, with_outer=True)
    v = vs(qc, 0.37, 0.61, 0.5 * 0.37, 1, n_random=32, n_phys=8, seed=SEED)
    assert v["err"] <= TOL and v["gauss"] <= TOL and v["mode"] == "layers"
    m = _lm(qc)
    g = H.step_metrics(H.general_link_fn, H.general_ub_fn, with_outer=True)
    assert m["cx"] <= g["cx"] and m["t_fixed"] + 3 * m["n_rot"] * np.log2(1e6) <= g["t_fixed"] + 3 * g["n_rot"] * np.log2(1e6) + 1e-9
    f = root / "results" / "fuzzy" / "compressed_step.json"
    assert f.exists()
    d = json.loads(f.read_text())
    for k in ("order", "with_outer", "units", "composed", "general", "verification", "provenance"):
        assert k in d, k
    assert d["order"] == 1 and d["with_outer"] is True and set(d["units"]) == {"fuzzy_ub", "fuzzy_link"}
    for enc in ("fuzzy_ub", "fuzzy_link"):
        assert d["units"][enc]["entry"] == info["units"][enc]["entry"] and list(d["units"][enc]["key"]) == list(info["units"][enc]["key"])
    for k in ("cx", "t_fixed", "n_rot", "depth", "qubits"):
        assert d["composed"][k] == m[k] and d["general"][k] == g[k]
    assert d["verification"]["err"] <= TOL and d["verification"]["gauss"] <= TOL and d["verification"]["seed"] == SEED
    assert "git_commit" in d["provenance"]


def test_M10_R1_reports_rendered_with_lean_column(root):
    """report_table renders for both units (Lean column present, general and GLOBAL BEST rows, summary.json written) and
    docs/report-10-fuzzy-compression.md has the before/after table with a Lean column and the composed-step row."""
    _hook()
    rt = api("su2plaq.compress.report:report_table")
    for enc, kind in UNITS:
        text = rt(enc, kind, root=root)
        for col in ("qubits", "CX", "T_fixed", "N_rot", "T(1e-6)", "depth", "verdict", "Lean"):
            assert col in text
        assert "general" in text and "GLOBAL BEST" in text
        assert (root / "results" / "compress" / enc / "summary.json").exists()
    doc = root / "docs" / "report-10-fuzzy-compression.md"
    assert doc.exists()
    t = doc.read_text()
    assert "Lean" in t and "fuzzy_ub" in t and "fuzzy_link" in t and "composed" in t.lower() and "compressed_step.json" in t
    assert "before" in t.lower() and "after" in t.lower()
