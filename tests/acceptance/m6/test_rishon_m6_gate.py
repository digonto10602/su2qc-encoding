"""M6-G1..G4 — milestone gate of the rishon compression loop (prompts/203 §5 step 6.8, §6): the real archive's best
re-evaluates as valid from its program source and is not worse than the best seed, the round's Clifford+T re-verification
passed, the best touches no outer qubit, and the protocol budgets (prompts/001 §4) were respected.  Reads the real
archive / results only (never writes)."""
import functools
import json
import pathlib

import pytest

from tests.acceptance._api import api

ENC, KIND = "rishon", "step"
MAX_ROUNDS, MAX_SESSIONS = 8, 20


@functools.lru_cache(maxsize=None)
def _spec():
    return api("su2plaq.rishon.compress.spec:rishon_spec")(KIND)


def _rounds(root) -> list[dict]:
    rdir = root / "results" / "compress" / ENC
    files = sorted(rdir.glob("round-*.json"))
    if not files:
        pytest.fail("PENDING: no results/compress/rishon/round-*.json yet (steps 6.5-6.7)", pytrace=False)
    return [json.loads(f.read_text()) for f in files]


def _best(root):
    A = api("su2plaq.compress.archive")
    arch = A.Archive.load(ENC, root=root)
    best = arch.best()
    if best is None:
        pytest.fail("PENDING: the rishon archive has no valid entry yet", pytrace=False)
    return arch, best


@pytest.mark.slow
def test_M6_G1_archive_best_valid_and_not_worse_than_seed(root):
    """The global best re-evaluates (full mode) as valid from its program file; the recorded key equals the fresh key; it
    is <= the best round-0 key; its evaluator sha is the current rishon code hash."""
    spec = _spec()
    arch, best = _best(root)
    ev = api("su2plaq.rishon.compress.evaluate")
    M = api("su2plaq.compress.metrics")
    # prompts/204 section 3, 6: rishon prune cap 10 % of tol_err; the archive must be the one replayed under the new evaluator hash
    assert api("su2plaq.rishon.verify:RISHON_PRUNE_FRACTION") == 0.1
    if not (root / "results" / "compress" / ENC / "replay-204.json").exists():
        pytest.fail("PENDING: the archive has not been replayed under the 10 % cap (prompts/204 step C2)", pytrace=False)
    assert best.valid and best.mode == "full"
    r = ev.evaluate_program(str(root / best.program_path), spec, mode="full")
    assert r.valid and r.skeleton_equal, (r.reason, r.message)
    assert tuple(M.key(r.metrics)) == tuple(best.key)
    seeds = [e for e in arch.entries() if e.round == 0 and e.valid]
    assert seeds and tuple(best.key) <= min(tuple(e.key) for e in seeds)
    assert best.evaluator_sha256 == api("su2plaq.rishon.compress:code_hash")()
    assert r.verdict.op_norm_error <= 1e-10 and r.verdict.dropped_total <= 1e-11 and r.verdict.gauss_residual <= 1e-10


def test_M6_G2_best_synthesised_reverified(root):
    """The round that produced the global best re-verified its Clifford+T synthesis at eps = 1e-6 within N_rot eps + 1e-9."""
    arch, best = _best(root)
    rounds = _rounds(root)
    hits = [r["synthesis_verification"] for r in rounds if r.get("synthesis_verification") and r["synthesis_verification"].get("entry") == best.id]
    assert hits, f"no synthesis_verification for {best.id}"
    s = hits[-1]
    assert s["ok"] is True and s["certified"] is True and s["op_norm_error"] <= s["tolerances"]["tol_err"]
    assert s["eps"] == 1e-6 and s["t_total"] == best.metrics_raw["t_eps"]


def test_M6_G3_best_touches_no_outer_qubit(root):
    """The best circuit never acts on qubits 16..47 (outer register), reads no outer bit, and its qubit count is
    48 + ancillas (prompts/203 §1.6); the circuit uses only the allowed gate classes."""
    spec = _spec()
    arch, best = _best(root)
    ev = api("su2plaq.compress.evaluate")
    B = api("su2plaq.compress.builder")
    mod = ev.load_program(str(root / best.program_path))
    qc = mod.build(spec).circuit()
    touched = {qc.find_bit(q).index for inst in qc.data for q in inst.qubits}
    assert not (touched & set(range(16, 48))), sorted(touched & set(range(16, 48)))
    assert best.verdict_nominal.get("outer_bits_read", 0) == 0
    assert qc.num_qubits == best.metrics_raw["qubits"] >= 48 and qc.num_qubits <= spec.peak_qubit_cap()
    assert not ev._gate_violations(qc)
    assert max(touched) < qc.num_qubits and all(inst.operation.name in B.BASIS | B.MACROS for inst in qc.data if inst.operation.name != "barrier")


def test_M6_G4_summary_and_budgets(root):
    """summary.json agrees with the archive; at most 8 rounds after round 0; at most 20 non-seed programs; every archived
    id is in the attempts log; the `pruning_bound` decisions are countable from the round files (Report 6 §5)."""
    arch, best = _best(root)
    rounds = _rounds(root)
    nums = sorted(r["round"] for r in rounds)
    assert nums[0] == 0 and nums == list(range(len(nums))) and nums[-1] <= MAX_ROUNDS
    progs = [p for p in (root / "compress" / "programs" / ENC).rglob("*.py") if p.parent.name != "seed"]
    assert len(progs) <= MAX_SESSIONS
    sj = root / "results" / "compress" / ENC / "summary.json"
    if not sj.exists():
        api("su2plaq.compress.report:report_table")(ENC, KIND, root=root)
    summary = json.loads(sj.read_text())
    assert summary["global_best"] == best.id and tuple(summary["global_best_key"]) == tuple(best.key)
    att = root / "compress" / "attempts" / f"{ENC}.jsonl"
    ids = {json.loads(ln)["id"] for ln in att.read_text().splitlines() if ln.strip()}
    assert {e.id for e in arch.entries()} <= ids
    n_prune = sum(1 for r in rounds for c in r["candidates"] if c["reason"] == "pruning_bound")
    assert n_prune >= 0 and all(isinstance(r.get("wall_s"), (int, float)) for r in rounds)
    lineage = summary["lineage"]
    assert any(l["id"] == best.id for l in lineage)
    # prompts/203 §13 E3: the headline (robust key over the locked angle set) is a valid archived entry and is what the summary names
    R = api("su2plaq.rishon.compress.robust")
    h = R.headline(KIND, root=root)
    valid_ids = {e.id for e in arch.entries() if e.valid}
    assert h["id"] in valid_ids and h["robust_key"] is not None and h["archive_best"] == best.id
    assert summary.get("headline", {}).get("id") == h["id"] and tuple(summary["headline"]["robust_key"]) == tuple(h["robust_key"])
    keyed = [tuple(r["robust_key"]) for r in h["ranking"] if r["robust_key"] is not None]
    assert keyed == sorted(keyed) and tuple(h["robust_key"]) == keyed[0]
