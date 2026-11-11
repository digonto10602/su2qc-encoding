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
