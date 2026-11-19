"""M8 step 8.9: results/lsh/m8-compressed.json (+ .qpy/.qasm3 of the headline) and results/lsh/m8-before-after.md
(prompts/401 section 3 row 8.9, section 5; schema prompts/002 section 2.11).  Deterministic; every number is computed here or read
from the archive / robust.json / stop.json / round files / the M4 and M7 result files; none is typed in.

    PYTHONPATH=src taskset -c 0-8 tools/run-capped python scripts/m8_results.py [--out results/lsh] [--root .] [--quick]

Run it on a CLEAN commit (provenance.git_dirty must be false) after the loop has stopped, `python -m su2plaq.lsh.loop headline` has
left a current robust cache (results/compress/lsh/robust.json; this script never recomputes it) and `python -m su2plaq.lsh.loop
certify-headline` (step 8.8) has stored the Lean status of the headline entry and written lean/certs/lsh-best-step.lean.  If the
theorem file is missing the Lean block says so (`theorem_file_status: "missing"`, `theorem_file: null`); nothing is faked.

The circuit of the file is the HEADLINE entry (prompts/008 section 6: the valid archive entry with the smallest robust key; the
archive-key best is listed as `extra.archive_best`).  Its program is rebuilt from the archived file (sha256 checked), verified at the
nominal angles (exact angles, sparse engine, 433 states), its logical metrics and the T(eps) table at eps in {1e-4, 1e-6, 1e-8,
1e-10} computed, and every synthesised circuit re-verified with synth_tolerances (as scripts/m7_results.py).  `extra` carries the
before/after rows, the three numbers (spin network / wrapped / LSH headline, native_gain_cx, overhead_cx), the CX-versus-T-bar front,
the uniform-split row, the stop record, the Lean block, the lineage and the M7 outer electric row.
--quick: schema check only (eps grid (1e-4,), no elaboration of the theorem file; never used for committed results).
Nothing is written into the repository except <out>: the stop rule is evaluated on a temporary copy of its three input files.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import platform
import re
import resource
import shutil
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import m7_results as M7                                              # noqa: E402  (shared helpers of the LSH results script)
from su2plaq.metrics.provenance import provenance                    # noqa: E402
from su2plaq.results.store import save_result                        # noqa: E402

ENC, KIND = "lsh", "step"
ALPHA, BETA = 0.37, 0.61
EPS = M7.EPS
ROOT = M7.ROOT
SEEDS = {**M7.SEEDS, "angle_set": 20261107}  # must equal su2plaq.compress.robust.ANGLE_SET_SEED (imported lazily); checked in tests/unit/test_m8_results_unit.py
STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
THEOREM_REL = "lean/certs/lsh-best-step.lean"
THEOREM_NAME = "lsh_best"
LEAN_WORDS = ("certified", "n_a", "failed", "not_run")
# before/after row order (prompts/401 section 5); the first eleven are labels of the round-0 candidates / external rows
SEED_ROWS = ("general", "general+polish", "qiskit_l3", "qiskit_l3_whole", "wrap_pairs9", "wrap_flags4", "wrap_flags5", "wrap_flags6",
             "wrap_sn_headline", "wrap_sn_r05F3", "wrap_sn_r02F5", "paulo15_wrapped")
TRUST_LABEL = "native-certified, first-order step"
TRUST_NOTE = ("native-certified (not kernel-checked): the compiled Lean checker su2plaq_cert_lsh (computable code) accepted the exact "
              "certificate; the theorem file proves Su2PlaqCert.LSH.checkJsonString certJson = true by native_decide (the standard axioms "
              "plus one native_decide axiom, so the trust root is the Lean compiler plus the checker source).  The certificate is of the "
              "first-order step U_B U_E and holds for every (alpha, beta) of the angle-linear family of the program, not only at (0.37, "
              "0.61); a headline with status n_a (non_linear_angle... / phase_not_in_K) has no certificate and is reported as such.")
OUTER_NOTE = ("the same electric layer with 12 extra phases on the outer-site qubits (include_outer_electric); it reads 12 outer bits and "
              "is unchanged by the compression loop (committed M7 result results/lsh/UE.json).  Its exact-angle circuit is verified; its "
              "synthesised (Clifford+T) form writes the outer register and is NOT verifiable by this evaluator (audit 303 N5), so only "
              "its T cost is reported.")


# ---------------------------------------------------------------------------------------------------------------- pure helpers
def t_at(table, eps):
    """Value of an {eps: value} table whose keys are floats (a fresh metrics dict) or strings ("1e-06", after a JSON round trip);
    None if the table is missing or has no such key."""
    if not table:
        return None
    want = float(eps)
    return next((v for k, v in table.items() if float(k) == want), None)


def rel(path, root=ROOT):
    """Path relative to `root` (a string); paths outside it and None are returned as they are (None, or the absolute string)."""
    if path is None:
        return None
    try:
        return str(pathlib.Path(path).resolve().relative_to(pathlib.Path(root).resolve()))
    except ValueError:
        return str(path)


def lean_word(status) -> str:
    """The Lean column word of a status string (same words as `compress.robust._lean_word`)."""
    from su2plaq.compress import robust as RB

    return RB._lean_word(status)


def read_json(root, relpath):
    """JSON file `relpath` under `root`; a missing file falls back to the repository (committed M4 / M7 results are not copied into
    a temporary root).  FileNotFoundError names the path."""
    for base in (pathlib.Path(root), ROOT):
        f = base / relpath
        if f.exists():
            return json.loads(f.read_text())
    raise FileNotFoundError(f"{relpath} not found under {root} or {ROOT}")


def atomic_write(path, data) -> None:
    """Write bytes / str to `path` through a temporary file in the same directory and os.replace (no partial file is ever visible)."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp{os.getpid()}")
    try:
        if isinstance(data, str):
            tmp.write_text(data)
        else:
            tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def save_circuit(qc, out, name: str) -> dict:
    """<out>/<name>.qpy and .qasm3 (atomic); the sha256 of the qpy file; a Qiskit export limitation is recorded, not hidden."""
    from qiskit import qasm3, qpy

    out = pathlib.Path(out)
    buf = io.BytesIO()
    qpy.dump(qc, buf)
    atomic_write(out / f"{name}.qpy", buf.getvalue())
    files = {"qpy": rel(out / f"{name}.qpy"), "sha256": hashlib.sha256(buf.getvalue()).hexdigest()}
    try:
        atomic_write(out / f"{name}.qasm3", qasm3.dumps(qc))
        files["qasm3"] = rel(out / f"{name}.qasm3")
    except qasm3.QASM3ExporterError as exc:
        files["qasm3"] = None
        files["qasm3_error"] = f"{type(exc).__name__}: {exc}"
    return files


