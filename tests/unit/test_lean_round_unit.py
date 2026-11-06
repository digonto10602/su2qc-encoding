"""Lean hooks of the compression round (prompts/006 step 2.L7/2.L8), exercised on a scratch root only."""
import json
import pathlib
import shutil

from su2plaq.compress import archive as A
from su2plaq.compress import round as R
from su2plaq.compress.baselines import general_program_path
from su2plaq.compress.spec import default_spec


def _program(tmp_path, with_lemma):
    spec = default_spec("twelve", "step")
    src = pathlib.Path(general_program_path(spec))
    d = tmp_path / "compress" / "programs" / "twelve"
    d.mkdir(parents=True, exist_ok=True)
    prog = d / "001-general-copy.py"
    shutil.copy(src, prog)
    if with_lemma:
        (d / "001-general-copy.lean").write_text("import Su2Plaq\n\ntheorem proposer_fact : (2 : Nat) + 2 = 4 := by decide\n")
    return prog


def test_round_lean_default_records_certificate_and_lemma_check(tmp_path):
    prog = _program(tmp_path, with_lemma=True)
    info = R.run_round("twelve", "step", 0, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(prog)])
    assert info["n_valid"] == 1 and 0 < info["lean_seconds"] <= 1200
    best = A.Archive.load("twelve", root=tmp_path).best()
    assert best.lean["status"] == "certified", best.lean
    rec = json.loads((tmp_path / "results" / "compress" / "twelve" / "round-000.json").read_text())
    cand = rec["candidates"][0]
    assert cand["lean"]["status"] == "certified"
    assert cand["lean_lemmas"]["status"] == "proved" and cand["lean_lemmas"]["theorems"] == ["proposer_fact"]


def test_certify_best_after_a_lean_free_round(tmp_path):
    prog = _program(tmp_path, with_lemma=False)
    info = R.run_round("twelve", "step", 0, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(prog)], lean=False)
    assert info["lean_seconds"] == 0.0
    assert A.Archive.load("twelve", root=tmp_path).best().lean is None
    out = R.certify_best("twelve", "step", root=tmp_path)
    assert out["lean"]["status"] == "certified", out
    best = A.Archive.load("twelve", root=tmp_path).best()
    assert best.lean["status"] == "certified" and best.valid
