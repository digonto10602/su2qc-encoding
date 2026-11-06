"""Unit tests for su2plaq.spinnet.loop (M4 steps 4.0-4.3; prompts/104 §2): interface, shim, facts, spec text, worker, seeds, rounds, CLI."""
import dataclasses
import json
import numpy as np
import pathlib
import re
import subprocess
import sys

import pytest

from su2plaq.compress import evaluate as E
from su2plaq.compress import round as R
from su2plaq.compress import spec as S
from su2plaq.spinnet import loop as L

ROOT = S.ROOT


@pytest.fixture(scope="module")
def sp():
    return L.spec()


# ------------------------------------------------------------------------------------------------- interface (4.0)
def test_interface_names_exist():
    for name in ("ENC", "KIND", "SPINNET_CODE_FILES", "INSTALLED", "install", "spec", "code_hash", "structure_facts", "render_spec",
                 "write_spec", "general_program_path", "SeedCircuit", "import_seed", "seed_program_source", "evaluate_seed",
                 "seed_round", "run_round", "make_ideation_brief", "make_brief", "report_table", "certify_best", "main"):
        assert hasattr(L, name), name
    assert (L.ENC, L.KIND) == ("spinnet", "step")
    assert L.SPINNET_CODE_FILES == ("encodings/spinnet.py", "circuits/spinnet.py", "spinnet/walk.py", "spinnet/trotter_v2.py",
                                    "spinnet/paulo.py")
    assert all((ROOT / "src" / "su2plaq" / f).exists() for f in L.SPINNET_CODE_FILES)


def test_seed_circuit_dataclass_fields():
    f = {x.name: x for x in dataclasses.fields(L.SeedCircuit)}
    assert list(f) == ["qc", "source", "fixed_angle", "alpha", "beta", "kind", "can_be_parent", "gauge"]
    assert f["gauge"].default is None


# ------------------------------------------------------------------------------------------------------- shim (4.1)
def test_install_is_idempotent_and_registers_the_four_overrides(sp):
    L.install()
    first = dict(L.INSTALLED)
    L.install()
    assert L.INSTALLED == first and set(L.INSTALLED) == {"encoding", "build_in_subprocess", "certify"}
    assert S.get_encoding("spinnet").name == "spinnet"
    from su2plaq.encodings.base import NOMINAL_ANGLES

    assert NOMINAL_ANGLES["spinnet"] == (0.37, 0.61)
    assert E._build_in_subprocess is not L.INSTALLED["build_in_subprocess"] and E._build_in_subprocess._spinnet_shim
    assert R._certify is not L.INSTALLED["certify"] and R._certify._spinnet_shim
    assert not getattr(L.INSTALLED["build_in_subprocess"], "_spinnet_shim", False)
    src = __import__("inspect").getsource(L.INSTALLED["build_in_subprocess"])
    assert "su2plaq.compress.evaluate" in src and "su2plaq.spinnet.loop" not in src      # the original was not modified


def test_certify_dispatch_leaves_other_encodings_to_the_original(sp):
    L.install()
    seen = []
    orig = L.INSTALLED["certify"]
    wrapped = L._certify_dispatch(lambda circ, spec: seen.append((circ, spec.encoding)) or ({"status": "x"}, 0.0))
    tw = S.default_spec("twelve", "step")
    assert wrapped("circ", tw) == ({"status": "x"}, 0.0) and seen == [("circ", "twelve")]
    assert callable(orig)


def test_worker_copy_rejects_a_changed_laptop_function():
    def not_the_function():
        return 1

    with pytest.raises(RuntimeError, match="worker command"):
        L._worker_copy(not_the_function)


def test_need_names_the_missing_attribute():
    with pytest.raises(RuntimeError, match="no_such_attribute"):
        L._need(E, "no_such_attribute", "test")


def test_spec_orders(sp):
    assert (sp.encoding, sp.kind, sp.order, sp.alpha, sp.beta) == ("spinnet", "step", 1, 0.37, 0.61)
    assert L.spec(order=2).order == 2 and L.spec(order=2).alpha == sp.alpha
    assert sp.peak_qubit_cap() == 48


def test_code_hash_depends_on_the_spinnet_files(monkeypatch, tmp_path):
    h = L.code_hash()
    assert len(h) == 64 and h == L.code_hash()
    fake = tmp_path / "src" / "su2plaq"
    for rel in L.SPINNET_CODE_FILES:
        (fake / rel).parent.mkdir(parents=True, exist_ok=True)
        (fake / rel).write_bytes((L._SRC / rel).read_bytes())
    monkeypatch.setattr(L, "_SRC", fake)
    assert L.code_hash() == h
    (fake / L.SPINNET_CODE_FILES[0]).write_bytes(b"x")
    assert L.code_hash() != h


