"""Unit tests for the fuzzy encoding (registers, codec, layout, targets, physical sample)."""
import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.encodings.fuzzy import FuzzyEncoding
from su2plaq.fuzzy import targets as tg
from su2plaq.fuzzy.gauss import gauss_residual


@pytest.fixture(scope="module")
def enc():
    return FuzzyEncoding()


def test_registers(enc):
    assert enc.registers["d"] == list(range(16)) and enc.registers["o"] == list(range(16, 48))
    assert enc.registers["link_t"] == [8, 9, 10, 11] and enc.registers["row_t"] == [11, 10]
    assert enc.registers["col_l"] == [13, 12]
    assert enc.registers["outer_7"] == [44, 45, 46, 47]


def test_codec(enc):
    assert np.array_equal(enc.inner_codes(), np.arange(65536))
    assert enc.decode(7) == 7 and enc.decode(65535) == 65535 and enc.decode(65536) is None


def test_layout_of(enc):
    qc = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"), QuantumRegister(2, "a"))
    lay = enc.layout_of(qc)
    assert lay.data == list(range(16)) and lay.outer == list(range(16, 48)) and lay.ancilla == [48, 49]
    lay2 = enc.layout_of(QuantumCircuit(QuantumRegister(20, "x")))
    assert lay2.data == list(range(16)) and lay2.outer == [] and lay2.ancilla == [16, 17, 18, 19]
    with pytest.raises(ValueError):
        enc.layout_of(QuantumCircuit(QuantumRegister(15, "x")))
    with pytest.raises(ValueError):
        enc.layout_of(QuantumCircuit(QuantumRegister(15, "d"), QuantumRegister(32, "o")))


def test_targets(enc):
    assert np.allclose(enc.target("UE", 0.37, 0.61), tg.UE_link(0.37))
    assert np.allclose(enc.target("UK", 0.37, 0.61, r=0.0), np.eye(16))
    assert np.allclose(enc.target("UEK", 0.37, 0.61, r=1.0), enc.target("UK", 0.37, 0.61) @ enc.target("UE", 0.37, 0.61))
    assert enc.target("UB", 0.37, 0.61).shape == (256, 256)
    with pytest.raises(ValueError):
        enc.target("step", 0.37, 0.61)
    with pytest.raises(ValueError):
        enc.target("nonsense", 0.37, 0.61)


def test_physical_vectors_sample(enc):
    eb = enc.physical_vectors(n_sample=3, seed=5)
    assert len(eb.codes) == 3 and eb.n_data == 16 and eb.n_outer == 32
    for c, a in zip(eb.codes, eb.amps):
        assert c.dtype == np.int64 and abs(np.linalg.norm(a) - 1) < 1e-12 and c.max() < 2 ** 48
        assert gauss_residual(c, a) < 1e-10
    again = enc.physical_vectors(n_sample=3, seed=5)
    assert all(np.array_equal(x, y) for x, y in zip(eb.codes, again.codes))


def test_describe_and_import_map(enc):
    d = enc.describe()
    assert "q_1" in d and "48" in d
    assert isinstance(enc.import_map("paulo34"), str)
    with pytest.raises(ValueError):
        enc.import_map("nonsense")
