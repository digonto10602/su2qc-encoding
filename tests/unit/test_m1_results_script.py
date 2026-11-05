"""Light checks of scripts/m1_results.py helpers and of the written results files (written by the script, not by this test)."""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("m1_results", ROOT / "scripts" / "m1_results.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_physics_block_is_computed_not_typed(mod):
    from su2plaq.encodings.twelve import TwelveQubit

    p = mod._physics(TwelveQubit())
    assert p["n_outer_patterns"] == 3 ** 8 and sum(p["dim_So_histogram"].values()) == 3 ** 8
    assert p["inner_span_rank"] == 625 and p["n_physical_states"] == 433


@pytest.mark.parametrize("kind", ["UE", "UB", "step"])
def test_results_files_are_consistent_if_present(kind):
    p = ROOT / "results" / "twelve" / f"{kind}.json"
    if not p.exists():
        pytest.skip("run scripts/m1_results.py first")
    d = json.loads(p.read_text())
    v = d["verification"]
    assert v["ok"] and abs(v["op_norm_error"] - (v["block_error"] + v["dropped_total"] + v["leak_amplitude"])) < 1e-15
    for row in d["metrics"]["t_table"]:
        s = row["synth"]
        assert s["error_measured_sum"] <= s["error_bound_sum"] + 1e-15 and s["verdict"]["tolerances"]["tol_err"] > s["error_bound_sum"]
        assert s["verdict"]["op_norm_error"] <= s["verdict"]["tolerances"]["tol_err"] or not s["verdict"]["ok"]
