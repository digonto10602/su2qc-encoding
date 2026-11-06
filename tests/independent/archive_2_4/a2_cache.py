"""Independent cache checks (tester, M2 step 2.4)."""
import dataclasses, json, pathlib, shutil, sys, tempfile, time, copy
sys.path.insert(0, "src")
from su2plaq.compress import evaluate as E, provenance as P, archive as A
from su2plaq.compress.spec import default_spec

SCR = pathlib.Path(sys.argv[1])
OUT = {}
SPEC = default_spec("twelve", "UE")
GOOD = SCR / "prog" / "001-ue.py"
BAD = SCR / "prog" / "002-bad.py"
BAD.write_text(GOOD.read_text().replace("-0.75", "+0.75"))

calls = []
real = E._evaluate_program_bytes
E._evaluate_program_bytes = lambda *a, **k: calls.append(1) or real(*a, **k)
def ncalls(): n = len(calls); calls.clear(); return n

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    t0 = time.time(); r1 = E.evaluate_program(GOOD, SPEC, "full", cache=True, root=root); t1 = time.time() - t0
    n1 = ncalls()
    t0 = time.time(); r2 = E.evaluate_program(GOOD, SPEC, "full", cache=True, root=root); t2 = time.time() - t0
    n2 = ncalls()
    OUT["A_miss_then_hit"] = dict(evals_first=n1, evals_second=n2, t_first=round(t1, 2), t_second=round(t2, 3), valid=r2.valid,
                                  same_key=r1.metrics == r2.metrics, same_verdict=r1.verdict.op_norm_error == r2.verdict.op_norm_error,
                                  files=len(list((root / "compress/cache").rglob("*.json"))))
    # hit regardless of path (content-keyed)
    cp = SCR / "prog" / "copy-of-001.py"; cp.write_bytes(GOOD.read_bytes())
    E.evaluate_program(cp, SPEC, "full", cache=True, root=root); OUT["A_same_bytes_other_path_hit"] = ncalls() == 0
    # C: one program byte
    gb = SCR / "prog" / "003-onebyte.py"; gb.write_bytes(GOOD.read_bytes() + b"#\n")
    E.evaluate_program(gb, SPEC, "full", cache=True, root=root); OUT["C_program_byte_edit_miss"] = ncalls() == 1
    # D: each spec field
    base = SPEC.sha256(); alt = {"alpha": 0.38, "beta": 0.62, "order": 2, "alt_angles": ((0.5, 0.5),), "tol_err": 1e-9, "tol_gauss": 1e-9,
           "eps": 1e-5, "eval_budget_s": 299.0, "support_cap": 4_000_000, "max_qubits": 40, "cell_k": 9, "trial_inputs": 63,
           "trial_seed": 1, "kind": "UB", "encoding": "twelve2"}
    fields = {}
    for k, v in alt.items():
        try:
            s2 = dataclasses.replace(SPEC, **{k: v}) if k != "encoding" else dataclasses.replace(SPEC, encoding=v)
            fields[k] = s2.sha256() != base
        except Exception as ex: fields[k] = f"err {ex}"
    OUT["D_spec_fields_change_sha"] = fields
    allf = {f.name for f in dataclasses.fields(SPEC)}
    OUT["D_fields_not_probed"] = sorted(allf - set(alt))
    # real miss for two spec edits through evaluate_program (cheap ones: eps and tol)
    for k, v in (("eps", 1e-5), ("tol_err", 1e-9)):
        E.evaluate_program(GOOD, dataclasses.replace(SPEC, **{k: v}), "full", cache=True, root=root); OUT[f"D_spec_{k}_miss"] = ncalls() == 1
    # E: trial not cached, and trial after full not served from cache
    nfiles = len(list((root / "compress/cache").rglob("*.json")))
    rt = E.evaluate_program(GOOD, SPEC, "trial", cache=True, root=root)
    OUT["E_trial_not_cached"] = dict(evals=ncalls(), files_before=nfiles, files_after=len(list((root / "compress/cache").rglob("*.json"))), mode=rt.mode)
    rt2 = E.evaluate_program(GOOD, SPEC, "trial", cache=True, root=root); OUT["E_trial_twice_reevaluates"] = ncalls() == 1
    # any file under cache with mode trial?
    OUT["E_cached_modes"] = sorted({json.loads(p.read_text())["payload"]["mode"] for p in (root / "compress/cache").rglob("*.json")})

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    # B: edit one evaluator source file in a COPY of the tree
    cp = pathlib.Path(td) / "srccopy"; shutil.copytree("src/su2plaq", cp, ignore=shutil.ignore_patterns("__pycache__"))
    realsrc = P._SRC; P._SRC = cp
    h0 = P.code_hash(); per_file = {}
    for f in P.EVALUATOR_FILES:
        fp = cp / f
        if not fp.exists(): per_file[f] = "missing"; continue
        orig = fp.read_bytes(); fp.write_bytes(orig + b"\n# x\n"); per_file[f] = P.code_hash() != h0; fp.write_bytes(orig)
    OUT["B_each_evaluator_file_edit_changes_hash"] = per_file
    OUT["B_all_changed"] = all(v is True for v in per_file.values())
    # files that are NOT in the list but under src/su2plaq/compress, evaluate, metrics, results, encodings, exact, su2 -> no effect
    other = {}
    for fp in sorted(cp.rglob("*.py")):
        rel = str(fp.relative_to(cp))
        if rel in P.EVALUATOR_FILES: continue
        orig = fp.read_bytes(); fp.write_bytes(orig + b"\n# x\n"); other[rel] = P.code_hash() != h0; fp.write_bytes(orig)
    OUT["B_unlisted_files_that_do_not_change_hash"] = sorted(k for k, v in other.items() if not v)
    P._SRC = realsrc
    # through evaluate_program: patch code_hash to use the edited copy
    E.evaluate_program(GOOD, SPEC, "full", cache=True, root=root); ncalls()
    (cp / "compress/synth.py").write_bytes((cp / "compress/synth.py").read_bytes() + b"\n#edit\n")
    P._SRC = cp
    E.evaluate_program(GOOD, SPEC, "full", cache=True, root=root); OUT["B_evaluate_program_miss_after_evaluator_edit"] = ncalls() == 1
    P._SRC = realsrc
    E.evaluate_program(GOOD, SPEC, "full", cache=True, root=root); OUT["B_back_to_original_hits_old_entry"] = ncalls() == 0

