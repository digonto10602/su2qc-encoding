"""Unit tests of su2plaq.crosscheck.report (prompts/009 §5.4): headline picks, Pareto front, gate-table rows, rendering, figure.
Headline caches are replaced by synthetic rankings (monkeypatch), so nothing is built or evaluated."""
from __future__ import annotations

import json
import pathlib

import pytest

from su2plaq.crosscheck import report as R

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _row(i, cx, t, tn=None, key=None, rho=0, depth=100, rob=True):
    return {"id": i, "robust_key": [cx, int(20 * t), rho, depth, 10] if rob else None, "t_mean": t, "lean": "n_a", "laptop_key": [cx, tn or int(t), depth, 10],
            "family": "F", "round": 0, "cx": cx, "qubits": 10, "t_nominal": tn or int(t), "depth_mean": float(depth), "angle_linear": rho == 0}


RANK = [_row("a", 10, 500.0), _row("b", 10, 480.0, rho=1), _row("c", 12, 300.0), _row("d", 20, 300.0), _row("e", 8, 900.0), _row("u", 5, 1.0, rob=False)]


def _fake_headline(enc, ranking=RANK):
    head = min((r for r in ranking if r["robust_key"]), key=lambda r: tuple(r["robust_key"]))
    return {"id": head["id"], "robust_key": head["robust_key"], "t_mean": head["t_mean"], "lean": "n_a", "ranking": ranking, "unrankable": ["u"]}


def test_pick_and_pareto():
    head, tfirst = R._pick(RANK)
    assert head["id"] == "e" and tfirst["id"] == "c"                  # smallest CX = 8; smallest sum T = 300 with the smaller CX = 12
    par = R._pareto(RANK)
    assert [p["entry"] for p in par] == ["e", "b", "c"]               # a is dominated by b; d by c; the unrankable u is ignored
    assert all(p["cx"] == next(r["cx"] for r in RANK if r["id"] == p["entry"]) for p in par)


def test_cached_headline_reasons(monkeypatch, tmp_path):
    from su2plaq.compress import robust as RB

    monkeypatch.setattr(RB, "headline", lambda *a, **k: None)
    h, why = R._cached_headline("twelve", "step", tmp_path)
    assert h is None and "no cache file results/compress/twelve/robust.json" in why and "prompts/008" in why
    (tmp_path / "results" / "compress" / "spinnet").mkdir(parents=True)
    (tmp_path / "results" / "compress" / "spinnet" / "robust.json").write_text("{}")
    h, why = R._cached_headline("spinnet", "step", tmp_path)
    assert h is None and "present but stale" in why
    monkeypatch.setattr(RB, "headline", lambda *a, **k: {"id": None, "ranking": []})
    h, why = R._cached_headline("lsh", "step", tmp_path)
    assert h is None and "no ranked valid entry" in why and "prompts/401" in why
    monkeypatch.setattr(RB, "headline", lambda *a, **k: _fake_headline("x"))
    h, why = R._cached_headline("lsh", "step", tmp_path)
    assert why is None and h["id"] == "e"


