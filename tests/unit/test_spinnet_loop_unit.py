"""Unit tests for su2plaq.spinnet.loop (M4 steps 4.0-4.3; prompts/104 §2): interface, facade, facts, spec text, worker, seeds, rounds, CLI."""
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


# ------------------------------------------------------------------------------------------------------- facade (prompts/008 B3)
def test_install_is_idempotent_and_replaces_nothing(sp):
    ids = lambda: {"build": id(E._build_in_subprocess), "certify": id(R._certify), "render": id(S.TaskSpec.render),
                   "get_encoding": id(S.get_encoding)}
    before = ids()
    L.install()
    L.install()
    assert L.INSTALLED == {"encoding": True} and ids() == before
    assert not getattr(E._build_in_subprocess, "_spinnet_shim", False) and not getattr(R._certify, "_spinnet_shim", False)
    assert S.get_encoding("spinnet").name == "spinnet"
    from su2plaq.encodings import registry
    from su2plaq.encodings.base import NOMINAL_ANGLES

    assert NOMINAL_ANGLES["spinnet"] == (0.37, 0.61) and registry.info("spinnet").stamp == "shared"
    assert S._ENCODINGS.get("spinnet") is None or S._ENCODINGS["spinnet"] is registry.get("spinnet")


def test_fresh_interpreter_install_leaves_the_stock_worker_in_place():
    code = ("import json\nfrom su2plaq.compress import evaluate as E, round as R\nb, c, w = id(E._build_in_subprocess), id(R._certify), id(E._worker)\n"
            "from su2plaq.spinnet import loop as L\nL.install(); L.install()\n"
            "print(json.dumps({'same': (id(E._build_in_subprocess), id(R._certify), id(E._worker)) == (b, c, w), "
            "'mark': hasattr(E._build_in_subprocess, '_spinnet_shim'), 'installed': L.INSTALLED}))")
    env = {"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin", "OMP_NUM_THREADS": "1"}
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300, env=env, cwd=str(ROOT))
    assert p.returncode == 0, p.stderr[-800:]
    assert json.loads(p.stdout.strip().splitlines()[-1]) == {"same": True, "mark": False, "installed": {"encoding": True}}


def test_shim_machinery_is_gone():
    for name in ("_worker_copy", "_certify_dispatch", "_need", "_TOOL_REWRITES", "_rewrite_text", "_finish_brief", "_SHIM_MARK"):
        assert not hasattr(L, name), name


def test_registry_entry_hooks_resolve_to_this_module():
    from su2plaq.encodings import registry

    info = registry.info("spinnet")
    assert set(L.SPINNET_CODE_FILES) <= set(info.evaluator_files)
    for field in ("general_circuit", "seed_candidates", "import_seed", "lean_certify", "render_spec"):
        dotted = getattr(info, field)
        assert dotted.startswith("su2plaq.spinnet.loop:") and callable(registry.resolve(dotted)), field
    assert info.tools == ("python -m su2plaq.spinnet.loop candidate", "python -m su2plaq.spinnet.loop oracle")
    assert info.structure_json == "compress/specs/spinnet-structure.json" and info.worker_warmup is None and info.verdict is None


def test_general_circuit_hook_is_the_reference_circuit(sp):
    assert L.general_circuit is L._reference_circuit
    from su2plaq.compress import baselines as BL

    assert BL.general_circuit(sp).num_qubits == L.general_circuit(sp).num_qubits > 16      # registry dispatch, not the twelve circuit


def test_lean_certify_hook_is_dispatched_by_the_shared_round(sp, monkeypatch):
    from su2plaq.lean.certify import LeanCert
    from su2plaq.spinnet import lean_export

    seen = {}

    def fake(circ, enc, kind, alpha, beta, order, timeout=0):
        seen.update(kind=kind, alpha=alpha, beta=beta, order=order, timeout=timeout, enc=enc.name)
        return {"status": "certified", "cert_path": None, "seconds": 0.5, "checker_sha256": "c" * 64, "axioms": ["propext"]}

    monkeypatch.setattr(lean_export, "certify", fake)
    cert = L.lean_certify("circ", sp, timeout=7.0, extra_provenance={"x": 1})
    assert isinstance(cert, LeanCert) and cert.status == "certified" and cert.axioms == ["propext"] and cert.checker_sha256 == "c" * 64
    assert seen == {"kind": "step", "alpha": 0.37, "beta": 0.61, "order": 1, "timeout": 7.0, "enc": "spinnet"}
    d, _sec = R._certify("circ", sp, program_file_sha256="f" * 64)
    assert d["status"] == "certified" and d["program_file_sha256"] == "f" * 64 and seen["timeout"] == 1200.0