def entry_row(name: str, e, ranked: dict, extra=None) -> dict:
    """One before/after row from an archive entry: its nominal-pair metrics and verdict, its recorded Lean word, and (if the entry has a
    robust key) the angle-averaged T `t_avg` and the robust key.  `ranked` = {id: row of the headline ranking}."""
    m = e.metrics_raw or {}
    v = e.verdict_nominal or {}
    r = ranked.get(e.id)
    own = e.lean if isinstance(e.lean, dict) else {}
    out = {"row": name, "entry": e.id, "family": e.family, "round": e.round, "commit": e.git_commit, "program_path": str(e.program_path),
           "qubits": m.get("qubits"), "cx": m.get("cx"), "t_fixed": m.get("t_fixed"), "n_rot": m.get("n_rot"),
           "t_1e-6": t_at(m.get("t_measured"), 1e-6), "t_est_1e-6": t_at(m.get("t_estimate"), 1e-6),
           "t_1e-10": t_at(m.get("t_measured"), 1e-10), "depth_ct": m.get("depth_ct"),
           "t_avg": r["t_mean"] if r else None, "robust_key": [int(x) for x in r["robust_key"]] if r else None,
           "key": [int(x) for x in e.key],
           "verdict": f"valid (err {v.get('op_norm_error', float('nan')):.3g}, leak {v.get('leak_amplitude', float('nan')):.3g})"
                      if e.valid else "invalid",
           "lean": lean_word(own.get("status")), "lean_reason": own.get("reason", "")}
    if extra:
        out.update(extra)
    return out


