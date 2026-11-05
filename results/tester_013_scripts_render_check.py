import sys, json, pathlib, re, shutil, tempfile, math, dataclasses
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
import numpy as np
from su2plaq.evaluate.evaluator import Verdict
from su2plaq.results.store import save_result, load_result, verdict_to_dict, RESULT_KEYS
from su2plaq.results.report import render

S = pathlib.Path("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/r13")
S.mkdir(exist_ok=True)
print("Verdict fields:", [f.name for f in dataclasses.fields(Verdict)])
out = {}

# ---------- 1. Verdict with inf values round trip
v = Verdict(ok=False, reason="leak", op_norm_error=float("inf"), max_leak=float("inf"), dirty_ancilla=float("nan"),
            phase=complex(0.6, -0.8), outer_bits_read=3, n_blocks=7, gauss_residual=float("inf"), method="inner_span",
            engine="aer_mps", seconds=1.25, failing_inputs=[1, 5, 9], n_inputs=625,
            tolerances={"tol_err": 1e-10, "tol_leak": 1e-12, "tol_gauss": 1e-9})
vd = verdict_to_dict(v)
print("verdict_to_dict keys:", list(vd))
p = save_result(S / "inf.json", encoding="twelve", circuit_id="inf", kind="UB", params={"alpha": None, "beta": 0.61, "order": 1},
                verification=v, metrics={"logical": {"cx": 1}}, seeds={"t": 20261104})
txt = p.read_text()
print("raw tokens:", re.findall(r"Infinity|-Infinity|NaN", txt))
d = load_result(p)
print("loaded op_norm_error:", d["verification"]["op_norm_error"], "gauss", d["verification"]["gauss_residual"],
      "dirty_ancilla", d["verification"]["dirty_ancilla"], "phase", d["verification"]["phase"], "failing", d["verification"]["failing_inputs"])
out["inf_roundtrip_inf_ok"] = d["verification"]["op_norm_error"] == math.inf and d["verification"]["max_leak"] == math.inf
out["nan_roundtrip_ok"] = math.isnan(d["verification"]["dirty_ancilla"])
out["phase_ok"] = d["verification"]["phase"] == [0.6, -0.8]
# second save of loaded -> identical text
p2 = save_result(S / "inf2.json", encoding=d["encoding"], circuit_id=d["circuit_id"], kind=d["kind"], params=d["params"],
                 verification=d["verification"], metrics=d["metrics"], files=d["files"], extra=d["extra"], seeds=d["provenance"]["seeds"])
a, b = json.loads(txt), json.loads(p2.read_text())
a["provenance"].pop("timestamp_utc"); b["provenance"].pop("timestamp_utc")
out["resave_identical_modulo_timestamp"] = (json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True))
# strict parsers
def strict(s):
    def bad(c): raise ValueError("non-strict constant " + c)
    return json.loads(s, parse_constant=bad)
try:
    strict(txt); out["strict_python_parse"] = "ok"
except ValueError as e:
    out["strict_python_parse"] = "REJECTED: " + str(e)
print("strict python parse:", out["strict_python_parse"])
for tool in ("jq", "node"):
    pass

# ---------- 2. render: only JSON numbers, idempotent, perturbation
ver = {"ok": True, "reason": "ok", "op_norm_error": 1.2345e-13, "max_leak": 2.5e-15, "gauss_residual": 3.5e-14, "method": "inner_span",
       "engine": "sparse", "certified": True}
mets = {"logical": {"cx": 294, "depth": 391, "n_rot": 14, "t_fixed": 296, "qubits": 34, "ancilla": 22},
        "t_table": [{"eps": 1e-6, "t_fixed": 296, "n_rot": 14, "t_rot_pygridsynth": 884, "t_total": 1180, "t_est": 1133.06, "t_qiskit": 1096,
                     "cx_qiskit": 294, "depth_qiskit": 2549}]}
pp = save_result(S / "base.json", encoding="twelve", circuit_id="UB", kind="UB", params={"alpha": None, "beta": 0.61, "order": 1},
                 verification=ver, metrics=mets)
r1 = render([pp]); r2 = render([pp]); r3 = render([str(pp)])
print(r1)
out["idempotent"] = (r1 == r2 == r3)
# render does not touch the file (mtime/content)
before = pp.read_bytes(); render([pp]); out["file_unchanged_by_render"] = (before == pp.read_bytes())
# numbers in rendered text vs numbers in JSON
nums_json = set()
def walk(x):
    if isinstance(x, bool) or x is None: return
    if isinstance(x, (int, float)): nums_json.add(float(x))
    elif isinstance(x, (list, tuple)): [walk(i) for i in x]
    elif isinstance(x, dict): [walk(i) for i in x.values()]
