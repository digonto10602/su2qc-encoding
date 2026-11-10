"""M6-K0..K3 — rishon compression spec, view, oracle and structure facts (prompts/203 §3.1, §4, §6; METHODS-rishon R10).
Everything here is exact (definitions, integer gate counts) except two 1e-12 / 1e-14 float comparisons justified in
prompts/203 §6.  PENDING rule: a missing `su2plaq.rishon.compress` name fails with `PENDING:` (never a collection error)."""
import functools
import inspect
import json
import pathlib

import numpy as np
import pytest

from tests.acceptance._api import api

ENC, KIND = "rishon", "step"
NOMINAL, ALT = (0.37, 0.61), ((0.91, 0.23), (1.70, 1.00))
# research 202 §3 (measured with the production code path at beta = 0.61): gate counts of the three ladder styles
LADDER_COUNTS = {"ccx": {"ccx": 1402, "rccx": 0}, "rccx": {"ccx": 54, "rccx": 1620}, "mcx": {"ccx": 216, "rccx": 1458}}
REQUIRED_FACTS = {   # name -> (value or None if free-form, proved_by)
    "card_rishon_physical": (38432, "decide"), "card_rishon_closed": (4352, "decide"), "card_inner_codes": (1296, "decide"),
    "jw_string_free": (True, "decide"), "corner_kernel_dims": (81, "decide"), "ue_exact_all_codes": (True, "decide"),
    "hb_bright_pairs": (None, "native"), "heights_raising": (None, "numerical"), "pair_supports": (None, "numerical"),
    "amplitude_alphabet": (None, "numerical"), "closed_bright_block": (None, "numerical"), "inner_span_rank": (1296, "numerical"),
    "u1_sectors": (431, "numerical"), "prune_rates": (None, "numerical"),
}
SPEC_PHRASES = ("quantum link model", "1296", "38432", "outer_read_unsupported", "pruning", "rccx", "ccx", "1e-10", "1e-11",
                "su2plaq.rishon.compress.run_candidate", "su2plaq.rishon.compress.oracle", "Proved structure (Lean)", "DISCOVERY",
                "4\\sqrt2", "sqrt2", "kappa", "0.37", "0.61", "80")


@functools.lru_cache(maxsize=None)
def _spec(kind=KIND):
    return api("su2plaq.rishon.compress.spec:rishon_spec")(kind)


def _quartet_casimir_reference() -> float:
    """Independent numpy reference (no project import): H_E = (1/2) sum_a (L_a^2 + R_a^2) on the link code Q = 1010 (= 5)
    with c_k = (prod_{m<k} Z_m) sigma^-_k on 4 modes (L1, L2, R1, R2), T_a = sigma_a / 2 (METHODS-rishon R1/R2)."""
    I2, Z, SM = np.eye(2), np.diag([1.0, -1.0]), np.array([[0, 1], [0, 0]], dtype=complex)
    sig = [np.array([[0, 1], [1, 0]], complex), np.array([[0, -1j], [1j, 0]]), np.diag([1.0 + 0j, -1.0])]

    def kron(ops):      # ops[0] on the least significant qubit
        out = np.array([[1.0 + 0j]])
        for o in ops:
            out = np.kron(o, out)
        return out

    c = [kron([Z] * k + [SM] + [I2] * (3 - k)) for k in range(4)]
    cd = [m.conj().T for m in c]
    gens = []
    for end in ((0, 1), (2, 3)):
        for a in range(3):
            gens.append(sum((sig[a][i, j] / 2) * cd[end[i]] @ c[end[j]] for i in range(2) for j in range(2)))
    H = 0.5 * sum(g @ g for g in gens)
    q, a_code, b_code = 5, 3, 12
    assert abs(H[a_code, a_code]) <= 1e-14 and abs(H[b_code, b_code]) <= 1e-14
    return float(H[q, q].real)


