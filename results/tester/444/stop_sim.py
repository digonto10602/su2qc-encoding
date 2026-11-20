"""Tester 444: stop-state on a COPY of the stop inputs (scratch root; stop_state() writes stop.json back, so the real tree is not used).
(a) current files (round 6 done): expect sessions 20, streak 2, stop True, reason max_sessions (CLI and function).
(b) the same copy with the round-6 attempt line and round-6 record removed (= the state of report 443): sessions 19, stop False, streak 1.
(c) round-6 record that WOULD improve (cx 66): streak 0, still stop by max_sessions.  (d) improves() at the margins.  No RNG.
Run: PYTHONPATH=src python results/tester/444/stop_sim.py <scratch dir>"""
import json, sys, shutil, pathlib, subprocess, copy, os
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding"); TMP = pathlib.Path(sys.argv[1])
from su2plaq.lsh import loop as LL
for sub in ("results/compress/lsh", "compress/attempts", "compress/ideation"): (TMP / sub).mkdir(parents=True, exist_ok=True)
def fresh():
    shutil.copy(ROOT / "results/compress/lsh/stop.json", TMP / "results/compress/lsh/stop.json")
    shutil.copy(ROOT / "compress/attempts/lsh.jsonl", TMP / "compress/attempts/lsh.jsonl")
    shutil.copy(ROOT / "compress/ideation/lsh.md", TMP / "compress/ideation/lsh.md")
keys = ("streak", "sessions", "stop", "reason", "reasons")
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": None}
fresh()
cli = subprocess.run([sys.executable, "-m", "su2plaq.lsh.loop", "stop-state", "--root", str(TMP)], capture_output=True, text=True, cwd=ROOT, env={**os.environ, "PYTHONPATH": "src"})
out["cli_current"] = {"rc": cli.returncode, "stdout_head": cli.stdout[:400]}
st = LL.stop_state(TMP); out["a_current"] = {k: st[k] for k in keys}
real = json.loads((ROOT / "results/compress/lsh/stop.json").read_text()); out["real_file"] = {k: real[k] for k in keys}
# (b) back to the round-5 state
fresh(); att = TMP / "compress/attempts/lsh.jsonl"
lines = [l for l in att.read_text().splitlines() if l.strip() and json.loads(l)["round"] != 6]; att.write_text("\n".join(lines) + "\n")
rounds = [{k: v for k, v in x.items() if k != "improved"} for x in real["rounds"] if x["round"] != 6]
(TMP / "results/compress/lsh/stop.json").write_text(json.dumps({"rounds": rounds}))
st = LL.stop_state(TMP); out["b_round5_state"] = {k: st[k] for k in keys}
# (c) round 6 improving
fresh(); r6 = [x for x in real["rounds"] if x["round"] == 6][0]
rec = copy.deepcopy(r6["record"]); rec["cx"] = 66
rounds = [{k: v for k, v in x.items() if k != "improved"} for x in real["rounds"] if x["round"] != 6] + [{"round": 6, "headline_id": "r06-X", "robust_key": r6["robust_key"], "record": rec}]
(TMP / "results/compress/lsh/stop.json").write_text(json.dumps({"rounds": rounds}))
st = LL.stop_state(TMP); out["c_improving_round6"] = {k: st[k] for k in keys}
# (d) margins
r4 = [x for x in real["rounds"] if x["round"] == 4][0]["record"]; r5 = [x for x in real["rounds"] if x["round"] == 5][0]["record"]; r6r = r6["record"]
out["d"] = {"r6_vs_r4": LL.improves(r6r, r4), "r6_equals_r5_record": r6r == r5, "cx_67": LL.improves(dict(r6r, cx=67), r4), "qubits_23": LL.improves(dict(r6r, qubits=23), r4),
            "t_sum_minus_441": LL.improves(dict(r6r, t_sum=r4["t_sum"] - 441), r4), "t_sum_minus_440": LL.improves(dict(r6r, t_sum=r4["t_sum"] - 440), r4)}
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/tester/444/stop_sim.json", "w"), indent=1)
