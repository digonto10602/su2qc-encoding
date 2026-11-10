"""Tester, step 3.6 (reports/tests/103): vendoring fidelity vs the sibling's spinnet_v2 source.
The sibling is loaded ONLY here (sys.path of the sibling checkout), never by production code.
Compares (1) the step lists, (2) the expanded gate lists gate by gate, (3) the gate counts vs the sibling's own JSON."""
import json, sys, subprocess
sys.path.insert(0, "src"); sys.path.insert(0, "/home/digonto/Projects/siblings/su2qc-trotter/src")
import numpy as np
from su2trotter.designs import spinnet_v2 as sib
from su2plaq.spinnet import trotter_v2 as ours
from su2plaq.circuits import spinnet as cs
from su2plaq.metrics.logical import logical_metrics

out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), "skeletons": {}}
for name in ("pairs9", "flags4", "flags5", "flags6"):
    r = {}
    s_steps = sib.SKELETONS[name]()
    s_frame = sib.SKELETON_FRAMES.get(name, sib.FRAME)
    o_steps, n_anc, o_frame = ours.SKELETONS[name]
    r["sib_wires_ints_anc"] = [list(sib.INTS), list(sib.ANC[:3])]
    # step lists: map the sibling's rccx_dg -> rccx
    conv = [("rccx",) + tuple(s[1:]) if s[0] == "rccx_dg" else tuple(s) for s in s_steps]
    r["steps_equal_after_rccx_dg_to_rccx"] = (conv == [tuple(s) for s in o_steps])
    r["n_steps_sib_ours"] = [len(s_steps), len(o_steps)]
    r["frame_equal"] = tuple(map(tuple, s_frame)) == tuple(map(tuple, o_frame))
    r["rc3x_dg_positions_equal"] = [i for i, s in enumerate(s_steps) if s[0] == "rc3x_dg"] == [i for i, s in enumerate(o_steps) if s[0] == "rc3x_dg"]
    r["n_rccx_dg_sib"] = sum(s[0] == "rccx_dg" for s in s_steps)
    # gate-by-gate: sibling circuit (alpha=2) vs ours expanded
    sc = sib.plaquette(2.0, name)
    sg = [(g.name, tuple(g.qubits), g.param) for g in sc.gates if g.name != "mark"] if hasattr(sc, "gates") else None
    r["sib_gate_names"] = sorted({g[0] for g in sg})
    qo = cs.trotter_v2_circuit(name, 2.0)
    from qiskit import transpile
    og = []
    for i in qo.data:                      # manual in-order expansion of rccx (decompose() re-sorts topologically)
        qs = tuple(qo.find_bit(q).index for q in i.qubits)
        if i.operation.name == "rccx":
            for j in i.operation.definition.data:
                og.append((j.operation.name if j.operation.name != "u2" else "u2", tuple(qs[i.operation.definition.find_bit(q).index] for q in j.qubits), (float(j.operation.params[0]) if j.operation.params else None)))
        else:
            og.append((i.operation.name, qs, (float(i.operation.params[0]) if i.operation.params else None)))
    r["ours_expanded_names"] = sorted({g[0] for g in og})
    # sibling rccx macros are already lowered (macro False by default?)
    r["n_gates_sib_ours"] = [len(sg), len(og)]
    same_skel = [(a[0], a[1]) for a in sg] == [(a[0], a[1]) for a in og]
    r["gate_names_qubits_identical"] = same_skel
    if same_skel:
        ratios = [(a[2], b[2]) for a, b in zip(sg, og) if a[0] == "rz"]
        r["rz_angles_sib_ours_beta2"] = ratios
        r["rz_angle_abs_equal"] = bool(all(abs(abs(a) - abs(b)) < 1e-12 for a, b in ratios))
        r["rz_angle_sign_flip_all"] = bool(all(abs(a + b) < 1e-12 for a, b in ratios))
        r["rz_angle_same_all"] = bool(all(abs(a - b) < 1e-12 for a, b in ratios))
    else:
        for k, (a, b) in enumerate(zip(sg, og)):
            if (a[0], a[1]) != (b[0], b[1]):
                r["first_mismatch"] = [k, a, b]; break
    lm = logical_metrics(cs.trotter_v2_circuit(name, 0.61))
    r["ours_metrics_beta0.61"] = {k: lm[k] for k in ("cx", "n_rot", "t_fixed", "ancilla", "depth")}
    sx = sum(1 for g in sg if g[0] == "cx"); stt = sum(1 for g in sg if g[0] in ("t", "tdg")); sr = sum(1 for g in sg if g[0] == "rz")
    r["sib_metrics"] = {"cx": sx, "t_fixed": stt, "n_rot": sr}
    out["skeletons"][name] = r
J = json.load(open("/home/digonto/Projects/siblings/su2qc-trotter/docs/compression/results_spinnet_v2.json"))
out["sibling_json_variants"] = list(J["variants"])
print(json.dumps(out, indent=1, default=str))
json.dump(out, open("results/spinnet/tester/m3_step_3_6_fidelity.json", "w"), indent=1, default=str)
