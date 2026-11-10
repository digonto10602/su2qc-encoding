"""M3 step 3.7: write results/spinnet/{UE,UB,step}.json (prompts/100 §2, §3 row 3.7, §5; schema prompts/002 §2.11).
Deterministic; every number is computed here, none typed in.

    PYTHONPATH=src taskset -c 0-9 python scripts/m3_results.py [--out results/spinnet] [--quick]

For U_E, U_B and the step (order 1) at (alpha, beta) = (0.37, 0.61): the exact-angle circuit is verified (sparse engine), its
logical metrics and the T(eps) table at eps in {1e-4, 1e-6, 1e-8, 1e-10} are computed, and every synthesised circuit is
re-verified with synth_tolerances.  Extras: U_E with the outer electric row; the order-2 step; the physics block; and for U_B the
like-for-like comparison {paulo15, spinnet_v2 (pairs9, flags4), ours at beta = 0.61 and 0.05} at eps = 1e-6 per rotation
(pygridsynth sums and Qiskit Clifford+T, seed 12345).  --quick shrinks the grid / drops the Qiskit pass manager and the
comparison rows (schema check only; never used for the committed results).  The provenance snapshot (commit, git_dirty,
versions, platform, host, command, seeds, wall time, peak RSS) is taken before anything is written and shared by all files.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import platform
import resource
import sys
import time

import numpy as np

from su2plaq.circuits import spinnet as C
from su2plaq.encodings.spinnet import SpinNet, align_inner_block
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
from su2plaq.evaluate.sparse_sim import encoded_block, run_batch
from su2plaq.metrics.cliffordt import ct_compile, synthesize, t_table
from su2plaq.metrics.logical import logical_metrics, lower
from su2plaq.metrics.provenance import provenance
from su2plaq.results.store import save_result, verdict_to_dict
from su2plaq.spinnet import paulo
from su2plaq.spinnet.walk import coupling_table

ALPHA, BETA = 0.37, 0.61
BETA_PAULO = paulo.FILE_ALPHA_P / 2           # Paulo Eq. 16 normalisation: beta = alpha_P / 2 (= 0.05)
EPS = (1e-4, 1e-6, 1e-8, 1e-10)
EPS_CMP = 1e-6
CT_SEED = 12345
SEEDS = {"transpiler_logical": 20261104, "clifford_t_pass_manager": CT_SEED, "trial_subset": 0}
ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGICAL_KEYS = ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")


def _verdict_block(v) -> dict:
    d = verdict_to_dict(v)
    d.pop("failing_inputs", None) if not d.get("failing_inputs") else None
    return d


def _rel(p: pathlib.Path) -> str:
    """Path relative to the repository root when inside it, else absolute."""
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


def _metrics_block(qc, enc, V, eps_grid, qiskit) -> dict:
    """logical metrics, macro counts, and the T(eps) table; each row carries the re-verification of its synthesised circuit
    (rows whose synthesised circuit writes the outer register carry an `evaluable: False` record instead of a verdict)."""
    lm = logical_metrics(qc)
    rows = t_table(qc, eps_grid, qiskit=qiskit)
    for row in rows:
        eps = row["eps"]
        synth, info = synthesize(qc, eps)
        v = evaluate(synth, enc, V, **synth_tolerances(info["n_rot"], eps))
        row["synth"] = {"n_rot": info["n_rot"], "t_rot": info["t_rot"], "error_bound_sum": info["error_bound_sum"],
                        "error_measured_sum": info["error_measured_sum"],
                        "verdict": _unevaluable(v) if v.reason == "writes_outer" else _verdict_block(v)}
    return {"logical": {k: lm[k] for k in LOGICAL_KEYS}, "gates_lowered": lm["gates"], "t_table": rows,
            "macro_counts": dict(qc.count_ops())}


def _entry(qc, enc, V, out, name, eps_grid, qiskit, **kw):
    t0 = time.time()
    v = evaluate(qc, enc, V)
    return {"verification": _verdict_block(v), "metrics": _metrics_block(qc, enc, V, eps_grid, qiskit),
            "files": _save_circuit(qc, out, name), "seconds": time.time() - t0, **kw}


def _cmp_row(qc, verdict_block, beta, out, name, label, grid, files=None) -> dict:
    """One like-for-like row: verification, logical counts, pygridsynth T at eps = 1e-6 and on the grid, Qiskit CT at 1e-6."""
    _, ct = ct_compile(lower(qc), EPS_CMP, level=3, seed=CT_SEED)
    return {"label": label, "beta": beta, "verification": verdict_block, "logical": _logical(qc),
            "t_table_pygridsynth": t_table(qc, (EPS_CMP,), qiskit=False),
            "t_table_pygridsynth_grid": t_table(qc, grid, qiskit=False),
            "qiskit_clifford_t_eps_1e-6": {"t": ct["t"], "cx": ct["cx"], "depth": ct["depth"], "qubits": ct["qubits"],
                                           "seed": CT_SEED, "optimization_level": 3},
            "files": files if files is not None else _save_circuit(qc, out, name)}


def _paulo_row(enc, out, grid) -> dict:
    """Paulo's 15-qubit file: open 433 states with the outer register present, gauge-fixed target (one -1 per bright pair)."""
    qc = C.paulo_circuit()
    codes = enc.inner_codes()
    M, leak = encoded_block(run_batch(qc, codes), codes, len(codes), code_mask=(1 << 8) - 1)
    D, res, phase = align_inner_block(M, enc.inner_target("UB", None, BETA_PAULO))
    if D is None:
        raise RuntimeError("Paulo's inner block differs from exp(-i beta K) in modulus: no gauge")
    minus = sorted(int(c) for c, d in zip(codes, D) if d.real < 0)
    qo = C.paulo_circuit(with_outer=True)
    Vg = enc.regauge(enc.target("UB", None, BETA_PAULO), D)
    v = evaluate(qo, enc, Vg, method="physical", gauss=True)
    v_raw = evaluate(qo, enc, enc.target("UB", None, BETA_PAULO), method="physical")
    row = _cmp_row(qc, _verdict_block(v), BETA_PAULO, out, "UB_paulo15", "Paulo 15-qubit file (alpha_P = 0.1)", grid)
    row.update({
        "verification_ungauged_route_b_target": _verdict_block(v_raw),
        "gauge_minus_codes": minus, "gauge_alignment": {"residual": res, "phase": [phase.real, phase.imag],
                                                        "inner_block_leak_max": float(leak.max()), "n_minus": len(minus)},
        "alpha_P": qc.metadata["alpha_P"], "source": qc.metadata["source"], "sha256": qc.metadata["sha256"],
        "gauge_note": "the 15-qubit file equals exp(-i beta K) up to the real diagonal sign gauge D with D = -1 exactly on the "
                      "bright data codes with j_l = 1/2 (gauge_minus_codes = {8..15}, left link, file q[3]), i.e. the "
                      "beta-independent centre-symmetry convention (-1)^(2 j_l) of one link's j = 1/2 states "
                      "(METHODS-spinnet section 2): the verdict above is for the target regauged with D; the ungauged "
                      "route-B target is rejected because the file is U_B(-beta) in route-B signs."})
    return row


