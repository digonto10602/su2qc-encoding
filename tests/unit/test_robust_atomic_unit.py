"""Race fix of `robust.headline(..., compute=True)` (reports/tests/428 §4): the cache is written once, atomically, through a unique
temporary name, so parallel workers never collide and a reader never sees a partial file.  Toy archive, stubbed `robust_metrics`."""
import hashlib
import json
import multiprocessing as mp
import pathlib
from types import SimpleNamespace

import pytest

from su2plaq.compress import archive as A
from su2plaq.compress import robust as RB
from su2plaq.compress.spec import default_spec

ENC = "toyenc"
N_ENTRIES = 6


def _toy(monkeypatch, root):
    entries, table = [], {}
    for i in range(N_ENTRIES):
        f = root / "compress" / "programs" / ENC / "F1" / f"{i:03d}-x.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# toy {i}\n")
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        key = (30 + i, 800 + i, 1500, 17)
        rkey = (30 + i, 16000 + 20 * i, 0, 33000, 17)
        entries.append(SimpleNamespace(id=f"r0{i}-F1-00{i}", program_path=str(f.relative_to(root)), program_sha256=sha, valid=True, key=key,
                                       family="F1", round=i, lean=None))
        table[f.name] = {"program_sha256": sha, "angle_set_sha256": RB.angle_set_sha256(), "skeleton_equal": True, "t_eps": [rkey[1] // 20] * 20,
                         "depth_ct": [rkey[3] // 20] * 20, "t_sum": rkey[1], "depth_sum": rkey[3], "t_mean": rkey[1] / 20, "cx": key[0],
                         "qubits": key[3], "angle_linear": True, "export_status": "ok", "robust_key": rkey, "offset_class": "linear",
                         "offset_units": None}
    best = min(entries, key=lambda e: (tuple(e.key), e.id))
    monkeypatch.setattr(A.Archive, "load", classmethod(lambda cls, *a, **k: SimpleNamespace(entries=lambda: list(entries), best=lambda: best)))
    monkeypatch.setattr(RB, "robust_metrics", lambda encoding, kind, path, root=None: dict(table[pathlib.Path(path).name]))
    monkeypatch.setattr("su2plaq.compress.spec.default_spec", lambda e, k: default_spec("fuzzy_link", "UE"))


def _writer(args):
    root, n = args
    ids = []
    for _ in range(n):
        h = RB.headline(ENC, "step", root=root, refresh=True)
        ids.append(h["id"])
    return ids


def test_atomic_write_unique_tmp_no_leftovers_and_identical_content_not_rewritten(tmp_path):
    f = tmp_path / "d" / "robust.json"
    RB._atomic_write_text(f, '{"a": 1}')
    assert f.read_text() == '{"a": 1}' and [p.name for p in f.parent.iterdir()] == ["robust.json"]
    m = f.stat().st_mtime_ns
    RB._atomic_write_text(f, '{"a": 1}')
    assert f.stat().st_mtime_ns == m                                    # identical content: file untouched
    RB._atomic_write_text(f, '{"a": 2}')
    assert json.loads(f.read_text()) == {"a": 2} and [p.name for p in f.parent.iterdir()] == ["robust.json"]


def test_atomic_write_failure_leaves_old_file_and_no_tmp(tmp_path, monkeypatch):
    f = tmp_path / "robust.json"
    f.write_text('{"ok": true}')
    monkeypatch.setattr(RB.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(OSError):
        RB._atomic_write_text(f, '{"ok": false}')
    assert f.read_text() == '{"ok": true}' and [p.name for p in tmp_path.iterdir()] == ["robust.json"]


def test_cache_is_written_once_after_the_loop(tmp_path, monkeypatch):
    _toy(monkeypatch, tmp_path)
    writes = []
    orig = RB._atomic_write_text
    monkeypatch.setattr(RB, "_atomic_write_text", lambda p, t: (writes.append(pathlib.Path(p).name), orig(p, t))[1])
    RB.headline(ENC, "step", root=tmp_path)
    assert writes == ["robust.json"]                                     # one write for N_ENTRIES entries (no summary.json in the toy tree)
    assert len(json.loads((tmp_path / "results" / "compress" / ENC / "robust.json").read_text())["entries"]) == N_ENTRIES


def test_two_concurrent_writers_and_a_reader_never_fail_or_see_a_partial_cache(tmp_path, monkeypatch):
    _toy(monkeypatch, tmp_path)
    RB.headline(ENC, "step", root=tmp_path)                              # the cache exists before the race
    f = tmp_path / "results" / "compress" / ENC / "robust.json"
    expected = f.read_text()
    ctx = mp.get_context("fork")                                         # the children inherit the stubs of this process
    with ctx.Pool(2) as pool:
        r = pool.map_async(_writer, [(tmp_path, 12), (tmp_path, 12)])
        seen = 0
        while not r.ready():                                             # reader: every observed file is complete valid JSON
            d = json.loads(f.read_text())
            assert len(d["entries"]) == N_ENTRIES
            seen += 1
        out = r.get(timeout=120)                                         # re-raises a worker exception (FileNotFoundError before the fix)
    assert all(ids == [ids[0]] * 12 for ids in out) and out[0][0] == out[1][0]
    d = json.loads(f.read_text())
    assert len(d["entries"]) == N_ENTRIES and f.read_text() == expected
    assert sorted(p.name for p in f.parent.iterdir()) == ["robust.json"]  # no stray temporary files
    assert seen >= 0
