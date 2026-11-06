"""M2 step 2.L5: Lean certificate of the general step circuit (round-0 seed) and its theorem file.

    PYTHONPATH=src python scripts/lean_general_cert.py [--no-theorem-file]

Builds `baselines.general_circuit(default_spec("twelve", "step"))`, exports and checks the exact certificate
(`compress/lean/certs/*.json`, gitignored), writes `lean/certs/twelve-general-step.lean` (committed; `native_decide` on the
certificate string) and `results/lean/general_step_certificate.json` with provenance and timings.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time

from su2plaq.compress.baselines import general_circuit
from su2plaq.compress.spec import default_spec
from su2plaq.lean import certify as C
from su2plaq.metrics.provenance import provenance

ROOT = pathlib.Path(__file__).resolve().parents[1]
THEOREM = "gen_step_ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-theorem-file", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "results" / "lean" / "general_step_certificate.json"))
    args = ap.parse_args()
    spec = default_spec("twelve", "step")
    qc = general_circuit(spec)
    t0 = time.time()
    cert = C.certify_circuit(qc, spec)
    doc = {"circuit": "general_circuit(twelve, step)", "n_qubits_circuit": qc.num_qubits, "n_gates_circuit": len(qc.data),
           "alpha": spec.alpha, "beta": spec.beta, "order": spec.order, "status": cert.status, "reason": cert.reason,
           "cert_path": cert.cert_path, "seconds_export_and_check": cert.seconds, "checker_sha256": cert.checker_sha256}
    if cert.status == "certified" and not args.no_theorem_file:
        f = C.write_theorem_file(cert.cert_path, THEOREM, ROOT / "lean" / "certs" / "twelve-general-step.lean")
        doc["theorem_file"] = str(f.relative_to(ROOT))
        doc["theorem_name"] = THEOREM
    doc["provenance"] = provenance({})
    doc["seconds_total"] = time.time() - t0
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, default=str))
    print(json.dumps({k: doc[k] for k in ("status", "reason", "seconds_export_and_check", "seconds_total")}))
    return 0 if cert.status == "certified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
