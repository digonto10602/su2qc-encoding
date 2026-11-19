"""B6 finding F1 (reports/tests/419): `robust.headline(..., compute=False)` never computes and never writes, also for the encodings
served by a `headline` hook (spinnet, rishon).  Self-contained: every test builds a small toy archive, programs, cache and summary.json in
`tmp_path` (passed as `root=`); the real results/ and compress/ trees are never read, so replays of the real archives cannot break it."""
import hashlib
import json
import pathlib
from types import SimpleNamespace

import pytest

from su2plaq.compress import archive as A
from su2plaq.compress import provenance as P
from su2plaq.compress import report as RP
from su2plaq.compress import robust as RB
from su2plaq.encodings import registry

HOOKED = [("spinnet", "step"), ("rishon", "step")]
ENTRIES = [("r01-F1-001", (32, 832, 1583, 18), (32, 16948, 0, 33256, 18), "certified"),         # archive best, angle-linear
           ("r02-F2-002", (33, 840, 1600, 18), (33, 16000, 1, 33500, 18), None),                   # not angle-linear
           ("r03-F1-003", (34, 850, 1700, 19), None, None)]                                          # skeleton changes in the set: no robust key


def _record(i, key, rkey, sha):
    return {"program_sha256": sha, "angle_set_sha256": RB.angle_set_sha256(), "skeleton_equal": rkey is not None,
            "t_eps": [rkey[1] // 20] * 20 if rkey else [0] * 20, "depth_ct": [rkey[3] // 20] * 20 if rkey else [0] * 20,
            "t_sum": rkey[1] if rkey else 0, "depth_sum": rkey[3] if rkey else 0, "t_mean": rkey[1] / 20 if rkey else 0.0, "cx": key[0],
            "qubits": key[3], "angle_linear": bool(rkey) and rkey[2] == 0, "export_status": "ok", "robust_key": rkey,
            "laptop_key": list(key)}


def _toy(enc, tmp_path, monkeypatch, fresh=True):
    """A toy tree for `enc` under tmp_path: programs, an Archive.load stub over three entries, results/compress/<enc>/{robust.json,
    summary.json,round-000.json}.  `fresh`: robust.json carries the keys that make it current for the code of `enc`."""
    entries, recs = [], {}
    for i, (eid, key, rkey, lean) in enumerate(ENTRIES):
        f = tmp_path / "compress" / "programs" / enc / "F1" / f"{i:03d}-x.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# toy {eid}\n")
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        entries.append(SimpleNamespace(id=eid, program_path=str(f.relative_to(tmp_path)), program_sha256=sha, valid=True, key=key,
                                       family=eid.split("-")[1], round=i + 1, lean=None if lean is None else {"status": lean}))
        recs[eid] = _record(i, key, rkey, sha)
    best = min(entries, key=lambda e: (tuple(e.key), e.id))
    monkeypatch.setattr(A.Archive, "load", classmethod(lambda cls, *a, **k: SimpleNamespace(entries=lambda: list(entries), best=lambda: best)))
    rdir = tmp_path / "results" / "compress" / enc
    rdir.mkdir(parents=True)
    cache = {"angle_set": RB._angle_set_record(), "evaluator_sha256": P.stamp_hash(enc) if fresh else "0" * 64, "entries": recs}
    if enc == "spinnet" and fresh:
        from su2plaq.spinnet.loop import code_hash

        cache["spinnet_code_sha256"] = code_hash()
    (rdir / "robust.json").write_text(json.dumps(cache, indent=1))
    rid = entries[0]
    rec = {"label": "001-x", "id": rid.id, "family": "F1", "program_sha256": rid.program_sha256, "program_path": rid.program_path, "valid": True,
           "key": list(rid.key), "metrics": {"cx": rid.key[0], "t_eps": rid.key[1], "depth_ct": rid.key[2], "qubits": rid.key[3]}, "verdict": {"ok": True},
           "lean": None, "round": 1, "parent": None, "parent_known": True}
    (rdir / "round-001.json").write_text(json.dumps({"round": 1, "entries": [rid.id], "candidates": [rec], "external": []}))
    (rdir / "summary.json").write_text(json.dumps({"encoding": enc, "kind": "step", "n_valid": 1, "t_avg": {rid.id: 1.0},
                                                   "headline": {"id": rid.id, "robust_key": list(ENTRIES[0][2]), "t_mean": 847.4,
                                                                "angle_set_sha256": RB.angle_set_sha256()}}, indent=1))
    return tmp_path


