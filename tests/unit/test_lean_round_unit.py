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


def test_certify_best_does_not_erase_a_certificate_after_a_crash(tmp_path, monkeypatch):
    prog = _program(tmp_path, with_lemma=False)
    R.run_round("twelve", "step", 0, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(prog)], lean=False)
    arc = A.Archive.load("twelve", root=tmp_path)
    arc.best().lean = {"status": "certified", "reason": "", "cert_path": "x", "seconds": 1.0, "checker_sha256": "abc"}
    arc.save()
    monkeypatch.setattr(R, "_certify", lambda circ, spec: ({"status": "failed", "reason": "RuntimeError: transient"}, 0.5))
    out = R.certify_best("twelve", "step", root=tmp_path)
    assert out["kept_previous"] is True and out["attempt"]["status"] == "failed"
    assert A.Archive.load("twelve", root=tmp_path).best().lean["status"] == "certified"
    line = (tmp_path / "results" / "compress" / "twelve" / "lean-attempts.jsonl").read_text().strip().splitlines()
    assert len(line) == 1 and json.loads(line[0])["attempt"]["reason"].endswith("transient")
    # a real rejection is a finding and does replace the old status; a fresh certificate replaces too
    monkeypatch.setattr(R, "_certify", lambda circ, spec: ({"status": "rejected", "reason": "state 3 differs"}, 0.5))
    R.certify_best("twelve", "step", root=tmp_path)
    assert A.Archive.load("twelve", root=tmp_path).best().lean["status"] == "rejected"
    monkeypatch.setattr(R, "_certify", lambda circ, spec: ({"status": "certified", "reason": ""}, 0.5))
    assert R.certify_best("twelve", "step", root=tmp_path)["lean"]["status"] == "certified"
