"""M3x (M3 extension, prompts/102) — kernel-checked exact structure of the spin-network encoding, Lean 4.

m3x is an extension folder: m3 is locked (acceptance-v7) and m4 belongs to the compression milestone, so the wait-time
Lean work of prompts/102 gets its own folder, locked with `python tools/lock.py m3x` + acceptance-lock.

W1 (lean/Su2Plaq/SpinNet/Recoupling.lean, Mathlib-free): Wigner 6j by Racah's formula and the F-symbol over exact
    square-root-free arithmetic (q*sqrt(r), q, r rational); the codec (code -> label); the route-B plaquette amplitude
    P[y', y] and K = -(P + P^T) on the 47 inner codes.  Kernel-checked: validCodes = exported codes, 2K = exported
    coupling table on all 47 x 47 entries (coupling_from_6j, k_from_6j_full), K symmetric and a four-link-flip matching.
W2 (lean/Su2Plaq/SpinNet/Semantics.lean, Mathlib-free): exact gate semantics (Qiskit matrices of x, cx, rccx, h, rz) over
    Z[i][z, z^-1], z = e^{i beta/4}; the 48-gate build_UB rendered from the Qiskit circuit; kernel-checked
    ub_exact_all_codes: the circuit maps every valid inner code (ancillas 0) exactly to e^{-i beta K}|code> for all beta.
W3 (lean/Su2Plaq/SpinNet/Spectrum.lean, Mathlib-free): the 433 states from the codec, H_B = (+)_o K|_o, an explicit
    eigenbasis e_s +- e_s' checked densely inside every outer block, multiplicities 16/96/16/177/16/96/16.
L  (lean/Su2Plaq/SpinNet/Bridge.lean imports Circuit): the exported tables equal the m3 tables (tables_agree); every
    theorem above depends on the standard axioms only (no native_decide, no sorry).

Numbers: float cross-checks of exact values use 1e-12 (exact rationals / q*sqrt(r) of magnitude <= 2 rounded to float64:
~1e-15; same margin as every exact-vs-float check of M2/M3); eigenvalue binning 1e-9 (eigvalsh error ~1e-14 * ||H_B||);
time limits: lean_eval 300 s per call (Mathlib-free #eval, measured <= 5 s), print_axioms 900 s (one Mathlib import,
as M2/M3).  Prototype numbers: scratch/planner/lean/SpinNetExact.lean, 22 s / 1.9 GB for all theorems (reports/research/101).
"""
import itertools
import pathlib
import time

import numpy as np
import pytest

from tests.acceptance._api import api

STANDARD = {"propext", "Classical.choice", "Quot.sound"}
NS = "Su2Plaq.SpinNet."
RECOUPLING_THEOREMS = ("valid_codes_from_codec", "k_matching", "coupling_from_6j", "k_from_6j_full")
SEMANTICS_THEOREMS = ("ub_h_count", "ub_exact_all_codes")
SPECTRUM_THEOREMS = ("card_states_exact", "blocks_cover", "eig_blocks", "eig_count", "eig_mult")
BRIDGE_THEOREMS = ("tables_agree",)
ALL_THEOREMS = tuple(NS + n for n in RECOUPLING_THEOREMS + SEMANTICS_THEOREMS + SPECTRUM_THEOREMS + BRIDGE_THEOREMS)
MULTIPLICITIES = {-4: 16, -2: 96, -1: 16, 0: 177, 1: 16, 2: 96, 4: 16}      # 2 lambda -> multiplicity
GATE_NAMES = ("x", "cx", "rccx", "h", "rz")
TOL_EXACT = 1e-12
TOL_EIG = 1e-9


def _lean_file(root: pathlib.Path, rel: str) -> pathlib.Path:
    d = root / "lean"
    if not (d / "lakefile.toml").exists():
        pytest.fail("PENDING: lean/lakefile.toml missing (prompts/006 step 2.L1)", pytrace=False)
    p = d / rel
    if not p.exists():
        pytest.fail(f"PENDING: {p.relative_to(root)} missing (prompts/102 steps W1-W4)", pytrace=False)
    return p


def _no_native_no_sorry(src: str):
    assert "native_decide" not in src and "sorry" not in src and "admit" not in src