# F: tampering (new format {meta, payload, checksum})
import hashlib
def canon(o): return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)
def reseal(d): d["checksum"] = hashlib.sha256(canon({"meta": d["meta"], "payload": d["payload"]}).encode()).hexdigest(); return d
def shas(path): return path.read_text()
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    rb = E.evaluate_program(BAD, SPEC, "full", cache=True, root=root); ncalls()
    OUT["F_bad_program_uncached_result"] = dict(valid=rb.valid, reason=rb.reason, op_norm=rb.verdict.op_norm_error if rb.verdict else None)
    (cache_file,) = list((root / "compress/cache").rglob("*.json"))
    orig = cache_file.read_text(); od = json.loads(orig)
    OUT["F_file_keys"] = sorted(od)
    def attempt(name, mutate, restore=True):
        d = json.loads(orig); mutate(d); cache_file.write_text(json.dumps(d))
        r_ = E.evaluate_program(BAD, SPEC, "full", cache=True, root=root); n_ = ncalls()
        out = dict(reevaluated=n_ == 1, returned_valid=r_.valid, returned_reason=r_.reason, cx=(r_.metrics or {}).get("cx"))
        healed = json.loads(cache_file.read_text()) != d
        out["file_overwritten_with_fresh"] = healed
        cache_file.write_text(orig)
        return out
    def flip_valid(d): d["payload"]["valid"] = True; d["payload"]["reason"] = "ok"
    def metrics_zero(d): d["payload"]["metrics"].update(cx=0, t_eps=0, depth_ct=0, qubits=0)
    def valid_resealed_only(d): flip_valid(d); reseal(d)
    def valid_and_verdict_not_certified(d):
        flip_valid(d); d["payload"]["skeleton_equal"] = True; reseal(d)
    def full_consistent_forgery(d):
        p_ = d["payload"]; p_["valid"] = True; p_["reason"] = "ok"; p_["skeleton_equal"] = True
        for v_ in [p_["verdict"]] + p_["verdicts_alt"]: v_["ok"] = True; v_["certified"] = True
        p_["metrics"].update(cx=0, t_eps=1, depth_ct=1, qubits=1)
        reseal(d)
    def forged_full_but_alt_missing(d):
        p_ = d["payload"]; p_["valid"] = True; p_["reason"] = "ok"; p_["skeleton_equal"] = True; p_["verdicts_alt"] = []
        p_["verdict"]["ok"] = True; p_["verdict"]["certified"] = True; reseal(d)
    def meta_edit_only(d): d["meta"]["program_sha256"] = "0" * 64
    def mode_trial_resealed(d): d["payload"]["mode"] = "trial"; reseal(d)
    def checksum_wrong(d): d["checksum"] = "0" * 64; flip_valid(d)
    def drop_checksum(d): del d["checksum"]; flip_valid(d)
    def evaluator_sha_other_resealed(d): d["meta"]["evaluator_sha256"] = "f" * 64; reseal(d)
    F = {}
    for name, fn in {"1_payload_valid_flipped_stale_checksum": flip_valid, "2_payload_metrics_zero_stale_checksum": metrics_zero,
                     "3_valid_flipped_checksum_recomputed_but_verdict_not_ok": valid_resealed_only,
                     "4_checksum_garbage": checksum_wrong, "5_checksum_missing": drop_checksum,
                     "6_meta_program_sha_edited_stale_checksum": meta_edit_only, "7_mode_trial_resealed": mode_trial_resealed,
                     "8_meta_other_evaluator_sha_resealed": evaluator_sha_other_resealed,
                     "9_valid_resealed_alt_verdicts_removed": forged_full_but_alt_missing,
                     "10_FULLY_CONSISTENT_FORGERY_resealed": full_consistent_forgery}.items():
        F[name] = attempt(name, fn)
    OUT["F_tamper"] = F
    # --- consequences of case 10: archive and gate
    d = json.loads(orig); full_consistent_forgery(d); cache_file.write_text(json.dumps(d))
    r_forged = E.evaluate_program(BAD, SPEC, "full", cache=True, root=root); ncalls()
    arch = A.Archive.load("twelve", root=root, n_alt=len(SPEC.alt_angles))
    e = A.entry_from_result(r_forged, program_path=str(BAD), family="F9", round=1, parent=None)
    ins = arch.insert(e); arch.save()
    a2 = A.Archive.load("twelve", root=root, n_alt=len(SPEC.alt_angles))
    best = a2.best()
    # the gate: re-evaluate the best entry from its program source (no cache), compare with the recorded key
    fresh = E.evaluate_program(best.program_path, SPEC, "full", cache=False, root=root) if best else None
    from collections import OrderedDict
    OUT["F10_archive_and_gate"] = dict(forged_result_valid=r_forged.valid, archive_insert_accepts_forged=ins, best_id=best.id if best else None,
        recorded_key=list(best.key) if best else None, gate_fresh_valid=fresh.valid if fresh else None, gate_fresh_reason=fresh.reason if fresh else None,
        gate_fresh_key=[fresh.metrics.get(k) for k in ("cx", "t_eps", "depth_ct", "qubits")] if fresh and fresh.metrics else None,
        gate_catches=bool(fresh is not None and (not fresh.valid)))
    # the real gate test's own predicate (acceptance test_archive_best_valid...): valid AND recorded key == fresh key
    cache_file.write_text(orig)
    # G: result of program A copied to program B's slot, in several ways
    ra = E.evaluate_program(GOOD, SPEC, "full", cache=True, root=root); ncalls()
    fa = [p_ for p_ in (root / "compress/cache").rglob("*.json") if p_.name.startswith(ra.program_sha256)][0]
    fb = fa.with_name(f"{rb.program_sha256}-{SPEC.sha256()}.json")
    G = {}
    shutil.copy(fa, fb); r_ = E.evaluate_program(BAD, SPEC, "full", cache=True, root=root); G["A_file_copied_verbatim"] = dict(reevaluated=ncalls() == 1, valid=r_.valid, sha_ok=r_.program_sha256 == rb.program_sha256)
    d = json.loads(fa.read_text()); d["meta"]["program_sha256"] = rb.program_sha256; reseal(d); fb.write_text(json.dumps(d))
    r_ = E.evaluate_program(BAD, SPEC, "full", cache=True, root=root); G["B_meta_retargeted_resealed_payload_still_A"] = dict(reevaluated=ncalls() == 1, valid=r_.valid, sha_ok=r_.program_sha256 == rb.program_sha256)
    d["payload"]["program_sha256"] = rb.program_sha256; reseal(d); fb.write_text(json.dumps(d))
    r_ = E.evaluate_program(BAD, SPEC, "full", cache=True, root=root); G["C_meta_and_payload_sha_retargeted_resealed_(A_verdict_for_B)"] = dict(reevaluated=ncalls() == 1, valid=r_.valid, sha_ok=r_.program_sha256 == rb.program_sha256)
    OUT["G_swapped_cache_file"] = G
    # H: malformed variants
    H = {}
    good_d = json.loads(fa.read_text())
    variants = {"truncated": lambda s_: s_[: len(s_) // 2], "empty": lambda s_: "", "list": lambda s_: "[1,2]", "null": lambda s_: "null",
                "no_payload": lambda s_: json.dumps({k: v_ for k, v_ in good_d.items() if k != "payload"}),
                "payload_string_resealed": lambda s_: json.dumps(reseal({**good_d, "payload": "x"})),
                "payload_list_resealed": lambda s_: json.dumps(reseal({**good_d, "payload": [1]})),
                "verdict_string_resealed": lambda s_: json.dumps(reseal({**good_d, "payload": {**good_d["payload"], "verdict": "x"}})),
                "phase_bad_resealed": lambda s_: json.dumps(reseal({**good_d, "payload": {**good_d["payload"], "verdict": {**good_d["payload"]["verdict"], "phase": "zz"}}})),
                "alts_none_resealed": lambda s_: json.dumps(reseal({**good_d, "payload": {**good_d["payload"], "verdicts_alt": None}})),
                "meta_list_resealed": lambda s_: json.dumps(reseal({**good_d, "meta": [1]})),
                "binary": lambda s_: "\x00\xff\xfe"}
    for name, fn in variants.items():
        fa.write_text(fn(fa.read_text()))
        try:
            r_ = E.evaluate_program(GOOD, SPEC, "full", cache=True, root=root); H[name] = f"ok reeval={ncalls()} valid={r_.valid}"
        except Exception as ex: H[name] = f"RAISES {type(ex).__name__}: {str(ex)[:60]}"; ncalls()
        E.evaluate_program(GOOD, SPEC, "full", cache=True, root=root); ncalls()
    OUT["H_malformed_cache"] = H

print(json.dumps(OUT, indent=1, default=str))
json.dump(OUT, open("results/tester_m2_step2_4_recheck_cache.json", "w"), indent=1, default=str)
