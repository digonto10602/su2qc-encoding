"""LSH compression loop, LSH-owned part (prompts/401 sections 1-2, docs/METHODS-lsh.md L12-L16).

`lsh` is a registry encoding of the shared loop (step 8.R, prompts/008); this module holds only what is specific to it: the
registry hooks (seeds, task text, Lean hook, angle-linearity), the seed circuits of round 0, the stop rule and the loop
bookkeeping.  It is in NO evaluator-hash list, assigns nothing into a shared module and edits no environment variable.

Phase 0 (steps 8.0-8.1): constants, `wrap_spinnet_step`, `seed_circuit`, `seed_program_source`, `stop_key`, `improves`,
`structure_facts`, `write_structure`, `BRIEF_NOTE`, `brief_note`.  Phase 1 (steps 8.2-8.4, on the registry entry `lsh` of
prompts/008): the registry hooks (`general_circuit`, `import_seed`, `render_spec`, `angle_linear`, `seed_candidates`,
`lean_certify`), the round bookkeeping (`seed_round`, `run_round`, `stop_record`, `stop_state`), `certify_headline` and the
CLI `main`.  `certify_headline` (step 8.4) is run on the finished loop in a clean worktree (step 8.8)."""
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
    if not path.exists():                       # a temporary root does not hold the immutable spin-network programs
        path = ROOT / rel
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


# ------------------------------------------------------------------------------------------------------ registry hooks (8.2)
def spec(order: int = 1):
    """The LSH step TaskSpec (nominal angles (0.37, 0.61) from `NOMINAL_ANGLES["lsh"]`; order 2 via dataclasses.replace)."""
    import dataclasses

    from su2plaq.compress.spec import default_spec

    sp = default_spec(ENC, KIND)
    return sp if order == 1 else dataclasses.replace(sp, order=order)


def general_circuit(spec) -> QuantumCircuit:
    """Registry hook `general_circuit(spec)`: the LSH reference circuit of the spec's kind / order / angles, outer register present."""
    from su2plaq.circuits import lsh as CL

    if spec.kind == "UE":
        return CL.build_UE(spec.alpha, with_outer=True)
    if spec.kind == "UB":
        return CL.build_UB(spec.beta, with_outer=True)
    return CL.build_step(spec.alpha, spec.beta, spec.order, with_outer=True)


def general_program_path(spec, root=None) -> pathlib.Path:
    """<root>/compress/programs/lsh/seed/000-general.py: the general circuit as an angle-linear Builder program (generated on first
    use by the shared `baselines.program_source`, afterwards immutable)."""
    from su2plaq.compress import baselines as BL

    path = _root(root) / "compress" / "programs" / spec.encoding / BL.SEED_FAMILY / f"000-{BL._stem(spec)}.py"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BL.program_source(general_circuit, spec, summary=(
            f"the reference circuit of the {spec.encoding} encoding ({spec.kind}) expressed through the Builder; every angle is a "
            "linear function of spec.alpha / spec.beta.")))
    return path


def _wrapped_paulo():
    """Paulo's 15-qubit spin-network file wrapped by the LSH transcoder (registers d[12], o[12], a[7])."""
    from su2plaq.circuits import lsh as CL
    from su2plaq.circuits import spinnet as CS

    return CL.wrap_spinnet(CS.paulo_circuit(), with_outer=True)


PAULO_WRAPPED_BETA = -0.05      # METHODS-lsh L5: the file is U_B(+0.05) of the spin-network gauge = U_B(-0.05) in the LSH gauge
_REASONS = {
    "paulo34": "paulo34 is the 34-qubit twelve-qubit-encoding file: it does not act on the LSH register",
    "lean22": "lean22 is a twelve-qubit-encoding plaquette circuit: it does not act on the LSH register",
    "lean22_v2": "lean22_v2 is a twelve-qubit-encoding plaquette circuit: it does not act on the LSH register",
    "spinnet15": "spinnet15 is the spin-network 15-qubit file; here it is the external row 'paulo15_wrapped' (the source 'paulo15') "
                 "and the vendored spin-network skeletons are the seeds 'wrap_*'",
}


