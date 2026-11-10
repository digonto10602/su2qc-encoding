"""M6-H3, H4, G5, G6 — the three-layer step and the continuation of the rishon loop after prompts/204.

Decisions of prompts/204 (section 6): (1) the compression unit stays U_B(beta) U_E(alpha) -- its target does not contain the
det angle eta, so the archive of rounds 0-4 stays physically valid; (2) the det layer U_D(eta) is a separate layer in front of
the unit: three-layer first-order step = U_B U_D U_E = (U_B U_E) U_D because [U_D, U_E] = 0 (M5-DT3); (3) the rishon prune cap
is 10 % of tol_err (M5-V2), which changes the rishon evaluator hash, so rounds 0-4 are replayed once under the new hash
(`su2plaq.rishon.compress.replay`, record results/compress/rishon/replay-204.json; the old files are kept under pre-204/).

H3: the det layer's cost and the locked eta set for its angle-averaged T count (same idea as the (alpha, beta) set of
prompts/203 section 13 E3; a separate generator so that set and its sha stay unchanged).
H4: the headline program with the det layer in front is the three-layer step on all 1296 inner codes (hence on all 38 432
physical states, METHODS-rishon R6) at the three (alpha, beta, eta) triples; cost is additive.
G5: the replay record.  G6: the three-layer summary file of the gate.
Tolerances: validity as everywhere (op_norm_error <= 1e-10, Gauss <= 1e-10, exact-angle) with the rishon cap
dropped_total <= 0.1 * 1e-10; integer keys compared exactly."""
import functools
import json

import numpy as np
import pytest

from tests.acceptance._api import api, ross_selinger_band

ENC, KIND = "rishon", "step"
DET_TRIPLES = ((0.37, 0.61, 0.29), (0.91, 0.23, 0.53), (1.70, 1.00, 1.07))
ETA_SET_SEED, ETA_SET_N, ETA_SET_RANGE = 20261110, 20, (0.05, 1.2)
TOL_ERR, TOL_GAUSS, PRUNE_FRACTION = 1e-10, 1e-10, 0.1


@functools.lru_cache(maxsize=None)
def _spec():
    return api("su2plaq.rishon.compress.spec:rishon_spec")(KIND)


def _headline(root):
    A = api("su2plaq.compress.archive")
    R = api("su2plaq.rishon.compress.robust")
    arch = A.Archive.load(ENC, root=root)
    if arch.best() is None:
        pytest.fail("PENDING: the rishon archive has no valid entry yet", pytrace=False)
    h = R.headline(KIND, root=root)
    entry = next(e for e in arch.entries() if e.id == h["id"])
    return arch, h, entry


def test_M6_H3_det_layer_metrics_and_eta_set():
    """DET_TRIPLES and the eta set are the locked definitions; det_layer_metrics(0.29) equals the laptop metrics of
    build_UD(0.29, with_outer=True) (key, T measured with pygridsynth at 1e-6 in the Ross-Selinger band per rotation), has no
    ancilla (48 qubits), at most 32 CX and 8 rotations; the 20 T counts over the eta set are each the laptop metric at that eta."""
    TL = api("su2plaq.rishon.compress.three_layer")
    C = api("su2plaq.circuits.rishon")
    M = api("su2plaq.compress.metrics")
    spec = _spec()
    assert tuple(tuple(t) for t in TL.DET_TRIPLES) == DET_TRIPLES
    assert (TL.ETA_SET_SEED, TL.ETA_SET_N, tuple(TL.ETA_SET_RANGE)) == (ETA_SET_SEED, ETA_SET_N, ETA_SET_RANGE)
    want = np.random.default_rng(ETA_SET_SEED).uniform(ETA_SET_RANGE[0], ETA_SET_RANGE[1], ETA_SET_N)
    assert len(TL.ETA_SET) == ETA_SET_N and np.array_equal(np.array(TL.ETA_SET, float), want)
    R = api("su2plaq.rishon.compress.robust")       # the (alpha, beta) set of prompts/203 section 13 E3 is untouched
    assert R.ANGLE_SET_SEED == 20261107 and len(R.ANGLE_SET) == 20
    dm = TL.det_layer_metrics(0.29)
    ref = M.metrics(C.build_UD(0.29, with_outer=True), spec, measured=True)
    assert dm["cx"] == ref["cx"] <= 32 and dm["n_rot"] == ref["n_rot"] <= 8 and dm["t_fixed"] == ref["t_fixed"] == 0
    assert dm["t_eps"] == ref["t_eps"] and dm["depth_ct"] == ref["depth_ct"] and dm["qubits"] == ref["qubits"] == 48
    assert tuple(dm["key"]) == tuple(M.key(ref))
    lo, hi = ross_selinger_band(1e-6)
    assert dm["n_rot"] * lo <= dm["t_eps"] <= dm["n_rot"] * hi
    assert len(dm["t_eps_set"]) == ETA_SET_N and dm["t_sum"] == sum(dm["t_eps_set"]) and abs(dm["t_mean"] - dm["t_sum"] / ETA_SET_N) <= 1e-12
    for i in (0, 7, 19):
        assert dm["t_eps_set"][i] == M.metrics(C.build_UD(float(want[i]), with_outer=True), spec, measured=True)["t_eps"]
    assert all(dm["n_rot"] * lo <= t <= dm["n_rot"] * hi for t in dm["t_eps_set"])


