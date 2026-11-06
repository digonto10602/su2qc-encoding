"""M4 — compression of the spin-network step circuit with the laptop's loop (prompts/104 §1–§4; prompts/001 §4;
prompts/002 §5 instantiated for `spinnet`).

The laptop's `su2plaq.compress.*` is the machinery; `su2plaq.spinnet.loop` registers the encoding at run time, replaces
the build worker (so that the sandboxed subprocess knows the encoding) and runs round 0 with the spin-network seeds.
Tolerances are the spec's (1e-10 on the combined error and on Gauss) and exact counts; time limits as justified in
prompts/104 §4.  Gate tests (`slow`) read the real archive; everything else runs under `tmp_path`.

PENDING rule: a missing module / attribute / NotImplementedError fails with `PENDING:` (conftest + `_api.api`)."""
from __future__ import annotations

import functools
import json
import pathlib
import time

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction

from tests.acceptance._api import api

ENC, KIND = "spinnet", "step"
NOMINAL = (0.37, 0.61)
ALTS = ((0.91, 0.23), (1.70, 1.00))
SEED_LABELS = {"general", "general+polish", "qiskit_l3", "spinnet_v2_pairs9", "spinnet_v2_flags4", "spinnet_v2_flags5",
               "spinnet_v2_flags6"}
PAULO_BETA = 0.05                 # alpha_P = 0.1, beta = alpha_P / 2 (METHODS-spinnet §5)
PAULO_N_MINUS = 8                 # M3-P1 locked measurement: one -1 per bright pair (gauge_minus_codes = {8..15})


# ---------------------------------------------------------------------------------------------------- helpers
@functools.lru_cache(maxsize=None)
def _loop():
    L = api("su2plaq.spinnet.loop")
    L.install()
    L.install()              # idempotent
    return L


@functools.lru_cache(maxsize=None)
def _spec():
    return _loop().spec()


def _enc():
    return api("su2plaq.compress.spec:get_encoding")(ENC)


def _general_qc(alpha=NOMINAL[0], beta=NOMINAL[1], order=1):
    return api("su2plaq.circuits.spinnet:build_step")(alpha, beta, order, with_outer=True)


def _with_extra(qc: QuantumCircuit, fn) -> QuantumCircuit:
    out = qc.copy()
    fn(out)
    return out


def _perturb_first_rotation(qc: QuantumCircuit, delta: float) -> QuantumCircuit:
    """Qiskit >= 2 returns a fresh operation object on every access: rebuild the instruction (prompts/006 §12)."""
    out = qc.copy()
    for i, inst in enumerate(out.data):
        if inst.operation.name in ("rz", "p", "crz", "crx", "cp") and inst.operation.params:
            op = inst.operation.copy()
            old = float(op.params[0])
            op.params = [old + delta]
            out.data[i] = CircuitInstruction(op, inst.qubits, inst.clbits)
            assert abs(float(out.data[i].operation.params[0]) - (old + delta)) <= 1e-15
            return out
    raise AssertionError("no rotation found")


def _move_first_cx_control(qc: QuantumCircuit) -> QuantumCircuit:
    out = qc.copy()
    for i, inst in enumerate(out.data):
        if inst.operation.name == "cx":
            c, t = (out.find_bit(q).index for q in inst.qubits)
            new_c = next(q for q in range(out.num_qubits) if q not in (c, t))
            out.data[i] = CircuitInstruction(inst.operation, [out.qubits[new_c], out.qubits[t]], inst.clbits)
            return out
    raise AssertionError("no cx found")


def _rational_multiple(theta: float, base: float, max_den: int = 4, tol: float = 1e-9) -> bool:
    from fractions import Fraction

    f = Fraction(theta / base).limit_denominator(max_den)
    return abs(theta - float(f) * base) <= tol


def _program(tmp: pathlib.Path, name: str, body: str) -> pathlib.Path:
    p = tmp / f"{name}.py"
    p.write_text(body)
    return p


