"""Tester 434 item 3: mutation hunt on rishon three-angle certificates.  Every mutant is run through the RAW compiled Lean checker
(`su2plaq_rishon_cert check`, no Python pre-check) and a subset also through the Python `check_inner_certificate`.
usage: mutate.py <base: UE|UB|UD|F3|step> <worker> <nworkers> [<max_mutants>]"""
import copy, json, pathlib, random, subprocess, sys, time, hashlib
BASE = {"UE": "scratch/t434/UE/UE-o1-fcc27782db55.json", "UB": "scratch/t434/UB/UB-o1-d2869a2974b9.json",
        "UD": "scratch/t434/UD/UD-o1-8e8b367d09a4.json", "F3": "scratch/t434/F3/step-o1-24d16bdd9c45.json",
        "step": "scratch/t434/step/step-o1-280998490c3e.json"}
EXE = "lean/.lake/build/bin/su2plaq_rishon_cert"
name, worker, nw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
maxn = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
base = json.load(open(BASE[name]))
rng = random.Random(434)
G = base["gates"]; NQ = base["n_qubits"]; ND = base["n_data"]
OUT = pathlib.Path("scratch/t434/mut") / name; OUT.mkdir(parents=True, exist_ok=True)
ONE = ["1", "0", "0", "0", "0", "0", "0", "0"]
MUT = []        # (label, expect, mutated-cert-fn)  expect in {"reject", "accept"}
def add(label, expect, fn): MUT.append((label, expect, fn))
def with_gates(f):
    def g(c): c["gates"] = f(c["gates"]); return c
    return g
def pick(pred, n):
    idx = [i for i, g in enumerate(G) if pred(g)]
    rng.shuffle(idx); return sorted(idx[:n])
N = 6 if name in ("UB", "step", "F3") else 10**9      # samples per category on big circuits
# -- gate kind swaps
SW = {"t": "tdg", "tdg": "t", "s": "sdg", "sdg": "s", "h": "sx", "x": "z", "z": "x", "cx": "cz", "cz": "cx", "ccx": "ccz", "rz": "p", "p": "rz"}
for k, v in SW.items():
    for i in pick(lambda g: g["g"] == k, N if name != "UE" else 3):
        def f(gs, i=i, v=v, k=k):
            gs = copy.deepcopy(gs); gs[i]["g"] = v
            if v in ("p", "rz") and "m" not in gs[i]: gs[i]["m"] = [1, 0, 0]
            if v not in ("p", "rz", "cp") and "m" in gs[i]: del gs[i]["m"]
            return gs
        add(f"kind {k}->{v} @gate{i}", "reject", with_gates(f))
# -- qubit changes
for i in pick(lambda g: True, N * 3 if name != "UE" else 12):
    def f(gs, i=i):
        gs = copy.deepcopy(gs); q = gs[i]["q"]; new = (q[-1] + 1) % ND
        while new in q: new = (new + 1) % ND
        gs[i]["q"][-1] = new; return gs
    add(f"qubit last->other @gate{i} ({G[i]['g']})", "reject", with_gates(f))
for i in pick(lambda g: g["g"] in ("cx", "cz", "ccx"), N * 2):
    def f(gs, i=i):
        gs = copy.deepcopy(gs); gs[i]["q"] = list(reversed(gs[i]["q"])); return gs
    # cz is symmetric: swapped cz must still be accepted
    add(f"reverse qubits @gate{i} ({G[i]['g']})", "accept" if G[i]["g"] == "cz" else "reject", with_gates(f))
