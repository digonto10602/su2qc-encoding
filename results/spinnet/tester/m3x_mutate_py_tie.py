"""Report 107: for mutants that survive all Lean theorems, show that the locked PYTHON-side ties (Lean sixj vs sympy; Lean gate
matrices vs Qiskit Operator) catch them.  Runs bare `lean` on the mutated concatenated file + an appended #eval (scratch dir)."""
import itertools, pathlib, subprocess, sys, json
import numpy as np
sys.path.insert(0, "results/spinnet/tester"); sys.path.insert(0, "src")
import m3x_mutate as M
from sympy import Rational
from sympy.physics.wigner import wigner_6j
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

scratch = pathlib.Path(sys.argv[1]); out = {}
def mutated(mid, extra):
    edits = dict((m[0], m[2]) for m in M.MUT)[mid] if mid in dict((m[0], m[2]) for m in M.MUT) else EXTRA[mid]
    t = M.base_text()
    for old, new, cnt in edits:
        assert t.count(old) == cnt, (mid, old, t.count(old))
        t = t.replace(old, new)
    d = scratch / (mid + "_tie"); d.mkdir(exist_ok=True)
    f = d / "Mut.lean"; f.write_text(t + "\nopen Su2Plaq.SpinNet\n" + extra + "\n")
    r = subprocess.run(["taskset", "-c", "0-9", "lean", str(f)], capture_output=True, text=True, cwd=str(M.REPO / "lean"), timeout=600)
    return [l for l in r.stdout.splitlines() if "error" not in l and "warning" not in l and l.strip() and not l.startswith(" ")]
EXTRA = {
 "T2b_F_J12_value": [("  ⟨⟨ph * s.q.num, s.q.den⟩, s.r.mul", "  let ph : Int := if j1 == 1 && j2 == 0 && j12 == 1 then -ph else ph\n  ⟨⟨ph * s.q.num, s.q.den⟩, s.r.mul", 1)],
 "T2c_F_J0_value": [("  ⟨⟨ph * s.q.num, s.q.den⟩, s.r.mul", "  let ph : Int := if j1 == 0 && j2 == 1 && j12 == 1 && j3 == 1 && J == 0 then -ph else ph\n  ⟨⟨ph * s.q.num, s.q.den⟩, s.r.mul", 1)],
 "T7_sixj_single_value": [("  else SR.zero\n\n/-- F-symbol", "  else SR.zero\n\n/-- F-symbol", 1)],
}
# 6j table
sixj_eval = ("#eval IO.println (String.intercalate \"\\n\" ((List.range 729).map fun i =>\n"
  "  let a := i / 243 % 3; let b := i / 81 % 3; let c := i / 27 % 3; let d := i / 9 % 3; let e := i / 3 % 3; let f := i % 3\n"
  "  let s := sixj a b c d e f\n  s!\"{a} {b} {c} {d} {e} {f} {s.q.num} {s.q.den} {s.r.num} {s.r.den}\"))")
def sixj_dev(lines):
    worst = 0.0; nbad = 0
    for l in lines:
        p = l.split()
        if len(p) != 10: continue
        a, b, c, d, e, f, qn, qd, rn, rd = map(int, p)
        v = qn / qd * (rn / rd) ** 0.5
        args = (a, b, c, d, e, f)
        try:
            ref = float(wigner_6j(*(Rational(x, 2) for x in args)).evalf(30))
        except ValueError:
            ref = 0.0
        dev = abs(v - ref); worst = max(worst, dev); nbad += dev > 1e-12
    return worst, nbad
for mid in ("T1_racah_sign", "T2_one_F_value"):
    worst, nbad = sixj_dev(mutated(mid, sixj_eval))
    out[mid + "_sixj_vs_sympy"] = dict(max_dev=worst, entries_off_of_729=nbad)
# F-symbol value changes: K unchanged? (equivalent mutant for K) report the number of 47x47 K entries that change
# gate images
for mid in ("G6_rccx_phase_conj", "G7_rccx_toffoli"):
    body = ("#eval IO.println (String.intercalate \"\\n\" ((List.range 8).flatMap fun i =>\n"
            "  (applyBasis (Gate.rccx 0 1 2) i [(0, 1, 0)]).flatMap fun p => p.2.map fun t => s!\"{i} {p.1} {t.1} {t.2.1} {t.2.2}\"))")
    lines = mutated(mid, body)
    mat = np.zeros((8, 8), complex)
    for l in lines:
        p = l.split()
        if len(p) == 5:
            i, j, m, re, im = map(int, p); mat[j, i] += complex(re, im)
    qc = QuantumCircuit(3); qc.rccx(0, 1, 2)
    out[mid + "_rccx_matrix_vs_qiskit"] = float(np.abs(mat - Operator(qc).data).max())
qc = QuantumCircuit(3); qc.rccx(0, 1, 2)
print(json.dumps(out, indent=1))
pathlib.Path("results/spinnet/tester/m3x_mutation_pytie.json").write_text(json.dumps(out, indent=1))
