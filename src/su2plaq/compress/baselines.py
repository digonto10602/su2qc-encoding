"""Baselines and external seeds of the compression loop (prompts/002 §2.10, §5 row 2.5).

* `general_circuit(spec)`: the M1 reference circuit (build_UE / build_UB / build_step with the outer register) for the spec's
  kind, order and angles; `general_program_path(spec)` its image as a proposer program (generated, angle-linear, through the
  Builder; `compress/programs/<encoding>/seed/000-general.py` for step order 1).
* `qiskit_l3(spec, seed)`: Qiskit's level-3 transpile of it into the Builder basis.
* `import_seed(spec, source)`: "paulo34" (his compiled Clifford+T circuit: fixed angle beta = 1, kind UB, never a parent),
  "lean22" / "lean22_v2" (su2qc-trotter plaquette circuits, vendored in refs/trotter/ at a recorded commit; su2qc-trotter applies
  its electric phases AFTER the plaquette, so only the plaquette is imported and OUR U_E is prepended), "spinnet15" (a reason).
* `verify_synthesised(qc, spec)`: the Clifford+T re-verification the spec promises: synthesise at spec.eps and evaluate with
  `synth_tolerances(n_rot, eps)` (sparse engine, aer_mps fallback; `ok and certified` required).
"""
from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass

import numpy as np

from su2plaq.circuits import twelve as C
from su2plaq.compress import builder as B
from su2plaq.compress.spec import ROOT, TaskSpec, get_encoding

SEED_FAMILY = "seed"


# ---------------------------------------------------------------------------------------------- general circuit
def general_circuit(spec: TaskSpec):
    """The reference circuit for the spec (registers d, o, then the ancilla registers of the M1 port)."""
    if spec.kind == "UE":
        return C.build_UE(spec.alpha, with_outer=True)
    if spec.kind == "UB":
        return C.build_UB(spec.beta, with_outer=True)
    return C.build_step(spec.alpha, spec.beta, spec.order, with_outer=True)


def _stem(spec: TaskSpec, base: str = "general") -> str:
    suffix = "" if (spec.kind == "step" and spec.order == 1) else f"-{spec.kind.lower()}" + (f"-o{spec.order}" if spec.kind == "step" and spec.order != 1 else "")
    return f"{base}{suffix}"


def general_program_path(spec: TaskSpec) -> pathlib.Path:
    """compress/programs/<encoding>/seed/000-general[-<kind>].py, generated on first use (afterwards the file is immutable)."""
    path = ROOT / "compress" / "programs" / spec.encoding / SEED_FAMILY / f"000-{_stem(spec)}.py"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(program_source(lambda s: general_circuit(s), spec, summary=f"the reference circuit of the {spec.encoding} encoding "
                        f"({spec.kind}) expressed through the Builder; every angle is a linear function of spec.alpha / spec.beta."))
    return path


# ---------------------------------------------------------------------------------------------- program generation
_ONE = {"x", "z", "h", "s", "sdg", "t", "tdg"}
_TWO = {"cx", "cz", "ch", "swap"}
_THREE = {"ccx", "rccx", "ccz"}
_ROT1 = {"rz", "p"}
_ROT2 = {"crz", "crx", "cp"}


def _gate_list(qc):
    out = []
    for i in qc.data:
        op = i.operation
        if op.name == "barrier":
            continue
        out.append((op.name, tuple(float(x) for x in op.params), tuple(qc.find_bit(q).index for q in i.qubits)))
    return out


def _fit_angles(circuit_fn, spec: TaskSpec):
    """Per rotation: angle = ca * alpha + cb * beta, fitted from three circuits and CHECKED at the nominal and alternate angles."""
    pts = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    base = [_gate_list(circuit_fn(spec.with_angles(a, b))) for a, b in pts]
    if not (len({tuple((g[0], g[2]) for g in gl) for gl in base}) == 1):
        raise ValueError("the circuit skeleton depends on the angles; no angle-linear program can be generated")
    coeffs = []
    for k, (name, params, qs) in enumerate(base[0]):
        if params:
            if abs(params[0]) > 1e-12:
                raise ValueError(f"gate {k} ({name}) has a non-zero angle at alpha = beta = 0")
            coeffs.append((base[1][k][1][0] - params[0], base[2][k][1][0] - params[0]))
        else:
            coeffs.append(None)
    for a, b in [(spec.alpha, spec.beta), *spec.alt_angles]:
        gl = _gate_list(circuit_fn(spec.with_angles(a, b)))
        for (name, params, qs), c in zip(gl, coeffs):
            if params and abs(params[0] - (c[0] * a + c[1] * b)) > 1e-10:
                raise ValueError(f"angle of a {name} gate is not linear in (alpha, beta)")
    return base[0], coeffs


def _expr(ca: float, cb: float) -> str:
    terms = []
    for c, nm in ((ca, "spec.alpha"), (cb, "spec.beta")):
        if abs(c) > 1e-14:
            terms.append(f"{c!r} * {nm}")
    return " + ".join(terms) if terms else "0.0"


