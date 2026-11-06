"""Design of the exact magnetic circuit U_B = prod_p exp(i kappa_p beta (|u_p><v_p| + h.c.)) (prompts/200 §2.5; METHODS-rishon R7).

Every bright pair p is a two-level rotation between two *stabiliser-type* vectors of the 16-bit data register,
u, v = 2^{-k/2} sum over an affine subspace of (-1)^{q(x)} |x>  with q quadratic over GF(2) (amplitudes +-1, +-1/sqrt2,
+-1/2, +-1/4 -- read from the operator, nothing is typed in).  For each pair this module builds, from the operator only:

* a separating bit j (a GF(2) combination of data bits that is 0 on supp(u) and 1 on supp(v); a CX network makes it a qubit),
* a frame F_p (X, CX, Z, CZ, H and their j-controlled versions) with F_p u = s_u |0_j=0, 0...0>, F_p v = s_v |j=1, 0...0>,
* a minimal set of control qubits C (all required to be 0) such that the rotation  C-Rx(-2 s kappa beta) on j  leaves
  F_p(complement of span{u, v}) untouched; "minimal" is a greedy hitting set over the support of F_p c for the valid codes c
  (don't-care outside the 1296 valid codes), computed by exact sparse simulation of the frame.

Then  U_B restricted to the pair = F_p^dagger [C-Rx] F_p  exactly.  The gate list of a frame is independent of beta.
"""
from __future__ import annotations

import functools

import numpy as np
import scipy.sparse as sp

from su2plaq.rishon import operators as _ops

_TOL_AMP = 1e-9
_CTRL_TOL = 1e-9


# ----------------------------------------------------------------------------------------------------- GF(2) helpers
def _bits(x: int) -> list[int]:
    return [i for i in range(x.bit_length()) if (x >> i) & 1]


def _solve_separator(s_u: list[int], s_v: list[int], n: int = 16) -> list[int]:
    """All lambda (as bitmasks) with lambda.x constant = c on s_u, = c+1 on s_v, for some c: returns the affine solution
    family as [particular, nullspace basis...] over the unknowns (lambda_0..lambda_{n-1}, c)."""
    rows = []
    for x in s_u:
        rows.append((x | (1 << n), 0))                    # lambda.x + c = 0
    for x in s_v:
        rows.append((x | (1 << n), 1))                    # lambda.x + c = 1
    # gaussian elimination on (mask, rhs)
    piv: dict[int, tuple[int, int]] = {}
    for mask, rhs in rows:
        for p, (m, r) in piv.items():
            if (mask >> p) & 1:
                mask ^= m
                rhs ^= r
        if mask == 0:
            if rhs:
                raise ValueError("supp(u) and supp(v) have intersecting affine hulls: no separating functional")
            continue
        p = mask.bit_length() - 1
        for q, (m, r) in list(piv.items()):
            if (m >> p) & 1:
                piv[q] = (m ^ mask, r ^ rhs)
        piv[p] = (mask, rhs)
    free = [i for i in range(n + 1) if i not in piv]
    part = 0
    for p, (m, r) in piv.items():
        if r:
            part |= 1 << p
    null = []
    for f in free:
        vec = 1 << f
        for p, (m, r) in piv.items():
            if (m >> f) & 1:
                vec |= 1 << p
        null.append(vec)
    return [part] + null


def _best_separator(s_u: list[int], s_v: list[int]) -> int:
    """Minimum-weight lambda (bitmask over the 16 data bits), ties -> smallest bitmask value."""
    fam = _solve_separator(s_u, s_v)
    part, null = fam[0], fam[1:]
    combos = np.array([part], dtype=np.int64)
    for nv in null:
        combos = np.concatenate([combos, combos ^ np.int64(nv)])
    lam = combos & np.int64((1 << 16) - 1)
    weight = np.zeros(len(lam), dtype=np.int64)
    for b in range(16):
        weight += (lam >> b) & 1
    ok = weight > 0
    lam, weight = lam[ok], weight[ok]
    best = np.lexsort((lam, weight))[0]
    return int(lam[best])


def _apply_gate_code(code: int, name: str, qs: tuple[int, ...]) -> int:
    if name == "x":
        return code ^ (1 << qs[0])
    if name == "cx":
        return code ^ (((code >> qs[0]) & 1) << qs[1])
    raise ValueError(f"not a permutation gate: {name}")