def _mathlib_free(src: str):
    """Only imports of Su2Plaq.SpinNet.{Recoupling,Semantics} are allowed (the heavy `decide`s must not load Mathlib)."""
    for line in src.splitlines():
        if line.startswith("import "):
            assert line.split()[1] in ("Su2Plaq.SpinNet.Recoupling", "Su2Plaq.SpinNet.Semantics"), line


def _statement(src: str, short: str) -> str:
    assert f"theorem {short}" in src, short
    return src.split(f"theorem {short}", 1)[1].split(":= by", 1)[0]


def _codes_433(enc) -> set:
    """The 433 physical codes y + 256 o of METHODS-spinnet section 1 from the route-B labels."""
    out = set()
    for j, J in enc.labels():
        y = sum(int(j[l] == 0.5) << l for l in range(4)) + sum(int(J[c] == 1.0) << (4 + c) for c in range(4))
        o = sum(int(j[4 + k] == 0.5) << k for k in range(8))
        out.add(y + 256 * o)
    assert len(out) == 433
    return out


def test_M3X_W1_recoupling_matches_wigner_and_codec(root):
    """Recoupling.lean exists, is Mathlib-free, contains the four theorem statements (no native_decide/sorry) and the
    exported tables verbatim; Lean's 6j (q*sqrt(r), Racah) agrees with su2plaq.su2.wigner.six_j on all 729 doubled-spin
    argument tuples in {0, 1/2, 1}^6 to 1e-12; Lean's validCodes are the encoding's 47 sorted inner codes."""
    p = _lean_file(root, "Su2Plaq/SpinNet/Recoupling.lean")
    src = p.read_text()
    _no_native_no_sorry(src)
    _mathlib_free(src)
    for short in RECOUPLING_THEOREMS:
        _statement(src, short)
    assert "racahSum" in src and "fsym" in src and "sixj" in src
    LE = api("su2plaq.spinnet.lean_export")
    enc = api("su2plaq.encodings.spinnet:SpinNet")()
    lit = LE.lean_literals(enc)
    assert lit["coupling"] in src and lit["codes"] in src, "exported tables must appear verbatim in Recoupling.lean"
    six_j = api("su2plaq.su2.wigner:six_j")
    t0 = time.time()
    table = LE.lean_sixj_table()
    assert time.time() - t0 <= 300
    assert len(table) == 3 ** 6
    worst = 0.0
    for args in itertools.product((0, 1, 2), repeat=6):
        ref = six_j(*(a / 2 for a in args))
        worst = max(worst, abs(table[args] - ref))
    assert worst <= TOL_EXACT, worst
    assert sum(1 for v in table.values() if abs(v) > TOL_EXACT) >= 50       # the table is not trivially zero
    assert LE.lean_valid_codes() == [int(c) for c in enc.inner_codes()]


def test_M3X_W2_semantics_gate_list_and_qiskit_matrices(root):
    """Semantics.lean exists, is Mathlib-free, states ub_h_count (= 2) and ub_exact_all_codes; its generated gate list is
    exactly build_UB(1.0) gate for gate (names, little-endian qubit indices, rz angles as integers in units of beta/2,
    48 gates, rz integers = angle_ints); the Lean gate semantics evaluated at beta = 0.61 reproduce Qiskit's matrices of
    x, cx, rccx, h, rz on 3 qubits to 1e-12 (the only link between the Lean model and Qiskit's gate definitions)."""
    p = _lean_file(root, "Su2Plaq/SpinNet/Semantics.lean")
    src = p.read_text()
    _no_native_no_sorry(src)
    _mathlib_free(src)
    assert "= 2" in _statement(src, "ub_h_count")
    _statement(src, "ub_exact_all_codes")
    LE = api("su2plaq.spinnet.lean_export")
    enc = api("su2plaq.encodings.spinnet:SpinNet")()
    build_UB = api("su2plaq.circuits.spinnet:build_UB")
    qc = build_UB(1.0)
    gates = LE.gate_ints(qc)
    assert len(gates) == len(qc.data) == 48
    assert all(g[0] in GATE_NAMES for g in gates)
    for g, ins in zip(gates, qc.data):
        assert g[0] == ins.operation.name
        assert list(g[1:1 + len(ins.qubits)]) == [qc.find_bit(q).index for q in ins.qubits]
    assert [g[2] for g in gates if g[0] == "rz"] == LE.angle_ints(enc)
    assert LE.gate_literal(qc) in src, "the Lean gate list differs from the shipped build_UB"
    assert LE.gate_literal(build_UB(0.61)) == LE.gate_literal(qc)              # angle-linear: beta-independent literal
    Operator = api("qiskit.quantum_info:Operator")
    QuantumCircuit = api("qiskit:QuantumCircuit")
    beta = 0.61
    t0 = time.time()
    for gate in (("x", 0), ("cx", 0, 1), ("cx", 2, 0), ("rccx", 0, 1, 2), ("rccx", 2, 0, 1), ("h", 0), ("h", 2),
                 ("rz", 0, -7), ("rz", 1, 3)):
        M = LE.lean_gate_images(gate, 3, beta)
        ref = QuantumCircuit(3)
        if gate[0] == "rz":
            ref.rz(gate[2] * beta / 2, gate[1])
        else:
            getattr(ref, gate[0])(*gate[1:])
        R = Operator(ref).data
        assert M.shape == R.shape == (8, 8)
        assert np.abs(M - R).max() <= TOL_EXACT, (gate, np.abs(M - R).max())
    assert time.time() - t0 <= 300


