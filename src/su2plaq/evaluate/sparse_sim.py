"""Batched sparse (COO) circuit simulator (prompts/002 §2.7, docs/METHODS.md §6).

All inputs (computational basis integers, ancillas 0) are simulated at once on the state
(keys int64, cols int32 = input index, amps complex128).  Gates are translated to SIM_BASIS at
level 0; permutation gates (x, cx, swap, ccx) rewrite keys, diagonal gates (z, s, sdg, t, tdg, rz, p, cz,
cp, ccz) multiply amplitudes, branching gates (h, sx, u, unitary) split entries and coalesce them.
After a branching gate, amplitudes with |a| <= PRUNE_REL * max|amp of the same input column| are dropped
(exact-cancellation noise, ~1e-16 relative).  The dropped weight is CERTIFIED, not silent: for every input column
`Batch.dropped_l2[col]` accumulates sqrt(dropped weight) over all gates (triangle inequality; later gates are
unitary), so ||psi_sim - psi_exact||_2 <= dropped_l2[col] up to float64 rounding, and the evaluator adds it to the error
budget.  The number of stored amplitudes is capped and an overflow raises `SimCapExceeded`.
Gates are executed in a topological order of the circuit DAG that postpones branching gates as long as
non-branching gates are ready (any topological order is exact; the heuristic keeps few qubits open).
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass

import numpy as np

SIM_BASIS = ["x", "z", "s", "sdg", "t", "tdg", "h", "sx", "rz", "p", "u", "cx", "cz", "cp", "swap", "ccx", "ccz", "unitary"]

PRUNE_REL = 1e-14  # relative to the largest |amplitude| of the same input column
_W8 = np.exp(1j * np.pi / 4)
_DIAG1 = {"z": (1.0, -1.0), "s": (1.0, 1j), "sdg": (1.0, -1j), "t": (1.0, _W8), "tdg": (1.0, np.conj(_W8))}
_BRANCH = {"h", "sx", "u", "unitary"}


@dataclass
class Batch:
    keys: np.ndarray
    cols: np.ndarray
    amps: np.ndarray
    n_qubits: int
    dropped_l2: np.ndarray | None = None  # per input column: certified bound on the L2 norm dropped by pruning

    @property
    def dropped_total(self) -> float:
        """sqrt(sum_col dropped_l2^2): bounds the Frobenius (hence operator) norm of the pruning error of the matrix."""
        return 0.0 if self.dropped_l2 is None else float(np.sqrt(np.sum(self.dropped_l2 ** 2)))

    @property
    def dropped_max(self) -> float:
        return 0.0 if self.dropped_l2 is None or len(self.dropped_l2) == 0 else float(self.dropped_l2.max())


class SimCapExceeded(RuntimeError):
    pass


def _coalesce(keys, cols, amps, n_qubits, n_cols, dropped):
    """Sum amplitudes of equal (col, key); drop |a| <= PRUNE_REL * (column max) and add sqrt(dropped weight) per
    column to `dropped` (in place); sorted by (col, key)."""
    if len(keys) == 0:
        return keys, cols, amps
    if n_qubits + max(1, int(n_cols).bit_length()) <= 62:
        comp = (cols.astype(np.int64) << n_qubits) | keys
        order = np.argsort(comp, kind="stable")
        comp = comp[order]
        new = np.empty(len(comp), dtype=bool)
        new[0] = True
        new[1:] = comp[1:] != comp[:-1]
    else:
        order = np.lexsort((keys, cols))
        k_s, c_s = keys[order], cols[order]
        new = np.empty(len(k_s), dtype=bool)
        new[0] = True
        new[1:] = (k_s[1:] != k_s[:-1]) | (c_s[1:] != c_s[:-1])
    starts = np.flatnonzero(new)
    a = np.add.reduceat(amps[order], starts)
    k = keys[order][starts]
    c = cols[order][starts]
    mag = np.abs(a)
    cstart = np.flatnonzero(np.r_[True, c[1:] != c[:-1]])
    cmax = np.maximum.reduceat(mag, cstart)
    thr = np.repeat(cmax, np.diff(np.r_[cstart, len(c)])) * PRUNE_REL
    keep = mag > thr
    if not keep.all():
        w = np.bincount(c[~keep], weights=mag[~keep] ** 2, minlength=n_cols)
        dropped += np.sqrt(w)
    return k[keep], c[keep], a[keep]


def _schedule(ops):
    """Topological order of the gate list that keeps few qubits in superposition: non-branching ready gates first (by
    original index); when only branching gates are ready, prefer one on a qubit that an earlier branching gate has already
    opened (it usually closes the branch: H ... H of a relative-phase Toffoli), else the earliest ready one.  Any topological
    order is exact; this one avoids the layer-by-layer hoisting of Hadamards that Qiskit's transpile output has."""
    n = len(ops)
    last: dict = {}
    indeg = [0] * n
    succ: list = [[] for _ in range(n)]
    for i, (_, qs, _) in enumerate(ops):
        deps = {last[q] for q in qs if q in last}
        for d in deps:
            succ[d].append(i)
        indeg[i] = len(deps)
        for q in qs:
            last[q] = i
    plain, branch = [], set()
    for i in range(n):
        if indeg[i] == 0:
            if ops[i][0] in _BRANCH:
                branch.add(i)
            else:
                heapq.heappush(plain, i)
    order, opened = [], set()
    while plain or branch:
        if plain:
            i = heapq.heappop(plain)
        else:
            closers = [b for b in branch if any(q in opened for q in ops[b][1])]
            i = min(closers) if closers else min(branch)
            branch.discard(i)
            qs = ops[i][1]
            if len(qs) == 1:
                opened ^= {qs[0]}
            else:
                opened |= set(qs)
        order.append(i)
        for s_ in succ[i]:
            indeg[s_] -= 1
            if indeg[s_] == 0:
                if ops[s_][0] in _BRANCH:
                    branch.add(s_)
                else:
                    heapq.heappush(plain, s_)
    return order


