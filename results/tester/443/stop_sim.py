"""Tester 443: stop-state on a COPY of the stop inputs (scratch root; stop_state() writes stop.json back, so the real tree is not used).
(a) current files: sessions 19, stop False.  (b) + one proposer session in round 6 (family F3 brief exists) and a round-6 record that does not improve: sessions 20 -> stop (max_sessions),
streak 2.  (c) round-6 record that does improve: still stop by max_sessions.  (d) the rule at the margins: improves() on constructed records.  No RNG."""
import json, sys, shutil, pathlib, subprocess, copy
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding"); TMP = pathlib.Path(sys.argv[1])
from su2plaq.lsh import loop as LL
for sub in ("results/compress/lsh", "compress/attempts", "compress/ideation"): (TMP / sub).mkdir(parents=True, exist_ok=True)
shutil.copy(ROOT / "results/compress/lsh/stop.json", TMP / "results/compress/lsh/stop.json")
shutil.copy(ROOT / "compress/attempts/lsh.jsonl", TMP / "compress/attempts/lsh.jsonl")
shutil.copy(ROOT / "compress/ideation/lsh.md", TMP / "compress/ideation/lsh.md")
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": None}
cli = subprocess.run([sys.executable, "-m", "su2plaq.lsh.loop", "stop-state", "--root", str(TMP)], capture_output=True, text=True, cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": "src"})
out["cli_current"] = {"rc": cli.returncode, "stdout_head": cli.stdout[:300]}
st = LL.stop_state(TMP); out["a"] = {k: st[k] for k in ("streak", "sessions", "stop", "reason", "reasons")}
last = json.loads((TMP / "results/compress/lsh/stop.json").read_text())["rounds"][-1]
# (b) round 6: one session, record identical to round 5's (no improvement)
att = TMP / "compress/attempts/lsh.jsonl"; lines = att.read_text().splitlines(); a0 = json.loads(lines[-1]); a6 = dict(a0, round=6, family="F3", id="r06-F3-006")
att.write_text("\n".join(lines + [json.dumps(a6)]) + "\n")
raw = json.loads((TMP / "results/compress/lsh/stop.json").read_text())["rounds"]
raw6 = [{k: v for k, v in x.items() if k != "improved"} for x in raw] + [{"round": 6, "headline_id": "r06-F3-006", "robust_key": last["robust_key"], "record": last["record"]}]
(TMP / "results/compress/lsh/stop.json").write_text(json.dumps({"rounds": raw6}))
st = LL.stop_state(TMP); out["b_no_improvement"] = {k: st[k] for k in ("streak", "sessions", "stop", "reason", "reasons")}
# (c) improvement in round 6 (cx 66)
rec = copy.deepcopy(last["record"]); rec["cx"] = 66
raw6[-1] = {"round": 6, "headline_id": "r06-F3-006", "robust_key": last["robust_key"], "record": rec}
(TMP / "results/compress/lsh/stop.json").write_text(json.dumps({"rounds": raw6}))
st = LL.stop_state(TMP); out["c_improvement"] = {k: st[k] for k in ("streak", "sessions", "stop", "reason", "reasons")}
# (d) improves() margins: round-5 record vs round-4 record, and constructed variants
r4 = [x for x in raw if x["round"] == 4][0]["record"]; r5 = [x for x in raw if x["round"] == 5][0]["record"]
out["d"] = {"r5_vs_r4": LL.improves(r5, r4), "r4_vs_r5": LL.improves(r4, r5), "r5_equal_but_qubits_23": LL.improves(dict(r5, qubits=23), r4), "r5_equal_but_rho_1": LL.improves(dict(r5, rho=1), r4),
            "cx_67": LL.improves(dict(r5, cx=67), r4), "t_sum_minus_441 (outside 20*22 band, same cx/n_rot/t_fixed)": LL.improves(dict(r5, t_sum=r4["t_sum"] - 441), r4),
            "t_sum_minus_440 (inside band -> tie -> (rho,qubits) equal -> False)": LL.improves(dict(r5, t_sum=r4["t_sum"] - 440), r4),
            "depth_not_in_record": "depth" not in r5 and set(r5) == {"id", "cx", "t_sum", "rho", "qubits", "n_rot", "t_fixed"}}
print(json.dumps(out, indent=1))
json.dump(out, open(ROOT / "results/tester/443/stop_sim.json", "w"), indent=1)
