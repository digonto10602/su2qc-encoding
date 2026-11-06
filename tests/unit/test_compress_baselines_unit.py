"""Unit tests for su2plaq.compress.{baselines,passes,round} (M2 step 2.5)."""
import json
import math

import pytest
from qiskit import QuantumCircuit

from su2plaq.compress import archive as A
from su2plaq.compress import baselines as BL
from su2plaq.compress import builder as B
from su2plaq.compress import evaluate as E
from su2plaq.compress import passes as PS
from su2plaq.compress import round as R
from su2plaq.compress.spec import TaskSpec, default_spec

STEP = default_spec("twelve", "step")
UE = default_spec("twelve", "UE")
UB = default_spec("twelve", "UB")


def skeleton_of(qc):
    return E.skeleton(qc)


# ------------------------------------------------------------------------------------------------ general circuit / program
@pytest.mark.parametrize("spec", [STEP, UE, UB, TaskSpec(**{**STEP.to_dict(), "order": 2})])
def test_general_circuit_matches_the_spec_kind(spec):
    qc = BL.general_circuit(spec)
    assert [r.name for r in qc.qregs][:2] == ["d", "o"] and qc.metadata["kind"] == spec.kind
    assert (qc.num_qubits == 28) == (spec.kind == "UE")


@pytest.mark.parametrize("spec", [UE, UB])
def test_generated_program_rebuilds_the_circuit_at_every_angle_pair(spec, tmp_path):
    src = BL.program_source(lambda s: BL.general_circuit(s), spec, summary="x")
    f = tmp_path / "000-g.py"
    f.write_text(src)
    assert B.parse_program_header(src)["family"] == "seed"
    mod = E.load_program(f)
    for a, b in [(spec.alpha, spec.beta), *spec.alt_angles, (0.123, 0.456)]:
        s = spec.with_angles(a, b)
        got, ref = mod.build(s).circuit(), BL.general_circuit(s)
        assert skeleton_of(got) == skeleton_of(ref)
        for gi, gr in zip(got.data, ref.data):
            assert all(abs(float(x) - float(y)) < 1e-12 for x, y in zip(gi.operation.params, gr.operation.params))
    r = E.evaluate_program(f, spec, "trial")
    assert r.valid


def test_program_generator_refuses_angle_dependent_skeletons():
    def fn(spec):
        qc = QuantumCircuit(28)
        if spec.alpha > 0.5:
            qc.x(0)
        qc.rz(spec.alpha, 0)
        return qc

    with pytest.raises(ValueError, match="skeleton"):
        BL.program_source(fn, STEP, summary="x")

    def nonlinear(spec):
        qc = QuantumCircuit(28)
        qc.rz(spec.alpha ** 2, 0)
        return qc

    with pytest.raises(ValueError, match="linear|non-zero"):
        BL.program_source(nonlinear, STEP, summary="x")


def test_committed_general_program_has_not_drifted():
    path = BL.general_program_path(STEP)
    assert path.name == "000-general.py" and path.exists()
    assert path.read_text() == BL.program_source(lambda s: BL.general_circuit(s), STEP, summary=f"the reference circuit of the "
        f"{STEP.encoding} encoding ({STEP.kind}) expressed through the Builder; every angle is a linear function of spec.alpha / spec.beta.")


