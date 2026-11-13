"""LSH compression loop, LSH-owned part (prompts/401 sections 1-2, docs/METHODS-lsh.md L12-L16).

`lsh` is a registry encoding of the shared loop (step 8.R, prompts/008); this module holds only what is specific to it: the
registry hooks (seeds, task text, Lean hook, angle-linearity), the seed circuits of round 0, the stop rule and the loop
bookkeeping.  It is in NO evaluator-hash list, assigns nothing into a shared module and edits no environment variable.

Phase 0 (steps 8.0-8.1, built now): constants, `wrap_spinnet_step`, `seed_circuit`, `seed_program_source`, `stop_key`,
`improves`, `structure_facts`, `write_structure`, `BRIEF_NOTE`, `brief_note`.  Everything that needs the registry or the
prompts/008 machinery (phase 1, steps 8.2-8.4) is a stub raising NotImplementedError and is built after step 8.R."""
from __future__ import annotations

import hashlib
import pathlib
import re

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister

ROOT = pathlib.Path(__file__).resolve().parents[3]
ENC, KIND = "lsh", "step"
NOMINAL = (0.37, 0.61)
LSH_EVALUATOR_FILES = ("encodings/lsh.py", "lsh/operators.py", "exact/spinnet.py", "exact/compare.py", "lsh/walk.py", "circuits/lsh.py")
V2_SKELETONS = ("pairs9", "flags4", "flags5", "flags6")
# label -> (spin-network program file, its sha256, spin-network archive entry id); the spin-network loop is closed (prompts/104):
# its programs are immutable, so a changed pin means the planner must be told (prompts/401 section 4.5), never re-pin here.
WRAP_SOURCES = {
    "wrap_sn_headline": ("compress/programs/spinnet/F1/002-dimer-linear-corner-walk.py",
                         "750151e9ad417de7d52e4c59a203f1dc493bdea3be5742aa331533170a0ec650", "r02-F1-002"),
    "wrap_sn_r05F3": ("compress/programs/spinnet/F3/005-angle-linear-walk.py",
                      "43605421051ce5e26b85b1b5241eb02638fc5f8ad7c6297a67e7dd0e96fd22e4", "r05-F3-005"),
    "wrap_sn_r02F5": ("compress/programs/spinnet/F5/002-bright_flag_6rot.py",
                      "734a62fe58f316d6deb59561fb90cedcb04e5854f260f4d78e680eb688428f81", "r02-F5-002"),
}
SEED_FILES = (("general", "000-general.py"), ("wrap_pairs9", "001-wrap_pairs9.py"), ("wrap_flags4", "002-wrap_flags4.py"),
              ("wrap_flags5", "003-wrap_flags5.py"), ("wrap_flags6", "004-wrap_flags6.py"),
              ("wrap_sn_headline", "005-wrap_sn_headline.py"), ("wrap_sn_r05F3", "006-wrap_sn_r05F3.py"),
              ("wrap_sn_r02F5", "007-wrap_sn_r02F5.py"), ("general+polish", "010-general_polish.py"),
              ("qiskit_l3", "011-qiskit_l3.py"))
SEED_LABELS = tuple(lab for lab, _ in SEED_FILES)
CIRCUIT_SEEDS = tuple(lab for lab in SEED_LABELS if lab not in ("general+polish", "qiskit_l3"))
STOP_MAX_ROUNDS, STOP_NO_GAIN_ROUNDS, STOP_MAX_SESSIONS = 8, 3, 20
T_NOISE_PER_ROTATION = 1          # T per rotation per angle pair that tuning can extract from synthesis noise (prompts/104 E3)
N_ANGLE_PAIRS = 20

