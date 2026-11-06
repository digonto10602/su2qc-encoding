"""Unit tests for the rishon U_B / step circuits (steps 5.7-5.8): stabiliser unprep, separators, cancellation, small exactness."""
import functools

import numpy as np
import pytest

from su2plaq.circuits import rishon as C
from su2plaq.evaluate.sparse_sim import encoded_block, run_batch
from su2plaq.rishon import frames as FR
from su2plaq.rishon import operators as O

ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}


def _apply(code_amps: dict, gates) -> dict:
    """Tiny dense-dict simulator for x, cx, z, cz, h on a few qubits (reference for _unprep)."""
    st = dict(code_amps)
    for name, qs in gates:
        new: dict = {}
        for c, a in st.items():
            if name == "x":
                new[c ^ (1 << qs[0])] = new.get(c ^ (1 << qs[0]), 0) + a
            elif name == "cx":
                k = c ^ (((c >> qs[0]) & 1) << qs[1])
                new[k] = new.get(k, 0) + a
            elif name == "z":
                new[c] = new.get(c, 0) + a * (-1) ** ((c >> qs[0]) & 1)
            elif name == "cz":
                new[c] = new.get(c, 0) + a * (-1) ** (((c >> qs[0]) & (c >> qs[1])) & 1)
            elif name == "h":
                for b in (0, 1):
                    k = (c & ~(1 << qs[0])) | (b << qs[0])
                    new[k] = new.get(k, 0) + a * (1 if not ((c >> qs[0]) & b & 1) else -1) / np.sqrt(2)
            else:
                raise AssertionError(name)
        st = {k: v for k, v in new.items() if abs(v) > 1e-12}
    return st


def test_unprep_maps_signed_affine_state_to_zero():
    codes = [0b0100 | x for x in (0b0000, 0b0011, 0b0101, 0b0110)]       # affine, 2-dim; bit 3 constant 0
    amps = [0.5, -0.5, 0.5, 0.5]
    info = FR._unprep(codes, amps, skip=3)
    out = _apply(dict(zip(codes, amps)), info["net"] + info["phase"] + info["had"])
    assert list(out) == [0] and abs(abs(out[0]) - 1) < 1e-12 and np.sign(out[0]) == info["sign"]


def test_unprep_rejects_non_clifford_signs_and_non_affine_support():
    codes = [0b0000, 0b0001, 0b0010, 0b0100, 0b0011, 0b0101, 0b0110, 0b0111]    # 3-dim affine
    cubic = [1.0 if c != 0b0111 else -1.0 for c in codes]                         # AND of three bits: cubic phase
    with pytest.raises(ValueError, match="quadratic"):
        FR._unprep(codes, [x / np.sqrt(8) for x in cubic], skip=7)
    with pytest.raises(ValueError, match="affine"):
        FR._unprep([0b00, 0b01, 0b10], [1 / np.sqrt(3)] * 3, skip=7)
    with pytest.raises(ValueError, match="uniform"):
        FR._unprep([0b00, 0b01], [0.6, 0.8], skip=7)


def test_separator_minimum_weight_and_inseparable():
    lam = FR._best_separator([0b0011, 0b1011], [0b0111])
    assert bin(lam).count("1") == 1 and lam == 0b0100
    with pytest.raises(ValueError, match="no separating functional"):
        FR._solve_separator([0b001, 0b010, 0b100], [0b111])


def test_min_hitting_set():
    rows = np.array([0b0110, 0b0101, 0b1100, 0b0010], dtype=np.int64)
    assert FR._min_hitting_set(rows, j=0) == [1, 2]                    # {1,2} hits all; no single bit does
    with pytest.raises(ValueError):
        FR._min_hitting_set(np.array([0, 0b10], dtype=np.int64), j=3)


def test_cancel_adjacent_only_identical_self_inverse_neighbours():
    ops = [("x", (0,), ()), ("cx", (0, 1), ()), ("x", (0,), ()), ("cx", (0, 1), ()), ("x", (0,), ()), ("x", (0,), ()),
           ("crx", (0, 1), (0.3,)), ("crx", (0, 1), (0.3,)), ("cz", (2, 3), ()), ("cz", (3, 2), ()), ("ccx", (0, 1, 2), ()),
           ("ccx", (1, 0, 2), ())]
    out = C._cancel_adjacent(ops)
    assert [o[0] for o in out] == ["x", "cx", "x", "cx", "crx", "crx", "ccx", "ccx"]
    assert C._cancel_adjacent([("h", (0,), ()), ("cx", (0, 1), ()), ("h", (0,), ())]) == [("h", (0,), ()), ("cx", (0, 1), ()), ("h", (0,), ())]


@functools.lru_cache(maxsize=1)
def _frames():
    return C.pair_frames(0.5)


