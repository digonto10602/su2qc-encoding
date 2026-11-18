"""Unit tests of `su2plaq.compress.robust` (prompts/008 step B6, §6): the locked angle set, the generic rho test, the ranking, the cache,
the report and brief integration, registry dispatch.  Small systems: the fuzzy link unit (4 qubits) and toy archives."""
import hashlib
import json
import math
import pathlib
from types import SimpleNamespace

import numpy as np
import pytest
from qiskit import QuantumCircuit

from su2plaq.compress import archive as A
from su2plaq.compress import brief as BR
from su2plaq.compress import report as RP
from su2plaq.compress import robust as RB
from su2plaq.compress.spec import ROOT, default_spec
from su2plaq.encodings import registry

LINK_PROGRAM = ROOT / "compress" / "programs" / "fuzzy_link" / "seed" / "000-general-ue.py"
ENC, KIND = "fuzzy_link", "UE"


def _derived(tmp_path, name, epilogue):
    text = LINK_PROGRAM.read_text()
    body, tail = text.rsplit("    return b", 1)
    f = tmp_path / "compress" / "programs" / ENC / "F1" / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body + epilogue + "    return b" + tail)
    return f


# ---------------------------------------------------------------------------------------------------- the angle set
def test_angle_set_is_the_locked_seeded_set_and_equals_both_track_sets():
    from su2plaq.rishon.compress import robust as RR
    from su2plaq.spinnet import loop as L

    rng = np.random.default_rng(20261107)
    a, b = rng.uniform(0.05, 2.0, 20), rng.uniform(0.05, 1.2, 20)
    assert (RB.ANGLE_SET_SEED, RB.ANGLE_SET_N, RB.ANGLE_SET_RANGES) == (20261107, 20, ((0.05, 2.0), (0.05, 1.2)))
    assert np.array_equal(np.asarray(RB.ANGLE_SET), np.c_[a, b]) and all(isinstance(x, float) for p in RB.ANGLE_SET for x in p)
    for track in (L, RR):                                       # spinnet (prompts/104 §11 E3) and rishon (prompts/203 §13 E3)
        assert tuple(track.ANGLE_SET) == tuple(RB.ANGLE_SET) and track.ANGLE_SET_SEED == RB.ANGLE_SET_SEED
        assert track.ANGLE_SET_RANGES == RB.ANGLE_SET_RANGES and track.angle_set_sha256() == RB.angle_set_sha256()
    assert RB.angle_set_sha256() == hashlib.sha256(repr(RB.ANGLE_SET).encode()).hexdigest()


def test_generality_points():
    ub = RB.generality_points("twelve")
    assert len(ub) == 2 and ub == RB.generality_points("fuzzy_ub")
    rng = np.random.default_rng(20261110)
    assert np.array_equal(np.asarray(ub), np.c_[rng.uniform(0.05, 2.0, 2), rng.uniform(0.05, 1.2, 2)])
    link = RB.generality_points("fuzzy_link")
    assert link == ub + ((0.37, 0.0), (0.37, 0.185))
    assert not set(ub) & set(RB.ANGLE_SET)


def test_headline_rule_section_title_and_content():
    first = RB.HEADLINE_RULE_SECTION.strip().splitlines()[0]
    assert first == "## Headline rule" and "will not count" in RB.HEADLINE_RULE_SECTION and "robust key" in RB.HEADLINE_RULE_SECTION


def test_module_is_not_hashed_and_imports_only_numpy_at_top_level():
    from su2plaq.compress import provenance as P

    assert "compress/robust.py" not in P.EVALUATOR_FILES
    for name in ("spinnet", "rishon", "fuzzy_ub", "fuzzy_link", "lsh", "twelve"):
        assert "compress/robust.py" not in [str(f.relative_to(P._SRC)) for f in P.evaluator_files(name)]
    top = "\n".join(l for l in pathlib.Path(RB.__file__).read_text().splitlines() if l.startswith(("import ", "from ")))
    assert "su2plaq" not in top


# ---------------------------------------------------------------------------------------------------- generic rho
def _circuits(fn):
    pairs = [*RB.ANGLE_SET, (0.37, 0.61)]
    out = []
    for a, b in pairs:
        qc = QuantumCircuit(2)
        fn(qc, a, b)
        out.append(qc)
    return out, pairs


