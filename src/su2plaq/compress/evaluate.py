"""Evaluation of a candidate program or circuit for the compression loop (prompts/002 §2.10, §5; prompts/003-005).

The evaluator is `su2plaq.evaluate.evaluator.evaluate` with `gauss=True` (mandatory in the loop) and the spec's tolerances.
`evaluate_program` loads the proposer's file, builds the circuit in a SUBPROCESS (timeout; the parent never executes proposer
code), re-checks every gate of the returned circuit itself (class identity, not names; a Builder's attributes are writable)
and evaluates the circuit it received.  Modes:

  trial : `trial_inputs` seeded physical inputs, nominal angles, sparse engine, metrics from the T estimate (seconds)
  full  : all physical states, nominal + the two alternate angle pairs (identical skeleton required), pygridsynth T

An `ok` verdict that is not `certified` (aer_mps fallback at exact-angle tolerances) is `unverified` and never valid.

What is enforced about proposer code (and what is NOT):
  * the program is built from a private copy of exactly the bytes that were hashed (an edit of the original file during the
    evaluation cannot change what is built or the recorded sha256);
  * the build runs in a separate Python process, started in a fresh empty temporary directory, with a wall timeout;
  * before the program is imported the worker installs a `sys.addaudithook` that raises PermissionError for: opening any file
    for writing / creating / truncating (except the two result files the worker writes itself), os.remove / rename / mkdir /
    rmdir / chmod / chown / link / symlink / truncate / utime, shutil.*, subprocess / os.system / os.exec* / os.fork /
    os.spawn* / posix_spawn / pty, socket.*, ctypes.dlopen and urllib/http connections;
  * static scan of the source: import whitelist and no open / exec / eval / compile / __import__ names.
  This stops accidental and casual file writes, process spawns and network access from numpy, pathlib, builtins reached via
  the allowed modules, and so on.  It is NOT a security sandbox: audit hooks live inside the interpreter, so native code or an
  interpreter-level exploit can defeat them, reading files is not blocked, and CPU / memory are limited only by the timeout.
  Run untrusted programs under OS-level isolation if that matters.

TODO(2.5/2.6): the Clifford+T re-verification of a candidate (synthesise at spec.eps, evaluate with synth_tolerances, as the
spec text promises) belongs to baselines / round.py, not to this module.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field

import numpy as np

from su2plaq.compress import builder as B
from su2plaq.compress.spec import TaskSpec, get_encoding

ROOT = pathlib.Path(__file__).resolve().parents[3]
BUILD_TIMEOUT_S = 120.0
ALLOWED_IMPORTS = {"numpy", "math", "cmath", "itertools", "functools", "collections", "fractions", "typing", "dataclasses",
                   "operator", "heapq", "bisect", "qiskit", "__future__"}
ALLOWED_PROJECT_IMPORTS = {"su2plaq.compress.oracle", "su2plaq.compress.builder", "su2plaq.compress.spec"}
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}


class ContractError(ValueError):
    """The program file violates the program contract (header, imports, build)."""


@dataclass
class ProgramResult:
    valid: bool
    reason: str
    verdict: object | None
    verdicts_alt: list
    skeleton_equal: bool
    metrics: dict | None
    program_sha256: str
    wall_s: float
    discoveries: list
    summary: str
    mode: str = "full"
    message: str = ""
    spec_sha256: str = ""
    seeds: dict = field(default_factory=dict)


# --------------------------------------------------------------------------------------------- program loading
def _scan_source(source: str) -> dict:
    """Contract + static safety net (not a sandbox): header via builder.parse_program_header, imports restricted to numpy / the
    standard maths modules / qiskit / the oracle, builder and spec modules; no open / exec / eval / compile / __import__."""
    try:
        header = B.parse_program_header(source)
    except B.BuilderError as exc:
        raise ContractError(str(exc)) from exc
    tree = ast.parse(source)
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise ContractError("relative imports are not allowed")
            mod = node.module or ""
            names = [mod] + ([f"{mod}.{a.name}" for a in node.names] if mod == "su2plaq.compress" else [])
        for nm in names:
            if nm in ALLOWED_PROJECT_IMPORTS or nm == "su2plaq.compress":
                continue
            if nm.split(".")[0] not in ALLOWED_IMPORTS:
                raise ContractError(f"import of {nm!r} is not allowed (allowed: numpy, qiskit, standard maths modules and "
                                    f"{sorted(ALLOWED_PROJECT_IMPORTS)})")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise ContractError(f"use of {node.id!r} is not allowed")
    return header


def load_program(path):
    """Import a program file as a module after checking the contract (`SUMMARY:` docstring, FAMILY, PARENT, build(spec), import
    whitelist).  Executes the file: callers that do not trust it must do so in a subprocess (`evaluate_program` does)."""
    path = pathlib.Path(path)
    source = path.read_text()
    header = _scan_source(source)
    name = "su2plaq_program_" + hashlib.sha256(str(path.resolve()).encode() + source.encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(name, None)
        raise
    mod.HEADER = header
    return mod


def skeleton(qc) -> list[tuple]:
    """(gate name, qubit tuple) per instruction of the circuit as emitted (parameters ignored)."""
    return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data]


# --------------------------------------------------------------------------------------------- checks
def _gate_violations(qc) -> list[str]:
    from su2plaq.evaluate.sparse_sim import _is_barrier, is_standard_gate

    bad = []
    for inst in qc.data:
        op = inst.operation
        if _is_barrier(op):
            continue
        if inst.clbits or not is_standard_gate(op) or (op.name not in B.BASIS and op.name not in B.MACROS):
            bad.append(op.name)
    return sorted(set(bad))


class EvalTimeout(Exception):
    pass


@contextlib.contextmanager
def _time_limit(seconds: float):
    """SIGALRM wall limit (main thread, POSIX); elsewhere no limit.  Numpy calls are interrupted when they return to Python."""
    if not hasattr(signal, "setitimer") or threading.current_thread() is not threading.main_thread():
        yield
        return

    def handler(signum, frame):
        raise EvalTimeout()

    old = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, float(seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def _one_verdict(qc, spec: TaskSpec, mode: str, budget: float):
    from su2plaq.compress import oracle
    from su2plaq.evaluate.evaluator import evaluate

    enc = get_encoding(spec.encoding)
    V = oracle.target(spec)
    states = None
    if mode == "trial":
        rng = np.random.default_rng(spec.trial_seed)
        dim = V.shape[0]
        states = np.sort(rng.choice(dim, size=min(spec.trial_inputs, dim), replace=False))
    with _time_limit(budget):
        return evaluate(qc, enc, V, tol_err=spec.tol_err, tol_gauss=spec.tol_gauss, gauss=True,
                        engine="sparse" if mode == "trial" else "auto", cap=spec.support_cap, states=states)


def _classify(verdict, violations) -> tuple[bool, str]:
    if not verdict.ok:
        return False, verdict.reason
    if not verdict.certified:
        return False, "unverified"
    if violations:
        return False, "disallowed_gate"
    return True, "ok"


def _seeds(spec: TaskSpec) -> dict:
    from su2plaq.metrics.logical import SEED

    return {"trial_seed": spec.trial_seed, "transpiler_logical": SEED, "clifford_t_pass_manager": 12345, "gridsynth": 0}


def evaluate_circuit(qc, spec: TaskSpec, mode: str = "full", alt_circuits=None, *, program_sha256: str = "",
                     summary: str = "", discoveries=(), t0: float | None = None) -> ProgramResult:
    """Same checks for an already-built circuit.  `alt_circuits`: the circuits built at spec.alt_angles (full mode, from
    `evaluate_program`); their skeleton must equal the nominal one and each must verify at its own angles."""
    if mode not in ("trial", "full"):
        raise ValueError(f"mode must be 'trial' or 'full', got {mode!r}")
    t0 = time.time() if t0 is None else t0
    base = dict(program_sha256=program_sha256, summary=summary, discoveries=list(discoveries), mode=mode,
                spec_sha256=spec.sha256(), seeds=_seeds(spec))

    def result(valid, reason, verdict=None, alts=(), skel=True, met=None, message=""):
        return ProgramResult(valid, reason, verdict, list(alts), skel, met, wall_s=time.time() - t0, message=message, **base)

    violations = _gate_violations(qc)
    if qc.num_qubits > spec.peak_qubit_cap():
        return result(False, "max_qubits", message=f"{qc.num_qubits} qubits > cap {spec.peak_qubit_cap()}")
    try:
        verdict = _one_verdict(qc, spec, mode, spec.eval_budget_s)
    except EvalTimeout:
        return result(False, "eval_budget", message=f"nominal evaluation exceeded {spec.eval_budget_s:g} s")
    valid, reason = _classify(verdict, violations)
    alts, skel_ok = [], True
    if valid and mode == "full" and alt_circuits:
        sk0 = skeleton(qc)
        for (a, b), qa in zip(spec.alt_angles, alt_circuits):
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
                ok_a, why = _classify(va, _gate_violations(qa))
                if not ok_a:
                    valid, reason = False, f"alt_angles:{why}"
    met = None
    try:
        from su2plaq.compress.metrics import metrics

        met = metrics(qc, spec, measured=(mode == "full" and valid))
    except ValueError:
        met = None   # a circuit the lowering rejects (unitary, wide mcx, ...) has no metrics
    return result(valid, reason, verdict, alts, skel_ok, met)


# --------------------------------------------------------------------------------------------- programs (subprocess build)
def _build_in_subprocess(source: bytes, specs: list[TaskSpec], timeout: float):
    """Build the circuits from exactly `source` (a private copy in a temporary directory) in a worker process.
    -> (circuits, discoveries) or raises ContractError / RuntimeError / subprocess.TimeoutExpired."""
    from qiskit import qpy

    with tempfile.TemporaryDirectory(prefix="su2plaq-build-") as td:
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
        p = subprocess.run([sys.executable, "-m", "su2plaq.compress.evaluate", "--worker", str(prog), str(spec_json), str(out), str(meta)],
                           capture_output=True, text=True, timeout=timeout, env=env, cwd=str(work))
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
        # the worker's word is not trusted beyond what the parent can check: the circuit file must exist and parse, and the
        # circuits themselves (not the meta) are what gets evaluated
        if not out.exists():
            raise RuntimeError(f"build worker exited (code {p.returncode}) without writing the circuits")
        try:
            with open(out, "rb") as fh:
                circuits = qpy.load(fh)
        except Exception as exc:   # noqa: BLE001 - any QPY failure of a worker-written file is a build failure
            raise RuntimeError(f"build worker wrote an unreadable circuit file: {type(exc).__name__}: {exc}") from exc
        from qiskit import QuantumCircuit

        if len(circuits) != len(specs) or not all(isinstance(c, QuantumCircuit) for c in circuits):
            raise RuntimeError("build worker returned the wrong number of circuits")
        disc = m.get("discoveries")
        disc = [[str(x)[:500] for x in lines][:B.MAX_DISCOVERIES] if isinstance(lines, list) else []
                for lines in (disc if isinstance(disc, list) else [])]
        disc += [[] for _ in range(len(specs) - len(disc))]
        return circuits, disc


def result_from_dict(d: dict) -> ProgramResult:
    """Inverse of `result_to_dict` (used by the result cache)."""
    from su2plaq.evaluate.evaluator import Verdict

    def verdict(v):
        if v is None:
            return None
        v = dict(v)
        v["phase"] = complex(*v["phase"]) if isinstance(v.get("phase"), list) else complex(v.get("phase", 1.0))
        v["failing_inputs"] = [tuple(x) for x in v.get("failing_inputs", [])]
        keys = set(Verdict.__dataclass_fields__)
        return Verdict(**{k: x for k, x in v.items() if k in keys})

    return ProgramResult(valid=d["valid"], reason=d["reason"], verdict=verdict(d["verdict"]),
                         verdicts_alt=[verdict(v) for v in d["verdicts_alt"]], skeleton_equal=d["skeleton_equal"],
                         metrics=d["metrics"], program_sha256=d["program_sha256"], wall_s=d["wall_s"],
                         discoveries=list(d["discoveries"]), summary=d["summary"], mode=d.get("mode", "full"),
                         message=d.get("message", ""), spec_sha256=d.get("spec_sha256", ""), seeds=d.get("seeds", {}))


def evaluate_program(path, spec: TaskSpec, mode: str = "full", *, cache: bool = False, root=None) -> ProgramResult:
    """`cache=True` (full mode only): a result for the same (evaluator code hash, program sha256, spec sha256) under
    <root>/compress/cache/ is returned instead of re-evaluating, and a fresh full result is stored there (any edit of an
    evaluator source file changes the code hash, so a stale entry can never be hit)."""
    path = pathlib.Path(path)
    source = path.read_bytes()
    sha = hashlib.sha256(source).hexdigest()
    cpath = None
    if cache and mode == "full":
        from su2plaq.compress import provenance as P

        ev_sha = P.code_hash()
        cpath = P.cache_path(ev_sha, sha, spec.sha256(), root=root)
        if cpath.exists():
            cached = _read_cache(cpath, ev_sha, sha, spec.sha256())
            if cached is not None:
                return cached          # otherwise: unreadable / tampered / foreign entry -> re-evaluate and overwrite
    r = _evaluate_program_bytes(source, sha, spec, mode)
    if cpath is not None and r.reason not in ("eval_budget", "build_timeout"):
        try:
            cpath.parent.mkdir(parents=True, exist_ok=True)
            tmp = cpath.with_suffix(".tmp")
            tmp.write_text(_cache_blob(result_to_dict(r), ev_sha, sha, spec.sha256()))
            tmp.replace(cpath)
        except OSError:
            pass
    return r


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _cache_blob(payload: dict, evaluator_sha: str, program_sha: str, spec_sha: str) -> str:
    """Cache file content: {meta, payload, checksum}; checksum = sha256 of the canonical JSON of (meta, payload).  This is an
    integrity check against stale / copied / hand-edited entries, not a MAC: someone who can write the cache and knows this
    code can forge it; the archive's own rules (full mode, ok AND certified, key recomputed from the metrics) are a second line."""
    meta = {"evaluator_sha256": evaluator_sha, "program_sha256": program_sha, "spec_sha256": spec_sha}
    return json.dumps({"meta": meta, "payload": payload,
                       "checksum": hashlib.sha256(_canonical({"meta": meta, "payload": payload}).encode()).hexdigest()})


