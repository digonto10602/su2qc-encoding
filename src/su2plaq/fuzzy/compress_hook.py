"""M10 hook: the Gu-et-al compression loop on the fuzzy one-Trotter-step units (prompts/302; METHODS-fuzzy F9).

Two compression units are registered in the laptop machinery (`su2plaq.compress.*`, never edited) by attribute patching:

* ``fuzzy_ub``  / kind ``UB``: exp(+2 i beta square) on the 8 row qubits (256 x 256); unit frame qubit i = circuit qubit ROW_QUBITS[i]
  (frame qubit 2l = q2^l, 2l+1 = q1^l); up to 32 ancillas.
* ``fuzzy_link`` / kind ``UE``: the one-link block exp(-i(alpha/2 K1 + kappa2 K2)) (16 x 16) on frame qubits (q4, q3, q2, q1);
  ``spec.beta`` plays kappa2; no ancilla.

`compose_step` builds the 48 (+ ancilla) qubit step from unit circuits with layer metadata, so that the composed circuit is scored
(`logical_metrics`) and re-verified with `verify_step_samples` (M9).  `install()` is idempotent and exports the environment that
makes the sandboxed build worker (a subprocess of `su2plaq.compress.evaluate`) install the hook as well (`sitehook/sitecustomize.py`).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.circuits import fuzzy as C
from su2plaq.fuzzy import targets as tg
from su2plaq.fuzzy.verify import ROW_QUBITS, FuzzyBlockEncoding

ENCODINGS = ("fuzzy_ub", "fuzzy_link")
UNITS = {"fuzzy_ub": "UB", "fuzzy_link": "UE"}
NOMINAL = (0.37, 0.61)
SEED = 20261104
ROOT = pathlib.Path(__file__).resolve().parents[3]
STRUCTURE_FILE = ROOT / "compress" / "specs" / "fuzzy-structure.json"
SITEHOOK_DIR = pathlib.Path(__file__).resolve().parent / "sitehook"
LEAN_NA = {"status": "n_a", "reason": "fuzzy: no exact exporter for the Lean certificate (plan 302 §0.5)"}
_UB_ANC = 7


# ------------------------------------------------------------------------------------------------------------ tasks
class _Basis:
    """All 2^n computational codes are physical: labels code0 .. code{2^n-1}."""

    def __init__(self, n: int):
        self.labels = [f"code{k}" for k in range(n)]

    def index(self, key):
        return self.labels.index(key)


_PROPOSER_NOTE = (
    "Proposer commands (the fuzzy hook is installed by these wrappers; the plain `python -m su2plaq.compress.*` modules do not know "
    "the fuzzy units, so use the script): `python scripts/m10_round.py candidate <program.py> --encoding {enc} --kind {kind} --trial|--full` "
    "(wraps `su2plaq.compress.run_candidate`), `python scripts/m10_round.py oracle --encoding {enc} --kind {kind} [--column j] [--element i j]`. "
    "Programs import only `su2plaq.compress.{{builder,oracle,spec}}` and numpy. Background: docs/METHODS-fuzzy.md F5, F9.\n")


class FuzzyUBTask(FuzzyBlockEncoding):
    name = "fuzzy_ub"

    def __init__(self):
        super().__init__(8, data_qubits=list(range(8)))
        self.registers = {"d": list(range(8)), "row_b": [1, 0], "row_r": [3, 2], "row_t": [5, 4], "row_l": [7, 6]}
        self.basis = _Basis(256)

    def target(self, kind, alpha, beta, order=1):
        if kind != "UB":
            raise ValueError("fuzzy_ub only has the kind 'UB'")
        return tg.UB_row(beta)

    def peak_qubit_cap(self, spec):
        return self.n_data + 32

    def task_text(self, spec) -> str:
        return (f"Implement $U_B(\\beta)=\\exp(+2i\\beta\\,\\square)$ of the fuzzy-gauge-theory plaquette (arXiv:2308.05253; "
                f"METHODS-fuzzy F5) exactly (up to one global phase) on the 8 row qubits, i.e. a $256\\times256$ unitary on all {len(self.basis.labels)} "
                f"computational codes (all are physical), at $\\beta={spec.beta:g}$ and, with the same gate skeleton, at the alternate "
                f"pairs. Every ancilla must return to $|0\\rangle$.")

    def describe(self) -> str:
        return (
            "FUZZY unit `fuzzy_ub` (fuzzy gauge theory, arXiv:2308.05253, METHODS-fuzzy F1-F5): the row block of the plaquette "
            "operator of the 4-link plaquette. Data register `d` = 8 row qubits; frame qubit 2l = q2 and 2l+1 = q1 of link l "
            "(l = 0,1,2,3 = b, r, t, l), registers `row_b=[1,0]`, `row_r=[3,2]`, `row_t=[5,4]`, `row_l=[7,6]` "
            "(most significant first). Row index of a code is sum_l (2 q1^l + q2^l) 4^l. The target is the exact 256 x 256 unitary "
            "exp(+2 i beta square) with `spec.beta` = beta (`spec.alpha` is unused). Only the row qubits carry data: the column "
            "qubits (q3, q4) are not touched by the plaquette. The known structure: parity frame (3 CNOTs q1^b -> q1^{r,t,l}); the "
            "operator splits into 8 parity sectors, each Clifford-conjugate to a rotation R_x(-4 beta sigma) with singular values "
            "{16, 0^12}, {4, 0^15} or {1^16}; the baseline spends ~1700 CX on one 3-controlled AND and Clifford frames per sector. "
            "Ancillas: up to 32 clean ancillas, `Builder.alloc/free`.\n"
            + _PROPOSER_NOTE.format(enc="fuzzy_ub", kind="UB"))


class FuzzyLinkTask(FuzzyBlockEncoding):
    name = "fuzzy_link"

    def __init__(self):
        super().__init__(4, data_qubits=[0, 1, 2, 3])
        self.registers = {"d": [0, 1, 2, 3]}
        self.basis = _Basis(16)

    def target(self, kind, alpha, beta, order=1):
        if kind != "UE":
            raise ValueError("fuzzy_link only has the kind 'UE'")
        return tg.UEK_link(alpha, beta)             # spec.beta plays kappa2

    def peak_qubit_cap(self, spec):
        return self.n_data                           # no ancilla: the composed step keeps link-local kinetic layers

    def task_text(self, spec) -> str:
        return (f"Implement the one-link kinetic block $U_{{EK}}(\\alpha,\\kappa_2)=\\exp[-i(\\tfrac\\alpha2\\mathcal K_1+\\kappa_2\\mathcal K_2)]$ "
                f"of the fuzzy gauge theory (arXiv:2308.05253; METHODS-fuzzy F2, F9) exactly (up to one global phase) as a $16\\times16$ "
                f"unitary on the 4 link qubits, at $(\\alpha,\\kappa_2)=({spec.alpha:g},{spec.beta:g})$ and, with the same gate skeleton, at the "
                f"alternate pairs. **`spec.beta` is $\\kappa_2$** (the Trotter step uses $\\kappa_2=r\\alpha/2$; the three angle pairs are "
                f"three independent $(\\alpha,\\kappa_2)$ points). No ancilla: do not call `alloc` (more than 4 qubits is rejected).")

    def describe(self) -> str:
        return (
            "FUZZY unit `fuzzy_link` (fuzzy gauge theory, arXiv:2308.05253, METHODS-fuzzy F1-F2, F9): one link. Data register `d` = "
            "frame qubits (0,1,2,3) = (q4, q3, q2, q1) of the link. Target exp(-i(alpha/2 K1 + kappa2 K2)) with `spec.alpha` = alpha and "
            "**`spec.beta` = kappa2** (the Trotter step applies it to 12 links with kappa2 = r alpha/2). K1 = 3/2 - 1/4 (X2X4 - Y2Y4 + Z2Z4)"
            "(1 + Z1Z3), K2 = -X1X3 + Y1X2Y3X4 - Y1Y2Y3Y4 + Y1Z2Y3Z4 (qubit k = q_k), [K1, K2] = 0. In the Clifford frame cx(q1,q3) cx(q2,q4) "
            "h(q1) h(q2) both are diagonal sums of Z-strings (10 strings in total; see F9), so the block is one frame plus a phase "
            "polynomial; the baseline uses two CNOT ladders (36 CX). No ancilla.\n"
            + _PROPOSER_NOTE.format(enc="fuzzy_link", kind="UE"))


# ------------------------------------------------------------------------------------------------------------ circuits
def _replace_const_phase(big_inst_op):
    """p(+-pi) -> z (exact); any other constant p is refused (the laptop program generator needs angle-linear gates)."""
    lam = float(big_inst_op.params[0])
    if abs(abs(lam) - np.pi) < 1e-12:
        from qiskit.circuit.library import ZGate

        return ZGate()
    raise ValueError(f"constant p({lam}) cannot be expressed as an angle-linear gate")


def ub_frame(big: QuantumCircuit) -> QuantumCircuit:
    """build_UB's 23-qubit circuit -> 8-qubit unit frame (row qubits) + 7 ancillas 'anc'; p(-pi) -> z."""
    qc = QuantumCircuit(QuantumRegister(8, "d"), QuantumRegister(big.num_qubits - 16, "anc"), global_phase=big.global_phase)
    pos = {q: i for i, q in enumerate(ROW_QUBITS)}
    for i in range(16, big.num_qubits):
        pos[i] = 8 + i - 16
    for inst in big.data:
        op = inst.operation
        if op.name == "p":
            op = _replace_const_phase(op)
        qs = [big.find_bit(q).index for q in inst.qubits]
        if any(q not in pos for q in qs):
            raise ValueError("build_UB touches a column qubit")
        qc.append(op, [pos[q] for q in qs])
    return qc


