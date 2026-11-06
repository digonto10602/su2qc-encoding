"""M6-S1..S3 — round-0 seeds of the rishon loop (prompts/203 §2, §3.1 `rishon.compress.baselines`; research 202 §2-§3):
the general circuit in three ladder styles as angle-linear programs, polish, the windowed Qiskit L3 baseline, no external
seeds (reasons recorded), and the real round-0 file.  Validity tolerances unchanged (prompts/003-005); keys exact."""
import functools
import json
import pathlib

import pytest

from tests.acceptance._api import api

ENC, KIND = "rishon", "step"
SEED_LABELS = ("general", "general+polish", "qiskit_l3", "general-rccx", "general-mcx")
EXTERNAL = {"qiskit_l3_whole", "paulo34", "lean22", "lean22_v2", "spinnet15"}


@functools.lru_cache(maxsize=None)
def _spec(kind=KIND):
    return api("su2plaq.rishon.compress.spec:rishon_spec")(kind)


def test_M6_S1_seed_programs_and_import_reasons():
    """The three ladder variants exist as immutable seed programs (family seed, no parent, angle-linear); every external
    source is a reason string; the ladder programs rebuild to the ladder circuits' gate counts."""
    spec = _spec()
    BL = api("su2plaq.rishon.compress.baselines")
    B = api("su2plaq.compress.builder")
    ev = api("su2plaq.compress.evaluate")
    assert tuple(BL.LADDERS) == ("ccx", "rccx", "mcx")
    names = {}
    for ladder in BL.LADDERS:
        p = pathlib.Path(BL.general_program_path(spec, ladder=ladder))
        assert p.exists() and p.parent.name == "seed" and p.parent.parent.name == ENC
        hdr = B.parse_program_header(p.read_text())
        assert hdr["family"] == "seed" and hdr["parent"] is None and hdr["summary"]
        names[ladder] = p.name
        mod = ev.load_program(str(p))
        qc = mod.build(spec).circuit()
        ops = qc.count_ops()
        want = BL.general_circuit(spec, ladder=ladder).count_ops()
        assert ops.get("rccx", 0) == want.get("rccx", 0) and ops.get("ccx", 0) == want.get("ccx", 0) and ops.get("cx", 0) == want.get("cx", 0)
        assert ev.skeleton(qc) == ev.skeleton(mod.build(spec.with_angles(*spec.alt_angles[1])).circuit())
    assert names["ccx"].startswith("000-") and names["rccx"].startswith("001-") and names["mcx"].startswith("002-")
    assert len(set(names.values())) == 3
    for src in ("paulo34", "lean22", "lean22_v2", "spinnet15"):
        res = BL.import_seed(spec, src)
        assert isinstance(res, str) and len(res) > 10, src
    with pytest.raises(ValueError):
        BL.import_seed(spec, "no_such_seed")


def test_M6_S2_polish_and_l3_trial():
    """polish is exact and not worse (laptop rewrite rules + our trial evaluation); the windowed Qiskit L3 baseline of the
    U_E general circuit is valid; a polish log line starts with a Lean-certified rule name."""
    spec = _spec("UE")
    BL = api("su2plaq.rishon.compress.baselines")
    ev = api("su2plaq.rishon.compress.evaluate")
    M = api("su2plaq.compress.metrics")
    R = api("su2plaq.lean.rules")
    qc = BL.general_circuit(spec)
    out, log = BL.polish(qc, spec)
    assert isinstance(log, list) and log and all(str(ln).split(":")[0].split()[0] in R.LEAN_RULES for ln in log)
    assert ev.evaluate_circuit(out, spec, mode="trial").valid
    assert M.key(M.metrics(out, spec, measured=False)) <= M.key(M.metrics(qc, spec, measured=False))
    l3 = BL.qiskit_l3(spec, seed=12345)
    r = ev.evaluate_circuit(l3, spec, mode="trial")
    assert r.valid, r.reason
    # the step general circuit: polish keeps or improves the key and stays valid (trial)
    spec_s = _spec("step")
    qs = BL.general_circuit(spec_s)
    out_s, log_s = BL.polish(qs, spec_s)
    assert M.key(M.metrics(out_s, spec_s, measured=False)) <= M.key(M.metrics(qs, spec_s, measured=False))
    if out_s is not qs:
        assert ev.evaluate_circuit(out_s, spec_s, mode="trial").valid


@pytest.mark.slow
def test_M6_S3_round0_recorded(root):
    """The real round 0 (results/compress/rishon/round-000.json, step 6.5): five labelled seed rows, the external sources
    with reasons, valid rows satisfy the tolerances, the two ladder variants are recorded as the evaluator judged them
    (ok or pruning_bound: both are physically exact, research 202 §3), and the archive best is the cheapest valid seed."""
    f = root / "results" / "compress" / ENC / "round-000.json"
    if not f.exists():
        pytest.fail("PENDING: results/compress/rishon/round-000.json missing (step 6.5)", pytrace=False)
    d = json.loads(f.read_text())
    assert d["round"] == 0 and d["encoding"] == ENC and d["kind"] == KIND and "git_commit" in d["provenance"]
    by = {c["label"]: c for c in d["candidates"]}
    assert set(SEED_LABELS) <= set(by), sorted(by)
    for lab in ("general", "general+polish", "qiskit_l3"):
        c = by[lab]
        assert c["valid"] and c["reason"] == "ok" and c["verdict"]["op_norm_error"] <= 1e-10 and c["verdict"]["certified"], lab
        assert c["mode"] == "full" and c["skeleton_equal"] and all(c["alt_ok"])
    assert tuple(by["general+polish"]["key"]) <= tuple(by["general"]["key"])
    for lab in ("general-rccx", "general-mcx"):
        c = by[lab]
        assert c["reason"] in ("ok", "pruning_bound"), (lab, c["reason"])
        assert c["valid"] == (c["reason"] == "ok")
        if c["reason"] == "pruning_bound":
            v = c["verdict"]
            assert v["block_error"] + v["leak_amplitude"] <= 1e-10 and v["dropped_total"] > 1e-12
    ext = {x["source"]: x for x in d["external"]}
    assert set(ext) == EXTERNAL
    for s in ("paulo34", "lean22", "lean22_v2", "spinnet15"):
        assert isinstance(ext[s].get("reason"), str) and ext[s]["reason"]
    assert ext["qiskit_l3_whole"]["valid"] is False and ("metrics" in ext["qiskit_l3_whole"] or "reason" in ext["qiskit_l3_whole"])
    valid = [c for c in d["candidates"] if c["valid"]]
    assert valid and d["best_key"] == min((c["key"] for c in valid), key=tuple)
    A = api("su2plaq.compress.archive")
    arch = A.Archive.load(ENC, root=root)
    seeds = [e for e in arch.entries() if e.round == 0 and e.valid]
    assert seeds and min(tuple(e.key) for e in seeds) == tuple(d["best_key"])
    assert d["synthesis_verification"] is not None and d["synthesis_verification"]["ok"] is True
