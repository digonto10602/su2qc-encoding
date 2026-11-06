"""M9-D1, M9-D2 — fuzzy link algebra, Pauli forms, irreps/spectra and plaquette structure (prompts/300 §3 steps 9.1–9.2;
METHODS-fuzzy F2, F5; arXiv:2308.05253v4 Eqs. 24–25, 29–30, 35–37, 63–64)."""
import numpy as np
import pytest

from tests.acceptance.m9._fz import (GAMMA, GAMMA0, GAMMA5, SIG, T_L, T_R, U_link, ad, api, lmul, ref_K1, ref_K2,
                                     ref_plaquette_row, rmul)

TOL = 1e-12  # entries are multiples of 1/4; products of <= 3 16x16 matrices round at <= 1e-15 in float64


def test_M9_D1_link_algebra():
    """Production link operators equal the paper's matrices (residual <= 1e-12); su(2) relations for calT_L, calT_R;
    [calT_L, calT_R] = 0; transformation law (Eqs. 24-25) with the signs stated; pseudo-reality; K1, K2 definitions;
    Pauli forms (SparsePauliOp on 4 qubits, q_k on qubit 4-k) reproduce the matrices; F = Z_3 commutes with K1 and anticommutes with K2."""
    lk = api("su2plaq.fuzzy.link")
    assert np.abs(lk.GAMMA0 - GAMMA0).max() <= TOL and np.abs(lk.GAMMA5 - GAMMA5).max() <= TOL
    for A in range(3):
        assert np.abs(lk.GAMMA[A] - GAMMA[A]).max() <= TOL
        assert np.abs(lk.T_L[A] - T_L[A]).max() <= TOL and np.abs(lk.T_R[A] - T_R[A]).max() <= TOL
    for a in range(2):
        for b in range(2):
            assert np.abs(lk.U_link(a, b) - U_link(a, b)).max() <= TOL
            assert np.abs(lk.U_op(a, b) - lmul(U_link(a, b))).max() <= TOL
    M = np.arange(16, dtype=complex).reshape(4, 4) + 1j
    assert np.abs(lk.lmul(M) - lmul(M)).max() <= TOL and np.abs(lk.rmul(M) - rmul(M)).max() <= TOL
    TLs = [lk.calT_L(A) for A in range(3)]
    TRs = [lk.calT_R(A) for A in range(3)]
    for A in range(3):
        assert np.abs(TLs[A] - ad(T_L[A])).max() <= TOL and np.abs(TRs[A] - ad(T_R[A])).max() <= TOL
    eps = np.zeros((3, 3, 3))
    for (i, j, k), v in {(0, 1, 2): 1, (1, 2, 0): 1, (2, 0, 1): 1, (0, 2, 1): -1, (2, 1, 0): -1, (1, 0, 2): -1}.items():
        eps[i, j, k] = v
    for A in range(3):
        for B in range(3):
            for Ts in (TLs, TRs):
                comm = Ts[A] @ Ts[B] - Ts[B] @ Ts[A]
                assert np.abs(comm - 1j * sum(eps[A, B, C] * Ts[C] for C in range(3))).max() <= TOL
            assert np.abs(TLs[A] @ TRs[B] - TRs[B] @ TLs[A]).max() <= TOL
    U = [[lk.U_op(a, b) for b in range(2)] for a in range(2)]
    for A in range(3):
        for a in range(2):
            for b in range(2):
                lhs = TLs[A] @ U[a][b] - U[a][b] @ TLs[A]
                assert np.abs(lhs + 0.5 * sum(SIG[A][a, c] * U[c][b] for c in range(2))).max() <= TOL
                rhs = TRs[A] @ U[a][b] - U[a][b] @ TRs[A]
                assert np.abs(rhs - 0.5 * sum(U[a][c] * SIG[A][c, b] for c in range(2))).max() <= TOL
    ep = np.array([[0, 1], [-1, 0]])
    for a in range(2):
        for b in range(2):
            assert np.abs(U[a][b].conj().T - sum(ep[a, c] * ep[b, d] * U[c][d] for c in range(2) for d in range(2))).max() <= TOL
    K1, K2 = lk.K1(), lk.K2()
    assert np.abs(K1 - ref_K1()).max() <= TOL and np.abs(K2 - ref_K2()).max() <= TOL
    assert np.abs(K1 - K1.conj().T).max() <= TOL and np.abs(K2 - K2.conj().T).max() <= TOL
    # Pauli forms: little-endian qubit 4-k carries q_k, so SparsePauliOp.to_matrix() (qubit 0 least significant)
    # is directly the 16x16 matrix in the index 8 q1 + 4 q2 + 2 q3 + q4
    assert np.abs(lk.pauli_K1().to_matrix() - K1).max() <= TOL
    assert np.abs(lk.pauli_K2().to_matrix() - K2).max() <= TOL
    assert len(lk.pauli_K2().simplify()) == 4 and len(lk.pauli_K1().simplify()) == 7
    for a in range(2):
        for b in range(2):
            pu = lk.pauli_U(a, b).simplify()
            assert np.abs(pu.to_matrix() - U[a][b]).max() <= TOL and len(pu) <= 2
    F = lk.flavour()
    assert np.abs(F - rmul(GAMMA5)).max() <= TOL
    Zq3 = np.kron(np.kron(np.kron(np.eye(2), np.eye(2)), SIG[2]), np.eye(2))
    assert np.abs(F - Zq3).max() <= TOL
    assert np.abs(F @ K1 - K1 @ F).max() <= TOL and np.abs(F @ K2 + K2 @ F).max() <= TOL
    Zc = lk.centre()
    assert np.abs(Zc - np.kron(np.kron(np.kron(SIG[2], np.eye(2)), SIG[2]), np.eye(2))).max() <= TOL
    assert np.abs(Zc @ K1 - K1 @ Zc).max() <= TOL and np.abs(Zc @ K2 - K2 @ Zc).max() <= TOL
    assert all(np.abs(Zc @ U[a][b] + U[a][b] @ Zc).max() <= TOL for a in range(2) for b in range(2))


