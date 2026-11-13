"""M8-G1..G4, L5, R1 — gate tests of the LSH compression milestone on the REAL archive (prompts/401 §3 steps 8.9-8.11, §5).

G1: the archive best (archive key) and the headline (robust key, prompts/008 §6) re-evaluate from their program sources as valid
    with their keys; both are not worse than the round-0 seeds; every entry and round file carries the current hashes.
G2: second engine.  Qiskit-Aer statevector on the data + ancilla qubits of the circuit, on every one of the 47 inner codes,
    against the 47 x 47 inner target.  This covers all 433 states because (i) the circuit must not touch the outer register
    (asserted here), and (ii) the LSH step is block-diagonal in the outer-site pattern with every block the restriction of the
    inner operator (locked M7-K2 / M7-C2).  A full 24-qubit register plus ancillas would need 2^25..2^31 amplitudes per
    state; the reduced circuit needs 2^(12 + ancillas).  A circuit that reads outer qubits, or has more than 14 ancillas,
    fails here with a message (a planner decision, not a skip).
G3: the loop stayed inside its budgets and ended by its stop rule; lineage and summary are complete.
G4: best and headline are exact at two seeded angle pairs that no evaluation used (audit 301 A2, prompts/008 M2C-G4).
L5: Lean status of best and headline; the theorem file lean/certs/lsh-best-step.lean is the headline's: the binding fields sit
    inside the proved literal and its gates equal a fresh export of the rebuilt headline program at two angle pairs
    (audit 302 N3); it elaborates with the standard axioms plus exactly one native axiom.
R1: results/lsh/m8-compressed.json (clean commit) and the before/after table.

Tolerances: `total_error` <= 1e-10, Gauss <= 1e-10 (exact-angle rule); Aer: operator norm after one global phase <= 1e-10,
weights <= 1e-20 (as M4-G2; M7 Aer runs gave <= 3.7e-15); synthesised rows N_rot * eps + 1e-9 (prompts/003-004); 300 s per
evaluation, 900 s per Lean call.  All tests are `slow` and `PENDING` until the loop has run."""
from __future__ import annotations

import json
import pathlib
import re
import time

import numpy as np
import pytest
from qiskit import QuantumCircuit

from tests.acceptance._api import api

ENC, KIND = "lsh", "step"
NOMINAL = (0.37, 0.61)
TOL = 1e-10
STANDARD = {"propext", "Classical.choice", "Quot.sound"}
ANGLE_SET_SEED, ANGLE_SET_N = 20261107, 20
ANGLE_RANGES = ((0.05, 2.0), (0.05, 1.2))
GENERALITY_SEED = 20261110                 # prompts/008 M2C-G4: two further pairs, same ranges
BINDING_PAIR = (1.3, 0.17)                 # audit 302 §2.4: a pair outside the spec for the re-export comparison
ROUND0_BEST_CX = 71                        # wrapped spin-network headline (prompts/401 §1.3)
SPINNET_HEADLINE = ("r02-F1-002", 31)      # prompts/104: the closed spin-network loop
TRANSCODER = {"cx": 40, "t_fixed": 32}     # M7-V1
BEFORE_AFTER_ROWS = ("general", "general+polish", "qiskit_l3", "wrap_pairs9", "wrap_flags4", "wrap_flags5", "wrap_flags6",
                     "wrap_sn_headline", "wrap_sn_r05F3", "wrap_sn_r02F5", "paulo15_wrapped", "global_best", "headline")
STOP_REASONS = ("no_gain", "max_rounds", "max_sessions")


# ---------------------------------------------------------------------------------------------------- helpers
def _spec():
    if api("su2plaq.encodings.registry").lookup(ENC) is None:
        pytest.fail("PENDING: encoding 'lsh' is not in the registry (prompts/401 step 8.2)", pytrace=False)
    return api("su2plaq.compress.spec:default_spec")(ENC, KIND)


def _archive(root):
    if not (root / "compress" / "archive" / ENC).exists():
        pytest.fail("PENDING: compress/archive/lsh missing (prompts/401 step 8.6: round 0)", pytrace=False)
    arch = api("su2plaq.compress.archive").Archive.load(ENC, root=root, n_alt=2, strict=True)
    assert arch.entries() and arch.rejected == []
    return arch


