"""Unit tests for su2plaq.spinnet.loop (M4 steps 4.0 / 4.1; prompts/104 §2): interface stubs, shim, facts, spec text, worker."""
import dataclasses
import json
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


@pytest.mark.parametrize("call", [
    lambda sp: L.import_seed(sp, "paulo15"),
    lambda sp: L.seed_program_source(sp, "spinnet_v2:pairs9"),
    lambda sp: L.evaluate_seed(sp, None),
    lambda sp: L.seed_round(dry_run=True),
    lambda sp: L.run_round(1, dry_run=True),
    lambda sp: L.make_ideation_brief(),
    lambda sp: L.make_brief(1, "F1"),
    lambda sp: L.report_table(),
    lambda sp: L.certify_best(),
    lambda sp: L.main(["seed"]),
])
def test_later_steps_are_stubs_that_raise_not_implemented(sp, call):
    with pytest.raises(NotImplementedError):
        call(sp)


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
