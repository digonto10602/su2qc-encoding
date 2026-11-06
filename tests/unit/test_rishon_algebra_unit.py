"""Unit tests for su2plaq.rishon.algebra (step 5.1): small, deterministic."""
import itertools

import numpy as np
import pytest

from su2plaq.rishon import algebra as A


def test_jw_car_two_and_four_modes():
    for n in (2, 4):
        c = [A.jw_annihilation(k, n) for k in range(n)]
        for k, l in itertools.product(range(n), repeat=2):
            ac = c[k] @ c[l].conj().T + c[l].conj().T @ c[k]
            assert np.abs(ac - (np.eye(2 ** n) if k == l else 0)).max() < 1e-14
            assert np.abs(c[k] @ c[l] + c[l] @ c[k]).max() < 1e-14
    with pytest.raises(ValueError):
        A.jw_annihilation(4, 4)


def test_link_sector_types_and_casimirs():
    lk = A.RishonLink()
    assert lk.sector.tolist() == [3, 5, 6, 9, 10, 12]
    assert [lk.link_type(int(s)) for s in lk.sector] == ["A", "Q", "Q", "Q", "Q", "B"]
    assert lk.link_type(0) is None and lk.link_type(15) is None
    cas = np.real(np.diag(lk.casimir_L))[lk.sector]
    assert np.allclose(cas, [0, 0.75, 0.75, 0.75, 0.75, 0])
    assert lk.c[0].dtype == np.complex128


def test_det_u_on_sector():
    lk = A.RishonLink()
    D = lk.det_U[np.ix_(lk.sector, lk.sector)]
    expect = np.zeros((6, 6))
    expect[5, 0] = 2.0
    assert np.abs(D - expect).max() < 1e-14


def test_end_generator_matches_link_generator():
    lk = A.RishonLink()
    for a in range(3):
        gl, gr = lk.end_generator(a, "L"), lk.end_generator(a, "R")
        assert np.abs(np.kron(np.eye(4), gl) - lk.L[a]).max() < 1e-14
        assert np.abs(np.kron(gr, np.eye(4)) - lk.R[a]).max() < 1e-14
    with pytest.raises(ValueError):
        lk.end_generator(0, "X")


def test_embed_and_global_bilinear_string_free():
    lk = A.RishonLink()
    g = A.global_bilinear(4, 6, 8)
    assert np.abs(g - A.embed_link_op(lk.U(0, 0), 1, 2).toarray()).max() < 1e-14
    E = A.embed_link_op(np.diag(np.arange(16.0)), 2, 3)
    assert np.abs(np.real(E.diagonal()) - ((np.arange(16 ** 3) >> 8) & 15)).max() == 0
