"""M8-E, S, H, L — the LSH compression loop on the shared machinery (prompts/401 §1-§3; prompts/008 §3, §6; prompts/104 as the model).

`lsh` is an entry of the shared encoding registry (prompts/008 D11): no shim, no patched attribute; the stock worker, CLIs,
round, brief and report code serve it.  `su2plaq.lsh.loop` only holds the registry hooks (seeds, spec text, Lean hook,
angle-linearity) and the loop bookkeeping (round 0 externals, stop state).  Task: U = U_B(beta) U_E(alpha) on the 24-qubit LSH
register (12 data + 12 read-only outer qubits), exact on the 433 physical codes, same skeleton at three angle pairs.

Planner measurements (scratch/planner/m8/proto_m8_seeds.py, shared evaluator, hand registration in the prototype process only):
general (94, 598, 880, 31); wrapped spin-network headline (71, 1118, 2276, 25) = round-0 best; full-mode evaluation 0.6-1.4 s;
robust metrics 0.5-3.4 s per program; Lean certificate of the wrapped headline 1.3 s (175 gates, 25 qubits, base (4, 8)).

Tolerances: `total_error` <= 1e-10 and Gauss <= 1e-10 (the loop's exact-angle rule, prompts/004 + prompts/008 §5); oracle vs
encoding target 1e-12 (the same computation twice); angle-linearity 1e-9; wall limits as in prompts/104 §4 (trial 30 s, seed
round 600 s, Lean 900 s).  Everything runs under `tmp_path`; the real archive is read only by test_lsh_m8_gate.py.
PENDING rule: a missing module / attribute / registry entry fails with `PENDING:` (conftest + `_api.api`)."""
from __future__ import annotations

import functools
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import CircuitInstruction

from tests.acceptance._api import api

ROOT = pathlib.Path(__file__).resolve().parents[3]
ENC, KIND = "lsh", "step"
NOMINAL = (0.37, 0.61)
ALTS = ((0.91, 0.23), (1.70, 1.00))
TOL = 1e-10
LSH_FILES = ["encodings/lsh.py", "lsh/operators.py", "exact/spinnet.py", "exact/compare.py", "lsh/walk.py", "circuits/lsh.py"]
HOOKS = ("general_circuit", "seed_candidates", "import_seed", "lean_certify", "render_spec", "brief_note", "angle_linear")
SEED_FILES = {"general": "000-general.py", "wrap_pairs9": "001-wrap_pairs9.py", "wrap_flags4": "002-wrap_flags4.py",
              "wrap_flags5": "003-wrap_flags5.py", "wrap_flags6": "004-wrap_flags6.py", "wrap_sn_headline": "005-wrap_sn_headline.py",
              "wrap_sn_r05F3": "006-wrap_sn_r05F3.py", "wrap_sn_r02F5": "007-wrap_sn_r02F5.py",
              "general+polish": "010-general_polish.py", "qiskit_l3": "011-qiskit_l3.py"}
SEED_CX = {"general": 94, "wrap_pairs9": 74, "wrap_flags4": 84, "wrap_flags5": 82, "wrap_flags6": 76, "wrap_sn_headline": 71,
           "wrap_sn_r05F3": 72, "wrap_sn_r02F5": 74}                      # planner prototype; test_lsh_m8_seeds.py::EXPECTED
ROUND0_BEST = ("wrap_sn_headline", 71)
PAULO_WRAPPED = {"beta": -0.05, "cx": 108}                               # METHODS-lsh L8: equals U_B(-0.05) in the LSH gauge; 68 + 40 CX
ANGLE_SET_SEED, ANGLE_SET_N = 20261107, 20                               # prompts/104 §11 E3 = prompts/008 §6
ANGLE_RANGES = ((0.05, 2.0), (0.05, 1.2))
# facts of the proposer spec: name -> value (all kernel-checked, `decide`); files under lean/Su2Plaq/LSH/
REQUIRED_FACTS = {
    "card_site_codes": 5, "card_inner_codes": 47, "card_bright_codes": 16, "card_dark_codes": 31, "card_states_lsh": 433,
    "card_bright_states": 256, "site_valid_list": [0, 1, 2, 4, 6], "inner_codes_from_rules": True, "coupling_zero_iff_dark": True,
    "dark_site_is_and": True, "coupling_by_y_weight": {"0": -4, "1": 2, "2": -1}, "link_bit_two_ways": True,
    "move_per_site": {"w0": 1, "w1": 6}, "y_parity_invariant": True, "eight_differences": 8, "transcode_into_spinnet": True,
    "coupling_matches_spinnet": True,
}
NUMERICAL_FACTS = {"n_outer_site_patterns": 305, "transcoder_overhead": {"cx": 40, "t_fixed": 32}}


# ---------------------------------------------------------------------------------------------------- helpers
def _registry():
    return api("su2plaq.encodings.registry")                 # PENDING until prompts/008 step B1


def _info():
    info = _registry().lookup(ENC)
    if info is None:
        pytest.fail("PENDING: encoding 'lsh' is not in the registry (prompts/401 step 8.2, inside the prompts/008 window)", pytrace=False)
    return info


@functools.lru_cache(maxsize=None)
def _spec():
    _info()
    return api("su2plaq.compress.spec:default_spec")(ENC, KIND)


