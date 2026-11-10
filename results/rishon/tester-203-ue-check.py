"""Tester 203 item 3: build_UE physics with Qiskit Operator/Statevector (independent of the sparse simulator)."""
import itertools, json, subprocess, sys
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector
sys.path.insert(0, "src")
from su2plaq.circuits.rishon import build_UE
from su2plaq.metrics.logical import logical_metrics

out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), "alphas": {}}
SING, QUART = [3, 12], [5, 6, 9, 10]
for alpha in (0.37, 0.91):
    rec = {}
    qc = build_UE(alpha)
    # (1) per-link 4-qubit slices: build the sub-circuit of gates touching qubits 4l..4l+3 and take its dense 16x16 Operator
    maxdev = 0.0; invalid = {}
    for link in range(4):
        sub = QuantumCircuit(4)
        for inst in qc.data:
            qs = [qc.find_bit(q).index for q in inst.qubits]
            if all(4 * link <= q < 4 * link + 4 for q in qs):
                sub.append(inst.operation, [q - 4 * link for q in qs])
        # every gate of qc touches exactly one link
        nl = sum(1 for inst in qc.data if all(4 * link <= qc.find_bit(q).index < 4 * link + 4 for q in inst.qubits))
        U = Operator(sub).data
        assert np.abs(U - np.diag(np.diag(U))).max() < 1e-15
        d = np.diag(U)
        for c in SING: maxdev = max(maxdev, abs(d[c] - 1))
        for c in QUART: maxdev = max(maxdev, abs(d[c] - np.exp(-0.75j * alpha)))
        invalid[link] = {int(c): complex(d[c]) for c in range(16) if c not in SING + QUART}
        rec[f"gates_on_link{link}"] = nl
    rec["per_link_max_dev_valid_codes"] = maxdev
    rec["invalid_code_phases_link0"] = {k: [v.real, v.imag] for k, v in invalid[0].items()}
    # (2) full 16-qubit Statevector on random valid inner codes vs exp(-i alpha 3/4 #Q)
    rng = np.random.default_rng(203)
    dev = 0.0
    for _ in range(40):
        types = rng.integers(0, 6, 4)
        code = sum(([3, 12, 5, 6, 9, 10][t]) << (4 * l) for l, t in enumerate(types))
        sv = Statevector.from_int(code, 2 ** 16).evolve(qc).data
        nq = sum(t >= 2 for t in types)
        expect = np.exp(-0.75j * alpha * nq)
        dev = max(dev, abs(sv[code] - expect), np.abs(np.delete(sv, code)).max())
    rec["statevector_16q_40_codes_max_dev"] = dev
    # (3) counts
    m = logical_metrics(qc); ops = dict(qc.count_ops())
    rec["inner"] = dict(count_ops=ops, logical=dict(cx=m["cx"], n_rot=m["n_rot"], depth=qc.depth(), t_fixed=m["t_fixed"]))
    qo = build_UE(alpha, with_outer=True); mo = logical_metrics(qo)
    qe = build_UE(alpha, with_outer=True, include_outer_electric=True); me = logical_metrics(qe)
    rec["with_outer_no_row"] = dict(num_qubits=qo.num_qubits, count_ops=dict(qo.count_ops()), cx=mo["cx"], n_rot=mo["n_rot"])
    rec["with_outer_row"] = dict(count_ops=dict(qe.count_ops()), cx=me["cx"], n_rot=me["n_rot"], depth=qe.depth())
    rec["outer_row_separately"] = dict(cx=me["cx"] - m["cx"], n_rot=me["n_rot"] - m["n_rot"])
    # (4) outer row: every gate on one outer link acts only inside the link; per-link diag; physical outer codes (4 per link, near end L or R)
    ok = True; vals = {}
    for link in range(4, 12):
        sub = QuantumCircuit(4)
        for inst in qe.data:
            qs = [qe.find_bit(q).index for q in inst.qubits]
            if all(4 * link <= q < 4 * link + 4 for q in qs): sub.append(inst.operation, [q - 4 * link for q in qs])
        U = Operator(sub).data
        assert np.abs(U - np.diag(np.diag(U))).max() < 1e-15
        d = np.diag(U)
        # valid outer patterns: near L: (near,far) = (L state, far R fixed): A: L=11,R=00 ; B: L=00,R=11 ; Q near L: L in {01,10 ints 1,2}, R=int1 ->R1 set
        # codes = L1 + 2 L2 + 4 R1 + 8 R2 ; list all with L-end/R-end occupancies: A=3, B=12, Q = single colour each end
        for c in SING: ok &= abs(d[c] - 1) < 1e-15
        for c in QUART: ok &= abs(d[c] - np.exp(-0.75j * alpha)) < 1e-15
    rec["outer_links_valid_codes_phase_ok"] = bool(ok)
    # outer far-end/near-end physical codes of a Q outer link: near L (colour 1 or 2) far R colour 1 ; near R, far L colour 1 -> all four are quartet codes
    near_L_Q = [(c1 + 4 * 1) for c1 in (1, 2)]   # L single colour (int 1 or 2), R int 1 -> code = L + 4*R
    near_R_Q = [1 + 4 * c2 for c2 in (1, 2)]
    rec["outer_Q_physical_codes_are_quartet_codes"] = set(near_L_Q + near_R_Q) <= set(QUART)
    out["alphas"][str(alpha)] = rec
    print(alpha, json.dumps(rec, default=str)[:1800])
json.dump(out, open("results/rishon/tester-203-ue-check.json", "w"), indent=1, default=str)
