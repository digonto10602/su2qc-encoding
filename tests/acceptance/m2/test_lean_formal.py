"""M2 — Lean 4 formal verification of the compression methods and the loop integration (prompts/006 §3–§7,
docs/METHODS.md §11).  Everything Lean checks is exact; the only numbers here are time limits (justified in prompts/006 §7)
and the 1e-12 float cross-check between the exact checker and the validated sparse simulator.

PENDING rule: when the Lean project (lean/lakefile.toml) or the `su2plaq.lean` package does not exist yet, every test fails
with `PENDING:` (never a collection error)."""
import json
import pathlib
import shutil
import time

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import CircuitInstruction

from tests.acceptance._api import api

ENC, KIND = "twelve", "step"
TOOLCHAIN = "leanprover/lean4:v4.35.0"
STANDARD = {"propext", "Classical.choice", "Quot.sound"}

# LOCKED: the generic theorems (kernel-checked, standard axioms only) — prompts/006 §3.
GENERIC_THEOREMS = (
    "Su2Plaq.norm_sum_sq_of_pairwise_orth", "Su2Plaq.opNorm_add_three_le_of_orth", "Su2Plaq.rss_le_sum",
    "Su2Plaq.pruning_triangle", "Su2Plaq.opNorm_le_of_blockdiag", "Su2Plaq.verdict_sound",
    "Su2Plaq.gauss_max_ge", "Su2Plaq.span_leak_le_four_gauss",
    "Su2Plaq.cs_block_bound",
    "Su2Plaq.norm_list_prod_le_one", "Su2Plaq.prod_sub_prod_le", "Su2Plaq.synth_bound",
    "Su2Plaq.ctrl_mulVec_e", "Su2Plaq.mono_mulVec_e", "Su2Plaq.mono_conjTranspose_mul", "Su2Plaq.sandwich",
    "Su2Plaq.rccx_crx_rccx_eq_ccrx", "Su2Plaq.h_z_h", "Su2Plaq.h_rz_h",
    "Su2Plaq.cx_involutive", "Su2Plaq.perm_conj_diagonal", "Su2Plaq.cx_comm_diagonal_of_indep", "Su2Plaq.cx_comm_cx",
    "Su2Plaq.ccz_circuit",
    "Su2Plaq.kron_disjoint_comm", "Su2Plaq.outer_electric_commutes",
)


def _lean_dir(root: pathlib.Path) -> pathlib.Path:
    d = root / "lean"
    if not (d / "lakefile.toml").exists():
        pytest.fail("PENDING: lean/lakefile.toml missing (prompts/006 step 2.L1)", pytrace=False)
    return d


def _spec():
    return api("su2plaq.compress.spec:default_spec")(ENC, KIND)


def _with_first_angle(qc: QuantumCircuit, name: str, new_angle: float) -> QuantumCircuit:
    """Copy of qc with the FIRST gate named `name` rebuilt with angle `new_angle`.  Qiskit 2.5.2 stores standard gates
    natively and `inst.operation` returns a fresh object on every access, so `inst.operation.params[0] = …` is a silent
    no-op; the instruction must be replaced through `qc.data[i] = CircuitInstruction(...)` (coordinator/Digonto fix,
    2026-11-05)."""
    out = qc.copy()
    for i, inst in enumerate(out.data):
        if inst.operation.name == name:
            op = inst.operation.copy()
            op.params = [new_angle]
            out.data[i] = CircuitInstruction(op, inst.qubits, inst.clbits)
            assert abs(float(out.data[i].operation.params[0]) - new_angle) <= 1e-15      # the change really landed
            assert abs(float(qc.data[i].operation.params[0]) - new_angle) > 1e-9        # and the original is untouched
            return out
    raise AssertionError(f"no gate {name!r} found")


def _axioms_ok(ax: set, allow_native: bool = False) -> bool:
    P = api("su2plaq.lean.project")
    extra = set(ax) - STANDARD
    if not allow_native:
        return not extra
    return all(P.is_native_axiom(a) for a in extra)