def _tree_digest(root, enc):
    d = root / "results" / "compress" / enc
    return {str(p.relative_to(root)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in sorted(d.rglob("*")) if p.is_file()}


@pytest.fixture
def no_build(monkeypatch):
    """Any program rebuild (the expensive path) is an error; counts the calls of the track and shared `robust_metrics`."""
    calls = []

    def boom(*a, **k):
        calls.append(a)
        raise AssertionError("a program was rebuilt although compute=False")

    from su2plaq.rishon.compress import robust as RR
    from su2plaq.spinnet import loop as SL

    for mod in (RB, RR, SL):
        monkeypatch.setattr(mod, "robust_metrics", boom)
    return calls


@pytest.mark.parametrize("enc,kind", HOOKED)
def test_compute_false_stale_cache_returns_none_without_build_or_write(enc, kind, tmp_path, monkeypatch, no_build):
    root = _toy(enc, tmp_path, monkeypatch)
    f = root / "results" / "compress" / enc / "robust.json"
    cache = json.loads(f.read_text())
    cache["evaluator_sha256"] = "0" * 64                      # stale: the hook would recompute every entry
    f.write_text(json.dumps(cache, indent=1))
    before = _tree_digest(root, enc)
    assert RB.headline(enc, kind, root=root, compute=False) is None
    assert RB.report_rows(enc, kind, root=root) == []
    assert _tree_digest(root, enc) == before and no_build == []


@pytest.mark.parametrize("enc,kind", HOOKED)
def test_compute_false_missing_cache_and_refresh(enc, kind, tmp_path, monkeypatch, no_build):
    root = _toy(enc, tmp_path, monkeypatch)
    f = root / "results" / "compress" / enc / "robust.json"
    assert RB.headline(enc, kind, root=root, compute=False, refresh=True) is None        # refresh would recompute
    f.unlink()
    assert RB.headline(enc, kind, root=root, compute=False) is None
    assert not f.exists() and no_build == []


@pytest.mark.parametrize("enc,kind", HOOKED)
def test_compute_false_fresh_cache_equals_the_hook_and_writes_nothing(enc, kind, tmp_path, monkeypatch, no_build):
    root = _toy(enc, tmp_path, monkeypatch)
    f = root / "results" / "compress" / enc / "robust.json"
    cache = json.loads(f.read_text())
    cache["evaluator_sha256"] = P.stamp_hash(enc)             # make the copy's cache current: only its keys are changed
    if enc == "spinnet":
        from su2plaq.spinnet.loop import code_hash

        cache["spinnet_code_sha256"] = code_hash()
    f.write_text(json.dumps(cache, indent=1))
    before = _tree_digest(root, enc)
    h = RB.headline(enc, kind, root=root, compute=False)
    assert h is not None and h["id"] is not None and _tree_digest(root, enc) == before
    hook = registry.resolve(registry.info(enc).headline)(kind, root, False)     # the track's own function on the same cache (no rebuild needed)
    assert (h["id"], tuple(h["robust_key"]), h["archive_best"]) == (hook["id"], tuple(hook["robust_key"]), hook["archive_best"])
    assert [(r["id"], r["robust_key"]) for r in h["ranking"]] == [(r["id"], r["robust_key"]) for r in hook["ranking"] if r["robust_key"] is not None]
    assert no_build == []
    # the report table of the copy: prints the headline rows from the cache, does not touch robust.json
    robust_bytes = f.read_bytes()
    text = RP.report_table(enc, kind, root=root)
    assert "HEADLINE (robust key): " + h["id"] in text and f.read_bytes() == robust_bytes and no_build == []


def test_compute_true_still_delegates_to_the_hook(monkeypatch, tmp_path):
    seen = []

    def hook(kind, root, refresh):
        seen.append((kind, refresh))
        return {"id": None, "robust_key": None, "t_mean": None, "lean": None, "archive_best": None, "archive_best_robust_key": None,
                "ranking": []}

    monkeypatch.setattr(registry, "resolve", lambda s, _r=registry.resolve: hook if s == "x:hook" else _r(s))
    monkeypatch.setitem(registry._TABLE, "spinnet", registry.info("spinnet").__class__(**{**registry.info("spinnet").__dict__, "headline": "x:hook"}))
    h = RB.headline("spinnet", "step", root=tmp_path, refresh=True)
    assert seen == [("step", True)] and h["unrankable"] == []


# ---------------------------------------------------------------------------------------------- N1: a stale cache never degrades summary.json
@pytest.mark.parametrize("enc,kind", HOOKED)
def test_generic_report_leaves_a_track_summary_unchanged_and_names_the_refresh_command(enc, kind, tmp_path, monkeypatch, no_build):
    root = _toy(enc, tmp_path, monkeypatch)
    sf = root / "results" / "compress" / enc / "summary.json"
    before = sf.read_bytes()
    assert "headline" in json.loads(before) and "t_avg" in json.loads(before)
    f = root / "results" / "compress" / enc / "robust.json"
    cache = json.loads(f.read_text())
    cache["evaluator_sha256"] = "0" * 64                                    # stale cache
    f.write_text(json.dumps(cache, indent=1))
    text = RP.report_table(enc, kind, root=root)
    assert sf.read_bytes() == before and "stale or missing" in text and RP.refresh_command(enc, kind, root) in text
    assert "python -m su2plaq." in text and "--root" in text and no_build == []
    cache["evaluator_sha256"] = P.stamp_hash(enc)                           # a fresh cache: still not rewritten by the generic table
    if enc == "spinnet":
        from su2plaq.spinnet.loop import code_hash

        cache["spinnet_code_sha256"] = code_hash()
    f.write_text(json.dumps(cache, indent=1))
    text = RP.report_table(enc, kind, root=root)
    assert sf.read_bytes() == before and "HEADLINE (robust key): " in text and "written by the track report" in text


def test_refresh_commands():
    assert RP.refresh_command("spinnet", "step") == "python -m su2plaq.spinnet.loop report"
    assert RP.refresh_command("rishon", "step") == "python -m su2plaq.rishon.compress.robust report --kind step"
    assert RP.refresh_command("fuzzy_ub", "UB") == "python -m su2plaq.compress.robust --encoding fuzzy_ub --kind UB"


def test_generic_report_keeps_an_existing_headline_block_and_writes_otherwise(tmp_path, monkeypatch):
    """twelve (no hook): with a `headline` block in summary.json and no usable cache the file is not rewritten; without a block it is
    refreshed from the round files; `headline=False` (the track reports) always writes."""
    root = _toy("twelve", tmp_path, monkeypatch, fresh=False)
    (root / "results" / "compress" / "twelve" / "robust.json").unlink()                 # no usable headline cache
    sf = root / "results" / "compress" / "twelve" / "summary.json"
    d = json.loads(sf.read_text())
    d.pop("headline", None)
    d["n_valid"] = -1                                       # a value the report would change
    sf.write_text(json.dumps(d))
    text = RP.report_table("twelve", "step", root=root)
    assert json.loads(sf.read_text())["n_valid"] == 1 and "stale or missing" not in text      # no block: refreshed as before
    d = json.loads(sf.read_text())
    d["headline"] = {"id": "r00-x", "robust_key": None, "t_mean": 1.0, "angle_set_sha256": "x"}
    d["n_valid"] = -1
    sf.write_text(json.dumps(d))
    before = sf.read_bytes()
    text = RP.report_table("twelve", "step", root=root)
    assert sf.read_bytes() == before and "stale or missing" in text and "python -m su2plaq.compress.robust --encoding twelve" in text
    RP.report_table("twelve", "step", root=root, headline=False)
    assert json.loads(sf.read_text())["n_valid"] == 1


def test_robust_cli_computes_the_headline_and_prints_one_json_line(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(RB, "headline", lambda enc, kind, root=None, refresh=False, compute=True: seen.update(enc=enc, kind=kind, refresh=refresh)
                        or {"id": "r01-A-001", "robust_key": (1, 2, 0, 3, 4), "t_mean": 1.0, "archive_best": "r01-A-001", "unrankable": []})
    assert RB.main(["--encoding", "fuzzy_ub"]) == 0
    assert seen == {"enc": "fuzzy_ub", "kind": "UB", "refresh": False} and json.loads(capsys.readouterr().out)["id"] == "r01-A-001"
