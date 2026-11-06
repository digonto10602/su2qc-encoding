"""Tester, step 3.6: own T-count re-derivation (own T_fixed from the expanded gate list, own pygridsynth call + own 2x2 word
check), Qiskit Clifford+T cross-check (own pass-manager call, 2 seeds), sibling comparison at |alpha|=2 <-> beta=1.
Output results/spinnet/tester/m3_step_3_6_tcount.json."""
import json, sys, subprocess, math
sys.path.insert(0, "src")
import numpy as np, mpmath
from pygridsynth.gridsynth import gridsynth_gates
from su2plaq.circuits.spinnet import trotter_v2_circuit
from su2plaq.metrics.cliffordt import t_table
from su2plaq.metrics.logical import logical_metrics

OUT = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), "rows": {}}
M = {"H": np.array([[1, 1], [1, -1]]) / math.sqrt(2), "S": np.diag([1, 1j]), "T": np.diag([1, np.exp(1j * math.pi / 4)]),
     "X": np.array([[0, 1], [1, 0]]), "W": np.exp(1j * math.pi / 4) * np.eye(2)}
def word_err(w, th):
    U = np.eye(2, dtype=complex)
    for ch in w: U = U @ M[ch]
    B = np.diag([np.exp(-0.5j * th), np.exp(0.5j * th)])
    ov = np.trace(B.conj().T @ U); ph = ov / abs(ov)
    return float(np.linalg.norm(U - ph * B, 2))
def own_T(th, eps):
    k = th / (math.pi / 4)
    if abs(k - round(k)) < 1e-9: return abs(round(k)) % 2, 0.0, ""    # rz(k pi/4) = T^k up to phase: k odd -> 1 T
    w = str(gridsynth_gates(theta=mpmath.mpf(repr(th)), epsilon=mpmath.mpf(repr(eps))))
    return w.count("T"), word_err(w, th), w

def expanded_counts(qc):
    """own T_fixed and rz angles, from qiskit definitions (rccx -> 4 T, rc3x/rc3x_dg expanded already)."""
    nT, nCX, rz = 0, 0, []
    for i in qc.data:
        n = i.operation.name
        if n == "rccx":
            d = i.operation.definition
            nT += sum(1 for j in d.data if j.operation.name in ("t", "tdg")); nCX += sum(1 for j in d.data if j.operation.name == "cx")
        elif n in ("t", "tdg"): nT += 1
        elif n == "cx": nCX += 1
        elif n == "rz": rz.append(float(i.operation.params[0]))
    return nT, nCX, rz

EPS = (1e-4, 1e-6, 1e-8, 1e-10)
for sk in ("pairs9", "flags4", "flags5", "flags6"):
    qc = trotter_v2_circuit(sk, 0.61)
    nT, nCX, rz = expanded_counts(qc)
    lm = logical_metrics(qc)
    rows = t_table(qc, EPS)
    r = {"own_T_fixed": nT, "own_CX": nCX, "own_n_rz": len(rz), "lib_T_fixed": lm["t_fixed"], "lib_CX": lm["cx"], "lib_depth": lm["depth"],
         "angles_over_beta": [t / 0.61 for t in rz], "eps": []}
    for row in rows:
        eps = row["eps"]
        tot = 0; maxerr = 0.0
        for th in rz:
            t, e, w = own_T(th, eps); tot += t; maxerr = max(maxerr, e)
            assert e <= eps
        r["eps"].append({"eps": eps, "own_t_rot": tot, "own_t_total": nT + tot, "lib_t_total": row["t_total"], "lib_t_qiskit": row["t_qiskit"],
                         "qiskit_vs_total": row["t_qiskit"] / row["t_total"] - 1, "max_word_err": maxerr, "t_est": row["t_est"],
                         "cx_qiskit": row["cx_qiskit"]})
        print(sk, r["eps"][-1], flush=True)
    OUT["rows"][sk] = r

# independent Qiskit CT call, other seed and level
from qiskit.transpiler import generate_preset_clifford_t_pass_manager
from su2plaq.metrics.logical import lower
OUT["qiskit_indep"] = {}
for sk in ("pairs9", "flags4"):
    low = lower(trotter_v2_circuit(sk, 0.61))
    for eps in (1e-4, 1e-6):
        for seed, lvl in ((7, 3), (11, 1)):
            pm = generate_preset_clifford_t_pass_manager(basis_gates=["cx", "h", "s", "sdg", "t", "tdg"], optimization_level=lvl,
                  rz_synthesis_config={"rz_synthesis_error": eps, "rz_cache_error": eps / 10}, seed_transpiler=seed, qubits_initially_zero=False)
            o = pm.run(low).count_ops()
            ref = [x for x in OUT["rows"][sk]["eps"] if x["eps"] == eps][0]["own_t_total"]
            OUT["qiskit_indep"][f"{sk}_eps{eps}_seed{seed}_lvl{lvl}"] = {"t": o.get("t", 0) + o.get("tdg", 0), "cx": o.get("cx", 0), "own_t_total": ref,
                                                                         "rel": (o.get("t", 0) + o.get("tdg", 0)) / ref - 1}
            print(sk, eps, seed, lvl, OUT["qiskit_indep"][f"{sk}_eps{eps}_seed{seed}_lvl{lvl}"], flush=True)

# sibling comparison: sibling alpha=2 <-> our beta=1 (angles(beta) = -2 * sibling_angles(alpha=beta)  => alpha_sib = -2 beta)
OUT["sibling_cmp"] = {}
for sk, beta in (("pairs9", 1.0), ("flags4", 1.0)):
    qc = trotter_v2_circuit(sk, beta); nT, nCX, rz = expanded_counts(qc)
    for eps in (1e-6,):
        tot = sum(own_T(th, eps)[0] for th in rz)
        OUT["sibling_cmp"][f"{sk}_beta{beta}_eps{eps}"] = {"our_rotation_T": tot, "our_T_fixed": nT, "our_total": nT + tot, "rz": rz}
        print(sk, beta, eps, tot, nT, nT + tot, flush=True)
json.dump(OUT, open("results/spinnet/tester/m3_step_3_6_tcount.json", "w"), indent=1)
