"""M2c-R / M2c-P — encoding registry, dispatch without monkey-patching, per-encoding provenance (prompts/008 §3, §4; METHODS §12).

After the consolidation every encoding is known to the PLAIN shared machinery (`su2plaq.compress.*`, `su2plaq.evaluate.*`) in a
fresh interpreter that never imports a track module, the build worker is the stock one, and importing / "installing" the track
facades (`su2plaq.spinnet.loop`, `su2plaq.rishon.compress`, `su2plaq.fuzzy.compress_hook`) changes no attribute of a shared module
and no environment variable.  Everything here is exact (identities, shapes, hashes); the only float tolerances are 1e-12 on
|oracle element| <= 1 inside the probe program and exact equality of nominal angles.

Fresh-interpreter tests run `python -c` with PYTHONPATH = <repo>/src only, so that state left by other tests of the same pytest
worker (the pre-consolidation shims patch process-global attributes) cannot influence them.  Run time: about 30 s in total.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from tests.acceptance._api import api

ROOT = pathlib.Path(__file__).resolve().parents[3]
# encoding -> (kind of its compression archive, dimension of the oracle target = number of states the evaluator judges)
UNITS = {"twelve": ("step", 433), "spinnet": ("step", 433), "rishon": ("step", 1296), "fuzzy_ub": ("UB", 256), "fuzzy_link": ("UE", 16)}
NOMINAL = (0.37, 0.61)                     # prompts/001 §8, prompts/100 §10, prompts/203, prompts/302: the same pair for every encoding
RISHON_EXTRA = ["encodings/rishon.py", "circuits/rishon.py", "rishon/algebra.py", "rishon/physical.py", "rishon/operators.py",
                "rishon/frames.py", "rishon/verify.py", "rishon/compress/spec.py", "rishon/compress/evaluate.py",
                "rishon/compress/baselines.py"]                          # prompts/203 §3.1 (RISHON_EVALUATOR_FILES minus the shared list)
SPINNET_EXTRA = ["encodings/spinnet.py", "circuits/spinnet.py", "spinnet/walk.py", "spinnet/trotter_v2.py", "spinnet/paulo.py"]   # prompts/104 §1
FUZZY_EXTRA = ["fuzzy/verify.py", "fuzzy/targets.py", "circuits/fuzzy.py"]   # the files that decide a fuzzy unit verdict / general circuit (audit 301)


def _registry():
    return api("su2plaq.encodings.registry")           # PENDING until step A2


def _fresh(code: str, timeout: float = 600.0) -> dict:
    """Run `code` in a fresh interpreter (PYTHONPATH = src only, no hook variables); the last stdout line is JSON."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SU2PLAQ_")}
    env.update({"PYTHONPATH": str(ROOT / "src"), "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1"})
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout, env=env, cwd=str(ROOT))
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_M2C_R1_registry_content():
    """The registry lists the five built encodings with their factories, nominal angles and evaluator file lists; unknown names
    raise ValueError naming the known ones; `base.NOMINAL_ANGLES` and the registry have the same keys."""
    R = _registry()
    base = api("su2plaq.encodings.base")
    names = tuple(R.names())
    assert set(UNITS) <= set(names) and len(names) == len(set(names))
    assert set(base.NOMINAL_ANGLES) == set(names)
    src = ROOT / "src" / "su2plaq"
    for name in UNITS:
        info = R.info(name)
        assert info.name == name and base.NOMINAL_ANGLES[name] == NOMINAL
        assert isinstance(info.factory, str) and ":" in info.factory                 # lazy "module:attr", nothing imported by the table
        assert UNITS[name][0] in info.kinds and info.loop_kind == UNITS[name][0]
        assert info.stamp in ("shared", "encoding") and isinstance(info.gauss_in_loop, bool)
        assert all((src / f).is_file() for f in info.evaluator_files), [f for f in info.evaluator_files if not (src / f).is_file()]
    assert tuple(R.info("twelve").evaluator_files) == ()                             # the twelve files are in the shared list (prompts/002)
    assert list(R.info("rishon").evaluator_files) == RISHON_EXTRA and R.info("rishon").stamp == "encoding"
    assert set(SPINNET_EXTRA) <= set(R.info("spinnet").evaluator_files) and R.info("spinnet").stamp == "shared"
    for name in ("fuzzy_ub", "fuzzy_link"):
        assert set(FUZZY_EXTRA) <= set(R.info(name).evaluator_files) and R.info(name).stamp == "shared"
        assert R.info(name).gauss_in_loop is False and R.info(name).lean_certify is None      # METHODS-fuzzy F9; prompts/302 §0.5
    assert R.info("twelve").gauss_in_loop and R.info("spinnet").gauss_in_loop
    assert R.info("twelve").stamp == "shared"
    with pytest.raises(ValueError, match="twelve"):
        R.info("no_such_encoding")
    with pytest.raises(ValueError):
        api("su2plaq.compress.spec:default_spec")("no_such_encoding", "step")


