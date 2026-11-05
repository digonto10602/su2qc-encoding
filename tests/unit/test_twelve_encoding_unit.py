"""Unit tests for TwelveQubit.describe and import_map (step 1.1)."""
import pytest

from su2plaq.encodings.twelve import TwelveQubit


@pytest.fixture(scope="module")
def enc():
    return TwelveQubit()


def test_describe_contains_codec_and_register_facts(enc):
    d = enc.describe()
    for token in ("111", "110", "101", "100", "000", "q_j", "q_m'", "625", "433", "outer", "o7", "`b`", "`l`"):
        assert token in d, token
    assert d == enc.describe()   # deterministic


def test_import_map_sources(enc):
    p = enc.import_map("paulo34")
    assert p["fixed_angle"] and p["kind"] == "UB" and len(p["qubit_map"]) == 34
    assert p["qubit_map"][:12] == list(range(12)) and p["qubit_map"][12:] == list(range(28, 50))
    assert p["angles"](0.37, 0.61) == {"kind": "UB", "beta": 1.0, "alpha_P": 2.0} == p["angles"](1.0, 2.0)
    for src, n in (("lean22", 22), ("lean22_v2", 19)):
        m = enc.import_map(src)
        assert not m["fixed_angle"] and len(m["qubit_map"]) == n == m["n_source_qubits"]
        assert len(set(m["qubit_map"])) == n and m["qubit_map"][:12] == list(range(12))
        a = m["angles"](0.37, 0.61)
        assert a["alpha_P"] == pytest.approx(1.22) and a["electric_p"] == pytest.approx(-0.75 * 0.37)
    r = enc.import_map("spinnet15")
    assert isinstance(r, str) and "spin-network" in r
    with pytest.raises(ValueError):
        enc.import_map("nonsense")
