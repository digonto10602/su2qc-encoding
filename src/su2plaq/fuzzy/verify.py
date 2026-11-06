"""Verification adapter for the fuzzy circuits (M9; METHODS-fuzzy F6).

The laptop evaluator (`su2plaq.evaluate.evaluator.evaluate`) is reused unchanged through `FuzzyBlockEncoding`: an encoding in which
every one of the 2^n data codes is a physical state (``n_outer = 0``, basis states with unit amplitude).  Because the physical
set is the complete computational basis, "equal to the target on every physical state" is equality of the full 2^n x 2^n
unitary (one global phase), the ancillas (every qubit that is not a data qubit) must return to |0>, and no outer qubit exists.
`gauss=False`: the fuzzy Gauss law is checked separately (`gauss_residual_outputs`), the evaluator's Gauss branch is KS specific.
"""
from __future__ import annotations

import numpy as np

from su2plaq.encodings.base import EncodedBasis, Layout
from su2plaq.evaluate.evaluator import Verdict, evaluate

ROW_QUBITS = tuple(q for l in range(4) for q in (4 * l + 2, 4 * l + 3))       # data bit 2l <- qubit 4l+2 (q2), bit 2l+1 <- 4l+3 (q1)
COLUMN_QUBITS = tuple(q for l in range(4) for q in (4 * l, 4 * l + 1))        # q4 -> 4l, q3 -> 4l+1


class FuzzyBlockEncoding:
    """All 2^n_data codes physical; data qubit i of the canonical frame is circuit qubit ``data_qubits[i]``
    (default: the qubits of register 'd' if present, else 0..n_data-1); every other qubit is an ancilla."""

    name = "fuzzy_block"
    n_outer = 0
    is_basis_encoding = True
    basis = None

    def __init__(self, n_data: int, data_qubits=None):
        self.n_data = int(n_data)
        self.data_qubits = None if data_qubits is None else [int(q) for q in data_qubits]
        if self.data_qubits is not None and len(self.data_qubits) != self.n_data:
            raise ValueError(f"data_qubits must have {self.n_data} entries")
        self.registers = {"d": list(range(self.n_data))}

    def inner_codes(self) -> np.ndarray:
        return np.arange(2 ** self.n_data, dtype=np.int64)

    def decode(self, code: int):
        return int(code)

    def physical_vectors(self) -> EncodedBasis:
        n = 2 ** self.n_data
        return EncodedBasis([np.array([k], dtype=np.int64) for k in range(n)],
                            [np.ones(1, dtype=np.complex128) for _ in range(n)], self.n_data, 0)

    def target(self, kind, alpha, beta, order=1):
        raise ValueError("FuzzyBlockEncoding has no named targets: pass the unitary to the verification function")

    def layout_of(self, qc) -> Layout:
        n = qc.num_qubits
        if self.data_qubits is not None:
            data = list(self.data_qubits)
        else:
            regs = {reg.name: [qc.find_bit(q).index for q in reg] for reg in qc.qregs}
            data = regs["d"] if "d" in regs else list(range(self.n_data))
        if len(data) != self.n_data or len(set(data)) != self.n_data or max(data) >= n:
            raise ValueError(f"circuit with {n} qubits has no data layout {data}")
        used = set(data)
        return Layout(data=list(data), outer=[], ancilla=[q for q in range(n) if q not in used])

    def describe(self) -> str:
        return f"fuzzy block adapter: {self.n_data} data qubits, all {2 ** self.n_data} codes physical, no outer register"

    def import_map(self, source: str):
        return "n_a"


def _touched(qc) -> set[int]:
    return {qc.find_bit(q).index for inst in qc.data for q in inst.qubits}


def verify_link(qc, V16, tol_err: float = 1e-10) -> Verdict:
    """Full 16x16 unitary check of a one-link circuit (data = qubits 0..3 = (q4,q3,q2,q1); extra qubits are clean ancillas)."""
    enc = FuzzyBlockEncoding(4, data_qubits=[0, 1, 2, 3])
    return evaluate(qc, enc, np.asarray(V16, dtype=np.complex128), tol_err=tol_err, gauss=False, method="physical")


