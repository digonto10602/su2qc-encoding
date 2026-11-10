"""Unit tests for su2plaq.encodings.rishon (step 5.4): codec, vectors, inner view, restricted target.
No expected totals are hard-coded: sizes are compared with the basis and with the operator module."""
import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.encodings.rishon import RISHON_NOMINAL, RishonEncoding, RishonInnerView
from su2plaq.rishon import operators as O
from su2plaq.rishon import physical as P


@pytest.fixture(scope="module")
def enc():
    return RishonEncoding()


def test_registers_and_attributes(enc):
    assert RISHON_NOMINAL == (0.37, 0.61)
    assert (enc.name, enc.n_data, enc.n_outer, enc.is_basis_encoding) == ("rishon", 16, 32, False)
    assert enc.registers["d"] + enc.registers["o"] == list(range(48))
    assert enc.registers["link_t"] == [8, 9, 10, 11] and enc.registers["outer_3"] == [28, 29, 30, 31]
    assert np.array_equal(enc.inner_codes(), O.inner_codes())


def test_inner_codec_bijection(enc):
    """With a valid outer part, exactly the 1296 inner codes decode; the types are those of the link nibbles."""
    codes = enc.inner_codes()
    outer = _near_empty_outer()
    assert len(set(codes.tolist())) == len(codes)
    for c in codes:
        t = enc.decode(int(c) | outer)
        assert t is not None and len(t) == 12
        for l in range(4):
            nib = (int(c) >> (4 * l)) & 15
            assert t[l] == {3: "A", 12: "B"}.get(nib, "Q")
    valid16 = {int(c) for c in codes}
    rng = np.random.default_rng(1)
    for c in rng.integers(0, 1 << 16, size=2000):
        assert (enc.decode(int(c) | outer) is not None) == (int(c) in valid16)


def _near_empty_outer() -> int:
    b = P.rishon_basis()
    k = P.closed_indices(b)[0]
    return int(b.keys[k][0]) & ~0xFFFF


def test_decode_rejects_invalid(enc):
    outer = _near_empty_outer()
    va = O.closed_codes()[0]
    assert enc.decode(va | outer) is not None
    assert enc.decode(-1) is None and enc.decode(1 << 48) is None
    assert enc.decode(va | outer | (1 << 2)) is None            # link b weight 3
    assert enc.decode(((va & ~0xF) | 1) | outer) is None        # weight 1
    D = P._diagram()
    l = D.outer_links()[0]
    sh = 4 * l
    flipped = (va | outer) ^ (0b1100 << sh) ^ (0b0011 << sh)      # swap near/far full<->empty: far end no longer fixed
    assert enc.decode(flipped) is None or enc.decode(flipped)[l] in ("A", "B")


def test_decode_state(enc):
    outer = _near_empty_outer()
    va, vb, _ = O.closed_codes()
    keys, amps = enc.decode_state(np.array([va | outer, vb | outer]), np.array([1.0, 0.5]))
    assert np.array_equal(keys, [va | outer, vb | outer]) and np.allclose(amps, [1.0, 0.5])
    with pytest.raises(ValueError):
        enc.decode_state(np.array([va | outer | (1 << 2)]), np.array([1.0]))


def test_all_basis_states_decode(enc):
    b = enc.basis
    ti = enc._type_indices(np.concatenate([k[:50] for k in b.keys[::97]]))
    assert np.all(ti >= 0)
    # the decoded types equal the label's types
    for k in range(0, b.dim, 997):
        assert enc.decode(int(b.keys[k][0])) == b.labels[k][0]


def test_physical_vectors_variants(enc):
    allv = enc.physical_vectors("all")
    assert len(allv.codes) == enc.basis.dim and allv.n_data == 16 and allv.n_outer == 32
    cl = enc.physical_vectors("closed")
    assert len(cl.codes) == len(P.closed_indices(enc.basis))
    sm = enc.physical_vectors("sample", n_sample=10, seed=3)
    sm2 = enc.physical_vectors("sample", n_sample=10, seed=3)
    assert len(sm.codes) == len(cl.codes) + 10
    assert all(np.array_equal(a, b) for a, b in zip(sm.codes, sm2.codes))
    assert all(a.dtype == np.complex128 for a in sm.amps)
    assert np.allclose([np.linalg.norm(a) for a in sm.amps], 1.0, atol=1e-12)
    with pytest.raises(ValueError):
        enc.physical_vectors("nope")


