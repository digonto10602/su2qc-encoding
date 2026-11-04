"""M1-R1 — results files for the 12-qubit general circuits exist, validate and render (prompts/002 §2.11)."""
import json

import pytest

from tests.acceptance._api import api


@pytest.mark.parametrize("kind", ["UE", "UB", "step"])
def test_M1_R1_results_files(kind, root):
    """results/twelve/<kind>.json exists with the schema keys, verification ok at the nominal angles, logical metrics
    and the 4-row T(eps) table, provenance commit; render() produces the report table."""
    p = root / "results" / "twelve" / f"{kind}.json"
    assert p.exists(), f"missing {p}"
    d = json.loads(p.read_text())
    RESULT_KEYS = api("su2plaq.results.store:RESULT_KEYS")
    assert list(d.keys()) == list(RESULT_KEYS)
    assert d["encoding"] == "twelve" and d["kind"] == kind and d["circuit_id"] == kind
    assert d["params"]["alpha"] in (0.37, None) and d["params"]["beta"] in (0.61, None)
    assert d["verification"]["ok"] and d["verification"]["op_norm_error"] <= 1e-10 and d["verification"]["max_leak"] <= 1e-12
    assert d["metrics"]["logical"]["cx"] >= 0 and len(d["metrics"]["t_table"]) == 4
    assert len(d["provenance"]["git_commit"]) >= 7 and "qiskit" in d["provenance"]["versions"]
    if kind in ("UB", "step"):
        assert d["metrics"]["logical"]["cx"] > 0 and d["metrics"]["logical"]["t_fixed"] > 0 and d["metrics"]["logical"]["ancilla"] == 22
    text = api("su2plaq.results.report:render")([p])
    assert kind in text and str(d["metrics"]["logical"]["cx"]) in text
