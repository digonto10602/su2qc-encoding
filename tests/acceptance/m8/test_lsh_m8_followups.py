"""M8-A1..A4 — follow-ups of the M7 audit (reports/audits/303 notes N1, N2, N3, N4, N8; prompts/401 §3 steps 8.A1-8.A3).

A1 (N1): a kernel-checked theorem ties the exported table `lshInnerCodes` of lean/Su2Plaq/LSH/Circuit.lean to the LSH rules
    counted in Counts.lean (flux cap + Abelian Gauss law), so that every circuit-structure theorem speaks about the codes the
    count theorems count; plus the raw-bit structure facts offered to the M8 proposers (new file lean/Su2Plaq/LSH/Facts.lean).
    Planner prototype: scratch/planner/lean/LSHTie.lean (8 theorems, `lake env lean` 5.0 s, standard axioms only).
A2 (N2, N3): the committed certificate of the general step was generated on a clean commit that contains the exporter, records
    `git_dirty`, is linked from results/lsh/step.json (`extra.lean`) and equals a fresh export of the circuit it names; `certify`
    carries binding fields into the certificate and does not rewrite an unchanged certificate (the locked M7-L3 test used to
    dirty the tree on every run).
A3 (N4): negative controls that REACH the compiled checker (status `rejected`, not the exporter's `n_a`).
    Planner prototype: scratch/planner/m8/proto_m8_negative.py (9 rejections, 0.2-0.5 s each).  This test locks behaviour that
    exists since step 7.L3: it is green at lock time.
A4 (N8): source hygiene of BOTH Lean folders of the encoding; the checker docstring names base (8, 4) for order 2.

Tolerances: none (exact text, hashes, statuses); 900 s per Lean call as in M7-L1..L3 (prompts/006 §7).
PENDING rule: a missing file / attribute / keyword fails with `PENDING:` (conftest + `_api.api`)."""
from __future__ import annotations

import hashlib
import inspect
import json
import pathlib
import re
import subprocess
import time

import pytest

from tests.acceptance._api import api

STANDARD = {"propext", "Classical.choice", "Quot.sound"}
NOMINAL = (0.37, 0.61)
EXPORTER_COMMIT = "731da36"            # M7 step 7.L3: first commit that contains lsh.lean_export.export_certificate (audit 303 N2)
FACTS_FILE = "Su2Plaq/LSH/Facts.lean"
# theorem (namespace Su2Plaq.LSH) -> text that must occur in its statement (between `theorem <name>` and `:= by`)
FACT_THEOREMS = {
    "inner_codes_from_rules": ["lshInnerCodes = (List.range 4096).filter innerOK"],
    "coupling_zero_iff_dark": ["bright"],
    "dark_site_is_and": ["n3"],
    "coupling_by_y_weight": ["bright", "-4", "2", "-1"],
    "link_bit_two_ways": ["% 2"],
    "move_per_site": ["lshPartner", "then 1 else 6"],
    "y_parity_invariant": ["lshPartner", "% 2"],
    "eight_differences": ["lshPartner", "= 8"],
}


def _lean_file(root: pathlib.Path, rel: str, step: str) -> pathlib.Path:
    p = root / "lean" / rel
    if not p.exists():
        pytest.fail(f"PENDING: lean/{rel} missing (prompts/401 step {step})", pytrace=False)
    return p


def _enc():
    return api("su2plaq.encodings.lsh:LSH")()


def _general(alpha=NOMINAL[0], beta=NOMINAL[1], order=1):
    return api("su2plaq.circuits.lsh:build_step")(alpha, beta, order, with_outer=True)


def _certify_with_binding():
    LE = api("su2plaq.lsh.lean_export")
    if "extra_provenance" not in inspect.signature(LE.certify).parameters:
        pytest.fail("PENDING: lsh.lean_export.certify has no keyword extra_provenance (prompts/401 step 8.A2)", pytrace=False)
    return LE


