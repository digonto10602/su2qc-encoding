"""Independent archive checks (tester, M2 step 2.4): seeded random insert sequences vs a brute-force model."""
import json, math, os, pathlib, random, sys, tempfile, hashlib, copy
import numpy as np
sys.path.insert(0, "src")
from su2plaq.compress import archive as A

OUT = {"seed": 20261105}
rng = random.Random(20261105)


NALT = 2
def mk(id_, cx, t, d, q, family, valid=True, reason="ok", cell=None, key=None, nalt=None, metrics=None, vn=None, **kw):
    k = (cx, t, d, q) if key is None else key
    nalt = NALT if nalt is None else nalt
    metrics = {"cx": cx, "t_eps": t, "depth_ct": d, "qubits": q} if metrics is None else metrics
    c = cell if cell is not None else (int(math.floor(8 * math.log2(cx + 1))), int(math.floor(8 * math.log2(t + 1))))
    return A.Entry(id=id_, program_path=f"p/{id_}.py", program_sha256="a" * 64, parent=None, family=family, round=1,
                   valid=valid, reason=reason, key=k, cell=c, metrics_raw=metrics, metrics_polished=None,
                   verdict_nominal=({"ok": valid, "certified": True} if vn is None else vn), verdicts_alt=[{"ok": True, "certified": True} for _ in range(nalt)], skeleton_equal=True, discoveries=[], summary="s",
                   evaluator_sha256="e" * 64, spec_sha256="s" * 64, git_commit="0000000", versions={"q": "2"}, seeds={},
                   machine="m", wall_s=0.1, written_utc="2026-11-05T00:00:00Z", **kw)


def snapshot(arch):
    return json.dumps([e.to_dict() for e in sorted(arch.entries(), key=lambda e: e.id)], sort_keys=True)


res = {"trials": 0, "insert_ok": 0, "refused": 0, "elite_mismatch": 0, "best_mismatch": 0, "fam_mismatch": 0, "changed_on_refusal": 0,
       "roundtrip_mismatch": 0, "bytes_unstable_entries": 0, "ties": 0}
fams = ["F1", "F2", "F3", "F4"]
for trial in range(300):
    with tempfile.TemporaryDirectory() as td:
        arch = A.Archive.load("twelve", root=td, n_alt=NALT)
        model = {}
        n = rng.randint(1, 40)
        for i in range(n):
            # small key ranges force ties and cell collisions
            cx, t, d, q = rng.randint(0, 40), rng.randint(0, 60), rng.randint(0, 5), rng.randint(0, 3)
            kind = rng.choice(["ok"] * 6 + ["invalid", "unverified", "inf", "nan", "dup"])
            id_ = f"r01-{rng.choice(fams)}-{i:03d}"
            fam = id_.split("-")[1]
            before = snapshot(arch)
            if kind == "ok":
                e = mk(id_, cx, t, d, q, fam)
                assert arch.insert(e) is True
                model[id_] = e; res["insert_ok"] += 1
                continue
            if kind == "invalid":
                e = mk(id_, cx, t, d, q, fam, valid=False, reason="error", key=(math.inf,) * 4)
            elif kind == "unverified":
                e = mk(id_, cx, t, d, q, fam, valid=True, reason="unverified")
            elif kind == "inf":
                e = mk(id_, cx, t, d, q, fam, key=(cx, math.inf, d, q), metrics={"cx": cx, "t_eps": math.inf, "depth_ct": d, "qubits": q})
            elif kind == "nan":
                e = mk(id_, cx, t, d, q, fam, key=(cx, float("nan"), d, q), metrics={"cx": cx, "t_eps": float("nan"), "depth_ct": d, "qubits": q})
            elif kind == "dup" and model:
                dup = rng.choice(list(model))
                e = mk(dup, cx, t, d, q, dup.split("-")[1])
                try:
                    r = arch.insert(e); assert r is False
                except ValueError:
                    pass
                res["refused"] += 1
                if snapshot(arch) != before: res["changed_on_refusal"] += 1
                continue
            else:
                continue
            r = arch.insert(e)
            res["refused"] += 1
            if r is not False or snapshot(arch) != before: res["changed_on_refusal"] += 1
        # model: brute force
        el = {}
        for e in model.values():
            c = tuple(e.cell)
            if c not in el or (tuple(e.key), e.id) < (tuple(el[c].key), el[c].id): el[c] = e
        got = arch.elites()
        if {c: e.id for c, e in got.items()} != {c: e.id for c, e in el.items()}: res["elite_mismatch"] += 1
        # every elite has the min key in its cell
        for c, e in got.items():
            assert all(tuple(e.key) <= tuple(x.key) for x in model.values() if tuple(x.cell) == c)
        b = min(model.values(), key=lambda e: (tuple(e.key), e.id), default=None)
        if (arch.best().id if arch.best() else None) != (b.id if b else None): res["best_mismatch"] += 1
        # best has global min key
        if model: assert tuple(arch.best().key) == min(tuple(e.key) for e in model.values())
        for f in fams:
            fb = min((e for e in model.values() if e.family == f), key=lambda e: (tuple(e.key), e.id), default=None)
            if (arch.family_best(f).id if arch.family_best(f) else None) != (fb.id if fb else None): res["fam_mismatch"] += 1
        # best is elite of its cell
        if model: assert arch.best().id in {e.id for e in got.values()}
        # round trip
        arch.save()
        d = pathlib.Path(td) / "compress/archive/twelve"
        bytes1 = {p.name: p.read_bytes() for p in sorted((d / "entries").glob("*.json"))}
        a2 = A.Archive.load("twelve", root=td, n_alt=NALT)
        if snapshot(a2) != snapshot(arch): res["roundtrip_mismatch"] += 1
        if {c: e.id for c, e in a2.elites().items()} != {c: e.id for c, e in got.items()}: res["roundtrip_mismatch"] += 1
        a2.save()
        bytes2 = {p.name: p.read_bytes() for p in sorted((d / "entries").glob("*.json"))}
        if bytes1 != bytes2: res["bytes_unstable_entries"] += 1
        idx = json.loads((d / "index.json").read_text())
        assert idx["n_entries"] == len(model) and idx["best"] == (b.id if b else None)
        assert not list(d.rglob("*.tmp"))
        res["trials"] += 1
