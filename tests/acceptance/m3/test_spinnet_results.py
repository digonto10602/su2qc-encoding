"""M3-R1 — results files of the spin-network general circuits (prompts/100 §3 step 3.7, §5; schema prompts/002 §2.11).
Written by scripts/m3_results.py; the UB file carries the like-for-like comparison rows (Paulo's 15-qubit file,
spinnet_v2 skeletons) that Report 3 renders."""
import json

import pytest

from tests.acceptance._api import api


@pytest.mark.parametrize("kind", ["UE", "UB", "step"])
def test_M3_R1_results_files(kind, root):
    """results/spinnet/<kind>.json exists with the schema keys, verification ok at the nominal angles (exact-angle rule),
    logical metrics (7 ancillas for UB/step), the 4-row T(eps) table with per-row synthesised verdicts, provenance commit;
    render() produces the report table.  UB.json extra.comparison has 'paulo15' (verdict ok with the recorded gauge) and
    'spinnet_v2' (pairs9, flags4 verdicts ok) with logical counts and pygridsynth T at 1e-6; UE.json extra has the
    outer_electric_row; step.json extra has order2."""
    p = root / "results" / "spinnet" / f"{kind}.json"
    assert p.exists(), f"missing {p}"
    d = json.loads(p.read_text())
    RESULT_KEYS = api("su2plaq.results.store:RESULT_KEYS")
    assert list(d.keys()) == list(RESULT_KEYS)
    assert d["encoding"] == "spinnet" and d["kind"] == kind and d["circuit_id"] == kind
    assert d["params"]["alpha"] in (0.37, None) and d["params"]["beta"] in (0.61, None)
    ver = d["verification"]
    assert ver["ok"] and ver["op_norm_error"] <= 1e-10 and ver["leak_amplitude"] <= 1e-10 and ver["gauss_residual"] <= 1e-10
    assert ver["max_leak"] <= 1e-20 and ver["block_error"] <= ver["op_norm_error"] and ver["certified"] and ver["engine"] == "sparse"
    assert ver["outer_bits_read"] == 0
    assert d["metrics"]["logical"]["cx"] >= 0 and len(d["metrics"]["t_table"]) == 4
    for row in d["metrics"]["t_table"]:
        assert row["t_total"] == row["t_fixed"] + row["t_rot_pygridsynth"] and "synth" in row and row["synth"]["verdict"]["ok"]
    assert len(d["provenance"]["git_commit"]) >= 7 and "qiskit" in d["provenance"]["versions"]
    assert d["extra"]["physics"]["n_physical_states"] == 433 and d["extra"]["physics"]["n_inner_codes"] == 47
    if kind in ("UB", "step"):
        assert d["metrics"]["logical"]["cx"] > 0 and d["metrics"]["logical"]["t_fixed"] > 0 and d["metrics"]["logical"]["ancilla"] == 7
        assert d["metrics"]["logical"]["n_rot"] == (4 if kind == "UB" else 8)
    if kind == "UE":
        orow = d["extra"]["outer_electric_row"]
        assert orow["verification"]["ok"] and orow["metrics"]["logical"]["n_rot"] == 12
    if kind == "step":
        assert d["extra"]["order2"]["verification"]["ok"] and d["extra"]["order2"]["metrics"]["logical"]["n_rot"] == 12
    if kind == "UB":
        cmp_ = d["extra"]["comparison"]
        pa = cmp_["paulo15"]
        assert pa["verification"]["ok"] and pa["logical"]["cx"] == 68 and pa["logical"]["n_rot"] == 4 and pa["logical"]["t_fixed"] == 64
        assert len(pa["gauge_minus_codes"]) == 8 and pa["beta"] == 0.05 and pa["t_table_pygridsynth"][0]["eps"] == 1e-6
        for name, cx in (("pairs9", 34), ("flags4", 44)):
            row = cmp_["spinnet_v2"][name]
            assert row["verification"]["ok"] and row["logical"]["cx"] == cx and row["t_table_pygridsynth"][0]["eps"] == 1e-6
        ours = cmp_["ours_beta_0_61"]
        assert ours["logical"]["cx"] == d["metrics"]["logical"]["cx"] and ours["t_table_pygridsynth"][0]["eps"] == 1e-6
    text = api("su2plaq.results.report:render")([p])
    assert kind in text and str(d["metrics"]["logical"]["cx"]) in text
