"""Tester 437: independent Aer exactness + CX/T recount for every round-0 LSH seed program (reuses the 436 script).
Run by hand under tools/run-capped.  Output results/tester/437-indep-aer.json."""
import json, sys, subprocess, hashlib, pathlib
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/tests/independent/lsh_m8_436")
import indep_check as IC
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(),
       "engine": "qiskit-aer statevector, own target from L13 rules, own 47-code set", "seed_note": "deterministic, no RNG"}
for f in sorted((ROOT/"compress/programs/lsh/seed").glob("*.py")):
    label = f.stem
    r = {"sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
    pairs = [(0.37, 0.61), (0.91, 0.23), (1.7, 1.0)] + ([(1.13, 0.47)] if label == "005-wrap_sn_headline" else [])
    for ab in pairs:
        r[str(ab)] = IC.run_one(str(f), *ab, sign_check=(ab == (0.37, 0.61)))
    r["counts"] = IC.count_circuit(E.load_program(str(f)).build(LL.spec()).circuit())
    out[label] = r
    print(label, json.dumps({k: (v if k in ("counts", "sha256") else {kk: vv for kk, vv in v.items() if kk in ("op_norm_err", "anc_leak_prob", "gauss_leak_prob", "op_norm_err_vs_minus_beta")}) for k, v in r.items()}), flush=True)
json.dump(out, open(ROOT/"results/tester/437-indep-aer.json", "w"), indent=1)
