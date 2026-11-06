"""Light checks of scripts/m9_results.py helpers and of the written results/fuzzy files (written by the script, not by this test)."""
import importlib.util
import json
import pathlib

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("m9_results", ROOT / "scripts" / "m9_results.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_isolated_plaquette_basis_is_the_gauss_kernel(mod):
    from su2plaq.fuzzy import gauss as gz

    vecs, w = mod.isolated_plaquette_basis()
    assert vecs.shape == (gz.isolated_plaquette_count(), 65536) == (50, 65536)
    assert np.abs(vecs.conj() @ vecs.T - np.eye(50)).max() <= 1e-12
    assert mod.gauss_residual_dense(vecs) <= 1e-12
    assert w[w > 1e-9].min() > 1.0                         # kernel is separated from the rest of the spectrum


def test_gauss_residual_detects_a_non_singlet(mod):
    v = np.zeros((1, 65536), dtype=complex)
    v[0, 1] = 1.0                                          # a computational basis state is not a Gauss singlet
    assert mod.gauss_residual_dense(v) > 0.1


def test_kinetic_layer_check_accepts_exact_layer_and_rejects_wrong_target(mod):
    from su2plaq.circuits import fuzzy as C
    from su2plaq.fuzzy import targets as tg

    r = mod._kinetic_layer_check(C.build_UE(0.37), tg.UE_link(0.37))
    assert r["n_blocks"] == 4 and r["max_block_error"] <= 1e-12
    assert mod._kinetic_layer_check(C.build_UE(0.37), tg.UE_link(0.5))["max_block_error"] > 1e-3


def test_kinetic_layer_check_rejects_gate_across_links(mod):
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(16)
    qc.cx(3, 4)
    with pytest.raises(ValueError):
        mod._kinetic_layer_check(qc, np.eye(16, dtype=complex))


def test_phase_dist_ignores_global_phase(mod):
    U = np.diag([1.0, 1j, -1.0, 1.0]).astype(complex)
    assert mod._phase_dist(np.exp(0.7j) * U, U) <= 1e-14
    assert mod._phase_dist(np.diag([1, 1, 1, 1]).astype(complex), U) > 0.1


def test_step_verdict_convention(mod):
    d = mod._step_verdict({"err": 3e-15, "leak": 1e-15, "gauss": 2e-14, "mode": "layers", "n_inputs": 40}, 1e-10, 1.0, "m")
    assert d["ok"] and d["block_error"] <= d["op_norm_error"] and d["max_leak"] == pytest.approx(1e-30)
    bad = mod._step_verdict({"err": 1e-3, "leak": 0.0, "gauss": 0.0, "mode": "layers", "n_inputs": 1}, 1e-10, 1.0, "m")
    assert not bad["ok"]


def test_lean_summary_is_a_static_scan(mod):
    s = mod.lean_summary()
    assert set(s["files"]) >= {"Counts.lean", "Link.lean"} and all(v["sorry"] == 0 for v in s["files"].values())


def test_script_takes_one_provenance_snapshot_before_writing():
    src = (ROOT / "scripts" / "m9_results.py").read_text()
    assert src.index("snap = provenance(SEEDS)") < src.index("out.mkdir(parents=True") < src.index("save_result(out")
    assert src.count("provenance_snapshot=snap") == src.count("save_result(out")


@pytest.mark.parametrize("kind", ["UE", "UK", "UB", "step"])
def test_results_files_are_consistent_if_present(kind):
    p = ROOT / "results" / "fuzzy" / f"{kind}.json"
    if not p.exists():
        pytest.skip("run scripts/m9_results.py first")
    d = json.loads(p.read_text())
    v = d["verification"]
    assert v["ok"] and abs(v["op_norm_error"] - (v["block_error"] + v["leak_amplitude"])) <= 1e-12 + v.get("dropped_total", 0.0)
    assert d["extra"]["verification_scope"] in ("full_unitary_link", "full_unitary_row_block", "blocks_certified_composition_sampled")
    for row in d["metrics"]["t_table"]:
        s = row["synth"]
        assert s["error_measured_sum"] <= s["error_bound_sum"] + 1e-15
        assert s["verdict"]["ok"] and s["verdict"]["tolerances"]["tol_err"] > s["error_bound_sum"]


def test_outer_row_totals_if_present():
    p = ROOT / "results" / "fuzzy" / "outer_row.json"
    if not p.exists():
        pytest.skip("run scripts/m9_results.py first")
    d = json.loads(p.read_text())
    assert d["consistency_with_build_step_with_outer"]["matches_totals"]
    for key in ("cx", "n_rot", "t_fixed"):
        assert d["totals"][key] == 8 * (d["per_link"]["UE"][key] + d["per_link"]["UK"][key])


def test_synthesize_layered_has_the_gate_content_of_synthesize(mod):
    from su2plaq.circuits import fuzzy as C
    from su2plaq.metrics.cliffordt import synthesize

    qc = C.build_step(0.37, 0.61, 0.185, 1)
    s, info = mod.synthesize_layered(qc, 1e-4)
    s0, info0 = synthesize(qc, 1e-4)
    assert s.count_ops() == s0.count_ops() and info["n_rot"] == info0["n_rot"] and info["t_rot"] == info0["t_rot"]
    lay = s.metadata["layers"]
    assert [k for k, _, _ in lay] == ["UE", "UK", "UB"] and lay[0][1] == 0 and lay[-1][2] == len(s.data)
    with pytest.raises(ValueError):
        mod.synthesize_layered(C.build_UB(0.61), 1e-4)
