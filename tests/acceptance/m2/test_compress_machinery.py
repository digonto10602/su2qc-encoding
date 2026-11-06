"""M2 — compression machinery (prompts/002 §2.10, §5; design B §6; METHODS §9) on the 12-qubit encoding.
Tolerances are those of the evaluator (1e-10 / 1e-12) and the Ross-Selinger band; everything else is exact."""
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
import pytest
from qiskit import QuantumCircuit

import functools

from tests.acceptance._api import api, ross_selinger_band

ENC, KIND = "twelve", "step"


@functools.lru_cache(maxsize=None)
def _spec():
    return api("su2plaq.compress.spec:default_spec")(ENC, KIND)


@functools.lru_cache(maxsize=None)
def _general():
    return (api("su2plaq.compress.baselines:general_circuit")(_spec()), pathlib.Path(api("su2plaq.compress.baselines:general_program_path")(_spec())))


def _perturb_first_rotation(qc: QuantumCircuit, delta: float) -> QuantumCircuit:
    """Copy of qc with the first rotation angle shifted by delta.  Qiskit 2.5.2 stores standard gates natively and
    `inst.operation` is a fresh object on every access, so `inst.operation.params[0] = …` was a silent no-op (prompts/006
    §12 fix, 2026-11-05): the instruction is rebuilt and replaced in `out.data`."""
    from qiskit.circuit import CircuitInstruction
    out = qc.copy()
    for i, inst in enumerate(out.data):
        if inst.operation.name in ("rz", "p", "crz", "crx", "cp") and inst.operation.params:
            op = inst.operation.copy()
            old = float(op.params[0])
            op.params = [old + delta]
            out.data[i] = CircuitInstruction(op, inst.qubits, inst.clbits)
            assert abs(float(out.data[i].operation.params[0]) - (old + delta)) <= 1e-15 and abs(float(qc.data[i].operation.params[0]) - old) <= 1e-15
            return out
    raise AssertionError("no rotation found")


def _with_extra(qc: QuantumCircuit, fn) -> QuantumCircuit:
    out = qc.copy()
    fn(out)
    return out


# ---------------------------------------------------------------------------- spec + oracle (2.1)
def test_oracle_matches_exact_step():
    """oracle.target == encoding target 'step' (order 1) at the spec angles; column/element views agree; spec renders
    the hand-text with the registers, costs and tolerances; sha256 is stable."""
    spec = _spec()
    oracle = api("su2plaq.compress.oracle")
    enc = api("su2plaq.encodings.twelve:TwelveQubit")()
    assert spec.encoding == ENC and spec.kind == KIND and (spec.alpha, spec.beta) == (0.37, 0.61) and spec.order == 1
    assert tuple(spec.alt_angles) == ((0.91, 0.23), (1.70, 1.00)) and spec.tol_err == 1e-10 and spec.eps == 1e-6
    assert spec.tol_gauss == 1e-10 and not hasattr(spec, "tol_leak")  # prompts/004 (audit 001 N1, N6): one amplitude budget + Gauss
    V = oracle.target(spec)
    assert V.shape == (433, 433) and np.abs(V - enc.target("step", spec.alpha, spec.beta, order=1)).max() <= 1e-12
    col = oracle.column(spec, 0, top=5)          # [(row index, value), ...] sorted by |value| descending
    assert 1 <= len(col) <= 5 and abs(col[0][1] - V[col[0][0], 0]) <= 1e-12
    assert abs(col[0][1]) >= max(abs(V[:, 0])) - 1e-12
    assert abs(oracle.element(spec, 3, 3) - V[3, 3]) <= 1e-12
    assert "111" in oracle.codec(spec)
    blk = oracle.block(spec, 0)
    assert blk.shape == (2, 2) and np.abs(blk.conj().T @ blk - np.eye(2)).max() <= 1e-10
    text = spec.render()
    for needle in ("U_B", "U_E", "0.37", "0.61", "ccx", "rccx", "1e-10", "run_candidate", "DISCOVERY"):
        assert needle in text
    assert spec.sha256() == spec.sha256() and len(spec.sha256()) == 64


