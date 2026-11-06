"""Compression of the spin-network step circuit with the laptop's loop (track S, milestone 4; prompts/104 §1, §2).

The laptop's `su2plaq.compress.*` is the machinery (evaluator, archive, briefs, report, Lean integration).  This module
only (a) registers the encoding `spinnet` in it at run time (`install`, four overrides, nothing else), (b) renders the
spin-network task specification with OUR tool commands and the spin-network Lean facts, (c) builds the round-0 seeds.

Step 4.0 created the interface (stubs raise NotImplementedError, the locked tests then fail with `PENDING:`); step 4.1
implements `install / spec / code_hash / structure_facts / render_spec / write_spec / general_program_path` and the
`--worker` entry point; the seed and round functions follow in steps 4.2 and 4.3.

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


def _todo(name: str, step: str):
    raise NotImplementedError(f"su2plaq.spinnet.loop.{name} is not built yet (prompts/104 step {step})")


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
    def _certify(circ, spec):
        """Round._certify with `spinnet` routed to the spin-network exporter/checker (Lean never changes a verdict)."""
        if spec.encoding != ENC:
            return original(circ, spec)
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
            return asdict(cert), time.time() - t0
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
        "the exact semantics of the 48-gate U_B circuit equals exp(-i beta K) of every valid inner code, for all beta",
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
    text = text[:i] + _structure_markdown(structure_facts()) + "\n" + text[j:]
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


def general_program_path(sp, root=None) -> pathlib.Path:
    """<root>/compress/programs/spinnet/seed/000-general.py: the general circuit as an angle-linear Builder program (generated
    on first use through the laptop's `program_source`, afterwards immutable)."""
    from su2plaq.circuits import spinnet as C
    from su2plaq.compress import baselines as BL

    install()

    def circuit(s):
        if s.kind == "UE":
            return C.build_UE(s.alpha, with_outer=True)
        if s.kind == "UB":
            return C.build_UB(s.beta, with_outer=True)
        return C.build_step(s.alpha, s.beta, s.order, with_outer=True)

    path = _root(root) / "compress" / "programs" / sp.encoding / BL.SEED_FAMILY / f"000-{BL._stem(sp)}.py"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BL.program_source(circuit, sp, summary=(
            f"the reference circuit of the {sp.encoding} encoding ({sp.kind}) expressed through the Builder; every angle is a "
            "linear function of spec.alpha / spec.beta.")))
    return path


# ------------------------------------------------------------------------------------------------ seeds (step 4.2)
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


def import_seed(sp, source: str):
    _todo("import_seed", "4.2")


def seed_program_source(sp, source: str) -> str:
    _todo("seed_program_source", "4.2")


def evaluate_seed(sp, seed: SeedCircuit, mode: str = "full"):
    _todo("evaluate_seed", "4.2")


# ----------------------------------------------------------------------------------------------- rounds (step 4.3)
def seed_round(root=None, lean: bool = True, dry_run: bool = False) -> dict:
    _todo("seed_round", "4.3")


def run_round(round: int, evaluate: bool = True, dry_run: bool = False, root=None, proposals=None, lean: bool = True) -> dict:
    _todo("run_round", "4.3")


def make_ideation_brief(root=None) -> pathlib.Path:
    _todo("make_ideation_brief", "4.3")


def make_brief(round: int, family: str, root=None) -> pathlib.Path:
    _todo("make_brief", "4.3")


def report_table(root=None) -> str:
    _todo("report_table", "4.3")


def certify_best(root=None) -> dict:
    _todo("certify_best", "4.3")


# ------------------------------------------------------------------------------------------------------------ CLI
def main(argv=None) -> int:
    """`--worker <prog> <specs.json> <out.qpy> <meta.json>` (step 4.1): install(), then the laptop's `evaluate._worker`
    (audit guard, QPY round trip and contract checks are the laptop's).  The other subcommands (candidate, oracle, seed,
    round, brief, ideation, report, certify-best) follow in step 4.3."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--worker":
        if len(argv) != 5:
            raise SystemExit("usage: python -m su2plaq.spinnet.loop --worker <program> <specs.json> <out.qpy> <meta.json>")
        install()                        # heavy imports and the registration come before the worker's audit guard
        from su2plaq.compress import evaluate as E

        E._worker(*argv[1:])
        return 0
    _todo("main (subcommands candidate/oracle/seed/round/brief/ideation/report/certify-best)", "4.3")


if __name__ == "__main__":
    raise SystemExit(main())