def test_generic_rho_linear_toy_program():
    def lin(qc, a, b):
        qc.rz(-0.75 * a, 0)
        qc.cx(0, 1)
        qc.p(0.5 * b + 0.25 * a, 1)
        qc.crz(2.0 * b, 0, 1)

    ok, why = RB.generic_angle_linear(*_circuits(lin))
    assert ok is True and why == "ok"
    ok, why = RB.generic_angle_linear(*_circuits(lambda qc, a, b: qc.h(0)))               # no rotation at all
    assert ok is True


def test_generic_rho_shifted_angle_and_nonlinear_toys():
    def shifted(qc, a, b):                       # a constant offset: not homogeneous-linear
        qc.rz(a + 0.3, 0)

    ok, why = RB.generic_angle_linear(*_circuits(shifted))
    assert ok is False and why.startswith("non_linear_angle") and "gate parameter 0" in why

    def pi_offset(qc, a, b):                     # the +-pi/4 trick: a rotation shifted by a Clifford+T angle
        qc.p(b + math.pi / 4, 0)

    assert RB.generic_angle_linear(*_circuits(pi_offset))[0] is False

    def quadratic(qc, a, b):
        qc.rz(a * a, 0)

    assert RB.generic_angle_linear(*_circuits(quadratic))[0] is False

    def only_nominal(qc, a, b):                  # linear on the set, wrong at the nominal pair only (last circuit)
        qc.rz(a + (0.2 if (a, b) == (0.37, 0.61) else 0.0), 0)

    assert RB.generic_angle_linear(*_circuits(only_nominal))[0] is False


# ---------------------------------------------------------------------------------------------------- one program
def test_robust_metrics_of_the_link_general_program(tmp_path):
    from su2plaq.compress import metrics as M

    rm = RB.robust_metrics(ENC, KIND, LINK_PROGRAM)
    assert rm["skeleton_equal"] and len(rm["t_eps"]) == 20 and len(rm["depth_ct"]) == 20 and rm["angle_linear"] is True
    assert rm["robust_key"] == (rm["cx"], rm["t_sum"], 0, rm["depth_sum"], rm["qubits"]) and rm["export_status"] == "ok"
    assert rm["t_sum"] == sum(rm["t_eps"]) and rm["depth_sum"] == sum(rm["depth_ct"]) and abs(rm["t_mean"] - rm["t_sum"] / 20) <= 1e-12
    assert rm["program_sha256"] == hashlib.sha256(LINK_PROGRAM.read_bytes()).hexdigest() and rm["angle_set_sha256"] == RB.angle_set_sha256()
    from su2plaq.fuzzy.compress_hook import general_circuit

    spec = default_spec(ENC, KIND)
    for i in (0, 7, 19):
        a, b = RB.ANGLE_SET[i]
        s = spec.with_angles(a, b)
        ref = M.metrics(general_circuit(s), s, measured=True)
        assert rm["t_eps"][i] == ref["t_eps"] and rm["depth_ct"][i] == ref["depth_ct"] and rm["cx"] == ref["cx"]


def test_robust_metrics_skeleton_hardenings_and_nonlinear(tmp_path):
    rm = RB.robust_metrics(ENC, KIND, LINK_PROGRAM)
    betas = np.array([p[1] for p in RB.ANGLE_SET])
    thr = float(np.sort(betas)[10])
    bad = _derived(tmp_path, "004-range.py", f"    if spec.beta > {thr!r}:\n        b.x(0)\n        b.x(0)\n")
    rb = RB.robust_metrics(ENC, KIND, bad, root=tmp_path)
    assert not rb["skeleton_equal"] and rb["robust_key"] is None and rb["angle_linear"] is False
    nominal = _derived(tmp_path, "005-nominal.py", "    if abs(spec.alpha - 0.37) < 1e-12 and abs(spec.beta - 0.61) < 1e-12:\n        b.x(0)\n        b.x(0)\n")
    rn = RB.robust_metrics(ENC, KIND, nominal, root=tmp_path)
    assert not rn["skeleton_equal"] and rn["robust_key"] is None                       # the nominal pair is part of the skeleton set
    nonlin = _derived(tmp_path, "006-nonlinear.py", "    b.p(0.123, 0)\n    b.p(-0.123, 0)\n")
    rl = RB.robust_metrics(ENC, KIND, nonlin, root=tmp_path)
    assert rl["skeleton_equal"] and rl["angle_linear"] is False and rl["robust_key"][2] == 1 and rl["robust_key"] > rm["robust_key"]
    assert rl["export_status"].startswith("non_linear_angle")