def _physics(enc) -> dict:
    """433 / 47 / 16 / 31 / couplings / gauge / outer-pattern structure, all computed from the encoding."""
    table = coupling_table(enc)
    codes = [int(c) for c in enc.inner_codes()]
    vals = [table[c] for c in codes]
    bright = [c for c, v in zip(codes, vals) if abs(v) > 1e-12]
    pair_vals = collections.Counter(round(table[c], 12) for c in bright if c < (c ^ 0b1111))
    all_codes = [int(c) for c in enc._codes]
    pat = collections.defaultdict(list)
    for k, c in enumerate(all_codes):
        pat[c >> 8].append(k)
    hist = collections.Counter(len(v) for v in pat.values())
    V = enc.target("UB", None, BETA)
    Vi = enc.inner_target("UB", None, BETA)
    pos = enc._pos_of_k
    pattern_of = np.array([c >> 8 for c in all_codes])
    diff = pattern_of[:, None] != pattern_of[None, :]
    cross = float(np.abs(V[diff]).max()) if diff.any() else 0.0
    same = ~diff
    same_dev = float(np.abs(V[same] - Vi[np.ix_(pos, pos)][same]).max())
    return {"n_physical_states": len(enc.basis.labels), "n_inner_codes": len(codes), "n_bright_codes": len(bright),
            "n_dark_codes": len(codes) - len(bright), "n_bright_pairs": len(bright) // 2,
            "coupling_values_per_pair": {str(k): v for k, v in sorted(pair_vals.items())},
            "n_gauge_minus_433": int((enc.gauge < 0).sum()), "gauge_residual": enc.gauge_residual,
            "n_outer_patterns_with_states": len(pat), "states_per_outer_pattern_histogram": {str(k): hist[k] for k in sorted(hist)},
            "max_states_per_outer_pattern": max(hist), "closed_pattern_states": len(pat.get(0, [])),
            "target_cross_pattern_max_abs": cross, "target_same_pattern_vs_inner_block_max_dev": same_dev,
            "partner_rule": "partner = code XOR 0b1111 (corner bits unchanged)"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "spinnet"))
    ap.add_argument("--quick", action="store_true", help="schema check only: eps grid (1e-4, 1e-6), no Qiskit CT, no comparison rows")
    args = ap.parse_args(argv)
    t_start = time.time()
    grid = (1e-4, 1e-6) if args.quick else EPS
    qiskit = not args.quick
    # one provenance snapshot (commit, dirty flag, versions) taken BEFORE anything is written and shared by all files of the run
    snap = provenance(SEEDS)
    snap["provenance_captured_at"] = snap["timestamp_utc"]
    snap["host"] = platform.node()
    snap["command"] = " ".join([pathlib.Path(sys.executable).name, *sys.argv])
    snap["quick"] = bool(args.quick)
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    enc = SpinNet()
    physics = _physics(enc)

    # ---- U_E (+ outer electric row)
    e = _entry(C.build_UE(ALPHA), enc, enc.target("UE", ALPHA, None), out, "UE", grid, qiskit)
    outer_row = _entry(C.build_UE(ALPHA, with_outer=True, include_outer_electric=True), enc,
                       enc.target("UE", ALPHA, None, include_outer_electric=True), out, "UE_outer_row", grid, qiskit)
    ue_extra = {"physics": physics, "outer_electric_row": {k: outer_row[k] for k in ("verification", "metrics", "files")},
                "note": "outer_electric_row: the same step with 8 extra p(-3 alpha/4) on the outer j-qubits (include_outer_electric); "
                        "not evaluable synthesised (writes_outer); bound 12 eps"}

    # ---- U_B (+ comparison)
    b = _entry(C.build_UB(BETA), enc, enc.target("UB", None, BETA), out, "UB", grid, qiskit)
    ub_extra = {"physics": physics}
    if not args.quick:
        qb = C.build_UB(BETA)
        q05 = C.build_UB(BETA_PAULO)
        row05 = _cmp_row(q05, _verdict_block(evaluate(q05, enc, enc.target("UB", None, BETA_PAULO))), BETA_PAULO, out,
                         "UB_beta_0_05", "ours, general7 skeleton at Paulo's beta", EPS)
        row61 = _cmp_row(qb, b["verification"], BETA, out, "UB", "ours, general7 skeleton at the nominal beta", EPS, files=b["files"])
        v2 = {}
        for name in ("pairs9", "flags4"):
            q = C.trotter_v2_circuit(name, BETA)
            v2[name] = _cmp_row(q, _verdict_block(evaluate(q, enc, enc.target("UB", None, BETA))), BETA, out, f"UB_{name}",
                                f"spinnet_v2 {name} skeleton", EPS)
            v2[name]["source"] = q.metadata["source"]
        ub_extra["comparison"] = {
            "paulo15": _paulo_row(enc, out, EPS), "spinnet_v2": v2, "ours_beta_0_61": row61, "ours_beta_0_05": row05,
            "eps_per_rotation": EPS_CMP, "qiskit_seed": CT_SEED,
            "note": "Like-for-like at the same per-rotation eps = 1e-6: pygridsynth sums (plain per-rotation synthesis of each "
                    "logical circuit) and the Qiskit Clifford+T pass manager (seed 12345, level 3) on the lowered circuit. Paulo's file is "
                    "run at its own angle (beta = alpha_P / 2 = 0.05); 'ours_beta_0_05' is our circuit at that beta, 'ours_beta_0_61' at "
                    "the nominal beta; spinnet_v2 skeletons are at beta = 0.61 with angles solved from K in route-B gauge. "
                    "The accuracy budgets are n_rot * eps with each circuit's own n_rot, so T counts are not a same-accuracy comparison. "
                    "The route-A/B sign difference of Paulo's file is a basis-sign convention (gauge_minus_codes)."}

    # ---- step, order 1 (+ order 2)
    s1 = _entry(C.build_step(ALPHA, BETA, 1), enc, enc.target("step", ALPHA, BETA, 1), out, "step", grid, qiskit)
    s2 = _entry(C.build_step(ALPHA, BETA, 2), enc, enc.target("step", ALPHA, BETA, 2), out, "step_order2", grid, qiskit)
    step_extra = {"physics": physics, "order2": {"params": {"alpha": ALPHA, "beta": BETA, "order": 2},
                                                 **{k: s2[k] for k in ("verification", "metrics", "files")}}}

    snap["wall_seconds"] = time.time() - t_start
    snap["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    for name, ent, extra, params in (("UE", e, ue_extra, {"alpha": ALPHA, "beta": None, "order": 1}),
                                     ("UB", b, ub_extra, {"alpha": None, "beta": BETA, "order": 1}),
                                     ("step", s1, step_extra, {"alpha": ALPHA, "beta": BETA, "order": 1})):
        save_result(out / f"{name}.json", encoding="spinnet", circuit_id=name, kind=name, params=params,
                    verification=ent["verification"], metrics=ent["metrics"], files=ent["files"], seeds=SEEDS,
                    provenance_snapshot=snap, extra=extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
