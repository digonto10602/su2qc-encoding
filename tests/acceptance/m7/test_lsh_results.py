"""M7-R1 — results files of the LSH general circuits (prompts/400 §3 step 7.10, §5; schema prompts/002 §2.11).
Written by scripts/m7_results.py; Report 7 is rendered from these files only.  The UB file carries the comparison rows
(spin-network circuits wrapped by the transcoder, and the spin-network encoding's own counts for the like-for-like
statement "LSH register = spin-network register + 40 CX + 32 T")."""
import json

import pytest

from tests.acceptance._api import api


@pytest.mark.parametrize("kind", ["UE", "UB", "step"])
def test_M7_R1_results_files(kind, root):
    """results/lsh/<kind>.json exists with the schema keys, verification ok at the nominal angles (exact-angle rule,
    sparse engine, certified, outer never read), logical metrics, the 4-row T(eps) table with per-row synthesised verdicts,
    provenance commit; render() produces the report table.  extra.physics records the model numbers (433 states, 47 inner
    codes, 16 bright, 305 outer-site patterns, 5920 raw AGL states, 28 942 AGL-violating data-valid codes).  UE: 4..8
    rotations and the outer_electric_row; UB: at most 16 rotations, comparison rows; step: order2."""
    p = root / "results" / "lsh" / f"{kind}.json"
    if not p.exists():
        pytest.fail(f"PENDING: results/lsh/{kind}.json missing (run scripts/m7_results.py, prompts/400 step 7.10)", pytrace=False)
    d = json.loads(p.read_text())
    RESULT_KEYS = api("su2plaq.results.store:RESULT_KEYS")
    assert list(d.keys()) == list(RESULT_KEYS)
    assert d["encoding"] == "lsh" and d["kind"] == kind and d["circuit_id"] == kind
    assert d["params"]["alpha"] in (0.37, None) and d["params"]["beta"] in (0.61, None)
    ver = d["verification"]
    assert ver["ok"] and ver["op_norm_error"] <= 1e-10 and ver["leak_amplitude"] <= 1e-10 and ver["gauss_residual"] <= 1e-10
    assert ver["max_leak"] <= 1e-20 and ver["block_error"] <= ver["op_norm_error"] and ver["certified"] and ver["engine"] == "sparse"
    assert ver["outer_bits_read"] == 0 and ver["n_inputs"] == 433
    lg = d["metrics"]["logical"]
    assert lg["cx"] >= 0 and len(d["metrics"]["t_table"]) == 4
    for row in d["metrics"]["t_table"]:
        assert row["t_total"] == row["t_fixed"] + row["t_rot_pygridsynth"] and "synth" in row and row["synth"]["verdict"]["ok"]
    assert len(d["provenance"]["git_commit"]) >= 7 and "qiskit" in d["provenance"]["versions"]
    ph = d["extra"]["physics"]
    assert ph["n_physical_states"] == 433 and ph["n_inner_codes"] == 47 and ph["n_bright_codes"] == 16
    assert ph["n_outer_site_patterns"] == 305 and ph["n_raw_agl_states"] == 5920 and ph["n_agl_violating_data_valid_codes"] == 28942
    assert ph["qubits_data"] == 12 and ph["qubits_outer"] == 12
    if kind == "UE":
        assert lg["cx"] == 0 and 4 <= lg["n_rot"] <= 8
        orow = d["extra"]["outer_electric_row"]
        assert orow["verification"]["ok"] and orow["verification"]["outer_bits_read"] == 12
        assert lg["n_rot"] + 8 <= orow["metrics"]["logical"]["n_rot"] <= lg["n_rot"] + 12
    if kind in ("UB", "step"):
        assert 0 < lg["cx"] <= 188 and lg["ancilla"] <= 16 and lg["qubits"] == 12 + lg["ancilla"]
    if kind == "UB":
        assert 1 <= lg["n_rot"] <= 16
        cmp_ = d["extra"]["comparison"]
        for name in ("general7", "pairs9", "flags4"):
            row = cmp_["wrapped_spinnet"][name]
            assert row["verification"]["ok"] and row["logical"]["cx"] == row["spinnet_logical"]["cx"] + 40
            assert row["logical"]["t_fixed"] == row["spinnet_logical"]["t_fixed"] + 32
            assert row["t_table_pygridsynth"][0]["eps"] == 1e-6
        assert cmp_["transcoder"] == {"cx": 20, "t_fixed": 16, "n_rot": 0, "ancilla": 0}
    if kind == "step":
        o2 = d["extra"]["order2"]
        assert o2["verification"]["ok"] and o2["metrics"]["logical"]["cx"] == lg["cx"]
        assert o2["metrics"]["logical"]["n_rot"] > lg["n_rot"]
    text = api("su2plaq.results.report:render")([p])
    assert kind in text and str(lg["cx"]) in text