def import_seed(spec, source: str):
    """Registry hook `import_seed(spec, source)`.  "paulo15": `baselines.SeedCircuit` of Paulo's 15-qubit file wrapped by the
    transcoder (fixed angle, kind UB, beta = -0.05, never a parent); "paulo34", "lean22", "lean22_v2", "spinnet15": a reason
    string (the shared round skips it); anything else: ValueError."""
    from su2plaq.compress.baselines import SeedCircuit

    if source == "paulo15":
        return SeedCircuit(qc=_wrapped_paulo(), source="paulo15_wrapped", fixed_angle=True, alpha=None, beta=PAULO_WRAPPED_BETA, kind="UB",
                           can_be_parent=False)
    if source in _REASONS:
        return _REASONS[source]
    raise ValueError(f"unknown seed source {source!r}; known: ['paulo15', {', '.join(map(repr, _REASONS))}]")


def angle_linear(circuit, spec) -> tuple:
    """Registry hook `angle_linear(circuit, spec)` (rho of the headline rule, audit 302 N6): (True, "ok") iff the LSH Lean exporter
    produces a certificate for the circuit at the nominal pair; otherwise (False, <the exporter's reason>), e.g.
    `non_linear_angle:...`, `too_many_qubits`, `phase_not_in_K`."""
    import tempfile

    from su2plaq.compress.spec import get_encoding
    from su2plaq.lean.exact import ExactError
    from su2plaq.lsh import lean_export as LE

    with tempfile.TemporaryDirectory() as td:
        try:
            res = LE.export_certificate(circuit, get_encoding(spec.encoding), spec.kind, spec.alpha, spec.beta, spec.order,
                                        pathlib.Path(td) / "angle-linearity.json")
        except ExactError as exc:
            return False, f"exact export failed: {exc}"
    if isinstance(res, str):
        return False, res
    return True, "ok"


def _structure_markdown(facts: dict) -> str:
    lines = []
    for f in facts["facts"]:
        if f["proved_by"] == "decide":
            lines.append(f"- `{f['name']}` = {f['value']} (proved by decide, {f['theorem']}) -- {f['note']}")
        else:
            lines.append(f"- `{f['name']}` = {f['value']} (measured, not proved) -- {f['note']}")
    return ("## Proved structure (Lean)\n\n"
            "Machine-checked facts about the problem (Lean 4, kernel-checked by `decide`, standard axioms only); the numerical evaluator "
            "remains ground truth. Facts marked *measured* are numbers read off the Python encoding, not proved.\n\n"
            + "\n".join(lines) + "\n")


def _rules_markdown(sp) -> str:
    """Section 'LSH register and rules' (layout, valid codes, Abelian Gauss law, the target in LSH variables, the electric phase);
    counts from the encoding, angles from the spec."""
    from su2plaq.compress.spec import get_encoding

    enc = get_encoding(sp.encoding)
    n_inner = len(enc.inner_codes())
    return (
        "## LSH register and rules\n\n"
        f"The register is `d[0..{enc.n_data - 1}]` (the four 'in' sites, `d[3c], d[3c+1], d[3c+2]` = ($\\ell_{{pn}}$, $\\ell_{{nv}}$, "
        f"$\\ell_{{vp}}$) of corner $c$, written `l_pn`, `l_nv`, `l_vp`), `o[{enc.n_data}..{enc.n_data + enc.n_outer - 1}]` (the "
        f"read-only outer sites: use them as controls only; a program that writes an outer qubit is invalid) and the ancillas you "
        f"allocate. A site holds one of the five codes 000, 001, 010, 100, 110 (bit order `l_vp l_nv l_pn`); a state is physical when "
        f"all four 'in' sites are valid and the Abelian Gauss law holds on the four inner links (`l_pn xor l_nv` at one site equals "
        f"`l_pn xor l_vp` at the next): {n_inner} data codes, {len(enc.basis.labels)} physical states with the outer pattern. "
        f"Target: $U=U_B(\\beta)\\,U_E(\\alpha)$ at $(\\alpha,\\beta)=({sp.alpha:g},{sp.beta:g})$; $U_B=e^{{-i\\beta K}}$ with $K$ the "
        f"real symmetric coupling of the {n_inner} inner codes (zero on dark codes), identity structure in the outer pattern; "
        "$U_E=e^{-i\\alpha H_E}$ is diagonal: $H_E=\\tfrac34\\sum_c N_n(c)$ with $N_n=\\ell_{pn}+\\ell_{nv}$ at each site, i.e. the phase "
        "$-3\\alpha/4$ per set `l_pn` or `l_nv` bit (the two never are both set on a physical site). A final state that breaks the "
        "Abelian Gauss law or the flux cap on a physical input makes the program invalid; intermediate states are unrestricted. "
        "`rccx` (relative-phase Toffoli, 3 CX) is available where an exact `ccx` (6 CX) is not needed.\n\n")


