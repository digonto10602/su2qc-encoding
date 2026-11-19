"""Unit tests of su2plaq.lsh.loop (prompts/401 steps 8.1-8.4: seeds, stop rule, facts, registry hooks, rounds, stop state, Lean hook,
headline certification) and su2plaq.lsh.rs_split (step 8.U)."""
import json
import pathlib
import shutil

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.lsh import loop as L
from su2plaq.lsh import rs_split as RS
from su2plaq.metrics.logical import logical_metrics

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_constants():
    assert L.SEED_LABELS == ("general", "wrap_pairs9", "wrap_flags4", "wrap_flags5", "wrap_flags6", "wrap_sn_headline",
                             "wrap_sn_r05F3", "wrap_sn_r02F5", "general+polish", "qiskit_l3")
    assert [f for _, f in L.SEED_FILES][:3] == ["000-general.py", "001-wrap_pairs9.py", "002-wrap_flags4.py"]
    assert len(L.LSH_EVALUATOR_FILES) == 6 and all((ROOT / "src" / "su2plaq" / f).exists() for f in L.LSH_EVALUATOR_FILES)
    assert (L.STOP_MAX_ROUNDS, L.STOP_NO_GAIN_ROUNDS, L.STOP_MAX_SESSIONS, L.N_ANGLE_PAIRS) == (8, 3, 20, 20)
    assert set(L.WRAP_SOURCES) == {"wrap_sn_headline", "wrap_sn_r05F3", "wrap_sn_r02F5"}
    assert "native" in L.BRIEF_NOTE and L.brief_note("lsh", "step") == L.BRIEF_NOTE


def test_wrap_spinnet_step_registers_and_refusals():
    sn = QuantumCircuit(QuantumRegister(8, "d"), QuantumRegister(1, "a"))
    sn.ccx(0, 1, 8)
    qc = L.wrap_spinnet_step(sn)
    assert [r.name for r in qc.qregs] == ["d", "o", "a"] and [r.size for r in qc.qregs] == [12, 12, 1]
    lm = logical_metrics(L.wrap_spinnet_step(QuantumCircuit(QuantumRegister(8, "d"))))
    assert (lm["cx"], lm["t_fixed"]) == (40, 32)                            # the transcoder pair alone (M7-V1)
    with_o = QuantumCircuit(QuantumRegister(8, "d"), QuantumRegister(8, "o"))
    with_o.cx(0, 1)
    assert L.wrap_spinnet_step(with_o).num_qubits == 24                      # untouched outer register is dropped onto o[12]
    with_o.cx(8, 1)
    with pytest.raises(ValueError):
        L.wrap_spinnet_step(with_o)
    with pytest.raises(ValueError):
        L.wrap_spinnet_step(QuantumCircuit(QuantumRegister(7, "d")))
    with pytest.raises(ValueError):
        L.wrap_spinnet_step(QuantumCircuit(QuantumRegister(8, "x")))


@pytest.mark.parametrize("label,cx", [("general", 94), ("wrap_flags4", 84), ("wrap_sn_headline", 71)])
def test_seed_circuit_counts(label, cx):
    qc = L.seed_circuit(label, 0.37, 0.61)
    assert [r.name for r in qc.qregs][:2] == ["d", "o"] and logical_metrics(qc)["cx"] == cx


def test_seed_circuit_errors_and_pin(tmp_path):
    for bad in ("nope", "general+polish", "qiskit_l3"):
        with pytest.raises(ValueError):
            L.seed_circuit(bad, 0.37, 0.61)
    rel = pathlib.Path(L.WRAP_SOURCES["wrap_sn_headline"][0])
    (tmp_path / rel).parent.mkdir(parents=True)
    shutil.copy(ROOT / rel, tmp_path / rel)
    assert L.seed_circuit("wrap_sn_headline", 0.37, 0.61, root=tmp_path).num_qubits == 25      # intact copy: the pin accepts it
    with open(tmp_path / rel, "a") as fh:
        fh.write("\n# edited\n")
    with pytest.raises(ValueError, match="pinned"):
        L.seed_circuit("wrap_sn_headline", 0.37, 0.61, root=tmp_path)