BRIEF_NOTE = (
    "**LSH note (prompts/401).** The target is the step on the full 24-qubit LSH register (12 data loop-number qubits, 12 "
    "read-only outer qubits). You are free to recode the sites or not: nothing requires the spin-network code to appear. For "
    "orientation: the cheapest known circuit is a spin-network circuit between the per-site transcoder (`cx`, `cx`, `rccx`) "
    "and its inverse; the transcoder pair alone costs 40 CX and 32 T, of which 24 CX and 32 T are four relative-phase Toffoli "
    "pairs. This loop asks how much of that is needed. Families are of two kinds: *transcoding* (a spin-network-style walk "
    "after recoding all four sites; gains come from merging or thinning the recoding) and *native* (work on the raw "
    "loop-number bits and never hold the complete spin-network code of all four sites). An ideation file must contain at "
    "least two native families. Facts you may rely on (kernel-checked, see the structure file): a code is dark iff some site "
    "has `l_nv = l_vp = 1`; on bright codes the coupling depends only on the number of set `l_nv` bits (0, 1, 2 give k = -2, "
    "+1, -1/2) and the parity of the four `l_nv` bits is unchanged by the plaquette move; every inner link bit can be read at "
    "two sites (Abelian Gauss law: `l_pn xor l_nv` at one site equals `l_pn xor l_vp` at the next); the move flips `l_pn` "
    "where `w = l_nv xor l_vp` is 0, and `l_nv`, `l_vp` where `w` is 1. A final state that breaks the Abelian Gauss law or "
    "the flux cap on a physical input makes the program invalid; intermediate states are unrestricted. Outer qubits may be "
    "used as controls only.")


def _root(root=None) -> pathlib.Path:
    return pathlib.Path(root) if root is not None else ROOT


# ------------------------------------------------------------------------------------------------------ seed circuits (8.1)
def wrap_spinnet_step(sn_qc) -> QuantumCircuit:
    """Spin-network step circuit on d[8] (+ o[8], never touched) + ancillas -> LSH circuit on d[12], o[12], ancillas:
    transcoder, the circuit on the transcoded wires (links 0, 3, 6, 9; corner bits 1, 4, 7, 10), transcoder reversed.
    ValueError if the circuit has no d[8] first register or touches its outer register."""
    from su2plaq.lsh import walk as W

    names = [r.name for r in sn_qc.qregs]
    if not names or names[0] != "d" or sn_qc.qregs[0].size != 8:
        raise ValueError("need a spin-network circuit with register d[8] first")
    n_outer = 8 if "o" in names else 0
    n_anc = sn_qc.num_qubits - 8 - n_outer
    regs = [QuantumRegister(12, "d"), QuantumRegister(12, "o")] + ([QuantumRegister(n_anc, "a")] if n_anc else [])
    qc = QuantumCircuit(*regs, name=f"lsh_{sn_qc.name}")
    wire = {i: W.LINK[i] for i in range(4)}
    wire.update({4 + c: W.CBIT[c] for c in range(4)})
    wire.update({8 + n_outer + k: 24 + k for k in range(n_anc)})

    def emit(steps):
        for st in steps:
            (qc.cx if st[0] == "cx" else qc.rccx)(*st[1:])

    emit(W.TRANSCODE)
    for ins in sn_qc.data:
        qs = [sn_qc.find_bit(q).index for q in ins.qubits]
        if any(q not in wire for q in qs):
            raise ValueError("the spin-network circuit touches its outer register: it cannot be wrapped")
        qc.append(ins.operation, [wire[q] for q in qs])
    emit(W.mirror(W.TRANSCODE))
    return qc


def _sn_program_circuit(label: str, alpha: float, beta: float, root=None):
    """The spin-network program behind `label` (sha256 checked against the pin), built at (alpha, beta)."""
    from su2plaq.compress import evaluate as E
    from su2plaq.spinnet import loop as SL

    rel, sha, _ = WRAP_SOURCES[label]
    path = _root(root) / rel
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise ValueError(f"{rel} differs from the pinned spin-network program (sha256 {sha[:12]}...)")
    return E.load_program(path).build(SL.spec().with_angles(alpha, beta)).circuit()