def render_spec(spec) -> str:
    """Registry hook `render_spec(spec)`: the shared default text with the "Proved structure (Lean)" section replaced by the section
    'LSH register and rules', the facts of `structure_facts()` (read from the Lean sources) and the headline rule
    (`robust.HEADLINE_RULE_SECTION`), the tools section unchanged (the stock commands with `--encoding lsh --kind step`).  It names
    no seed and no spin-network entry."""
    from su2plaq.compress.robust import HEADLINE_RULE_SECTION

    text = spec._render_default()
    head, tools = "## Proved structure (Lean)", "## Tools"
    i, j = text.find(head), text.find(tools)
    if i < 0 or j < i:
        raise RuntimeError("shared module shape changed: TaskSpec._render_default() lost its 'Proved structure (Lean)' / 'Tools' sections")
    return (text[:i] + _rules_markdown(spec) + _structure_markdown(structure_facts()) + "\n" + HEADLINE_RULE_SECTION.rstrip("\n") + "\n\n"
            + text[j:])


# ------------------------------------------------------------------------------------------------------ round 0 and rounds (8.3)
def _polished_fn(s):
    from su2plaq.compress import baselines as BL

    return BL.general_polished(s)[0]


def _l3_fn(s):
    from su2plaq.compress import baselines as BL

    return BL.qiskit_l3(s, seed=12345)


def seed_candidates(spec, root):
    """Registry hook `seed_candidates(spec, root)`: [(label, program_path | None, circuit_fn | None)], the ten rows of `SEED_FILES`
    in that order.  The programs are written under `<root>/compress/programs/lsh/seed/` on first use and are immutable afterwards:
    the general program and the wrapped circuits through the shared `baselines.program_source` (angles fitted from the circuits,
    never typed), the two shared baselines (general + polish, Qiskit level 3 in windows of 32) likewise; a baseline whose
    skeleton or angle-linearity the fit refuses (the windowed L3 circuit loses its rotations at alpha = beta = 0, measured) has
    no program file and is evaluated as a circuit (`circuit_fn`)."""
    from su2plaq.compress import baselines as BL

    root = _root(root)
    d = root / "compress" / "programs" / spec.encoding / BL.SEED_FAMILY
    d.mkdir(parents=True, exist_ok=True)
    gp = general_program_path(spec, root)
    out = []
    for label, fname in SEED_FILES:
        f = d / fname
        if label == "general":
            out.append((label, gp, None))
            continue
        fn = {"general+polish": _polished_fn, "qiskit_l3": _l3_fn}.get(label)
        if not f.exists():
            if fn is None:
                f.write_text(seed_program_source(label, spec, root))
            else:
                summary = ("the reference circuit after the deterministic polish passes." if label == "general+polish"
                           else f"Qiskit level-3 transpile (windows of {BL.L3_WINDOW}) of the reference circuit.")
                try:
                    f.write_text(BL.program_source(fn, spec, summary=summary))
                except ValueError:
                    f = None          # angle-dependent skeleton / angle that is not linear at alpha = beta = 0: evaluated as a circuit
        out.append((label, f, fn))
    return out


