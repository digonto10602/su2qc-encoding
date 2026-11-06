"""Unit tests for su2plaq.compress.{evaluate,metrics,synth,provenance,run_candidate} (M2 step 2.3)."""
import json
import os
import pathlib
import subprocess
import sys
import time

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.circuits import twelve as C
from su2plaq.compress import evaluate as E
from su2plaq.compress import metrics as M
from su2plaq.compress import provenance as P
from su2plaq.compress import synth as S
from su2plaq.compress.spec import TaskSpec, default_spec
from su2plaq.evaluate import evaluator as ev

ROOT = pathlib.Path(__file__).resolve().parents[2]
STEP = default_spec("twelve", "step")
UE = default_spec("twelve", "UE")

HEADER = '"""SUMMARY: {summary}\n\nDISCOVERY: one idea\n"""\nFAMILY = "F0"\nPARENT = None\n\nfrom su2plaq.compress.builder import Builder\n\n\n'
UE_BODY = '''def build(spec):
    b = Builder(spec)
    d = b.reg("d")
    for link in range(4):
        b.p({sign}0.75 * spec.alpha, d[3 * link + 2])
    return b
'''


def write(tmp_path, body, name="001-p.py", summary="test"):
    f = tmp_path / name
    f.write_text(HEADER.format(summary=summary) + body)
    return f


def step_circuit(alpha=0.37, beta=0.61, order=1):
    return C.build_step(alpha, beta, order, with_outer=True)


# ------------------------------------------------------------------------------------------------ circuits
def test_trial_and_full_accept_the_reference_step():
    qc = step_circuit()
    r = E.evaluate_circuit(qc, STEP, "trial")
    assert r.valid and r.reason == "ok" and r.verdict.certified and r.verdict.n_inputs == STEP.trial_inputs
    assert r.verdict.engine == "sparse" and r.metrics["measured"] is False and r.metrics["qubits"] == qc.num_qubits == 50
    alts = [step_circuit(a, b) for a, b in STEP.alt_angles]
    rf = E.evaluate_circuit(qc, STEP, "full", alt_circuits=alts)
    assert rf.valid and rf.skeleton_equal and len(rf.verdicts_alt) == 2 and all(v.ok for v in rf.verdicts_alt)
    assert rf.verdict.n_inputs == 433 and rf.metrics["measured"] is True and rf.metrics["t_eps"] >= rf.metrics["t_fixed"]
    # a skeleton that depends on the angle is rejected
    bad_alt = [step_circuit(a, b) for a, b in STEP.alt_angles]
    bad_alt[0].x(0)
    r2 = E.evaluate_circuit(qc, STEP, "full", alt_circuits=bad_alt)
    assert not r2.valid and r2.reason == "skeleton" and not r2.skeleton_equal


def test_wrong_circuits_are_invalid_with_the_evaluator_reason():
    qc = step_circuit()
    wrong = qc.copy()
    wrong.x(0)
    assert not E.evaluate_circuit(wrong, STEP, "trial").valid
    dirty = qc.copy()
    a = QuantumRegister(1, "d1")
    dirty.add_register(a)
    dirty.cx(2, a[0])
    r = E.evaluate_circuit(dirty, STEP, "trial")
    assert not r.valid and r.reason in ("dirty_ancilla", "leak")
    outer = qc.copy()
    outer.x(13)
    assert E.evaluate_circuit(outer, STEP, "trial").reason == "writes_outer"
    small = qc.copy()
    a2 = QuantumRegister(1, "d2")
    small.add_register(a2)
    small.ry(1.9e-6, a2[0])              # also a disallowed gate: the numbers are still reported, the verdict is the leak
    r = E.evaluate_circuit(small, STEP, "trial")
    assert not r.valid and r.verdict.leak_amplitude >= 9e-7 and r.reason in ("dirty_ancilla", "leak")
    partial = C.build_UB(STEP.beta, with_outer=True)
    assert E.evaluate_circuit(partial, STEP, "trial").verdict.op_norm_error > 1e-3


def test_disallowed_gate_alone_is_not_valid_even_if_exact():
    qc = step_circuit()
    qc.sx(0)
    qc.sxdg(0)                            # exact identity, but sx is not in BASIS u MACROS
    r = E.evaluate_circuit(qc, STEP, "trial")
    assert r.verdict.ok and not r.valid and r.reason == "disallowed_gate"


