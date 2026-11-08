"""Tester 113: (1) static import check with the evaluator's own scanner AND an independent ast pass (module + imported names); (2) F1 certificate:
re-export from archived program, compare, compiled checker accept, tamper probes must REJECT."""
import sys, json, ast, copy, pathlib, subprocess, hashlib
from su2plaq.spinnet import loop; loop.install()
from su2plaq.compress import evaluate as EV
from su2plaq.spinnet import lean_export as LE
from su2plaq.compress.spec import default_spec
root = pathlib.Path(sys.argv[1]); T = pathlib.Path(sys.argv[2]); T.mkdir(parents=True, exist_ok=True)
out = {"static": {}, "lean": {}}
ALLOWED = EV.ALLOWED_IMPORTS; PROJ = EV.ALLOWED_PROJECT_IMPORTS
for eid in ["r02-F1-002","r02-F2-002","r02-F3-002","r02-F5-002"]:
    ent = json.load(open(root/f"compress/archive/spinnet/entries/{eid}.json")); src = (root/ent["program_path"]).read_text()
    try: EV._scan_source(src); ev = "accepted"
    except Exception as e: ev = f"REJECTED {e}"
    mods = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import): mods += [(a.name, None) for a in n.names]
        elif isinstance(n, ast.ImportFrom): mods += [(n.module, a.name) for a in n.names]
    bad = []
    for m, nm in mods:
        full = m if nm is None else f"{m}.{nm}"
        ok = (m.split(".")[0] in ALLOWED) or (m in PROJ) or (full in PROJ)
        if not ok: bad.append(full)
    forb = sorted({n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name) and n.id in EV.FORBIDDEN_NAMES})
    out["static"][eid] = {"evaluator_scan": ev, "imports": [f"{m}:{nm}" for m, nm in mods], "own_non_whitelisted": bad, "forbidden_names": forb}
    print(eid, out["static"][eid], flush=True)
exe = LE.project.LEAN_DIR / ".lake/build/bin/su2plaq_cert_spinnet"
def chk(p):
    r = subprocess.run([str(exe), "check", str(p)], capture_output=True, text=True, timeout=300)
    return (r.stdout.strip().splitlines() or [r.stderr[-200:]])[0]
ent = json.load(open(root/"compress/archive/spinnet/entries/r02-F1-002.json"))
cert_path = pathlib.Path(ent["lean"]["cert_path"]); old = json.load(open(cert_path))
out["lean"]["archived_cert"] = str(cert_path); out["lean"]["cert_sha256"] = hashlib.sha256(cert_path.read_bytes()).hexdigest()
out["lean"]["checker_sha256"] = hashlib.sha256(exe.read_bytes()).hexdigest()
out["lean"]["check_archived"] = chk(cert_path)
import importlib.util
ns = {}; f = root/ent["program_path"]; exec(compile(f.read_text(), str(f), "exec"), ns)
qc = ns["build"](default_spec("spinnet","step").with_angles(0.37,0.61)).circuit()
from su2plaq.encodings.spinnet import SpinNet
new_p = LE.export_certificate(qc, SpinNet(), "step", 0.37, 0.61, 1, T/"F1-reexport.json")
new = json.loads(pathlib.Path(new_p).read_text())
out["lean"]["same_circuit_id"] = new["circuit_id"] == old["circuit_id"]
out["lean"]["fields_differing_besides_provenance"] = [k for k in new if k != "provenance" and new[k] != old[k]]
out["lean"]["check_reexport"] = chk(new_p)
out["lean"]["n_gates"] = len(old["gates"]); out["lean"]["n_states"] = len(old["states"]); out["lean"]["schema"] = old.get("schema")
muts = {}
def run(name, f):
    d = copy.deepcopy(old); r = f(d); p = T/f"F1-mut-{name}.json"; p.write_text(json.dumps(d, separators=(",", ":"))); muts[name] = chk(p)
def first(d, g, fn):
    for x in d["gates"]:
        if x["g"] == g: fn(x); return
    raise RuntimeError(g)
def drop_mid(d): del d["gates"][len(d["gates"])//2]
def swapcx(d): first(d, "cx", lambda x: x.__setitem__("q", x["q"][::-1]))
def rzp(d): first(d, "rz", lambda x: x["m"].__setitem__(1, x["m"][1] + 2))
def tdgt(d): first(d, "tdg", lambda x: x.__setitem__("g", "t"))
def phase(d): d["phase"]["m"] = [d["phase"]["m"][0] + 1, d["phase"]["m"][1]]
def dropstate(d): d["states"] = d["states"][:-1]
def swap_last_two_cx_targets(d):
    cxs = [x for x in d["gates"] if x["g"] == "cx"]; cxs[-1]["q"], cxs[-2]["q"] = cxs[-2]["q"], cxs[-1]["q"]
def insert_x(d): d["gates"].insert(5, {"g": "x", "q": [0]})
def rm_rccx_half(d):
    for i, x in enumerate(d["gates"]):
        if x["g"] == "tdg": del d["gates"][i]; return
def beta_rot(d):
    # change the last rz by one unit in a different slot
    rz = [x for x in d["gates"] if x["g"] == "rz"]; rz[-1]["m"][1] += 2
for n, fn in (("drop_middle_gate", drop_mid), ("swap_first_cx", swapcx), ("rz_plus_unit", rzp), ("tdg_to_t", tdgt), ("phase_shift", phase),
              ("drop_state", dropstate), ("swap_last_two_cx", swap_last_two_cx_targets), ("insert_x", insert_x), ("remove_first_tdg", rm_rccx_half), ("last_rz_plus_unit", beta_rot)):
    try: run(n, fn)
    except Exception as e: muts[n] = f"MUTATION-SETUP-ERROR {e!r}"
out["lean"]["mutations"] = muts
print(json.dumps(out["lean"], indent=1), flush=True)
json.dump(out, open(pathlib.Path(__file__).with_name("static_and_lean.json"), "w"), indent=1)
