"""Unit tests of the helpers of scripts/m6_results.py (pure functions; no Lean, no archive evaluation)."""
from __future__ import annotations

import json
import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import m6_results as M6  # noqa: E402


def _entry(valid=True, lean=None, key=(216, 832, 1350, 52)):
    m = {"qubits": 52, "cx": 216, "t_fixed": 196, "n_rot": 10, "t_measured": {"1e-06": 832, "1e-10": 1228},
         "t_estimate": {1e-06: 793.9}, "depth_ct": 1350}
    return types.SimpleNamespace(id="rXX-F3-001", family="F3", round=6, git_commit="abc1234", program_path="compress/programs/x.py",
                                 metrics_raw=m, verdict_nominal={"op_norm_error": 1.5e-13, "leak_amplitude": 0.0}, key=key, valid=valid,
                                 lean=lean)


def test_t_at_accepts_float_and_string_keys():
    assert M6.t_at({"1e-06": 5}, 1e-6) == 5 and M6.t_at({1e-06: 7}, 1e-6) == 7 and M6.t_at({"1e-10": 1}, 1e-6) is None
    assert M6.t_at(None, 1e-6) is None and M6.t_at({}, 1e-6) is None


def test_entry_row_fields_and_lean_words():
    r = M6.entry_row("headline", _entry(lean={"status": "certified", "reason": ""}), {"rXX-F3-001": 829.8})
    assert r["layer"] == "unit" and r["cx"] == 216 and r["t_1e-6"] == 832 and r["t_1e-10"] == 1228 and r["t_est_1e-6"] == 793.9
    assert r["t_avg"] == 829.8 and r["lean"] == "certified" and r["lean_source"] == "archive" and r["key"] == [216, 832, 1350, 52]
    assert M6.entry_row("x", _entry(lean=None), {})["lean"] == "not_run"
    assert M6.entry_row("x", _entry(lean={"status": "n_a", "reason": "angle_fit_not_confirmed: y"}), {})["lean"] == "n_a"
    fresh = M6.entry_row("x", _entry(), {}, {"status": "certified", "reason": "", "source": "fresh (3.0 s)"}, {"selection": "s"})
    assert fresh["lean"] == "certified" and fresh["lean_source"] == "fresh (3.0 s)" and fresh["selection"] == "s"
    assert M6.entry_row("x", _entry(valid=False), {})["verdict"] == "invalid"


def test_layered_row_from_metrics_dict():
    m = {"qubits": 48, "cx": 32, "t_fixed": 0, "n_rot": 8, "t_measured": {"1e-06": 496}, "t_estimate": {1e-06: 478.4}, "depth_ct": 326}
    r = M6.layered_row("det_layer", "det", m, t_avg=500.8, lean="certified")
    assert (r["layer"], r["cx"], r["t_1e-6"], r["t_1e-10"], r["t_est_1e-6"], r["t_avg"]) == ("det", 32, 496, None, 478.4, 500.8)


def _consistent():
    unit = {"cx": 216, "t_fixed": 196, "n_rot": 10, "t_eps": 832, "depth_ct": 1350, "qubits": 52}
    full = {"cx": 248, "t_fixed": 196, "n_rot": 18, "t_eps": 1328, "depth_ct": 1676, "qubits": 52}
    det = {"cx": 32, "key": [32, 496, 326, 48], "t_mean": 500.8}
    head = types.SimpleNamespace(id="rXX-F3-001", program_sha256="ab" * 32, key=(216, 832, 1350, 52))
    tl = {"entry": "rXX-F3-001", "program_sha256": "ab" * 32, "ok": True, "skeleton_equal": True, "outer_touched": False,
          "unit_key": [216, 832, 1350, 52], "det_key": [32, 496, 326, 48], "three_layer_key": [248, 1328, 1676, 52],
          "unit_t_mean": 829.8, "det_t_mean": 500.8, "three_layer_t_mean": 1330.6}
    return tl, head, det, unit, full


def test_check_three_layer_accepts_a_consistent_file():
    tl, head, det, unit, full = _consistent()
    M6.check_three_layer(tl, head, det, unit, full)