def test_registered_angle_linear_hook_decides_rho(monkeypatch):
    import sys
    import types

    m = types.ModuleType("su2plaq_robust_hooks")
    m.calls = []

    def hook(circuit, spec):
        m.calls.append((circuit.num_qubits, spec.encoding))
        return False, "hook says no"

    m.hook = hook
    monkeypatch.setitem(sys.modules, "su2plaq_robust_hooks", m)
    import dataclasses

    old = registry.info(ENC)
    registry.register(dataclasses.replace(old, angle_linear="su2plaq_robust_hooks:hook"), replace=True)
    try:
        rm = RB.robust_metrics(ENC, KIND, LINK_PROGRAM)
    finally:
        registry.register(old, replace=True)
    assert rm["angle_linear"] is False and rm["export_status"] == "hook says no" and rm["robust_key"][2] == 1 and m.calls == [(4, ENC)]


# ---------------------------------------------------------------------------------------------------- ranking on a toy archive
def _fake_archive(monkeypatch, tmp_path, specs, enc="toyenc", offset_class="non_clifford_offset"):
    """specs: (id, archive key, robust key | None, lean status | None, has program).  robust_metrics is stubbed."""
    entries, table = [], {}
    for i, (eid, key, rkey, lean, has_prog) in enumerate(specs):
        f = tmp_path / "compress" / "programs" / enc / "F1" / f"{i:03d}-x.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# {eid}\n")
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        entries.append(SimpleNamespace(id=eid, program_path=str(f.relative_to(tmp_path)) if has_prog else f"compress/programs/{enc}/seed/{eid}.circuit",
                                       program_sha256=sha, valid=True, key=key, family="F1", round=1,
                                       lean=None if lean is None else {"status": lean}))
        table[f.name] = {"program_sha256": sha, "angle_set_sha256": RB.angle_set_sha256(), "skeleton_equal": rkey is not None,
                         "t_eps": [rkey[1] // 20] * 20 if rkey else [0] * 20, "depth_ct": [rkey[3] // 20] * 20 if rkey else [0] * 20,
                         "t_sum": rkey[1] if rkey else 0, "depth_sum": rkey[3] if rkey else 0, "t_mean": rkey[1] / 20 if rkey else 0.0,
                         "cx": key[0], "qubits": key[3], "angle_linear": bool(rkey) and rkey[2] == 0, "export_status": "ok", "robust_key": rkey,
                         "offset_class": None if rkey is None else ("linear" if rkey[2] == 0 else offset_class), "offset_units": None}
    best = min(entries, key=lambda e: (tuple(e.key), e.id))
    monkeypatch.setattr(A.Archive, "load", classmethod(lambda cls, *a, **k: SimpleNamespace(entries=lambda: list(entries), best=lambda: best)))
    calls = []

    def stub(encoding, kind, path, root=None):
        calls.append(pathlib.Path(path).name)
        return dict(table[pathlib.Path(path).name])

    monkeypatch.setattr(RB, "robust_metrics", stub)
    monkeypatch.setattr("su2plaq.compress.spec.default_spec", lambda e, k: default_spec(ENC, KIND))
    return calls


def test_ranking_on_a_three_entry_toy_archive(tmp_path, monkeypatch):
    calls = _fake_archive(monkeypatch, tmp_path, [
        ("r03-F1-003", (31, 1062, 2189, 17), (31, 21840, 1, 46141, 17), "n_a", True),        # archive best, tied in sum T, not angle-linear
        ("r02-F1-002", (31, 1086, 2258, 17), (31, 21840, 0, 46024, 17), "certified", True),   # angle-linear: wins the tie
        ("r01-F1-001", (32, 832, 1583, 18), (32, 16948, 0, 33256, 18), "certified", True),
        ("r04-F1-004", (30, 900, 2000, 17), None, None, True),                                # the skeleton changes in the set
        ("r00-seed-005", (29, 800, 1900, 17), None, None, False)])                            # no program file
    h = RB.headline("toyenc", "step", root=tmp_path)
    assert h["id"] == "r02-F1-002" and h["archive_best"] == "r00-seed-005" and h["lean"] == "certified"
    assert [r["id"] for r in h["ranking"]] == ["r02-F1-002", "r03-F1-003", "r01-F1-001"]
    assert h["unrankable"] == ["r00-seed-005", "r04-F1-004"] and h["archive_best_robust_key"] is None
    assert tuple(h["robust_key"]) == (31, 21840, 0, 46024, 17) and abs(h["t_mean"] - 21840 / 20) < 1e-12
    cache = json.loads((tmp_path / "results" / "compress" / "toyenc" / "robust.json").read_text())
    assert set(cache["entries"]) == {"r02-F1-002", "r03-F1-003", "r01-F1-001", "r04-F1-004"} and cache["angle_set"]["seed"] == 20261107
    assert len(cache["angle_set"]["pairs"]) == 20 and len(calls) == 4
    RB.headline("toyenc", "step", root=tmp_path)                       # second call: everything from the cache
    assert len(calls) == 4
    RB.headline("toyenc", "step", root=tmp_path, refresh=True)
    assert len(calls) == 8


def test_full_ties_fall_back_to_the_archive_key_then_the_id(tmp_path, monkeypatch):
    _fake_archive(monkeypatch, tmp_path, [("r02-F1-002", (31, 1086, 2258, 17), (31, 100, 0, 200, 17), None, True),
                                          ("r02-F1-003", (31, 1062, 2189, 17), (31, 100, 0, 200, 17), None, True),
                                          ("r02-F1-001", (31, 1062, 2189, 17), (31, 100, 0, 200, 17), None, True)])
    assert [r["id"] for r in RB.headline("toyenc", "step", root=tmp_path)["ranking"]] == ["r02-F1-001", "r02-F1-003", "r02-F1-002"]


def test_cache_is_invalidated_by_a_changed_angle_set_or_code_hash(tmp_path, monkeypatch):
    calls = _fake_archive(monkeypatch, tmp_path, [("r01-F1-001", (32, 832, 1583, 18), (32, 16948, 0, 33256, 18), None, True)])
    RB.headline("toyenc", "step", root=tmp_path)
    f = tmp_path / "results" / "compress" / "toyenc" / "robust.json"
    d = json.loads(f.read_text())
    d["angle_set"]["sha256"] = "0" * 64
    f.write_text(json.dumps(d))
    RB.headline("toyenc", "step", root=tmp_path)
    assert len(calls) == 2
    d = json.loads(f.read_text())
    d["encoding_sha256"] = "1" * 64
    f.write_text(json.dumps(d))
    RB.headline("toyenc", "step", root=tmp_path)
    assert len(calls) == 3


def test_compute_false_uses_the_cache_only(tmp_path, monkeypatch):
    calls = _fake_archive(monkeypatch, tmp_path, [("r01-F1-001", (32, 832, 1583, 18), (32, 16948, 0, 33256, 18), None, True)])
    assert RB.headline("toyenc", "step", root=tmp_path, compute=False) is None and calls == []
    assert not (tmp_path / "results" / "compress" / "toyenc" / "robust.json").exists()
    h = RB.headline("toyenc", "step", root=tmp_path)
    assert RB.headline("toyenc", "step", root=tmp_path, compute=False)["id"] == h["id"] and len(calls) == 1


def test_headline_writes_the_summary_block_and_delegates_to_a_registered_hook(tmp_path, monkeypatch):
    import dataclasses
    import sys
    import types

    _fake_archive(monkeypatch, tmp_path, [("r01-F1-001", (32, 832, 1583, 18), (32, 16948, 0, 33256, 18), "certified", True)])
    sf = tmp_path / "results" / "compress" / "toyenc" / "summary.json"
    sf.parent.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps({"encoding": "toyenc"}))
    h = RB.headline("toyenc", "step", root=tmp_path)
    s = json.loads(sf.read_text())
    assert s["headline"] == {"id": "r01-F1-001", "robust_key": [32, 16948, 0, 33256, 18], "t_mean": 16948 / 20,
                             "angle_set_sha256": RB.angle_set_sha256()}
    m = types.ModuleType("su2plaq_robust_hooks2")
    m.headline = lambda kind, root, refresh: {"id": "from-hook", "kind": kind, "refresh": refresh}
    monkeypatch.setitem(sys.modules, "su2plaq_robust_hooks2", m)
    old = registry.info("twelve")
    registry.register(dataclasses.replace(old, name="toyenc", headline="su2plaq_robust_hooks2:headline"), replace=True)
    try:
        assert RB.headline("toyenc", "UB", root=tmp_path, refresh=True) == {"id": "from-hook", "kind": "UB", "refresh": True, "unrankable": []}
    finally:
        registry._TABLE.pop("toyenc", None)


