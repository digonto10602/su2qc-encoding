"""M6-R1..R3 — the loop plumbing for rishon (prompts/203 §3.1 `rishon.compress.{round,brief,run_candidate}`): the CLI,
a dry round end to end under a temporary root, the briefs, and the laptop report reading our round JSON.  Time limits are
justified in prompts/203 §6; everything else is exact."""
import functools
import json
import os
import pathlib
import subprocess
import sys
import time

import pytest

from tests.acceptance._api import api

ENC = "rishon"


@functools.lru_cache(maxsize=None)
def _spec(kind):
    return api("su2plaq.rishon.compress.spec:rishon_spec")(kind)


def _program(kind) -> pathlib.Path:
    return pathlib.Path(api("su2plaq.rishon.compress.baselines:general_program_path")(_spec(kind)))


def _cli(root, args, timeout):
    """Run the CLI in a subprocess.  A stub (NotImplementedError) in the child cannot reach the conftest PENDING hook, so it
    is reported as `PENDING:` here (prompts/203 erratum E1); any other non-zero exit is a real failure."""
    api("su2plaq.rishon.compress.run_candidate:main")          # PENDING when the module / entry point does not exist
    t0 = time.time()
    p = subprocess.run([sys.executable, "-m", "su2plaq.rishon.compress.run_candidate", *args], cwd=root, capture_output=True,
                       text=True, env={**os.environ, "PYTHONPATH": str(root / "src")}, timeout=timeout + 60)
    if p.returncode != 0 and "NotImplementedError" in p.stderr:
        pytest.fail(f"PENDING: run_candidate CLI is a stub: {p.stderr.strip().splitlines()[-1]}", pytrace=False)
    return p, time.time() - t0


def test_M6_R1_run_candidate_cli_trial(root, tmp_path):
    """`python -m su2plaq.rishon.compress.run_candidate <ue program> --kind UE --trial --json out` exits 0 with valid=true
    within 60 s (a 12-gate program; the limit absorbs process start-up on a loaded machine)."""
    out = tmp_path / "trial.json"
    p, wall = _cli(root, [str(_program("UE")), "--kind", "UE", "--trial", "--json", str(out)], 60)
    assert p.returncode == 0, p.stderr[-2000:]
    assert wall <= 60
    d = json.loads(out.read_text())
    assert d["valid"] is True and d["reason"] == "ok" and d["mode"] == "trial" and d["metrics"]["cx"] == 8
    assert "valid" in p.stdout.lower()


def test_M6_R2_round_dry_run_brief_and_report(tmp_path):
    """Dry round 0 (kind UE) with the U_E program as the only candidate under a temporary root, then the ideation brief,
    a family brief, a dry round 1, the laptop report table and summary.json from our round JSON; attempts / discoveries /
    feedback files exist; the evaluator sha of the archived entry is the rishon code hash."""
    kind = "UE"
    spec = _spec(kind)
    path = _program(kind)
    rd = api("su2plaq.rishon.compress.round")
    br = api("su2plaq.rishon.compress.brief")
    A = api("su2plaq.compress.archive")
    info0 = rd.run_round(kind, round=0, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(path)], lean=False)
    assert info0["round"] == 0 and info0["n_valid"] >= 1 and info0["best_key"] is not None
    ib = pathlib.Path(br.make_ideation_brief(kind, root=tmp_path))
    assert ib.exists() and f"compress/specs/{ENC}-{kind}.md" in ib.read_text() and "ideation" in ib.read_text().lower()
    brief = pathlib.Path(br.make_brief(kind, round=1, family="seed", root=tmp_path))
    txt = brief.read_text()
    assert brief.exists() and "Rewrite the parent to improve the key; return the complete program" in txt
    assert "su2plaq.rishon.compress.run_candidate" in txt and "su2plaq.rishon.compress.oracle" in txt and f"compress/programs/{ENC}/" in txt
    assert (tmp_path / "compress" / "specs" / f"{ENC}-{kind}.md").exists()
    info1 = rd.run_round(kind, round=1, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(path)], lean=False)
    assert info1["round"] == 1 and info1["n_valid"] >= 1
    rj = tmp_path / "results" / "compress" / ENC / "round-001.json"
    d = json.loads(rj.read_text())
    assert d["round"] == 1 and len(d["entries"]) >= 1 and "git_commit" in d["provenance"] and d["encoding"] == ENC
    rec = d["candidates"][0]
    for k in ("label", "id", "family", "valid", "reason", "key", "metrics", "verdict", "alt_ok", "skeleton_equal", "parent", "round", "mode"):
        assert k in rec, k
    assert rec["verdict"]["method"] == "rishon_inner_block" and rec["verdict"]["certified"] is True
    arch = A.Archive.load(ENC, root=tmp_path)
    best = arch.best()
    assert best is not None and best.valid and best.evaluator_sha256 == api("su2plaq.rishon.compress:code_hash")()
    assert (tmp_path / "compress" / "attempts" / f"{ENC}.jsonl").exists()
    assert (tmp_path / "results" / "compress" / ENC / "feedback" / f"{best.id}.json").exists()
    text = api("su2plaq.compress.report:report_table")(ENC, kind, root=tmp_path)
    for col in ("qubits", "CX", "T_fixed", "N_rot", "T(1e-6)", "depth", "verdict", "Lean"):
        assert col in text
    assert "general" in text
    summary = tmp_path / "results" / "compress" / ENC / "summary.json"
    assert summary.exists() and json.loads(summary.read_text())["global_best"] == best.id


@pytest.mark.slow
def test_M6_R3_run_candidate_cli_step_trial(root, tmp_path):
    """The general step program (about 4 600 macro gates) in trial mode through the CLI: valid within 300 s."""
    out = tmp_path / "trial-step.json"
    p, wall = _cli(root, [str(_program("step")), "--kind", "step", "--trial", "--json", str(out)], 300)
    assert p.returncode == 0, p.stderr[-2000:]
    assert wall <= 300
    d = json.loads(out.read_text())
    assert d["valid"] is True and d["metrics"]["qubits"] == 58 and d["metrics"]["n_rot"] == 166
