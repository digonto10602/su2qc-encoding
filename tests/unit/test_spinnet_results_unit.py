"""Light checks of scripts/m3_results.py (prompts/100 step 3.7): helpers, schema of a --quick run, written files if present."""
import importlib.util
import json
import pathlib

import pytest

from su2plaq.results.store import RESULT_KEYS

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("m3_results", ROOT / "scripts" / "m3_results.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_physics_block_is_computed_not_typed(mod):
    from su2plaq.encodings.spinnet import SpinNet

    p = mod._physics(SpinNet())
    assert p["n_physical_states"] == 433 and p["n_inner_codes"] == 47
    assert (p["n_bright_codes"], p["n_dark_codes"], p["n_bright_pairs"]) == (16, 31, 8)
    assert p["coupling_values_per_pair"] == {"-2.0": 1, "-0.5": 1, "1.0": 6}
    assert p["n_gauge_minus_433"] == 64 and p["gauge_residual"] <= 1e-10
    assert sum(int(k) * v for k, v in p["states_per_outer_pattern_histogram"].items()) == 433
    assert p["target_cross_pattern_max_abs"] <= 1e-12 and p["target_same_pattern_vs_inner_block_max_dev"] <= 1e-12


def test_rel_path_helper_and_unevaluable_record(mod, tmp_path):
    assert mod._rel(ROOT / "results" / "spinnet" / "UE.json") == str(pathlib.Path("results") / "spinnet" / "UE.json")
    assert mod._rel(tmp_path / "x.qpy") == str((tmp_path / "x.qpy").resolve())

    class V:
        reason = "writes_outer"

    rec = mod._unevaluable(V())
    assert rec["evaluable"] is False and "ok" not in rec and "certified" not in rec


def test_script_takes_one_provenance_snapshot_before_writing_and_records_machine():
    src = (ROOT / "scripts" / "m3_results.py").read_text()
    assert src.index("snap = provenance(SEEDS)") < src.index("out.mkdir(parents=True") < src.index("save_result(out")
    assert src.count("provenance_snapshot=snap") == src.count("save_result(out")
    for key in ("host", "command", "wall_seconds", "peak_rss_mb"):
        assert f'snap["{key}"]' in src


def test_quick_run_writes_schema_files(mod, tmp_path):
    assert mod.main(["--quick", "--out", str(tmp_path)]) == 0
    for kind in ("UE", "UB", "step"):
        d = json.loads((tmp_path / f"{kind}.json").read_text())
        assert tuple(d) == RESULT_KEYS and d["encoding"] == "spinnet" and d["kind"] == kind
        assert d["verification"]["ok"] and d["verification"]["outer_bits_read"] == 0
        assert [r["eps"] for r in d["metrics"]["t_table"]] == [1e-4, 1e-6]
        assert all(r["synth"]["verdict"]["ok"] for r in d["metrics"]["t_table"])
        p = d["provenance"]
        assert {"git_commit", "git_dirty", "versions", "platform", "seeds", "host", "command", "wall_seconds", "peak_rss_mb"} <= set(p)
        assert d["extra"]["physics"]["n_physical_states"] == 433 and p["quick"] is True
        assert (ROOT / d["files"]["qpy"]).exists() or pathlib.Path(d["files"]["qpy"]).exists()
    assert "comparison" not in json.loads((tmp_path / "UB.json").read_text())["extra"]
    assert json.loads((tmp_path / "UE.json").read_text())["extra"]["outer_electric_row"]["verification"]["ok"]
    assert json.loads((tmp_path / "step.json").read_text())["extra"]["order2"]["metrics"]["logical"]["n_rot"] == 12


@pytest.mark.parametrize("kind", ["UE", "UB", "step"])
def test_results_files_are_consistent_if_present(kind):
    p = ROOT / "results" / "spinnet" / f"{kind}.json"
    if not p.exists():
        pytest.skip("run scripts/m3_results.py first")
    d = json.loads(p.read_text())
    v = d["verification"]
    assert v["ok"] and abs(v["op_norm_error"] - (v["block_error"] + v["dropped_total"] + v["leak_amplitude"])) < 1e-15
    for row in d["metrics"]["t_table"]:
        s = row["synth"]
        assert s["error_measured_sum"] <= s["error_bound_sum"] + 1e-15 and s["verdict"]["tolerances"]["tol_err"] > s["error_bound_sum"]