# ---------------------------------------------------------------------------------------------------- report and brief
def test_report_rows_and_table_print_global_best_and_headline(tmp_path, monkeypatch):
    _fake_archive(monkeypatch, tmp_path, [("r03-F1-003", (31, 1062, 2189, 17), (31, 21840, 1, 46141, 17), "n_a", True),
                                          ("r02-F1-002", (31, 1086, 2258, 17), (31, 21840, 0, 46024, 17), "certified", True)])
    h = RB.headline("toyenc", "step", root=tmp_path)
    rows = RB.report_rows("toyenc", "step", root=tmp_path, h=h)
    assert rows[0][0] == "GLOBAL BEST (archive key): r03-F1-003" and rows[1][0] == "HEADLINE (robust key): r02-F1-002"
    assert rows[1][5] == "1092.00" and rows[1][8] == "yes" and rows[0][8] == "no" and rows[1][9] == "certified"
    assert rows[2][0].startswith("best of family F1") and len(rows[0]) == len(RB.HEADLINE_HEADER)
    note = RB.headline_note(h)
    assert "GLOBAL BEST" in note and "HEADLINE" in note and RB.angle_set_sha256()[:16] in note


def test_shared_report_table_appends_the_headline_table_only_when_cached(tmp_path, monkeypatch):
    from su2plaq.encodings import base

    monkeypatch.setitem(base.NOMINAL_ANGLES, "toyenc", (0.37, 0.61))
    _fake_archive(monkeypatch, tmp_path, [("r00-seed-000", (12, 600, 100, 4), (12, 12000, 0, 2000, 4), "certified", True)])
    round0 = {"round": 0, "entries": ["r00-seed-000"], "external": [], "candidates": [
        {"label": "general", "id": "r00-seed-000", "family": "seed", "valid": True, "key": [12, 600, 100, 4], "round": 0,
         "metrics": {"qubits": 4, "cx": 12, "t_fixed": 0, "n_rot": 10, "t_eps": 600, "depth_ct": 100}, "verdict": {}, "lean": None,
         "git_commit": "abc"}]}
    rdir = tmp_path / "results" / "compress" / "toyenc"
    rdir.mkdir(parents=True)
    (rdir / "round-000.json").write_text(json.dumps(round0))
    text = RP.report_table("toyenc", "step", root=tmp_path)                       # nothing cached: only the main table
    assert "GLOBAL BEST" in text and "### Headline" not in text and "headline" not in json.loads((rdir / "summary.json").read_text())
    assert not (rdir / "robust.json").exists()                                    # the report never computes a headline
    h = RB.headline("toyenc", "step", root=tmp_path)
    text2 = RP.report_table("toyenc", "step", root=tmp_path)
    assert text2.startswith(text) and "### Headline" in text2 and "HEADLINE (robust key): r00-seed-000" in text2 and "GLOBAL BEST (archive key)" in text2
    assert json.loads((rdir / "summary.json").read_text())["headline"]["id"] == h["id"] == "r00-seed-000"
    assert RP.report_table("toyenc", "step", root=tmp_path, headline=False) == text


