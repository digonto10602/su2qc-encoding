"""M6-L1..L8 — Lean inside the rishon loop (prompts/203 §2, §3.2, §6; prompts/006 trust levels; METHODS-rishon R12):
the structure facts proposers may rely on (kernel / native), the track-owned three-angle exact certificate checker
(z_alpha, z_beta, z_gamma = e^{i sqrt2 beta / d}), per-circuit certificates of the general circuits, the round integration,
and the gate status of the archive best.  Everything Lean checks is exact; numbers are time limits and one 1e-12 float
cross-check (prompts/203 §6).  PENDING rule: missing lean/ files or `su2plaq.rishon.lean_cert` names fail with `PENDING:`."""
import functools
import json
import pathlib
import time

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction

from tests.acceptance._api import api

ENC = "rishon"
STANDARD = {"propext", "Classical.choice", "Quot.sound"}
SCHEMA = "su2plaq-rishon-cert3-1"
SQ2 = float(np.sqrt(2.0))


def _lean_dir(root: pathlib.Path) -> pathlib.Path:
    d = root / "lean"
    if not (d / "lakefile.toml").exists():
        pytest.fail("PENDING: lean/lakefile.toml missing", pytrace=False)
    for rel in ("Su2PlaqCert/Rishon/Laurent3.lean", "Su2PlaqCert/Rishon/Gates3.lean", "Su2PlaqCert/Rishon/Check3.lean", "Su2PlaqCert/Rishon/Main.lean"):
        if not (d / rel).exists():
            pytest.fail(f"PENDING: lean/{rel} missing (step 6.L2)", pytrace=False)
    return d


@functools.lru_cache(maxsize=None)
def _spec(kind="step"):
    return api("su2plaq.rishon.compress.spec:rishon_spec")(kind)


def _with_first_angle(qc: QuantumCircuit, name: str, new_angle: float) -> QuantumCircuit:
    out = qc.copy()
    for i, inst in enumerate(out.data):
        if inst.operation.name == name:
            op = inst.operation.copy()
            op.params = [new_angle]
            out.data[i] = CircuitInstruction(op, inst.qubits, inst.clbits)
            assert abs(float(out.data[i].operation.params[0]) - new_angle) <= 1e-15 and abs(float(qc.data[i].operation.params[0]) - new_angle) > 1e-9
            return out
    raise AssertionError(f"no gate {name!r} found")


def _random_three_angle_circuit(seed: int, n_qubits: int = 6, n_gates: int = 40) -> QuantumCircuit:
    """Seeded SIM_BASIS circuit whose angles are k alpha/4, k beta/2 or k sqrt2 beta/2 (alpha, beta nominal)."""
    rng = np.random.default_rng(seed)
    alpha, beta = 0.37, 0.61
    bases = (alpha / 4, beta / 2, SQ2 * beta / 2)
    qc = QuantumCircuit(n_qubits)
    one = ["x", "z", "s", "sdg", "t", "tdg", "h", "sx"]
    for _ in range(n_gates):
        kind = rng.integers(0, 5)
        q = int(rng.integers(0, n_qubits))
        if kind == 0:
            getattr(qc, one[int(rng.integers(0, len(one)))])(q)
        elif kind == 1:
            k = int(rng.integers(-6, 7)) or 1
            qc.p(k * bases[int(rng.integers(0, 3))], q)
        elif kind == 2:
            k = int(rng.integers(-6, 7)) or 1
            qc.rz(2 * k * bases[int(rng.integers(0, 3))], q)      # rz uses half angles
        elif kind == 3:
            r = int(rng.integers(0, n_qubits))
            r = (r + 1) % n_qubits if r == q else r
            qc.cx(q, r) if rng.random() < 0.7 else qc.cp(int(rng.integers(1, 4)) * bases[int(rng.integers(1, 3))], q, r)
        else:
            a, b, c = rng.choice(n_qubits, size=3, replace=False)
            qc.ccx(int(a), int(b), int(c)) if rng.random() < 0.5 else qc.ccz(int(a), int(b), int(c))
    return qc


