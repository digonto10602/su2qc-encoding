"""Unit tests of su2plaq.compress.replay (prompts/008 step B7): dry replay of a kind-`UE` twelve seed round under a temporary root,
record schema, backups, byte-for-byte restore of the attempts log, refusal of a reused tag, `latest_record`, the Lean carry-over,
and the exit code of the CLI.  Everything happens under tmp_path (never the real results/ or compress/ trees)."""
import hashlib
import json

import pytest

from su2plaq.compress import archive as A
from su2plaq.compress import provenance as P
from su2plaq.compress import replay as RP
from su2plaq.compress.round import run_round
from su2plaq.compress.spec import default_spec

ENC, KIND = "twelve", "UE"


@pytest.fixture(scope="module")
def replayed(tmp_path_factory):
    root = tmp_path_factory.mktemp("replay_root_twelve")
    run_round(ENC, KIND, 0, evaluate=True, root=root, lean=False)
    rdir = root / "results" / "compress" / ENC
    f = rdir / "round-000.json"
    d = json.loads(f.read_text())
    d["evaluator_sha256"] = "0" * 64                # stale hash on purpose: what a replay is for
    f.write_text(json.dumps(d, indent=1))
    # a Lean record on the best entry: must be carried over (the program is unchanged)
    arch = A.Archive.load(ENC, root=root, n_alt=len(default_spec(ENC, KIND).alt_angles), strict=True)
    best = arch.best()
    best.lean = {"status": "certified", "marker": "carry-me"}
    arch.save()
    attempts = root / "compress" / "attempts" / f"{ENC}.jsonl"
    disc = root / "compress" / "discoveries" / f"{ENC}.md"
    before = {p.name: (hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None) for p in (attempts, disc)}
    first = json.loads(f.read_text())
    res = RP.replay(ENC, KIND, root=root, tag="t1")
    return root, first, res, before, best.id


def test_record_schema_backup_and_hashes(replayed):
    root, first, res, _, _ = replayed
    rdir = root / "results" / "compress" / ENC
    assert res["tag"] == "t1" and res["encoding"] == ENC and res["kind"] == KIND and res["rounds"] == [0]
    assert res["evaluator_sha256"] == P.stamp_hash(ENC) and res["encoding_sha256"] == P.code_hash_for(ENC)
    assert res["evaluator_sha256_old"] == ["0" * 64] and "prune_fraction" not in res
    assert res["lost"] == [] and len(res["entries"]) == len(first["candidates"]) >= 1
    assert res["best_new"]["key"] == res["best_old"]["key"] and res["best_new"]["id"] == res["best_old"]["id"]
    for e in res["entries"]:
        assert e["old"]["valid"] == e["new"]["valid"] and e["old"]["reason"] == e["new"]["reason"]
        if e["new"]["valid"]:
            assert e["key_equal"] is True
    assert json.loads((rdir / "replay-t1.json").read_text())["written_utc"] == res["written_utc"]
    assert (rdir / "pre-t1" / "round-000.json").exists() and (root / "compress" / "archive" / f"{ENC}-pre-t1" / "index.json").exists()
    assert json.loads((rdir / "round-000.json").read_text())["evaluator_sha256"] == P.stamp_hash(ENC)
    assert res["attempts_unchanged"] is True and res["discoveries_unchanged"] is True and isinstance(res["provenance"]["git_commit"], str)
    arch = A.Archive.load(ENC, root=root, n_alt=len(default_spec(ENC, KIND).alt_angles), strict=True)
    assert arch.rejected == [] and all(x.evaluator_sha256 == P.stamp_hash(ENC) for x in arch.entries())


def test_logs_restored_tag_refused_latest_record_and_lean_carried(replayed):
    root, _, res, before, best_id = replayed
    for name, path in ((f"{ENC}.jsonl", root / "compress" / "attempts" / f"{ENC}.jsonl"), (f"{ENC}.md", root / "compress" / "discoveries" / f"{ENC}.md")):
        assert (hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None) == before[name]
    with pytest.raises(ValueError, match="already exists"):
        RP.replay(ENC, KIND, root=root, tag="t1")
    with pytest.raises(ValueError, match="belong to"):
        RP.replay(ENC, "step", root=root, tag="t2")          # refused before anything is moved
    assert not (root / "results" / "compress" / ENC / "pre-t2").exists()
    assert RP.latest_record(ENC, root=root)["tag"] == "t1"
    assert RP.latest_record("spinnet", root=root) is None
    assert best_id in res["lean_carried"]
    arch = A.Archive.load(ENC, root=root, n_alt=len(default_spec(ENC, KIND).alt_angles), strict=True)
    assert next(x for x in arch.entries() if x.id == best_id).lean == {"status": "certified", "marker": "carry-me"}
    rd = json.loads((root / "results" / "compress" / ENC / "round-000.json").read_text())
    assert next(c for c in rd["candidates"] if c["id"] == best_id)["lean"]["marker"] == "carry-me"


def test_refuses_empty_root(tmp_path):
    with pytest.raises(ValueError, match="no round files"):
        RP.replay(ENC, KIND, root=tmp_path)


def test_latest_record_orders_by_written_utc_then_mtime(tmp_path):
    d = tmp_path / "results" / "compress" / "x"
    d.mkdir(parents=True)
    (d / "replay-a.json").write_text(json.dumps({"tag": "a", "written_utc": "2026-11-16T10:00:00Z"}))
    (d / "replay-b.json").write_text(json.dumps({"tag": "b", "written_utc": "2026-11-16T09:00:00Z"}))
    assert RP.latest_record("x", root=tmp_path)["tag"] == "a"
    (d / "replay-c.json").write_text(json.dumps({"tag": "c"}))            # no field: file modification time (now, later than a and b)
    assert RP.latest_record("x", root=tmp_path)["tag"] == "c"


def _fake(entries, lost):
    return {"tag": "x", "rounds": [0], "newly_valid": [], "lost": lost, "entries": entries, "best_old": {"id": None, "key": None},
            "best_new": {"id": None, "key": None}, "wall_s": 1.0}


@pytest.mark.parametrize("key_equal, lost, code, text", [
    ([True, None], [], 0, ""),
    ([True, False], [], 1, "r00-b"),
    ([True, True], ["r00-c"], 1, "r00-c"),
])
def test_cli_exit_code_covers_changed_keys_and_lost(monkeypatch, capsys, key_equal, lost, code, text):
    entries = [{"id": f"r00-{c}", "key_equal": k} for c, k in zip("ab", key_equal)]
    seen = {}
    monkeypatch.setattr(RP, "replay", lambda enc, kind, **k: seen.update(enc=enc, kind=kind, **k) or _fake(entries, lost))
    assert RP.main(["--encoding", "twelve", "--kind", "step", "--tag", "x"]) == code
    cap = capsys.readouterr()
    assert (text in cap.err) if code else cap.err == ""
    assert seen["enc"] == "twelve" and seen["kind"] == "step" and seen["tag"] == "x" and seen["lean"] is False
    assert RP.problems(_fake(entries, lost))["lost"] == lost


def test_cli_default_kind_is_the_registry_loop_kind(monkeypatch):
    seen = {}
    monkeypatch.setattr(RP, "replay", lambda enc, kind, **k: seen.update(kind=kind) or _fake([], []))
    assert RP.main(["--encoding", "fuzzy_link"]) == 0 and seen["kind"] == "UE"