# ---------------------------------------------------------------------------- project (2.L1)
def test_lean_project_present_and_builds_checker(root):
    """Toolchain and Mathlib pins; the Mathlib-free checker library builds (<= 600 s)."""
    d = _lean_dir(root)
    assert (d / "lean-toolchain").read_text().strip() == TOOLCHAIN
    lake = (d / "lakefile.toml").read_text()
    assert 'rev = "v4.35.0"' in lake and "mathlib" in lake and "Su2PlaqCert" in lake and "Su2Plaq" in lake
    P = api("su2plaq.lean.project")
    assert P.TOOLCHAIN == TOOLCHAIN and P.MATHLIB_REV == "v4.35.0" and set(P.STANDARD_AXIOMS) == STANDARD
    t0 = time.time()
    r = P.build("Su2PlaqCert", timeout=600)
    assert r["ok"], r.get("stderr", "")[-2000:]
    assert time.time() - t0 <= 600


# ---------------------------------------------------------------------------- generic theorems (2.L2, 2.L3)
def test_lean_generic_theorems_standard_axioms(root):
    """Every locked theorem name exists and depends on the standard axioms only; no `sorry` anywhere in lean/."""
    _lean_dir(root)
    P = api("su2plaq.lean.project")
    assert set(GENERIC_THEOREMS) <= set(P.GENERIC_THEOREMS), set(GENERIC_THEOREMS) - set(P.GENERIC_THEOREMS)
    assert P.no_sorry() == []
    ax = P.print_axioms(list(GENERIC_THEOREMS), timeout=900)
    missing = [n for n in GENERIC_THEOREMS if n not in ax or "<unknown>" in ax[n]]
    assert not missing, f"unknown theorems: {missing}"
    bad = {n: sorted(ax[n] - STANDARD) for n in GENERIC_THEOREMS if not _axioms_ok(ax[n])}
    assert not bad, f"non-standard axioms: {bad}"


# ---------------------------------------------------------------------------- exact checker (2.L4)
def _random_linear_circuit(seed: int, n_qubits: int = 6, n_gates: int = 40) -> QuantumCircuit:
    """Seeded SIM_BASIS circuit whose angles are k*alpha/4 or k*beta/2 (alpha, beta nominal) — exactly representable."""
    rng = np.random.default_rng(seed)
    alpha, beta = 0.37, 0.61
    qc = QuantumCircuit(n_qubits)
    one = ["x", "z", "s", "sdg", "t", "tdg", "h", "sx"]
    for _ in range(n_gates):
        kind = rng.integers(0, 5)
        q = int(rng.integers(0, n_qubits))
        if kind == 0:
            getattr(qc, one[int(rng.integers(0, len(one)))])(q)
        elif kind == 1:
            k = int(rng.integers(-6, 7)) or 1
            qc.p(k * alpha / 4 if rng.random() < 0.5 else k * beta / 2, q)
        elif kind == 2:
            k = int(rng.integers(-6, 7)) or 1
            qc.rz(k * alpha / 2 if rng.random() < 0.5 else k * beta, q)   # rz uses half angles: multiples of alpha/4, beta/2
        elif kind == 3:
            r = int(rng.integers(0, n_qubits))
            r = (r + 1) % n_qubits if r == q else r
            qc.cx(q, r) if rng.random() < 0.7 else qc.cp(int(rng.integers(1, 4)) * beta / 2, q, r)
        else:
            a, b, c = rng.choice(n_qubits, size=3, replace=False)
            qc.ccx(int(a), int(b), int(c)) if rng.random() < 0.5 else qc.ccz(int(a), int(b), int(c))
    return qc


def test_lean_checker_semantics_match_sparse_sim(root, seed, tmp_path):
    """The exact checker's gate semantics equal the validated float simulator: exact output of a seeded 40-gate circuit,
    evaluated at the nominal angles, agrees with run_batch to 1e-12 (exact vs float64 over 40 gates ~1e-15)."""
    _lean_dir(root)
    C = api("su2plaq.lean.certify")
    ss = api("su2plaq.evaluate.sparse_sim")
    qc = _random_linear_circuit(seed)
    n = qc.num_qubits
    inputs = np.arange(2 ** n, dtype=np.int64)
    batch = ss.run_batch(qc, inputs)
    cert = tmp_path / "semantics.json"
    out = C.export_raw_circuit(qc, cert, alpha=0.37, beta=0.61)       # gates + base angles only (no states/target)
    assert isinstance(out, pathlib.Path)
    base = json.loads(cert.read_text())["base"]
    th_a, th_b = 0.37 / base["d_alpha"], 0.61 / base["d_beta"]
    t0 = time.time()
    for col in (0, 3, 2 ** n - 1):
        exact = C.checker_eval(cert, col, timeout=300)                 # list of (basis int, Laurent)
        vec = np.zeros(2 ** n, dtype=np.complex128)
        for key, lp in exact:
            vec[key] += lp.evaluate(th_a, th_b)
        ref = np.zeros(2 ** n, dtype=np.complex128)
        sel = batch.cols == col
        np.add.at(ref, batch.keys[sel], batch.amps[sel])
        # the checker ignores the circuit's global phase (it is irrelevant for the certificate): compare up to one phase
        ov = np.vdot(ref, vec)
        ph = ov / abs(ov)
        assert np.abs(vec - ph * ref).max() <= 1e-12
    assert time.time() - t0 <= 300