def test_every_round_brief_carries_the_headline_rule_and_the_ideation_brief_does_not(tmp_path):
    first = RB.HEADLINE_RULE_SECTION.strip().splitlines()[0]
    b = BR.make_brief("twelve", "step", 1, "F1", root=tmp_path).read_text()
    assert b.count(first) == 1 and b.index("## Output") < b.index(first)
    ib = BR.make_ideation_brief("twelve", "step", root=tmp_path).read_text()
    assert first not in ib


# ---------------------------------------------------------------------------------------------------- registered hooks (prompts/008 §6)
def test_registry_names_the_track_headlines_and_the_twelve_rho_hook():
    for name, dotted in (("spinnet", "su2plaq.spinnet.loop:headline_for"), ("rishon", "su2plaq.rishon.compress.robust:headline")):
        info = registry.info(name)
        assert info.headline == dotted and callable(registry.resolve(dotted))
    tw = registry.info("twelve")
    assert tw.angle_linear == "su2plaq.compress.robust:twelve_angle_linear" and callable(registry.resolve(tw.angle_linear))
    for name in ("fuzzy_ub", "fuzzy_link"):
        assert registry.info(name).headline is None and registry.info(name).angle_linear is None      # §6 is silent: the generic rule


def test_twelve_angle_linear_is_the_lean_exporter_test():
    from su2plaq.circuits import twelve as C

    spec = default_spec("twelve", "UE")
    qc = C.build_UE(spec.alpha, with_outer=True)
    ok, why = RB.twelve_angle_linear(qc, spec)
    assert ok is True and why == "ok"
    bad = qc.copy()
    bad.p(0.123, 12)                                         # a constant angle on an unused qubit, not undone
    ok, why = RB.twelve_angle_linear(bad, spec)
    assert ok is False and why.startswith("non_linear_angle")
    wide = QuantumCircuit(63)
    ok, why = RB.twelve_angle_linear(wide, spec)
    assert ok is True and why == "too_many_qubits"           # any answer but non_linear_angle counts as linear (as the spinnet track)


