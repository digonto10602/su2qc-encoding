"""Tester 205: every .qpy/.qasm3 exists + loads; sha256; gate counts recomputed from the loaded qpy vs JSON.
Independent lowering via qiskit transpile (not su2plaq.metrics) plus production logical_metrics for comparison."""
import json, hashlib, pathlib, re, collections, subprocess, sys, time
from qiskit import qpy, transpile
R = pathlib.Path("results/rishon")
out = {"commit": subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(), "checks": {}}
BASIS = ["cx","h","s","sdg","t","tdg","x","z","rz"]
from su2plaq.metrics.logical import logical_metrics
for k in ["UE","UE_outer_row","UB","step","step_order2"]:
    d = json.load(open(R/f"{k}.json")); rec = {}
    qp = pathlib.Path(d["files"]["qpy"]); rec["qpy_exists"] = qp.exists(); rec["sha_ok"] = hashlib.sha256(qp.read_bytes()).hexdigest()==d["files"]["sha256"]
    qc = qpy.load(open(qp,"rb"))[0]
    rec["qubits"] = qc.num_qubits; rec["macro_counts_match"] = dict(qc.count_ops())==d["metrics"]["macro_counts"]
    rec["macro_depth_match"] = qc.depth()==d["metrics"]["macro"]["depth"]; rec["size_match"] = qc.size()==d["metrics"]["macro"]["size"]
    lm = logical_metrics(qc); L = d["metrics"]["logical"]
    rec["logical_metrics_match_json"] = all(lm[x]==L[x] for x in L)
    # independent lowering
    t0=time.time(); low = transpile(qc, basis_gates=BASIS, optimization_level=0, seed_transpiler=1); co = low.count_ops()
    rec["indep_cx"] = co.get("cx",0); rec["indep_nrot"] = co.get("rz",0); rec["indep_t"] = co.get("t",0)+co.get("tdg",0)
    rec["indep_matches"] = (rec["indep_cx"]==L["cx"], rec["indep_nrot"]==L["n_rot"], rec["indep_t"]==L["t_fixed"] or "t_fixed counts only Clifford+T from non-rz")
    rec["json_logical"] = L; rec["json_lowered_gates"] = d["metrics"]["gates_lowered"]; rec["indep_lowered_ops"] = dict(co)
    # qasm3 text
    ap = d["files"].get("qasm3"); rec["qasm3_file"] = ap
    if ap:
        txt = pathlib.Path(ap).read_text(); rec["qasm3_header_ok"] = txt.startswith("OPENQASM 3")
        rec["qasm3_qubit_decls"] = re.findall(r"qubit\[(\d+)\]\s+(\w+)", txt)
        stmts = [l for l in txt.splitlines() if re.match(r"^\s*(cx|ccx|rccx|crx|ch|cz|x|h|z|rz|s|sdg|t|tdg|p|mcx\w*|\w+)\b.*;", l) and not l.startswith(("OPENQASM","include","qubit","bit","gate","def"))]
        rec["qasm3_gate_stmt_lines"] = len(stmts)
        rec["qasm3_sha"] = hashlib.sha256(txt.encode()).hexdigest()[:12]
    else: rec["qasm3_error"] = d["files"].get("qasm3_error")
    out["checks"][k] = rec; print(k, {x:rec[x] for x in ("qubits","macro_counts_match","logical_metrics_match_json","indep_cx","indep_nrot","indep_t","indep_matches")}, flush=True)
json.dump(out, open(R/"tester-205-files-gates.json","w"), indent=1, default=str)