def test_M6_L1_structure_facts_axioms_and_spec_section(root):
    """Every `decide` fact names a theorem that exists with standard axioms (no native_decide, no sorry in lean/Su2Plaq/Rishon);
    the native fact names an existing certificate file; the spec file has the "Proved structure (Lean)" section with the
    kernel-checked count."""
    if not (root / "lean" / "lakefile.toml").exists():
        pytest.fail("PENDING: lean/lakefile.toml missing", pytrace=False)
    S = api("su2plaq.rishon.compress.spec")
    P = api("su2plaq.lean.project")
    facts = S.structure_facts()["facts"]
    names = sorted({f["theorem"] for f in facts if f["proved_by"] == "decide"})
    assert len(names) >= 6
    ax = P.print_axioms(names, timeout=900)
    bad = {n: sorted(a - STANDARD) for n, a in ax.items() if (a - STANDARD) or "<unknown>" in a}
    assert not bad, bad
    for f in facts:
        if f["proved_by"] == "native":
            assert (root / f["certificate"]).exists() or (root / "lean" / "certs" / pathlib.Path(f["certificate"]).name).exists(), f["certificate"]
    for src in (root / "lean" / "Su2Plaq" / "Rishon").glob("*.lean"):
        assert "native_decide" not in src.read_text() and "sorry" not in src.read_text(), src.name
    text = (root / "compress" / "specs" / "rishon-step.md").read_text()
    sec = text.split("Proved structure (Lean)")[1]
    assert "38432" in sec and "decide" in sec and "native" in sec and "card_rishon_physical" in sec


def test_M6_L2_cert3_builds_and_semantics(root, seed, tmp_path):
    """`lake build Su2PlaqCert.Rishon.Main` succeeds (<= 600 s, Mathlib-free); the exact three-angle checker's gate
    semantics equal the validated sparse simulator on a seeded 40-gate circuit at the nominal angles (<= 1e-12);
    recognise_angle returns the canonical (m_alpha, m_beta, m_gamma, d) triples."""
    _lean_dir(root)
    P = api("su2plaq.lean.project")
    LC = api("su2plaq.rishon.lean_cert")
    ss = api("su2plaq.evaluate.sparse_sim")
    t0 = time.time()
    b = P.build("Su2PlaqCert.Rishon.Main", timeout=600)
    assert b["ok"], b.get("stderr", "")[-2000:]
    assert time.time() - t0 <= 600
    assert LC.SCHEMA == SCHEMA
    alpha, beta = 0.37, 0.61
    assert LC.recognise_angle(8 * SQ2 * beta, alpha, beta) == (0, 0, 8, 1)
    assert LC.recognise_angle(-0.75 * alpha, alpha, beta) == (-3, 0, 0, 4)
    assert LC.recognise_angle(beta + 2 * SQ2 * beta, alpha, beta) == (0, 1, 2, 1)
    assert LC.recognise_angle(0.123, alpha, beta) is None
    ma, mb, mg, d = LC.recognise_angle((3 * alpha - 5 * beta + 7 * SQ2 * beta) / 16, alpha, beta)
    assert abs((ma * alpha + mb * beta + mg * SQ2 * beta) / d - (3 * alpha - 5 * beta + 7 * SQ2 * beta) / 16) <= 1e-12 and 1 <= d <= 64
    qc = _random_three_angle_circuit(seed)
    n = qc.num_qubits
    batch = ss.run_batch(qc, np.arange(2 ** n, dtype=np.int64))
    cert = tmp_path / "semantics.json"
    out = LC.export_raw_circuit(qc, cert, alpha=alpha, beta=beta)
    assert isinstance(out, pathlib.Path), out
    base = json.loads(cert.read_text())["base"]
    th = (alpha / base["d_alpha"], beta / base["d_beta"], SQ2 * beta / base["d_gamma"])
    t1 = time.time()
    for col in (0, 3, 2 ** n - 1):
        exact = LC.checker_eval(cert, col, timeout=300)
        vec = np.zeros(2 ** n, dtype=np.complex128)
        for key, lp in exact:
            vec[key] += lp.evaluate(*th)
        ref = np.zeros(2 ** n, dtype=np.complex128)
        sel = batch.cols == col
        np.add.at(ref, batch.keys[sel], batch.amps[sel])
        ov = np.vdot(ref, vec)
        ph = ov / abs(ov)
        assert np.abs(vec - ph * ref).max() <= 1e-12
    assert time.time() - t1 <= 300


