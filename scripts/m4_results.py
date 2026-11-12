"""M4 step 4.7: results/spinnet/m4-compressed.json (+ .qpy/.qasm3 of the headline), m4-before-after.md, and the Lean theorem file
lean/certs/spinnet-best-step.lean (prompts/104 §3 row 4.7, §5, §11 erratum E3; schema prompts/002 §2.11).
Deterministic; every number is computed here or read from the archive / robust.json, none typed in.

    PYTHONPATH=src taskset -c 2-3 tools/run-capped python scripts/m4_results.py [--out results/spinnet] [--quick]

Run it on a CLEAN commit (provenance.git_dirty must be false).  Prerequisites: the loop has stopped; `python -m
su2plaq.spinnet.loop certify-best` has stored the Lean status of the archive best and of the headline entry.

The circuit is the HEADLINE entry (erratum E3: the valid archive entry with the smallest robust key; not the laptop-key best, which
is listed as `extra.archive_best`).  Its program is rebuilt from the archived file (sha256 checked), verified at the nominal angles
(exact-angle circuit, sparse engine, 433 codes), its logical metrics and the T(eps) table at eps in {1e-4, 1e-6, 1e-8, 1e-10} are
computed, and every synthesised circuit is re-verified with synth_tolerances (scripts/m3_results.py machinery).  Extras:
the before/after rows (seeds, per-family bests, archive best, headline; nominal and angle-averaged T and the Lean word), the lineage
(results/compress/spinnet/summary.json), the angle set of the headline rule, the U_E outer-electric row (+8 phases; fixed layer,
independent of the compressed U_B), the headline at Paulo's beta = 0.05, and the Lean block (certificate, theorem file, axioms).
--quick: schema check only (eps grid (1e-4,), no Qiskit Clifford+T pass manager; never used for committed results).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import platform
import re
import resource
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import m3_results as M3                                              # noqa: E402  (shared helpers of the M3 results script)
from su2plaq.circuits import spinnet as C                            # noqa: E402
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances    # noqa: E402,F401
from su2plaq.lean import project                                     # noqa: E402
from su2plaq.metrics.cliffordt import synthesize, t_table            # noqa: E402
from su2plaq.metrics.provenance import provenance                    # noqa: E402
from su2plaq.results.store import save_result                        # noqa: E402
from su2plaq.spinnet import lean_export as LE                        # noqa: E402
from su2plaq.spinnet import loop as L                                # noqa: E402

ALPHA, BETA = M3.ALPHA, M3.BETA
BETA_PAULO = M3.BETA_PAULO
EPS = M3.EPS
SEEDS = {**M3.SEEDS, "angle_set": L.ANGLE_SET_SEED}
ROOT = M3.ROOT
THEOREM_NAME = "spinnet_best"
THEOREM_FILE = ROOT / "lean" / "certs" / "spinnet-best-step.lean"
SEED_ROWS = (("general", "000-general"), ("general+polish", "010-general_polish"), ("qiskit_l3", "011-qiskit_l3"),
             ("spinnet_v2_pairs9", "001-spinnet_v2_pairs9"), ("spinnet_v2_flags4", "002-spinnet_v2_flags4"),
             ("spinnet_v2_flags5", "003-spinnet_v2_flags5"), ("spinnet_v2_flags6", "004-spinnet_v2_flags6"))


def _eps_get(table, eps):
    """Value of an {eps: value} table whose keys are floats (1e-6, as in a fresh metrics dict) or strings ("1e-06", as after a JSON
    round trip); None if the table is missing or has no such key."""
    if not table:
        return None
    want = float(eps)
    for k, v in table.items():
        if float(k) == want:
            return v
    return None


def _entry_row(name, e, arch_entry_t_avg, extra=None) -> dict:
    """One before/after row from an archive entry (valid: its nominal-pair metrics and verdict)."""
    m = e.metrics_raw
    v = e.verdict_nominal or {}
    out = {"row": name, "entry": e.id, "family": e.family, "round": e.round, "commit": e.git_commit, "program_path": str(e.program_path),
           "qubits": m["qubits"], "cx": m["cx"], "t_fixed": m["t_fixed"], "n_rot": m["n_rot"], "t_1e-6": _eps_get(m["t_measured"], 1e-6),
           "t_est_1e-6": _eps_get(m["t_estimate"], 1e-6), "t_1e-10": _eps_get(m["t_measured"], 1e-10), "depth_ct": m["depth_ct"],
           "t_avg": arch_entry_t_avg.get(e.id), "key": [int(x) for x in e.key],
           "verdict": f"valid (err {v.get('op_norm_error', float('nan')):.3g}, leak {v.get('leak_amplitude', float('nan')):.3g})"
                      if e.valid else "invalid",
           "lean": L._lean_word(L._lean_status(e)), "lean_reason": (e.lean or {}).get("reason", "") if isinstance(e.lean, dict) else ""}
    if extra:
        out.update(extra)
    return out


def _external_rows(sp) -> list[dict]:
    """qiskit_l3_whole (counts only) and paulo15 through the loop's own evaluation of the external seeds."""
    rows = []
    for r in L._external_rows(sp):
        m = r.get("metrics") or {}
        name = {"qiskit_l3_whole": "qiskit_l3_whole"}.get(r["source"], r["source"])
        verdict = ("unverifiable (counts only): " + r["reason"]) if not r.get("valid") and r["source"] == "qiskit_l3_whole" else \
            f"valid at its own angle (beta = {r.get('beta')}), err {r.get('op_norm_error'):.3g}" if r.get("valid") else f"invalid: {r.get('reason')}"
        rows.append({"row": name, "entry": None, "qubits": m.get("qubits"), "cx": m.get("cx"), "t_fixed": m.get("t_fixed"),
                     "n_rot": m.get("n_rot"), "t_1e-6": _eps_get(m.get("t_measured"), 1e-6),
                     "t_est_1e-6": _eps_get(m.get("t_estimate"), 1e-6), "t_1e-10": _eps_get(m.get("t_measured"), 1e-10),
                     # depth_ct = depth after Clifford+T synthesis; a counts-only (measured = False) row has only the uncompiled depth
                     "depth_ct": m.get("depth_ct") if m.get("measured", True) else None, "t_avg": None, "verdict": verdict,
                     "lean": "n_a",
                     "lean_reason": "external circuit (counts only / fixed angle): no native certificate",
                     "fixed_angle": r.get("fixed_angle", False), "gauge_minus_codes": r.get("gauge_minus_codes")})
    return rows


