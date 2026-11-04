"""Route-B (spin network, 6j) construction (prompts/002 §2.4, docs/METHODS.md §5).

Built only from the label enumeration and Wigner 6j/F-symbols; never from route A (compare in compare.py)."""
from __future__ import annotations

import itertools

import numpy as np

from su2plaq.geometry import plaquette_diagram
from su2plaq.su2.wigner import f_symbol, triangle


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
    """Distinct inner parts ((j_b, j_r, j_t, j_l), (J_0..J_3)) of the route-B labels, sorted (47 at jmax = 1/2).
    Every triangle-admissible J has an outer completion, so these are the inner-only admissible labels."""
    return sorted({(j[:4], J) for j, J in labels(None, jmax)})


# loop corners: c visits the inner links (p(c), n(c)) = c0:(l,b), c1:(b,r), c2:(r,t), c3:(t,l); link indices b,r,t,l = 0..3
_CORNER_PN = [(3, 0), (0, 1), (1, 2), (2, 3)]


def plaquette_P(labels) -> np.ndarray:
    """P[new, old] = prod_c F^{J_c j_p(c) j_n(c)}_{1/2 j'_n(c) j'_p(c)}, with j'_l = j_l +- 1/2 on the four inner links and
    J, outer spins unchanged (docs/METHODS.md §5).  In the code's argument order
    f_symbol(j1, j2, j12, j3, J, j23) = F^{j1 j2 j12}_{j3 J j23} this is
    f_symbol(J_c, j_p, j_n, 1/2, j'_n, j'_p).  Only labels present in `labels` are reachable (truncation).
    Labels need only carry j[:4] and J (inner labels work as well as full labels)."""
    index = {lab: i for i, lab in enumerate(labels)}
    n = len(labels)
    P = np.zeros((n, n))
    for col, (j, Jl) in enumerate(labels):
        for signs in itertools.product((0.5, -0.5), repeat=4):
            jn = list(j)
            for e, sg in enumerate(signs):
                jn[e] = j[e] + sg
            new = (tuple(jn), Jl)
            if new not in index:
                continue
            amp = 1.0
            for c, (ep, en) in enumerate(_CORNER_PN):
                amp *= f_symbol(Jl[c], j[ep], j[en], 0.5, jn[en], jn[ep])
                if amp == 0.0:
                    break
            if abs(amp) > 1e-14:
                P[index[new], col] += amp
    return P


def K_inner(jmax: float = 0.5) -> np.ndarray:
    """-(P + P^T) on inner_labels (47x47 at jmax = 1/2)."""
    P = plaquette_P(inner_labels(jmax))
    return -(P + P.T)


def h_magnetic_phys_6j(labels) -> np.ndarray:
    """-(P + P^T) on the full labels (433x433 at jmax = 1/2)."""
    P = plaquette_P(labels)
    return -(P + P.T)


def h_electric_6j(labels, inner_only: bool = True) -> np.ndarray:
    """Diagonal matrix sum_l j_l (j_l+1) over the inner links (all 12 if inner_only is False)."""
    out = []
    for j, _J in labels:
        js = j[:4] if inner_only else j
        out.append(sum(x * (x + 1) for x in js))
    return np.diag(np.array(out, dtype=np.float64))