def seed_circuit(label: str, alpha: float, beta: float, root=None) -> QuantumCircuit:
    """Round-0 circuit of `label` at (alpha, beta), order 1, registers d[12], o[12], ancillas.  The eight circuit seeds only
    (`general+polish` and `qiskit_l3` are produced by the shared baselines).  ValueError: unknown label, or a pinned
    spin-network source whose sha256 changed."""
    from su2plaq.circuits import lsh as CL
    from su2plaq.circuits import spinnet as CS

    if label == "general":
        return CL.build_step(alpha, beta, 1, with_outer=True)
    if label.startswith("wrap_") and label[5:] in V2_SKELETONS:
        ub = CS.trotter_v2_circuit(label[5:], beta)
        sn = QuantumCircuit(*ub.qregs, name=f"step_{label[5:]}")
        for q in range(4):
            sn.p(-0.75 * alpha, q)
        sn.compose(ub, inplace=True)
        return wrap_spinnet_step(sn)
    if label in WRAP_SOURCES:
        return wrap_spinnet_step(_sn_program_circuit(label, alpha, beta, root))
    raise ValueError(f"unknown circuit seed {label!r}; known: {list(CIRCUIT_SEEDS)}")


def _seed_summary(label: str) -> str:
    if label == "general":
        return "round-0 seed: the general LSH step circuit (circuits.lsh.build_step, with_outer=True): transcoder, frame, flags, 4-rotation walk."
    if label.startswith("wrap_") and label[5:] in V2_SKELETONS:
        return (f"round-0 seed: vendored spinnet_v2 skeleton '{label[5:]}' (electric layer p(-3 alpha/4) on the four link wires, then "
                "the plaquette circuit) between the LSH transcoder and its inverse.")
    rel, sha, entry = WRAP_SOURCES[label]
    return (f"round-0 seed: spin-network program {rel} (archive entry {entry}, sha256 {sha}) between the LSH transcoder "
            "and its inverse.")


def seed_program_source(label: str, spec=None, root=None) -> str:
    """Program text (plain Builder gate list, angles fitted from the circuit and verified at the nominal and alternate pairs) of
    the circuit seed `label`; the summary names the source file / entry and its sha256.  Needs the `lsh` registry entry
    (step 8.R) through `compress.baselines.program_source`."""
    from su2plaq.compress import baselines
    from su2plaq.compress.spec import TaskSpec

    if label not in CIRCUIT_SEEDS:
        raise ValueError(f"unknown circuit seed {label!r}; known: {list(CIRCUIT_SEEDS)}")
    if spec is None:
        spec = TaskSpec(encoding=ENC, kind=KIND, alpha=NOMINAL[0], beta=NOMINAL[1])
    return baselines.program_source(lambda sp: seed_circuit(label, sp.alpha, sp.beta, root), spec, summary=_seed_summary(label))


# ------------------------------------------------------------------------------------------------------ stop rule (8.1)
def stop_key(rec: dict) -> tuple:
    return (rec["cx"], rec["t_sum"], rec["rho"], rec["qubits"])


def improves(new: dict | None, old: dict | None) -> bool:
    """Stop-rule comparison of two headline records {"cx","t_sum","rho","qubits","n_rot","t_fixed"} (prompts/401 section 1.6,
    METHODS-lsh L14): lexicographic on (cx, t_sum, rho, qubits); with cx, n_rot and t_fixed unchanged a change of t_sum of at
    most 20 * n_rot is a tie decided by (rho, qubits); the first headline always improves, a missing one never does."""
    if new is None:
        return False
    if old is None:
        return True
    same_structure = all(new[k] == old[k] for k in ("cx", "n_rot", "t_fixed"))
    if same_structure and abs(new["t_sum"] - old["t_sum"]) <= N_ANGLE_PAIRS * T_NOISE_PER_ROTATION * new["n_rot"]:
        return (new["rho"], new["qubits"]) < (old["rho"], old["qubits"])
    return stop_key(new) < stop_key(old)