# ------------------------------------------------------------------------------------------------ A1 (audit 303 N1)
def test_M8_A1_lean_tables_tied_to_rules(root):
    """lean/Su2Plaq/LSH/Facts.lean imports Counts and Circuit and proves, with `decide` and the standard axioms only, that the
    exported code list is exactly the set cut out by the counted LSH rules, and the raw-bit facts used in the proposer spec.
    The same facts are recomputed here from the production Python objects (47 codes, coupling and partner tables)."""
    p = _lean_file(root, FACTS_FILE, "8.A1")
    src = p.read_text()
    assert "native_decide" not in src and "sorry" not in src and "admit" not in src
    assert "import Su2Plaq.LSH.Counts" in src and "import Su2Plaq.LSH.Circuit" in src and "namespace Su2Plaq.LSH" in src
    assert "import Su2Plaq.LSH.Facts" in (root / "lean" / "Su2Plaq.lean").read_text()
    for short, needles in FACT_THEOREMS.items():
        assert re.search(rf"^theorem {short}\b", src, re.M), short
        stmt = src.split(f"theorem {short}", 1)[1].split(":= by", 1)[0]
        for needle in needles:
            assert needle in stmt, (short, needle, stmt)
    # the same statements, recomputed from the production objects
    enc = _enc()
    W = api("su2plaq.lsh.walk")
    O = api("su2plaq.lsh.operators")
    codes = enc.inner_codes().tolist()
    assert codes == [x for x in range(4096) if all(O.site_valid((x >> (3 * c)) & 7) for c in range(4))
                     and not [v for v in O.agl_violations(x) if v in ("b", "r", "t", "l")]] and len(codes) == 47
    table, ptab = W.coupling_table(enc), W.partner_table(enc)
    X = lambda x, c: (x >> (3 * c)) & 1
    Y = lambda x, c: (x >> (3 * c + 1)) & 1
    Z = lambda x, c: (x >> (3 * c + 2)) & 1
    bright = [x for x in codes if x in ptab]
    assert len(bright) == 16
    for x in codes:
        dark_sites = [c for c in range(4) if Y(x, c) & Z(x, c)]
        assert (x not in ptab) == bool(dark_sites) == (abs(table[x]) < 1e-12)                     # coupling_zero_iff_dark, dark_site_is_and
        assert all((X(x, c) ^ Y(x, c)) == (X(x, (c + 1) % 4) ^ Z(x, (c + 1) % 4)) for c in range(4))   # link_bit_two_ways
    by_weight = {}
    for x in bright:
        sy, sz = sum(Y(x, c) for c in range(4)), sum(Z(x, c) for c in range(4))
        assert sy == sz <= 2
        by_weight.setdefault(sy, set()).add(round(2 * table[x]))
        d = x ^ ptab[x]
        assert all(((d >> (3 * c)) & 7) == (6 if Y(x, c) ^ Z(x, c) else 1) for c in range(4))        # move_per_site
        assert sum(Y(ptab[x], c) for c in range(4)) % 2 == sy % 2 and (sy % 2 == 1) == (round(2 * table[x]) == 2)   # y_parity_invariant
    assert by_weight == {0: {-4}, 1: {2}, 2: {-1}}                                                 # coupling_by_y_weight
    assert len({x ^ ptab[x] for x in bright}) == 8                                                 # eight_differences
    P = api("su2plaq.lean.project")
    names = [f"Su2Plaq.LSH.{s}" for s in FACT_THEOREMS]
    t0 = time.time()
    ax = P.print_axioms(names, timeout=900)
    assert time.time() - t0 <= 900
    missing = [n for n in names if n not in ax or "<unknown>" in ax[n]]
    assert not missing, missing
    bad = {n: sorted(ax[n] - STANDARD) for n in names if ax[n] - STANDARD}
    assert not bad, bad