def test_seed_candidates_hook_lists_the_seven_programs(sp, tmp_path):
    cands = L.seed_candidates(sp, tmp_path)
    assert [c[0] for c in cands] == [lab for lab, _ in L._SEED_FILES] and all(c[2] is None and c[1].exists() for c in cands)


def test_stock_round_zero_import_seed_answers_with_reasons(sp):
    from su2plaq.compress import baselines as BL

    for src in ("paulo34", "spinnet15", "lean22", "lean22_v2"):
        assert isinstance(BL.import_seed(sp, src), str), src


def test_write_structure_is_idempotent(tmp_path):
    p = L.write_structure(root=tmp_path)
    assert p == tmp_path / "compress" / "specs" / "spinnet-structure.json"
    before = p.stat().st_mtime_ns
    assert L.write_structure(root=tmp_path) == p and p.stat().st_mtime_ns == before
    assert json.loads(p.read_text())["facts"][0]["name"] == "card_inner_labels"


def test_committed_structure_file_is_current():
    p = ROOT / "compress" / "specs" / "spinnet-structure.json"
    assert p.exists() and json.loads(p.read_text()) == json.loads(json.dumps(L.structure_facts()))


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
    assert "su2plaq.compress.run_candidate" not in t and "--encoding" not in t and t == sp.render()
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


def test_worker_cli_alias_builds_the_general_program_in_a_subprocess(sp, tmp_path):
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
    assert d["spinnet"] == {"code_sha256": L.code_hash(), "shim": ["encoding"]}
    assert tuple(info["best_key"]) == min(tuple(c["key"]) for c in d["candidates"])


def test_seed_programs_are_immutable_once_written(round0):
    root, _ = round0
    f = root / "compress" / "programs" / "spinnet" / "seed" / "011-qiskit_l3.py"
    original = f.read_text()
    text = original + "# marker\n"
    f.write_text(text)
    try:
        progs = L.seed_programs(L.spec(), root)
        assert dict(progs)["qiskit_l3"].read_text() == text
    finally:
        f.write_text(original)               # the module-scoped archive must keep matching its program hashes (headline checks them)


def test_briefs_name_our_commands_and_the_spec_file_is_ours(round0):
    root, _ = round0
    b = L.make_brief(2, "F3", root=root).read_text()
    assert "python -m su2plaq.spinnet.loop candidate <program.py> --encoding spinnet --kind step --trial" in b
    assert "python -m su2plaq.spinnet.loop oracle" in b
    assert "su2plaq.compress.run_candidate" not in b and "su2plaq.compress.oracle" not in b
    assert "`compress/specs/spinnet-structure.json`" in b and "compress/lean/structure.json" not in b
    assert "Proved structure (Lean)" in b
    ib = L.make_ideation_brief(root=root).read_text()
    assert "su2plaq.spinnet.loop oracle" in ib and "su2plaq.compress.oracle" not in ib and "compress/ideation/spinnet.md" in ib
    assert (root / "compress" / "specs" / "spinnet-step.md").read_text() == L.render_spec()
    assert (root / "compress" / "specs" / "spinnet-structure.json").exists()


def test_report_and_run_round_one_annotation(round0, tmp_path):
    root, _ = round0
    text = L.report_table(root=root)
    assert "paulo15" in text and (root / "results" / "compress" / "spinnet" / "summary.json").exists()
    gp = L.general_program_path(L.spec(), root=root)
    info = L.run_round(1, dry_run=True, root=root, proposals=[str(gp)], lean=False)
    assert info["round"] == 1
    d = json.loads((root / "results" / "compress" / "spinnet" / "round-001.json").read_text())
    assert d["spinnet"]["code_sha256"] == L.code_hash()


def test_certify_best_goes_through_the_shared_round_and_the_registry_hook(round0, monkeypatch):
    from su2plaq.spinnet import lean_export

    root, _ = round0
    calls = []
    monkeypatch.setattr(lean_export, "certify", lambda qc, enc, kind, a, b, order, **kw: (calls.append(kind) or
                                                                                           {"status": "not_run", "reason": "stub"}))
    best = L.headline(root=root)["archive_best"]
    monkeypatch.setattr(L, "headline", lambda root=None, refresh=False: {"id": best})     # headline == archive best: certified once
    out = L.certify_best(root=root)
    assert calls == ["step"] and out["lean"]["status"] == "not_run" and out["entry"].startswith("r00-seed-")
    assert out["headline"] == {"entry": best, "same_as_archive_best": True}


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


