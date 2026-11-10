"""M5x-O1 (prompts/202 step O1) — certified outer electric row of build_UE (METHODS-rishon R6, R9; audit 200 N5).

The outer-row circuit build_UE(alpha, with_outer=True, include_outer_electric=True) is a tensor product of 12 per-link
gadgets on disjoint qubits.  `outer_electric_certify` partitions the gates by link, computes each link's exact 16x16
operator and compares it on the 6 sector codes with diag(exp(-i (3/4) alpha [type Q])) after one global phase per link;
error_bound = sum over links of the link errors bounds the error on every superposition of valid 48-bit codes (telescoping
of a tensor product of unitaries), i.e. on all 38 432 physical states -- exhaustive, unlike the seeded sample
`outer_electric_check` of M5 (which stays as is).

Tolerance 1e-10 = METHODS section 6 tol_err for exact-angle circuits; each link error is a 16-dim product of <= 3 exact gates
(~1e-16), so the bound (12 terms) is far below it.  The 1e-7 phase mutant sits 1000x above the tolerance.  Cross-checks:
own per-link operators 1e-14 (same arithmetic, different code), sparse run_batch on seeded 48-bit codes 1e-12 (exact engine
on diagonal/permutation gates).  Prototype: scratch/planner/proto_outer_row.py (5 ms, error 0.0; reports/research/201)."""
import json
import pathlib

import numpy as np
import pytest

from tests.acceptance._api import api

TOL_ERR = 1e-10
TOL_OWN = 1e-14
TOL_SPARSE = 1e-12
ALPHAS = (0.37, 0.91, 1.70)
N_LINKS = 12
N_SAMPLE_CODES = 40
SEED = 20261104


