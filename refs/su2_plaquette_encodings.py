"""
SU(2) plaquette with 8 outer links (12 links, 4 four-valent corners):
register sizes and gauge-invariant state counts for several truncations/encodings.

Run:  python3 su2_plaquette_encodings.py
Needs: numpy

Geometry
--------
Inner links: b = U_1(0,0), r = U_2(1,0), t = U_1(0,1), l = U_2(0,0)
Corners and the two inner links that meet there:
    (0,0): b, l     (1,0): b, r     (1,1): r, t     (0,1): t, l
Each corner also has its own two outer links (8 in total).

Outer-link boundary choices
---------------------------
closed : all outer links fixed to j = 0  (isolated plaquette)
open   : outer links dynamical; far ends are free.  Two numbers are reported:
         'labels' = number of spin-network states (far-end index fixed)
         'full'   = full Hilbert-space dimension (far-end index free, x (2j+1) per outer link)
"""
from fractions import Fraction as F
from itertools import product
from math import ceil, log2
import numpy as np

HALF = F(1, 2)


def spins(jmax):
    """Allowed spins 0, 1/2, ..., jmax."""
    return [F(n, 2) for n in range(int(2 * jmax) + 1)]


def qubits_binary(d):
    return 0 if d <= 1 else ceil(log2(d))


# ---------------------------------------------------------------- fusion rules
def admissible(a, b, c, k=None):
    """Can spins a, b couple to c?  k=None: ordinary SU(2).  k int: SU(2)_k."""
    if (a + b + c).denominator != 1:
        return False
    if not (abs(a - b) <= c <= a + b):
        return False
    if k is not None and a + b + c > k:
        return False
    return True


def n_intertwiners(a, b, c, d, k=None):
    """Number of singlets in a (x) b (x) c (x) d, counted via intermediate spin J
    (pairing a,b | c,d).  This is the extra label a 4-valent vertex needs."""
    Jmax = min(a + b, c + d)
    count = 0
    J = F(0)
    while J <= Jmax:
        if admissible(a, b, J, k) and admissible(c, d, J, k):
            count += 1
        J += HALF
    return count


# ------------------------------------------------- numerical check of Gauss law
def spin_ops(j):
    """Spin matrices Sx, Sy, Sz for spin j (dimension 2j+1)."""
    d = int(2 * j + 1)
    m = np.array([float(j) - i for i in range(d)])
    sp = np.zeros((d, d))
    for i in range(1, d):
        sp[i - 1, i] = np.sqrt(float(j * (j + 1)) - m[i] * (m[i] + 1))
    sx = (sp + sp.T) / 2
    sy = (sp - sp.T) / 2j
    sz = np.diag(m)
    return sx, sy, sz


def singlet_dim_numeric(js):
    """Dimension of the total-spin-0 subspace of the tensor product of spins js,
    found by diagonalising the total Casimir S^2.  This is Gauss's law at a vertex."""
    dims = [int(2 * j + 1) for j in js]
    D = int(np.prod(dims))
    if D == 1:
        return 1
    S = [np.zeros((D, D), dtype=complex) for _ in range(3)]
    for idx, j in enumerate(js):
        ops = spin_ops(j)
        for a in range(3):
            mats = [np.eye(d) for d in dims]
            mats[idx] = ops[a]
            full = mats[0]
            for M in mats[1:]:
                full = np.kron(full, M)
            S[a] += full
    S2 = sum(s @ s for s in S)
    ev = np.linalg.eigvalsh(S2)
    return int(np.sum(np.abs(ev) < 1e-8))


def check_gauss_law(jmax):
    bad = 0
    tested = 0
    for js in product(spins(jmax), repeat=4):
        tested += 1
        if singlet_dim_numeric(js) != n_intertwiners(*js):
            bad += 1
    return tested, bad


# ------------------------------------------------ gauge-invariant state counts
CORNERS = [("b", "l"), ("b", "r"), ("r", "t"), ("t", "l")]


def count_states(jmax, boundary, k=None, link_weight=None, outer_free_index=False):
    """Sum over inner-link spins of the product over corners of
    sum over that corner's two outer spins of N_intertwiner * weights."""
    S = spins(jmax)
    w = link_weight or (lambda j: 1)
    total = 0
    for jb, jr, jt, jl in product(S, repeat=4):
        inner = {"b": jb, "r": jr, "t": jt, "l": jl}
        weight_inner = w(jb) * w(jr) * w(jt) * w(jl)
        prod_c = 1
        for (p, q) in CORNERS:
            a, bb = inner[p], inner[q]
            s = 0
            outer = [F(0)] if boundary == "closed" else S
            for o1, o2 in product(outer, repeat=2):
                n = n_intertwiners(a, bb, o1, o2, k)
                if n == 0:
                    continue
                f = n * w(o1) * w(o2)
                if outer_free_index:
                    f *= int(2 * o1 + 1) * int(2 * o2 + 1)
                s += f
            prod_c *= s
            if prod_c == 0:
                break
        total += weight_inner * prod_c
    return total