def verify_plaquette(qc, V256, tol_err: float = 1e-10) -> Verdict:
    """256x256 row-block check: data = the 8 row qubits {4l+2, 4l+3} (index sum_l (2 q1 + q2) 4^l), every other qubit must stay
    |0> (ancillas).  ``extra['touches_column']`` is False iff no gate acts on a column qubit {4l, 4l+1}."""
    enc = FuzzyBlockEncoding(8, data_qubits=ROW_QUBITS)
    v = evaluate(qc, enc, np.asarray(V256, dtype=np.complex128), tol_err=tol_err, gauss=False, method="physical")
    v.extra["touches_column"] = bool(_touched(qc) & set(COLUMN_QUBITS))
    return v


# ---------------------------------------------------------------------------------------------------------------------
# Sampled composition check on the 16 inner data qubits
# ---------------------------------------------------------------------------------------------------------------------
def _inner_part(qc):
    """Circuit restricted to register 'd' and the qubits that are neither 'd' nor 'o' (ancillas); gates acting only on the
    outer register 'o' (the outer-link kinetic blocks, which commute with everything) are dropped.  Returns (circuit,
    data-qubit list, position map old qubit -> new qubit)."""
    from qiskit import QuantumCircuit

    regs = {reg.name: [qc.find_bit(q).index for q in reg] for reg in qc.qregs}
    data = regs.get("d", list(range(16)))
    outer = set(regs.get("o", []))
    keep = [q for q in range(qc.num_qubits) if q not in outer]
    pos = {q: i for i, q in enumerate(keep)}
    sub = QuantumCircuit(len(keep), global_phase=qc.global_phase)
    for inst in qc.data:
        qs = [qc.find_bit(q).index for q in inst.qubits]
        o = [q in outer for q in qs]
        if all(o):
            continue
        if any(o):
            raise ValueError("a gate mixes inner and outer qubits")
        sub.append(inst.operation, [pos[q] for q in qs])
    return sub, [pos[q] for q in data], pos


def _run_dense(sub, psi_list, n):
    """Fallback for circuits without layer metadata: Aer statevector for each input vector (length 2^n).  Aer chops amplitudes
    below its zero threshold (1e-10 by default), so this path is only accurate to ~1e-8; the global phase of `sub` is ignored."""
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator

    sim = AerSimulator(method="statevector", max_parallel_threads=1, zero_threshold=1e-300)
    base = transpile(sub, sim, optimization_level=0, qubits_initially_zero=False)
    outs = []
    for psi in psi_list:
        c = QuantumCircuit(n)
        c.set_statevector(psi)
        c.compose(base, inplace=True)
        c.save_statevector(label="sv")
        outs.append(np.asarray(sim.run(c).result().data()["sv"].data))
    return outs


def _embed_index(data_pos, n_total=None):
    ar = np.arange(65536)
    idx = np.zeros(65536, dtype=np.int64)
    for i, q in enumerate(data_pos):
        idx |= ((ar >> i) & 1) << q
    return idx


def _row_keys(data_pos=None):
    """Computational-basis keys (inner qubits 4l+2, 4l+3) of the 256 row codes sum_l (2 q1 + q2) 4^l."""
    r = np.arange(256, dtype=np.int64)
    key = np.zeros(256, dtype=np.int64)
    for l in range(4):
        key |= ((r >> (2 * l)) & 1) << (4 * l + 2)
        key |= ((r >> (2 * l + 1)) & 1) << (4 * l + 3)
    return key


class LayerMetadataError(ValueError):
    """``qc.metadata['layers']`` does not describe the circuit (partition, register or outer-link violation)."""


_OUTER_FIRST, _N_OUTER_LINKS = 16, 8
_LAYER_KINDS = ("UE", "UK", "UB", "outer")