def test_M6_L3_cert3_accept_reject_na(root, tmp_path):
    """build_UE(0.37) (16 data qubits, 4 gadgets): certified for all angles; a wrong multiple of alpha: rejected; an
    angle that is not (m_a alpha + m_b beta + m_g sqrt2 beta)/d: n_a with reason non_linear_angle.  <= 300 s total."""
    _lean_dir(root)
    LC = api("su2plaq.rishon.lean_cert")
    build_UE = api("su2plaq.circuits.rishon:build_UE")
    alpha, beta = 0.37, 0.61
    t0 = time.time()
    qc = build_UE(alpha)
    c1 = LC.certify_circuit_kind(qc, "UE", alpha, beta, 1, out_dir=tmp_path, timeout=300)
    assert c1.status == "certified", (c1.status, c1.reason)
    assert c1.cert_path and json.loads(pathlib.Path(c1.cert_path).read_text())["schema"] == SCHEMA
    cert = json.loads(pathlib.Path(c1.cert_path).read_text())
    assert cert["n_data"] == 16 and cert["n_outer"] == 0 and len(cert["states"]) == 1296 and set(cert["base"]) == {"d_alpha", "d_beta", "d_gamma"}
    assert all(len(g["m"]) == 3 for g in cert["gates"] if "m" in g)
    c2 = LC.certify_circuit_kind(_with_first_angle(qc, "p", -alpha / 2), "UE", alpha, beta, 1, out_dir=tmp_path / "bad", timeout=300)
    assert c2.status == "rejected", (c2.status, c2.reason)
    c3 = LC.certify_circuit_kind(_with_first_angle(qc, "p", 0.123), "UE", alpha, beta, 1, out_dir=tmp_path / "na", timeout=300)
    assert c3.status == "n_a" and c3.reason.startswith("non_linear_angle"), (c3.status, c3.reason)
    assert time.time() - t0 <= 300


@pytest.mark.slow
def test_M6_L4_cert3_general_ub_and_step(root, tmp_path):
    """The general U_B(0.61) (angles 2 beta, 4 beta, 8 sqrt2 beta) and the general step circuit are certified exactly for
    all (alpha, beta) by the three-angle checker, each within 900 s (research 202 §4 estimate, 3x margin)."""
    _lean_dir(root)
    LC = api("su2plaq.rishon.lean_cert")
    BL = api("su2plaq.rishon.compress.baselines")
    alpha, beta = 0.37, 0.61
    ub = api("su2plaq.circuits.rishon:build_UB")(beta)
    t0 = time.time()
    c = LC.certify_circuit_kind(ub, "UB", alpha, beta, 1, out_dir=tmp_path / "ub", timeout=900)
    assert c.status == "certified", (c.status, c.reason)
    assert time.time() - t0 <= 900 and c.seconds <= 900
    spec = _spec("step")
    t1 = time.time()
    cs = LC.certify_circuit(BL.general_circuit(spec), spec, out_dir=tmp_path / "step", timeout=900)
    assert cs.status == "certified", (cs.status, cs.reason)
    assert time.time() - t1 <= 900
    cert = json.loads(pathlib.Path(cs.cert_path).read_text())
    assert cert["n_qubits"] == 26 and cert.get("outer_dropped") == 32 and len(cert["states"]) == 1296