def test_unverified_is_never_valid(monkeypatch):
    real = ev.Verdict

    def fake(qc, spec, mode, budget):
        v = real(ok=True, reason="ok", op_norm_error=0.0, max_leak=0.0, dirty_ancilla=0.0, phase=1 + 0j, outer_bits_read=0,
                 n_blocks=1, gauss_residual=0.0, method="physical", engine="aer_mps", seconds=0.0, failing_inputs=[], n_inputs=1,
                 certified=False)
        return v

    monkeypatch.setattr(E, "_one_verdict", fake)
    r = E.evaluate_circuit(step_circuit(), STEP, "trial")
    assert not r.valid and r.reason == "unverified"


def test_qubit_cap_uses_the_circuit_not_builder_attributes():
    spec = TaskSpec(**{**STEP.to_dict(), "max_qubits": 40})
    r = E.evaluate_circuit(step_circuit(), spec, "trial")
    assert not r.valid and r.reason == "max_qubits" and r.verdict is None


def test_time_limit_raises():
    with pytest.raises(E.EvalTimeout):
        with E._time_limit(0.2):
            time.sleep(2)
    with E._time_limit(5):
        pass


def test_states_subset_matches_full_columns_and_detects_errors():
    from su2plaq.compress import oracle
    from su2plaq.encodings.twelve import TwelveQubit

    enc = TwelveQubit()
    V = oracle.target(STEP)
    qc = step_circuit()
    full = ev.evaluate(qc, enc, V, method="physical")
    sub = np.array([3, 40, 100, 250, 400])
    part = ev.evaluate(qc, enc, V, states=sub)
    assert full.ok and part.ok and part.n_inputs == 5 and part.method == "physical"
    wrong = qc.copy()
    wrong.rz(1e-6, 2)
    vw = ev.evaluate(wrong, enc, V, states=np.arange(433)[::7])
    assert not vw.ok and vw.op_norm_error > 1e-8
    with pytest.raises(ValueError):
        ev.evaluate(qc, enc, V, states=[])
    with pytest.raises(ValueError):
        ev.evaluate(qc, enc, V, states=[0], method="inner_span")


# ------------------------------------------------------------------------------------------------ programs
def test_program_good_and_wrong_angle(tmp_path):
    good = write(tmp_path, UE_BODY.format(sign="-"))
    r = E.evaluate_program(good, UE, "full")
    assert r.valid and r.skeleton_equal and len(r.verdicts_alt) == 2 and len(r.program_sha256) == 64 and r.summary == "test"
    assert r.discoveries == ["DISCOVERY: one idea"]
    wrong = write(tmp_path, UE_BODY.format(sign="+"), name="002-wrong.py")
    r2 = E.evaluate_program(wrong, UE, "trial")
    assert not r2.valid and r2.reason == "error" and r2.verdict.op_norm_error > 0.1
    # the hash is the file's, and a changed file is a different program
    assert r2.program_sha256 != r.program_sha256


def test_program_contract_violations(tmp_path):
    cases = {
        "import os": "import os\n\n" + UE_BODY.format(sign="-"),
        "import su2plaq.evaluate.evaluator": "import su2plaq.evaluate.evaluator\n\n" + UE_BODY.format(sign="-"),
        "from su2plaq.circuits import twelve": "from su2plaq.circuits import twelve\n\n" + UE_BODY.format(sign="-"),
        "open": "x = open('/etc/passwd')\n\n" + UE_BODY.format(sign="-"),
        "exec": "exec('1')\n\n" + UE_BODY.format(sign="-"),
        "relative": "from . import x\n\n" + UE_BODY.format(sign="-"),
    }
    for nm, body in cases.items():
        r = E.evaluate_program(write(tmp_path, body, name=f"c-{abs(hash(nm))}.py"), UE, "trial")
        assert not r.valid and r.reason == "contract", nm
    nohdr = tmp_path / "nohdr.py"
    nohdr.write_text("def build(spec):\n    return None\n")
    assert E.evaluate_program(nohdr, UE, "trial").reason == "contract"


