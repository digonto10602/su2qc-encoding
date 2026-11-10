"""Tester 221: does the 2-decimal alias of recognise_angle (0.12 = 12 alpha/37 at alpha = 0.37) fool robust_metrics?  UE seed program + p(c)/p(-c) on a freed ancilla,
c = 0.12 (alias at nominal pair), 0.123 (no alias), 0.37*3/4 (true alpha-linear). Expect: linear False, False, True."""
import json, os, pathlib, tempfile, subprocess, sys
import su2plaq.rishon.compress
from su2plaq.rishon.compress import robust
from su2plaq.rishon.compress import baselines as BL
from su2plaq.compress.spec import default_spec
spec = default_spec("rishon", "UE")
gp = pathlib.Path(BL.general_program_path(spec)); src = gp.read_text()
tmp = pathlib.Path(tempfile.mkdtemp(prefix="t221alias", dir=sys.argv[1]))
out = {}
for name, expr in [("c0.12", "0.12"), ("c0.123", "0.123"), ("c0.1233_alpha_lin", "0.75*spec.alpha"), ("c0.50_beta_lin", "0.5*spec.beta")]:
    body = f'    w = b.alloc(1, "w")\n    b.p({expr}, w[0])\n    b.p(-({expr}), w[0])\n    b.free(w)\n'
    i = src.index("    return b")
    f = tmp / f"{name}.py"; f.write_text(src[:i] + body + src[i:])
    r = robust.robust_metrics(f, spec, root=tmp)
    out[name] = dict(linear=r["angle_linear"], rho=None if r["robust_key"] is None else r["robust_key"][2], fits=[tuple(x) if x else None for x in r["angle_fit"]][-2:])
    print(name, out[name], flush=True)
json.dump(dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip(), result=out), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tester-221-alias.json"), "w"), indent=1, default=str)
