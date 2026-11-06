"""M5-R1 — results files for the rishon general circuits (prompts/200 §2.8, step 5.10; prompts/002 §2.11 schema)."""
import json

import pytest

from tests.acceptance._api import api

REGISTER_VARIANTS = {"jw_4_per_link": 48, "codeword_3_per_link": 36, "touched": 16}
PHYSICS = {"dim": 38432, "closed": 4352, "u2_sector": 2192, "inner_span_rank": 1296, "bright_pairs": 81}


@pytest.mark.parametrize("kind", ["UE", "UB", "step"])
def test_M5_R1_results_files(kind, root):
    """results/rishon/<kind>.json: schema keys, verification ok/certified by the inner-block method with the Gauss sample,
    logical metrics, 4-row T(eps) table, provenance; the register-variant and physics rows; render() works."""
    p = root / "results" / "rishon" / f"{kind}.json"
    if not p.exists():
        pytest.fail(f"PENDING: missing {p} (step 5.10)", pytrace=False)
    d = json.loads(p.read_text())
    RESULT_KEYS = api("su2plaq.results.store:RESULT_KEYS")
    assert list(d.keys()) == list(RESULT_KEYS)
    assert d["encoding"] == "rishon" and d["kind"] == kind and d["circuit_id"] == kind
    assert d["params"]["alpha"] in (0.37, None) and d["params"]["beta"] in (0.61, None)
    ver = d["verification"]
    assert ver["ok"] and ver["certified"] and ver["method"] == "inner_block" and ver["reason"] == "ok"
    assert ver["op_norm_error"] <= 1e-10 and ver["leak_amplitude"] <= 1e-10 and ver["block_error"] <= ver["op_norm_error"]
    assert ver["max_leak"] <= 1e-20 and ver["gauss_residual"] <= 1e-10 and ver["gauss_states"] == 273 and ver["outer_bits_read"] == 0
    assert d["metrics"]["logical"]["cx"] >= 0 and d["metrics"]["logical"]["qubits"] >= 16 and len(d["metrics"]["t_table"]) == 4
    assert len(d["provenance"]["git_commit"]) >= 7 and "qiskit" in d["provenance"]["versions"]
    assert d["extra"]["register_variants"] == REGISTER_VARIANTS and d["extra"]["physics"] == PHYSICS
    if kind in ("UB", "step"):
        assert d["metrics"]["logical"]["cx"] > 0 and d["metrics"]["logical"]["n_rot"] >= 1
    if kind == "UE":
        assert d["metrics"]["logical"]["n_rot"] == 4
    text = api("su2plaq.results.report:render")([p])
    assert kind in text and str(d["metrics"]["logical"]["cx"]) in text


def test_M5_R1_observables_and_register_rows(root):
    """results/rishon/observables.json holds the shared-observable table (three angle pairs, n = 1, 2, both theories,
    closed spectra at three couplings, definitions) and results/rishon/register_rows.json the register rows; the outer
    electric row file exists."""
    p = root / "results" / "rishon" / "observables.json"
    if not p.exists():
        pytest.fail(f"PENDING: missing {p} (step 5.10)", pytrace=False)
    d = json.loads(p.read_text())
    assert len(d["angles"]) == 3 and set(d) >= {"angles", "rishon", "ks", "closed_spectra", "definitions", "provenance"}
    for th in ("rishon", "ks"):
        for row in d[th]:
            assert set(row) >= {"alpha", "beta", "n", "E_link", "P", "echo"}
        assert {r["n"] for r in d[th]} == {1, 2}
    assert set(map(float, d["closed_spectra"]["g2"])) == {0.5, 1.0, 2.0}
    r = json.loads((root / "results" / "rishon" / "register_rows.json").read_text())
    assert r["rows"]["jw_4_per_link"]["qubits"] == 48 and r["rows"]["codeword_3_per_link"]["qubits"] == 36
    assert r["rows"]["jw_4_per_link"]["touched"] == 16
    assert (root / "results" / "rishon" / "UE_outer_row.json").exists()
    o = json.loads((root / "results" / "rishon" / "UE_outer_row.json").read_text())
    assert o["metrics"]["logical"]["n_rot"] == 12