def general_ub_fn(beta: float) -> QuantumCircuit:
    return ub_frame(C.build_UB(beta))


def general_link_fn(alpha: float, kappa2: float) -> QuantumCircuit:
    qc = QuantumCircuit(QuantumRegister(4, "d"))
    qc.compose(C.link_UE(alpha), inplace=True)
    qc.compose(C.link_UK(kappa2), inplace=True)
    return qc


def general_circuit(spec) -> QuantumCircuit:
    if spec.encoding == "fuzzy_ub":
        return general_ub_fn(spec.beta)
    if spec.encoding == "fuzzy_link":
        return general_link_fn(spec.alpha, spec.beta)
    raise ValueError(f"not a fuzzy unit: {spec.encoding!r}")


def ub_frame_to_full(qc8: QuantumCircuit) -> QuantumCircuit:
    """8-qubit unit frame (+ ancillas) -> registers d (16) [+ w]: frame qubit i -> ROW_QUBITS[i], ancilla j -> qubit 16 + j."""
    n_anc = qc8.num_qubits - 8
    if n_anc < 0:
        raise ValueError("a U_B unit circuit needs the 8 row qubits")
    regs = [QuantumRegister(16, "d")] + ([QuantumRegister(n_anc, "w")] if n_anc else [])
    out = QuantumCircuit(*regs, global_phase=0.0)
    out.compose(qc8, qubits=list(ROW_QUBITS) + [16 + j for j in range(n_anc)], inplace=True)
    return out


