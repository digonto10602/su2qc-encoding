"""Tester 112: re-export both certificates from the archived program sources, compare with the archived certificates, run the compiled checker,
and run mutation probes (the checker must REJECT tampered certificates)."""
import sys, json, pathlib, subprocess, copy, hashlib
from su2plaq.spinnet import loop; loop.install()
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import own_verify as OV
from su2plaq.spinnet import lean_export as LE
from su2plaq.compress.spec import default_spec
R = pathlib.Path(sys.argv[1]); T = pathlib.Path(sys.argv[2]); T.mkdir(parents=True, exist_ok=True)
exe = LE.project.LEAN_DIR / ".lake/build/bin/su2plaq_cert_spinnet"
def chk(p): 
    r = subprocess.run([str(exe), "check", str(p)], capture_output=True, text=True, timeout=300); return r.stdout.strip().splitlines()[0] if r.stdout.strip() else r.stderr[-200:]
res = {}
for stem, cid in (("000-general", "b0a415d9322f"), ("001-spinnet_v2_pairs9", "066f66922ff8")):
    qc = OV.build(R/f"compress/programs/spinnet/seed/{stem}.py", 0.37, 0.61)
    out = LE.export_certificate(qc, OV.enc, "step", 0.37, 0.61, 1, T/f"{stem}.json")
    new = json.loads(out.read_text()); old = json.load(open(R/f"results/spinnet/certs/spinnet-step-o1-{cid}.json"))
    diff = [k for k in new if k != "provenance" and new[k] != old[k]]
    r = {"re_exported_id": new["circuit_id"], "archived_id": old["circuit_id"], "same_id": new["circuit_id"] == old["circuit_id"],
         "fields_differing_besides_provenance": diff, "check_archived": chk(R/f"results/spinnet/certs/spinnet-step-o1-{cid}.json"), "check_re_exported": chk(out)}
    # mutation probes on the re-exported certificate
    muts = {}
    def mut(name, f):
        d = copy.deepcopy(new); f(d); p = T/f"{stem}-mut-{name}.json"; p.write_text(json.dumps(d, separators=(",", ":"))); muts[name] = chk(p)
    def drop_gate(d): del d["gates"][len(d["gates"])//2]
    def swap_cx(d):
        for g in d["gates"]:
            if g.get("op") == "cx" or g.get("name") == "cx": g["qubits"] = list(reversed(g["qubits"])); break
    def flip_target(d):
        e = d["target"]["blocks"][0]["entries"][0]; e[0], e[1] = e[1], e[0] if e[0] != e[1] else None
    def sha(d): d["program_sha256"] = "0"*64
    def base(d): d["base"] = [8, 8] if not isinstance(d["base"], int) else 3
    print(stem, [g for g in new["gates"][:3]], list(new["target"]["blocks"][0].keys()), new["base"], flush=True)
    mut("drop_middle_gate", drop_gate); mut("swap_first_cx", swap_cx); mut("sha", sha); mut("base", base)
    # first rotation angle +1 unit
    def rot(d):
        for g in d["gates"]:
            for k, v in g.items():
                pass
    r["mutations"] = muts; res[stem] = r
print(json.dumps(res, indent=1))
