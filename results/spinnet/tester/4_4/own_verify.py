"""Independent verification (tester, report 111): own build (exec of the program file in-process, no sandbox worker), own Aer statevector on
all 433 physical states, own target from su2plaq.exact.spinnet (route B, scipy expm) and su2plaq.exact.operators (route A + gauge).
Usage: own_verify.py <root> <label-or-stem>[,..] [--all-angles] [--paulo]"""
import sys, json, time, pathlib, importlib.util
import numpy as np
from scipy.linalg import expm
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from su2plaq.compress.builder import Builder
from su2plaq.exact import spinnet as XS
from su2plaq.exact.operators import target as target_A
from su2plaq.exact.compare import gauge_align
from su2plaq.encodings.spinnet import SpinNet, code_of_label

enc = SpinNet()
labels = XS.labels()
assert labels == enc.labels
codes = np.array([code_of_label(l) for l in labels], dtype=np.int64)
assert (codes == enc._codes).all()
HB = XS.h_magnetic_phys_6j(labels)
HE = XS.h_electric_6j(labels)           # inner electric (diag or matrix?)
HE = np.diag(HE) if HE.ndim == 2 else HE
index = {int(c): k for k, c in enumerate(codes)}
sim = AerSimulator(method="statevector", max_parallel_threads=1)

def targetB(kind, a, b, order=1):
    UE = lambda x: np.diag(np.exp(-1j * x * HE))
    UB = expm(-1j * b * HB)
    if kind == "UB": return UB
    if kind == "UE": return UE(a)
    return UB @ UE(a) if order == 1 else UE(a / 2) @ UB @ UE(a / 2)

def aer_block(qc):
    n = qc.num_qubits
    body = transpile(qc, sim, optimization_level=0)
    outs = np.zeros((433, 433), complex); anc = 0.0; outer = 0.0
    for k, c in enumerate(codes):
        prep = QuantumCircuit(n)
        for q in range(16):
            if (int(c) >> q) & 1: prep.x(q)
        full = prep.compose(body); full.save_statevector()
        psi = np.asarray(sim.run(full, shots=1).result().get_statevector(full))
        nz = np.nonzero(np.abs(psi) > 1e-14)[0]
        o_in = int(c) >> 8
        for i in nz:
            if i >> 16: anc += abs(psi[i])**2; continue
            if (int(i) >> 8) != o_in: outer += abs(psi[i])**2
            j = index.get(int(i))
            if j is not None: outs[j, k] = psi[i]
            else: anc += abs(psi[i])**2   # leak out of the physical code set counted with anc
    return outs, anc, outer

def err(outs, V):
    ov = np.trace(V.conj().T @ outs); ph = ov / abs(ov)
    return float(np.linalg.norm(outs - ph * V, 2))

def build(path, a, b, order=1):
    src = pathlib.Path(path).read_text()
    ns = {"__name__": "prog"}
    exec(compile(src, str(path), "exec"), ns)
    class S: pass
    from su2plaq.compress.spec import default_spec
    from su2plaq.spinnet import loop; loop.install()
    sp = default_spec("spinnet", "step").with_angles(a, b)
    bld = ns["build"](sp)
    return bld.circuit() if hasattr(bld, "circuit") else bld.qc

if __name__ == "__main__":
    root = pathlib.Path(sys.argv[1]); stems = sys.argv[2].split(","); allang = "--all-angles" in sys.argv
    pairs = [(0.37, 0.61)] + ([(0.91, 0.23), (1.70, 1.00)] if allang else [])
    res = {}
    # sanity: route A gauged vs route B
    for st in stems:
        f = next((root / "compress/programs/spinnet/seed").glob(f"*{st}*.py"))
        for (a, b) in pairs:
            t0 = time.time(); qc = build(f, a, b)
            outs, anc, outer = aer_block(qc)
            V = targetB("step", a, b)
            e = err(outs, V)
            res[f"{f.stem}@{a},{b}"] = {"err": e, "ancilla_or_leak_weight_max_sum": anc, "outer_changed_sum": outer, "n_qubits": qc.num_qubits,
                                         "ops": dict(qc.count_ops()), "wall": time.time() - t0}
            print(f.stem, a, b, res[f"{f.stem}@{a},{b}"], flush=True)
    print(json.dumps(res, default=str))
