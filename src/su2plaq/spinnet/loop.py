"""Compression of the spin-network step circuit with the laptop's loop (track S, milestone 4; prompts/104 §1, §2).

The laptop's `su2plaq.compress.*` is the machinery (evaluator, archive, briefs, report, Lean integration).  This module
only (a) registers the encoding `spinnet` in it at run time (`install`, four overrides, nothing else), (b) renders the
spin-network task specification with OUR tool commands and the spin-network Lean facts, (c) builds the round-0 seeds.

Step 4.0 created the interface, step 4.1 the shim / spec / `--worker`, step 4.2 the seeds (`import_seed`,
`seed_program_source`, `evaluate_seed`), step 4.3 the rounds (`seed_round`, `run_round`, briefs, report, `certify_best`) and
the command line (`python -m su2plaq.spinnet.loop candidate|oracle|seed|round|brief|ideation|report|certify-best|headline`),
step 4.3b the headline rule (`ANGLE_SET`, `robust_metrics`, `headline`; prompts/104 §11 E3).

No laptop-owned file is edited.  `SPINNET_CODE_FILES` are frozen during M4 (their hash is recorded in every round).
"""
from __future__ import annotations

import dataclasses
import hashlib
import inspect
import pathlib
import re
import subprocess
import sys
import time
from dataclasses import dataclass

import numpy as np

ENC, KIND = "spinnet", "step"
SPINNET_CODE_FILES: tuple[str, ...] = ("encodings/spinnet.py", "circuits/spinnet.py", "spinnet/walk.py",
                                       "spinnet/trotter_v2.py", "spinnet/paulo.py")
NOMINAL = (0.37, 0.61)
INSTALLED: dict = {}                     # {} before install(); then {"encoding": True, "build_in_subprocess": <orig>, "certify": <orig>}

_SRC = pathlib.Path(__file__).resolve().parents[1]            # src/su2plaq
_LEAN_SPINNET = pathlib.Path("lean") / "Su2Plaq" / "SpinNet"
_SHIM_MARK = "_spinnet_shim"

# headline rule (prompts/104 §11 erratum E3): the angle set on which T and depth_CT are averaged
ANGLE_SET_SEED, ANGLE_SET_N = 20261107, 20
ANGLE_SET_RANGES = ((0.05, 2.0), (0.05, 1.2))


def _make_angle_set() -> tuple[tuple[float, float], ...]:
    rng = np.random.default_rng(ANGLE_SET_SEED)
    a = rng.uniform(*ANGLE_SET_RANGES[0], ANGLE_SET_N)           # all alphas first ...
    b = rng.uniform(*ANGLE_SET_RANGES[1], ANGLE_SET_N)           # ... then all betas
    return tuple((float(x), float(y)) for x, y in zip(a, b))


ANGLE_SET: tuple[tuple[float, float], ...] = _make_angle_set()

HEADLINE_RULE_SECTION = """## Headline rule (track S)

The archive key counts T at the nominal pair; the Report 4 headline and the Lean theorem file go to the smallest robust key (CX, T summed over 20 fixed random angle pairs, angle-linear first, depth, qubits). Offsetting a rotation by +-pi/4 with a compensating `t`/`tdg` costs +1 T at every angle and saves nothing on average: it will not count. Offsets that are multiples of pi/2 belong in separate `s`/`sdg`/`z` gates so that the rotation angle stays a rational multiple of alpha or beta (Lean-certifiable). Fewer CX, fewer rotations, smaller rational coefficients, and shared rotations are what move the headline.
"""


def _root(root=None) -> pathlib.Path:
    from su2plaq.compress.spec import ROOT

    return pathlib.Path(root) if root is not None else ROOT


# ------------------------------------------------------------------------------------------------------ shim (§1)
def _need(module, name: str, what: str):
    if not hasattr(module, name):
        raise RuntimeError(f"laptop module shape changed: {module.__name__} has no attribute {name!r} ({what}); the shim of "
                           "su2plaq.spinnet.loop.install() must be amended by the planner (prompts/104 §7)")
    return getattr(module, name)


def _worker_copy(original):
    """A copy of the laptop's `_build_in_subprocess` whose worker command is `python -m su2plaq.spinnet.loop --worker ...`.
    The copy is derived from the laptop function's own source (so it follows the laptop code); RuntimeError if the worker
    command line is not found exactly once."""
    from su2plaq.compress import evaluate as E

    old = '"su2plaq.compress.evaluate", "--worker"'
    src = inspect.getsource(original)
    if src.count(old) != 1:
        raise RuntimeError("laptop module shape changed: su2plaq.compress.evaluate._build_in_subprocess no longer contains the "
                           f"worker command {old}; the shim must be amended by the planner (prompts/104 §7)")
    src = src.replace(old, '"su2plaq.spinnet.loop", "--worker"')
    ns: dict = {}
    exec(compile(src, "<spinnet shim of su2plaq.compress.evaluate._build_in_subprocess>", "exec"), E.__dict__, ns)  # noqa: S102
    fn = ns[original.__name__]
    setattr(fn, _SHIM_MARK, True)
    return fn


def _certify_dispatch(original):
    def _certify(circ, spec, program_file_sha256=None):
        """Round._certify with `spinnet` routed to the spin-network exporter/checker (Lean never changes a verdict).
        `program_file_sha256` (laptop audit-004 N2) is passed through for other encodings and recorded in the dict."""
        if spec.encoding != ENC:
            if program_file_sha256 is None:
                return original(circ, spec)
            return original(circ, spec, program_file_sha256=program_file_sha256)
        t0 = time.time()
        try:
            from dataclasses import asdict

            from su2plaq.compress.spec import get_encoding
            from su2plaq.lean.certify import LeanCert
            from su2plaq.spinnet import lean_export

            res = lean_export.certify(circ, get_encoding(ENC), spec.kind, spec.alpha, spec.beta, spec.order, timeout=1200.0)
            cert = LeanCert(status=res["status"], reason=res.get("reason", ""), cert_path=res.get("cert_path"),
                            seconds=float(res.get("seconds", time.time() - t0)), checker_sha256=res.get("checker_sha256", ""),
                            theorem_path=None, axioms=list(res.get("axioms", [])))
            d = asdict(cert)
            if program_file_sha256:
                d["program_file_sha256"] = program_file_sha256
            return d, time.time() - t0
        except NotImplementedError as exc:
            return {"status": "not_run", "reason": f"Lean certification not available: {exc}"}, time.time() - t0
        except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            return {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}, time.time() - t0

    setattr(_certify, _SHIM_MARK, True)
    return _certify


