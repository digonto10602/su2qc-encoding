"""M0-A1..A3 — link algebra, 6j symbols, Paulo adapter (prompts/002 §2.2, METHODS §3)."""
import itertools

import numpy as np
import pytest

from tests.acceptance._api import api


@pytest.mark.parametrize("jmax", [0.5, 1.0])
def test_M0_A1_link_algebra(jmax):
    """[L_a,U_ij] = -(T_a U)_ij, [R_a,U_ij] = +(U T_a)_ij, sum L^2 = sum R^2 = j(j+1).
    Tolerance 1e-12: closed-form CG coefficients, <= 20 float64 operations per matrix element."""
    LinkSpace = api("su2plaq.su2.algebra:LinkSpace")
    SIGMA = api("su2plaq.su2.algebra:SIGMA")
    ls = LinkSpace(jmax)
    assert ls.dim == {0.5: 5, 1.0: 14}[jmax]
    U = ls.U()
    L, R = ls.generators()
    T = [s / 2 for s in SIGMA]
    worst = 0.0
    for a in range(3):
        for i in range(2):
            for j in range(2):
                lhs = L[a] @ U[i][j] - U[i][j] @ L[a]
                rhs = -sum(T[a][i, k] * U[k][j] for k in range(2))
                worst = max(worst, np.abs(lhs - rhs).max())
                lhs = R[a] @ U[i][j] - U[i][j] @ R[a]
                rhs = sum(U[i][k] * T[a][k, j] for k in range(2))
                worst = max(worst, np.abs(lhs - rhs).max())
    cas = ls.casimir()
    worst = max(worst, np.abs(sum(l @ l for l in L) - cas).max(), np.abs(sum(r @ r for r in R) - cas).max())
    assert worst <= 1e-12
    # local order at jmax = 1/2 is fixed by METHODS §3
    if jmax == 0.5:
        assert [tuple(s) for s in ls.states] == [(0.0, 0.0, 0.0), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5), (0.5, -0.5, 0.5), (0.5, -0.5, -0.5)]


def test_M0_A2_six_j_vs_sympy():
    """In-house Racah 6j equals sympy's wigner_6j for all admissible arguments <= 3/2, and f_symbol follows its
    definition. Tolerance 1e-13: rationals times square roots, two independent closed formulas."""
    six_j = api("su2plaq.su2.wigner:six_j")
    f_symbol = api("su2plaq.su2.wigner:f_symbol")
    from sympy import Rational
    from sympy.physics.wigner import wigner_6j

    vals = [0.0, 0.5, 1.0, 1.5]
    worst, n_checked = 0.0, 0
    for args in itertools.product(vals, repeat=6):
        try:
            ref = float(wigner_6j(*[Rational(int(round(2 * x)), 2) for x in args]))
        except ValueError:  # sympy raises for inadmissible triangles; ours must return 0 there
            assert six_j(*args) == 0.0
            continue
        worst = max(worst, abs(six_j(*args) - ref))
        n_checked += 1
    assert n_checked > 100 and worst <= 1e-13
    # f_symbol definition (METHODS §5)
    j1, j2, j12, j3, J, j23 = 0.5, 0.5, 1.0, 0.5, 0.5, 0.0
    expect = (-1) ** int(round(j1 + j2 + j3 + J)) * np.sqrt((2 * j12 + 1) * (2 * j23 + 1)) * six_j(j1, j2, j12, j3, J, j23)
    assert abs(f_symbol(j1, j2, j12, j3, J, j23) - expect) <= 1e-13
    # orthogonality of the recoupling matrix: sum_{j12} F(j12,j23) F(j12,j23') = delta
    for j23 in (0.0, 1.0):
        for j23p in (0.0, 1.0):
            s = sum(f_symbol(0.5, 0.5, j12, 0.5, 0.5, j23) * f_symbol(0.5, 0.5, j12, 0.5, 0.5, j23p) for j12 in (0.0, 1.0))
            assert abs(s - (1.0 if j23 == j23p else 0.0)) <= 1e-13


def test_M0_A3_paulo_adapter():
    """V_P U_cg V_P^T = U_paulo (Eq. 28 rules) for all colour indices; V_P is the explicit signed permutation
    |mm'>_P = s(m)s(m')|1/2,-m,-m'>_CG. Tolerance 1e-14: a signed permutation is exact up to one rounding."""
    LinkSpace = api("su2plaq.su2.algebra:LinkSpace")
    paulo_U = api("su2plaq.su2.algebra:paulo_U")
    paulo_adapter = api("su2plaq.su2.algebra:paulo_adapter")
    PAULO_ORDER = api("su2plaq.su2.algebra:PAULO_ORDER")
    assert tuple(PAULO_ORDER) == ("0", "++", "+-", "-+", "--")
    V = np.asarray(paulo_adapter(), dtype=float)
    Ucg = LinkSpace(0.5).U()
    Up = paulo_U()
    # rules of Eq. 28 reproduced independently here
    r = 1 / np.sqrt(2)
    s = {0: 1.0, 1: -1.0}
    idx = {(0, 0): 1, (0, 1): 2, (1, 0): 3, (1, 1): 4}
    for a in range(2):
        for b in range(2):
            ref = np.zeros((5, 5), complex)
            ref[0, idx[(a, b)]] = r
            ref[idx[(1 - a, 1 - b)], 0] = r * s[a] * s[b]
            assert np.abs(np.asarray(Up[a][b]) - ref).max() <= 1e-14
            assert np.abs(V @ Ucg[a][b] @ V.T - ref).max() <= 1e-14
    expected_V = np.zeros((5, 5))
    expected_V[0, 0] = 1
    expected_V[4, 1] = 1    # CG (1/2,+,+) -> Paulo |--|, sign +
    expected_V[3, 2] = -1   # CG (1/2,+,-) -> Paulo |-+>, sign -
    expected_V[2, 3] = -1   # CG (1/2,-,+) -> Paulo |+->, sign -
    expected_V[1, 4] = 1    # CG (1/2,-,-) -> Paulo |++>, sign +
    assert np.array_equal(V, expected_V)
    assert np.array_equal(V @ V.T, np.eye(5))
