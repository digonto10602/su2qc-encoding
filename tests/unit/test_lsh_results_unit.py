"""Unit test of scripts/m7_results.py in --quick mode (schema, physics block, outer-row, order 2); the committed full run is
checked by M7-R1."""
import importlib.util
import json
import pathlib

from su2plaq.results.store import RESULT_KEYS

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_quick_results_run(tmp_path):
    spec = importlib.util.spec_from_file_location("m7_results", ROOT / "scripts" / "m7_results.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--quick", "--out", str(tmp_path)]) == 0
    for kind in ("UE", "UB", "step"):
        d = json.loads((tmp_path / f"{kind}.json").read_text())
        assert list(d) == list(RESULT_KEYS) and d["encoding"] == "lsh" and d["kind"] == kind
        assert d["verification"]["ok"] and len(d["metrics"]["t_table"]) == 2 and d["provenance"]["quick"] is True
        ph = d["extra"]["physics"]
        assert (ph["n_physical_states"], ph["n_inner_codes"], ph["n_bright_codes"], ph["n_outer_site_patterns"]) == (433, 47, 16, 305)
        assert ph["n_raw_agl_states"] == 5920 and ph["n_agl_violating_data_valid_codes"] == 28942
        assert ph["K_minus_K6j"] < 1e-12 and max(ph["spectra_vs_route_A"].values()) < 1e-10
    ue = json.loads((tmp_path / "UE.json").read_text())
    assert ue["extra"]["outer_electric_row"]["verification"]["outer_bits_read"] == 12
    assert json.loads((tmp_path / "step.json").read_text())["extra"]["order2"]["verification"]["ok"]
    assert "comparison" not in json.loads((tmp_path / "UB.json").read_text())["extra"]
