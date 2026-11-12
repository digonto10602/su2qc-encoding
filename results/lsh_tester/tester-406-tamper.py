"""Tester 406: tampered certificates against the compiled su2plaq_cert_lsh checker.
Run: taskset -c 14-19 tools/run-capped python results/lsh_tester/tester-406-tamper.py"""
import copy, json, pathlib, subprocess, sys, time
sys.path.insert(0, "src")
from su2plaq.lsh import lean_export as LE
exe = LE.checker_exe()
base = json.load(open("results/lsh/certs/lsh-step-o1-ddc1571c27bd.json"))
td = pathlib.Path("scratch/tester406tamper"); td.mkdir(parents=True, exist_ok=True)

def run(name, c, expect="REJECT"):
    p = td / (name + ".json"); p.write_text(json.dumps(c, separators=(",", ":")))
    t0 = time.time()
    r = subprocess.run([str(exe), "check", str(p)], capture_output=True, text=True, timeout=900)
    line = (r.stdout.strip().splitlines() or [""])[0]
    ok = line.startswith(expect)
    print(("PASS " if ok else "FAIL ") + f"{name:42s} rc={r.returncode} {time.time()-t0:5.2f}s  {line[:110]}")
    return {"name": name, "line": line, "rc": r.returncode, "ok": ok}