def _loop():
    _info()
    return api("su2plaq.lsh.loop")


def _enc():
    return api("su2plaq.compress.spec:get_encoding")(ENC)


def _robust():
    return api("su2plaq.compress.robust")                     # PENDING until prompts/008 step B6


def _err(v) -> float:
    if not hasattr(v, "total_error"):
        pytest.fail("PENDING: Verdict has no field total_error (prompts/008 step B2)", pytrace=False)
    return v.total_error


def _general_qc(alpha=NOMINAL[0], beta=NOMINAL[1], order=1):
    return api("su2plaq.circuits.lsh:build_step")(alpha, beta, order, with_outer=True)


def _with_extra(qc: QuantumCircuit, fn) -> QuantumCircuit:
    out = qc.copy()
    fn(out)
    return out


def _perturb_first_rotation(qc: QuantumCircuit, delta: float) -> QuantumCircuit:
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
            new_c = next(q for q in range(12) if q not in (c, t))
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


def _derived_program(gp: pathlib.Path, *, prologue: str = "", epilogue: str = "") -> str:
    """A proposer-style rewrite of the generated gate-list program `000-general.py`: `prologue` right after `def build(spec):`,
    `epilogue` right before `return b`.  Like every proposer program it reaches the circuit only through the gate list and the
    whitelisted `su2plaq.compress.{oracle,builder,spec}` modules."""
    text = gp.read_text()
    assert text.count("def build(spec):\n") == 1 and text.rstrip().endswith("return b"), gp
    for banned in ("su2plaq.circuits", "su2plaq.lsh", "su2plaq.spinnet"):
        assert banned not in text, f"the general program must be a plain gate list ({banned})"
    head, body = text.split("def build(spec):\n", 1)
    body, tail = body.rsplit("    return b", 1)
    return head + "def build(spec):\n" + prologue + body + epilogue + "    return b" + tail


def _angle_set() -> np.ndarray:
    rng = np.random.default_rng(ANGLE_SET_SEED)
    a = rng.uniform(*ANGLE_RANGES[0], ANGLE_SET_N)
    b = rng.uniform(*ANGLE_RANGES[1], ANGLE_SET_N)
    return np.c_[a, b]


