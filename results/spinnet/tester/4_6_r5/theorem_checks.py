"""Tester 118: theorem file lean/certs/spinnet-best-step.lean (step 4.L1/4.L2). (1) embedded JSON == results/spinnet/certs/spinnet-step-o1-ec21654efa8e.json byte for byte,
sha pin; (2) compiled checker ACCEPT on it; the embedded certificate is the headline r02-F1-002's (program sha, circuit_id, own re-export from the archived program);
(3) write_theorem_file refuses tampered states / target / names / multi-line comments, and accepts the real one (output byte-identical to the committed file apart from the comment);
(4) elaboration of a hand-built theorem file from a TAMPERED certificate (gate dropped; one state amplitude; target entry) must fail (native_decide false)."""
import sys, json, re, copy, hashlib, pathlib, subprocess, os
from su2plaq.spinnet import loop; loop.install()
from su2plaq.spinnet import lean_export as LE
from su2plaq.compress.spec import default_spec
from su2plaq.encodings.spinnet import SpinNet
root = pathlib.Path(sys.argv[1]); W = root/"results/spinnet/tester/4_6_r5/theorem"; W.mkdir(exist_ok=True, parents=True)
env = {**os.environ, "PATH": str(pathlib.Path.home()/".local/bin") + ":" + str(pathlib.Path.home()/".elan/bin") + ":" + os.environ["PATH"]}
out = {}
tf = (root/"lean/certs/spinnet-best-step.lean").read_text()
m = re.search(r'^def certJson : String := "(.*)"$', tf, re.M); lit = m.group(1)
# unescape Lean string literal (only \\ and \")
emb = lit.replace('\\"', '"').replace('\\\\', '\\')
cert = (root/"results/spinnet/certs/spinnet-step-o1-ec21654efa8e.json").read_text()
out["embedded_equals_cert_file"] = emb == cert
out["cert_sha256"] = hashlib.sha256(cert.encode()).hexdigest(); out["header_sha_in_theorem_file"] = re.search(r"certificate sha256 ([0-9a-f]{64})", tf).group(1)
out["first_line"] = tf.splitlines()[0]; out["theorem_lines"] = [l for l in tf.splitlines() if l.startswith(("theorem", "#print", "import"))]
d = json.loads(cert); out["n_gates"], out["n_states"], out["n_qubits"], out["circuit_id"] = len(d["gates"]), len(d["states"]), d["n_qubits"], d["circuit_id"]
ent = json.load(open(root/"compress/archive/spinnet/entries/r02-F1-002.json")); out["archive_program_sha"] = ent["program_sha256"]; out["theorem_first_line_names_sha"] = ent["program_sha256"] in tf.splitlines()[0]
out["archive_lean"] = ent["lean"]
exe = root/"lean/.lake/build/bin/su2plaq_cert_spinnet"
chk = lambda p: (subprocess.run([str(exe), "check", str(p)], capture_output=True, text=True).stdout.strip().splitlines() or ["?"])[0]
(W/"embedded.json").write_text(emb); out["checker_on_embedded"] = chk(W/"embedded.json")
# own re-export of the archived headline program
f = root/ent["program_path"]; ns = {}; exec(compile(f.read_text(), str(f), "exec"), ns)
qc = ns["build"](default_spec("spinnet", "step").with_angles(0.37, 0.61)).circuit()
new = json.loads(pathlib.Path(LE.export_certificate(qc, SpinNet(), "step", 0.37, 0.61, 1, W/"reexport.json")).read_text())
out["reexport_same_circuit_id"] = new["circuit_id"] == d["circuit_id"]; out["reexport_fields_differing_except_provenance"] = [k for k in new if k != "provenance" and new[k] != d[k]]
# (3) write_theorem_file refusals
def attempt(name, mut, tname="spinnet_best", comment=None):
    c = copy.deepcopy(d); mut(c); p = W/f"{name}.json"; p.write_text(json.dumps(c, separators=(",", ":")))
    try: LE.write_theorem_file(p, tname, W/f"{name}.lean", comment); return "WRITTEN"
    except ValueError as e: return "REFUSED: " + str(e)[:110]