def _headline(root):
    return api("su2plaq.compress.robust").headline(ENC, KIND, root=root)


def _best_and_head(root):
    arch = _archive(root)
    h = _headline(root)
    by = {e.id: e for e in arch.entries()}
    return arch, arch.best(), by[h["id"]], h


def _err(v) -> float:
    if not hasattr(v, "total_error"):
        pytest.fail("PENDING: Verdict has no field total_error (prompts/008 step B2)", pytrace=False)
    return v.total_error


def _angle_set() -> np.ndarray:
    rng = np.random.default_rng(ANGLE_SET_SEED)
    a = rng.uniform(*ANGLE_RANGES[0], ANGLE_SET_N)
    b = rng.uniform(*ANGLE_RANGES[1], ANGLE_SET_N)
    return np.c_[a, b]


def _generality_pairs():
    rng = np.random.default_rng(GENERALITY_SEED)
    a = rng.uniform(*ANGLE_RANGES[0], 2)
    b = rng.uniform(*ANGLE_RANGES[1], 2)
    return [(float(x), float(y)) for x, y in zip(a, b)]


def _rebuild(root, entry, specs):
    E = api("su2plaq.compress.evaluate")
    circuits, _ = E._build_in_subprocess((root / entry.program_path).read_bytes(), list(specs), E.BUILD_TIMEOUT_S)
    return circuits


def aer_inner_check(qc: QuantumCircuit, enc, alpha: float, beta: float) -> dict:
    """Aer statevector of the circuit restricted to its data and ancilla qubits on the 47 inner codes vs enc.inner_target.
    Returns {"n_qubits", "error", "ancilla_weight", "leak_weight"}; AssertionError if the circuit touches an outer qubit."""
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    layout = enc.layout_of(qc)
    outer = set(layout.outer)
    pos = {q: i for i, q in enumerate(layout.data)}
    pos.update({q: 12 + k for k, q in enumerate(layout.ancilla)})
    n = 12 + len(layout.ancilla)
    assert len(layout.data) == 12 and len(layout.outer) == 12
    assert n <= 26, f"the circuit has {len(layout.ancilla)} ancillas: Aer on 2^{n} amplitudes exceeds the 26-qubit limit (planner decision)"
    red = QuantumCircuit(n, global_phase=qc.global_phase)
    for inst in qc.data:
        qs = [qc.find_bit(q).index for q in inst.qubits]
        assert not (set(qs) & outer), f"gate {inst.operation.name} touches the outer register: the reduced check does not apply (planner decision)"
        red.append(inst.operation, [pos[q] for q in qs])
    sim = AerSimulator(method="statevector")
    body = transpile(red, sim, optimization_level=0)
    codes = [int(c) for c in enc.inner_codes()]
    index = {c: k for k, c in enumerate(codes)}
    V = np.asarray(enc.inner_target("step", alpha, beta, 1))
    assert len(codes) == 47 and V.shape == (47, 47)
    outs = np.zeros((47, 47), dtype=complex)
    worst_anc = worst_leak = 0.0
    for k, c in enumerate(codes):
        prep = QuantumCircuit(n)
        for q in range(12):
            if (c >> q) & 1:
                prep.x(q)
        full = prep.compose(body)
        full.save_statevector()
        psi = np.asarray(sim.run(full, shots=1).result().get_statevector(full))
        anc_w = leak_w = 0.0
        for idx in np.nonzero(np.abs(psi) > 1e-13)[0]:
            idx = int(idx)
            if idx >> 12:
                anc_w += abs(psi[idx]) ** 2
            elif idx in index:
                outs[index[idx], k] = psi[idx]
            else:
                leak_w += abs(psi[idx]) ** 2
        worst_anc, worst_leak = max(worst_anc, anc_w), max(worst_leak, leak_w)
    ov = np.trace(V.conj().T @ outs)
    ph = ov / abs(ov) if abs(ov) > 1e-300 else 1.0
    return {"n_qubits": n, "error": float(np.linalg.norm(outs - ph * V, 2)), "ancilla_weight": worst_anc, "leak_weight": worst_leak}


