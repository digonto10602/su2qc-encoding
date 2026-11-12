"""Unit test of the pure helpers of scripts/m4_results.py (the full script is exercised by acceptance M4-R1 on a clean commit)."""
import importlib.util
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "m4_results.py"


def _load():
    spec = importlib.util.spec_from_file_location("m4_results_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_before_after_markdown_names_both_entries_and_marks_missing_cells():
    m = _load()
    row = {"row": "headline", "entry": "r02-F1-002", "qubits": 17, "cx": 31, "t_fixed": 16, "n_rot": 17, "t_1e-6": 1086, "t_avg": 1092.0,
           "t_est_1e-6": 1032.5, "t_1e-10": 1784, "depth_ct": 2258, "verdict": "valid (err 5e-15, leak 0)", "lean": "certified"}
    ext = {"row": "paulo15", "entry": None, "qubits": 23, "cx": 68, "t_fixed": 64, "n_rot": 4, "t_1e-6": None, "t_avg": None,
           "t_est_1e-6": None, "t_1e-10": None, "depth_ct": 726, "verdict": "valid at its own angle", "lean": "n_a"}
    text = m._rows_markdown([row, ext], "r02-F1-002", "r04-F1-004", "a" * 64)
    assert "r02-F1-002" in text and "r04-F1-004" in text and "aaaaaaaaaaaaaaaa" in text
    lines = [ln for ln in text.splitlines() if ln.startswith("| ")]
    assert len(lines) == 3 and lines[1].count("|") == lines[2].count("|") == lines[0].count("|")
    assert "| 1092.0 |" in lines[1] and "| paulo15 | - |" in lines[2]


def _fake_external_rows():
    # metrics as a fresh (not JSON-round-tripped) compress.metrics dict: float eps keys; the qiskit row is counts only (measured False)
    return [
        {"source": "qiskit_l3_whole", "valid": False, "reason": "unverifiable",
         "metrics": {"qubits": 23, "cx": 54, "t_fixed": 56, "n_rot": 8, "t_measured": None, "t_estimate": {1e-6: 534.4, 1e-10: 853.3},
                     "depth": 67, "depth_ct": 67, "measured": False}},
        {"source": "paulo15", "fixed_angle": True, "beta": 0.05, "valid": True, "op_norm_error": 1e-14,
         "metrics": {"qubits": 23, "cx": 68, "t_fixed": 64, "n_rot": 4, "t_measured": {1e-6: 316, 1e-10: 478},
                     "t_estimate": {1e-6: 303.2, 1e-10: 462.6}, "depth": 90, "depth_ct": 726, "measured": True}},
    ]


def test_eps_get_accepts_float_and_string_keys():
    m = _load()
    assert m._eps_get({1e-6: 316, 1e-10: 478}, 1e-6) == 316
    assert m._eps_get({"1e-06": 316, "1e-10": 478}, 1e-10) == 478
    assert m._eps_get({1e-6: 316}, 1e-10) is None and m._eps_get(None, 1e-6) is None


def test_external_rows_have_t_values_for_float_and_string_eps_keys_and_no_fake_depth_ct(monkeypatch):
    m = _load()
    for as_string in (False, True):
        rows_in = _fake_external_rows()
        if as_string:
            for r in rows_in:
                for k in ("t_measured", "t_estimate"):
                    t = r["metrics"][k]
                    r["metrics"][k] = {str(float(e)): v for e, v in t.items()} if t else t
        monkeypatch.setattr(m.L, "_external_rows", lambda sp, _r=rows_in: _r)
        rows = {r["row"]: r for r in m._external_rows(None)}
        p, q = rows["paulo15"], rows["qiskit_l3_whole"]
        assert (p["t_1e-6"], p["t_1e-10"], p["t_est_1e-6"]) == (316, 478, 303.2)      # the old string-key lookup gave None here
        assert p["depth_ct"] == 726
        assert q["t_1e-6"] is None and q["t_est_1e-6"] == 534.4
        assert q["depth_ct"] is None                    # the uncompiled depth 67 is not a Clifford+T depth
