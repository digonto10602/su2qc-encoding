"""Unit tests for su2plaq.rishon.verify and circuits.rishon.build_UE (steps 5.5-5.6): small, cheap checks."""
import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.circuits.rishon import build_UE
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.rishon import verify as V
from su2plaq.rishon.operators import inner_target


@pytest.fixture(scope="module")
def enc():
    return RishonEncoding()


def test_identity_ok_without_gauss(enc):
    qc = QuantumCircuit(QuantumRegister(16, "d"))
    v = V.verify(qc, enc, "UE", 0.0, None, gauss=False)
    assert v.ok and v.reason == "ok" and np.isnan(v.gauss_residual) and v.gauss_states == 0 and v.method == "inner_block"


def test_outer_read_and_write_reasons(enc):
    qc = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"))
    qc.cz(16, 0)
    v = V.verify(qc, enc, "UE", 0.0, None)
    assert v.reason == "outer_read_unsupported" and not v.ok and v.outer_bits_read == 1
    qc = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"))
    qc.x(20)
    assert V.verify(qc, enc, "UE", 0.0, None).reason == "writes_outer"


def test_wrong_alpha_rejected_and_gauss_counts(enc):
    v = V.verify(build_UE(0.37), enc, "UE", 0.37, None, gauss_sample=8)
    assert v.ok and v.gauss_states == 17 + 8 and v.gauss_residual <= 1e-10
    v = V.verify(build_UE(0.37), enc, "UE", 0.38, None, gauss=False)
    assert not v.ok and v.reason == "error"


def test_synth_tolerances_reexport():
    assert V.synth_tolerances(4, 1e-3) == {"tol_err": 4e-3 + 1e-9, "tol_gauss": 4e-3 + 1e-9}


def test_cross_check_detects_wrong_target(enc):
    x = V.physical_cross_check(build_UE(0.5), enc, "UE", 0.5, None, states=list(range(5)))
    assert x["max_abs_diff"] <= 1e-12 and x["n_states"] == 5
    from su2plaq.rishon.physical import closed_indices

    x = V.physical_cross_check(build_UE(0.5), enc, "UE", 1.5, None, states=closed_indices(enc.basis))   # contains the loop state
    assert x["max_abs_diff"] >= 1e-3


def test_build_UE_structure_and_options():
    qc = build_UE(0.7)
    assert qc.num_qubits == 16 and [r.name for r in qc.qregs] == ["d"]
    ops = qc.count_ops()
    assert ops["cx"] == 8 and ops["p"] == 4 and qc.metadata == {"kind": "UE", "alpha": 0.7}
    qo = build_UE(0.7, with_outer=True, include_outer_electric=True)
    assert qo.num_qubits == 48 and qo.count_ops()["cx"] == 24 and qo.count_ops()["p"] == 12
    with pytest.raises(ValueError):
        build_UE(0.7, include_outer_electric=True)


def test_build_UE_matches_diagonal_target():
    from su2plaq.evaluate import sparse_sim as ss
    from su2plaq.rishon.operators import inner_codes

    codes = inner_codes()
    b = ss.run_batch(build_UE(0.91), codes)
    M, leak = ss.encoded_block(b, codes, len(codes), (1 << 16) - 1)
    assert leak.max() <= 1e-20
    assert np.abs(M - inner_target("UE", 0.91, None)).max() <= 1e-12     # no global phase needed: p-gates are diagonal