def amp(c): t = c["states"][5]["terms"][0]; t["c"] = json.loads(json.dumps(t["c"])); 
def amp2(c):
    t = c["states"][5]["terms"][0]["c"]; k = next(kk for kk, v in t.items() if isinstance(v, list) or isinstance(v, int)) if isinstance(t, dict) else None
    c["states"][5]["terms"][0]["code"] ^= 1
def tgt(c):
    b = c["target"]["blocks"][3]["entries"][0]; b[0], b[1] = b[1] + 1, b[0]
def tgt2(c): c["target"]["blocks"][0]["entries"].pop()
def drop_state(c): c["states"].pop()
def dup_state(c): c["states"][1]["k"] = c["states"][0]["k"]
ref = {}
ref["states: term code flipped"] = attempt("t_state_code", amp2)
ref["states: one state dropped"] = attempt("t_state_drop", drop_state)
ref["states: duplicate index"] = attempt("t_state_dup", dup_state)
ref["target: entry indices changed"] = attempt("t_target_idx", tgt)
ref["target: block entry dropped"] = attempt("t_target_drop", tgt2)
ref["name: too long"] = attempt("t_name_long", lambda c: None, "spinnet_best_xxxxxxxxx")
ref["name: injection"] = attempt("t_name_inj", lambda c: None, "a b:=by sorry --")
ref["name: empty"] = attempt("t_name_empty", lambda c: None, "")
ref["comment: newline"] = attempt("t_comment_nl", lambda c: None, "spinnet_best", "x\nimport Evil")
ref["not a cert (schema)"] = attempt("t_schema", lambda c: c.__setitem__("schema", "other"))
out["refusals"] = ref
# accepted: real cert -> byte-compare against committed file
LE.write_theorem_file(root/"results/spinnet/certs/spinnet-step-o1-ec21654efa8e.json", "spinnet_best", W/"regen.lean", "entry r02-F1-002, program sha256 " + ent["program_sha256"])
out["regenerated_equals_committed_file"] = (W/"regen.lean").read_text() == tf
# (4) elaborate hand-built theorem files from tampered certificates (bypass the writer) -> must FAIL
def hand(name, c):
    text = json.dumps(c, separators=(",", ":")); l = text.replace("\\", "\\\\").replace('"', '\\"')
    (root/f"lean/certs/_tester118_{name}.lean").write_text("import Su2PlaqCert.SpinNet.Check\n\n" f'def certJson : String := "{l}"\n\ntheorem tt : Su2PlaqCert.SpinNet.checkJsonString certJson = true := by native_decide\n\n#print axioms tt\n')
res = {}
def gate_drop(c): del c["gates"][40]
def rz_shift(c): [g for g in c["gates"] if g["g"] == "rz"][0]["m"][1] += 2
def state_change(c): c["states"][7]["terms"][0]["code"] ^= 1
def tgt_change(c): c["target"]["blocks"][2]["entries"][0][0] += 1
muts = {"gate_dropped": gate_drop, "rz_shifted": rz_shift, "state_term_code_flipped": state_change, "target_entry_index_changed": tgt_change, "untampered_control": lambda c: None}
for n, fn in muts.items():
    c = copy.deepcopy(d); fn(c); hand(n, c); (W/f"hand_{n}.json").write_text(json.dumps(c, separators=(",", ":")))
    p = subprocess.run(["lake", "env", "lean", f"certs/_tester118_{n}.lean"], cwd=root/"lean", capture_output=True, text=True, env=env, timeout=900)
    res[n] = {"rc": p.returncode, "checker_cli": chk(W/f"hand_{n}.json"), "msg": (p.stdout + p.stderr).strip().splitlines()[:2]}
    (root/f"lean/certs/_tester118_{n}.lean").unlink()
out["hand_built_theorem_files"] = res
json.dump(out, open(W.parent/"theorem_checks.json", "w"), indent=1); print(json.dumps(out, indent=1))