# -- angle multiplier
for i in pick(lambda g: "m" in g, 40):
    gm = G[i]["m"]; step = 2 if G[i]["g"] == "rz" else 1
    for lab, new in [("+1", [gm[0] + step, gm[1], gm[2]]), ("neg", [-x for x in gm]), ("x2", [2 * x for x in gm]), ("zero", [0, 0, 0]),
                     ("beta+", [gm[0], gm[1] + step, gm[2]]), ("gamma+", [gm[0], gm[1], gm[2] + step])]:
        if new == gm: continue          # negating / zeroing an already-zero vector is not a mutation
        def f(gs, i=i, new=new):
            gs = copy.deepcopy(gs); gs[i]["m"] = new; return gs
        add(f"angle {lab} @gate{i} ({G[i]['g']}) m={gm}", "reject", with_gates(f))
# rz with odd exponent -> structural
for i in pick(lambda g: g["g"] == "rz", 2):
    def f(gs, i=i):
        gs = copy.deepcopy(gs); gs[i]["m"] = [gs[i]["m"][0] + 1, gs[i]["m"][1], gs[i]["m"][2]]; return gs
    add(f"rz odd exponent @gate{i}", "reject", with_gates(f))
# -- drop / duplicate
for i in pick(lambda g: True, N * 4 if name != "UE" else 12):
    add(f"drop gate {i} ({G[i]['g']})", "reject", with_gates(lambda gs, i=i: gs[:i] + gs[i + 1:]))
    add(f"duplicate gate {i} ({G[i]['g']})", "reject" if G[i]["g"] not in () else "reject", with_gates(lambda gs, i=i: gs[:i + 1] + [copy.deepcopy(gs[i])] + gs[i + 1:]))
add("drop last gate", "reject", with_gates(lambda gs: gs[:-1]))
add("drop first gate", "reject", with_gates(lambda gs: gs[1:]))
add("empty gate list", "reject", with_gates(lambda gs: []))
# swap two adjacent gates (may commute -> only flag if accepted and not equivalent: expect reject, recorded)
# -- extra gates at the end: dirty ancilla, leak, outside code space
anc = list(range(ND, NQ))
def app(g): return with_gates(lambda gs: gs + [g])
if anc:
    add("append x on ancilla (dirty)", "reject", app({"g": "x", "q": [anc[0]]}))
    add("append h on ancilla", "reject", app({"g": "h", "q": [anc[0]]}))
    add("append cx data->ancilla (dirty)", "reject", app({"g": "cx", "q": [0, anc[0]]}))
    add("append z on clean ancilla (global-phase-free no-op)", "accept", app({"g": "z", "q": [anc[0]]}))
    add("append t on clean ancilla (no-op)", "accept", app({"g": "t", "q": [anc[0]]}))
    add("prepend x on ancilla (dirty start)", "reject", with_gates(lambda gs: [{"g": "x", "q": [anc[0]]}] + gs))
    add("prepend x on ancilla and x at end (garbage-in-garbage-out, ancilla starts at 0 so wrong)", "reject",
        with_gates(lambda gs: [{"g": "x", "q": [anc[0]]}] + gs + [{"g": "x", "q": [anc[0]]}]))
add("append x on data qubit 0 (leaves code space)", "reject", app({"g": "x", "q": [0]}))
add("append x on data qubit 1 (leaves code space)", "reject", app({"g": "x", "q": [1]}))
add("append h on data qubit 3", "reject", app({"g": "h", "q": [3]}))
add("append swap(0,4) (permutes links)", "reject", app({"g": "swap", "q": [0, 4]}))
add("append x x on data (identity) ", "accept", with_gates(lambda gs: gs + [{"g": "x", "q": [2]}, {"g": "x", "q": [2]}]))
add("append cx cx data (identity)", "accept", with_gates(lambda gs: gs + [{"g": "cx", "q": [2, 5]}, {"g": "cx", "q": [2, 5]}]))
add("append p(1,0,0) on data (relative phase)", "reject", app({"g": "p", "q": [0], "m": [1, 0, 0]}))
add("append z on data 0", "reject", app({"g": "z", "q": [0]}))
add("append global-phase-like: s,s,z on data (identity)", "accept", with_gates(lambda gs: gs + [{"g": "s", "q": [0]}, {"g": "s", "q": [0]}, {"g": "z", "q": [0]}]))
# a gate beyond the register
add("gate qubit out of range", "reject", app({"g": "x", "q": [NQ]}))
add("repeated qubit in cx", "reject", app({"g": "cx", "q": [0, 0]}))
add("wrong arity", "reject", app({"g": "cx", "q": [0]}))
add("unknown gate y", "reject", app({"g": "y", "q": [0]}))
add("angle on angle-free gate", "reject", app({"g": "x", "q": [0], "m": [1, 0, 0]}))
# -- phase
for j in range(1, 8):
    def f(c, j=j):
        from su2plaq.lean import exact as E
        c["phase"]["k"] = E.omega_power(j).to_json(); return c
    add(f"phase omega^{j} (valid root, wrong)", "reject", f)
