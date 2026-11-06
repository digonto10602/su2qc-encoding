"""M9-R1 — results files for the fuzzy general circuits exist, validate and render (prompts/300 step 9.7; METHODS §8)."""
import json

import pytest

from tests.acceptance.m9._fz import api


@pytest.mark.parametrize("kind", ["UE", "UK", "UB", "step"])
def test_M9_R1_results_files(kind, root):
    """results/fuzzy/<kind>.json: RESULT_KEYS schema, encoding 'fuzzy', nominal params (alpha 0.37, beta 0.61, kappa2 0.185, r 1),
    verification ok (op-norm <= 1e-10, leak amplitude <= 1e-10, weights <= 1e-20), logical metrics, 4-row T(eps) table,
    provenance commit; UB/step have cx > 0 and n_rot <= 4000 (plan cap); render() produces the table."""
    p = root / "results" / "fuzzy" / f"{kind}.json"
    assert p.exists(), f"missing {p}"
    d = json.loads(p.read_text())
    RESULT_KEYS = api("su2plaq.results.store:RESULT_KEYS")
    assert list(d.keys()) == list(RESULT_KEYS)
    assert d["encoding"] == "fuzzy" and d["kind"] == kind and d["circuit_id"] == kind
    pr = d["params"]
    assert pr.get("alpha") in (0.37, None) and pr.get("beta") in (0.61, None) and pr.get("r") in (1.0, None)
    if kind in ("UK", "step"):
        assert abs(pr["kappa2"] - 0.185) <= 1e-15
    v = d["verification"]
    assert v["ok"] and v["op_norm_error"] <= 1e-10 and v["leak_amplitude"] <= 1e-10 and v["max_leak"] <= 1e-20
    assert v["block_error"] <= v["op_norm_error"] and v["dirty_ancilla"] <= 1e-20
    assert d["metrics"]["logical"]["cx"] >= 0 and len(d["metrics"]["t_table"]) == 4
    assert d["metrics"]["logical"]["n_rot"] <= 4000
    assert len(d["provenance"]["git_commit"]) >= 7 and "qiskit" in d["provenance"]["versions"]
    if kind in ("UB", "step"):
        assert d["metrics"]["logical"]["cx"] > 0
        assert d["extra"]["verification_scope"] in ("full_unitary_row_block", "blocks_certified_composition_sampled")
    if kind == "step":
        assert d["extra"]["order"] == 1 and "outer_row" in d["extra"]
    text = api("su2plaq.results.report:render")([p])
    assert kind in text and str(d["metrics"]["logical"]["cx"]) in text


def test_M9_R1_outer_row_and_splitting(root):
    """results/fuzzy/outer_row.json: the 8 outer U_E and 8 outer U_K blocks (cx, n_rot, t_fixed per block and totals) — the
    separate row of Digonto's decision; results/fuzzy/splitting.json: the commuting-cluster product error vs the exact
    exponential at the nominal and alternate beta (>= 0.5 at beta = 0.61: the product is not the target), and the Trotter
    splitting error between orders 1 and 2 at the nominal angles on the 50-dim isolated-plaquette singlet space (> 0)."""
    p = root / "results" / "fuzzy" / "outer_row.json"
    assert p.exists(), f"missing {p}"
    d = json.loads(p.read_text())
    assert d["n_outer_links"] == 8 and d["per_link"]["UE"]["n_rot"] >= 1 and d["per_link"]["UK"]["n_rot"] >= 1
    assert d["totals"]["n_rot"] == 8 * (d["per_link"]["UE"]["n_rot"] + d["per_link"]["UK"]["n_rot"])
    assert d["totals"]["cx"] == 8 * (d["per_link"]["UE"]["cx"] + d["per_link"]["UK"]["cx"])
    assert len(d["provenance"]["git_commit"]) >= 7
    q = root / "results" / "fuzzy" / "splitting.json"
    assert q.exists(), f"missing {q}"
    s = json.loads(q.read_text())
    cl = {row["beta"]: row["error"] for row in s["cluster_product_vs_exact"]}
    assert 0.61 in cl and cl[0.61] >= 0.5 and all(e >= 0 for e in cl.values())
    assert s["trotter_order1_vs_order2"]["alpha"] == 0.37 and s["trotter_order1_vs_order2"]["error"] > 1e-4
    assert s["trotter_order1_vs_order2"]["space"] == "isolated_plaquette_singlets_50"