def test_seed_program_source_text(monkeypatch):
    from su2plaq.compress import baselines
    from su2plaq.encodings.lsh import LSH

    monkeypatch.setattr(baselines, "get_encoding", lambda name: LSH())          # the registry of step 8.R does this in production
    for label in ("general", "wrap_flags4"):
        text = L.seed_program_source(label)
        compile(text, label, "exec")
        for forbidden in ("su2plaq.circuits", "su2plaq.spinnet", "su2plaq.lsh"):
            assert forbidden not in text
        assert "from su2plaq.compress.builder import Builder" in text and "def build(spec):" in text
    assert "r02-F1-002" in L.seed_program_source("wrap_sn_headline") and L.WRAP_SOURCES["wrap_sn_headline"][1] in L.seed_program_source("wrap_sn_headline")
    with pytest.raises(ValueError):
        L.seed_program_source("qiskit_l3")


def _rec(cx=71, t_sum=22480, rho=0, qubits=25, n_rot=17, t_fixed=48):
    return {"id": "x", "cx": cx, "t_sum": t_sum, "rho": rho, "qubits": qubits, "n_rot": n_rot, "t_fixed": t_fixed}


def test_improves_rule():
    old = _rec()
    assert L.improves(old, None) and not L.improves(None, old) and not L.improves(_rec(), old)
    assert L.improves(_rec(cx=70, t_sum=99999), old) and not L.improves(_rec(cx=72, t_sum=1), old)
    band = 20 * 17
    assert not L.improves(_rec(t_sum=22480 - band), old) and L.improves(_rec(t_sum=22480 - band - 1), old)
    assert L.improves(_rec(t_sum=22480 + 5, rho=0), _rec(rho=1)) and L.improves(_rec(t_sum=22480 + 5, qubits=24), old)
    assert L.improves(_rec(n_rot=16, t_sum=22480 - 100), old) and not L.improves(_rec(n_rot=16, t_sum=22480 + 100), old)
    assert L.stop_key(old) == (71, 22480, 0, 25)


def test_structure_facts_read_from_lean_and_file_is_current(tmp_path):
    facts = L.structure_facts()
    by = {f["name"]: f for f in facts["facts"]}
    assert by["card_inner_codes"]["value"] == 47 and by["coupling_by_y_weight"]["value"] == {"0": -4, "1": 2, "2": -1}
    assert by["transcoder_overhead"]["proved_by"] == "numerical" and by["eight_differences"]["proved_by"] == "decide"
    p = pathlib.Path(L.write_structure(path=tmp_path / "s.json"))
    assert json.loads(p.read_text())["facts"] == json.loads(json.dumps(facts["facts"]))
    mtime = p.stat().st_mtime_ns
    L.write_structure(path=p)
    assert p.stat().st_mtime_ns == mtime                                      # unchanged content: not rewritten
    committed = ROOT / "compress" / "specs" / "lsh-structure.json"
    assert committed.exists() and json.loads(committed.read_text()) == json.loads(p.read_text())


def test_structure_facts_refuse_changed_lean_source(tmp_path):
    d = tmp_path / "lean" / "Su2Plaq" / "LSH"
    d.mkdir(parents=True)
    for n in ("Counts", "Facts", "Circuit"):
        shutil.copy(ROOT / "lean" / "Su2Plaq" / "LSH" / f"{n}.lean", d / f"{n}.lean")
    assert L.structure_facts(root=tmp_path)["facts"]
    t = (d / "Counts.lean").read_text().replace("innerCodes = 47", "innerCodes = 48")
    (d / "Counts.lean").write_text(t)
    with pytest.raises(RuntimeError, match="card_inner_codes"):
        L.structure_facts(root=tmp_path)
    (d / "Counts.lean").write_text(t.replace("innerCodes = 48", "innerCodes = 47") + "\n-- native_decide\n")
    with pytest.raises(RuntimeError, match="native_decide"):
        L.structure_facts(root=tmp_path)


def test_rs_split_row():
    R = RS.recoupling()
    assert R.shape == (433, 433) and np.abs(R.T @ R - np.eye(433)).max() <= 1e-12
    s = RS.structure()
    assert (s["nnz"], s["max_per_row"], s["sites_touched"], s["qubits_touched"]) == (400, 4, 6, 18)
    assert (s["ours"]["nnz"], s["ours"]["max_per_row"]) == (256, 1) and s["spectrum_diff"] <= 1e-10


