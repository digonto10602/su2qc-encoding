"""Shared helpers for the locked M9 (fuzzy) acceptance tests (LOCKED, planner-owned; prompts/300 §2, METHODS-fuzzy F1–F5).

Independent reference constructions in plain numpy (never imported from the production code) so that the tests check the
production operators against the paper's matrices (arXiv:2308.05253v4 Eqs. 29–30, 35–37) rather than against themselves.
Conventions: row-major vectorisation |row,col>, index 8 q1 + 4 q2 + 2 q3 + q4; link l at qubits 4l..4l+3 with q_k on qubit
4l+4-k (little-endian, METHODS-fuzzy F1).
"""
from __future__ import annotations

import itertools
from fractions import Fraction

import numpy as np

from tests.acceptance._api import api, op_norm_after_phase  # noqa: F401  (re-exported)

SEED = 20261104
NOMINAL = (0.37, 0.61)
ALTS = ((0.91, 0.23), (1.70, 1.00))
ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}

I2 = np.eye(2)
SIG = [np.array([[0, 1], [1, 0]], complex), np.array([[0, -1j], [1j, 0]]), np.array([[1, 0], [0, -1]], complex)]
_Z = np.zeros((2, 2))
GAMMA0 = 0.5 * np.block([[_Z, I2], [I2, _Z]]).astype(complex)
GAMMA = [0.5 * np.block([[_Z, 1j * s], [-1j * s, _Z]]) for s in SIG]
GAMMA5 = np.block([[I2, _Z], [_Z, -I2]]).astype(complex)
T_R = [0.5 * np.block([[s, _Z], [_Z, _Z]]) for s in SIG]
T_L = [0.5 * np.block([[_Z, _Z], [_Z, s]]) for s in SIG]
I4 = np.eye(4)


def U_link(a: int, b: int) -> np.ndarray:
    return (1 if a == b else 0) * GAMMA0 - 1j * sum(SIG[A][a, b] * GAMMA[A] for A in range(3))


def lmul(M):
    return np.kron(M, I4)


def rmul(M):
    return np.kron(I4, M.T)


def ad(M):
    return lmul(M) - rmul(M)


def ref_K1():
    return sum(ad(T) @ ad(T) for T in T_L) + sum(ad(T) @ ad(T) for T in T_R)


def ref_K2():
    return -sum(lmul(U_link(a, b)) @ rmul(U_link(a, b).conj().T) + lmul(U_link(a, b).conj().T) @ rmul(U_link(a, b))
                for a in range(2) for b in range(2))


def ref_plaquette_row() -> np.ndarray:
    """256x256 on the row spaces of (b, r, t, l) with link b LEAST significant (index sum_l (2 q1^l + q2^l) 4^l)."""
    U = [[U_link(a, b) for b in range(2)] for a in range(2)]
    Ud = [[U[a][b].conj().T for b in range(2)] for a in range(2)]

    def k4(Ab, Ar, At, Al):  # kron with link l most significant, b least significant
        return np.kron(np.kron(np.kron(Al, At), Ar), Ab)

    return sum(k4(U[a][b], U[b][c], Ud[d][c], Ud[a][d]) for a in range(2) for b in range(2) for c in range(2) for d in range(2))


# ---- counting references (METHODS-fuzzy F4) ----
IRREPS = [((0, 0), 1), ((0, 0), 1), ((Fraction(1, 2), Fraction(1, 2)), 1), ((Fraction(1, 2), Fraction(1, 2)), 1), ((1, 0), 1), ((0, 1), 1)]
CORNERS = {0: [("b", "out"), ("l", "out"), ("o0", "in"), ("o1", "in")],
           1: [("b", "in"), ("r", "out"), ("o2", "out"), ("o3", "in")],
           2: [("r", "in"), ("t", "in"), ("o4", "out"), ("o5", "out")],
           3: [("t", "out"), ("l", "in"), ("o6", "in"), ("o7", "out")]}
LINKS = ["b", "r", "t", "l"] + [f"o{k}" for k in range(8)]