# ------------------------------------------------------------------------------------------------------ Lean facts (8.1)
_LEAN_DIR = pathlib.Path("lean") / "Su2Plaq" / "LSH"
# (name, file, kind, note); the value of every fact is read from the theorem statement in the Lean source and cross-checked
# against the Python encoding; a disagreement raises (no value is typed into this module).
_FACTS = (
    ("card_site_codes", "Counts", "nat", "valid loop-number codes of one site (the flux cap: virtual spin at most 1)"),
    ("card_inner_codes", "Counts", "nat", "inner codes: four valid sites obeying the Abelian Gauss law on the four inner links"),
    ("card_bright_codes", "Counts", "nat", "inner codes on which the plaquette coupling is non-zero"),
    ("card_dark_codes", "Counts", "nat", "inner codes on which the plaquette coupling is zero"),
    ("card_states_lsh", "Counts", "nat", "physical states = valid data codes with a valid outer-site pattern"),
    ("card_bright_states", "Counts", "nat", "physical states whose inner code is bright"),
    ("site_valid_list", "Counts", "list", "the five valid site codes (bit 0 = l_pn, bit 1 = l_nv, bit 2 = l_vp)"),
    ("inner_codes_from_rules", "Facts", "bool", "the 47 inner codes are exactly the codes cut out by the flux cap and the Abelian Gauss law"),
    ("coupling_zero_iff_dark", "Facts", "bool", "the coupling is zero exactly on dark codes"),
    ("dark_site_is_and", "Facts", "bool", "a site is dark iff l_nv AND l_vp are both set (one AND of raw bits)"),
    ("coupling_by_y_weight", "Facts", "map", "on bright codes 2K depends only on the number of set l_nv bits: {number of set l_nv bits: 2K}"),
    ("link_bit_two_ways", "Facts", "bool", "every inner link bit is readable at two sites: l_pn xor l_nv at one site = l_pn xor l_vp at the next"),
    ("move_per_site", "Facts", "move", "the plaquette move flips l_pn where w = l_nv xor l_vp is 0 and l_nv, l_vp where w is 1; value: the site XOR pattern {w=0, w=1}"),
    ("y_parity_invariant", "Facts", "bool", "the parity of the four l_nv bits is unchanged by the move and equals [2K = +2]"),
    ("eight_differences", "Facts", "nat", "the eight difference vectors (code XOR partner) of the move are pairwise different: no CNOT-only frame exists"),
    ("transcode_into_spinnet", "Circuit", "bool", "the per-site transcoder maps the 47 LSH inner codes onto valid spin-network codes"),
    ("coupling_matches_spinnet", "Circuit", "bool", "the LSH coupling table equals the spin-network coupling on the transcoded codes"),
)


def _statement(src: str, theorem: str, file: str) -> str:
    """Text between `theorem <name>` and `:= by decide` (whitespace collapsed); RuntimeError if absent."""
    m = re.search(rf"^theorem {re.escape(theorem)}\b(.*?):=\s*by\s+decide\b", src, re.M | re.S)
    if m is None:
        raise RuntimeError(f"theorem {theorem} with proof `by decide` not found in {file}")
    return " ".join(m.group(1).split())


def _numeric_cross_check(enc) -> dict:
    """The structural facts recomputed from the production Python objects (independent of the Lean text)."""
    from su2plaq.lsh import operators as O
    from su2plaq.lsh import walk as W

    codes = [int(c) for c in enc.inner_codes()]
    table, ptab = W.coupling_table(enc), W.partner_table(enc)
    bit = lambda x, k: (x >> k) & 1
    bright = [x for x in codes if x in ptab]
    by_weight: dict = {}
    w0, w1 = set(), set()
    for x in bright:
        sy = sum(bit(x, 3 * c + 1) for c in range(4))
        by_weight.setdefault(str(sy), set()).add(int(round(2 * table[x])))
        d = x ^ ptab[x]
        for c in range(4):
            (w1 if bit(x, 3 * c + 1) ^ bit(x, 3 * c + 2) else w0).add((d >> (3 * c)) & 7)
    if any(len(v) != 1 for v in by_weight.values()) or len(w0) != 1 or len(w1) != 1:
        raise RuntimeError("the coupling / move structure of the Python encoding is not the proved one")
    return {"n_inner": len(codes), "n_bright": len(bright), "n_physical": len(enc.labels),
            "site_valid": [s for s in range(8) if O.site_valid(s)],
            "by_weight": {k: next(iter(v)) for k, v in by_weight.items()}, "w0": next(iter(w0)), "w1": next(iter(w1)),
            "n_outer_site_patterns": len({int(c) >> 12 for c in O.physical_codes()}),
            "n_differences": len({x ^ ptab[x] for x in bright})}


