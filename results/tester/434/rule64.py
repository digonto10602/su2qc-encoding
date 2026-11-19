"""Tester 434: the exporter rule of prompts/204 section 6.4 (angle_fit_not_confirmed) with real program files."""
import json, pathlib, shutil
from su2plaq.rishon import lean_cert as LC
from su2plaq.rishon.compress import spec as SP, round as RD
src = pathlib.Path("compress/programs/rishon/seed/000-general-ue.py").read_text()
D = pathlib.Path("scratch/t434/rule64"); D.mkdir(parents=True, exist_ok=True)
spec = SP.rishon_spec("UE")
out = {}
def prog(name, text): p = D / name; p.write_text(text); return p
good = prog("good.py", src)
bad_const = prog("bad_const.py", src.replace("-0.75 * spec.alpha", "(-0.75 * 0.37)"))                       # linear only at the nominal alpha
bad_quad = prog("bad_quad.py", src.replace("-0.75 * spec.alpha", "(-0.75 * 0.37 * (spec.alpha / 0.37) ** 2)"))  # same at nominal
bad_skel = prog("bad_skel.py", src.replace("    b.cx(12, 13)\n    b.p(-0.75 * spec.alpha, 13)", "    b.cx(12, 13)\n    if spec.alpha > 1.0:\n        b.p(0.1, 13)\n    b.p(-0.75 * spec.alpha, 13)"))
for nm, p in [("good", good), ("const", bad_const), ("quad", bad_quad), ("skeleton_changes", bad_skel)]:
    fit = LC.confirm_angle_fit(str(p.resolve()), spec)
    circ, err = RD._circuit_of(spec, str(p.resolve()), nm, None, pathlib.Path("."))
    bare = LC.certify_circuit(circ, spec, out_dir=D / "bare")
    gated = LC.certify_circuit(circ, spec, out_dir=D / "gated", angle_fit=fit)
    via_round, _ = RD._certify(circ, spec, str(p.resolve()), pathlib.Path("."))
    out[nm] = {"confirmed": fit["confirmed"], "reason": fit["reason"][:90], "bare_status": bare.status, "gated_status": gated.status,
               "gated_reason": gated.reason[:90], "round._certify_status": via_round["status"], "round._certify_reason": via_round.get("reason", "")[:90]}
    print(nm, out[nm])
json.dump(out, open("results/tester/434-rule64.json", "w"), indent=1)
