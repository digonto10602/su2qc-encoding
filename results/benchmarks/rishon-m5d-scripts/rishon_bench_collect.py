"""Collect benchmark 303 (rishon milestone 5d) raw records -> results/rishon/bench-303-m5d.json (medians, ranges, commit, load, machine)."""
import json, statistics as st, collections, subprocess, re, os, platform
ROOT = "/home/digimonk/Projects/su2qc-encoding"; RAW = ROOT + "/results/benchmarks/rishon-m5d-raw/"
def load(f):
    d = collections.defaultdict(list)
    for l in open(RAW + f):
        r = json.loads(l); d[r["task"]].append(r)
    return d
def summarize(d):
    out = {}
    for t, rs in d.items():
        names = collections.OrderedDict()
        for r in rs:
            for k, v in r["times"].items(): names.setdefault(k, []).append(v)
        e = {"n_processes": len(rs), "rss_mb_median": st.median(r["rss_mb"] for r in rs), "wall_process_s_median": st.median(r["wall_process_s"] for r in rs),
             "load1_start": [r["load_start"][0] for r in rs if "load_start" in r], "cpu": sorted({(r.get("cpu_start"), r.get("cpu_end")) for r in rs}), "times": {}}
        for k, vs in names.items():
            first = [v[0] for v in vs]; later = [x for v in vs for x in v[1:]]
            e["times"][k] = {"first_median": st.median(first), "first_min": min(first), "first_max": max(first),
                             "later_median": st.median(later) if later else None}
        e["out_first"] = rs[0].get("out")
        out[t] = e
    return out
def tfile(p):
    s = open(RAW + p).read(); m = re.search(r"seconds\): ([\d.]+)", s); r = re.search(r"\(kbytes\): (\d+)", s)
    return {"wall_s": float(m.group(1)), "max_rss_kb": int(r.group(1))}
J = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip(),
     "report": "reports/benchmarks/303-rishon-milestone-5d.md", "baseline_report": "reports/benchmarks/200-m5-rishon.md (commit 86fda8e, old SupremeCommander install)",
     "machine": "omnicommander (former supremecommander desktop, new Omarchy install), i7-12700KF, 20 threads, 31 GiB; taskset cpu 14 (P-core SMT thread) for single-process tasks, 14-19 for pytest/Lean",
     "python": platform.python_version(), "env": "OMP/OPENBLAS/MKL_NUM_THREADS=1 PYTHONHASHSEED=20261104",
     "seeds": {"gauss_sample_default": 20261104, "ct_compile": 12345, "eta_set": 20261110},
     "src_changes_since_b4bc2a4": "none (git diff b4bc2a4 HEAD -- src empty)",
     "rishon": summarize(load("rishon.jsonl")), "twelve": summarize(load("twelve.jsonl")),
     "pytest": {k: tfile(f"pytest_m5_{k}.time") for k in ("notslow", "notT1_1", "notT1_2", "notT1_3", "slow")},
     "lean_raw": open(RAW + "lean.txt").read().splitlines(), "l3": json.loads(open(RAW + "l3.out").read().split("RESULT ", 1)[1]), "l3_process": tfile("l3.time"),
     "control_ab_old_vs_head": json.load(open(RAW + "ctl/ctl_summary.json")),
     "load_monitor": {}}
for f in ("monitor.log", "monitor2.log"):
    L = [float(re.search(r"load=([\d.]+)", l).group(1)) for l in open(RAW + f)]
    J["load_monitor"][f] = {"samples": len(L), "load1_min": min(L), "load1_median": sorted(L)[len(L)//2], "load1_max": max(L)}
json.dump(J, open(ROOT + "/results/rishon/bench-303-m5d.json", "w"), indent=1, default=str)
print("written")
# comparison table vs report 200 (values typed from reports/benchmarks/200-m5-rishon.md section 1 and 3)
R = J["rishon"]; T = J["twelve"]
def f(t, k, w="first_median"): return R[t]["times"][k][w]
rows = {"basis_cold": (2.372, f("basis", "rishon_basis_cold")), "W_build": (0.0685, f("inner", "_W_build_after_sector_ops")),
        "eigh1296": (1.275, f("inner", "eigh_1296_complex128_with_vectors")), "inner_target_UB": (1.005, f("inner", "inner_target_UB1")),
        "inner_target_step1": (1.225, f("inner", "inner_target_step1")), "inner_target_step2": (1.455, f("inner", "inner_target_step2")),
        "build_UE_cold": (0.132, f("build", "build_UE")), "build_UB_cold": (1.838, f("build", "build_UB")),
        "verify_UE_first": (4.74, f("verify_UE", "verify")), "verify_UB_first": (6.38, f("verify_UB", "verify")),
        "verify_step_first": (6.58, f("verify_step", "verify")), "verify_step2_first": (6.84, f("verify_step2", "verify")),
        "synth_UE_verify": (6.95, f("synth_UE_1e-6", "verify_synth")), "synth_UB_verify": (276.6, f("synth_UB_1e-6", "verify_synth")),
        "ttable_UB_cold": (0.71, f("ttable_UB", "t_table_qiskit_False_cold")), "ttable_step_cold": (0.79, f("ttable_step", "t_table_qiskit_False_cold")),
        "twelve_eval_UB_later": (0.800, T["eval_UB"]["times"]["evaluate"]["later_median"]), "paulo_evaluate": (24.34, T["paulo_m1"]["times"]["evaluate_paulo"]["first_median"])}
J["comparison_vs_report200"] = {k: {"report200": a, "now": b, "change_pct": 100 * (b / a - 1)} for k, (a, b) in rows.items()}
json.dump(J, open(ROOT + "/results/rishon/bench-303-m5d.json", "w"), indent=1, default=str)