def test_lean_certificate_small_accept_reject_na(root, tmp_path):
    """U_E alone (4 phase gates, outer register present): certified; a wrong multiple of alpha: rejected; an angle that is
    not a rational multiple of alpha or beta: n_a (not certifiable, numerically verified only)."""
    _lean_dir(root)
    C = api("su2plaq.lean.certify")
    enc = api("su2plaq.encodings.twelve:TwelveQubit")()
    build_UE = api("su2plaq.circuits.twelve:build_UE")
    alpha, beta = 0.37, 0.61
    t0 = time.time()
    qc = build_UE(alpha, with_outer=True)
    c1 = C.certify_circuit_kind(qc, enc, "UE", alpha, beta, 1, out_dir=tmp_path, timeout=300)
    assert c1.status == "certified", (c1.status, c1.reason)
    assert c1.cert_path and json.loads(pathlib.Path(c1.cert_path).read_text())["schema"] == "su2plaq-cert-1"
    bad = _with_first_angle(qc, "p", -alpha / 2)          # still angle-linear, but wrong
    c2 = C.certify_circuit_kind(bad, enc, "UE", alpha, beta, 1, out_dir=tmp_path / "bad", timeout=300)
    assert c2.status == "rejected", (c2.status, c2.reason)
    na = _with_first_angle(qc, "p", 0.123)                # not a rational multiple of alpha or beta
    c3 = C.certify_circuit_kind(na, enc, "UE", alpha, beta, 1, out_dir=tmp_path / "na", timeout=300)
    assert c3.status == "n_a" and c3.reason.startswith("non_linear_angle"), (c3.status, c3.reason)
    assert time.time() - t0 <= 300


@pytest.mark.slow
def test_lean_certificate_general_circuit(root, tmp_path):
    """The general step circuit (round-0 seed) is Lean-certified exactly for all (alpha, beta) within 900 s."""
    _lean_dir(root)
    C = api("su2plaq.lean.certify")
    spec = _spec()
    qc = api("su2plaq.compress.baselines:general_circuit")(spec)
    t0 = time.time()
    cert = C.certify_circuit(qc, spec, out_dir=tmp_path, timeout=900)
    assert cert.status == "certified", (cert.status, cert.reason)
    assert cert.seconds <= 900 and time.time() - t0 <= 900
    d = json.loads(pathlib.Path(cert.cert_path).read_text())
    assert d["schema"] == "su2plaq-cert-1" and len(d["states"]) == 433 and d["n_data"] == 12 and d["n_outer"] == 16


@pytest.mark.slow
def test_lean_theorem_file_general(root):
    """lean/certs/twelve-general-step.lean exists, elaborates, and its theorem depends on the standard axioms plus exactly
    one native (compiler-trust) axiom — the labelled trust level of certificates (prompts/006 §0, §8)."""
    d = _lean_dir(root)
    P = api("su2plaq.lean.project")
    f = d / "certs" / "twelve-general-step.lean"
    assert f.exists()
    text = f.read_text()
    assert "native_decide" in text and "sorry" not in text
    t0 = time.time()
    r = P.lake(["env", "lean", str(f)], timeout=1800)
    assert r.returncode == 0, r.stderr[-2000:]
    assert time.time() - t0 <= 1800
    lines = [ln for ln in r.stdout.splitlines() if "depends on axioms" in ln]
    assert len(lines) == 1, r.stdout[-2000:]
    ax = {a.strip(" ,[]'\"") for a in lines[0].split("axioms:")[1].split(",")}
    ax = {a.strip("[] ") for a in ax if a.strip("[] ")}
    extra = ax - STANDARD
    assert len(extra) == 1 and all(P.is_native_axiom(a) for a in extra), ax
    assert "sorryAx" not in ax


