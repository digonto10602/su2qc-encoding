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
    R.run_round("twelve", "UE", 1, evaluate=True, dry_run=True, root=d, proposals=[str(a), str(b)])
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
