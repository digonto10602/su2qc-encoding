"""M2c-Y / M2c-G — the replay tool and the consolidation gate (prompts/008 §6, §7; METHODS §12).

Y1: `su2plaq.compress.replay.replay(encoding, kind, root, tag)` re-evaluates the recorded rounds of an archive in order under the
current code and writes `results/compress/<enc>/replay-<tag>.json` (schema of prompts/204 §6.2, any encoding); tested on a copy of
the smallest real archive (fuzzy_link) under a temporary root.
G1: every real archive was replayed under the consolidated code: its latest replay record and every entry carry the current
hashes; no entry that was valid before is lost and every such entry keeps its key exactly.
G2: `compress/lean/structure.json` carries the current exporter / checker fingerprints.
G3: the shared headline rule (robust key over the 20 locked angle pairs, prompts/104 §11 E3 = prompts/203 §13 E3, now for every
encoding) is defined on every archive and agrees with the track functions for spinnet and rishon.
G4 (audit 301 A2): the archive best and the headline of every encoding are valid at two further seeded angle pairs that no
loop evaluation used (plus kappa2 = 0 and the step's kappa2 = alpha/2 for the fuzzy link unit), with the nominal skeleton.

Tolerances: exact comparisons (hashes, keys, ids); G4 uses the loop's own exact-angle tolerance 1e-10 on `total_error`.
The G tests read the real archives: they are `PENDING` until step C1/C2 of prompts/008 has written the replay records.
"""
from __future__ import annotations

import json
import pathlib
import shutil

import numpy as np
import pytest

from tests.acceptance._api import api

UNITS = (("twelve", "step"), ("spinnet", "step"), ("rishon", "step"), ("fuzzy_ub", "UB"), ("fuzzy_link", "UE"))
GENERALITY_SEED = 20261110                                  # two extra pairs, same ranges as the locked 20-pair set
RANGES = ((0.05, 2.0), (0.05, 1.2))                         # prompts/104 §11 E3
LINK_EXTRA = ((0.37, 0.0), (0.37, 0.185))                   # fuzzy_link: kappa2 = 0 and the step's kappa2 = r alpha / 2 at r = 1 (audit 301 A2)
TOL = 1e-10


def _replay():
    return api("su2plaq.compress.replay")                    # PENDING until step B7


def _robust():
    return api("su2plaq.compress.robust")                    # PENDING until step B6


def _generality_pairs(enc):
    rng = np.random.default_rng(GENERALITY_SEED)
    a = rng.uniform(*RANGES[0], 2)
    b = rng.uniform(*RANGES[1], 2)
    pairs = [(float(x), float(y)) for x, y in zip(a, b)]
    return pairs + (list(LINK_EXTRA) if enc == "fuzzy_link" else [])


def _record_checks(rec, enc, kind):
    assert rec["encoding"] == enc and rec["kind"] == kind and isinstance(rec["tag"], str) and rec["tag"]
    assert rec["rounds"] == list(range(len(rec["rounds"]))) and len(rec["rounds"]) >= 1
    ents = {e["id"]: e for e in rec["entries"]}
    assert len(ents) == len(rec["entries"]) >= 1
    for e in rec["entries"]:
        if e["old"]["valid"]:
            assert e["new"]["valid"] and e["new"]["reason"] == "ok" and tuple(e["new"]["key"]) == tuple(e["old"]["key"]) and e["key_equal"] is True, e["id"]
    assert rec["lost"] == []
    assert set(rec["newly_valid"]) == {i for i, e in ents.items() if e["new"]["valid"] and not e["old"]["valid"]}
    assert tuple(rec["best_new"]["key"]) <= tuple(rec["best_old"]["key"]) and rec["best_new"]["id"] in ents
    assert rec["attempts_unchanged"] is True and rec["discoveries_unchanged"] is True
    assert isinstance(rec["provenance"]["git_commit"], str) and len(rec["provenance"]["git_commit"]) >= 7
    return ents