def test_M6_H4_three_layer_headline(root):
    """The headline entry (robust key) rebuilt from its program at the three (alpha, beta) pairs, with the det layer in front
    (circuits.rishon.prepend_det_layer), is the three-layer first-order step U_B U_D U_E: ok and certified on the 1296 inner
    codes, Gauss sample, clean ancillas, no outer qubit touched, identical skeleton over the triples; the unit alone is NOT the
    three-layer step; CX and T(1e-6) are additive; three_layer.verify_three_layer() reports the same."""
    spec = _spec()
    arch, h, entry = _headline(root)
    C = api("su2plaq.circuits.rishon")
    Vf = api("su2plaq.rishon.verify")
    TL = api("su2plaq.rishon.compress.three_layer")
    ev = api("su2plaq.compress.evaluate")
    M = api("su2plaq.compress.metrics")
    enc = api("su2plaq.encodings.rishon:RishonEncoding")()
    mod = ev.load_program(str(root / entry.program_path))
    skels, full0, unit0 = [], None, None
    for a, b, eta in DET_TRIPLES:
        unit = mod.build(spec.with_angles(a, b)).circuit()
        full = C.prepend_det_layer(unit, eta)
        assert full.num_qubits == unit.num_qubits
        touched = {full.find_bit(q).index for inst in full.data for q in inst.qubits}
        assert not (touched & set(range(16, 48))), sorted(touched & set(range(16, 48)))
        v = Vf.verify(full, enc, "step", a, b, eta=eta)
        assert v.ok and v.certified and v.reason == "ok", (v.reason, v.op_norm_error, v.dropped_total)
        assert v.op_norm_error <= TOL_ERR and v.dropped_total <= PRUNE_FRACTION * TOL_ERR and v.gauss_residual <= TOL_GAUSS
        assert v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20 and v.outer_bits_read == 0
        skels.append(ev.skeleton(full))
        if full0 is None:
            full0, unit0 = full, unit
            w = Vf.verify(unit, enc, "step", a, b, eta=eta, gauss=False)
            assert not w.ok and w.op_norm_error > 1e-3
    assert all(s == skels[0] for s in skels)
    mu, m3 = M.metrics(unit0, spec, measured=True), M.metrics(full0, spec, measured=True)
    md = TL.det_layer_metrics(DET_TRIPLES[0][2])
    assert tuple(M.key(mu)) == tuple(entry.key)
    assert m3["cx"] == mu["cx"] + md["cx"] and m3["t_eps"] == mu["t_eps"] + md["t_eps"] and m3["qubits"] == mu["qubits"]
    assert mu["depth_ct"] <= m3["depth_ct"] <= mu["depth_ct"] + md["depth_ct"]
    r = TL.verify_three_layer(root=root)
    assert r["entry"] == h["id"] and r["program_sha256"] == entry.program_sha256 and r["ok"] is True and r["skeleton_equal"] is True
    assert [tuple(t) for t in r["triples"]] == list(DET_TRIPLES) and len(r["verdicts"]) == 3 and r["outer_touched"] is False
    assert all(x["ok"] and x["certified"] and x["op_norm_error"] <= TOL_ERR and x["dropped_total"] <= PRUNE_FRACTION * TOL_ERR
               and x["gauss_residual"] <= TOL_GAUSS for x in r["verdicts"])
    assert tuple(r["unit_key"]) == tuple(entry.key) and tuple(r["det_key"]) == tuple(md["key"]) and tuple(r["three_layer_key"]) == tuple(M.key(m3))