def _rows_markdown(rows: list[dict], head_id: str, best_id: str, aset_sha: str) -> str:
    hdr = ["row", "entry", "qubits", "CX", "T_fixed", "N_rot", "T(1e-6)", "T_avg(1e-6)", "T_est(1e-6)", "T(1e-10)", "depth_CT", "verdict", "Lean"]
    fmt = lambda x: "-" if x is None else (f"{x:.1f}" if isinstance(x, float) else str(x))      # noqa: E731
    lines = ["# M4 before / after (spin-network step, alpha = 0.37, beta = 0.61, order 1)", "",
             "Rendered by `scripts/m4_results.py` from the archive; T = pygridsynth T count at eps = 1e-6 per rotation at the nominal pair, "
             f"T_avg = the same averaged over the 20 fixed random angle pairs (seed {L.ANGLE_SET_SEED}, sha256 {aset_sha[:16]}); "
             "depth_CT = depth after Clifford+T synthesis. T(1e-6) at the nominal pair can depend on pygridsynth's word length at "
             "those angles (see the NOTE); T_avg does not.", "",
             f"GLOBAL BEST (laptop key): {best_id}.  HEADLINE (robust key): {head_id}.", "",
             "| " + " | ".join(hdr) + " |", "|" + "|".join("---" for _ in hdr) + "|"]
    for r in rows:
        lines.append("| " + " | ".join([r["row"], fmt(r.get("entry")), fmt(r["qubits"]), fmt(r["cx"]), fmt(r["t_fixed"]), fmt(r["n_rot"]),
                                        fmt(r["t_1e-6"]), fmt(r.get("t_avg")), fmt(r["t_est_1e-6"]), fmt(r["t_1e-10"]), fmt(r["depth_ct"]),
                                        r["verdict"], r["lean"]]) + " |")
    lines += ["", "NOTE: the nominal-pair T(1e-6) of an entry whose rotations are emitted as rz(theta + pi/4) . tdg (or with other shifted "
              "angle forms) can be smaller than its T_avg because pygridsynth's word is cheaper at the nominal angles; T_avg is the "
              "robust cost. Structural gains are the CX and N_rot columns.", ""]
    return "\n".join(lines)