def external_row(name: str, x: dict) -> dict:
    """A before/after row of an external (never archived) circuit from its round-0 record: `qiskit_l3_whole` (counts only: the
    depth column is blank) or `paulo15_wrapped` (U_B alone at its own angle)."""
    m = x.get("metrics") or {}
    if x.get("valid"):
        verdict = f"valid at its own angle (kind {x.get('kind')}, beta = {x.get('beta')}), err {x.get('op_norm_error', float('nan')):.3g}"
    elif name == "qiskit_l3_whole":
        why = str(x.get("reason"))
        verdict = why if why.startswith("unverifiable") else "unverifiable: " + why
        verdict += " (counts only)"
    else:
        verdict = f"invalid: {x.get('reason')}"
    return {"row": name, "entry": None, "qubits": m.get("qubits"), "cx": m.get("cx"), "t_fixed": m.get("t_fixed"), "n_rot": m.get("n_rot"),
            "t_1e-6": t_at(m.get("t_measured"), 1e-6), "t_est_1e-6": t_at(m.get("t_estimate"), 1e-6),
            "t_1e-10": t_at(m.get("t_measured"), 1e-10),
            "depth_ct": m.get("depth_ct") if m.get("measured", True) else None, "t_avg": None, "robust_key": None,
            "verdict": verdict, "lean": "n_a", "lean_reason": "external circuit (counts only / fixed angle): no native certificate",
            "fixed_angle": bool(x.get("fixed_angle", False))}


def pareto_front(ranking: list) -> list:
    """The CX-versus-T-bar front of the ranked (valid, robust-key) entries: sorted by CX ascending; a point is kept only if its
    angle-averaged T is strictly smaller than that of every point with fewer (or equal, earlier in the order) CX.  Rows:
    {id, cx, t_avg, robust_key, family, round, lean}."""
    rows = sorted((r for r in ranking if r.get("robust_key") is not None), key=lambda r: (int(r["cx"]), float(r["t_mean"]), r["id"]))
    front, best_t = [], float("inf")
    for r in rows:
        if float(r["t_mean"]) < best_t:
            front.append({"id": r["id"], "cx": int(r["cx"]), "t_avg": float(r["t_mean"]), "robust_key": [int(x) for x in r["robust_key"]],
                          "family": r["family"], "round": r["round"], "lean": lean_word(r["lean"])})
            best_t = float(r["t_mean"])
    return front


def vs_spinnet(sn: dict, wrapped: dict, lsh: dict, transcoder: dict) -> dict:
    """The three numbers: spin-network headline (`sn`: id, cx, t_avg), the same circuit wrapped by the transcoder (`wrapped`: cx, t_avg),
    the LSH headline (`lsh`: id, cx, t_avg).  native_gain_cx = wrapped - LSH (how much of the transcoder cost the loop removed),
    overhead_cx = LSH - spin network (what the LSH register still costs).  RuntimeError if wrapped.cx != spin-network cx + transcoder cx
    (the wrapped circuit would not be the pinned spin-network headline plus the transcoder)."""
    if wrapped["cx"] != sn["cx"] + transcoder["cx"]:
        raise RuntimeError(f"wrapped headline cx {wrapped['cx']} != spin-network cx {sn['cx']} + transcoder cx {transcoder['cx']}")
    out = {"spinnet_headline": dict(sn), "wrapped": dict(wrapped), "lsh_headline": dict(lsh), "transcoder": dict(transcoder),
           "native_gain_cx": wrapped["cx"] - lsh["cx"], "overhead_cx": lsh["cx"] - sn["cx"]}
    if all(x.get("t_avg") is not None for x in (sn, wrapped, lsh)):
        out["native_gain_t_avg"] = wrapped["t_avg"] - lsh["t_avg"]
        out["overhead_t_avg"] = lsh["t_avg"] - sn["t_avg"]
        out["wrapped_minus_spinnet_t_avg"] = wrapped["t_avg"] - sn["t_avg"]
    out["reading"] = ("the recoding cost was not reduced (native_gain_cx = 0)" if out["native_gain_cx"] == 0 else
                      f"the loop removed {out['native_gain_cx']} of the {transcoder['cx']} transcoder CX; the LSH register still costs "
                      f"{out['overhead_cx']} CX beyond the spin-network optimum")
    return out


def parse_axioms(text: str):
    """Sorted axiom names printed by `#print axioms` in `text`, or None if there is no such line."""
    m = re.search(r"depends on axioms:\s*\[([^\]]*)\]", text)
    return sorted(a.strip() for a in m.group(1).replace("\n", " ").split(",") if a.strip()) if m else None


