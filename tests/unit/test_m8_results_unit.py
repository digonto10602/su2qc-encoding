"""Unit tests of scripts/m8_results.py (prompts/401 step 8.9): the pure helpers on small fixtures, and one end-to-end `--quick` run on a
temporary copy of the live LSH archive (nothing is written into results/; the run is deterministic w.r.t. the copy)."""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import m8_results as M8  # noqa: E402


def _entry(valid=True, lean=None, key=(71, 1118, 2276, 25), eid="r02-F1-002"):
    m = {"qubits": 25, "cx": 71, "t_fixed": 48, "n_rot": 17, "t_measured": {"1e-06": 1118, "1e-10": 1816},
         "t_estimate": {1e-06: 1064.5}, "depth_ct": 2276}
    return types.SimpleNamespace(id=eid, family="F1", round=2, git_commit="abc1234", program_path="compress/programs/lsh/F1/x.py",
                                 metrics_raw=m, verdict_nominal={"op_norm_error": 8.9e-15, "leak_amplitude": 0.0}, key=key, valid=valid, lean=lean)


def _rank(eid="r02-F1-002", cx=71, t=1116.0, fam="F1", rnd=2, lean="certified", key=None):
    return {"id": eid, "robust_key": key or (cx, int(t * 20), 0, 40000, 25), "t_mean": t, "family": fam, "round": rnd, "cx": cx, "lean": lean,
            "laptop_key": (cx, int(t), 2000, 25), "qubits": 25, "angle_linear": True}


def test_t_at_and_rel():
    assert M8.t_at({"1e-06": 5}, 1e-6) == 5 and M8.t_at({1e-06: 7}, 1e-6) == 7 and M8.t_at({"1e-10": 1}, 1e-6) is None
    assert M8.t_at(None, 1e-6) is None and M8.t_at({}, 1e-6) is None
    assert M8.rel(None) is None and M8.rel(ROOT / "compress" / "x.json") == "compress/x.json" and M8.rel("/elsewhere/y") == "/elsewhere/y"


def test_entry_row_fields_ranked_and_unranked():
    e = _entry(lean={"status": "certified", "reason": ""})
    r = M8.entry_row("headline", e, {e.id: _rank()})
    assert r["cx"] == 71 and r["t_1e-6"] == 1118 and r["t_1e-10"] == 1816 and r["t_est_1e-6"] == 1064.5 and r["depth_ct"] == 2276
    assert r["t_avg"] == 1116.0 and r["robust_key"] == [71, 22320, 0, 40000, 25] and r["lean"] == "certified" and r["key"] == [71, 1118, 2276, 25]
    u = M8.entry_row("x", _entry(lean=None), {})
    assert u["t_avg"] is None and u["robust_key"] is None and u["lean"] == "not_run"
    assert M8.entry_row("x", _entry(lean={"status": "n_a", "reason": "non_linear_angle: y"}), {})["lean"] == "n_a"
    assert M8.entry_row("x", _entry(valid=False), {})["verdict"] == "invalid"


def test_external_rows_blank_depth_and_verdicts():
    m = {"cx": 94, "t_fixed": 88, "n_rot": 8, "qubits": 31, "depth_ct": 87, "measured": False, "t_estimate": {"1e-06": 566.4}, "t_measured": None}
    q = M8.external_row("qiskit_l3_whole", {"source": "qiskit_l3_whole", "valid": False, "reason": "unverifiable: hoists Hadamards", "metrics": m})
    assert q["depth_ct"] is None and q["t_1e-6"] is None and q["t_est_1e-6"] == 566.4 and q["cx"] == 94 and q["lean"] == "n_a"
    assert q["verdict"].count("unverifiable") == 1 and "counts only" in q["verdict"]
    pm = dict(m, cx=108, measured=True, depth_ct=746, t_measured={"1e-06": 348})
    p = M8.external_row("paulo15_wrapped", {"source": "paulo15_wrapped", "valid": True, "kind": "UB", "beta": -0.05, "op_norm_error": 1e-14,
                                            "metrics": pm, "fixed_angle": True})
    assert p["cx"] == 108 and p["depth_ct"] == 746 and p["t_1e-6"] == 348 and p["fixed_angle"] and p["verdict"].startswith("valid at its own angle")