_TRANSPILE_BASIS = [g for g in SIM_BASIS if g != "unitary"]  # qiskit refuses the non-standard name 'unitary'


def _to_ops(t, ops):
    for inst in t.data:
        name = inst.operation.name
        if name == "barrier":
            continue
        if name not in SIM_BASIS:
            raise ValueError(f"gate {name!r} cannot be simulated (measure/reset/unsupported)")
        qs = tuple(t.find_bit(q).index for q in inst.qubits)
        if name in _BRANCH:
            payload = np.asarray(inst.operation.to_matrix(), dtype=np.complex128)
        else:
            payload = tuple(float(p) for p in inst.operation.params)
        ops.append((name, qs, payload))


def _reject_wide_mcx(circ, _depth=0):
    """Reject native mcx with >= 3 controls, also inside custom/composite gates (recurses into `op.definition` of every
    gate whose name is not a standard-library name)."""
    from qiskit.circuit.library.standard_gates import get_standard_gate_name_mapping

    standard = _standard_names(get_standard_gate_name_mapping)
    for inst in circ.data:
        op = inst.operation
        if op.name.startswith("mcx") and getattr(op, "num_ctrl_qubits", op.num_qubits - 1) >= 3:
            raise ValueError(
                f"{op.name} with {getattr(op, 'num_ctrl_qubits', op.num_qubits - 1)} controls is not accepted: Qiskit's "
                "transpile may use idle qubits as clean ancillas and silently change the operator; build it from "
                "ccx/rccx on explicit ancillas")
        if op.name not in standard and op.name != "barrier" and _depth < 20:
            d = getattr(op, "definition", None)
            if d is not None:
                _reject_wide_mcx(d, _depth + 1)


_STD = None


def _standard_names(getter):
    global _STD
    if _STD is None:
        _STD = set(getter().keys()) | set(SIM_BASIS)
    return _STD


_DECOMP_CACHE: dict = {}


def decomposition_cache_key(op):
    """Cache key for a gate's decomposition, or None if it must not be cached.  Only gates of Qiskit's own standard library
    are cached (their name + params + control state determine the gate completely); custom / composite gates
    (QuantumCircuit.to_gate(), Gate subclasses) carry their content in `definition` and share names freely, so they are
    decomposed every time -- never keyed on a name alone."""
    from qiskit.circuit.library.standard_gates import get_standard_gate_name_mapping

    ref = get_standard_gate_name_mapping().get(op.name)
    if ref is None or not isinstance(op, type(ref)):
        return None
    if type(op).__name__ not in (type(ref).__name__, "_Singleton" + type(ref).__name__):
        return None
    try:
        return (type(op).__name__, op.name, tuple(float(x) for x in op.params), op.num_qubits,
                getattr(op, "ctrl_state", None))
    except (TypeError, ValueError):
        return None