def lineage_rows(rounds: list, ranked: dict) -> list:
    """Lineage of the valid archived candidates in the (CX, T) plane (as `compress.report.report_table` writes it, plus `t_avg`)."""
    archived = {i for r in rounds for i in r.get("entries", [])}
    out = []
    for r in rounds:
        for c in r.get("candidates", []):
            if c.get("valid") and c.get("key") and c["id"] in archived:
                out.append({"id": c["id"], "parent": c.get("parent"), "family": c["family"], "round": r["round"], "cx": c["key"][0],
                            "t_eps": c["key"][1], "t_avg": (ranked.get(c["id"]) or {}).get("t_mean"),
                            "parent_known": c.get("parent_known", True)})
    return out


def round_table(rounds: list, stop: dict) -> list:
    """Per-round table: counts, archive best key, wall time, hashes, synthesis re-verification, and the headline recorded by the stop rule."""
    head = {x["round"]: x for x in stop.get("rounds", [])}
    return [{"round": d["round"], "n_candidates": len(d.get("candidates", [])), "n_valid": d.get("n_valid"), "n_invalid": d.get("n_invalid"),
             "best_key": d.get("best_key"), "wall_s": d.get("wall_s"), "evaluator_sha256": d.get("evaluator_sha256"),
             "headline_id": (head.get(d["round"]) or {}).get("headline_id"),
             "headline_robust_key": (head.get(d["round"]) or {}).get("robust_key"),
             "improved": (head.get(d["round"]) or {}).get("improved"), "synthesis_verification": d.get("synthesis_verification")}
            for d in rounds]


def rows_markdown(rows: list, head_id: str, best_id: str, aset_sha: str, aset_seed: int) -> str:
    """The m8-before-after.md table of the rows (every row, in order; best and headline named in the sentence above it)."""
    hdr = ["row", "entry", "qubits", "CX", "T_fixed", "N_rot", "T(1e-6)", "T_avg(1e-6)", "T_est(1e-6)", "T(1e-10)", "depth_CT", "verdict", "Lean"]
    fmt = lambda x: "-" if x is None else (f"{x:.1f}" if isinstance(x, float) else str(x))      # noqa: E731
    lines = ["| " + " | ".join(hdr) + " |", "|" + "|".join("---" for _ in hdr) + "|"]
    for r in rows:
        lines.append("| " + " | ".join([r["row"], fmt(r.get("entry")), fmt(r["qubits"]), fmt(r["cx"]), fmt(r["t_fixed"]), fmt(r["n_rot"]),
                                        fmt(r["t_1e-6"]), fmt(r.get("t_avg")), fmt(r["t_est_1e-6"]), fmt(r["t_1e-10"]), fmt(r["depth_ct"]),
                                        r["verdict"], r["lean"]]) + " |")
    head = ["# M8 before / after (LSH step, alpha = 0.37, beta = 0.61, order 1)", "",
            "Rendered by `scripts/m8_results.py` from the archive; T = pygridsynth T count at eps = 1e-6 per rotation at the nominal pair, "
            f"T_avg = the same averaged over the 20 fixed random angle pairs (seed {aset_seed}, sha256 {aset_sha[:16]}); depth_CT = depth "
            "after Clifford+T synthesis (blank for the counts-only row).", "",
            f"GLOBAL BEST (archive key): {best_id}.  HEADLINE (robust key): {head_id}.", ""]
    return "\n".join(head + lines) + "\n"


