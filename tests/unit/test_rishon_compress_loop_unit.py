"""Step 6.4 unit tests: briefs, run_candidate CLI (in process), round seeds / helpers (no full evaluation; the dry rounds are the
acceptance tests M6-R2 / R3)."""
import functools
import json

import pytest

from su2plaq.rishon.compress import baselines as BL
from su2plaq.rishon.compress import brief as BR
from su2plaq.rishon.compress import round as RD
from su2plaq.rishon.compress import run_candidate as RC
from su2plaq.rishon.compress import spec as S


@functools.lru_cache(maxsize=None)
def _sp(kind):
    return S.rishon_spec(kind)


def test_ideation_and_family_briefs_name_rishon_commands_and_rules(tmp_path):
    ib = BR.make_ideation_brief("step", root=tmp_path)
    t = ib.read_text()
    assert ib == tmp_path / "compress" / "briefs" / "rishon" / "ideation.md"
    assert "compress/specs/rishon-step.md" in t and "compress/specs/rishon-structure.json" in t and "compress/ideation/rishon.md" in t
    assert (tmp_path / "compress" / "specs" / "rishon-step.md").read_text() == S.render_spec(_sp("step"))
    assert json.loads((tmp_path / "compress" / "specs" / "rishon-structure.json").read_text()) == S.structure_facts()
    b = BR.make_brief("step", 1, "F1", root=tmp_path)
    t = b.read_text()
    assert b.name == "round-001-F1.md" and BR.TASK_LINE in t and "compress/programs/rishon/F1/001-<slug>.py" in t
    for needle in ("su2plaq.rishon.compress.run_candidate", "su2plaq.rishon.compress.oracle", "may be neither read nor written",
                   "is not a validity verdict", "Only `--full` decides", "pruning_bound", "never `su2plaq.rishon.*`", "none: write a fresh"):
        assert needle in t, needle
    assert "su2plaq.compress.run_candidate <" not in t.replace("Do NOT use `su2plaq.compress.run_candidate`", "")
    assert BR.make_brief("UE", 3, "seed", root=tmp_path).name == "round-003-seed.md"


def test_brief_cli(tmp_path, capsys):
    assert BR.main(["--ideation", "--kind", "UE", "--root", str(tmp_path)]) == 0
    assert "ideation.md" in capsys.readouterr().out
    assert BR.main(["--round", "2", "--family", "F2", "--root", str(tmp_path)]) == 0
    assert (tmp_path / "compress" / "briefs" / "rishon" / "round-002-F2.md").exists()
    with pytest.raises(SystemExit):
        BR.main(["--round", "2", "--root", str(tmp_path)])


def test_run_candidate_main_in_process(tmp_path, capsys):
    prog = BL.general_program_path(_sp("UE"))
    out = tmp_path / "o.json"
    assert RC.main([str(prog), "--kind", "UE", "--trial", "--json", str(out)]) == 0
    txt = capsys.readouterr().out
    assert txt.startswith("valid: ok") and "NOT a validity verdict" in txt and "metrics: CX 8" in txt
    d = json.loads(out.read_text())
    assert d["valid"] and d["mode"] == "trial" and d["verdict"]["method"] == "rishon_inner_block"
    bad = tmp_path / "bad.py"
    bad.write_text("import os\n")
    assert RC.main([str(bad), "--kind", "UE"]) == 1
    assert capsys.readouterr().out.startswith("invalid: contract")


def test_seed_candidates_labels_and_programs(tmp_path):
    (tmp_path / "ue").mkdir()
    ue = RD._seed_candidates(_sp("UE"), tmp_path / "ue")      # one root per kind: the seed file numbers are not kind-specific
    assert [x[0] for x in ue] == ["general", "general+polish", "qiskit_l3"] and all(x[1] is not None for x in ue)
    st = RD._seed_candidates(_sp("step"), tmp_path)
    assert [x[0] for x in st] == ["general", "general+polish", "qiskit_l3", "general-rccx", "general-mcx"]
    by = {x[0]: x for x in st}
    assert by["qiskit_l3"][1] is None and by["qiskit_l3"][2] is not None           # Qiskit merges a Clifford phase: no linear program
    for lab, name in (("general", "000-general.py"), ("general-rccx", "001-general-rccx.py"), ("general-mcx", "002-general-mcx.py"),
                      ("general+polish", "010-general_polish.py")):
        assert by[lab][1].name == name and by[lab][1].parent == tmp_path / "compress" / "programs" / "rishon" / "seed"
    ext = RD._external_rows(_sp("UE"))
    assert [x["source"] for x in ext] == ["qiskit_l3_whole", "paulo34", "lean22", "lean22_v2", "spinnet15"]
    assert ext[0]["valid"] is False and ext[0]["metrics"]["cx"] == 8 and all(isinstance(x["reason"], str) for x in ext)


def test_round_argument_errors_and_empty_certify(tmp_path, capsys):
    with pytest.raises(SystemExit):
        RD.main(["--kind", "UE"])                                  # neither --seed nor --round
    assert RD.certify_best("UE", root=tmp_path) == {"entry": None, "lean": None, "seconds": 0.0}
    assert RD.main(["--kind", "UE", "--certify-best", "--root", str(tmp_path)]) == 0
    # evaluate=False writes only the (empty) round file
    info = RD.run_round("UE", 1, evaluate=False, dry_run=True, root=tmp_path, proposals=[], lean=False)
    assert info["n_valid"] == 0 and info["best_key"] is None
    assert json.loads((tmp_path / "results" / "compress" / "rishon" / "round-001.json").read_text())["candidates"] == []


def test_certify_reports_unbuilt_checker():
    d, sec = RD._certify(BL.general_circuit(_sp("UE")), _sp("UE"))
    assert d["status"] in ("not_run", "certified", "n_a", "failed") and sec >= 0
