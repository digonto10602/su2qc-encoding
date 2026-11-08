"""M6-H1/H2 — the headline rule (prompts/203 §13 E3, mirrored from the spinnet erratum prompts/104 §11 E3): the laptop archive
key counts T at the nominal angles only, which rewards pygridsynth luck (rz(theta +- pi/4) T^-+ rewrites); the track's HEADLINE
circuit (Report 6, results JSON, Lean theorem file, stop-rule counter) is the valid archive entry with the smallest robust key
(CX, sum of T(1e-6) over 20 locked seeded angle pairs, angle-linear rank, sum of depth_CT, qubits).  T counting needs only the
rebuilt circuit and pygridsynth (no 1296-code evaluation).  Exact definitions; the only numbers are the locked angle set.
PENDING rule: missing `su2plaq.rishon.compress.robust` names fail with `PENDING:`."""
import functools
import json
import pathlib

import numpy as np
import pytest

from tests.acceptance._api import api

ENC = "rishon"
ANGLE_SET_SEED, ANGLE_SET_N = 20261107, 20
ANGLE_RANGES = ((0.05, 2.0), (0.05, 1.2))


def _angle_set() -> np.ndarray:
    """The locked set, recomputed here: alpha drawn first, then beta (same generator and seed as track S)."""
    rng = np.random.default_rng(ANGLE_SET_SEED)
    a = rng.uniform(*ANGLE_RANGES[0], ANGLE_SET_N)
    b = rng.uniform(*ANGLE_RANGES[1], ANGLE_SET_N)
    return np.column_stack([a, b])


@functools.lru_cache(maxsize=None)
def _spec(kind):
    return api("su2plaq.rishon.compress.spec:rishon_spec")(kind)


def _program(tmp_path: pathlib.Path, name: str, source: str) -> pathlib.Path:
    d = tmp_path / "compress" / "programs" / ENC / "seed"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.py"
    p.write_text(source)
    return p


def _derived(src: str, epilogue: str) -> str:
    """The generated seed program with extra Builder calls before its `return b`."""
    assert src.count("    return b\n") == 1
    return src.replace("    return b\n", epilogue + "    return b\n")