def _paulo_row(spec) -> dict:
    """External row of round 0 (never archived): Paulo's 15-qubit file wrapped by the transcoder, judged at its OWN kind and angle
    (U_B, beta = -0.05, no alternate pairs) with the spec's exact tolerances."""
    from su2plaq.compress import evaluate as E
    from su2plaq.compress import oracle
    from su2plaq.compress.metrics import metrics
    from su2plaq.compress.spec import TaskSpec, get_encoding
    from su2plaq.evaluate.evaluator import evaluate

    seed = import_seed(spec, "paulo15")
    s2 = TaskSpec(**{**spec.to_dict(), "kind": seed.kind, "beta": seed.beta, "alt_angles": ()})
    v = evaluate(seed.qc, get_encoding(spec.encoding), oracle.target(s2), tol_err=s2.tol_err, tol_gauss=s2.tol_gauss, gauss=True, engine="auto",
                 cap=spec.support_cap)
    valid, reason = E._classify(v, E._gate_violations(seed.qc))
    try:
        met = metrics(seed.qc, s2, measured=valid)
    except ValueError:
        met = None
    return {"source": seed.source, "fixed_angle": True, "kind": seed.kind, "beta": seed.beta, "valid": valid, "reason": reason, "metrics": met,
            "op_norm_error": getattr(v, "op_norm_error", None), "total_error": getattr(v, "total_error", None),
            "gauss_residual": getattr(v, "gauss_residual", None), "certified": getattr(v, "certified", None),
            "message": f"fixed angle beta={seed.beta}, kind {seed.kind}; exact-angle tolerance {s2.tol_err:g}; the file is U_B(+0.05) of the "
                       "spin-network gauge = U_B(-0.05) in the LSH gauge (METHODS-lsh L5)"}


def _wrapped_sources_record(root=None) -> dict:
    """{label: {"path", "sha256", "spinnet_entry"}} of the pinned spin-network programs; every pin is checked against the file."""
    out = {}
    for label, (rel, sha, entry) in WRAP_SOURCES.items():
        path = _root(root) / rel
        if not path.exists():
            path = ROOT / rel
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError(f"{rel} differs from the pinned spin-network program (sha256 {sha[:12]}...)")
        out[label] = {"path": rel, "sha256": sha, "spinnet_entry": entry}
    return out


def _round_file(root: pathlib.Path, round: int) -> pathlib.Path:
    return root / "results" / "compress" / ENC / f"round-{round:03d}.json"


def _stop_file(root: pathlib.Path) -> pathlib.Path:
    return root / "results" / "compress" / ENC / "stop.json"


def _atomic_json(path: pathlib.Path, obj) -> None:
    import json
    import os

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(obj, indent=1, default=str))
    tmp.replace(path)


def stop_record(entry_id: str, root=None) -> dict:
    """Headline record of the stop rule {"id", "cx", "t_sum", "rho", "qubits", "n_rot", "t_fixed"}: (CX, sum T, rho, qubits) from the
    robust metrics of the entry (`robust.json`, computed and cached if missing), (n_rot, t_fixed) from the archive entry's
    nominal metrics.  RuntimeError for an unknown or unrankable (skeleton changes over the angle set) entry."""
    import json

    from su2plaq.compress import archive as A
    from su2plaq.compress import robust as RB
    from su2plaq.compress.spec import default_spec

    root = _root(root)
    sp = default_spec(ENC, KIND)
    arch = A.Archive.load(ENC, root=root, n_alt=len(sp.alt_angles), strict=True)
    e = next((x for x in arch.entries() if x.id == entry_id), None)
    if e is None:
        raise RuntimeError(f"entry {entry_id!r} is not in the archive of {ENC}")
    cache = root / "results" / "compress" / ENC / "robust.json"
    rec = json.loads(cache.read_text()).get("entries", {}).get(entry_id) if cache.exists() else None
    if rec is None or rec.get("program_sha256") != e.program_sha256:
        RB.headline(ENC, KIND, root=root)
        rec = json.loads(cache.read_text())["entries"].get(entry_id)
    if rec is None or rec.get("robust_key") is None:
        raise RuntimeError(f"entry {entry_id!r} has no robust key (its skeleton changes over the angle set)")
    m = e.metrics_raw
    return {"id": entry_id, "cx": int(rec["cx"]), "t_sum": int(rec["t_sum"]), "rho": 0 if rec["angle_linear"] else 1, "qubits": int(rec["qubits"]),
            "n_rot": int(m["n_rot"]), "t_fixed": int(m["t_fixed"])}