def _fresh(code: str, timeout: float = 600.0) -> dict:
    """Run `code` in a fresh interpreter (PYTHONPATH = src only, no hook variables); the last stdout line is JSON."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SU2PLAQ_")}
    env.update({"PYTHONPATH": str(ROOT / "src"), "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1"})
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout, env=env, cwd=str(ROOT))
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads(p.stdout.strip().splitlines()[-1])


ORACLE_PROLOGUE = '''    from su2plaq.compress import oracle
    v = oracle.element(spec, 0, 0)
    assert abs(v) <= 1.0 + 1e-12
'''
# nominal beta = 0.61 > 0.5, first alternate 0.23: a gate pair whose presence depends on beta; qubit 24 = first ancilla
SKELETON_EPILOGUE = '''    if spec.beta > 0.5:
        b.x(24)
        b.x(24)
'''
WRITING_PROGRAM = '''"""SUMMARY: a program that tries to write a file through pathlib (must be refused by the worker's audit guard).

"""
FAMILY = "T"
PARENT = None

from su2plaq.compress.builder import Builder
import su2plaq.compress.builder as BB


def build(spec):
    BB.pathlib.Path(%(marker)r).write_text("x")
    b = Builder(spec)
    return b
'''
_PROBE_PROGRAM = '''"""SUMMARY: probe of prompts/401 (m8): an empty Builder plus one oracle query made inside the sandboxed worker.

"""
FAMILY = "T"
PARENT = None

from su2plaq.compress.builder import Builder
from su2plaq.compress import oracle


def build(spec):
    v = oracle.element(spec, 0, 0)
    assert abs(v) <= 1.0 + 1e-12
    return Builder(spec)
'''
_FRESH = r'''
import json, os, sys, tempfile
from su2plaq.compress import baselines as BL, brief as BR, evaluate as E, oracle, round as RD, spec as S
from su2plaq.compress.builder import Builder
from su2plaq.encodings import base, registry
from su2plaq.evaluate import evaluator as EV
PROGRAM = %(program)r
spec = S.default_spec("lsh", "step")
enc = S.get_encoding("lsh")
V = oracle.target(spec)
b = Builder(spec)
specs = [spec] + [spec.with_angles(a, c) for a, c in spec.alt_angles]
circuits, disc = E._build_in_subprocess(PROGRAM.encode(), specs, E.BUILD_TIMEOUT_S)
out = {"enc_name": enc.name, "angles": [spec.alpha, spec.beta], "shape": list(V.shape), "n_reg": len(b.reg("d")),
       "n_data": enc.n_data, "n_outer": enc.n_outer, "n_circuits": len(circuits), "qubits": [c.num_qubits for c in circuits],
       "cap": spec.peak_qubit_cap(),
       "hook_module_imported_by_shared_code": "su2plaq.lsh.loop" in sys.modules}
def snap():
    return {"E._build_in_subprocess": id(E._build_in_subprocess), "E._one_verdict": id(E._one_verdict), "E._worker": id(E._worker),
            "E.evaluate_circuit": id(E.evaluate_circuit), "E.evaluate_program": id(E.evaluate_program),
            "EV.evaluate": id(EV.evaluate), "RD._certify": id(RD._certify), "RD.run_round": id(RD.run_round),
            "BL.general_circuit": id(BL.general_circuit), "BL.import_seed": id(BL.import_seed),
            "S.get_encoding": id(S.get_encoding), "S.default_spec": id(S.default_spec), "S.TaskSpec.render": id(S.TaskSpec.render),
            "S.TaskSpec.peak_qubit_cap": id(S.TaskSpec.peak_qubit_cap), "BR.make_brief": id(BR.make_brief),
            "BR.make_ideation_brief": id(BR.make_ideation_brief), "ALLOWED_PROJECT_IMPORTS": sorted(E.ALLOWED_PROJECT_IMPORTS),
            "NOMINAL_ANGLES": sorted(base.NOMINAL_ANGLES.items()), "registry": sorted(registry.names()),
            "PYTHONPATH": os.environ.get("PYTHONPATH"), "hook_vars": sorted(k for k in os.environ if k.startswith("SU2PLAQ_"))}
before = snap()
from su2plaq.lsh import loop as LL
LL.structure_facts(); spec.render(); LL.general_circuit(spec); LL.brief_note("lsh", "step")
after = snap()
out["changed"] = sorted(k for k in before if before[k] != after[k])
print(json.dumps(out))
'''


# ---------------------------------------------------------------------------------------------------- 8.2 registry
def test_M8_E1_registry_entry_lsh():
    """The registry entry of `lsh` (prompts/401 §2.1): lazy factory, kinds, stamp 'encoding' (an edit of an LSH file makes the
    LSH archive stale, nothing else), the LSH evaluator file list, the seven hooks resolving to callables of `su2plaq.lsh.loop`
    (which is not itself a hashed file), the generic headline rule and the stock tool commands."""
    info = _info()
    R = _registry()
    P = api("su2plaq.compress.provenance")
    base = api("su2plaq.encodings.base")
    src = ROOT / "src" / "su2plaq"
    assert info.name == ENC and info.factory == "su2plaq.encodings.lsh:LSH" and ENC in R.names()
    assert KIND in info.kinds and info.loop_kind == KIND and info.stamp == "encoding" and info.gauss_in_loop is True
    assert info.prune_fraction is None and info.verdict is None and info.worker_warmup is None
    assert list(info.evaluator_files) == LSH_FILES and all((src / f).is_file() for f in LSH_FILES)
    for field in HOOKS:
        dotted = getattr(info, field)
        assert isinstance(dotted, str) and dotted.startswith("su2plaq.lsh.loop:"), (field, dotted)
        assert callable(R.resolve(dotted)), field
    assert info.headline is None and info.tools is None and info.structure_json == "compress/specs/lsh-structure.json"
    assert base.NOMINAL_ANGLES[ENC] == NOMINAL
    shared = [src / f for f in P.EVALUATOR_FILES if (src / f).exists()]
    files = [pathlib.Path(f) for f in P.evaluator_files(ENC)]
    assert files == shared + [src / f for f in LSH_FILES]
    h = P.code_hash_for(ENC)
    assert len(h) == 64 and h == P.code_hash(files=files) and P.stamp_hash(ENC) == h and h != P.code_hash()
    assert P.code_hash_for("twelve") == P.code_hash()
    assert tuple(api("su2plaq.lsh.loop:LSH_EVALUATOR_FILES")) == tuple(LSH_FILES)


def test_M8_E2_fresh_process_stock_worker_and_no_patching():
    """In a fresh interpreter that imports only shared modules, default_spec / get_encoding / oracle / Builder and the STOCK
    build worker know `lsh` (probe program with an oracle query inside the sandbox, three angle pairs) without importing the
    hook module; importing and using `su2plaq.lsh.loop` afterwards changes no attribute of a shared module, no registry
    content, no import whitelist and no environment variable."""
    _info()
    d = _fresh(_FRESH % {"program": _PROBE_PROGRAM})
    assert d["enc_name"] == ENC and tuple(d["angles"]) == NOMINAL and d["shape"] == [433, 433]
    assert d["n_reg"] == d["n_data"] == 12 and d["n_outer"] == 12 and d["n_circuits"] == 3 and d["qubits"] == [24] * 3
    assert d["cap"] == 12 + 12 + 32
    assert d["hook_module_imported_by_shared_code"] is False
    assert d["changed"] == [], d["changed"]


def test_M8_S0_spec_oracle_builder_lsh(tmp_path):
    """default_spec / oracle / Builder for `lsh` with the nominal angles, alternates and tolerances of prompts/001 §8; the
    rendered spec is the LSH one: register layout, the Abelian Gauss law, the kernel-checked facts, the headline rule and
    the stock tool commands."""
    spec = _spec()
    assert spec.encoding == ENC and spec.kind == KIND and spec.order == 1
    assert (spec.alpha, spec.beta) == NOMINAL and tuple(spec.alt_angles) == ALTS
    assert spec.tol_err == TOL and spec.tol_gauss == TOL and spec.eps == 1e-6 and spec.peak_qubit_cap() == 56
    enc = _enc()
    assert enc.name == ENC and enc.n_data == 12 and enc.n_outer == 12
    oracle = api("su2plaq.compress.oracle")
    V = oracle.target(spec)
    assert V.shape == (433, 433) and np.abs(V - enc.target("step", *NOMINAL, order=1)).max() <= 1e-12
    assert abs(oracle.element(spec, 3, 3) - V[3, 3]) <= 1e-12
    b = api("su2plaq.compress.builder").Builder(spec)
    assert b.reg("d") == list(range(12)) and b.reg("o") == list(range(12, 24)) and b.alloc(1, "w") == [24]
    text = spec.render()
    assert text == api("su2plaq.lsh.loop:render_spec")(spec)
    title = _robust().HEADLINE_RULE_SECTION.strip().splitlines()[0]
    for needle in ("lsh", "433", "47", "python -m su2plaq.compress.run_candidate", "python -m su2plaq.compress.oracle", "--encoding lsh",
                   "Proved structure (Lean)", "inner_codes_from_rules", "coupling_by_y_weight", "Abelian Gauss law", "l_pn", "l_nv",
                   "l_vp", "read-only", "0.37", "0.61", "rccx", "1e-10", "DISCOVERY", title):
        assert needle in text, needle
    for banned in ("su2plaq.spinnet.loop", "wrap_sn_headline", "r02-F1-002"):        # the spec states the task, not the seeds
        assert banned not in text, banned
    p = spec.write(path=tmp_path / "lsh-step.md")
    assert pathlib.Path(p).read_text() == text


# ---------------------------------------------------------------------------------------------------- 8.3 programs, worker
def test_M8_S2_general_program_worker_and_sandbox(tmp_path):
    """compress/programs/lsh/seed/000-general.py: a plain gate list, angle-linear image of build_step, valid in full mode with
    the key of the circuit it came from; a program calling the oracle inside build() is valid; importing the reference
    circuit or the LSH walk module is refused by the static scan; a pathlib write is refused by the worker's audit guard."""
    LL = _loop()
    spec = _spec()
    E = api("su2plaq.compress.evaluate"); M = api("su2plaq.compress.metrics")
    gp = LL.general_program_path(spec, root=tmp_path)
    assert gp.name == "000-general.py" and gp.read_text().lstrip().startswith('"""SUMMARY:')
    assert gp.parent == tmp_path / "compress" / "programs" / ENC / "seed"
    r = E.evaluate_program(str(gp), spec, mode="full")
    assert r.valid and r.reason == "ok" and r.skeleton_equal and len(r.verdicts_alt) == 2 and all(v.ok for v in r.verdicts_alt)
    assert _err(r.verdict) <= TOL and r.verdict.gauss_residual <= TOL and r.verdict.certified and r.verdict.outer_bits_read == 0
    ref = M.metrics(_general_qc(), spec, measured=True)
    assert tuple(M.key(r.metrics)) == tuple(M.key(ref)) and r.metrics["n_rot"] == 8 and r.metrics["cx"] == SEED_CX["general"]
    qc = E.load_program(str(gp)).build(spec).circuit()
    for inst in qc.data:
        if inst.operation.params:
            th = float(inst.operation.params[0])
            assert _rational_multiple(th, spec.alpha) or _rational_multiple(th, spec.beta), (inst.operation.name, th)
    t0 = time.time()
    ro = E.evaluate_program(str(_program(tmp_path, "001-oracle", _derived_program(gp, prologue=ORACLE_PROLOGUE))), spec, mode="trial")
    assert ro.valid and ro.reason == "ok", (ro.reason, ro.message)
    assert time.time() - t0 <= 30
    for k, mod in enumerate(("su2plaq.circuits.lsh", "su2plaq.lsh.walk", "su2plaq.lsh.loop")):
        bad = _derived_program(gp, prologue=f"    import {mod}\n")
        ri = E.evaluate_program(str(_program(tmp_path, f"00{k + 2}-import", bad)), spec, mode="trial")
        assert not ri.valid and ri.reason == "contract" and mod in ri.message, (mod, ri.reason, ri.message)
    marker = tmp_path / "MARKER-should-not-exist.txt"
    writer = WRITING_PROGRAM % {"marker": str(marker)}
    E._scan_source(writer)                    # passes the static scan on purpose: only the audit guard is under test
    rw = E.evaluate_program(str(_program(tmp_path, "005-writer", writer)), spec, mode="trial")
    assert not rw.valid and rw.reason == "build_error", (rw.reason, rw.message)
    assert "PermissionError" in rw.message and "write" in rw.message.lower(), rw.message
    assert not marker.exists()


def test_M8_S5_evaluator_rejections_on_lsh(tmp_path):
    """The shared evaluator's rules act on the LSH register: wrong gate, dirty ancilla, angle error 1e-6, outer write, control
    change are invalid; a beta-dependent skeleton is rejected in full mode with reason 'skeleton'; a 63-qubit circuit is
    refused before simulation."""
    LL = _loop()
    spec = _spec()
    E = api("su2plaq.compress.evaluate")
    qc = _general_qc()
    assert E.evaluate_circuit(qc, spec, mode="trial").valid
    last = qc.num_qubits - 1
    cases = {
        "wrong_gate": _with_extra(qc, lambda c: c.x(0)),
        "dirty_ancilla": _with_extra(qc, lambda c: c.x(last)),
        "angle_error": _perturb_first_rotation(qc, 1e-6),
        "outer_write": _with_extra(qc, lambda c: c.x(12)),
        "control_change": _move_first_cx_control(qc),
    }
    for name, bad in cases.items():
        r = E.evaluate_circuit(bad, spec, mode="trial")
        assert not r.valid and r.reason != "ok", name
    gp = LL.general_program_path(spec, root=tmp_path)
    r = E.evaluate_program(str(_program(tmp_path, "003-skel", _derived_program(gp, epilogue=SKELETON_EPILOGUE))), spec, mode="full")
    assert not r.valid and r.reason == "skeleton", (r.reason, r.message)
    wide = QuantumCircuit(QuantumRegister(12, "d"), QuantumRegister(12, "o"), QuantumRegister(39, "a"))
    rw = E.evaluate_circuit(wide, spec, mode="trial")
    assert not rw.valid and rw.reason != "ok"


# ---------------------------------------------------------------------------------------------------- 8.4 rounds
def test_M8_S3_seed_round_dry_run(tmp_path):
    """Round 0 under a temporary root (Lean off): ten seeds evaluated in full mode through the stock worker and archived with
    both hashes; the best is the wrapped spin-network headline at 71 CX; Paulo's 15-qubit file wrapped by the transcoder is
    an external row at beta = -0.05 (U_B only); the pinned sources are recorded; the stock report reads the round file."""
    LL = _loop()
    P = api("su2plaq.compress.provenance")
    t0 = time.time()
    info = LL.seed_round(root=tmp_path, lean=False, dry_run=True)
    assert time.time() - t0 <= 600
    assert info["round"] == 0 and info["n_valid"] == 10 and info["n_invalid"] == 0
    d = json.loads((tmp_path / "results" / "compress" / ENC / "round-000.json").read_text())
    cands = {c["label"]: c for c in d["candidates"]}
    assert set(cands) == set(SEED_FILES), set(cands)
    assert all(c["valid"] and c["key"] for c in cands.values())
    for label, cx in SEED_CX.items():
        assert cands[label]["key"][0] == cx, (label, cands[label]["key"])
    assert cands["general+polish"]["key"][0] <= SEED_CX["general"]
    keys = [tuple(c["key"]) for c in cands.values()]
    assert tuple(info["best_key"]) == min(keys) and min(keys) == tuple(cands[ROUND0_BEST[0]]["key"]) and min(keys)[0] == ROUND0_BEST[1]
    assert d["evaluator_sha256"] == P.stamp_hash(ENC) and d["encoding_sha256"] == P.code_hash_for(ENC)
    assert "git_commit" in d["provenance"]
    srcs = d["lsh"]["wrapped_sources"]
    assert {k: (v["path"], v["sha256"], v["spinnet_entry"]) for k, v in srcs.items()} == {k: tuple(v) for k, v in LL.WRAP_SOURCES.items()}
    ext = {x["source"]: x for x in d["external"]}
    assert "qiskit_l3_whole" in ext and "paulo15_wrapped" in ext
    pw = ext["paulo15_wrapped"]
    assert pw["valid"] is True and pw["fixed_angle"] is True and pw["kind"] == "UB" and abs(pw["beta"] - PAULO_WRAPPED["beta"]) <= 1e-15
    assert pw["op_norm_error"] <= TOL and pw["certified"] is True and pw["metrics"]["cx"] == PAULO_WRAPPED["cx"]
    A = api("su2plaq.compress.archive")
    arch = A.Archive.load(ENC, root=tmp_path, n_alt=2, strict=True)
    assert arch.rejected == [] and len([e for e in arch.entries() if e.valid]) == 10
    best = arch.best()
    assert best is not None and best.valid and tuple(best.key) == min(keys) and best.round == 0
    assert all(e.evaluator_sha256 == P.stamp_hash(ENC) and e.encoding_sha256 == P.code_hash_for(ENC) for e in arch.entries())
    for label, n in SEED_FILES.items():           # the windowed L3 circuit loses its rotations at alpha = beta = 0: it may stay
        if label != "qiskit_l3":                  # a circuit-valued baseline without a program file (measured, proto_m8_l3.py)
            assert (tmp_path / "compress" / "programs" / ENC / "seed" / n).exists(), n
    for n in ("005-wrap_sn_headline.py", "001-wrap_pairs9.py"):
        text = (tmp_path / "compress" / "programs" / ENC / "seed" / n).read_text()
        assert text.lstrip().startswith('"""SUMMARY:') and "su2plaq.spinnet" not in text and "su2plaq.lsh" not in text
    assert (tmp_path / "compress" / "attempts" / f"{ENC}.jsonl").exists()
    text = api("su2plaq.compress.report:report_table")(ENC, KIND, root=tmp_path)
    for col in ("qubits", "CX", "T_fixed", "N_rot", "T(1e-6)", "depth", "verdict", "Lean"):
        assert col in text
    for row in ("general", "wrap_sn_headline", "paulo15_wrapped"):
        assert row in text
    assert (tmp_path / "results" / "compress" / ENC / "summary.json").exists()
    spec = _spec()
    for src in ("paulo34", "lean22_v2", "spinnet15"):
        assert isinstance(LL.import_seed(spec, src), str)
    with pytest.raises(ValueError):
        LL.import_seed(spec, "no-such-seed")


def test_M8_S4_round_one_dry_run_briefs_and_stop_state(tmp_path):
    """After round 0: the stock briefs carry the stock commands with `--encoding lsh`, the headline rule and the LSH note
    (target = the full LSH register, native and transcoding families); a dry round 1 whose only proposal is the general
    program is evaluated and archived, does not improve the headline, and the stop state counts it."""
    LL = _loop()
    spec = _spec()
    BR = api("su2plaq.compress.brief")
    RB = _robust()
    LL.seed_round(root=tmp_path, lean=False, dry_run=True)
    st0 = LL.stop_state(root=tmp_path)
    assert [x["round"] for x in st0["rounds"]] == [0] and st0["rounds"][0]["improved"] is True
    assert st0["streak"] == 0 and st0["stop"] is False and st0["sessions"] == 0
    assert st0["rounds"][0]["record"]["cx"] == ROUND0_BEST[1]
    brief = pathlib.Path(BR.make_brief(ENC, KIND, 1, "F1", root=tmp_path))
    bt = brief.read_text()
    assert "Rewrite the parent" in bt and "python -m su2plaq.compress.run_candidate" in bt and "--encoding lsh" in bt
    assert RB.HEADLINE_RULE_SECTION.strip().splitlines()[0] in bt
    note = LL.brief_note(ENC, KIND)
    assert note.strip() and note.strip() in bt
    for needle in ("native", "transcoder", "Abelian Gauss law", "24-qubit"):
        assert needle in note, needle
    ib = pathlib.Path(BR.make_ideation_brief(ENC, KIND, root=tmp_path)).read_text()
    assert "compress/ideation/lsh.md" in ib and note.strip() in ib and "at least two" in note
    st = (tmp_path / "compress" / "specs" / f"{ENC}-{KIND}.md").read_text()
    assert "inner_codes_from_rules" in st and "47" in st
    gp = LL.general_program_path(spec, root=tmp_path)
    info = LL.run_round(1, evaluate=True, dry_run=True, root=tmp_path, proposals=[str(gp)], lean=False)
    assert info["round"] == 1 and info["n_valid"] + info["n_invalid"] >= 1
    d = json.loads((tmp_path / "results" / "compress" / ENC / "round-001.json").read_text())
    assert d["round"] == 1 and len(d["candidates"]) >= 1 and d["encoding_sha256"] == api("su2plaq.compress.provenance:code_hash_for")(ENC)
    lines = [json.loads(x) for x in (tmp_path / "compress" / "attempts" / f"{ENC}.jsonl").read_text().splitlines() if x.strip()]
    assert any(a["round"] == 1 for a in lines)
    st1 = LL.stop_state(root=tmp_path)
    assert [x["round"] for x in st1["rounds"]] == [0, 1] and st1["rounds"][1]["improved"] is False
    assert st1["streak"] == 1 and st1["stop"] is False and st1["sessions"] == 1
    assert st1["rounds"][1]["headline_id"] == st0["rounds"][0]["headline_id"]
    assert json.loads((tmp_path / "results" / "compress" / ENC / "stop.json").read_text())["streak"] == 1


# ---------------------------------------------------------------------------------------------------- 8.5 headline rule
def test_M8_H1_robust_metrics_and_hardenings(tmp_path):
    """The shared headline rule on `lsh` (prompts/008 §6): the locked 20-pair angle set; T(1e-6) and depth_CT at every pair
    equal the shared metrics of the reference circuit; robust key (CX, sum T, rho, sum depth, qubits).  Hardenings of audit
    302: the skeleton set contains the nominal pair (N2: a program that differs ONLY at the nominal pair has no robust key);
    rho = 0 only when the Lean exporter returns a certificate (N6: a 63-qubit circuit is `too_many_qubits`, rho = 1)."""
    LL = _loop()
    spec = _spec()
    RB = _robust()
    M = api("su2plaq.compress.metrics")
    assert RB.ANGLE_SET_SEED == ANGLE_SET_SEED
    A_set = np.asarray(RB.ANGLE_SET, dtype=float)
    assert A_set.shape == (ANGLE_SET_N, 2) and np.array_equal(A_set, _angle_set())
    gp = LL.general_program_path(spec, root=tmp_path)
    rm = RB.robust_metrics(ENC, KIND, gp, root=tmp_path)
    assert rm["skeleton_equal"] and len(rm["t_eps"]) == ANGLE_SET_N and len(rm["depth_ct"]) == ANGLE_SET_N
    assert rm["t_sum"] == sum(rm["t_eps"]) and rm["depth_sum"] == sum(rm["depth_ct"]) and rm["angle_linear"] is True
    assert tuple(rm["robust_key"]) == (rm["cx"], rm["t_sum"], 0, rm["depth_sum"], rm["qubits"]) and rm["cx"] == SEED_CX["general"]
    assert abs(rm["t_mean"] - rm["t_sum"] / ANGLE_SET_N) <= 1e-12
    for i in (0, 7, 19):
        a_i, b_i = (float(x) for x in A_set[i])
        ref = M.metrics(_general_qc(a_i, b_i), spec.with_angles(a_i, b_i), measured=True)
        assert rm["t_eps"][i] == ref["t_eps"] and rm["depth_ct"][i] == ref["depth_ct"], i
        assert rm["cx"] == ref["cx"] and rm["qubits"] == ref["qubits"]
    betas = A_set[:, 1]
    thr = float(np.sort(betas)[ANGLE_SET_N // 2])
    bad = _derived_program(gp, epilogue=f"    if spec.beta > {thr!r}:\n        b.x(24)\n        b.x(24)\n")
    rb = RB.robust_metrics(ENC, KIND, _program(tmp_path, "004-skel-range", bad), root=tmp_path)
    assert not rb["skeleton_equal"] and rb["robust_key"] is None
    only_nominal = _derived_program(gp, epilogue=(f"    if abs(spec.alpha - {NOMINAL[0]!r}) < 1e-12 and abs(spec.beta - {NOMINAL[1]!r}) < 1e-12:\n"
                                                  "        b.x(24)\n        b.x(24)\n"))
    rn = RB.robust_metrics(ENC, KIND, _program(tmp_path, "005-skel-nominal", only_nominal), root=tmp_path)
    assert not rn["skeleton_equal"] and rn["robust_key"] is None                      # audit 302 N2
    nonlin = _derived_program(gp, epilogue="    b.p(0.123, 24)\n    b.p(-0.123, 24)\n")
    rl = RB.robust_metrics(ENC, KIND, _program(tmp_path, "006-nonlinear", nonlin), root=tmp_path)
    assert rl["skeleton_equal"] and rl["angle_linear"] is False and rl["robust_key"][2] == 1 and rl["robust_key"] > rm["robust_key"]
    ok, why = LL.angle_linear(_general_qc(), spec)
    assert ok is True and isinstance(why, str)
    ok, why = LL.angle_linear(_with_extra(_general_qc(), lambda c: (c.p(0.123, 24), c.p(-0.123, 24))), spec)
    assert ok is False and why.startswith("non_linear_angle")
    wide = QuantumCircuit(QuantumRegister(12, "d"), QuantumRegister(12, "o"), QuantumRegister(39, "a"))
    ok, why = LL.angle_linear(wide, spec)
    assert ok is False and why == "too_many_qubits"                                 # audit 302 N6


@pytest.mark.slow
def test_M8_H2_headline_selection_on_seed_round(tmp_path):
    """Headline rule on a round-0 archive under tmp: `robust.headline('lsh', 'step')` is the valid entry with the smallest
    robust key (the wrapped spin-network headline, 71 CX); the ranking is complete and sorted; the cache, the report and the
    summary carry it next to the archive best."""
    LL = _loop()
    RB = _robust()
    LL.seed_round(root=tmp_path, lean=False, dry_run=True)
    A = api("su2plaq.compress.archive")
    arch = A.Archive.load(ENC, root=tmp_path, n_alt=2, strict=True)
    valid = {e.id: e for e in arch.entries() if e.valid}
    h = RB.headline(ENC, KIND, root=tmp_path)
    assert h["id"] in valid and h["archive_best"] == arch.best().id and h["robust_key"][0] == ROUND0_BEST[1]
    assert valid[h["id"]].program_path.endswith("005-wrap_sn_headline.py")
    ranked = [r for r in h["ranking"] if r["robust_key"] is not None]
    assert {r["id"] for r in h["ranking"]} | set(h["unrankable"]) == set(valid)
    keys = [tuple(r["robust_key"]) for r in ranked]
    assert keys == sorted(keys) and tuple(h["robust_key"]) == keys[0]
    for r in ranked[:3]:
        rm = RB.robust_metrics(ENC, KIND, tmp_path / valid[r["id"]].program_path, root=tmp_path)
        assert tuple(rm["robust_key"]) == tuple(r["robust_key"]) and rm["cx"] == valid[r["id"]].key[0]
    assert (tmp_path / "results" / "compress" / ENC / "robust.json").exists()
    text = api("su2plaq.compress.report:report_table")(ENC, KIND, root=tmp_path)
    assert "HEADLINE" in text and "GLOBAL BEST" in text and h["id"] in text
    summary = json.loads((tmp_path / "results" / "compress" / ENC / "summary.json").read_text())
    assert summary["headline"]["id"] == h["id"] and tuple(summary["headline"]["robust_key"]) == tuple(h["robust_key"])


# ---------------------------------------------------------------------------------------------------- 8.L Lean
def test_M8_L2_structure_facts_match_lean_sources(root, tmp_path):
    """The facts offered to the proposers: every `decide` fact names a theorem that exists in the named file under
    lean/Su2Plaq/LSH/ (no native_decide, no sorry there); values as locked in M7-A1 / M8-A1; measured-only facts are labelled
    `numerical`; the structure file and the rendered spec list them."""
    LL = _loop()
    if not (root / "lean" / "Su2Plaq" / "LSH" / "Facts.lean").exists():
        pytest.fail("PENDING: lean/Su2Plaq/LSH/Facts.lean missing (prompts/401 step 8.A1)", pytrace=False)
    facts = LL.structure_facts()
    by = {f["name"]: f for f in facts["facts"]}
    for name, value in REQUIRED_FACTS.items():
        assert name in by and by[name]["value"] == value and by[name]["proved_by"] == "decide", name
    for name, value in NUMERICAL_FACTS.items():
        assert name in by and by[name]["value"] == value and by[name]["proved_by"] == "numerical", name
    assert all(f["proved_by"] in ("decide", "numerical") for f in facts["facts"])
    for f in facts["facts"]:
        if f["proved_by"] != "decide":
            continue
        assert f["theorem"].startswith("Su2Plaq.LSH."), f["name"]
        short = f["theorem"].rsplit(".", 1)[1]
        src_path = root / f["file"]
        assert src_path.exists() and src_path.is_relative_to(root / "lean" / "Su2Plaq" / "LSH"), f["file"]
        src = src_path.read_text()
        assert re.search(rf"^theorem {re.escape(short)}\b", src, re.M), (f["name"], f["theorem"], f["file"])
        assert "native_decide" not in src and "sorry" not in src
    p = pathlib.Path(LL.write_structure(path=tmp_path / "lsh-structure.json"))
    assert json.loads(p.read_text())["facts"] == json.loads(json.dumps(facts["facts"]))
    text = _spec().render()
    for name in REQUIRED_FACTS:
        assert name in text, name


@pytest.mark.slow
def test_M8_L1_lean_hook_certifies_and_binds(tmp_path):
    """The registry's Lean hook `lsh.loop.lean_certify(circ, spec, timeout=, extra_provenance=, out_dir=)`: the general step
    and the wrapped spin-network headline are `certified` by `su2plaq_cert_lsh` with the binding fields inside the
    certificate; a circuit at -beta is `rejected` by the checker; a non-linear angle is `n_a`."""
    LL = _loop()
    spec = _spec()
    bind = {"entry_id": "r00-seed-005", "program_file_sha256": "cd" * 32}
    for qc in (_general_qc(), LL.seed_circuit("wrap_sn_headline", *NOMINAL)):
        t0 = time.time()
        r = LL.lean_certify(qc, spec, timeout=900.0, extra_provenance=bind, out_dir=tmp_path)
        assert time.time() - t0 <= 900
        assert r["status"] == "certified", (r["status"], r.get("reason"))
        c = json.loads(pathlib.Path(r["cert_path"]).read_text())
        assert c["provenance"]["entry_id"] == bind["entry_id"] and c["provenance"]["program_file_sha256"] == bind["program_file_sha256"]
        assert c["n_data"] == 12 and c["n_outer"] == 12 and len(c["states"]) == 433 and c["target"]["kind"] == "step"
        assert len(r.get("checker_sha256", "")) == 64
    r = LL.lean_certify(_general_qc(beta=-NOMINAL[1]), spec, timeout=900.0, extra_provenance=None, out_dir=tmp_path)
    assert r["status"] == "rejected" and r["reason"]
    r = LL.lean_certify(_perturb_first_rotation(_general_qc(), 0.123), spec, timeout=900.0, extra_provenance=None, out_dir=tmp_path)
    assert r["status"] == "n_a" and r["reason"].startswith("non_linear_angle")


@pytest.mark.slow
def test_M8_L3_theorem_file_writer(tmp_path):
    """`lsh.lean_export.write_theorem_file`: the certificate as a Lean string literal and `theorem <name> :
    Su2PlaqCert.LSH.checkJsonString certJson = true := by native_decide`; it elaborates with the standard axioms plus exactly
    one native axiom; a certificate whose states differ from the exporter's exact data is refused."""
    LE = api("su2plaq.lsh.lean_export")
    write_theorem_file = api("su2plaq.lsh.lean_export:write_theorem_file")
    P = api("su2plaq.lean.project")
    enc = api("su2plaq.encodings.lsh:LSH")()
    qc = api("su2plaq.circuits.lsh:build_UE")(NOMINAL[0], with_outer=True)
    r = LE.certify(qc, enc, "UE", NOMINAL[0], NOMINAL[1], 1, out_dir=tmp_path)
    assert r["status"] == "certified", (r["status"], r.get("reason"))
    out = pathlib.Path(write_theorem_file(r["cert_path"], "lsh_ue", tmp_path / "lsh-ue.lean", comment="entry test, program sha256 " + "0" * 64))
    text = out.read_text()
    assert text.startswith("-- entry test, program sha256 ") and "import Su2PlaqCert.LSH.Check" in text
    assert "theorem lsh_ue : Su2PlaqCert.LSH.checkJsonString certJson = true := by native_decide" in text
    t0 = time.time()
    p = P.lake(["env", "lean", str(out)], timeout=900)
    assert time.time() - t0 <= 900
    assert p.returncode == 0, p.stderr[-2000:] + p.stdout[-2000:]
    m = re.search(r"depends on axioms:\s*\[([^\]]*)\]", p.stdout)
    assert m, p.stdout[-2000:]
    axioms = {a.strip() for a in m.group(1).split(",") if a.strip()}
    native = [a for a in axioms if a not in {"propext", "Classical.choice", "Quot.sound"}]
    assert len(native) == 1 and P.is_native_axiom(native[0]), axioms
    c = json.loads(pathlib.Path(r["cert_path"]).read_text())
    c["states"][0]["terms"][0]["code"] = int(c["states"][0]["terms"][0]["code"]) ^ 1
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(c, separators=(",", ":")))
    with pytest.raises(ValueError):
        write_theorem_file(forged, "lsh_bad", tmp_path / "lsh-bad.lean")