@pytest.mark.slow
def test_M6_L5_theorem_file_general_step(root):
    """lean/certs/rishon-general-step.lean (written by step 6.L3) elaborates; its theorem uses the standard axioms plus
    exactly one native axiom (native-certified); <= 1800 s (a ~1 MB literal, as the laptop's twelve file)."""
    _lean_dir(root)
    LC = api("su2plaq.rishon.lean_cert")
    P = api("su2plaq.lean.project")
    f = root / "lean" / "certs" / "rishon-general-step.lean"
    if not f.exists():
        pytest.fail("PENDING: lean/certs/rishon-general-step.lean missing (step 6.L3)", pytrace=False)
    src = f.read_text()
    assert "native_decide" in src and "sorry" not in src and "import Su2PlaqCert.Rishon.Check3" in src
    t0 = time.time()
    r = LC.check_theorem_file(f, timeout=1800)
    assert r["status"] == "certified", r
    extra = set(r["axioms"]) - STANDARD
    assert len(extra) == 1 and all(P.is_native_axiom(a) for a in extra), r["axioms"]
    assert time.time() - t0 <= 1800


@pytest.mark.slow
def test_M6_L6_round_records_lean(root, tmp_path):
    """A dry round 0 (kind UE) with the U_E program records a Lean certificate on the archived best within the Lean budget
    (prompts/006 §0: <= 1200 s per round); validity stays the numerical verdict."""
    _lean_dir(root)
    rd = api("su2plaq.rishon.compress.round")
    A = api("su2plaq.compress.archive")
    path = pathlib.Path(api("su2plaq.rishon.compress.baselines:general_program_path")(_spec("UE")))
    info = rd.run_round("UE", round=0, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(path)], lean=True)
    assert info["n_valid"] >= 1 and info.get("lean_seconds", 0.0) <= 1200
    best = A.Archive.load(ENC, root=tmp_path).best()
    assert best is not None and best.valid and isinstance(best.lean, dict)
    assert best.lean["status"] == "certified", best.lean


@pytest.mark.slow
def test_M6_L7_archive_best_lean_status_recorded(root):
    """After the loop (gate): the real archive's global best carries a Lean status; `n_a` only for the allowed reasons;
    the report table has the Lean column."""
    _lean_dir(root)
    A = api("su2plaq.compress.archive")
    best = A.Archive.load(ENC, root=root).best()
    if best is None:
        pytest.fail("PENDING: the rishon archive has no valid entry yet", pytrace=False)
    assert isinstance(best.lean, dict), best.lean
    assert best.lean["status"] in ("certified", "n_a"), best.lean
    if best.lean["status"] == "n_a":
        assert str(best.lean["reason"]).startswith(("non_linear_angle", "phase_not_in_K", "unitary_gate", "too_many_qubits")), best.lean
    text = api("su2plaq.compress.report:report_table")(ENC, "step", root=root)
    assert "Lean" in text


def test_M6_L8_polish_rules_lean_certified(root):
    """Every rewrite rule our polish can emit on the general step circuit names a laptop Lean theorem with standard axioms."""
    if not (root / "lean" / "lakefile.toml").exists():
        pytest.fail("PENDING: lean/lakefile.toml missing", pytrace=False)
    R = api("su2plaq.lean.rules")
    P = api("su2plaq.lean.project")
    BL = api("su2plaq.rishon.compress.baselines")
    spec = _spec("step")
    _, log = BL.polish(BL.general_circuit(spec), spec)
    assert isinstance(R.LEAN_RULES, dict) and R.LEAN_RULES
    for line in log:
        rule = str(line).split(":")[0].split()[0]
        assert rule in R.LEAN_RULES, (rule, line)
    ax = P.print_axioms(sorted(set(R.LEAN_RULES.values())), timeout=900)
    bad = {n: sorted(a - STANDARD) for n, a in ax.items() if (a - STANDARD) or "<unknown>" in a}
    assert not bad, bad