GENERAL_WITH_ORACLE = '''"""SUMMARY: the general spin-network step circuit; reads one target element from the oracle at emission time.

"""
FAMILY = "T"
PARENT = None

from su2plaq.compress.builder import Builder


def build(spec):
    from su2plaq.compress import oracle
    import numpy as np
    v = oracle.element(spec, 0, 0)          # the worker must know the encoding for this to work
    assert abs(v) <= 1.0 + 1e-12
    from su2plaq.circuits.spinnet import build_step
    qc = build_step(spec.alpha, spec.beta, spec.order, with_outer=True)
    b = Builder(spec)
    b.alloc(qc.num_qubits - 16, "work")
    b.append_qiskit(qc, list(range(qc.num_qubits)))
    return b
'''

WRITING_PROGRAM = '''"""SUMMARY: a program that tries to write a file (must be refused by the worker sandbox).

"""
FAMILY = "T"
PARENT = None

from su2plaq.compress.builder import Builder


def build(spec):
    open("/tmp/su2plaq-m4-should-not-exist.txt", "w").write("x")
    b = Builder(spec)
    return b
'''

ANGLE_DEPENDENT_SKELETON = '''"""SUMMARY: the general circuit plus a gate whose presence depends on beta (skeleton rule violation).

"""
FAMILY = "T"
PARENT = None

from su2plaq.compress.builder import Builder


def build(spec):
    from su2plaq.circuits.spinnet import build_step
    qc = build_step(spec.alpha, spec.beta, spec.order, with_outer=True)
    b = Builder(spec)
    b.alloc(qc.num_qubits - 16, "work")
    b.append_qiskit(qc, list(range(qc.num_qubits)))
    if spec.beta > 0.5:
        b.x(16); b.x(16)
    return b
'''


# ---------------------------------------------------------------------------------------------------- 4.1 shim
def test_M4_S0_spec_oracle_builder_spinnet(tmp_path):
    """After install(): the laptop's default_spec / oracle / Builder work for `spinnet` with the nominal angles, alternates
    and tolerances of prompts/001 §8; the rendered spec is the spin-network one with OUR tool commands."""
    L = _loop()
    spec = _spec()
    assert spec.encoding == ENC and spec.kind == KIND and spec.order == 1
    assert (spec.alpha, spec.beta) == NOMINAL and tuple(spec.alt_angles) == ALTS
    assert spec.tol_err == 1e-10 and spec.tol_gauss == 1e-10 and spec.eps == 1e-6 and spec.peak_qubit_cap() == 8 + 8 + 32
    enc = _enc()
    assert enc.name == ENC and enc.n_data == 8 and enc.n_outer == 8
    oracle = api("su2plaq.compress.oracle")
    V = oracle.target(spec)
    assert V.shape == (433, 433) and np.abs(V - enc.target("step", *NOMINAL, order=1)).max() <= 1e-12
    assert abs(oracle.element(spec, 3, 3) - V[3, 3]) <= 1e-12
    B = api("su2plaq.compress.builder")
    b = B.Builder(spec)
    assert b.reg("d") == list(range(8)) and b.reg("o") == list(range(8, 16)) and b.alloc(1, "w") == [16]
    text = L.render_spec()
    for needle in ("spinnet", "433", "47", "python -m su2plaq.spinnet.loop candidate", "python -m su2plaq.spinnet.loop oracle",
                   "Proved structure (Lean)", "card_inner_labels", "0.37", "0.61", "rccx", "1e-10", "DISCOVERY"):
        assert needle in text, needle
    assert "su2plaq.compress.run_candidate" not in text
    p = L.write_spec(path=tmp_path / "spinnet-step.md")
    assert pathlib.Path(p).read_text() == text


