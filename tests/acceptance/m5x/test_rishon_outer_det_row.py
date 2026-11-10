"""M5x-O2 (prompts/204 step D5) — certified det row over all 12 links (METHODS-rishon R14).

H_D = sum over all 12 links of (det U_l + det U_l^dag).  The four inner terms are the det layer U_D of the Trotter step (verified
on the 1296 inner codes, M5-DT4).  The eight outer terms commute with H_E, with H_B and with the inner det terms (different
links, even operators; det commutes with the link Casimir), so exp(-i t H) = exp(-i t lam_d H_D^outer) x (everything else)
exactly: like the outer electric row they are a separate, exactly factorised row that WRITES the outer register (an outer
link flips between its two singlet types A <-> B) and is therefore not covered by the inner-block verdict.

`build_UD(eta, with_outer=True, include_outer_det=True)` is a tensor product of 12 per-link gadgets on disjoint qubits;
`outer_det_certify` partitions the gates by link, computes each link's exact 16 x 16 operator V_l and compares its 16 x 6 block
on the sector codes with T = exp(-i eta (det U + det U^dag)) after one phase per link (the fitted phase arg tr(T^dag V); |tr(T^dag V)| = 6
for the correct gadget at every eta; any phase gives a valid bound); error_bound = sum over links of the link errors bounds the error
on every superposition of products of sector codes, hence on all 38 432 physical states (telescoping of a tensor product of
unitaries, as M5x-O1).

Tolerance 1e-10 = METHODS section 6 tol_err for exact-angle circuits; each link error is a 16-dim product of 14 exact gates
(measured 3.3e-16, planner prototype scratch/planner/proto_rishon_det_circuit_204.py), so the bound (12 terms) is ~4e-15.
The 1e-7 angle mutant changes one rz(2 eta) by 1e-7 (generator Z/2, norm 1/2): link error 5.0e-8 with the fitted phase
(measured, scratch/planner/proto_rishon_det_numbers_204.py); the lower threshold 2e-8 leaves a factor 2.5 and sits 200x above
the tolerance; the wrong-sign row measures 13.2 (threshold 1).
Cross-checks: own per-link operators from the own JW link (1e-12), sparse run_batch on seeded valid 48-bit codes (1e-10)."""
import json

import numpy as np
import pytest

from tests.acceptance._api import api
from tests.acceptance.m5 import _ref

TOL_ERR = 1e-10
ETAS = (0.29, -0.53, 1.07, float(np.pi / 4))      # pi/4: cos 2eta = 0 (full A <-> B transfer), the edge case of a phase anchor
N_LINKS = 12
N_SAMPLE_CODES = 24
SEED = 20261110
SECTOR = [3, 5, 6, 9, 10, 12]


def _own_target(eta: float) -> np.ndarray:
    lk = _ref.link()
    hd = lk.det_U + lk.det_U.conj().T
    w, v = np.linalg.eigh(hd)
    return ((v * np.exp(-1j * eta * w)) @ v.conj().T)[:, SECTOR]