def summary_markdown(extra: dict) -> str:
    """The sections below the table: three numbers, front, uniform split, stop record, Lean status, outer row."""
    vs, ln, us, st, lean = extra["vs_spinnet"], extra["pareto_cx_tavg"], extra["uniform_split"], extra["stop"], extra["lean"]
    f = lambda x: "-" if x is None else (f"{x:.1f}" if isinstance(x, float) else str(x))      # noqa: E731
    sn, wr, ls, tr = vs["spinnet_headline"], vs["wrapped"], vs["lsh_headline"], vs["transcoder"]
    lines = ["", "## The three numbers", "",
             f"- spin-network headline `{sn['id']}`: {sn['cx']} CX, T_avg {f(sn.get('t_avg'))}",
             f"- the same circuit wrapped by the LSH transcoder (+{tr['cx']} CX, +{tr['t_fixed']} T): {wr['cx']} CX, T_avg {f(wr.get('t_avg'))}",
             f"- LSH headline `{ls['id']}`: {ls['cx']} CX, T_avg {f(ls.get('t_avg'))}",
             f"- native_gain_cx = {vs['native_gain_cx']}, overhead_cx = {vs['overhead_cx']}.  {vs['reading']}.", "",
             "## CX versus T_avg front (valid entries, CX ascending)", "", "| id | CX | T_avg | family | round | Lean |", "|---|---|---|---|---|---|"]
    lines += [f"| {p['id']} | {p['cx']} | {f(p['t_avg'])} | {p['family']} | {p['round']} | {p['lean']} |" for p in ln]
    lines += ["", "Moving down the table buys fewer T_avg at the price of more CX; the first row is the headline (smallest CX).", "",
              "## Uniform splitting (structure only)", "",
              f"nnz {us['nnz']}, max {us['max_per_row']} per row, {us['sites_touched']} sites / {us['qubits_touched']} qubits touched; "
              f"circuit: {us['circuit']} (a structure row, not a built circuit: it is not comparable with the rows above).", "",
              "## Stop record", "", f"stop = {st['stop']}, reason = {st['reason']}, streak = {st['streak']}, sessions = {st['sessions']}.", "",
              "## Lean", "",
              f"status: {lean['status']}; trust: {lean['trust']} ({TRUST_LABEL} when certified); theorem file: {lean['theorem_file']} "
              f"(status: {lean['theorem_file_status']}); axioms: {lean['axioms']}.", "",
              "## Outer electric row (M7, unchanged by the loop)", "", extra["outer_electric_row"]["note"], ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------------------------- measured parts
def stop_state_readonly(root) -> dict:
    """`lsh.loop.stop_state` on a temporary copy of its three inputs (stop.json, the attempts log, the ideation file): the function
    writes its result back into stop.json, and this script never writes into the repository."""
    from su2plaq.lsh import loop as LL

    root = pathlib.Path(root)
    with tempfile.TemporaryDirectory() as td:
        t = pathlib.Path(td)
        for relp in (f"results/compress/{ENC}/stop.json", f"compress/attempts/{ENC}.jsonl", f"compress/ideation/{ENC}.md"):
            if (root / relp).exists():
                (t / relp).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / relp, t / relp)
        return LL.stop_state(root=t)


def transcoder_cost() -> tuple:
    """({"cx", "t_fixed"}, detail) of the transcoder pair (transcoder and its inverse around an empty spin-network circuit), measured from the
    circuit `lsh.loop.wrap_spinnet_step` builds; `detail` = the other logical numbers."""
    from qiskit import QuantumCircuit, QuantumRegister

    from su2plaq.lsh import loop as LL
    from su2plaq.metrics.logical import logical_metrics

    lm = logical_metrics(LL.wrap_spinnet_step(QuantumCircuit(QuantumRegister(8, "d"))))
    return {"cx": int(lm["cx"]), "t_fixed": int(lm["t_fixed"])}, {k: lm[k] for k in M7.LOGICAL_KEYS}