def test_gate_table_pending_now_and_final_with_synthetic_headlines(monkeypatch, tmp_path):
    t = R.gate_table(out=False)
    assert [r["encoding"] for r in t["rows"]] == ["twelve", "spinnet", "lsh", "rishon", "fuzzy"]
    for r in t["rows"]:
        assert r["general"]["source"].startswith(R.GENERAL_FILE[r["encoding"]]) and r["general"]["cx"] > 0
        assert r["status"].startswith("pending: ") or r["status"] == "final"
    assert t["rows"][3]["general_two_layer"]["cx"] > 0
    # synthetic caches for all six archives, on a scratch root that holds only the general-step files (so that the existence of the real
    # results/fuzzy/compressed_step_headline.json, which step H.3 creates, does not matter)
    import shutil

    for rel in [*R.GENERAL_FILE.values(), "results/rishon/step.json"]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    monkeypatch.setattr(R, "_cached_headline", lambda enc, kind, root: (_fake_headline(enc), None))
    t = R.gate_table(out=False, root=tmp_path)
    tw = t["rows"][0]
    assert tw["headline"]["entry"] == "e" and tw["headline"]["cx"] == 8 and tw["t_first"]["entry"] == "c" and tw["status"] == "final"
    assert [p["entry"] for p in tw["pareto"]] == ["e", "b", "c"]
    fz = t["rows"][4]
    assert fz["headline"]["cx"] == 8 + 4 * 8 and abs(fz["headline"]["t_mean"] - 5 * 900.0) <= 1e-9
    assert fz["t_first"]["cx"] == 12 * 5 and set(fz["units"]) == {"fuzzy_ub", "fuzzy_link"}
    assert fz["status"].startswith("pending: ") and "compressed_step_headline.json" in fz["status"]       # file does not exist in the scratch root
    rs = t["rows"][3]
    assert rs["headline_with_det"] is None and "three-layer.json" in rs["status"]
    (tmp_path / "results" / "fuzzy" / "compressed_step_headline.json").write_text("{}")                  # once the file exists the fuzzy row is final
    assert R.gate_table(out=False, root=tmp_path)["rows"][4]["status"] == "final"


def _synthetic_spectra():
    """Minimal spectra.json content with every key `render` reads (synthetic numbers; only the structure matters here)."""
    fb = [{"signs": [1, 1, -1, -1], "dim": 2, "ks_level_distance": {"0.5": 0.0, "1.0": 0.0, "2.0": 0.0}},
          {"signs": [1, 1, 1, 1], "dim": 3, "ks_level_distance": {"0.5": 1.0, "1.0": 1.0, "2.0": 1.0}}]
    emb = {m: {"isometry": 0.0, "U": 0.0, "L": 0.0, "R": 0.0, "HE": 0.0, "P_commutes_generators": 0.0, "plaquette": 0.0, "phase": [1.0, 0.0],
               "leak_U_sq": 0.5, "leak_plaquette_sq": 15.0} for m in ("rishon_plus", "fuzzy_one")}
    cst = {"g2": [1.0], "ks": {"1.0": [-0.5, 2.0]}, "rishon": {"lam_d=0": {"1.0": [-1.0] * 17}}, "fuzzy": {"r=0": {"1.0": [0.0] * 9}, "r=1": {"1.0": [0.1] * 12}}}
    return {"schema": "crosscheck-spectra-1",
            "ks": {"max_pairwise_level_dev": {"1.0": 1e-14}, "transported_target_max": 1e-15, "headline_skipped": [
                {"circuit": "twelve", "target": "spinnet", "which": "headline", "reason": "synthetic reason"}], "cross_verdicts": [
                {"circuit": "twelve", "target": "lsh", "which": "general", "entry": None, "alpha": 0.37, "beta": 0.61, "ok": True, "certified": True,
                 "total_error": 1e-13, "mutant": {"beta_shift": 1e-6, "ok": False, "block_error": 2e-6}}]},
            "embedding": emb,
            "rishon_ks_limit": {"full": [{"g2": 1.0, "L": 64.0, "max_dev": 0.1, "L_times_max_dev": 6.4, "gap_to_next_band": 247.0}],
                                "dropped_images": {"HB": {"images_outside_code": 0, "outside_weight_max": 0.0}, "HD": {"images_outside_code": 0, "outside_weight_max": 0.0}},
                                "block_sizes": {"n_blocks": 305, "largest": 4352}},
            "fuzzy": {"flavour_blocks": fb, "isolated": {"k2_only": {"slope_first_pair": 7.0}, "r1": {"slope_first_pair": 7.0, "gap_over_2g2_at_16": 1.0}}},
            "closed_sector_table": cst, "not_comparable": {"rishon_step_distance_to_ks_step": 1.99, "source": "synthetic"}}