def test_M6_H1_angle_set_and_robust_metrics(tmp_path):
    """The locked angle set; `robust_metrics` of the U_E seed program: identical skeleton over the set, 20 T and depth values
    equal to the laptop metrics of the reference circuit at the same pairs, angle-linear (three-variable rule), robust key
    (CX, sum T, 0, sum depth, qubits); a skeleton that changes inside the range has no robust key; a valid program with a
    constant angle on an ancilla is not angle-linear (rank 1)."""
    R = api("su2plaq.rishon.compress.robust")
    BL = api("su2plaq.rishon.compress.baselines")
    M = api("su2plaq.compress.metrics")
    spec = _spec("UE")
    assert R.ANGLE_SET_SEED == ANGLE_SET_SEED and R.ANGLE_SET_N == ANGLE_SET_N and tuple(map(tuple, R.ANGLE_SET_RANGES)) == ANGLE_RANGES
    A_set = np.asarray(R.ANGLE_SET, dtype=float)
    assert A_set.shape == (ANGLE_SET_N, 2) and np.array_equal(A_set, _angle_set())
    assert len(R.angle_set_sha256()) == 64 and R.HEADLINE_SECTION_TITLE.startswith("## Headline rule")
    gp = pathlib.Path(BL.general_program_path(spec))
    rm = R.robust_metrics(gp, spec, root=tmp_path)
    assert rm["skeleton_equal"] and len(rm["t_eps"]) == ANGLE_SET_N and len(rm["depth_ct"]) == ANGLE_SET_N
    assert rm["t_sum"] == sum(rm["t_eps"]) and rm["depth_sum"] == sum(rm["depth_ct"]) and abs(rm["t_mean"] - rm["t_sum"] / ANGLE_SET_N) <= 1e-12
    assert rm["angle_linear"] is True and tuple(rm["robust_key"]) == (rm["cx"], rm["t_sum"], 0, rm["depth_sum"], rm["qubits"])
    assert rm["cx"] == 8 and rm["qubits"] == 48 and len(rm["program_sha256"]) == 64 and rm["angle_set_sha256"] == R.angle_set_sha256()
    fits = rm["angle_fit"]                               # per rotation of the nominal circuit: (m_alpha, m_beta, m_gamma, d)
    assert len(fits) == 4 and all(tuple(f) == (-3, 0, 0, 4) for f in fits)
    for i in (0, 7, 19):
        a_i, b_i = (float(x) for x in A_set[i])
        ref = M.metrics(BL.general_circuit(spec.with_angles(a_i, b_i)), spec.with_angles(a_i, b_i), measured=True)
        assert rm["t_eps"][i] == ref["t_eps"] and rm["depth_ct"][i] == ref["depth_ct"] and rm["cx"] == ref["cx"], i
    src = gp.read_text()
    betas = A_set[:, 1]
    thr = float(np.sort(betas)[ANGLE_SET_N // 2])
    assert (betas > thr).any() and (betas <= thr).any()
    bad = _derived(src, f'    if spec.beta > {thr!r}:\n        w = b.alloc(1, "w")\n        b.x(w[0])\n        b.x(w[0])\n        b.free(w)\n')
    rb = R.robust_metrics(_program(tmp_path, "004-skel-range", bad), spec, root=tmp_path)
    assert not rb["skeleton_equal"] and rb["robust_key"] is None
    nonlin = _derived(src, '    w = b.alloc(1, "nl")\n    b.p(0.123, w[0])\n    b.p(-0.123, w[0])\n    b.free(w)\n')
    rn = R.robust_metrics(_program(tmp_path, "005-nonlinear", nonlin), spec, root=tmp_path)
    assert rn["skeleton_equal"] and rn["angle_linear"] is False and rn["robust_key"][2] == 1
    assert rn["cx"] == rm["cx"] and tuple(rn["robust_key"]) > tuple(rm["robust_key"])
    # the three-variable rule: an angle m_gamma sqrt2 beta / d is angle-linear for rishon
    lin3 = _derived(src, '    w = b.alloc(1, "g")\n    b.p(8 * 1.4142135623730951 * spec.beta / 2, w[0])\n    b.p(-8 * 1.4142135623730951 * spec.beta / 2, w[0])\n    b.free(w)\n')
    r3 = R.robust_metrics(_program(tmp_path, "006-sqrt2", lin3), spec, root=tmp_path)
    assert r3["skeleton_equal"] and r3["angle_linear"] is True and any(tuple(f)[2] != 0 for f in r3["angle_fit"])


@pytest.mark.slow
def test_M6_H2_headline_selection_on_seed_round(tmp_path):
    """Dry round 0 (kind UE) under tmp: `headline()` picks the valid entry with the smallest robust key (full ties: laptop
    key, then id); every valid entry is ranked (entries without a program file rank last with key None); the per-entry
    robust metrics are cached with the angle set; the report has a HEADLINE section and summary.json a `headline` block
    next to the laptop global best."""
    kind = "UE"
    R = api("su2plaq.rishon.compress.robust")
    rd = api("su2plaq.rishon.compress.round")
    A = api("su2plaq.compress.archive")
    rd.run_round(kind, round=0, evaluate=True, dry_run=True, root=tmp_path, lean=False)
    arch = A.Archive.load(ENC, root=tmp_path)
    valid = {e.id: e for e in arch.entries() if e.valid}
    assert valid
    h = R.headline(kind, root=tmp_path)
    assert h["id"] in valid and h["archive_best"] == arch.best().id and h["robust_key"] is not None
    ranking = h["ranking"]
    assert {r["id"] for r in ranking} == set(valid)
    keyed = [tuple(r["robust_key"]) for r in ranking if r["robust_key"] is not None]
    assert keyed and keyed == sorted(keyed) and tuple(h["robust_key"]) == keyed[0]
    assert all(r["robust_key"] is None for r in ranking[len(keyed):])
    for r in ranking:
        if r["robust_key"] is not None:
            rm = R.robust_metrics(tmp_path / valid[r["id"]].program_path, _spec(kind), root=tmp_path)
            assert tuple(rm["robust_key"]) == tuple(r["robust_key"]) and rm["cx"] == valid[r["id"]].key[0]
    cache = json.loads((tmp_path / "results" / "compress" / ENC / "robust.json").read_text())
    assert set(cache["entries"]) >= {r["id"] for r in ranking if r["robust_key"] is not None}
    assert cache["angle_set"]["seed"] == ANGLE_SET_SEED and len(cache["angle_set"]["pairs"]) == ANGLE_SET_N and cache["angle_set"]["sha256"] == R.angle_set_sha256()
    text = R.report_table(kind, root=tmp_path)
    assert "HEADLINE" in text and h["id"] in text and "T_avg" in text and "GLOBAL BEST" in text
    summary = json.loads((tmp_path / "results" / "compress" / ENC / "summary.json").read_text())
    assert summary["headline"]["id"] == h["id"] and tuple(summary["headline"]["robust_key"]) == tuple(h["robust_key"])
    assert summary["global_best"] == arch.best().id and summary["headline"]["angle_set_sha256"] == R.angle_set_sha256()