def install() -> None:
    """Register `spinnet` in the laptop's compression machinery.  Exactly four effects (prompts/104 §1):
    (i) `spec._ENCODINGS["spinnet"]`; (ii) `encodings.base.NOMINAL_ANGLES["spinnet"]`; (iii) `evaluate._build_in_subprocess`
    replaced by a copy that starts `python -m su2plaq.spinnet.loop --worker`; (iv) `round._certify` replaced by a dispatcher.
    Idempotent.  RuntimeError (naming the missing attribute) if the laptop modules have another shape."""
    from su2plaq.compress import evaluate as E
    from su2plaq.compress import round as R
    from su2plaq.compress import spec as S
    from su2plaq.encodings import base

    encodings = _need(S, "_ENCODINGS", "encoding registry")
    nominal = _need(base, "NOMINAL_ANGLES", "nominal angle table")
    _need(E, "_worker", "worker entry point called by --worker")
    _need(S, "default_spec", "default spec")
    original_build = _need(E, "_build_in_subprocess", "sandboxed program build")
    original_certify = _need(R, "_certify", "round-level Lean certification")
    if ENC not in encodings:
        from su2plaq.encodings.spinnet import SpinNet

        encodings[ENC] = SpinNet()
    nominal[ENC] = NOMINAL
    INSTALLED["encoding"] = True
    if not getattr(original_build, _SHIM_MARK, False):
        INSTALLED["build_in_subprocess"] = original_build
        E._build_in_subprocess = _worker_copy(original_build)
    if not getattr(original_certify, _SHIM_MARK, False):
        INSTALLED["certify"] = original_certify
        R._certify = _certify_dispatch(original_certify)


def spec(order: int = 1):
    """The spin-network step TaskSpec (nominal angles (0.37, 0.61); order 2 via dataclasses.replace)."""
    from su2plaq.compress.spec import default_spec

    install()
    sp = default_spec(ENC, KIND)
    return sp if order == 1 else dataclasses.replace(sp, order=order)


def code_hash() -> str:
    """sha256 of the laptop `provenance.code_hash()` followed by the (name, content) of every SPINNET_CODE_FILES entry
    (the laptop's list does not contain the spin-network files)."""
    from su2plaq.compress import provenance

    h = hashlib.sha256()
    h.update(provenance.code_hash().encode())
    for rel in SPINNET_CODE_FILES:
        f = _SRC / rel
        h.update(f.name.encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ Lean facts (§1)
# (name, Lean file, theorem, short note) -- the value of every fact is read from the theorem's statement in the Lean source
# and cross-checked against the Python encoding; a disagreement raises (no value is typed into this module).
_COUNT_FACTS = (
    ("card_inner_labels", "Counts", "number of inner labels = admissible data codes (4 link bits + 4 corner bits)"),
    ("card_bright_labels", "Counts", "inner labels with no corner bit set (the codes K acts on)"),
    ("card_dark_labels", "Counts", "inner labels with a corner bit set (K = 0 on them)"),
    ("card_bright_pairs", "Counts", "bright codes come in pairs y <-> y xor 0b1111 (K couples only the two members)"),
    ("card_states_spinnet", "Counts", "physical states = distinct computational-basis codes y + 256 o"),
    ("mult_two", "Counts", "states of the vacuum pair 0000 <-> 1111, |K| = 2 (multiplicity of the eigenvalues -2 and +2)"),
    ("mult_one", "Counts", "states of the six pairs with |K| = 1 (multiplicity of the eigenvalues -1 and +1)"),
    ("mult_half", "Counts", "states of the alternating pair 0101 <-> 1010, |K| = 1/2 (multiplicity of -1/2 and +1/2)"),
)


def _lean_text(name: str, root: pathlib.Path) -> tuple[str, str]:
    rel = (_LEAN_SPINNET / f"{name}.lean").as_posix()
    p = root / rel
    if not p.exists():
        raise RuntimeError(f"Lean source {rel} not found under {root}")
    return rel, p.read_text()


def _statement(src: str, theorem: str, file: str) -> str:
    """Text between `theorem <name>` and `:= by decide` (the statement, whitespace collapsed); RuntimeError if absent."""
    m = re.search(rf"^theorem {re.escape(theorem)}\b(.*?):=\s*by\s+decide\b", src, re.M | re.S)
    if m is None:
        raise RuntimeError(f"theorem {theorem} with proof `by decide` not found in {file}")
    return " ".join(m.group(1).split())


def _lean_nat(src: str, theorem: str, file: str) -> int:
    m = re.search(r"=\s*(\d+)\s*$", _statement(src, theorem, file))
    if m is None:
        raise RuntimeError(f"theorem {theorem} in {file} does not have the shape `... = <number>`")
    return int(m.group(1))


def _lean_nat_list(src: str, theorem: str, file: str) -> list[int]:
    m = re.search(r"=\s*\[([0-9,\s]+)\]\s*$", _statement(src, theorem, file))
    if m is None:
        raise RuntimeError(f"theorem {theorem} in {file} does not have the shape `... = [n, n, ...]`")
    return [int(x) for x in m.group(1).replace(" ", "").split(",")]


def _numeric_counts(enc) -> dict:
    """The same counts from the Python encoding (independent of the Lean text)."""
    from su2plaq.spinnet import walk

    table = walk.coupling_table(enc)
    codes = sorted(table)
    bright = [c for c in codes if c >> 4 == 0]
    cls = {2.0: 0, 0.5: 0, 1.0: 0}
    for k in range(len(enc.labels)):
        d = int(enc._codes[k]) & 0xFF
        if d >> 4 == 0 and d & 1 == 0:
            cls[abs(table[d])] += 1
    pair_2k: dict[str, int] = {}
    for c in bright:
        if c < (c ^ walk.FLIP):
            key = str(int(round(2.0 * table[c])))
            pair_2k[key] = pair_2k.get(key, 0) + 1
    pair_2k["0"] = sum(1 for c in codes if c >> 4 != 0 and table[c] == 0.0)
    ev = np.linalg.eigvalsh(enc.h_magnetic())
    two_lam = np.round(2.0 * ev).astype(int)
    if np.abs(2.0 * ev - two_lam).max() > 1e-9:
        raise RuntimeError("H_B has an eigenvalue that is not a multiple of 1/2")
    spectrum = [(l / 2.0, int((two_lam == l).sum())) for l in (-4, -2, -1, 0, 1, 2, 4)]
    return {"card_inner_labels": len(codes), "card_bright_labels": len(bright), "card_dark_labels": len(codes) - len(bright),
            "card_bright_pairs": len(bright) // 2, "card_states_spinnet": len(enc.labels), "mult_two": cls[2.0],
            "mult_one": cls[1.0], "mult_half": cls[0.5], "couplings_2k": pair_2k, "spectrum": spectrum,
            "n_eigs": int(len(ev))}


def structure_facts(root=None) -> dict:
    """Kernel-checked facts about the spin-network problem for the task specification:
    {"facts": [{"name", "value", "proved_by": "decide", "theorem": "Su2Plaq.SpinNet.<name>", "file", "note"}...], "provenance": {...}}.
    Values are read from the Lean statements (`by decide`, no native_decide) and must agree with the Python encoding."""
    from su2plaq.compress.spec import get_encoding

    install()
    root = _root(root)
    enc = get_encoding(ENC)
    num = _numeric_counts(enc)
    texts = {n: _lean_text(n, root) for n in ("Counts", "Recoupling", "Spectrum", "Semantics")}
    for n, (rel, src) in texts.items():
        if "native_decide" in src or "sorry" in src:
            raise RuntimeError(f"{rel} contains native_decide or sorry: its theorems are not kernel-checked structure facts")
    facts = []

    def add(name, value, theorem_file, note, theorem=None):
        rel = texts[theorem_file][0]
        facts.append({"name": name, "value": value, "proved_by": "decide", "theorem": f"Su2Plaq.SpinNet.{theorem or name}",
                      "file": rel, "note": note})

    for name, fname, note in _COUNT_FACTS:
        rel, src = texts[fname]
        value = _lean_nat(src, name, rel)
        if value != num[name]:
            raise RuntimeError(f"{name}: Lean statement says {value}, the Python encoding gives {num[name]}")
        add(name, value, fname, note)
    rel, src = texts["Spectrum"]
    mult = _lean_nat_list(src, "eig_mult", rel)
    if mult != [m for _, m in num["spectrum"]] or sum(mult) != num["card_states_spinnet"] or num["n_eigs"] != sum(mult):
        raise RuntimeError(f"eig_mult: Lean says {mult}, the Python H_B spectrum gives {[m for _, m in num['spectrum']]}")
    add("spectrum_multiplicities", [[lam, m] for lam, m in num["spectrum"]], "Spectrum",
        "multiplicity of each eigenvalue of H_B (= the spectrum of K block by block) on the 433 states, as "
        "[eigenvalue, multiplicity]", theorem="eig_mult")
    rel, src = texts["Recoupling"]
    _statement(src, "coupling_from_6j", rel)
    add("couplings_2k", num["couplings_2k"], "Recoupling",
        "2K from the Racah 6j symbols on all 47 inner codes; the map is 2K -> number of bright pairs with that coupling "
        "('0': number of dark codes, K = 0). K = -2 (0000<->1111), -1/2 (0101<->1010), +1 (six pairs)",
        theorem="coupling_from_6j")
    rel, src = texts["Semantics"]
    st = _statement(src, "ub_exact_all_codes", rel)
    if not st.endswith("= true"):
        raise RuntimeError(f"ub_exact_all_codes in {rel} does not have the shape `... = true`")
    add("ub_exact_semantics", True, "Semantics",
        "the exact semantics of the reference U_B circuit equals exp(-i beta K) of every valid inner code, for all beta",
        theorem="ub_exact_all_codes")
    return {"facts": facts,
            "provenance": {"lean_files": {rel: hashlib.sha256(src.encode()).hexdigest() for rel, src in texts.values()},
                           "values_from": "Lean theorem statements, cross-checked against the Python encoding",
                           "trust": "kernel-checked (by decide, standard axioms only)"}}


def _structure_markdown(facts: dict) -> str:
    lines = []
    for f in facts["facts"]:
        val = f["value"]
        if f["name"] == "spectrum_multiplicities":
            val = ", ".join(f"{lam:g}: {m}" for lam, m in val)
            val = f"{{{val}}} (eigenvalue: multiplicity)"
        elif f["name"] == "couplings_2k":
            val = "{" + ", ".join(f"2K = {k}: {n}" for k, n in val.items()) + "}"
        lines.append(f"- `{f['name']}` = {val} (proved by {f['proved_by']}, {f['theorem']}) -- {f['note']}")
    return ("## Proved structure (Lean)\n\n"
            "Machine-checked facts about the problem (Lean 4, kernel-checked by `decide`); the numerical evaluator remains ground "
            "truth. Here K is the real symmetric coupling of the 47 admissible data codes, U_B = exp(-i beta K) acts on the "
            "data register, and a code is *bright* when its four corner bits are 0, *dark* otherwise.\n\n"
            + "\n".join(lines) + "\n")


# --------------------------------------------------------------------------------------------------- spec text (§1)
_TOOL_REWRITES = (
    ("`python -m su2plaq.compress.run_candidate <program.py> --encoding {enc} --kind {kind} --trial`",
     "`python -m su2plaq.spinnet.loop candidate <program.py> --trial`"),
    ("or `--full`.", "or `--full` (`--order 2` for the second-order step)."),
    ("`python -m su2plaq.compress.oracle --encoding {enc} --kind {kind} [--column j]",
     "`python -m su2plaq.spinnet.loop oracle [--column j]"),
)


def render_spec(sp=None) -> str:
    """The laptop `TaskSpec.render()` with the "Proved structure (Lean)" section replaced by the spin-network facts and the
    tool commands rewritten to `python -m su2plaq.spinnet.loop candidate|oracle`."""
    install()
    sp = sp if sp is not None else spec()
    text = sp.render()
    head, tools = "## Proved structure (Lean)", "## Tools"
    i, j = text.find(head), text.find(tools)
    if i < 0 or j < i:
        raise RuntimeError("laptop module shape changed: TaskSpec.render() lost its 'Proved structure (Lean)' / 'Tools' sections")
    text = text[:i] + _structure_markdown(structure_facts()) + "\n" + HEADLINE_RULE_SECTION + "\n" + text[j:]
    for old, new in _TOOL_REWRITES:
        old = old.format(enc=sp.encoding, kind=sp.kind)
        if text.count(old) != 1:
            raise RuntimeError(f"laptop module shape changed: the tool text {old!r} was not found exactly once in TaskSpec.render()")
        text = text.replace(old, new)
    if "su2plaq.compress.run_candidate" in text or "--encoding" in text:
        raise RuntimeError("laptop module shape changed: a laptop tool command remains in the rendered spin-network spec")
    return text


def write_spec(path=None, root=None) -> pathlib.Path:
    """Write `render_spec()` to <root>/compress/specs/spinnet-step.md (or `path`)."""
    p = pathlib.Path(path) if path is not None else _root(root) / "compress" / "specs" / f"{ENC}-{KIND}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_spec())
    return p


def _reference_circuit(s):
    """The reference circuit of the spin-network encoding for the spec `s` (kind, order, angles), outer register present."""
    from su2plaq.circuits import spinnet as C

    if s.kind == "UE":
        return C.build_UE(s.alpha, with_outer=True)
    if s.kind == "UB":
        return C.build_UB(s.beta, with_outer=True)
    return C.build_step(s.alpha, s.beta, s.order, with_outer=True)


def general_program_path(sp, root=None) -> pathlib.Path:
    """<root>/compress/programs/spinnet/seed/000-general.py: the general circuit as an angle-linear Builder program (generated
    on first use through the laptop's `program_source`, afterwards immutable)."""
    from su2plaq.compress import baselines as BL

    install()
    path = _root(root) / "compress" / "programs" / sp.encoding / BL.SEED_FAMILY / f"000-{BL._stem(sp)}.py"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BL.program_source(_reference_circuit, sp, summary=(
            f"the reference circuit of the {sp.encoding} encoding ({sp.kind}) expressed through the Builder; every angle is a "
            "linear function of spec.alpha / spec.beta.")))
    return path


