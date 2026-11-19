"""Tester 437: archive / round / stop / Lean-cert consistency of the real LSH round 0.  Run by hand under tools/run-capped."""
import hashlib, json, pathlib, subprocess, sys, tempfile
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, str(ROOT/"src"))
from su2plaq.compress import provenance
from su2plaq.compress.spec import get_encoding
from su2plaq.lsh import loop as LL, lean_export as LE
from su2plaq.compress import round as R
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
J = lambda p: json.load(open(ROOT/p))
out = {"commit": subprocess.run(["git","rev-parse","--short","HEAD"],capture_output=True,text=True,cwd=ROOT).stdout.strip(), "checks": {}}
C = out["checks"]
expect = {  # prompts/401 section 1.3
 "r00-seed-000": [94,598,880,31], "r00-seed-001": [74,864,1615,27], "r00-seed-002": [84,586,888,27], "r00-seed-003": [82,638,1027,27],
 "r00-seed-004": [76,690,1139,27], "r00-seed-005": [71,1118,2276,25], "r00-seed-006": [72,864,1570,25], "r00-seed-007": [74,690,1134,25],
 "r00-seed-010": [94,598,880,31], "r00-seed-qiskit_l3": [94,598,880,31]}
nrot = {"r00-seed-000":(8,88),"r00-seed-001":(13,56),"r00-seed-002":(8,80),"r00-seed-003":(9,72),"r00-seed-004":(10,64),"r00-seed-005":(17,48),"r00-seed-006":(13,56),"r00-seed-007":(10,64)}
code_hash = provenance.code_hash_for("lsh")
rnd = J("results/compress/lsh/round-000.json"); idx = J("compress/archive/lsh/index.json")
C["code_hash_for_lsh"] = code_hash
rows = {}
for eid, key in expect.items():
    e = J(f"compress/archive/lsh/entries/{eid}.json")
    cand = next(c for c in rnd["candidates"] if c["id"] == eid)
    r = {"valid": e["valid"], "key_archive": e["key"], "key_round": cand["key"], "key_expected": key,
         "keys_equal": e["key"] == key == cand["key"], "evaluator_hash_ok": e["evaluator_sha256"] == code_hash and e["encoding_sha256"] == code_hash,
         "reason": e["reason"], "family": e["family"], "round": e["round"]}
    m = e["metrics_raw"]; r["n_rot_t_fixed"] = (m["n_rot"], m["t_fixed"])
    if eid in nrot: r["nrot_tfixed_ok"] = tuple(nrot[eid]) == (m["n_rot"], m["t_fixed"])
    r["verdict_ok"] = e["verdict_nominal"]["ok"]; r["alt_ok"] = [v["ok"] for v in e["verdicts_alt"]]
    r["op_norm_error"] = e["verdict_nominal"]["op_norm_error"]
    if e["program_sha256"]:
        p = ROOT/e["program_path"]; r["file_sha"] = sha(p)
        r["sha_three_way"] = (sha(p) == e["program_sha256"] == cand["program_sha256"])
    else: r["sha_three_way"] = None; r["note"] = "circuit-valued seed, no program file"
    rows[eid] = r
C["entries"] = rows
C["round_hashes"] = {"evaluator": rnd["evaluator_sha256"] == code_hash, "encoding": rnd["encoding_sha256"] == code_hash,
                     "n_valid": rnd["n_valid"], "n_invalid": rnd["n_invalid"], "best_key": rnd["best_key"], "entries": rnd["entries"], "index_best": idx["best"], "index_n": idx["n_entries"]}
# pinned sources
pins = {}
sn_index = J("compress/archive/spinnet/index.json") if (ROOT/"compress/archive/spinnet/index.json").exists() else None
for lab, d in rnd["lsh"]["wrapped_sources"].items():
    p = ROOT/d["path"]; se = ROOT/f"compress/archive/spinnet/entries/{d['spinnet_entry']}.json"
    pins[lab] = {"file_sha": sha(p), "pin_sha": d["sha256"], "equal": sha(p) == d["sha256"],
                 "spinnet_entry_sha": (json.load(open(se)).get("program_sha256") if se.exists() else "entry missing"),
                 "git_tracked_unmodified": subprocess.run(["git","diff","--quiet","HEAD","--",d["path"]],cwd=ROOT).returncode == 0}