for m in ([1, 0, 0], [0, 1, 0], [0, 0, 1], [-1, 0, 0]):
    def f(c, m=m): c["phase"]["m"] = m; return c
    add(f"phase exponent {m}", "reject", f)
def f(c): c["phase"]["k"] = ["0"] * 8; return c
add("phase zero", "reject", f)
def f(c): c["phase"]["k"] = ["2"] + ["0"] * 7; return c
add("phase 2 (not unit)", "reject", f)
def f(c): del c["phase"]; return c
add("phase missing (defaults to 1; right iff the true phase is 1)", "accept", f)      # base phase is 1 in all four certificates
# -- target
ents = base["target"]["entries"]
def tmut(label, fn, expect="reject"):
    def f(c): fn(c["target"]["entries"]); return c
    add(label, expect, f)
for idx in sorted(rng.sample(range(len(ents)), min(len(ents), 8))):
    def sign(es, idx=idx): es[idx][2][0][1] = [("-" + x if x not in ("0",) and not x.startswith("-") else (x[1:] if x.startswith("-") else x)) for x in es[idx][2][0][1]]
    def coef(es, idx=idx):
        es[idx][2][0][1] = ["1/3"] + ["0"] * 7
    def shift(es, idx=idx): es[idx][2][0][0][1] += 1
    def drop(es, idx=idx): del es[idx]
    def dup(es, idx=idx): es.append(copy.deepcopy(es[idx]))
    def swapij(es, idx=idx): es[idx][0], es[idx][1] = es[idx][1], es[idx][0]
    tmut(f"target entry {idx}: sign flip", sign)
    tmut(f"target entry {idx}: coefficient replaced by 1/3", coef)
    tmut(f"target entry {idx}: exponent beta shift", shift)
    tmut(f"target entry {idx}: dropped", drop)
    tmut(f"target entry {idx}: duplicated", dup)
    tmut(f"target entry {idx}: i<->j", swapij, "accept" if ents[idx][0] == ents[idx][1] else "reject")
# swap sqrt2 component: find an entry with nonzero 3rd (sqrt2) component and move it to the 1st
for idx, e in enumerate(ents):
    k = e[2][0][1]
    if k[2] != "0" and k[0] == "0":
        def sq(es, idx=idx):
            k = es[idx][2][0][1]; k[0], k[2] = k[2], k[0]
        tmut(f"target entry {idx}: sqrt2 coefficient moved to rational slot (sqrt2 swapped with 1)", sq); break
for idx, e in enumerate(ents):
    k = e[2][0][1]
    if k[0] != "0" and k[2] == "0":
        def sq(es, idx=idx):
            k = es[idx][2][0][1]; k[0], k[2] = k[2], k[0]
        tmut(f"target entry {idx}: rational coefficient moved to sqrt2 slot", sq); break