def _transcoder_overhead() -> dict:
    """CX and fixed T of the transcoder pair, measured: an empty spin-network circuit wrapped by the transcoder."""
    from su2plaq.metrics.logical import logical_metrics

    lm = logical_metrics(wrap_spinnet_step(QuantumCircuit(QuantumRegister(8, "d"))))
    return {"cx": int(lm["cx"]), "t_fixed": int(lm["t_fixed"])}


def structure_facts(root=None) -> dict:
    """Kernel-checked facts about the LSH problem for the task specification:
    {"facts": [{"name", "value", "proved_by": "decide"|"numerical", "theorem", "file", "note"}...], "provenance": {...}}.
    Values are read from the Lean statements (`by decide`, no native_decide) of lean/Su2Plaq/LSH/{Counts,Facts,Circuit}.lean and
    cross-checked against the Python encoding; the two `numerical` facts are measured."""
    from su2plaq.encodings.lsh import LSH

    root = _root(root)
    texts = {}
    for n in ("Counts", "Facts", "Circuit"):
        rel = (_LEAN_DIR / f"{n}.lean").as_posix()
        p = root / rel
        if not p.exists():
            raise RuntimeError(f"Lean source {rel} not found under {root}")
        src = p.read_text()
        if "native_decide" in src or "sorry" in src:
            raise RuntimeError(f"{rel} contains native_decide or sorry: its facts are not kernel-checked")
        texts[n] = (rel, src)
    num = _numeric_cross_check(LSH())
    facts = []
    for name, fname, kind, note in _FACTS:
        rel, src = texts[fname]
        st = _statement(src, name, rel)
        if kind == "nat":
            m = re.search(r"=\s*(\d+)\s*$", st)
            if m is None:
                raise RuntimeError(f"theorem {name} in {rel} does not have the shape `... = <number>`")
            value = int(m.group(1))
        elif kind == "list":
            m = re.search(r"=\s*\[([0-9,\s]+)\]\s*$", st)
            if m is None:
                raise RuntimeError(f"theorem {name} in {rel} does not have the shape `... = [n, n, ...]`")
            value = [int(x) for x in m.group(1).replace(" ", "").split(",")]
        elif kind == "map":                          # `... = (if S = 0 then a else if S = 1 then b else c)`
            ms = re.findall(r"=\s*(\d+)\s*then\s*(-?\d+)", st)
            me = re.search(r"else\s*(-?\d+)\)?\s*(?:∧|$)", st)
            if len(ms) != 2 or me is None:
                raise RuntimeError(f"theorem {name} in {rel} does not have the shape `if S = 0 then a else if S = 1 then b else c`")
            value = {ms[0][0]: int(ms[0][1]), ms[1][0]: int(ms[1][1]), "2": int(me.group(1))}
        elif kind == "move":                         # `... = (if w = 0 then 1 else 6)`
            m = re.search(r"then\s*(\d+)\s*else\s*(\d+)", st)
            if m is None:
                raise RuntimeError(f"theorem {name} in {rel} does not have the shape `if w = 0 then a else b`")
            value = {"w0": int(m.group(1)), "w1": int(m.group(2))}
        else:
            value = True
        facts.append({"name": name, "value": value, "proved_by": "decide", "theorem": f"Su2Plaq.LSH.{name}", "file": rel, "note": note})
    by = {f["name"]: f["value"] for f in facts}
    checks = {"card_inner_codes": num["n_inner"], "card_bright_codes": num["n_bright"], "card_dark_codes": num["n_inner"] - num["n_bright"],
              "card_states_lsh": num["n_physical"], "card_site_codes": len(num["site_valid"]), "site_valid_list": num["site_valid"],
              "coupling_by_y_weight": num["by_weight"], "move_per_site": {"w0": num["w0"], "w1": num["w1"]},
              "eight_differences": num["n_differences"]}
    for k, v in checks.items():
        if by[k] != v:
            raise RuntimeError(f"{k}: Lean says {by[k]!r}, the Python encoding gives {v!r}")
    facts.append({"name": "n_outer_site_patterns", "value": num["n_outer_site_patterns"], "proved_by": "numerical", "theorem": "", "file": "",
                  "note": "distinct outer-site patterns (the 12 read-only outer qubits take 305 values on the physical states); measured, not proved"})
    facts.append({"name": "transcoder_overhead", "value": _transcoder_overhead(), "proved_by": "numerical", "theorem": "", "file": "",
                  "note": "CX and fixed T of the per-site transcoder and its inverse around a spin-network circuit; measured on the circuit"})
    return {"facts": facts,
            "provenance": {"lean_files": {rel: hashlib.sha256(src.encode()).hexdigest() for rel, src in texts.values()},
                           "values_from": "Lean theorem statements, cross-checked against the Python encoding; two facts are numerical",
                           "plan": "prompts/401", "methods": "docs/METHODS-lsh.md L13",
                           "trust": "kernel-checked (by decide, standard axioms only) except the facts marked numerical"}}


