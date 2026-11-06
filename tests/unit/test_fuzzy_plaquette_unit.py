"""Unit tests: fuzzy plaquette / targets (src/su2plaq/fuzzy/plaquette.py, targets.py)."""
import numpy as np
import scipy.sparse as sps
import scipy.sparse.linalg as spl

from su2plaq.fuzzy import link as lk
from su2plaq.fuzzy import plaquette as pq
from su2plaq.fuzzy import targets as tg


def test_hermitian_and_pauli():
    W = pq.plaquette_row()
    assert np.abs(W - W.conj().T).max() < 1e-13
    assert np.abs(pq.plaquette_pauli().to_matrix() - W).max() < 1e-12


def test_block_reconstructs_plaquette():
    W = pq.plaquette_row()
    R = np.zeros_like(W)
    for blk in pq.block_structure().values():
        R[np.ix_(blk["rows"], blk["cols"])] = blk["D"]
        R[np.ix_(blk["cols"], blk["rows"])] = blk["D"].conj().T
    assert np.abs(R - W).max() < 1e-13


def test_targets_unitary_and_additive():
    for M in (tg.UE_link(0.37), tg.UK_link(0.2), tg.UEK_link(0.37, 0.2), tg.UB_row(0.61)):
        assert np.abs(M.conj().T @ M - np.eye(M.shape[0])).max() < 1e-12
    assert np.abs(tg.UEK_link(0.37, 0.2) - tg.UK_link(0.2) @ tg.UE_link(0.37)).max() < 1e-12
    assert tg.kappa2_of(0.37, 1.0) == 0.185 and tg.kappa2_of(0.37, 0.0) == 0.0


def _sparse_plaquette_full():
    U = [[lk.U_op(a, b) for b in range(2)] for a in range(2)]
    W = None
    for a in range(2):
        for b in range(2):
            for c in range(2):
                for d in range(2):
                    ops = [U[a][b], U[b][c], U[d][c].conj().T, U[a][d].conj().T]  # b, r, t, l
                    t = sps.csr_matrix(np.eye(1))
                    for o in reversed(ops):  # link l most significant
                        t = sps.kron(t, sps.csr_matrix(o), format="csr")
                    W = t if W is None else W + t
    return W


def test_apply_step_matches_sparse_reference():
    rng = np.random.default_rng(20261104)
    psi = rng.normal(size=65536) + 1j * rng.normal(size=65536)
    psi /= np.linalg.norm(psi)
    alpha, beta, k2 = 0.37, 0.61, 0.185
    K = [sps.csr_matrix(m) for m in (lk.K1(), lk.K2())]
    I16 = sps.identity(16, format="csr")

    def on_link(M, l):  # link l at 16^l (b least significant)
        t = sps.identity(1, format="csr")
        for j in reversed(range(4)):
            t = sps.kron(t, M if j == l else I16, format="csr")
        return t

    Hk = sum(on_link(0.5 * alpha * K[0] + k2 * K[1], l) for l in range(4))
    W = _sparse_plaquette_full()
    ref1 = spl.expm_multiply(-1j * Hk, psi)
    ref1 = spl.expm_multiply(2j * beta * W, ref1)
    assert np.linalg.norm(tg.apply_step(psi, alpha, beta, k2, 1) - ref1) < 1e-10
    h = spl.expm_multiply(-0.5j * Hk, psi)
    ref2 = spl.expm_multiply(-0.5j * Hk, spl.expm_multiply(2j * beta * W, h))
    assert np.linalg.norm(tg.apply_step(psi, alpha, beta, k2, 2) - ref2) < 1e-10