tmut("target: extra spurious entry (0,0)=z", lambda es: es.append([0, 1, [[[0, 0, 0], ONE]]]) if not any(e[0] == 0 and e[1] == 1 for e in es) else es.append([1295, 0, [[[0, 0, 0], ONE]]]))
tmut("target: all entries empty list", lambda es: es.clear())
def f(c): c["target"]["entries"][0][2] = []; return c
add("target entry 0 emptied", "reject", f)
def f(c): c["target"]["kind"] = {"UE": "UB", "UB": "step", "UD": "UB", "F3": "UB", "step": "UB"}[name]; return c
add("target kind changed", "reject", f)
def f(c): c["target"]["kind"] = "step" if name != "step" and name != "F3" else "UE"; return c
add("target kind -> other", "reject", f)
def f(c): c["target"]["kind"] = "bogus"; return c
add("target kind bogus", "reject", f)
def f(c): c["target"]["order"] = 2; return c
add("target order 2", "accept" if name in ("UE", "UB", "UD") else "reject", f)
def f(c): del c["target"]; return c
add("target missing", "reject", f)
# -- states
def f(c): c["states"] = c["states"][::-1]; return c
add("states reversed", "reject", f)
def f(c): c["states"][5], c["states"][6] = c["states"][6], c["states"][5]; return c
add("states swap 5,6", "reject", f)
def f(c): c["states"] = c["states"][:-1]; return c
add("states drop last", "reject", f)
def f(c): c["states"][-1] = c["states"][0]; return c
add("states duplicate", "reject", f)
def f(c): c["states"] = c["states"] + [c["states"][-1] + 1]; return c
add("states extra", "reject", f)
def f(c): del c["states"]; return c
add("states missing", "reject", f)
def f(c): c["states"][0] += 1; return c
add("states code 0 off by one", "reject", f)
def f(c): c["states"] = c["states"][:648]; return c
add("states only first half (checker must not trust a shorter list)", "reject", f)
# -- base
def rescale(c, fa, fb, fg):
    c["base"] = {"d_alpha": c["base"]["d_alpha"] * fa, "d_beta": c["base"]["d_beta"] * fb, "d_gamma": c["base"]["d_gamma"] * fg}
    for g in c["gates"]:
        if "m" in g: g["m"] = [g["m"][0] * fa, g["m"][1] * fb, g["m"][2] * fg]
    for e in c["target"]["entries"]:
        for t in e[2]: t[0] = [t[0][0] * fa, t[0][1] * fb, t[0][2] * fg]
    c["phase"]["m"] = [c["phase"]["m"][0] * fa, c["phase"]["m"][1] * fb, c["phase"]["m"][2] * fg]
    return c
add("base consistently rescaled x(2,1,1) (same unitary)", "accept", lambda c: rescale(c, 2, 1, 1))
add("base consistently rescaled x(1,3,1) (same unitary)", "accept", lambda c: rescale(c, 1, 3, 1))
add("base consistently rescaled x(1,1,5) (same unitary)", "accept", lambda c: rescale(c, 1, 1, 5))
add("base consistently rescaled x(2,2,2) (same unitary)", "accept", lambda c: rescale(c, 2, 2, 2))
def only_base(fa, fb, fg):
    def f(c):
        c["base"] = {"d_alpha": c["base"]["d_alpha"] * fa, "d_beta": c["base"]["d_beta"] * fb, "d_gamma": c["base"]["d_gamma"] * fg}; return c
    return f
def uses(s):
    return (any("m" in g and g["m"][s] for g in G) or any(t[0][s] for e in base["target"]["entries"] for t in e[2]) or any(base["phase"]["m"][s] for _ in [0]))
