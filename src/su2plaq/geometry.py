"""Plaquette diagram and point-split graph (prompts/002 §2.1, docs/METHODS.md §1)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Link:
    index: int
    name: str
    start: tuple[int, int]
    end: tuple[int, int]
    inner: bool
    near_end: str | None  # 'L' (starts at its corner) or 'R' (ends there) for outer links, None for inner


@dataclass(frozen=True)
class Corner:
    index: int
    site: tuple[int, int]
    ends: tuple[tuple[int, str], ...]  # ((link_index,'out'|'in'),)*4 in canonical order


@dataclass
class Diagram:
    links: list[Link] = field(default_factory=list)
    corners: list[Corner] = field(default_factory=list)
    loop: list[tuple[int, int]] = field(default_factory=list)  # [(0,+1),(1,+1),(2,-1),(3,-1)]

    def inner_links(self) -> list[int]:
        return [l.index for l in self.links if l.inner]

    def outer_links(self) -> list[int]:
        return [l.index for l in self.links if not l.inner]

    def corner_of_end(self, link: int, role: str) -> int:
        """Corner index at the 'out' (start) or 'in' (end) end of `link`."""
        for c in self.corners:
            if (link, role) in c.ends:
                return c.index
        raise ValueError(f"link {link} has no '{role}' end at a corner")


# (name, start, end, inner) in link-index order (METHODS §1); outer links o0..o7 in corner order.
_LINKS = [
    ("b", (0, 0), (1, 0), True),
    ("r", (1, 0), (1, 1), True),
    ("t", (0, 1), (1, 1), True),
    ("l", (0, 0), (0, 1), True),
    ("o0", (-1, 0), (0, 0), False),
    ("o1", (0, -1), (0, 0), False),
    ("o2", (1, 0), (2, 0), False),
    ("o3", (1, -1), (1, 0), False),
    ("o4", (1, 1), (2, 1), False),
    ("o5", (1, 1), (1, 2), False),
    ("o6", (-1, 1), (0, 1), False),
    ("o7", (0, 1), (0, 2), False),
]
_CORNER_SITES = [(0, 0), (1, 0), (1, 1), (0, 1)]


def plaquette_diagram() -> Diagram:
    links = []
    for i, (name, s, e, inner) in enumerate(_LINKS):
        near = None
        if not inner:
            near = "R" if e in _CORNER_SITES else "L"
        links.append(Link(i, name, s, e, inner, near))
    corners = []
    for c, site in enumerate(_CORNER_SITES):
        ends = []
        for inner in (True, False):  # inner pair first, then outer pair; each by increasing link index
            for l in links:
                if l.inner != inner:
                    continue
                if l.start == site:
                    ends.append((l.index, "out"))
                if l.end == site:
                    ends.append((l.index, "in"))
        corners.append(Corner(c, site, tuple(ends)))
    return Diagram(links, corners, [(0, 1), (1, 1), (2, -1), (3, -1)])


@dataclass
class SplitGraph:
    sites: list[tuple[str, int]]
    edges: dict[int, tuple[tuple[str, int], tuple[str, int]]]
    loop_sites: list[tuple[str, int]]
    virtual: dict[int, int]  # corner -> virtual edge index (12+c)


def point_split(d: Diagram) -> SplitGraph:
    """Split every corner into ('in', c) (inner pair + virtual edge) and ('out', c) (outer pair + virtual edge).

    Edge tuples follow the link direction (start site, end site). The far end of an outer link is the
    external leg ('ext', link_index), which is not one of the 8 trivalent sites.
    """
    sites = [(k, c) for k in ("in", "out") for c in range(len(d.corners))]
    edges: dict[int, tuple[tuple[str, int], tuple[str, int]]] = {}
    for l in d.links:
        if l.inner:
            edges[l.index] = (("in", d.corner_of_end(l.index, "out")), ("in", d.corner_of_end(l.index, "in")))
        elif l.near_end == "L":
            edges[l.index] = (("out", d.corner_of_end(l.index, "out")), ("ext", l.index))
        else:
            edges[l.index] = (("ext", l.index), ("out", d.corner_of_end(l.index, "in")))
    n = len(d.links)
    virtual = {}
    for c in d.corners:
        virtual[c.index] = n + c.index
        edges[n + c.index] = (("in", c.index), ("out", c.index))
    return SplitGraph(sites, edges, [("in", c.index) for c in d.corners], virtual)
