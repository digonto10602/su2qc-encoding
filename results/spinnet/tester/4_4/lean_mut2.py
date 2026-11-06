import sys, json, copy, pathlib, subprocess
R = pathlib.Path(sys.argv[1]); T = pathlib.Path(sys.argv[2])
exe = R/"lean/.lake/build/bin/su2plaq_cert_spinnet"
def chk(p):
    r = subprocess.run([str(exe), "check", str(p)], capture_output=True, text=True, timeout=300); return r.stdout.strip().splitlines()[0] if r.stdout.strip() else r.stderr[-200:]
out = {}
for stem, cid in (("general", "b0a415d9322f"), ("pairs9", "066f66922ff8")):
    old = json.load(open(R/f"results/spinnet/certs/spinnet-step-o1-{cid}.json")); m = {}
    def run(name, f):
        d = copy.deepcopy(old); f(d); p = T/f"{stem}-{name}.json"; p.write_text(json.dumps(d, separators=(",", ":"))); m[name] = chk(p)
    def swapcx(d):
        for g in d["gates"]:
            if g["g"] == "cx": g["q"] = g["q"][::-1]; return
    def rot(d):
        for g in d["gates"]:
            if g["g"] == "rz": g["m"][1] += 1; return
    def rotp(d):
        for g in d["gates"]:
            if g["g"] == "p": g["m"][0] += 1; return
    def tdg(d):
        for g in d["gates"]:
            if g["g"] == "tdg": g["g"] = "t"; return
    def tgt(d):
        e = d["target"]["blocks"][0]["entries"][0]; print(stem, "entry", e); e[2] = e[2] if False else e[2]
    def phase(d): d["phase"]["m"] = [d["phase"]["m"][0] + 1, d["phase"]["m"][1]]
    def nstates(d): d["states"] = d["states"][:-1]
    for n, f in (("swap_first_cx", swapcx), ("rz_plus_one_unit", rot), ("p_plus_one_unit", rotp), ("tdg_to_t", tdg), ("phase_shift", phase), ("drop_state", nstates)): run(n, f)
    out[stem] = m
print(json.dumps(out, indent=1))
