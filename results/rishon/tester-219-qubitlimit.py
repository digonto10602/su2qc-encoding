"""Tester 219: verify commit 27bc972 (engine_qubit_limit).  Padded copies of the valid round-2 program r02-F3-001 (54 qubits) with k extra clean ancillas that are
used (cx(0,q) twice, so they are touched but end clean), total n = 62 (valid expected), 63, 64, 70, 80 (invalid engine_qubit_limit expected), 81 (invalid max_qubits expected).
Paths: evaluate_program full + trial, run_candidate CLI, run_round (dry_run=False, root=scratch dir: archive/attempts/feedback/round JSON) with a mixed batch.
usage: tester-219-qubitlimit.py <scratch dir>"""
import sys, os, json, pathlib, subprocess, time
scratch = pathlib.Path(sys.argv[1]); scratch.mkdir(parents=True, exist_ok=True)
ROOT = pathlib.Path(__file__).resolve().parents[2]
import su2plaq.rishon.compress  # noqa
from su2plaq.rishon.compress import spec as S, evaluate as E, round as RD
spec = S.rishon_spec("step")
src0 = (ROOT / "compress/programs/rishon/F3/001-hadamard-test-partner.py").read_text()
assert src0.count("def build(spec)") == 1


def padded(n_total, name):
    k = n_total - 54
    s = src0.replace("def build(spec)", "def _build0(spec)")
    s += f"\n\ndef build(spec):\n    b = _build0(spec)\n    q = b.alloc({k}, 'pad')\n    for x in q:\n        b.cx(0, x)\n        b.cx(0, x)\n    return b\n"
    d = scratch / "compress" / "programs" / "rishon" / "F3"
    d.mkdir(parents=True, exist_ok=True)
    f = d / name
    f.write_text(s)
    return f


out = dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT).decode().strip(), rows=[])
files = {n: padded(n, f"{n:03d}-pad{n}.py") for n in (62, 63, 64, 70, 80, 81)}
print("constants: ENGINE_QUBIT_LIMIT", S.ENGINE_QUBIT_LIMIT, "REASON", S.REASON_ENGINE_QUBIT_LIMIT, "peak_qubit_cap", spec.peak_qubit_cap(), flush=True)
for n, f in files.items():
    for mode in ("full", "trial"):
        t0 = time.time()
        try:
            r = E.evaluate_program(f, spec, mode)
            row = dict(n=n, mode=mode, valid=r.valid, reason=r.reason, message=r.message, wall=round(time.time() - t0, 1), qubits=(r.metrics or {}).get("qubits"),
                       err=(r.verdict.op_norm_error if r.verdict is not None else None), exc=None)
        except Exception as ex:
            row = dict(n=n, mode=mode, exc=f"{type(ex).__name__}: {ex}")
        out["rows"].append(row)
        print(row, flush=True)
env = {**os.environ, "PYTHONPATH": "src"}
for n in (62, 63, 81):
    p = subprocess.run([sys.executable, "-m", "su2plaq.rishon.compress.run_candidate", str(files[n]), "--kind", "step", "--trial"], capture_output=True, text=True, cwd=ROOT, env=env)
    print("CLI --trial n=%d exit %d: %s" % (n, p.returncode, (p.stdout.splitlines() or [""])[0]), "| stderr tail:", p.stderr.strip()[-120:], flush=True)
    out["rows"].append(dict(cli=True, n=n, mode="trial", exit=p.returncode, first_line=(p.stdout.splitlines() or [""])[0], stderr_tail=p.stderr.strip()[-200:]))
p = subprocess.run([sys.executable, "-m", "su2plaq.rishon.compress.run_candidate", str(files[63]), "--kind", "step", "--full"], capture_output=True, text=True, cwd=ROOT, env=env)
print("CLI --full n=63 exit %d:\n%s" % (p.returncode, p.stdout[:600]), "| stderr:", p.stderr.strip()[-200:], flush=True)
out["rows"].append(dict(cli=True, n=63, mode="full", exit=p.returncode, stdout=p.stdout[:800], stderr_tail=p.stderr.strip()[-200:]))
t0 = time.time()
info = RD.run_round("step", 1, evaluate=True, dry_run=False, root=scratch, proposals=[files[62], files[63], files[80], files[81]], lean=False)
print("run_round:", {k: info[k] for k in ("round", "n_valid", "n_invalid", "best_key", "entries")}, "%.0f s" % (time.time() - t0), flush=True)
rd = json.load(open(scratch / "results/compress/rishon/round-001.json"))
inv = rd["invalid"]
print("round JSON invalid:", [(i.get("label") or i.get("id"), i["reason"], i["message"][:70]) for i in inv], flush=True)
att = [json.loads(l) for l in open(scratch / "compress/attempts/rishon.jsonl")]
fb = sorted(os.listdir(scratch / "results/compress/rishon/feedback"))
idx = json.load(open(scratch / "compress/archive/rishon/index.json"))
ents = sorted(os.listdir(scratch / "compress/archive/rishon/entries"))
print("attempts:", [(a["id"], a["valid"], a["reason"]) for a in att], "| feedback:", fb, "| archive entries:", ents, "| best:", idx["best"], flush=True)
out["round"] = dict(info={k: info[k] for k in ("round", "n_valid", "n_invalid", "best_key", "entries")}, invalid=inv, attempts=[(a["id"], a["valid"], a["reason"]) for a in att], feedback=fb, entries=ents,
                    best=idx["best"], n_valid_round_json=rd["n_valid"], n_invalid_round_json=rd["n_invalid"])
json.dump(out, open(ROOT / "results/rishon/tester-219-qubitlimit.json", "w"), indent=1, default=str)