# ---- step 8.2: registry hooks (the `lsh` entry of the shared registry)
def test_spec_and_general_circuit_by_kind():
    sp = L.spec()
    assert (sp.encoding, sp.kind, sp.order, sp.alpha, sp.beta) == ("lsh", "step", 1, 0.37, 0.61) and L.spec(2).order == 2
    for kind, cx in (("step", 94), ("UB", 94), ("UE", 0)):
        import dataclasses

        qc = L.general_circuit(dataclasses.replace(sp, kind=kind))
        assert [r.name for r in qc.qregs][:2] == ["d", "o"] and logical_metrics(qc)["cx"] == cx, kind


def test_general_program_path_written_once_under_root(tmp_path):
    sp = L.spec()
    gp = L.general_program_path(sp, root=tmp_path)
    assert gp == tmp_path / "compress" / "programs" / "lsh" / "seed" / "000-general.py"
    text = gp.read_text()
    assert text.lstrip().startswith('"""SUMMARY:') and "su2plaq.circuits" not in text and "su2plaq.lsh" not in text
    gp.write_text(text + "\n# marker\n")
    assert L.general_program_path(sp, root=tmp_path).read_text().endswith("# marker\n")        # generated once, then immutable


def test_import_seed_paulo15_and_reasons():
    sp = L.spec()
    s = L.import_seed(sp, "paulo15")
    assert s.fixed_angle and s.kind == "UB" and s.beta == -0.05 and s.alpha is None and not s.can_be_parent
    assert s.qc.num_qubits == 12 + 12 + 7 and logical_metrics(s.qc)["cx"] == 108
    for src in ("paulo34", "lean22", "lean22_v2", "spinnet15"):
        assert isinstance(L.import_seed(sp, src), str)
    with pytest.raises(ValueError):
        L.import_seed(sp, "nope")


def test_angle_linear_reasons():
    sp = L.spec()
    qc = L.general_circuit(sp)
    assert L.angle_linear(qc, sp) == (True, "ok")
    bad = qc.copy()
    bad.p(0.123, 24)
    bad.p(-0.123, 24)
    ok, why = L.angle_linear(bad, sp)
    assert ok is False and why.startswith("non_linear_angle")
    wide = QuantumCircuit(QuantumRegister(12, "d"), QuantumRegister(12, "o"), QuantumRegister(39, "a"))
    assert L.angle_linear(wide, sp) == (False, "too_many_qubits")


def test_render_spec_sections_and_no_seed_names():
    sp = L.spec()
    text = L.render_spec(sp)
    assert text == sp.render()
    for needle in ("## LSH register and rules", "## Proved structure (Lean)", "## Headline rule", "## Tools", "Abelian Gauss law",
                   "inner_codes_from_rules", "transcoder_overhead", "--encoding lsh --kind step", "read-only"):
        assert needle in text, needle
    assert text.index("## LSH register and rules") < text.index("## Proved structure (Lean)") < text.index("## Headline rule") < text.index("## Tools")
    for banned in ("wrap_sn_headline", "r02-F1-002", "su2plaq.spinnet.loop"):
        assert banned not in text


# ---- step 8.3: seed candidates, stop state, CLI
def _stop_json(tmp_path, records):
    f = tmp_path / "results" / "compress" / "lsh" / "stop.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"rounds": [{"round": r, "headline_id": f"h{r}", "robust_key": [0], "record": rec} for r, rec in enumerate(records)]}))
    return f


def test_stop_state_streak_reasons_and_sessions(tmp_path):
    assert L.stop_state(root=tmp_path) == {"rounds": [], "streak": 0, "sessions": 0, "stop": False, "reason": None, "reasons": [],
                                           "max_rounds": 8, "no_gain_rounds": 3, "max_sessions": 20}
    f = _stop_json(tmp_path, [_rec(), _rec(), _rec(cx=70), _rec(cx=70), _rec(cx=70)])
    st = L.stop_state(root=tmp_path)
    assert [x["improved"] for x in st["rounds"]] == [True, False, True, False, False] and st["streak"] == 2 and st["stop"] is False
    assert json.loads(f.read_text())["streak"] == 2                                 # written back
    d = tmp_path / "compress" / "attempts"
    d.mkdir(parents=True)
    (d / "lsh.jsonl").write_text("".join(json.dumps({"round": r, "family": fam}) + "\n" for r, fam in
                                         ((0, "seed"), (1, "F1"), (1, "F1"), (1, "F2"), (2, "F1"))))
    assert L.stop_state(root=tmp_path)["sessions"] == 3                              # (1,F1) (1,F2) (2,F1); round 0 not counted
    (tmp_path / "compress" / "ideation").mkdir()
    (tmp_path / "compress" / "ideation" / "lsh.md").write_text("x")
    assert L.stop_state(root=tmp_path)["sessions"] == 4                              # + the ideation session
    _stop_json_more = json.loads(f.read_text())["rounds"]
    _stop_json_more.append({"round": 5, "headline_id": "h", "robust_key": [0], "record": _rec(cx=70)})
    f.write_text(json.dumps({"rounds": _stop_json_more}))
    st = L.stop_state(root=tmp_path)
    assert st["streak"] == 3 and st["stop"] is True and st["reason"] == "no_gain"


