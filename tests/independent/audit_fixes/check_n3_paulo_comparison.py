"""N3: recompute the Paulo comparison numbers independently of su2plaq.metrics (own Qiskit pass-manager call, own pygridsynth loop)
and compare with results/twelve/UB.json.
Usage: PYTHONPATH=src python tests/independent/audit_fixes/check_n3_paulo_comparison.py results/m1_audit_fixes_n3.json"""
import sys, json, math, subprocess, warnings
import numpy as np
warnings.filterwarnings("ignore")
import mpmath
from qiskit import transpile
from qiskit.transpiler import generate_preset_clifford_t_pass_manager
from pygridsynth.gridsynth import gridsynth_gates
from su2plaq.circuits.twelve import build_UB, paulo_logical

out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip() + "+uncommitted", "checks": {}}
J = json.load(open("results/twelve/UB.json"))
PC = J["extra"]["paulo_comparison"]
meta = json.load(open("refs/paulo/_metadata.json")) if __import__("os").path.exists("refs/paulo/_metadata.json") else None
print("paulo metadata:", meta)
def rec(name, expected, got, tol=0):
    ok = abs(expected - got) <= tol
    out["checks"][name] = dict(expected=expected, got=got, tol=tol, ok=bool(ok)); print(("PASS" if ok else "FAIL"), name, "| JSON/claimed:", expected, "| mine:", got, flush=True)

# --- (a) Qiskit Clifford+T pass manager, Paulo's settings, own call
def my_ct(qc, eps):
    pm = generate_preset_clifford_t_pass_manager(basis_gates=["cx", "h", "s", "sdg", "t", "tdg"], optimization_level=3,
            rz_synthesis_config={"rz_synthesis_error": eps, "rz_cache_error": eps / 10}, seed_transpiler=12345, qubits_initially_zero=False)
    o = pm.run(qc); c = o.count_ops(); return c.get("t", 0) + c.get("tdg", 0), c.get("cx", 0)
ours = build_UB(1.0)
t_o, cx_o = my_ct(ours, 1e-6)
j = PC["our_UB_beta_1"]["qiskit_clifford_t_pm_paulo_settings_eps_1e-6"]
rec("ours via Qiskit CT (T)", j["t"], t_o); rec("ours via Qiskit CT (CX)", j["cx"], cx_o)
rec("ours via CT: T == 662 (task statement)", 662, t_o); rec("ours via CT: CX == 294", 294, cx_o)
t_p, cx_p = my_ct(paulo_logical(1.0), 1e-6)
rec("paulo_logical via same CT (T)", 1162, t_p); rec("paulo_logical via same CT (CX)", 294, cx_p)
# his compiled file as shipped
from su2plaq.circuits.twelve import paulo_circuit
pc = paulo_circuit().count_ops()
rec("Paulo's shipped file T", 1162, pc.get("t", 0) + pc.get("tdg", 0)); rec("Paulo's shipped file CX", 294, pc.get("cx", 0))
out["ours_ct"] = dict(t=t_o, cx=cx_o); out["paulo_logical_ct"] = dict(t=t_p, cx=cx_p)

# --- (b) pygridsynth tables, own implementation
def table(qc, eps_list):
    w = transpile(qc, basis_gates=["cx", "h", "s", "sdg", "t", "tdg", "x", "z", "rz"], optimization_level=0, seed_transpiler=1, qubits_initially_zero=False)
    ops = w.count_ops(); tfix = ops.get("t", 0) + ops.get("tdg", 0); angs = []
    for i in w.data:
        if i.operation.name == "rz":
            th = float(i.operation.params[0]); k = th / (math.pi / 4)
            if abs(k - round(k)) * (math.pi / 4) < 1e-9:
                tfix += int(round(k)) % 2
            else:
                angs.append(th)
    rows = []
    for eps in eps_list:
        tr = [str(gridsynth_gates(theta=mpmath.mpf(repr(th)), epsilon=mpmath.mpf(repr(eps)))).count("T") for th in angs]
        rows.append(dict(eps=eps, t_fixed=tfix, n_rot=len(angs), t_rot=sum(tr), t_total=tfix + sum(tr)))
    return rows
EPS = (1e-4, 1e-6, 1e-8, 1e-10)
mine_o, mine_p = table(ours, EPS), table(paulo_logical(1.0), EPS)
Jo = PC["our_UB_beta_1"]["t_table_pygridsynth"]; Jp = PC["paulo_logical_beta_1"]["t_table_pygridsynth"]
for e, ro, rp, jo, jp in zip(EPS, mine_o, mine_p, Jo, Jp):
    assert jo["eps"] == e and jp["eps"] == e
    rec(f"ours pygridsynth T_total eps={e:g}", jo["t_total"], ro["t_total"]); rec(f"ours n_rot eps={e:g}", jo["n_rot"], ro["n_rot"]); rec(f"ours t_fixed eps={e:g}", jo["t_fixed"], ro["t_fixed"])
    rec(f"Paulo-logical pygridsynth T_total eps={e:g}", jp["t_total"], rp["t_total"]); rec(f"Paulo n_rot eps={e:g}", jp["n_rot"], rp["n_rot"]); rec(f"Paulo t_fixed eps={e:g}", jp["t_fixed"], rp["t_fixed"])
for claimed, row in zip((564, 684, 812, 936), mine_o): rec(f"ours table value {claimed} (task statement) eps={row['eps']:g}", claimed, row["t_total"])
for claimed, row in zip((872, 1180, 1488, 1736), mine_p): rec(f"his table value {claimed} (task statement) eps={row['eps']:g}", claimed, row["t_total"])
out["ours_table"] = mine_o; out["paulo_table"] = mine_p
out["all_ok"] = all(v["ok"] for v in out["checks"].values()); print("ALL", out["all_ok"])
json.dump(out, open(sys.argv[1], "w"), indent=1)
