import sys, json, time
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding")
import numpy as np
import scipy.sparse as sp
from qiskit import QuantumCircuit, QuantumRegister
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.evaluate.evaluator import evaluate, inner_target
from su2plaq.exact.operators import target

enc = TwelveQubit()
basis = enc.basis
I = np.eye(433, dtype=complex)
alpha, beta = 0.37, 0.61
RES = []
OUT = '/home/digimonk/Projects/su2qc-encoding/results/evaluator_0_8_final_'
J = np.array([l[0] for l in basis.labels])  # (433,12) link spins

def rec(name, expected, got, tol, ok, note=""):
    RES.append(dict(check=name, expected=str(expected), got=str(got), tol=str(tol), ok=bool(ok), note=note))
    print(("PASS" if ok else "FAIL"), name, "| exp:", expected, "| got:", got, "|", note, flush=True)

def circ(outer=False, nanc=0, order="d,o,a"):
    regs = {"d": QuantumRegister(12, "d")}
    if outer: regs["o"] = QuantumRegister(16, "o")
    if nanc: regs["a"] = QuantumRegister(nanc, "a")
    names = [n for n in order.split(",") if n in regs]
    qc = QuantumCircuit(*[regs[n] for n in names])
    return qc, regs

def fmt(v):
    return f"ok={v.ok} reason={v.reason} err={v.op_norm_error:.3e} leak={v.max_leak:.2e} dirty={v.dirty_ancilla:.2e} gauss={v.gauss_residual:.2e} read={v.outer_bits_read} method={v.method} eng={v.engine} t={v.seconds:.1f}s"

# oracle: A[k',k] = <psi_k'| F |psi_k> for F a (partial) permutation-with-phase on 28-bit codes, from physical_vectors
EV = enc.physical_vectors()
CODES = np.concatenate(EV.codes); AMPS = np.concatenate(EV.amps).astype(complex)
ST = np.concatenate([np.full(len(c), k) for k, c in enumerate(EV.codes)])
ORD = np.argsort(CODES, kind="stable")
CS, AS, SS = CODES[ORD], AMPS[ORD], ST[ORD]

def oracle_A(fcode, fphase):
    """F|c> = fphase(c)|fcode(c)>; returns 433x433 A = Psi^dag F Psi (codes that map outside every state contribute 0)."""
    c2 = fcode(CODES); ph = fphase(CODES)
    A = np.zeros((433, 433), complex)
    lo = np.searchsorted(CS, c2, "left"); hi = np.searchsorted(CS, c2, "right")
    for i in range(len(CODES)):
        for t in range(lo[i], hi[i]):
            A[SS[t], ST[i]] += np.conj(AS[t]) * ph[i] * AMPS[i]
    return A

def bit(c, q): return (c >> q) & 1
