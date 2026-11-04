"""Plaquette diagram and point-split graph (prompts/002 §2.1). Stubs (step 0.1)."""
from __future__ import annotations

from dataclasses import dataclass

from su2plaq._stub import todo


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


class Diagram:
    links: list[Link]
    corners: list[Corner]
    loop: list[tuple[int, int]]  # [(0,+1),(1,+1),(2,-1),(3,-1)]

    def inner_links(self) -> list[int]:
        todo("Diagram.inner_links")

    def outer_links(self) -> list[int]:
        todo("Diagram.outer_links")

    def corner_of_end(self, link: int, role: str) -> int:
        todo("Diagram.corner_of_end")


def plaquette_diagram() -> Diagram:
    todo("plaquette_diagram")


@dataclass
class SplitGraph:
    sites: list[tuple[str, int]]
    edges: dict[int, tuple[tuple[str, int], tuple[str, int]]]
    loop_sites: list[tuple[str, int]]
    virtual: dict[int, int]  # corner -> virtual edge index (12+c)


def point_split(d: Diagram) -> SplitGraph:
    todo("point_split")
