"""Encoding registry (prompts/008 §3.1; METHODS §12).

One table, in the shared code, that says for every encoding which object, files and hooks the compression machinery uses.
Pure data and lazy lookups: importing this module imports no other project module (a hook or a factory is a "module:attr" string,
resolved with `resolve` only when it is needed).  This file is part of `provenance.EVALUATOR_FILES`: an edit of the table makes
every archive stale, so entries are added only inside the consolidation window (prompts/008 §8).

`register` changes the table of THIS process only (tests); the build worker is a fresh interpreter and sees the static table.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass


@dataclass(frozen=True)
class EncodingInfo:
    name: str
    factory: str                              # "module:attr", attr() -> the encoding object the compression code sees
    kinds: tuple = ("step", "UB", "UE")
    loop_kind: str = "step"                   # the kind whose archive exists
    evaluator_files: tuple = ()               # extra files, relative to src/su2plaq, that decide a verdict or a metric of THIS encoding
    stamp: str = "shared"                     # "shared": Entry.evaluator_sha256 = provenance.code_hash(); "encoding": = code_hash_for(name)
    gauss_in_loop: bool = True
    prune_fraction: float | None = None       # None -> evaluator.PRUNE_FRACTION
    verdict: str | None = None                # "module:attr"(qc, spec, mode, budget) -> Verdict; None -> the shared evaluator
    worker_warmup: str | None = None          # "module:attr"() run in the build worker BEFORE the audit guard is installed
    general_circuit: str | None = None        # "module:attr"(spec) -> QuantumCircuit
    seed_candidates: str | None = None        # "module:attr"(spec, root) -> [(label, program_path | None, circuit_fn | None)] for round 0
    import_seed: str | None = None            # "module:attr"(spec, source) -> SeedCircuit | reason string
    lean_certify: str | None = None           # "module:attr"(circ, spec, *, timeout, extra_provenance) -> dict | LeanCert; None -> status "n_a"
    lean_na_reason: str = ""
    render_spec: str | None = None            # "module:attr"(spec) -> str; None -> TaskSpec default text
    structure_json: str | None = None         # facts file shown to proposers, relative to the repository root
    tools: tuple | None = None                # (candidate command, oracle command) for spec and brief text; None -> the stock CLIs
    brief_note: str | None = None             # "module:attr"(encoding, kind) -> text appended to a brief
    headline: str | None = None               # "module:attr"(kind, root, refresh) -> dict; None -> the generic rule of compress/robust.py
    angle_linear: str | None = None           # "module:attr"(circuit, spec) -> (bool, str); None -> the generic linear fit


# The static table (registration order).  twelve: B1; spinnet: B3; lsh: step 8.R of prompts/401 (pure data, lazy strings;
# su2plaq/lsh/loop.py and su2plaq/spinnet/loop.py decide no verdict and are in no hash list); fuzzy_ub / fuzzy_link: B4 (their hooks live in
# fuzzy/compress_hook.py, which also hosts the unit encodings and is therefore hashed).  rishon B5 is added by its step.
_TABLE: dict = {}


def _add(info: EncodingInfo) -> None:
    _TABLE[info.name] = info


_add(EncodingInfo(
    name="twelve", factory="su2plaq.encodings.twelve:TwelveQubit",
    lean_certify="su2plaq.lean.certify:certify_circuit"))     # the twelve-qubit exporter / checker (evaluator files: all in the shared list)

_add(EncodingInfo(
    name="spinnet", factory="su2plaq.encodings.spinnet:SpinNet", kinds=("step", "UB", "UE"), loop_kind="step",
    evaluator_files=("encodings/spinnet.py", "circuits/spinnet.py", "spinnet/walk.py", "spinnet/trotter_v2.py", "spinnet/paulo.py"),
    stamp="shared", gauss_in_loop=True,
    general_circuit="su2plaq.spinnet.loop:general_circuit", seed_candidates="su2plaq.spinnet.loop:seed_candidates",
    import_seed="su2plaq.spinnet.loop:import_seed", lean_certify="su2plaq.spinnet.loop:lean_certify",
    render_spec="su2plaq.spinnet.loop:render_spec", structure_json="compress/specs/spinnet-structure.json",
    tools=("python -m su2plaq.spinnet.loop candidate", "python -m su2plaq.spinnet.loop oracle")))

_FUZZY_FILES = ("fuzzy/verify.py", "fuzzy/targets.py", "circuits/fuzzy.py", "fuzzy/compress_hook.py")
_FUZZY_HOOKS = dict(
    stamp="shared", gauss_in_loop=False,         # METHODS-fuzzy F9: every code is physical, the targets commute with the Gauss generators
    worker_warmup="su2plaq.fuzzy.compress_hook:warm_up", general_circuit="su2plaq.fuzzy.compress_hook:general_circuit",
    import_seed="su2plaq.fuzzy.compress_hook:import_seed", lean_certify=None,
    lean_na_reason="fuzzy: no exact exporter for the Lean certificate (plan 302 §0.5)",
    render_spec="su2plaq.fuzzy.compress_hook:render_spec", structure_json="compress/specs/fuzzy-structure.json",
    tools=("python scripts/m10_round.py candidate", "python scripts/m10_round.py oracle"),
    brief_note="su2plaq.fuzzy.compress_hook:brief_note")

_add(EncodingInfo(name="fuzzy_ub", factory="su2plaq.fuzzy.compress_hook:FuzzyUBTask", kinds=("UB",), loop_kind="UB",
                  evaluator_files=_FUZZY_FILES, **_FUZZY_HOOKS))
_add(EncodingInfo(name="fuzzy_link", factory="su2plaq.fuzzy.compress_hook:FuzzyLinkTask", kinds=("UE",), loop_kind="UE",
                  evaluator_files=_FUZZY_FILES, **_FUZZY_HOOKS))

_add(EncodingInfo(
    name="lsh", factory="su2plaq.encodings.lsh:LSH", kinds=("step", "UB", "UE"), loop_kind="step",
    evaluator_files=("encodings/lsh.py", "lsh/operators.py", "exact/spinnet.py", "exact/compare.py", "lsh/walk.py", "circuits/lsh.py"),
    stamp="encoding", gauss_in_loop=True,
    general_circuit="su2plaq.lsh.loop:general_circuit", seed_candidates="su2plaq.lsh.loop:seed_candidates",
    import_seed="su2plaq.lsh.loop:import_seed", lean_certify="su2plaq.lsh.loop:lean_certify",
    render_spec="su2plaq.lsh.loop:render_spec", structure_json="compress/specs/lsh-structure.json",
    brief_note="su2plaq.lsh.loop:brief_note", angle_linear="su2plaq.lsh.loop:angle_linear"))

_INSTANCES: dict = {}


def names() -> tuple:
    """Registered encoding names, in registration order."""
    return tuple(_TABLE)


def info(name: str) -> EncodingInfo:
    try:
        return _TABLE[name]
    except KeyError:
        raise ValueError(f"unknown encoding {name!r}; known: {list(names())}") from None


def lookup(name: str) -> EncodingInfo | None:
    """The entry, or None for a name that is not registered (hand-made test encodings)."""
    return _TABLE.get(name)


def resolve(dotted: str):
    """"module:attr" -> the object (importlib; attr may be dotted)."""
    mod, _, attr = dotted.partition(":")
    if not mod or not attr:
        raise ValueError(f"expected 'module:attr', got {dotted!r}")
    obj = importlib.import_module(mod)
    for part in attr.split("."):
        obj = getattr(obj, part)
    return obj


def get(name: str):
    """Cached instance of `info(name).factory` (one object per process and name)."""
    i = info(name)
    key = (i.name, i.factory)
    if key not in _INSTANCES:
        _INSTANCES[key] = resolve(i.factory)()
    return _INSTANCES[key]


def register(info: EncodingInfo, replace: bool = False) -> None:      # noqa: F811 - the parameter shadows the module function on purpose
    """Add an entry to the table of this process (tests only).  An existing name needs `replace=True`; the cached instance of a
    replaced entry is dropped."""
    if not isinstance(info, EncodingInfo):
        raise TypeError(f"expected EncodingInfo, got {type(info).__name__}")
    if info.name in _TABLE and not replace:
        raise ValueError(f"encoding {info.name!r} is already registered (replace=True to overwrite)")
    for k in [k for k in _INSTANCES if k[0] == info.name]:
        del _INSTANCES[k]
    _TABLE[info.name] = info
