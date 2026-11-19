"""Clean-up of the non-blocking notes of reports/audits/305 (N2-N7): replay `program_changed`, program-sha check of rebuilt headline
circuits, the `robust.json` constants key, the shared atomic write (unique temp name, mode), and the brief wording about offsets."""
import hashlib
import inspect
import io
import json
import os
import stat
from types import SimpleNamespace

import pytest

from su2plaq.compress import replay as RP
from su2plaq.compress import robust as RB
from su2plaq.compress import round as RD


# ------------------------------------------------------------------------------------------------ N2
def _res(old_sha, new_sha):
    e = {"id": "r00-F1-001", "key_equal": True, "program_sha256": new_sha}
    if old_sha is not _MISSING:
        e["old_program_sha256"] = old_sha
    return {"entries": [e], "lost": [], "tag": "t", "rounds": [0], "newly_valid": [], "best_old": None, "best_new": None, "wall_s": 1.0}


_MISSING = object()


def test_problems_flags_changed_program_sha_and_report_exits_1():
    assert RP.problems(_res("a" * 64, "a" * 64))["program_changed"] == []
    assert RP.problems(_res("a" * 64, "b" * 64))["program_changed"] == ["r00-F1-001"]
    out, err = io.StringIO(), io.StringIO()
    assert RP.report(_res("a" * 64, "a" * 64), out=out, err=err) == 0 and err.getvalue() == ""
    out, err = io.StringIO(), io.StringIO()
    assert RP.report(_res("a" * 64, "b" * 64), out=out, err=err) == 1
    assert "r00-F1-001" in err.getvalue() and "r00-F1-001" in json.loads(out.getvalue())["program_changed"]


def test_problems_record_without_old_sha_counts_none():
    assert RP.problems(_res(_MISSING, "b" * 64))["program_changed"] == []      # a record written before the field existed
    assert RP.problems(_res(None, "b" * 64))["program_changed"] == []


# ------------------------------------------------------------------------------------------------ N3
def test_check_program_sha(tmp_path):
    f = tmp_path / "compress" / "programs" / "x" / "p.py"
    f.parent.mkdir(parents=True)
    f.write_text("# a\n")
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    RD.check_program_sha("compress/programs/x/p.py", sha, root=tmp_path)
    RD.check_program_sha(str(f), sha)
    RD.check_program_sha("whatever.circuit", "0" * 64, root=tmp_path)           # circuit-valued baselines have no file
    f.write_text("# b\n")
    with pytest.raises(RD.ProgramShaMismatch):
        RD.check_program_sha("compress/programs/x/p.py", sha, root=tmp_path)


def test_ks_headline_circuit_refuses_a_modified_program(tmp_path, monkeypatch):
    from su2plaq.compress import archive as A
    from su2plaq.compress import evaluate as E
    from su2plaq.crosscheck import ks

    f = tmp_path / "compress" / "programs" / "twelve" / "p.py"
    f.parent.mkdir(parents=True)
    f.write_text("# a\n")
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    entry = SimpleNamespace(id="r00-F1-001", program_path=str(f.relative_to(tmp_path)), program_sha256=sha)
    monkeypatch.setattr(RB, "headline", lambda *a, **k: {"id": entry.id})
    monkeypatch.setattr(A.Archive, "load", classmethod(lambda cls, *a, **k: SimpleNamespace(entries=lambda: [entry])))
    built = []
    monkeypatch.setattr(E, "_build_in_subprocess", lambda src, specs, t: (built.append(src) or ["QC"], None))
    qc, info = ks.step_circuit("twelve", "headline", root=tmp_path)
    assert qc == "QC" and info["program_sha256"] == sha and built == [b"# a\n"]
    f.write_text("# changed\n")
    with pytest.raises(RD.ProgramShaMismatch):
        ks.step_circuit("twelve", "headline", root=tmp_path)
    assert len(built) == 1


def test_fuzzy_headline_step_checks_the_program_sha(tmp_path, monkeypatch):
    from su2plaq.compress import archive as A
    from su2plaq.fuzzy import headline_step as HS

    f = tmp_path / "p.py"
    f.write_text("# a\n")
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    entry = SimpleNamespace(id="r00-F1-001", program_path=str(f), program_sha256=sha)
    monkeypatch.setattr(RB, "headline", lambda *a, **k: {"id": entry.id, "ranking": [{"id": entry.id, "robust_key": (1, 2, 0, 3, 4)}]})
    monkeypatch.setattr(A.Archive, "load", classmethod(lambda cls, *a, **k: SimpleNamespace(entries=lambda: [entry])))
    assert HS._cached_unit("fuzzy_link", tmp_path)[0] is entry
    f.write_text("# changed\n")
    with pytest.raises(RD.ProgramShaMismatch):
        HS._cached_unit("fuzzy_link", tmp_path)