def test_M4_S2_worker_registers_encoding_and_keeps_sandbox(tmp_path):
    """The build worker subprocess knows the encoding (prompts/104 §1 shim iii): the general program builds at the three
    angle pairs with one skeleton, a program that calls the oracle inside build() is valid, and the laptop's sandbox still
    refuses file writes."""
    L = _loop()
    spec = _spec()
    E = api("su2plaq.compress.evaluate")
    assert callable(L.INSTALLED.get("build_in_subprocess")) and E._build_in_subprocess is not L.INSTALLED["build_in_subprocess"]
    gp = L.general_program_path(spec, root=tmp_path)
    specs = [spec] + [spec.with_angles(a, b) for a, b in spec.alt_angles]
    circuits, disc = E._build_in_subprocess(gp.read_bytes(), specs, E.BUILD_TIMEOUT_S)
    assert len(circuits) == 3 and len({tuple(map(tuple, E.skeleton(c))) for c in circuits}) == 1
    t0 = time.time()
    r = E.evaluate_program(str(_program(tmp_path, "001-oracle", GENERAL_WITH_ORACLE)), spec, mode="trial")
    assert r.valid and r.reason == "ok", (r.reason, r.message)
    assert time.time() - t0 <= 30
    r2 = E.evaluate_program(str(_program(tmp_path, "002-writer", WRITING_PROGRAM)), spec, mode="trial")
    assert not r2.valid and r2.reason == "build_error" and "write" in r2.message.lower(), (r2.reason, r2.message)
    assert not pathlib.Path("/tmp/su2plaq-m4-should-not-exist.txt").exists()


def test_M4_S7_shim_leaves_twelve_untouched():
    """With the shim installed the laptop's own encoding still goes through the same functions (dispatch, not replacement):
    the twelve general program is valid in trial mode."""
    L = _loop()
    S = api("su2plaq.compress.spec")
    E = api("su2plaq.compress.evaluate")
    BL = api("su2plaq.compress.baselines")
    tw = S.default_spec("twelve", "step")
    assert S.get_encoding("twelve").name == "twelve" and (tw.alpha, tw.beta) == NOMINAL
    t0 = time.time()
    r = E.evaluate_program(str(BL.general_program_path(tw)), tw, mode="trial")
    assert r.valid and r.reason == "ok", (r.reason, r.message)
    assert time.time() - t0 <= 30
    assert set(L.INSTALLED) >= {"encoding", "build_in_subprocess", "certify"}


# ---------------------------------------------------------------------------------------------------- 4.2 seeds
def test_M4_S1_general_program_valid_angle_linear(tmp_path):
    """compress/programs/spinnet/seed/000-general.py: angle-linear image of build_step (p(-3a/4) x4, rz multiples of b/2),
    valid in full mode with the same key as the circuit it came from."""
    L = _loop()
    spec = _spec()
    E = api("su2plaq.compress.evaluate"); M = api("su2plaq.compress.metrics")
    gp = L.general_program_path(spec, root=tmp_path)
    assert gp.name == "000-general.py" and gp.read_text().lstrip().startswith('"""SUMMARY:')
    r = E.evaluate_program(str(gp), spec, mode="full")
    assert r.valid and r.reason == "ok" and r.skeleton_equal and len(r.verdicts_alt) == 2 and all(v.ok for v in r.verdicts_alt)
    assert r.verdict.op_norm_error <= 1e-10 and r.verdict.gauss_residual <= 1e-10 and r.verdict.certified
    ref = M.metrics(_general_qc(), spec, measured=True)
    assert tuple(M.key(r.metrics)) == tuple(M.key(ref)) and r.metrics["n_rot"] == 8
    mod = E.load_program(str(gp))
    qc = mod.build(spec).circuit()
    for inst in qc.data:
        if inst.operation.params:
            th = float(inst.operation.params[0])
            assert _rational_multiple(th, spec.alpha) or _rational_multiple(th, spec.beta), (inst.operation.name, th)


