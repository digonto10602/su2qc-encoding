"""M9-C1 — fuzzy encoding: registers/codec, Gauss generators, physical counts by two routes, seeded physical states
(prompts/300 step 9.3; METHODS-fuzzy F1, F4). Counts are exact integers; route B (character integral) must round to them."""
import numpy as np
import pytest

from tests.acceptance.m9._fz import (SEED, api, ref_count, ref_gauss_residual, ref_isolated_plaquette_count)

FIXED_FAR_END = 101_197_218
FAR_WEIGHTED = 6_767_266_914
OUTER_VACUUM = 12_800
ISOLATED = 50


def test_M9_C1_codec_registers():
    """FuzzyEncoding: name, 16 data + 32 outer qubits, link l at 4l..4l+3 (row qubits 4l+3, 4l+2), is_basis_encoding, every
    16-bit code is a valid inner code (65536), decode is the identity, layout_of as in the twelve encoding."""
    enc = api("su2plaq.encodings.fuzzy:FuzzyEncoding")()
    assert enc.name == "fuzzy" and enc.n_data == 16 and enc.n_outer == 32 and enc.is_basis_encoding and enc.basis is None
    assert enc.registers["d"] == list(range(16)) and enc.registers["o"] == list(range(16, 48))
    for l, nm in enumerate(["link_b", "link_r", "link_t", "link_l"]):
        assert enc.registers[nm] == [4 * l, 4 * l + 1, 4 * l + 2, 4 * l + 3]
        assert enc.registers["row_" + nm[-1]] == [4 * l + 3, 4 * l + 2]
    for k in range(8):
        assert enc.registers[f"outer_{k}"] == [16 + 4 * k + i for i in range(4)]
    codes = enc.inner_codes()
    assert codes.dtype == np.int64 and len(codes) == 65536 and np.array_equal(codes, np.arange(65536))
    assert enc.decode(0) == 0 and enc.decode(0xBEEF) == 0xBEEF
    from qiskit import QuantumCircuit, QuantumRegister
    qc = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"), QuantumRegister(3, "a"))
    lay = enc.layout_of(qc)
    assert lay.data == list(range(16)) and lay.outer == list(range(16, 48)) and lay.ancilla == [48, 49, 50]
    desc = enc.describe()
    assert isinstance(desc, str) and "q_1" in desc and "48" in desc


def test_M9_C1_counts_two_routes():
    """Physical-state counts (METHODS-fuzzy F4): isolated plaquette 50; outer-vacuum sector 12 800; 12 links with the far end of
    every outer link fixed 101 197 218; far-end weighted 6 767 266 914.  Route A (corner-factorised CG rule) must give the exact
    integers (checked against this file's independent implementation); route B (Haar character integral) must agree within 1e-3
    (the integrand is a trigonometric polynomial, Gauss-Legendre with >= 40 points is exact; the float sum of <= 4e7 positive terms
    of size <= 1e5 carries a relative rounding of ~1e-12, i.e. absolute < 1e-2 — 1e-3 holds for the measured 1e-6)."""
    gz = api("su2plaq.fuzzy.gauss")
    assert gz.corner_singlet_dim(0.5, 0.5, 0.5, 0.5) == 2 and gz.corner_singlet_dim(0, 0, 0, 0) == 1
    assert gz.corner_singlet_dim(1, 0, 0.5, 0.5) == 1 and gz.corner_singlet_dim(1, 1, 1, 1) == 3 and gz.corner_singlet_dim(0.5, 0, 0, 0) == 0
    assert gz.isolated_plaquette_count() == ISOLATED == ref_isolated_plaquette_count()
    assert gz.physical_count(False) == FIXED_FAR_END == ref_count(False)
    assert gz.physical_count(True) == FAR_WEIGHTED == ref_count(True)
    assert gz.physical_count(False, outer_vacuum=True) == OUTER_VACUUM == ref_count(False, outer_vacuum=True)
    assert abs(gz.physical_count_characters(False) - FIXED_FAR_END) <= 1e-3
    assert abs(gz.physical_count_characters(True) - FAR_WEIGHTED) <= 1e-3


def test_M9_C1_seeded_physical_states_and_gauss():
    """sample_physical_states(n, seed): n distinct unit-norm 48-qubit COO states (keys < 2^48, <= max_components components) with
    Gauss residual <= 1e-10 both by the production gauss_residual and by this file's independent COO generator application
    (corner tensors come from eigh on <= 81x81, accurate to 1e-13); a seeded random non-physical state has residual > 1e-2;
    the vacuum (every link Psi = 1/2) is physical; a single flux link is not."""
    gz = api("su2plaq.fuzzy.gauss")
    states = gz.sample_physical_states(12, SEED, max_components=4096)
    assert len(states) == 12
    seen = set()
    for keys, amps in states:
        keys = np.asarray(keys, dtype=np.int64)
        amps = np.asarray(amps, dtype=complex)
        assert keys.min() >= 0 and keys.max() < 2 ** 48 and len(keys) == len(np.unique(keys)) and 1 <= len(keys) <= 4096
        assert abs(np.linalg.norm(amps) - 1) <= 1e-12
        assert gz.gauss_residual(keys, amps) <= 1e-10 and ref_gauss_residual(keys, amps) <= 1e-10
        seen.add((tuple(keys.tolist()), tuple(np.round(amps, 10).tolist())))
    assert len(seen) == 12
    # vacuum: Psi = 1/2 on every link = (|0000> + |0101> + |1010> + |1111>)/2 per link
    one = np.array([0b0000, 0b0101, 0b1010, 0b1111], dtype=np.int64)
    keys = np.zeros(1, dtype=np.int64)
    for l in range(12):
        keys = (keys[:, None] | (one[None, :] << (4 * l))).ravel()
    amps = np.full(len(keys), 2.0 ** -12, dtype=complex)
    assert gz.gauss_residual(keys, amps) <= 1e-10 and ref_gauss_residual(keys, amps) <= 1e-10
    flux = keys.copy()
    flux = (flux & ~np.int64(15)) | 0b1100          # link b: matrix unit E_{3,0}: row 3, col 0 -> not gauge invariant
    assert gz.gauss_residual(flux, amps) > 1e-2 and ref_gauss_residual(flux, amps) > 1e-2
    rng = np.random.default_rng(SEED)
    rk = np.unique(rng.integers(0, 2 ** 48, size=50, dtype=np.int64))
    ra = rng.normal(size=len(rk)) + 1j * rng.normal(size=len(rk))
    ra /= np.linalg.norm(ra)
    assert gz.gauss_residual(rk, ra) > 1e-2
    # corner_generator_apply agrees with the reference on one corner/component
    k2, a2 = gz.corner_generator_apply(0, 2, keys, amps)
    assert np.linalg.norm(np.asarray(a2)) <= 1e-10
