"""Tester report 113 (M4 round 1): own build (exec of the archived program file, in-process), own Aer statevector on all 433 physical codes,
own route-B target (su2plaq.exact.spinnet 6j H_B, scipy expm; diag U_E).  Usage: aer_verify.py <root> <entry-id> -> JSON on stdout.
Separates: ancilla weight (ancilla bits nonzero), leak (data/outer code not one of the 433), outer-changed weight, block error (2-norm after global phase),
full column residual (max over inputs of || psi_k - e^{i phi} embed(V e_k) ||)."""
import sys, json, time, pathlib, hashlib
import numpy as np
from scipy.linalg import expm
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from su2plaq.exact import spinnet as XS
from su2plaq.encodings.spinnet import SpinNet, code_of_label
from su2plaq.spinnet import loop; loop.install()
from su2plaq.compress.spec import default_spec

enc = SpinNet(); labels = XS.labels()
codes = np.array([code_of_label(l) for l in labels], dtype=np.int64)
index = {int(c): k for k, c in enumerate(codes)}
HB = XS.h_magnetic_phys_6j(labels); HE = XS.h_electric_6j(labels); HE = np.diag(HE) if HE.ndim == 2 else HE
sim = AerSimulator(method="statevector", max_parallel_threads=1)

def target(a, b):
    return expm(-1j * b * HB) @ np.diag(np.exp(-1j * a * HE))

def build(path, a, b):
    ns = {"__name__": "prog"}; src = pathlib.Path(path).read_text()
    exec(compile(src, str(path), "exec"), ns)
    sp = default_spec("spinnet", "step").with_angles(a, b)
    bld = ns["build"](sp)
    return bld.circuit()

def run(qc):
    n = qc.num_qubits; body = transpile(qc, sim, optimization_level=0)
    cols = []
    for k, c in enumerate(codes):
        prep = QuantumCircuit(n)
        for q in range(16):
            if (int(c) >> q) & 1: prep.x(q)
        full = prep.compose(body); full.save_statevector()
        psi = np.asarray(sim.run(full, shots=1).result().get_statevector(full))
        nz = np.nonzero(np.abs(psi) > 1e-15)[0]
        cols.append((nz, psi[nz]))
    return cols

if __name__ == "__main__":
    root = pathlib.Path(sys.argv[1]); eid = sys.argv[2]
    ent = json.load(open(root / f"compress/archive/spinnet/entries/{eid}.json"))
    f = root / ent["program_path"]; sha = hashlib.sha256(f.read_bytes()).hexdigest()
    out = {"id": eid, "sha_equal_archive": sha == ent["program_sha256"], "cases": {}}
    for (a, b) in [(0.37, 0.61), (0.91, 0.23), (1.70, 1.00)]:
        t0 = time.time(); qc = build(f, a, b); cols = run(qc); V = target(a, b)
        M = np.zeros((433, 433), complex); anc = 0.0; leak = 0.0; outer = 0.0
        for k, (nz, amp) in enumerate(cols):
            o_in = int(codes[k]) >> 8
            for i, z in zip(nz, amp):
                w = abs(z) ** 2
                if int(i) >> 16: anc += w; continue
                if (int(i) >> 8) != o_in: outer += w
                j = index.get(int(i))
                if j is None: leak += w
                else: M[j, k] = z
        ov = np.trace(V.conj().T @ M); ph = ov / abs(ov)
        e_block = float(np.linalg.norm(M - ph * V, 2))
        # full column residual: block part + everything else
        res_cols = []
        for k, (nz, amp) in enumerate(cols):
            d = M[:, k] - ph * V[:, k]
            other = sum(abs(z) ** 2 for i, z in zip(nz, amp) if (int(i) >> 16) or index.get(int(i)) is None)
            res_cols.append(np.sqrt(np.linalg.norm(d) ** 2 + other))
        # unitarity of the block (columns norms sum) and Gauss: all weight inside the 433 codes
        out["cases"][f"{a},{b}"] = {"block_err_2norm": e_block, "max_col_residual": float(max(res_cols)), "ancilla_weight_sum": anc,
                                    "leak_weight_sum": leak, "outer_changed_weight_sum": outer, "n_qubits": qc.num_qubits,
                                    "ops": {k: int(v) for k, v in qc.count_ops().items()}, "wall_s": time.time() - t0}
        print(eid, a, b, out["cases"][f"{a},{b}"], flush=True)
    print("JSON:" + json.dumps(out))