def count_link_label_configs(jmax, k=None):
    """How many assignments of one spin per link (n-qubit encoding) obey the coupling rules
    at every corner, and how many of those have a corner with >1 intertwiner
    (i.e. the link labels alone do NOT fix the state)."""
    S = spins(jmax)
    allowed, ambiguous = 0, 0
    for jb, jr, jt, jl in product(S, repeat=4):
        inner = {"b": jb, "r": jr, "t": jt, "l": jl}
        per_corner = []
        for (p, q) in CORNERS:
            ok, amb = 0, 0
            for o1, o2 in product(S, repeat=2):
                n = n_intertwiners(inner[p], inner[q], o1, o2, k)
                if n >= 1:
                    ok += 1
                if n >= 2:
                    amb += 1
            per_corner.append((ok, amb))
        a = int(np.prod([c[0] for c in per_corner]))
        u = int(np.prod([c[0] - c[1] for c in per_corner]))  # all corners unambiguous
        allowed += a
        ambiguous += a - u
    return allowed, ambiguous


# ----------------------------------------------------------------- registers
def report(jmax):
    print(f"\n================  j_max = {jmax}  ================")
    nlinks, ncorners = 12, 4
    S = spins(jmax)
    d_link = sum(int(2 * j + 1) ** 2 for j in S)
    k = int(2 * jmax)

    print(f"Gauss-law check (numeric Casimir vs. intertwiner formula), one corner:")
    tested, bad = check_gauss_law(jmax)
    print(f"  {tested} spin assignments tested, {bad} mismatches")

    print("\nGauge-invariant state counts on the 12-link diagram")
    rows = [
        ("closed (outer j=0)", count_states(jmax, "closed")),
        ("open, spin-network labels", count_states(jmax, "open")),
        ("open, full (far-end index free)", count_states(jmax, "open", outer_free_index=True)),
        (f"q-deformed SU(2)_{k}, closed", count_states(jmax, "closed", k=k)),
        (f"q-deformed SU(2)_{k}, open labels", count_states(jmax, "open", k=k)),
    ]
    for name, n in rows:
        print(f"  {name:38s} {n:>10d}")

    allowed, amb = count_link_label_configs(jmax)
    print(f"\nn-qubit encoding, link labels alone: {len(S)**12} raw strings, {allowed} obey the corner rules,"
          f" {amb} of those have a corner with >1 singlet (labels alone not enough)")

    # point-split: each corner -> two 3-valent sites joined by a virtual link (spin J <= 2 jmax)
    J_vals = 2 * int(2 * jmax) + 1                 # J = 0 .. 2 jmax in half-integer steps
    print("\nRegister sizes (qubits, binary encoding)")
    reg = {
        "KS electric basis |j m m'> per link":
            (nlinks * qubits_binary(d_link), f"{d_link} states/link"),
        "n-qubit: one spin label per link, n = L*ceil(log2(2jmax+1))":
            (nlinks * qubits_binary(len(S)), f"L = {nlinks} links, {len(S)} labels/link, misses intertwiners"),
        "spin network: link labels + corner intertwiner":
            (nlinks * qubits_binary(len(S)) + ncorners * qubits_binary(J_vals),
             f"intertwiner J has up to {J_vals} values (unused ones = leakage)"),
        "LSH, point-split (8 trivalent sites x 3 loop numbers)":
            (8 * 3 * qubits_binary(int(2 * jmax) + 1),
             f"loop numbers 0..{int(2*jmax)}, Abelian-like checks on links"),
        "q-deformed SU(2)_k (k = 2 j_max), labels + intertwiner":
            (nlinks * qubits_binary(len(S)) + ncorners * qubits_binary(int(2 * jmax) + 1),
             f"k = {k}: coupling rule j1+j2+j3 <= k removes some J"),
    }
    for name, (q, note) in reg.items():
        print(f"  {name:55s} {q:>4d}   ({note})")
    print(f"  {'unary/one-hot spin label per link':55s} {nlinks*len(S):>4d}   (one qubit per allowed j)")

    print("\nn-qubit encoding for other link counts (binary, one label per link)")
    b = qubits_binary(len(S))
    for name, L in [("closed plaquette, inner links only", 4),
                    ("this diagram: 4 inner + 8 outer", 12)]:
        print(f"  {name:40s} L = {L:2d}  ->  n = {L*b}")
    bv = qubits_binary(J_vals)   # virtual link carries J = 0 .. 2 jmax
    print(f"  {'this diagram + 4 point-split virtual links':40s} n = 12*{b} + 4*{bv} = {12*b + 4*bv}"
          f"  (virtual J up to {2*jmax})")


def report_jmax_independent():
    print("\n================  schemes not set by j_max  ================")
    groups = {"binary tetrahedral 2T": 24, "binary octahedral 2O": 48, "binary icosahedral 2I": 120}
    for name, order in groups.items():
        q = qubits_binary(order)
        print(f"  group-element register, {name:24s} |G|={order:3d}: {q} qubits/link, {12*q} total")
    print("  rishon quantum link model: 4 fermion modes/link (2 colours x 2 ends) -> 4 qubits/link, 48 total;"
          " rishon-number-2 sector has C(4,2)=6 states/link")
    for Q in (2, 3, 4):
        print(f"  orbifold lattice, Q={Q} qubits/boson: minimal SU(2) embedding 4 bosons/link -> {4*Q*12} total;"
              f" standard C^4 embedding 8 bosons/link -> {8*Q*12} total")
    print("  fuzzy gauge theory, D=4 (SO(5) spinor example): D^2 = 16 states/link -> 4 qubits/link, 48 total")


if __name__ == "__main__":
    for jm in (HALF, F(1)):
        report(jm)
    report_jmax_independent()
