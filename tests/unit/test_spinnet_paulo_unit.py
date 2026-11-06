"""Unit tests for spinnet/paulo.py and circuits/spinnet.paulo_circuit (prompts/100 step 3.2)."""
import hashlib
import re

import numpy as np
import pytest

from su2plaq.circuits.spinnet import paulo_circuit
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.spinnet import paulo


def test_constants_match_provenance():
    sources = (paulo.GATES_FILE.parents[0] / "SOURCE.md").read_text()
    m = re.search(r"spin_network_plaquette3\.gates\.txt \| \S+ \| ([0-9a-f]{64})", sources)
    assert m and m.group(1) == paulo.SHA256 == hashlib.sha256(paulo.GATES_FILE.read_bytes()).hexdigest()
    assert paulo.FILE_ALPHA_P == 0.1


def test_parse_file_counts_and_untouched_qubits():
    gates = paulo.parse_file()
    assert len(gates) == 182
    names = [g[0] for g in gates]
    assert {n: names.count(n) for n in set(names)} == {"cx": 68, "h": 34, "t": 32, "tdg": 32, "x": 12, "p": 4}
    touched = {q for _, qs, _ in gates for q in qs}
    assert touched == set(range(4)) | set(range(12, 23))
    angles = [a for n, _, a in gates if n == "p"]
    assert np.allclose(np.array(angles) / paulo.FILE_ALPHA_P, [0.25, 0.5, 1.0, -2.0], atol=1e-12)
    assert all(a is None for n, _, a in gates if n != "p")


def test_qubit_maps_agree_with_encoding_import_map():
    imp = SpinNet().import_map("paulo15")
    assert imp["qubit_map"] == paulo.QUBIT_MAP and imp["qubit_map_open"] == paulo.QUBIT_MAP_OPEN
    assert sorted(paulo.QUBIT_MAP.values()) == list(range(4)) + list(range(4, 8)) + list(range(16, 23))
    assert sorted(paulo.QUBIT_MAP_OPEN.values()) == list(range(15))


@pytest.mark.parametrize("with_outer", [False, True])
def test_load_and_paulo_circuit(with_outer):
    qc = paulo_circuit(with_outer)
    assert qc.num_qubits == (23 if with_outer else 15) and qc.global_phase == 0
    assert [r.name for r in qc.qregs] == (["d", "o", "a"] if with_outer else ["d", "a"])
    assert qc.metadata["kind"] == "UB" and qc.metadata["alpha_P"] == 0.1 and qc.metadata["sha256"] == paulo.SHA256
    assert abs(qc.metadata["beta"] - 0.05) <= 1e-15
    qmap = paulo.QUBIT_MAP if with_outer else paulo.QUBIT_MAP_OPEN
    for inst, (name, qs, ang) in zip(qc.data, paulo.parse_file()):
        assert inst.operation.name == name and tuple(qc.find_bit(q).index for q in inst.qubits) == tuple(qmap[q] for q in qs)
        if ang is not None:
            assert inst.operation.params[0] == ang


def test_tampered_file_is_rejected(monkeypatch, tmp_path):
    bad = tmp_path / "gates.txt"
    bad.write_text(paulo.GATES_FILE.read_text() + "\n")
    monkeypatch.setattr(paulo, "GATES_FILE", bad)
    with pytest.raises(ValueError, match="sha256"):
        paulo.parse_file()
