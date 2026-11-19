"""Regression (prompts/008 C1, reports/fixes): a round whose candidates share a label (the program's file stem) must replay.

twelve round 4 (F2/004-clean-frame-inwalk-pa.py and F4/004-clean-frame-inwalk-pa.py) and fuzzy_ub round 5 (F1 and F3
005-two-swap-single-middle.py) were evaluated identically by the replay, but `replay` matched candidates by label and raised
"the replayed candidates differ from the recorded ones".  The candidate's identity is its program path.  These tests rebuild that
situation on a fuzzy_link kind-UE archive under tmp_path (seconds) and check that the comparison is still strict: a replayed round
whose (program_path, label) pairs differ from the recorded ones is still an error, and a recorded round that names a program path
twice is refused before anything is moved."""
import json
import shutil

import pytest

from su2plaq.compress import replay as RP
from su2plaq.compress.round import run_round
from su2plaq.compress.spec import ROOT

ENC, KIND = "fuzzy_link", "UE"
STEM = "001-same-stem"


@pytest.fixture(scope="module")
def dup_root(tmp_path_factory):
    """Round 0 (seeds) and round 1 with two programs of different families and the same file stem, under a temporary root."""
    root = tmp_path_factory.mktemp("replay_dup_labels")
    shutil.copytree(ROOT / "compress" / "programs" / ENC, root / "compress" / "programs" / ENC)
    src = (ROOT / "compress" / "programs" / ENC / "F1" / "001-bell_parity_net13.py").read_text()
    assert 'FAMILY = "F1"' in src
    paths = []
    for fam in ("F1", "F2"):
        p = root / "compress" / "programs" / ENC / fam / f"{STEM}.py"
        p.write_text(src.replace('FAMILY = "F1"', f'FAMILY = "{fam}"'))
        paths.append(str(p))
    run_round(ENC, KIND, 0, evaluate=True, dry_run=False, root=root, lean=False)
    run_round(ENC, KIND, 1, evaluate=True, dry_run=False, root=root, proposals=paths, lean=False)
    r1 = json.loads((root / "results" / "compress" / ENC / "round-001.json").read_text())
    assert [c["label"] for c in r1["candidates"]] == [STEM, STEM]                     # the situation of twelve r4 / fuzzy_ub r5
    assert len({c["id"] for c in r1["candidates"]}) == 2 and all(c["valid"] for c in r1["candidates"])
    return root


def _copy(src, dst):
    shutil.copytree(src / "results", dst / "results")
    shutil.copytree(src / "compress", dst / "compress")
    return dst


def test_round_with_duplicate_labels_replays_with_all_invariants(dup_root, tmp_path):
    root = _copy(dup_root, tmp_path)
    res = RP.replay(ENC, KIND, root=root, tag="dup")
    r1 = [e for e in res["entries"] if e["round"] == 1]
    assert [e["label"] for e in r1] == [STEM, STEM]
    assert sorted(e["program_path"] for e in r1) == sorted(f"compress/programs/{ENC}/{f}/{STEM}.py" for f in ("F1", "F2"))
    assert all(e["id"] == e["old_id"] and e["key_equal"] is True for e in r1)            # each paired with its own recorded candidate
    assert res["lost"] == [] and res["best_new"] == res["best_old"] and RP.problems(res) == {"key_changed": [], "lost": [], "refused": [], "program_changed": []}
    assert res["attempts_unchanged"] is True and res["discoveries_unchanged"] is True


def test_replayed_round_with_other_candidates_is_still_an_error(dup_root, tmp_path):
    """Strictness kept: the recorded round 1 says the second program had another label -> the replay must not pass."""
    root = _copy(dup_root, tmp_path)
    f = root / "results" / "compress" / ENC / "round-001.json"
    d = json.loads(f.read_text())
    d["candidates"][1]["label"] = "001-some-other-stem"
    f.write_text(json.dumps(d, indent=1))
    with pytest.raises(RuntimeError, match="round 1: the replayed candidates differ.*position 1"):
        RP.replay(ENC, KIND, root=root, tag="dup2")


def test_recorded_round_naming_a_program_twice_is_refused_before_anything_moves(dup_root, tmp_path):
    root = _copy(dup_root, tmp_path)
    f = root / "results" / "compress" / ENC / "round-001.json"
    d = json.loads(f.read_text())
    d["candidates"][1]["program_path"] = d["candidates"][0]["program_path"]
    f.write_text(json.dumps(d, indent=1))
    with pytest.raises(ValueError, match="round 1: recorded candidates .* repeated"):
        RP.replay(ENC, KIND, root=root, tag="dup3")
    assert not (root / "results" / "compress" / ENC / "pre-dup3").exists()
    assert not (root / "compress" / "archive" / f"{ENC}-pre-dup3").exists()