def _record_round(round: int, root: pathlib.Path) -> dict:
    """After an evaluated round: the headline of the archive (shared robust rule, cached) and its stop record are appended to
    `results/compress/lsh/stop.json` (a record of the same round is replaced: a replay is not a round).  -> `stop_state(root)`."""
    import json

    from su2plaq.compress import robust as RB

    h = RB.headline(ENC, KIND, root=root)
    if not h or h.get("id") is None:
        raise RuntimeError(f"round {round}: the archive has no headline (no valid entry with a robust key)")
    f = _stop_file(root)
    raw = json.loads(f.read_text()).get("rounds", []) if f.exists() else []
    raw = [x for x in raw if x["round"] != round] + [{"round": round, "headline_id": h["id"], "robust_key": [int(x) for x in h["robust_key"]],
                                                      "record": stop_record(h["id"], root)}]
    raw.sort(key=lambda x: x["round"])
    _atomic_json(f, {"rounds": raw})
    return stop_state(root)


def _sessions(root: pathlib.Path) -> int:
    """Proposer sessions so far: distinct (round, family) pairs with round >= 1 in the attempts log, plus one for the ideation."""
    import json

    n = set()
    f = root / "compress" / "attempts" / f"{ENC}.jsonl"
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip():
                a = json.loads(line)
                if a["round"] >= 1:
                    n.add((a["round"], a["family"]))
    return len(n) + (1 if (root / "compress" / "ideation" / f"{ENC}.md").exists() else 0)


def stop_state(root=None) -> dict:
    """The stop rule of prompts/401 section 1.6 applied to the headline records of `results/compress/lsh/stop.json`:
    {"rounds": [{"round", "headline_id", "robust_key", "record", "improved"}], "streak" (rounds since the last improvement),
    "sessions", "stop", "reason" (None | "no_gain" | "max_rounds" | "max_sessions"; the first that applies), "reasons" (all that
    apply)}.  The result is written back to stop.json."""
    import json

    root = _root(root)
    f = _stop_file(root)
    raw = json.loads(f.read_text()).get("rounds", []) if f.exists() else []
    rounds, prev = [], None
    for x in sorted(raw, key=lambda x: x["round"]):
        better = improves(x["record"], prev)
        if better:
            prev = x["record"]
        rounds.append({"round": x["round"], "headline_id": x["headline_id"], "robust_key": x["robust_key"], "record": x["record"],
                       "improved": bool(better)})
    streak = 0
    for x in reversed(rounds):
        if x["improved"]:
            break
        streak += 1
    sessions = _sessions(root)
    reasons = []
    if rounds and streak >= STOP_NO_GAIN_ROUNDS:
        reasons.append("no_gain")
    if rounds and rounds[-1]["round"] >= STOP_MAX_ROUNDS:
        reasons.append("max_rounds")
    if sessions >= STOP_MAX_SESSIONS:
        reasons.append("max_sessions")
    out = {"rounds": rounds, "streak": streak, "sessions": sessions, "stop": bool(reasons), "reason": reasons[0] if reasons else None,
           "reasons": reasons, "max_rounds": STOP_MAX_ROUNDS, "no_gain_rounds": STOP_NO_GAIN_ROUNDS, "max_sessions": STOP_MAX_SESSIONS}
    if rounds:
        _atomic_json(f, out)
    return out


def seed_round(root=None, lean: bool = True, dry_run: bool = False) -> dict:
    """Round 0 (prompts/401 section 3, step 8.3): the ten seeds through the shared `round.run_round("lsh", "step", 0)` (hook
    `seed_candidates`; archive, feedback, attempts, synthesis re-verification and, with `lean`, the Lean certificate of the best are
    the shared ones), then `results/compress/lsh/round-000.json` gains the external row `paulo15_wrapped` and the key
    `"lsh": {"wrapped_sources": ...}`, and the headline record of round 0 is appended to stop.json.
    -> the shared info dict + {"stop": stop_state}."""
    import json

    from su2plaq.compress import round as R

    root = _root(root)
    sp = spec()
    info = R.run_round(ENC, KIND, 0, evaluate=True, dry_run=dry_run, root=root, lean=lean)
    f = _round_file(root, 0)
    d = json.loads(f.read_text())
    d["external"] = [x for x in d.get("external", []) if x.get("source") != "paulo15_wrapped"] + [_paulo_row(sp)]
    d["lsh"] = {"wrapped_sources": _wrapped_sources_record(root), "plan": "prompts/401"}
    _atomic_json(f, d)
    info["external"] = [x["source"] for x in d["external"]]
    info["stop"] = _record_round(0, root)
    return info