def program_source(circuit_fn, spec: TaskSpec, *, summary: str, family: str = SEED_FAMILY, parent: str | None = None,
                   discoveries: tuple = ()) -> str:
    """Python source of a proposer program that rebuilds `circuit_fn(spec)` through the Builder with angles as linear functions
    of spec.alpha / spec.beta (coefficients fitted and verified from the circuit itself, not typed)."""
    gates, coeffs = _fit_angles(circuit_fn, spec)
    enc = get_encoding(spec.encoding)
    nq = max(max(qs) for _, _, qs in gates) + 1
    n_anc = max(0, nq - (enc.n_data + enc.n_outer))
    lines = [f'"""SUMMARY: {summary}', ""]
    lines += [f"DISCOVERY: {d}" for d in discoveries]
    lines += ['"""', f"FAMILY = {family!r}", f"PARENT = {parent!r}", "", "from su2plaq.compress.builder import Builder", "", "",
              "def build(spec):", "    b = Builder(spec)"]
    if n_anc:
        lines.append(f'    b.alloc({n_anc}, "work")')
    for (name, params, qs), c in zip(gates, coeffs):
        args = ", ".join(([_expr(*c)] if params else []) + [str(q) for q in qs])
        lines.append(f"    b.{name}({args})")
    lines += ["    return b", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------- Qiskit level-3 baseline
L3_WINDOW = 32


def qiskit_l3_whole(spec: TaskSpec, seed: int = 12345):
    """Whole-circuit level-3 transpile of the general circuit into the Builder basis (idle qubits are NOT assumed clean).
    Qiskit's optimiser hoists Hadamards across the whole circuit (up to ~2^21 amplitudes per input), so this version cannot be
    verified by the exact sparse engine; it is kept for the cost comparison only."""
    from qiskit import transpile

    return transpile(general_circuit(spec), basis_gates=sorted(B.BASIS), optimization_level=3, seed_transpiler=seed,
                     qubits_initially_zero=False)


def qiskit_l3(spec: TaskSpec, seed: int = 12345, window: int = L3_WINDOW):
    """The Qiskit level-3 baseline: the general circuit is cut into windows of `window` consecutive instructions, each window is
    transpiled with optimization_level=3 (seed `seed`, Builder basis, idle qubits not assumed clean) and the results are
    concatenated in program order.  Windowing keeps the optimiser from hoisting Hadamards across the whole circuit, which would
    make the baseline unverifiable (see qiskit_l3_whole); within a window the optimisation is the stock Qiskit one."""
    from qiskit import QuantumCircuit, transpile

    qc = general_circuit(spec)
    out = QuantumCircuit(*qc.qregs, global_phase=qc.global_phase, name="qiskit_l3")
    data = list(qc.data)
    for s0 in range(0, len(data), window):
        chunk = data[s0:s0 + window]
        qs = sorted({qc.find_bit(q).index for i in chunk for q in i.qubits})
        idx = {q: k for k, q in enumerate(qs)}
        sub = QuantumCircuit(len(qs))
        for i in chunk:
            sub.append(i.operation, [idx[qc.find_bit(q).index] for q in i.qubits])
        t = transpile(sub, basis_gates=sorted(B.BASIS), optimization_level=3, seed_transpiler=seed, qubits_initially_zero=False)
        out.compose(t, qubits=[out.qubits[q] for q in qs], inplace=True)      # compose adds t.global_phase
    return out


def general_polished(spec: TaskSpec):
    from su2plaq.compress.passes import polish

    return polish(general_circuit(spec), spec)


# ---------------------------------------------------------------------------------------------- external seeds
@dataclass
class SeedCircuit:
    qc: object
    source: str
    fixed_angle: bool
    alpha: float | None
    beta: float | None
    kind: str
    can_be_parent: bool


_TROTTER = ROOT / "refs" / "trotter" / "plaquette_seeds.json"


def trotter_plaquette(source: str, beta: float, *, with_outer: bool = True):
    """The vendored su2qc-trotter plaquette circuit `source` ('lean22' | 'lean22_v2') at alpha_P = 2 beta, in our layout
    (data, outer, ancillas via import_map)."""
    from qiskit import QuantumCircuit, QuantumRegister

    d = json.loads(_TROTTER.read_text())[source]
    enc = get_encoding("twelve")
    m = enc.import_map(source)
    qmap = m["qubit_map"]
    n_anc = len(qmap) - enc.n_data
    qc = QuantumCircuit(QuantumRegister(enc.n_data, "d"), QuantumRegister(enc.n_outer, "o"), QuantumRegister(n_anc, "anc"),
                        name=source)
    alpha_p = 2.0 * beta
    for name, qs, coeff in d["gates"]:
        q = [qmap[x] for x in qs]
        if coeff is None:
            getattr(qc, name)(*q)
        else:
            qc.rz(coeff * alpha_p, *q)
    return qc


def _seed_step_circuit(source: str, spec: TaskSpec):
    """Our U_E layer (electric first) + the imported plaquette (+ the second half layer for order 2)."""
    from qiskit import QuantumCircuit

    pl = trotter_plaquette(source, spec.beta)
    qc = QuantumCircuit(*pl.qregs, name=f"{source}-{spec.kind}")
    data = list(range(12))
    if spec.kind == "UB":
        qc.compose(pl, inplace=True)
        return qc
    qc.compose(C.build_UE(spec.alpha if spec.order == 1 else spec.alpha / 2), qubits=data, inplace=True)
    qc.compose(pl, inplace=True)
    if spec.order == 2:
        qc.compose(C.build_UE(spec.alpha / 2), qubits=data, inplace=True)
    return qc


def import_seed(spec: TaskSpec, source: str):
    """SeedCircuit or a reason string."""
    if source == "spinnet15":
        return get_encoding(spec.encoding).import_map("spinnet15")
    if source == "paulo34":
        return SeedCircuit(qc=C.paulo_circuit(with_outer=True), source=source, fixed_angle=True, alpha=None, beta=1.0, kind="UB",
                           can_be_parent=False)
    if source in ("lean22", "lean22_v2"):
        if spec.kind == "UE":
            return f"{source} is a plaquette circuit; it has no electric (U_E) part"
        return SeedCircuit(qc=_seed_step_circuit(source, spec), source=source, fixed_angle=False, alpha=spec.alpha, beta=spec.beta,
                           kind=spec.kind, can_be_parent=True)
    raise ValueError(f"unknown seed source {source!r}")


def seed_program_source(spec: TaskSpec, source: str) -> str:
    """Parent-able seeds as a proposer program (angle-linear)."""
    return program_source(lambda s: _seed_step_circuit(source, s), spec, summary=f"su2qc-trotter {source} plaquette (vendored, "
                          "plaquette only) behind our electric layer.")


def evaluate_seed(spec: TaskSpec, seed: SeedCircuit, mode: str = "full"):
    """Fixed-angle seeds are judged at their OWN angles / kind with the tolerance of a synthesised circuit whose rotation count is
    bounded from its T count (no alternate angles); the others by `evaluate_circuit`."""
    from su2plaq.compress import evaluate as E

    if not seed.fixed_angle:
        return E.evaluate_circuit(seed.qc, spec, mode)
    import time

    from su2plaq.compress import oracle
    from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
    from su2plaq.metrics.logical import logical_metrics

    t0 = time.time()
    n_t = sum(1 for i in seed.qc.data if i.operation.name in ("t", "tdg"))
    t_fixed = logical_metrics(C.paulo_logical(seed.beta))["t_fixed"]
    eps = spec.eps
    n_rot = max(1, int((n_t - t_fixed) // (3 * math.log2(1 / eps) - 6)))
    tol = synth_tolerances(n_rot, eps)
    s2 = TaskSpec(**{**spec.to_dict(), "kind": seed.kind, "alpha": spec.alpha if seed.alpha is None else seed.alpha,
                     "beta": seed.beta, "alt_angles": (), "tol_err": tol["tol_err"], "tol_gauss": tol["tol_gauss"]})
    enc = get_encoding(spec.encoding)
    v = evaluate(seed.qc, enc, oracle.target(s2), tol_err=s2.tol_err, tol_gauss=s2.tol_gauss, gauss=True, engine="auto",
                 cap=spec.support_cap)
    violations = E._gate_violations(seed.qc)
    valid, reason = E._classify(v, violations)
    try:
        from su2plaq.compress.metrics import metrics

        met = metrics(seed.qc, s2, measured=False)
    except ValueError:
        met = None
    return E.ProgramResult(valid, reason, v, [], True, met, "", time.time() - t0, [], f"external seed {seed.source}", mode,
                           f"fixed angle beta={seed.beta}, kind {seed.kind}; synthesised tolerance {tol['tol_err']:.2e} "
                           f"(<= {n_rot} rotations)", spec_sha256=s2.sha256(), seeds=E._seeds(s2))


# ---------------------------------------------------------------------------------------------- Clifford+T re-verification
def verify_synthesised(qc, spec: TaskSpec, eps: float | None = None) -> dict:
    """Synthesise `qc` with pygridsynth at eps (default spec.eps) and re-verify it against the spec's target with
    `synth_tolerances(n_rot, eps)` on both the error and the Gauss residual.  ok = verdict ok AND certified."""
    from su2plaq.compress import oracle
    from su2plaq.compress.synth import gridsynth_word
    from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
    from su2plaq.metrics.cliffordt import synthesize

    eps = spec.eps if eps is None else eps
    synth, info = synthesize(qc, eps, word_fn=gridsynth_word)
    tol = synth_tolerances(info["n_rot"], eps)
    v = evaluate(synth, get_encoding(spec.encoding), oracle.target(spec), **tol, gauss=True, engine="auto", cap=spec.support_cap)
    t_total = sum(1 for i in synth.data if i.operation.name in ("t", "tdg"))
    return {"ok": bool(v.ok and v.certified), "verdict": v, "eps": eps, "n_rot": info["n_rot"], "tolerances": tol,
            "t_total": t_total, "error_bound_sum": info["error_bound_sum"], "error_measured_sum": info["error_measured_sum"]}