# ---------------------------------------------------------------------------- builder (2.2)
def test_builder_gateset():
    """Builder emits only BASIS u MACROS; a disallowed gate (mcx with 3 controls as a native gate, unitary, measure) is a
    BuilderError; alloc/free track the peak; reg() exposes the encoding registers."""
    spec = _spec()
    B = api("su2plaq.compress.builder")
    assert set(B.BASIS) == {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz"}
    assert set(B.MACROS) == {"ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}
    b = B.Builder(spec)
    d = b.reg("d")
    assert d == list(range(12)) and b.reg("o") == list(range(12, 28))
    a = b.alloc(2, "work")
    assert a == [28, 29]
    b.ccx(d[0], d[1], a[0]); b.rccx(d[2], d[3], a[1]); b.crx(0.3, a[0], d[4]); b.cp(0.2, d[5], d[6])
    b.h(d[7]); b.rz(0.1, d[8]); b.p(0.1, d[9]); b.swap(d[10], d[11]); b.ch(d[0], d[1]); b.crz(0.1, d[0], d[1]); b.ccz(d[0], d[1], d[2])
    b.rccx(d[2], d[3], a[1]); b.ccx(d[0], d[1], a[0])
    b.free(a)
    qc = b.circuit()
    assert qc.num_qubits == 30 and b.peak_qubits == 30
    assert {i.operation.name for i in qc.data} <= set(B.BASIS) | set(B.MACROS)
    from qiskit.circuit.library import MCXGate, UnitaryGate
    bad = QuantumCircuit(4); bad.append(MCXGate(3), [0, 1, 2, 3])
    with pytest.raises(B.BuilderError):
        B.Builder(spec).append_qiskit(bad, [0, 1, 2, 3])
    bad2 = QuantumCircuit(1); bad2.append(UnitaryGate(np.eye(2)), [0])
    with pytest.raises(B.BuilderError):
        B.Builder(spec).append_qiskit(bad2, [0])
    bad3 = QuantumCircuit(1, 1); bad3.measure(0, 0)
    with pytest.raises(B.BuilderError):
        B.Builder(spec).append_qiskit(bad3, [0])
    b2 = B.Builder(spec); b2.discover("DISCOVERY: squaring is CNOT-only"); b2.discover("x"); b2.discover("y")
    with pytest.raises(B.BuilderError):
        b2.discover("too many")
    assert len(b2.discoveries) == 3


def test_macro_costs_match_lowering():
    """MACRO_COST (CX, T_fixed, N_rot) equals the project's level-0 lowering for every macro (and cz)."""
    B = api("su2plaq.compress.builder")
    lm = api("su2plaq.metrics.logical:logical_metrics")
    th = 0.37
    for name, cost in B.MACRO_COST.items():
        qc = QuantumCircuit(3)
        if name in ("ccx", "rccx", "ccz"):
            getattr(qc, name)(0, 1, 2)
        elif name in ("crz", "crx", "cp"):
            getattr(qc, name)(th, 0, 1)
        else:
            getattr(qc, name)(0, 1)
        m = lm(qc)
        assert tuple(cost) == (m["cx"], m["t_fixed"], m["n_rot"]), name
    assert set(B.MACRO_COST) == set(B.MACROS) | {"cz"}


def test_builder_mcx_chain():
    """Builder.mcx with k >= 3 controls uses k-2 clean ancillas: exact k-control Toffoli (dense Operator check on
    k = 3, 4), cost 6 + 6(k-2) CX and 7 + 8(k-2) T, ancillas returned to |0>."""
    spec = _spec()
    from qiskit.circuit.library import MCXGate
    from qiskit.quantum_info import Operator

    B = api("su2plaq.compress.builder")
    lm = api("su2plaq.metrics.logical:logical_metrics")
    for k in (3, 4):
        b = B.Builder(n_qubits=k + 1)          # bare builder: k+1 fixed qubits, ancillas allocated by mcx
        qs = list(range(k + 1))
        b.mcx(qs[:k], qs[k])
        qc = b.circuit()
        n = qc.num_qubits
        assert n == (k + 1) + (k - 2)
        m = lm(qc)
        assert (m["cx"], m["t_fixed"], m["n_rot"]) == (6 + 6 * (k - 2), 7 + 8 * (k - 2), 0)
        # compare on the k+1 logical qubits with ancillas |0>: U restricted to ancilla = 0 in and out equals MCX
        U = Operator(qc).data
        ref = QuantumCircuit(k + 1); ref.append(MCXGate(k), qs)
        R = Operator(ref).data
        anc = [q for q in range(n) if q not in qs]
        idx = [i for i in range(2 ** n) if all(((i >> a) & 1) == 0 for a in anc)]
        sub = U[np.ix_(idx, idx)]
        # map idx (ancilla bits 0) to the (k+1)-qubit integer
        order = np.argsort([sum(((i >> q) & 1) << p for p, q in enumerate(qs)) for i in idx])
        sub = sub[np.ix_(order, order)]
        assert np.abs(sub - R).max() <= 1e-12
        assert np.abs(np.linalg.norm(U[:, idx], axis=0) - 1).max() <= 1e-12 and np.abs(U[np.ix_([i for i in range(2 ** n) if i not in idx], idx)]).max() <= 1e-12


# ---------------------------------------------------------------------------- evaluator adapter (2.3)
def test_evaluator_accepts_general_circuit():
    spec = _spec()
    general = _general()
    qc, path = general
    ev = api("su2plaq.compress.evaluate")
    assert path.exists() and path.read_text().lstrip().startswith('"""SUMMARY:')
    r = ev.evaluate_program(str(path), spec, mode="trial")
    assert r.valid and r.reason == "ok" and r.verdict.op_norm_error <= 1e-10 and r.verdict.leak_amplitude <= 1e-10  # prompts/004
    assert r.verdict.certified and r.verdict.gauss_residual <= 1e-10  # audit 001 N6: gauss=True is mandatory in the loop
    assert len(r.program_sha256) == 64 and r.summary
    r2 = ev.evaluate_circuit(qc, spec, mode="trial")
    assert r2.valid


def test_evaluator_accepts_global_phase():
    """x z x z on a fresh ancilla = -1 global phase: valid."""
    spec = _spec()
    general = _general()
    qc, _ = general
    ev = api("su2plaq.compress.evaluate")
    from qiskit import QuantumRegister
    out = qc.copy(); a = QuantumRegister(1, "anc_phase"); out.add_register(a)
    for g in ("x", "z", "x", "z"):
        getattr(out, g)(a[0])
    r = ev.evaluate_circuit(out, spec, mode="trial")
    assert r.valid and abs(r.verdict.phase + 1) <= 1e-10


def test_evaluator_rejects_wrong_gate():
    spec = _spec()
    general = _general()
    qc, _ = general
    r = api("su2plaq.compress.evaluate").evaluate_circuit(_with_extra(qc, lambda c: c.x(0)), spec, mode="trial")
    assert not r.valid and r.reason != "ok"


def test_evaluator_rejects_dirty_ancilla():
    spec = _spec()
    general = _general()
    qc, _ = general
    from qiskit import QuantumRegister
    out = qc.copy(); a = QuantumRegister(1, "anc_dirty"); out.add_register(a); out.cx(2, a[0])
    r = api("su2plaq.compress.evaluate").evaluate_circuit(out, spec, mode="trial")
    assert not r.valid and ("ancilla" in r.reason or "leak" in r.reason)


def test_evaluator_rejects_small_ancilla_leak():
    """prompts/004 (audit 001 N1): a proposer program whose uncompute leaves amplitude ~1e-6 on an ancilla must be invalid
    in the loop too — under the old weight tolerance (9e-13 <= 1e-12) it was accepted as 'exact'. Here ry(1.9e-6) on a
    fresh ancilla: leaked amplitude sin(0.95e-6) = 9.5e-7 on EVERY input, so the verdict does not depend on which physical
    states the trial subset samples (the data-controlled version of the auditor's case is pinned exactly in M0-E6)."""
    spec = _spec()
    general = _general()
    qc, _ = general
    from qiskit import QuantumRegister
    out = qc.copy(); a = QuantumRegister(1, "anc_small"); out.add_register(a); out.ry(1.9e-6, a[0])
    r = api("su2plaq.compress.evaluate").evaluate_circuit(out, spec, mode="trial")
    assert not r.valid and r.verdict is not None and r.verdict.leak_amplitude >= 9e-7 and r.verdict.op_norm_error > 1e-10


def test_evaluator_rejects_angle_error():
    """One rotation off by 1e-6 -> error ~1e-6 >> 1e-10: invalid."""
    spec = _spec()
    general = _general()
    qc, _ = general
    r = api("su2plaq.compress.evaluate").evaluate_circuit(_perturb_first_rotation(qc, 1e-6), spec, mode="trial")
    assert not r.valid and r.verdict is not None and r.verdict.op_norm_error > 1e-8


def test_evaluator_rejects_partial():
    """U_B alone is not the step (U_E factor missing): invalid."""
    spec = _spec()
    qc = api("su2plaq.circuits.twelve:build_UB")(spec.beta, with_outer=True)
    r = api("su2plaq.compress.evaluate").evaluate_circuit(qc, spec, mode="trial")
    assert not r.valid and r.verdict.op_norm_error > 1e-3


def test_evaluator_rejects_control_change():
    """X on an outer control qubit: writes_outer."""
    spec = _spec()
    general = _general()
    qc, _ = general
    assert "o" in [r.name for r in qc.qregs]
    r = api("su2plaq.compress.evaluate").evaluate_circuit(_with_extra(qc, lambda c: c.x(13)), spec, mode="trial")
    assert not r.valid and "outer" in r.reason


def test_metrics_match_qiskit_count_ops():
    spec = _spec()
    general = _general()
    qc, _ = general
    M = api("su2plaq.compress.metrics")
    lower = api("su2plaq.metrics.logical:lower")
    m = M.metrics(qc, spec, measured=False)
    low = lower(qc)
    assert m["cx"] == low.count_ops().get("cx", 0) and m["depth"] == low.depth() and m["qubits"] == qc.num_qubits
    assert m["t_fixed"] == low.count_ops().get("t", 0) + low.count_ops().get("tdg", 0) + sum(
        1 for i in low.data if i.operation.name == "rz" and abs(float(i.operation.params[0]) / (np.pi / 4) - round(float(i.operation.params[0]) / (np.pi / 4))) < 1e-9 and round(float(i.operation.params[0]) / (np.pi / 4)) % 2 == 1)
    key = M.key(m); cell = M.cell(m, 8)
    assert len(key) == 4 and key[0] == m["cx"] and len(cell) == 2 and cell[0] == int(np.floor(8 * np.log2(m["cx"] + 1)))


@pytest.mark.parametrize("eps", [1e-4, 1e-6, 1e-8])
def test_t_eps_in_ross_selinger_band(eps):
    S = api("su2plaq.compress.synth")
    lo, hi = ross_selinger_band(eps)
    for th in (0.37, 0.61, -0.555, 1.22):
        T = S.gridsynth_T(th, eps)
        assert lo <= T <= hi


def test_t_eps_deterministic():
    S = api("su2plaq.compress.synth")
    assert S.gridsynth_T(0.37, 1e-6) == S.gridsynth_T(0.37, 1e-6) == api("su2plaq.metrics.cliffordt:pygridsynth_tcount")(0.37, 1e-6)


def test_t_estimate_formula():
    spec = _spec()
    general = _general()
    qc, _ = general
    M = api("su2plaq.compress.metrics")
    m = M.metrics(qc, spec, measured=True)
    for eps in (1e-6, 1e-10):
        assert abs(m["t_estimate"][eps] - (m["t_fixed"] + m["n_rot"] * 3 * np.log2(1 / eps))) <= 1e-6
    assert m["t_eps"] >= m["t_fixed"] and m["synth_error_bound"] <= m["n_rot"] * spec.eps


# ---------------------------------------------------------------------------- archive, cache, provenance (2.4)
def _fake_entry(A, id_, valid, cx, t, depth, qubits, family="F1", rnd=1):
    return A.Entry(id=id_, program_path=f"compress/programs/twelve/{family}/{id_}.py", program_sha256="a" * 64, parent=None, family=family,
                   round=rnd, valid=valid, reason="ok" if valid else "error", key=(cx, t, depth, qubits) if valid else (float("inf"),) * 4,
                   cell=(int(np.floor(8 * np.log2(cx + 1))), int(np.floor(8 * np.log2(t + 1)))) if valid else None,
                   metrics_raw={"cx": cx, "t_eps": t, "depth_ct": depth, "qubits": qubits}, metrics_polished=None,
                   verdict_nominal={"ok": valid}, verdicts_alt=[], skeleton_equal=valid, discoveries=[], summary="s",
                   evaluator_sha256="e" * 64, spec_sha256="s" * 64, git_commit="0000000", versions={"qiskit": "2.5.2"},
                   seeds={"trial_seed": 0}, machine="test", wall_s=0.1, written_utc="2026-11-04T00:00:00Z")


def test_archive_roundtrip_and_elites(tmp_path):
    A = api("su2plaq.compress.archive")
    arch = A.Archive.load(ENC, root=tmp_path)
    assert arch.best() is None
    e1 = _fake_entry(A, "r01-F1-001", True, 100, 600, 500, 40)
    e2 = _fake_entry(A, "r01-F1-002", True, 100, 590, 520, 40)      # same cell, better key
    e3 = _fake_entry(A, "r01-F2-001", True, 60, 900, 400, 50, family="F2")  # different cell
    for e in (e1, e2, e3):
        assert arch.insert(e)
    arch.save()
    arch2 = A.Archive.load(ENC, root=tmp_path)
    assert sorted(x.id for x in arch2.entries()) == sorted(x.id for x in arch.entries())
    el = arch2.elites()
    assert set(e.id for e in el.values()) == {"r01-F1-002", "r01-F2-001"}
    assert arch2.best().id == "r01-F2-001" and arch2.family_best("F1").id == "r01-F1-002"


def test_archive_rejects_invalid(tmp_path):
    A = api("su2plaq.compress.archive")
    arch = A.Archive.load(ENC, root=tmp_path)
    bad = _fake_entry(A, "r01-F1-009", False, 1, 1, 1, 1)
    assert not arch.insert(bad) and arch.entries() == [] and arch.best() is None


def test_cache_keyed_by_code_hash(tmp_path):
    P = api("su2plaq.compress.provenance")
    h = P.code_hash()
    assert isinstance(h, str) and len(h) == 64 and h == P.code_hash()
    f = tmp_path / "x.py"; f.write_text("a = 1\n")
    h1 = P.code_hash(files=[f]); f.write_text("a = 2\n"); h2 = P.code_hash(files=[f])
    assert h1 != h2
    p1 = P.cache_path("e" * 64, "p" * 64, "s" * 64, root=tmp_path)
    p2 = P.cache_path("f" * 64, "p" * 64, "s" * 64, root=tmp_path)
    assert p1 != p2 and str(p1).startswith(str(tmp_path)) and "cache" in str(p1)


def test_entry_has_provenance_fields():
    spec = _spec()
    general = _general()
    qc, path = general
    ev = api("su2plaq.compress.evaluate"); A = api("su2plaq.compress.archive")
    r = ev.evaluate_program(str(path), spec, mode="trial")
    e = A.entry_from_result(r, program_path=str(path), family="seed", round=0, parent=None)
    for f in ("program_sha256", "evaluator_sha256", "spec_sha256", "git_commit", "versions", "seeds", "machine", "wall_s", "written_utc"):
        assert getattr(e, f) not in (None, "", {})
    assert e.spec_sha256 == spec.sha256() and e.program_sha256 == r.program_sha256 and len(e.evaluator_sha256) == 64


# ---------------------------------------------------------------------------- passes, baselines, skeleton (2.5)
def test_polish_valid_and_not_worse():
    spec = _spec()
    general = _general()
    qc, _ = general
    ev = api("su2plaq.compress.evaluate"); M = api("su2plaq.compress.metrics")
    out, log = api("su2plaq.compress.passes:polish")(qc, spec)
    r = ev.evaluate_circuit(out, spec, mode="trial")
    assert r.valid and isinstance(log, list)
    assert M.key(M.metrics(out, spec, measured=False)) <= M.key(M.metrics(qc, spec, measured=False))


def test_qiskit_l3_baseline_valid():
    spec = _spec()
    qc = api("su2plaq.compress.baselines:qiskit_l3")(spec, seed=12345)
    r = api("su2plaq.compress.evaluate").evaluate_circuit(qc, spec, mode="trial")
    assert r.valid


@pytest.mark.parametrize("source", ["paulo34", "lean22_v2", "spinnet15"])
def test_seed_import_declared(source):
    """import_seed returns a SeedCircuit (then it must be valid at its own angles) or a reason string."""
    spec = _spec()
    bl = api("su2plaq.compress.baselines")
    res = bl.import_seed(spec, source)
    assert isinstance(res, (str, bl.SeedCircuit))
    if isinstance(res, bl.SeedCircuit):
        r = bl.evaluate_seed(spec, res, mode="trial")
        assert r.valid, (source, r.reason)
        if res.fixed_angle:
            assert not res.can_be_parent


def test_skeleton_angle_independent_general():
    spec = _spec()
    general = _general()
    _, path = general
    ev = api("su2plaq.compress.evaluate")
    mod = ev.load_program(str(path))
    s1 = ev.skeleton(mod.build(spec).circuit())
    s2 = ev.skeleton(mod.build(spec.with_angles(*spec.alt_angles[0])).circuit())
    assert s1 == s2 and len(s1) > 0
    qc = mod.build(spec).circuit(); qc.x(0)
    assert ev.skeleton(qc) != s1
    r = ev.evaluate_program(str(path), spec, mode="full")
    assert r.valid and r.skeleton_equal and len(r.verdicts_alt) == 2 and all(v.ok for v in r.verdicts_alt)


# ---------------------------------------------------------------------------- CLIs, round, report (2.6)
def test_run_candidate_cli_trial_and_full(tmp_path, root):
    """`python -m su2plaq.compress.run_candidate <general> --encoding twelve --kind step --trial --json out` exits 0 with
    valid=true in <= 30 s (budget 10 s typical, 3x for a loaded machine); --full also valid."""
    spec = _spec()
    general = _general()
    _, path = general
    out = tmp_path / "trial.json"
    t0 = time.time()
    p = subprocess.run([sys.executable, "-m", "su2plaq.compress.run_candidate", str(path), "--encoding", ENC, "--kind", KIND, "--trial", "--json", str(out)],
                       cwd=root, capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": str(root / "src")})
    assert p.returncode == 0, p.stderr
    assert time.time() - t0 <= 30
    d = json.loads(out.read_text())
    assert d["valid"] is True and "metrics" in d and "op_norm_error" in d["verdict"]
    assert "valid" in p.stdout.lower()
    out2 = tmp_path / "full.json"
    p2 = subprocess.run([sys.executable, "-m", "su2plaq.compress.run_candidate", str(path), "--encoding", ENC, "--kind", KIND, "--full", "--json", str(out2)],
                        cwd=root, capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": str(root / "src")})
    assert p2.returncode == 0, p2.stderr
    d2 = json.loads(out2.read_text())
    assert d2["valid"] is True and d2["skeleton_equal"] is True and d2["metrics"]["t_eps"] >= d2["metrics"]["t_fixed"]


def test_round_dry_run_end_to_end(tmp_path):
    """A dry round with the general program as the only proposal: brief written, program evaluated, archived, round
    JSON and attempts/discoveries files produced under a temporary root."""
    spec = _spec()
    general = _general()
    _, path = general
    rd = api("su2plaq.compress.round")
    A = api("su2plaq.compress.archive")
    info0 = rd.run_round(ENC, KIND, round=0, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(path)])
    assert info0["round"] == 0 and info0["n_valid"] >= 1
    brief = api("su2plaq.compress.brief:make_brief")(ENC, KIND, round=1, family="seed", root=tmp_path)
    assert pathlib.Path(brief).exists() and "Rewrite the parent" in pathlib.Path(brief).read_text()
    info = rd.run_round(ENC, KIND, round=1, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(path)])
    assert info["round"] == 1 and info["n_valid"] >= 1
    rj = tmp_path / "results" / "compress" / ENC / "round-001.json"
    assert rj.exists()
    d = json.loads(rj.read_text())
    assert d["round"] == 1 and len(d["entries"]) >= 1 and "git_commit" in d["provenance"]
    arch = A.Archive.load(ENC, root=tmp_path)
    assert arch.best() is not None and arch.best().valid
    assert (tmp_path / "compress" / "attempts" / f"{ENC}.jsonl").exists()


def test_report_table_from_results(tmp_path):
    spec = _spec()
    general = _general()
    _, path = general
    rd = api("su2plaq.compress.round")
    rd.run_round(ENC, KIND, round=0, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(path)])
    text = api("su2plaq.compress.report:report_table")(ENC, KIND, root=tmp_path)
    for col in ("qubits", "CX", "T_fixed", "N_rot", "T(1e-6)", "depth", "verdict"):
        assert col in text
    assert "general" in text
    summary = tmp_path / "results" / "compress" / ENC / "summary.json"
    assert summary.exists()


# ---------------------------------------------------------------------------- gate (2.7)
@pytest.mark.slow
def test_archive_best_valid_and_not_worse_than_seed(root):
    """After the loop: the global best of the real archive re-evaluates from its program source as valid (full mode) and
    its key is <= the best round-0 key (seeds); the entry's recorded key equals the fresh evaluation's key."""
    spec = _spec()
    A = api("su2plaq.compress.archive"); ev = api("su2plaq.compress.evaluate"); M = api("su2plaq.compress.metrics")
    arch = A.Archive.load(ENC, root=root)
    best = arch.best()
    assert best is not None and best.valid
    r = ev.evaluate_program(str(root / best.program_path), spec, mode="full")
    assert r.valid and r.skeleton_equal
    fresh = M.key(r.metrics)
    assert tuple(fresh) == tuple(best.key)
    seeds = [e for e in arch.entries() if e.round == 0 and e.valid]
    assert seeds and tuple(best.key) <= min(tuple(e.key) for e in seeds)
    assert best.evaluator_sha256 == api("su2plaq.compress.provenance:code_hash")()