def _mult(vals, tol=1e-8):
    r = np.round(np.asarray(vals).real / tol) * tol
    u, c = np.unique(r, return_counts=True)
    return {float(k): int(v) for k, v in zip(u, c)}


def test_M9_D2_irreps_spectra_plaquette():
    """Irreps 2(0,0)+2(1/2,1/2)+(1,0)+(0,1); K1 spectrum {0^2, 3/2^8, 2^6}; K2 spectrum {-4, -2^4, 0^6, 2^4, 4}; [K1,K2] = 0;
    plaquette_row equals the reference, is Hermitian, spectrum {0^174, +-1^16, +-2^24, +-4}; 64 Pauli strings with |c| = 1/8;
    block structure: only z -> zbar transitions, singular values per parity pattern {2^4 (x6), 1^16 (x1), 4 (x1)};
    the greedy 4-cluster product is NOT the exponential (error >= 0.5 at beta = 0.61) — it is a reported row only.
    Eigenvalues are rounded at 1e-8 (eigh on <= 256x256 is accurate to 1e-13); multiplicities are exact integers."""
    lk = api("su2plaq.fuzzy.link")
    pq = api("su2plaq.fuzzy.plaquette")
    irr = lk.irreps()
    assert sorted((float(a), float(b), int(m)) for a, b, m in irr) == [(0.0, 0.0, 2), (0.0, 1.0, 1), (0.5, 0.5, 2), (1.0, 0.0, 1)]
    CL, CR = lk.casimirs()
    assert np.abs(CL - sum(ad(T) @ ad(T) for T in T_L)).max() <= TOL and np.abs(CR - sum(ad(T) @ ad(T) for T in T_R)).max() <= TOL
    K1, K2 = lk.K1(), lk.K2()
    assert _mult(np.linalg.eigvalsh(K1)) == {0.0: 2, 1.5: 8, 2.0: 6}
    assert _mult(np.linalg.eigvalsh(K2)) == {-4.0: 1, -2.0: 4, 0.0: 6, 2.0: 4, 4.0: 1}
    assert np.abs(K1 @ K2 - K2 @ K1).max() <= TOL
    W = pq.plaquette_row()
    assert W.shape == (256, 256) and np.abs(W - ref_plaquette_row()).max() <= TOL and np.abs(W - W.conj().T).max() <= TOL
    assert _mult(np.linalg.eigvalsh(W)) == {-4.0: 1, -2.0: 24, -1.0: 16, 0.0: 174, 1.0: 16, 2.0: 24, 4.0: 1}
    P = pq.plaquette_pauli().simplify()
    assert P.num_qubits == 8 and len(P) == 64 and np.allclose(np.abs(P.coeffs), 0.125, atol=1e-12)
    assert np.abs(P.to_matrix() - W).max() <= TOL
    # block structure in the four block bits (qubits 1,3,5,7 of the 8-qubit row register: q1 of links b,r,t,l)
    idx = np.arange(256)
    z = sum(((idx >> (2 * l + 1)) & 1) << l for l in range(4))
    nz = np.argwhere(np.abs(W) > 1e-12)
    assert np.all(z[nz[:, 0]] == 15 - z[nz[:, 1]])
    bs = pq.block_structure()
    assert sorted(bs) == list(range(8))
    sv_all = []
    for p, blk in bs.items():
        sv = np.sort(np.asarray(blk["sing_vals"]))[::-1]
        sv_all.append(tuple(np.round(sv, 8)))
        D = np.asarray(blk["D"])
        assert D.shape == (16, 16) and np.allclose(np.linalg.svd(D, compute_uv=False), sv, atol=1e-10)
    from collections import Counter
    c = Counter(sv_all)
    assert c[tuple([2.0] * 4 + [0.0] * 12)] == 6 and c[tuple([1.0] * 16)] == 1 and c[tuple([4.0] + [0.0] * 15)] == 1
    from scipy.linalg import expm
    beta = 0.61
    Ucl = pq.cluster_product(beta)
    assert np.abs(Ucl.conj().T @ Ucl - np.eye(256)).max() <= 1e-10
    assert np.linalg.norm(expm(2j * beta * W) - Ucl, 2) >= 0.5
