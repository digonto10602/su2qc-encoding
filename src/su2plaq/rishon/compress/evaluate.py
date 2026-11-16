"""Rishon evaluator: the verdict function and the helpers of the rishon compression loop (prompts/203 section 2, 3.1; METHODS-rishon R10;
facade since prompts/008 step B5, D14).

The shared `su2plaq.compress.evaluate` does the work (program contract, stock build worker with the audit guard, class-identity gate
check, 62-qubit engine limit, skeleton check at the alternate angle pairs, result cache keyed by `code_hash_for("rishon")`,
`ProgramResult`); this module keeps what is rishon's own and registers it (`su2plaq.encodings.registry`, entry `rishon`):

* `verdict(qc, spec, mode, budget)`: the verdict of `su2plaq.rishon.verify.verify`, inner-block certification on the 1296 inner codes
  (sound for all 38 432 physical states because the circuit may not read the outer register, METHODS-rishon R6), the sampled Gauss
  check on 17 closed + 256 seeded physical states (full mode) and the rishon prune cap, converted by `to_verdict` to the shared
  `Verdict` (method "rishon_inner_block", `extra = {"gauss_states", "outer_bits_read", "inner_method", "rishon": True}`);
* `trial_states(spec)`: the seeded inner codes of trial mode (nominal angles, sparse engine, no Gauss sample, T estimate);
* `warm_up()`: the registry's `worker_warmup`, run in the stock build worker before the audit guard;
* `main`: alias of the stock worker (`python -m su2plaq.rishon.compress.evaluate --worker ...`).

`evaluate_circuit`, `evaluate_program`, `verify_synthesised` and `_build_in_subprocess` are the shared functions (re-exported).
"""
from __future__ import annotations

import math
import sys

import numpy as np

import su2plaq.rishon.compress  # noqa: F401  (package init: spec wrapper, hash list)
from su2plaq.compress import builder as B  # noqa: F401
from su2plaq.compress import evaluate as LE
from su2plaq.compress.evaluate import (  # noqa: F401  (re-exported: the shared functions serve the rishon loop)
    ContractError, EvalTimeout, ProgramResult, _build_in_subprocess, _gate_violations, evaluate_circuit, evaluate_program, load_program,
    skeleton)
from su2plaq.compress.baselines import verify_synthesised  # noqa: F401
from su2plaq.compress.spec import TaskSpec, get_encoding
from su2plaq.evaluate.evaluator import Verdict, synth_tolerances  # noqa: F401
from su2plaq.rishon.compress.spec import ENGINE_QUBIT_LIMIT, REASON_ENGINE_QUBIT_LIMIT, engine_qubit_message  # noqa: F401

ROOT = LE.ROOT
BUILD_TIMEOUT_S = LE.BUILD_TIMEOUT_S
_METHOD = "rishon_inner_block"


# --------------------------------------------------------------------------------------------- verdicts
def trial_states(spec: TaskSpec) -> np.ndarray:
    """The 64 seeded code positions (rng default_rng(spec.trial_seed).choice(1296, 64, replace=False), sorted)."""
    dim = len(get_encoding(spec.encoding).inner_codes())
    rng = np.random.default_rng(spec.trial_seed)
    return np.sort(rng.choice(dim, size=min(spec.trial_inputs, dim), replace=False))


def to_verdict(rv) -> Verdict:
    """Laptop `Verdict` with the fields of a `rishon.verify.RishonVerdict` (method 'rishon_inner_block')."""
    iv = rv.inner_verdict
    span = iv.span_leak if iv is not None else float("nan")       # prompts/008 §5: copied from the inner verdict (0.0 on the inner view)
    # an early verdict (bad_layout, unsimulable, ...) judged nothing: total_error stays at the evaluator's default `inf`, never NaN
    total = rv.op_norm_error + span if math.isfinite(span) and math.isfinite(rv.op_norm_error) else float("inf")
    return Verdict(
        ok=rv.ok, reason=rv.reason, op_norm_error=rv.op_norm_error, max_leak=rv.max_leak, dirty_ancilla=rv.dirty_ancilla,
        phase=rv.phase, outer_bits_read=rv.outer_bits_read, n_blocks=iv.n_blocks if iv is not None else 0,
        gauss_residual=rv.gauss_residual, method=_METHOD, engine=rv.engine, seconds=rv.seconds,
        failing_inputs=list(rv.failing_inputs), n_inputs=iv.n_inputs if iv is not None else 0, dropped_total=rv.dropped_total,
        engine_accuracy=iv.engine_accuracy if iv is not None else 0.0, certified=rv.certified, tolerances=dict(rv.tolerances),
        block_error=rv.block_error, leak_amplitude=rv.leak_amplitude, span_leak=span,
        total_error=total,
        extra={"gauss_states": rv.gauss_states, "outer_bits_read": rv.outer_bits_read, "inner_method": rv.extra.get("inner_method"),
               "rishon": True})


def verdict(qc, spec: TaskSpec, mode: str, budget) -> Verdict:
    """Registry hook `verdict(qc, spec, mode, budget)`: the rishon inner-block verdict (`budget` seconds of wall time, None = no limit);
    trial mode = `trial_states(spec)`, sparse engine, no Gauss sample."""
    from su2plaq.compress import oracle
    from su2plaq.rishon import verify as RV

    enc = get_encoding(spec.encoding).encoding
    V = oracle.target(spec)
    trial = mode == "trial"
    with LE._time_limit(budget):
        rv = RV.verify(qc, enc, spec.kind, spec.alpha, spec.beta, spec.order, tol_err=spec.tol_err, tol_gauss=spec.tol_gauss,
                       gauss=not trial, engine="sparse" if trial else "auto", cap=spec.support_cap, target=V,
                       states=trial_states(spec) if trial else None)
    return to_verdict(rv)


_one_verdict = verdict          # the name the module used before the registry


# --------------------------------------------------------------------------------------------- worker
def warm_up() -> None:
    """Registry hook `worker_warmup`: warm the operator caches in the build worker BEFORE the audit guard (so the guard never sees their
    first import or computation)."""
    view = get_encoding("rishon")
    view.bright_pairs()
    view.target("step", 0.37, 0.61)
    view.closed_codes()
    view.dark_codes()


def main(argv=None) -> int:
    """--worker <program> <specs.json> <out.qpy> <meta.json>: alias of the stock build worker (`su2plaq.compress.evaluate._worker`, which
    runs the registry's `worker_warmup` before the audit guard)."""
    argv = sys.argv[1:] if argv is None else list(argv)
    if len(argv) == 5 and argv[0] == "--worker":
        LE._worker(*argv[1:])
        return 0
    raise SystemExit("usage: python -m su2plaq.rishon.compress.evaluate --worker <program> <specs.json> <out.qpy> <meta.json>")


if __name__ == "__main__":
    raise SystemExit(main())
