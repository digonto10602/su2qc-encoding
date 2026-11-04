"""M1 — lattice geometry of the 2x2 periodic lattice (plan 001 §6, METHODS §1.1).

Exact combinatorial references (no tolerance needed).
"""
import numpy as np
import pytest

from su2qc.lattice import torus2x2, open_plaquette, single_link


def test_torus_counts():
    lat = torus2x2()
    assert lat.n_sites == 4
    assert lat.n_links == 8
    assert lat.n_plaquettes == 4
    assert set(lat.sites) == {(0, 0), (1, 0), (0, 1), (1, 1)}


def test_torus_link_indexing_and_ends():
    lat = torus2x2()
    # link index i = 2*site_index + mu, site_index = 2*ny + nx
    for s_idx, (nx, ny) in enumerate(lat.sites):
        for mu in (0, 1):
            i = lat.link_index((nx, ny), mu)
            assert i == 2 * s_idx + mu
            start, end = lat.link_ends(i)
            assert start == s_idx
            ex, ey = ((nx + 1) % 2, ny) if mu == 0 else (nx, (ny + 1) % 2)
            assert lat.sites[end] == (ex, ey)


def test_torus_doubled_edges_present():
    """With L=2 the two x-links of a row join the same pair of sites in opposite directions."""
    lat = torus2x2()
    pairs = {}
    for i in range(lat.n_links):
        a, b = lat.link_ends(i)
        pairs.setdefault(frozenset((a, b)), []).append(i)
    assert all(len(v) == 2 for v in pairs.values()), pairs
    assert len(pairs) == 4


def test_torus_plaquettes():
    lat = torus2x2()
    for p_idx, (nx, ny) in enumerate(lat.sites):
        plaq = lat.plaquettes[p_idx]
        assert len(plaq) == 4
        links = [l for (l, o) in plaq]
        orients = [o for (l, o) in plaq]
        assert len(set(links)) == 4
        # U_x(n) U_y(n+x) U_x^dag(n+y) U_y^dag(n)
        assert links == [lat.link_index((nx, ny), 0), lat.link_index(((nx + 1) % 2, ny), 1),
                         lat.link_index((nx, (ny + 1) % 2), 0), lat.link_index((nx, ny), 1)]
        assert orients == [+1, +1, -1, -1]
    # every link appears in exactly two plaquettes, once forward and once backward
    count = {i: [] for i in range(lat.n_links)}
    for plaq in lat.plaquettes:
        for (l, o) in plaq:
            count[l].append(o)
    assert all(sorted(v) == [-1, 1] for v in count.values()), count


def test_links_at_site():
    lat = torus2x2()
    for s in range(lat.n_sites):
        legs = lat.links_at(s)
        assert len(legs) == 4
        assert sorted(e for (_, e) in legs) == [0, 0, 1, 1]  # two outgoing, two incoming


def test_staggered_phases_and_mass_signs():
    lat = torus2x2()
    for (nx, ny) in lat.sites:
        assert lat.eta((nx, ny), 0) == 1
        assert lat.eta((nx, ny), 1) == (-1) ** nx
        assert lat.stag_sign((nx, ny)) == (-1) ** (nx + ny)
    assert sum(lat.stag_sign(s) for s in lat.sites) == 0


def test_open_plaquette_and_single_link():
    op = open_plaquette()
    assert op.n_sites == 4 and op.n_links == 4 and op.n_plaquettes == 1
    links = [l for (l, o) in op.plaquettes[0]]
    assert links == [op.link_index((0, 0), 0), op.link_index((1, 0), 1), op.link_index((0, 1), 0), op.link_index((0, 0), 1)]
    assert [o for (l, o) in op.plaquettes[0]] == [1, 1, -1, -1]
    sl = single_link()
    assert sl.n_sites == 2 and sl.n_links == 1 and sl.n_plaquettes == 0