def _decompose_local(op):
    """Level-0 decomposition of one foreign gate on qubits 0..k-1: (ops over SIM_BASIS, global phase); cached."""
    from qiskit import QuantumCircuit, transpile

    key = decomposition_cache_key(op)
    if key is not None and key in _DECOMP_CACHE:
        return _DECOMP_CACHE[key]
    sub = QuantumCircuit(op.num_qubits)
    sub.append(op, list(range(op.num_qubits)), [])
    t = transpile(sub, basis_gates=_TRANSPILE_BASIS, optimization_level=0, seed_transpiler=20261104,
                  qubits_initially_zero=False)
    ops: list = []
    _to_ops(t, ops)
    res = (ops, float(t.global_phase))
    if key is not None:
        _DECOMP_CACHE[key] = res
    return res


def _translate(qc):
    """Gate list [(name, qubits, payload)] over SIM_BASIS and the global phase, in PROGRAM ORDER: every foreign gate is
    replaced in place by its level-0 decomposition (one transpile per distinct gate, cached), so that e.g. the H ... H of a
    relative-phase Toffoli stay adjacent (transpiling the whole circuit would reorder the DAG layer by layer and hoist all
    the Hadamards).  Idle qubits are never assumed clean (qubits_initially_zero=False); native mcx with >= 3 controls is
    rejected."""
    _reject_wide_mcx(qc)
    ops: list = []
    phase = float(qc.global_phase)
    for inst in qc.data:
        op = inst.operation
        name = op.name
        if name == "barrier":
            continue
        if inst.clbits or name in ("measure", "reset", "delay") or name.startswith("if_") or name in ("for_loop", "while_loop", "switch_case"):
            raise ValueError(f"gate {name!r} cannot be simulated (measure/reset/classical control/unsupported)")
        qs = tuple(qc.find_bit(q).index for q in inst.qubits)
        if name in SIM_BASIS:
            payload = (np.asarray(op.to_matrix(), dtype=np.complex128) if name in _BRANCH
                       else tuple(float(x) for x in op.params))
            ops.append((name, qs, payload))
        else:
            phase += _expand(op, qs, ops)
    return ops, phase


def _expand(op, qs, ops, _depth=0) -> float:
    """Append the decomposition of a foreign gate on qubits `qs` to `ops`; returns the global phase.  Standard-library gates
    are transpiled one at a time (cached); custom / composite gates (to_gate(), Gate subclasses) are inlined from their
    `definition` in program order, recursively, so nested macros keep their local gate order too."""
    if decomposition_cache_key(op) is not None or _depth > 30 or getattr(op, "definition", None) is None:
        local, ph = _decompose_local(op)
        ops.extend((nm, tuple(qs[k] for k in lq), pl) for nm, lq, pl in local)
        return ph
    d = op.definition
    phase = float(d.global_phase)
    for inst in d.data:
        sub = inst.operation
        sq = tuple(qs[d.find_bit(q).index] for q in inst.qubits)
        if sub.name == "barrier":
            continue
        if inst.clbits or sub.name in ("measure", "reset", "delay"):
            raise ValueError(f"gate {sub.name!r} cannot be simulated (measure/reset/classical control/unsupported)")
        if sub.name in SIM_BASIS:
            payload = (np.asarray(sub.to_matrix(), dtype=np.complex128) if sub.name in _BRANCH
                       else tuple(float(x) for x in sub.params))
            ops.append((sub.name, sq, payload))
        else:
            phase += _expand(sub, sq, ops, _depth + 1)
    return phase


def run_batch(qc, inputs: np.ndarray, cap: int = 5_000_000) -> Batch:
    """Simulate `qc` on every basis integer in `inputs` (ancillas 0). Raises SimCapExceeded if the number of stored
    amplitudes (over all inputs) exceeds `cap`. Applies qc.global_phase.

    Gates run in program order first (fast, and branches of a decomposed macro open and close locally); if that exceeds the
    cap, a second attempt uses the DAG schedule that postpones branching gates (`_schedule`).  Both orders are exact."""
    n = qc.num_qubits
    if n > 62:
        raise ValueError("at most 62 qubits")
    inputs = np.asarray(inputs, dtype=np.int64)
    ops, gphase = _translate(qc)
    try:
        return _run(ops, gphase, n, inputs, cap, range(len(ops)))
    except SimCapExceeded:
        return _run(ops, gphase, n, inputs, cap, _schedule(ops))