# ------------------------------------------------------------------------------------------------ seeds (step 4.2)
SKELETONS = ("pairs9", "flags4", "flags5", "flags6")
PAULO_SOURCE = "paulo15"
V2_PREFIX = "spinnet_v2:"


@dataclass
class SeedCircuit:
    qc: object
    source: str
    fixed_angle: bool
    alpha: float | None
    beta: float | None
    kind: str
    can_be_parent: bool
    gauge: np.ndarray | None = None      # +-1 over the 433 states for paulo15, else None


def _v2_circuit(skeleton: str, s):
    """The vendored spinnet_v2 U_B skeleton behind OUR electric layer (electric layer first; order 2: half layers on both sides),
    angles solved from K at build time, outer register present.  UB kind: the skeleton alone."""
    from qiskit import QuantumCircuit

    from su2plaq.circuits import spinnet as C

    pl = C.trotter_v2_circuit(skeleton, s.beta, with_outer=True)
    if s.kind == "UB":
        return pl
    qc = QuantumCircuit(*pl.qregs, name=f"{skeleton}-{s.kind}")
    half = s.alpha if s.order == 1 else s.alpha / 2
    qc.compose(C.build_UE(half, with_outer=True), qubits=list(range(16)), inplace=True)
    qc.compose(pl, inplace=True)
    if s.order == 2:
        qc.compose(C.build_UE(half, with_outer=True), qubits=list(range(16)), inplace=True)
    return qc


