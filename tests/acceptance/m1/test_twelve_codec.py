"""M1-C1 — 12-qubit encoding: Eq. 31 codec, outer 2-qubit code, physical vectors (prompts/002 §2.5, METHODS §3.2)."""
import numpy as np
import pytest

import functools

from tests.acceptance._api import api


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.twelve:TwelveQubit")()


def test_M1_C1_codec_and_vectors():
    """Codec bijection on 625 inner codes (Eq. 31 table, qubit order (q_m', q_m, q_j) per link); outer code (q_m, q_j);
    433 physical vectors with unit norm (1e-12), orthogonal (1e-12), and Gauss residual <= 1e-10 after decoding to
    the electric basis in Paulo's convention."""
    enc = _enc()
    assert enc.name == "twelve" and enc.n_data == 12 and enc.n_outer == 16 and not enc.is_basis_encoding
    assert dict(enc.LINK_CODE) == {"0": 0b000, "++": 0b111, "+-": 0b110, "-+": 0b101, "--": 0b100}
    assert enc.registers["d"] == list(range(12)) and enc.registers["o"] == list(range(12, 28))
    assert enc.registers["link_b"] == [0, 1, 2] and enc.registers["link_l"] == [9, 10, 11]
    assert enc.registers["outer_0"] == [12, 13] and enc.registers["outer_7"] == [26, 27]
    codes = enc.inner_codes()
    assert codes.dtype == np.int64 and len(codes) == 625 and np.array_equal(codes, np.sort(codes)) and codes.max() < 4096
    link_codes = sorted(enc.LINK_CODE.values())
    expect = sorted(sum(c[l] << (3 * l) for l in range(4)) for c in __import__("itertools").product(link_codes, repeat=4))
    assert list(codes) == expect
    # decode: every inner code with outer register 0 maps to a distinct electric key < 625 whose link spins agree with the j bits
    keys = [enc.decode(int(c)) for c in codes]
    assert len(set(keys)) == 625 and all(0 <= k < 625 for k in keys)
    bp = api("su2plaq.exact.physical:to_convention")(enc.basis, "paulo")
    LinkSpace = api("su2plaq.su2.algebra:LinkSpace")
    ls = LinkSpace(0.5)
    for c, k in zip(codes, keys):
        for l in range(4):
            jbit = (int(c) >> (3 * l + 2)) & 1
            s = (k // 5 ** l) % 5
            assert (ls.states[s][0] == 0.5) == bool(jbit)
    assert enc.decode(0b001) is None and enc.decode(0b011 << 3) is None
    # outer code: j=0 -> 00; j=1/2 -> q_j = 1; m_near encoded in q_m; the far end is fixed
    k_vac = enc.decode(0)
    assert k_vac == 0
    k_o = enc.decode(0b11 << 12)      # outer link 0 at j = 1/2, m_near = +
    assert k_o is not None and k_o // 625 > 0 and ls.states[(k_o // 5 ** 4) % 5][0] == 0.5
    assert enc.decode(0b01 << 12) is None  # q_m = 1 with q_j = 0 is not a code
    eb = enc.physical_vectors()
    assert eb.n_data == 12 and eb.n_outer == 16 and len(eb.codes) == 433 and len(eb.amps) == 433
    norms = np.array([np.linalg.norm(a) for a in eb.amps])
    assert np.abs(norms - 1).max() <= 1e-12
    assert all(c.dtype == np.int64 and c.min() >= 0 and c.max() < 2 ** 28 for c in eb.codes)
    # orthogonality on a seeded sample of pairs
    rng = np.random.default_rng(20261104)
    for _ in range(200):
        i, k = rng.integers(0, 433, size=2)
        if i == k:
            continue
        common, ii, kk = np.intersect1d(eb.codes[i], eb.codes[k], return_indices=True)
        assert abs(np.vdot(eb.amps[i][ii], eb.amps[k][kk])) <= 1e-12
    # Gauss via decode, in Paulo's convention
    gauss_residual = api("su2plaq.exact.physical:gauss_residual")
    worst = 0.0
    for i in range(433):
        ks = np.array([enc.decode(int(c)) for c in eb.codes[i]], dtype=np.int64)
        assert all(k is not None for k in ks)
        worst = max(worst, gauss_residual(bp, ks, eb.amps[i]))
    assert worst <= 1e-10
    desc = enc.describe()
    assert isinstance(desc, str) and "111" in desc and "q_j" in desc