def compose_step(link_fn, ub_fn, alpha: float, beta: float, kappa2: float | None = None, order: int = 1,
                 with_outer: bool = True) -> QuantumCircuit:
    """The Trotter step from unit circuits.  Registers d (16), [o (32)], w (ancillas of U_B).  order 1: 4 inner link blocks
    U_EK(alpha, kappa2), U_B(beta), then the outer blocks; order 2: half-angle inner blocks on both sides of U_B.  The outer
    links get one full-angle block each (as `circuits.fuzzy.build_step`).  ``metadata['layers']`` = [(kind, i0, i1)]: kind 'UE'
    for the inner link blocks (kinetic layer), 'UB', 'outer' (one range per outer link)."""
    if order not in (1, 2):
        raise ValueError(f"order must be 1 or 2, got {order}")
    kappa2 = 0.5 * alpha if kappa2 is None else kappa2
    ub = ub_fn(beta)
    n_anc = ub.num_qubits - 8
    if n_anc < 0:
        raise ValueError("ub_fn must return a circuit on the 8 row qubits (+ ancillas)")
    regs = [QuantumRegister(16, "d")] + ([QuantumRegister(32, "o")] if with_outer else []) + ([QuantumRegister(n_anc, "w")] if n_anc else [])
    qc = QuantumCircuit(*regs, name="step")
    anc0 = 16 + (32 if with_outer else 0)
    layers = []

    def add(kind, circ, qubits):
        a = len(qc.data)
        qc.compose(circ, qubits=list(qubits), inplace=True)
        layers.append((kind, a, len(qc.data)))

    def kinetic(a, k):
        blk = link_fn(a, k)
        if blk.num_qubits != 4:
            raise ValueError(f"link_fn must return a 4-qubit circuit, got {blk.num_qubits}")
        a0 = len(qc.data)
        for l in range(4):
            qc.compose(blk, qubits=range(4 * l, 4 * l + 4), inplace=True)
        layers.append(("UE", a0, len(qc.data)))

    half = 1.0 if order == 1 else 0.5
    kinetic(half * alpha, half * kappa2)
    add("UB", ub, list(ROW_QUBITS) + [anc0 + j for j in range(n_anc)])
    if order == 2:
        kinetic(half * alpha, half * kappa2)
    if with_outer:
        blk = link_fn(alpha, kappa2)
        for l in range(4, 12):
            add("outer", blk, range(4 * l, 4 * l + 4))
    qc.metadata = {"kind": "step", "alpha": alpha, "beta": beta, "kappa2": kappa2, "order": order, "layers": layers}
    return qc


