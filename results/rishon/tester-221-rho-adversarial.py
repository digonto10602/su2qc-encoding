"""Tester 221: adversarial angle programs through the production robust_metrics (kind UE seed + one extra free-ancilla rotation pair p(x), p(-x)):
 constants equal to the nominal alpha / beta, 2-decimal constant (alias window of recognise_angle at (0.37, 0.61)), alpha*beta, alpha^2, (alpha+beta)/2 (linear but no sqrt2 beta),
 (alpha + sqrt2 beta)/2 (linear, with sqrt2 beta), -3*beta/7, a/2 + beta... Expectation: linear iff the expression is a TRUE linear form in alpha, beta, sqrt2 beta."""
import os, sys, json, subprocess, tempfile, pathlib
import su2plaq.rishon.compress
from su2plaq.rishon.compress import robust
from su2plaq.compress.spec import default_spec, ROOT
spec = default_spec("rishon", "UE")
src = (ROOT / "compress/programs/rishon/seed/000-general-ue.py").read_text()
tmp = pathlib.Path(tempfile.mkdtemp(prefix="t221rho", dir=sys.argv[1]))
cases = {
 "const_0.37_(=alpha nominal)": ("0.37", False), "const_0.61_(=beta nominal)": ("0.61", False), "const_0.12_(2 decimals)": ("0.12", False),
 "const_1.58_(2 decimals)": ("1.58", False), "alpha*beta": ("spec.alpha*spec.beta", False), "alpha**2": ("spec.alpha**2", False),
 "(alpha+beta)/2 [true linear, no sqrt2]": ("(spec.alpha+spec.beta)/2", True), "(alpha+sqrt2*beta)/2 [true linear]": ("(spec.alpha+2**0.5*spec.beta)/2", True),
 "-3*beta/7 [true linear]": ("-3*spec.beta/7", True), "8*sqrt2*beta [locked example]": ("8*2**0.5*spec.beta", True), "(3 alpha - 5 sqrt2 beta + beta)/8 [true linear]": ("(3*spec.alpha-5*2**0.5*spec.beta+spec.beta)/8", True),
 "beta+0.01 [affine, not linear]": ("spec.beta+0.01", False)}
out = {}
for name, (expr, truth) in cases.items():
    prog = src.replace("    return b", f"    w = b.alloc(1, 'w')\n    b.p({expr}, w[0])\n    b.p(-({expr}), w[0])\n    b.free(w)\n    return b")
    f = tmp / (str(abs(hash(name)) % 10**8) + ".py"); f.write_text(prog)
    r = robust.robust_metrics(f, spec, root=tmp)
    out[name] = dict(truth_linear=truth, production_linear=r["angle_linear"], robust_key_rho=None if r["robust_key"] is None else r["robust_key"][2], fit_extra=r["angle_fit"][-2:], skeleton_equal=r["skeleton_equal"])
    print(f"{name:55s} truth {truth!s:5s} production {r['angle_linear']!s:5s} {'OK' if truth == r['angle_linear'] else 'MISMATCH (conservative)' if (truth and not r['angle_linear']) else 'MISMATCH (UNSOUND)'} fit {r['angle_fit'][-2:]}", flush=True)
json.dump(dict(commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), result=out), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tester-221-rho-adversarial.json"), "w"), indent=1, default=str)