def _gauge_of_paulo(enc, beta: float):
    """(+-1 vector over the 433 states, residual, inner-block leak) of Paulo's 15-qubit file against exp(-i beta K): the real diagonal
    gauge D over the 47 inner codes found by `align_inner_block` (M3-P1: one -1 per bright pair), extended to every state by the
    data part of its code (the file never touches the outer register)."""
    from su2plaq.circuits import spinnet as C
    from su2plaq.encodings.spinnet import align_inner_block
    from su2plaq.evaluate.sparse_sim import encoded_block, run_batch

    codes = enc.inner_codes()
    M, leak = encoded_block(run_batch(C.paulo_circuit(), codes), codes, len(codes), code_mask=(1 << 8) - 1)
    D, res, _phase = align_inner_block(M, enc.inner_target("UB", None, beta))
    if D is None:
        raise RuntimeError("Paulo's inner block differs from exp(-i beta K) in modulus: no gauge exists")
    if np.abs(np.asarray(D).imag).max() > 1e-12 or np.abs(np.abs(D) - 1.0).max() > 1e-12:
        raise RuntimeError("the gauge of Paulo's file is not a real +-1 diagonal")
    return np.sign(np.asarray(D).real)[enc._pos_of_k].astype(float), float(res), float(np.max(leak))


def gauge_minus_codes(gauge) -> list[int]:
    """Sorted data codes (8 bits) of the inner codes on which the gauge is -1 (M3-P1: {8..15})."""
    from su2plaq.compress.spec import get_encoding

    enc = get_encoding(ENC)
    return sorted({int(c) & 0xFF for c, g in zip(enc._codes, np.asarray(gauge)) if g < 0})


def import_seed(sp, source: str):
    """SeedCircuit for "paulo15" (fixed angle beta = 0.05, kind UB, never a parent, with the sign gauge) and
    "spinnet_v2:pairs9|flags4|flags5|flags6" (step seeds at the spec's angles, parent-able); a reason string for the 12-qubit
    sources; ValueError for unknown names."""
    from su2plaq.circuits import spinnet as C
    from su2plaq.compress.spec import get_encoding

    install()
    enc = get_encoding(ENC)
    if source == PAULO_SOURCE:
        qc = C.paulo_circuit(with_outer=True)
        beta = float(qc.metadata["beta"])
        gauge, _res, _leak = _gauge_of_paulo(enc, beta)
        return SeedCircuit(qc=qc, source=source, fixed_angle=True, alpha=None, beta=beta, kind="UB", can_be_parent=False, gauge=gauge)
    if source.startswith(V2_PREFIX):
        skel = source[len(V2_PREFIX):]
        if skel not in SKELETONS:
            raise ValueError(f"unknown spinnet_v2 skeleton {skel!r}; known: {list(SKELETONS)}")
        if sp.kind == "UE":
            return f"{source} is a magnetic-layer circuit; it has no electric (U_E) part"
        return SeedCircuit(qc=_v2_circuit(skel, sp), source=source, fixed_angle=False, alpha=sp.alpha, beta=sp.beta, kind=sp.kind,
                           can_be_parent=True)
    if source in ("paulo34", "lean22", "lean22_v2"):
        reason = enc.import_map(source)
        if not isinstance(reason, str):
            raise RuntimeError(f"import_map({source!r}) of the spin-network encoding no longer returns a reason string")
        return reason
    raise ValueError(f"unknown seed source {source!r}")


def seed_program_source(sp, source: str) -> str:
    """Angle-linear program text (laptop `program_source`) of a parent-able seed."""
    from su2plaq.compress import baselines as BL

    seed = import_seed(sp, source)
    if isinstance(seed, str):
        raise ValueError(seed)
    if not seed.can_be_parent:
        raise ValueError(f"{source} is a fixed-angle seed and cannot be written as an angle-linear program")
    skel = source[len(V2_PREFIX):]
    return BL.program_source(lambda s: _v2_circuit(skel, s), sp, summary=(
        f"the vendored su2qc-trotter spinnet_v2 {skel} skeleton for U_B (angles solved from K, route-B signs) behind our electric "
        "layer; every angle is a linear function of spec.alpha / spec.beta."))


def evaluate_seed(sp, seed: SeedCircuit, mode: str = "full"):
    """A fixed-angle seed (Paulo's file) is judged at its OWN angle and kind with the spec's exact tolerances (its p gates are
    exact) against the target regauged with seed.gauge (`SpinNet.regauge`), without alternate angles; the message records the
    gauge.  A parent-able seed goes through `evaluate_circuit` with the alternate-angle circuits rebuilt at sp.alt_angles."""
    from su2plaq.compress import evaluate as E
    from su2plaq.compress import oracle
    from su2plaq.compress.spec import TaskSpec, get_encoding

    install()
    if not seed.fixed_angle:
        alts = None
        if mode == "full":
            skel = seed.source[len(V2_PREFIX):]
            alts = [_v2_circuit(skel, sp.with_angles(a, b)) for a, b in sp.alt_angles]
        return E.evaluate_circuit(seed.qc, sp, mode, alt_circuits=alts)
    from su2plaq.evaluate.evaluator import evaluate

    if seed.gauge is None:
        raise ValueError("a fixed-angle spin-network seed needs its sign gauge (SeedCircuit.gauge)")
    t0 = time.time()
    s2 = TaskSpec(**{**sp.to_dict(), "kind": seed.kind, "alpha": sp.alpha if seed.alpha is None else seed.alpha,
                     "beta": seed.beta, "alt_angles": ()})
    enc = get_encoding(ENC)
    g = np.asarray(seed.gauge, dtype=float)
    Vg = g[:, None] * oracle.target(s2) * g[None, :]                      # == enc.regauge(V, D) for a real D
    v = evaluate(seed.qc, enc, Vg, tol_err=s2.tol_err, tol_gauss=s2.tol_gauss, gauss=True, method="physical", engine="auto",
                 cap=sp.support_cap)
    valid, reason = E._classify(v, E._gate_violations(seed.qc))
    try:
        from su2plaq.compress.metrics import metrics

        met = metrics(seed.qc, s2, measured=(mode == "full" and valid))
    except ValueError:
        met = None
    minus = gauge_minus_codes(g)
    return E.ProgramResult(valid, reason, v, [], True, met, "", time.time() - t0, [], f"external seed {seed.source}", mode,
                           f"fixed angle beta={seed.beta}, kind {seed.kind}; exact-angle tolerances {s2.tol_err:g}; target regauged "
                           f"with the sign gauge D (n_minus {len(minus)} inner codes with -1: {minus})",
                           spec_sha256=s2.sha256(), seeds=E._seeds(s2))


# ----------------------------------------------------------------------------------------------- rounds (step 4.3)
_SEED_FILES = (("general", None), ("spinnet_v2_pairs9", "001-spinnet_v2_pairs9.py"), ("spinnet_v2_flags4", "002-spinnet_v2_flags4.py"),
               ("spinnet_v2_flags5", "003-spinnet_v2_flags5.py"), ("spinnet_v2_flags6", "004-spinnet_v2_flags6.py"),
               ("general+polish", "010-general_polish.py"), ("qiskit_l3", "011-qiskit_l3.py"))