def _metrics_dict(qc) -> dict:
    from su2plaq.metrics.cliffordt import t_estimate
    from su2plaq.metrics.logical import logical_metrics

    m = logical_metrics(qc)
    m.pop("rz_angles", None)
    m["t_estimate"] = t_estimate(m["n_rot"], m["t_fixed"], 1e-6)
    return m


def step_metrics(link_fn, ub_fn, with_outer: bool = True, order: int = 1) -> dict:
    """logical_metrics of the composed step at the nominal angles (0.37, 0.61, r = 1) + 't_estimate' (eps = 1e-6)."""
    return _metrics_dict(compose_step(link_fn, ub_fn, NOMINAL[0], NOMINAL[1], None, order, with_outer))


# ------------------------------------------------------------------------------------------------------------ archive entries
def _root(root):
    return pathlib.Path(root) if root is not None else ROOT


def circuit_of_entry(entry, spec, root=None) -> QuantumCircuit:
    """The circuit of an archive entry at spec's angles (programs are rebuilt in the laptop's sandboxed worker)."""
    install()
    from su2plaq.compress import baselines as BL
    from su2plaq.compress import evaluate as E

    root = _root(root)
    pp = pathlib.Path(entry.program_path)
    if str(pp).endswith(".circuit"):
        label = pp.stem
        if label == "general":
            return BL.general_circuit(spec)
        if label == "general+polish":
            return BL.general_polished(spec)[0]
        if label == "qiskit_l3":
            return BL.qiskit_l3(spec, seed=12345)
        raise ValueError(f"unknown circuit-valued baseline {label!r}")
    f = pp if pp.is_absolute() else (root / pp if (root / pp).exists() else ROOT / pp)
    circuits, _ = E._build_in_subprocess(f.read_bytes(), [spec], E.BUILD_TIMEOUT_S)
    return circuits[0]