OUT["random_sequences"] = res
print(res)

# ---- index byte stability (save twice, different seconds)
import time
with tempfile.TemporaryDirectory() as td:
    arch = A.Archive.load("twelve", root=td, n_alt=NALT); arch.insert(mk("r01-F1-001", 1, 2, 3, 4, "F1")); arch.save()
    i1 = (pathlib.Path(td) / "compress/archive/twelve/index.json").read_bytes(); time.sleep(1.1); arch.save()
    i2 = (pathlib.Path(td) / "compress/archive/twelve/index.json").read_bytes()
    j1, j2 = json.loads(i1), json.loads(i2); w1, w2 = j1.pop("written_utc"), j2.pop("written_utc")
    OUT["index_bytes_identical_across_saves"] = i1 == i2
    OUT["index_equal_except_timestamp"] = j1 == j2

# ---- hardening probes: things insert() must now refuse
import dataclasses as dc
probe = {}
def tryins(name, e, n_alt=NALT):
    with tempfile.TemporaryDirectory() as td:
        arch = A.Archive.load("twelve", root=td, n_alt=n_alt)
        try: r = bool(arch.insert(e)); probe[name] = (r, arch.rejected[-1][1] if arch.rejected else None, len(arch.entries()))
        except Exception as ex: probe[name] = f"raises {type(ex).__name__}"
def v(**kw):
    e = mk("r01-F1-001", 3, 4, 5, 6, "F1")
    for k_, x in kw.items(): setattr(e, k_, x)
    return e
tryins("control_valid_entry(expect True)", v())
tryins("trial_mode", v(mode="trial"))
tryins("skeleton_equal_False", v(skeleton_equal=False))
tryins("verdict_nominal_not_ok", v(verdict_nominal={"ok": False, "certified": False}))
tryins("verdict_nominal_ok_not_certified", v(verdict_nominal={"ok": True, "certified": False}))
tryins("verdict_nominal_empty", v(verdict_nominal={}))
tryins("verdict_nominal_ok_without_certified_field", v(verdict_nominal={"ok": True}))
tryins("alt_not_ok", v(verdicts_alt=[{"ok": True, "certified": True}, {"ok": False, "certified": True}]))
tryins("alt_not_certified", v(verdicts_alt=[{"ok": True, "certified": True}, {"ok": True, "certified": False}]))
tryins("alt_empty_dict", v(verdicts_alt=[{"ok": True, "certified": True}, {}]))
tryins("alt_count_0_with_n_alt2", v(verdicts_alt=[]))
tryins("alt_count_1_with_n_alt2", v(verdicts_alt=[{"ok": True, "certified": True}]))
tryins("alt_count_3_with_n_alt2", v(verdicts_alt=[{"ok": True, "certified": True}] * 3))
tryins("alt_count_0_with_n_alt0(default)", v(verdicts_alt=[]), n_alt=0)
tryins("cell_inconsistent_with_key", v(cell=(999, 999)))
tryins("key_inconsistent_with_metrics(lower key)", v(key=(0, 0, 0, 0), cell=(0, 0)))
tryins("metrics_missing_field", v(metrics_raw={"cx": 3, "t_eps": 4, "depth_ct": 5}))
tryins("metrics_empty", v(metrics_raw={}))
tryins("metrics_string_values", v(metrics_raw={"cx": "3", "t_eps": 4, "depth_ct": 5, "qubits": 6}))
tryins("metrics_negative", v(metrics_raw={"cx": -3, "t_eps": -4, "depth_ct": 5, "qubits": 6}, key=(-3, -4, 5, 6), cell=(0, 0)))
tryins("metrics_bool", v(metrics_raw={"cx": True, "t_eps": 4, "depth_ct": 5, "qubits": 6}, key=(True, 4, 5, 6)))
tryins("key_with_numpy_int64", v(key=(np.int64(3), np.float64(4), np.int32(5), np.int64(6))))
tryins("numpy_metrics_and_key", v(metrics_raw={"cx": np.int64(3), "t_eps": np.float64(4), "depth_ct": np.int64(5), "qubits": np.int64(6)}, key=(np.int64(3), np.float64(4), np.int64(5), np.int64(6))))
for bad in ("../../../escape", "r01-F1-001/../../x", "r01-F1-0 01", "", "r01-" + "a" * 200, "/abs/path", "r01-F1-001\n", "R01-F1-001", "r01..F1", "r1-F1-001", "r01-F1-001.json", "..", "r01-F1-001\x00x", "r01-é"):
    tryins(f"id={bad!r}", v(id=bad))
