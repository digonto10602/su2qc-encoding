"""Tester 406: stress the 008-A1 test body (and the old one) over random hex commits. seed 406."""
import json, random, sys, tempfile, pathlib
sys.path.insert(0, "src"); sys.path.insert(0, "tests/unit")
import numpy as np
from su2plaq.metrics.provenance import provenance
from su2plaq.results.report import render
import test_results_unit as T
rng = random.Random(406)
commits = ["c1c1c1c", "c0c0c0c", "0000000", "fffffff", "1c1c1c1"] + ["".join(rng.choice("0123456789abcdef") for _ in range(7)) for _ in range(300)]
newfail = oldfail = 0
for cm in commits:
    snap = provenance({"s": 1}); snap["git_commit"] = cm
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        paths = T._render_two(d, snapshot=snap)
        t = render(paths); t1 = render(paths[:1])
        newfail += not (t == render(paths) and "zq-first" in t and "zq-second" in t and "zq-second" not in t1 and cm in t)
        # old test's assertions with ids c0 / c1 against the same commit
        from su2plaq.results.store import save_result, verdict_to_dict
        ver = verdict_to_dict(T._verdict())
        ps = [save_result(d / f"o{i}.json", encoding="twelve", circuit_id=f"c{i}", kind="UB", params={"beta": 0.5}, verification=ver,
                          metrics={}, provenance_snapshot=snap) for i in range(2)]
        oldfail += not ("c1" not in render(ps[:1]))
print({"n_commits": len(commits), "new_test_failures": newfail, "old_test_failures": oldfail})
json.dump({"n_commits": len(commits), "new_test_failures": newfail, "old_test_failures_for_same_commits": oldfail, "seed": 406},
          open("results/lsh_tester/tester-406-flaky.json", "w"))
