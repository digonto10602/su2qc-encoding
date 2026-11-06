"""M5 step 5.10: write results/rishon/*.json (+ .qpy/.qasm3) (prompts/200 §2.8, §3 row 5.10, §8; schema prompts/002 §2.11).
Deterministic; every number is computed here or in su2plaq.rishon.results, none typed in.

    PYTHONPATH=src taskset -c 10-19 python scripts/m5_results.py [--out results/rishon] [--quick]

Files: UE.json, UB.json, step.json (order 1), step_order2.json, UE_outer_row.json (the 48-qubit U_E with the outer electric row;
it writes and restores outer qubits, so it is checked with `results.outer_electric_check`, not with `verify`),
observables.json (shared observables vs Kogut-Susskind: three angle pairs, n = 1, 2; closed spectra; definitions),
register_rows.json (48-qubit JW register, 36-qubit codeword variant as a size row, touched qubits).

For U_E, U_B and the step at (alpha, beta) = (0.37, 0.61): the exact-angle circuit is verified by `rishon.verify.verify` (inner
block on the 1296 codes = all 38 432 states, plus the sampled Gauss check on 273 states), its logical metrics (depth = depth of
the LOWERED circuit; the macro depth of the circuit as built is recorded separately and labelled) and the T(eps) table at
eps in {1e-4, 1e-6, 1e-8, 1e-10} (pygridsynth sums, Qiskit Clifford+T seed 12345, estimate 3 log2(1/eps)) are computed, and
every synthesised circuit is re-verified through `verify` with `synth_tolerances`.

--quick: schema check for unit tests only (eps grid (1e-4,), no Qiskit Clifford+T, no order-2 step, small Gauss sample,
small outer sample; never used for committed results).  The provenance snapshot (commit, dirty flag, versions, platform, host,
command, seeds, wall time, peak RSS) is taken before anything is written and shared by all files of the run.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import functools
import hashlib
import json
import multiprocessing as mp
import pathlib
import platform
import resource
import sys
import time

from su2plaq.circuits import rishon as C
from su2plaq.encodings.rishon import RISHON_NOMINAL, RishonEncoding
from su2plaq.metrics.cliffordt import synthesize, t_table
from su2plaq.metrics.logical import logical_metrics
from su2plaq.metrics.provenance import provenance
from su2plaq.results.store import save_result
from su2plaq.rishon import observables as O
from su2plaq.rishon import results as R
from su2plaq.rishon.verify import synth_tolerances, verify

ALPHA, BETA = RISHON_NOMINAL
EPS = (1e-4, 1e-6, 1e-8, 1e-10)
CT_SEED = 12345
SEEDS = {"transpiler_logical": 20261104, "clifford_t_pass_manager": CT_SEED, "gauss_sample": 20261104,
         "outer_row_sample": 20261104, "trial_subset": 0}
ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGICAL_KEYS = ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")
ANGLES = ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00))
MACRO_LABEL = ("depth of the circuit as built (macro gates such as rccx/mcx/crx counted as one layer each); the headline "
               "`logical.depth` is the depth of the level-0 lowered circuit (logical_metrics)")


def _rel(p: pathlib.Path) -> str:
    p = p.resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _save_circuit(qc, out: pathlib.Path, name: str) -> dict:
    from qiskit import qasm3, qpy

    qpath = out / f"{name}.qpy"
    with open(qpath, "wb") as fh:
        qpy.dump(qc, fh)
    files = {"qpy": _rel(qpath), "sha256": hashlib.sha256(qpath.read_bytes()).hexdigest()}
    try:
        apath = out / f"{name}.qasm3"
        apath.write_text(qasm3.dumps(qc))
        files["qasm3"] = _rel(apath)
    except qasm3.QASM3ExporterError as exc:   # export limitation of Qiskit, recorded not hidden
        files["qasm3"] = None
        files["qasm3_error"] = f"{type(exc).__name__}: {exc}"
    return files


# circuit key -> (builder, kind, alpha, beta, order, outer_row)
SPECS = {
    "UE": (lambda: C.build_UE(ALPHA), "UE", ALPHA, None, 1, False),
    "UE_outer_row": (lambda: C.build_UE(ALPHA, with_outer=True, include_outer_electric=True), "UE", ALPHA, None, 1, True),
    "UB": (lambda: C.build_UB(BETA), "UB", None, BETA, 1, False),
    "step": (lambda: C.build_step(ALPHA, BETA, 1), "step", ALPHA, BETA, 1, False),
    "step_order2": (lambda: C.build_step(ALPHA, BETA, 2), "step", ALPHA, BETA, 2, False),
}
COST = {"UB": 4, "step": 4, "step_order2": 4, "UE_outer_row": 1, "UE": 0}     # scheduling order only (largest first)
SAMPLES = {"gauss": 256, "outer": 4000}                                       # --quick shrinks them (set in main, inherited by fork)


@functools.lru_cache(maxsize=None)
def _enc() -> RishonEncoding:
    return RishonEncoding()


def _outer_block(chk: dict, tol: dict) -> dict:
    return {"method": "outer_electric_check", "sampled": True, "certified": False, "ok": chk["max_error"] <= tol["tol_err"],
            "tolerances": tol, **R._jsonable(chk)}


def _run_task(task: tuple) -> tuple:
    """Worker: ('exact', key) -> exact-angle verification; ('synth', key, eps) -> synthesise at eps and re-verify with
    synth_tolerances.  Returns (task, result dict, seconds)."""
    t0 = time.time()
    mode, key = task[0], task[1]
    build, kind, alpha, beta, order, outer_row = SPECS[key]
    qc, enc = build(), _enc()
    if mode == "exact":
        if outer_row:
            res = _outer_block(R.outer_electric_check(qc, enc, alpha, n_codes=SAMPLES["outer"]), {"tol_err": 1e-10})
        else:
            res = R.verdict_to_dict(verify(qc, enc, kind, alpha if kind != "UB" else None, beta if kind != "UE" else None,
                                           order, gauss_sample=SAMPLES["gauss"]))
        return task, res, time.time() - t0
    eps = task[2]
    synth, info = synthesize(qc, eps)
    tol = synth_tolerances(info["n_rot"], eps)
    if outer_row:
        ver = _outer_block(R.outer_electric_check(synth, enc, alpha, n_codes=SAMPLES["outer"]), tol)
    else:
        ver = R.verdict_to_dict(verify(synth, enc, kind, alpha if kind != "UB" else None, beta if kind != "UE" else None,
                                       order, gauss_sample=SAMPLES["gauss"], **tol))
    n_t = sum(1 for inst in synth.data if inst.operation.name in ("t", "tdg"))
    res = {"n_rot": info["n_rot"], "t_rot": info["t_rot"], "error_bound_sum": info["error_bound_sum"],
           "error_measured_sum": info["error_measured_sum"], "t_gates_in_synthesised_circuit": n_t, "verdict": ver}
    return task, res, time.time() - t0


def _static_metrics(qc, grid, qiskit) -> dict:
    """logical metrics (depth = depth of the lowered circuit), macro depth/counts, T(eps) table without the synth records."""
    lm = logical_metrics(qc)
    return {"logical": {k: lm[k] for k in LOGICAL_KEYS}, "gates_lowered": lm["gates"], "t_table": t_table(qc, grid, qiskit=qiskit),
            "macro": {"depth": qc.depth(), "depth_label": MACRO_LABEL, "size": qc.size()}, "macro_counts": dict(qc.count_ops())}


def _log(msg: str) -> None:
    print(f"[m5_results {time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "rishon"))
    ap.add_argument("--quick", action="store_true",
                    help="schema check for unit tests: eps (1e-4,), no Qiskit CT, no order-2 step, small samples, synthesised "
                         "re-verification only for U_E and the outer row")
    ap.add_argument("--jobs", type=int, default=None, help="worker processes for the verification tasks (default 8; 1 with --quick)")
    args = ap.parse_args(argv)
    t_start = time.time()
    grid = (1e-4,) if args.quick else EPS
    qiskit = not args.quick
    jobs = args.jobs if args.jobs is not None else (1 if args.quick else 8)
    if args.quick:
        SAMPLES.update(gauss=8, outer=200)
    snap = provenance(SEEDS)
    snap["provenance_captured_at"] = snap["timestamp_utc"]
    snap["host"] = platform.node()
    snap["command"] = " ".join([pathlib.Path(sys.executable).name, *sys.argv])
    snap["quick"] = bool(args.quick)
    snap["jobs"] = jobs
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    enc = _enc()
    physics, detail = R.physics_block(enc)
    keys = [k for k in SPECS if not (args.quick and k == "step_order2")]
    circuits = {k: SPECS[k][0]() for k in keys}
    _log(f"physics block done; circuits {keys}")

    # ---- static metrics + T tables (main process), files
    metrics = {k: _static_metrics(circuits[k], grid, qiskit) for k in keys}
    files = {k: _save_circuit(circuits[k], out, k) for k in keys}
    _log("static metrics and circuit files done")

    # ---- verification tasks (exact + one synthesised re-verification per eps), largest first
    quick_synth = {"UE", "UE_outer_row"}
    tasks = [("exact", k) for k in keys]
    tasks += [("synth", k, e) for k in keys for e in grid if not (args.quick and k not in quick_synth)]
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
        rows = metrics[k]["t_table"]
        for row in rows:
            tk = ("synth", k, row["eps"])
            if tk in results:
                row["synth"], row["synth_seconds"] = results[tk][0], results[tk][1]
                row["synth"]["t_matches_table"] = row["synth"]["t_gates_in_synthesised_circuit"] == row["t_total"]
            else:
                row["synth"] = {"skipped": True, "reason": "--quick"}
        metrics[k]["seconds"] = {"verify_exact": sec}
        metrics[k]["verification_block"] = ver

    reg = R.register_rows(enc, {n: circuits[n] for n in ("UE", "UB", "step")})
    variants = {"jw_4_per_link": reg["rows"]["jw_4_per_link"]["qubits"],
                "codeword_3_per_link": reg["rows"]["codeword_3_per_link"]["qubits"],
                "touched": reg["rows"]["jw_4_per_link"]["touched"]}
    tab = O.observables_table(ANGLES)
    obs = R.observable_rows(tab)
    _log("observables done")

    snap["wall_seconds"] = time.time() - t_start
    snap["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    snap["peak_rss_mb_largest_worker"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0
    obs["provenance"] = dict(snap)
    (out / "observables.json").write_text(json.dumps(R._jsonable(obs), indent=2) + "\n")
    (out / "register_rows.json").write_text(json.dumps(R._jsonable({**reg, "provenance": dict(snap)}), indent=2) + "\n")
    common = {"register_variants": variants, "physics": physics, "physics_detail": detail}
    outer_note = ("U_E with the electric term of the 8 outer links (12 links in total): the outer qubits are CX targets that are "
                  "restored, so `verify` (which refuses circuits touching the outer register) is not used; verification = sampled "
                  "diagonal check against exp(-i alpha (3/4) #Q) on seeded valid 48-bit codes (not a certificate)")
    for k in keys:
        _, kind, alpha, beta, order, outer_row = SPECS[k]
        m = metrics[k]
        ver = m.pop("verification_block")
        extra = {**common, "seconds": m.pop("seconds")}
        if k == "UE":
            extra["outer_electric_row"] = {"file": "UE_outer_row.json", "n_rot": metrics["UE_outer_row"]["logical"]["n_rot"]}
        if outer_row:
            extra["note"] = outer_note
        save_result(out / f"{k}.json", encoding="rishon", circuit_id=k, kind=kind,
                    params={"alpha": alpha, "beta": beta, "order": order}, verification=ver, metrics=m, files=files[k],
                    seeds=SEEDS, provenance_snapshot=snap, extra=extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