M = lambda: copy.deepcopy(base)
out = [run("untampered", M(), "ACCEPT")]
# --- gates
def gate_idx(c, g): return [i for i, x in enumerate(c["gates"]) if x["g"] == g]
c = M(); i = gate_idx(c, "cx")[10]; c["gates"][i]["q"] = [c["gates"][i]["q"][0], (c["gates"][i]["q"][1] + 1) % 12]; out.append(run("gate_cx_target_changed", c))
c = M(); i = gate_idx(c, "cx")[40]; c["gates"][i]["q"].reverse(); out.append(run("gate_cx_reversed", c))
c = M(); i = gate_idx(c, "t")[3]; c["gates"][i]["g"] = "tdg"; out.append(run("gate_t_to_tdg", c))
c = M(); i = gate_idx(c, "h")[7]; c["gates"][i]["g"] = "x"; out.append(run("gate_h_replaced_by_x", c))
c = M(); i = gate_idx(c, "rz")[0]; c["gates"][i]["m"] = [c["gates"][i]["m"][0], c["gates"][i]["m"][1] + 1]; out.append(run("gate_rz_exponent_plus1", c))
c = M(); i = gate_idx(c, "rz")[1]; c["gates"][i]["m"] = [c["gates"][i]["m"][0] + 1, c["gates"][i]["m"][1]]; out.append(run("gate_rz_alpha_exponent_plus1", c))
c = M(); i = gate_idx(c, "p")[0]; c["gates"][i]["m"] = [-2, 0]; out.append(run("gate_p_exponent_changed", c))
c = M(); del c["gates"][gate_idx(c, "cx")[20]]; out.append(run("gate_removed", c))
c = M(); c["gates"].append({"g": "x", "q": [5]}); out.append(run("gate_appended_x_on_data", c))
c = M(); c["gates"].append({"g": "x", "q": [14]}); out.append(run("gate_appended_x_on_outer", c))
c = M(); c["gates"].append({"g": "x", "q": [28]}); out.append(run("gate_appended_x_on_ancilla", c))
c = M(); c["gates"].insert(0, {"g": "x", "q": [28]}); out.append(run("gate_prepended_x_on_ancilla", c))
c = M(); c["gates"][5]["q"] = [99, 1] if len(c["gates"][5]["q"]) == 2 else [99]; out.append(run("gate_qubit_out_of_range", c))
# --- states
c = M(); c["states"].pop(); out.append(run("state_removed_last", c))
c = M(); c["states"].pop(100); out.append(run("state_removed_middle", c))
c = M(); c["states"][7], c["states"][8] = c["states"][8], c["states"][7]; out.append(run("states_swapped", c))
c = M(); c["states"][50]["terms"][0]["code"] ^= 1; out.append(run("state_code_flipped_bit", c))
c = M(); c["states"][50]["terms"][0]["c"][0] = "-1"; out.append(run("state_sign_flipped", c))
c = M(); c["states"][50]["terms"].append({"code": 1 << 26, "c": ["1"] + ["0"] * 7}); out.append(run("state_support_on_ancilla", c))
c = M(); c["states"].append(copy.deepcopy(c["states"][0])); out.append(run("state_duplicated_extra", c))
c = M(); c["states"][3] = copy.deepcopy(c["states"][4]); out.append(run("state_replaced_by_other", c))
# --- target
c = M(); e = c["target"]["blocks"][0]["entries"][0][2][0][1]; e[0] = "1/3"; out.append(run("target_coeff_changed", c))
c = M(); c["target"]["blocks"][5]["entries"][0][2][0][0][1] += 1; out.append(run("target_exponent_changed", c))
c = M(); c["target"]["blocks"][5]["entries"].pop(); out.append(run("target_entry_removed", c))
c = M(); c["target"]["blocks"].pop(); out.append(run("target_block_removed", c))
c = M(); c["target"]["blocks"][0]["ks"] = c["target"]["blocks"][0]["ks"][::-1]; out.append(run("target_ks_reversed", c))
c = M(); c["target"]["kind"] = "UB"; out.append(run("target_kind_label_changed", c))
c = M(); c["target"]["order"] = 2; out.append(run("target_order_label_changed", c))
# --- phase / base
c = M(); c["phase"]["m"] = [1, 0]; out.append(run("phase_m_changed", c))
c = M(); c["phase"]["k"] = ["0", "1"] + ["0"] * 6; out.append(run("phase_k_changed", c))
c = M(); c["base"]["d_beta"] = 8; out.append(run("base_dbeta_8", c))
c = M(); c["base"]["d_alpha"] = 3; out.append(run("base_dalpha_3", c))
# --- registers
c = M(); c["n_data"] = 11; out.append(run("n_data_11", c))
c = M(); c["n_outer"] = 11; out.append(run("n_outer_11", c))
c = M(); c["n_data"] = 8; c["n_outer"] = 8; out.append(run("n_data_outer_8_spinnet", c))
c = M(); c["n_qubits"] = 20; out.append(run("n_qubits_20", c))
c = M(); c["n_qubits"] = 63; out.append(run("n_qubits_63", c))
c = M(); c["n_qubits"] = 30; out.append(run("n_qubits_30_ancilla_use", c))
c = M(); c["schema"] = "su2plaq-cert-2"; out.append(run("schema_changed", c))
# --- spin-network cert fed to the LSH checker and vice versa
sn = sorted(pathlib.Path("results/spinnet/certs").glob("spinnet-step-o1-*.json"))[0]
r = subprocess.run([str(exe), "check", str(sn)], capture_output=True, text=True); print("spinnet cert -> lsh checker:", r.stdout.strip()[:110])
out.append({"name": "spinnet_cert_in_lsh_checker", "line": r.stdout.strip(), "ok": r.stdout.startswith("REJECT")})
sx = LE.CERT_DIR.parent.parent.parent / "lean/.lake/build/bin/su2plaq_cert_spinnet"
r = subprocess.run([str(sx), "check", "results/lsh/certs/lsh-step-o1-ddc1571c27bd.json"], capture_output=True, text=True); print("lsh cert -> spinnet checker:", r.stdout.strip()[:110])
out.append({"name": "lsh_cert_in_spinnet_checker", "line": r.stdout.strip(), "ok": r.stdout.startswith("REJECT")})
json.dump(out, open("results/lsh_tester/tester-406-tamper.json", "w"), indent=1)
print("accepted-as-expected:", sum(o["ok"] for o in out), "/", len(out))
