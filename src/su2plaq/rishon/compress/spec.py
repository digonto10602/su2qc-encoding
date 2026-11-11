"""Rishon task spec, registered compress view, structure facts, spec text (prompts/203 section 3.1, 4; METHODS-rishon R10, R12).

`register()` inserts the encoding into the laptop machinery at runtime (two dict inserts; no laptop file is edited):
`NOMINAL_ANGLES["rishon"]` and `su2plaq.compress.spec._ENCODINGS["rishon"]`.  The registered object, `RishonCompressView`, is the
encoding the laptop builder / oracle / evaluator see: the 1296 valid inner codes as single-code "states" (outer bits 0), the target
is the inner operator V_in (R4).  The 38 432-state physical basis and the Gauss sample stay behind `view.encoding` and are used by
`su2plaq.rishon.verify` only.
"""
from __future__ import annotations

import copy
import functools
import hashlib
import inspect
import itertools
import json
import math
import pathlib
import re
from fractions import Fraction

import numpy as np

from su2plaq.encodings.base import NOMINAL_ANGLES, EncodedBasis
from su2plaq.encodings.rishon import RISHON_NOMINAL as _ENC_NOMINAL
from su2plaq.encodings.rishon import RishonEncoding, RishonInnerView
from su2plaq.rishon import operators as _ops
from su2plaq.rishon import physical as _phys

RISHON_NOMINAL = _ENC_NOMINAL       # = encodings.rishon.RISHON_NOMINAL = (0.37, 0.61)

# measured growth of the sparse engine's certified pruning bound per BRANCHING gate of its own lowering (h, sx, u; ch, crx, rccx count 2;
# macro ccx/ccz and every permutation/phase gate count 0), Frobenius over the 1296 inputs, worst measured rate over the circuits of the
# table in prompts/203 section 13 E2 (planner, scratchpad/proto_prune_h.py; METHODS-rishon R11): a measured input, not derived here.
# Re-measure with the same prototype if the engine's pruning (PRUNE_REL, coalescing) changes.
PRUNE_RATE_PER_BRANCHING_GATE = 1.1e-15
PRUNE_BRANCHING = ["h", "sx", "u", "ch (2)", "crx (2)", "rccx (2)", "crz (0)", "cp (0)"]
PRUNE_ENGINE_EXACT = ["x", "z", "s", "sdg", "t", "tdg", "p", "rz", "cx", "cz", "cp", "swap", "ccx", "ccz"]
PRUNE_PROVENANCE = "prompts/203 §13 E2 table"

_STATE_INDEXING = ("**State indexing.** Inner codes 0..1295 in sorted code order (the 6^4 = 1296 valid inner codes are the "
                   "single-code input states of the evaluator, outer bits 0); `oracle --codec --state k` prints the code of "
                   "state k and the link types of b, r, t, l.")


# ------------------------------------------------------------------------------------------------ the registered view
class _InnerBasis:
    """`.labels` = [(code,) for code in inner_codes()] and `.index((code,))`: the laptop oracle's state lookup."""

    def __init__(self, codes: np.ndarray):
        self.labels = [(int(c),) for c in codes]
        self._pos = {lab: i for i, lab in enumerate(self.labels)}
        self.dim = len(self.labels)

    def index(self, key) -> int:
        lab = (int(key[0]),)
        if lab not in self._pos:
            raise KeyError(f"{key!r} is not a valid inner code")
        return self._pos[lab]


