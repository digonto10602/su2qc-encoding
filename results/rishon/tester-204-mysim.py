"""Tester 204: own batched sparse gate simulator (numpy only) + own JW reference.  No import of su2plaq.evaluate."""
import numpy as np, scipy.sparse as sp, itertools
NQ_SHIFT = 26

def merge(key, amp, thr=1e-15):
    o = np.argsort(key, kind='stable'); key, amp = key[o], amp[o]
    first = np.r_[True, key[1:] != key[:-1]]
    idx = np.flatnonzero(first)
    amp = np.add.reduceat(amp, idx); key = key[idx]
    small = np.abs(amp) < thr
    # dropped L2 per column
    dcol = np.zeros(0)
    dropped = (key[small] >> NQ_SHIFT, np.abs(amp[small]) ** 2)
    return key[~small], amp[~small], dropped

class Sim:
    def __init__(self, codes_in, nq, shift=None):
        global NQ_SHIFT
        NQ_SHIFT = nq
        self.nq = nq
        n = len(codes_in)
        self.key = (np.arange(n, dtype=np.int64) << nq) | np.asarray(codes_in, dtype=np.int64)
        self.amp = np.ones(n, dtype=complex)
        self.ncol = n
        self.dw = np.zeros(n)         # dropped squared weight per call, accumulated per column as sqrt sum (triangle)
        self.maxsize = n
    def bit(self, q): return (self.key >> q) & 1
    def _merge(self):
        self.key, self.amp, (dc, dw) = merge(self.key, self.amp)
        if len(dc):
            # per-merge dropped weight per column -> add sqrt (triangle inequality)
            tmp = np.zeros(self.ncol); np.add.at(tmp, dc, dw); self.dw += np.sqrt(tmp)
        self.maxsize = max(self.maxsize, len(self.key))
    def gate(self, name, qs, params=()):
        k = self.key
        if name == 'x': self.key = k ^ (1 << qs[0])
        elif name == 'cx': self.key = k ^ (((k >> qs[0]) & 1) << qs[1])
        elif name == 'ccx': self.key = k ^ ((((k >> qs[0]) & (k >> qs[1])) & 1) << qs[2])
        elif name == 'z': self.amp = self.amp * (1 - 2 * ((k >> qs[0]) & 1))
        elif name == 'cz': self.amp = self.amp * (1 - 2 * (((k >> qs[0]) & (k >> qs[1])) & 1))
        elif name == 'ccz': self.amp = self.amp * (1 - 2 * (((k >> qs[0]) & (k >> qs[1]) & (k >> qs[2])) & 1))
        elif name == 'p': self.amp = self.amp * np.where((k >> qs[0]) & 1, np.exp(1j * params[0]), 1.0)
        elif name == 'h' or name == 'ch':
            t = qs[-1]
            act = np.ones(len(k), bool) if name == 'h' else (((k >> qs[0]) & 1) == 1)
            b = (k >> t) & 1
            ka, aa, ba = k[act], self.amp[act], b[act]
            k0 = ka & ~np.int64(1 << t); k1 = ka | np.int64(1 << t)
            r = 1 / np.sqrt(2)
            nk = np.concatenate([k[~act], k0, k1])
            na = np.concatenate([self.amp[~act], aa * r, aa * r * (1 - 2 * ba)])
            self.key, self.amp = nk, na; self._merge()
        elif name == 'crx':
            th = params[0]; c, t = qs
            act = ((k >> c) & 1) == 1
            ka, aa = k[act], self.amp[act]
            cs, sn = np.cos(th / 2), np.sin(th / 2)
            nk = np.concatenate([k[~act], ka, ka ^ (1 << t)])
            na = np.concatenate([self.amp[~act], aa * cs, -1j * sn * aa])
            self.key, self.amp = nk, na; self._merge()
        else:
            raise ValueError(name)
    def run(self, qc):
        for inst in qc.data:
            self.gate(inst.operation.name, tuple(qc.find_bit(q).index for q in inst.qubits), tuple(float(p) for p in inst.operation.params))
        return self
    def block(self, codes_out, data_mask):
        """M[i_out, col] for outputs with ancilla bits (above data_mask) == 0 and data in codes_out; returns M, leak_total_per_col_norm"""
        st = self.key & ((1 << self.nq) - 1); col = self.key >> self.nq
        lookup = {int(c): i for i, c in enumerate(codes_out)}
        pos = np.full(1 << 16, -1, dtype=np.int64)
        for c, i in lookup.items(): pos[c] = i
        anc_clean = (st >> 16) == 0
        d = st & 0xFFFF
        inc = anc_clean & (pos[d] >= 0)
        M = np.zeros((len(codes_out), self.ncol), complex)
        np.add.at(M, (pos[d[inc]], col[inc]), self.amp[inc])
        w_anc = np.zeros(self.ncol); np.add.at(w_anc, col[~anc_clean], np.abs(self.amp[~anc_clean]) ** 2)
        w_out = np.zeros(self.ncol); np.add.at(w_out, col[anc_clean & ~inc], np.abs(self.amp[anc_clean & ~inc]) ** 2)
        return M, w_anc, w_out

def own_reference():
    n = 16
    Z = sp.csr_matrix(np.diag([1., -1.])); I2 = sp.identity(2, format='csr'); SM = sp.csr_matrix(np.array([[0, 1], [0, 0]], float))
    def kronle(ops):
        o = sp.identity(1, format='csr')
        for x in ops: o = sp.kron(x, o, format='csr')
        return o
    c = [kronle([Z] * k + [SM] + [I2] * (n - k - 1)) for k in range(n)]
    cd = [x.T.tocsr() for x in c]
    U = lambda l, i, j: c[4 * l + i] @ cd[4 * l + 2 + j]
    wt = lambda x: bin(x).count('1')
    nib = [x for x in range(16) if wt(x) == 2]
    codes = np.array(sorted(sum(s << (4 * l) for l, s in enumerate(cfg)) for cfg in itertools.product(nib, repeat=4)), dtype=np.int64)
    Wf = sp.csr_matrix((2 ** n, 2 ** n))
    for a, b, cc, d in itertools.product(range(2), repeat=4):
        Wf = Wf + U(0, a, b) @ U(1, b, cc) @ U(2, d, cc).T @ U(3, a, d).T
    W = Wf[codes][:, codes].toarray()
    HB = -(W + W.T)
    sig = [np.array([[0, 1], [1, 0]], complex), np.array([[0, -1j], [1j, 0]]), np.array([[1, 0], [0, -1]], complex)]
    T = [s / 2 for s in sig]
    def Lgen(l, a): return sum(T[a][i, j] * (cd[4 * l + i] @ c[4 * l + j]) for i in range(2) for j in range(2))
    HE = np.zeros(1296)
    for l in range(4):
        CL = sum(Lgen(l, a) @ Lgen(l, a) for a in range(3))
        HE += np.real(np.diag(CL[codes][:, codes].toarray()))
    return codes, HB, HE
