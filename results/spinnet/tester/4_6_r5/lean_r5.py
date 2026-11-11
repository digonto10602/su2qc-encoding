"""Tester 118: Lean certifiability of the three round-5 programs (now angle-linear): export from the archived program at (0.37,0.61),
compiled checker, tamper probes (circuit-changing -> REJECT; harmless -> ACCEPT), plus static import check (evaluator scanner + own ast)."""
import sys, json, ast, copy, pathlib, subprocess, hashlib, collections, time
from su2plaq.spinnet import loop; loop.install()
from su2plaq.compress import evaluate as EV
from su2plaq.spinnet import lean_export as LE
from su2plaq.compress.spec import default_spec
from su2plaq.encodings.spinnet import SpinNet
root = pathlib.Path(sys.argv[1]); T = root/"results/spinnet/tester/4_6_r5/certs"; T.mkdir(parents=True, exist_ok=True)
exe = LE.project.LEAN_DIR/".lake/build/bin/su2plaq_cert_spinnet"
out = {"checker_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(), "entries": {}}
ALLOWED = EV.ALLOWED_IMPORTS; PROJ = EV.ALLOWED_PROJECT_IMPORTS
def chk(p):
    r = subprocess.run([str(exe), "check", str(p)], capture_output=True, text=True, timeout=900)
    return (r.stdout.strip().splitlines() or [r.stderr[-200:]])[0]
for eid in sys.argv[2:]:
    ent = json.load(open(root/f"compress/archive/spinnet/entries/{eid}.json")); f = root/ent["program_path"]; src = f.read_text(); o = {}
    try: EV._scan_source(src); o["evaluator_scan"] = "accepted"
    except Exception as e: o["evaluator_scan"] = f"REJECTED {e}"
    mods = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import): mods += [(a.name, None) for a in n.names]
        elif isinstance(n, ast.ImportFrom): mods += [(n.module, a.name) for a in n.names]
    bad = [(m if nm is None else f"{m}.{nm}") for m, nm in mods if not ((m.split(".")[0] in ALLOWED) or m in PROJ or (m if nm is None else f"{m}.{nm}") in PROJ)]
    o["imports"] = [f"{m}:{nm}" for m, nm in mods]; o["own_non_whitelisted"] = bad
    o["forbidden_names"] = sorted({n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name) and n.id in EV.FORBIDDEN_NAMES})
    ns = {"__name__": "prog"}; exec(compile(src, str(f), "exec"), ns)
    qc = ns["build"](default_spec("spinnet", "step").with_angles(0.37, 0.61)).circuit()
    t0 = time.time(); r = LE.export_certificate(qc, SpinNet(), "step", 0.37, 0.61, 1, T/f"{eid}-export.json")
    if isinstance(r, str) and not r.endswith(".json"):
        o["export"] = r[:200]; out["entries"][eid] = o; print(eid, o, flush=True); continue
    cert = json.load(open(r)); o["export"] = "ok"; o["export_s"] = time.time()-t0; o["n_gates"] = len(cert["gates"]); o["n_states"] = len(cert["states"])
    o["gate_counts"] = dict(collections.Counter(x["g"] for x in cert["gates"])); o["circuit_id"] = cert.get("circuit_id"); o["n_qubits_cert"] = cert.get("n_qubits", cert.get("qubits"))
    t0 = time.time(); o["check"] = chk(r); o["check_s"] = time.time()-t0
    old = cert; muts = {}
    def run(name, fn):
        d = copy.deepcopy(old); fn(d); p = T/f"{eid}-mut-{name}.json"; p.write_text(json.dumps(d, separators=(",", ":"))); muts[name] = chk(p)
    def first(d, g, fn):
        for x in d["gates"]:
            if x["g"] == g: fn(x); return
        raise RuntimeError(g)
    gs = old["gates"]; cxi = [i for i, x in enumerate(gs) if x["g"] == "cx"]
    def drop_mid(d): del d["gates"][len(d["gates"])//2]
    def rev_first_cx(d): first(d, "cx", lambda x: x.__setitem__("q", x["q"][::-1]))
    def rz_plus(d): first(d, "rz", lambda x: x["m"].__setitem__(1, x["m"][1] + 2))
    def last_rz_plus(d): [x for x in d["gates"] if x["g"] == "rz"][-1]["m"].__setitem__(1, [x for x in d["gates"] if x["g"] == "rz"][-1]["m"][1] + 2)
    def tdg_t(d): first(d, "tdg", lambda x: x.__setitem__("g", "t"))
    def phase(d): d["phase"]["m"] = [d["phase"]["m"][0] + 1, d["phase"]["m"][1]]
    def dropstate(d): d["states"] = d["states"][:-1]
    def insx(d): d["gates"].insert(5, {"g": "x", "q": [0]})
    def rm_tdg(d):
        for i, x in enumerate(d["gates"]):
            if x["g"] == "tdg": del d["gates"][i]; return
    def p_plus(d): first(d, "p", lambda x: x["m"].__setitem__(0, x["m"][0] + 1))
    def s_sdg(d): first(d, "s", lambda x: x.__setitem__("g", "sdg"))
    def drop_last(d): del d["gates"][-1]
    def x_outer(d): d["gates"].insert(0, {"g": "x", "q": [8]})
    def x_anc(d): d["gates"].insert(0, {"g": "x", "q": [16]})
    def retarget_last(d):
        q = d["gates"][cxi[-1]]["q"]; d["gates"][cxi[-1]]["q"] = [q[0], (q[1]+1) % 8 if (q[1]+1) % 8 != q[0] else (q[1]+2) % 8]
    def rev_last_cx(d): d["gates"][cxi[-1]]["q"] = d["gates"][cxi[-1]]["q"][::-1]
    for n, fn in (("drop_middle_gate", drop_mid), ("reverse_first_cx", rev_first_cx), ("rz_plus_unit", rz_plus), ("last_rz_plus_unit", last_rz_plus), ("tdg_to_t", tdg_t),
                  ("phase_shift", phase), ("drop_state", dropstate), ("insert_x", insx), ("remove_first_tdg", rm_tdg), ("p_plus_unit", p_plus), ("s_to_sdg", s_sdg),
                  ("drop_last_gate", drop_last), ("x_on_outer_8", x_outer), ("x_on_ancilla_16", x_anc), ("retarget_last_cx", retarget_last), ("reverse_last_cx", rev_last_cx)):
        try: run(n, fn)
        except Exception as e: muts[n] = f"MUTATION-SETUP-ERROR {e!r}"
    # non-commuting adjacent cx swaps
    res = []
    for a, b in zip(cxi, cxi[1:]):
        qa, qb = gs[a]["q"], gs[b]["q"]
        if (qa[0] == qb[1] or qa[1] == qb[0]) and not any(set(gs[m]["q"]) & (set(qa) | set(qb)) for m in range(a+1, b)):
            d = copy.deepcopy(old); g = d["gates"]; g[a], g[b] = g[b], g[a]; p = T/f"{eid}-mut-swapnc_{a}_{b}.json"; p.write_text(json.dumps(d, separators=(",", ":"))); res.append(chk(p))
    muts["swap_noncommuting_adjacent_cx(n=%d)" % len(res)] = "all REJECT" if all(x.startswith("REJECT") for x in res) else res
    d = copy.deepcopy(old); d["program_sha256"] = "0"*64; p = T/f"{eid}-mut-sha.json"; p.write_text(json.dumps(d, separators=(",", ":"))); muts["HARMLESS program_sha256 change"] = chk(p)
    o["mutations"] = muts; out["entries"][eid] = o; print(eid, json.dumps(o, indent=1), flush=True)
json.dump(out, open(pathlib.Path(__file__).with_name("lean_r5.json"), "w"), indent=1)