def test_program_build_failures(tmp_path):
    boom = write(tmp_path, "def build(spec):\n    raise RuntimeError('boom')\n", name="003-boom.py")
    r = E.evaluate_program(boom, UE, "trial")
    assert not r.valid and r.reason == "build_error" and "boom" in r.message
    wrongtype = write(tmp_path, "def build(spec):\n    return 3\n", name="004-type.py")
    r = E.evaluate_program(wrongtype, UE, "trial")
    assert not r.valid and r.reason == "contract"
    bad_gate = write(tmp_path, 'def build(spec):\n    b = Builder(spec)\n    b.cx(0, 0)\n    return b\n', name="005-gate.py")
    assert E.evaluate_program(bad_gate, UE, "trial").reason == "build_error"


def test_program_build_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "BUILD_TIMEOUT_S", 3.0)
    loop = write(tmp_path, "def build(spec):\n    while True:\n        pass\n", name="006-loop.py")
    t0 = time.time()
    r = E.evaluate_program(loop, UE, "trial")
    assert not r.valid and r.reason == "build_timeout" and time.time() - t0 < 30


def test_program_with_angle_dependent_skeleton_is_rejected(tmp_path):
    body = '''def build(spec):
    b = Builder(spec)
    d = b.reg("d")
    for link in range(4):
        b.p(-0.75 * spec.alpha, d[3 * link + 2])
    if spec.alpha > 0.5:
        b.x(d[0])
        b.x(d[0])
    return b
'''
    r = E.evaluate_program(write(tmp_path, body, name="007-skel.py"), UE, "full")
    assert not r.valid and r.reason == "skeleton" and not r.skeleton_equal


def test_load_program_checks_the_contract_and_skeleton_ignores_angles(tmp_path):
    f = write(tmp_path, UE_BODY.format(sign="-"))
    mod = E.load_program(f)
    s1 = E.skeleton(mod.build(UE).circuit())
    s2 = E.skeleton(mod.build(UE.with_angles(0.91, 0.23)).circuit())
    assert s1 == s2 == [("p", (q,)) for q in (2, 5, 8, 11)]
    with pytest.raises(E.ContractError):
        E.load_program(write(tmp_path, "import os\n" + UE_BODY.format(sign="-"), name="x.py"))


def test_run_candidate_cli(tmp_path):
    good = write(tmp_path, UE_BODY.format(sign="-"))
    out = tmp_path / "o.json"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    p = subprocess.run([sys.executable, "-m", "su2plaq.compress.run_candidate", str(good), "--kind", "UE", "--trial", "--json", str(out)],
                       capture_output=True, text=True, cwd=ROOT, env=env)
    assert p.returncode == 0 and p.stdout.startswith("valid") and json.loads(out.read_text())["valid"] is True
    d = json.loads(out.read_text())
    assert "op_norm_error" in d["verdict"] and d["metrics"]["qubits"] == 28 and d["mode"] == "trial"
    bad = write(tmp_path, UE_BODY.format(sign="+"), name="002-bad.py")
    p = subprocess.run([sys.executable, "-m", "su2plaq.compress.run_candidate", str(bad), "--kind", "UE", "--trial"],
                       capture_output=True, text=True, cwd=ROOT, env=env)
    assert p.returncode == 1 and p.stdout.startswith("invalid: error")


# ------------------------------------------------------------------------------------------------ metrics, synth, provenance
def test_metrics_measured_and_estimated_agree_in_counts():
    qc = step_circuit()
    est, meas = M.metrics(qc, STEP, measured=False), M.metrics(qc, STEP, measured=True)
    for k in ("cx", "t_fixed", "n_rot", "depth", "qubits"):
        assert est[k] == meas[k]
    assert meas["t_eps"] >= meas["t_fixed"] and abs(est["t_eps"] - est["t_estimate"][1e-6]) < 1e-9
    assert est["depth_ct"] == est["depth"] <= meas["depth_ct"] and meas["synth_error_bound"] == meas["n_rot"] * STEP.eps


def test_key_cell_and_invalid_key():
    m = {"cx": 100, "t_eps": 600, "depth_ct": 500, "qubits": 40}
    assert S.key(m) == (100, 600, 500, 40) and S.cell(m, 8) == (int(np.floor(8 * np.log2(101))), int(np.floor(8 * np.log2(601))))
    assert S.INVALID_KEY > S.key(m)


