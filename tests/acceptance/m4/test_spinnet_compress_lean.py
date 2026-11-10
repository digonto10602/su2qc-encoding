"""M4 — Lean inside the spin-network compression loop (prompts/104 §1 "Lean", §4 L1–L5; prompts/006 trust levels).

Per-circuit certificates are exact (Laurent polynomials over K = Q(i, sqrt2, sqrt3), base angles alpha/4, beta/4) and are
checked by OUR entry point `su2plaq_cert_spinnet` (laptop checker modules, spin-network pins); kernel-checked structure
facts from lean/Su2Plaq/SpinNet/*.lean are rendered into the task specification.  Lean never decides validity.  The only
numbers are time limits (prompts/006 §7, prompts/104 §4).

PENDING rule: missing module / attribute / NotImplementedError, or a missing lean/ project, fails with `PENDING:`."""
from __future__ import annotations

import functools
import json
import pathlib
import re
import subprocess
import time

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction

from tests.acceptance._api import api

ENC, KIND = "spinnet", "step"
NOMINAL = (0.37, 0.61)
STANDARD = {"propext", "Classical.choice", "Quot.sound"}
SPECTRUM = {-2.0: 16, -1.0: 96, -0.5: 16, 0.0: 177, 0.5: 16, 1.0: 96, 2.0: 16}
REQUIRED_FACTS = {"card_inner_labels": 47, "card_bright_labels": 16, "card_dark_labels": 31, "card_bright_pairs": 8,
                  "card_states_spinnet": 433, "mult_two": 16, "mult_one": 96, "mult_half": 16}
COUPLINGS_2K = {"-4": 1, "-1": 1, "2": 6, "0": 31}       # pairs with 2K = -4, -1, +2 and the dark rows (M3-L1, M3X-W1)


@functools.lru_cache(maxsize=None)
def _loop():
    L = api("su2plaq.spinnet.loop")
    L.install()
    return L


def _lean_dir(root: pathlib.Path) -> pathlib.Path:
    d = root / "lean"
    if not (d / "lakefile.toml").exists():
        pytest.fail("PENDING: lean/lakefile.toml missing (prompts/006 step 2.L1)", pytrace=False)
    for rel in ("Su2PlaqCert/SpinNet/Check.lean", "Su2PlaqCert/SpinNet/Pins.lean", "Su2PlaqCert/SpinNet/Main.lean"):
        if not (d / rel).exists():
            pytest.fail(f"PENDING: lean/{rel} missing (prompts/104 step 4.L1)", pytrace=False)
    return d


def _enc():
    return api("su2plaq.encodings.spinnet:SpinNet")()


def _step(alpha=NOMINAL[0], beta=NOMINAL[1], order=1):
    return api("su2plaq.circuits.spinnet:build_step")(alpha, beta, order, with_outer=True)


def _with_first_angle(qc: QuantumCircuit, name: str, new_angle: float) -> QuantumCircuit:
    out = qc.copy()
    for i, inst in enumerate(out.data):
        if inst.operation.name == name:
            op = inst.operation.copy()
            op.params = [new_angle]
            out.data[i] = CircuitInstruction(op, inst.qubits, inst.clbits)
            assert abs(float(out.data[i].operation.params[0]) - new_angle) <= 1e-15
            assert abs(float(qc.data[i].operation.params[0]) - new_angle) > 1e-9
            return out
    raise AssertionError(f"no gate {name!r}")


