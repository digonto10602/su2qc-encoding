"""Assemble results/benchmarks/spinnet-m4.json and lsh-m7.json from the driver output (scratch/bench-m4m7/raw_*.json, summary.json,
ab.json, ab2.json, old_suite.json, physdiff.json).  usage: python make_json_m4.py <commit>"""
import json, sys, pathlib, platform
R = pathlib.Path(__file__).resolve().parents[3]; S = R / "scratch/bench-m4m7"; commit = sys.argv[1]
J = lambda n: json.load(open(S / n))
summ = J("summary.json"); raw = {p: J(f"raw_{p}.json") for p in ("tasksA", "tasksB", "round", "scripts", "suites_m4", "suites_m7", "suites_unit")}
machine = {"host": platform.node(), "cpu": "Intel i7-12700KF (8 P-cores = CPU 0-15 as SMT pairs, 4 E-cores = CPU 16-19), 20 logical CPUs, 31 GiB",
           "cpus_used": "taskset -c 14 (single-process tasks: P-core 7 thread), taskset -c 14-19 (suites, loop; 14-15 = P-core 7, 16-19 = E-cores)",
           "os": "Linux 7.2.15-1-omarchy (new install; the M3 baseline 100 ran on the same hardware under the previous OS)",
           "versions": {"python": "3.12.16", "numpy": "2.5.4", "scipy": "1.18.1", "qiskit": "2.5.2", "qiskit_aer": "0.17.2", "pygridsynth": "1.2.0"},
           "env": {"OMP_NUM_THREADS": 1, "OPENBLAS_NUM_THREADS": 1, "MKL_NUM_THREADS": 1, "PYTHONHASHSEED": 20261104},
           "other_agents": "fuzzy round evaluation on CPUs 12-13 and other agent jobs; 1-min load average 3-31 during the session (per-run values in load_before)"}
seeds = {"transpiler_logical": 20261104, "ct_compile": 12345, "angle_set": 20261107, "note": "no stochastic call is timed; scripts use their own fixed seeds"}
common = {"commit": commit, "machine": machine, "seeds": seeds, "scripts": ["results/benchmarks/spinnet-m4-scripts/bench_worker_m4.py", "results/benchmarks/spinnet-m4-scripts/bench_driver_m4.py",
          "results/benchmarks/spinnet-m4-scripts/analyze_m4.py", "results/benchmarks/spinnet-m4-scripts/make_root.sh", "results/benchmarks/spinnet-m4-scripts/make_json_m4.py"],
          "control_AB": {"description": "old code (git archive 9c0aee6, the M3 benchmark commit) vs HEAD, same worker script, interleaved, same machine and hour, taskset -c 14",
                         "run1_4rep": J("ab.json"), "run2_8rep": J("ab2.json")},
          "old_suite_m0_m1_9c0aee6": J("old_suite.json"), "m3_results_AB_old_vs_new": J("m3_ab.json"), "interleaved_spinnet_vs_lsh": J("sn_vs_lsh.json"), "physics_diff": J("physdiff.json")}
def pick(d, names): return {k: v for k, v in d.items() if k in names}
A = {**common, "report": "reports/benchmarks/301-spinnet-m4.md", "baseline": "results/benchmarks/spinnet-m3.json (report 100)",
     "summary": {"tasks": summ["tasksA"], "round_and_candidates": summ["round"], "scripts": pick(summ["scripts"], ("m3_results", "m4_results")),
                 "suites": {**summ["suites_m4"], "pytest_unit": summ["suites_unit"]["pytest_unit"]}},
     "raw": {"tasks": raw["tasksA"], "round": raw["round"], "scripts": raw["scripts"], "suites_m4": raw["suites_m4"], "suites_unit": raw["suites_unit"]}}
B = {**common, "report": "reports/benchmarks/302-lsh-m7.md", "baseline": "none for LSH (new baseline); shared quantities vs report 101 / 100",
     "summary": {"tasks": summ["tasksB"], "scripts": pick(summ["scripts"], ("m7_results",)), "suites": {**summ["suites_m7"], "pytest_unit": summ["suites_unit"]["pytest_unit"]}},
     "raw": {"tasks": raw["tasksB"], "scripts": raw["scripts"], "suites_m7": raw["suites_m7"], "suites_unit": raw["suites_unit"]}}
json.dump(A, open(R / "results/benchmarks/spinnet-m4.json", "w"), indent=1, default=str)
json.dump(B, open(R / "results/benchmarks/lsh-m7.json", "w"), indent=1, default=str)
print("written")
