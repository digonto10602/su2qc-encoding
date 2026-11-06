"""Fuzzy-gauge-theory circuits (M9; prompts/300 §1, METHODS-fuzzy F2, F3, F5).

Qubit map (F1): link l occupies qubits 4l..4l+3 with q1 -> 4l+3, q2 -> 4l+2, q3 -> 4l+1, q4 -> 4l.  Register 'd' = the 16 inner
qubits (links b, r, t, l), 'o' = the 32 outer qubits, ancillas after.  Allowed gates: the M1 ALLOWED set.

* `link_UE`, `link_UK` (one-link 4-qubit circuits, exact): a fixed Clifford basis change C (CNOT + H) diagonalises the Pauli
  strings of K1 resp. K2; the diagonal operator is a sum of Z-strings, each exponentiated as a CNOT ladder around one `rz`
  (angle linear in alpha resp. kappa2).
* `build_UB`: exact exp(+2 i beta square) on the 8 row qubits (METHODS-fuzzy F5).  Parity frame: three CNOTs q1^b -> q1^{l_k}
  leave the parities p_k in the qubits of q1^{r,t,l}; the operator then splits into 8 sectors p, in each of which
  square = X_f (x) D_p-type block, D_p = A_p Sigma_p B_p^dag.  For every sector the fixed unitaries B_p, A_p are *Clifford*
  (measured: every right/left singular basis of D_p is a Pauli orbit of a stabiliser state; the singular values are
  {2^4, 0^12}, {4, 0^15} and {1^16}); they are applied controlled on the flag a_p and on f (single-control gates on
  ancillas c0 = a_p & ~f, c1 = a_p & f), the rotation R_x(-4 beta sigma) acts on f controlled on the singular-label
  predicate, and the fixed parts are undone.  The only rotations are 8 controlled R_x with angles linear in beta.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister

N_INNER, N_OUTER = 16, 32

# ---- one-link Pauli data (METHODS-fuzzy F2): strings over (q1,q2,q3,q4) = qubits (3,2,1,0) ----
_Q1, _Q2, _Q3, _Q4 = 3, 2, 1, 0
# K1 = 3/2 - 1/4 (X2X4 - Y2Y4 + Z2Z4)(1 + Z1Z3); Clifford C = [cx(q2, q4), h(q2)] maps X2X4 -> Z2, Y2Y4 -> -Z2Z4, Z2Z4 -> Z4
_E_CLIFFORD = (("cx", (_Q2, _Q4)), ("h", (_Q2,)))
_E_CONST = 1.5
_E_ZSTRINGS = [((_Q2,), -0.25), ((_Q2, _Q4), -0.25), ((_Q4,), -0.25),
               ((_Q1, _Q2, _Q3), -0.25), ((_Q1, _Q2, _Q3, _Q4), -0.25), ((_Q1, _Q3, _Q4), -0.25)]
# K2 = -X1X3 + Y1X2Y3X4 - Y1Y2Y3Y4 + Y1Z2Y3Z4; same Clifford on the pairs (q1,q3) and (q2,q4):
# X1X3 -> Z1, Y1Y3 -> -Z1Z3, X2X4 -> Z2, Y2Y4 -> -Z2Z4, Z2Z4 -> Z4
_K_CLIFFORD = (("cx", (_Q1, _Q3)), ("cx", (_Q2, _Q4)), ("h", (_Q1,)), ("h", (_Q2,)))
_K_ZSTRINGS = [((_Q1,), -1.0), ((_Q1, _Q2, _Q3), -1.0), ((_Q1, _Q2, _Q3, _Q4), -1.0), ((_Q1, _Q3, _Q4), -1.0)]


def _zrot(qc: QuantumCircuit, qubits, phi: float) -> None:
    """exp(-i phi/2 Z_S) on the qubits S (CNOT ladder onto the last qubit)."""
    qubits = list(qubits)
    t = qubits[-1]
    for q in qubits[:-1]:
        qc.cx(q, t)
    qc.rz(phi, t)
    for q in reversed(qubits[:-1]):
        qc.cx(q, t)


def _diag_link(name: str, theta: float, clifford, zstrings, const: float) -> QuantumCircuit:
    """exp(-i theta K) with K = const + sum_S c_S (basis-changed Z_S): C^dag [prod_S exp(-i theta c_S Z_S)] C."""
    qc = QuantumCircuit(4, name=name)
    for nm, qs in clifford:
        getattr(qc, nm)(*qs)
    for qs, c in zstrings:
        _zrot(qc, qs, 2.0 * theta * c)
    for nm, qs in reversed(clifford):
        getattr(qc, nm)(*qs)
    qc.global_phase = -theta * const
    return qc


def link_UE(alpha: float) -> QuantumCircuit:
    """exp(-i alpha/2 K1) on one link (4 qubits)."""
    return _diag_link("link_UE", 0.5 * alpha, _E_CLIFFORD, _E_ZSTRINGS, _E_CONST)


def link_UK(kappa2: float) -> QuantumCircuit:
    """exp(-i kappa2 K2) on one link (4 qubits)."""
    return _diag_link("link_UK", kappa2, _K_CLIFFORD, _K_ZSTRINGS, 0.0)


def _layer(block: QuantumCircuit, name: str, with_outer: bool) -> QuantumCircuit:
    regs = [QuantumRegister(N_INNER, "d")] + ([QuantumRegister(N_OUTER, "o")] if with_outer else [])
    qc = QuantumCircuit(*regs, name=name)
    for l in range(12 if with_outer else 4):
        qc.compose(block, qubits=range(4 * l, 4 * l + 4), inplace=True)
    return qc


def build_UE(alpha: float, with_outer: bool = False) -> QuantumCircuit:
    qc = _layer(link_UE(alpha), "UE", with_outer)
    qc.metadata = {"kind": "UE", "alpha": alpha}
    return qc


def build_UK(kappa2: float, with_outer: bool = False) -> QuantumCircuit:
    qc = _layer(link_UK(kappa2), "UK", with_outer)
    qc.metadata = {"kind": "UK", "kappa2": kappa2}
    return qc


# ---------------------------------------------------------------------------------------------------------------------
# U_B
# ---------------------------------------------------------------------------------------------------------------------
F_QUBIT = 3                                   # f = q1^b
PARITY_QUBITS = (7, 11, 15)                   # q1^r, q1^t, q1^l  (hold p_r, p_t, p_l after the three CNOTs)
SPIN_QUBITS = (2, 6, 10, 14)                  # q2^b, q2^r, q2^t, q2^l  = spin bits 0..3 of the 16x16 blocks D_p


def _synth_clifford(M: np.ndarray):
    """(circuit, gamma): 4-qubit Clifford circuit with unitary e^{i gamma} M (qubit j = bit j)."""
    from qiskit.quantum_info import Clifford, Operator

    if np.allclose(M, np.eye(16)):
        return QuantumCircuit(4), 0.0
    qc = Clifford.from_matrix(M).to_circuit()
    U = Operator(qc).data
    ov = np.trace(M.conj().T @ U)
    gamma = float(np.angle(ov))
    err = float(np.linalg.norm(U - np.exp(1j * gamma) * M, 2))
    if err > 1e-9:
        raise RuntimeError(f"fixed unitary is not Clifford (deviation {err:.2e})")
    return qc, gamma


def _pauli(x: int, z: int) -> np.ndarray:
    X = np.array([[0, 1], [1, 0]], complex)
    Z = np.diag([1.0, -1.0]).astype(complex)
    m = np.eye(1, dtype=complex)
    for j in range(3, -1, -1):
        xj, zj = (x >> j) & 1, (z >> j) & 1
        f = 1j * X @ Z if (xj and zj) else X if xj else Z if zj else np.eye(2, dtype=complex)
        m = np.kron(m, f)
    return m


_PAULIS = [(x, z) for x in range(16) for z in range(16)]


def _symp(a, b) -> int:
    return (bin(a[0] & b[1]).count("1") + bin(a[1] & b[0]).count("1")) & 1


def _gf2_rank(vs) -> int:
    basis = []
    for v in vs:
        w = v
        for b in basis:
            w = min(w, w ^ b)
        if w:
            basis.append(w)
    return len(basis)


def _encoder(vecs, n_label: int):
    """Clifford M (16x16) with M|0,k> = vecs[k] exactly (k = label in the low n_label bits, syndrome in the high bits), or None.
    vecs: orthonormal stabiliser-code vectors forming a Pauli orbit of vecs[0] (up to sign): vecs[2^j] = +-Q_j vecs[0]."""
    r = len(vecs)
    n_syn = 4 - n_label
    P = sum(np.outer(v, v.conj()) for v in vecs)
    pm = {k: _pauli(*k) for k in _PAULIS}
    stab = [(k, e) for k in _PAULIS if k != (0, 0) for e in (1, -1) if np.allclose(e * pm[k] @ P, P)]
    if len(stab) != 16 // r - 1:
        return None
    gens = []
    for k, e in stab:
        if _gf2_rank([g[0][0] | (g[0][1] << 4) for g in gens] + [k[0] | (k[1] << 4)]) > len(gens):
            gens.append((k, e))
    stabset = {k for k, _ in stab} | {(0, 0)}
    v0 = vecs[0]
    qs = []
    for j in range(n_label):
        pick = None
        for k in _PAULIS:
            if k in stabset or any(_symp(k, g[0]) for g in gens) or any(_symp(k, q[0]) for q in qs):
                continue
            for e in (1, -1):
                if np.allclose(e * pm[k] @ v0, vecs[1 << j]):
                    pick = (k, e)
                    break
            if pick:
                break
        if pick is None:
            return None
        qs.append(pick)
    ts = []
    for i in range(n_syn):
        for k in _PAULIS:
            if all(_symp(k, gens[j][0]) == (1 if j == i else 0) for j in range(n_syn)) and \
                    all(_symp(k, q[0]) == 0 for q in qs) and all(_symp(k, t) == 0 for t in ts):
                ts.append(k)
                break
        else:
            return None
    M = np.zeros((16, 16), complex)
    for s in range(2 ** n_syn):
        for kk in range(r):
            v = v0.copy()
            for j in range(n_label):
                if (kk >> j) & 1:
                    v = qs[j][1] * pm[qs[j][0]] @ v
            ov = np.vdot(vecs[kk], v)
            if abs(abs(ov) - 1) > 1e-9:
                return None
            v = v * np.conj(ov) / abs(ov)
            for i in range(n_syn):
                if (s >> i) & 1:
                    v = pm[ts[i]] @ v
            M[:, (s << n_label) | kk] = v
    if not np.allclose(M.conj().T @ M, np.eye(16), atol=1e-9):
        return None
    return M


@lru_cache(maxsize=1)
def _sector_data():
    """{p: dict(rank, sigma, B (circuit, gamma), A (circuit, gamma), Bdag, Adag)} from the singular value decomposition of D_p.
    D_p = A_p Sigma B_p^dag with Sigma = sigma * diag(1_rank, 0); B|0,k>, A|0,k> are the Pauli-orbit bases of the right/left
    singular spaces, so that B^dag u_k = |k> and A^dag D_p B = sigma on the labels."""
    import itertools

    from su2plaq.fuzzy.plaquette import block_structure

    out = {}
    for p, blk in block_structure().items():
        D, sv = blk["D"], blk["sing_vals"]
        rank = int(np.sum(sv > 1e-9))
        sigma = float(sv[0])
        if rank == 16:                                   # D unitary: B = 1, A = D
            MB, MA = np.eye(16, dtype=complex), np.asarray(D, dtype=complex) / sigma
        else:
            n_label = {4: 2, 1: 0}.get(rank)
            if n_label is None:
                raise RuntimeError(f"sector {p}: unexpected rank {rank}")
            Pu = D.conj().T @ D / sigma ** 2
            us = []
            for c in range(16):
                v = Pu[:, c]
                n = np.linalg.norm(v)
                if n > 1e-9 and all(abs(np.vdot(v / n, w)) < 1e-9 for w in us):
                    us.append(v / n)
            if len(us) != rank:
                raise RuntimeError(f"sector {p}: could not build {rank} orthogonal right-singular vectors")
            MB = MA = None
            for perm in itertools.permutations(range(rank)):
                u = [us[i] for i in perm]
                MB = _encoder(u, n_label)
                if MB is None:
                    continue
                MA = _encoder([D @ x / sigma for x in u], n_label)
                if MA is not None:
                    break
                MB = None
            if MB is None:
                raise RuntimeError(f"sector {p}: fixed unitaries are not Clifford")
        out[p] = {"rank": rank, "sigma": sigma, "B": _synth_clifford(MB), "A": _synth_clifford(MA),
                  "Bdag": _synth_clifford(MB.conj().T), "Adag": _synth_clifford(MA.conj().T)}
    return out


def _emit_controlled(qc: QuantumCircuit, ctrl: int, circ: QuantumCircuit, gamma: float) -> None:
    """Append `circ` (4 local qubits -> SPIN_QUBITS) controlled on qubit `ctrl`; the global phase e^{i gamma} of circ is removed."""
    for inst in circ.data:
        nm = inst.operation.name
        qs = [SPIN_QUBITS[circ.find_bit(q).index] for q in inst.qubits]
        if nm == "h":
            qc.ch(ctrl, qs[0])
        elif nm == "x":
            qc.cx(ctrl, qs[0])
        elif nm == "z":
            qc.cz(ctrl, qs[0])
        elif nm == "s":
            qc.cp(np.pi / 2, ctrl, qs[0])
        elif nm == "sdg":
            qc.cp(-np.pi / 2, ctrl, qs[0])
        elif nm == "y":                                  # Y = S X S^dag
            qc.sdg(qs[0])
            qc.cx(ctrl, qs[0])
            qc.s(qs[0])
        elif nm == "cx":
            qc.ccx(ctrl, qs[0], qs[1])
        elif nm == "cz":
            qc.ccz(ctrl, qs[0], qs[1])
        elif nm == "swap":                               # controlled swap = cx . ccx . cx
            qc.cx(qs[1], qs[0])
            qc.ccx(ctrl, qs[0], qs[1])
            qc.cx(qs[1], qs[0])
        else:
            raise RuntimeError(f"no controlled form for gate {nm}")
    if abs(gamma) > 1e-12:
        qc.p(-gamma, ctrl)


def _and_into(qc: QuantumCircuit, ctrls, target: int, scratch) -> None:
    """target ^= AND of the control qubits (all positive polarity), ladder through `scratch` qubits (left clean)."""
    ctrls = list(ctrls)
    if len(ctrls) == 1:
        qc.cx(ctrls[0], target)
    elif len(ctrls) == 2:
        qc.ccx(ctrls[0], ctrls[1], target)
    else:
        need = len(ctrls) - 2
        sc = list(scratch)[:need]
        if len(sc) < need:
            raise ValueError("not enough scratch qubits")
        qc.ccx(ctrls[0], ctrls[1], sc[0])
        for i in range(1, need):
            qc.ccx(sc[i - 1], ctrls[i + 1], sc[i])
        qc.ccx(sc[-1], ctrls[-1], target)
        for i in range(need - 1, 0, -1):
            qc.ccx(sc[i - 1], ctrls[i + 1], sc[i])
        qc.ccx(ctrls[0], ctrls[1], sc[0])


def build_UB(beta: float) -> QuantumCircuit:
    """exp(+2 i beta square) on the row qubits {4l+2, 4l+3} of register 'd' (16 qubits); ancillas 'w' (7), clean on exit; no
    column qubit is touched."""
    data = _sector_data()
    d = QuantumRegister(N_INNER, "d")
    w = QuantumRegister(7, "w")
    qc = QuantumCircuit(d, w, name="UB")
    a, c0, c1, t = (N_INNER + i for i in range(4))
    scratch = [N_INNER + 4 + i for i in range(3)]
    f = F_QUBIT
    for q in PARITY_QUBITS:                                           # parity frame
        qc.cx(f, q)
    for p in range(8):
        sec = data[p]
        pb = [(p >> k) & 1 for k in range(3)]
        flip = [q for q, b in zip(PARITY_QUBITS, pb) if b == 0]
        rank = sec["rank"]
        # flag a_p = [parities == p]
        for q in flip:
            qc.x(q)
        _and_into(qc, PARITY_QUBITS, a, scratch)
        for q in flip:
            qc.x(q)

        def flags(on: bool):
            qc.ccx(a, f, c1)
            qc.x(f)
            qc.ccx(a, f, c0)
            qc.x(f)

        def fixed(side_b: str, side_a: str):
            flags(True)
            if len(sec[side_b][0].data) > 0:
                _emit_controlled(qc, c0, *sec[side_b])
            if len(sec[side_a][0].data) > 0 or abs(sec[side_a][1]) > 1e-12:
                _emit_controlled(qc, c1, *sec[side_a])
            flags(False)

        fixed("Bdag", "Adag")
        # rotation R_x(-4 beta sigma) on f, controlled on a_p and on the singular label being one with sigma != 0
        if rank == 16:
            qc.crx(-4.0 * beta * sec["sigma"], a, f)
        else:
            syn = list(SPIN_QUBITS[2:]) if rank == 4 else list(SPIN_QUBITS)
            for q in syn:
                qc.x(q)
            _and_into(qc, [a] + syn, t, scratch)
            for q in syn:
                qc.x(q)
            qc.crx(-4.0 * beta * sec["sigma"], t, f)
            for q in syn:
                qc.x(q)
            _and_into(qc, [a] + syn, t, scratch)
            for q in syn:
                qc.x(q)
        fixed("B", "A")
        for q in flip:
            qc.x(q)
        _and_into(qc, PARITY_QUBITS, a, scratch)
        for q in flip:
            qc.x(q)
    for q in PARITY_QUBITS:
        qc.cx(f, q)
    qc.metadata = {"kind": "UB", "beta": beta}
    return qc


def build_step(alpha: float, beta: float, kappa2: float | None = None, order: int = 1, with_outer: bool = False) -> QuantumCircuit:
    """One Trotter step on registers d (16), [o (32)], w (7 clean ancillas).

    order 1: U_E(alpha), U_K(kappa2), U_B(beta) in circuit order (= U_B U_K U_E as an operator);
    order 2: U_E(alpha/2) U_K(kappa2/2) U_B(beta) U_K(kappa2/2) U_E(alpha/2).  kappa2=None -> r = 1 (kappa2 = alpha/2).
    with_outer adds, once at the full angles, one link_UE(alpha) and one link_UK(kappa2) block on every outer link (they commute with
    everything else).  ``metadata['layers']`` lists (kind, first instruction, last+1) for the layered verification."""
    if order not in (1, 2):
        raise ValueError(f"order must be 1 or 2, got {order}")
    if kappa2 is None:
        kappa2 = 0.5 * alpha
    regs = [QuantumRegister(N_INNER, "d")] + ([QuantumRegister(N_OUTER, "o")] if with_outer else []) + [QuantumRegister(7, "w")]
    qc = QuantumCircuit(*regs, name="step")
    n_anc0 = N_INNER + (N_OUTER if with_outer else 0)
    layers = []

    def add(kind, circ, qubits):
        a = len(qc.data)
        qc.compose(circ, qubits=list(qubits), inplace=True)
        layers.append((kind, a, len(qc.data)))

    inner = list(range(N_INNER))
    if order == 1:
        seq = [("UE", alpha), ("UK", kappa2), ("UB", beta)]
    else:
        seq = [("UE", alpha / 2), ("UK", kappa2 / 2), ("UB", beta), ("UK", kappa2 / 2), ("UE", alpha / 2)]
    for kind, x in seq:
        if kind == "UE":
            add("UE", build_UE(x), inner)
        elif kind == "UK":
            add("UK", build_UK(x), inner)
        else:
            add("UB", build_UB(x), inner + list(range(n_anc0, n_anc0 + 7)))
    if with_outer:
        for l in range(4, 12):
            add("outer", link_UE(alpha), range(4 * l, 4 * l + 4))
            add("outer", link_UK(kappa2), range(4 * l, 4 * l + 4))
    qc.metadata = {"kind": "step", "alpha": alpha, "beta": beta, "kappa2": kappa2, "order": order, "layers": layers}
    return qc