# ---------------------------------------------------------------------------------------------------- G1
@pytest.mark.slow
def test_M8_G1_best_and_headline_reverified_from_source(root):
    """Archive best and headline: full-mode re-evaluation from the program file (cache off) is valid with the stored key; the
    best is not worse than the best seed in the archive key, the headline not worse in the robust key and at most 71 CX;
    every entry and every round file carries the current stamp and encoding hashes (a hashed LSH or shared file changed
    after the loop -> replay with `su2plaq.compress.replay`, a new tag)."""
    spec = _spec()
    E = api("su2plaq.compress.evaluate"); M = api("su2plaq.compress.metrics"); P = api("su2plaq.compress.provenance")
    arch, best, head, h = _best_and_head(root)
    assert best is not None and best.valid and head.valid
    for e in {best.id: best, head.id: head}.values():
        t0 = time.time()
        r = E.evaluate_program(str(root / e.program_path), spec, mode="full")
        assert time.time() - t0 <= 300
        assert r.valid and r.reason == "ok" and r.skeleton_equal and len(r.verdicts_alt) == 2 and all(v.ok for v in r.verdicts_alt), (e.id, r.reason, r.message)
        assert _err(r.verdict) <= TOL and r.verdict.gauss_residual <= TOL and r.verdict.certified, e.id
        assert tuple(M.key(r.metrics)) == tuple(e.key), e.id
    seeds = [e for e in arch.entries() if e.round == 0 and e.valid]
    assert seeds and tuple(best.key) <= min(tuple(e.key) for e in seeds)
    seed_ids = {e.id for e in seeds}
    seed_keys = [tuple(r["robust_key"]) for r in h["ranking"] if r["id"] in seed_ids and r["robust_key"] is not None]
    assert seed_keys and tuple(h["robust_key"]) <= min(seed_keys) and h["robust_key"][0] <= ROUND0_BEST_CX
    hs, he = P.stamp_hash(ENC), P.code_hash_for(ENC)
    assert all(e.evaluator_sha256 == hs and e.encoding_sha256 == he for e in arch.entries()), "stale hashes: replay the lsh archive"
    rounds = sorted((root / "results" / "compress" / ENC).glob("round-*.json"))
    assert rounds and all(json.loads(f.read_text())["evaluator_sha256"] == hs for f in rounds)


# ---------------------------------------------------------------------------------------------------- G2
@pytest.mark.slow
def test_M8_G2_best_and_headline_second_engine_aer(root):
    """Aer statevector (second engine) on the 47 inner codes, data + ancilla qubits only, for the archive best and the
    headline rebuilt through the stock worker at the nominal angles: equal to the inner target up to one global phase,
    ancillas back in |0>, no weight outside the inner codes, outer register untouched."""
    spec = _spec()
    enc = api("su2plaq.compress.spec:get_encoding")(ENC)
    arch, best, head, h = _best_and_head(root)
    for e in {best.id: best, head.id: head}.values():
        qc = _rebuild(root, e, [spec])[0]
        res = aer_inner_check(qc, enc, *NOMINAL)
        assert res["error"] <= TOL, (e.id, res)
        assert res["ancilla_weight"] <= 1e-20 and res["leak_weight"] <= 1e-20, (e.id, res)