def test_M3X_W3_spectrum_states_and_multiplicities(root):
    """Spectrum.lean exists, is Mathlib-free, states the five theorems with the locked numbers (433 states, 433 vectors,
    multiplicities [16, 96, 16, 177, 16, 96, 16] for 2 lambda in [-4, -2, -1, 0, 1, 2, 4]); Lean's `states` are exactly
    the encoding's 433 codes y + 256 o; the numerical spectrum of the encoding's H_B has the same multiplicities."""
    p = _lean_file(root, "Su2Plaq/SpinNet/Spectrum.lean")
    src = p.read_text()
    _no_native_no_sorry(src)
    _mathlib_free(src)
    assert "= 433" in _statement(src, "card_states_exact")
    assert "= 433" in _statement(src, "blocks_cover")
    assert "= 433" in _statement(src, "eig_count")
    _statement(src, "eig_blocks")
    s = _statement(src, "eig_mult")
    assert "[-4, -2, -1, 0, 1, 2, 4]" in s and "[16, 96, 16, 177, 16, 96, 16]" in s
    LE = api("su2plaq.spinnet.lean_export")
    enc = api("su2plaq.encodings.spinnet:SpinNet")()
    t0 = time.time()
    states = LE.lean_states()
    assert time.time() - t0 <= 300
    assert len(states) == 433 and len(set(states)) == 433
    assert set(states) == _codes_433(enc)
    HB = enc.h_magnetic()
    assert HB.shape == (433, 433) and np.abs(HB - HB.T).max() <= TOL_EXACT
    ev = np.linalg.eigvalsh(HB)
    counts = {k: int(np.sum(np.abs(2 * ev - k) <= TOL_EIG)) for k in MULTIPLICITIES}
    assert counts == MULTIPLICITIES, counts
    assert sum(counts.values()) == 433


def test_M3X_L_exact_theorems_kernel_checked(root):
    """All twelve theorems exist, are proved without native_decide or sorry, and depend on the standard axioms only
    (`decide` proofs: propext or none); Bridge.lean ties the exported tables to the m3 tables of Circuit.lean; lean/
    Su2Plaq.lean imports Su2Plaq.SpinNet.Bridge; no_sorry() is clean."""
    for rel in ("Su2Plaq/SpinNet/Recoupling.lean", "Su2Plaq/SpinNet/Semantics.lean", "Su2Plaq/SpinNet/Spectrum.lean"):
        _no_native_no_sorry(_lean_file(root, rel).read_text())
    bridge = _lean_file(root, "Su2Plaq/SpinNet/Bridge.lean").read_text()
    _no_native_no_sorry(bridge)
    assert "import Su2Plaq.SpinNet.Circuit" in bridge
    s = _statement(bridge, "tables_agree")
    assert "validInnerCodes" in s and "couplingTable" in s
    assert "import Su2Plaq.SpinNet.Bridge" in (root / "lean" / "Su2Plaq.lean").read_text()
    P = api("su2plaq.lean.project")
    t0 = time.time()
    ax = P.print_axioms(list(ALL_THEOREMS), timeout=900)
    assert time.time() - t0 <= 900
    missing = [n for n in ALL_THEOREMS if n not in ax or "<unknown>" in ax[n]]
    assert not missing, missing
    bad = {n: sorted(ax[n] - STANDARD) for n in ALL_THEOREMS if ax[n] - STANDARD}
    assert not bad, bad
    assert P.no_sorry() == []