def entry_fn(entry, spec, root=None):
    """callable for compose_step: link unit (alpha, kappa2) -> circuit, U_B unit (beta) -> circuit (cached per angle)."""
    cache: dict = {}

    def build(a, b):
        key = (float(a), float(b))
        if key not in cache:
            cache[key] = circuit_of_entry(entry, spec.with_angles(a, b), root=root)
        return cache[key].copy()

    if spec.encoding == "fuzzy_link":
        return lambda alpha, kappa2: build(alpha, kappa2)
    if spec.encoding == "fuzzy_ub":
        return lambda beta: build(spec.alpha, beta)
    raise ValueError(f"not a fuzzy unit: {spec.encoding!r}")


def best_step(root=None, order: int = 1, with_outer: bool = True):
    """-> (composed circuit from the archive's best entry of each unit, info).  A unit without a valid entry uses the general circuit."""
    install()
    from su2plaq.compress import archive as A
    from su2plaq.compress.spec import default_spec

    root = _root(root)
    fns, units = {}, {}
    for enc in ENCODINGS:
        spec = default_spec(enc, UNITS[enc])
        arch = A.Archive.load(enc, root=root, n_alt=len(spec.alt_angles), strict=True)
        best = arch.best()
        if best is None:
            fns[enc] = general_link_fn if enc == "fuzzy_link" else general_ub_fn
            units[enc] = {"entry": "general", "key": None}
        else:
            fns[enc] = entry_fn(best, spec, root=root)
            units[enc] = {"entry": best.id, "key": [float(x) for x in best.key]}
    qc = compose_step(fns["fuzzy_link"], fns["fuzzy_ub"], NOMINAL[0], NOMINAL[1], None, order, with_outer)
    return qc, {"units": units, "metrics": _metrics_dict(qc)}


def write_compressed_step(root=None, out=None, order: int = 1, with_outer: bool = True) -> dict:
    """Compose the best units, verify with `verify_step_samples`, write results/fuzzy/compressed_step.json."""
    from su2plaq.fuzzy.verify import verify_step_samples
    from su2plaq.metrics.provenance import provenance

    root = _root(root)
    qc, info = best_step(root, order, with_outer)
    v = verify_step_samples(qc, NOMINAL[0], NOMINAL[1], 0.5 * NOMINAL[0], order, n_random=32, n_phys=8, seed=SEED)
    gen = step_metrics(general_link_fn, general_ub_fn, with_outer, order)
    doc = {"order": order, "with_outer": with_outer, "units": info["units"], "composed": info["metrics"], "general": gen,
           "verification": {"err": float(v["err"]), "gauss": float(v["gauss"]), "n_inputs": int(v["n_inputs"]), "seed": SEED,
                            "mode": v["mode"], "leak": float(v["leak"])},
           "provenance": provenance({"verify_seed": SEED})}
    path = pathlib.Path(out) if out is not None else root / "results" / "fuzzy" / "compressed_step.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, default=str))
    return doc


