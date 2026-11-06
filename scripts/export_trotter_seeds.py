"""One-off exporter: vendor su2qc-trotter's plaquette circuits `lean22` and `lean22_v2` as JSON gate lists (refs/trotter/).

    PYTHONPATH=/home/digimonk/Projects/su2qc-trotter/src python scripts/export_trotter_seeds.py

This is the ONLY place that imports su2trotter (cross-project imports are not allowed in src/).  The gate lists are the
PLAQUETTE only (kind "UB": exp(+i alpha_P Re Tr W) with alpha_P = 2 beta); su2qc-trotter applies its electric phases after the
plaquette (U_E U_B), the opposite of ours, so they are not exported (audit 003 N4).  Every rz angle is exported as a coefficient c
with theta = c * alpha_P (checked linear: c(alpha=2) == 2 c(alpha=1), c(alpha=0) == 0); the skeleton is checked angle independent.
"""
import json
import pathlib
import subprocess

from su2trotter import lean
from su2trotter.designs import lean22_v2 as L

root = pathlib.Path(__file__).resolve().parents[1]
trotter = pathlib.Path(L.__file__).resolve().parents[3]
commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=trotter, capture_output=True, text=True, check=True).stdout.strip()
dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=trotter, capture_output=True, text=True).stdout.strip())

out = {}
for name, fn, src in (("lean22", lambda a: lean.build(a), "su2trotter.lean.build(alpha)"),
                      ("lean22_v2", lambda a: L.A_plaq(a), "su2trotter.designs.lean22_v2.A_plaq(alpha)")):
    c0, c1, c2 = fn(0.0), fn(1.0), fn(2.0)
    sk = [(g.name, g.qubits) for g in c1.gates]
    assert sk == [(g.name, g.qubits) for g in c2.gates] == [(g.name, g.qubits) for g in c0.gates], name
    gates = []
    for g0, g1, g2 in zip(c0.gates, c1.gates, c2.gates):
        if g1.param is None:
            gates.append([g1.name, list(g1.qubits), None])
        else:
            assert abs(g0.param) < 1e-12 and abs(g2.param - 2 * g1.param) < 1e-12, (name, g1)
            gates.append([g1.name, list(g1.qubits), g1.param])     # coefficient of alpha_P
    out[name] = {"source": src, "commit": commit, "commit_dirty": dirty, "num_qubits": c1.num_qubits,
                 "registers": c1.registers, "kind": "UB", "angle": "rz(theta) with theta = coefficient * alpha_P, alpha_P = 2 beta",
                 "gates": gates}
(root / "refs" / "trotter" / "plaquette_seeds.json").write_text(json.dumps(out, indent=1))
print({k: (v["num_qubits"], len(v["gates"])) for k, v in out.items()}, commit, "dirty" if dirty else "clean")
