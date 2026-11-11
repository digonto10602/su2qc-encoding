"""Tester 222 addendum: the Gauss sample must still decide after the re-judge says 'ok'.  Circuits that keep the valid codes but are not
gauge invariant (rz / cz / swap), shared verdict faked as a clean `pruning_bound` (dropped 5e-12).  Also the rx case of the main mutation
script (leaves the valid codes: invisible to the Gauss sample by construction, caught by the leak amplitude which is faked clean here).
Run: PYTHONPATH=src python results/rishon/tester-222-rejudge-gauss.py"""
import dataclasses, json, subprocess
from su2plaq.circuits import rishon as C
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.evaluate import evaluator as shared_ev
from su2plaq.rishon import verify as RV
enc = RishonEncoding(); real = shared_ev.evaluate; qc0 = C.build_UE(0.37)
rows = []
for name, f in (("rz(0.7) q1", lambda q: q.rz(0.7, 1)), ("cz(0,4)", lambda q: q.cz(0, 4)), ("swap(0,4)", lambda q: q.swap(0, 4)), ("rx(0.7) q1 (leaves valid codes)", lambda q: q.rx(0.7, 1))):
    q = qc0.copy(); f(q)
    for dropped, why in ((5e-12, "re-judged ok, then Gauss decides"),):
        RV.evaluate = lambda *a, **k: dataclasses.replace(real(*a, **k), ok=False, reason="pruning_bound", dropped_total=dropped, op_norm_error=1e-13,
                                                          leak_amplitude=0.0, block_error=1e-13)
        v = RV.verify(q, enc, "UE", 0.37, None, 1)
        RV.evaluate = real
        rows.append({"circuit": name, "faked_shared": "pruning_bound, dropped 5e-12, errors 1e-13", "ok": bool(v.ok), "reason": v.reason,
                     "gauss_residual": float(v.gauss_residual), "failing_inputs": [list(map(str, x)) for x in v.failing_inputs]})
        print(rows[-1])
out = {"rows": rows, "git": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()}
json.dump(out, open("results/rishon/tester-222-rejudge-gauss.json", "w"), indent=1)
