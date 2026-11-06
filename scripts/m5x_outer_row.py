"""M5x step O1: write results/rishon/UE_outer_row_certified.json (prompts/202 section 3; METHODS-rishon R6).

    PYTHONPATH=src taskset -c 10-19 python scripts/m5x_outer_row.py [--out results/rishon]

The 48-qubit U_E with the outer electric row at alpha = 0.37 (the M5 nominal alpha) is certified by
`results.outer_electric_certify`: exhaustive per-link 16 x 16 check, bound = sum of the 12 link errors (all 6^12 valid codes,
hence all 38 432 physical states).  Deterministic (no random numbers); the seed of the sampled M5 check of the same circuit
(results/rishon/UE_outer_row.json) is recorded for reference.  Provenance snapshot as scripts/m5_results.py.
Run on a clean commit: the result file's `git_dirty` flag must be false.
"""
from __future__ import annotations

import argparse
import pathlib
import platform
import resource
import sys
import time

from su2plaq.circuits import rishon as C
from su2plaq.encodings.rishon import RISHON_NOMINAL, RishonEncoding
from su2plaq.metrics.provenance import provenance
from su2plaq.results.store import save_result
from su2plaq.rishon import results as R

ALPHA, _ = RISHON_NOMINAL
SEEDS = {"outer_row_certified": None, "outer_row_sample": 20261104}   # certify is deterministic; the 2nd seed belongs to UE_outer_row.json
ROOT = pathlib.Path(__file__).resolve().parents[1]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "rishon"))
    args = ap.parse_args(argv)
    t0 = time.time()
    snap = provenance(SEEDS)
    snap["provenance_captured_at"] = snap["timestamp_utc"]
    snap["host"] = platform.node()
    snap["command"] = " ".join([pathlib.Path(sys.executable).name, *sys.argv])
    enc = RishonEncoding()
    qc = C.build_UE(ALPHA, with_outer=True, include_outer_electric=True)
    ver = R.outer_electric_certify(qc, enc, ALPHA)
    snap["wall_seconds"] = time.time() - t0
    snap["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    out = pathlib.Path(args.out).resolve()
    save_result(out / "UE_outer_row_certified.json", encoding="rishon", circuit_id="UE_outer_row_certified", kind="UE",
                params={"alpha": ALPHA}, verification=R._jsonable(ver), metrics={}, files={}, seeds=SEEDS,
                provenance_snapshot=snap,
                extra={"sampled_check_file": "results/rishon/UE_outer_row.json",
                       "note": "exhaustive per-link check; see prompts/202 section 1 O1"})
    return 0 if ver["certified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