def test_headline_delegates_to_the_track_hooks_and_completes_the_result(tmp_path, monkeypatch):
    from su2plaq.rishon.compress import robust as RR
    from su2plaq.spinnet import loop as L

    sf = tmp_path / "results" / "compress" / "rishon" / "summary.json"
    sf.parent.mkdir(parents=True)
    sf.write_text("{}")
    fake = {"id": "r1", "robust_key": (1, 2, 0, 3, 4), "t_mean": 0.1, "ranking": [
        {"id": "r1", "robust_key": (1, 2, 0, 3, 4)}, {"id": "r0", "robust_key": None}]}
    seen = {}
    monkeypatch.setattr(RR, "headline", lambda kind="step", root=None, refresh=False: (seen.update(kind=kind, root=root, refresh=refresh) or dict(fake)))
    h = RB.headline("rishon", "step", root=tmp_path, refresh=True)
    assert h["id"] == "r1" and h["unrankable"] == ["r0"] and seen == {"kind": "step", "root": tmp_path, "refresh": True}
    assert json.loads(sf.read_text())["headline"]["id"] == "r1"
    monkeypatch.setattr(L, "headline", lambda root=None, refresh=False: {"id": "s1", "robust_key": (9, 9, 0, 9, 9), "t_mean": 1.0, "ranking": [], "root": root})
    assert RB.headline("spinnet", "step", root=tmp_path)["id"] == "s1"
    with pytest.raises(ValueError):
        L.headline_for("UB")


# ---------------------------------------------------------------------------------------------------- offset classes (prompts/010 §3, §4.1)
PI = float(np.pi)


def _family(fill):
    pairs = [*RB.ANGLE_SET, (0.37, 0.61)]
    circuits = []
    for a, b in pairs:
        qc = QuantumCircuit(2)
        fill(qc, a, b)
        circuits.append(qc)
    return circuits, pairs


def _clifford(qc, a, b):
    qc.rz(a - PI, 0); qc.cx(0, 1); qc.rz(b - 3 * PI / 2, 1); qc.p(a + PI / 2, 0); qc.s(1); qc.crz(2 * b + PI, 0, 1)


