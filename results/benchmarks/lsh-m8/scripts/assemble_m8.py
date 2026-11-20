"""Assemble results/benchmarks/lsh-m8/*.json from the raw phase files (tester, reports/benchmarks/306).
usage: python assemble_m8.py <out_dir> <raw_dir> [<raw_dir> ...]   (later raw dirs override earlier ones for the same phase file)"""
import json, sys, pathlib, statistics as st, subprocess, platform, shutil
import numpy as np
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
rawdirs = [pathlib.Path(p) for p in sys.argv[2:]]
raw = {}
for d in rawdirs:
    for f in sorted(d.glob("raw_*.json")):
        if "INVALID" in f.name: continue
        raw.setdefault(f.stem[4:], []).append((str(f), json.load(open(f))))
def get(phase, i=0): return raw[phase][i][1]
def stats(x):
    x = [float(v) for v in x]
    return {"n": len(x), "median": st.median(x), "min": min(x), "max": max(x), "q25": float(np.percentile(x, 25)), "q75": float(np.percentile(x, 75))}
S = {"commit_src": "148d404 (src, tests, compress identical at 513eb51 = HEAD at the end of the session: only docs/ and notes/ differ)",
     "machine": {"host": platform.node(), "cpu": "Intel i7-12700KF (8 P-core with SMT + 4 E-core, 20 logical CPUs), 31 GiB RAM, no GPU",
                 "cores_used": "single-process tasks: taskset -c 0 (P-core 0, SMT sibling cpu 1 idle); scripts/round/seed/certify: taskset -c 0-8; m7/unit suites: taskset -c 0-8 with pytest -n 6; m8 suite: taskset -c 0-7 with -n 2",
                 "python": platform.python_version()},
     "env": {"OMP_NUM_THREADS": 1, "OPENBLAS_NUM_THREADS": 1, "MKL_NUM_THREADS": 1, "PYTHONHASHSEED": 20261104},
     "seeds": "no stochastic call is timed; the robust angle set is seed 20261107 (n=20); transpiler seed 20261104", "phases": {}}
# item 1
ev = get("evalprog"); S["phases"]["evalprog"] = {"cmd": "taskset -c 0 python scripts/w_eval.py eval <program> N [cold]; 5 fresh processes x (1 warm-up + 5 timed) warm, 5 x 3 cold", "programs": {}}
for tag in ("headline_F3_005", "seed005_wrap_sn_headline", "seed000_general"):
    w = ev["runs"][f"eval_{tag}_warm"]["runs"]; c = ev["runs"][f"eval_{tag}_cold"]["runs"]
    S["phases"]["evalprog"]["programs"][tag] = {
        "warm_evaluate_program_s": stats([t for r in w for t in r["calls"][1:]]), "warm_first_call_in_process_s": stats([r["calls"][0] for r in w]),
        "build_subprocess_s": stats([t for r in w for t in r["build_s"]]), "evaluate_circuit_s": stats([t for r in w for t in r["evaluate_circuit_s"]]),
        "verdict_evaluate_s": stats([t for r in w for t in r["verdict_evaluate_s"]]),
        "cold_gridsynth_first_call_s": stats([r["calls"][0] for r in c]), "cold_then_warm_s": stats([t for r in c for t in r["calls"][1:]]),
        "cx": w[0]["cx"], "t_eps_1e-6": w[0]["t_eps"], "depth_ct": w[0]["depth_ct"], "qubits": w[0]["qubits"], "n_rot": w[0]["n_rot"], "t_fixed": w[0]["t_fixed"],
        "program_sha256": w[0]["program_sha256"], "rss_mb": max(r["rss_mb"] for r in w), "verdict": w[0]["verdict"],
        "load_before": [r["load_before"][0] for r in w]}
# item 3
rb = get("robust"); S["phases"]["robust"] = {"cmd": "taskset -c 0 python scripts/w_eval.py robust <program> N [cold]; headline_refresh: loop headline --refresh --root <scratch copy>", "programs": {}}
for k, tag in (("robust_headline_warm", "headline_warm"), ("robust_seed005_warm", "seed005_warm")):
    r = rb["runs"][k]["runs"]; S["phases"]["robust"]["programs"][tag] = {"timed_s": stats([t for x in r for t in x["calls"][1:]]), "first_call_s": stats([x["calls"][0] for x in r]),
        "robust_key": r[0]["robust_key"], "rss_mb": max(x["rss_mb"] for x in r), "load_before": [x["load_before"][0] for x in r]}