class RishonCompressView:
    """The encoding object the laptop machinery sees for "rishon" (duck-typed as prompts/002 section 2.7)."""

    name = "rishon"
    n_data = 16
    n_outer = 32
    is_basis_encoding = True

    def __init__(self):
        self.encoding = RishonEncoding()
        self.registers = {k: list(v) for k, v in self.encoding.registers.items()}
        self._inner_view = RishonInnerView()
        codes = _ops.inner_codes()
        self.basis = _InnerBasis(codes)
        self._pv: EncodedBasis | None = None

    def inner_codes(self) -> np.ndarray:
        return _ops.inner_codes()

    def physical_vectors(self) -> EncodedBasis:
        if self._pv is None:
            self._pv = self._inner_view.physical_vectors()
        return self._pv

    def target(self, kind, alpha, beta, order=1) -> np.ndarray:
        return _ops.inner_target(kind, alpha, beta, order)

    def layout_of(self, qc):
        return self._inner_view.layout_of(qc)

    def decode_state(self, codes, amps):
        return self._inner_view.decode_state(codes, amps)

    def describe(self) -> str:
        return self.encoding.describe() + "\n" + _STATE_INDEXING + "\n"

    def import_map(self, source) -> str:
        return self.encoding.import_map(source)

    def bright_pairs(self) -> list:
        return _ops.bright_pairs()

    def heights(self, code: int) -> tuple:
        return _ops.heights(code)

    def closed_codes(self):
        return _ops.closed_codes()

    def dark_codes(self) -> np.ndarray:
        return _ops.dark_codes()


_VIEW: RishonCompressView | None = None


# Effective qubit limit of the exact sparse engine.  PROVENANCE: laptop-owned `su2plaq/evaluate/sparse_sim.py:298-299`
# (`run_batch`: `if n > 62: raise ValueError("at most 62 qubits")`, int64 basis keys); the laptop module does not expose the number,
# so it is repeated here (tests/unit/test_rishon_compress_spec_unit.py checks that the engine really rejects 63 and accepts 62).
# The task spec's `peak_qubit_cap()` (80, locked by tests/acceptance/m6) is NOT lowered; circuits above this limit are recorded
# invalid with the reason `engine_qubit_limit` instead of reaching the engine.
ENGINE_QUBIT_LIMIT = 62
REASON_ENGINE_QUBIT_LIMIT = "engine_qubit_limit"


def engine_qubit_message(n_qubits: int) -> str:
    return (f"{n_qubits} qubits > the exact simulation engine's limit of {ENGINE_QUBIT_LIMIT} qubits "
            f"(the circuit cannot be evaluated; use at most {ENGINE_QUBIT_LIMIT} qubits in total)")


def register() -> None:
    """NOMINAL_ANGLES["rishon"] = RISHON_NOMINAL; su2plaq.compress.spec._ENCODINGS["rishon"] = RishonCompressView() (idempotent)."""
    global _VIEW
    from su2plaq.compress import spec as laptop

    NOMINAL_ANGLES["rishon"] = RISHON_NOMINAL
    if _VIEW is None:
        _VIEW = RishonCompressView()
    laptop._ENCODINGS["rishon"] = _VIEW


def rishon_spec(kind: str = "step", order: int = 1):
    """TaskSpec for the rishon encoding (same sha256 as the laptop default_spec("rishon", kind) after register())."""
    from su2plaq.compress.spec import TaskSpec

    register()
    a, b = RISHON_NOMINAL
    return TaskSpec(encoding="rishon", kind=kind, alpha=a, beta=b, order=order)


# ------------------------------------------------------------------------------------------------ structure facts
ROOT = pathlib.Path(__file__).resolve().parents[4]
LEAN_DIR = ROOT / "lean"
_HB_CERT = "lean/certs/rishon-hb-structure.lean"
_LEAN_SRC = {"counts": "Su2Plaq/Rishon/Counts.lean", "jw": "Su2Plaq/Rishon/JW.lean", "corner": "Su2Plaq/Rishon/CornerKernel.lean",
             "ue": "Su2Plaq/Rishon/UESemantics.lean"}


def _lean_theorem(rel: str, name: str) -> str:
    """The statement of `theorem <name>` in lean/<rel> (up to ':= by'); FileNotFoundError / ValueError if absent."""
    text = (LEAN_DIR / rel).read_text()
    m = re.search(r"^theorem " + re.escape(name) + r"\b(.*?):=", text, flags=re.S | re.M)
    if m is None:
        raise ValueError(f"theorem {name} not found in lean/{rel}")
    return m.group(1)


def _lean_number(rel: str, name: str, pattern: str) -> int:
    stmt = _lean_theorem(rel, name)
    m = re.search(pattern, stmt)
    if m is None:
        raise ValueError(f"theorem {name} in lean/{rel}: pattern {pattern!r} not found in {stmt!r}")
    return int(m.group(1))


