"""M8-S1, M8-H3, M8-U1 — registry-independent parts of the LSH compression milestone (prompts/401 §1.3, §1.6, §1.8; steps 8.1, 8.U).

S1: the round-0 seed circuits.  The LSH register holds the spin-network state in another bit code (audit 303 N7), so every
    spin-network step circuit C gives the LSH circuit T^dag C T (T = per-site transcoder cx, cx, rccx): +40 CX, +32 T exactly
    (M7-V1).  Seeds: the M7 general circuit, the four vendored spinnet_v2 skeletons behind the electric layer, and three programs
    of the closed spin-network loop (prompts/104) pinned by sha256: its headline r02-F1-002 (31 CX) and the two cheaper-T
    points of its CX / T front.  Planner measurements (scratch/planner/m8/proto_m8_seeds.py, proto_m8_paulo.py; shared
    evaluator, all 433 states, three angle pairs): errors <= 2.0e-14, Gauss <= 6.0e-16, counts as in EXPECTED below; the
    round-0 best is the wrapped spin-network headline, 71 CX.
H3: the stop-rule comparison (prompts/401 §1.6): the headline improves when (CX, sum T, rho, qubits) decreases; the depth
    component of the robust key is ignored (audit 302 §7.7: synthesis-word noise), and at unchanged CX / rotation count /
    fixed T a change of sum T of at most 20 * N_rot (one T per rotation per angle pair, the bound of prompts/104 §11 E3 on
    what tuning can extract from synthesis noise) is a tie.
U1: the uniform Raychowdhury-Stryker point splitting as a comparison ROW (structure only, no circuit): the corner recoupling
    R is real orthogonal with entries that are products of the four-spin-1/2 recoupling coefficients {1, 1/2, sqrt3/2}, and
    R^T H_B R has the structure measured in reports/research/400 §6 (400 non-zeros, up to 4 per row, 9 moduli, depends on the
    outer spins, 6 sites touched) against ours (256, a matching, 3 moduli, 4 sites).

Tolerances: exact-angle circuits 1e-10 on the combined error and on Gauss, weights 1e-20 (prompts/003-004; measured 2e-14);
recoupling orthogonality and entry values 1e-12 (products of <= 2 Clebsch-Gordan overlaps, measured 2.7e-15); spectrum 1e-10
(eigvalsh of a 433 x 433 matrix with norm <= 2, measured 3.3e-15, as M7-X1); counts exact."""
from __future__ import annotations

import functools
import hashlib
import itertools

import numpy as np
import pytest

from tests.acceptance._api import api

ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}
ANGLES = ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00))
# label -> (CX, rotations, fixed T, ancillas): planner prototype; wrapped = spin-network counts + 40 CX + 32 T (M7-V1)
EXPECTED = {
    "general": (94, 8, 88, 7),
    "wrap_pairs9": (74, 13, 56, 3),
    "wrap_flags4": (84, 8, 80, 3),
    "wrap_flags5": (82, 9, 72, 3),
    "wrap_flags6": (76, 10, 64, 3),
    "wrap_sn_headline": (71, 17, 48, 1),
    "wrap_sn_r05F3": (72, 13, 56, 1),
    "wrap_sn_r02F5": (74, 10, 64, 1),
}
# spin-network programs of the closed M4 loop (git 49e247e): label -> (file, sha256, spin-network archive entry, its CX)
WRAP_SOURCES = {
    "wrap_sn_headline": ("compress/programs/spinnet/F1/002-dimer-linear-corner-walk.py",
                         "750151e9ad417de7d52e4c59a203f1dc493bdea3be5742aa331533170a0ec650", "r02-F1-002", 31),
    "wrap_sn_r05F3": ("compress/programs/spinnet/F3/005-angle-linear-walk.py",
                      "43605421051ce5e26b85b1b5241eb02638fc5f8ad7c6297a67e7dd0e96fd22e4", "r05-F3-005", 32),
    "wrap_sn_r02F5": ("compress/programs/spinnet/F5/002-bright_flag_6rot.py",
                      "734a62fe58f316d6deb59561fb90cedcb04e5854f260f4d78e680eb688428f81", "r02-F5-002", 34),
}
SEED_LABELS = ("general", "wrap_pairs9", "wrap_flags4", "wrap_flags5", "wrap_flags6", "wrap_sn_headline", "wrap_sn_r05F3",
               "wrap_sn_r02F5", "general+polish", "qiskit_l3")


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.lsh:LSH")()


def _skeleton(qc):
    return [(inst.operation.name, tuple(qc.find_bit(q).index for q in inst.qubits)) for inst in qc.data]