# ------------------------------------------------------------------------------------------------ A2 (audit 303 N2, N3)
def test_M8_A2_committed_certificate_clean_provenance(root, tmp_path):
    """results/lsh/step.json names the Lean certificate of the general step (`extra.lean`); the certificate file was written
    on a clean commit that contains the exporter, records `git_dirty: false`, and its gates / states / target / phase equal a
    fresh export of build_step(0.37, 0.61, 1, with_outer=True) (31 qubits): the file is the certificate of that circuit."""
    f = root / "results" / "lsh" / "step.json"
    if not f.exists():
        pytest.fail("PENDING: results/lsh/step.json missing", pytrace=False)
    d = json.loads(f.read_text())
    lean = d["extra"].get("lean")
    if lean is None:
        pytest.fail("PENDING: results/lsh/step.json has no extra.lean (prompts/401 step 8.A2: scripts/m7_results.py on a clean commit)",
                    pytrace=False)
    assert lean["status"] == "certified" and lean["trust"] == "native-certified"
    assert lean["circuit"] == "build_step(0.37, 0.61, 1, with_outer=True)" and lean["n_qubits"] == 31
    assert not pathlib.Path(lean["cert_path"]).is_absolute()
    cp = root / lean["cert_path"]
    assert cp.exists() and cp.parent == root / "results" / "lsh" / "certs"
    raw = cp.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == lean["cert_sha256"]
    cert = json.loads(raw)
    prov = cert["provenance"]
    assert prov["git_dirty"] is False and d["provenance"]["git_dirty"] is False
    a, b = str(prov["git_commit"]), str(d["provenance"]["git_commit"])
    assert len(a) >= 7 and (a.startswith(b) or b.startswith(a)), (a, b)          # one clean snapshot for results and certificate
    r = subprocess.run(["git", "merge-base", "--is-ancestor", EXPORTER_COMMIT, a], cwd=root, capture_output=True)
    assert r.returncode == 0, f"certificate commit {a} does not contain the exporter (needs a descendant of {EXPORTER_COMMIT})"
    assert cert["schema"] == "su2plaq-cert-1" and cert["circuit_id"] == lean["circuit_id"] == cp.stem
    assert cert["n_qubits"] == 31 and cert["n_data"] == 12 and cert["n_outer"] == 12 and len(cert["states"]) == 433
    assert cert["target"]["kind"] == "step" and cert["target"]["order"] == 1
    gates_sha = hashlib.sha256(json.dumps(cert["gates"]).encode()).hexdigest()
    assert cert["gates_sha256"] == cert["program_sha256"] == gates_sha and cert["circuit_id"].endswith(gates_sha[:12])
    LE = api("su2plaq.lsh.lean_export")
    out = LE.export_certificate(_general(), _enc(), "step", *NOMINAL, 1, tmp_path / "fresh.json")
    assert not isinstance(out, str), out
    fresh = json.loads(pathlib.Path(out).read_text())
    for key in ("gates", "states", "target", "phase", "base", "n_qubits"):
        assert fresh[key] == cert[key], key


@pytest.mark.slow
def test_M8_A2_certify_binding_fields_and_idempotent_write(tmp_path):
    """`certify(..., extra_provenance=...)` writes the binding fields (entry id, program-file sha256) INSIDE the certificate,
    records `git_dirty` and `gates_sha256`, and leaves an existing certificate untouched when only volatile provenance
    (commit, dirty flag, timings) would change; a changed binding rewrites it; no temporary file is left behind."""
    LE = _certify_with_binding()
    enc, qc = _enc(), _general()
    bind = {"entry_id": "r00-seed-000", "program_file_sha256": "ab" * 32}
    t0 = time.time()
    r1 = LE.certify(qc, enc, "step", *NOMINAL, 1, out_dir=tmp_path, extra_provenance=bind)
    assert time.time() - t0 <= 900
    assert r1["status"] == "certified", (r1["status"], r1.get("reason"))
    f = pathlib.Path(r1["cert_path"])
    assert f.parent == tmp_path
    b1 = f.read_bytes()
    c = json.loads(b1)
    assert c["provenance"]["entry_id"] == bind["entry_id"] and c["provenance"]["program_file_sha256"] == bind["program_file_sha256"]
    assert isinstance(c["provenance"]["git_dirty"], bool) and len(str(c["provenance"]["git_commit"])) >= 7
    assert c["gates_sha256"] == c["program_sha256"] == hashlib.sha256(json.dumps(c["gates"]).encode()).hexdigest()
    r2 = LE.certify(_general(), enc, "step", *NOMINAL, 1, out_dir=tmp_path, extra_provenance=dict(bind))
    assert r2["status"] == "certified" and pathlib.Path(r2["cert_path"]) == f and f.read_bytes() == b1
    r3 = LE.certify(qc, enc, "step", *NOMINAL, 1, out_dir=tmp_path, extra_provenance={**bind, "entry_id": "r01-F1-001"})
    assert r3["status"] == "certified" and json.loads(f.read_bytes())["provenance"]["entry_id"] == "r01-F1-001"
    r4 = LE.certify(qc, enc, "step", *NOMINAL, 1, out_dir=tmp_path)                       # no binding: fields absent, same file name
    assert r4["status"] == "certified" and "entry_id" not in json.loads(f.read_bytes())["provenance"]
    assert sorted(p.name for p in tmp_path.iterdir()) == [f.name]


