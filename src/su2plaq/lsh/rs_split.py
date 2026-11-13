"""Uniform Raychowdhury-Stryker point splitting (prompts/401 step 8.U, METHODS-lsh L16).

Uniform Raychowdhury-Stryker point splitting as a COMPARISON ROW (no circuit): at corners 1 and 3 the four link ends are
paired (inner a, outer d | inner b, outer c) instead of (inner a, inner b | outer c, outer d).  The route-A magnetic
Hamiltonian is rotated into that basis by the corner recoupling R (real orthogonal, built from `corner_singlets`).
Source of the numbers: reports/research/400-lsh-model.md section 6.  Structure row only: a circuit in this splitting would write
outer-site qubits (a sixth encoding, prompts/401 D10)."""
from __future__ import annotations

import functools

import numpy as np

RS_CORNERS = (1, 3)
RS_PERM = (0, 3, 1, 2)          # (inner a, outer d | inner b, outer c) in the end order (inner a, inner b, outer c, outer d)
_TOL = 1e-12


@functools.lru_cache(maxsize=None)
def _route_a():
    from su2plaq.exact.operators import h_magnetic_phys
    from su2plaq.exact.physical import physical_basis

    basis = physical_basis(convention="cg")
    HA, _ = h_magnetic_phys(basis)
    return basis, np.asarray(HA)


def recoupling() -> np.ndarray:
    """433 x 433 real orthogonal R: column k' = the state with the RS pair spin at corners 1, 3, expanded in the route-A
    (inner | outer) corner-singlet basis; identity wherever a corner's intertwiner space is one-dimensional."""
    from su2plaq.exact.physical import corner_singlets

    basis, _ = _route_a()
    labels = basis.labels
    index = {lab: k for k, lab in enumerate(labels)}
    n = len(labels)
    R = np.eye(n)
    for c in RS_CORNERS:
        ends = basis.diagram.corners[c].ends
        Rc = np.zeros((n, n))
        for k, (j, J) in enumerate(labels):
            js = tuple(j[i] for i, _ in ends)
            roles = tuple(r for _, r in ends)
            V, Js = corner_singlets(js, roles)
            jsp, rolesp = tuple(js[p] for p in RS_PERM), tuple(roles[p] for p in RS_PERM)
            Vp, Jp = corner_singlets(jsp, rolesp)
            dims = [int(round(2 * x + 1)) for x in jsp]
            Vp_o = np.transpose(Vp.reshape(dims + [Vp.shape[1]]), list(np.argsort(RS_PERM)) + [4]).reshape(V.shape[0], Vp.shape[1])
            O = V.T @ Vp_o
            a = Js.index(J[c])
            for b in range(len(Jp)):
                Rc[k, index[(j, J[:c] + (Js[b],) + J[c + 1:])]] = O[a, b]
        R = R @ Rc
    return R


def h_magnetic_rs() -> np.ndarray:
    R = recoupling()
    return R.T @ _route_a()[1] @ R


def _pattern(H) -> dict:
    nz = np.abs(H) > _TOL
    return {"nnz": int(nz.sum()), "max_per_row": int(nz.sum(1).max()), "rows_nonzero": int((nz.sum(1) > 0).sum()),
            "moduli": sorted(set(np.round(np.abs(H[nz]), 9).tolist()))}


def structure() -> dict:
    basis, HA = _route_a()
    H = h_magnetic_rs()
    nz = np.abs(H) > _TOL
    dep = {}
    for k, (j, J) in enumerate(basis.labels):
        col = tuple(sorted(np.round(np.abs(H[:, k][nz[:, k]]), 9).tolist()))
        dep.setdefault((j[:4], J), set()).add(col)
    out = _pattern(H)
    out.update({"ours": _pattern(HA), "n_inner_patterns": len(dep),
                "outer_dependent_inner_patterns": sum(1 for v in dep.values() if len(v) > 1),
                "spectrum_diff": float(np.abs(np.linalg.eigvalsh(H) - np.linalg.eigvalsh(HA)).max()),
                "corners_repaired": list(RS_CORNERS), "sites_touched": 2 + 2 * len(RS_CORNERS), "qubits_touched": 3 * (2 + 2 * len(RS_CORNERS)),
                "sites_touched_ours": 4, "qubits_touched_ours": 12})
    return out

