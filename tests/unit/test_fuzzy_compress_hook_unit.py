"""Unit tests of the M10 hook (su2plaq.fuzzy.compress_hook; plan 302): small systems, fixed seeds."""
import json
import pathlib
import subprocess
import sys

import numpy as np
import pytest

from su2plaq.fuzzy import compress_hook as H

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module", autouse=True)
def _installed():
    H.install()


def test_install_idempotent_and_registered():
    from su2plaq.compress import spec as S

    H.install()
    assert isinstance(S.get_encoding("fuzzy_ub"), H.FuzzyUBTask) and isinstance(S.get_encoding("fuzzy_link"), H.FuzzyLinkTask)
    assert S.default_spec("fuzzy_ub", "UB").peak_qubit_cap() == 40 and S.default_spec("fuzzy_link", "UE").peak_qubit_cap() == 4
    assert S.default_spec("twelve", "step").peak_qubit_cap() == 12 + 16 + 32          # twelve untouched


def test_ub_frame_constant_phase_becomes_z():
    from su2plaq.circuits import fuzzy as C

    qc = H.general_ub_fn(0.61)
    assert qc.num_qubits == 15 and not any(i.operation.name == "p" for i in qc.data)
    assert sum(1 for i in qc.data if i.operation.name == "z") >= sum(1 for i in C.build_UB(0.61).data if i.operation.name == "p")
    with pytest.raises(ValueError):
        from qiskit.circuit.library import PhaseGate

        H._replace_const_phase(PhaseGate(0.3))


def test_ub_frame_to_full_maps_row_qubits():
    from qiskit import QuantumCircuit

    q8 = QuantumCircuit(9)
    q8.cx(0, 1)
    q8.cx(7, 8)
    full = H.ub_frame_to_full(q8)
    assert full.num_qubits == 17 and [r.name for r in full.qregs] == ["d", "w"]
    got = [[full.find_bit(q).index for q in i.qubits] for i in full.data]
    assert got == [[H.ROW_QUBITS[0], H.ROW_QUBITS[1]], [H.ROW_QUBITS[7], 16]]


def test_compose_step_layers_and_counts_without_outer():
    from su2plaq.circuits import fuzzy as C
    from su2plaq.metrics.logical import logical_metrics

    for order in (1, 2):
        qc = H.compose_step(H.general_link_fn, H.general_ub_fn, 0.37, 0.61, None, order, with_outer=False)
        ref = C.build_step(0.37, 0.61, order=order, with_outer=False)
        a, b = logical_metrics(qc), logical_metrics(ref)
        assert (a["cx"], a["t_fixed"], a["n_rot"]) == (b["cx"], b["t_fixed"], b["n_rot"])
        lay = qc.metadata["layers"]
        assert lay[0][1] == 0 and lay[-1][2] == len(qc.data) and all(lay[i][2] == lay[i + 1][1] for i in range(len(lay) - 1))
        assert [k for k, *_ in lay] == (["UE", "UB"] if order == 1 else ["UE", "UB", "UE"])
        assert [r.name for r in qc.qregs] == ["d", "w"] and qc.num_qubits == 16 + 7


def test_link_unit_exact_and_ub_task_targets():
    from su2plaq.compress import oracle, spec as S
    from su2plaq.fuzzy.verify import verify_link

    spec = S.default_spec("fuzzy_link", "UE")
    v = verify_link(H.general_circuit(spec), oracle.target(spec))
    assert v.ok and v.op_norm_error <= 1e-12
    ub = S.default_spec("fuzzy_ub", "UB")
    assert oracle.target(ub).shape == (256, 256)


def test_structure_file_written():
    d = json.loads(H.write_structure().read_text())
    names = {f["name"]: f for f in d["facts"]}
    assert names["card_isolated_plaquette"]["value"] == 50 and names["card_far_end_weighted"]["value"] == 6767266914


def test_stock_worker_builds_fuzzy_programs_in_a_fresh_interpreter(tmp_path):
    """A fresh interpreter with PYTHONPATH = src only (no hook module imported, no environment variable) resolves fuzzy_ub /
    fuzzy_link through the registry, and the stock build worker builds the general programs of both units."""
    import os

    code = ("from su2plaq.compress.builder import Builder; from su2plaq.compress.spec import default_spec;"
            "import sys; assert 'su2plaq.fuzzy.compress_hook' not in sys.modules;"
            "b = Builder(default_spec('fuzzy_ub', 'UB')); print(b.reg('d'), b.n_fixed);"
            "b = Builder(default_spec('fuzzy_link', 'UE')); print(b.reg('d'), b.n_fixed)")
    env = {k: v for k, v in os.environ.items() if not k.startswith("SU2PLAQ_")}
    env["PYTHONPATH"] = str(ROOT / "src")
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=str(tmp_path))
    assert p.returncode == 0, p.stderr
    assert p.stdout.split("\n")[:2] == ["[0, 1, 2, 3, 4, 5, 6, 7] 8", "[0, 1, 2, 3] 4"]
    sh = (ROOT / "src" / "su2plaq" / "fuzzy" / "sitehook")
    assert not sh.exists()


