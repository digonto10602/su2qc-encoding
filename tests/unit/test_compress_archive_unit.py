"""Unit tests for su2plaq.compress.archive (M2 step 2.4)."""
import json
import math

import pytest

from su2plaq.compress import archive as A
from su2plaq.compress import evaluate as E
from su2plaq.compress.spec import default_spec

SPEC = default_spec("twelve", "UE")


def entry(id_, valid, cx, t, depth, qubits, family="F1", rnd=1, reason=None):
    ok = valid and reason in (None, "ok")
    return A.Entry(id=id_, program_path=f"compress/programs/twelve/{family}/{id_}.py", program_sha256="a" * 64, parent=None,
                   family=family, round=rnd, valid=valid, reason=reason or ("ok" if valid else "error"),
                   key=(cx, t, depth, qubits) if ok else (math.inf,) * 4,
                   cell=(int(math.floor(8 * math.log2(cx + 1))), int(math.floor(8 * math.log2(t + 1)))) if ok else None,
                   metrics_raw={"cx": cx, "t_eps": t, "depth_ct": depth, "qubits": qubits} if ok else {}, metrics_polished=None,
                   verdict_nominal={"ok": True, "certified": True} if ok else {}, verdicts_alt=[], skeleton_equal=True, discoveries=[],
                   summary="s", evaluator_sha256="e" * 64, spec_sha256="s" * 64, git_commit="0000000", versions={"qiskit": "2.5.2"},
                   seeds={}, machine="m", wall_s=0.1, written_utc="2026-11-05T00:00:00Z")


def test_roundtrip_elites_best_and_family_best(tmp_path):
    arch = A.Archive.load("twelve", root=tmp_path)
    assert arch.best() is None and arch.entries() == [] and arch.elites() == {}
    es = [entry("r01-F1-001", True, 100, 600, 500, 40), entry("r01-F1-002", True, 100, 590, 520, 40),
          entry("r01-F2-001", True, 60, 900, 400, 50, family="F2"), entry("r01-F3-001", True, 100, 590, 510, 40, family="F3")]
    assert all(arch.insert(e) for e in es)
    assert arch.best().id == "r01-F2-001" and arch.family_best("F1").id == "r01-F1-002" and arch.family_best("nope") is None
    # same cell as F1-002 but better depth: becomes the elite (lexicographic key CX > T > depth > qubits)
    assert {e.id for e in arch.elites().values()} == {"r01-F2-001", "r01-F3-001"}
    arch.save()
    arch2 = A.Archive.load("twelve", root=tmp_path)
    assert sorted(e.id for e in arch2.entries()) == sorted(e.id for e in es)
    assert arch2.best().id == "r01-F2-001" and isinstance(arch2.best().key, tuple) and isinstance(arch2.best().cell, tuple)
    idx = json.loads((tmp_path / "compress" / "archive" / "twelve" / "index.json").read_text())
    assert idx["best"] == "r01-F2-001" and set(idx["elites"].values()) == {"r01-F2-001", "r01-F3-001"}
    assert arch2.entries()[0].lean is None


def test_invalid_unverified_nonfinite_and_duplicates_are_refused(tmp_path):
    arch = A.Archive.load("twelve", root=tmp_path)
    assert not arch.insert(entry("r01-F1-009", False, 1, 1, 1, 1))
    assert not arch.insert(entry("r01-F1-010", False, 1, 1, 1, 1, reason="unverified"))
    nonfinite = entry("r01-F1-011", True, 1, 1, 1, 1)
    nonfinite.key = (1, math.inf, 1, 1)
    assert not arch.insert(nonfinite)
    wrong_reason = entry("r01-F1-012", True, 1, 1, 1, 1)
    wrong_reason.reason = "skeleton"
    assert not arch.insert(wrong_reason)
    assert arch.entries() == [] and arch.best() is None
    e = entry("r01-F1-001", True, 5, 5, 5, 5)
    assert arch.insert(e)
    with pytest.raises(ValueError):
        arch.insert(entry("r01-F1-001", True, 4, 4, 4, 4))


def test_entry_from_result_has_provenance_and_is_insertable(tmp_path):
    f = tmp_path / "007-p.py"
    f.write_text('"""SUMMARY: ue.\n"""\nFAMILY = "F9"\nPARENT = None\n\nfrom su2plaq.compress.builder import Builder\n\n\n'
                 'def build(spec):\n    b = Builder(spec)\n    d = b.reg("d")\n    for l in range(4):\n        b.p(-0.75 * spec.alpha, d[3 * l + 2])\n    return b\n')
    r = E.evaluate_program(f, SPEC, "full")
    e = A.entry_from_result(r, program_path=str(f), family="F9", round=3, parent="r02-F9-001")
    assert e.id == "r03-F9-007" and e.parent == "r02-F9-001" and e.valid and e.reason == "ok" and e.mode == "full"
    for name in ("program_sha256", "evaluator_sha256", "spec_sha256", "git_commit", "versions", "seeds", "machine", "wall_s", "written_utc"):
        assert getattr(e, name) not in (None, "", {})
    assert e.spec_sha256 == SPEC.sha256() and e.program_sha256 == r.program_sha256 and len(e.evaluator_sha256) == 64
    assert e.key == (0, e.metrics_raw["t_eps"], e.metrics_raw["depth_ct"], 28) and e.cell == (0, int(math.floor(8 * math.log2(e.key[1] + 1))))
    assert len(e.verdicts_alt) == 2 and e.verdict_nominal["ok"] and e.synthesis["measured"] is True
    arch = A.Archive.load("twelve", root=tmp_path)
    assert arch.insert(e)
    arch.save()
    again = A.Archive.load("twelve", root=tmp_path).best()
    assert again.to_dict() == e.to_dict()
    bad = f.with_name("008-bad.py")
    bad.write_text(f.read_text().replace("-0.75", "+0.75"))
    rb = E.evaluate_program(bad, SPEC, "trial")
    eb = A.entry_from_result(rb, program_path=str(bad), family="F9", round=3, parent=None)
    assert not eb.valid and eb.key == A.INVALID_KEY and eb.cell is None and not arch.insert(eb)