# ------------------------------------------------------------------------------------------------ A3 (audit 303 N4)
@pytest.mark.slow
def test_M8_A3_negative_controls_reach_the_checker(tmp_path):
    """Wrong circuits whose angles ARE rational multiples of alpha / beta pass the exporter and must be refused by the compiled
    checker `su2plaq_cert_lsh` itself: status `rejected` with a reason (the locked M7-L3 control, beta (1 + 1e-6), stops in the
    exporter as `n_a` and never exercises the checker).  A correct circuit is `certified` in the same run."""
    LE = api("su2plaq.lsh.lean_export")
    C = api("su2plaq.circuits.lsh")
    enc = _enc()
    a, b = NOMINAL
    good = LE.certify(_general(), enc, "step", a, b, 1, out_dir=tmp_path)
    assert good["status"] == "certified", (good["status"], good.get("reason"))
    extra_x, dirty, outer = _general(), _general(), _general()
    extra_x.x(0)
    dirty.x(24)                                   # first ancilla (data 0..11, outer 12..23)
    outer.x(12)
    cases = {
        "order-1 circuit, order-2 target": (_general(order=1), "step", 2),
        "order-2 circuit, order-1 target": (_general(order=2), "step", 1),
        "minus beta": (_general(beta=-b), "step", 1),
        "U_B circuit, step target": (C.build_UB(b, with_outer=True), "step", 1),
        "U_E circuit, U_B target": (C.build_UE(a, with_outer=True), "UB", 1),
        "extra x on d[0]": (extra_x, "step", 1),
        "dirty ancilla": (dirty, "step", 1),
        "outer qubit written": (outer, "step", 1),
    }
    for name, (qc, kind, order) in cases.items():
        t0 = time.time()
        r = LE.certify(qc, enc, kind, a, b, order, out_dir=tmp_path)
        assert time.time() - t0 <= 900
        assert r["status"] == "rejected", (name, r["status"], r.get("reason"))
        assert r["reason"], name


# ------------------------------------------------------------------------------------------------ A4 (audit 303 N8)
def test_M8_A4_lean_hygiene_both_folders(root):
    """No `native_decide` / `sorry` / `admit` in lean/Su2Plaq/LSH/ (kernel-checked library) nor in lean/Su2PlaqCert/LSH/ (compiled
    checker: `native_decide` belongs to the theorem files under lean/certs/ only); the checker does not import Mathlib; its
    docstring names both target bases; the entry point's header does not call itself a copy of itself."""
    _lean_file(root, FACTS_FILE, "8.A1")
    lib = sorted((root / "lean" / "Su2Plaq" / "LSH").glob("*.lean"))
    cert = sorted((root / "lean" / "Su2PlaqCert" / "LSH").glob("*.lean"))
    assert {p.name for p in lib} >= {"Counts.lean", "Circuit.lean", "Facts.lean"}
    assert {p.name for p in cert} >= {"Check.lean", "Main.lean", "Pins.lean"}
    for p in lib + cert:
        src = p.read_text()
        for word in ("native_decide", "sorry", "admit"):
            assert word not in src, (p.name, word)
    for p in cert:
        assert not re.search(r"^import Mathlib", p.read_text(), re.M), p.name
    check = (root / "lean" / "Su2PlaqCert" / "LSH" / "Check.lean").read_text()
    doc = check.split("/-!", 1)[1].split("-/", 1)[0]
    assert "(4, 4)" in doc and "(8, 4)" in doc and "order 2" in doc
    main = (root / "lean" / "Su2PlaqCert" / "LSH" / "Main.lean").read_text()
    assert "copy of `su2plaq_cert_lsh`" not in main          # the checker is a copy of the spin-network one (reports/tests/406)