def test_pair_frames_structure_from_operator():
    fr = _frames()
    assert len(fr) == 81
    kap = sorted(round(f["kappa"], 9) for f in fr)
    assert kap.count(1.0) == 32 and kap.count(2.0) == 48 and abs(kap[-1] - 4 * np.sqrt(2)) < 1e-9
    for f in fr:
        assert abs(abs(f["angle_over_beta"]) - 2 * f["kappa"]) < 1e-12 and abs(f["angle"] - 0.5 * f["angle_over_beta"]) < 1e-12
        assert f["sign"] in (-1, 1) and f["pivot"] not in f["controls"]
        assert all(n in {"x", "cx", "ccx", "z", "cz", "ccz", "h", "ch"} for n, _ in f["frame_gates"])
        assert all(max(q) < 16 for _, q in f["frame_gates"])
    assert [f["frame_gates"] for f in C.pair_frames(2.0)] == [f["frame_gates"] for f in fr]
    assert abs(max(abs(f["angle_over_beta"]) for f in fr) - 8 * np.sqrt(2)) < 1e-9


def test_frame_images_are_basis_states_and_controls_sufficient():
    """For three pairs (one per kappa class): F u, F v are the basis states |0>, |1_j>, and the controlled rotation of the
    frame acts as the exact two-level rotation on the full 1296 block."""
    codes = O.inner_codes()
    pairs = O.bright_pairs()
    fr = _frames()
    picks = [0, 40, 80]
    for i in picks:
        f = fr[i]
        u, v, k = pairs[i]
        assert abs(k - f["kappa"]) < 1e-12
        qc = C.build_UB(0.7)          # only used for ancilla count
        n_anc = qc.num_qubits - 16
        ops = C._pair_ops({**C.pair_frames(0.7)[i]}, list(range(16, 16 + n_anc)))
        from qiskit import QuantumCircuit

        sub = QuantumCircuit(16 + n_anc)
        for name, qs, params in ops:
            getattr(sub, name)(*params, *qs)
        b = run_batch(sub, codes)
        M, leak = encoded_block(b, codes, len(codes), (1 << 16) - 1)
        th = 0.7 * k
        V = np.eye(1296, dtype=complex) + (np.cos(th) - 1) * (np.outer(u, u) + np.outer(v, v)) + 1j * np.sin(th) * (np.outer(u, v) + np.outer(v, u))
        assert leak.max() < 1e-20 and np.abs(M - V).max() < 1e-12


@functools.lru_cache(maxsize=1)
def _ub():
    return C.build_UB(0.61)


def test_build_UB_columns_match_inner_target_and_ancillas_clean():
    qc = _ub()
    rng = np.random.default_rng(20261104)
    codes = O.inner_codes()
    bright = np.flatnonzero(np.abs(O.inner_target("UB", None, 0.61) - np.eye(1296)).max(axis=0) > 1e-9)
    pick = np.unique(np.concatenate([rng.choice(1296, 20, replace=False), rng.choice(bright, 20, replace=False)]))
    b = run_batch(qc, codes[pick])
    # all output keys have zero ancilla bits and lie in the code space
    assert not np.any(b.keys >> 16)
    M, leak = encoded_block(b, codes, len(pick), (1 << 16) - 1)
    V = O.inner_target("UB", None, 0.61)[:, pick]
    assert leak.max() < 1e-20 and np.abs(M - V).max() < 1e-10
    assert {i.operation.name for i in qc.data} <= ALLOWED and qc.global_phase == 0


def test_build_UB_registers_metadata_and_outer_untouched():
    qc = _ub()
    assert [r.name for r in qc.qregs] == ["d", "anc"] and qc.qregs[0].size == 16
    md = qc.metadata
    assert md["kind"] == "UB" and md["beta"] == 0.61 and md["n_pairs"] == 81
    cnt = md["angle_over_beta_abs_counts"]
    assert cnt["2"] == 32 and cnt["4"] == 48 and sorted(cnt.values()) == [1, 32, 48]
    qo = C.build_UB(0.61, with_outer=True)
    assert [r.name for r in qo.qregs] == ["d", "o", "anc"] and qo.num_qubits == 48 + (qc.num_qubits - 16)
    used = {qo.find_bit(q).index for inst in qo.data for q in inst.qubits}
    assert not used & set(range(16, 48))
    assert [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data] == \
           [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in C.build_UB(0.23).data]


def test_build_step_structure_and_order_check():
    for order in (1, 2):
        qc = C.build_step(0.37, 0.61, order=order)
        assert qc.metadata["kind"] == "step" and qc.metadata["order"] == order and qc.metadata["alpha"] == 0.37
        p_angles = [float(i.operation.params[0]) for i in qc.data if i.operation.name == "p"]
        assert np.allclose(p_angles, [-0.75 * 0.37 * (0.5 if order == 2 else 1.0)] * (4 if order == 1 else 8))
    q1 = C.build_step(0.37, 0.61, order=1)
    assert [i.operation.name for i in q1.data[:12]] == ["cx", "p", "cx"] * 4      # electric layer first
    q2 = C.build_step(0.37, 0.61, order=2)
    assert [i.operation.name for i in q2.data[-12:]] == ["cx", "p", "cx"] * 4
    with pytest.raises(ValueError, match="order"):
        C.build_step(0.1, 0.1, order=3)
    qo = C.build_step(0.37, 0.61, order=1, with_outer=True)
    assert [r.name for r in qo.qregs] == ["d", "o", "anc"]