OFFSET_CASES = {
    "linear": (lambda qc, a, b: (qc.rz(a, 0), qc.cx(0, 1), qc.rz(-b / 2, 1), qc.p(3 * a - b, 0), qc.crz(2 * b, 0, 1)), True, "linear"),
    "clifford": (_clifford, False, "clifford_offset"),
    "hidden_t": (lambda qc, a, b: (qc.rz(a, 0), qc.cx(0, 1), qc.rz(b + PI / 4, 1)), False, "non_clifford_offset"),
    "crz_half": (lambda qc, a, b: (qc.rz(a, 0), qc.crz(b + PI / 2, 0, 1)), False, "non_clifford_offset"),
    "crz_pi": (lambda qc, a, b: (qc.rz(a, 0), qc.crz(b + PI, 0, 1)), False, "clifford_offset"),
    "cp_pi": (lambda qc, a, b: (qc.rz(a, 0), qc.cp(b - PI, 0, 1)), False, "clifford_offset"),
    "rx_half": (lambda qc, a, b: (qc.rx(a + PI / 2, 0), qc.ry(b - PI, 1)), False, "clifford_offset"),
    "u_gate_offset": (lambda qc, a, b: (qc.u(a, b, 0.0, 0), qc.u(a, b, PI / 2, 1)), False, "non_clifford_offset"),     # no unit for `u`
    "constant": (lambda qc, a, b: (qc.rz(a, 0), qc.rz(PI / 2, 1), qc.cx(0, 1), qc.rz(b, 1)), False, "clifford_offset"),
    "product": (lambda qc, a, b: (qc.rz(a * b, 0), qc.cx(0, 1), qc.rz(b, 1)), False, "non_affine"),
    "tiny": (lambda qc, a, b: (qc.rz(a + 1e-10, 0), qc.cx(0, 1), qc.rz(b, 1)), True, "linear"),
    "just_above_tol": (lambda qc, a, b: (qc.rz(a + 5e-9, 0), qc.cx(0, 1), qc.rz(b, 1)), False, "non_clifford_offset"),
}


@pytest.mark.parametrize("name", sorted(OFFSET_CASES))
def test_angle_offsets_classes_and_generic_rho_are_consistent(name):
    fill, is_linear, cls = OFFSET_CASES[name]
    circuits, pairs = _family(fill)
    ok, why = RB.generic_angle_linear(circuits, pairs)                  # unchanged by H.1
    assert ok is is_linear and ((why == "ok") if is_linear else why.startswith("non_linear_angle"))
    info = RB.angle_offsets(circuits, pairs)
    assert info["class"] == cls
    assert (info["class"] == "linear") == ok                            # class "linear" is exactly rho = 0
    n = len(RB.rotation_angles(circuits[0]))
    assert len(info["offsets"]) == len(info["offset_units"]) == len(info["gates"]) == n
    if cls != "non_affine":
        assert info["affine_residual"] <= 1e-9


def test_angle_offsets_values_units_and_gate_names():
    circuits, pairs = _family(_clifford)
    info = RB.angle_offsets(circuits, pairs)
    assert info["offset_units"] == [-2, -3, 1, 2] and info["gates"] == ["rz", "rz", "p", "crz"]
    assert np.abs(np.array(info["offsets"]) - np.array([-PI, -1.5 * PI, 0.5 * PI, PI])).max() <= 1e-9
    circuits, pairs = _family(OFFSET_CASES["hidden_t"][0])
    info = RB.angle_offsets(circuits, pairs)
    assert info["offset_units"] == [0, None] and abs(info["offsets"][1] - PI / 4) <= 1e-9
    circuits, pairs = _family(OFFSET_CASES["linear"][0])
    assert RB.angle_offsets(circuits, pairs)["offset_units"] == [0, 0, 0, 0]
    assert RB.angle_offsets([QuantumCircuit(1) for _ in range(21)], pairs) == {
        "class": "linear", "affine_residual": 0.0, "offsets": [], "offset_units": [], "gates": []}
    assert RB.OFFSET_TOL == RB.LINEAR_TOL == 1e-9 and RB.CLIFFORD_OFFSET_UNIT["crz"] == PI and RB.CLIFFORD_OFFSET_UNIT["rz"] == PI / 2