# ---------------------------------------------------------------------------------------------------- G3
@pytest.mark.slow
def test_M8_G3_loop_budget_lineage_and_stop(root):
    """Budgets of prompts/001 §4: at most 8 rounds and 20 proposer sessions (ideation counts as one); every proposer entry has a
    family and a parent that is None or an archived id; synthesis re-verification ok in every round that ran it; the loop
    ended by its stop rule (prompts/401 §1.6), recomputed here from the recorded headline records; summary complete."""
    _spec()
    LL = api("su2plaq.lsh.loop")
    arch, best, head, h = _best_and_head(root)
    ids = {e.id for e in arch.entries()}
    att = [json.loads(x) for x in (root / "compress" / "attempts" / f"{ENC}.jsonl").read_text().splitlines() if x.strip()]
    assert att and max(a["round"] for a in att) <= 8
    sessions = {(a["round"], a["family"]) for a in att if a["round"] >= 1}
    assert (root / "compress" / "ideation" / f"{ENC}.md").exists()
    assert len(sessions) + 1 <= 20
    for e in arch.entries():
        if e.round >= 1:
            assert e.family != "seed" and (e.parent is None or e.parent in ids), (e.id, e.parent)
    rounds = [json.loads(f.read_text()) for f in sorted((root / "results" / "compress" / ENC).glob("round-*.json"))]
    assert rounds and [r["round"] for r in rounds] == list(range(len(rounds))) and len(rounds) <= 9
    for r in rounds:
        sv = r.get("synthesis_verification")
        if sv and sv.get("n_rot") is not None:
            assert sv["ok"] is True, (r["round"], sv)
    st = LL.stop_state(root=root)
    assert [x["round"] for x in st["rounds"]] == list(range(len(rounds)))
    assert st["sessions"] == len(sessions) + 1
    flags, prev = [], None
    for x in st["rounds"]:                                  # the improved flags are the stop-rule comparison of consecutive records
        flags.append(LL.improves(x["record"], prev))
        if flags[-1]:
            prev = x["record"]
        assert x["improved"] is flags[-1], x["round"]
    streak = 0
    for f in reversed(flags):
        if f:
            break
        streak += 1
    assert st["streak"] == streak
    assert st["stop"] is True and st["reason"] in STOP_REASONS, st
    if st["reason"] == "no_gain":
        assert streak >= LL.STOP_NO_GAIN_ROUNDS
    if st["reason"] == "max_rounds":
        assert len(rounds) - 1 == LL.STOP_MAX_ROUNDS
    if st["reason"] == "max_sessions":
        assert st["sessions"] >= LL.STOP_MAX_SESSIONS
    assert st["rounds"][-1]["headline_id"] == h["id"]
    api("su2plaq.compress.report:report_table")(ENC, KIND, root=root)
    summary = json.loads((root / "results" / "compress" / ENC / "summary.json").read_text())
    assert {e.id for e in arch.entries() if e.valid} <= {x["id"] for x in summary["lineage"]}
    assert summary["global_best"] == best.id and summary["headline"]["id"] == h["id"]


# ---------------------------------------------------------------------------------------------------- G4
@pytest.mark.slow
def test_M8_G4_best_and_headline_valid_at_unseen_angles(root):
    """Rebuilt from their program files at two seeded angle pairs that neither the spec nor the robust angle set contains,
    the archive best and the headline keep the nominal skeleton and are exact (total_error <= 1e-10, certified)."""
    spec = _spec()
    E = api("su2plaq.compress.evaluate")
    RB = api("su2plaq.compress.robust")
    arch, best, head, h = _best_and_head(root)
    pairs = _generality_pairs()
    used = {(spec.alpha, spec.beta), *map(tuple, spec.alt_angles), *map(tuple, RB.ANGLE_SET)}
    assert not used & set(pairs)
    for e in {best.id: best, head.id: head}.values():
        specs = [spec] + [spec.with_angles(a, b) for a, b in pairs]
        circuits = _rebuild(root, e, specs)
        sk0 = E.skeleton(circuits[0])
        for sp, qc in zip(specs[1:], circuits[1:]):
            assert E.skeleton(qc) == sk0, (e.id, sp.alpha, sp.beta)
            r = E.evaluate_circuit(qc, sp, mode="full")
            assert r.valid and r.reason == "ok" and r.verdict.certified, (e.id, sp.alpha, sp.beta, r.reason, r.message)
            assert _err(r.verdict) <= TOL, (e.id, sp.alpha, sp.beta)


# ---------------------------------------------------------------------------------------------------- L5
def _literal_of(text: str) -> dict:
    m = re.search(r'^def certJson : String := "(.*)"$', text, re.M)
    assert m, "theorem file has no certJson literal"
    return json.loads(re.sub(r"\\(.)", r"\1", m.group(1)))          # undo the Lean string escapes (backslash, quote)


