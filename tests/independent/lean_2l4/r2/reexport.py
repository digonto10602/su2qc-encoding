import sys, json, time, hashlib
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
S = "/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/r2/"
from su2plaq.compress.baselines import general_circuit
from su2plaq.compress.spec import default_spec
from su2plaq.lean import certify as C
spec = default_spec("twelve", "step")
qc = general_circuit(spec)
t = time.time()
p = C.export_certificate(qc, C._encoding(), spec.kind, spec.alpha, spec.beta, spec.order, S + "reexport.json")
print("export", p, round(time.time() - t, 1), "s")
a = json.load(open(S + "reexport.json")); b = json.load(open(S + "embedded.json"))
for d in (a, b): d.pop("provenance")
print("identical to embedded (minus provenance):", a == b)
for k in a:
    if a[k] != b[k]: print("differs:", k)
print("circuit gates", len(qc.data), "program_sha", a["program_sha256"][:12])