# ------------------------------------------------------------------------------------------------ Lean facts (4.1)
def test_structure_facts_values_come_from_the_lean_text(tmp_path):
    f = L.structure_facts()
    by = {x["name"]: x for x in f["facts"]}
    assert by["card_inner_labels"]["value"] == 47 and by["card_states_spinnet"]["value"] == 433
    assert by["couplings_2k"]["value"] == {"-4": 1, "-1": 1, "2": 6, "0": 31}
    assert by["spectrum_multiplicities"]["theorem"] == "Su2Plaq.SpinNet.eig_mult"
    assert all(x["proved_by"] == "decide" for x in f["facts"])
    assert set(f["provenance"]["lean_files"]) == {f"lean/Su2Plaq/SpinNet/{n}.lean" for n in ("Counts", "Recoupling", "Spectrum", "Semantics")}
    # a Lean file whose statement disagrees with the Python encoding is refused (nothing is typed into loop.py)
    d = tmp_path / "lean" / "Su2Plaq" / "SpinNet"
    d.mkdir(parents=True)
    for n in ("Counts", "Recoupling", "Spectrum", "Semantics"):
        txt = (ROOT / "lean" / "Su2Plaq" / "SpinNet" / f"{n}.lean").read_text()
        if n == "Counts":
            txt = txt.replace("theorem card_inner_labels : innerLabels = 47", "theorem card_inner_labels : innerLabels = 48")
        (d / f"{n}.lean").write_text(txt)
    with pytest.raises(RuntimeError, match="card_inner_labels"):
        L.structure_facts(root=tmp_path)


def test_structure_facts_refuse_native_decide(tmp_path):
    d = tmp_path / "lean" / "Su2Plaq" / "SpinNet"
    d.mkdir(parents=True)
    for n in ("Counts", "Recoupling", "Spectrum", "Semantics"):
        txt = (ROOT / "lean" / "Su2Plaq" / "SpinNet" / f"{n}.lean").read_text()
        (d / f"{n}.lean").write_text(txt + ("\ntheorem bad : 1 = 1 := by native_decide\n" if n == "Spectrum" else ""))
    with pytest.raises(RuntimeError, match="native_decide"):
        L.structure_facts(root=tmp_path)


def test_every_fact_names_a_theorem_in_its_file():
    for x in L.structure_facts()["facts"]:
        short = x["theorem"].rsplit(".", 1)[1]
        assert re.search(rf"^theorem {short}\b", (ROOT / x["file"]).read_text(), re.M), x["name"]


# ---------------------------------------------------------------------------------------------- spec text (4.1)
def test_render_spec_has_our_commands_and_facts(sp, tmp_path):
    t = L.render_spec()
    assert t == L.render_spec(sp)
    for needle in ("python -m su2plaq.spinnet.loop candidate", "python -m su2plaq.spinnet.loop oracle", "card_inner_labels",
                   "spectrum_multiplicities", "couplings_2k", "ub_exact_semantics", "433"):
        assert needle in t, needle
    assert "su2plaq.compress.run_candidate" not in t and "--encoding" not in t
    assert t.index("## Cost") < t.index("## Proved structure (Lean)") < t.index("## Tools")
    p = L.write_spec(root=tmp_path)
    assert p == tmp_path / "compress" / "specs" / "spinnet-step.md" and p.read_text() == t


def test_committed_spec_file_is_current():
    p = ROOT / "compress" / "specs" / "spinnet-step.md"
    assert p.exists() and p.read_text() == L.render_spec()


# ------------------------------------------------------------------------------------------------ programs (4.1)
def test_general_program_path_generated_once_and_angle_linear(sp, tmp_path):
    gp = L.general_program_path(sp, root=tmp_path)
    assert gp == tmp_path / "compress" / "programs" / "spinnet" / "seed" / "000-general.py"
    text = gp.read_text()
    assert text.lstrip().startswith('"""SUMMARY:') and "spec.alpha" in text and "spec.beta" in text
    gp.write_text(text + "# marker\n")
    assert L.general_program_path(sp, root=tmp_path).read_text().endswith("# marker\n")      # immutable once generated


def test_worker_cli_builds_the_general_program_in_a_subprocess(sp, tmp_path):
    gp = L.general_program_path(sp, root=tmp_path)
    specs = [sp] + [sp.with_angles(a, b) for a, b in sp.alt_angles]
    (tmp_path / "specs.json").write_text(json.dumps([s.to_dict() for s in specs]))
    out, meta = tmp_path / "out.qpy", tmp_path / "meta.json"
    env = {"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
           "MKL_NUM_THREADS": "1"}
    p = subprocess.run([sys.executable, "-m", "su2plaq.spinnet.loop", "--worker", str(gp), str(tmp_path / "specs.json"), str(out),
                        str(meta)], capture_output=True, text=True, timeout=300, env=env, cwd=str(tmp_path))
    assert p.returncode == 0, p.stderr[-800:]
    assert out.exists() and "error" not in json.loads(meta.read_text())


