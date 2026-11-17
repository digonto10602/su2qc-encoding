"""B6 finding F1 (reports/tests/419): `robust.headline(..., compute=False)` never computes and never writes, also for the encodings
served by a `headline` hook (spinnet, rishon).  Works on temporary copies of the real archives (never the real results/ tree)."""
import hashlib
import json
import pathlib
import shutil

import pytest

from su2plaq.compress import report as RP
from su2plaq.compress import robust as RB
from su2plaq.compress.spec import ROOT
from su2plaq.encodings import registry

HOOKED = [("spinnet", "step"), ("rishon", "step")]


def _copy(enc, tmp_path):
    for rel in (f"compress/archive/{enc}", f"results/compress/{enc}", f"compress/programs/{enc}"):
        shutil.copytree(ROOT / rel, tmp_path / rel)
    for old in list((tmp_path / "results" / "compress" / enc).glob("pre-*")):
        shutil.rmtree(old)
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
def test_compute_false_stale_cache_returns_none_without_build_or_write(enc, kind, tmp_path, no_build):
    root = _copy(enc, tmp_path)
    f = root / "results" / "compress" / enc / "robust.json"
    cache = json.loads(f.read_text())
    cache["evaluator_sha256"] = "0" * 64                      # stale: the hook would recompute every entry
    f.write_text(json.dumps(cache, indent=1))
    before = _tree_digest(root, enc)
    assert RB.headline(enc, kind, root=root, compute=False) is None
    assert RB.report_rows(enc, kind, root=root) == []
    assert _tree_digest(root, enc) == before and no_build == []


@pytest.mark.parametrize("enc,kind", HOOKED)
def test_compute_false_missing_cache_and_refresh(enc, kind, tmp_path, no_build):
    root = _copy(enc, tmp_path)
    f = root / "results" / "compress" / enc / "robust.json"
    assert RB.headline(enc, kind, root=root, compute=False, refresh=True) is None        # refresh would recompute
    f.unlink()
    assert RB.headline(enc, kind, root=root, compute=False) is None
    assert not f.exists() and no_build == []


@pytest.mark.parametrize("enc,kind", HOOKED)
def test_compute_false_fresh_cache_equals_the_hook_and_writes_nothing(enc, kind, tmp_path, no_build):
    from su2plaq.compress import provenance as P

    root = _copy(enc, tmp_path)
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