# ---------------------------------------------------------------------------------------------------- 4.L1
def test_M4_L1_certificate_general_and_seeds(root):
    """Exact certificates through our checker entry: the general step / U_E / U_B circuits and the vendored pairs9 U_B
    skeleton are `certified`; a beta scaled by (1 + 1e-6) (angles no longer multiples of the base) is `rejected` or `n_a`;
    an irrational angle is `n_a` starting `non_linear_angle`.  Each certificate within 900 s (prompts/006 §7)."""
    _loop()
    _lean_dir(root)
    LE = api("su2plaq.spinnet.lean_export")
    enc = _enc()
    assert LE.CHECKER_TARGET == "su2plaq_cert_spinnet"
    t0 = time.time()
    r = LE.certify(_step(), enc, "step", *NOMINAL, 1)
    assert time.time() - t0 <= 900
    assert r["status"] == "certified", (r["status"], r.get("reason"))
    cert = json.loads(pathlib.Path(r["cert_path"]).read_text())
    assert cert["schema"] == "su2plaq-cert-1" and cert["n_data"] == 8 and cert["n_outer"] == 8 and len(cert["states"]) == 433
    assert cert["base"]["d_alpha"] % 4 == 0 and cert["base"]["d_beta"] % 4 == 0
    assert all(a in STANDARD or api("su2plaq.lean.project").is_native_axiom(a) for a in r.get("axioms", []))
    assert len(r.get("checker_sha256", "")) == 64
    bad = _step(beta=NOMINAL[1] * (1 + 1e-6))
    r2 = LE.certify(bad, enc, "step", *NOMINAL, 1)
    assert r2["status"] in ("rejected", "n_a"), r2
    irr = _with_first_angle(_step(), "p", 0.123)
    r3 = LE.certify(irr, enc, "step", *NOMINAL, 1)
    assert r3["status"] == "n_a" and r3["reason"].startswith("non_linear_angle"), r3
    ue = api("su2plaq.circuits.spinnet:build_UE")(NOMINAL[0], with_outer=True)
    assert LE.certify(ue, enc, "UE", NOMINAL[0], NOMINAL[1], 1)["status"] == "certified"
    ub = api("su2plaq.circuits.spinnet:build_UB")(NOMINAL[1], with_outer=True)
    assert LE.certify(ub, enc, "UB", NOMINAL[0], NOMINAL[1], 1)["status"] == "certified"
    v2 = api("su2plaq.circuits.spinnet:trotter_v2_circuit")("pairs9", NOMINAL[1], with_outer=True)
    rv = LE.certify(v2, enc, "UB", NOMINAL[0], NOMINAL[1], 1)
    assert rv["status"] == "certified", rv


# ---------------------------------------------------------------------------------------------------- 4.L2
@pytest.mark.slow
def test_M4_L2_seed_round_records_certificates(root, tmp_path):
    """A dry round 0 with Lean on: the `general` seed entry and the round's best entry carry `lean.status == "certified"`
    (all seeds are angle-linear with denominators <= 8) within the 1200 s round budget; validity is unchanged."""
    L = _loop()
    _lean_dir(root)
    info = L.seed_round(root=tmp_path, lean=True, dry_run=True)
    assert info["n_valid"] == 7 and info.get("lean_seconds", 0.0) <= 1200
    A = api("su2plaq.compress.archive")
    arch = A.Archive.load(ENC, root=tmp_path)
    best = arch.best()
    assert best is not None and isinstance(best.lean, dict) and best.lean["status"] == "certified", best.lean
    d = json.loads((tmp_path / "results" / "compress" / ENC / "round-000.json").read_text())
    gen = next(c for c in d["candidates"] if c["label"] == "general")
    assert gen["valid"] and isinstance(gen.get("lean"), dict) and gen["lean"]["status"] == "certified", gen.get("lean")


# ---------------------------------------------------------------------------------------------------- 4.L2
def test_M4_L3_structure_facts_match_lean_sources(root):
    """The spin-network facts offered to the proposers are the kernel-checked M3/M3x theorems: every `decide` fact names
    a theorem that exists in the named file under lean/Su2Plaq/SpinNet/ (no native_decide, no sorry there); values are the
    locked M3 ones; the rendered spec lists them; nothing is labelled `native` (no native structure certificate exists)."""
    L = _loop()
    if not (root / "lean" / "Su2Plaq" / "SpinNet" / "Counts.lean").exists():
        pytest.fail("PENDING: lean/Su2Plaq/SpinNet missing (prompts/100 3.L1)", pytrace=False)
    facts = L.structure_facts()
    by = {f["name"]: f for f in facts["facts"]}
    for name, value in REQUIRED_FACTS.items():
        assert name in by and by[name]["value"] == value and by[name]["proved_by"] == "decide", name
    assert by["spectrum_multiplicities"]["proved_by"] == "decide"
    assert {float(l): int(m) for l, m in by["spectrum_multiplicities"]["value"]} == SPECTRUM
    assert by["couplings_2k"]["proved_by"] == "decide" and {str(k): int(v) for k, v in dict(by["couplings_2k"]["value"]).items()} == COUPLINGS_2K
    assert by["ub_exact_semantics"]["proved_by"] == "decide" and by["ub_exact_semantics"]["value"] is True
    assert all(f["proved_by"] in ("decide", "numerical") for f in facts["facts"])
    for f in facts["facts"]:
        if f["proved_by"] != "decide":
            continue
        assert f["theorem"].startswith("Su2Plaq.SpinNet."), f["name"]
        short = f["theorem"].rsplit(".", 1)[1]
        src_path = root / f["file"]
        assert src_path.exists() and src_path.is_relative_to(root / "lean" / "Su2Plaq" / "SpinNet"), f["file"]
        src = src_path.read_text()
        assert re.search(rf"^theorem {re.escape(short)}\b", src, re.M), (f["name"], f["theorem"], f["file"])
        assert "native_decide" not in src and "sorry" not in src
    text = L.render_spec()
    for name in REQUIRED_FACTS:
        assert name in text, name
    assert "spectrum_multiplicities" in text and "coupling" in text