def test_worker_cli_usage_error():
    with pytest.raises(SystemExit):
        L.main(["--worker", "only-one-argument"])


# ------------------------------------------------------------------------------------------------------ seeds (4.2)
def test_ub_exact_semantics_fact_does_not_leak_the_reference_circuit_size():
    note = next(f["note"] for f in L.structure_facts()["facts"] if f["name"] == "ub_exact_semantics")
    assert "reference U_B circuit" in note and "48" not in note and "48-gate" not in L.render_spec()


def test_import_seed_paulo15_gauge_is_a_state_vector_with_eight_minus_inner_codes(sp):
    seed = L.import_seed(sp, "paulo15")
    g = np.asarray(seed.gauge)
    assert g.shape == (433,) and set(g.tolist()) == {-1.0, 1.0}
    assert L.gauge_minus_codes(g) == list(range(8, 16))                      # M3-P1: one -1 per bright pair, codes 8..15
    assert int((g < 0).sum()) == 128                                           # every state whose data code is in 8..15 (all outer patterns)
    assert seed.fixed_angle and not seed.can_be_parent and seed.kind == "UB" and seed.alpha is None and abs(seed.beta - 0.05) < 1e-15


def test_import_seed_reasons_and_errors(sp):
    for src in ("paulo34", "lean22", "lean22_v2"):
        assert isinstance(L.import_seed(sp, src), str)
    with pytest.raises(ValueError):
        L.import_seed(sp, "spinnet_v2:nope")
    with pytest.raises(ValueError):
        L.import_seed(sp, "unknown")
    ue = dataclasses.replace(sp, kind="UE")
    assert isinstance(L.import_seed(ue, "spinnet_v2:pairs9"), str)


@pytest.mark.parametrize("skel, cx", [("pairs9", 34), ("flags4", 44)])
def test_v2_seed_evaluates_with_alternate_angles_and_its_program_is_angle_linear(sp, skel, cx):
    seed = L.import_seed(sp, f"spinnet_v2:{skel}")
    r = L.evaluate_seed(sp, seed, "full")
    assert r.valid and r.skeleton_equal and len(r.verdicts_alt) == 2 and r.metrics["cx"] == cx
    src = L.seed_program_source(sp, f"spinnet_v2:{skel}")
    assert src.lstrip().startswith('"""SUMMARY:') and "spec.beta" in src and "spec.alpha" in src
    with pytest.raises(ValueError):
        L.seed_program_source(sp, "paulo15")


def test_evaluate_seed_paulo15_exact_tolerance_and_raw_target_rejected(sp):
    seed = L.import_seed(sp, "paulo15")
    r = L.evaluate_seed(sp, seed, "full")
    assert r.valid and r.verdict.op_norm_error <= 1e-10 and "n_minus 8" in r.message and r.metrics["cx"] == 68
    no_gauge = dataclasses.replace(seed, gauge=np.ones(433))
    assert not L.evaluate_seed(sp, no_gauge, "full").valid                      # the raw route-B target is rejected
    with pytest.raises(ValueError):
        L.evaluate_seed(sp, dataclasses.replace(seed, gauge=None), "full")


def test_linear_in_angles_recovers_the_l3_skeleton_where_the_laptop_fit_points_fail(sp):
    from su2plaq.compress import baselines as BL

    fn = lambda s: L._qiskit_l3(L._reference_circuit(s))
    with pytest.raises(ValueError):
        BL.program_source(fn, sp, summary="x")                                  # (0,0) deletes the rotations: skeleton differs
    lin = L._linear_in_angles(fn, sp)
    for a, b in ((0.37, 0.61), (0.91, 0.23), (0.7, 0.9)):
        s = sp.with_angles(a, b)
        got = [(i.operation.name, [x for x in i.operation.params]) for i in lin(s).data]
        ref = [(i.operation.name, [x for x in i.operation.params]) for i in fn(s).data]
        assert [n for n, _ in got] == [n for n, _ in ref]
        assert np.allclose([p for _, ps in got for p in ps], [p for _, ps in ref for p in ps], atol=1e-10)
    assert BL.program_source(lin, sp, summary="x").lstrip().startswith('"""SUMMARY:')


def test_linear_in_angles_refuses_a_nonlinear_angle(sp):
    from su2plaq.circuits import spinnet as C

    def fn(s):
        qc = C.build_UE(s.alpha ** 2, with_outer=True)
        return qc
    with pytest.raises(ValueError):
        L._linear_in_angles(fn, sp)


