"""Unit tests of su2plaq.circuits.fuzzy (link circuits, U_B sector data); small systems, fixed inputs."""
import numpy as np
import pytest
from qiskit.quantum_info import Operator
from scipy.linalg import expm

from su2plaq.circuits import fuzzy as cf
from su2plaq.fuzzy import link as lk
from su2plaq.fuzzy.plaquette import block_structure

ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}


def _phase_err(A, B):
    ov = np.trace(B.conj().T @ A)
    return np.linalg.norm(A - ov / abs(ov) * B, 2)


@pytest.mark.parametrize("alpha", [0.0, 0.37, 1.7])
def test_link_UE_exact_including_global_phase(alpha):
    qc = cf.link_UE(alpha)
    assert {i.operation.name for i in qc.data} <= ALLOWED
    assert np.abs(Operator(qc).data - expm(-0.5j * alpha * lk.K1())).max() <= 1e-12


@pytest.mark.parametrize("kappa", [0.0, 0.185, 0.9])
def test_link_UK_exact_including_global_phase(kappa):
    qc = cf.link_UK(kappa)
    assert {i.operation.name for i in qc.data} <= ALLOWED
    assert np.abs(Operator(qc).data - expm(-1j * kappa * lk.K2())).max() <= 1e-12


def test_pauli_tables_match_link_operators():
    """The hand-derived Z-string tables of the circuits reproduce K1, K2 (through the basis-change Cliffords)."""
    for clifford, zs, const, K in ((cf._E_CLIFFORD, cf._E_ZSTRINGS, cf._E_CONST, lk.K1()), (cf._K_CLIFFORD, cf._K_ZSTRINGS, 0.0, lk.K2())):
        from qiskit import QuantumCircuit
        C = QuantumCircuit(4)
        for nm, qs in clifford:
            getattr(C, nm)(*qs)
        Cm = Operator(C).data
        idx = np.arange(16)
        D = np.full(16, float(const))
        for qs, c in zs:
            sign = np.ones(16)
            for q in qs:
                sign *= 1 - 2 * ((idx >> q) & 1)
            D = D + c * sign
        assert np.abs(Cm.conj().T @ np.diag(D) @ Cm - K).max() <= 1e-12


def test_build_layers_register_layout():
    for n_links, with_outer in ((4, False), (12, True)):
        qc = cf.build_UE(0.37, with_outer=with_outer)
        assert qc.num_qubits == 4 * n_links and [r.name for r in qc.qregs] == (["d", "o"] if with_outer else ["d"])
    # the 16-qubit layer equals the tensor product of the link blocks (checked on a seeded random state, never as a 2^16 matrix)
    from qiskit.quantum_info import Statevector
    rng = np.random.default_rng(1)
    psi = rng.normal(size=65536) + 1j * rng.normal(size=65536)
    psi /= np.linalg.norm(psi)
    one = Operator(cf.link_UK(0.2)).data
    t = psi.reshape(16, 16, 16, 16)
    for ax in range(4):
        t = np.moveaxis(np.tensordot(one, t, axes=([1], [ax])), 0, ax)
    out = Statevector(psi).evolve(cf.build_UK(0.2)).data
    assert np.linalg.norm(out - t.reshape(-1)) <= 1e-12


def test_sector_data_is_clifford_with_expected_ranks():
    data = cf._sector_data()
    ranks = sorted((d["rank"], round(d["sigma"], 6)) for d in data.values())
    assert ranks == sorted([(4, 2.0)] * 6 + [(1, 4.0), (16, 1.0)])
    names = set()
    for d in data.values():
        for key in ("B", "A", "Bdag", "Adag"):
            names |= {i.operation.name for i in d[key][0].data}
    assert names <= {"h", "x", "z", "y", "s", "sdg", "cx", "cz", "swap"}


def test_sector_singular_vectors_diagonalise_D():
    """A_p^dag D_p B_p = sigma on the singular labels, from the synthesised fixed circuits (checks signs and phases)."""
    data = cf._sector_data()
    bs = block_structure()
    for p, d in data.items():
        def mat(key):
            qc, g = d[key]
            return np.exp(-1j * g) * Operator(qc).data
        Adag, B = mat("Adag"), mat("B")
        G = Adag @ bs[p]["D"] @ B
        r = d["rank"]
        idx = [(s << {4: 2, 1: 0, 16: 4}[r]) | k for s in [0] for k in range(r)] if r != 16 else list(range(16))
        assert np.abs(G[np.ix_(idx, idx)] - d["sigma"] * np.eye(r)).max() <= 1e-12
        mask = np.ones((16, 16), bool)
        mask[np.ix_(idx, idx)] = False
        assert np.abs(G[mask]).max(initial=0.0) <= 1e-12


def test_UB_small_exact_and_ancillas_clean():
    from scipy.linalg import expm as _expm
    from su2plaq.fuzzy.plaquette import plaquette_row
    beta = 0.61
    qc = cf.build_UB(beta)
    assert qc.num_qubits == 16 + 7 and qc.qregs[0].name == "d"
    assert {i.operation.name for i in qc.data} <= ALLOWED
    rows = {4 * l + 2 for l in range(4)} | {4 * l + 3 for l in range(4)}
    touched = {qc.find_bit(q).index for i in qc.data for q in i.qubits}
    assert touched <= rows | set(range(16, 23))
    # a few row-basis inputs through the sparse simulator
    from su2plaq.evaluate import sparse_sim as ss
    inputs = np.array([sum(((v >> (2 * l)) & 3) << (4 * l + 2) for l in range(4)) for v in (0, 5, 37, 100, 255)], dtype=np.int64)
    b = ss.run_batch(qc, inputs, cap=2_000_000)
    W = plaquette_row()
    V = _expm(2j * beta * W)
    for col, v in enumerate((0, 5, 37, 100, 255)):
        sel = b.cols == col
        keys, amps = b.keys[sel], b.amps[sel]
        # outputs live on row qubits only
        assert np.all((keys & ~np.int64(sum(3 << (4 * l + 2) for l in range(4)))) == 0)
        row = sum(((keys >> (4 * l + 2)) & 3) << (2 * l) for l in range(4))
        out = np.zeros(256, complex)
        np.add.at(out, row, amps)
        ph = np.vdot(V[:, v], out)
        assert np.linalg.norm(out - V[:, v]) <= 1e-10          # no global phase either