walk(json.loads(pp.read_text()))
# tokens in table cells that look numeric
toks = []
for line in r1.splitlines():
    if line.startswith("|") and not line.startswith("|---"):
        for cell in line.strip("|").split("|"):
            cell = cell.strip()
            if re.fullmatch(r"-?\d+(\.\d+)?([eE][+-]?\d+)?", cell): toks.append(cell)
# commit hash cell is not numeric-like normally; may be (e.g. 5f094ab not fullmatch). check
alien = [t for t in toks if not any(math.isclose(float(t), n, rel_tol=1e-5, abs_tol=0) for n in nums_json)]
print("numeric cells:", toks); print("cells not found in JSON:", alien)
out["alien_numeric_cells"] = alien

# perturbation: change several values in JSON, re-render, diff
def perturb(path_keys, newval, name):
    d0 = json.loads(pp.read_text())
    ref = d0
    for k in path_keys[:-1]: ref = ref[k]
    ref[path_keys[-1]] = newval
    q = S / f"{name}.json"; q.write_text(json.dumps(d0, indent=2) + "\n")
    rr = render([q])
    ld = [(x, y) for x, y in zip(r1.splitlines(), rr.splitlines()) if x != y]
    return rr, ld
cases = [(("metrics", "logical", "cx"), 777, "cx"), (("metrics", "t_table"), None, "tt"),
         (("verification", "op_norm_error"), 9.87e-7, "err"), (("verification", "ok"), False, "ok"),
         (("params", "beta"), 0.5, "beta"), (("metrics", "logical", "depth"), 4242, "depth")]
d0 = json.loads(pp.read_text())
for keys, val, name in cases:
    if name == "tt":
        d1 = json.loads(pp.read_text()); d1["metrics"]["t_table"][0]["t_total"] = 31415; q = S / "tt.json"; q.write_text(json.dumps(d1, indent=2) + "\n")
        rr = render([q]); ld = [(x, y) for x, y in zip(r1.splitlines(), rr.splitlines()) if x != y]
        probe = "31415"
    else:
        rr, ld = perturb(keys, val, name)
        probe = {"cx": "777", "err": "9.87e-07", "ok": "no", "beta": "0.5", "depth": "4242"}[name]
    print(f"perturb {name}: new value present={probe in rr}, old line changed={len(ld)==1}, n changed lines={len(ld)}")
    out[f"perturb_{name}"] = (probe in rr) and len(ld) == 1
# number fed only via JSON: change t_est, check output
d1 = json.loads(pp.read_text()); d1["metrics"]["t_table"][0]["t_est"] = 1234.5678; q = S / "test.json"; q.write_text(json.dumps(d1, indent=2) + "\n")
rr = render([q]); out["t_est_from_json"] = "1234.57" in rr and "1133.06" not in rr
print("t_est from JSON:", out["t_est_from_json"])
# multi-file order
q2 = S / "second.json"; d2 = json.loads(pp.read_text()); d2["circuit_id"] = "UE"; q2.write_text(json.dumps(d2, indent=2) + "\n")
out["order_respected"] = render([q2, pp]).index("UE") < render([q2, pp]).index("UB") and render([pp, q2]).index("UB") < render([pp, q2]).index("UE")
# dirty marker
dd = json.loads(pp.read_text()); dd["provenance"]["git_dirty"] = True; q3 = S / "dirty.json"; q3.write_text(json.dumps(dd, indent=2) + "\n")
print("dirty marker '*' in commit col:", "*" in render([q3]), "| clean has none:", "*" not in r1.split("### Logical")[0].replace("---", ""))
# load_result key validation
bad = json.loads(pp.read_text()); bad["schema_version"] = 2; (S / "bad.json").write_text(json.dumps(bad))
try: load_result(S / "bad.json"); out["bad_schema_rejected"] = False
except ValueError: out["bad_schema_rejected"] = True
bad = json.loads(pp.read_text()); del bad["extra"]; (S / "bad2.json").write_text(json.dumps(bad))
try: load_result(S / "bad2.json"); out["missing_key_rejected"] = False
except ValueError: out["missing_key_rejected"] = True
# unknown type
try:
    save_result(S / "obj.json", encoding="e", circuit_id="c", kind="k", params={"o": object()}, verification={}, metrics={}); out["unserialisable_raises"] = False
except TypeError: out["unserialisable_raises"] = True
print(json.dumps(out, indent=1))
json.dump(out, open("/home/digimonk/Projects/su2qc-encoding/results/tester_013_step010.json.tmp", "w")) if False else None
json.dump(out, open(S / "out13.json", "w"), indent=1)
