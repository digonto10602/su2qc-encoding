"""M0-G1, M0-G2 — diagram and point-split graph (prompts/002 §2.1, METHODS §1). Exact combinatorial checks."""
from tests.acceptance._api import api


def test_M0_G1_diagram():
    """12 links (4 inner, 8 outer), 4 corners with 2 inner + 2 outer ends in canonical order, loop [b+, r+, t-, l-].
    Tolerance: exact (combinatorial)."""
    d = api("su2plaq.geometry:plaquette_diagram")()
    assert len(d.links) == 12 and len(d.corners) == 4
    assert [l.name for l in d.links[:4]] == ["b", "r", "t", "l"]
    assert [(l.start, l.end) for l in d.links[:4]] == [((0, 0), (1, 0)), ((1, 0), (1, 1)), ((0, 1), (1, 1)), ((0, 0), (0, 1))]
    assert all(l.inner for l in d.links[:4]) and not any(l.inner for l in d.links[4:])
    assert d.inner_links() == [0, 1, 2, 3] and d.outer_links() == list(range(4, 12))
    assert all(l.near_end is None for l in d.links[:4])
    # outer links o0..o7: into (0,0), into (0,0), out of (1,0), into (1,0), out of (1,1), out of (1,1), into (0,1), out of (0,1)
    assert [l.near_end for l in d.links[4:]] == ["R", "R", "L", "R", "L", "L", "R", "L"]
    assert [l.end for l in d.links[4:6]] == [(0, 0), (0, 0)]
    assert d.links[6].start == (1, 0) and d.links[7].end == (1, 0)
    assert d.links[8].start == (1, 1) and d.links[9].start == (1, 1)
    assert d.links[10].end == (0, 1) and d.links[11].start == (0, 1)
    assert [c.site for c in d.corners] == [(0, 0), (1, 0), (1, 1), (0, 1)]
    expected_ends = [
        ((0, "out"), (3, "out"), (4, "in"), (5, "in")),
        ((0, "in"), (1, "out"), (6, "out"), (7, "in")),
        ((1, "in"), (2, "in"), (8, "out"), (9, "out")),
        ((2, "out"), (3, "in"), (10, "in"), (11, "out")),
    ]
    assert [tuple(c.ends) for c in d.corners] == expected_ends
    assert list(d.loop) == [(0, 1), (1, 1), (2, -1), (3, -1)]
    assert d.corner_of_end(0, "out") == 0 and d.corner_of_end(0, "in") == 1 and d.corner_of_end(11, "out") == 3


def test_M0_G2_point_split():
    """8 trivalent sites, 16 edges (12 real + 4 virtual), loop through the 4 inner sites, each virtual edge joins
    ('in',c) and ('out',c). Tolerance: exact."""
    d = api("su2plaq.geometry:plaquette_diagram")()
    g = api("su2plaq.geometry:point_split")(d)
    assert len(g.sites) == 8 and set(g.sites) == {(k, c) for k in ("in", "out") for c in range(4)}
    assert len(g.edges) == 16
    assert list(g.loop_sites) == [("in", 0), ("in", 1), ("in", 2), ("in", 3)]
    for c in range(4):
        e = g.virtual[c]
        assert e == 12 + c and set(g.edges[e]) == {("in", c), ("out", c)}
    # every real edge joins the two corners it connects; inner links join 'in' sites, outer links join an 'out' site
    for l in d.links:
        a, b = g.edges[l.index]
        if l.inner:
            assert {a[0], b[0]} == {"in"}
        else:
            assert "out" in (a[0], b[0])
    # each site has exactly 3 incident edges
    deg = {s: 0 for s in g.sites}
    for e, (a, b) in g.edges.items():
        if a in deg:
            deg[a] += 1
        if b in deg:
            deg[b] += 1
    assert all(v == 3 for s, v in deg.items() if s[0] == "in") and all(v == 3 for s, v in deg.items() if s[0] == "out")