def test_M4_S5_evaluator_rejections_on_spinnet(tmp_path):
    """The laptop evaluator's rules act on our encoding: wrong gate, dirty ancilla, angle error 1e-6, outer write, control
    change are invalid; a beta-dependent skeleton is rejected in full mode with reason 'skeleton'."""
    L = _loop()
    spec = _spec()
    E = api("su2plaq.compress.evaluate")
    qc = _general_qc()
    assert E.evaluate_circuit(qc, spec, mode="trial").valid
    last = qc.num_qubits - 1
    cases = {
        "wrong_gate": _with_extra(qc, lambda c: c.x(0)),
        "dirty_ancilla": _with_extra(qc, lambda c: c.x(last)),
        "angle_error": _perturb_first_rotation(qc, 1e-6),
        "outer_write": _with_extra(qc, lambda c: c.x(8)),
        "control_change": _move_first_cx_control(qc),
    }
    for name, bad in cases.items():
        r = E.evaluate_circuit(bad, spec, mode="trial")
        assert not r.valid and r.reason != "ok", name
    r = E.evaluate_program(str(_program(tmp_path, "003-skel", ANGLE_DEPENDENT_SKELETON)), spec, mode="full")
    assert not r.valid and r.reason == "skeleton", (r.reason, r.message)


def test_M4_S6_external_seeds_paulo15_and_spinnet_v2(tmp_path):
    """Round-0 external seeds: Paulo's 15-qubit file (fixed angle beta = 0.05, kind UB, never a parent) is valid against the
    gauge-fixed target (M3-P1) and rejected against the raw one; the vendored spinnet_v2 skeletons behind our U_E are
    parent-able step seeds whose generated programs evaluate valid; 12-qubit sources give a reason string."""
    L = _loop()
    spec = _spec()
    E = api("su2plaq.compress.evaluate")
    seed = L.import_seed(spec, "paulo15")
    assert isinstance(seed, L.SeedCircuit) and seed.fixed_angle and not seed.can_be_parent and seed.kind == "UB"
    assert abs(seed.beta - PAULO_BETA) <= 1e-15 and seed.gauge is not None and len(seed.gauge) == 433
    assert set(np.sign(np.asarray(seed.gauge)).tolist()) <= {-1.0, 1.0} and int((np.asarray(seed.gauge) < 0).sum()) == PAULO_N_MINUS
    r = L.evaluate_seed(spec, seed, mode="trial")
    assert r.valid and r.reason == "ok" and r.verdict.op_norm_error <= 1e-10 and r.verdict.gauss_residual <= 1e-10, (r.reason, r.message)
    raw = spec.with_angles(spec.alpha, PAULO_BETA)
    raw = type(spec)(**{**raw.to_dict(), "kind": "UB", "alt_angles": ()})
    r_raw = E.evaluate_circuit(seed.qc, raw, mode="trial")
    assert not r_raw.valid and r_raw.verdict is not None and r_raw.verdict.op_norm_error > 0.1
    for skel in ("pairs9", "flags4"):
        s = L.import_seed(spec, f"spinnet_v2:{skel}")
        assert isinstance(s, L.SeedCircuit) and not s.fixed_angle and s.can_be_parent and s.kind == KIND
        assert (s.alpha, s.beta) == NOMINAL
        rs = L.evaluate_seed(spec, s, mode="trial")
        assert rs.valid and rs.reason == "ok", (skel, rs.reason, rs.message)
        src = L.seed_program_source(spec, f"spinnet_v2:{skel}")
        assert src.lstrip().startswith('"""SUMMARY:')
        rp = E.evaluate_program(str(_program(tmp_path, f"00{1 if skel == 'pairs9' else 2}-{skel}", src)), spec, mode="trial")
        assert rp.valid and rp.reason == "ok", (skel, rp.reason, rp.message)
    for src_name in ("paulo34", "lean22_v2"):
        assert isinstance(L.import_seed(spec, src_name), str)
    with pytest.raises(ValueError):
        L.import_seed(spec, "no-such-seed")