def test_M4_L4_polish_rules_lean_certified_on_spinnet():
    """The laptop's polish pass on our general circuit only emits rule names that map to kernel-checked theorems
    (rules.LEAN_RULES), stays valid and is not worse."""
    L = _loop()
    spec = L.spec()
    P = api("su2plaq.compress.passes"); R = api("su2plaq.lean.rules"); E = api("su2plaq.compress.evaluate")
    M = api("su2plaq.compress.metrics")
    qc = _step()
    out, log = P.polish(qc, spec)
    assert R.LEAN_RULES and all(any(line.startswith(name) for name in R.LEAN_RULES) for line in log), log
    r = E.evaluate_circuit(out, spec, mode="trial")
    assert r.valid
    assert M.key(M.metrics(out, spec, measured=False)) <= M.key(M.metrics(qc, spec, measured=False))


# ---------------------------------------------------------------------------------------------------- gate (4.7)
@pytest.mark.slow
def test_M4_L5_final_best_lean_status_and_theorem_file(root):
    """After the loop: the real archive's global best carries a Lean status (`certified`, or `n_a` for the two allowed
    reasons); when certified, the theorem file lean/certs/spinnet-best-step.lean elaborates with the standard axioms plus
    exactly one native axiom; the report has a Lean column."""
    L = _loop()
    _lean_dir(root)
    A = api("su2plaq.compress.archive")
    arch = A.Archive.load(ENC, root=root)
    best = arch.best()
    assert best is not None and isinstance(best.lean, dict), best
    assert best.lean["status"] in ("certified", "n_a"), best.lean
    if best.lean["status"] == "n_a":
        assert best.lean["reason"].startswith(("non_linear_angle", "phase_not_in_K")), best.lean
    # erratum E3: the headline circuit (robust-key minimum, prompts/104 §11) carries a Lean status too, and the theorem file is its
    h = api("su2plaq.spinnet.loop:headline")(root=root)
    head = {e.id: e for e in arch.entries()}[h["id"]]
    assert isinstance(head.lean, dict) and head.lean["status"] in ("certified", "n_a"), head.lean
    assert h["lean"] == head.lean["status"]
    if head.lean["status"] == "n_a":
        assert head.lean["reason"].startswith(("non_linear_angle", "phase_not_in_K")), head.lean
    else:
        f = root / "lean" / "certs" / "spinnet-best-step.lean"
        assert f.exists(), "write_theorem_file for the headline circuit (step 4.7)"
        assert head.id in f.read_text() or head.program_sha256[:12] in f.read_text(), "theorem file must name the headline entry"
        env = {**__import__("os").environ, "PATH": str(pathlib.Path.home() / ".elan" / "bin") + ":" + __import__("os").environ["PATH"]}
        t0 = time.time()
        p = subprocess.run(["lake", "env", "lean", str(f)], cwd=root / "lean", capture_output=True, text=True, timeout=900, env=env)
        assert time.time() - t0 <= 900
        assert p.returncode == 0, p.stderr[-2000:] + p.stdout[-2000:]
        m = re.search(r"depends on axioms:\s*\[([^\]]*)\]", p.stdout)
        assert m, p.stdout[-2000:]
        axioms = {a.strip() for a in m.group(1).split(",") if a.strip()}
        native = [a for a in axioms if a not in STANDARD]
        assert len(native) == 1 and api("su2plaq.lean.project").is_native_axiom(native[0]), axioms
    text = L.report_table(root=root)
    assert "Lean" in text