def _gf2_rank(vectors) -> int:
    basis: list[int] = []
    for v in vectors:
        v = int(v)
        for b in basis:
            v = min(v, v ^ b)
        if v:
            basis.append(v)
    return len(basis)


def _affine_dim(codes: np.ndarray) -> tuple[int, bool]:
    """(dimension of the GF(2) affine span of a set of bit strings, whether the set IS that affine subspace)."""
    codes = np.asarray(codes, dtype=np.int64)
    d = _gf2_rank(codes ^ codes[0])
    return d, len(codes) == 2 ** d


def _kappa_label(k: float) -> str:
    for lab, val in (("1", 1.0), ("2", 2.0), ("4*sqrt2", 4.0 * np.sqrt(2.0))):
        if abs(k - val) <= 1e-9:
            return lab
    return f"{k:.12g}"


def _alphabet_k(a: float) -> int:
    k = int(round(-2.0 * np.log2(a)))          # a = 2^{-k/2}
    if abs(a - 2.0 ** (-k / 2.0)) > 1e-9:
        raise ValueError(f"amplitude {a} is not a power of 1/sqrt2")
    return k


def _alphabet_label(a: float) -> str:
    k = _alphabet_k(a)
    n = 2 ** (k // 2)
    if k % 2 == 0:
        return "1" if n == 1 else f"1/{n}"
    return f"1/{n}sqrt2" if n > 1 else "1/sqrt2"


def _alphabet_tex(a: float) -> str:
    k = _alphabet_k(a)
    n = 2 ** (k // 2)
    if k % 2 == 0:
        return "1" if n == 1 else f"\\tfrac1{{{n}}}"
    return f"\\tfrac1{{{n if n > 1 else ''}\\sqrt2}}"


@functools.lru_cache(maxsize=1)
def _structure_facts_cached() -> dict:
    codes = _ops.inner_codes()
    cbf = _phys.count_by_fusion()
    pairs = _ops.bright_pairs()
    dark = _ops.dark_codes()
    facts: list[dict] = []

    def decide(name, value, theorem, rel, note):
        _lean_theorem(rel, theorem)                      # the theorem must exist in the Lean source
        facts.append({"name": name, "value": value, "proved_by": "decide", "theorem": f"Su2Plaq.{theorem}" if rel.endswith("Counts.lean")
                      else f"Su2Plaq.Rishon.{theorem}", "note": note})

    # --- kernel-checked (Lean `decide +kernel`; the value is recomputed here and compared with the literal in the Lean statement)
    n_phys = int(cbf["dim"])
    if n_phys != _lean_number(_LEAN_SRC["counts"], "card_rishon_physical", r"=\s*(\d+)"):
        raise ValueError("physical-state count of the code differs from the Lean statement")
    decide("card_rishon_physical", n_phys, "card_rishon_physical", _LEAN_SRC["counts"], "number of Gauss-law (SU(2)) states of the plaquette with 8 outer links")
    n_closed = int(cbf["closed"])
    if n_closed != _lean_number(_LEAN_SRC["counts"], "card_rishon_closed", r"=\s*(\d+)"):
        raise ValueError("closed-state count of the code differs from the Lean statement")
    decide("card_rishon_closed", n_closed, "card_rishon_closed", _LEAN_SRC["counts"], "states with every outer link a singlet")
    n_inner = int(len(codes))
    if n_inner != _lean_number(_LEAN_SRC["ue"], "card_inner_codes", r"=\s*(\d+)"):
        raise ValueError("inner-code count of the code differs from the Lean statement")
    decide("card_inner_codes", n_inner, "card_inner_codes", _LEAN_SRC["ue"], "valid inner codes (6 link states on each of the 4 inner links)")
    _lean_theorem(_LEAN_SRC["jw"], "bilinear_string_free_8")
    facts.append({"name": "jw_string_free", "value": True, "proved_by": "decide", "theorem": "Su2Plaq.Rishon.bilinear_string_free_8",
                  "note": "Jordan-Wigner strings of other links cancel in every link bilinear: link operators act on their own 4 qubits only"})
    n_ends = len(_phys._diagram().corners[0].ends)
    n_end_states = 2 + 1                                     # an end carries 0, 1 or 2 rishons (two colour modes)
    n_cfg = n_end_states ** n_ends
    if n_cfg != _lean_number(_LEAN_SRC["corner"], "corner_kernel_dims", r"List\.range\s+(\d+)"):
        raise ValueError("corner-configuration count of the code differs from the Lean statement")
    decide("corner_kernel_dims", n_cfg, "corner_kernel_dims", _LEAN_SRC["corner"],
           "for all corner end configurations the Gauss kernel dimension equals the SU(2) fusion count")
    decide("ue_exact_all_codes", True, "ue_exact_all_codes", _LEAN_SRC["ue"],
           "the 12 electric gates map every valid inner code exactly to z^{-3 #Q}|code> for all alpha (exact Laurent arithmetic)")

    # --- native (compiled checker)
    kappas: dict[str, int] = {}
    for _, _, k in pairs:
        kappas[_kappa_label(k)] = kappas.get(_kappa_label(k), 0) + 1
    facts.append({"name": "hb_bright_pairs", "proved_by": "native", "certificate": _HB_CERT,
                  "value": {"n_pairs": len(pairs), "kappa_multiset": dict(sorted(kappas.items())), "dark_codes": int(len(dark)),
                            "vectors": 2 * len(pairs)},
                  "note": "H_B^in = -sum_p kappa_p (|u_p><v_p| + h.c.) over commuting bright pairs; the other codes are dark (exact integer pairs a + b sqrt2)"})

    # --- numerical
    W = _ops.plaquette_W_inner()
    r, c = np.nonzero(np.abs(W) > 1e-12)
    h = np.array([_ops.heights(int(x)) for x in codes], dtype=np.int64)
    shifts = sorted({tuple(int(x) for x in row) for row in (h[r] - h[c])})
    import scipy.sparse as sp

    Ws = sp.csr_matrix(W)
    w3 = float(np.abs((Ws @ Ws @ Ws).toarray()).max())
    facts.append({"name": "heights_raising", "proved_by": "numerical",
                  "value": {"height_shifts": [list(s) for s in shifts], "raises_all_by_one": shifts == [(1, 1, 1, 1)],
                            "W_cubed_zero": w3 <= 1e-12, "W_nonzero_entries": int(len(r))},
                  "summary": "W (the plaquette trace) raises all four link heights by one; W^3 = 0",
                  "note": "heights A=0, Q=1, B=2 on b, r and 2, 1, 0 on t, l (operators.heights)"})
    sup = []
    all_affine = True
    for u, v, k in pairs:
        su, sv = np.flatnonzero(np.abs(u) > 0), np.flatnonzero(np.abs(v) > 0)
        du, au = _affine_dim(codes[su])
        dv, av = _affine_dim(codes[sv])
        all_affine &= bool(au and av)
        sup.append([int(len(su)), int(len(sv)), int(du), int(dv)])
    facts.append({"name": "pair_supports", "proved_by": "numerical",
                  "value": {"columns": ["n_u", "n_v", "affine_dim_u", "affine_dim_v"], "per_pair": sup, "supports_are_affine": bool(all_affine),
                            "max_support": int(max(max(s[0], s[1]) for s in sup))},
                  "summary": f"supports of u and v: sizes 2^d on GF(2) affine subspaces of dimension d (all affine: {all_affine}); "
                             f"largest support {max(max(s[0], s[1]) for s in sup)}",
                  "note": "per pair: support sizes of u and v and the GF(2) affine-subspace dimension of each support"})
    amps = np.concatenate([np.abs(x[np.abs(x) > 1e-13]) for u, v, _ in pairs for x in (u, v)])
    alphabet = sorted({round(float(a), 9) for a in amps}, reverse=True)
    facts.append({"name": "amplitude_alphabet", "proved_by": "numerical", "value": alphabet,
                  "summary": "absolute amplitudes of the pair vectors: " + ", ".join(_alphabet_label(a) for a in alphabet),
                  "note": "absolute values of all nonzero entries of the 162 pair vectors, rounded to 1e-9"})
    k_max = max(range(len(pairs)), key=lambda i: pairs[i][2])
    uu, vv, kk = pairs[k_max]
    va, vb, loop_codes = _ops.closed_codes()
    ia, ib = int(np.searchsorted(codes, va)), int(np.searchsorted(codes, vb))
    ref_u = np.zeros(len(codes)); ref_u[ia] = ref_u[ib] = 1.0 / np.sqrt(2.0)
    loop_col = np.real(W[:, ia]); ref_v = loop_col / np.linalg.norm(loop_col)
    u_ok = bool(abs(float(np.dot(uu, ref_u))) >= 1.0 - 1e-12)
    v_ok = bool(abs(float(np.dot(vv, ref_v))) >= 1.0 - 1e-12)
    facts.append({"name": "closed_bright_block", "proved_by": "numerical",
                  "value": {"kappa": float(kk), "kappa_closed_form": _kappa_label(kk), "u": "(vac_A + vac_B)/sqrt2", "v": "loop",
                            "u_is_vac_sum": u_ok, "v_is_loop": v_ok, "vac_A": int(va), "vac_B": int(vb),
                            "loop_codes": [int(x) for x in loop_codes]},
                  "summary": f"the kappa = 4 sqrt2 pair is u = (vac_A + vac_B)/sqrt2, v = loop ~ W vac_A (checked: {u_ok and v_ok}); "
                             "the closed 3x3 block lives on (vac_A, loop, vac_B)",
                  "note": "the only pair that touches the closed sector"})
    rank = int(_phys.inner_span_rank_by_corners())
    facts.append({"name": "inner_span_rank", "value": rank, "proved_by": "numerical",
                  "note": "the inner components of the physical states span all 1296 inner codes (R6 item 1: inner-block soundness)"})
    facts.append({"name": "u1_sectors", "value": int(cbf["n_u1_sectors"]), "proved_by": "numerical",
                  "note": "distinct U(1) charge sectors of the physical states (corner occupation quartets)"})
    budget = prune_budget(rishon_spec())
    facts.append({"name": "prune_rates",
                  "value": {"per_branching_gate": PRUNE_RATE_PER_BRANCHING_GATE, "budget_at_cap": budget,
                            "branching": list(PRUNE_BRANCHING), "engine_exact": list(PRUNE_ENGINE_EXACT),
                            "provenance": PRUNE_PROVENANCE},
                  "proved_by": "numerical",
                  "summary": f"growth of the sparse engine's certified pruning bound: {PRUNE_RATE_PER_BRANCHING_GATE:.1e} per branching gate "
                             f"of its lowering (budget at the cap: {budget} branching gates; macro ccx/ccz and permutation/phase gates cost 0)",
                  "note": "measured, prompts/203 section 13 E2 (METHODS-rishon R11)"})
    lean_files = sorted(str(p.relative_to(ROOT)) for p in (LEAN_DIR / "Su2Plaq" / "Rishon").glob("*.lean")) + [_HB_CERT]
    prov = {"generator": "su2plaq.rishon.compress.spec.structure_facts", "plan": "prompts/203", "methods": "docs/METHODS-rishon.md R12",
            "lean_sources": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in lean_files}}
    return {"facts": facts, "provenance": prov}


def structure_facts() -> dict:
    """{"facts": [{"name","value","proved_by": "decide"|"native"|"numerical","theorem"|"certificate","note"}], "provenance": {...}}.
    Kernel-checked and native facts are recomputed from the production code and compared with the literal in the Lean statement
    (a mismatch raises); numerical facts are computed from the operators.  Deterministic: no timestamp, no commit."""
    return copy.deepcopy(_structure_facts_cached())


def write_structure_json(path=None) -> pathlib.Path:
    """compress/specs/rishon-structure.json (default)."""
    p = pathlib.Path(path) if path is not None else _default_root() / "compress" / "specs" / "rishon-structure.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(structure_facts(), indent=1) + "\n")
    return p


def _default_root() -> pathlib.Path:
    from su2plaq.compress.spec import ROOT as LROOT

    return LROOT


# ------------------------------------------------------------------------------------------------ spec text
def prune_budget(spec) -> int:
    """How many branching gates of the engine's lowering the rishon prune cap (RISHON_PRUNE_FRACTION x tol_err, prompts/204
    section 3) allows at the measured PRUNE_RATE_PER_BRANCHING_GATE: floor(cap / rate).  The single source of the number in
    the proposers' spec text."""
    from su2plaq.rishon.verify import RISHON_PRUNE_FRACTION

    return int(math.floor(RISHON_PRUNE_FRACTION * spec.tol_err / PRUNE_RATE_PER_BRANCHING_GATE))


def _fmt_num(x: float) -> str:
    return f"{x:g}"


def _casimir_tex() -> str:
    f = Fraction(_ops.electric_coefficient()).limit_denominator(64)
    return f"\\frac{{{f.numerator}}}{{{f.denominator}}}" if f.denominator != 1 else str(f.numerator)


def _operator_text(spec) -> str:
    if spec.kind == "UE":
        return r"$U=U_E(\alpha)$"
    if spec.kind == "UB":
        return r"$U=U_B(\beta)$"
    if spec.order == 1:
        return r"$U=U_B(\beta)\,U_E(\alpha)$ (electric layer first in the circuit)"
    return r"$U=U_E(\alpha/2)\,U_B(\beta)\,U_E(\alpha/2)$"


def _gauss_count() -> tuple[int, int]:
    from su2plaq.rishon import verify as V

    n_sample = int(inspect.signature(V.verify).parameters["gauss_sample"].default)
    n_closed = len(_phys.closed_indices(_phys.rishon_basis()))
    return n_closed, n_sample


def _kappa_tex(label: str) -> str:
    return label.replace("*sqrt2", r"\sqrt2")


def _structure_section(facts: dict) -> str:
    lines = []
    numerical = []
    for f in facts["facts"]:
        if f["proved_by"] == "numerical":
            numerical.append(f)
            continue
        ref = f.get("theorem") or f.get("certificate")
        val = f["value"]
        lines.append(f"- `{f['name']}` = {json.dumps(val) if isinstance(val, (dict, list)) else val} "
                     f"(proved by {f['proved_by']}, {ref}) -- {f['note']}")
    nl = []
    for f in numerical:
        s = f.get("summary") or f"{json.dumps(f['value'])}"
        nl.append(f"- `{f['name']}`: {s}" + ("" if f.get("summary") else f" -- {f['note']}"))
    return ("## Proved structure (Lean)\n\nMachine-checked facts about the problem; the numerical evaluator remains ground truth. "
            "Trust levels: `decide` = kernel-checked Lean theorem, `native` = compiled exact-arithmetic certificate, `numerical` = "
            "computed from the operators (not a Lean statement).\n\n" + "\n".join(lines) + "\n\nNumerical structure (not proved in Lean):\n\n"
            + "\n".join(nl) + "\n")


def render_spec(spec) -> str:
    """The hand-text of prompts/203 section 4 with every number from the spec / encoding / MACRO_COST / structure_facts()."""
    from su2plaq.compress.builder import BASIS, MACRO_COST, MACROS
    from su2plaq.evaluate.evaluator import synth_tolerances
    from su2plaq.rishon.verify import RISHON_PRUNE_FRACTION as PRUNE_FRACTION

    register()
    view = _VIEW
    facts = structure_facts()
    by = {f["name"]: f for f in facts["facts"]}
    n_inner = len(view.inner_codes())
    n_phys = by["card_rishon_physical"]["value"]
    hb = by["hb_bright_pairs"]["value"]
    kap = ", ".join(f"{_kappa_tex(k)}\\ (\\times{n})" for k, n in hb["kappa_multiset"].items())
    alph = ", ".join("\\pm" + _alphabet_tex(a) for a in by["amplitude_alphabet"]["value"])
    cap = PRUNE_FRACTION * spec.tol_err
    n_budget = prune_budget(spec)
    slack = synth_tolerances(0, spec.eps)["tol_err"]
    n_closed, n_sample = _gauss_count()
    alts = ", ".join(f"({a:g}, {b:g})" for a, b in spec.alt_angles)
    costs = ", ".join(f"{m} ({c[0]}, {c[1]}, {c[2]})" for m, c in MACRO_COST.items() if m in MACROS or m == "cz")
    gates, macros = " ".join(sorted(BASIS)), " ".join(sorted(MACROS))
    tool = f"--kind {spec.kind}"
    link_t = hb["n_pairs"]
    return (
        f"# Task specification: `rishon` / `{spec.kind}`\n\n"
        f"## Task\n\nImplement {_operator_text(spec)} for the SU(2) **quantum link model** (two fermionic rishons per link, 6 link "
        f"states; Report 5, `docs/METHODS-rishon.md`) on the plaquette with 8 outer links, in the {view.n_data + view.n_outer}-qubit "
        f"Jordan-Wigner encoding, exactly (up to one global phase) on every one of the {n_inner} valid inner codes - which certifies "
        f"all {n_phys} physical states (METHODS-rishon R6) - at $(\\alpha,\\beta)=({spec.alpha:g},{spec.beta:g})$ and, with the same "
        f"gate skeleton (gate names and qubits; angles may differ), at {alts}. Invalid codes are don't-care. Every ancilla must "
        "return to $|0\\rangle$. Angles must be computed from the spec's `alpha`/`beta` (and the oracle), never typed in.\n\n"
        f"## Registers\n\n{view.describe()}\n"
        f"Writing the outer register is rejected as `writes_outer`. The outer qubits are in the layout because the machinery fixes "
        f"`d` + `o`; they count in the key's qubit component ({view.n_data + view.n_outer} + ancillas). **Effective qubit limit: "
        f"{ENGINE_QUBIT_LIMIT} qubits in total, i.e. at most {ENGINE_QUBIT_LIMIT - view.n_data - view.n_outer} ancillas** (the exact "
        f"simulation engine stores basis states in 64-bit keys); a circuit with more qubits is invalid as `{REASON_ENGINE_QUBIT_LIMIT}`.\n\n"
        f"## Target structure (exact)\n\n$U_E^{{\\rm in}}=\\mathrm{{diag}}(e^{{-i{_casimir_tex()}\\alpha\\,\\#Q}})$ with $\\#Q$ the number "
        f"of inner links in a quartet state (`1010`, `0110`, `1001`, `0101`); "
        f"$U_B^{{\\rm in}}=\\prod_{{p=1}}^{{{hb['n_pairs']}}}\\exp\\big(i\\beta\\kappa_p(|u_p\\rangle\\langle v_p|+{{\\rm h.c.}})\\big)$ with "
        f"$\\kappa\\in\\{{{kap}\\}}$, {hb['dark_codes']} dark codes, real pair vectors with amplitudes in $\\{{{alph}\\}}$ supported on "
        f"affine GF(2) subspaces; the {link_t} blocks commute. `get_encoding(\"rishon\").bright_pairs()` returns them; "
        "`python -m su2plaq.rishon.compress.oracle --pairs`. The facts of `structure_facts()` with their trust level are listed in "
        "the proved-structure section below.\n\n"
        f"## Circuit model\n\nGates `{gates}` and macros `{macros}` with costs (CX, T, rotations) from the builder table: {costs}. "
        "`Builder.alloc/free` for clean ancillas; `Builder.mcx` for 3 or more controls ((k-2) rccx + ccx + (k-2) rccx; native mcx, "
        "mcrx, cu, unitary and measurement are rejected); at most "
        f"{min(spec.peak_qubit_cap(), ENGINE_QUBIT_LIMIT)} qubits in total (the engine limit; the nominal cap is "
        f"{spec.peak_qubit_cap()}); no measurement; emission-time classical computation is allowed "
        "(`su2plaq.compress.oracle`, `su2plaq.compress.spec.get_encoding(\"rishon\")`, numpy).\n\n"
        f"## Correctness\n\n`op_norm_error` = block error + leak amplitude + certified pruning bound must be at most {spec.tol_err:g} "
        f"after one global phase; `dropped_total` must be at most {cap:g} (**prune cap** = {PRUNE_FRACTION:g} x tolerance for this encoding; measured on "
        f"this task the engine's certified pruning bound grows by about {PRUNE_RATE_PER_BRANCHING_GATE:.1e} per branching gate of its lowering "
        f"(h, sx, u; ch, crx and rccx count 2; macro ccx/ccz and all permutation/phase gates count 0), so the cap allows about {n_budget} "
        "branching gates; exact circuits above that are rejected as `pruning_bound` - the uncompressed circuit in bare h/t form, its "
        "rccx-ladder variants and its Qiskit L3 transpile use about 3 500-4 400 of them and pass); "
        f"Gauss residual of the outputs on {n_closed + n_sample} sampled "
        f"physical states ({n_closed} closed + {n_sample} seeded) at most {spec.tol_gauss:g}; identical skeleton at the three angle "
        f"pairs; evaluation wall at most {spec.eval_budget_s:g} s and at most {spec.support_cap} stored amplitudes; synthesised "
        f"re-verification of the round's best at $\\varepsilon={spec.eps:g}$ with $N_{{\\rm rot}}\\varepsilon+{slack:g}$. "
        "The evaluator is ground truth.\n\n"
        f"## Cost\n\nKey $(\\mathrm{{CX}},\\,T_{{\\varepsilon}},\\,\\mathrm{{depth}}_{{\\rm CT}},\\,\\mathrm{{qubits}})$, lexicographic. "
        f"$T_\\varepsilon=T_{{\\rm fixed}}+\\sum_r T_r$ with each rotation $T_r$ measured with pygridsynth at $\\varepsilon={spec.eps:g}$; "
        f"estimate $3\\log_2(1/\\varepsilon)$ per rotation. MAP-Elites cells "
        f"$(\\lfloor{spec.cell_k}\\log_2(\\mathrm{{CX}}+1)\\rfloor,\\lfloor{spec.cell_k}\\log_2(T_\\varepsilon+1)\\rfloor)$. "
        "Reference (round 0, measured by the evaluator, not typed here): the general circuit's row.\n\n"
        f"## Lean\n\nRotation angles of the form $(m_\\alpha\\alpha+m_\\beta\\beta+m_\\gamma\\sqrt2\\beta)/d$, $d\\le64$, make the circuit "
        "certifiable for all angles by the rishon three-angle checker (status `certified`); other emission-time angles give `n_a`. "
        "Informative only: Lean never changes validity.\n\n"
        f"{_structure_section(facts)}\n"
        "## Tools\n\n"
        f"`python -m su2plaq.rishon.compress.run_candidate <program.py> {tool} --trial` (seconds; {spec.trial_inputs} of the "
        f"{n_inner} inner codes, nominal angles, no Gauss sample, T estimate) or `--full`. **A trial `valid` is not a validity "
        "verdict**: it can miss a wrong controlled rotation that acts on few codes "
        "(reports/tests/215: most single-gate errors passed it); only `--full` (all codes, three angle pairs, Gauss sample) decides, so run `--full` before you finish.\n"
        f"`python -m su2plaq.rishon.compress.oracle {tool} [--column j] [--element i j] [--codec [--state k]] [--pairs [--closed]] "
        "[--block]` prints the exact target (matrix column, element, codec, bright pairs, closed 3x3 block).\n\n"
        "Program contract: ONE file `compress/programs/rishon/<family>/NNN-slug.py` whose docstring starts with `SUMMARY: ...` "
        "followed by at most 3 `DISCOVERY: ...` lines, with `FAMILY = \"...\"`, `PARENT = \"...\" | None` and "
        "`def build(spec) -> Builder`; imports: numpy, standard maths modules, qiskit and `su2plaq.compress.{oracle,builder,spec}` "
        "only.\n")


def write_spec(spec, path=None) -> pathlib.Path:
    """compress/specs/rishon-<kind>.md (default); the committed file must equal `render_spec(spec)`."""
    p = pathlib.Path(path) if path is not None else _default_root() / "compress" / "specs" / f"rishon-{spec.kind}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_spec(spec))
    return p
