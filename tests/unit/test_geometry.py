"""Unit tests for su2plaq.geometry (own checks, independent of the acceptance file)."""
from collections import Counter

from su2plaq.geometry import plaquette_diagram, point_split


def test_every_link_end_belongs_to_exactly_one_corner_or_is_external():
    d = plaquette_diagram()
    used = Counter(e for c in d.corners for e in c.ends)
    assert all(v == 1 for v in used.values()) and len(used) == 16
    # inner links have both ends at corners, outer links exactly one
    for l in d.links:
        n = sum((l.index, r) in used for r in ("in", "out"))
        assert n == (2 if l.inner else 1)


def test_corner_site_matches_link_endpoints():
    d = plaquette_diagram()
    for c in d.corners:
        for li, role in c.ends:
            l = d.links[li]
            assert (l.start if role == "out" else l.end) == c.site


def test_near_end_consistent_with_role():
    d = plaquette_diagram()
    for l in d.links[4:]:
        c = d.corners[d.corner_of_end(l.index, "out" if l.near_end == "L" else "in")]
        assert (l.start if l.near_end == "L" else l.end) == c.site


def test_split_graph_edges_follow_link_direction():
    d = plaquette_diagram()
    g = point_split(d)
    for l in d.links[:4]:
        a, b = g.edges[l.index]
        assert a == ("in", d.corner_of_end(l.index, "out")) and b == ("in", d.corner_of_end(l.index, "in"))
    assert sorted(g.edges) == list(range(16))
