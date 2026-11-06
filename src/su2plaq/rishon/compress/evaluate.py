"""Rishon evaluator: trial / full mode, worker, cache, synthesised re-verification (prompts/203 section 2, 3.1; METHODS-rishon R10).

Same protocol as the laptop `su2plaq.compress.evaluate` (program contract, subprocess build with the audit guard, class-identity
gate check, skeleton check at the alternate angle pairs, result cache, `ProgramResult`), with three differences:

* the verdict comes from `su2plaq.rishon.verify.verify`: inner-block certification on the 1296 inner codes (sound for all 38 432
  physical states because the circuit may not read the outer register, METHODS-rishon R6), the sampled Gauss check on
  17 closed + 256 seeded physical states, and the laptop prune cap; it is converted to the laptop `Verdict` (method
  "rishon_inner_block", `extra = {"gauss_states", "outer_bits_read", "inner_method", "rishon": True}`) so that archive / report / cache
  work unchanged;
* trial mode = the `trial_inputs` seeded inner codes at the nominal angles, sparse engine, no Gauss sample, T estimate;
* the build worker is `python -m su2plaq.rishon.compress.evaluate --worker ...` (it registers the encoding, then runs the laptop
  worker) and the result cache is keyed by `su2plaq.rishon.compress.code_hash()`.

The sandbox of the laptop module (import whitelist, forbidden names, audit hook) is used unchanged; nothing here widens it.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

import numpy as np

import su2plaq.rishon.compress  # noqa: F401  (registers the encoding)
from su2plaq.compress import builder as B
from su2plaq.compress import evaluate as LE
from su2plaq.compress.evaluate import ContractError, EvalTimeout, ProgramResult, load_program, skeleton  # noqa: F401
from su2plaq.compress.spec import TaskSpec, get_encoding
from su2plaq.evaluate.evaluator import Verdict, synth_tolerances

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
    return Verdict(
        ok=rv.ok, reason=rv.reason, op_norm_error=rv.op_norm_error, max_leak=rv.max_leak, dirty_ancilla=rv.dirty_ancilla,
        phase=rv.phase, outer_bits_read=rv.outer_bits_read, n_blocks=iv.n_blocks if iv is not None else 0,
        gauss_residual=rv.gauss_residual, method=_METHOD, engine=rv.engine, seconds=rv.seconds,
        failing_inputs=list(rv.failing_inputs), n_inputs=iv.n_inputs if iv is not None else 0, dropped_total=rv.dropped_total,
        engine_accuracy=iv.engine_accuracy if iv is not None else 0.0, certified=rv.certified, tolerances=dict(rv.tolerances),
        block_error=rv.block_error, leak_amplitude=rv.leak_amplitude,
        extra={"gauss_states": rv.gauss_states, "outer_bits_read": rv.outer_bits_read, "inner_method": rv.extra.get("inner_method"),
               "rishon": True})


def _one_verdict(qc, spec: TaskSpec, mode: str, budget: float) -> Verdict:
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


# --------------------------------------------------------------------------------------------- circuits
def evaluate_circuit(qc, spec: TaskSpec, mode: str = "full", alt_circuits=None, *, program_sha256: str = "", summary: str = "",
                     discoveries=(), t0: float | None = None) -> ProgramResult:
    """Same checks as the laptop `evaluate_circuit`, with the rishon verdict.  `alt_circuits`: the circuits built at spec.alt_angles
    (full mode); their skeleton must equal the nominal one and each must verify at its own angles."""
    if mode not in ("trial", "full"):
        raise ValueError(f"mode must be 'trial' or 'full', got {mode!r}")
    t0 = time.time() if t0 is None else t0
    base = dict(program_sha256=program_sha256, summary=summary, discoveries=list(discoveries), mode=mode,
                spec_sha256=spec.sha256(), seeds=LE._seeds(spec))

    def result(valid, reason, verdict=None, alts=(), skel=True, met=None, message=""):
        return ProgramResult(valid, reason, verdict, list(alts), skel, met, wall_s=time.time() - t0, message=message, **base)

    violations = LE._gate_violations(qc)
    if qc.num_qubits > spec.peak_qubit_cap():
        return result(False, "max_qubits", message=f"{qc.num_qubits} qubits > cap {spec.peak_qubit_cap()}")
    try:
        verdict = _one_verdict(qc, spec, mode, spec.eval_budget_s)
    except EvalTimeout:
        return result(False, "eval_budget", message=f"nominal evaluation exceeded {spec.eval_budget_s:g} s")
    valid, reason = LE._classify(verdict, violations)
    alts, skel_ok = [], True
    if valid and mode == "full" and alt_circuits:
        sk0 = skeleton(qc)
        for qa in alt_circuits:
            if skeleton(qa) != sk0:
                skel_ok = False
        if not skel_ok:
            valid, reason = False, "skeleton"
        else:
            for (a, b), qa in zip(spec.alt_angles, alt_circuits):
                try:
                    va = _one_verdict(qa, spec.with_angles(a, b), "full", min(120.0, spec.eval_budget_s))
                except EvalTimeout:
                    valid, reason = False, "eval_budget"
                    break
                alts.append(va)
                ok_a, why = LE._classify(va, LE._gate_violations(qa))
                if not ok_a:
                    valid, reason = False, f"alt_angles:{why}"
    met = None
    try:
        from su2plaq.compress.metrics import metrics

        met = metrics(qc, spec, measured=(mode == "full" and valid))
    except ValueError:
        met = None   # a circuit the lowering rejects (unitary, wide mcx, ...) has no metrics
    return result(valid, reason, verdict, alts, skel_ok, met)


def verify_synthesised(qc, spec: TaskSpec, eps: float | None = None) -> dict:
    """Synthesise `qc` with pygridsynth at eps (default spec.eps) and re-verify it against the spec's target with
    `synth_tolerances(n_rot, eps)` on both the error and the Gauss residual (rishon inner-block verdict, sparse engine, aer_mps
    fallback).  ok = verdict ok AND certified."""
    from su2plaq.compress import oracle
    from su2plaq.compress.synth import gridsynth_word
    from su2plaq.metrics.cliffordt import synthesize
    from su2plaq.rishon import verify as RV

    eps = spec.eps if eps is None else eps
    synth, info = synthesize(qc, eps, word_fn=gridsynth_word)
    tol = synth_tolerances(info["n_rot"], eps)
    rv = RV.verify(synth, get_encoding(spec.encoding).encoding, spec.kind, spec.alpha, spec.beta, spec.order, **tol, gauss=True,
                   engine="auto", cap=spec.support_cap, target=oracle.target(spec))
    v = to_verdict(rv)
    t_total = sum(1 for i in synth.data if i.operation.name in ("t", "tdg"))
    return {"ok": bool(v.ok and v.certified), "verdict": v, "eps": eps, "n_rot": info["n_rot"], "tolerances": tol,
            "t_total": t_total, "error_bound_sum": info["error_bound_sum"], "error_measured_sum": info["error_measured_sum"]}


# --------------------------------------------------------------------------------------------- programs (subprocess build)
def _build_in_subprocess(source: bytes, specs: list[TaskSpec], timeout: float):
    """As the laptop `_build_in_subprocess`, but the worker is THIS module (it registers the encoding first).
    -> (circuits, discoveries) or raises ContractError / RuntimeError / subprocess.TimeoutExpired."""
    from qiskit import QuantumCircuit, qpy

    with tempfile.TemporaryDirectory(prefix="su2plaq-rishon-build-") as td:
        td = pathlib.Path(td)
        prog = td / "program.py"
        prog.write_bytes(source)
        spec_json = td / "specs.json"
        spec_json.write_text(json.dumps([s.to_dict() for s in specs]))
        out = td / "out.qpy"
        meta = td / "meta.json"
        work = td / "cwd"
        work.mkdir()
        env = {**os.environ, "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(work),
               "PYTHONPATH": str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")}
        p = subprocess.run([sys.executable, "-m", "su2plaq.rishon.compress.evaluate", "--worker", str(prog), str(spec_json), str(out),
                            str(meta)], capture_output=True, text=True, timeout=timeout, env=env, cwd=str(work))
        if not meta.exists():
            raise RuntimeError(f"build worker failed (exit {p.returncode}): {p.stderr.strip()[-800:]}")
        try:
            m = json.loads(meta.read_text())
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"build worker wrote an unreadable meta file: {exc}") from exc
        if not isinstance(m, dict):
            raise RuntimeError("build worker wrote a malformed meta file")
        if "error" in m:
            raise (ContractError if m.get("kind") == "contract" else RuntimeError)(str(m["error"])[:2000])
        if not out.exists():
            raise RuntimeError(f"build worker exited (code {p.returncode}) without writing the circuits")
        try:
            with open(out, "rb") as fh:
                circuits = qpy.load(fh)
        except Exception as exc:   # noqa: BLE001 - any QPY failure of a worker-written file is a build failure
            raise RuntimeError(f"build worker wrote an unreadable circuit file: {type(exc).__name__}: {exc}") from exc
        if len(circuits) != len(specs) or not all(isinstance(c, QuantumCircuit) for c in circuits):
            raise RuntimeError("build worker returned the wrong number of circuits")
        disc = m.get("discoveries")
        disc = [[str(x)[:500] for x in lines][:B.MAX_DISCOVERIES] if isinstance(lines, list) else []
                for lines in (disc if isinstance(disc, list) else [])]
        disc += [[] for _ in range(len(specs) - len(disc))]
        return circuits, disc


def _evaluate_program_bytes(source: bytes, sha: str, spec: TaskSpec, mode: str) -> ProgramResult:
    t0 = time.time()
    summary, discoveries = "", []

    def fail(reason, message=""):
        return ProgramResult(False, reason, None, [], True, None, sha, time.time() - t0, discoveries, summary, mode, message,
                             spec_sha256=spec.sha256(), seeds=LE._seeds(spec))

    try:
        header = LE._scan_source(source.decode())
    except (ContractError, UnicodeDecodeError) as exc:
        return fail("contract", str(exc))
    summary, discoveries = header["summary"], list(header["discoveries"])
    specs = [spec] + ([spec.with_angles(a, b) for a, b in spec.alt_angles] if mode == "full" else [])
    try:
        circuits, disc = _build_in_subprocess(source, specs, BUILD_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return fail("build_timeout", f"build exceeded {BUILD_TIMEOUT_S:g} s")
    except ContractError as exc:
        return fail("contract", str(exc))
    except RuntimeError as exc:
        return fail("build_error", str(exc))
    for line in disc[0]:
        if line not in discoveries and len(discoveries) < B.MAX_DISCOVERIES:
            discoveries.append(line)
    return evaluate_circuit(circuits[0], spec, mode, alt_circuits=circuits[1:], program_sha256=sha, summary=summary,
                            discoveries=discoveries, t0=t0)


def evaluate_program(path, spec: TaskSpec, mode: str = "full", *, cache: bool = False, root=None) -> ProgramResult:
    """`cache=True` (full mode only): a result for the same (rishon code hash, program sha256, spec sha256) under
    <root>/compress/cache/<code_hash>/ is returned instead of re-evaluating, and a fresh full result is stored there (the laptop
    cache blob format; any edit of a file in RISHON_EVALUATOR_FILES changes the hash, so a stale entry can never be hit)."""
    from su2plaq.compress import provenance as P
    from su2plaq.rishon.compress import code_hash

    path = pathlib.Path(path)
    source = path.read_bytes()
    sha = hashlib.sha256(source).hexdigest()
    cpath = None
    if cache and mode == "full":
        ev_sha = code_hash()
        cpath = P.cache_path(ev_sha, sha, spec.sha256(), root=root)
        if cpath.exists():
            cached = LE._read_cache(cpath, ev_sha, sha, spec.sha256())
            if cached is not None:
                return cached          # otherwise: unreadable / tampered / foreign entry -> re-evaluate and overwrite
    r = _evaluate_program_bytes(source, sha, spec, mode)
    if cpath is not None and r.reason not in ("eval_budget", "build_timeout"):
        try:
            cpath.parent.mkdir(parents=True, exist_ok=True)
            tmp = cpath.with_suffix(".tmp")
            tmp.write_text(LE._cache_blob(LE.result_to_dict(r), ev_sha, sha, spec.sha256()))
            tmp.replace(cpath)
        except OSError:
            pass
    return r


# --------------------------------------------------------------------------------------------- worker entry point
def main(argv=None) -> int:
    """--worker <program> <specs.json> <out.qpy> <meta.json>: register the rishon encoding, warm the operator caches (so that the
    audit guard of the laptop worker never sees their first import / computation), then run the laptop worker."""
    argv = sys.argv[1:] if argv is None else list(argv)
    if len(argv) == 5 and argv[0] == "--worker":
        view = get_encoding("rishon")
        view.bright_pairs()
        view.target("step", 0.37, 0.61)
        view.closed_codes()
        view.dark_codes()
        LE._worker(*argv[1:])
        return 0
    raise SystemExit("usage: python -m su2plaq.rishon.compress.evaluate --worker <program> <specs.json> <out.qpy> <meta.json>")


if __name__ == "__main__":
    raise SystemExit(main())
