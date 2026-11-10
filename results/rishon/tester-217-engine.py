"""Tester 217: own batched sparse simulator (numpy only, no su2plaq.evaluate) + own targets from su2plaq.rishon.algebra.

Gate model: every gate is reduced to (controls, target, 2x2 matrix) using Qiskit's own base_gate matrices, or decomposed by
Qiskit's definition (rccx, mcx, swap, ...).  Diagonal 2x2 -> amplitude multiply, X-like -> key flip, general -> split.
Pruning: absolute |a| < thr per (column,key) after each splitting gate; dropped squared weight is accumulated per column.
"""
import itertools
import numpy as np
import scipy.sparse as sp
import scipy.linalg as sl
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import XGate

SIM_NAMES = {"x", "z", "y", "h", "s", "sdg", "t", "tdg", "sx", "sxdg", "rx", "ry", "rz", "p", "u1", "u", "cx", "cz", "cy", "ch", "crx", "cry",
             "crz", "cp", "ccx", "ccz", "swap"}


def lower(qc):
    """Return list of (controls tuple, target, 2x2 complex, name) in circuit order (after Qiskit decomposition of unknown gates)."""
    ops = []
    pend = [(inst.operation, [qc.find_bit(q).index for q in inst.qubits]) for inst in qc.data]
    pend.reverse()
    while pend:
        g, qs = pend.pop()
        nm = g.name
        if nm in ("barrier",):
            continue
        if nm == "swap":
            a, b = qs
            for (c, t) in ((a, b), (b, a), (a, b)):
                ops.append(((c,), t, np.array([[0, 1], [1, 0]], complex), "cx"))
            continue
        if nm == "ccx":
            ops.append(((qs[0], qs[1]), qs[2], np.array([[0, 1], [1, 0]], complex), "ccx"))
            continue
        if nm == "ccz":
            ops.append(((qs[0], qs[1]), qs[2], np.diag([1, -1]).astype(complex), "ccz"))
            continue
        nctrl = getattr(g, "num_ctrl_qubits", 0)
        if nctrl and hasattr(g, "base_gate") and g.base_gate.num_qubits == 1 and g.ctrl_state == (1 << nctrl) - 1 \
                and nm not in ("rccx", "mcx"):
            ops.append((tuple(qs[:nctrl]), qs[nctrl], np.array(g.base_gate.to_matrix(), complex), nm))
            continue
        if g.num_qubits == 1 and nm != "rccx":
            ops.append(((), qs[0], np.array(g.to_matrix(), complex), nm))
            continue
        # rccx, mcx (many controls), anything else: Qiskit's own definition, expanded in place
        d = g.definition
        if d is None:
            raise ValueError("cannot lower gate " + nm)
        sub = [(inst.operation, [qs[d.find_bit(q).index] for q in inst.qubits]) for inst in d.data]
        gp = float(d.global_phase)
        if gp:
            ops.append(("phase", gp))
        sub.reverse()
        pend.extend(sub)
    return ops