def test_render_and_figure_from_files(monkeypatch, tmp_path):
    """Everything is built in tmp_path: a synthetic spectra.json and a gate table from synthetic headline rankings."""
    monkeypatch.setattr(R, "_cached_headline", lambda enc, kind, root: (_fake_headline(enc) if enc != "lsh" else None, None if enc != "lsh" else "synthetic: pending"))
    cd = tmp_path / "results" / "crosscheck"
    cd.mkdir(parents=True)
    (cd / "spectra.json").write_text(json.dumps(_synthetic_spectra()))
    R.gate_table(out=cd / "gate-table.json", root=ROOT)               # general numbers are read from the committed step files
    text = R.render(root=tmp_path)
    for word in ("Kogut-Susskind", "quantum link", "fuzzy", "different model", "T_avg", "spectra.json", "gate-table.json", "Table 1", "Table 2", "Table 3",
                 "synthetic reason", "2.0000e-06"):
        assert word in text, word
    assert "pending" in text
    fig = R.tradeoff_figure(root=tmp_path)
    assert fig == cd / "tradeoff.pdf" and fig.stat().st_size > 1000


def test_gate_table_and_spectra_are_written_to_a_given_path(monkeypatch, tmp_path):
    out = tmp_path / "sub" / "gate.json"
    d = R.gate_table(out=out, root=ROOT, command="python scripts/m11_results.py --test")
    assert json.loads(out.read_text()) == d and d["provenance"]["command"].endswith("--test")
    assert d["schema"] == "crosscheck-gate-table-1" and not (tmp_path / "results").exists()      # out=<path> writes only there


@pytest.mark.parametrize("model,leak_u,leak_w", [("rishon_plus", 0.5, 15.0), ("fuzzy_fplus", 1.0, 4.0)])
def test_embedding_record_stores_squared_leaks(model, leak_u, leak_w):
    rec = R._embedding_record(model)
    for k in ("isometry", "U", "L", "R", "HE", "P_commutes_generators", "plaquette"):
        assert 0.0 <= rec[k] <= 1e-12, k
    assert abs(rec["leak_U_sq"] - leak_u) <= 1e-9 and abs(rec["leak_plaquette_sq"] - leak_w) <= 1e-6
    assert rec["phase"] == [1.0, 0.0] and set(rec) >= {"leak_U_sq", "leak_plaquette_sq", "phase"}


def test_m11_results_takes_one_git_snapshot_before_any_write(monkeypatch, tmp_path):
    """The first output file dirties the tree; both files must still carry the pre-write git state (bug: gate-table.json said dirty on a clean checkout)."""
    import importlib.util

    from su2plaq.metrics import provenance as P

    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(P, "_git", lambda *a: ("abc1234" if a[0] == "rev-parse" else ("M results/crosscheck/spectra.json" if (out / "spectra.json").exists() else "")))
    assert R.git_snapshot() == {"git_commit": "abc1234", "git_dirty": False}
    orig_gate = R.gate_table

    def fake_spectra(out=None, root=None, headline=True, command=None, **kw):
        d = {"ks": {"cross_verdicts": [], "headline_skipped": []}, "provenance": R._prov(command, **kw)}
        R._write_json(d, tmp_path / "out" / "spectra.json")
        return d

    monkeypatch.setattr(R, "spectra_results", fake_spectra)
    monkeypatch.setattr(R, "gate_table", lambda out=None, root=None, command=None, **kw: orig_gate(out=tmp_path / "out" / "gate-table.json", root=ROOT, command=command, **kw))
    monkeypatch.setattr(R, "_cached_headline", lambda enc, kind, root: (None, "synthetic: pending"))
    monkeypatch.setattr(R, "tradeoff_figure", lambda root=None: tmp_path / "out" / "tradeoff.pdf")
    monkeypatch.setattr(R, "render", lambda root=None: "")
    spec = importlib.util.spec_from_file_location("m11_results_script", ROOT / "scripts" / "m11_results.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main(["--no-headline"])
    ps = [json.loads((out / f).read_text())["provenance"] for f in ("spectra.json", "gate-table.json")]
    assert [p["git_dirty"] for p in ps] == [False, False]
    assert ps[0]["git_commit"] == ps[1]["git_commit"] == "abc1234"
    assert P._git("status") != ""                                      # the simulated first write did dirty the tree