def test_gridsynth_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "CACHE_DIR", tmp_path / "gs")
    t1 = S.gridsynth_T(0.4321, 1e-5)
    assert any((tmp_path / "gs").iterdir())
    assert S.gridsynth_T(0.4321, 1e-5) == t1
    from su2plaq.metrics.cliffordt import pygridsynth_tcount

    assert t1 == pygridsynth_tcount(0.4321, 1e-5)


def test_code_hash_depends_on_the_files_and_cache_path_on_all_three_keys(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("a = 1\n")
    h1 = P.code_hash([f])
    f.write_text("a = 2\n")
    assert P.code_hash([f]) != h1 and P.code_hash() == P.code_hash() and len(P.code_hash()) == 64
    ps = {P.cache_path(e, p, s, root=tmp_path) for e in "ef" for p in "pq" for s in "st"}
    assert len(ps) == 8


# ------------------------------------------------------------------------------------------------ tester 027: N1, N2, N4
ATTACKS = {
    "np.save": 'import numpy as np\nnp.save({m!r}, np.zeros(1))\n',
    "np.savetxt": 'import numpy as np\nnp.savetxt({m!r}, np.zeros(1))\n',
    "builtins-open via Builder globals": 'from su2plaq.compress.builder import Builder as _B\n_B.__init__.__globals__["__builtins__"]["open"]({m!r}, "w").write("x")\n',
    "pathlib via the builder module": 'import su2plaq.compress.builder as BB\nBB.pathlib.Path({m!r}).write_text("x")\n',
    "numpy.lib._npyio_impl (the module behind numpy.lib.npyio)": 'import numpy as np\nimport numpy.lib._npyio_impl as nio\nnio.save({m!r}, np.zeros(1))\n',
    "os.system via pathlib": 'import su2plaq.compress.builder as BB\nBB.pathlib.os.system("touch " + {m!r})\n',
    "os.popen via pathlib": 'import su2plaq.compress.builder as BB\nBB.pathlib.os.popen("touch " + {m!r}).read()\n',
    "mkdir via pathlib": 'import su2plaq.compress.builder as BB\nBB.pathlib.Path({m!r}).mkdir()\n',
    "os.open O_CREAT via pathlib": 'import su2plaq.compress.builder as BB\nBB.pathlib.os.close(BB.pathlib.os.open({m!r}, BB.pathlib.os.O_CREAT | BB.pathlib.os.O_WRONLY))\n',
    "os.remove of a project file": 'import su2plaq.compress.builder as BB\nBB.pathlib.os.remove({m!r})\n',
}


@pytest.mark.parametrize("name", list(ATTACKS))
def test_worker_blocks_file_writes_and_spawns(tmp_path, name):
    marker = tmp_path / "MARKER"
    if name == "os.remove of a project file":
        marker.write_text("keep me")
    body = ATTACKS[name].format(m=str(marker)) + "\n\n" + UE_BODY.format(sign="-")
    f = tmp_path / "evil.py"
    f.write_text('"""SUMMARY: attack.\n"""\nFAMILY = "F0"\nPARENT = None\n\nfrom su2plaq.compress.builder import Builder\n' + body)
    # the AST scan lets these through on purpose (only the worker guard is under test)
    E._scan_source(f.read_text())
    r = E.evaluate_program(f, UE, "trial")
    assert not r.valid and r.reason == "build_error" and "PermissionError" in r.message, (name, r.reason, r.message[:200])
    if name == "os.remove of a project file":
        assert marker.read_text() == "keep me"
    else:
        assert not marker.exists(), name


def test_worker_still_runs_legitimate_programs_that_use_numpy_and_the_oracle(tmp_path):
    body = '''import numpy as np
from su2plaq.compress import oracle


def build(spec):
    V = oracle.target(spec)
    th = float(np.angle(V[0, 0]))         # emission-time classical computation
    b = Builder(spec)
    d = b.reg("d")
    for link in range(4):
        b.p(-0.75 * spec.alpha + 0.0 * th, d[3 * link + 2])
    return b
'''
    f = tmp_path / "ok.py"
    f.write_text('"""SUMMARY: uses the oracle.\n"""\nFAMILY = "F0"\nPARENT = None\n\nfrom su2plaq.compress.builder import Builder\n' + body)
    assert E.evaluate_program(f, UE, "trial").valid


def test_program_edited_during_evaluation_is_evaluated_under_its_true_sha(tmp_path, monkeypatch):
    f = write(tmp_path, UE_BODY.format(sign="-"))
    original = f.read_bytes()
    real_scan = E._scan_source

    def scan_then_swap(source):
        out = real_scan(source)
        f.write_text(f.read_text().replace("-0.75", "+0.75"))      # a different, wrong program appears after hashing
        return out

    monkeypatch.setattr(E, "_scan_source", scan_then_swap)
    r = E.evaluate_program(f, UE, "trial")
    import hashlib

    assert r.valid and r.program_sha256 == hashlib.sha256(original).hexdigest()
    assert f.read_bytes() != original                                  # the swap really happened


GARBAGE = {
    "garbage word": lambda ver, th, eps, w: json.dumps({"version": ver, "theta": repr(th), "eps": repr(eps), "word": "HTHT",
                                                       "sha256": S._checksum(ver, th, eps, "HTHT")}),
    "wrong checksum": lambda ver, th, eps, w: json.dumps({"version": ver, "theta": repr(th), "eps": repr(eps), "word": w, "sha256": "0" * 64}),
    "other version": lambda ver, th, eps, w: json.dumps({"version": "0.0", "theta": repr(th), "eps": repr(eps), "word": w,
                                                        "sha256": S._checksum("0.0", th, eps, w)}),
    "other angle": lambda ver, th, eps, w: json.dumps({"version": ver, "theta": repr(0.1), "eps": repr(eps), "word": w,
                                                      "sha256": S._checksum(ver, 0.1, eps, w)}),
    "bad letters": lambda ver, th, eps, w: json.dumps({"version": ver, "theta": repr(th), "eps": repr(eps), "word": "not a word ###",
                                                      "sha256": S._checksum(ver, th, eps, "not a word ###")}),
    "word of another angle, valid checksum": lambda ver, th, eps, w: json.dumps(
        {"version": ver, "theta": repr(th), "eps": repr(eps), "word": S.pygridsynth_word(1.3, eps), "sha256": S._checksum(ver, th, eps, S.pygridsynth_word(1.3, eps))}),
    "empty file": lambda ver, th, eps, w: "",
    "truncated json": lambda ver, th, eps, w: '{"version": "1.2.0", "the',
    "legacy plain text": lambda ver, th, eps, w: w,
}


@pytest.mark.parametrize("name", list(GARBAGE))
def test_corrupt_synth_cache_entries_are_recomputed_not_trusted(tmp_path, monkeypatch, name):
    from importlib.metadata import version

    monkeypatch.setattr(S, "CACHE_DIR", tmp_path)
    th, eps = 0.4321, 1e-5
    good = S.pygridsynth_word(th, eps)
    ver = version("pygridsynth")
    import hashlib

    f = tmp_path / (hashlib.sha256(f"{ver}|{float(th)!r}|{float(eps)!r}".encode()).hexdigest() + ".json")
    f.write_text(GARBAGE[name](ver, th, eps, good))
    assert S.gridsynth_word(th, eps) == good and S.gridsynth_T(th, eps) == good.count("T")
    assert S._read_valid(f, ver, th, eps) == good               # the entry was repaired on disk


def test_states_must_be_integer_indices():
    from su2plaq.encodings.twelve import TwelveQubit

    enc = TwelveQubit()
    from su2plaq.compress import oracle

    qc = step_circuit()
    for bad in ([0.5], np.array([1.0, 2.0])):
        with pytest.raises(ValueError):
            ev.evaluate(qc, enc, oracle.target(STEP), states=bad)


# ------------------------------------------------------------------------------------------------ N6 (forged meta) and the cache
def test_forged_meta_and_exit_is_a_build_error_not_an_exception(tmp_path):
    body = '''import su2plaq.compress.builder as BB


def build(spec):
    # impersonate a successful worker: write the (whitelisted) meta file and exit without any circuit file
    meta = BB.pathlib.sys.argv[5]
    BB.pathlib.Path(meta).write_text('{"discoveries": [[], [], []]}')
    BB.pathlib.os._exit(0)
'''
    f = tmp_path / "forge.py"
    f.write_text('"""SUMMARY: forge.\n"""\nFAMILY = "F0"\nPARENT = None\n\nfrom su2plaq.compress.builder import Builder\n' + body)
    r = E.evaluate_program(f, UE, "trial")
    assert not r.valid and r.reason == "build_error" and r.verdict is None and "without writing" in r.message


def test_worker_output_checks(tmp_path, monkeypatch):
    # malformed meta, wrong circuit count, missing circuit file: all build_error
    import subprocess as sp

    real_run = sp.run

    def fake_run_factory(mutate):
        def run(cmd, **kw):
            p = real_run(cmd, **kw)
            out, meta = pathlib.Path(cmd[-2]), pathlib.Path(cmd[-1])
            mutate(out, meta)
            return p
        return run

    good = write(tmp_path, UE_BODY.format(sign="-"))
    for name, mutate in {"missing circuits": lambda o, m: o.unlink(), "meta not json": lambda o, m: m.write_text("not json"),
                         "meta not a dict": lambda o, m: m.write_text("[1]"), "corrupt qpy": lambda o, m: o.write_bytes(b"junk")}.items():
        monkeypatch.setattr(E.subprocess, "run", fake_run_factory(mutate))
        r = E.evaluate_program(good, UE, "trial")
        assert not r.valid and r.reason == "build_error", name
    monkeypatch.undo()
    assert E.evaluate_program(good, UE, "trial").valid


def test_program_result_cache_is_keyed_by_code_hash(tmp_path, monkeypatch):
    good = write(tmp_path, UE_BODY.format(sign="-"))
    r1 = E.evaluate_program(good, UE, "full", cache=True, root=tmp_path)
    cached = list((tmp_path / "compress" / "cache").rglob("*.json"))
    assert len(cached) == 1 and r1.valid
    calls = []
    real = E._evaluate_program_bytes
    monkeypatch.setattr(E, "_evaluate_program_bytes", lambda *a, **k: calls.append(1) or real(*a, **k))
    r2 = E.evaluate_program(good, UE, "full", cache=True, root=tmp_path)
    assert not calls and r2.valid and r2.program_sha256 == r1.program_sha256 and r2.verdict.op_norm_error == r1.verdict.op_norm_error
    assert len(r2.verdicts_alt) == 2 and r2.metrics["t_eps"] == r1.metrics["t_eps"] and r2.spec_sha256 == UE.sha256()
    # another evaluator code hash (any source edit) never hits the old entry
    monkeypatch.setattr(P, "code_hash", lambda files=None: "f" * 64)
    E.evaluate_program(good, UE, "full", cache=True, root=tmp_path)
    assert calls == [1]
    # trial results are not cached
    E.evaluate_program(good, UE, "trial", cache=True, root=tmp_path)
    assert len(list((tmp_path / "compress" / "cache").rglob("*.json"))) == 2


# ------------------------------------------------------------------------------------------------ tester 030: cache integrity
def _cache_file(root):
    files = list((root / "compress" / "cache").rglob("*.json"))
    assert len(files) == 1
    return files[0]


@pytest.mark.parametrize("tamper", ["flip valid", "zero metrics", "bad checksum", "other program sha", "other evaluator meta",
                                    "claim valid with wrong verdict", "trial mode", "garbage"])
def test_tampered_cache_entries_are_ignored_and_the_program_is_reevaluated(tmp_path, tamper):
    bad = write(tmp_path, UE_BODY.format(sign="+"), name="002-wrong.py")         # an INVALID program
    r0 = E.evaluate_program(bad, UE, "full", cache=True, root=tmp_path)
    assert not r0.valid
    cf = _cache_file(tmp_path)
    d = json.loads(cf.read_text())
    p = d["payload"]
    if tamper == "flip valid":
        p["valid"], p["reason"] = True, "ok"
    elif tamper == "zero metrics":
        p["valid"], p["reason"], p["metrics"] = True, "ok", {"cx": 0, "t_eps": 0, "depth_ct": 0, "qubits": 0, "t_fixed": 0}
    elif tamper == "bad checksum":
        d["checksum"] = "0" * 64
    elif tamper == "other program sha":
        p["program_sha256"] = "1" * 64
    elif tamper == "other evaluator meta":
        d["meta"]["evaluator_sha256"] = "2" * 64
    elif tamper == "claim valid with wrong verdict":
        p["valid"], p["reason"] = True, "ok"           # verdict stays the failing one
        d["checksum"] = E.hashlib.sha256(E._canonical({"meta": d["meta"], "payload": p}).encode()).hexdigest()   # even a re-signed lie
    elif tamper == "trial mode":
        p["mode"] = "trial"
    if tamper != "garbage":
        if tamper not in ("bad checksum", "claim valid with wrong verdict"):
            d["checksum"] = E.hashlib.sha256(E._canonical({"meta": d["meta"], "payload": p}).encode()).hexdigest()   # re-signed
        cf.write_text(json.dumps(d))
    else:
        cf.write_text("{ not json")
    calls = []
    real = E._evaluate_program_bytes
    E._evaluate_program_bytes = lambda *a, **k: calls.append(1) or real(*a, **k)
    try:
        r = E.evaluate_program(bad, UE, "full", cache=True, root=tmp_path)
    finally:
        E._evaluate_program_bytes = real
    assert calls == [1] and not r.valid and r.reason == r0.reason       # never served from the tampered entry
    again = json.loads(cf.read_text())                                  # and the entry was repaired
    assert again["payload"]["valid"] is False and again["payload"]["program_sha256"] == r0.program_sha256


def test_cache_entry_of_another_program_is_not_served(tmp_path):
    good_p = write(tmp_path, UE_BODY.format(sign="-"), name="001-good.py")
    bad_p = write(tmp_path, UE_BODY.format(sign="+"), name="002-wrong.py")
    E.evaluate_program(good_p, UE, "full", cache=True, root=tmp_path)
    good_cache = _cache_file(tmp_path)
    E.evaluate_program(bad_p, UE, "full", cache=True, root=tmp_path)
    files = sorted((tmp_path / "compress" / "cache").rglob("*.json"))
    assert len(files) == 2
    bad_cf = [f for f in files if f != good_cache][0]
    bad_cf.write_text(good_cache.read_text())                           # copy the GOOD program's entry onto the bad one's path
    r = E.evaluate_program(bad_p, UE, "full", cache=True, root=tmp_path)
    assert not r.valid


def test_an_untampered_cache_entry_is_still_served(tmp_path, monkeypatch):
    good_p = write(tmp_path, UE_BODY.format(sign="-"))
    r1 = E.evaluate_program(good_p, UE, "full", cache=True, root=tmp_path)
    monkeypatch.setattr(E, "_evaluate_program_bytes", lambda *a, **k: pytest.fail("re-evaluated"))
    r2 = E.evaluate_program(good_p, UE, "full", cache=True, root=tmp_path)
    assert r2.valid and r2.verdict.op_norm_error == r1.verdict.op_norm_error


def test_cached_result_equals_the_fresh_one_including_float_keyed_tables(tmp_path):
    good_p = write(tmp_path, UE_BODY.format(sign="-"))
    r1 = E.evaluate_program(good_p, UE, "full", cache=True, root=tmp_path)
    r2 = E.evaluate_program(good_p, UE, "full", cache=True, root=tmp_path)
    assert all(isinstance(k, float) for k in r2.metrics["t_estimate"]) and set(r2.metrics["t_estimate"]) == set(r1.metrics["t_estimate"])
    assert all(isinstance(k, float) for k in r2.metrics["t_measured"]) and r2.metrics["t_measured"] == r1.metrics["t_measured"]
    assert r2.metrics == r1.metrics


def test_cache_key_changes_with_package_versions(tmp_path):
    v = P.package_versions()
    assert set(v) == {"qiskit", "qiskit_aer", "pygridsynth"}
    base = P.cache_path("e" * 64, "p" * 64, "s" * 64, root=tmp_path)
    assert base == P.cache_path("e" * 64, "p" * 64, "s" * 64, root=tmp_path, versions=v)        # default = installed versions
    for name in v:
        other = P.cache_path("e" * 64, "p" * 64, "s" * 64, root=tmp_path, versions={**v, name: v[name] + ".post1"})
        assert other != base and other.parent == base.parent, name