def lean_block(head, root, theorem_check: bool, ranked_head: dict) -> dict:
    """Lean block of the headline: the archive's recorded status, the certificate (sha256, binding fields inside it), the theorem
    file (first line, sha256, elaboration with the axiom check) or its absence.  A missing theorem file or certificate is reported in
    `theorem_file_status`, never faked.  RuntimeError if an existing theorem file does not elaborate with the standard axioms plus one
    native axiom."""
    from su2plaq.compress import round as LR
    from su2plaq.lean import project as P

    own = head.lean if isinstance(head.lean, dict) else {}
    status = own.get("status")
    out = {"status": status, "reason": own.get("reason", ""), "trust": "native-certified" if status == "certified" else "n_a",
           "trust_label": TRUST_LABEL, "trust_note": TRUST_NOTE, "checker_sha256": own.get("checker_sha256", ""),
           "cert_path": own.get("cert_path"), "cert_sha256": None, "program_file_sha256": own.get("program_file_sha256"),
           "theorem_file": None, "theorem_name": THEOREM_NAME, "theorem_file_status": "not_applicable (headline not certified)",
           "axioms": None, "angle_linear": ranked_head.get("angle_linear")}
    if status != "certified":
        return out
    cp = LR.resolve_cert_path(own, pathlib.Path(root))
    if cp is None or not cp.exists():
        out["theorem_file_status"] = f"missing certificate {own.get('cert_path')}"
        return out
    out["cert_sha256"] = hashlib.sha256(cp.read_bytes()).hexdigest()
    cert = json.loads(cp.read_text())
    prov = cert.get("provenance", {})
    out["binding"] = {"entry_id": prov.get("entry_id"), "program_file_sha256": prov.get("program_file_sha256"),
                      "git_dirty": prov.get("git_dirty"), "git_commit": prov.get("git_commit"),
                      "matches_headline": bool(prov.get("entry_id") == head.id and prov.get("program_file_sha256") == head.program_sha256)}
    f = pathlib.Path(root) / THEOREM_REL
    if not f.exists():
        out["theorem_file_status"] = "missing (step 8.8: python -m su2plaq.lsh.loop certify-headline in a clean worktree)"
        return out
    text = f.read_text()
    first = text.splitlines()[0] if text else ""
    out.update({"theorem_file": THEOREM_REL, "theorem_file_sha256": hashlib.sha256(text.encode()).hexdigest(), "theorem_first_line": first,
                "theorem_names_headline": bool(first.startswith("-- ") and head.id in first and head.program_sha256 in first),
                "theorem_file_status": "present"})
    if not theorem_check:
        out["theorem_file_status"] = "present (not elaborated: --quick)"
        return out
    t0 = time.time()
    p = P.lake(["env", "lean", str(f)], timeout=900)
    out["elaboration_seconds"] = time.time() - t0
    out["elaboration_returncode"] = p.returncode
    out["axioms"] = parse_axioms(p.stdout)
    extra_ax = sorted(set(out["axioms"] or []) - STANDARD_AXIOMS)
    if p.returncode != 0 or out["axioms"] is None or len(extra_ax) != 1 or not all(P.is_native_axiom(a) for a in extra_ax):
        raise RuntimeError(f"theorem file {f} is not accepted with standard axioms + one native axiom:\n" + p.stdout[-1500:] + p.stderr[-1500:])
    out["theorem_file_status"] = "elaborated"
    return out


def build_rows(arch, entries: dict, best, head, h: dict, ranked: dict, round0: dict) -> list:
    """The before/after rows in the order of prompts/401 section 5.  `round0` = the round-0 file (labels -> ids in `candidates`, the
    external records).  A seed label whose candidate is not in the archive gets a row from its candidate record."""
    label_id = {c["label"]: c["id"] for c in round0.get("candidates", [])}
    ext = {x["source"]: x for x in round0.get("external", []) if x.get("metrics") is not None or x.get("source") in SEED_ROWS}
    rows = []
    for name in SEED_ROWS:
        if name in ("qiskit_l3_whole", "paulo15_wrapped"):
            if name not in ext:
                raise RuntimeError(f"round-000.json has no external record {name!r}")
            rows.append(external_row(name, ext[name]))
        elif label_id.get(name) in entries:
            rows.append(entry_row(name, entries[label_id[name]], ranked, {"selection": "round-0 seed"}))
        else:
            c = next((c for c in round0.get("candidates", []) if c["label"] == name), None)
            if c is None:
                raise RuntimeError(f"round-000.json has no candidate {name!r}")
            m = c.get("metrics") or {}
            rows.append({"row": name, "entry": None, "qubits": m.get("qubits"), "cx": m.get("cx"), "t_fixed": m.get("t_fixed"),
                         "n_rot": m.get("n_rot"), "t_1e-6": t_at(m.get("t_measured"), 1e-6), "t_est_1e-6": t_at(m.get("t_estimate"), 1e-6),
                         "t_1e-10": t_at(m.get("t_measured"), 1e-10), "depth_ct": m.get("depth_ct"), "t_avg": None, "robust_key": None,
                         "verdict": f"not archived: {c.get('reason')}", "lean": "not_run", "lean_reason": ""})
    fam_best = {}
    for r in h["ranking"]:
        if r["family"] != "seed":
            fam_best.setdefault(r["family"], r["id"])
    for fam in sorted(fam_best):
        rows.append(entry_row(f"best_family_{fam}", entries[fam_best[fam]], ranked, {"selection": "best of the family by the robust key"}))
    rows.append(entry_row("global_best", best, ranked, {"selection": "archive key (CX, T(1e-6) at the nominal pair, depth_CT, qubits)"}))
    hrow = entry_row("headline", head, ranked, {"selection": "smallest robust key (prompts/008 section 6)", "robust_key": [int(x) for x in h["robust_key"]]})
    hrow["cx"] = int(h["robust_key"][0])
    rows.append(hrow)
    for r in rows:
        assert r["lean"] in LEAN_WORDS, r
    return rows


