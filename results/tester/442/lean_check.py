"""Tester 442: Lean compiled checker on the new headline certificate (r04-F3-004), previous headline cert (F3-003), and 4 mutants of the new cert (scratchpad copies).
Also: gate list of the cert == own rebuild of the program at nominal angles (names, qubits).  No RNG.
Run: PYTHONPATH=src python results/tester/442/lean_check.py <scratch dir> -> results/tester/442/lean_check.json"""
import json, sys, subprocess, pathlib, copy, hashlib, warnings
warnings.filterwarnings("ignore")
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding"); SC = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "results/tester/442"))
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
CHK = str(ROOT / "lean/.lake/build/bin/su2plaq_cert_lsh")
new = json.load(open(ROOT / "results/lsh/certs/lsh-step-o1-43bdeb21d084.json"))
prev = ROOT / "results/lsh/certs/lsh-step-o1-96f37437a2e6.json"
ent = json.load(open(ROOT / "compress/archive/lsh/entries/r04-F3-004.json"))
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": None}
def run(p):
    r = subprocess.run([CHK, "check", str(p)], capture_output=True, text=True, timeout=900)
    return {"rc": r.returncode, "stdout": r.stdout.strip()[:300], "stderr": r.stderr.strip()[:300]}
out["checker_sha256_disk"] = hashlib.sha256(open(CHK, "rb").read()).hexdigest(); out["checker_sha256_entry"] = ent["lean"]["checker_sha256"]
out["entry_lean"] = {k: v for k, v in ent["lean"].items()}
out["cert_provenance"] = {k: new["provenance"].get(k) for k in ("git_commit", "git_dirty", "program_file_sha256", "encoding", "alpha_nominal", "beta_nominal")}
out["program_sha_file"] = hashlib.sha256((ROOT / ent["program_path"]).read_bytes()).hexdigest(); out["program_sha_entry"] = ent["program_sha256"]
out["gates_sha_cert"] = new["gates_sha256"]; out["gates_sha_entry_lean"] = ent["lean"]["gates_sha256"]
out["n_qubits"] = new["n_qubits"]; out["n_states"] = len(new["states"]); out["n_gates"] = len(new["gates"])
from collections import Counter
out["gate_counts_cert"] = dict(Counter(g["g"] for g in new["gates"]))
out["cx_controls_outer"] = dict(Counter(g["q"][0] for g in new["gates"] if g["g"] == "cx" and g["q"][0] >= 12))
out["outer_as_target_or_1q"] = [g for g in new["gates"] if (g["g"] == "cx" and g["q"][1] >= 12) or (g["g"] != "cx" and g["q"][0] >= 12)]
# own rebuild at nominal angles
qc = E.load_program(str(ROOT / ent["program_path"])).build(LL.spec()).circuit()
mine = [(n, q) for n, q, p in OS.gates_of(qc)]
cg = [(g["g"], list(g["q"])) for g in new["gates"]]
out["gate_list_equal_own_rebuild"] = mine == cg; out["n_gates_own"] = len(mine)
out["check_new"] = run(SC / "new.json") if False else None
import shutil
shutil.copy(ROOT / "results/lsh/certs/lsh-step-o1-43bdeb21d084.json", SC / "new.json"); shutil.copy(prev, SC / "prev.json")
out["check_new"] = run(SC / "new.json"); out["check_prev_headline_F3-003"] = run(SC / "prev.json")
def save(name, c): json.dump(c, open(SC / f"{name}.json", "w"))
G = new["gates"]
muts = {}
m = copy.deepcopy(new); del m["gates"][0]; muts["drop_first_cx"] = m
i = next(i for i, g in enumerate(G) if g["g"] == "cx" and g["q"][0] < 12 and g["q"][1] < 12 and i > 80)
m = copy.deepcopy(new); m["gates"][i]["q"] = [G[i]["q"][0], (G[i]["q"][1] + 1) % 12]; muts[f"retarget_cx_at_{i}"] = m
i13 = next(i for i, g in enumerate(G) if g["g"] == "cx" and g["q"][0] == 13)
m = copy.deepcopy(new); del m["gates"][i13]; muts[f"drop_cx_from_q13_at_{i13}"] = m
i14 = next(i for i, g in enumerate(G) if g["g"] == "cx" and g["q"][0] == 14)
m = copy.deepcopy(new); m["gates"][i14]["q"] = [1, G[i14]["q"][1]]; muts[f"reroute_q14_control_to_q1_at_{i14}"] = m
# extra: change one rz-walk angle (change a coefficient) -- find an rz gate and flip its multiplier if representable
rz = [i for i, g in enumerate(G) if g["g"] == "rz"]
out["rz_gate_example"] = G[rz[0]] if rz else None
out["mutants"] = {}
for name, c in muts.items():
    save(name, c); out["mutants"][name] = run(SC / f"{name}.json"); print(name, out["mutants"][name])
print({k: out[k] for k in ("check_new", "check_prev_headline_F3-003", "gate_list_equal_own_rebuild", "checker_sha256_disk", "checker_sha256_entry", "cx_controls_outer", "gate_counts_cert", "outer_as_target_or_1q")})
json.dump(out, open(ROOT / "results/tester/442/lean_check.json", "w"), indent=1, default=str)