_LABEL_OF_STEM = {"000-general": "general", "001-spinnet_v2_pairs9": "spinnet_v2_pairs9", "002-spinnet_v2_flags4": "spinnet_v2_flags4",
                  "003-spinnet_v2_flags5": "spinnet_v2_flags5", "004-spinnet_v2_flags6": "spinnet_v2_flags6",
                  "010-general_polish": "general+polish", "011-qiskit_l3": "qiskit_l3"}


def _qiskit_l3(qc, seed: int = 12345, window: int | None = None):
    """The laptop's windowed level-3 baseline (`baselines.qiskit_l3`) applied to OUR general circuit (the laptop function builds
    twelve's circuit): windows of `L3_WINDOW` instructions, optimisation_level=3, Builder basis, idle qubits not assumed clean."""
    from qiskit import QuantumCircuit, transpile

    from su2plaq.compress import baselines as BL
    from su2plaq.compress import builder as B

    window = BL.L3_WINDOW if window is None else window
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
        out.compose(t, qubits=[out.qubits[q] for q in qs], inplace=True)
    return out


def _qiskit_l3_whole(qc, seed: int = 12345):
    from qiskit import transpile

    from su2plaq.compress import builder as B

    return transpile(qc, basis_gates=sorted(B.BASIS), optimization_level=3, seed_transpiler=seed, qubits_initially_zero=False)


_FIT_POINTS = ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00), (0.50, 0.50), (0.20, 1.30))


def _linear_in_angles(circuit_fn, sp):
    """`circuit_fn` with its angles replaced by their exact linear form c_a * alpha + c_b * beta, fitted at generic angle pairs.
    The laptop's `program_source` fits at (alpha, beta) = (0,0), (1,0), (0,1), where an optimising transpile (the Qiskit level-3
    baseline) deletes the zero-angle rotations and changes the skeleton; at generic pairs the skeleton is stable.  Raises
    ValueError if the skeleton differs between the pairs or an angle is not (to 1e-10) linear homogeneous in (alpha, beta)."""
    from qiskit import QuantumCircuit

    from su2plaq.compress import baselines as BL

    gls = [BL._gate_list(circuit_fn(sp.with_angles(a, b))) for a, b in _FIT_POINTS]
    skel = [[(n, q) for n, _p, q in g] for g in gls]
    if any(k != skel[0] for k in skel):
        raise ValueError("the circuit skeleton depends on the angles at the generic fit points; no angle-linear program exists")
    A = np.array(_FIT_POINTS)
    coeffs = {}
    for k, (name, params, _q) in enumerate(gls[0]):
        if params:
            y = np.array([g[k][1][0] for g in gls])
            c = np.linalg.lstsq(A, y, rcond=None)[0]
            if np.abs(A @ c - y).max() > 1e-10:
                raise ValueError(f"angle of gate {k} ({name}) is not linear homogeneous in (alpha, beta)")
            coeffs[k] = (float(c[0]), float(c[1]))
    base = circuit_fn(sp)

    def fn(s):
        out = QuantumCircuit(*base.qregs)
        for k, inst in enumerate(base.data):
            op = inst.operation
            if k in coeffs:
                op = type(op)(coeffs[k][0] * s.alpha + coeffs[k][1] * s.beta)
            out.append(op, [base.find_bit(q).index for q in inst.qubits])
        return out
    return fn


def _polished(s):
    from su2plaq.compress.passes import polish

    return polish(_reference_circuit(s), s)[0]


def seed_programs(sp, root=None) -> list[tuple[str, pathlib.Path]]:
    """Write (once; the files are immutable afterwards) and return [(label, path)] of the seven round-0 candidate programs under
    <root>/compress/programs/spinnet/seed/."""
    from su2plaq.compress import baselines as BL

    install()
    gp = general_program_path(sp, root)
    out = [("general", gp)]
    texts = {"general+polish": lambda: BL.program_source(_polished, sp, summary="the reference circuit after the deterministic polish passes."),
             "qiskit_l3": lambda: BL.program_source(_linear_in_angles(lambda s: _qiskit_l3(_reference_circuit(s)), sp), sp,
                                                    summary=f"Qiskit level-3 transpile (windows of {BL.L3_WINDOW}) of the reference circuit.")}
    for label, fname in _SEED_FILES[1:]:
        f = gp.parent / fname
        if not f.exists():
            f.write_text(seed_program_source(sp, f"{V2_PREFIX}{label[len('spinnet_v2_'):]}") if label.startswith("spinnet_v2_")
                         else texts[label]())
        out.append((label, f))
    return out


def _annotate(root: pathlib.Path, round: int, *, relabel: bool = False, external=None, lean_general=None, extra_lean_seconds: float = 0.0):
    """Append our provenance key to results/compress/spinnet/round-rrr.json (and, for round 0, the labels, the external rows and
    the extra Lean record)."""
    import json

    f = root / "results" / "compress" / ENC / f"round-{round:03d}.json"
    d = json.loads(f.read_text())
    d["spinnet"] = {"code_sha256": code_hash(), "shim": sorted(INSTALLED)}
    if relabel:
        for c in d["candidates"]:
            c["label"] = _LABEL_OF_STEM.get(pathlib.Path(c["program_path"]).stem, c["label"])
    if external is not None:
        d["external"] = list(external)
    if lean_general is not None:
        for c in d["candidates"]:
            if c["label"] == "general":
                c["lean"] = lean_general
    d["lean_seconds"] = float(d.get("lean_seconds", 0.0)) + extra_lean_seconds
    f.write_text(json.dumps(d, indent=1, default=str))
    return d


def _external_rows(sp) -> list[dict]:
    from su2plaq.compress.metrics import metrics

    rows = []
    try:
        rows.append({"source": "qiskit_l3_whole", "valid": False, "reason": "unverifiable: Qiskit's whole-circuit level-3 transpile "
                     "hoists Hadamards (more than 1e6 amplitudes per input), beyond the exact sparse engine",
                     "metrics": metrics(_qiskit_l3_whole(_reference_circuit(sp)), sp, measured=False)})
    except (ValueError, RuntimeError) as exc:
        rows.append({"source": "qiskit_l3_whole", "valid": False, "reason": f"counts unavailable: {exc}"})
    seed = import_seed(sp, PAULO_SOURCE)
    rs = evaluate_seed(sp, seed, "full")
    minus = gauge_minus_codes(seed.gauge)
    rows.append({"source": seed.source, "fixed_angle": True, "kind": seed.kind, "beta": seed.beta, "valid": rs.valid, "reason": rs.reason,
                 "metrics": rs.metrics, "op_norm_error": getattr(rs.verdict, "op_norm_error", None),
                 "leak_amplitude": getattr(rs.verdict, "leak_amplitude", None), "gauss_residual": getattr(rs.verdict, "gauss_residual", None),
                 "certified": getattr(rs.verdict, "certified", None), "message": rs.message, "gauge_minus_codes": minus,
                 "n_minus": len(minus)})
    return rows