# ------------------------------------------------------------------------------------------------ N4
def _cache(tmp_path, name="robust.json", **extra):
    from su2plaq.compress import provenance as P

    f = tmp_path / name
    d = {"angle_set": RB._angle_set_record(), "evaluator_sha256": P.stamp_hash("fuzzy_link"),
         "encoding_sha256": P.code_hash_for("fuzzy_link"), "entries": {"x": {"k": 1}}, **extra}
    f.write_text(json.dumps(d))
    return f


def test_constants_sha_tracks_values_and_cache_key(tmp_path, monkeypatch):
    base = RB.robust_constants_sha256()
    assert base == RB.robust_constants_sha256() and len(base) == 64
    f = _cache(tmp_path, robust_constants_sha256=base)
    assert RB._load_cache(f, "fuzzy_link", False) == {"x": {"k": 1}}
    assert RB._load_cache(_cache(tmp_path, "legacy.json"), "fuzzy_link", False) == {"x": {"k": 1}}          # legacy cache without the key stays valid
    monkeypatch.setattr(RB, "LINEAR_TOL", 1e-8)
    assert RB.robust_constants_sha256() != base
    assert RB._load_cache(f, "fuzzy_link", False) == {}
    monkeypatch.setattr(RB, "LINEAR_TOL", 1e-9)
    monkeypatch.setattr(RB, "OFFSET_TOL", 1e-8)
    assert RB._load_cache(f, "fuzzy_link", False) == {}
    monkeypatch.setattr(RB, "OFFSET_TOL", 1e-9)
    monkeypatch.setattr(RB, "CLIFFORD_OFFSET_UNIT", {**RB.CLIFFORD_OFFSET_UNIT, "crz": RB.CLIFFORD_OFFSET_UNIT["crz"] / 2})
    assert RB._load_cache(f, "fuzzy_link", False) == {}
    monkeypatch.undo()
    assert RB._load_cache(f, "fuzzy_link", False) == {"x": {"k": 1}}


def test_committed_generic_caches_still_load():
    from su2plaq.compress.spec import ROOT

    for enc in ("twelve", "fuzzy_ub", "fuzzy_link"):
        assert RB._load_cache(ROOT / "results" / "compress" / enc / "robust.json", enc, False), enc


# ------------------------------------------------------------------------------------------------ N5, N6
def test_robust_writers_share_the_atomic_write():
    from su2plaq.rishon.compress import robust as RR
    from su2plaq.spinnet import loop as L

    assert L._atomic_write_text is RB._atomic_write_text and RR._atomic_write_text is RB._atomic_write_text
    for mod in (L, RR):
        assert ".json.tmp" not in inspect.getsource(mod)


def test_atomic_write_mode_follows_umask(tmp_path):
    old = os.umask(0o022)
    try:
        RB._atomic_write_text(tmp_path / "a.json", "{}")
        assert stat.S_IMODE((tmp_path / "a.json").stat().st_mode) == 0o644
        os.umask(0o077)
        RB._atomic_write_text(tmp_path / "b.json", "{}")
        assert stat.S_IMODE((tmp_path / "b.json").stat().st_mode) == 0o600
    finally:
        os.umask(old)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.json", "b.json"]


# ------------------------------------------------------------------------------------------------ N7
def test_offset_wording_distinguishes_controlled_rotations():
    from su2plaq.rishon.compress import robust as RR
    from su2plaq.spinnet import loop as L

    for text in (RB.HEADLINE_RULE_SECTION, RR.HEADLINE_SECTION,
                 L.HEADLINE_RULE_SECTION):
        if text is None:
            continue
        assert "`crz`/`crx`/`cry`/`cp` only multiples of" in text and "controlled-" in text
    assert RB.CLIFFORD_OFFSET_UNIT["rz"] == RB.CLIFFORD_OFFSET_UNIT["p"] and RB.CLIFFORD_OFFSET_UNIT["cp"] == 2 * RB.CLIFFORD_OFFSET_UNIT["p"]