# ------------------------------------------------------------------------------------------------ polish
def test_cancel_and_merge_rules():
    f = PS._cancel_and_merge
    assert f([("x", (), (0,)), ("x", (), (0,))])[0] == []
    assert f([("h", (), (0,)), ("x", (), (1,)), ("h", (), (0,))])[0] == [("x", (), (1,))]          # x on another qubit is irrelevant
    assert f([("h", (), (0,)), ("cx", (), (0, 1)), ("h", (), (0,))])[0] != []                       # blocked by the cx
    assert f([("s", (), (0,)), ("sdg", (), (0,))])[0] == [] and f([("t", (), (0,)), ("tdg", (), (0,))])[0] == []
    assert f([("s", (), (0,)), ("s", (), (0,))])[0] != []                                           # s s is z, not identity
    assert f([("cz", (), (0, 1)), ("cz", (), (1, 0))])[0] == []                                     # symmetric
    assert f([("cx", (), (0, 1)), ("cx", (), (1, 0))])[0] != []                                     # different roles
    assert f([("rccx", (), (0, 1, 2)), ("rccx", (), (0, 1, 2))])[0] == []
    merged, nc, nm = f([("rz", (0.25,), (0,)), ("rz", (0.5,), (0,)), ("cp", (0.1,), (0, 1)), ("cp", (0.2,), (0, 1))])
    assert nm == 2 and merged[0][1] == (0.75,) and abs(merged[1][1][0] - 0.3) < 1e-15
    nested = f([("h", (), (0,)), ("x", (), (0,)), ("x", (), (0,)), ("h", (), (0,))])
    assert nested[0] == [] and nested[1] == 4                                                       # cascade to a fixpoint


def test_polish_keeps_the_input_when_nothing_is_better_and_improves_when_it_can():
    from qiskit import QuantumRegister

    ue = BL.general_circuit(UE)
    out, log = PS.polish(ue, UE)
    assert out is ue and isinstance(log, list)
    worse = ue.copy()
    worse.cx(2, 5)
    worse.cx(2, 5)                       # a redundant CX pair: removing it is strictly better and exact
    out, log = PS.polish(worse, UE)
    assert out is not worse and out.count_ops().get("cx", 0) == 0 and any("accepted" in x for x in log)
    assert all(x.split(":")[0] in ("cancel_inverse_pairs", "merge_adjacent_rotations") for x in log)    # Lean rule names
    assert E.evaluate_circuit(out, UE, "trial").valid
    bad = ue.copy()
    bad.sx(0)
    assert PS.polish(bad, UE)[0] is bad


# ------------------------------------------------------------------------------------------------ Qiskit L3
def test_qiskit_l3_is_allowed_gates_only_valid_and_not_costlier():
    from su2plaq.metrics.logical import logical_metrics

    l3 = BL.qiskit_l3(STEP, seed=12345)
    assert {i.operation.name for i in l3.data} <= B.BASIS and E._gate_violations(l3) == []
    assert E.evaluate_circuit(l3, STEP, "trial").valid
    assert logical_metrics(l3)["cx"] <= logical_metrics(BL.general_circuit(STEP))["cx"]
    assert logical_metrics(BL.qiskit_l3(STEP, seed=12345))["cx"] == logical_metrics(l3)["cx"]       # deterministic
    whole = BL.qiskit_l3_whole(STEP)
    assert {i.operation.name for i in whole.data} <= B.BASIS


# ------------------------------------------------------------------------------------------------ external seeds
def test_vendored_trotter_file_records_its_source_commit():
    d = json.loads(BL._TROTTER.read_text())
    assert set(d) == {"lean22", "lean22_v2"} and all(len(v["commit"]) == 40 and v["kind"] == "UB" for v in d.values())
    assert sum(1 for g in d["lean22_v2"]["gates"] if g[2] is not None) == 4


@pytest.mark.parametrize("source", ["lean22_v2", "lean22"])
@pytest.mark.parametrize("spec", [STEP, UB])
def test_lean_seeds_import_with_our_electric_layer_and_verify(source, spec):
    seed = BL.import_seed(spec, source)
    assert isinstance(seed, BL.SeedCircuit) and seed.can_be_parent and not seed.fixed_angle and seed.kind == spec.kind
    r = BL.evaluate_seed(spec, seed, "trial")
    assert r.valid, (source, spec.kind, r.reason)
    names = [i.operation.name for i in seed.qc.data]
    assert ("p" in names) == (spec.kind == "step")                    # our U_E (p gates) is prepended for the step only