def seed_round(root=None, lean: bool = True, dry_run: bool = False) -> dict:
    """Round 0 (prompts/104 §1): the seven seed programs through the laptop's `round.run_round` (round 0 with an explicit program
    list = the proposals branch: archive, feedback, attempts, synthesised re-verification and Lean certificate of the best are the
    laptop's), then the labels, the external rows (qiskit_l3_whole, paulo15), our provenance key and the Lean certificate of the
    `general` seed are added to results/compress/spinnet/round-000.json.
    -> {"round": 0, "n_valid", "n_invalid", "best_key", "entries", "lean_seconds"}."""
    from su2plaq.compress import archive as A
    from su2plaq.compress import round as R

    install()
    root = _root(root)
    sp = spec()
    progs = seed_programs(sp, root)
    info = R.run_round(ENC, KIND, 0, evaluate=True, dry_run=dry_run, root=root, proposals=[str(p) for _, p in progs], lean=lean)
    lean_general, extra = None, 0.0
    if lean:
        arch = A.Archive.load(ENC, root=root, n_alt=len(sp.alt_angles), strict=True)
        e = next((x for x in arch.entries() if pathlib.Path(x.program_path).name == "000-general.py"), None)
        if e is not None and e.lean is None:
            new, extra = R._certify(_reference_circuit(sp), sp)
            R._store_lean(e, new, root, ENC, "round 0: general seed")
            arch.save()
        lean_general = e.lean if e is not None else None
    d = _annotate(root, 0, relabel=True, external=_external_rows(sp), lean_general=lean_general, extra_lean_seconds=extra)
    info["lean_seconds"] = d["lean_seconds"]
    info["external"] = [x["source"] for x in d["external"]]
    return info


def run_round(round: int, evaluate: bool = True, dry_run: bool = False, root=None, proposals=None, lean: bool = True) -> dict:
    """Round 0: `seed_round`.  Round r >= 1: the laptop's `round.run_round("spinnet", "step", r)` after `install()` plus our
    provenance key `spinnet = {code_sha256, shim}` in results/compress/spinnet/round-rrr.json."""
    from su2plaq.compress import round as R

    install()
    if round == 0 and proposals is None:
        return seed_round(root=root, lean=lean, dry_run=dry_run)
    info = R.run_round(ENC, KIND, round, evaluate=evaluate, dry_run=dry_run, root=_root(root), proposals=proposals, lean=lean)
    _annotate(_root(root), round)
    return info


# briefs: the laptop's text with our commands (the proposer agent file is not edited; plan §9 decision 3)
def _rewrite_text(text: str, root: pathlib.Path, ideation: bool) -> str:
    """The laptop's brief text with OUR commands: every replaced snippet must occur exactly once (else the laptop text changed and
    the shim needs the planner)."""
    from su2plaq.compress import brief as BR

    pairs = [(BR._structure_pointer(root), "the section 'Proved structure (Lean)' of the specification (kernel-checked facts about "
                                          "the spin-network problem; there is no separate structure file)")]
    if ideation:
        pairs.append((f"(`python -m su2plaq.compress.oracle --encoding {ENC} --kind {KIND} ...`)",
                      "(`python -m su2plaq.spinnet.loop oracle ...`)"))
    else:
        pairs += [(f"`python -m su2plaq.compress.run_candidate <program.py> --encoding {ENC} --kind {KIND} --trial`",
                   "`python -m su2plaq.spinnet.loop candidate <program.py> --trial`"),
                  ("`--full` before you finish; the oracle: `python -m su2plaq.compress.oracle ...`",
                   "`--full` before you finish (`--order 2` for the second-order step); the oracle: "
                   "`python -m su2plaq.spinnet.loop oracle ...`")]
    for old, new in pairs:
        if text.count(old) != 1:
            raise RuntimeError(f"laptop module shape changed: brief text {old!r} found {text.count(old)} times (expected 1); the "
                               "shim of su2plaq.spinnet.loop must be amended by the planner")
        text = text.replace(old, new)
    if not ideation:                     # E3: the headline rule follows the laptop's last section ("## Output")
        if text.count("\n## Output") != 1 or "## Headline rule (track S)" in text:
            raise RuntimeError("laptop module shape changed: the round brief must contain exactly one '## Output' section and no "
                               "headline rule yet")
        text = text.rstrip("\n") + "\n\n" + HEADLINE_RULE_SECTION
    return text


def _finish_brief(path, root: pathlib.Path, ideation: bool) -> pathlib.Path:
    path = pathlib.Path(path)
    text = _rewrite_text(path.read_text(), root, ideation)
    if "su2plaq.compress.run_candidate" in text or "su2plaq.compress.oracle" in text:
        raise RuntimeError(f"laptop module shape changed: a laptop tool command remains in {path}")
    path.write_text(text)
    write_spec(root=root)                  # the laptop's brief regenerated the spec file with its own text
    return path


def make_ideation_brief(root=None) -> pathlib.Path:
    """compress/briefs/spinnet/ideation.md: spec only (laptop text) with our oracle command and the spin-network facts."""
    from su2plaq.compress import brief as BR

    install()
    root = _root(root)
    return _finish_brief(BR.make_ideation_brief(ENC, KIND, root), root, True)


def make_brief(round: int, family: str, root=None) -> pathlib.Path:
    """compress/briefs/spinnet/round-rrr-<family>.md: laptop brief with `python -m su2plaq.spinnet.loop candidate|oracle` and the
    spin-network facts; the spec file the laptop regenerated is rewritten with ours."""
    from su2plaq.compress import brief as BR

    install()
    root = _root(root)
    return _finish_brief(BR.make_brief(ENC, KIND, round, family, root), root, False)


# ------------------------------------------------------------------------------------------ headline rule (E3)
def angle_set_sha256() -> str:
    """sha256 of the repr of the locked angle pairs (identifies the set in every cache and report)."""
    return hashlib.sha256(repr(ANGLE_SET).encode()).hexdigest()


def _program_file(program_path, root=None) -> pathlib.Path:
    f = pathlib.Path(program_path)
    if f.is_absolute():
        return f
    r = _root(root)
    return r / f


def robust_metrics(program_path, sp=None, root=None) -> dict:
    """Angle-averaged cost of a program (prompts/104 §11 E3).  The program is rebuilt through our worker at the 20 pairs of
    `ANGLE_SET` (and at the nominal pair of `sp`, used for the angle-linearity test); the laptop's `metrics(measured=True)` gives
    T(1e-6) and depth_CT at every pair.  -> {"program_sha256", "angle_set_sha256", "skeleton_equal", "t_eps": [20 int],
    "depth_ct": [20 int], "t_sum", "depth_sum", "t_mean", "cx", "qubits", "angle_linear", "export_status",
    "robust_key": (cx, t_sum, 0|1, depth_sum, qubits) | None}.  `robust_key` is None when the gate skeleton changes inside the
    angle set (the laptop's "no fixed-angle tricks" rule extended to the set).  `angle_linear` is False when the Lean exporter
    answers `non_linear_angle:...` for the nominal circuit; `export_status` is the exporter's answer ("ok" or its reason text)."""
    import tempfile

    from su2plaq.compress import evaluate as E
    from su2plaq.compress import metrics as M
    from su2plaq.compress.spec import get_encoding
    from su2plaq.spinnet import lean_export

    install()
    sp = sp if sp is not None else spec()
    src = _program_file(program_path, root).read_bytes()
    specs = [sp.with_angles(a, b) for a, b in ANGLE_SET]
    circuits, _ = E._build_in_subprocess(src, [*specs, sp], E.BUILD_TIMEOUT_S)
    nominal, circuits = circuits[-1], circuits[:-1]
    skeleton_equal = len({tuple(map(tuple, E.skeleton(c))) for c in circuits}) == 1
    ms = [M.metrics(c, s, measured=True) for c, s in zip(circuits, specs)]
    t_eps = [int(m["t_eps"]) for m in ms]
    depth_ct = [int(m["depth_ct"]) for m in ms]
    with tempfile.TemporaryDirectory() as td:
        res = lean_export.export_certificate(nominal, get_encoding(ENC), sp.kind, sp.alpha, sp.beta, sp.order,
                                             pathlib.Path(td) / "angle-linearity.json")
    status = res if isinstance(res, str) else "ok"
    linear = not status.startswith("non_linear_angle")
    out = {"program_sha256": hashlib.sha256(src).hexdigest(), "angle_set_sha256": angle_set_sha256(), "skeleton_equal": skeleton_equal,
           "t_eps": t_eps, "depth_ct": depth_ct, "t_sum": sum(t_eps), "depth_sum": sum(depth_ct), "t_mean": sum(t_eps) / len(t_eps),
           "cx": int(ms[0]["cx"]), "qubits": int(ms[0]["qubits"]), "angle_linear": linear, "export_status": status}
    out["robust_key"] = ((out["cx"], out["t_sum"], 0 if linear else 1, out["depth_sum"], out["qubits"]) if skeleton_equal else None)
    return out


