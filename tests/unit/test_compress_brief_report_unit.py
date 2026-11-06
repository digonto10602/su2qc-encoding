"""Unit tests for su2plaq.compress.{brief,report} and the round bookkeeping added in step 2.6."""
import json

import pytest

from su2plaq.compress import archive as A
from su2plaq.compress import brief as BR
from su2plaq.compress import report as RP
from su2plaq.compress import round as R

PROG = '''"""SUMMARY: {summary}.

DISCOVERY: {disc}
"""
FAMILY = "{fam}"
PARENT = None

from su2plaq.compress.builder import Builder


def build(spec):
    b = Builder(spec)
    d = b.reg("d")
    for l in range(4):
        b.p({sign}0.75 * spec.alpha, d[3 * l + 2])
    return b
'''


def program(root, fam, num, sign="-", disc="idea", summary="ue"):
    f = root / "compress" / "programs" / "twelve" / fam / f"{num:03d}-x.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(PROG.format(summary=summary, disc=disc, fam=fam, sign=sign))
    return f


@pytest.fixture(scope="module")
def root(tmp_path_factory):
    d = tmp_path_factory.mktemp("loop")
    a = program(d, "F1", 1, summary="first")
    b = program(d, "F1", 2, sign="+", summary="wrong")
    R.run_round("twelve", "UE", 1, evaluate=True, dry_run=True, root=d, proposals=[str(a), str(b)], lean=False)
    return d


def test_round_stores_relative_paths_feedback_and_candidate_records(root):
    arch = A.Archive.load("twelve", root=root)
    e = arch.entries()[0]
    assert e.program_path == "compress/programs/twelve/F1/001-x.py" and (root / e.program_path).exists()
    fb = json.loads((root / "results" / "compress" / "twelve" / "feedback" / f"{e.id}.json").read_text())
    assert fb["valid"] is True and fb["verdict"]["ok"]
    rj = json.loads((root / "results" / "compress" / "twelve" / "round-001.json").read_text())
    ids = {c["id"]: c for c in rj["candidates"]}
    assert len(ids) == 2 and ids[e.id]["valid"] and ids[e.id]["key"] == list(e.key) and ids["r01-F1-002"]["valid"] is False
    assert ids["r01-F1-002"]["reason"] == "error" and rj["lean_seconds"] == 0.0 and rj["synthesis_verification"]["ok"] is True


def test_circuit_of_reports_errors_instead_of_swallowing_them(tmp_path):
    from su2plaq.compress.spec import default_spec

    c, err = R._circuit_of(default_spec("twelve", "UE"), "compress/programs/nope.py", "x", None, tmp_path)
    assert c is None and "not found" in err
    bad = tmp_path / "bad.py"
    bad.write_text("not a program")
    c, err = R._circuit_of(default_spec("twelve", "UE"), str(bad), "x", None, tmp_path)
    assert c is None and "ContractError" in err


def test_brief_points_at_files_and_follows_the_template(root):
    p = BR.make_brief("twelve", "UE", round=2, family="F1", root=root)
    t = p.read_text()
    assert p == root / "compress" / "briefs" / "twelve" / "round-002-F1.md"
    assert BR.TASK_LINE in t and "Rewrite the parent to improve the key; return the complete program" in t
    assert "compress/programs/twelve/F1/001-x.py" in t and "results/compress/twelve/feedback/r01-F1-001.json" in t
    assert "compress/programs/twelve/F1/003-<slug>.py" in t          # next free number
    assert "Proved structure (Lean)" in t and "--trial" in t and "idea" in t           # discovery note
    assert "spec.alpha" not in t and "b.reg(" not in t                                  # paths, not pasted programs
    seed_brief = BR.make_brief("twelve", "UE", round=1, family="seed", root=root).read_text()
    assert "none: write a fresh program" in seed_brief
    ideation = BR.make_ideation_brief("twelve", "UE", root=root).read_text()
    assert "compress/ideation/twelve.md" in ideation and "at most 5 families" in ideation


def test_discovery_notes_are_capped_at_30_lines(tmp_path):
    d = tmp_path / "compress" / "discoveries"
    d.mkdir(parents=True)
    (d / "twelve.md").write_text("\n".join(f"- note {i}" for i in range(100)))
    t = BR.make_brief("twelve", "UE", round=1, family="F1", root=tmp_path).read_text()
    assert "- note 99" in t and "- note 70" in t and "- note 69" not in t


