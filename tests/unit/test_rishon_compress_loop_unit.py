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


# ---------------------------------------------------------------------------------- engine qubit limit (62)
_WIDE = '"""SUMMARY: dummy program with {n} qubits (engine-limit test).\n\n"""\nFAMILY = "Ftest"\nPARENT = None\n\n' \
        "from su2plaq.compress.builder import Builder\n\n\ndef build(spec):\n    b = Builder(spec)\n    b.alloc({a}, 'work')\n" \
        "    b.x(48)\n    b.x(48)\n    return b\n"


def _wide(tmp_path, n_anc, name="001-wide.py"):
    d = tmp_path / "compress" / "programs" / "rishon" / "Ftest"
    d.mkdir(parents=True, exist_ok=True)
    f = d / name
    f.write_text(_WIDE.format(n=48 + n_anc, a=n_anc))
    return f


def test_engine_limit_constant_matches_the_laptop_engine():
    import numpy as np
    from qiskit import QuantumCircuit

    from su2plaq.evaluate import sparse_sim

    assert S.ENGINE_QUBIT_LIMIT == 62
    sparse_sim.run_batch(QuantumCircuit(62), np.zeros(1, dtype=np.int64))              # accepted
    with pytest.raises(ValueError, match="at most 62 qubits"):
        sparse_sim.run_batch(QuantumCircuit(63), np.zeros(1, dtype=np.int64))


def test_wide_program_is_recorded_invalid_by_run_round(tmp_path):
    f = _wide(tmp_path, 15)                                             # 48 + 15 = 63 qubits
    info = RD.run_round("step", 1, evaluate=True, dry_run=True, root=tmp_path, proposals=[f], lean=False)
    assert info["n_valid"] == 0 and info["n_invalid"] == 1
    rd = json.loads((tmp_path / "results" / "compress" / "rishon" / "round-001.json").read_text())
    (inv,) = rd["invalid"]
    assert inv["reason"] == "engine_qubit_limit" and "63 qubits" in inv["message"] and "62" in inv["message"]
    fb = list((tmp_path / "results" / "compress" / "rishon" / "feedback").glob("*.json"))
    assert len(fb) == 1 and json.loads(fb[0].read_text())["reason"] == "engine_qubit_limit"
    assert "engine_qubit_limit" in (tmp_path / "compress" / "attempts" / "rishon.jsonl").read_text()


def test_wide_program_run_candidate_reports_reason(tmp_path, capsys):
    f = _wide(tmp_path, 15)
    assert RC.main([str(f), "--kind", "step", "--trial"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("invalid: engine_qubit_limit") and "63 qubits" in out and "limit of 62" in out


def test_62_qubit_program_is_not_rejected_by_the_limit(tmp_path):
    f = _wide(tmp_path, 14, "002-ok62.py")
    r = RC.evaluate_program(f, S.rishon_spec("step"), "trial")
    assert r.reason != "engine_qubit_limit"