def _angle_set_record() -> dict:
    return {"seed": ANGLE_SET_SEED, "n": ANGLE_SET_N, "ranges": [list(r) for r in ANGLE_SET_RANGES],
            "pairs": [list(p) for p in ANGLE_SET], "sha256": angle_set_sha256()}


def _lean_status(entry):
    return (entry.lean or {}).get("status") if isinstance(entry.lean, dict) else None


def headline(root=None, refresh: bool = False) -> dict:
    """The headline entry of the archive (prompts/104 §11 E3): among the valid entries, the smallest robust key
    (CX, sum T over `ANGLE_SET`, angle-linear rank, sum depth_CT, qubits); full ties: the laptop key, then the id.  Entries whose
    skeleton changes inside the angle set have no robust key and are listed under "unrankable".  The per-entry `robust_metrics`
    are cached in results/compress/spinnet/robust.json, keyed by (id, program_sha256, angle_set_sha256) and the evaluator /
    spin-network code hashes; mismatch or `refresh` recomputes.
    -> {"id", "robust_key", "t_mean", "lean", "archive_best", "archive_best_robust_key", "ranking": [{"id", "robust_key",
    "t_mean", "lean", "laptop_key", "family", "round", "cx", "qubits", "t_nominal", "depth_mean", "angle_linear"}...] sorted,
    "unrankable": [ids]}."""
    import json

    from su2plaq.compress import archive as A
    from su2plaq.compress import provenance

    install()
    root = _root(root)
    sp = spec()
    arch = A.Archive.load(ENC, root=root, n_alt=len(sp.alt_angles), strict=True)
    valid = sorted((e for e in arch.entries() if e.valid), key=lambda e: e.id)
    best = arch.best()
    cache_file = root / "results" / "compress" / ENC / "robust.json"
    ev_sha, sp_sha, as_sha = provenance.code_hash(), code_hash(), angle_set_sha256()
    cache = {}
    if cache_file.exists() and not refresh:
        cache = json.loads(cache_file.read_text())
        if cache.get("evaluator_sha256") != ev_sha or cache.get("spinnet_code_sha256") != sp_sha \
                or cache.get("angle_set", {}).get("sha256") != as_sha:
            cache = {}
    cached = cache.get("entries", {})
    store = {"angle_set": _angle_set_record(), "evaluator_sha256": ev_sha, "spinnet_code_sha256": sp_sha, "entries": {}}
    for e in valid:
        rec = cached.get(e.id)
        if rec is None or rec.get("program_sha256") != e.program_sha256 or rec.get("angle_set_sha256") != as_sha:
            rec = robust_metrics(_program_file(e.program_path, root), sp, root=root)
            rec["laptop_key"] = [int(x) for x in e.key]
            if rec["program_sha256"] != e.program_sha256:
                raise RuntimeError(f"program file of {e.id} ({e.program_path}) differs from the archived sha256")
        store["entries"][e.id] = rec
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(store, indent=1))
        tmp.replace(cache_file)
    by_id = {e.id: e for e in valid}
    rows, unrankable = [], []
    for i, rec in store["entries"].items():
        if rec["robust_key"] is None:
            unrankable.append(i)
            continue
        e = by_id[i]
        rows.append({"id": i, "robust_key": tuple(rec["robust_key"]), "t_mean": rec["t_mean"], "lean": _lean_status(e),
                     "laptop_key": tuple(int(x) for x in e.key), "family": e.family, "round": e.round, "cx": rec["cx"],
                     "qubits": rec["qubits"], "t_nominal": int(e.key[1]), "depth_mean": rec["depth_sum"] / len(rec["depth_ct"]),
                     "angle_linear": rec["angle_linear"]})
    rows.sort(key=lambda r: (r["robust_key"], r["laptop_key"], r["id"]))
    top = rows[0] if rows else None
    best_row = next((r for r in rows if best is not None and r["id"] == best.id), None)
    return {"id": top["id"] if top else None, "robust_key": top["robust_key"] if top else None,
            "t_mean": top["t_mean"] if top else None, "lean": top["lean"] if top else None,
            "archive_best": best.id if best else None,
            "archive_best_robust_key": best_row["robust_key"] if best_row else None, "ranking": rows, "unrankable": sorted(unrankable)}


_LEAN_WORDS = {"certified": "certified", "accepted": "certified", "failed": "failed", "rejected": "failed"}


def _lean_word(status) -> str:
    return "not_run" if status is None else _LEAN_WORDS.get(status, "n_a")