def test_M6_K0_ladder_variants_and_casimir():
    """build_UB/build_step accept ladder in {ccx, rccx, mcx} (default ccx, M5 circuit unchanged); the gate counts are the
    measured ones (research 202 §3); the electric coefficient comes from the link algebra (audit 201 N4), equals the
    independent Casimir 3/4 to 1e-14, and is what the circuit, the inner operator and the outer-row certificate use."""
    C = api("su2plaq.circuits.rishon")
    O = api("su2plaq.rishon.operators")
    R = api("su2plaq.rishon.results")
    coef = api("su2plaq.rishon.operators:electric_coefficient")()      # PENDING until step 6.0 (before the ladder keyword is used)
    default = C.build_UB(0.61).count_ops()
    for ladder, want in LADDER_COUNTS.items():
        qc = C.build_UB(0.61, ladder=ladder)
        ops = qc.count_ops()
        assert ops.get("ccx", 0) == want["ccx"] and ops.get("rccx", 0) == want["rccx"], (ladder, dict(ops))
        assert ops.get("crx", 0) == 81
        st = C.build_step(0.37, 0.61, 1, ladder=ladder).count_ops()
        assert st.get("rccx", 0) == want["rccx"] and st.get("ccx", 0) == want["ccx"]
    assert dict(default) == dict(C.build_UB(0.61, ladder="ccx").count_ops())
    assert abs(coef - _quartet_casimir_reference()) <= 1e-14 and abs(coef - 0.75) <= 1e-14
    he = O.h_electric_inner()
    codes = O.inner_codes()
    n_q = np.array([sum(((int(c) >> (4 * l)) & 15) in (5, 6, 9, 10) for l in range(4)) for c in codes])
    assert he.shape == (1296,) and np.abs(he - coef * n_q).max() <= 1e-14
    # wiring: the three production sites take the coefficient from operators.electric_coefficient; no typed literal in code
    import ast
    for fn in (C._emit_ue, O.h_electric_inner, R.outer_electric_certify):
        src = inspect.cleandoc(inspect.getsource(fn)) if inspect.getsource(fn)[0].isspace() else inspect.getsource(fn)
        doc = ast.get_docstring(ast.parse(src).body[0]) or ""
        code_lines = [ln for ln in src.replace(doc, "").splitlines() if not ln.strip().startswith("#")]
        body = "\n".join(code_lines)
        assert "electric_coefficient" in body, fn.__name__
        assert "0.75" not in body and "3 / 4" not in body and "3/4" not in body, fn.__name__


def test_M6_K1_spec_view_and_oracle():
    """rishon_spec fields (prompts/203 §3.1); the view is registered with the laptop machinery; the oracle target is the
    inner operator (1296 x 1296); column / element / codec / pairs / closed block are consistent with it."""
    spec = _spec()
    assert spec.encoding == ENC and spec.kind == KIND and (spec.alpha, spec.beta) == NOMINAL and spec.order == 1
    assert tuple(spec.alt_angles) == ALT and spec.tol_err == 1e-10 and spec.tol_gauss == 1e-10 and spec.eps == 1e-6
    assert spec.max_qubits is None and spec.peak_qubit_cap() == 80 and spec.eval_budget_s == 300.0 and spec.support_cap == 5_000_000
    assert spec.trial_inputs == 64 and spec.trial_seed == 0 and len(spec.sha256()) == 64
    get_encoding = api("su2plaq.compress.spec:get_encoding")
    view = get_encoding(ENC)
    assert view.name == ENC and view.n_data == 16 and view.n_outer == 32 and len(view.basis.labels) == 1296
    assert api("su2plaq.compress.spec:default_spec")(ENC, KIND).sha256() == spec.sha256()
    O = api("su2plaq.rishon.operators")
    codes = O.inner_codes()
    assert np.array_equal(view.inner_codes(), codes) and view.basis.index((int(codes[7]),)) == 7
    oracle = api("su2plaq.rishon.compress.oracle")
    lap = api("su2plaq.compress.oracle")
    V = oracle.target(spec)
    assert V.shape == (1296, 1296) and np.abs(V - O.inner_target("step", 0.37, 0.61, 1)).max() <= 1e-12
    assert np.abs(lap.target(spec) - V).max() <= 1e-12
    col = oracle.column(spec, 0, top=5)
    assert 1 <= len(col) <= 5 and abs(col[0][1] - V[col[0][0], 0]) <= 1e-12 and abs(col[0][1]) >= np.abs(V[:, 0]).max() - 1e-12
    assert abs(oracle.element(spec, 3, 3) - V[3, 3]) <= 1e-12
    text = oracle.codec(spec, 0)
    assert "1100" in text and "0011" in text and "State 0" in text
    pairs = oracle.pairs(spec)
    kappas = sorted(round(p["kappa"], 9) for p in pairs)
    assert len(pairs) == 81 and kappas.count(1.0) == 32 and kappas.count(2.0) == 48 and kappas.count(round(4 * np.sqrt(2), 9)) == 1
    for p in pairs[:5]:
        for vec in ("u", "v"):
            amps = np.array([a for _, a in p[vec]])
            assert abs(np.linalg.norm(amps) - 1) <= 1e-12 and all(int(c) in set(codes.tolist()) for c, _ in p[vec])
    blk = oracle.closed_block(spec)
    assert blk.shape == (3, 3) and np.abs(blk.conj().T @ blk - np.eye(3)).max() <= 1e-10
    vp = view.bright_pairs()
    assert len(vp) == 81 and abs(vp[0][2] - O.bright_pairs()[0][2]) <= 1e-12
    assert isinstance(view.heights(int(codes[0])), tuple) and len(view.heights(int(codes[0]))) == 4
    assert isinstance(view.import_map("paulo34"), str)