def _consistent(r: ProgramResult) -> bool:
    """A result may claim `valid` only if its own fields say so."""
    if not r.valid:
        return True
    v = r.verdict
    return (r.reason == "ok" and r.mode == "full" and v is not None and v.ok and v.certified and r.skeleton_equal
            and all(a.ok and a.certified for a in r.verdicts_alt) and bool(r.metrics))


def _read_cache(cpath: pathlib.Path, evaluator_sha: str, program_sha: str, spec_sha: str):
    """The cached ProgramResult, or None if the entry is unreadable, its checksum fails, its meta / payload identify another
    (evaluator code, program, spec), or the result contradicts itself."""
    try:
        d = json.loads(cpath.read_text())
        meta, payload = d["meta"], d["payload"]
        if d["checksum"] != hashlib.sha256(_canonical({"meta": meta, "payload": payload}).encode()).hexdigest():
            return None
        if (meta != {"evaluator_sha256": evaluator_sha, "program_sha256": program_sha, "spec_sha256": spec_sha}
                or payload.get("program_sha256") != program_sha or payload.get("spec_sha256") != spec_sha
                or payload.get("mode") != "full"):
            return None
        r = result_from_dict(payload)
        return r if _consistent(r) else None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def _evaluate_program_bytes(source: bytes, sha: str, spec: TaskSpec, mode: str) -> ProgramResult:
    t0 = time.time()
    summary, discoveries = "", []

    def fail(reason, message=""):
        return ProgramResult(False, reason, None, [], True, None, sha, time.time() - t0, discoveries, summary, mode, message,
                             spec_sha256=spec.sha256(), seeds=_seeds(spec))

    try:
        header = _scan_source(source.decode())
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