# ---------------------------------------------------------------------------------------------------- 4.3 rounds
def test_M4_S3_seed_round_dry_run(tmp_path):
    """Round 0 under a temporary root (Lean off): the seven seeds are evaluated in full mode and archived, the best key is
    the minimum, Paulo's file is an external row at its own beta with the recorded gauge, and the laptop's report reads
    the round JSON."""
    L = _loop()
    t0 = time.time()
    info = L.seed_round(root=tmp_path, lean=False, dry_run=True)
    assert time.time() - t0 <= 600
    assert info["round"] == 0 and info["n_valid"] == 7 and info["n_invalid"] == 0
    rj = tmp_path / "results" / "compress" / ENC / "round-000.json"
    d = json.loads(rj.read_text())
    labels = {c["label"] for c in d["candidates"]}
    assert labels == SEED_LABELS, labels
    assert all(c["valid"] and c["key"] for c in d["candidates"])
    keys = [tuple(c["key"]) for c in d["candidates"]]
    assert tuple(info["best_key"]) == min(keys)
    assert "git_commit" in d["provenance"] and len(d["evaluator_sha256"]) == 64
    assert d["spinnet"]["code_sha256"] == L.code_hash() and len(d["spinnet"]["code_sha256"]) == 64
    ext = {x["source"]: x for x in d["external"]}
    assert "paulo15" in ext and "qiskit_l3_whole" in ext
    p = ext["paulo15"]
    assert p["valid"] is True and p["fixed_angle"] is True and p["kind"] == "UB" and abs(p["beta"] - PAULO_BETA) <= 1e-15
    assert p["op_norm_error"] <= 1e-10 and p["n_minus"] == PAULO_N_MINUS and p["certified"] is True
    A = api("su2plaq.compress.archive")
    arch = A.Archive.load(ENC, root=tmp_path)
    best = arch.best()
    assert best is not None and best.valid and tuple(best.key) == min(keys) and best.round == 0
    assert len([e for e in arch.entries() if e.valid]) == 7
    assert (tmp_path / "compress" / "attempts" / f"{ENC}.jsonl").exists()
    for n in ("000-general.py", "001-spinnet_v2_pairs9.py", "002-spinnet_v2_flags4.py", "003-spinnet_v2_flags5.py",
              "004-spinnet_v2_flags6.py", "010-general_polish.py", "011-qiskit_l3.py"):
        assert (tmp_path / "compress" / "programs" / ENC / "seed" / n).exists(), n
    text = L.report_table(root=tmp_path)
    for col in ("qubits", "CX", "T_fixed", "N_rot", "T(1e-6)", "depth", "verdict", "Lean"):
        assert col in text
    for row in ("general", "spinnet_v2_pairs9", "paulo15"):
        assert row in text
    assert (tmp_path / "results" / "compress" / ENC / "summary.json").exists()


def test_M4_S4_round_one_dry_run_and_brief(tmp_path):
    """After round 0: a family brief names OUR commands and the spin-network Lean facts; a dry round 1 with the general
    program as the only proposal evaluates and archives it through the laptop's run_round."""
    L = _loop()
    spec = _spec()
    L.seed_round(root=tmp_path, lean=False, dry_run=True)
    brief = pathlib.Path(L.make_brief(1, "F1", root=tmp_path))
    assert brief.exists()
    bt = brief.read_text()
    assert "Rewrite the parent" in bt and "python -m su2plaq.spinnet.loop candidate" in bt
    assert "su2plaq.compress.run_candidate" not in bt
    st = (tmp_path / "compress" / "specs" / f"{ENC}-{KIND}.md").read_text()
    assert "card_inner_labels" in st and "47" in st and "su2plaq.compress.run_candidate" not in st
    ib = pathlib.Path(L.make_ideation_brief(root=tmp_path))
    assert ib.exists() and "compress/ideation/spinnet.md" in ib.read_text()
    gp = L.general_program_path(spec, root=tmp_path)
    info = L.run_round(1, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(gp)], lean=False)
    assert info["round"] == 1 and info["n_valid"] >= 1
    d = json.loads((tmp_path / "results" / "compress" / ENC / "round-001.json").read_text())
    assert d["round"] == 1 and len(d["candidates"]) >= 1 and d["spinnet"]["code_sha256"] == L.code_hash()
    lines = [json.loads(x) for x in (tmp_path / "compress" / "attempts" / f"{ENC}.jsonl").read_text().splitlines() if x.strip()]
    assert any(a["round"] == 1 for a in lines)