def _lean_block(head, root: pathlib.Path, make_theorem: bool) -> dict:
    """Certificate of the headline entry + the theorem file (written, elaborated; axioms recorded)."""
    from su2plaq.compress import round as R

    lean = head.lean if isinstance(head.lean, dict) else {}
    out = {"status": lean.get("status"), "reason": lean.get("reason", ""), "checker_sha256": lean.get("checker_sha256", ""),
           "cert_path": lean.get("cert_path"), "program_file_sha256": lean.get("program_file_sha256"),
           "trust": "native-certified: compiled Lean checker su2plaq_cert_spinnet (computable code); the theorem file proves "
                    "Su2PlaqCert.SpinNet.checkJsonString certJson = true by native_decide (standard axioms + one native_decide axiom)"}
    if lean.get("status") != "certified":
        out["theorem_file"] = None
        return out
    cp = R.resolve_cert_path(lean, root)
    if cp is None or not cp.exists():
        raise RuntimeError(f"certificate {lean.get('cert_path')} of {head.id} not found")
    if lean.get("program_file_sha256") != head.program_sha256:
        raise RuntimeError("the certificate was made from another program file than the archived headline program")
    out["cert_sha256"] = hashlib.sha256(cp.read_bytes()).hexdigest()
    if not make_theorem:
        out["theorem_file"] = None
        return out
    f = LE.write_theorem_file(cp, THEOREM_NAME, THEOREM_FILE, comment=f"entry {head.id}, program sha256 {head.program_sha256}")
    out["theorem_file"] = str(f.relative_to(ROOT))
    out["theorem_name"] = THEOREM_NAME
    t0 = time.time()
    p = project.lake(["env", "lean", str(f)], timeout=900)
    out["elaboration_seconds"] = time.time() - t0
    out["elaboration_returncode"] = p.returncode
    m = re.search(r"depends on axioms:\s*\[([^\]]*)\]", p.stdout)
    out["axioms"] = sorted(a.strip() for a in m.group(1).split(",") if a.strip()) if m else None
    if p.returncode != 0 or out["axioms"] is None:
        raise RuntimeError("theorem file does not elaborate:\n" + p.stdout[-1500:] + p.stderr[-1500:])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "spinnet"))
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--quick", action="store_true", help="schema check only (eps grid (1e-4,), no Qiskit CT, no theorem file)")
    args = ap.parse_args(argv)
    t_start = time.time()
    root = pathlib.Path(args.root).resolve()
    grid = (1e-4,) if args.quick else EPS
    qiskit = not args.quick
    snap = provenance(SEEDS)           # one snapshot (commit, dirty flag, versions) BEFORE anything is written
    snap["provenance_captured_at"] = snap["timestamp_utc"]
    snap["host"] = platform.node()
    snap["command"] = " ".join([pathlib.Path(sys.executable).name, *sys.argv])
    snap["quick"] = bool(args.quick)
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    from su2plaq.compress import archive as A
    from su2plaq.compress import round as R
    from su2plaq.compress.spec import get_encoding

    L.install()
    sp = L.spec()
    enc = get_encoding(L.ENC)
    arch = A.Archive.load(L.ENC, root=root, n_alt=len(sp.alt_angles), strict=True)
    entries = {e.id: e for e in arch.entries()}
    best = arch.best()
    h = L.headline(root)
    head = entries[h["id"]]
    report_text = L.report_table(root)                      # also writes results/compress/spinnet/summary.json
    summary = json.loads((root / "results" / "compress" / L.ENC / "summary.json").read_text())
    t_avg = {r["id"]: r["t_mean"] for r in h["ranking"]}

    # ---- the headline circuit, rebuilt from its archived program (sha256 checked), verified and measured
    circ, err = R._circuit_of(sp, head.program_path, head.id, None, root, expected_sha256=head.program_sha256)
    if circ is None:
        raise RuntimeError(f"cannot rebuild the headline circuit {head.id}: {err}")
    V = enc.target("step", ALPHA, BETA, 1)
    entry = M3._entry(circ, enc, V, out, "m4-headline-step", grid, qiskit)

    # ---- the headline at Paulo's beta (like-for-like line), built by the same program
    from su2plaq.compress import evaluate as CE

    qb, _ = CE._build_in_subprocess(L._program_file(head.program_path, root).read_bytes(), [sp.with_angles(ALPHA, BETA_PAULO)],
                                    CE.BUILD_TIMEOUT_S)
    qb = qb[0]
    vb = evaluate(qb, enc, enc.target("step", ALPHA, BETA_PAULO, 1))
    rows_b = t_table(qb, (M3.EPS_CMP,), qiskit=False)
    at_paulo = {"beta": BETA_PAULO, "alpha": ALPHA, "verification": M3._verdict_block(vb), "logical": M3._logical(qb),
                "t_table_pygridsynth": rows_b,
                "note": "the headline program rebuilt at (alpha, beta) = (0.37, 0.05) with the same skeleton; the electric layer is "
                        "included, so this is the step, not U_B alone (Paulo's file is U_B alone)"}

    # ---- U_E outer electric row (fixed layer: independent of the compressed U_B)
    outer_row = M3._entry(C.build_UE(ALPHA, with_outer=True, include_outer_electric=True), enc,
                          enc.target("UE", ALPHA, None, include_outer_electric=True), out, "m4-UE_outer_row", grid, qiskit)
    outer = {k: outer_row[k] for k in ("verification", "metrics", "files")}
    outer["note"] = ("the electric layer with 8 extra p(-3 alpha/4) on the outer j-qubits (include_outer_electric); a fixed layer that "
                     "does not depend on the compressed U_B; not evaluable synthesised (writes_outer); bound 12 eps")

    # ---- before/after rows
    by_stem = {pathlib.Path(str(e.program_path)).stem: e for e in arch.entries() if e.round == 0}
    ext = {r["row"]: r for r in _external_rows(sp)}
    paulo_row = {**next(v for k, v in ext.items() if k != "qiskit_l3_whole"), "row": "paulo15"}
    seeds = [_entry_row(name, by_stem[stem], t_avg) for name, stem in SEED_ROWS]
    rows = [*seeds[:3], ext["qiskit_l3_whole"], *seeds[3:], paulo_row]
    fam_best = {}
    for r in h["ranking"]:
        fam_best.setdefault(r["family"], r["id"])
    for fam in sorted(fam_best):
        rows.append(_entry_row(f"best_family_{fam}", entries[fam_best[fam]], t_avg))
    rows.append(_entry_row("global_best", best, t_avg, {"selection": "laptop key (CX, T(1e-6) at the nominal pair, depth_CT, qubits)"}))
    hrow = _entry_row("headline", head, t_avg, {"selection": "smallest robust key (erratum E3)", "robust_key": list(h["robust_key"])})
    hrow["cx"] = h["robust_key"][0]
    rows.append(hrow)
    for r in rows:
        assert r["lean"] in ("certified", "n_a", "failed", "not_run"), r

    lean = _lean_block(head, root, make_theorem=not args.quick)

    extra = {"headline": {"id": h["id"], "robust_key": list(h["robust_key"]), "t_mean": h["t_mean"], "lean": h["lean"],
                          "rule": "valid archive entry with the smallest (CX, sum T(1e-6) over the angle set, angle-linear first, "
                                  "sum depth_CT, qubits) (prompts/104 section 11 E3)",
                          "program_path": str(head.program_path), "program_sha256": head.program_sha256, "family": head.family,
                          "round": head.round, "parent": head.parent, "entry_commit": head.git_commit},
             "archive_best": best.id, "archive_best_key": [int(x) for x in best.key],
             "angle_set": L._angle_set_record(), "ranking": [{**r, "robust_key": list(r["robust_key"]), "laptop_key": list(r["laptop_key"])}
                                                            for r in h["ranking"]],
             "before_after": rows, "lineage": summary["lineage"], "outer_electric_row": outer, "at_paulo_beta": at_paulo,
             "lean": lean, "report_table_markdown": report_text, "n_rounds": summary["n_rounds"], "n_candidates": summary["n_candidates"],
             "n_valid": summary["n_valid"]}
    snap["wall_seconds"] = time.time() - t_start
    snap["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    save_result(out / "m4-compressed.json", encoding=L.ENC, circuit_id=head.id, kind="step",
                params={"alpha": ALPHA, "beta": BETA, "order": 1}, verification=entry["verification"], metrics=entry["metrics"],
                files=entry["files"], seeds=SEEDS, provenance_snapshot=snap, extra=extra)
    (out / "m4-before-after.md").write_text(_rows_markdown(rows, head.id, best.id, L.angle_set_sha256()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
