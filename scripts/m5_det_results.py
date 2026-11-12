"""M5 addendum step D6: write the det-layer results of prompts/204 (METHODS-rishon R13-R14) to results/rishon/.
Deterministic; every number is computed here or in su2plaq.rishon.*, none typed in.  `scripts/m5_results.py` is untouched
(its files UE, UB, step, step_order2, observables, ... stay valid as the lambda_D = 0 limit).

    PYTHONPATH=src taskset -c <cores> tools/run-capped python scripts/m5_det_results.py [--out results/rishon] [--quick] [--jobs N]

Run on a CLEAN commit (git_dirty must be false in the files; tests M5-DT7 / M5X-O2 check it).

Files (all with the provenance snapshot of the run, taken before anything is written):
  UD.json, UD.qpy, UD.qasm3          the det layer U_D(eta), eta = 0.29 (16 qubits, 4 inner links, 32 CX, 8 rotations)
  step3.json (+ .qpy/.qasm3)         three-layer first-order step U_B U_D(eta) U_E at (alpha, beta, eta) = (0.37, 0.61, 0.29)
  step3_order2.json (+ ...)          three-layer second-order step U_E(a/2) U_D(e/2) U_B U_D(e/2) U_E(a/2)
  UD_outer_row_certified.json        the 12-link det row (inner + 8 outer links, 48 qubits) certified per link by
                                     results.outer_det_certify (exhaustive, bound = sum of the 12 link errors)
  observables_det.json               observables.det_observables_table: E_link, P, echo at the three triples with / without the det
                                     layer, closed spectra at lambda_D in {0, 0.2, 0.5}, sector structure, definitions
For UD and the steps: exact-angle verification by `rishon.verify.verify(..., eta=eta)` (inner block on the 1296 codes = all 38 432
physical states, Gauss sample on 273 states, rishon prune cap 0.1), logical metrics, the T(eps) table at eps in {1e-4, 1e-6, 1e-8, 1e-10}
(pygridsynth, Qiskit Clifford+T seed 12345) and every synthesised circuit re-verified with `synth_tolerances`.

--quick: schema check only (eps (1e-4,), no Qiskit Clifford+T, no order-2 step, no synthesised re-verification except UD, small
Gauss sample, observables table restricted to the nominal triple and lambda_D in {0, 0.2}); never used for committed results.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import functools
import json
import multiprocessing as mp
import pathlib
import platform
import resource
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import m5_results as M  # noqa: E402  (reuses its helpers; the file itself is untouched)
from su2plaq.circuits import rishon as C  # noqa: E402
from su2plaq.encodings.rishon import RISHON_NOMINAL, RISHON_NOMINAL_ETA, RishonEncoding  # noqa: E402
from su2plaq.metrics.cliffordt import synthesize  # noqa: E402
from su2plaq.metrics.logical import logical_metrics  # noqa: E402
from su2plaq.metrics.provenance import provenance  # noqa: E402
from su2plaq.results.store import save_result  # noqa: E402
from su2plaq.rishon import observables as O  # noqa: E402
from su2plaq.rishon import results as R  # noqa: E402
from su2plaq.rishon.verify import synth_tolerances, verify  # noqa: E402

ALPHA, BETA = RISHON_NOMINAL
ETA = RISHON_NOMINAL_ETA
EPS = M.EPS
SEEDS = {**M.SEEDS, "outer_det_row": None}
TOL_ERR = 1e-10

# circuit key -> (builder, kind, alpha, beta, order)
SPECS = {
    "UD": (lambda: C.build_UD(ETA), "UD", None, None, None),
    "step3": (lambda: C.build_step(ALPHA, BETA, 1, eta=ETA), "step", ALPHA, BETA, 1),
    "step3_order2": (lambda: C.build_step(ALPHA, BETA, 2, eta=ETA), "step", ALPHA, BETA, 2),
}
COST = {"step3": 4, "step3_order2": 4, "UD": 0}
SAMPLES = {"gauss": 256}


@functools.lru_cache(maxsize=None)
def _enc() -> RishonEncoding:
    return RishonEncoding()


def _verify(qc, key, **tol):
    _, kind, alpha, beta, order = SPECS[key]
    return R.verdict_to_dict(verify(qc, _enc(), kind, alpha, beta, order or 1, eta=ETA, gauss_sample=SAMPLES["gauss"], **tol))


def _run_task(task: tuple) -> tuple:
    """('exact', key) -> exact-angle verification; ('synth', key, eps) -> synthesise at eps, re-verify with synth_tolerances."""
    t0 = time.time()
    mode, key = task[0], task[1]
    qc = SPECS[key][0]()
    if mode == "exact":
        return task, _verify(qc, key), time.time() - t0
    eps = task[2]
    synth, info = synthesize(qc, eps)
    ver = _verify(synth, key, **synth_tolerances(info["n_rot"], eps))
    n_t = sum(1 for inst in synth.data if inst.operation.name in ("t", "tdg"))
    res = {"n_rot": info["n_rot"], "t_rot": info["t_rot"], "error_bound_sum": info["error_bound_sum"],
           "error_measured_sum": info["error_measured_sum"], "t_gates_in_synthesised_circuit": n_t, "verdict": ver}
    return task, res, time.time() - t0


def _log(msg: str) -> None:
    print(f"[m5_det_results {time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "rishon"))
    ap.add_argument("--quick", action="store_true", help="schema check only; never used for committed results")
    ap.add_argument("--only", nargs="+", choices=sorted(SPECS), help="dry-run aid: build only these circuits (never for committed results)")
    ap.add_argument("--jobs", type=int, default=None, help="worker processes for the verification tasks (default 8; 1 with --quick)")
    args = ap.parse_args(argv)
    t_start = time.time()
    grid = (1e-4,) if args.quick else EPS
    qiskit = not args.quick
    jobs = args.jobs if args.jobs is not None else (1 if args.quick else 8)
    if args.quick:
        SAMPLES.update(gauss=8)
    snap = provenance(SEEDS)
    snap["provenance_captured_at"] = snap["timestamp_utc"]
    snap["host"] = platform.node()
    snap["command"] = " ".join([pathlib.Path(sys.executable).name, *sys.argv])
    snap["quick"] = bool(args.quick)
    snap["only"] = list(args.only) if args.only else None
    snap["jobs"] = jobs
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    enc = _enc()
    physics, detail = R.physics_block(enc)
    keys = [k for k in (args.only or SPECS) if not (args.quick and k == "step3_order2")]
    circuits = {k: SPECS[k][0]() for k in keys}
    _log(f"physics block done; circuits {keys}")

    metrics = {k: M._static_metrics(circuits[k], grid, qiskit) for k in keys}
    files = {k: M._save_circuit(circuits[k], out, k) for k in keys}
    _log("static metrics and circuit files done")

    tasks = [("exact", k) for k in keys]
    tasks += [("synth", k, e) for k in keys for e in grid if not (args.quick and k != "UD")]
    tasks.sort(key=lambda t: (-COST[t[1]], t[0] != "exact", t[2:] and t[2]))
    results: dict = {}
    if jobs <= 1:
        for t in tasks:
            _, res, sec = _run_task(t)
            results[t] = (res, sec)
            _log(f"done {t} in {sec:.1f} s")
    else:
        _enc()                  # build the 38 432-state basis once before forking (copy-on-write)
        with cf.ProcessPoolExecutor(max_workers=jobs, mp_context=mp.get_context("fork")) as ex:
            futs = {ex.submit(_run_task, t): t for t in tasks}
            for f in cf.as_completed(futs):
                t, res, sec = f.result()
                results[t] = (res, sec)
                _log(f"done {t} in {sec:.1f} s ({len(results)}/{len(tasks)})")
    for k in keys:
        ver, sec = results[("exact", k)]
        for row in metrics[k]["t_table"]:
            tk = ("synth", k, row["eps"])
            if tk in results:
                row["synth"], row["synth_seconds"] = results[tk][0], results[tk][1]
                row["synth"]["t_matches_table"] = row["synth"]["t_gates_in_synthesised_circuit"] == row["t_total"]
            else:
                row["synth"] = {"skipped": True, "reason": "--quick"}
        metrics[k]["seconds"] = {"verify_exact": sec}
        metrics[k]["verification_block"] = ver

    # ---- outer det row: 48 qubits, 12 links, certified per link (not covered by the inner-block verdict: it writes the outer register)
    row_qc = C.build_UD(ETA, with_outer=True, include_outer_det=True)
    row_ver = R.outer_det_certify(row_qc, enc, ETA, tol_err=TOL_ERR)
    row_lm = logical_metrics(row_qc)
    row_files = M._save_circuit(row_qc, out, "UD_outer_row")
    _log(f"outer det row certified={row_ver['certified']} bound={row_ver['error_bound']:.3e}")

    # ---- observables with the det layer
    if args.quick:
        tab = O.det_observables_table(triples=O.DET_TRIPLES[:1], lam_d_list=(0.0, 0.2))
    else:
        tab = O.det_observables_table()
    _log("observables with det done")

    snap["wall_seconds"] = time.time() - t_start
    snap["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    snap["peak_rss_mb_largest_worker"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0
    tab["provenance"] = dict(snap)
    (out / "observables_det.json").write_text(json.dumps(R._jsonable(tab), indent=2) + "\n")
    common = {"physics": physics, "physics_detail": detail,
              "symbols": "lambda_D = det coupling, eta = lambda_D dt = angle of the det layer (prompts/204 section 2.1)"}
    for k in keys:
        _, kind, alpha, beta, order = SPECS[k]
        m = metrics[k]
        ver = m.pop("verification_block")
        extra = {**common, "seconds": m.pop("seconds")}
        params = {"eta": ETA, "order": order, **({"alpha": alpha, "beta": beta} if kind == "step" else {})}
        if k == "UD":
            extra["outer_det_row"] = {"file": "UD_outer_row_certified.json", "n_rot": row_lm["n_rot"], "cx": row_lm["cx"]}
        save_result(out / f"{k}.json", encoding="rishon", circuit_id=k, kind=kind, params=params, verification=ver, metrics=m,
                    files=files[k], seeds=SEEDS, provenance_snapshot=snap, extra=extra)
    save_result(out / "UD_outer_row_certified.json", encoding="rishon", circuit_id="UD_outer_row_certified", kind="UD",
                params={"eta": ETA}, verification=R._jsonable(row_ver),
                metrics={"logical": {kk: row_lm[kk] for kk in M.LOGICAL_KEYS}}, files=row_files, seeds=SEEDS, provenance_snapshot=snap,
                extra={"note": "det row over all 12 links (inner det layer + 8 outer links); the outer part writes the outer register "
                               "(A <-> B), so it is certified per link by outer_det_certify, not by the inner-block verdict",
                       "analogous_file": "results/rishon/UE_outer_row_certified.json"})
    return 0 if row_ver["certified"] and all(results[("exact", k)][0]["ok"] for k in keys) else 1


if __name__ == "__main__":
    raise SystemExit(main())