# ------------------------------------------------------------------------------------------------ tester 030: strict insert / load
import copy
import dataclasses

import numpy as np


def good(id_="r01-F1-001", **kw):
    e = entry(id_, True, 10, 100, 50, 30)
    return dataclasses.replace(e, **kw)


BAD = {
    "trial-mode result": dict(mode="trial"),
    "empty nominal verdict": dict(verdict_nominal={}),
    "nominal verdict not ok": dict(verdict_nominal={"ok": False, "certified": True}),
    "nominal verdict not certified": dict(verdict_nominal={"ok": True, "certified": False}),
    "alt verdict not ok": dict(verdicts_alt=[{"ok": True, "certified": True}, {"ok": False, "certified": True}]),
    "alt verdict not certified": dict(verdicts_alt=[{"ok": True, "certified": False}, {"ok": True, "certified": True}]),
    "alt verdict empty": dict(verdicts_alt=[{}, {"ok": True}]),
    "skeleton differs": dict(skeleton_equal=False),
    "key lower than the metrics": dict(key=(1, 1, 1, 1)),
    "cell not matching": dict(cell=(0, 0)),
    "empty metrics": dict(metrics_raw={}),
    "metrics without cx": dict(metrics_raw={"t_eps": 1, "depth_ct": 1, "qubits": 1}),
    "non-finite metrics": dict(metrics_raw={"cx": 10, "t_eps": math.inf, "depth_ct": 50, "qubits": 30}),
    "nan key": dict(key=(10, math.nan, 50, 30)),
    "not valid": dict(valid=False),
    "reason not ok": dict(reason="unverified"),
    "path traversal id": dict(id="r01-../../x-001"),
    "slash id": dict(id="r01-a/b-001"),
    "absolute id": dict(id="/etc/passwd"),
    "backslash id": dict(id="r01-a\\b-001"),
    "no round prefix": dict(id="x-001"),
    "dotdot id": dict(id="r01-a..b-001"),
    "empty id": dict(id=""),
    "huge id": dict(id="r01-" + "a" * 200),
}


@pytest.mark.parametrize("name", list(BAD))
def test_insert_enforces_the_plan_rules(tmp_path, name):
    arch = A.Archive.load("twelve", root=tmp_path)
    assert arch.insert(good("r01-F1-900"))
    n = len(arch.entries())
    assert not arch.insert(good(**BAD[name])), name
    assert len(arch.entries()) == n and arch.rejected and arch.best().id == "r01-F1-900"


def test_alternate_angle_verdicts_are_required_when_the_archive_expects_them(tmp_path):
    arch = A.Archive.load("twelve", root=tmp_path, n_alt=2)
    assert not arch.insert(good())                                  # no alternate verdicts at all
    assert not arch.insert(good(verdicts_alt=[{"ok": True, "certified": True}]))
    ok = [{"ok": True, "certified": True}] * 2
    assert arch.insert(good(verdicts_alt=ok))


def test_numpy_scalars_in_key_and_metrics_are_accepted(tmp_path):
    e = good(key=(np.int64(10), np.float64(100.0), np.int32(50), np.int64(30)), cell=(np.int64(27), np.int64(53)),
             metrics_raw={"cx": np.int64(10), "t_eps": np.float64(100.0), "depth_ct": np.int64(50), "qubits": np.int32(30)})
    e.cell = (int(math.floor(8 * math.log2(11))), int(math.floor(8 * math.log2(101))))
    arch = A.Archive.load("twelve", root=tmp_path)
    assert arch.insert(e)
    arch.save()
    assert A.Archive.load("twelve", root=tmp_path).best().id == e.id


def test_save_cannot_write_outside_the_entries_directory(tmp_path):
    arch = A.Archive.load("twelve", root=tmp_path / "root")
    e = good()
    assert arch.insert(e)
    e.id = "../../../escaped"                                       # mutated after the insert
    arch._entries[e.id] = e
    with pytest.raises(ValueError):
        arch.save()
    assert not list(tmp_path.rglob("escaped*"))


def test_load_revalidates_every_stored_entry(tmp_path):
    arch = A.Archive.load("twelve", root=tmp_path)
    assert arch.insert(good("r01-F1-001")) and arch.insert(good("r01-F1-002"))
    arch.save()
    d = tmp_path / "compress" / "archive" / "twelve" / "entries"
    # 1: a stored trial-mode result, 2: key tampered, 3: file name != id, 4: garbage file
    for name, change in (("r01-F1-003", dict(mode="trial")), ("r01-F1-004", dict(key=[0, 0, 0, 0]))):
        e = good(name, **{k: v for k, v in change.items() if k != "key"}).to_dict()
        if "key" in change:
            e["key"] = change["key"]
        (d / f"{name}.json").write_text(json.dumps(e))
    (d / "r01-F1-005.json").write_text(json.dumps(good("r01-F1-009").to_dict()))
    (d / "r01-F1-006.json").write_text("not json")
    again = A.Archive.load("twelve", root=tmp_path)
    assert sorted(e.id for e in again.entries()) == ["r01-F1-001", "r01-F1-002"]
    assert sorted(n for n, _ in again.rejected) == ["r01-F1-003.json", "r01-F1-004.json", "r01-F1-005.json", "r01-F1-006.json"]
