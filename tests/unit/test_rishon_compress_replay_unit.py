"""Unit test of su2plaq.rishon.compress.replay (prompts/204 step C1): a dry replay of a kind-`UE` round 0 in a temporary root.
The cap and the hash of the real archive are not touched: everything happens under tmp_path."""
import hashlib
import json

import pytest

from su2plaq.rishon.compress import code_hash, replay as RP
from su2plaq.rishon.compress.round import run_round


@pytest.fixture(scope="module")
def replayed(tmp_path_factory):
    root = tmp_path_factory.mktemp("replay_root")
    info = run_round("UE", 0, evaluate=True, root=root, lean=False)
    rdir = root / "results" / "compress" / "rishon"
    # stale hash on purpose: what a replay is for
    f = rdir / "round-000.json"
    d = json.loads(f.read_text())
    d["evaluator_sha256"] = "0" * 64
    f.write_text(json.dumps(d, indent=1))
    attempts = root / "compress" / "attempts" / "rishon.jsonl"
    disc = root / "compress" / "discoveries" / "rishon.md"
    before = {p.name: (hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None) for p in (attempts, disc)}
    first = json.loads((rdir / "round-000.json").read_text())
    res = RP.replay("UE", root=root)
    return root, info, first, res, before


def test_replay_record_and_backup(replayed):
    root, info, first, res, _ = replayed
    rdir = root / "results" / "compress" / "rishon"
    assert res["tag"] == "204" and res["kind"] == "UE" and res["rounds"] == [0] and res["prune_fraction"] == 0.1
    assert res["evaluator_sha256"] == code_hash() and res["evaluator_sha256_old"] == ["0" * 64]
    assert res["lost"] == [] and len(res["entries"]) == len(first["candidates"]) and res["best_new"]["key"] == res["best_old"]["key"]
    for e in res["entries"]:
        assert e["old"]["valid"] == e["new"]["valid"] and e["old"]["reason"] == e["new"]["reason"]
        if e["new"]["valid"]:
            assert e["key_equal"] is True and e["new"]["dropped_total"] <= 0.1 * 1e-10
    assert json.loads((rdir / "replay-204.json").read_text())["tag"] == "204"
    assert (rdir / "pre-204" / "round-000.json").exists() and (root / "compress" / "archive" / "rishon-pre-204" / "index.json").exists()
    assert json.loads((rdir / "round-000.json").read_text())["evaluator_sha256"] == code_hash()
    assert res["attempts_unchanged"] is True and res["discoveries_unchanged"] is True


def test_replay_restores_logs_and_refuses_twice(replayed):
    root, _, _, _, before = replayed
    for name, path in (("rishon.jsonl", root / "compress" / "attempts" / "rishon.jsonl"), ("rishon.md", root / "compress" / "discoveries" / "rishon.md")):
        now = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        assert now == before[name]
    with pytest.raises(ValueError):
        RP.replay("UE", root=root)
    with pytest.raises(ValueError, match="belong to"):
        RP.replay("step", root=root, tag="205")            # the round files are kind UE; refused before anything is moved
    assert not (root / "results" / "compress" / "rishon" / "pre-205").exists()


def test_replay_refuses_empty_root_and_wrong_kind(tmp_path):
    with pytest.raises(ValueError):
        RP.replay("UE", root=tmp_path)