def test_stop_state_max_rounds_and_max_sessions(tmp_path):
    recs = [_rec(cx=71 - r) for r in range(9)]                                      # improves every round, nine records: rounds 0..8
    _stop_json(tmp_path, recs)
    st = L.stop_state(root=tmp_path)
    assert st["streak"] == 0 and st["reason"] == "max_rounds" and st["reasons"] == ["max_rounds"]
    d = tmp_path / "compress" / "attempts"
    d.mkdir(parents=True)
    (d / "lsh.jsonl").write_text("".join(json.dumps({"round": 1 + k // 5, "family": f"F{k % 5}"}) + "\n" for k in range(20)))
    assert L.stop_state(root=tmp_path)["sessions"] == 20 and "max_sessions" in L.stop_state(root=tmp_path)["reasons"]


def test_seed_candidates_ten_rows_written_once(tmp_path):
    sp = L.spec()
    cands = L.seed_candidates(sp, tmp_path)
    assert [c[0] for c in cands] == list(L.SEED_LABELS)
    d = tmp_path / "compress" / "programs" / "lsh" / "seed"
    for label, path, fn in cands:
        if path is not None:
            assert path.parent == d and path.read_text().lstrip().startswith('"""SUMMARY:'), label
            assert "su2plaq.circuits" not in path.read_text() and "su2plaq.spinnet" not in path.read_text()
        assert (fn is not None) == (label in ("general+polish", "qiskit_l3")), label
    by = {c[0]: c for c in cands}
    assert by["general"][1].name == "000-general.py" and by["wrap_sn_headline"][1].name == "005-wrap_sn_headline.py"
    assert by["qiskit_l3"][1] is None                                               # measured: no angle-linear program (planner research 401)
    marker = by["wrap_flags4"][1]
    marker.write_text(marker.read_text() + "\n# kept\n")
    again = {c[0]: c for c in L.seed_candidates(sp, tmp_path)}
    assert again["wrap_flags4"][1].read_text().endswith("# kept\n")                  # immutable once written


def test_paulo_wrapped_external_row():
    row = L._paulo_row(L.spec())
    assert row["source"] == "paulo15_wrapped" and row["fixed_angle"] is True and row["kind"] == "UB" and row["beta"] == -0.05
    assert row["valid"] is True and row["certified"] is True and row["op_norm_error"] <= 1e-10 and row["metrics"]["cx"] == 108


def test_wrapped_sources_record_pins(tmp_path):
    rec = L._wrapped_sources_record()
    assert {k: (v["path"], v["sha256"], v["spinnet_entry"]) for k, v in rec.items()} == {k: tuple(v) for k, v in L.WRAP_SOURCES.items()}
    rel = pathlib.Path(L.WRAP_SOURCES["wrap_sn_r05F3"][0])
    (tmp_path / rel).parent.mkdir(parents=True)
    (tmp_path / rel).write_text("edited\n")
    with pytest.raises(ValueError, match="pinned"):
        L._wrapped_sources_record(root=tmp_path)


def test_main_usage_and_stop_state_cli(tmp_path, capsys):
    with pytest.raises(SystemExit):
        L.main([])
    with pytest.raises(SystemExit):
        L.main(["no-such-command"])
    _stop_json(tmp_path, [_rec()])
    assert L.main(["stop-state", "--root", str(tmp_path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["streak"] == 0 and out["rounds"][0]["improved"] is True and out["stop"] is False


# ---- step 8.4: Lean hook
def test_lean_certify_hook_statuses_and_binding(tmp_path):
    sp = L.spec()
    bind = {"entry_id": "r00-seed-000", "program_file_sha256": "ab" * 32}
    r = L.lean_certify(L.general_circuit(sp), sp, timeout=900.0, extra_provenance=bind, out_dir=tmp_path)
    assert r["status"] == "certified" and len(r["checker_sha256"]) == 64 and r["axioms"] == []
    c = json.loads(pathlib.Path(r["cert_path"]).read_text())
    assert c["provenance"]["entry_id"] == bind["entry_id"] and c["provenance"]["program_file_sha256"] == bind["program_file_sha256"]
    assert c["gates_sha256"] == c["program_sha256"] and "git_dirty" in c["provenance"]
    neg = L.lean_certify(L.seed_circuit("general", 0.37, -0.61), sp, timeout=900.0, out_dir=tmp_path)
    assert neg["status"] == "rejected" and neg["reason"]
    bad = L.general_circuit(sp)
    bad.p(0.123, 24)
    bad.p(-0.123, 24)
    na = L.lean_certify(bad, sp, timeout=900.0, out_dir=tmp_path)
    assert na["status"] == "n_a" and na["reason"].startswith("non_linear_angle") and na["cert_path"] is None


# ---- steps 8.3 / 8.4 end to end on a temporary root (dry round 0 without Lean, headline certification, briefs)
@pytest.fixture(scope="module")
def dry_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("lsh-dry")
    info = L.seed_round(root=root, lean=False, dry_run=True)
    return root, info


def test_dry_seed_round_files_and_stop_record(dry_root):
    root, info = dry_root
    assert info["round"] == 0 and info["n_valid"] == 10 and info["n_invalid"] == 0 and tuple(info["best_key"])[0] == 71
    d = json.loads((root / "results" / "compress" / "lsh" / "round-000.json").read_text())
    assert [c["label"] for c in d["candidates"]] == list(L.SEED_LABELS)
    assert {x["source"] for x in d["external"]} >= {"qiskit_l3_whole", "paulo15_wrapped"} and set(d["lsh"]["wrapped_sources"]) == set(L.WRAP_SOURCES)
    st = json.loads((root / "results" / "compress" / "lsh" / "stop.json").read_text())
    rec = st["rounds"][0]["record"]
    assert rec["id"] == "r00-seed-005" and (rec["cx"], rec["rho"], rec["qubits"], rec["n_rot"], rec["t_fixed"]) == (71, 0, 25, 17, 48)
    assert st["rounds"][0]["improved"] is True and st["streak"] == 0 and st["stop"] is False
    assert L.stop_record("r00-seed-005", root=root) == rec


def test_dry_certify_headline_binding_and_theorem_file(dry_root):
    root, _ = dry_root
    out = L.certify_headline(root=root)
    assert out["headline"] == out["archive_best"] == "r00-seed-005" and out["lean_headline"]["status"] == "certified"
    cert = json.loads((root / out["lean_headline"]["cert_path"]).read_text())
    assert cert["provenance"]["entry_id"] == "r00-seed-005" and cert["provenance"]["program_file_sha256"] == out["lean_headline"]["program_file_sha256"]
    text = pathlib.Path(out["theorem_file"]).read_text()
    assert text.splitlines()[0].startswith("-- entry r00-seed-005, program sha256 ")
    assert "theorem lsh_best : Su2PlaqCert.LSH.checkJsonString certJson = true := by native_decide" in text
    from su2plaq.compress import archive as A

    e = next(x for x in A.Archive.load("lsh", root=root, n_alt=2, strict=True).entries() if x.id == "r00-seed-005")
    assert e.lean["status"] == "certified" and e.lean["program_file_sha256"] == cert["provenance"]["program_file_sha256"]


def test_dry_briefs_cli(dry_root, capsys):
    root, _ = dry_root
    assert L.main(["ideation", "--root", str(root)]) == 0
    assert L.main(["brief", "--round", "1", "--family", "F1", "--root", str(root)]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    ideation, brief = pathlib.Path(out[-2]), pathlib.Path(out[-1])
    assert "compress/ideation/lsh.md" in ideation.read_text() and L.BRIEF_NOTE.strip() in ideation.read_text()
    assert "--encoding lsh" in brief.read_text() and L.BRIEF_NOTE.strip() in brief.read_text()
    assert (root / "compress" / "specs" / "lsh-structure.json").exists()
