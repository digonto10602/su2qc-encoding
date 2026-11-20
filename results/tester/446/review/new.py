"""M8-G1..G4, L5, R1 — gate tests of the LSH compression milestone on the REAL archive (prompts/401 §3 steps 8.9-8.11, §5).

G1: the archive best (archive key) and the headline (robust key, prompts/008 §6) re-evaluate from their program sources as valid
    with their keys; both are not worse than the round-0 seeds; every entry and round file carries the current hashes.
G2: second engine.  Qiskit-Aer statevector on the data + ancilla qubits of the circuit, on every one of the 47 inner codes,
    against the 47 x 47 inner target.  This covers all 433 states because (i) the circuit must not touch the outer register
    (asserted here), and (ii) the LSH step is block-diagonal in the outer-site pattern with every block the restriction of the
    inner operator (locked M7-K2 / M7-C2).  A full 24-qubit register plus ancillas would need 2^25..2^31 amplitudes per
    state; the reduced circuit needs 2^(12 + ancillas).  A circuit with more than 14 ancillas fails here with a message
    (a planner decision, not a skip).
    Erratum prompts/402 (approved 2026-11-20): a circuit that READS outer qubits (every gate on an outer qubit is diagonal
    in that qubit: a control; checked gate by gate, a gate that writes an outer qubit fails) is checked on data + ancilla +
    the read outer qubits (the untouched outer qubits are idle, the gate list is unchanged): every distinct
    (data code, read bits) input among the 433 physical codes is run, and all 433 columns are compared with the
    433 x 433 target `enc.target` (the shared evaluator's target) at the three spec angle pairs.  Same 26-qubit limit.
    In addition Aer runs the circuit on the full register (24 qubits; a circuit that reads outer qubits and has ancillas
    fails here with a message: 4 copies of the state, 1.0 GB at 24 qubits) on 10 seeded physical states (seed 20261120)
    that each have weight in every sector of the read bits, at the same three pairs.
G3: the loop stayed inside its budgets and ended by its stop rule; lineage and summary are complete.
G4: best and headline are exact at two seeded angle pairs that no evaluation used (audit 301 A2, prompts/008 M2C-G4).
L5: Lean status of best and headline; the theorem file lean/certs/lsh-best-step.lean is the headline's: the binding fields sit
    inside the proved literal and its gates equal a fresh export of the rebuilt headline program at two angle pairs
    (audit 302 N3); it elaborates with the standard axioms plus exactly one native axiom.
R1: results/lsh/m8-compressed.json (clean commit) and the before/after table.

Tolerances: `total_error` <= 1e-10, Gauss <= 1e-10 (exact-angle rule); Aer: operator norm after one global phase <= 1e-10,
weights <= 1e-20 (as M4-G2; M7 Aer runs gave <= 3.7e-15; prompts/402: the same two numbers on the outer-reading path, plus the
weight on changed read bits <= 1e-20, same definition as the other weights, and on the full register the change of the
probability of every outer pattern <= 1e-10, the first-order image 2 * 1e-10 of the amplitude tolerance); synthesised rows N_rot * eps + 1e-9 (prompts/003-004); 300 s per
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
G2_PAIRS = (NOMINAL, (0.91, 0.23), (1.70, 1.00))   # prompts/402: the three spec angle pairs (outer-reading path of G2)
G2_SEED, G2_STATES = 20261120, 10                   # prompts/402: seeded physical states of the full-register Aer run
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


def outer_reads(qc: QuantumCircuit, enc) -> dict:
    """Static scan (prompts/402 section 3.1): {outer qubit: number of gates that read it}.  A gate may touch an outer qubit
    only as a control in the general sense: its matrix is |0><0| (x) A + |1><1| (x) B on that qubit, i.e. no entry couples
    the two values of the bit (exact zeros of the gate's own matrix; qubit p of the gate is bit p of the matrix index).
    AssertionError for every other gate on an outer qubit: it writes the outer register."""
    from qiskit.quantum_info import Operator

    outer = set(enc.layout_of(qc).outer)
    reads: dict = {}
    for inst in qc.data:
        qs = [qc.find_bit(q).index for q in inst.qubits]
        hit = [p for p, q in enumerate(qs) if q in outer]
        if not hit:
            continue
        U = np.asarray(Operator(inst.operation).data)
        bits = np.arange(U.shape[0])
        for p in hit:
            b = (bits >> p) & 1
            assert not np.any(U[b[:, None] != b[None, :]]), f"gate {inst.operation.name} on qubits {qs} writes the outer qubit {qs[p]}: invalid circuit (prompts/402)"
            reads[qs[p]] = reads.get(qs[p], 0) + 1
    return reads


def aer_outer_read_check(qc: QuantumCircuit, enc, alpha: float, beta: float, reads) -> dict:
    """Second engine for a circuit that reads the outer qubits `reads` (prompts/402 section 3.2).  No gate acts on the other
    outer qubits, so the circuit is the identity on them and Aer runs the unchanged gate list on data + ancilla + read outer
    qubits.  Every distinct (data code, read bits) input among the 433 physical codes is run once (ancillas in |0>); the
    output of the physical code (d, o) is the run of (d, o restricted to the read qubits) with the outer pattern o kept.
    All 433 columns are compared with enc.target (433 x 433, physical-basis order) after one global phase.
    Returns {"n_qubits", "n_runs", "error", "ancilla_weight", "leak_weight", "outer_weight"}; the weights sum |amplitude|^2
    over the amplitudes above 1e-13 (as in aer_inner_check): ancilla not |0>; read outer bits changed; a code that is not
    one of the 433 physical codes (worst case over the runs, for the leak over the 433 columns)."""
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    layout = enc.layout_of(qc)
    R = sorted(reads)
    assert len(layout.data) == 12 and len(layout.outer) == 12 and set(R) <= set(layout.outer)
    na = len(layout.ancilla)
    n = 12 + na + len(R)
    assert n <= 26, f"the circuit has {na} ancillas and reads {len(R)} outer qubits: Aer on 2^{n} amplitudes exceeds the 26-qubit limit (planner decision)"
    pos = {q: i for i, q in enumerate(layout.data)}
    pos.update({q: 12 + k for k, q in enumerate(layout.ancilla)})
    pos.update({q: 12 + na + k for k, q in enumerate(R)})
    red = QuantumCircuit(n, global_phase=qc.global_phase)
    for inst in qc.data:
        qs = [qc.find_bit(q).index for q in inst.qubits]
        assert all(q in pos for q in qs), f"gate {inst.operation.name} on qubits {qs} touches an outer qubit outside the read set {R}"
        red.append(inst.operation, [pos[q] for q in qs])
    sim = AerSimulator(method="statevector")
    body = transpile(red, sim, optimization_level=0)
    basis = enc.physical_vectors()
    assert all(len(c) == 1 and a[0] == 1 for c, a in zip(basis.codes, basis.amps))
    codes = [int(c[0]) for c in basis.codes]
    index = {c: k for k, c in enumerate(codes)}
    V = np.asarray(enc.target("step", alpha, beta, 1))
    assert len(index) == 433 and V.shape == (433, 433)
    rbit = [12 + layout.outer.index(q) for q in R]          # outer qubit layout.outer[j] holds bit 12 + j of the code
    runs: dict = {}
    for k, c in enumerate(codes):
        runs.setdefault((c & 0xFFF, sum(((c >> j) & 1) << i for i, j in enumerate(rbit))), []).append(k)
    outs = np.zeros((433, 433), dtype=complex)
    worst_anc = worst_leak = worst_outer = 0.0
    for (d, r), cols in runs.items():
        prep = QuantumCircuit(n)
        for q in range(12):
            if (d >> q) & 1:
                prep.x(q)
        for i in range(len(R)):
            if (r >> i) & 1:
                prep.x(12 + na + i)
        full = prep.compose(body)
        full.save_statevector()
        psi = np.asarray(sim.run(full, shots=1).result().get_statevector(full))
        nz = np.nonzero(np.abs(psi) > 1e-13)[0]
        amp = psi[nz]
        w = np.abs(amp) ** 2
        anc_set = ((nz >> 12) & ((1 << na) - 1)) != 0
        moved = ~anc_set & ((nz >> (12 + na)) != r)
        keep = ~anc_set & ~moved
        worst_anc, worst_outer = max(worst_anc, float(w[anc_set].sum())), max(worst_outer, float(w[moved].sum()))
        d_out = (nz[keep] & 0xFFF).tolist()
        a_out = amp[keep]
        for k in cols:
            o = (codes[k] >> 12) << 12
            leak_w = 0.0
            for dp, a in zip(d_out, a_out):
                j = index.get(dp | o)
                if j is None:
                    leak_w += abs(a) ** 2
                else:
                    outs[j, k] = a
            worst_leak = max(worst_leak, leak_w)
    ov = np.trace(V.conj().T @ outs)
    ph = ov / abs(ov) if abs(ov) > 1e-300 else 1.0
    return {"n_qubits": n, "n_runs": len(runs), "error": float(np.linalg.norm(outs - ph * V, 2)),
            "ancilla_weight": worst_anc, "leak_weight": worst_leak, "outer_weight": worst_outer}


def g2_states(qc: QuantumCircuit, enc, reads) -> np.ndarray:
    """G2_STATES seeded random physical states (rows: complex amplitudes over the 433 physical codes, unit norm, seed
    G2_SEED).  Every state has weight in every sector, i.e. for every value of the read outer bits that occurs among the
    physical codes (asserted)."""
    layout = enc.layout_of(qc)
    codes = np.array([int(c[0]) for c in enc.physical_vectors().codes])
    rng = np.random.default_rng(G2_SEED)
    c = rng.normal(size=(G2_STATES, len(codes))) + 1j * rng.normal(size=(G2_STATES, len(codes)))
    c /= np.linalg.norm(c, axis=1, keepdims=True)
    sector = sum(((codes >> (12 + layout.outer.index(q))) & 1) << i for i, q in enumerate(sorted(reads)))
    for s_ in np.unique(sector):
        assert (np.abs(c[:, sector == s_]) ** 2).sum(axis=1).min() > 0, f"a state has no weight in sector {int(s_)}"
    return c


def aer_full_register_check(qc: QuantumCircuit, enc, alpha: float, beta: float, states: np.ndarray) -> dict:
    """Aer statevector on the FULL register (12 data + 12 outer qubits + ancillas in |0>, unchanged gate list) for the given
    physical states (prompts/402 section 3.3) against enc.target, one global phase for all states.
    Returns {"n_qubits", "n_states", "error" (largest 2-norm of output - phase * target state), "ancilla_weight",
    "leak_weight" (amplitudes above 1e-13: ancilla not |0>; ancilla |0> and not a physical code),
    "outer_weight_change" (largest change of the probability of any of the 4096 outer patterns, no threshold)}."""
    import gc

    from qiskit import transpile
    from qiskit_aer import AerSimulator

    layout = enc.layout_of(qc)
    assert len(layout.data) == 12 and len(layout.outer) == 12
    na = len(layout.ancilla)
    n = 24 + na
    assert n <= 24, f"the circuit reads outer qubits and has {na} ancillas: the full-register Aer run on 2^{n} amplitudes exceeds the 24-qubit limit (planner decision)"
    pos = {q: i for i, q in enumerate(layout.data)}
    pos.update({q: 12 + j for j, q in enumerate(layout.outer)})
    pos.update({q: 24 + k for k, q in enumerate(layout.ancilla)})
    red = QuantumCircuit(n, global_phase=qc.global_phase)
    for inst in qc.data:
        red.append(inst.operation, [pos[qc.find_bit(q).index] for q in inst.qubits])
    sim = AerSimulator(method="statevector")
    body = transpile(red, sim, optimization_level=0)
    codes = np.array([int(c[0]) for c in enc.physical_vectors().codes])
    V = np.asarray(enc.target("step", alpha, beta, 1))
    assert V.shape == (433, 433) and states.shape[1] == 433
    got, exp = [], []
    worst_anc = worst_leak = worst_outer = 0.0
    for c in states:
        psi = np.zeros(1 << n, dtype=complex)
        psi[codes] = c
        full = QuantumCircuit(n)
        full.set_statevector(psi)
        del psi
        full.compose(body, inplace=True)
        full.save_statevector()
        psi = np.asarray(sim.run(full, shots=1).result().get_statevector(full))
        del full
        got.append(psi[codes].copy())
        exp.append(V @ c)
        w_out = np.zeros(4096)
        for blk in psi.reshape(1 << na, 4096, 4096):                 # [ancilla, outer pattern, data code]
            for lo in range(0, 4096, 256):
                part = blk[lo:lo + 256]
                w_out[lo:lo + 256] += (part.real ** 2 + part.imag ** 2).sum(axis=1)
        w_in = np.bincount(codes >> 12, weights=np.abs(c) ** 2, minlength=4096)
        worst_outer = max(worst_outer, float(np.abs(w_out - w_in).max()))
        nz = np.nonzero(np.abs(psi) > 1e-13)[0]
        w = np.abs(psi[nz]) ** 2
        anc_set = (nz >> 24) != 0
        stray = ~anc_set & ~np.isin(nz, codes)
        worst_anc, worst_leak = max(worst_anc, float(w[anc_set].sum())), max(worst_leak, float(w[stray].sum()))
        del psi
        gc.collect()                                                 # the circuit that holds the input state is in a reference cycle
    G, X = np.array(got), np.array(exp)
    ov = np.vdot(X, G)
    ph = ov / abs(ov) if abs(ov) > 1e-300 else 1.0
    return {"n_qubits": n, "n_states": len(states), "error": float(np.linalg.norm(G - ph * X, axis=1).max()),
            "ancilla_weight": worst_anc, "leak_weight": worst_leak, "outer_weight_change": worst_outer}


def g2_second_engine(rebuild, spec, enc, tag) -> list:
    """The G2 check of one archive entry; `rebuild(specs)` returns its circuits from the program source (stock worker).
    No outer qubit touched: the check of prompts/401, unchanged (47 inner codes, nominal angles).  Outer qubits read
    (prompts/402), at each of the three spec angle pairs: static scan with the same read set; all 433 physical codes on the
    reduced register; G2_STATES seeded physical states on the full register."""
    qc = rebuild([spec])[0]
    reads = outer_reads(qc, enc)
    if not reads:
        res = aer_inner_check(qc, enc, *NOMINAL)
        assert res["error"] <= TOL, (tag, res)
        assert res["ancilla_weight"] <= 1e-20 and res["leak_weight"] <= 1e-20, (tag, res)
        return [res]
    assert (spec.alpha, spec.beta) == G2_PAIRS[0]
    states = g2_states(qc, enc, reads)
    out = []
    for (a, b), qc in zip(G2_PAIRS, rebuild([spec] + [spec.with_angles(a, b) for a, b in G2_PAIRS[1:]])):
        assert set(outer_reads(qc, enc)) == set(reads), (tag, a, b)
        res = aer_outer_read_check(qc, enc, a, b, reads)
        assert res["error"] <= TOL, (tag, a, b, res)
        assert res["ancilla_weight"] <= 1e-20 and res["leak_weight"] <= 1e-20 and res["outer_weight"] <= 1e-20, (tag, a, b, res)
        full = aer_full_register_check(qc, enc, a, b, states)
        assert full["error"] <= TOL, (tag, a, b, full)
        assert full["ancilla_weight"] <= 1e-20 and full["leak_weight"] <= 1e-20 and full["outer_weight_change"] <= TOL, (tag, a, b, full)
        out.append({**res, "full": full})
    return out


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
    """Aer statevector (second engine) for the archive best and the headline rebuilt through the stock worker.  A circuit
    that touches no outer qubit: the 47 inner codes, data + ancilla qubits only, at the nominal angles: equal to the inner
    target up to one global phase, ancillas back in |0>, no weight outside the inner codes.  A circuit that reads outer
    qubits as controls (prompts/402): all 433 physical codes on data + ancilla + read outer qubits at the three spec angle
    pairs: equal to the 433 x 433 target up to one global phase, ancillas back in |0>, no weight outside the physical
    codes, read bits unchanged; and 10 seeded physical states on the full register at the same pairs: equal to the target
    states up to one global phase, probability of every outer pattern unchanged.  A gate that writes an outer qubit fails
    in both cases."""
    spec = _spec()
    enc = api("su2plaq.compress.spec:get_encoding")(ENC)
    arch, best, head, h = _best_and_head(root)
    for e in {best.id: best, head.id: head}.values():
        g2_second_engine(lambda specs, e=e: _rebuild(root, e, specs), spec, enc, e.id)


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
