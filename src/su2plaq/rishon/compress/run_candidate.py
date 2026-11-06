"""CLI: python -m su2plaq.rishon.compress.run_candidate <program.py> [--kind step] [--order 1] [--trial|--full] [--json out.json]

Evaluates one proposer program with the rishon evaluator (prompts/203 section 3.1): prints valid / invalid with the reason, the error
numbers and the cost metrics; exit code 0 iff valid (as the laptop CLI).  --trial (default): `trial_inputs` seeded inner codes,
nominal angles, sparse engine, no Gauss sample, T estimate (seconds); a trial `valid` is NOT a validity verdict.  --full: all 1296
inner codes, three angle pairs with identical skeleton, Gauss sample, pygridsynth T; this decides validity.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import su2plaq.rishon.compress  # noqa: F401  (registers the encoding)
from su2plaq.compress.spec import TaskSpec, default_spec
from su2plaq.rishon.compress.evaluate import LE, evaluate_program


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m su2plaq.rishon.compress.run_candidate")
    ap.add_argument("program")
    ap.add_argument("--kind", default="step", choices=["step", "UB", "UE"])
    ap.add_argument("--order", type=int, default=1)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--trial", action="store_true")
    g.add_argument("--full", action="store_true")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args(argv)
    spec = default_spec("rishon", a.kind)
    spec = TaskSpec(**{**spec.to_dict(), "order": a.order})
    mode = "full" if a.full else "trial"
    r = evaluate_program(pathlib.Path(a.program), spec, mode=mode)
    d = LE.result_to_dict(r)
    if a.json_out:
        pathlib.Path(a.json_out).write_text(json.dumps(d, indent=2) + "\n")
    print(f"{'valid' if r.valid else 'invalid'}: {r.reason}  [{mode}, {r.wall_s:.1f} s]  sha256 {r.program_sha256[:12]}")
    if mode == "trial":
        print("note: a trial result is NOT a validity verdict (a seeded subset of the inner codes, nominal angles, no Gauss sample); "
              "run --full to decide")
    print(f"summary: {r.summary}")
    if r.message:
        print(f"message: {r.message}")
    v = r.verdict
    if v is not None:
        print(f"op_norm_error {v.op_norm_error:.3e} (block {v.block_error:.3e}, leak {v.leak_amplitude:.3e}, pruning {v.dropped_total:.3e}), "
              f"gauss {v.gauss_residual:.3e}, engine {v.engine}, certified {v.certified}")
        if not v.ok and v.failing_inputs:
            print("worst inputs: " + ", ".join(f"{i}: {e:.3e}" if isinstance(e, float) else f"{i}: {e}" for i, e in v.failing_inputs[:5]))
    if r.verdicts_alt:
        print("alternate angles: " + ", ".join(f"ok={x.ok} err={x.op_norm_error:.2e}" for x in r.verdicts_alt) + f"; skeleton_equal={r.skeleton_equal}")
    if r.metrics:
        m = r.metrics
        print(f"metrics: CX {m['cx']}, T_fixed {m['t_fixed']}, N_rot {m['n_rot']}, T_eps {m['t_eps']}"
              f"{'' if m.get('measured') else ' (estimate)'}, depth {m['depth']}, depth_CT {m['depth_ct']}, qubits {m['qubits']}")
    for line in r.discoveries:
        print(line)
    return 0 if r.valid else 1


if __name__ == "__main__":
    sys.exit(main())
