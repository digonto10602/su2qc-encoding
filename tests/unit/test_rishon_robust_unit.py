"""Step 6.4b unit tests: the headline rule (prompts/203 section 13 E3): angle recognition, the locked angle set, the spec / brief
section, the headline ranking on a hand-made archive (no program evaluation; robust metrics are monkeypatched), the report table."""
import json
import math

import numpy as np
import pytest

from su2plaq.compress import archive as A
from su2plaq.rishon.compress import brief as BR
from su2plaq.rishon.compress import robust as R
from su2plaq.rishon.compress import spec as S
from su2plaq.rishon.lean_cert import recognise_angle

SQ2 = math.sqrt(2.0)
ALPHA, BETA = 0.37, 0.61


def test_recognise_angle_canonical_triples():
    assert recognise_angle(0.0, ALPHA, BETA) == (0, 0, 0, 1)
    assert recognise_angle(8 * SQ2 * BETA, ALPHA, BETA) == (0, 0, 8, 1)
    assert recognise_angle(-0.75 * ALPHA, ALPHA, BETA) == (-3, 0, 0, 4)
    assert recognise_angle(0.5 * BETA, ALPHA, BETA) == (0, 1, 0, 2)
    assert recognise_angle(BETA + 2 * SQ2 * BETA, ALPHA, BETA) == (0, 1, 2, 1)
    assert recognise_angle((3 * ALPHA - 5 * BETA + 7 * SQ2 * BETA) / 16, ALPHA, BETA) == (3, -5, 7, 16)
    # alpha and beta are rational at the nominal pair: 0.123 = (5 alpha + beta)/20 carries no information and is not recognised
    assert abs((5 * ALPHA + BETA) / 20 - 0.123) < 1e-12 and recognise_angle(0.123, ALPHA, BETA) is None
    # other pairs: generic values
    for a, b in ((0.91, 0.23), (math.pi / 7, 0.5)):
        m = recognise_angle((-3 * a + 2 * b - 5 * SQ2 * b) / 8, a, b)
        assert m is not None and m[3] <= 8 and abs((m[0] * a + m[1] * b + m[2] * SQ2 * b) / m[3] - (-3 * a + 2 * b - 5 * SQ2 * b) / 8) <= 1e-12
    assert recognise_angle(1.234567, math.pi / 7, 0.5) is None
    with pytest.raises(ValueError):
        recognise_angle(1.0, 0.0, 0.5)


def test_angle_set_is_locked_and_hashed():
    rng = np.random.default_rng(20261107)
    a, b = rng.uniform(0.05, 2.0, 20), rng.uniform(0.05, 1.2, 20)
    assert R.ANGLE_SET == tuple((float(x), float(y)) for x, y in zip(a, b)) and len(R.ANGLE_SET) == 20
    assert len(R.angle_set_sha256()) == 64 and R.angle_set_sha256() == R.angle_set_sha256()


def test_spec_and_brief_carry_the_headline_section(tmp_path):
    sp = S.rishon_spec("UE")
    text = S.render_spec(sp)
    assert text.count(R.HEADLINE_SECTION_TITLE) == 1 and text.index(R.HEADLINE_SECTION_TITLE) < text.index("## Tools")
    assert "robust key" in text and "pi/4" in text and S.render_spec(sp) == text
    assert R.with_headline_section(S.render_spec) is S.render_spec            # idempotent
    t = BR.make_brief("UE", 4, "F1", root=tmp_path).read_text()
    assert R.HEADLINE_SECTION_TITLE in t and t.index(R.HEADLINE_SECTION_TITLE) < t.index("## Output")
    assert R.HEADLINE_SECTION_TITLE not in BR.make_ideation_brief("UE", root=tmp_path).read_text()


def _entry(i, key, rnd=1, fam="F1", valid=True, program="compress/programs/rishon/F1/x.py", lean=None):
    return A.Entry(id=i, program_path=program, program_sha256="a" * 64, parent=None, family=fam, round=rnd, valid=valid, reason="ok",
                   key=tuple(key), cell=(0, 0), metrics_raw={}, metrics_polished=None, verdict_nominal={}, verdicts_alt=[],
                   skeleton_equal=True, discoveries=[], summary="", evaluator_sha256="e", spec_sha256="s", git_commit="c", versions={},
                   seeds={}, machine="m", wall_s=0.0, written_utc="t", lean=lean)


def test_headline_ranking_ties_cache_and_report(tmp_path, monkeypatch):
    (tmp_path / "compress" / "programs" / "rishon" / "F1").mkdir(parents=True)
    (tmp_path / "compress" / "programs" / "rishon" / "F1" / "x.py").write_text("# stub")
    class StubArchive:                       # hand-made entries cannot pass the archive's strict insert rules
        def __init__(self, es):
            self.es = es

        def entries(self):
            return list(self.es)

        def best(self):
            return min(self.es, key=lambda x: (tuple(x.key), x.id))

    ents = [_entry("e-a", (10, 100, 50, 48)), _entry("e-b", (10, 100, 50, 48), fam="F3", lean={"status": "certified", "reason": ""}),
            _entry("e-c", (12, 90, 40, 48)), _entry("e-circ", (11, 95, 45, 48), program="compress/programs/rishon/seed/c.circuit"),
            _entry("e-bad", (9, 80, 40, 48))]
    arch = StubArchive(ents)
    monkeypatch.setattr(A.Archive, "load", classmethod(lambda cls, *a, **k: arch))
    robust = {"e-a": (10, 2000, 0, 900, 48), "e-b": (10, 2000, 0, 900, 48), "e-c": (12, 1800, 0, 800, 48), "e-bad": None}
    seq = iter(sorted(robust))        # headline() visits the entries in id order

    def fake_metrics(path, spec=None, root=None):
        k = robust[next(seq)]
        base = {"program_sha256": "a" * 64, "angle_set_sha256": R.angle_set_sha256(), "skeleton_equal": k is not None,
                "t_eps": [100] * 20, "depth_ct": [45] * 20, "t_sum": 2000, "depth_sum": 900, "t_mean": 100.0, "cx": 10, "qubits": 48,
                "angle_linear": True, "angle_fit": [], "robust_key": k}
        return base

    monkeypatch.setattr(R, "robust_metrics", fake_metrics)
    h = R.headline("UE", root=tmp_path)
    ids = [r["id"] for r in h["ranking"]]
    assert ids == ["e-a", "e-b", "e-c", "e-bad", "e-circ"]            # CX first; None keys last, ordered by laptop key
    assert h["ranking"][0]["robust_key"] == min(r for r in robust.values() if r is not None)
    assert all(r["robust_key"] is None for r in h["ranking"][-2:])
    assert h["id"] == h["ranking"][0]["id"] and h["archive_best"] == arch.best().id
    # the full tie (e-a, e-b: equal robust key and equal laptop key) is resolved by id
    tie = [r["id"] for r in h["ranking"] if r["robust_key"] == (10, 2000, 0, 900, 48)]
    assert tie == sorted(tie)
    cache = json.loads((tmp_path / "results" / "compress" / "rishon" / "robust.json").read_text())
    assert set(cache["entries"]) == {"e-a", "e-b", "e-c", "e-bad"} and cache["angle_set"]["sha256"] == R.angle_set_sha256()
    monkeypatch.setattr(R, "robust_metrics", lambda *a, **k: pytest.fail("cache must be used"))
    assert R.headline("UE", root=tmp_path)["ranking"] == h["ranking"]