tryins("id_non_str", v(id=7))
OUT["insert_probes"] = probe
for k_, x in probe.items(): print(k_, x)

# ---- path traversal at save: bypass insert by writing into the private dict
with tempfile.TemporaryDirectory() as td:
    arch = A.Archive.load("twelve", root=td, n_alt=NALT)
    e = mk("r01-F1-001", 3, 4, 5, 6, "F1"); arch._entries["../../../escape"] = dc.replace(e, id="../../../escape")
    try: arch.save(); esc = [str(p) for p in pathlib.Path(td).rglob("escape*")]
    except Exception as ex: esc = f"raises {type(ex).__name__}: {ex}"
    OUT["path_traversal_save_via_private_dict"] = esc
    arch = A.Archive.load("twelve", root=td, n_alt=NALT)
    e = mk("r01-F1-001", 3, 4, 5, 6, "F1"); e.key = (0, 0, 0, 0); arch._entries[e.id] = e
    try: arch.save(); saved = "saved"
    except Exception as ex: saved = f"raises {type(ex).__name__}"
    OUT["save_of_mutated_entry"] = saved
    print("traversal:", OUT["path_traversal_save_via_private_dict"], "| mutated:", saved)
    # in-place mutation after insert
    arch = A.Archive.load("twelve", root=td, n_alt=NALT); e = mk("r01-F1-002", 3, 4, 5, 6, "F1"); arch.insert(e); e.verdict_nominal = {"ok": False}
    try: arch.save(); OUT["save_after_inplace_mutation"] = "saved"
    except Exception as ex: OUT["save_after_inplace_mutation"] = f"raises {type(ex).__name__}"
    print(OUT["save_after_inplace_mutation"])

# ---- load-time attacks: hand-edited / hand-written entry files
def load_attack(name, mutate, fname=None, n_alt=NALT):
    with tempfile.TemporaryDirectory() as td:
        arch = A.Archive.load("twelve", root=td, n_alt=n_alt); arch.insert(mk("r01-F1-001", 30, 40, 5, 6, "F1")); arch.save()
        ed = pathlib.Path(td) / "compress/archive/twelve/entries"
        d = json.loads((ed / "r01-F1-001.json").read_text())
        d2 = mutate(copy.deepcopy(d))
        target = ed / (fname or "r01-F1-001.json")
        if d2 == "raw-garbage": target.write_text("\x00{{{")
        elif d2 is not None: target.write_text(json.dumps(d2))
        a2 = A.Archive.load("twelve", root=td, n_alt=n_alt)
        ids = sorted(e.id for e in a2.entries())
        return dict(loaded=ids, best=a2.best().id if a2.best() else None, rejected=[(f, w[:50]) for f, w in a2.rejected])
LA = {}
LA["control_unmodified"] = load_attack("c", lambda d: d)
LA["valid_false"] = load_attack("a", lambda d: {**d, "valid": False, "reason": "error"})
LA["forged_better_key_only"] = load_attack("b", lambda d: {**d, "key": [0, 0, 0, 0], "cell": [0, 0]})
def forged_consistent(d):   # fully consistent forgery: metrics, key, cell all zero
    d["metrics_raw"] = {"cx": 0, "t_eps": 0, "depth_ct": 0, "qubits": 0}; d["key"] = [0, 0, 0, 0]; d["cell"] = [0, 0]; d["id"] = "r99-F1-777"; return d