C["pins"] = pins
pe = [e for e in rnd["external"] if e.get("source") == "paulo15_wrapped"][0]
C["paulo15_wrapped"] = {"valid": pe["valid"], "cx": pe["metrics"]["cx"], "n_rot": pe["metrics"]["n_rot"], "t_fixed": pe["metrics"]["t_fixed"], "kind": pe["kind"], "beta": pe["beta"], "certified": pe["certified"], "total_error": pe["total_error"]}
C["external_sources"] = [e["source"] for e in rnd["external"]]
st = J("results/compress/lsh/stop.json"); C["stop"] = st
rb = J("results/compress/lsh/robust.json"); C["robust_entries"] = {k: {kk: vv for kk, vv in v.items() if kk in ("cx","t_sum","rho","qubits","key","robust_key","n_rot","t_fixed","valid")} for k, v in rb["entries"].items()}
C["robust_hash_ok"] = (rb["evaluator_sha256"] == code_hash, rb["encoding_sha256"] == code_hash)
# ---------------- Lean certificate
cp = ROOT/"results/lsh/certs/lsh-step-o1-975e51bd4fed.json"; c = json.load(open(cp))
best = J("compress/archive/lsh/entries/r00-seed-005.json"); bp = ROOT/best["program_path"]
L = {"cert_file_sha": sha(cp), "program_file_sha_in_cert": c["provenance"].get("program_file_sha256"), "program_file_sha_on_disk": sha(bp),
     "binding_ok": c["provenance"].get("program_file_sha256") == sha(bp) == best["program_sha256"], "entry_id_in_cert": c["provenance"].get("entry_id"),
     "archive_lean": best["lean"], "gates_sha_ok": c["gates_sha256"] == hashlib.sha256(json.dumps(c["gates"]).encode()).hexdigest() or None,
     "gates_sha256": c["gates_sha256"], "name_matches_sha": cp.stem.endswith(c["gates_sha256"][:12]), "n_states": len(c["states"]), "kind": c["target"]["kind"], "n_qubits": c["n_qubits"], "n_gates": len(c["gates"]),
     "git_dirty_in_cert": c["provenance"].get("git_dirty"), "provenance_commit": c["provenance"].get("git_commit")}
L["checker_recheck"] = LE.check_certificate(cp)
# independent re-export from the program file to scratch and compare gate list + target + states
sp = LL.spec()
circ, err = R._circuit_of(sp, bp, "r00-seed-005", None, ROOT, expected_sha256=best["program_sha256"])
assert circ is not None, err
tmp = pathlib.Path(sys.argv[1]); tmp.mkdir(parents=True, exist_ok=True)
res = LE.export_certificate(circ, get_encoding(sp.encoding), sp.kind, sp.alpha, sp.beta, sp.order, tmp/"reexport.json")
c2 = json.load(open(tmp/"reexport.json"))
L["reexport"] = {"result": str(res)[:100], "gates_equal": c2["gates"] == c["gates"], "target_equal": c2["target"] == c["target"], "states_equal": c2["states"] == c["states"], "phase_equal": c2["phase"] == c["phase"], "gates_sha_equal": c2["gates_sha256"] == c["gates_sha256"]}
L["reexport_check"] = LE.check_certificate(tmp/"reexport.json")
# negative control: swap one CX target in a copy -> must be rejected
import copy
t = copy.deepcopy(c); k = next(i for i, g in enumerate(t["gates"]) if g["g"] == "cx"); q = t["gates"][k]["q"]; t["gates"][k]["q"] = [q[1], q[0]]
(tmp/"forged.json").write_text(json.dumps(t, separators=(",", ":"))); L["negative_control_swapcx"] = LE.check_certificate(tmp/"forged.json")["status"]
C["lean"] = L
json.dump(out, open(ROOT/"results/tester/437-archive-checks.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str)[:12000])