_FRESH_KNOWS = r'''
import json, sys, tempfile, pathlib
from su2plaq.compress import evaluate as E, oracle
from su2plaq.compress.builder import Builder
from su2plaq.compress.spec import default_spec, get_encoding
UNITS = %(units)r
PROGRAM = %(program)r
out = {}
for name, (kind, dim) in UNITS.items():
    spec = default_spec(name, kind)
    enc = get_encoding(name)
    V = oracle.target(spec)
    b = Builder(spec)
    with tempfile.TemporaryDirectory() as td:
        specs = [spec] + [spec.with_angles(a, c) for a, c in spec.alt_angles]
        circuits, disc = E._build_in_subprocess(PROGRAM.encode(), specs, E.BUILD_TIMEOUT_S)
    out[name] = {"enc_name": enc.name, "angles": [spec.alpha, spec.beta], "shape": list(V.shape), "n_reg": len(b.reg("d")),
                 "n_data": enc.n_data, "n_outer": enc.n_outer, "n_circuits": len(circuits),
                 "qubits": [c.num_qubits for c in circuits], "cap": spec.peak_qubit_cap()}
out["track_modules_imported_by_parent"] = sorted(m for m in sys.modules if m in ("su2plaq.spinnet.loop", "su2plaq.fuzzy.compress_hook", "su2plaq.rishon.compress.round"))
print(json.dumps(out))
'''

_PROBE_PROGRAM = '''"""SUMMARY: probe of prompts/008 (m2c): an empty Builder plus one oracle query made inside the sandboxed worker.

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


def test_M2C_R2_fresh_process_and_stock_worker_know_every_encoding():
    """In a fresh interpreter that imports only shared modules: default_spec / get_encoding / oracle / Builder work for every
    encoding, and the STOCK build worker (`python -m su2plaq.compress.evaluate --worker`, started by the unpatched
    `_build_in_subprocess`) builds a probe program that queries the oracle inside the sandbox, at the three angle pairs."""
    _registry()
    d = _fresh(_FRESH_KNOWS % {"units": UNITS, "program": _PROBE_PROGRAM})
    assert d["track_modules_imported_by_parent"] == []
    for name, (kind, dim) in UNITS.items():
        r = d[name]
        assert r["enc_name"] == name and tuple(r["angles"]) == NOMINAL and r["shape"] == [dim, dim], (name, r)
        assert r["n_reg"] == r["n_data"] and r["n_circuits"] == 3 and r["qubits"] == [r["n_data"] + r["n_outer"]] * 3, (name, r)
    assert d["fuzzy_ub"]["cap"] == 40 and d["fuzzy_link"]["cap"] == 4          # prompts/302 §3 (locked M10-H1/H2)
    assert d["twelve"]["cap"] == 12 + 16 + 32 and d["spinnet"]["cap"] == 8 + 8 + 32 and d["rishon"]["cap"] == 80


_FRESH_NO_PATCH = r'''
import json, os
from su2plaq.compress import baselines as BL, brief as BR, evaluate as E, round as RD, spec as S
from su2plaq.encodings import base, registry
from su2plaq.evaluate import evaluator as EV
def snap():
    return {"E._build_in_subprocess": id(E._build_in_subprocess), "E._one_verdict": id(E._one_verdict), "E._worker": id(E._worker),
            "E.evaluate_circuit": id(E.evaluate_circuit), "E.evaluate_program": id(E.evaluate_program),
            "EV.evaluate": id(EV.evaluate), "EV.inner_target": id(EV.inner_target), "RD._certify": id(RD._certify),
            "RD.run_round": id(RD.run_round), "BL.general_circuit": id(BL.general_circuit), "BL.import_seed": id(BL.import_seed),
            "S.get_encoding": id(S.get_encoding), "S.default_spec": id(S.default_spec), "S.TaskSpec.render": id(S.TaskSpec.render),
            "S.TaskSpec.peak_qubit_cap": id(S.TaskSpec.peak_qubit_cap), "S.TaskSpec._structure_section": id(S.TaskSpec._structure_section),
            "S.STRUCTURE_JSON": str(S.STRUCTURE_JSON), "BR.make_brief": id(BR.make_brief), "BR.make_ideation_brief": id(BR.make_ideation_brief),
            "BR._structure_pointer": id(BR._structure_pointer), "NOMINAL_ANGLES": sorted(base.NOMINAL_ANGLES.items()),
            "registry": sorted(registry.names()), "PYTHONPATH": os.environ.get("PYTHONPATH"),
            "hook_vars": sorted(k for k in os.environ if k.startswith("SU2PLAQ_"))}