# ------------------------------------------------------------------------------------------------- headline rule (4.3b, E3)
def test_angle_set_is_the_locked_seeded_set():
    rng = np.random.default_rng(20261107)
    a, b = rng.uniform(0.05, 2.0, 20), rng.uniform(0.05, 1.2, 20)
    assert (L.ANGLE_SET_SEED, L.ANGLE_SET_N, L.ANGLE_SET_RANGES) == (20261107, 20, ((0.05, 2.0), (0.05, 1.2)))
    assert len(L.ANGLE_SET) == 20 and np.array_equal(np.asarray(L.ANGLE_SET), np.c_[a, b])
    assert all(isinstance(x, float) for pair in L.ANGLE_SET for x in pair)
    assert len(L.angle_set_sha256()) == 64 and L.angle_set_sha256() == L.angle_set_sha256()


def test_spec_carries_the_headline_rule_before_the_tools_section(sp):
    text = L.render_spec(sp)
    assert text.count("## Headline rule (track S)") == 1
    assert text.index("## Proved structure (Lean)") < text.index("## Headline rule (track S)") < text.index("## Tools")
    assert "will not count" in text and "multiples of pi/2" in text


def test_round_brief_points_to_the_spec_that_carries_the_headline_rule(round0):
    root, _ = round0
    b = L.make_brief(3, "F2", root=root).read_text()
    assert "compress/specs/spinnet-step.md" in b and "## Output" in b
    spec_text = (root / "compress" / "specs" / "spinnet-step.md").read_text()
    assert spec_text.count("## Headline rule (track S)") == 1 and spec_text == L.render_spec()