def test_report_is_computed_from_the_results_json_only(root, tmp_path):
    t = RP.report_table("twelve", "UE", root=root)
    for col in ("qubits", "CX", "T_fixed", "N_rot", "T(1e-6)", "T_est(1e-6)", "T(1e-10)", "depth_CT", "verdict", "Lean"):
        assert col in t
    assert "best of family F1" in t and "GLOBAL BEST" in t and "global phase" in t and "not_run" in t
    s = json.loads((root / "results" / "compress" / "twelve" / "summary.json").read_text())
    assert s["global_best"] == "r01-F1-001" and s["lineage"][0]["cx"] == 0 and s["n_valid"] == 1 and s["n_candidates"] == 2
    # the archive and the programs are not needed: move them away and the table is the same
    import shutil

    shutil.rmtree(root / "compress" / "archive")
    assert RP.report_table("twelve", "UE", root=root) == t


def test_report_cli(root, tmp_path, capsys):
    out = tmp_path / "t.md"
    assert RP.main(["--encoding", "twelve", "--kind", "UE", "--root", str(root), "--out", str(out)]) == 0
    assert "GLOBAL BEST" in out.read_text()


# ------------------------------------------------------------------------------------------------ tester 034 findings
def _fake_entry(id_, family, key, root, make_file=True, parent=None):
    from test_compress_archive_unit import entry

    e = entry(id_, True, key[0], key[1], key[2], key[3], family=family)
    e.program_path = f"compress/programs/twelve/{family}/{id_}.py"
    e.parent = parent
    e.verdict_nominal = {"ok": True, "certified": True}
    e.verdicts_alt = [{"ok": True, "certified": True}] * 2
    if make_file:
        f = root / e.program_path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# program\n")
    return e


def _archive_with(root, entries):
    arch = A.Archive.load("twelve", root=root)
    for e in entries:
        assert arch.insert(e), e.id
    arch.save()


def _listed(text):
    import re

    return re.findall(r"\(entry `([^`]+)`", text)


def test_alternatives_are_diverse_and_migration_adds_the_global_best(tmp_path):
    es = [_fake_entry("r01-A-001", "A", (10, 100, 50, 30), tmp_path), _fake_entry("r01-A-002", "A", (11, 100, 50, 30), tmp_path),
          _fake_entry("r01-A-003", "A", (12, 100, 50, 30), tmp_path), _fake_entry("r01-B-001", "B", (40, 400, 50, 30), tmp_path),
          _fake_entry("r01-C-001", "C", (80, 800, 50, 30), tmp_path)]
    _archive_with(tmp_path, es)
    alts = _listed(BR.make_brief("twelve", "UE", round=2, family="D", root=tmp_path).read_text().split("## Archive alternatives")[1])
    assert alts[:3] == ["r01-A-001", "r01-B-001", "r01-C-001"]          # one per family before more of the cheapest family
    # a family that has an elite: its parent is excluded and other families come first
    t = BR.make_brief("twelve", "UE", round=2, family="B", root=tmp_path).read_text()
    assert _listed(t.split("## Archive alternatives")[1])[:2] == ["r01-A-001", "r01-C-001"]
    # migration at round 3: the global best is present even when diversity would have left it out
    t3d = BR.make_brief("twelve", "UE", round=3, family="D", root=tmp_path).read_text()
    assert "r01-A-001" in _listed(t3d.split("## Archive alternatives")[1])
    # a family whose own parent is the global best: the migration clause must not list the parent again
    t3a = BR.make_brief("twelve", "UE", round=3, family="A", root=tmp_path).read_text()
    assert t3a.split("## Parent")[1].split("##")[0].count("r01-A-001") >= 1 and "r01-A-001" not in _listed(t3a.split("## Archive alternatives")[1])


def test_alternatives_never_list_a_missing_program_file_also_on_the_migration_branch(tmp_path):
    es = [_fake_entry("r01-A-001", "A", (10, 100, 50, 30), tmp_path, make_file=False), _fake_entry("r01-B-001", "B", (40, 400, 50, 30), tmp_path)]
    _archive_with(tmp_path, es)
    for rnd in (2, 3, 6):
        t = BR.make_brief("twelve", "UE", round=rnd, family="D", root=tmp_path).read_text()
        assert "r01-A-001" not in t and "r01-B-001" in t


def test_program_header_parent_is_recorded_known_and_unknown(tmp_path):
    a = program(tmp_path, "F1", 1)
    R.run_round("twelve", "UE", 1, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(a)], lean=False)
    child = tmp_path / "compress" / "programs" / "twelve" / "F1" / "002-child.py"
    child.write_text(PROG.format(summary="child", disc="d", fam="F1", sign="-").replace("PARENT = None", 'PARENT = "r01-F1-001"'))
    orphan = tmp_path / "compress" / "programs" / "twelve" / "F1" / "003-orphan.py"
    orphan.write_text(PROG.format(summary="orphan", disc="d", fam="F1", sign="-").replace("PARENT = None", 'PARENT = "r09-X-001"'))
    R.run_round("twelve", "UE", 2, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(child), str(orphan)], lean=False)
    arch = A.Archive.load("twelve", root=tmp_path, n_alt=2, strict=True)
    by = {e.id: e for e in arch.entries()}
    assert by["r02-F1-002"].parent == "r01-F1-001" and by["r02-F1-003"].parent == "r09-X-001"      # unknown parent kept as declared
    rj = json.loads((tmp_path / "results" / "compress" / "twelve" / "round-002.json").read_text())
    known = {c["id"]: c["parent_known"] for c in rj["candidates"]}
    assert known == {"r02-F1-002": True, "r02-F1-003": False}
    lin = {x["id"]: x for x in json.loads((tmp_path / "results" / "compress" / "twelve" / "summary.json").read_text())["lineage"]} \
        if RP.report_table("twelve", "UE", root=tmp_path) else None
    assert lin["r02-F1-002"]["parent"] == "r01-F1-001" and lin["r02-F1-003"]["parent_known"] is False