r = rb["runs"]["robust_headline_cold"]["runs"]
S["phases"]["robust"]["programs"]["headline_cold_gridsynth"] = {"first_call_s": stats([x["calls"][0] for x in r]), "later_s": stats([t for x in r for t in x["calls"][1:]]), "robust_key": r[0]["robust_key"]}
r = rb["runs"]["headline_refresh_all_entries"]["runs"]; S["phases"]["robust"]["headline_refresh_all_entries_wall_s"] = {**stats([x["wall"] for x in r]), "post": r[0]["post"], "rss_mb": max(x["maxrss_kb"] for x in r) // 1024}
# item 2
sd = get("seed"); S["phases"]["seed"] = {"cmd": "taskset -c 0-8 tools/run-capped python -m su2plaq.lsh.loop seed --root <empty scratch dir> [--no-lean]; cold: loop_cold.py-style wrapper with CACHE_DIR redirected", "runs": {}}
for k, v in sd["runs"].items():
    r = v["runs"]; S["phases"]["seed"]["runs"][k] = {**stats([x["wall"] for x in r]), "rss_mb": max(x["maxrss_kb"] for x in r) // 1024, "post": r[0].get("post"), "load_before": [x["load_before"][0] for x in r]}
# item 4
ce = get("certify"); r = ce["runs"]["certify_headline_cli"]["runs"]
S["phases"]["certify"] = {"cmd": "taskset -c 0-8 tools/run-capped python -m su2plaq.lsh.loop certify-headline --root <scratch copy of the LSH loop state, robust.json cached>",
    "wall_s": stats([x["wall"] for x in r]), "certify_seconds_reported": stats([x["post"]["seconds"] for x in r]), "check_seconds_reported": stats([x["post"]["check_seconds"] for x in r]),
    "status": sorted({x["post"]["status"] for x in r}), "cert_name": r[0]["post"]["cert_name"], "fields_differing_vs_committed": sorted({f for x in r for f in x["post"]["fields_differing"]}),
    "checker_sha256": r[0]["post"]["checker_sha256"], "rss_mb": max(x["maxrss_kb"] for x in r) // 1024, "load_before": [x["load_before"][0] for x in r]}
# item 5
tk = get("m7tasks", -1)
M302 = {  # reports/benchmarks/302-lsh-m7.md sections 1, 2, 4 (first, later) in s; scripts/suites: median
 "LSH()": (0.1742, 0.0517), "target_UB": (0.01895, 0.01032), "target_step": (0.01954, 0.01947), "build_UE": (9.8e-5, 2.5e-5), "build_UB": (0.0531, 0.00155),
 "build_step1": (0.00163, 0.00162), "build_step2": (0.00163, 0.00161),
 "lsh_eval_UE": (0.1698, 0.1524), "lsh_eval_UB": (0.5736, 0.1843), "lsh_eval_step1": (0.5770, 0.1897), "lsh_eval_step2": (0.5740, 0.1910),
 "lsh_eval_wrap_flags4": (0.5683, 0.1825), "lsh_eval_wrap_pairs9": (0.5753, 0.1905), "lsh_eval_wrap_general7": (0.5541, 0.1890),
 "lsh_synth_UE:synthesize": (0.4260, 0.00357), "lsh_synth_UE:evaluate_synth": (0.2875, 0.2328), "lsh_synth_UB:synthesize": (0.4964, 0.00376),
 "lsh_synth_UB:evaluate_synth": (0.2479, 0.2363), "lsh_synth_step1:synthesize": (0.5035, 0.00494), "lsh_synth_step1:evaluate_synth": (0.2693, 0.2597)}
rows = []
def rec(name, tag):
    runs = tk["runs"][name]["runs"]; return runs
tasks = ["lsh_enc_build", "lsh_eval_UE", "lsh_eval_UB", "lsh_eval_step1", "lsh_eval_step2", "lsh_eval_wrap_flags4", "lsh_eval_wrap_pairs9", "lsh_eval_wrap_general7",
         "lsh_synth_UE", "lsh_synth_UB", "lsh_synth_step1"]
for task in tasks:
    keys = (["LSH()", "target_UB", "target_step", "build_UE", "build_UB", "build_step1", "build_step2"] if task == "lsh_enc_build"
            else (["evaluate"] if task.startswith("lsh_eval") else ["synthesize", "evaluate_synth"]))
    for k in keys:
        qn = k if task == "lsh_enc_build" else (task if task.startswith("lsh_eval") else f"{task}:{k}")
        row = {"quantity": qn if task != "lsh_enc_build" else "lsh_enc_build:" + k}
        for tag in ("head", "m7src"):
            runs = rec(f"{task}@{tag}", tag)
            f = [r["times"][k][0] for r in runs]; l = [t for r in runs for t in r["times"][k][1:]]
            row[tag] = {"first": stats(f), "later": stats(l), "load_before": [r["load_before"][0] for r in runs], "su2plaq_file": runs[0]["su2plaq_file"]}
        row["ratio_head_over_m7src"] = {"first": row["head"]["first"]["median"] / row["m7src"]["first"]["median"], "later": row["head"]["later"]["median"] / row["m7src"]["later"]["median"]}
        m = M302.get(qn)
        if m: row["report302"] = {"first": m[0], "later": m[1]}; row["head_over_302"] = {"first": row["head"]["first"]["median"] / m[0], "later": row["head"]["later"]["median"] / m[1]}
        rows.append(row)
lc = tk["runs"]["lsh_lean_cert@head"]["runs"]
S["phases"]["m7tasks"] = {"raw": raw["m7tasks"][-1][0], "rows": rows,
    "lean_cert_general_step": {"certify_total_s": stats([r["times"]["certify_total"][0] for r in lc]), "check_s": stats([r["times"]["check_seconds"][0] for r in lc]),
                               "export_s": stats([r["times"]["export_seconds"][0] for r in lc]), "report302_total_s": 1.976, "status": lc[0]["out"]["status"], "checker_sha256": lc[0]["out"]["checker_sha256"]},
    "note": "HEAD vs milestone-7 source (git archive milestone-7 src) interleaved, 5 fresh processes each, cpu 0; the first run of this phase (raw_m7tasks_INVALID_AB_head_vs_head.json, run1) compared HEAD with HEAD because of a wrong path and is discarded"}
def wall_stats(ph, name, idx=None):
    runs = [x for _, d in raw[ph] for x in d["runs"][name]["runs"]]
    return {**stats([x["wall"] for x in runs]), "rss_mb": max(x["maxrss_kb"] for x in runs) // 1024, "walls": [x["wall"] for x in runs], "load_before": [x["load_before"][0] for x in runs],
            "rc": sorted({x["rc"] for x in runs})}
S["phases"]["scripts"] = {"m7_results_head_script": wall_stats("scripts", "m7_results"), "report302_median_s": 9.20, "report302_rss_mb": 281,
    "ab": {k: wall_stats("m7results_ab", f"m7_results@{k}") for k in ("head_src_head_script", "head_src_m7script", "m7src_m7script")}}
S["phases"]["round"] = {k: {**wall_stats("round", k), "post": raw["round"][0][1]["runs"][k]["runs"][0]["post"]} for k in raw["round"][0][1]["runs"]}
S["phases"]["suites"] = {"pytest_m7": wall_stats("suite_m7", "pytest_m7"), "report302_m7_median_s": 12.08, "pytest_m8": wall_stats("suite_m8", "pytest_m8"), "pytest_unit": wall_stats("suite_unit", "pytest_unit"), "report302_unit_median_s": 504.9}
json.dump(S, open(out / "summary.json", "w"), indent=1)
for ph, lst in raw.items():
    for i, (f, d) in enumerate(lst):
        shutil.copy(f, out / f"raw_{ph}{'' if i == 0 else '_' + str(i)}.json")
for lf in sorted(pathlib.Path(rd).glob("log_pytest_m8_0.txt")) if False else []: pass
print(json.dumps(S["phases"]["evalprog"]["programs"]["headline_F3_005"], indent=1)[:1500])