def _fake_archive(monkeypatch, tmp_path, specs):
    """specs: (id, laptop key, robust key or None, lean status or None).  Programs are tiny files; robust_metrics is stubbed."""
    import hashlib
    from types import SimpleNamespace

    from su2plaq.compress import archive as A

    entries, table = [], {}
    for i, (eid, key, rkey, lean) in enumerate(specs):
        f = tmp_path / "compress" / "programs" / "spinnet" / "F1" / f"{i:03d}-x.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# {eid}\n")
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        entries.append(SimpleNamespace(id=eid, program_path=str(f.relative_to(tmp_path)), program_sha256=sha, valid=True, key=key,
                                       family="F1", round=1, lean=None if lean is None else {"status": lean}))
        table[f.name] = {"program_sha256": sha, "angle_set_sha256": L.angle_set_sha256(), "skeleton_equal": rkey is not None,
                         "t_eps": [rkey[1] // 20] * 20 if rkey else [0] * 20, "depth_ct": [rkey[3] // 20] * 20 if rkey else [0] * 20,
                         "t_sum": rkey[1] if rkey else 0, "depth_sum": rkey[3] if rkey else 0, "t_mean": rkey[1] / 20 if rkey else 0.0,
                         "cx": key[0], "qubits": key[3], "angle_linear": bool(rkey) and rkey[2] == 0, "export_status": "ok",
                         "robust_key": rkey}
    best = min(entries, key=lambda e: (tuple(e.key), e.id))
    monkeypatch.setattr(A.Archive, "load", classmethod(lambda cls, *a, **k: SimpleNamespace(entries=lambda: list(entries), best=lambda: best)))
    calls = []

    def stub(path, sp=None, root=None):
        calls.append(pathlib.Path(path).name)
        return dict(table[pathlib.Path(path).name])

    monkeypatch.setattr(L, "robust_metrics", stub)
    return calls


def test_headline_picks_the_smallest_robust_key_not_the_laptop_best(tmp_path, monkeypatch):
    calls = _fake_archive(monkeypatch, tmp_path, [
        ("r03-F1-003", (31, 1062, 2189, 17), (31, 21840, 1, 46141, 17), "n_a"),       # laptop best, tied in sum T, not angle-linear
        ("r02-F1-002", (31, 1086, 2258, 17), (31, 21840, 0, 46024, 17), "certified"),  # angle-linear: wins the tie
        ("r01-F1-001", (32, 832, 1583, 18), (32, 16948, 0, 33256, 18), "certified"),
        ("r04-F1-001", (30, 900, 2000, 17), None, None)])                              # skeleton changes in the set: never headline
    h = L.headline(root=tmp_path)
    assert h["id"] == "r02-F1-002" and h["archive_best"] == "r04-F1-001" and h["lean"] == "certified"
    assert [r["id"] for r in h["ranking"]] == ["r02-F1-002", "r03-F1-003", "r01-F1-001"] and h["unrankable"] == ["r04-F1-001"]
    assert h["archive_best_robust_key"] is None and tuple(h["robust_key"]) == (31, 21840, 0, 46024, 17)
    cache = json.loads((tmp_path / "results" / "compress" / "spinnet" / "robust.json").read_text())
    assert set(cache["entries"]) == {r["id"] for r in h["ranking"]} | {"r04-F1-001"} and cache["angle_set"]["seed"] == 20261107
    assert len(cache["angle_set"]["pairs"]) == 20 and len(calls) == 4
    L.headline(root=tmp_path)                                  # second call: everything from the cache
    assert len(calls) == 4
    L.headline(root=tmp_path, refresh=True)
    assert len(calls) == 8


def test_headline_full_tie_falls_back_to_the_laptop_key_then_the_id(tmp_path, monkeypatch):
    _fake_archive(monkeypatch, tmp_path, [("r02-F1-002", (31, 1086, 2258, 17), (31, 100, 0, 200, 17), None),
                                          ("r02-F1-003", (31, 1062, 2189, 17), (31, 100, 0, 200, 17), None),
                                          ("r02-F1-001", (31, 1062, 2189, 17), (31, 100, 0, 200, 17), None)])
    assert [r["id"] for r in L.headline(root=tmp_path)["ranking"]] == ["r02-F1-001", "r02-F1-003", "r02-F1-002"]


def test_headline_cache_is_invalidated_by_a_changed_angle_set_hash(tmp_path, monkeypatch):
    calls = _fake_archive(monkeypatch, tmp_path, [("r01-F1-001", (32, 832, 1583, 18), (32, 16948, 0, 33256, 18), None)])
    L.headline(root=tmp_path)
    f = tmp_path / "results" / "compress" / "spinnet" / "robust.json"
    d = json.loads(f.read_text())
    d["angle_set"]["sha256"] = "0" * 64
    f.write_text(json.dumps(d))
    L.headline(root=tmp_path)
    assert len(calls) == 2


def test_certify_best_also_certifies_a_different_headline(round0, monkeypatch):
    from su2plaq.compress import archive as A
    from su2plaq.spinnet import lean_export

    root, _ = round0
    calls = []
    monkeypatch.setattr(lean_export, "certify", lambda qc, enc, kind, a, b, order, **kw: (calls.append(qc.num_qubits) or
                                                                                           {"status": "n_a", "reason": "stub"}))
    arch = A.Archive.load("spinnet", root=root, n_alt=len(L.spec().alt_angles), strict=True)
    other = next(e.id for e in arch.entries() if e.valid and e.id != arch.best().id)
    monkeypatch.setattr(L, "headline", lambda root=None, refresh=False: {"id": other})
    out = L.certify_best(root=root)
    assert len(calls) == 2 and out["headline"]["entry"] == other and out["headline"]["lean"]["status"] == "n_a"
    assert A.Archive.load("spinnet", root=root, n_alt=len(L.spec().alt_angles), strict=True).entries()


def test_real_spinnet_certificate_goes_through_the_shared_certify():
    """The spin-network exporter writes the gate-list hash as `program_sha256` (no `gates_sha256`): the shared `round._certify`
    must still return the entry's lean dict with exactly the fields of the existing spinnet archive entries (plus
    `program_file_sha256`).  Uses the compiled checker (about 3 s); rewrites the tracked certificate byproducts."""
    import hashlib

    from su2plaq.compress import baselines as BL

    sp = L.spec()
    src = ROOT / "compress" / "programs" / "spinnet" / "seed" / "000-general.py"
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    d, _ = R._certify(BL.general_circuit(sp), sp, program_file_sha256=sha)
    assert d["status"] == "certified" and d["program_file_sha256"] == sha, d
    old = json.loads((ROOT / "compress" / "archive" / "spinnet" / "entries" / "r00-seed-000.json").read_text())["lean"]
    assert set(d) == set(old) | {"program_file_sha256"}, (sorted(d), sorted(old))
    assert d["checker_sha256"] == old["checker_sha256"] and d["axioms"] == old["axioms"] and d["theorem_path"] is None
    assert "gates_sha256" not in d


def test_certify_records_gates_sha256_when_the_certificate_names_it(tmp_path, monkeypatch):
    """Exporters that write `gates_sha256` (twelve-qubit, LSH) keep it in the dict; an exporter without it adds no field."""
    from su2plaq.encodings import registry

    cert = tmp_path / "c.json"
    for body, expect in (({"gates_sha256": "g" * 64}, "g" * 64), ({"program_sha256": "p" * 64}, None)):
        cert.write_text(json.dumps(body))
        monkeypatch.setattr(registry, "resolve", lambda dotted, c=str(cert): (lambda circ, spec, **kw: {"status": "certified", "cert_path": c}))
        d, _ = R._certify("circ", L.spec())
        assert d.get("gates_sha256") == expect and ("gates_sha256" in d) == (expect is not None)