# ---------------------------------------------------------------------------------------------------- gate (4.7, 4.8)
@pytest.mark.slow
def test_M4_G1_archive_best_reverified_from_source(root):
    """Real archive: the global best re-evaluates from its program source (cache off, full mode) as valid with the same
    key; it is not worse than the best round-0 seed; provenance hashes match the current code."""
    L = _loop()
    spec = _spec()
    A = api("su2plaq.compress.archive"); E = api("su2plaq.compress.evaluate"); M = api("su2plaq.compress.metrics")
    arch = A.Archive.load(ENC, root=root)
    best = arch.best()
    assert best is not None and best.valid
    t0 = time.time()
    r = E.evaluate_program(str(root / best.program_path), spec, mode="full")
    assert time.time() - t0 <= 300
    assert r.valid and r.skeleton_equal and r.verdict.op_norm_error <= 1e-10 and r.verdict.gauss_residual <= 1e-10
    assert tuple(M.key(r.metrics)) == tuple(best.key)
    seeds = [e for e in arch.entries() if e.round == 0 and e.valid]
    assert seeds and tuple(best.key) <= min(tuple(e.key) for e in seeds)
    assert best.evaluator_sha256 == api("su2plaq.compress.provenance:code_hash")()
    rounds = sorted((root / "results" / "compress" / ENC).glob("round-*.json"))
    assert rounds
    last = json.loads(rounds[-1].read_text())
    assert last["spinnet"]["code_sha256"] == L.code_hash()


@pytest.mark.slow
def test_M4_G2_archive_best_second_engine_aer(root):
    """Second engine: Qiskit-Aer statevector on every one of the 433 physical states (nominal angles) agrees with the exact
    target up to one global phase; ancillas return to |0>; the outer pattern of each state is unchanged.  Circuits above 26
    qubits fail here with their size (a planner decision, not a skip)."""
    L = _loop()
    spec = _spec()
    A = api("su2plaq.compress.archive"); E = api("su2plaq.compress.evaluate")
    best = A.Archive.load(ENC, root=root).best()
    assert best is not None
    circuits, _ = E._build_in_subprocess((root / best.program_path).read_bytes(), [spec], E.BUILD_TIMEOUT_S)
    qc = circuits[0]
    assert qc.num_qubits <= 26, f"best circuit has {qc.num_qubits} qubits: Aer on all 433 states exceeds the 26-qubit limit"
    enc = _enc()
    V = api("su2plaq.compress.oracle:target")(spec)
    vecs = enc.physical_vectors()
    codes = np.asarray([int(c[0]) for c in vecs.codes])          # basis encoding: one 16-bit code per physical state
    assert codes.shape == (433,) and all(len(c) == 1 for c in vecs.codes)
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    sim = AerSimulator(method="statevector")
    n = qc.num_qubits
    body = transpile(qc, sim, optimization_level=0)
    index = {int(c): k for k, c in enumerate(codes)}
    outs = np.zeros((433, 433), dtype=complex)
    worst_anc, worst_outer = 0.0, 0.0
    for k, c in enumerate(codes):
        prep = QuantumCircuit(n)
        for q in range(16):
            if (int(c) >> q) & 1:
                prep.x(q)
        full = prep.compose(body)
        full.save_statevector()
        psi = np.asarray(sim.run(full, shots=1).result().get_statevector(full))
        amp = np.zeros(433, dtype=complex)
        anc_w, outer_w = 0.0, 0.0
        o_in = int(c) >> 8
        for idx in np.nonzero(np.abs(psi) > 1e-13)[0]:
            if idx >> 16:
                anc_w += abs(psi[idx]) ** 2
                continue
            if (int(idx) >> 8) != o_in:
                outer_w += abs(psi[idx]) ** 2
            j = index.get(int(idx))
            if j is not None:
                amp[j] = psi[idx]
        outs[:, k] = amp
        worst_anc, worst_outer = max(worst_anc, anc_w), max(worst_outer, outer_w)
    ov = np.trace(V.conj().T @ outs)
    ph = ov / abs(ov)
    assert np.linalg.norm(outs - ph * V, 2) <= 1e-10
    assert worst_anc <= 1e-20 and worst_outer <= 1e-20