def test_pareto_front_is_strict_and_sorted():
    ranking = [_rank("a", 71, 1116.0), _rank("b", 71, 1124.0), _rank("c", 72, 879.4), _rank("d", 74, 900.0), _rank("e", 74, 697.6),
               _rank("f", 75, 697.6), _rank("g", 90, 585.1), dict(_rank("h", 60, 1.0), robust_key=None)]
    front = M8.pareto_front(ranking)
    assert [p["id"] for p in front] == ["a", "c", "e", "g"]
    assert [p["cx"] for p in front] == sorted(p["cx"] for p in front)
    assert all(front[i]["t_avg"] > front[i + 1]["t_avg"] for i in range(len(front) - 1))
    assert M8.pareto_front([]) == []


def test_vs_spinnet_numbers_and_consistency():
    sn, wr, ls, tr = {"id": "s", "cx": 31, "t_avg": 1092.0}, {"cx": 71, "t_avg": 1124.0}, {"id": "h", "cx": 71, "t_avg": 1116.0}, {"cx": 40, "t_fixed": 32}
    v = M8.vs_spinnet(sn, wr, ls, tr)
    assert v["native_gain_cx"] == 0 and v["overhead_cx"] == 40 and "not reduced" in v["reading"]
    assert v["native_gain_t_avg"] == 8.0 and v["overhead_t_avg"] == 24.0 and v["wrapped_minus_spinnet_t_avg"] == 32.0
    v2 = M8.vs_spinnet(sn, wr, {"id": "h", "cx": 60, "t_avg": 1500.0}, tr)
    assert v2["native_gain_cx"] == 11 and v2["overhead_cx"] == 29 and "removed 11" in v2["reading"]
    with pytest.raises(RuntimeError, match="transcoder"):
        M8.vs_spinnet(sn, {"cx": 72, "t_avg": 1.0}, ls, tr)
    assert "native_gain_t_avg" not in M8.vs_spinnet(sn, wr, {"id": "h", "cx": 71, "t_avg": None}, tr)


def test_transcoder_cost_is_measured_from_the_wrap():
    cost, detail = M8.transcoder_cost()
    assert cost == {"cx": 40, "t_fixed": 32} and detail["cx"] == 40 and detail["n_rot"] == 0


def test_parse_axioms():
    txt = "'t' depends on axioms: [propext,\n Classical.choice,\n Quot.sound, t._native.native_decide.ax_1]\n"
    assert M8.parse_axioms(txt) == ["Classical.choice", "Quot.sound", "propext", "t._native.native_decide.ax_1"]
    assert M8.parse_axioms("no axioms here") is None


def test_atomic_write_replaces_and_leaves_no_temp(tmp_path):
    f = tmp_path / "sub" / "a.txt"
    M8.atomic_write(f, "one")
    M8.atomic_write(f, b"two")
    assert f.read_bytes() == b"two" and [p.name for p in f.parent.iterdir()] == ["a.txt"]


def test_lineage_and_round_table():
    rounds = [{"round": 0, "entries": ["r00-seed-000"], "n_valid": 1, "n_invalid": 0, "best_key": [94, 598, 880, 31], "wall_s": 1.0,
               "evaluator_sha256": "x", "candidates": [{"id": "r00-seed-000", "family": "seed", "valid": True, "key": [94, 598, 880, 31]},
                                                       {"id": "r00-seed-999", "family": "seed", "valid": True, "key": [1, 1, 1, 1]}]},
              {"round": 1, "entries": ["r01-F1-001"], "n_valid": 1, "n_invalid": 1, "best_key": [71, 1, 1, 25], "candidates": [
                  {"id": "r01-F1-001", "family": "F1", "valid": True, "key": [71, 1118, 2276, 25], "parent": "r00-seed-000"},
                  {"id": "r01-F1-002", "family": "F1", "valid": False, "key": None}]}]
    lin = M8.lineage_rows(rounds, {"r01-F1-001": {"t_mean": 1124.0}})
    assert [x["id"] for x in lin] == ["r00-seed-000", "r01-F1-001"] and lin[1]["parent"] == "r00-seed-000" and lin[1]["t_avg"] == 1124.0 and lin[0]["t_avg"] is None
    stop = {"rounds": [{"round": 1, "headline_id": "r01-F1-001", "robust_key": [71, 1, 0, 1, 25], "improved": True}]}
    tab = M8.round_table(rounds, stop)
    assert [t["round"] for t in tab] == [0, 1] and tab[1]["headline_id"] == "r01-F1-001" and tab[0]["headline_id"] is None and tab[1]["n_candidates"] == 2