# ------------------------------------------------------------------------------------------------------------ structure facts
def structure_facts() -> dict:
    return {"schema": "fuzzy-structure-1", "facts": [
        {"name": "card_isolated_plaquette", "value": 50, "proved_by": "decide", "theorem": "Su2Plaq.Fuzzy.count_isolated_plaquette",
         "note": "physical states of the isolated fuzzy plaquette"},
        {"name": "card_outer_vacuum", "value": 12800, "proved_by": "decide", "theorem": "Su2Plaq.Fuzzy.count_outer_vacuum",
         "note": "outer-vacuum sector"},
        {"name": "card_fixed_far_end", "value": 101197218, "proved_by": "decide", "theorem": "Su2Plaq.Fuzzy.count_fixed_far_end",
         "note": "twelve links, far end of each outer link fixed"},
        {"name": "card_far_end_weighted", "value": 6767266914, "proved_by": "decide", "theorem": "Su2Plaq.Fuzzy.count_far_end_weighted",
         "note": "far-end weighted count"},
        {"name": "K1_spectrum", "value": "{0^2, (3/2)^8, 2^6}", "proved_by": "decide", "theorem": "Su2Plaq.Fuzzy.K1_spectrum",
         "note": "link kinetic operator K1 (fuzzy_link unit)"},
        {"name": "K2_spectrum", "value": "{-4, (-2)^4, 0^6, 2^4, 4}", "proved_by": "decide", "theorem": "Su2Plaq.Fuzzy.K2_spectrum",
         "note": "link kinetic operator K2 (fuzzy_link unit); [K1, K2] = 0 (K1_K2_commute)"},
        {"name": "K1_K2_joint_eigenphases", "value": "(K1,K2) in {(0,-4),(0,4),(3/2,-2),(3/2,2),(2,0)} (+ multiplicities)",
         "proved_by": "numerical", "note": "5 joint eigenphases of the link block"},
        {"name": "square_sector_singular_values", "value": "{16, 0^12}, {4, 0^15}, {1^16} per parity sector",
         "proved_by": "numerical", "note": "U_B unit: 8 parity sectors, Clifford fixed unitaries (F5)"},
    ], "provenance": {"source": "lean/Su2Plaq/Fuzzy/{Counts,Link}.lean and METHODS-fuzzy F5, F9; written by compress_hook"}}


def write_structure(path=None) -> pathlib.Path:
    path = pathlib.Path(path) if path is not None else STRUCTURE_FILE
    text = json.dumps(structure_facts(), indent=1) + "\n"
    if not path.exists() or path.read_text() != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return path


# ------------------------------------------------------------------------------------------------------------ install
_INSTALLED = False
_CMD_SWAPS = (("python -m su2plaq.compress.run_candidate", "python scripts/m10_round.py candidate"),
              ("python -m su2plaq.compress.oracle", "python scripts/m10_round.py oracle"))


def _is_fuzzy(name: str) -> bool:
    return name in ENCODINGS


def _swap_cmds(text: str) -> str:
    for a, b in _CMD_SWAPS:
        text = text.replace(a, b)
    return text