# ----------------------------------------------------------------------------------------------------- stabiliser unprep
def _unprep(codes: list[int], amps: list[float], skip: int) -> dict:
    """Gates (on bits != skip) that map the stabiliser-type vector sum_i amps[i] |codes[i]> to s |0...0> with s = +-1:
    {'net': X/CX (affine permutation onto the standard subspace), 'phase': Z/CZ, 'had': H, 'pivots': [...]}.
    Raises ValueError if the vector is not of that type."""
    x0 = codes[0]
    basis: list[tuple[int, int]] = []
    for c in codes[1:]:
        v = c ^ x0
        for p, b in basis:
            if (v >> p) & 1:
                v ^= b
        if v:
            p = v.bit_length() - 1
            basis = [(q, (b ^ v) if (b >> p) & 1 else b) for q, b in basis]
            basis.append((p, v))
    k = len(basis)
    if len(codes) != 2 ** k:
        raise ValueError("support is not an affine subspace")
    if any((b >> skip) & 1 for _, b in basis):
        raise ValueError("support varies on the separating bit")
    x0r = x0
    for p, b in basis:
        if (x0r >> p) & 1:
            x0r ^= b
    pivots = [p for p, _ in basis]
    net: list[tuple[str, tuple[int, ...]]] = []
    for p, b in basis:
        for m in _bits(b ^ (1 << p)):
            net.append(("cx", (p, m)))
    for m in _bits(x0r):
        if m != skip and m not in pivots:
            net.append(("x", (m,)))
    phi = np.zeros(2 ** k)
    seen = np.zeros(2 ** k, dtype=bool)
    for c, a in zip(codes, amps):
        t = sum(((c >> p) & 1) << i for i, p in enumerate(pivots))
        phi[t] = a
        seen[t] = True
    if not seen.all() or not np.allclose(np.abs(phi), 2.0 ** (-k / 2), atol=_TOL_AMP):
        raise ValueError("amplitudes are not uniform on the affine support")
    sign = 1 if phi[0] > 0 else -1
    f = (phi * sign < 0).astype(int)                      # (-1)^{q(t)}, q(0) = 0
    a = [int(f[1 << i]) for i in range(k)]
    c2 = {(i, j): int(f[(1 << i) | (1 << j)]) ^ a[i] ^ a[j] for i in range(k) for j in range(i + 1, k)}
    for t in range(2 ** k):
        q = 0
        for i in range(k):
            if (t >> i) & 1:
                q ^= a[i]
                for j in range(i + 1, k):
                    if (t >> j) & 1:
                        q ^= c2[(i, j)]
        if q != f[t]:
            raise ValueError("sign pattern is not a quadratic form over GF(2) (non-Clifford vector)")
    phase = [("z", (pivots[i],)) for i in range(k) if a[i]] + [("cz", (pivots[i], pivots[j])) for (i, j), v in c2.items() if v]
    had = [("h", (p,)) for p in pivots]
    return {"net": net, "phase": phase, "had": had, "pivots": pivots, "sign": sign}


def _cond(gates: list, j: int, branch: int) -> list:
    """Each gate g (x, cx, z, cz, h; all self-inverse) applied only when qubit j == branch.  branch 1: the j-controlled gate;
    branch 0: g followed by the j-controlled g (for j = 1 the two cancel)."""
    ctl = {"x": "cx", "cx": "ccx", "z": "cz", "cz": "ccz", "h": "ch"}
    out = []
    for name, qs in gates:
        if branch == 0:
            out.append((name, qs))
        out.append((ctl[name], (j,) + tuple(qs)))
    return out


def _min_hitting_set(rows: np.ndarray, j: int) -> list[int]:
    """Smallest set of qubits (!= j) such that every y in `rows` has a 1 on at least one of them (exhaustive by size,
    ties -> lexicographically smallest); the controls are then required to be 0."""
    import itertools

    masks = np.unique(rows & ~np.int64(1 << j))
    if len(masks) and masks.min() == 0:
        raise ValueError("complement images overlap the rotated pair: no control set exists")
    masks = [int(m) for m in masks]
    keep = [m for m in masks if not any(o != m and (o & m) == o for o in masks)]    # drop supersets
    cand = [i for i in range(16) if i != j]
    for size in range(0, len(cand) + 1):
        for comb in itertools.combinations(cand, size):
            s = sum(1 << i for i in comb)
            if all(m & s for m in keep):
                return list(comb)
    raise ValueError("no control set exists")