before = snap()
from su2plaq.spinnet import loop as L
L.install(); L.install()
from su2plaq.fuzzy import compress_hook as H
H.install(); H.install()
import su2plaq.rishon.compress as RC
from su2plaq.rishon.compress import spec as RS
RS.register()
sp = L.spec(); rs = RS.rishon_spec("step"); fs = S.default_spec("fuzzy_ub", "UB")
after = snap()
print(json.dumps({"changed": sorted(k for k in before if before[k] != after[k]),
                  "shim_marked": bool(getattr(E._build_in_subprocess, "_spinnet_shim", False) or getattr(RD._certify, "_spinnet_shim", False)),
                  "installed_encoding": L.INSTALLED.get("encoding")}))
'''


def test_M2C_R3_track_facades_patch_nothing():
    """Importing and 'installing' the three track facades changes no attribute of a shared module, no registry content and no
    environment variable (no `sitecustomize` hook, no PYTHONPATH edit): dispatch replaces monkey-patching."""
    _registry()
    d = _fresh(_FRESH_NO_PATCH)
    assert d["changed"] == [], d["changed"]
    assert d["shim_marked"] is False and d["installed_encoding"] is True
    assert not (ROOT / "src" / "su2plaq" / "fuzzy" / "sitehook" / "sitecustomize.py").exists()


def test_M2C_P1_code_hash_per_encoding():
    """`provenance.evaluator_files(enc)` = the shared list followed by the encoding's own files; `code_hash_for(enc)` is the hash of
    exactly that list; `stamp_hash(enc)` is what the archive records as `evaluator_sha256` (shared hash, or the encoding hash for
    encodings registered with stamp 'encoding'); the registry module itself is in the shared list; a twelve hash does not depend
    on any other encoding's file."""
    R = _registry()
    P = api("su2plaq.compress.provenance")
    src = ROOT / "src" / "su2plaq"
    shared = [src / f for f in P.EVALUATOR_FILES if (src / f).exists()]
    assert src / "encodings" / "registry.py" in shared
    for name in UNITS:
        files = [pathlib.Path(f) for f in P.evaluator_files(name)]
        assert files == shared + [src / f for f in R.info(name).evaluator_files], name
        h = P.code_hash_for(name)
        assert isinstance(h, str) and len(h) == 64 and h == P.code_hash(files=files)
        assert P.stamp_hash(name) == (h if R.info(name).stamp == "encoding" else P.code_hash())
    assert P.code_hash_for("twelve") == P.code_hash()
    assert P.code_hash_for("rishon") == api("su2plaq.rishon.compress:code_hash")()
    others = ("spinnet", "rishon", "fuzzy", "lsh")
    assert not [f for f in P.evaluator_files("twelve") if any(o in pathlib.Path(f).relative_to(src).as_posix() for o in others)]
    assert len({P.code_hash_for(n) for n in ("twelve", "spinnet", "rishon", "fuzzy_ub")}) == 4


def test_M2C_P2_shared_round_stamps_both_hashes(tmp_path):
    """A dry round 0 of the smallest unit (fuzzy_link, 16 x 16) through the PLAIN shared round module, no hook installed by this
    test: valid entries carry `evaluator_sha256` = stamp hash and the new `encoding_sha256` = per-encoding hash; the Lean status of
    the best is `n_a` (the registry says the encoding has no exporter); the verdict records that the Gauss check was not run."""
    R = _registry()
    P = api("su2plaq.compress.provenance")
    RD = api("su2plaq.compress.round")
    A = api("su2plaq.compress.archive")
    if "encoding_sha256" not in A.Entry.__dataclass_fields__:
        pytest.fail("PENDING: archive.Entry has no field encoding_sha256 (prompts/008 step B1)", pytrace=False)
    info = RD.run_round("fuzzy_link", "UE", 0, evaluate=True, dry_run=True, root=tmp_path, lean=True)
    assert info["round"] == 0 and info["n_valid"] >= 1 and info["best_key"] is not None
    arch = A.Archive.load("fuzzy_link", root=tmp_path, n_alt=2, strict=True)
    assert arch.entries() and arch.rejected == []
    for e in arch.entries():
        assert e.evaluator_sha256 == P.stamp_hash("fuzzy_link") == P.code_hash()
        assert e.encoding_sha256 == P.code_hash_for("fuzzy_link")
        assert e.verdict_nominal.get("extra", {}).get("gauss") == "not_checked"
    best = arch.best()
    assert isinstance(best.lean, dict) and best.lean.get("status") == "n_a"
    d = json.loads((tmp_path / "results" / "compress" / "fuzzy_link" / "round-000.json").read_text())
    assert d["evaluator_sha256"] == P.stamp_hash("fuzzy_link") and d["encoding_sha256"] == P.code_hash_for("fuzzy_link")