def _own_link_errors(qc, eta: float) -> list:
    Operator = api("qiskit.quantum_info:Operator")
    QuantumCircuit = api("qiskit:QuantumCircuit")
    per_link = {l: [] for l in range(N_LINKS)}
    for ins in qc.data:
        qs = [qc.find_bit(q).index for q in ins.qubits]
        links = {q // 4 for q in qs}
        assert len(links) == 1, "own check: gate across links"
        per_link[links.pop()].append((ins, qs))
    T = _own_target(eta)
    errs = []
    for l in range(N_LINKS):
        sub = QuantumCircuit(4)
        for ins, qs in per_link[l]:
            sub.append(ins.operation, [q - 4 * l for q in qs])
        V = Operator(sub).data[:, SECTOR]
        z = np.vdot(T, V)
        ph = z / abs(z) if abs(z) > 1e-300 else 1.0
        errs.append(float(np.linalg.norm(V - ph * T, 2)))
    return errs


def _with_first_rz(qc, delta: float, link: int):
    """Copy of qc whose first rz on a qubit of `link` has its angle shifted by delta."""
    CircuitInstruction = api("qiskit.circuit:CircuitInstruction")
    out = qc.copy()
    for i, inst in enumerate(out.data):
        if inst.operation.name in ("rz", "p", "crx", "crz", "cp", "rx", "ry") and out.find_bit(inst.qubits[-1]).index // 4 == link:
            op = inst.operation.copy()
            op.params = [float(op.params[0]) + delta]
            out.data[i] = CircuitInstruction(op, inst.qubits, inst.clbits)
            return out
    raise AssertionError(f"no rotation found on link {link}")


def test_M5X_O2_outer_det_row_certified():
    """outer_det_certify certifies the 12-link det row at four etas (bound <= 1e-10, 12 links, unit-modulus phase); the test's
    own per-link operators reproduce the link errors; the sparse engine on seeded valid 48-bit codes reproduces the product
    target (each link: cos 2eta on A / B, -i sin 2eta to the flipped code, 1 on the quartet) and stays inside the valid codes;
    the eight outer gadgets alone equal the row with the inner part removed; mutants (1e-7 angle error on an outer link, wrong
    sign, a cross-link CX, an X on an outer qubit, the inner-only circuit, an extra register) are not certified, never raise."""
    enc = api("su2plaq.encodings.rishon:RishonEncoding")()
    build_UD = api("su2plaq.circuits.rishon:build_UD")
    certify = api("su2plaq.rishon.results:outer_det_certify")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    assert [int(s) for s in api("su2plaq.rishon.algebra:RishonLink")().sector] == SECTOR
    for eta in ETAS:
        qc = build_UD(eta, with_outer=True, include_outer_det=True)
        assert qc.num_qubits == 48 and [r.name for r in qc.qregs] == ["d", "o"]
        touched = {qc.find_bit(q).index for inst in qc.data for q in inst.qubits}
        assert touched & set(range(16, 48)), "the row must act on the outer links"
        r = certify(qc, enc, eta)
        assert r["certified"] is True and r["ok"] is True and r["reason"] == "ok", r
        assert r["method"] == "outer_det_gadgets" and r["n_links"] == N_LINKS and r["tol_err"] == TOL_ERR
        assert len(r["link_errors"]) == N_LINKS and r["error_bound"] <= TOL_ERR
        assert abs(r["error_bound"] - sum(r["link_errors"])) <= 1e-15 and r["max_link_error"] == max(r["link_errors"])
        assert abs(abs(complex(r["phase"])) - 1.0) <= 1e-12
        own = _own_link_errors(qc, eta)
        assert max(abs(a - b) for a, b in zip(own, r["link_errors"])) <= 1e-12
        # sparse engine on seeded valid 48-bit codes: amplitude of every output code = product over links of the link entries
        sample = enc.physical_vectors("sample")
        codes = np.unique(np.concatenate([np.asarray(k, dtype=np.int64) for k in sample.codes]))
        rng = np.random.default_rng(SEED)
        codes = np.sort(rng.choice(codes, size=N_SAMPLE_CODES, replace=False))
        batch = run_batch(qc, codes)
        T16 = np.zeros((16, 16), dtype=complex)
        T16[:, SECTOR] = _own_target(eta)
        ph = complex(r["phase"])
        seen = np.zeros(len(codes))
        for key, col, amp in zip(batch.keys, batch.cols, batch.amps):
            if abs(amp) <= 1e-13:
                continue
            assert _ref.valid_code(int(key)), "the det row left the valid 48-bit codes"
            want = ph
            for l in range(N_LINKS):
                want *= T16[(int(key) >> (4 * l)) & 15, (int(codes[col]) >> (4 * l)) & 15]
            assert abs(amp - want) <= 1e-10, (int(key), int(codes[col]), amp, want)
            seen[col] += abs(amp) ** 2
        assert np.abs(seen - 1.0).max() <= 1e-10
    eta = 0.29
    base = build_UD(eta, with_outer=True, include_outer_det=True)
    r = certify(_with_first_rz(base, 1e-7, link=5), enc, eta)
    assert r["certified"] is False and 2e-8 <= r["error_bound"] <= 2e-7, r
    r = certify(build_UD(-eta, with_outer=True, include_outer_det=True), enc, eta)
    assert r["certified"] is False and r["error_bound"] >= 1.0, r
    qc = base.copy()
    qc.cx(3, 4)
    r = certify(qc, enc, eta)
    assert r["certified"] is False and r["reason"] == "cross_link_gate", r
    qc = base.copy()
    qc.x(18)
    r = certify(qc, enc, eta)
    assert r["certified"] is False and r["ok"] is False, r
    r = certify(build_UD(eta, with_outer=True), enc, eta)          # inner gadgets only: the outer links are missing their rotation
    assert r["certified"] is False and r["error_bound"] > TOL_ERR, r
    r = certify(build_UD(eta), enc, eta)                            # 16 qubits: not the 12-link register
    assert r["certified"] is False and r["reason"] == "ancilla_register", r


def test_M5X_O2_outer_det_row_results_file(root):
    """results/rishon/UD_outer_row_certified.json exists (scripts/m5_det_results.py), carries provenance on a clean commit, a
    certified `outer_det_gadgets` verdict at eta = 0.29 with error_bound <= 1e-10 and 12 links, the row's logical counts
    (at most 96 CX, 24 rotations: 12 gadgets), and a fresh outer_det_certify call reproduces its numbers."""
    f = root / "results" / "rishon" / "UD_outer_row_certified.json"
    if not f.exists():
        pytest.fail("PENDING: results/rishon/UD_outer_row_certified.json missing (prompts/204 step D6)", pytrace=False)
    d = json.loads(f.read_text())
    assert d["encoding"] == "rishon" and d["kind"] == "UD" and d["params"]["eta"] == 0.29
    prov = d["provenance"]
    assert isinstance(prov["git_commit"], str) and prov["git_commit"] not in ("", "unknown") and prov["git_dirty"] is False
    v = d["verification"]
    assert v["method"] == "outer_det_gadgets" and v["certified"] is True and v["ok"] is True
    assert v["n_links"] == N_LINKS and v["error_bound"] <= TOL_ERR and len(v["link_errors"]) == N_LINKS
    lg = d["metrics"]["logical"]
    assert 1 <= lg["n_rot"] <= 24 and lg["cx"] <= 96 and lg["qubits"] == 48
    enc = api("su2plaq.encodings.rishon:RishonEncoding")()
    build_UD = api("su2plaq.circuits.rishon:build_UD")
    certify = api("su2plaq.rishon.results:outer_det_certify")
    r = certify(build_UD(0.29, with_outer=True, include_outer_det=True), enc, 0.29)
    assert abs(r["error_bound"] - v["error_bound"]) <= 1e-15 and abs(r["max_link_error"] - v["max_link_error"]) <= 1e-15
    assert r["n_links"] == v["n_links"] and r["certified"] is True