def tri(j1, j2):
    return {Fraction(k, 2) for k in range(int(2 * abs(j1 - j2)), int(2 * (j1 + j2)) + 1, 2)}


def n_singlet(js):
    return len(tri(js[0], js[1]) & tri(js[2], js[3]))


def near(irr, role):
    return irr[0] if role == "out" else irr[1]


def far(irr, role):
    return irr[1] if role == "out" else irr[0]


def ref_count(far_weighted: bool, outer_vacuum: bool = False) -> int:
    inner = ["b", "r", "t", "l"]
    total = 0
    for assign in itertools.product(range(6), repeat=4):
        irr = {l: IRREPS[a][0] for l, a in zip(inner, assign)}
        prod = 1
        for ends in CORNERS.values():
            inn = [near(irr[l], r) for l, r in ends if l in irr]
            outs = [(l, r) for l, r in ends if l not in irr]
            s = 0
            for a1, a2 in itertools.product(range(6), repeat=2):
                i1, i2 = IRREPS[a1][0], IRREPS[a2][0]
                if outer_vacuum and (i1 != (0, 0) or i2 != (0, 0)):
                    continue
                n = n_singlet(inn + [near(i1, outs[0][1]), near(i2, outs[1][1])])
                if far_weighted:
                    n *= int(2 * far(i1, outs[0][1]) + 1) * int(2 * far(i2, outs[1][1]) + 1)
                s += n
            prod *= s
        total += prod
    return total


def ref_isolated_plaquette_count() -> int:
    inner = ["b", "r", "t", "l"]
    total = 0
    for assign in itertools.product(range(6), repeat=4):
        irr = {l: IRREPS[a][0] for l, a in zip(inner, assign)}
        prod = 1
        for ends in CORNERS.values():
            inn = [near(irr[l], r) for l, r in ends if l in irr]
            prod *= 1 if inn[0] == inn[1] else 0
        total += prod
    return total


# ---- COO Gauss residual on 48-qubit states (independent of the production code) ----
def _apply_one_link(M16: np.ndarray, link: int, keys: np.ndarray, amps: np.ndarray):
    """Apply a 16x16 one-link operator (index 8q1+4q2+2q3+q4 = bits 4l+3..4l) to a COO vector."""
    shift = 4 * link
    loc = (keys >> shift) & 15
    rest = keys & ~(np.int64(15) << shift)
    out_k, out_a = [], []
    for j in range(16):
        col = M16[:, j]
        nz = np.flatnonzero(np.abs(col) > 0)
        sel = loc == j
        if not sel.any() or len(nz) == 0:
            continue
        kk = rest[sel][:, None] | (nz[None, :].astype(np.int64) << shift)
        aa = amps[sel][:, None] * col[nz][None, :]
        out_k.append(kk.ravel())
        out_a.append(aa.ravel())
    if not out_k:
        return np.zeros(0, np.int64), np.zeros(0, complex)
    k = np.concatenate(out_k)
    a = np.concatenate(out_a)
    uk, inv = np.unique(k, return_inverse=True)
    ua = np.zeros(len(uk), complex)
    np.add.at(ua, inv, a)
    return uk, ua


def ref_gauss_residual(keys: np.ndarray, amps: np.ndarray) -> float:
    worst = 0.0
    for ends in CORNERS.values():
        for A in range(3):
            acc = {}
            for l, role in ends:
                M = ad(T_L[A]) if role == "out" else ad(T_R[A])
                k, a = _apply_one_link(M, LINKS.index(l), keys, amps)
                for kk, aa in zip(k.tolist(), a.tolist()):
                    acc[kk] = acc.get(kk, 0) + aa
            worst = max(worst, float(np.sqrt(sum(abs(v) ** 2 for v in acc.values()))))
    return worst


def ops_of(qc):
    return {inst.operation.name for inst in qc.data}


def qubits_touched(qc):
    return {qc.find_bit(q).index for inst in qc.data for q in inst.qubits}