# ---------------------------------------------------------------------------- loop integration (2.L7, 2.L8)
def test_polish_rules_are_lean_certified(root):
    """Every rewrite rule the polish pass can emit names a Lean theorem (standard axioms); polish's log on the general
    circuit uses only those names."""
    _lean_dir(root)
    R = api("su2plaq.lean.rules")
    P = api("su2plaq.lean.project")
    spec = _spec()
    qc = api("su2plaq.compress.baselines:general_circuit")(spec)
    assert isinstance(R.LEAN_RULES, dict) and len(R.LEAN_RULES) >= 1
    assert all(v.startswith("Su2Plaq.") for v in R.LEAN_RULES.values())
    out, log = api("su2plaq.compress.passes:polish")(qc, spec)
    for line in log:
        rule = str(line).split(":")[0].split()[0]
        assert rule in R.LEAN_RULES, (rule, line)
    ax = P.print_axioms(sorted(set(R.LEAN_RULES.values())), timeout=900)
    bad = {n: sorted(a - STANDARD) for n, a in ax.items() if a - STANDARD or "<unknown>" in a}
    assert not bad, bad


def test_program_lemma_file_checked(root, tmp_path):
    """A proposer may ship NNN-slug.lean next to NNN-slug.py: a valid lemma file -> proved (standard axioms); one with
    `sorry` -> failed; no file -> none.  Informative only — never part of validity."""
    _lean_dir(root)
    L = api("su2plaq.lean.lemmas")
    spec = _spec()
    src = pathlib.Path(api("su2plaq.compress.baselines:general_program_path")(spec))
    prog = tmp_path / "001-general-copy.py"
    shutil.copy(src, prog)
    assert L.check_program_lemmas(prog, timeout=120)["status"] == "none"
    lem = tmp_path / "001-general-copy.lean"
    lem.write_text("import Su2Plaq\n\ntheorem proposer_fact : (2 : Nat) + 2 = 4 := by decide\n")
    t0 = time.time()
    r = L.check_program_lemmas(prog, timeout=120)
    assert r["status"] == "proved" and r["axioms_ok"] and "proposer_fact" in r["theorems"], r
    assert time.time() - t0 <= 120
    lem.write_text("import Su2Plaq\n\ntheorem proposer_fact : (2 : Nat) + 2 = 5 := by sorry\n")
    r2 = L.check_program_lemmas(prog, timeout=120)
    assert r2["status"] == "failed", r2


@pytest.mark.slow
def test_round_records_lean_certificate(root, tmp_path):
    """A dry round 0 with the general program records a Lean certificate on the archived best, within the Lean budget
    (prompts/006 §0: <= 1200 s of Lean work per round), and validity stays the numerical verdict."""
    _lean_dir(root)
    spec = _spec()
    path = pathlib.Path(api("su2plaq.compress.baselines:general_program_path")(spec))
    rd = api("su2plaq.compress.round")
    A = api("su2plaq.compress.archive")
    info = rd.run_round(ENC, KIND, round=0, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(path)])
    assert info["n_valid"] >= 1 and info.get("lean_seconds", 0.0) <= 1200
    best = A.Archive.load(ENC, root=tmp_path).best()
    assert best is not None and best.valid and isinstance(best.lean, dict)
    assert best.lean["status"] == "certified", best.lean


@pytest.mark.slow
def test_archive_best_lean_status_recorded(root):
    """After the loop (gate): the real archive's global best carries a Lean status; `n_a` only for the two allowed reasons."""
    _lean_dir(root)
    A = api("su2plaq.compress.archive")
    best = A.Archive.load(ENC, root=root).best()
    assert best is not None and isinstance(best.lean, dict)
    assert best.lean["status"] in ("certified", "n_a"), best.lean
    if best.lean["status"] == "n_a":
        assert best.lean["reason"].startswith(("non_linear_angle", "phase_not_in_K")), best.lean
    text = api("su2plaq.compress.report:report_table")(ENC, KIND, root=root)
    assert "Lean" in text