@pytest.mark.slow
def test_M8_L5_headline_lean_status_theorem_file_and_binding(root, tmp_path):
    """Archive best and headline carry a Lean status (`certified`, or `n_a` with an exporter reason); when the headline is
    certified, lean/certs/lsh-best-step.lean exists, names the entry and its program file in its first line AND inside the
    proved literal (clean commit), the literal's gates / target / states equal fresh exports of the rebuilt headline program
    at the nominal pair and at (1.3, 0.17) (same angle exponents: the certificate is the program's, for every angle), and
    the file elaborates within 900 s with the standard axioms plus exactly one native axiom."""
    spec = _spec()
    arch, best, head, h = _best_and_head(root)
    LE = api("su2plaq.lsh.lean_export")
    P = api("su2plaq.lean.project")
    enc = api("su2plaq.compress.spec:get_encoding")(ENC)
    for e in (best, head):
        assert isinstance(e.lean, dict) and e.lean["status"] in ("certified", "n_a"), (e.id, e.lean)
        if e.lean["status"] == "n_a":
            assert e.lean["reason"].startswith(("non_linear_angle", "phase_not_in_K")), (e.id, e.lean)
    assert h["lean"] == head.lean["status"]
    if head.lean["status"] != "certified":
        return
    f = root / "lean" / "certs" / "lsh-best-step.lean"
    assert f.exists(), "write_theorem_file for the headline circuit (prompts/401 step 8.9)"
    text = f.read_text()
    first = text.splitlines()[0]
    assert first.startswith("-- ") and head.id in first and head.program_sha256 in first
    assert "theorem lsh_best : Su2PlaqCert.LSH.checkJsonString certJson = true := by native_decide" in text
    cert = _literal_of(text)
    prov = cert["provenance"]
    assert prov["entry_id"] == head.id and prov["program_file_sha256"] == head.program_sha256 and prov["git_dirty"] is False
    assert cert["n_data"] == 12 and cert["n_outer"] == 12 and len(cert["states"]) == 433
    assert cert["target"]["kind"] == "step" and cert["target"]["order"] == 1
    stored = root / head.lean["cert_path"] if not pathlib.Path(head.lean["cert_path"]).is_absolute() else pathlib.Path(head.lean["cert_path"])
    assert stored.exists() and json.loads(stored.read_text()) == cert
    pairs = [NOMINAL, BINDING_PAIR]
    circuits = _rebuild(root, head, [spec.with_angles(a, b) for a, b in pairs])
    for (a, b), qc in zip(pairs, circuits):
        out = LE.export_certificate(qc, enc, "step", a, b, 1, tmp_path / f"fresh-{a}-{b}.json")
        assert not isinstance(out, str), out
        fresh = json.loads(pathlib.Path(out).read_text())
        for key in ("gates", "target", "states", "phase", "base", "n_qubits"):
            assert fresh[key] == cert[key], (key, a, b)
    t0 = time.time()
    p = P.lake(["env", "lean", str(f)], timeout=900)
    assert time.time() - t0 <= 900
    assert p.returncode == 0, p.stderr[-2000:] + p.stdout[-2000:]
    m = re.search(r"depends on axioms:\s*\[([^\]]*)\]", p.stdout)
    assert m, p.stdout[-2000:]
    axioms = {a.strip() for a in m.group(1).split(",") if a.strip()}
    native = [a for a in axioms if a not in STANDARD]
    assert len(native) == 1 and P.is_native_axiom(native[0]), axioms