def _run(ops, gphase, n, inputs, cap, order) -> Batch:
    keys = inputs.copy()
    cols = np.arange(len(inputs), dtype=np.int32)
    amps = np.full(len(inputs), np.exp(1j * gphase), dtype=np.complex128)
    if len(inputs) > cap:
        raise SimCapExceeded(f"{len(inputs)} inputs exceed the amplitude cap {cap}")
    n_cols = len(inputs)
    dropped = np.zeros(n_cols)
    one = np.int64(1)
    for gi in order:
        name, qs, p = ops[gi]
        if name == "x":
            keys = keys ^ (one << qs[0])
        elif name == "cx":
            keys = keys ^ (((keys >> qs[0]) & 1) << qs[1])
        elif name == "ccx":
            keys = keys ^ ((((keys >> qs[0]) & (keys >> qs[1])) & 1) << qs[2])
        elif name == "swap":
            d = ((keys >> qs[0]) ^ (keys >> qs[1])) & 1
            keys = keys ^ (d << qs[0]) ^ (d << qs[1])
        elif name in _DIAG1:
            ph = np.array(_DIAG1[name])
            amps = amps * ph[(keys >> qs[0]) & 1]
        elif name == "rz":
            ph = np.exp(0.5j * p[0] * np.array([-1.0, 1.0]))
            amps = amps * ph[(keys >> qs[0]) & 1]
        elif name == "p":
            amps = amps * np.where((keys >> qs[0]) & 1, np.exp(1j * p[0]), 1.0)
        elif name == "cz":
            amps = amps * np.where(((keys >> qs[0]) & (keys >> qs[1])) & 1, -1.0, 1.0)
        elif name == "ccz":
            amps = amps * np.where(((keys >> qs[0]) & (keys >> qs[1]) & (keys >> qs[2])) & 1, -1.0, 1.0)
        elif name == "cp":
            amps = amps * np.where(((keys >> qs[0]) & (keys >> qs[1])) & 1, np.exp(1j * p[0]), 1.0)
        elif name in _BRANCH:
            U = p
            k = len(qs)
            b_in = np.zeros(len(keys), dtype=np.int64)
            base = keys.copy()
            for i, q in enumerate(qs):
                b_in |= ((keys >> q) & 1) << i
                base &= ~(one << q)
            nk, nc, na = [], [], []
            for b_out in range(2 ** k):
                coef = U[b_out, b_in]
                nz = np.abs(coef) > 0
                if not nz.any():
                    continue
                pat = np.int64(0)
                for i, q in enumerate(qs):
                    pat |= np.int64((b_out >> i) & 1) << q
                nk.append(base[nz] | pat)
                nc.append(cols[nz])
                na.append(coef[nz] * amps[nz])
            if not nk:  # every branch has zero coefficient (cannot happen for unitary gates) or the state is empty
                keys, cols, amps = keys[:0], cols[:0], amps[:0]
                continue
            keys, cols, amps = _coalesce(np.concatenate(nk), np.concatenate(nc), np.concatenate(na), n, n_cols, dropped)
            if len(keys) > cap:
                raise SimCapExceeded(f"more than {cap} stored amplitudes after gate #{gi} ({name} on {qs})")
        else:  # pragma: no cover - SIM_BASIS is exhaustive
            raise ValueError(f"unhandled gate {name}")
    return Batch(keys=keys, cols=cols, amps=amps, n_qubits=n, dropped_l2=dropped)


def encoded_block(batch: Batch, codes: np.ndarray, n_inputs: int, code_mask: int) -> tuple[np.ndarray, np.ndarray]:
    """(M[len(codes), n_inputs], leak[n_inputs]). Output basis state `key` is in the code space iff
    key & ~code_mask == 0 and key in `codes`; leak = summed |amp|^2 of all other outputs of that input."""
    codes = np.asarray(codes, dtype=np.int64)
    order = np.argsort(codes)
    sorted_codes = codes[order]
    keys = batch.keys
    inside = (keys & ~np.int64(code_mask)) == 0
    pos = np.searchsorted(sorted_codes, keys)
    pos_c = np.minimum(pos, len(sorted_codes) - 1)
    is_code = inside & (sorted_codes[pos_c] == keys) if len(sorted_codes) else np.zeros(len(keys), dtype=bool)
    M = np.zeros((len(codes), n_inputs), dtype=np.complex128)
    np.add.at(M, (order[pos_c[is_code]], batch.cols[is_code]), batch.amps[is_code])
    leak = np.zeros(n_inputs)
    np.add.at(leak, batch.cols[~is_code], np.abs(batch.amps[~is_code]) ** 2)
    return M, leak