def test_install_replaces_nothing_and_sets_no_environment():
    import os

    from su2plaq.compress import baselines as BL, brief as BR, evaluate as E, round as RD, spec as S
    from su2plaq.evaluate import evaluator as EV

    ids = lambda: [id(x) for x in (E._build_in_subprocess, RD._certify, BL.general_circuit, BL.import_seed, S.TaskSpec.render,
                                   S.TaskSpec.peak_qubit_cap, S.TaskSpec._structure_section, BR.make_brief, BR.make_ideation_brief,
                                   EV.evaluate)]
    before, env = ids(), dict(os.environ)
    H.install()
    H.install()
    assert ids() == before and dict(os.environ) == env and not any(k.startswith("SU2PLAQ_") for k in os.environ)
    assert not hasattr(H, "SITEHOOK_DIR") and not hasattr(H, "_swap_cmds")
    assert H.FuzzyUBTask.__module__ == H.FuzzyLinkTask.__module__ == "su2plaq.fuzzy.units"          # the factories live apart from the hook


def test_registry_entries_and_hashes():
    from su2plaq.compress import provenance as P
    from su2plaq.encodings import registry

    files = ["fuzzy/verify.py", "fuzzy/targets.py", "circuits/fuzzy.py", "fuzzy/units.py", "fuzzy/compress_hook.py"]
    for name, kind in H.UNITS.items():
        info = registry.info(name)
        assert list(info.evaluator_files) == files and info.kinds == (kind,) and info.loop_kind == kind
        assert info.stamp == "shared" and info.gauss_in_loop is False and info.lean_certify is None
        assert info.factory.startswith("su2plaq.fuzzy.units:") and registry.get(name).name == name
        assert P.stamp_hash(name) == P.code_hash() and P.code_hash_for(name) != P.code_hash()
        for field in ("general_circuit", "import_seed", "render_spec", "brief_note", "worker_warmup"):
            assert callable(registry.resolve(getattr(info, field))), field
    assert P.code_hash_for("fuzzy_ub") == P.code_hash_for("fuzzy_link")                    # one shared list (prompts/008 §4)


def test_hooks_general_circuit_import_seed_note_and_warm_up():
    from su2plaq.compress import baselines as BL, spec as S

    ub, link = S.default_spec("fuzzy_ub", "UB"), S.default_spec("fuzzy_link", "UE")
    assert BL.general_circuit(ub).num_qubits == 15 and BL.general_circuit(link).num_qubits == 4           # stock dispatch
    for src in ("spinnet15", "paulo34", "lean22", "lean22_v2"):
        assert BL.import_seed(link, src).endswith("not applicable to the fuzzy encoding")
    with pytest.raises(ValueError):
        BL.import_seed(link, "nope")
    assert "kappa2" in H.brief_note("fuzzy_link", "UE") and "row qubits" in H.brief_note("fuzzy_ub", "UB")
    H.warm_up()


def test_stock_certify_is_n_a_and_verdict_has_no_gauss():
    from qiskit import QuantumCircuit

    from su2plaq.compress import evaluate as E, round as RD, spec as S, baselines as BL

    d, _ = RD._certify(QuantumCircuit(4), S.default_spec("fuzzy_link", "UE"))
    assert d == H.LEAN_NA
    sp = S.default_spec("fuzzy_link", "UE")
    r = E.evaluate_circuit(BL.general_circuit(sp), sp, "trial")
    assert r.valid and np.isnan(r.verdict.gauss_residual) and r.verdict.extra["gauss"] == "not_checked" and r.verdict.span_leak == 0.0
    v = BL.verify_synthesised(BL.general_circuit(sp), sp)           # the Clifford+T re-verification also skips the Gauss check
    assert v["ok"] and np.isnan(v["verdict"].gauss_residual)


def test_rendered_specs_are_the_committed_ones():
    from su2plaq.compress import spec as S

    for name, kind in H.UNITS.items():
        assert S.default_spec(name, kind).render() == (ROOT / "compress" / "specs" / f"{name}-{kind}.md").read_text()