def write_structure(path=None, root=None) -> pathlib.Path:
    """Write the structure file `compress/specs/lsh-structure.json` (or `path`); unchanged content is not rewritten."""
    import json

    p = pathlib.Path(path) if path is not None else _root(root) / "compress" / "specs" / "lsh-structure.json"
    text = json.dumps(structure_facts(root), indent=1)
    if p.exists() and p.read_text() == text:
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def brief_note(encoding: str, kind: str) -> str:
    """Registry hook: the LSH paragraph appended to the ideation brief and to every round brief."""
    return BRIEF_NOTE


# ------------------------------------------------------------------------------------------------------ phase 1 (stubs)
def _pending(what: str, step: str):
    raise NotImplementedError(f"su2plaq.lsh.loop.{what}: prompts/401 step {step} (needs the registry of prompts/008, step 8.R)")


def spec(order: int = 1):
    _pending("spec", "8.2")


def general_circuit(spec):
    _pending("general_circuit", "8.2")


def seed_candidates(spec, root):
    _pending("seed_candidates", "8.3")


def import_seed(spec, source: str):
    _pending("import_seed", "8.2")


def lean_certify(circ, spec, *, timeout: float = 1200.0, extra_provenance: dict | None = None, out_dir=None) -> dict:
    _pending("lean_certify", "8.4")


def render_spec(spec) -> str:
    _pending("render_spec", "8.2")


def angle_linear(circuit, spec) -> tuple:
    _pending("angle_linear", "8.2")


def general_program_path(spec, root=None) -> pathlib.Path:
    _pending("general_program_path", "8.2")


def seed_round(root=None, lean: bool = True, dry_run: bool = False) -> dict:
    _pending("seed_round", "8.3")


def run_round(round: int, evaluate: bool = True, dry_run: bool = False, root=None, proposals=None, lean: bool = True) -> dict:
    _pending("run_round", "8.3")


def stop_record(entry_id: str, root=None) -> dict:
    _pending("stop_record", "8.3")


def stop_state(root=None) -> dict:
    _pending("stop_state", "8.3")


def certify_headline(root=None) -> dict:
    _pending("certify_headline", "8.4 / 8.8")


def main(argv=None) -> int:
    _pending("main", "8.3")