def _own_link_errors(qc, alpha: float, sector: list) -> list:
    """Own per-link check: slice the circuit by link (q // 4), Qiskit Operator on 4 qubits, compare on the sector codes."""
    Operator = api("qiskit.quantum_info:Operator")
    QuantumCircuit = api("qiskit:QuantumCircuit")
    Q = {5, 6, 9, 10}
    per_link = {l: [] for l in range(N_LINKS)}
    for ins in qc.data:
        qs = [qc.find_bit(q).index for q in ins.qubits]
        links = {q // 4 for q in qs}
        assert len(links) == 1, "own check: gate across links"
        per_link[links.pop()].append((ins, qs))
    errs = []
    for l in range(N_LINKS):
        sub = QuantumCircuit(4)
        for ins, qs in per_link[l]:
            sub.append(ins.operation, [q - 4 * l for q in qs])
        V = Operator(sub).data[:, sector]
        tgt = np.array([np.exp(-0.75j * alpha * (s in Q)) for s in sector])
        z = sum(np.conj(tgt[k]) * V[s, k] for k, s in enumerate(sector))
        ph = z / abs(z) if abs(z) > 1e-300 else 1.0
        R = V.copy()
        for k, s in enumerate(sector):
            R[s, k] -= ph * tgt[k]
        errs.append(float(np.linalg.norm(R, 2)))
    return errs


def test_M5X_O1_outer_electric_row_certified():
    """outer_electric_certify certifies the shipped outer-row circuit at three alphas (bound <= 1e-10, 12 links, unit
    phase); the test's own per-link operators reproduce the link errors; sparse run_batch on seeded valid 48-bit codes
    agrees with exp(-i (3/4) alpha #Q); mutants (1e-7 phase on an outer qubit, a cross-link CX, an X on an outer qubit,
    the circuit without the outer row) are not certified and never raise."""
    enc = api("su2plaq.encodings.rishon:RishonEncoding")()
    build_UE = api("su2plaq.circuits.rishon:build_UE")
    certify = api("su2plaq.rishon.results:outer_electric_certify")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    sector = [int(s) for s in api("su2plaq.rishon.algebra:RishonLink")().sector]
    assert sector == [3, 5, 6, 9, 10, 12]
    for alpha in ALPHAS:
        qc = build_UE(alpha, with_outer=True, include_outer_electric=True)
        r = certify(qc, enc, alpha)
        assert r["certified"] is True and r["ok"] is True and r["reason"] == "ok", r
        assert r["method"] == "outer_electric_gadgets" and r["n_links"] == N_LINKS and r["tol_err"] == TOL_ERR
        assert len(r["link_errors"]) == N_LINKS and r["error_bound"] <= TOL_ERR
        assert abs(r["error_bound"] - sum(r["link_errors"])) <= 1e-15 and r["max_link_error"] == max(r["link_errors"])
        assert abs(abs(complex(r["phase"])) - 1.0) <= 1e-12
        own = _own_link_errors(qc, alpha, sector)
        assert max(abs(a - b) for a, b in zip(own, r["link_errors"])) <= TOL_OWN
        # sparse engine on seeded valid 48-bit codes (exact: 36 diagonal/permutation gates)
        sample = enc.physical_vectors("sample")
        codes = np.unique(np.concatenate([np.asarray(k, dtype=np.int64) for k in sample.codes]))
        rng = np.random.default_rng(SEED)
        codes = np.sort(rng.choice(codes, size=N_SAMPLE_CODES, replace=False))
        nq = np.array([enc.decode(int(c)).count("Q") for c in codes], dtype=np.float64)
        batch = run_batch(qc, codes)
        assert np.array_equal(batch.keys, codes[batch.cols]), "the row must map every valid code to itself"
        amps = np.zeros(len(codes), dtype=np.complex128)
        np.add.at(amps, batch.cols, batch.amps)
        tgt = np.exp(-0.75j * alpha * nq)
        ph = complex(r["phase"])
        assert np.abs(amps - ph * tgt).max() <= TOL_SPARSE
    alpha = 0.37
    qc = build_UE(alpha, with_outer=True, include_outer_electric=True)
    qc.p(1e-7, 20)
    r = certify(qc, enc, alpha)
    assert r["certified"] is False and r["error_bound"] >= 0.9e-7, r
    qc = build_UE(alpha, with_outer=True, include_outer_electric=True)
    qc.cx(3, 4)
    r = certify(qc, enc, alpha)
    assert r["certified"] is False and r["reason"] == "cross_link_gate", r
    qc = build_UE(alpha, with_outer=True, include_outer_electric=True)
    qc.x(18)
    r = certify(qc, enc, alpha)
    assert r["certified"] is False and r["ok"] is False, r
    qc = build_UE(alpha, with_outer=True)          # inner gadgets only: the outer links are missing their phase
    r = certify(qc, enc, alpha)
    assert r["certified"] is False and r["error_bound"] > TOL_ERR, r


def test_M5X_O1_outer_row_results_file(root):
    """results/rishon/UE_outer_row_certified.json exists (scripts/m5x_outer_row.py), carries provenance on a clean commit,
    a certified `outer_electric_gadgets` verdict at alpha = 0.37 with error_bound <= 1e-10 and 12 links, and a fresh
    outer_electric_certify call reproduces its numbers."""
    f = root / "results" / "rishon" / "UE_outer_row_certified.json"
    if not f.exists():
        pytest.fail("PENDING: results/rishon/UE_outer_row_certified.json missing (prompts/202 step O1)", pytrace=False)
    d = json.loads(f.read_text())
    assert d["encoding"] == "rishon" and d["kind"] == "UE" and d["params"]["alpha"] == 0.37
    prov = d["provenance"]
    assert isinstance(prov["git_commit"], str) and prov["git_commit"] not in ("", "unknown") and prov["git_dirty"] is False
    v = d["verification"]
    assert v["method"] == "outer_electric_gadgets" and v["certified"] is True and v["ok"] is True
    assert v["n_links"] == N_LINKS and v["error_bound"] <= TOL_ERR and len(v["link_errors"]) == N_LINKS
    enc = api("su2plaq.encodings.rishon:RishonEncoding")()
    build_UE = api("su2plaq.circuits.rishon:build_UE")
    certify = api("su2plaq.rishon.results:outer_electric_certify")
    r = certify(build_UE(0.37, with_outer=True, include_outer_electric=True), enc, 0.37)
    assert abs(r["error_bound"] - v["error_bound"]) <= 1e-15 and abs(r["max_link_error"] - v["max_link_error"]) <= 1e-15
    assert r["n_links"] == v["n_links"] and r["certified"] is True