def install() -> None:
    """Register the two units in the laptop modules (idempotent; attribute patching only; see the module docstring)."""
    global _INSTALLED
    if _INSTALLED:
        return
    from su2plaq.compress import baselines as BL
    from su2plaq.compress import brief as BR
    from su2plaq.compress import round as RD
    from su2plaq.compress import spec as S
    from su2plaq.encodings import base
    from su2plaq.evaluate import evaluator as EV

    S._ENCODINGS["fuzzy_ub"] = FuzzyUBTask()
    S._ENCODINGS["fuzzy_link"] = FuzzyLinkTask()
    for enc in ENCODINGS:
        base.NOMINAL_ANGLES[enc] = NOMINAL
    write_structure()

    # ---- spec: peak qubits, rendering, structure facts
    orig_cap, orig_render, orig_struct = S.TaskSpec.peak_qubit_cap, S.TaskSpec.render, S.TaskSpec._structure_section

    def peak_qubit_cap(self):
        if _is_fuzzy(self.encoding) and self.max_qubits is None:
            return S.get_encoding(self.encoding).peak_qubit_cap(self)
        return orig_cap(self)

    def structure_section(self):
        if not _is_fuzzy(self.encoding):
            return orig_struct(self)
        old = S.STRUCTURE_JSON
        S.STRUCTURE_JSON = STRUCTURE_FILE
        try:
            return orig_struct(self)
        finally:
            S.STRUCTURE_JSON = old

    def render(self):
        text = orig_render(self)
        if not _is_fuzzy(self.encoding):
            return text
        enc = S.get_encoding(self.encoding)
        head, rest = text.split("## Task\n\n", 1)
        _task, tail = rest.split("\n\n## Registers", 1)
        text = head + "## Task\n\n" + enc.task_text(self) + " Unphysical inputs do not exist: every code is physical.\n\n## Registers" + tail
        text = text.replace(f"and the Gauss residual of the outputs at most {self.tol_gauss:g}; ",
                            "(no per-unit Gauss check: every code is physical and the targets commute with the Gauss generators); ")
        return _swap_cmds(text)

    S.TaskSpec.peak_qubit_cap = peak_qubit_cap
    S.TaskSpec._structure_section = structure_section
    S.TaskSpec.render = render

    # ---- evaluator: no KS Gauss branch for the fuzzy block encodings
    orig_eval = EV.evaluate

    def evaluate(qc, enc, target, **kw):
        if isinstance(enc, FuzzyBlockEncoding):
            kw["gauss"] = False
            v = orig_eval(qc, enc, target, **kw)
            v.gauss_residual = 0.0
            return v
        return orig_eval(qc, enc, target, **kw)

    EV.evaluate = evaluate

    # ---- baselines: general circuit, no external seeds
    orig_general, orig_import = BL.general_circuit, BL.import_seed

    def general_dispatch(spec):
        return general_circuit(spec) if _is_fuzzy(spec.encoding) else orig_general(spec)

    def import_seed(spec, source):
        if _is_fuzzy(spec.encoding):
            if source not in ("spinnet15", "paulo34", "lean22", "lean22_v2"):
                raise ValueError(f"unknown seed source {source!r}")
            return f"{source}: not applicable to the fuzzy encoding"
        return orig_import(spec, source)

    BL.general_circuit = general_dispatch
    BL.import_seed = import_seed

    # ---- round: no Lean certificate for the fuzzy units
    orig_certify = RD._certify

    def certify(circ, spec):
        if _is_fuzzy(spec.encoding):
            return dict(LEAN_NA), 0.0
        return orig_certify(circ, spec)

    RD._certify = certify

    # ---- briefs: fuzzy structure pointer and the script commands
    orig_make, orig_ideate, orig_pointer = BR.make_brief, BR.make_ideation_brief, BR._structure_pointer

    def _fuzzy_pointer(root):
        return (f"`{STRUCTURE_FILE.relative_to(ROOT)}` (machine-proved facts about the fuzzy units: counts, K1/K2 spectra; the same "
                "facts are in the section 'Proved structure (Lean)' of the specification)")

    def _wrap(fn):
        def wrapped(encoding, kind, *a, **k):
            if not _is_fuzzy(encoding):
                return fn(encoding, kind, *a, **k)
            BR._structure_pointer = _fuzzy_pointer
            try:
                path = fn(encoding, kind, *a, **k)
            finally:
                BR._structure_pointer = orig_pointer
            path = pathlib.Path(path)
            path.write_text(_swap_cmds(path.read_text()) + _brief_note(encoding, kind))
            return path

        return wrapped

    BR.make_brief, BR.make_ideation_brief = _wrap(orig_make), _wrap(orig_ideate)

    # ---- the build worker (subprocess) installs the hook through sitecustomize
    os.environ["SU2PLAQ_FUZZY_HOOK"] = "1"
    parts = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
    if str(SITEHOOK_DIR) not in parts:
        os.environ["PYTHONPATH"] = os.pathsep.join(parts + [str(SITEHOOK_DIR)])
    _INSTALLED = True


def _brief_note(encoding: str, kind: str) -> str:
    extra = ("`spec.beta` is kappa2; `alloc` is not allowed (more than 4 qubits is rejected)." if encoding == "fuzzy_link"
             else "Frame qubits 0..7 are the row qubits (see the specification); ancillas via `Builder.alloc`.")
    return ("\n## Fuzzy hook (M10)\n\n"
            f"Use `python scripts/m10_round.py candidate <program> --encoding {encoding} --kind {kind} --trial|--full` instead of "
            "`python -m su2plaq.compress.run_candidate`, and `python scripts/m10_round.py oracle ...` instead of the oracle module. "
            f"Programs import only `su2plaq.compress.{{builder,oracle,spec}}`, numpy, qiskit. {extra}\n")