def test_generic_angle_linear_unchanged_on_the_toys_of_report_419():
    for fill, expect in ((lambda qc, a, b: qc.rz(a + PI / 2, 0), False), (lambda qc, a, b: qc.rz(a - PI, 0), False),
                         (lambda qc, a, b: qc.rz(a + PI / 4, 0), False), (lambda qc, a, b: qc.rz(a * b, 0), False),
                         (lambda qc, a, b: qc.rz(a + 1e-10, 0), True), (lambda qc, a, b: qc.rz(2 * a - b / 3, 0), True)):
        circuits, pairs = _family(fill)
        assert RB.generic_angle_linear(circuits, pairs)[0] is expect


def test_robust_metrics_carries_the_offset_class_of_the_link_general_program():
    rm = RB.robust_metrics(ENC, KIND, LINK_PROGRAM)
    assert rm["offset_class"] == "linear" and rm["angle_linear"] is True and isinstance(rm["offset_units"], list)
    assert all(u == 0 for u in rm["offset_units"]) and rm["robust_key"][2] == 0


def test_report_cell_marks_clifford_offsets_and_the_note_explains_it(tmp_path, monkeypatch):
    _fake_archive(monkeypatch, tmp_path, [("r03-F1-003", (31, 1062, 2189, 17), (31, 21840, 1, 46141, 17), "n_a", True),
                                          ("r02-F1-002", (31, 1086, 2258, 17), (31, 21840, 0, 46024, 17), "certified", True)],
                  offset_class="clifford_offset")
    h = RB.headline("toyenc", "step", root=tmp_path)
    assert {r["id"]: r["offset_class"] for r in h["ranking"]} == {"r02-F1-002": "linear", "r03-F1-003": "clifford_offset"}
    rows = RB.report_rows("toyenc", "step", root=tmp_path, h=h)
    assert rows[0][8] == "no (Clifford offsets)" and rows[1][8] == "yes"
    assert "Entries marked 'no (Clifford offsets)'" in RB.headline_note(h) and "not rewarded" in RB.headline_note(h)
    h["ranking"][0]["offset_class"] = "non_clifford_offset"
    h["ranking"][1]["offset_class"] = "non_clifford_offset"
    assert "Clifford offsets" not in RB.headline_note(h)
    assert RB.report_rows("toyenc", "step", root=tmp_path, h=h)[0][8] == "no"


def test_cached_record_without_the_class_is_recomputed_or_missing(tmp_path, monkeypatch):
    calls = _fake_archive(monkeypatch, tmp_path, [("r01-F1-001", (32, 832, 1583, 18), (32, 16948, 0, 33256, 18), None, True)])
    RB.headline("toyenc", "step", root=tmp_path)
    assert len(calls) == 1 and RB.headline("toyenc", "step", root=tmp_path, compute=False)["ranking"][0]["offset_class"] == "linear"
    f = tmp_path / "results" / "compress" / "toyenc" / "robust.json"
    d = json.loads(f.read_text())
    for rec in d["entries"].values():
        del rec["offset_class"]
    f.write_text(json.dumps(d))
    assert RB.headline("toyenc", "step", root=tmp_path, compute=False) is None          # not computed, not written
    assert "offset_class" not in next(iter(json.loads(f.read_text())["entries"].values()))
    h = RB.headline("toyenc", "step", root=tmp_path)                                    # recomputed
    assert len(calls) == 2 and h["ranking"][0]["offset_class"] == "linear"
    assert "offset_class" in next(iter(json.loads(f.read_text())["entries"].values()))


def test_no_encoding_lists_the_robust_module_among_its_evaluator_files():
    import subprocess
    import sys

    code = (f"import sys; sys.path.insert(0, {str(ROOT / 'src')!r})\n"
            "from su2plaq.compress import provenance as P; from su2plaq.encodings import registry as R\n"
            "bad=[(e, f) for e in R.names() for f in P.evaluator_files(e) if str(f).endswith('compress/robust.py')]\n"
            "assert not bad, bad; print('ok', len(R.names()))")
    r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.startswith("ok"), r.stderr