def _phase_error(M, T) -> float:
    """||M - e^{i phi} T||_2 for the best global phase phi."""
    tr = np.vdot(T, M)
    ph = tr / abs(tr) if abs(tr) > 1e-300 else 1.0
    return float(np.linalg.norm(M - ph * T, 2))


def validate_layers(qc, layers, alpha=None, kappa2=None, tol: float = 1e-10) -> list:
    """Check that ``layers`` = [(kind, i0, i1)] describes `qc` and return it as a list of (kind, i0, i1) int tuples.

    1. The ranges, in the listed order, partition ``range(len(qc.data))`` exactly (first i0 = 0, each i0 = previous i1, last i1 =
       len(qc.data); no gap, no overlap, no instruction outside a range) and every kind is one of UE, UK, UB, outer.
    2. Every instruction of an 'outer' range acts only on register 'o' (which must be qubits 16..47) and within one outer link
       (nibble); one range = one link.  If `alpha` and `kappa2` are given, every outer link must appear and the product of all its
       'outer' ranges must equal the one-link target UK_link(kappa2) UE_link(alpha) (K1, K2 commute) as a 16x16 operator up to a
       phase (error <= tol); otherwise only the structure is checked (`_outer_block_commutator` always checks the blocks against the
       gauge generators).
    3. UE/UK ranges: every gate inside one inner link (qubits 0..15, one nibble); UB ranges: no gate on register 'o' (the column
       check is made when the plaquette layer is built).
    Any violation raises `LayerMetadataError`; nothing is repaired or skipped."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator

    n = len(qc.data)
    try:
        lay = [(str(k), int(a), int(b)) for k, a, b in layers]
    except (TypeError, ValueError) as exc:
        raise LayerMetadataError(f"malformed layer list: {exc}") from exc
    pos = 0
    for kind, a, b in lay:
        if kind not in _LAYER_KINDS:
            raise LayerMetadataError(f"unknown layer kind {kind!r}")
        if a != pos or b < a:
            raise LayerMetadataError(f"layer ({kind}, {a}, {b}) does not continue the partition at instruction {pos}")
        pos = b
    if pos != n:
        raise LayerMetadataError(f"layers cover instructions [0, {pos}) of a circuit with {n} instructions")

    regs = {reg.name: [qc.find_bit(q).index for q in reg] for reg in qc.qregs}
    outer = regs.get("o", [])
    if outer and outer != list(range(_OUTER_FIRST, _OUTER_FIRST + 4 * _N_OUTER_LINKS)):
        raise LayerMetadataError("register 'o' must be qubits 16..47")
    oset = set(outer)
    per_link: dict[int, QuantumCircuit] = {}
    for kind, a, b in lay:
        if kind == "outer":
            link = None
            for inst in qc.data[a:b]:
                qs = [qc.find_bit(q).index for q in inst.qubits]
                if not qs or not all(q in oset for q in qs):
                    raise LayerMetadataError(f"outer range ({a}, {b}): gate {inst.operation.name} on {qs} is not inside register 'o'")
                this = (qs[0] - _OUTER_FIRST) // 4
                if any((q - _OUTER_FIRST) // 4 != this for q in qs) or (link is not None and this != link):
                    raise LayerMetadataError(f"outer range ({a}, {b}) spans more than one outer link")
                link = this
                per_link.setdefault(this, QuantumCircuit(4)).append(inst.operation, [(q - _OUTER_FIRST) % 4 for q in qs])
        elif kind in ("UE", "UK"):
            for inst in qc.data[a:b]:
                qs = [qc.find_bit(q).index for q in inst.qubits]
                if not qs or max(qs) > 15 or any(q // 4 != qs[0] // 4 for q in qs):
                    raise LayerMetadataError(f"layer {kind} ({a}, {b}): gate {inst.operation.name} on {qs} is not inside one inner link")
        else:                                                                    # UB
            for inst in qc.data[a:b]:
                qs = [qc.find_bit(q).index for q in inst.qubits]
                if any(q in oset for q in qs):
                    raise LayerMetadataError(f"layer UB ({a}, {b}): gate {inst.operation.name} on {qs} touches register 'o'")
    if alpha is not None and kappa2 is not None:
        from su2plaq.fuzzy import targets as tg

        if outer:
            missing = sorted(set(range(_N_OUTER_LINKS)) - set(per_link))
            if missing:
                raise LayerMetadataError(f"outer links {missing} have no 'outer' range")
        target = tg.UK_link(kappa2) @ tg.UE_link(alpha)
        for link, blk in sorted(per_link.items()):
            e = _phase_error(Operator(blk).data, target)
            if e > tol:
                raise LayerMetadataError(f"outer link {link}: block differs from UK(kappa2) UE(alpha) by {e:.2e} (> {tol:g})")
    return lay


class InnerAction:
    """The action of a step circuit on the 16 inner qubits as a function on 2^16 vectors, plus the ancilla leakage.

    Circuits built by `circuits.fuzzy.build_step` carry ``metadata['layers']`` = [(kind, i0, i1)] (instruction ranges).  Each layer
    is turned into its complete operator from its own gates: kinetic layers into the four 16x16 link blocks (Operator of the 4-qubit
    gate groups, nothing else may be touched), the plaquette layer into its complete 256x256 row-basis block by the exact sparse
    simulator (ancillas |0>; weight left outside the row space is the leak).  The layers are then applied in circuit order to dense
    vectors (blocks certified on a complete basis, composition sampled).  `validate_layers` first checks that the metadata partitions the
    instruction list exactly and that outer ranges / kinetic ranges touch only what they claim (`LayerMetadataError` otherwise: a
    stale or tampered metadata fails loudly).  Circuits without metadata are simulated densely with Aer."""

    def __init__(self, qc, alpha=None, kappa2=None):
        self.qc = qc
        self.alpha, self.kappa2 = alpha, kappa2                  # given: the outer blocks are checked against their targets
        layers = (qc.metadata or {}).get("layers")
        self.ops = []                          # ("kin", [M0..M3]) or ("ub", M256)
        self.leak = 0.0
        self.mode = "layers" if layers else "aer"
        if layers:
            self._build_layers(layers)
        else:
            self.sub, self.data_pos, _ = _inner_part(qc)
            self.idx = _embed_index(self.data_pos)

    def _build_layers(self, layers):
        from qiskit import QuantumCircuit
        from qiskit.quantum_info import Operator

        from su2plaq.evaluate import sparse_sim as ss

        qc = self.qc
        regs = {reg.name: [qc.find_bit(q).index for q in reg] for reg in qc.qregs}
        if regs.get("d", list(range(16))) != list(range(16)):
            raise ValueError("register 'd' must be the first 16 qubits")
        layers = validate_layers(qc, layers, self.alpha, self.kappa2)     # raises LayerMetadataError: no silent pass
        sub, _, pos = _inner_part(qc)
        for kind, a, b in layers:
            if kind == "outer":
                continue
            ins = qc.data[a:b]
            if kind in ("UE", "UK"):
                blocks = [QuantumCircuit(4) for _ in range(4)]
                for inst in ins:
                    qs = [qc.find_bit(q).index for q in inst.qubits]
                    link = qs[0] // 4
                    if link > 3 or any(q // 4 != link for q in qs):
                        raise ValueError(f"layer {kind}: gate {inst.operation.name} on {qs} is not inside one inner link")
                    blocks[link].append(inst.operation, [q % 4 for q in qs])
                self.ops.append(("kin", [Operator(bl).data for bl in blocks]))
            elif kind == "UB":
                layer = QuantumCircuit(sub.num_qubits)
                for inst in ins:
                    qs = [qc.find_bit(q).index for q in inst.qubits]
                    layer.append(inst.operation, [pos[q] for q in qs])
                if _touched(layer) & set(COLUMN_QUBITS):
                    raise ValueError("the plaquette layer touches a column qubit")
                keys = _row_keys()
                bt = ss.run_batch(layer, keys, cap=20_000_000)
                M = np.zeros((256, 256), dtype=np.complex128)
                rowmask = np.int64(sum(3 << (4 * l + 2) for l in range(4)))
                inside = (bt.keys & ~rowmask) == 0
                kk = bt.keys[inside]
                rows = sum(((kk >> (4 * l + 2)) & 3) << (2 * l) for l in range(4))
                np.add.at(M, (rows, bt.cols[inside]), bt.amps[inside])
                w_out = np.bincount(bt.cols[~inside], weights=np.abs(bt.amps[~inside]) ** 2, minlength=256)
                self.leak = max(self.leak, float(np.sqrt(w_out.max())))
                self.ops.append(("ub", M))
            else:
                raise ValueError(f"unknown layer kind {kind!r}")

    def __call__(self, vecs):
        """vecs: list of 2^16 vectors -> list of outputs (data part only)."""
        if self.mode == "aer":
            n = self.sub.num_qubits
            embedded = []
            for v in vecs:
                e = np.zeros(2 ** n, dtype=np.complex128)
                e[self.idx] = v
                embedded.append(e)
            outs = _run_dense(self.sub, embedded, n)
            res = []
            for o in outs:
                got = o[self.idx]
                self.leak = max(self.leak, float(np.sqrt(max(np.linalg.norm(o) ** 2 - np.linalg.norm(got) ** 2, 0.0))))
                res.append(got)
            return res
        from su2plaq.fuzzy.targets import _apply_kinetic, _apply_ub

        out = []
        for v in vecs:
            for kind, data in self.ops:
                if kind == "kin":
                    t = v.reshape(16, 16, 16, 16)          # axes: link 3, 2, 1, 0
                    for l in range(4):
                        ax = 3 - l
                        t = np.moveaxis(np.tensordot(data[l], t, axes=([1], [ax])), 0, ax)
                    v = t.reshape(-1)
                else:
                    v = _apply_ub(v, data)
            out.append(v)
        return out


def _sample_inputs(n_random: int, n_phys: int, seed: int):
    """Seeded inputs: n_random random product states and the heaviest outer-pattern inner component of n_phys physical states."""
    from su2plaq.fuzzy.gauss import sample_physical_states

    rng = np.random.default_rng(seed)
    inputs = []
    for _ in range(n_random):
        v = np.ones(1, dtype=np.complex128)
        for _q in range(16):                      # qubit 0 least significant: kron(new, old)
            a = rng.normal(size=2) + 1j * rng.normal(size=2)
            v = np.kron(a / np.linalg.norm(a), v)
        inputs.append(v)
    states = sample_physical_states(n_phys, seed) if n_phys > 0 else []
    for keys, amps in states:
        keys = np.asarray(keys, dtype=np.int64)
        amps = np.asarray(amps, dtype=np.complex128)
        uo, inv = np.unique(keys >> 16, return_inverse=True)
        w = np.bincount(inv, weights=np.abs(amps) ** 2)
        sel = inv == int(np.argmax(w))
        v = np.zeros(65536, dtype=np.complex128)
        np.add.at(v, keys[sel] & 0xFFFF, amps[sel])
        inputs.append(v / np.linalg.norm(v))
    return inputs, states


def verify_step_samples(qc, alpha, beta, kappa2, order, n_random: int = 32, n_phys: int = 8, seed: int = 20261104) -> dict:
    """Sampled composition check of the 16-inner-qubit part of a step circuit against `targets.apply_step` on `n_random` seeded
    random product states and the inner components of `n_phys` seeded physical states (one global phase for all inputs; ancilla
    leakage added to the error).  Returns {'err', 'gauss' (residual of the circuit's outputs on the seeded 48-qubit physical
    states), 'n_inputs', 'leak', 'mode'}; see `InnerAction` for what is certified and what is sampled."""
    from su2plaq.fuzzy.targets import apply_step

    act = InnerAction(qc, alpha, kappa2)
    inputs, states = _sample_inputs(n_random, n_phys, seed)
    outs = act(inputs)
    refs = [apply_step(v, alpha, beta, kappa2, order) for v in inputs]
    tr = sum(np.vdot(r, o) for r, o in zip(refs, outs))
    ph = tr / abs(tr) if abs(tr) > 1e-300 else 1.0
    err = max(float(np.linalg.norm(o - ph * r)) for r, o in zip(refs, outs)) + act.leak
    gres = gauss_residual_outputs(qc, states, _act=act) if states else 0.0
    return {"err": err, "gauss": gres, "n_inputs": len(inputs), "leak": act.leak, "mode": act.mode}


def _apply_link_coo(M16, nib: int, keys: np.ndarray, amps: np.ndarray):
    """Apply a 16x16 operator to nibble `nib` (bits 4 nib..4 nib+3) of a COO vector; duplicate keys are summed."""
    shift = 4 * nib
    loc = (keys >> shift) & 15
    rest = keys & ~(np.int64(15) << shift)
    ks, as_ = [], []
    for j in range(16):
        sel = loc == j
        nz = np.flatnonzero(np.abs(M16[:, j]) > 0)
        if not sel.any() or len(nz) == 0:
            continue
        ks.append((rest[sel][:, None] | (nz[None, :].astype(np.int64) << shift)).ravel())
        as_.append((amps[sel][:, None] * M16[nz, j][None, :]).ravel())
    if not ks:
        return np.zeros(0, np.int64), np.zeros(0, complex)
    k, a = np.concatenate(ks), np.concatenate(as_)
    uk, inv = np.unique(k, return_inverse=True)
    ua = np.zeros(len(uk), complex)
    np.add.at(ua, inv, a)
    return uk, ua


def _coo_dot(k1, a1, k2, a2) -> complex:
    """<v1|v2> for two COO vectors with unique sorted keys."""
    common, i1, i2 = np.intersect1d(k1, k2, assume_unique=True, return_indices=True)
    return complex(np.vdot(a1[i1], a2[i2])) if len(common) else 0j


def _outer_block_commutator(qc) -> float:
    """max over the outer-link gate blocks of ||[U_block, calT_{L,R}^A]|| (the blocks are the 4-qubit groups of gates on 'o')."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator

    from su2plaq.fuzzy import link as lk

    regs = {reg.name: [qc.find_bit(q).index for q in reg] for reg in qc.qregs}
    outer = regs.get("o", [])
    if not outer:
        return 0.0
    groups: dict[int, QuantumCircuit] = {}
    for inst in qc.data:
        qs = [qc.find_bit(q).index for q in inst.qubits]
        if not all(q in set(outer) for q in qs):
            continue
        link = (qs[0] - outer[0]) // 4
        if any((q - outer[0]) // 4 != link for q in qs):
            raise ValueError("an outer gate spans two links")
        g = groups.setdefault(link, QuantumCircuit(4))
        g.append(inst.operation, [(q - outer[0]) % 4 for q in qs])
    worst = 0.0
    for g in groups.values():
        U = Operator(g).data
        for A in range(3):
            for T in (lk.calT_L(A), lk.calT_R(A)):
                worst = max(worst, float(np.linalg.norm(U @ T - T @ U, 2)))
    return worst


def gauss_residual_outputs(qc, states, _act=None, alpha=None, kappa2=None) -> float:
    """Gauss residual max_{c,A} ||G^A_c U psi|| over 48-qubit physical COO states `states = [(keys, amps)]`.

    Exact reduction (no 2^48 output is formed): the outer-link blocks U_out (gates on register 'o') are unitary, act on qubits
    disjoint from the inner part U_in and G U psi = U_out G U_in psi + [G_out, U_out] U_in psi, so
    ||G U psi|| <= ||G U_in psi|| + max ||[U_out-block, calT]|| (the second term is evaluated from the gates, ~1e-16).
    psi = sum_r phi_r (x) c_r (SVD of the inner-vs-outer coefficient matrix; the rank of the samples is <= 48); the inner part is
    applied to the dense 2^16 vectors phi_r (+ ancillas, Aer statevector, ancilla leakage discarded) and
    G U_in psi = sum_r (G_in phi'_r) (x) c_r + phi'_r (x) (G_out c_r) is contracted through small Gram matrices."""
    import scipy.sparse as sp

    from su2plaq.fuzzy import gauss as gz
    from su2plaq.fuzzy import link as lk

    act = _act or InnerAction(qc, alpha, kappa2)
    comm = _outer_block_commutator(qc)
    worst = 0.0
    for keys, amps in states:
        keys = np.asarray(keys, dtype=np.int64)
        amps = np.asarray(amps, dtype=np.complex128)
        uo, io = np.unique(keys >> 16, return_inverse=True)
        ui, ii = np.unique(keys & 0xFFFF, return_inverse=True)
        M = sp.csr_matrix((amps, (ii, io)), shape=(len(ui), len(uo))).toarray()
        Uu, S, Vh = np.linalg.svd(M, full_matrices=False)
        keep = S > 1e-12 * S[0]
        Uu, S, Vh = Uu[:, keep], S[keep], Vh[keep]
        rank = len(S)
        phis = []
        for r in range(rank):
            v = np.zeros(65536, dtype=np.complex128)
            v[ui] = Uu[:, r]
            phis.append(v)
        P = np.array(act(phis))                                                # (rank, 65536) = phi'_r
        cs = S[:, None] * Vh                                                   # c_r over outer patterns uo
        for c in range(4):
            ends = gz.CORNER_ENDS[c]
            for A in range(3):
                X = np.zeros_like(P)                                           # G_in phi'_r
                for ell, role in ends:
                    if ell >= 4:
                        continue
                    T = lk.calT_L(A) if role == "out" else lk.calT_R(A)
                    t = P.reshape(rank, 16, 16, 16, 16)
                    ax = 1 + (3 - ell)
                    X += np.moveaxis(np.tensordot(T, t, axes=([1], [ax])), 0, ax).reshape(rank, 65536)
                Y = []                                                         # G_out c_r as COO vectors over the outer key
                for r in range(rank):
                    ky, ay = np.zeros(0, np.int64), np.zeros(0, complex)
                    for ell, role in ends:
                        if ell < 4:
                            continue
                        T = lk.calT_L(A) if role == "out" else lk.calT_R(A)
                        k2, a2 = _apply_link_coo(T, ell - 4, uo, cs[r])
                        ky = np.concatenate([ky, k2])
                        ay = np.concatenate([ay, a2])
                    if len(ky):
                        u2, inv = np.unique(ky, return_inverse=True)
                        a3 = np.zeros(len(u2), complex)
                        np.add.at(a3, inv, ay)
                        ky, ay = u2, a3
                    Y.append((ky, ay))
                # G U_in psi = sum_r X_r (x) c_r + phi'_r (x) Y_r with X_r, phi'_r in span(Q) (orthonormal Q from a QR of the stacked
                # vectors): the norm is the Frobenius norm of Z = sum_r a_r c_r^T + b_r Y_r^T (no squared-norm cancellation)
                Q, R = np.linalg.qr(np.concatenate([X, P], axis=0).T)
                a, b = R[:, :rank], R[:, rank:]
                union = np.unique(np.concatenate([uo] + [y[0] for y in Y]))
                Z = np.zeros((R.shape[0], len(union)), dtype=np.complex128)
                Z[:, np.searchsorted(union, uo)] += a @ cs
                for r in range(rank):
                    if len(Y[r][0]):
                        Z[:, np.searchsorted(union, Y[r][0])] += np.outer(b[:, r], Y[r][1])
                worst = max(worst, float(np.linalg.norm(Z)))
    return worst + comm