def test_M2C_Y1_replay_on_a_copy_of_the_link_archive(tmp_path, root):
    """Replay of the real fuzzy_link archive (4 entries, 3 rounds, seconds) copied under a temporary root: record schema and
    invariants, backups `pre-<tag>`, attempts / discoveries restored byte for byte, entries stamped with the current hashes,
    a second replay with the same tag refused, `latest_record` finds the record."""
    RP = _replay()
    P = api("su2plaq.compress.provenance")
    A = api("su2plaq.compress.archive")
    enc, kind, tag = "fuzzy_link", "UE", "t1"
    for rel in (f"compress/archive/{enc}", f"results/compress/{enc}", f"compress/programs/{enc}"):
        shutil.copytree(root / rel, tmp_path / rel)
    for rel in (f"compress/attempts/{enc}.jsonl", f"compress/discoveries/{enc}.md"):
        if (root / rel).exists():
            (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(root / rel, tmp_path / rel)
    for old in (tmp_path / "results" / "compress" / enc).glob("replay-*.json"):      # the copy starts without a replay history
        old.unlink()
    for old in list((tmp_path / "results" / "compress" / enc).glob("pre-*")) + list((tmp_path / "compress" / "archive").glob(f"{enc}-pre-*")):
        shutil.rmtree(old)
    attempts = (tmp_path / f"compress/attempts/{enc}.jsonl").read_bytes()
    n_old = len(A.Archive.load(enc, root=tmp_path).entries())
    assert n_old >= 4
    rec = RP.replay(enc, kind, root=tmp_path, tag=tag, lean=False)
    f = tmp_path / "results" / "compress" / enc / f"replay-{tag}.json"
    assert f.exists() and json.loads(f.read_text())["tag"] == tag == rec["tag"]
    ents = _record_checks(json.loads(f.read_text()), enc, kind)
    assert rec["evaluator_sha256"] == P.stamp_hash(enc) and rec["encoding_sha256"] == P.code_hash_for(enc)
    arch = A.Archive.load(enc, root=tmp_path, n_alt=2, strict=True)
    assert arch.rejected == [] and {x.id for x in arch.entries()} == {i for i, e in ents.items() if e["new"]["valid"]}
    assert len(arch.entries()) >= n_old
    assert all(x.evaluator_sha256 == P.stamp_hash(enc) and x.encoding_sha256 == P.code_hash_for(enc) for x in arch.entries())
    assert (tmp_path / "results" / "compress" / enc / f"pre-{tag}" / "round-000.json").exists()
    assert (tmp_path / "compress" / "archive" / f"{enc}-pre-{tag}" / "index.json").exists()
    assert (tmp_path / f"compress/attempts/{enc}.jsonl").read_bytes() == attempts
    assert RP.latest_record(enc, root=tmp_path)["tag"] == tag
    with pytest.raises(ValueError):
        RP.replay(enc, kind, root=tmp_path, tag=tag, lean=False)


@pytest.mark.parametrize("enc,kind", UNITS)
def test_M2C_G1_archive_replayed_under_current_code(enc, kind, root):
    """The real archive of every encoding: the latest replay record and every entry carry the current hashes; nothing valid
    was lost, keys are unchanged; the round files carry the same hash."""
    RP = _replay()
    P = api("su2plaq.compress.provenance")
    A = api("su2plaq.compress.archive")
    rec = RP.latest_record(enc, root=root)
    if rec is None:
        pytest.fail(f"PENDING: the {enc} archive has not been replayed under the consolidated code (prompts/008 steps C1/C2)", pytrace=False)
    _record_checks(rec, enc, kind)
    h, he = P.stamp_hash(enc), P.code_hash_for(enc)
    assert rec["evaluator_sha256"] == h, "a hashed file changed after the replay: replay again with a new tag"
    arch = A.Archive.load(enc, root=root)
    assert arch.entries() and arch.rejected == []
    assert all(x.evaluator_sha256 == h for x in arch.entries())
    assert all(x.encoding_sha256 == he for x in arch.entries())
    rounds = sorted((root / "results" / "compress" / enc).glob("round-*.json"))
    assert rounds and all(json.loads(r.read_text())["evaluator_sha256"] == h for r in rounds)


def test_M2C_G2_structure_json_is_current(root):
    """compress/lean/structure.json was regenerated after the last exporter / checker change (it went stale in the merges)."""
    api("su2plaq.encodings.registry")
    C = api("su2plaq.lean.certify")
    d = json.loads((root / "compress" / "lean" / "structure.json").read_text())
    assert d["provenance"]["exporter_sha256"] == C._exporter_sha(), "run python -m su2plaq.lean.structure --export (prompts/008 step C4)"
    assert d["provenance"]["checker_sha256"] == C.checker_sha256()
    assert d["provenance"]["structure_certificate"]["status"] == "certified"


@pytest.mark.slow
@pytest.mark.parametrize("enc,kind", UNITS)
def test_M2C_G3_headline_rule_on_every_archive(enc, kind, root):
    """One locked angle set for all encodings; `robust.headline(enc, kind)` returns the valid entry with the smallest robust key;
    for spinnet and rishon it is the track's own headline."""
    RB = _robust()
    A = api("su2plaq.compress.archive")
    L = api("su2plaq.spinnet.loop")
    RR = api("su2plaq.rishon.compress.robust")
    assert RB.ANGLE_SET_SEED == 20261107 and tuple(RB.ANGLE_SET) == tuple(L.ANGLE_SET) == tuple(RR.ANGLE_SET) and len(RB.ANGLE_SET) == 20
    assert RB.angle_set_sha256() == L.angle_set_sha256() == RR.angle_set_sha256()
    arch = A.Archive.load(enc, root=root)
    valid = {x.id for x in arch.entries() if x.valid}
    h = RB.headline(enc, kind, root=root)
    assert h["id"] in valid and h["robust_key"] is not None and h["archive_best"] == arch.best().id
    keyed = [tuple(r["robust_key"]) for r in h["ranking"] if r["robust_key"] is not None]
    ranked = {r["id"] for r in h["ranking"]}
    assert keyed and tuple(h["robust_key"]) == min(keyed) and h["id"] in ranked
    assert ranked | set(h["unrankable"]) <= valid and arch.best().id in ranked | set(h["unrankable"])   # entries without a program file are not ranked
    if enc == "spinnet":
        assert h["id"] == L.headline(root=root)["id"]
    if enc == "rishon":
        assert h["id"] == RR.headline(kind, root=root)["id"]
    s = json.loads((root / "results" / "compress" / enc / "summary.json").read_text())
    assert s["headline"]["id"] == h["id"]


@pytest.mark.slow
@pytest.mark.parametrize("enc,kind", UNITS)
def test_M2C_G4_best_and_headline_valid_at_unseen_angles(enc, kind, root):
    """Audit 301 A2: rebuilt from their program files at angle pairs that no loop evaluation used, the archive best and the
    headline keep the nominal skeleton and are exact (total_error <= 1e-10, certified) at each pair."""
    RB = _robust()
    A = api("su2plaq.compress.archive"); E = api("su2plaq.compress.evaluate")
    spec = api("su2plaq.compress.spec:default_spec")(enc, kind)
    arch = A.Archive.load(enc, root=root)
    ids = {arch.best().id, RB.headline(enc, kind, root=root)["id"]}
    pairs = _generality_pairs(enc)
    used = {(spec.alpha, spec.beta), *map(tuple, spec.alt_angles), *map(tuple, RB.ANGLE_SET)}
    assert not used & set(pairs)
    for i in sorted(ids):
        e = next(x for x in arch.entries() if x.id == i)
        specs = [spec] + [spec.with_angles(a, b) for a, b in pairs]
        circuits, _ = E._build_in_subprocess((root / e.program_path).read_bytes(), specs, E.BUILD_TIMEOUT_S)
        sk0 = E.skeleton(circuits[0])
        for sp, qc in zip(specs[1:], circuits[1:]):
            assert E.skeleton(qc) == sk0, (i, sp.alpha, sp.beta)
            r = E.evaluate_circuit(qc, sp, mode="full")
            assert r.valid and r.reason == "ok" and r.verdict.certified, (i, sp.alpha, sp.beta, r.reason, r.message)
            assert r.verdict.total_error <= TOL, (i, sp.alpha, sp.beta, r.verdict.total_error)
