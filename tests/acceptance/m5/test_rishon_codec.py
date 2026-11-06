"""M5-C1 (encoding) — RishonEncoding: registers, codec, physical vectors, inner view, restricted target
(prompts/200 §2.4; METHODS-rishon R2-R3)."""
import functools

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from tests.acceptance._api import api
from tests.acceptance.m5 import _ref


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.rishon:RishonEncoding")()


def test_M5_C1_encoding_codec_and_vectors():
    """name/sizes/registers; inner_codes = the 1296 two-rishon codes; decode gives the 12 link types for valid 48-bit codes
    and None for invalid ones (wrong weight, far end not fixed); physical_vectors('all') = 38 432 unit vectors with valid
    codes, 'closed' = 17, 'sample' = 17 + 256; the inner view exposes the 1296 codes as single-code states; the target
    restricted to the closed states equals the inner target on the closed codes (the outer register is a spectator)."""
    enc = _enc()
    assert enc.name == "rishon" and enc.n_data == 16 and enc.n_outer == 32 and not enc.is_basis_encoding
    assert enc.registers["d"] == list(range(16)) and enc.registers["o"] == list(range(16, 48))
    assert enc.registers["link_b"] == [0, 1, 2, 3] and enc.registers["link_l"] == [12, 13, 14, 15]
    assert enc.registers["outer_0"] == [16, 17, 18, 19] and enc.registers["outer_7"] == [44, 45, 46, 47]
    assert api("su2plaq.encodings.rishon:RISHON_NOMINAL") == (0.37, 0.61)
    codes = enc.inner_codes()
    assert codes.dtype == np.int64 and np.array_equal(codes, _ref.inner_codes())
    outer = _ref.outer_near_empty_code()
    va, vb = _ref.vac_codes()
    assert enc.decode(va | outer) is not None and enc.decode(va | outer)[:4] == ("A", "A", "B", "B")
    assert enc.decode(vb | outer)[:4] == ("B", "B", "A", "A")
    assert enc.decode(va | outer | (1 << 0)) is None                        # link b weight 3
    assert enc.decode((va & ~0xF) | 0b0001 | outer) is None                  # weight 1
    # outer Q link with far colour 2 is invalid; with far colour 1 valid
    k0 = 4 * 4
    near_is_L = _ref.NEAR[4] == "L"
    good = (va | outer) & ~(0xF << k0)
    good |= ((0b01 << 0) | (0b01 << 2)) << k0                              # near colour 1 (bit 0 of its pair), far colour 1
    assert enc.decode(good) is not None and enc.decode(good)[4] == "Q"
    bad = (va | outer) & ~(0xF << k0)
    bad |= (((0b01 << 0) | (0b10 << 2)) if near_is_L else ((0b10 << 0) | (0b01 << 2))) << k0   # far colour 2
    assert enc.decode(bad) is None
    keys, amps = enc.decode_state(np.array([va | outer, vb | outer], dtype=np.int64), np.array([1.0, 0.5]))
    assert np.array_equal(keys, [va | outer, vb | outer]) and np.allclose(amps, [1.0, 0.5])
    with pytest.raises(ValueError):
        enc.decode_state(np.array([va | outer | 1], dtype=np.int64), np.array([1.0]))
    eb = enc.physical_vectors("all")
    assert eb.n_data == 16 and eb.n_outer == 32 and len(eb.codes) == _ref.N_PHYS
    norms = np.array([np.linalg.norm(a) for a in eb.amps])
    assert np.abs(norms - 1).max() <= 1e-12
    rng = np.random.default_rng(20261104)
    for k in rng.integers(0, _ref.N_PHYS, size=200):
        assert eb.codes[k].dtype == np.int64 and all(enc.decode(int(c)) is not None for c in eb.codes[k])
    cl = enc.physical_vectors("closed")
    assert len(cl.codes) == 17 and cl.codes[0].tolist() == [va | outer] and cl.codes[1].tolist() == [vb | outer]
    sm = enc.physical_vectors("sample", n_sample=256, seed=20261104)
    assert len(sm.codes) == 17 + 256
    sm2 = enc.physical_vectors("sample", n_sample=256, seed=20261104)
    assert all(np.array_equal(a, b) for a, b in zip(sm.codes, sm2.codes))
    # inner view
    iv = enc.inner_view()
    assert iv.n_data == 16 and iv.n_outer == 32 and iv.is_basis_encoding and np.array_equal(iv.inner_codes(), codes)
    ivb = iv.physical_vectors()
    assert len(ivb.codes) == 1296 and all(len(c) == 1 and c[0] == codes[i] and abs(a[0] - 1) <= 1e-15 for i, (c, a) in enumerate(zip(ivb.codes, ivb.amps)))
    qc = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"), QuantumRegister(3, "anc"))
    for e in (enc, iv):
        lay = e.layout_of(qc)
        assert lay.data == list(range(16)) and lay.outer == list(range(16, 48)) and lay.ancilla == [48, 49, 50]
    lay = enc.layout_of(QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(2, "a")))
    assert lay.outer == [] and lay.ancilla == [16, 17]
    # restricted target on the closed states = inner target on the closed codes
    O = api("su2plaq.rishon.operators")
    P = api("su2plaq.rishon.physical")
    basis = enc.basis
    closed = P.closed_indices(basis)
    Vc = enc.target("step", 0.37, 0.61, order=1, states=closed)
    assert Vc.shape == (17, 17) and np.abs(Vc.conj().T @ Vc - np.eye(17)).max() <= 1e-10
    Vin = O.inner_target("step", 0.37, 0.61, 1)
    pos = {int(c): i for i, c in enumerate(codes)}
    B = np.zeros((17, 1296), complex)
    for r, k in enumerate(closed):
        for c, a in zip(basis.keys[k], basis.amps[k]):
            B[r, pos[int(c) & 0xFFFF]] = a
    assert np.abs(B.conj() @ Vin @ B.T - Vc).max() <= 1e-10
    with pytest.raises(ValueError):
        enc.target("step", 0.37, 0.61)
    assert np.abs(enc.inner_target("UB", None, 0.61) - O.inner_target("UB", None, 0.61)).max() <= 1e-14
    desc = enc.describe()
    assert isinstance(desc, str) and "1100" in desc and "0011" in desc and "38432" in desc
    assert isinstance(enc.import_map("paulo34"), str) and isinstance(enc.import_map("spinnet15"), str)