class Sim:
    def __init__(self, codes_in, qubits, thr=1e-15):
        """codes_in[c] = data/ancilla basis state of column c as an int over ORIGINAL qubit indices; qubits = sorted list of
        the original qubit indices actually used (compacted into bits 0..n-1)."""
        self.qubits = list(qubits)
        self.pos = {q: i for i, q in enumerate(self.qubits)}
        self.n = len(self.qubits)
        self.thr = thr
        ncol = len(codes_in)
        self.ncol = ncol
        st = np.zeros(ncol, dtype=np.int64)
        for q, i in self.pos.items():
            st |= ((np.asarray(codes_in, dtype=np.int64) >> q) & 1) << i
        self.key = (np.arange(ncol, dtype=np.int64) << self.n) | st
        self.amp = np.ones(ncol, dtype=complex)
        self.dw_sq = np.zeros(ncol)       # sum of squared dropped amplitudes (no triangle)
        self.dw_tri = np.zeros(ncol)      # sum over events of sqrt(dropped weight)  (triangle inequality, like the production bound)
        self.maxsize = ncol
        self.live = []                    # per gate: OR of state bits over all keys (for liveness analysis)

    def _bit(self, q):
        return (self.key >> self.pos[q]) & 1

    def _merge(self):
        o = np.argsort(self.key, kind="stable")
        k, a = self.key[o], self.amp[o]
        idx = np.flatnonzero(np.r_[True, k[1:] != k[:-1]])
        a = np.add.reduceat(a, idx)
        k = k[idx]
        small = np.abs(a) < self.thr
        if small.any():
            col = k[small] >> self.n
            w = np.abs(a[small]) ** 2
            tmp = np.zeros(self.ncol)
            np.add.at(tmp, col, w)
            self.dw_sq += tmp
            self.dw_tri += np.sqrt(tmp)
        self.key, self.amp = k[~small], a[~small]
        self.maxsize = max(self.maxsize, len(self.key))

    def apply(self, ctrls, t, m):
        k, amp = self.key, self.amp
        pt = self.pos[t]
        act = np.ones(len(k), bool)
        for c in ctrls:
            act &= ((k >> self.pos[c]) & 1) == 1
        isdiag = abs(m[0, 1]) < 1e-15 and abs(m[1, 0]) < 1e-15
        isx = abs(m[0, 0]) < 1e-15 and abs(m[1, 1]) < 1e-15 and abs(m[0, 1] - 1) < 1e-15 and abs(m[1, 0] - 1) < 1e-15
        if isdiag:
            b = (k >> pt) & 1
            f = np.where(b == 1, m[1, 1], m[0, 0])
            self.amp = np.where(act, amp * f, amp)
        elif isx:
            self.key = np.where(act, k ^ (1 << pt), k)
        else:
            ka, aa = k[act], amp[act]
            b = (ka >> pt) & 1
            k0 = ka & ~np.int64(1 << pt)
            k1 = ka | np.int64(1 << pt)
            # output amplitude to bit0 from input bit b: m[0,b]; to bit1: m[1,b]
            a0 = aa * np.where(b == 0, m[0, 0], m[0, 1])
            a1 = aa * np.where(b == 0, m[1, 0], m[1, 1])
            self.key = np.concatenate([k[~act], k0, k1])
            self.amp = np.concatenate([amp[~act], a0, a1])
            self._merge()

    def run(self, ops, anc_mask=None):
        self.gphase = 0.0
        for op in ops:
            if op[0] == "phase":
                self.gphase += op[1]
                continue
            self.apply(*op[:3])
            if anc_mask is not None:
                self.live.append(int(np.bitwise_or.reduce(self.key & anc_mask, initial=0)))
        return self

    def block(self, codes_out, data_qubits):
        """M[a, c] = <code_a| U |code_c> where outputs must have all non-data bits 0; also returns the weight outside
        (|dirty|^2 + |non-code data|^2 per column)."""
        n = self.n
        st = self.key & ((1 << n) - 1)
        col = self.key >> n
        dmask = 0
        dpos = [self.pos[q] for q in data_qubits]
        for p in dpos:
            dmask |= 1 << p
        clean = (st & ~np.int64(dmask)) == 0
        d = np.zeros(len(st), dtype=np.int64)
        for i, p in enumerate(dpos):
            d |= ((st >> p) & 1) << i
        lut = np.full(1 << len(dpos), -1, dtype=np.int64)
        lut[np.asarray(codes_out)] = np.arange(len(codes_out))
        row = lut[d]
        inc = clean & (row >= 0)
        M = np.zeros((len(codes_out), self.ncol), complex)
        np.add.at(M, (row[inc], col[inc]), self.amp[inc])
        w_dirty = np.zeros(self.ncol)
        np.add.at(w_dirty, col[~clean], np.abs(self.amp[~clean]) ** 2)
        w_out = np.zeros(self.ncol)
        np.add.at(w_out, col[clean & ~inc], np.abs(self.amp[clean & ~inc]) ** 2)
        return M * np.exp(1j * self.gphase), w_dirty, w_out


# ------------------------------------------------------------------------------------------ targets (rishon.algebra only)
def algebra_targets(alpha, beta):
    """(codes, HE diag, HB dense, UE, UB, step=UB UE) on the 1296 inner codes; operators built from RishonLink + embed_link_op on
    four links (65536-dim sparse), restricted to codes = sum_l s_l << 4l, s_l in the 6-state sector.  Does NOT import
    su2plaq.rishon.operators."""
    from su2plaq.rishon.algebra import RishonLink, embed_link_op
    rl = RishonLink()
    sec = [int(s) for s in rl.sector]
    codes = np.array(sorted(sum(s << (4 * l) for l, s in enumerate(cfg)) for cfg in itertools.product(sec, repeat=4)), dtype=np.int64)
    E = lambda M, l: embed_link_op(M, l, 4)
    U = lambda i, j, l: E(rl.U(i, j), l)
    Ud = lambda i, j, l: E(rl.Udag(i, j), l)
    # Tr(U_b U_r U_t^dag U_l^dag), links b=0, r=1, t=2, l=3.  (U^dag)_{cd} = (U_{dc})^dagger.
    W = sp.csr_matrix((16 ** 4, 16 ** 4), dtype=complex)
    for a, b, c, d in itertools.product(range(2), repeat=4):
        W = W + U(a, b, 0) @ U(b, c, 1) @ Ud(d, c, 2) @ Ud(a, d, 3)
    Wc = W[codes][:, codes].toarray()
    HB = -(Wc + Wc.conj().T)
    cas = 0.5 * (rl.casimir_L + rl.casimir_R)
    HEfull = sum(E(cas, l) for l in range(4))
    HE = np.real(np.asarray(HEfull[codes][:, codes].diagonal()))
    offdiag = np.abs(HEfull[codes][:, codes].toarray() - np.diag(HE)).max()
    UE = np.diag(np.exp(-1j * alpha * HE))
    UB = sl.expm(-1j * beta * HB)
    return dict(codes=codes, HE=HE, HB=HB, UE=UE, UB=UB, step=UB @ UE, W=Wc, he_offdiag=float(offdiag),
                hb_herm=float(np.abs(HB - HB.conj().T).max()), W_real=float(np.abs(Wc.imag).max()))


def compare(M, V):
    """(phase, spectral error ||M - phase V||_2) with the phase fitted as arg tr(V^dag M)."""
    tr = np.trace(V.conj().T @ M)
    ph = tr / abs(tr)
    E = M - ph * V
    return ph, float(np.linalg.norm(E, 2)), float(np.abs(E).max())


def used_qubits(ops):
    s = set()
    for op in ops:
        if op[0] == "phase":
            continue
        s.update(op[0]); s.add(op[1])
    return sorted(s)