def check_general_row(rows: list, root) -> dict:
    """The general round-0 row against the committed M7 result results/lsh/step.json (same circuit, same counts); RuntimeError on any
    difference."""
    g = next(r for r in rows if r["row"] == "general")
    lg = read_json(root, "results/lsh/step.json")["metrics"]["logical"]
    got = {k: g[k] for k in ("cx", "t_fixed", "n_rot")}
    want = {k: lg[k] for k in ("cx", "t_fixed", "n_rot")}
    if got != want:
        raise RuntimeError(f"general row {got} disagrees with results/lsh/step.json {want}")
    return {"file": "results/lsh/step.json", **want}


# ---------------------------------------------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "lsh"))
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--quick", action="store_true", help="schema check only (eps grid (1e-4,), theorem file not elaborated)")
    args = ap.parse_args(argv)
    t_start = time.time()
    root = pathlib.Path(args.root).resolve()
    grid = (1e-4,) if args.quick else EPS
    snap = provenance(SEEDS)              # one snapshot (commit, dirty flag, versions) BEFORE anything is written
    snap["provenance_captured_at"] = snap["timestamp_utc"]
    snap["host"] = platform.node()
    snap["command"] = " ".join([pathlib.Path(sys.executable).name, *sys.argv])
    snap["quick"] = bool(args.quick)
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    from su2plaq.compress import archive as A
    from su2plaq.compress import round as R
    from su2plaq.compress import robust as RB
    from su2plaq.compress.spec import get_encoding
    from su2plaq.evaluate.evaluator import evaluate
    from su2plaq.lsh import loop as LL
    from su2plaq.lsh import rs_split

    sp = LL.spec()
    enc = get_encoding(ENC)
    arch = A.Archive.load(ENC, root=root, n_alt=len(sp.alt_angles), strict=True)
    entries = {e.id: e for e in arch.entries()}
    best = arch.best()
    h = RB.headline(ENC, KIND, root=root, compute=False)          # never recomputed here: run `loop headline` first
    if not h or h.get("id") is None:
        raise RuntimeError("no current headline cache: run `python -m su2plaq.lsh.loop headline` (results/compress/lsh/robust.json) first")
    head = entries[h["id"]]
    ranked = {r["id"]: r for r in h["ranking"]}
    rdir = root / "results" / "compress" / ENC
    rounds = [json.loads(f.read_text()) for f in sorted(rdir.glob("round-*.json"))]
    round0 = next(r for r in rounds if r["round"] == 0)

    # ---- the headline circuit, rebuilt from its archived program (sha256 checked), verified and measured
    circ, err = R._circuit_of(sp, head.program_path, head.id, None, root, expected_sha256=head.program_sha256)
    if circ is None:
        raise RuntimeError(f"cannot rebuild the headline circuit {head.id}: {err}")
    V = enc.target("step", ALPHA, BETA, 1)
    t0 = time.time()
    ver = M7._verdict_block(evaluate(circ, enc, V))
    if not (ver["ok"] and ver["certified"]):
        raise RuntimeError(f"the headline {head.id} is not valid at the nominal pair: {ver}")
    metrics = M7._metrics_block(circ, enc, V, grid)
    files = save_circuit(circ, out, "m8-headline-step")
    build_s = time.time() - t0

    # ---- before/after rows, the three numbers, the front
    rows = build_rows(arch, entries, best, head, h, ranked, round0)
    m7_check = check_general_row(rows, root)
    transcoder, transcoder_detail = transcoder_cost()
    sn_m4 = read_json(root, "results/spinnet/m4-compressed.json")["extra"]["headline"]
    sn = {"id": sn_m4["id"], "cx": int(sn_m4["robust_key"][0]), "t_avg": sn_m4["t_mean"]}
    src_label = "wrap_sn_headline"
    if LL.WRAP_SOURCES[src_label][2] != sn["id"]:
        raise RuntimeError(f"pinned wrap source {LL.WRAP_SOURCES[src_label][2]} is not the spin-network headline {sn['id']}")
    wrow = next(r for r in rows if r["row"] == src_label)
    wrapped = {"entry": wrow["entry"], "cx": int(wrow["cx"]), "t_avg": wrow["t_avg"]}
    lsh = {"id": h["id"], "cx": int(h["robust_key"][0]), "t_avg": h["t_mean"]}
    vs = vs_spinnet(sn, wrapped, lsh, transcoder)
    vs["transcoder_detail"] = transcoder_detail
    front = pareto_front(h["ranking"])
    stop = stop_state_readonly(root)
    lean = lean_block(head, root, theorem_check=not args.quick, ranked_head=ranked[head.id])

    ue = read_json(root, "results/lsh/UE.json")
    orow = ue["extra"]["outer_electric_row"]
    outer = {**orow, "note": OUTER_NOTE, "file": "results/lsh/UE.json", "file_commit": ue["provenance"]["git_commit"],
             "file_git_dirty": ue["provenance"]["git_dirty"]}

    extra = {"order": 1, "angle_set": RB._angle_set_record(),
             "headline": {"id": h["id"], "robust_key": [int(x) for x in h["robust_key"]], "t_mean": h["t_mean"], "lean": h["lean"],
                          "rule": "valid archive entry with the smallest (CX, sum T(1e-6) over the angle set, angle-linear first, sum "
                                  "depth_CT, qubits) (prompts/008 section 6)",
                          "program_path": str(head.program_path), "program_sha256": head.program_sha256, "family": head.family,
                          "round": head.round, "parent": head.parent, "entry_commit": head.git_commit,
                          "angle_linear": ranked[head.id]["angle_linear"], "offset_class": ranked[head.id].get("offset_class")},
             "archive_best": best.id, "archive_best_key": [int(x) for x in best.key],
             "archive_best_robust_key": list(h["archive_best_robust_key"]) if h.get("archive_best_robust_key") else None,
             "ranking": [{**r, "robust_key": list(r["robust_key"]), "laptop_key": list(r["laptop_key"])} for r in h["ranking"]],
             "unrankable": h.get("unrankable", []),
             "before_after": rows, "m7_general_check": m7_check, "vs_spinnet": vs, "pareto_cx_tavg": front,
             "uniform_split": {**rs_split.structure(), "circuit": "not built"},
             "stop": stop, "lean": lean, "lineage": lineage_rows(rounds, ranked), "rounds": round_table(rounds, stop),
             "verdicts_alt": head.verdicts_alt, "n_rounds": len(rounds), "wrapped_sources": round0.get("lsh", {}).get("wrapped_sources"),
             "synthesis_verification": next((r["synthesis_verification"] for r in reversed(rounds)
                                             if (r.get("synthesis_verification") or {}).get("entry") == head.id), None),
             "outer_electric_row": outer, "verification_seconds": build_s}
    snap["wall_seconds"] = time.time() - t_start
    snap["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

    target = out / "m8-compressed.json"
    tmp = out / f".m8-compressed.json.tmp{os.getpid()}"
    try:
        save_result(tmp, encoding=ENC, circuit_id=head.id, kind=KIND, params={"alpha": ALPHA, "beta": BETA, "order": 1}, verification=ver,
                    metrics=metrics, files=files, seeds=SEEDS, provenance_snapshot=snap, extra=extra)
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    md = rows_markdown(rows, head.id, best.id, RB.angle_set_sha256(), RB.ANGLE_SET_SEED) + summary_markdown(extra)
    atomic_write(out / "m8-before-after.md", md)
    print(f"wrote {target} and {out / 'm8-before-after.md'}: headline {head.id} ({lsh['cx']} CX), native_gain_cx {vs['native_gain_cx']}, "
          f"overhead_cx {vs['overhead_cx']}, lean {lean['status']} / theorem file {lean['theorem_file_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