# ------------------------------------------------------------------------------------------------ S1
@pytest.mark.parametrize("label", list(EXPECTED))
def test_M8_S1_seed_circuits_exact(label, root):
    """`lsh.loop.seed_circuit(label, alpha, beta)`: registers d[12], o[12], ancillas; allowed gates; exact on all 433 states at
    the three angle pairs with one skeleton; the outer register is never touched; counts as measured; a wrapped spin-network
    program costs exactly its own CX + 40; the three archive sources are the pinned files."""
    LL = api("su2plaq.lsh.loop")
    seed_circuit = api("su2plaq.lsh.loop:seed_circuit")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    lmf = api("su2plaq.metrics.logical:logical_metrics")
    enc = _enc()
    assert tuple(LL.SEED_LABELS) == SEED_LABELS
    assert {k: tuple(v) for k, v in LL.WRAP_SOURCES.items()} == {k: v[:3] for k, v in WRAP_SOURCES.items()}
    if label in WRAP_SOURCES:
        rel, sha, _entry, sn_cx = WRAP_SOURCES[label]
        assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == sha, f"{rel} changed: the pinned spin-network program is gone"
        assert EXPECTED[label][0] == sn_cx + 40
    skel = None
    for alpha, beta in ANGLES:
        qc = seed_circuit(label, alpha, beta)
        assert [r.name for r in qc.qregs][:2] == ["d", "o"] and qc.qregs[0].size == 12 and qc.qregs[1].size == 12
        assert {inst.operation.name for inst in qc.data} <= ALLOWED
        assert not [1 for inst in qc.data for q in inst.qubits if 12 <= qc.find_bit(q).index < 24]
        v = evaluate(qc, enc, enc.target("step", alpha, beta, order=1))
        assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20
        assert v.gauss_residual <= 1e-10 and v.outer_bits_read == 0 and v.n_inputs == 433
        sk = _skeleton(qc)
        assert skel is None or sk == skel, "the skeleton depends on the angles"
        skel = sk
    lm = lmf(seed_circuit(label, *ANGLES[0]))
    assert (lm["cx"], lm["n_rot"], lm["t_fixed"], lm["ancilla"]) == EXPECTED[label], (label, lm["cx"], lm["n_rot"], lm["t_fixed"], lm["ancilla"])
    assert lm["qubits"] == 24 + EXPECTED[label][3]
    v = evaluate(seed_circuit(label, 0.37, 0.61), enc, enc.target("step", 0.37, -0.61, order=1))     # gauge pinned as in M7-S1
    assert not v.ok and v.op_norm_error > 1e-3
    with pytest.raises(ValueError):
        seed_circuit("no_such_seed", 0.37, 0.61)


# ------------------------------------------------------------------------------------------------ H3 (rule)
def _rec(cx=71, t_sum=22480, rho=0, qubits=25, n_rot=17, t_fixed=48):
    return {"id": "x", "cx": cx, "t_sum": t_sum, "rho": rho, "qubits": qubits, "n_rot": n_rot, "t_fixed": t_fixed}


def test_M8_H3_stop_rule_comparison():
    """`lsh.loop.improves(new, old)` on headline records {cx, t_sum, rho, qubits, n_rot, t_fixed}: lexicographic on
    (cx, t_sum, rho, qubits); with cx, n_rot and t_fixed all unchanged a difference |t_sum| <= 20 * n_rot is a tie decided by
    (rho, qubits); the first headline always improves; a missing new headline never does.  Budgets: 8 rounds, 3 rounds
    without improvement, 20 proposer sessions (prompts/001 §4)."""
    LL = api("su2plaq.lsh.loop")
    improves = api("su2plaq.lsh.loop:improves")
    assert (LL.STOP_MAX_ROUNDS, LL.STOP_NO_GAIN_ROUNDS, LL.STOP_MAX_SESSIONS) == (8, 3, 20)
    assert LL.T_NOISE_PER_ROTATION == 1 and LL.N_ANGLE_PAIRS == 20
    old = _rec()
    assert improves(old, None) is True and improves(None, old) is False
    assert improves(_rec(), old) is False                                  # identical
    assert improves(_rec(cx=70, t_sum=30000, qubits=40), old) is True      # CX first
    assert improves(_rec(cx=72, t_sum=10000), old) is False
    noise = 20 * 17                                                        # 340 T in the sum over the 20 pairs
    assert improves(_rec(t_sum=22480 - noise), old) is False               # same structure, inside the synthesis-noise band
    assert improves(_rec(t_sum=22480 - 8), old) is False
    assert improves(_rec(t_sum=22480 - noise - 1), old) is True            # same structure, beyond the band
    assert improves(_rec(t_sum=22480 + 8, rho=0), _rec(rho=1)) is True     # inside the band: angle-linear wins the tie
    assert improves(_rec(t_sum=22480 - 8, rho=1), old) is False
    assert improves(_rec(t_sum=22480 + 100, qubits=24), old) is True       # inside the band, same rho: fewer qubits
    assert improves(_rec(t_sum=22480 - 100, qubits=26), old) is False
    assert improves(_rec(n_rot=16, t_sum=22480 - 100), old) is True        # one rotation fewer: structure changed, plain comparison
    assert improves(_rec(n_rot=16, t_sum=22480 + 100), old) is False
    assert improves(_rec(t_fixed=40, t_sum=22480 - 160), old) is True      # fewer fixed T
    assert improves(_rec(rho=0), _rec(rho=1)) is True and improves(_rec(rho=1), _rec(rho=0)) is False
    assert improves(_rec(qubits=24), old) is True and improves(_rec(qubits=26), old) is False
    assert LL.stop_key(old) == (71, 22480, 0, 25)