@pytest.mark.parametrize("mutate", [
    lambda tl, head, det, unit, full: tl.update(entry="other"),
    lambda tl, head, det, unit, full: tl.update(program_sha256="00" * 32),
    lambda tl, head, det, unit, full: tl.update(ok=False),
    lambda tl, head, det, unit, full: tl.update(outer_touched=True),
    lambda tl, head, det, unit, full: tl.update(unit_key=[216, 833, 1350, 52]),
    lambda tl, head, det, unit, full: tl.update(det_key=[32, 497, 326, 48]),
    lambda tl, head, det, unit, full: tl.update(three_layer_key=[248, 1329, 1676, 52]),
    lambda tl, head, det, unit, full: tl.update(three_layer_t_mean=1331.0),
    lambda tl, head, det, unit, full: full.update(cx=249),
])
def test_check_three_layer_rejects_inconsistencies(mutate):
    tl, head, det, unit, full = _consistent()
    mutate(tl, head, det, unit, full)
    with pytest.raises(RuntimeError, match="inconsistent"):
        M6.check_three_layer(tl, head, det, unit, full)


def test_committed_three_layer_file_is_self_consistent():
    f = ROOT / "results" / "compress" / "rishon" / "three-layer.json"
    if not f.exists():
        pytest.skip("three-layer.json not present")
    tl = json.loads(f.read_text())
    assert tl["three_layer_key"][0] == tl["unit_key"][0] + tl["det_key"][0]
    assert abs(tl["three_layer_t_mean"] - tl["unit_t_mean"] - tl["det_t_mean"]) < 1e-9


def test_first_line_comment_is_prepended_once(tmp_path):
    f = tmp_path / "t.lean"
    f.write_text("import Su2PlaqCert.Rishon.Check3\n\ntheorem t : True := trivial\n")
    M6.with_first_line_comment(f, "entry r06-F3-006, program sha256 abc")
    M6.with_first_line_comment(f, "entry r06-F3-006, program sha256 abc")
    lines = f.read_text().splitlines()
    assert lines[0] == "-- entry r06-F3-006, program sha256 abc" and lines[1].startswith("import Su2PlaqCert") and f.read_text().count("-- entry") == 1
    with pytest.raises(ValueError, match="single line"):
        M6.with_first_line_comment(f, "a\nb")


def test_parse_axioms():
    txt = "'t' depends on axioms: [propext,\n Classical.choice,\n Quot.sound, t._native.native_decide.ax_1]\n"
    assert M6.parse_axioms(txt) == ["Classical.choice", "Quot.sound", "propext", "t._native.native_decide.ax_1"]
    assert M6.parse_axioms("no axioms here") is None


def test_rel_and_seeds_and_theorem_name():
    assert M6.rel(None) is None and M6.rel(ROOT / "compress" / "x.json") == "compress/x.json" and M6.rel("/elsewhere/y") == "/elsewhere/y"
    s = M6.seeds()
    assert s["angle_set"] == 20261107 and s["eta_set"] == 20261110
    assert M6.THEOREM_FILE == ROOT / "lean" / "certs" / "rishon-best-step.lean" and M6.THEOREM_NAME.isidentifier()


def test_rows_markdown_lists_every_row():
    m = {"qubits": 52, "cx": 216, "t_fixed": 196, "n_rot": 10, "t_measured": {"1e-06": 832}, "t_estimate": {1e-06: 793.9}, "depth_ct": 1350}
    rows = [M6.entry_row("headline", _entry(lean={"status": "certified"}), {"rXX-F3-001": 829.8}),
            M6.layered_row("three_layer", "three_layer", m, entry="rXX-F3-001", t_avg=1330.6, lean="certified")]
    text = M6.rows_markdown(rows, "rXX-F3-001", "rXX-F3-001", "ab" * 32, 20261107, 20261110)
    assert text.count("\n| ") == len(rows) + 1 and "HEADLINE (robust key): rXX-F3-001" in text and "1330.6" in text and "829.8" in text
