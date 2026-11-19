"""Tester 436: stop_state / improves of su2plaq.lsh.loop on synthetic stop.json and attempts logs (prompts/401 1.6, METHODS-lsh L14).
Independent of the builder's unit tests; the expected values are derived from the rule text, not from the implementation."""
import json
import pathlib

import pytest

from su2plaq.lsh import loop as LL


def rec(i, cx, t, rho=0, q=25, n=17, tf=48):
    return {"id": f"r{i:02d}-X", "cx": cx, "t_sum": t, "rho": rho, "qubits": q, "n_rot": n, "t_fixed": tf}


def write(root: pathlib.Path, recs, attempts=(), ideation=False):
    f = root / "results" / "compress" / "lsh"
    f.mkdir(parents=True, exist_ok=True)
    rounds = [{"round": i, "headline_id": r["id"], "robust_key": [r["cx"], r["t_sum"], r["rho"], 0, r["qubits"]], "record": r}
              for i, r in enumerate(recs)]
    (f / "stop.json").write_text(json.dumps({"rounds": rounds}))
    a = root / "compress" / "attempts"
    a.mkdir(parents=True, exist_ok=True)
    (a / "lsh.jsonl").write_text("".join(json.dumps({"id": f"x{k}", "round": r, "family": fam}) + "\n" for k, (r, fam) in enumerate(attempts)))
    idf = root / "compress" / "ideation" / "lsh.md"
    if ideation:
        idf.parent.mkdir(parents=True, exist_ok=True)
        idf.write_text("ideation")
    elif idf.exists():
        idf.unlink()


def test_round0_improves_and_streak_counting(tmp_path):
    write(tmp_path, [rec(0, 71, 22480), rec(1, 71, 22480), rec(2, 72, 20000), rec(3, 71, 22500)])
    s = LL.stop_state(tmp_path)
    assert [r["improved"] for r in s["rounds"]] == [True, False, False, False]    # 3: tie within band 20*17=340, same structure, same (rho, q)
    assert s["streak"] == 3 and s["stop"] and s["reason"] == "no_gain"
    write(tmp_path, [rec(0, 71, 22480), rec(1, 71, 22480), rec(2, 72, 20000)])
    s = LL.stop_state(tmp_path)
    assert s["streak"] == 2 and not s["stop"] and s["reason"] is None


def test_improvement_resets_streak(tmp_path):
    write(tmp_path, [rec(0, 71, 22480), rec(1, 71, 22480), rec(2, 71, 22480), rec(3, 70, 23000), rec(4, 70, 23000)])
    s = LL.stop_state(tmp_path)
    assert [r["improved"] for r in s["rounds"]] == [True, False, False, True, False]
    assert s["streak"] == 1 and not s["stop"]


def test_band_is_against_last_improving_record_not_last_round(tmp_path):
    # n_rot = 1 -> band 20.  r0 1000; r1 995 (tie), r2 990 (tie), r3 985 (tie) ... drift never accumulates; r4 970 is 30 below r0 -> improves
    recs = [rec(0, 40, 1000, n=1), rec(1, 40, 995, n=1), rec(2, 40, 990, n=1), rec(3, 40, 985, n=1), rec(4, 40, 970, n=1)]
    s = LL.stop_state(write(tmp_path, recs) or tmp_path)
    assert [r["improved"] for r in s["rounds"]] == [True, False, False, False, True]


def test_band_edges_and_structure_change(tmp_path):
    a = rec(0, 40, 1000, n=1)
    assert not LL.improves(rec(1, 40, 980, n=1), a)          # exactly 20: tie
    assert LL.improves(rec(1, 40, 979, n=1), a)              # 21: improvement
    assert not LL.improves(rec(1, 40, 1019, n=1), a)         # worse by 19: tie, same (rho, q)
    assert LL.improves(rec(1, 40, 1019, n=1, q=24), a)       # tie decided by qubits
    assert LL.improves(rec(1, 40, 1010, n=1, rho=0), rec(0, 40, 1000, n=1, rho=1))   # tie decided by rho
    assert LL.improves(rec(1, 40, 1000, n=1, tf=47), a) is False   # t_sum equal, fewer fixed T: structure changed -> plain comparison: equal -> no
    assert LL.improves(rec(1, 40, 990, n=1, tf=47), a) is True    # structure changed (t_fixed): plain lexicographic, 990 < 1000 counts
    assert LL.improves(rec(1, 39, 5000, n=1), a)             # fewer CX always improves
    assert not LL.improves(rec(1, 41, 1, n=1), a)            # more CX never improves
    assert not LL.improves(None, a) and LL.improves(a, None)


def test_sessions_and_max_sessions(tmp_path):
    att = [(0, "seed")] * 10 + [(1, "F1"), (1, "F1"), (1, "F2"), (2, "F1")]
    write(tmp_path, [rec(0, 71, 22480)], attempts=att)
    assert LL.stop_state(tmp_path)["sessions"] == 3              # distinct (round>=1, family); round 0 not counted; no ideation
    write(tmp_path, [rec(0, 71, 22480)], attempts=att, ideation=True)
    assert LL.stop_state(tmp_path)["sessions"] == 4              # ideation counts one
    att20 = [(r, f"F{k}") for r in (1, 2, 3, 4) for k in range(5)]    # 20 distinct sessions
    write(tmp_path, [rec(0, 71, 22480)], attempts=att20)
    s = LL.stop_state(tmp_path)
    assert s["sessions"] == 20 and s["stop"] and s["reason"] == "max_sessions"
    write(tmp_path, [rec(0, 71, 22480)], attempts=att20[:-1])
    s = LL.stop_state(tmp_path)
    assert s["sessions"] == 19 and not s["stop"]
    write(tmp_path, [rec(0, 71, 22480)], attempts=att20[:-1], ideation=True)
    s = LL.stop_state(tmp_path)
    assert s["sessions"] == 20 and s["reason"] == "max_sessions"  # 19 + ideation


def test_max_rounds(tmp_path):
    recs = [rec(i, 71 - i, 22480) for i in range(9)]               # improves every round: no_gain never
    write(tmp_path, recs[:8])
    s = LL.stop_state(tmp_path)
    assert s["streak"] == 0 and not s["stop"]                      # last round = 7
    write(tmp_path, recs)
    s = LL.stop_state(tmp_path)
    assert s["stop"] and s["reason"] == "max_rounds" and s["rounds"][-1]["round"] == 8


def test_empty_root(tmp_path):
    s = LL.stop_state(tmp_path)
    assert s["rounds"] == [] and s["streak"] == 0 and not s["stop"] and s["sessions"] == 0


def test_constants():
    assert (LL.STOP_MAX_ROUNDS, LL.STOP_NO_GAIN_ROUNDS, LL.STOP_MAX_SESSIONS, LL.T_NOISE_PER_ROTATION, LL.N_ANGLE_PAIRS) == (8, 3, 20, 1, 20)