def result_to_dict(r: ProgramResult) -> dict:
    from su2plaq.results.store import _jsonable, verdict_to_dict

    return _jsonable({"valid": r.valid, "reason": r.reason, "mode": r.mode, "message": r.message,
                      "spec_sha256": r.spec_sha256, "seeds": r.seeds,
                      "verdict": verdict_to_dict(r.verdict) if r.verdict is not None else None,
                      "verdicts_alt": [verdict_to_dict(v) for v in r.verdicts_alt], "skeleton_equal": r.skeleton_equal,
                      "metrics": r.metrics, "program_sha256": r.program_sha256, "wall_s": r.wall_s,
                      "discoveries": r.discoveries, "summary": r.summary})


# --------------------------------------------------------------------------------------------- worker entry point
_DENY_PREFIXES = ("shutil.", "socket.", "subprocess.", "os.exec", "os.spawn", "os.posix_spawn", "os.fork", "pty.", "ctypes.",
                  "urllib.", "http.client", "ftplib.", "smtplib.", "telnetlib.", "webbrowser.")
_DENY_EVENTS = {"os.system", "os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.chmod", "os.chown", "os.link", "os.symlink",
                "os.truncate", "os.utime", "os.putenv", "os.unsetenv", "os.setxattr", "os.removexattr", "os.mkfifo", "os.mknod",
                "os.kill", "os.killpg", "os.chroot", "os.chdir", "os.fchdir", "os.setuid", "os.setgid"}
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND


def _install_audit_guard(allowed_writes):
    """Install the audit hook of the build worker (see the module docstring for exactly what it enforces)."""
    allowed = {os.path.realpath(str(p)) for p in allowed_writes}

    def hook(event, args):
        if event == "open":
            path, mode, flags = args
            writing = bool(flags & _WRITE_FLAGS) if isinstance(flags, int) else False
            if isinstance(mode, str) and any(c in mode for c in "wax+"):
                writing = True
            if writing:
                try:
                    real = os.path.realpath(os.fspath(path)) if not isinstance(path, int) else None
                except (TypeError, ValueError):
                    real = None
                if real is None or real not in allowed:
                    raise PermissionError(f"proposer programs may not write files (open {path!r} mode {mode!r})")
        elif event in _DENY_EVENTS or event.startswith(_DENY_PREFIXES):
            raise PermissionError(f"proposer programs may not use {event}")

    sys.addaudithook(hook)


def _worker(path, spec_json, out, meta):
    # heavy imports first (so that importing them is not subject to the guard), then the guard, then the program
    import qiskit  # noqa: F401
    from qiskit import qpy

    import su2plaq.compress.oracle  # noqa: F401
    import su2plaq.compress.spec  # noqa: F401
    import su2plaq.evaluate.sparse_sim  # noqa: F401

    metap = pathlib.Path(meta)
    outp = pathlib.Path(out)
    _install_audit_guard([outp, metap])
    try:
        specs = []
        for d in json.loads(pathlib.Path(spec_json).read_text()):
            d["alt_angles"] = tuple(tuple(x) for x in d["alt_angles"])
            specs.append(TaskSpec(**d))
        mod = load_program(path)
        circuits, discoveries = [], []
        for sp in specs:
            b = mod.build(sp)
            if type(b) is not B.Builder:
                raise ContractError("build(spec) must return a su2plaq.compress.builder.Builder")
            circuits.append(b.circuit())
            discoveries.append(list(b.discoveries))
        with open(outp, "wb") as fh:
            qpy.dump(circuits, fh)
        metap.write_text(json.dumps({"discoveries": discoveries}))
    except ContractError as exc:
        metap.write_text(json.dumps({"error": str(exc), "kind": "contract"}))
    except BaseException as exc:   # noqa: BLE001 - the worker reports every failure of proposer code to the parent
        import traceback

        metap.write_text(json.dumps({"error": f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-600:]}", "kind": "runtime"}))


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "--worker":
        _worker(*sys.argv[2:])
    else:
        raise SystemExit("usage: python -m su2plaq.compress.evaluate --worker <program> <specs.json> <out.qpy> <meta.json>")