# ----------------------------------------------------------------------------------------------------- one pair
def _simulate_frame(frame: list, codes: np.ndarray):
    from qiskit import QuantumCircuit

    from su2plaq.evaluate.sparse_sim import run_batch

    qc = QuantumCircuit(16)
    for name, qs in frame:
        getattr(qc, name)(*qs)
    return run_batch(qc, codes)


def design_pair(u: np.ndarray, v: np.ndarray, codes: np.ndarray) -> dict:
    """Frame, pivot, controls and rotation sign of one bright pair (all from the vectors u, v on `codes`)."""
    iu = np.flatnonzero(np.abs(u) > 1e-12)
    iv = np.flatnonzero(np.abs(v) > 1e-12)
    cu, cv = [int(c) for c in codes[iu]], [int(c) for c in codes[iv]]
    au, av = [float(x) for x in u[iu]], [float(x) for x in v[iv]]
    lam = _best_separator(cu, cv)
    j = min(_bits(lam))
    frame: list[tuple[str, tuple[int, ...]]] = [("cx", (i, j)) for i in _bits(lam) if i != j]

    def push(cs):
        out = []
        for c in cs:
            for name, qs in frame:
                c = _apply_gate_code(c, name, qs)
            out.append(c)
        return out

    cu, cv = push(cu), push(cv)
    if (cu[0] >> j) & 1:
        frame.append(("x", (j,)))
        cu, cv = [c ^ (1 << j) for c in cu], [c ^ (1 << j) for c in cv]
    if any((c >> j) & 1 for c in cu) or not all((c >> j) & 1 for c in cv):
        raise ValueError("separating bit construction failed")
    # larger affine hull -> its network is unconditional, the smaller state gets the conditional part
    info_v = _unprep(cv, av, j)
    frame += info_v["net"]
    cu2 = cu
    for name, qs in info_v["net"]:
        cu2 = [_apply_gate_code(c, name, qs) for c in cu2]
    info_u = _unprep(cu2, au, j)
    frame += _cond(info_u["net"] + info_u["phase"] + info_u["had"], j, 0)
    frame += _cond(info_v["phase"] + info_v["had"], j, 1)
    # exact images and the control set
    nb = _simulate_frame(frame, codes)
    Fm = sp.csr_matrix((nb.amps, (nb.keys, nb.cols)), shape=(1 << 16, len(codes)))
    Fu, Fv = Fm @ u, Fm @ v
    su, sv = Fu[0], Fv[1 << j]
    if abs(abs(su) - 1) > 1e-10 or abs(abs(sv) - 1) > 1e-10 or abs(su.imag) > 1e-10 or abs(sv.imag) > 1e-10:
        raise ValueError(f"frame does not map u, v to basis states (amplitudes {su}, {sv})")
    if abs(np.abs(Fu).sum() - 1) > 1e-9 or abs(np.abs(Fv).sum() - 1) > 1e-9:
        raise ValueError("frame images of u, v are not single basis states")
    N = Fm - sp.csr_matrix(Fu[:, None]) @ sp.csr_matrix(u[None, :]) - sp.csr_matrix(Fv[:, None]) @ sp.csr_matrix(v[None, :])
    N = N.tocoo()
    rows = np.unique(N.row[np.abs(N.data) > _CTRL_TOL])
    controls = _min_hitting_set(rows, j)
    sign = int(round(su.real * sv.real))
    return {"pivot": j, "controls": sorted(controls), "frame_gates": [(n, tuple(q)) for n, q in frame],
            "sign": sign, "n_images": int(len(rows))}


@functools.lru_cache(maxsize=1)
def designs() -> tuple:
    """Per-pair designs (beta independent), in the order of operators.bright_pairs() (kappa, first code)."""
    codes = _ops.inner_codes()
    out = []
    for u, v, k in _ops.bright_pairs():
        d = design_pair(u, v, codes)
        d["kappa"] = float(k)
        out.append(d)
    return tuple(out)