def test_seed_import_reasons_and_fixed_angle_seed():
    assert isinstance(BL.import_seed(STEP, "spinnet15"), str)
    assert "no electric" in BL.import_seed(UE, "lean22_v2")
    with pytest.raises(ValueError):
        BL.import_seed(STEP, "nonsense")
    p = BL.import_seed(STEP, "paulo34")
    assert p.fixed_angle and p.beta == 1.0 and p.kind == "UB" and not p.can_be_parent and p.qc.num_qubits == 50


def test_seed_program_source_is_a_valid_angle_linear_program(tmp_path):
    src = BL.seed_program_source(STEP, "lean22_v2")
    f = tmp_path / "001-lean22_v2.py"
    f.write_text(src)
    assert B.parse_program_header(src)["family"] == "seed"
    assert E.evaluate_program(f, STEP, "trial").valid


# ------------------------------------------------------------------------------------------------ Clifford+T re-verification
def test_verify_synthesised_uses_synth_tolerances_and_is_ok_for_the_reference():
    v = BL.verify_synthesised(BL.general_circuit(UE), UE)
    assert v["ok"] and v["n_rot"] == 4 and v["tolerances"]["tol_err"] == 4 * UE.eps + 1e-9
    assert v["verdict"].tolerances == v["tolerances"] and v["verdict"].engine == "sparse" and v["t_total"] > 0
    wrong = QuantumCircuit(*BL.general_circuit(UE).qregs)
    wrong.p(0.3, 2)
    assert not BL.verify_synthesised(wrong, UE)["ok"]


# ------------------------------------------------------------------------------------------------ round
PROG = '''"""SUMMARY: ue.

DISCOVERY: diagonal in the j bits.
"""
FAMILY = "F9"
PARENT = None

from su2plaq.compress.builder import Builder


def build(spec):
    b = Builder(spec)
    d = b.reg("d")
    for l in range(4):
        b.p(-0.75 * spec.alpha, d[3 * l + 2])
    return b
'''


def test_run_round_with_proposals_archives_logs_and_is_idempotent(tmp_path):
    f = tmp_path / "compress" / "programs" / "twelve" / "F9" / "003-ue.py"
    f.parent.mkdir(parents=True)
    f.write_text(PROG)
    bad = f.with_name("004-bad.py")
    bad.write_text(PROG.replace("-0.75", "+0.75"))
    info = R.run_round("twelve", "UE", 1, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(f), str(bad)])
    assert info["round"] == 1 and info["n_valid"] == 1 and info["n_invalid"] == 1 and info["entries"] == ["r01-F9-003"]
    rj = json.loads((tmp_path / "results" / "compress" / "twelve" / "round-001.json").read_text())
    assert rj["entries"] == ["r01-F9-003"] and rj["invalid"][0]["reason"] == "error" and "git_commit" in rj["provenance"]
    assert rj["synthesis_verification"]["ok"] is True and rj["synthesis_verification"]["entry"] == "r01-F9-003"
    assert A.Archive.load("twelve", root=tmp_path).best().program_path == "compress/programs/twelve/F9/003-ue.py"   # relocatable
    att = [json.loads(x) for x in (tmp_path / "compress" / "attempts" / "twelve.jsonl").read_text().splitlines()]
    assert [a["valid"] for a in att] == [True, False]
    assert "diagonal in the j bits" in (tmp_path / "compress" / "discoveries" / "twelve.md").read_text()
    arch = A.Archive.load("twelve", root=tmp_path)
    assert [e.id for e in arch.entries()] == ["r01-F9-003"] and arch.best().key[0] == 0
    # default proposals skip programs that are already archived
    info2 = R.run_round("twelve", "UE", 2, evaluate=True, dry_run=True, root=tmp_path)
    assert info2["entries"] == [] and info2["n_invalid"] == 1          # only the (still invalid) 004 program is re-evaluated


def test_round_cli_argument_check():
    with pytest.raises(SystemExit):
        R.main(["--encoding", "twelve"])
    with pytest.raises(SystemExit):
        R.main(["--seed", "--round", "1"])