# ------------------------------------------------------------------------------------------------ U1
def test_M8_U1_uniform_split_structure_row():
    """`lsh.rs_split`: recoupling of corners 1 and 3 to the pairing (inner, outer | inner, outer) of Raychowdhury-Stryker's
    uniform splitting; orthogonal, analytic entry values, same spectrum; H_B in that basis is not a matching, has sqrt3
    entries, depends on the outer spins and acts on 6 sites (18 qubits) -- the numbers of reports/research/400 §6."""
    RS = api("su2plaq.lsh.rs_split")
    R = np.asarray(RS.recoupling(), dtype=float)
    assert R.shape == (433, 433) and tuple(RS.RS_CORNERS) == (1, 3)
    assert np.abs(R.T @ R - np.eye(433)).max() <= 1e-12
    factors = (1.0, 0.5, np.sqrt(3) / 2)                 # |<(j1 j2)J (j3 j4)J | (j1 j4)J' (j2 j3)J'>| for spins <= 1/2: 1, 1/2, sqrt3/2
    allowed = sorted({a * b for a, b in itertools.product(factors, repeat=2)})
    vals = np.abs(R[np.abs(R) > 1e-12])
    assert np.abs(vals[:, None] - np.asarray(allowed)[None, :]).min(axis=1).max() <= 1e-12
    mixed_rows = int((np.abs(np.abs(R).max(axis=1) - 1) > 1e-9).sum())
    assert 0 < mixed_rows < 433                          # identity wherever both corner spaces are one-dimensional
    basis = api("su2plaq.exact.physical:physical_basis")(convention="cg")
    HA = np.asarray(api("su2plaq.exact.operators:h_magnetic_phys")(basis)[0])
    H = np.asarray(RS.h_magnetic_rs())
    assert np.abs(H - R.T @ HA @ R).max() <= 1e-12 and np.abs(H - H.T).max() <= 1e-12
    assert np.abs(np.linalg.eigvalsh(H) - np.linalg.eigvalsh(HA)).max() <= 1e-10
    s = RS.structure()
    assert (s["nnz"], s["max_per_row"], s["rows_nonzero"]) == (400, 4, 324)
    assert (s["ours"]["nnz"], s["ours"]["max_per_row"], s["ours"]["rows_nonzero"]) == (256, 1, 256)
    r3 = np.sqrt(3)
    assert np.allclose(s["moduli"], [0.25, r3 / 4, 0.5, 0.75, r3 / 2, 1.0, 1.5, r3, 2.0], atol=1e-8) and len(s["moduli"]) == 9
    assert np.allclose(s["ours"]["moduli"], [0.5, 1.0, 2.0], atol=1e-8)
    assert s["n_inner_patterns"] == 47 and s["outer_dependent_inner_patterns"] == 16
    assert s["sites_touched"] == 6 and s["qubits_touched"] == 18 and s["sites_touched_ours"] == 4 and s["qubits_touched_ours"] == 12
    assert s["spectrum_diff"] <= 1e-10
    nz = np.abs(H) > 1e-12                               # independent recount of the pattern numbers from the matrix itself
    assert int(nz.sum()) == s["nnz"] and int(nz.sum(axis=1).max()) == s["max_per_row"] and int((nz.sum(axis=1) > 0).sum()) == s["rows_nonzero"]