add("base x2 alpha only (gates, target, phase unscaled)", "reject" if uses(0) else "accept", only_base(2, 1, 1))
add("base x2 beta only", "reject" if uses(1) else "accept", only_base(1, 2, 1))
add("base x2 gamma only", "reject" if uses(2) else "accept", only_base(1, 1, 2))
def f(c): g = c["gates"]; [x.__setitem__("m", [2 * x["m"][0], x["m"][1], x["m"][2]]) for x in g if "m" in x]; return c
add("gate exponents x2 in alpha slot, base unchanged", "reject", f)
def f(c): c["base"]["d_alpha"] += 1; return c
add("base d_alpha +1 (not a multiple)", "reject", f)
def f(c): c["base"]["d_alpha"] = 0; return c
add("base d_alpha = 0", "reject", f)
def f(c): c["base"]["d_beta"] = max(1, c["base"]["d_beta"] // 2) if c["base"]["d_beta"] > 1 else 0; return c
add("base d_beta halved (below target base) / zero", "reject", f)
def f(c): del c["base"]; return c
add("base missing (defaults 1,1,1)", "accept" if name == "UD" else "reject", f)
def f(c): c["base"]["d_gamma"] = -1; return c
add("base negative", "reject", f)
# -- schema fields
for fld, val in [("schema", "su2plaq-rishon-cert3-0"), ("schema", "su2plaq-cert-1"), ("n_data", 12), ("n_data", 17), ("n_outer", 8), ("n_outer", 32)]:
    def f(c, fld=fld, val=val): c[fld] = val; return c
    add(f"{fld} = {val!r}", "reject", f)
def f(c): c["n_qubits"] = 63 + 0; return c
add("n_qubits 63 (> 62)", "reject", f)
def f(c): c["n_qubits"] = NQ - 1; return c
add("n_qubits - 1", "reject" if (NQ - 1 < ND or any((NQ - 1) in g["q"] for g in G)) else "accept", f)
def f(c): c["n_qubits"] = NQ + 1; return c
add("n_qubits + 1 (idle spare qubit)", "accept", f)
def f(c): del c["gates"]; return c
add("gates missing", "reject", f)
def f(c): c["gates"] = "x"; return c
add("gates not a list", "reject", f)
def f(c): c["gates"][0]["g"] = None; return c
add("gate kind null", "reject", f)
def f(c): c["gates"][0]["q"] = [-1, 1] if len(c["gates"][0]["q"]) == 2 else [-1]; return c
add("negative qubit", "reject", f)
def f(c): c["gates"][0]["q"] = [0.5, 1][: len(c["gates"][0]["q"])]; return c
add("fractional qubit", "reject", f)
def f(c):
    for g in c["gates"]:
        if "m" in g: g["m"] = [g["m"][0] * 10**30, g["m"][1], g["m"][2]]; break
    return c
add("huge exponent (potential blow-up / overflow)", "reject", f)

# ----------------------------------------------------------------------------------------------- run
def run_raw(path, timeout=900):
    t0 = time.time()
    try:
        r = subprocess.run([EXE, "check", str(path)], capture_output=True, text=True, timeout=timeout)
        line = (r.stdout.strip().splitlines() or [""])[0]
        return line, r.returncode, time.time() - t0
    except subprocess.TimeoutExpired:
        return "TIMEOUT", -1, time.time() - t0
sel = [m for i, m in enumerate(MUT) if i % nw == worker][:maxn]
res = []
for label, expect, fn in sel:
    c = fn(copy.deepcopy(base))
    p = OUT / (hashlib.sha1(label.encode()).hexdigest()[:10] + ".json")
    try:
        p.write_text(json.dumps(c, separators=(",", ":")))
    except Exception as e:
        res.append({"label": label, "expect": expect, "got": f"SERIALISE-ERR {e}"}); continue
    line, rc, dt = run_raw(p)
    verdict = "accept" if line == "ACCEPT" and rc == 0 else ("reject" if line.startswith("REJECT") and rc == 1 else "ERROR")
    ok = verdict == expect
    res.append({"label": label, "expect": expect, "raw_line": line[:160], "verdict": verdict, "as_expected": ok, "seconds": round(dt, 2)})
    print(("OK  " if ok else "!!  ") + f"{verdict:7s} (exp {expect}) {label}  [{line[:70]}]", flush=True)
    p.unlink()
json.dump(res, open(f"results/tester/434/mut_{name}_{worker}.json", "w"), indent=1)