def run_round(round: int, evaluate: bool = True, dry_run: bool = False, root=None, proposals=None, lean: bool = True) -> dict:
    """Round 0: `seed_round`.  Round r >= 1: the shared `round.run_round("lsh", "step", r)` (default proposals: every unseen
    `compress/programs/lsh/<family>/NNN-*.py`), then the headline record of the round is appended to stop.json.  Without
    `evaluate` nothing is recorded."""
    from su2plaq.compress import round as R

    root = _root(root)
    if round == 0 and proposals is None:
        return seed_round(root=root, lean=lean, dry_run=dry_run)
    info = R.run_round(ENC, KIND, round, evaluate=evaluate, dry_run=dry_run, root=root, proposals=proposals, lean=lean)
    if evaluate:
        info["stop"] = _record_round(round, root)
    return info


def make_ideation_brief(root=None) -> pathlib.Path:
    """compress/briefs/lsh/ideation.md (shared `brief.make_ideation_brief`; the facts file is written first)."""
    from su2plaq.compress import brief as BR

    root = _root(root)
    write_structure(path=root / "compress" / "specs" / "lsh-structure.json")
    return BR.make_ideation_brief(ENC, KIND, root)


def make_brief(round: int, family: str, root=None) -> pathlib.Path:
    """compress/briefs/lsh/round-rrr-<family>.md (shared `brief.make_brief`)."""
    from su2plaq.compress import brief as BR

    root = _root(root)
    write_structure(path=root / "compress" / "specs" / "lsh-structure.json")
    return BR.make_brief(ENC, KIND, round, family, root)


_USAGE = ("python -m su2plaq.lsh.loop {seed [--no-lean] [--dry-run] | round --round r [--evaluate] [--no-lean] [--dry-run] | brief --round r "
          "--family F | ideation | stop-state | headline [--refresh] | certify-headline | structure}   (all take --root)")


def main(argv=None) -> int:
    """CLI of the loop; every subcommand takes `--root` (default: the repository).  `seed`, `round`, `brief`, `ideation`,
    `stop-state`, `headline`, `certify-headline`, `structure`; the candidate and oracle tools are the stock ones
    (`python -m su2plaq.compress.run_candidate|oracle ... --encoding lsh --kind step`)."""
    import argparse
    import json
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("seed", "round", "brief", "ideation", "stop-state", "headline", "certify-headline", "structure"):
        raise SystemExit(f"usage: {_USAGE}")
    cmd = argv[0]
    ap = argparse.ArgumentParser(prog=f"python -m su2plaq.lsh.loop {cmd}")
    ap.add_argument("--root")
    if cmd in ("seed", "round"):
        ap.add_argument("--dry-run", action="store_true")
        ap.add_argument("--no-lean", dest="lean", action="store_false", default=True)
    if cmd == "round":
        ap.add_argument("--round", type=int, required=True)
        ap.add_argument("--evaluate", action="store_true")
    if cmd == "brief":
        ap.add_argument("--round", type=int, required=True)
        ap.add_argument("--family", required=True)
    if cmd == "headline":
        ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args(argv[1:])
    if cmd == "seed":
        print(json.dumps(seed_round(a.root, lean=a.lean, dry_run=a.dry_run), indent=1, default=str))
    elif cmd == "round":
        print(json.dumps(run_round(a.round, evaluate=a.evaluate or a.round == 0, dry_run=a.dry_run, root=a.root, lean=a.lean), indent=1,
                         default=str))
    elif cmd == "brief":
        print(make_brief(a.round, a.family, a.root))
    elif cmd == "ideation":
        print(make_ideation_brief(a.root))
    elif cmd == "stop-state":
        print(json.dumps(stop_state(a.root), indent=1, default=str))
    elif cmd == "headline":
        from su2plaq.compress import robust as RB

        print(json.dumps(RB.headline(ENC, KIND, root=a.root, refresh=a.refresh), indent=1, default=str))
    elif cmd == "certify-headline":
        print(json.dumps(certify_headline(a.root), indent=1, default=str))
    else:
        print(write_structure(root=a.root))
    return 0


# ------------------------------------------------------------------------------------------------------ Lean (8.4)
THEOREM_NAME, THEOREM_FILE = "lsh_best", pathlib.Path("lean") / "certs" / "lsh-best-step.lean"