# ---------------------------------------------------------------------------------------------------- R1
@pytest.mark.slow
def test_M8_R1_results_and_before_after(root):
    """results/lsh/m8-compressed.json (clean commit): the headline re-verified, T(eps) rows with certified synthesised
    verdicts, the before/after rows (each archived row with its angle-averaged T), the comparison with the spin-network
    headline (what the LSH register costs beyond the transcoder), the CX / T front, the uniform-split structure row, the stop
    record, the Lean block and the outer electric row; the markdown table names best and headline."""
    _spec()
    arch, best, head, h = _best_and_head(root)
    f = root / "results" / ENC / "m8-compressed.json"
    if not f.exists():
        pytest.fail("PENDING: results/lsh/m8-compressed.json missing (prompts/401 step 8.10: scripts/m8_results.py on a clean commit)", pytrace=False)
    d = json.loads(f.read_text())
    assert d["encoding"] == ENC and d["kind"] == KIND and d["provenance"]["git_dirty"] is False and d["circuit_id"] == h["id"]
    assert d["params"]["alpha"] == NOMINAL[0] and d["params"]["beta"] == NOMINAL[1]
    v = d["verification"]
    assert v["ok"] and v["total_error"] <= TOL and v["op_norm_error"] <= TOL and v["gauss_residual"] <= TOL and v["certified"]
    assert v["n_inputs"] == 433
    assert d["metrics"]["logical"]["cx"] == head.key[0] == h["robust_key"][0]
    ex = d["extra"]
    aset = ex["angle_set"]
    assert aset["seed"] == ANGLE_SET_SEED and np.array_equal(np.asarray(aset["pairs"], dtype=float), _angle_set())
    assert tuple(ex["headline"]["robust_key"]) == tuple(h["robust_key"]) and ex["archive_best"] == best.id
    eps_seen = []
    for row in d["metrics"]["t_table"]:
        eps = float(row["eps"])
        eps_seen.append(eps)
        tol = row["n_rot"] * eps + 1e-9
        sv = row["synth"]["verdict"]
        assert sv["ok"] and sv["certified"] and sv["op_norm_error"] <= tol and sv["gauss_residual"] <= tol, eps
        assert row["t_total"] == row["t_fixed"] + row["t_rot_pygridsynth"]
    assert sorted(eps_seen) == sorted([1e-4, 1e-6, 1e-8, 1e-10])
    rows = {r["row"]: r for r in ex["before_after"]}
    for name in BEFORE_AFTER_ROWS:
        assert name in rows, name
        assert rows[name]["lean"] in ("certified", "n_a", "failed", "not_run"), name
    assert rows["global_best"]["entry"] == best.id and rows["global_best"]["cx"] == best.key[0]
    assert rows["headline"]["entry"] == h["id"] and rows["headline"]["cx"] == h["robust_key"][0]
    assert abs(rows["headline"]["t_avg"] - h["t_mean"]) <= 1e-9 and round(rows["headline"]["t_avg"] * ANGLE_SET_N) == h["robust_key"][1]
    assert rows["wrap_sn_headline"]["cx"] == ROUND0_BEST_CX and rows["general"]["cx"] == 94 and rows["paulo15_wrapped"]["cx"] == 108
    archived = {e.id for e in arch.entries()}
    for name, r in rows.items():
        if r.get("entry") in archived and r.get("robust_key") is not None:
            assert r["t_avg"] > 0, name
    vs = ex["vs_spinnet"]
    assert vs["spinnet_headline"]["id"] == SPINNET_HEADLINE[0] and vs["spinnet_headline"]["cx"] == SPINNET_HEADLINE[1]
    assert vs["transcoder"] == TRANSCODER and vs["wrapped"]["cx"] == SPINNET_HEADLINE[1] + TRANSCODER["cx"] == ROUND0_BEST_CX
    assert vs["lsh_headline"]["cx"] == h["robust_key"][0]
    assert vs["native_gain_cx"] == vs["wrapped"]["cx"] - vs["lsh_headline"]["cx"] >= 0
    assert vs["overhead_cx"] == vs["lsh_headline"]["cx"] - vs["spinnet_headline"]["cx"]
    front = ex["pareto_cx_tavg"]
    assert front and [p["cx"] for p in front] == sorted(p["cx"] for p in front)
    assert all(front[i]["t_avg"] > front[i + 1]["t_avg"] for i in range(len(front) - 1))      # a front: more CX only if fewer T
    assert front[0]["id"] == h["id"] or front[0]["cx"] == h["robust_key"][0]
    us = ex["uniform_split"]
    assert (us["nnz"], us["max_per_row"], us["sites_touched"], us["qubits_touched"]) == (400, 4, 6, 18) and us["circuit"] == "not built"
    st = ex["stop"]
    assert st["stop"] is True and st["reason"] in STOP_REASONS
    assert ex["lean"]["status"] == head.lean["status"] and ex["lean"]["trust"] in ("native-certified", "n_a")
    if ex["lean"]["status"] == "certified":
        assert ex["lean"]["theorem_file"] == "lean/certs/lsh-best-step.lean" and len(ex["lean"]["cert_sha256"]) == 64
    assert ex["lineage"] and "outer_electric_row" in ex and ex["order"] == 1
    md = root / "results" / ENC / "m8-before-after.md"
    assert md.exists() and best.id in md.read_text() and h["id"] in md.read_text()