def test_markdown_names_best_and_headline_and_every_row():
    e = _entry(lean={"status": "certified"})
    rows = [M8.entry_row("headline", e, {e.id: _rank()}), M8.entry_row("global_best", e, {e.id: _rank()})]
    text = M8.rows_markdown(rows, "H-ID", "B-ID", "ab" * 32, 20261107)
    assert text.count("\n| ") == len(rows) + 1 and "HEADLINE (robust key): H-ID" in text and "GLOBAL BEST (archive key): B-ID" in text and "1116.0" in text


def test_lean_block_reports_missing_theorem_file_and_n_a(tmp_path):
    head = _entry(lean={"status": "n_a", "reason": "non_linear_angle: x"})
    b = M8.lean_block(head, tmp_path, theorem_check=False, ranked_head={"angle_linear": False})
    assert b["status"] == "n_a" and b["trust"] == "n_a" and b["theorem_file"] is None and b["trust_label"] == "native-certified, first-order step"
    assert b["theorem_file_status"].startswith("not_applicable")
    head = _entry(lean={"status": "certified", "cert_path": "results/lsh/certs/none.json"})
    b = M8.lean_block(head, tmp_path, theorem_check=False, ranked_head={"angle_linear": True})
    assert b["status"] == "certified" and b["trust"] == "native-certified" and b["theorem_file"] is None and b["cert_sha256"] is None
    assert b["theorem_file_status"].startswith("missing certificate")


def test_lean_block_with_certificate_but_no_theorem_file(tmp_path):
    cert = tmp_path / "results" / "lsh" / "certs" / "c.json"
    cert.parent.mkdir(parents=True)
    cert.write_text(json.dumps({"provenance": {"entry_id": "r02-F1-002", "program_file_sha256": "ab" * 32, "git_dirty": False, "git_commit": "abc"}}))
    head = _entry(lean={"status": "certified", "cert_path": "results/lsh/certs/c.json"})
    head.program_sha256 = "ab" * 32
    b = M8.lean_block(head, tmp_path, theorem_check=False, ranked_head={"angle_linear": True})
    assert b["status"] == "certified" and len(b["cert_sha256"]) == 64 and b["binding"]["matches_headline"] is True
    assert b["theorem_file"] is None and b["theorem_file_status"].startswith("missing (step 8.8")
    thm = tmp_path / "lean" / "certs" / "lsh-best-step.lean"
    thm.parent.mkdir(parents=True)
    thm.write_text(f"-- entry r02-F1-002, program sha256 {'ab' * 32}\ntheorem lsh_best : True := trivial\n")
    b = M8.lean_block(head, tmp_path, theorem_check=False, ranked_head={"angle_linear": True})
    assert b["theorem_file"] == "lean/certs/lsh-best-step.lean" and b["theorem_names_headline"] is True and b["theorem_file_status"].startswith("present")


# ---------------------------------------------------------------------------------------------------- end to end (--quick)
def _copy_live_state(dst: pathlib.Path) -> None:
    for rel in ("compress/archive/lsh", "compress/programs/lsh", "results/compress/lsh"):
        shutil.copytree(ROOT / rel, dst / rel, ignore=shutil.ignore_patterns("__pycache__", "*.tmp*"))
    for rel in ("compress/attempts/lsh.jsonl", "compress/ideation/lsh.md"):
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst / rel)