@pytest.mark.slow
def test_M4_G3_loop_budget_and_lineage(root):
    """The loop stayed inside prompts/001 §4: at most 8 rounds, at most 20 proposer (round, family) sessions, every
    archived proposer entry has a family and a parent that is None or an archived id; synthesis re-verification ok in
    every round that ran it; the summary lineage covers every valid entry."""
    L = _loop()
    A = api("su2plaq.compress.archive")
    arch = A.Archive.load(ENC, root=root)
    ids = {e.id for e in arch.entries()}
    att = [json.loads(x) for x in (root / "compress" / "attempts" / f"{ENC}.jsonl").read_text().splitlines() if x.strip()]
    assert att and max(a["round"] for a in att) <= 8
    sessions = {(a["round"], a["family"]) for a in att if a["round"] >= 1}
    assert len(sessions) <= 20
    for e in arch.entries():
        if e.round >= 1:
            assert e.family != "seed" and (e.parent is None or e.parent in ids), (e.id, e.parent)
    rounds = [json.loads(f.read_text()) for f in sorted((root / "results" / "compress" / ENC).glob("round-*.json"))]
    assert rounds and rounds[0]["round"] == 0 and len(rounds) <= 9
    for r in rounds:
        sv = r.get("synthesis_verification")
        if sv and sv.get("n_rot") is not None:
            assert sv["ok"] is True, (r["round"], sv)
    L.report_table(root=root)
    summary = json.loads((root / "results" / "compress" / ENC / "summary.json").read_text())
    lineage_ids = {x["id"] for x in summary["lineage"]}
    assert {e.id for e in arch.entries() if e.valid} <= lineage_ids
    assert summary["global_best"] == arch.best().id


@pytest.mark.slow
def test_M4_R1_results_and_before_after(root):
    """results/spinnet/m4-compressed.json (clean commit): the archive best re-verified, T(eps) tables with certified
    synthesised verdicts, the before/after rows with a Lean column, the lineage and the outer electric row; the markdown
    table names the global best."""
    L = _loop()
    A = api("su2plaq.compress.archive")
    best = A.Archive.load(ENC, root=root).best()
    f = root / "results" / ENC / "m4-compressed.json"
    assert f.exists(), "run scripts/m4_results.py on a clean commit"
    d = json.loads(f.read_text())
    assert d["encoding"] == ENC and d["provenance"]["git_dirty"] is False and d["circuit_id"] == best.id
    v = d["verification"]
    assert v["ok"] and v["op_norm_error"] <= 1e-10 and v["gauss_residual"] <= 1e-10 and v["certified"]
    assert d["metrics"]["logical"]["cx"] == best.key[0]
    eps_seen = []
    for row in d["metrics"]["t_table"]:
        eps = float(row["eps"])
        eps_seen.append(eps)
        n_rot = row["n_rot"]
        tol = n_rot * eps + 1e-9
        sv = row["synth"]["verdict"]
        assert sv["ok"] and sv["certified"] and sv["op_norm_error"] <= tol and sv["gauss_residual"] <= tol, eps
        assert row["t_total"] == row["t_fixed"] + row["t_rot_pygridsynth"]
    assert sorted(eps_seen) == sorted([1e-4, 1e-6, 1e-8, 1e-10])
    ex = d["extra"]
    rows = {r["row"]: r for r in ex["before_after"]}
    for name in ("general", "general+polish", "qiskit_l3", "spinnet_v2_pairs9", "paulo15", "global_best"):
        assert name in rows, name
        assert rows[name]["lean"] in ("certified", "n_a", "failed", "not_run"), name
    assert rows["global_best"]["entry"] == best.id and rows["global_best"]["cx"] == best.key[0]
    assert ex["lineage"] and "outer_electric_row" in ex
    md = root / "results" / ENC / "m4-before-after.md"
    assert md.exists() and best.id in md.read_text()