# ----------------------------------------------------------------------------------------------- rounds, briefs, CLI (4.3)
@pytest.fixture(scope="module")
def round0(tmp_path_factory):
    root = tmp_path_factory.mktemp("round0")
    info = L.seed_round(root=root, lean=False, dry_run=True)
    return root, info


def test_seed_round_writes_labels_external_rows_and_our_key(round0):
    root, info = round0
    d = json.loads((root / "results" / "compress" / "spinnet" / "round-000.json").read_text())
    assert [c["label"] for c in d["candidates"]] == [lab for lab, _ in L._SEED_FILES]
    assert info["n_valid"] == 7 and info["external"] == ["qiskit_l3_whole", "paulo15"]
    p = d["external"][1]
    assert p["beta"] == 0.05 and p["n_minus"] == 8 and p["gauge_minus_codes"] == list(range(8, 16)) and p["valid"] and p["certified"]
    assert d["spinnet"] == {"code_sha256": L.code_hash(), "shim": sorted(L.INSTALLED)}
    assert tuple(info["best_key"]) == min(tuple(c["key"]) for c in d["candidates"])


def test_seed_programs_are_immutable_once_written(round0):
    root, _ = round0
    f = root / "compress" / "programs" / "spinnet" / "seed" / "011-qiskit_l3.py"
    text = f.read_text() + "# marker\n"
    f.write_text(text)
    progs = L.seed_programs(L.spec(), root)
    assert dict(progs)["qiskit_l3"].read_text() == text


def test_briefs_name_our_commands_and_the_spec_file_is_ours(round0):
    root, _ = round0
    b = L.make_brief(2, "F3", root=root).read_text()
    assert "python -m su2plaq.spinnet.loop candidate <program.py> --trial" in b and "python -m su2plaq.spinnet.loop oracle" in b
    assert "su2plaq.compress.run_candidate" not in b and "su2plaq.compress.oracle" not in b and "structure.json" not in b
    assert "Proved structure (Lean)" in b
    ib = L.make_ideation_brief(root=root).read_text()
    assert "su2plaq.spinnet.loop oracle" in ib and "su2plaq.compress.oracle" not in ib and "compress/ideation/spinnet.md" in ib
    assert (root / "compress" / "specs" / "spinnet-step.md").read_text() == L.render_spec()


def test_brief_rewrite_refuses_a_changed_laptop_text(tmp_path):
    with pytest.raises(RuntimeError, match="laptop module shape changed"):
        L._rewrite_text("nothing to rewrite here", tmp_path, False)
    with pytest.raises(RuntimeError, match="laptop module shape changed"):
        L._rewrite_text("nothing to rewrite here", tmp_path, True)


def test_report_and_run_round_one_annotation(round0, tmp_path):
    root, _ = round0
    text = L.report_table(root=root)
    assert "paulo15" in text and (root / "results" / "compress" / "spinnet" / "summary.json").exists()
    gp = L.general_program_path(L.spec(), root=root)
    info = L.run_round(1, dry_run=True, root=root, proposals=[str(gp)], lean=False)
    assert info["round"] == 1
    d = json.loads((root / "results" / "compress" / "spinnet" / "round-001.json").read_text())
    assert d["spinnet"]["code_sha256"] == L.code_hash()


def test_certify_best_goes_through_the_laptop_with_the_shim(round0, monkeypatch):
    from su2plaq.spinnet import lean_export

    root, _ = round0
    calls = []
    monkeypatch.setattr(lean_export, "certify", lambda qc, enc, kind, a, b, order, **kw: (calls.append(kind) or
                                                                                           {"status": "not_run", "reason": "stub"}))
    out = L.certify_best(root=root)
    assert calls == ["step"] and out["lean"]["status"] == "not_run" and out["entry"].startswith("r00-seed-")


def test_cli_oracle_and_usage_errors(capsys, tmp_path):
    assert L.main(["oracle"]) == 0
    assert "target step order 1" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        L.main([])
    with pytest.raises(SystemExit):
        L.main(["no-such-command"])


def test_cli_candidate_trial_on_the_general_program(sp, tmp_path, capsys):
    gp = L.general_program_path(sp, root=tmp_path)
    assert L.main(["candidate", str(gp), "--trial"]) == 0
    assert capsys.readouterr().out.startswith("valid: ok")


def test_cli_brief_ideation_report_and_seed_dispatch(round0, capsys):
    root, _ = round0
    assert L.main(["brief", "--round", "1", "--family", "F1", "--root", str(root)]) == 0
    assert L.main(["ideation", "--root", str(root)]) == 0
    assert L.main(["report", "--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "round-001-F1.md" in out and "ideation.md" in out and "GLOBAL BEST" in out
