"""M7 step 7.10: write results/lsh/{UE,UB,step}.json (prompts/400 §5; schema prompts/002 §2.11).
Deterministic; every number is computed here, none typed in.

    PYTHONPATH=src python scripts/m7_results.py [--out results/lsh] [--quick]

For U_E, U_B and the step (order 1) at (alpha, beta) = (0.37, 0.61) on the d-only LSH circuits: the exact-angle circuit is
verified (sparse engine), its logical metrics and the T(eps) table at eps in {1e-4, 1e-6, 1e-8, 1e-10} are computed, and every
synthesised circuit is re-verified with synth_tolerances.  Extras: the physics block (all files); U_E with the outer electric row;
the order-2 step; for U_B the comparison rows (spin-network circuits wrapped by the transcoder, the transcoder alone, the
spin-network general circuit).  --quick shrinks the eps grid and drops the comparison rows (schema check only; never used for
the committed results).  One provenance snapshot (commit, git_dirty, versions, platform, host, command, seeds, wall time,
peak RSS) is taken before anything is written and shared by all files.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json  # noqa: F401
import pathlib
import platform
import resource
import sys
import time

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.circuits import lsh as C
from su2plaq.circuits import spinnet as CS
from su2plaq.encodings.lsh import LSH
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
from su2plaq.exact.compare import gauge_align, spectra_match
from su2plaq.exact.operators import h_electric_inner, h_magnetic_phys
from su2plaq.exact.spinnet import K_inner, h_electric_6j, h_magnetic_phys_6j, inner_labels, labels as route_b_labels
from su2plaq.lsh import operators as O
from su2plaq.lsh import walk as W
from su2plaq.metrics.cliffordt import synthesize, t_table
from su2plaq.metrics.logical import logical_metrics
from su2plaq.metrics.provenance import provenance
from su2plaq.results.store import save_result, verdict_to_dict

ALPHA, BETA = 0.37, 0.61
EPS = (1e-4, 1e-6, 1e-8, 1e-10)
EPS_CMP = 1e-6
G2 = (0.5, 1.0, 2.0)
SEEDS = {"transpiler_logical": 20261104, "trial_subset": 0}
ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGICAL_KEYS = ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")
WRAPPED = ("general7", "pairs9", "flags4", "flags5", "flags6")


def _verdict_block(v) -> dict:
    d = verdict_to_dict(v)
    if not d.get("failing_inputs"):
        d.pop("failing_inputs", None)
    return d


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
    except qasm3.QASM3ExporterError as exc:  # export limitation of Qiskit, recorded not hidden
        files["qasm3"] = None
        files["qasm3_error"] = f"{type(exc).__name__}: {exc}"
    return files


def _unevaluable(v) -> dict:
    return {"evaluable": False, "reason": v.reason,
            "explanation": "not evaluable by this evaluator: the Clifford+T words of the synthesised rotations put Hadamards on "
                           "the outer-register qubits the rotation acts on, but the evaluator requires every gate to be diagonal "
                           "on the outer qubits (they are controls). The exact-angle circuit (diagonal p gates) is verified; the "
                           "T cost of the outer row is reported from the T table."}


def _logical(qc) -> dict:
    lm = logical_metrics(qc)
    return {k: lm[k] for k in LOGICAL_KEYS}


def _metrics_block(qc, enc, V, eps_grid) -> dict:
    """logical metrics, macro counts and the T(eps) table; each row carries the re-verification of its synthesised circuit
    (rows whose synthesised circuit writes the outer register carry an `evaluable: False` record instead of a verdict)."""
    lm = logical_metrics(qc)
    rows = t_table(qc, eps_grid, qiskit=False)
    for row in rows:
        eps = row["eps"]
        synth, info = synthesize(qc, eps)
        v = evaluate(synth, enc, V, **synth_tolerances(info["n_rot"], eps))
        row["synth"] = {"n_rot": info["n_rot"], "t_rot": info["t_rot"], "error_bound_sum": info["error_bound_sum"],
                        "error_measured_sum": info["error_measured_sum"],
                        "verdict": _unevaluable(v) if v.reason == "writes_outer" else _verdict_block(v)}
    return {"logical": {k: lm[k] for k in LOGICAL_KEYS}, "gates_lowered": lm["gates"], "t_table": rows,
            "macro_counts": dict(qc.count_ops())}


def _entry(qc, enc, V, out, name, eps_grid) -> dict:
    t0 = time.time()
    v = evaluate(qc, enc, V)
    return {"verification": _verdict_block(v), "metrics": _metrics_block(qc, enc, V, eps_grid),
            "files": _save_circuit(qc, out, name), "seconds": time.time() - t0}


def _physics(enc) -> dict:
    """Model numbers of prompts/400 §5, each computed here from the loop-number rules and the three routes."""
    inner = [int(c) for c in O.inner_codes()]
    phys = [int(c) for c in O.physical_codes()]
    table = W.coupling_table(enc)
    bright = [c for c in inner if abs(table[c]) > 1e-12]
    pair_vals: dict = {}
    for c in bright:
        pair_vals.setdefault(round(table[c], 12), set()).add(frozenset((c, W.partner_table(enc)[c])))
    # raw register without the flux cap: 3-bit sites, AGL only
    flux = [O.site_flux(s) for s in range(8)]
    n_by_nv = [sum(1 for s in range(8) if flux[s][2] == v) for v in range(3)]
    raw_states = 0
    for ss in itertools.product(range(8), repeat=4):
        fl = [flux[s] for s in ss]
        if all(fl[c][1] == fl[(c + 1) % 4][0] for c in range(4)):
            raw_states += int(np.prod([n_by_nv[f[2]] for f in fl]))
    # data-valid, outer-site-valid codes that break the AGL on a virtual link
    pset = set(phys)
    outer_sites = [sum(s << (3 * i) for i, s in enumerate(ss)) for ss in itertools.product(O.VALID_SITE, repeat=4)]
    n_viol = sum(1 for c in inner for o in outer_sites if (c | (o << 12)) not in pset)
    # spectra of (g^2/2) H_E + H_B / g^2 against route A and route B (433 states, label order)
    labs = route_b_labels(jmax=0.5)
    full = [O.code_of_label(lab) for lab in labs]
    HE, HB = O.h_electric_lsh(full), O.h_magnetic_lsh(full)
    HA, _leak = h_magnetic_phys(enc.basis)
    HEA = h_electric_inner(enc.basis)
    HB_B, HE_B = h_magnetic_phys_6j(labs), h_electric_6j(labs)
    spec_A = {str(g): spectra_match(HE, HB, HEA, HA, g2_list=(g,)) for g in G2}
    spec_B = {str(g): spectra_match(HE, HB, HE_B, HB_B, g2_list=(g,)) for g in G2}
    il = inner_labels(jmax=0.5)
    il_codes = [O.inner_code_of(j, J) for j, J in il]
    perm = [il_codes.index(c) for c in inner]
    K6 = K_inner(jmax=0.5)[np.ix_(perm, perm)]
    D, res = gauge_align(HA, HB)
    return {"n_physical_states": len(phys), "n_inner_codes": len(inner), "n_bright_codes": len(bright),
            "n_dark_codes": len(inner) - len(bright), "n_bright_pairs": len(bright) // 2,
            "n_outer_site_patterns": len({c >> 12 for c in phys}), "n_raw_agl_states": raw_states,
            "n_raw_inner_codes": sum(1 for ss in itertools.product(range(8), repeat=4)
                                     if all(flux[ss[c]][1] == flux[ss[(c + 1) % 4]][0] for c in range(4))),
            "n_agl_violating_data_valid_codes": n_viol, "qubits_data": enc.n_data, "qubits_outer": enc.n_outer,
            "couplings": {str(k): len(v) for k, v in sorted(pair_vals.items())},
            "couplings_note": "coupling value k of K_LSH -> number of bright pairs carrying it",
            "gauge_minus_count": int((enc.gauge < 0).sum()), "gauge_residual": enc.gauge_residual,
            "gauge_align_residual_recomputed": float(res), "spectra_vs_route_A": spec_A, "spectra_vs_route_B": spec_B,
            "K_minus_K6j": float(np.abs(O.K_lsh() - K6).max()),
            "H_B_minus_H_B_6j": float(np.abs(HB - HB_B).max())}


def _transcoder_circuit() -> QuantumCircuit:
    qc = QuantumCircuit(QuantumRegister(12, "d"), name="transcoder")
    for st in W.TRANSCODE:
        (qc.cx if st[0] == "cx" else qc.rccx)(*st[1:])
    return qc


def _comparison(enc) -> dict:
    wrapped = {}
    for name in WRAPPED:
        sn = CS.build_UB(BETA) if name == "general7" else CS.trotter_v2_circuit(name, BETA)
        qc = C.wrap_spinnet(sn)
        v = evaluate(qc, enc, enc.target("UB", None, BETA))
        wrapped[name] = {"verification": _verdict_block(v), "logical": _logical(qc), "spinnet_logical": _logical(sn),
                         "t_table_pygridsynth": t_table(qc, (EPS_CMP,), qiskit=False),
                         "spinnet_t_table_pygridsynth": t_table(sn, (EPS_CMP,), qiskit=False)}
    tr = logical_metrics(_transcoder_circuit())
    sn = CS.build_UB(BETA)
    return {"wrapped_spinnet": wrapped,
            "transcoder": {"cx": tr["cx"], "t_fixed": tr["t_fixed"], "n_rot": tr["n_rot"], "ancilla": tr["ancilla"]},
            "spinnet": {"logical": _logical(sn), "t_table_pygridsynth": t_table(sn, (EPS_CMP,), qiskit=False)},
            "eps_per_rotation": EPS_CMP,
            "note": "Like-for-like at the same per-rotation eps = 1e-6 (pygridsynth sums): the LSH register costs the spin-network "
                    "circuit plus the transcoder, +40 CX and +32 T (2 x 4 x (2 cx + 1 rccx)); beta = 0.61 for all rows."}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "lsh"))
    ap.add_argument("--quick", action="store_true", help="schema check only: eps grid (1e-4, 1e-6), no comparison rows")
    args = ap.parse_args(argv)
    t_start = time.time()
    grid = (1e-4, 1e-6) if args.quick else EPS
    snap = provenance(SEEDS)           # taken BEFORE anything is written, shared by all files of the run
    snap["provenance_captured_at"] = snap["timestamp_utc"]
    snap["host"] = platform.node()
    snap["command"] = " ".join([pathlib.Path(sys.executable).name, *sys.argv])
    snap["quick"] = bool(args.quick)
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    enc = LSH()
    physics = _physics(enc)

    e = _entry(C.build_UE(ALPHA), enc, enc.target("UE", ALPHA, None), out, "UE", grid)
    orow = _entry(C.build_UE(ALPHA, with_outer=True, include_outer_electric=True), enc,
                  enc.target("UE", ALPHA, None, include_outer_electric=True), out, "UE_outer_row", grid)
    ue_extra = {"physics": physics, "outer_electric_row": {k: orow[k] for k in ("verification", "metrics", "files")},
                "note": "outer_electric_row: the same layer with 12 extra phases on the outer-site qubits (include_outer_electric); "
                        "reads 12 outer bits, 305 blocks; not evaluable synthesised (writes_outer); bound 20 eps"}

    b = _entry(C.build_UB(BETA), enc, enc.target("UB", None, BETA), out, "UB", grid)
    ub_extra = {"physics": physics}
    if not args.quick:
        ub_extra["comparison"] = _comparison(enc)

    s1 = _entry(C.build_step(ALPHA, BETA, 1), enc, enc.target("step", ALPHA, BETA, 1), out, "step", grid)
    s2 = _entry(C.build_step(ALPHA, BETA, 2), enc, enc.target("step", ALPHA, BETA, 2), out, "step_order2", grid)
    step_extra = {"physics": physics, "order2": {"params": {"alpha": ALPHA, "beta": BETA, "order": 2},
                                                 **{k: s2[k] for k in ("verification", "metrics", "files")}}}

    snap["wall_seconds"] = time.time() - t_start
    snap["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    for name, ent, extra, params in (("UE", e, ue_extra, {"alpha": ALPHA, "beta": None, "order": 1}),
                                     ("UB", b, ub_extra, {"alpha": None, "beta": BETA, "order": 1}),
                                     ("step", s1, step_extra, {"alpha": ALPHA, "beta": BETA, "order": 1})):
        save_result(out / f"{name}.json", encoding="lsh", circuit_id=name, kind=name, params=params,
                    verification=ent["verification"], metrics=ent["metrics"], files=ent["files"], seeds=SEEDS,
                    provenance_snapshot=snap, extra=extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