def test_M6_K2_structure_facts_and_spec_text(root, tmp_path):
    """structure_facts(): the required names with their proved_by; the JSON writer; the committed spec file equals the
    renderer's output and carries the required phrases (prompts/203 §4)."""
    spec = _spec()
    S = api("su2plaq.rishon.compress.spec")
    # prompts/204 section 3 (Digonto 2026-11-10): the rishon prune cap is 10 % of tol_err = 1e-11; PENDING until it is built
    assert api("su2plaq.rishon.verify:RISHON_PRUNE_FRACTION") == 0.1
    facts = S.structure_facts()
    by = {f["name"]: f for f in facts["facts"]}
    for name, (value, proved_by) in REQUIRED_FACTS.items():
        assert name in by, name
        assert by[name]["proved_by"] == proved_by, (name, by[name]["proved_by"])
        if value is not None:
            assert by[name]["value"] == value, (name, by[name]["value"])
        if proved_by == "decide":
            assert str(by[name].get("theorem", "")).startswith("Su2Plaq."), name
        if proved_by == "native":
            assert "rishon-hb-structure" in str(by[name].get("certificate", "")), name
    hb = by["hb_bright_pairs"]["value"]
    assert hb["n_pairs"] == 81 and hb["dark_codes"] == 990 and hb["vectors"] == 162 and set(hb["kappa_multiset"].values()) == {32, 48, 1}
    pr = by["prune_rates"]["value"]            # prompts/203 §13 E2: one rate per branching gate of the engine's lowering + the budget
    assert {"per_branching_gate", "budget_at_cap", "branching", "engine_exact"} <= set(pr)
    assert 1e-16 <= pr["per_branching_gate"] <= 1e-14 and pr["budget_at_cap"] == int(np.floor(1e-11 / pr["per_branching_gate"]))
    assert "h" in pr["branching"] and "ccx" in pr["engine_exact"] and "cx" in pr["engine_exact"]
    p = S.write_structure_json(tmp_path / "rishon-structure.json")
    d = json.loads(pathlib.Path(p).read_text())
    assert {f["name"] for f in d["facts"]} >= set(REQUIRED_FACTS) and "provenance" in d
    committed = root / "compress" / "specs" / "rishon-step.md"
    assert committed.exists(), "compress/specs/rishon-step.md not written (step 6.1)"
    text = committed.read_text()
    assert text == S.render_spec(spec), "the committed spec is not the renderer's output"
    for needle in SPEC_PHRASES:
        assert needle in text, needle
    assert "1e-12" not in text, "the spec still quotes the 1 % cap (prompts/204 section 3)"
    # prompts/203 §13 E3 (headline rule): the spec carries the section before "## Tools" (PENDING until the robust module exists)
    title = api("su2plaq.rishon.compress.robust:HEADLINE_SECTION_TITLE")
    assert title in text and text.index(title) < text.index("## Tools") and "robust key" in text and "pi/4" in text.replace("\\pi/4", "pi/4").replace("\\pi", "pi")
    assert "U_B" in text and "U_E" in text and "12-qubit" not in text and "433" not in text
    sj = root / "compress" / "specs" / "rishon-structure.json"
    assert sj.exists() and json.loads(sj.read_text())["facts"]


def test_M6_K3_builder_registers_and_cap():
    """Builder(rishon_spec()) fixes d (16) + o (32) and exposes the link / outer registers; ancillas start at 48; the peak
    cap is 80; a program-contract header parses for the seed family."""
    spec = _spec()
    B = api("su2plaq.compress.builder")
    b = B.Builder(spec)
    assert b.n_fixed == 48 and b.peak_qubits == 48
    assert b.reg("d") == list(range(16)) and b.reg("o") == list(range(16, 48))
    assert b.reg("link_b") == [0, 1, 2, 3] and b.reg("link_l") == [12, 13, 14, 15] and b.reg("outer_7") == [44, 45, 46, 47]
    a = b.alloc(2, "work")
    assert a == [48, 49] and b.peak_qubits == 50
    b.cx(0, 1); b.rccx(0, 1, a[0]); b.crx(2 * spec.beta, a[0], 2); b.rccx(0, 1, a[0]); b.cx(0, 1); b.free(a)
    qc = b.circuit()
    assert qc.num_qubits == 50 and [r.name for r in qc.qregs][:2] == ["d", "o"]
    assert spec.peak_qubit_cap() == 80
    # the program contract the seed programs must satisfy (prompts/002 §2.10): SUMMARY docstring, DISCOVERY lines, FAMILY,
    # PARENT and `def build(spec)`; the laptop parser rejects a source without build (prompts/203 erratum E1)
    header = '"""SUMMARY: s\nDISCOVERY: d\n"""\nFAMILY = "seed"\nPARENT = None\n'
    hdr = B.parse_program_header(header + "\n\ndef build(spec):\n    return Builder(spec)\n")
    # the laptop parser keeps the whole `DISCOVERY: ...` line (that is how compress/discoveries/<enc>.md records them)
    assert hdr["family"] == "seed" and hdr["parent"] is None and hdr["discoveries"] == ["DISCOVERY: d"] and hdr["summary"] == "s"
    with pytest.raises(B.BuilderError):
        B.parse_program_header(header)
