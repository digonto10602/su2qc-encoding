"""Route-B (spin network) cross-check (prompts/002 §2.4). Stubs (step 0.1)."""
from __future__ import annotations

import numpy as np

import itertools

from su2plaq._stub import todo
from su2plaq.geometry import plaquette_diagram
from su2plaq.su2.wigner import triangle


def labels(diagram=None, jmax: float = 0.5) -> list[tuple]:
    """Route-B enumeration: ((j_0..j_11),(J_0..J_3)) admissible at the 8 trivalent sites of the (inner|outer)
    point-split graph, i.e. triangle(j_a, j_b, J_c) and triangle(j_1, j_2, J_c) at every corner c
    (docs/METHODS.md §5). Same tuples as `PhysicalBasis.labels`."""
    d = diagram if diagram is not None else plaquette_diagram()
    n2 = int(round(2 * jmax))
    spins = [k / 2 for k in range(n2 + 1)]
    Jvals = [k / 2 for k in range(2 * n2 + 1)]
    corner_links = [tuple(i for i, _ in c.ends) for c in d.corners]
    cache: dict = {}

    def choices(ja, jb, j1, j2):
        key = (ja, jb, j1, j2)
        if key not in cache:
            cache[key] = [J for J in Jvals if triangle(ja, jb, J) and triangle(j1, j2, J)]
        return cache[key]

    out = []
    for jconf in itertools.product(spins, repeat=len(d.links)):
        ch = [choices(*(jconf[i] for i in links)) for links in corner_links]
        if not all(ch):
            continue
        for Jl in itertools.product(*ch):
            out.append((jconf, tuple(Jl)))
    return out


def inner_labels(jmax: float = 0.5) -> list[tuple]:
    todo("inner_labels")


def plaquette_P(labels) -> np.ndarray:
    todo("plaquette_P")


def K_inner(jmax: float = 0.5) -> np.ndarray:
    todo("K_inner")


def h_magnetic_phys_6j(labels) -> np.ndarray:
    todo("h_magnetic_phys_6j")


def h_electric_6j(labels, inner_only: bool = True) -> np.ndarray:
    todo("h_electric_6j")