def test_quick_run_on_a_copy_of_the_archive_writes_only_to_out(tmp_path):
    from su2plaq.compress import robust as RB

    root, out = tmp_path / "root", tmp_path / "out"
    _copy_live_state(root)
    RB.headline("lsh", "step", root=root)                 # makes the copied cache current if the loop moved on (instant otherwise)
    before = {p: p.stat().st_mtime_ns for p in (ROOT / "results" / "lsh").rglob("*") if p.is_file()}
    assert M8.main(["--root", str(root), "--out", str(out), "--quick"]) == 0
    assert before == {p: p.stat().st_mtime_ns for p in (ROOT / "results" / "lsh").rglob("*") if p.is_file()}
    assert sorted(p.name for p in out.iterdir()) == ["m8-before-after.md", "m8-compressed.json", "m8-headline-step.qasm3", "m8-headline-step.qpy"]
    d = json.loads((out / "m8-compressed.json").read_text())
    ex = d["extra"]
    h = RB.headline("lsh", "step", root=root)
    assert d["encoding"] == "lsh" and d["kind"] == "step" and d["circuit_id"] == h["id"] and d["provenance"]["quick"] is True
    assert d["params"] == {"alpha": 0.37, "beta": 0.61, "order": 1} and ex["order"] == 1
    v = d["verification"]
    assert v["ok"] and v["certified"] and v["n_inputs"] == 433 and v["total_error"] <= 1e-10 and v["gauss_residual"] <= 1e-10
    assert d["metrics"]["logical"]["cx"] == h["robust_key"][0]
    assert [r["eps"] for r in d["metrics"]["t_table"]] == [1e-4]
    assert ex["angle_set"]["seed"] == RB.ANGLE_SET_SEED and len(ex["angle_set"]["pairs"]) == RB.ANGLE_SET_N
    assert tuple(ex["headline"]["robust_key"]) == tuple(h["robust_key"])
    rows = {r["row"]: r for r in ex["before_after"]}
    for name in M8.SEED_ROWS + ("global_best", "headline"):
        assert name in rows and rows[name]["lean"] in M8.LEAN_WORDS, name
    assert rows["headline"]["entry"] == h["id"] and rows["headline"]["cx"] == h["robust_key"][0] and abs(rows["headline"]["t_avg"] - h["t_mean"]) < 1e-9
    assert rows["qiskit_l3_whole"]["depth_ct"] is None and rows["paulo15_wrapped"]["entry"] is None
    vs = ex["vs_spinnet"]
    assert vs["transcoder"] == {"cx": 40, "t_fixed": 32} and vs["wrapped"]["cx"] == vs["spinnet_headline"]["cx"] + vs["transcoder"]["cx"]
    assert vs["native_gain_cx"] == vs["wrapped"]["cx"] - vs["lsh_headline"]["cx"] and vs["overhead_cx"] == vs["lsh_headline"]["cx"] - vs["spinnet_headline"]["cx"]
    front = ex["pareto_cx_tavg"]
    assert front and front[0]["cx"] == h["robust_key"][0] and all(front[i]["t_avg"] > front[i + 1]["t_avg"] for i in range(len(front) - 1))
    assert (ex["uniform_split"]["nnz"], ex["uniform_split"]["circuit"]) == (400, "not built") and "outer_electric_row" in ex and ex["lineage"]
    from su2plaq.compress import archive as A

    head = next(e for e in A.Archive.load("lsh", root=root, n_alt=2, strict=True).entries() if e.id == h["id"])
    assert ex["lean"]["status"] == (head.lean or {}).get("status") and rows["headline"]["lean"] == RB._lean_word(ex["lean"]["status"])
    assert ex["lean"]["trust"] in ("native-certified", "n_a") and ex["lean"]["trust_label"] == "native-certified, first-order step"
    assert ex["lean"]["theorem_file"] is None and ex["lean"]["theorem_file_status"].startswith(("missing", "not_applicable"))   # the copy has no lean/: reported, not faked
    md = (out / "m8-before-after.md").read_text()
    assert h["id"] in md and ex["archive_best"] in md and "native_gain_cx" in md


def test_angle_set_seed_matches_robust():
    """The seed recorded in SEEDS must be the one robust.py actually uses (tester 440 obs. 2)."""
    from su2plaq.compress import robust as RB
    assert M8.SEEDS["angle_set"] == RB.ANGLE_SET_SEED