LA["new_file_fully_consistent_forgery(expected accepted: files are not authenticated)"] = load_attack("d", forged_consistent, fname="r99-F1-777.json")
LA["file_name_not_id"] = load_attack("e", lambda d: {**d, "id": "r05-F1-005"})
LA["trial_mode_file"] = load_attack("f", lambda d: {**d, "mode": "trial"})
LA["alt_removed_n_alt2"] = load_attack("g", lambda d: {**d, "verdicts_alt": []})
LA["alt_removed_n_alt0_default"] = load_attack("g0", lambda d: {**d, "verdicts_alt": []}, n_alt=0)
LA["verdict_flipped"] = load_attack("h", lambda d: {**d, "verdict_nominal": {"ok": False, "certified": False}})
LA["garbage_file"] = load_attack("i", lambda d: "raw-garbage")
LA["missing_field"] = load_attack("j", lambda d: {k: x for k, x in d.items() if k != "metrics_raw"})
LA["id_with_traversal_inside_file"] = load_attack("k", lambda d: {**d, "id": "../x"}, fname="r01-F1-001.json")
LA["metrics_changed_key_not"] = load_attack("l", lambda d: {**d, "metrics_raw": {**d["metrics_raw"], "cx": 1}})
OUT["load_attacks"] = LA
for k_, x in LA.items(): print(k_, x)

# ---- atomic write: simulated kill mid-save at every os-level step
import unittest.mock as mock
with tempfile.TemporaryDirectory() as td:
    arch = A.Archive.load("twelve", root=td, n_alt=NALT)
    for i in range(6): arch.insert(mk(f"r01-F1-{i:03d}", 10 + i, 20 - i, 3, 4, "F1"))
    arch.save()
    d = pathlib.Path(td) / "compress/archive/twelve"
    base_idx = (d / "index.json").read_bytes()
    base_entries = {p.name: p.read_bytes() for p in (d / "entries").glob("*.json")}
    arch.insert(mk("r01-F2-000", 1, 1, 1, 1, "F2"))
    # kill during tmp write (partial tmp) at the k-th write, and kill at the k-th replace
    real_replace = pathlib.Path.replace; real_write = pathlib.Path.write_text
    results = []
    for mode in ("kill_in_write", "kill_before_replace"):
        for k in range(1, 9):
            # reset on-disk state
            for p in list(d.rglob("*")):
                if p.is_file(): p.unlink()
            (d / "entries").mkdir(parents=True, exist_ok=True)
            for n_, b_ in base_entries.items(): (d / "entries" / n_).write_bytes(b_)
            (d / "index.json").write_bytes(base_idx)
            cnt = {"w": 0, "r": 0}
            def fw(self, data, *a, **kw):
                cnt["w"] += 1
                if mode == "kill_in_write" and cnt["w"] == k:
                    real_write(self, data[: len(data) // 2], *a, **kw); raise KeyboardInterrupt("kill")
                return real_write(self, data, *a, **kw)
            def fr(self, target):
                cnt["r"] += 1
                if mode == "kill_before_replace" and cnt["r"] == k: raise KeyboardInterrupt("kill")
                return real_replace(self, target)
            killed = False
            with mock.patch.object(pathlib.Path, "write_text", fw), mock.patch.object(pathlib.Path, "replace", fr):
                try: arch.save()
                except KeyboardInterrupt: killed = True
            # state after the "crash"
            idx_ok = True
            try: json.loads((d / "index.json").read_text())
            except Exception: idx_ok = False
            finals = list((d / "entries").glob("*.json"))
            partial = []
            for p in finals:
                try: json.loads(p.read_text())
                except Exception: partial.append(p.name)
            try: a2 = A.Archive.load("twelve", root=td, n_alt=NALT); load_ok = True; n = len(a2.entries())
            except Exception as ex: load_ok = False; n = -1
            idx = json.loads((d / "index.json").read_text())
            results.append(dict(mode=mode, k=k, killed=killed, index_parses=idx_ok, partial_final_files=partial, load_ok=load_ok,
                                n_loaded=n, index_n=idx["n_entries"], index_unchanged=(d / "index.json").read_bytes() == base_idx))
    bad = [r for r in results if r["killed"] and (not r["index_parses"] or r["partial_final_files"] or not r["load_ok"])]
    OUT["atomic"] = {"cases": len(results), "killed": sum(r["killed"] for r in results), "bad": len(bad), "detail_first": results[:3],
                     "index_vs_entries_inconsistent_after_kill": sum(1 for r in results if r["killed"] and r["n_loaded"] != r["index_n"])}
    print(OUT["atomic"]["cases"], OUT["atomic"]["killed"], "bad", len(bad), "idx/entries inconsistent", OUT["atomic"]["index_vs_entries_inconsistent_after_kill"])

json.dump(OUT, open("results/tester_m2_step2_4_recheck_archive_props.json", "w"), indent=1, default=str)
