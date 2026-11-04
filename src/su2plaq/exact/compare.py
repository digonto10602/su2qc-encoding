"""Route A vs route B comparison (prompts/002 §2.4, docs/METHODS.md §5). Pure comparison tools."""
from __future__ import annotations

import numpy as np

from su2plaq.exact.spinnet import inner_labels


def gauge_align(A, B, tol: float = 1e-9) -> tuple[np.ndarray | None, float]:
    """Diagonal unitary D (returned as a vector) with A ~ D B D^dagger, A_ij = D_i B_ij conj(D_j).

    Phases are propagated along the non-zero pattern of B (|B_ij| > tol), one root per connected component with
    D = 1; residual = max|A - D B D^dagger|.  If the moduli differ (max ||A|-|B|| > tol) returns (None, max||A|-|B||)."""
    A = np.asarray(A)
    B = np.asarray(B)
    mod = float(np.abs(np.abs(A) - np.abs(B)).max())
    if mod > tol:
        return None, mod
    n = A.shape[0]
    D = np.zeros(n, dtype=np.complex128)
    seen = np.zeros(n, dtype=bool)
    for root in range(n):
        if seen[root]:
            continue
        D[root] = 1.0
        seen[root] = True
        stack = [root]
        while stack:
            i = stack.pop()
            for j in np.where((np.abs(B[i]) > tol) & ~seen)[0]:
                d = np.conj(A[i, j] / (D[i] * B[i, j]))  # conj(D_j) = A_ij / (D_i B_ij)
                D[j] = d / abs(d)
                seen[j] = True
                stack.append(j)
    res = float(np.abs(A - D[:, None] * B * np.conj(D)[None, :]).max())
    return D, res


def _as_matrix(H):
    H = np.asarray(H)
    return np.diag(H) if H.ndim == 1 else H


def spectra_match(HE_A, HB_A, HE_B, HB_B, g2_list=(0.5, 1.0, 2.0)) -> float:
    """max over g2 of max |eigvalsh(g2/2 HE + HB/g2)_A - (...)_B|."""
    worst = 0.0
    for g2 in g2_list:
        eA = np.linalg.eigvalsh(0.5 * g2 * _as_matrix(HE_A) + np.asarray(HB_A) / g2)
        eB = np.linalg.eigvalsh(0.5 * g2 * _as_matrix(HE_B) + np.asarray(HB_B) / g2)
        worst = max(worst, float(np.abs(eA - eB).max()))
    return worst


def outer_block_structure(HB_phys, basis, K=None) -> dict:
    """Structure of H_B^phys (rows/columns in basis.labels order) against the outer spins and the corner spins J.

    max_offblock = max |H_ik| between different outer-spin strings; max_J_violation = max |H_ik| between different
    J tuples; n_blocks, block_dims per outer-spin string (sorted by first occurrence); if K (the inner matrix) is
    given, every block is compared with K restricted to its inner labels: worst_abs_diff = max ||block|-|K_sub||,
    worst_gauge_residual = worst gauge_align residual over blocks (NaN entries if K is None)."""
    H = np.asarray(HB_phys)
    outer = [lab[0][4:] for lab in basis.labels]
    Jl = [lab[1] for lab in basis.labels]
    blocks: dict = {}
    for i, o in enumerate(outer):
        blocks.setdefault(o, []).append(i)
    n = len(outer)
    o_id = np.array([list(blocks).index(o) for o in outer])
    J_id = np.array([sorted(set(Jl)).index(J) for J in Jl])
    A = np.abs(H)
    max_off = float(A[o_id[:, None] != o_id[None, :]].max(initial=0.0))
    max_J = float(A[J_id[:, None] != J_id[None, :]].max(initial=0.0))
    worst_abs, worst_gauge = float("nan"), float("nan")
    if K is not None:
        il_index = {lab: i for i, lab in enumerate(inner_labels(basis.jmax))}
        worst_abs, worst_gauge = 0.0, 0.0
        for o, sel in blocks.items():
            il = [il_index[(basis.labels[i][0][:4], basis.labels[i][1])] for i in sel]
            blockA = H[np.ix_(sel, sel)]
            blockK = np.asarray(K)[np.ix_(il, il)]
            worst_abs = max(worst_abs, float(np.abs(np.abs(blockA) - np.abs(blockK)).max()))
            D, r = gauge_align(blockA, blockK)
            worst_gauge = max(worst_gauge, r if D is not None else float("inf"))
    return {"max_offblock": max_off, "max_J_violation": max_J, "n_blocks": len(blocks),
            "worst_gauge_residual": worst_gauge, "worst_abs_diff": worst_abs,
            "block_dims": [len(v) for v in blocks.values()]}
