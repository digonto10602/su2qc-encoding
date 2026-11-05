"""M1 step 1.9: write results/twelve/{UE,UB,step}.json (prompts/002 §2.11).  Deterministic; every number is computed here.

    PYTHONPATH=src python scripts/m1_results.py [--out results/twelve] [--no-paulo]

For each of U_E, U_B, step (order 1) at (alpha, beta) = (0.37, 0.61): the exact-angle circuit is verified (sparse engine), its
logical metrics and the T(eps) table at eps in {1e-4, 1e-6, 1e-8, 1e-10} are computed, and every synthesised circuit is
re-verified with synth_tolerances.  Extras: U_E with the outer electric row, the order-2 step, the 3^8 dim S_o table summary,
Paulo's compiled circuit (aer_mps / auto engine) with our U_B(beta = 1) next to it.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import time

import numpy as np

from su2plaq.circuits import twelve as C
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
from su2plaq.exact import operators
from su2plaq.exact.physical import inner_span, s_o_dims
from su2plaq.metrics.cliffordt import synthesize, t_table
from su2plaq.metrics.logical import logical_metrics
from su2plaq.results.store import save_result, verdict_to_dict

ALPHA, BETA = 0.37, 0.61
EPS = (1e-4, 1e-6, 1e-8, 1e-10)
SEEDS = {"transpiler_logical": 20261104, "clifford_t_pass_manager": 12345, "trial_subset": 0}
ROOT = pathlib.Path(__file__).resolve().parents[1]


def _verdict_block(v) -> dict:
    d = verdict_to_dict(v)
    d.pop("failing_inputs", None) if not d.get("failing_inputs") else None
    return d


def _save_circuit(qc, out: pathlib.Path, name: str) -> dict:
    from qiskit import qasm3, qpy

    qpath = out / f"{name}.qpy"
    with open(qpath, "wb") as fh:
        qpy.dump(qc, fh)
    files = {"qpy": str(qpath.relative_to(ROOT)), "sha256": hashlib.sha256(qpath.read_bytes()).hexdigest()}
    try:
        apath = out / f"{name}.qasm3"
        apath.write_text(qasm3.dumps(qc))
        files["qasm3"] = str(apath.relative_to(ROOT))
    except Exception as exc:  # export limitation of Qiskit, recorded not hidden
        files["qasm3"] = None
        files["qasm3_error"] = f"{type(exc).__name__}: {exc}"
    return files


def _metrics_block(qc, enc, V) -> dict:
    """logical metrics, macro counts, and the T(eps) table; each row carries the re-verification of its synthesised circuit."""
    lm = logical_metrics(qc)
    rows = t_table(qc, EPS)
    for row in rows:
        eps = row["eps"]
        synth, info = synthesize(qc, eps)
        v = evaluate(synth, enc, V, **synth_tolerances(info["n_rot"], eps))
        row["synth"] = {"n_rot": info["n_rot"], "t_rot": info["t_rot"], "error_bound_sum": info["error_bound_sum"],
                        "error_measured_sum": info["error_measured_sum"], "verdict": _verdict_block(v)}
    logical = {k: lm[k] for k in ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")}
    return {"logical": logical, "gates_lowered": lm["gates"], "t_table": rows, "macro_counts": dict(qc.count_ops())}


def _entry(qc, enc, V, out, name, **kw):
    t0 = time.time()
    v = evaluate(qc, enc, V)
    return {"verification": _verdict_block(v), "metrics": _metrics_block(qc, enc, V),
            "files": _save_circuit(qc, out, name), "seconds": time.time() - t0, **kw}


def _physics(enc) -> dict:
    dims = s_o_dims(enc.basis)
    hist = collections.Counter(dims.values())
    return {"n_physical_states": len(enc.basis.labels), "n_outer_patterns": len(dims),
            "n_outer_patterns_with_support": sum(1 for v in dims.values() if v > 0),
            "dim_So_histogram": {str(k): hist[k] for k in sorted(hist)}, "max_dim_So": max(dims.values()),
            "closed_pattern_dim": dims[0], "inner_span_rank": int(inner_span(enc.basis).shape[1]), "n_inner_codes": 625}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "twelve"))
    ap.add_argument("--no-paulo", action="store_true")
    args = ap.parse_args(argv)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    enc = TwelveQubit()
    physics = _physics(enc)

    # ---- U_E
    qc = C.build_UE(ALPHA)
    e = _entry(qc, enc, enc.target("UE", ALPHA, None), out, "UE")
    qo = C.build_UE(ALPHA, with_outer=True, include_outer_electric=True)
    outer_row = _entry(qo, enc, operators.target(enc.basis, "UE", alpha=ALPHA, include_outer_electric=True), out, "UE_outer_row")
    save_result(out / "UE.json", encoding="twelve", circuit_id="UE", kind="UE", params={"alpha": ALPHA, "beta": None, "order": 1},
                verification=e["verification"], metrics=e["metrics"], files=e["files"], seeds=SEEDS,
                extra={"physics": physics, "outer_electric_row": {k: outer_row[k] for k in ("verification", "metrics", "files")},
                       "note": "outer_electric_row: the same step with 8 extra p(-3 alpha/4) on the outer j-qubits (include_outer_electric)"})

    # ---- U_B (+ Paulo comparison)
    qb = C.build_UB(BETA)
    b = _entry(qb, enc, enc.target("UB", None, BETA), out, "UB")
    extra = {"physics": physics}
    if not args.no_paulo:
        pc = C.paulo_circuit()
        pm = json.loads((ROOT / "refs/paulo/SU2_plaquette_jmax_half_CT_metadata.json").read_text())
        V1 = enc.target("UB", None, 1.0)
        tol = dict(tol_err=2e-5, tol_gauss=2e-5)
        t0 = time.time()
        pv = evaluate(pc, enc, V1, engine="auto", **tol)
        ops = pc.count_ops()
        ours1 = C.build_UB(1.0)
        extra["paulo_comparison"] = {
            "paulo_circuit": {"num_qubits": pc.num_qubits, "cx": ops.get("cx", 0), "t": ops.get("t", 0) + ops.get("tdg", 0),
                              "metadata_resources": pm["resources"], "verification": _verdict_block(pv), "seconds": time.time() - t0,
                              "tolerances_note": "synthesised circuit: tol_err = tol_gauss = 2e-5 (prompts/003, prompts/004)"},
            "our_UB_beta_1": {"logical": {k: logical_metrics(ours1)[k] for k in ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")},
                              "t_table_eps_1e-6": [r for r in t_table(ours1, (1e-6,))],
                              "verification": _verdict_block(evaluate(ours1, enc, V1))},
            "paulo_logical_beta_1": {"logical": {k: logical_metrics(C.paulo_logical(1.0))[k] for k in ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")}}}
    save_result(out / "UB.json", encoding="twelve", circuit_id="UB", kind="UB", params={"alpha": None, "beta": BETA, "order": 1},
                verification=b["verification"], metrics=b["metrics"], files=b["files"], seeds=SEEDS, extra=extra)

    # ---- step, order 1 (+ order 2)
    s1 = _entry(C.build_step(ALPHA, BETA, 1), enc, enc.target("step", ALPHA, BETA, 1), out, "step")
    s2 = _entry(C.build_step(ALPHA, BETA, 2), enc, enc.target("step", ALPHA, BETA, 2), out, "step_order2")
    save_result(out / "step.json", encoding="twelve", circuit_id="step", kind="step",
                params={"alpha": ALPHA, "beta": BETA, "order": 1}, verification=s1["verification"], metrics=s1["metrics"],
                files=s1["files"], seeds=SEEDS,
                extra={"physics": physics, "order2": {"params": {"alpha": ALPHA, "beta": BETA, "order": 2},
                       **{k: s2[k] for k in ("verification", "metrics", "files")}}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
