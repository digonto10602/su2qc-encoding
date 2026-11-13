"""Tester 408 (c): certify no-rewrite rule, volatile-provenance tolerance, real changes still produce certs. Temp dir only."""
import json, sys, time, tempfile, pathlib, copy, os, subprocess
sys.path.insert(0, "src")
from qiskit import QuantumCircuit
from su2plaq.encodings.lsh import LSH
from su2plaq.lsh import lean_export as LE
from su2plaq.circuits.lsh import build_step

out = {}
enc = LSH()
tmp = pathlib.Path(tempfile.mkdtemp(prefix="t408-", dir="scratch/tester"))
def snap(): return {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in tmp.glob("*.json")}
qc = build_step(0.37, 0.61, 1, with_outer=True)
r1 = LE.certify(qc, enc, "step", 0.37, 0.61, 1, out_dir=tmp); s1 = snap()
time.sleep(0.05)
r2 = LE.certify(qc, enc, "step", 0.37, 0.61, 1, out_dir=tmp); s2 = snap()
out["1_same_twice"] = {"status": [r1["status"], r2["status"]], "files": sorted(s1), "bytes_and_mtime_identical": s1 == s2,
                       "pending_files_left": [p.name for p in tmp.glob("*pending*")]}
cid = r1["cert_path"].split("/")[-1]
c1 = json.loads(open(r1["cert_path"]).read())
out["1_binding_fields_present"] = {"gates_sha256": c1.get("gates_sha256") == c1["program_sha256"], "git_dirty": c1["provenance"].get("git_dirty")}
# 2 extra provenance
ex = {"entry_id": "t-1", "program_file_sha256": "ab" * 32}
r3 = LE.certify(qc, enc, "step", 0.37, 0.61, 1, out_dir=tmp, extra_provenance=ex); s3 = snap()
c3 = json.loads(open(r3["cert_path"]).read())
out["2_extra_added_rewrites"] = {"rewritten": s3 != s2, "has_fields": all(c3["provenance"].get(k) == v for k, v in ex.items()), "status": r3["status"]}
time.sleep(0.05)
r4 = LE.certify(qc, enc, "step", 0.37, 0.61, 1, out_dir=tmp, extra_provenance=ex); s4 = snap()
out["2_extra_same_no_rewrite"] = (s4 == s3)
ex2 = dict(ex, entry_id="t-2")
r5 = LE.certify(qc, enc, "step", 0.37, 0.61, 1, out_dir=tmp, extra_provenance=ex2); s5 = snap()
out["2_extra_changed_rewrites"] = {"rewritten": s5 != s4, "entry_id": json.loads(open(r5["cert_path"]).read())["provenance"]["entry_id"]}
# 3 a genuinely different circuit: identity pair appended (new gate list) -> new cert name, certified
qc2 = qc.copy(); qc2.x(0); qc2.x(0)
r6 = LE.certify(qc2, enc, "step", 0.37, 0.61, 1, out_dir=tmp); s6 = snap()
out["3_different_circuit_new_cert"] = {"status": r6["status"], "new_file": sorted(set(s6) - set(s5)), "old_files_unchanged": all(s6[k] == s5[k] for k in s5)}
# 3b a wrong circuit: extra X on a data qubit -> rejected, own file
qc3 = qc.copy(); qc3.x(1)
r7 = LE.certify(qc3, enc, "step", 0.37, 0.61, 1, out_dir=tmp)
out["3b_wrong_circuit"] = {"status": r7["status"], "reason": str(r7["reason"])[:100]}
# 4 tamper on disk (same name) -> replaced by fresh and certified
p = pathlib.Path(r1["cert_path"]); d = json.loads(p.read_text())
d["phase"]["m"] = [d["phase"]["m"][0] + 1, d["phase"]["m"][1]]; p.write_text(json.dumps(d, separators=(",", ":")))
tampered = p.read_bytes()
r8 = LE.certify(qc, enc, "step", 0.37, 0.61, 1, out_dir=tmp, extra_provenance=ex2)
out["4_tampered_existing_replaced"] = {"replaced": p.read_bytes() != tampered, "status": r8["status"]}
# tamper gates (angle exponent)
d = json.loads(p.read_text())
out["4b_gate_record_example"] = d["gates"][:3]
# 5 unit tests of _same_up_to_volatile
base = json.loads(p.read_text()); S = LE._same_up_to_volatile
def mut(f):
    x = copy.deepcopy(base); f(x); return S(base, x)
res = {}
res["volatile_git_commit_changes"] = mut(lambda x: x["provenance"].__setitem__("git_commit", "zzz"))
res["volatile_git_dirty_changes"] = mut(lambda x: x["provenance"].__setitem__("git_dirty", not x["provenance"]["git_dirty"]))
res["volatile_export_seconds_changes"] = mut(lambda x: x["provenance"].__setitem__("export_seconds", 99.0))
res["float_spread +1e-10 (tol 1e-9 -> same)"] = mut(lambda x: x["provenance"].__setitem__("float_phase_spread", x["provenance"]["float_phase_spread"] + 1e-10))
res["float_spread +1e-8 (-> different)"] = mut(lambda x: x["provenance"].__setitem__("float_phase_spread", x["provenance"]["float_phase_spread"] + 1e-8))
res["float_cross_check None->0 (-> different)"] = mut(lambda x: x["provenance"].__setitem__("float_phase_cross_check", 0.0))
res["phase m changed (-> different)"] = mut(lambda x: x["phase"].__setitem__("m", [x["phase"]["m"][0] + 1, x["phase"]["m"][1]]))
def gate_change(x):
    x["gates"][0]["q"] = [x["gates"][0]["q"][1], x["gates"][0]["q"][0]]
res["first cx control/target swapped (-> different)"] = mut(gate_change)
def angle_change(x):
    g = next(g for g in x["gates"] if "m" in g); g["m"] = [g["m"][0] + 1, g["m"][1]]
res["first rotation exponent m_alpha +1 (-> different)"] = mut(angle_change)

res["gates_sha256 changed (-> different)"] = mut(lambda x: x.__setitem__("gates_sha256", "0" * 64))
res["program_sha256 changed (-> different)"] = mut(lambda x: x.__setitem__("program_sha256", "0" * 64))
res["entry_id changed (-> different)"] = mut(lambda x: x["provenance"].__setitem__("entry_id", "other"))
res["extra key dropped (-> different)"] = mut(lambda x: x["provenance"].pop("entry_id"))
res["state term changed (-> different)"] = mut(lambda x: x["states"][0]["terms"][0].__setitem__("code", x["states"][0]["terms"][0]["code"] ^ 1))
res["target entry changed (-> different)"] = mut(lambda x: x["target"]["blocks"][0]["entries"][0].__setitem__(0, x["target"]["blocks"][0]["entries"][0][0] + 1))
res["n_qubits changed (-> different)"] = mut(lambda x: x.__setitem__("n_qubits", x["n_qubits"] + 1))
res["alpha_nominal changed (-> different)"] = mut(lambda x: x["provenance"].__setitem__("alpha_nominal", 0.5))
res["encoding changed (-> different)"] = mut(lambda x: x["provenance"].__setitem__("encoding", "x"))
res["identity"] = S(base, base)
out["5_same_up_to_volatile"] = res
out["commit"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
json.dump(out, open("results/lsh_tester/tester-408-certify-norewrite.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
import shutil; shutil.rmtree(tmp)