def lean_certify(circ, spec, *, timeout: float = 1200.0, extra_provenance: dict | None = None, out_dir=None) -> dict:
    """Registry hook `lean_certify(circ, spec, *, timeout, extra_provenance, out_dir)`: `lsh.lean_export.certify` (exact export of
    the circuit against the LSH target, then the compiled Lean checker `su2plaq_cert_lsh`).  -> {"status": "certified" | "rejected" |
    "n_a" | "failed", "reason", "cert_path", "seconds", "axioms", "check_seconds", "checker_sha256"}; `n_a` carries the exporter's reason
    (e.g. `non_linear_angle:...`).  `extra_provenance` (`entry_id`, `program_file_sha256`) is written inside the certificate.  Lean never
    changes a verdict."""
    from su2plaq.compress.spec import get_encoding
    from su2plaq.lsh import lean_export as LE

    return LE.certify(circ, get_encoding(spec.encoding), spec.kind, spec.alpha, spec.beta, spec.order, out_dir=out_dir, timeout=timeout,
                      extra_provenance=extra_provenance)


def _certify_entry(arch, entry, sp, root: pathlib.Path, why: str) -> dict:
    """Rebuild the entry's circuit from its program file (sha256 checked), certify it with the binding fields and store the status on
    the entry (`round._store_lean`); -> the stored dict (+ `entry_id`)."""
    import time

    from su2plaq.compress import round as R

    t0 = time.time()
    circ, err = R._circuit_of(sp, entry.program_path, entry.id, None, root, expected_sha256=entry.program_sha256)
    if circ is None:
        new = {"status": "failed", "reason": f"cannot rebuild the circuit: {err}", "seconds": time.time() - t0}
    else:
        new = dict(lean_certify(circ, sp, timeout=1200.0, extra_provenance={"entry_id": entry.id, "program_file_sha256": entry.program_sha256},
                                out_dir=root / "results" / ENC / "certs"))
        new["program_file_sha256"] = entry.program_sha256
        if new.get("cert_path"):
            import json

            new["gates_sha256"] = json.loads(pathlib.Path(new["cert_path"]).read_text())["gates_sha256"]
    R._store_lean(entry, new, root, ENC, why)
    return {**entry.lean, "entry_id": entry.id}


def certify_headline(root=None) -> dict:
    """Step 8.8: Lean-certify the headline (robust key) and, if different, the archive best: each is rebuilt through the stock worker from
    its program file (sha256 must equal the archived one), certified with the binding fields (`entry_id`, `program_file_sha256`) inside the
    certificate, and the status is stored on the archive entry.  A certified headline also gets the theorem file
    `lean/certs/lsh-best-step.lean` (`theorem lsh_best ... := by native_decide`, first line `-- entry <id>, program sha256 <sha>`).
    A headline with `n_a` (non-linear angle, phase not in K) is allowed and reported as such.  Run it in a clean worktree: the
    certificate records `git_dirty`.  -> {"headline", "archive_best", "lean_headline", "lean_best", "theorem_file", "git_dirty"}."""
    from su2plaq.compress import archive as A
    from su2plaq.compress import robust as RB
    from su2plaq.lsh import lean_export as LE

    root = _root(root)
    sp = spec()
    arch = A.Archive.load(ENC, root=root, n_alt=len(sp.alt_angles), strict=True)
    h = RB.headline(ENC, KIND, root=root)
    best = arch.best()
    if not h or h.get("id") is None or best is None:
        raise RuntimeError("the archive has no headline: nothing to certify")
    by = {e.id: e for e in arch.entries()}
    head = by[h["id"]]
    lean_head = _certify_entry(arch, head, sp, root, "certify_headline")
    lean_best = lean_head if best.id == head.id else _certify_entry(arch, best, sp, root, "certify_headline (archive best)")
    arch.save()
    theorem = None
    if lean_head.get("status") == "certified":
        from su2plaq.compress import round as R

        cert = R.resolve_cert_path(lean_head, root)
        theorem = str(LE.write_theorem_file(cert, THEOREM_NAME, root / THEOREM_FILE,
                                            comment=f"entry {head.id}, program sha256 {head.program_sha256}"))
    return {"headline": head.id, "archive_best": best.id, "lean_headline": lean_head, "lean_best": lean_best, "theorem_file": theorem,
            "git_dirty": LE._git_dirty()}


if __name__ == "__main__":
    raise SystemExit(main())