def test_M6_G5_replay_record(root):
    """results/compress/rishon/replay-204.json (python -m su2plaq.rishon.compress.replay): rounds 0..R re-evaluated in order
    under the rishon cap 0.1 and the current rishon evaluator hash; no previously valid entry is lost and every one keeps its
    key exactly (the looser cap cannot invalidate; the physics of the programs is unchanged); a candidate is newly valid only
    if its old reason was `pruning_bound`; every valid entry has dropped_total <= 1e-11; the archive holds exactly the valid
    ones with the current hash; the pre-replay files are kept under results/compress/rishon/pre-204/ and
    compress/archive/rishon-pre-204/; the attempts log and the discoveries file are byte-identical to before the replay."""
    f = root / "results" / "compress" / ENC / "replay-204.json"
    api("su2plaq.rishon.compress.replay:replay")
    if not f.exists():
        pytest.fail("PENDING: results/compress/rishon/replay-204.json missing (prompts/204 step C2)", pytrace=False)
    d = json.loads(f.read_text())
    assert d["encoding"] == ENC and d["kind"] == KIND and d["prune_fraction"] == PRUNE_FRACTION and d["tag"] == "204"
    assert d["rounds"] == list(range(len(d["rounds"]))) and len(d["rounds"]) >= 5
    h = api("su2plaq.rishon.compress:code_hash")()
    assert d["evaluator_sha256"] == h and h not in d["evaluator_sha256_old"] and d["evaluator_sha256_old"]
    ents = {e["id"]: e for e in d["entries"]}
    assert len(ents) == len(d["entries"]) >= 19
    for e in d["entries"]:
        if e["old"]["valid"]:
            assert e["new"]["valid"] and e["new"]["reason"] == "ok" and tuple(e["new"]["key"]) == tuple(e["old"]["key"]) and e["key_equal"] is True, e["id"]
        elif e["new"]["valid"]:
            assert e["old"]["reason"] == "pruning_bound" and e["id"] in d["newly_valid"], e["id"]
        if e["new"]["valid"]:
            assert e["new"]["dropped_total"] <= PRUNE_FRACTION * TOL_ERR
        if e["new"]["reason"] == "pruning_bound":
            assert e["new"]["dropped_total"] > PRUNE_FRACTION * TOL_ERR
    assert d["lost"] == [] and set(d["newly_valid"]) == {i for i, e in ents.items() if e["new"]["valid"] and not e["old"]["valid"]}
    A = api("su2plaq.compress.archive")
    arch = A.Archive.load(ENC, root=root)
    replayed = {x.id for x in arch.entries() if x.round < len(d["rounds"])}
    assert replayed == {i for i, e in ents.items() if e["new"]["valid"]}
    assert all(x.evaluator_sha256 == h for x in arch.entries())
    old_best, new_best = d["best_old"], d["best_new"]
    assert tuple(new_best["key"]) <= tuple(old_best["key"]) and new_best["id"] in ents
    assert (root / "results" / "compress" / ENC / "pre-204" / "round-000.json").exists()
    assert (root / "compress" / "archive" / f"{ENC}-pre-204" / "index.json").exists()
    assert d["attempts_unchanged"] is True and d["discoveries_unchanged"] is True
    prov = d["provenance"]
    assert isinstance(prov["git_commit"], str) and len(prov["git_commit"]) >= 7


def test_M6_G6_three_layer_summary(root):
    """results/compress/rishon/three-layer.json (python -m su2plaq.rishon.compress.three_layer, step 6.8): the current headline
    entry with the det layer, verified at the three triples (ok), with the additive keys and the angle-averaged T of both parts;
    written on a clean commit."""
    f = root / "results" / "compress" / ENC / "three-layer.json"
    api("su2plaq.rishon.compress.three_layer:verify_three_layer")
    if not f.exists():
        pytest.fail("PENDING: results/compress/rishon/three-layer.json missing (prompts/204 step C5)", pytrace=False)
    d = json.loads(f.read_text())
    arch, h, entry = _headline(root)
    assert d["entry"] == h["id"] and d["program_sha256"] == entry.program_sha256 and d["ok"] is True and d["outer_touched"] is False
    assert [tuple(t) for t in d["triples"]] == list(DET_TRIPLES)
    uk, dk, tk = tuple(d["unit_key"]), tuple(d["det_key"]), tuple(d["three_layer_key"])
    assert uk == tuple(entry.key) and tk[0] == uk[0] + dk[0] and tk[1] == uk[1] + dk[1] and tk[3] == max(uk[3], dk[3])
    assert uk[2] <= tk[2] <= uk[2] + dk[2]
    assert abs(d["three_layer_t_mean"] - (d["unit_t_mean"] + d["det_t_mean"])) <= 1e-9 and abs(d["unit_t_mean"] - h["t_mean"]) <= 1e-9
    assert d["evaluator_sha256"] == api("su2plaq.rishon.compress:code_hash")()
    prov = d["provenance"]
    assert isinstance(prov["git_commit"], str) and len(prov["git_commit"]) >= 7 and prov["git_dirty"] is False