def test_inner_view(enc):
    iv = enc.inner_view()
    assert isinstance(iv, RishonInnerView) and iv.is_basis_encoding and iv.registers == enc.registers
    eb = iv.physical_vectors()
    codes = iv.inner_codes()
    assert len(eb.codes) == len(codes)
    assert all(c.dtype == np.int64 and len(c) == 1 and c[0] == codes[i] for i, c in enumerate(eb.codes))
    assert all(np.array_equal(a, [1.0]) for a in eb.amps)
    k, a = iv.decode_state(codes[:3], np.ones(3))
    assert np.array_equal(k, codes[:3])


def test_layout(enc):
    qc = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"), QuantumRegister(2, "anc"))
    for e in (enc, enc.inner_view()):
        lay = e.layout_of(qc)
        assert lay.data == list(range(16)) and lay.outer == list(range(16, 48)) and lay.ancilla == [48, 49]
    lay = enc.layout_of(QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(1, "a")))
    assert lay.outer == [] and lay.ancilla == [16]
    with pytest.raises(ValueError):
        enc.layout_of(QuantumCircuit(QuantumRegister(15, "d")))
    with pytest.raises(ValueError):
        enc.layout_of(QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(3, "o")))


def test_target_restricted_matches_dense_embedding(enc):
    """<Psi_k'|V (x) 1|Psi_k> on a sample that includes states with several outer patterns, versus an explicit
    dictionary computation."""
    b = enc.basis
    states = P.closed_indices(b)[:3] + P.sample_indices(b, n=6, seed=11)
    V = enc.inner_target("step", 0.37, 0.61, 1)
    codes = O.inner_codes()
    ref = np.zeros((len(states), len(states)), dtype=complex)
    for i, ki in enumerate(states):
        for j, kj in enumerate(states):
            tot = 0j
            outs = {}
            for key, amp in zip(b.keys[kj], b.amps[kj]):
                outs.setdefault(int(key) >> 16, []).append((int(np.searchsorted(codes, int(key) & 0xFFFF)), amp))
            outs_i = {}
            for key, amp in zip(b.keys[ki], b.amps[ki]):
                outs_i.setdefault(int(key) >> 16, []).append((int(np.searchsorted(codes, int(key) & 0xFFFF)), amp))
            for o, lst in outs_i.items():
                for r, a in lst:
                    for c, a2 in outs.get(o, []):
                        tot += np.conj(a) * V[r, c] * a2
            ref[i, j] = tot
    got = enc.target("step", 0.37, 0.61, 1, states=states)
    assert np.abs(got - ref).max() <= 1e-12
    # the restricted target is a compression of a unitary: norm <= 1
    assert np.linalg.norm(got, 2) <= 1 + 1e-10


def test_target_closed_unitary_and_errors(enc):
    cl = P.closed_indices(enc.basis)
    Vc = enc.target("UB", None, 0.61, states=cl)
    assert np.abs(Vc.conj().T @ Vc - np.eye(len(cl))).max() <= 1e-10
    with pytest.raises(ValueError):
        enc.target("UB", None, 0.61)
    assert np.array_equal(enc.inner_target("UE", 0.4, None), O.inner_target("UE", 0.4, None))


def test_describe_and_import_map(enc):
    d = enc.describe()
    assert "1100" in d and "0011" in d and "38432" in d
    for s in ("paulo34", "lean22", "lean22_v2", "spinnet15"):
        assert isinstance(enc.import_map(s), str)
    with pytest.raises(ValueError):
        enc.import_map("nope")


def test_no_compress_import():
    import os
    import pathlib
    import subprocess
    import sys

    import su2plaq

    code = ("import sys; import su2plaq.encodings.rishon, su2plaq.rishon.operators; "
            "assert not any(m.startswith('su2plaq.compress') for m in sys.modules)")
    env = dict(os.environ, PYTHONPATH=str(pathlib.Path(su2plaq.__file__).resolve().parent.parent))
    subprocess.run([sys.executable, "-c", code], check=True, env=env)
