"""Independent reference for the M7 (loop-string-hadron) acceptance tests (LOCKED; numpy/scipy only, no project imports).

Schwinger-boson (prepotential) Fock space of one trivalent site: three link ends (legs 0, 1, 2), each an oscillator
doublet a_1, a_2, every mode truncated at NMAX quanta.  Definitions (Raychowdhury-Stryker, arXiv:1912.06133):
  loop operators (their Eq. for L^{sigma sigma'}_{ij}, with atilde_alpha = eps_{alpha beta} a_beta, eps_12 = +1)
      L++_ij = a^dag(i).atilde^dag(j),  L+-_ij = a^dag(i).a(j),  L-+_ij = a(i).a^dag(j),  L--_ij = a(i).atilde(j);
  loop states  |l_12, l_23, l_31> = (L++_12)^l12 (L++_23)^l23 (L++_31)^l31 |0> / sqrt(l12! l23! l31! (l12+l23+l31+1)!);
  link-end operators  U_L = (N+1)^(-1/2) [[a_2^dag, a_1], [-a_1^dag, a_2]],  U_R = [[a_1^dag, a_2^dag], [-a_2, a_1]] (N+1)^(-1/2).
All operators are exact on states with at most NMAX - 1 quanta per mode before a raising operator acts (the tests stay
inside that range).  Planner prototype: scratch/planner/proto_m7_lsh_model.py (P1, P2), residuals <= 1.2e-15.
"""
from __future__ import annotations

import functools
import itertools
import math

import numpy as np
import scipy.sparse as sp

NMAX = 4
NM = 6
DIM = (NMAX + 1) ** NM
CYCLIC = ((0, 1), (1, 2), (2, 0))          # loop numbers (l_12, l_23, l_31) <-> leg pairs


@functools.lru_cache(maxsize=1)
def _modes():
    a1 = sp.csr_matrix(np.diag(np.sqrt(np.arange(1, NMAX + 1)), 1))
    eye = sp.identity(NMAX + 1, format="csr")
    A = []
    for m in range(NM):
        out = None
        for q in range(NM):
            f = a1 if q == m else eye
            out = f if out is None else sp.kron(out, f, format="csr")
        A.append(out)
    return A, [x.T.conj().tocsr() for x in A]


def a(leg, al):
    return _modes()[0][2 * leg + al]


def ad(leg, al):
    return _modes()[1][2 * leg + al]


def loop_op(i, j, si, sj):
    """L^{si sj}_{ij} as a sparse matrix on the Fock space (si, sj = +1 / -1)."""
    if (si, sj) == (+1, +1):
        return ad(i, 0) @ ad(j, 1) - ad(i, 1) @ ad(j, 0)
    if (si, sj) == (+1, -1):
        return ad(i, 0) @ a(j, 0) + ad(i, 1) @ a(j, 1)
    if (si, sj) == (-1, +1):
        return a(i, 0) @ ad(j, 0) + a(i, 1) @ ad(j, 1)
    if (si, sj) == (-1, -1):
        return a(i, 0) @ a(j, 1) - a(i, 1) @ a(j, 0)
    raise ValueError((si, sj))


def number_op(leg):
    return ad(leg, 0) @ a(leg, 0) + ad(leg, 1) @ a(leg, 1)


def inv_sqrt_np1(leg):
    return sp.diags(1.0 / np.sqrt(number_op(leg).diagonal() + 1.0)).tocsr()


@functools.lru_cache(maxsize=None)
def loop_state(l):
    """Normalised |l_12, l_23, l_31> as a dense vector."""
    v = np.zeros(DIM)
    v[0] = 1.0
    for (i, j), n in zip(CYCLIC, l):
        for _ in range(n):
            v = loop_op(i, j, +1, +1) @ v
    s = sum(l)
    return v / math.sqrt(math.factorial(l[0]) * math.factorial(l[1]) * math.factorial(l[2]) * math.factorial(s + 1))


def dressed_ladder(sp_, sn_):
    """(N_n + 1)^(-1/2) L^{sp sn}_{pn} (N_p + 1)^(-1/2) with (p, n) = legs (0, 1)."""
    return inv_sqrt_np1(1) @ loop_op(0, 1, sp_, sn_) @ inv_sqrt_np1(0)


def UL(leg):
    f = inv_sqrt_np1(leg)
    return [[f @ ad(leg, 1), f @ a(leg, 0)], [-(f @ ad(leg, 0)), f @ a(leg, 1)]]


def UR(leg):
    f = inv_sqrt_np1(leg)
    return [[ad(leg, 0) @ f, ad(leg, 1) @ f], [-(a(leg, 1) @ f), a(leg, 0) @ f]]


def dagger(U):
    return [[U[j][i].T.conj().tocsr() for j in range(2)] for i in range(2)]


def matmul2(X, Y):
    return [[X[i][0] @ Y[0][j] + X[i][1] @ Y[1][j] for j in range(2)] for i in range(2)]


def vertex_product(kind):
    """2x2 operator matrix of the vertex contraction of type `kind` for incoming leg 0 (a) and outgoing leg 1 (b):
    RL = U_R(a) U_L(b), LR = U_L^dag(a) U_R^dag(b), RR = U_R(a) U_R^dag(b), LL = U_L^dag(a) U_L(b)."""
    if kind == "RL":
        return matmul2(UR(0), UL(1))
    if kind == "LR":
        return matmul2(dagger(UL(0)), dagger(UR(1)))
    if kind == "RR":
        return matmul2(UR(0), dagger(UR(1)))
    if kind == "LL":
        return matmul2(dagger(UL(0)), UL(1))
    raise ValueError(kind)


@functools.lru_cache(maxsize=1)
def safe_projector():
    """Columns = Fock states with at most NMAX - 2 quanta on each mode of legs 0, 1 and none on leg 2."""
    occ = np.array(list(itertools.product(range(NMAX + 1), repeat=NM)))
    safe = np.flatnonzero((occ[:, :4].max(axis=1) <= NMAX - 2) & (occ[:, 4:].max(axis=1) == 0))
    return sp.csr_matrix((np.ones(len(safe)), (safe, np.arange(len(safe)))), shape=(DIM, len(safe)))
