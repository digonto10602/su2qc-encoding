import sys, json, subprocess
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.lean import certify as C
one = ["1","0","0","0","0","0","0","0"]
n = 433
states = [{"k": k, "label": "fake", "terms": [{"code": k, "c": one}]} for k in range(n)]
# a "circuit" that is NOT U_E: one p gate with an arbitrary angle on data qubit 0; target = exact diagonal phase of that gate on these fake states
blocks = [{"ks": [k], "entries": [[0, 0, [[[1 if k & 1 else 0, 0], one]]]]} for k in range(n)]
cert = {"schema": "su2plaq-cert-1", "circuit_id": "fake", "n_qubits": 28, "n_data": 12, "n_outer": 16, "base": {"d_alpha": 4, "d_beta": 2},
        "gates": [{"g": "p", "q": [0], "m": [1, 0]}], "states": states, "target": {"kind": "UE", "order": 1, "blocks": blocks},
        "phase": {"k": one, "m": [0, 0]}}
json.dump(cert, open("fake.json", "w"), separators=(",", ":"))
r = subprocess.run(["/home/digimonk/Projects/su2qc-encoding/lean/.lake/build/bin/su2plaq_cert", "check", "fake.json"], capture_output=True, text=True)
print("bare Lean checker:", r.stdout.strip())
res = C.check_certificate("fake.json")
print("python check_certificate:", res.status, "|", res.reason)
C.write_theorem_file("fake.json", "fake_ok", "thm/fake_ok.lean"); print("write_theorem_file: wrote file without complaint")
