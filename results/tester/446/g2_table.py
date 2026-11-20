"""Tester 446: reproduce the prompts/402 section 7 table for r05-F3-005 by calling the LOCKED test's helpers directly (per angle pair)."""
import importlib.util, json, pathlib, subprocess, sys, time
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding"); sys.path.insert(0, str(ROOT))
sp = importlib.util.spec_from_file_location("g2locked", ROOT / "tests/acceptance/m8/test_lsh_m8_gate.py")
T = importlib.util.module_from_spec(sp); sp.loader.exec_module(T)
from su2plaq.compress.spec import default_spec, get_encoding
from su2plaq.compress.archive import Archive
from su2plaq.compress import robust
import numpy as np
spec = default_spec("lsh", "step"); enc = get_encoding("lsh")
arch = Archive.load("lsh", root=ROOT, n_alt=2, strict=True)
head = {e.id: e for e in arch.entries()}[robust.headline("lsh", "step", root=ROOT)["id"]]
best = min((e for e in arch.entries() if e.valid), key=lambda e: tuple(e.key))
out = {"commit": subprocess.run(["git","rev-parse","--short","HEAD"],capture_output=True,text=True,cwd=ROOT).stdout.strip(),
       "headline": head.id, "best": best.id, "seed": T.G2_SEED, "n_states": T.G2_STATES, "rows": []}
rebuild = lambda specs: T._rebuild(ROOT, head, specs)
qc0 = rebuild([spec])[0]
reads = T.outer_reads(qc0, enc); out["reads"] = {str(k): v for k, v in reads.items()}
out["n_ancilla"] = len(enc.layout_of(qc0).ancilla); out["n_qubits"] = qc0.num_qubits
out["gate_counts"] = {k: int(v) for k, v in qc0.count_ops().items()}
out["lay_data"] = list(map(int, enc.layout_of(qc0).data)); out["lay_outer"] = list(map(int, enc.layout_of(qc0).outer))
states = T.g2_states(qc0, enc, reads)
codes = enc.physical_vectors().codes
secw = []
for s_ in range(4):
    idx = [k for k, c in enumerate(codes) if ((int(c[0]) >> 13) & 3) == s_]
    secw.append((len(idx), float((abs(states[:, idx]) ** 2).sum(axis=1).min())))
out["sector_sizes_and_min_state_weight"] = secw
circs = rebuild([spec] + [spec.with_angles(a, b) for a, b in T.G2_PAIRS[1:]])
for (a, b), qc in zip(T.G2_PAIRS, circs):
    t0 = time.time(); r = T.aer_outer_read_check(qc, enc, a, b, reads); t1 = time.time()
    f = T.aer_full_register_check(qc, enc, a, b, states); t2 = time.time()
    out["rows"].append({"pair": [a, b], "reads": {str(k): v for k, v in T.outer_reads(qc, enc).items()}, "reduced": {k: float(v) for k, v in r.items()},
                        "full": {k: float(v) for k, v in f.items()}, "t_reduced": round(t1-t0,1), "t_full": round(t2-t1,1)})
    print(json.dumps(out["rows"][-1]), flush=True)
out["best_is_headline"] = best.id == head.id
pathlib.Path(ROOT / "results/tester/446/g2_table.json").write_text(json.dumps(out, indent=1))