def report_table(root=None) -> str:
    """Laptop `report.report_table("spinnet", "step", root)` (also writes results/compress/spinnet/summary.json) followed by the
    HEADLINE table of prompts/104 §11 E3 (GLOBAL BEST by the laptop key, HEADLINE by the robust key, best per family by the robust
    key; T_avg = T(1e-6) averaged over `ANGLE_SET`).  summary.json gains "headline" {id, robust_key, t_mean, angle_set_sha256},
    "t_avg" {id: T_avg} and `t_avg` in every lineage item."""
    import json

    from su2plaq.compress import archive as A
    from su2plaq.compress import report

    install()
    root = _root(root)
    text = report.report_table(ENC, KIND, root=root)
    h = headline(root)
    arch = A.Archive.load(ENC, root=root, n_alt=len(spec().alt_angles), strict=True)
    best = arch.best()
    by_id = {r["id"]: r for r in h["ranking"]}
    header = ["entry", "family", "round", "CX", "T nominal", "T_avg(1e-6)", "depth_CT avg", "qubits", "angle-linear", "Lean"]

    def row(label, i, e=None):
        r = by_id.get(i)
        e = e if e is not None else next(x for x in arch.entries() if x.id == i)
        if r is None:                                           # no robust key (skeleton changes inside the angle set)
            return [f"{label}{i}", e.family, e.round, int(e.key[0]), int(e.key[1]), "-", "-", int(e.key[3]), "-", _lean_word(_lean_status(e))]
        return [f"{label}{i}", r["family"], r["round"], r["cx"], r["t_nominal"], f"{r['t_mean']:.2f}", f"{r['depth_mean']:.1f}", r["qubits"],
                "yes" if r["angle_linear"] else "no", _lean_word(r["lean"])]

    rows = []
    if best is not None:
        rows.append(row("GLOBAL BEST (laptop key): ", best.id, best))
    if h["id"] is not None:
        rows.append(row("HEADLINE (robust key): ", h["id"]))
    fam_best = {}
    for r in h["ranking"]:
        fam_best.setdefault(r["family"], r["id"])
    rows += [row(f"best of family {f} (robust key): ", fam_best[f]) for f in sorted(fam_best)]
    lines = ["", "### HEADLINE (angle-averaged T, prompts/104 §11 E3)", "", "| " + " | ".join(header) + " |",
             "|" + "|".join("---" for _ in header) + "|"] + ["| " + " | ".join(str(c) for c in rw) + " |" for rw in rows]
    lines += ["", f"GLOBAL BEST is the archive's laptop-key minimum (CX, T(1e-6) at the nominal pair, depth_CT, qubits); HEADLINE is the "
              f"smallest robust key (CX, sum of T(1e-6) over the {ANGLE_SET_N} fixed random angle pairs of seed {ANGLE_SET_SEED}, "
              "angle-linear first, sum of depth_CT, qubits). T_avg = sum T / " + f"{ANGLE_SET_N}; angle set sha256 {angle_set_sha256()[:16]}."]
    if h["unrankable"]:
        lines.append("No robust key (skeleton changes inside the angle set): " + ", ".join(h["unrankable"]) + ".")
    summary_file = root / "results" / "compress" / ENC / "summary.json"
    summary = json.loads(summary_file.read_text())
    summary["headline"] = {"id": h["id"], "robust_key": list(h["robust_key"]) if h["robust_key"] else None, "t_mean": h["t_mean"],
                           "angle_set_sha256": angle_set_sha256()}
    summary["t_avg"] = {r["id"]: r["t_mean"] for r in h["ranking"]}
    for item in summary.get("lineage", []):
        item["t_avg"] = by_id[item["id"]]["t_mean"] if item["id"] in by_id else None
    summary_file.write_text(json.dumps(summary, indent=1))
    return text + "\n".join(lines) + "\n"


def certify_best(root=None) -> dict:
    """Laptop `round.certify_best("spinnet", "step", root)` after `install()` (the spin-network checker through the shim) for the
    archive's best by the laptop key, AND the headline entry (prompts/104 §11 E3) through the same `_certify` / `_store_lean` path
    when it is another entry.  -> the laptop's dict plus "headline": {"entry", "lean", "seconds", ...} (for the same entry:
    {"entry", "same_as_archive_best": True})."""
    from su2plaq.compress import archive as A
    from su2plaq.compress import round as R

    install()
    root = _root(root)
    res = R.certify_best(ENC, KIND, root=root)
    h = headline(root)
    if h["id"] is None or h["id"] == res.get("entry"):
        res["headline"] = {"entry": h["id"], "same_as_archive_best": True}
        return res
    sp = spec()
    arch = A.Archive.load(ENC, root=root, n_alt=len(sp.alt_angles), strict=True)
    e = next(x for x in arch.entries() if x.id == h["id"])
    circ, err = R._circuit_of(sp, e.program_path, e.id, None, root, expected_sha256=e.program_sha256)
    if circ is None:
        new, sec = {"status": "failed", "reason": f"cannot rebuild the headline circuit: {err}"}, 0.0
    else:
        new, sec = R._certify(circ, sp, program_file_sha256=e.program_sha256)
    before = e.lean
    R._store_lean(e, new, root, ENC, "certify_best: headline")
    arch.save()
    res["headline"] = {"entry": e.id, "lean": e.lean, "attempt": new, "kept_previous": before is not None and e.lean is before,
                       "seconds": sec}
    return res


# ------------------------------------------------------------------------------------------------------------ CLI
_USAGE = "python -m su2plaq.spinnet.loop {candidate|oracle|seed|round|brief|ideation|report|certify-best|headline|--worker} ..."


def main(argv=None) -> int:
    """`--worker <prog> <specs.json> <out.qpy> <meta.json>`: install(), then the laptop's `evaluate._worker` (audit guard, QPY round
    trip and contract checks are the laptop's).  `candidate <program.py> [--trial|--full] [--order 1|2] [--json out]` and
    `oracle [--column j] [--element i j] [--codec] [--block o]` are the laptop's `run_candidate` / `oracle` CLIs for the spin-network
    step; `seed [--no-lean] [--dry-run]`, `round --round r [--evaluate] [--dry-run] [--no-lean]`, `brief --round r --family F`,
    `ideation`, `report [--out]`, `certify-best`, `headline [--refresh]` drive the loop (all take `--root`)."""
    import argparse
    import json

    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--worker":
        if len(argv) != 5:
            raise SystemExit("usage: python -m su2plaq.spinnet.loop --worker <program> <specs.json> <out.qpy> <meta.json>")
        install()                        # heavy imports and the registration come before the worker's audit guard
        from su2plaq.compress import evaluate as E

        E._worker(*argv[1:])
        return 0
    if not argv:
        raise SystemExit(f"usage: {_USAGE}")
    cmd, rest = argv[0], argv[1:]
    install()
    if cmd == "candidate":
        from su2plaq.compress import run_candidate

        return run_candidate.main([*rest, "--encoding", ENC, "--kind", KIND])
    if cmd == "oracle":
        from su2plaq.compress import oracle

        return oracle.main(["--encoding", ENC, "--kind", KIND, *rest])
    ap = argparse.ArgumentParser(prog=f"python -m su2plaq.spinnet.loop {cmd}")
    if cmd in ("seed", "round", "brief", "ideation", "report", "certify-best", "headline"):
        ap.add_argument("--root")
    if cmd == "headline":
        ap.add_argument("--refresh", action="store_true")
    if cmd in ("seed", "round"):
        ap.add_argument("--dry-run", action="store_true")
        ap.add_argument("--no-lean", dest="lean", action="store_false", default=True)
    if cmd == "round":
        ap.add_argument("--round", type=int, required=True)
        ap.add_argument("--evaluate", action="store_true")
    if cmd == "brief":
        ap.add_argument("--round", type=int, required=True)
        ap.add_argument("--family", required=True)
    if cmd == "report":
        ap.add_argument("--out")
    if cmd not in ("seed", "round", "brief", "ideation", "report", "certify-best", "headline"):
        raise SystemExit(f"unknown subcommand {cmd!r}; usage: {_USAGE}")
    a = ap.parse_args(rest)
    if cmd == "seed":
        print(json.dumps(seed_round(a.root, lean=a.lean, dry_run=a.dry_run), indent=1, default=str))
    elif cmd == "round":
        print(json.dumps(run_round(a.round, evaluate=a.evaluate or a.round == 0, dry_run=a.dry_run, root=a.root, lean=a.lean), indent=1,
                         default=str))
    elif cmd == "brief":
        print(make_brief(a.round, a.family, a.root))
    elif cmd == "ideation":
        print(make_ideation_brief(a.root))
    elif cmd == "report":
        text = report_table(a.root)
        if a.out:
            pathlib.Path(a.out).write_text(text)
        else:
            print(text)
    elif cmd == "headline":
        print(json.dumps(headline(a.root, refresh=a.refresh), indent=1, default=str))
    else:
        print(json.dumps(certify_best(a.root), indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