def test_programs_already_evaluated_are_not_proposed_again_valid_or_not(tmp_path):
    good_p = program(tmp_path, "F1", 1)
    bad_p = program(tmp_path, "F1", 2, sign="+")
    assert R._proposals(R.default_spec("twelve", "UE"), tmp_path, A.Archive.load("twelve", root=tmp_path)) == [str(good_p), str(bad_p)]
    R.run_round("twelve", "UE", 1, evaluate=True, dry_run=True, root=tmp_path, lean=False)           # default proposals: both evaluated
    arch = A.Archive.load("twelve", root=tmp_path, n_alt=2, strict=True)
    assert R._proposals(R.default_spec("twelve", "UE"), tmp_path, arch) == []
    info = R.run_round("twelve", "UE", 2, evaluate=True, dry_run=True, root=tmp_path, lean=False)
    assert info["entries"] == [] and info["n_invalid"] == 0
    att = (tmp_path / "compress" / "attempts" / "twelve.jsonl").read_text().splitlines()
    assert len(att) == 2                                                                   # recorded once each
    new = program(tmp_path, "F1", 3, summary="third")
    assert R._proposals(R.default_spec("twelve", "UE"), tmp_path, arch) == [str(new)]


def test_global_best_is_the_archived_best_and_the_whole_circuit_row_has_no_fake_measurements(tmp_path):
    rdir = tmp_path / "results" / "compress" / "twelve"
    rdir.mkdir(parents=True)
    rec = lambda i, key, valid=True: {"label": i, "id": i, "family": "F", "program_path": "p", "valid": valid, "reason": "ok", "key": list(key),
                                      "metrics": {"qubits": 5, "cx": key[0], "t_fixed": 1, "n_rot": 2, "t_eps": key[1], "depth_ct": key[2],
                                                  "t_estimate": {"1e-06": 9.0, "1e-10": 20.0}, "t_measured": {"1e-06": key[1], "1e-10": 30}},
                                      "verdict": {"op_norm_error": 1e-13, "leak_amplitude": 0.0}, "git_commit": "abc", "lean": None, "parent": None}
    (rdir / "round-000.json").write_text(json.dumps({
        "round": 0, "entries": ["r00-F-001"], "candidates": [rec("r00-F-001", (10, 100, 50, 5)), rec("r00-F-002", (1, 1, 1, 5))],   # 002 valid but refused
        "external": [{"source": "qiskit_l3_whole", "valid": False, "reason": "unverifiable",
                      "metrics": {"qubits": 5, "cx": 3, "t_fixed": 7, "n_rot": 2, "t_eps": 77.7, "depth_ct": 268, "t_estimate": {"1e-06": 77.7, "1e-10": 99.0}}}],
        "synthesis_verification": None}))
    t = RP.report_table("twelve", "UE", root=tmp_path)
    best_row = [ln for ln in t.splitlines() if ln.startswith("| GLOBAL BEST")][0]
    assert "r00-F-001" in best_row and "r00-F-002" not in best_row
    whole = [ln for ln in t.splitlines() if ln.startswith("| Qiskit L3 (whole circuit")][0].split("|")
    cells = [c.strip() for c in whole]
    assert cells[6] == "n/a (unverifiable)" and cells[8] == "n/a (unverifiable)" and cells[9] == "n/a (unverifiable)"     # T(1e-6), T(1e-10), depth_CT
    assert cells[7] == "77.7" and "268" not in whole


def test_append_qiskit_refuses_a_non_numeric_global_phase_without_appending():
    from qiskit.circuit import Parameter, QuantumCircuit

    from su2plaq.compress import builder as B

    b = B.Builder(n_qubits=2)
    qc = QuantumCircuit(2, global_phase=Parameter("phi"))
    qc.h(0)
    with pytest.raises(B.BuilderError, match="global phase"):
        b.append_qiskit(qc, [0, 1])
    assert b.n_gates == 0
    ok = QuantumCircuit(2, global_phase=0.3)
    ok.h(0)
    b.append_qiskit(ok, [0, 1])
    assert b.n_gates == 1 and abs(b.circuit().global_phase - 0.3) < 1e-15
