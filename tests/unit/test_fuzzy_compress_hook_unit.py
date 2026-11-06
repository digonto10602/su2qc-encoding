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


def test_sitehook_worker_builds_fuzzy_program(tmp_path):
    """A fresh interpreter with only the exported environment (the sandboxed build worker) resolves fuzzy_ub / fuzzy_link;
    without SU2PLAQ_FUZZY_HOOK the units are unknown."""
    import os

    code = ("from su2plaq.compress.builder import Builder; from su2plaq.compress.spec import default_spec;"
            "b = Builder(default_spec('fuzzy_ub', 'UB')); print(b.reg('d'), b.n_fixed);"
            "b = Builder(default_spec('fuzzy_link', 'UE')); print(b.reg('d'), b.n_fixed)")
    assert os.environ["SU2PLAQ_FUZZY_HOOK"] == "1" and str(H.SITEHOOK_DIR) in os.environ["PYTHONPATH"].split(os.pathsep)
    base = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), os.environ["PYTHONPATH"]])}
    off = {k: v for k, v in base.items() if k != "SU2PLAQ_FUZZY_HOOK"}
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=off, cwd=str(tmp_path))
    assert p.returncode != 0 and "unknown" in p.stderr
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=base, cwd=str(tmp_path))
    assert p.returncode == 0, p.stderr
    assert p.stdout.split("\n")[:2] == ["[0, 1, 2, 3, 4, 5, 6, 7] 8", "[0, 1, 2, 3] 4"]
