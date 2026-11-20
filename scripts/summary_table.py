"""Gate-count summary of all five encodings -> results/summary/encodings-gate-counts.{pdf,md,json}.

Reads only committed result files (no circuit is rebuilt):
  results/<enc>/{UE,UB,step,...}.json          general (uncompressed) circuits, data register only
  results/compress/<enc>/summary.json           compression-loop rows (general vs headline; loop registers)
  results/compress/<enc>/robust.json            robust-key bookkeeping (angle set, hashes)
  results/{spinnet/m4,rishon/m6,lsh/m8}-compressed.json   native-certified headline circuit of that loop (robust rule)
  results/compress/<enc>/round-NNN.json         archive candidate records (headline fallback when no dedicated file)
  results/compress/lsh/stop.json                LSH stop reason
  results/fuzzy/compressed_step_headline.json   fuzzy composed step with the headline units (prompts/010)

Every loop row shows the HEADLINE (robust-key rule, `summary.json["headline"]`), not the nominal-angle archive best; when the
two differ the archive best is listed in the notes.

  python scripts/summary_table.py [--out results/summary]
"""
import argparse
import datetime
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]

ENCODINGS = [  # (label, results dir, circuits in order)
    ("1. 12-qubit (Paulo)", "twelve", ["UE", "UB", "step"]),
    ("2. Spin network", "spinnet", ["UE", "UB", "step"]),
    ("3. Rishon", "rishon", ["UE", "UB", "step", "UD", "step3"]),
    ("4. Loop-string-hadron", "lsh", ["UE", "UB", "step"]),
    ("5. Fuzzy", "fuzzy", ["UE", "UK", "UB", "step"]),
]
CIRCUIT_NAME = {"UE": "U_E (electric)", "UB": "U_B (magnetic)", "UK": "U_K (fuzzy kinetic)",
                "step": "step, order 1", "UD": "U_D (det layer)", "step3": "step + det, order 1"}
LOOPS = [  # (label, compress dir)
    ("1. 12-qubit, step", "twelve"),
    ("2. Spin network, step", "spinnet"),
    ("3. Rishon, step (no det)", "rishon"),
    ("4. Loop-string-hadron, step", "lsh"),
    ("5. Fuzzy, U_B", "fuzzy_ub"),
    ("5. Fuzzy, link U_E", "fuzzy_link"),
]
# Dedicated native-certified headline files (they carry the Lean status of the headline); used only if their headline id equals
# the one in results/compress/<enc>/summary.json.
HEADLINE_FILES = {"spinnet": "results/spinnet/m4-compressed.json", "rishon": "results/rishon/m6-compressed.json",
                  "lsh": "results/lsh/m8-compressed.json"}

# ---- HAND-WRITTEN STATUS TEXT (the only strings in this script that are not read from a result file) ----------------------------
# Default loop state is derived: "stopped after round <n_rounds-1>" (+ the stop reason of results/compress/<enc>/stop.json if it
# exists, translated with STOP_REASON_TEXT).  These dicts only add what no result file records.
HAND_WRITTEN = {
    "state_override": {"fuzzy_link": "finished"},                                   # loop ended because the family was exhausted
    "state_suffix": {"fuzzy_ub": " (Digonto)"},                                     # stopped by Digonto's decision
    "lean_when_not_run": {"fuzzy_ub": "n_a", "fuzzy_link": "n_a"},                  # no exact Lean exporter for fuzzy (plan 302 s0.5)
}
STOP_REASON_TEXT = {"max_sessions": "session limit", "max_rounds": "round limit", "no_gain": "no gain"}
def load(rel):
    return json.loads((ROOT / rel).read_text())


def t_at(metrics, eps=1e-6):
    for r in metrics.get("t_table") or []:
        if isinstance(r, dict) and abs(float(r.get("eps", 0)) - eps) < 1e-15:
            return r.get("t_total")
    return None


def general_rows():
    rows = []
    for label, enc, kinds in ENCODINGS:
        for k in kinds:
            p = ROOT / "results" / enc / f"{k}.json"
            if not p.exists():
                continue
            d = load(p.relative_to(ROOT))
            m = d["metrics"]
            lg = m.get("logical", m)
            v = d.get("verification") or {}
            pr = d.get("provenance") or {}
            rows.append({
                "encoding": label, "circuit": CIRCUIT_NAME.get(k, k), "qubits": lg.get("qubits"),
                "cx": lg.get("cx"), "n_rot": lg.get("n_rot"), "t_fixed": lg.get("t_fixed"),
                "t_1e6": t_at(m), "error": v.get("op_norm_error"),
                "source": f"results/{enc}/{k}.json @ {pr.get('git_commit')}" + (" (dirty)" if pr.get("git_dirty") else ""),
            })
    return rows


def _row(summary, name):
    for r in summary["rows"]:
        if r[0] == name:
            return dict(zip(summary["header"], r)) if summary.get("header") else None
    return None


def _rows_by_id(summary):
    hdr = summary.get("header") or ["row", "qubits", "CX", "T_fixed", "N_rot", "T(1e-6)", "T_est(1e-6)", "T(1e-10)",
                                    "depth_CT", "verdict", "Lean", "entry / commit"]
    return {r[0]: dict(zip(hdr, r)) for r in summary["rows"]}, hdr


def _entry_id(row):
    return str(row.get("entry / commit", "")).split(" @ ")[0]


def headline_record(enc, summary):
    """The headline row of loop `enc` as a dict with the summary-row keys, read from result files only."""
    hid = summary["headline"]["id"]
    rr, _ = _rows_by_id(summary)
    pth = HEADLINE_FILES.get(enc)
    if pth and (ROOT / pth).exists():
        hd = load(pth)
        hl = (hd.get("extra") or {}).get("headline")
        if isinstance(hl, dict) and hl.get("id") == hid:
            lg = hd["metrics"].get("logical", hd["metrics"])
            return {"qubits": lg["qubits"], "CX": lg["cx"], "N_rot": lg["n_rot"], "T(1e-6)": t_at(hd["metrics"]),
                    "verdict": f"valid (err {hd['verification']['op_norm_error']:.6g})",
                    "Lean": hl.get("lean", "not_run"), "entry / commit": f"{hid} @ {hd['provenance']['git_commit']}"}
    for name, r in rr.items():                                      # the headline is also a summary row (e.g. GLOBAL BEST)
        if _entry_id(r) == hid:
            return dict(r)
    rnd = hid.split("-")[0]                                         # r10-... -> results/compress/<enc>/round-010.json
    rp = ROOT / "results" / "compress" / enc / f"round-{int(rnd[1:]):03d}.json"
    for c in load(rp.relative_to(ROOT)).get("candidates", []):
        if c.get("id") == hid:
            m = c["metrics"]
            lean = (c.get("lean") or {}).get("status") or HAND_WRITTEN["lean_when_not_run"].get(enc, "not_run")
            return {"qubits": m["qubits"], "CX": m["cx"], "N_rot": m["n_rot"], "T(1e-6)": m["t_eps"],
                    "verdict": f"valid (err {c['verdict']['op_norm_error']:.6g})", "Lean": lean,
                    "entry / commit": f"{hid} @ {c.get('git_commit')}"}
    raise KeyError(f"headline {hid} of {enc} not found in summary rows, headline file or round record")


def loop_state(enc, summary):
    if enc in HAND_WRITTEN["state_override"]:
        return HAND_WRITTEN["state_override"][enc]
    state = f"stopped after round {summary['n_rounds'] - 1}"
    sp = ROOT / "results" / "compress" / enc / "stop.json"
    if sp.exists():
        reason = (load(sp.relative_to(ROOT)).get("reasons") or ["?"])[0]
        state += f" ({STOP_REASON_TEXT.get(reason, reason)})"
    return state + HAND_WRITTEN["state_suffix"].get(enc, "")


def loop_rows():
    rows = []
    for label, enc in LOOPS:
        s = load(f"results/compress/{enc}/summary.json")
        rr, _ = _rows_by_id(s)
        hl = s["headline"]
        rows.append({"loop": label, "general": rr["general"], "headline": headline_record(enc, s), "headline_id": hl["id"],
                     "archive_best": s["global_best"], "archive_best_key": s["global_best_key"], "t_mean_robust": hl["t_mean"],
                     "state": loop_state(enc, s), "rounds": s.get("n_rounds")})
    return rows


def fmt(x, nd=3):
    if x is None or x == "":
        return "-"
    if isinstance(x, float):
        return f"{x:.1e}" if (x != 0 and abs(x) < 1e-3) else (f"{x:.0f}" if x == int(x) else f"{x:.{nd}g}")
    return str(x)


def err_of(verdict):
    if isinstance(verdict, str) and "err" in verdict:
        try:
            return float(verdict.split("err")[1].strip(" )").split(",")[0])
        except ValueError:
            return None
    return None


def build(out):
    out.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "results", ":(exclude)results/summary"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip())
    gen, loops = general_rows(), loop_rows()
    fz = load("results/fuzzy/compressed_step_headline.json")
    data = {"general": gen, "loops": loops, "fuzzy_composed_step": {"general": fz["general"], "composed": fz["composed"],
            "units": fz["units"], "rule": fz.get("rule"), "commit": fz["provenance"]["git_commit"]},
            "provenance": {"git_commit": commit, "results_dirty": dirty, "command": "python scripts/summary_table.py",
                           "written_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}}
    (out / "encodings-gate-counts.json").write_text(json.dumps(data, indent=1, default=str) + "\n")

    t1_head = ["Encoding", "Circuit", "Qubits", "CX", "Rotations", "Fixed T", "T(1e-6)", "Error", "Source"]
    t1 = [[r["encoding"], r["circuit"], fmt(r["qubits"]), fmt(r["cx"]), fmt(r["n_rot"]), fmt(r["t_fixed"]),
           fmt(r["t_1e6"]), fmt(r["error"]), r["source"]] for r in gen]
    t2_head = ["Loop", "Version", "Qubits", "CX", "Rotations", "T(1e-6)", "Error", "Lean", "Entry", "State"]
    t2 = []
    for r in loops:
        for tag, x in (("general", r["general"]), ("headline", r["headline"])):
            t2.append([r["loop"] if tag == "general" else "", tag, fmt(x.get("qubits")), fmt(x.get("CX")),
                       fmt(x.get("N_rot")), fmt(x.get("T(1e-6)")), fmt(err_of(x.get("verdict"))), x.get("Lean", "-"),
                       _entry_id(x), r["state"] if tag == "headline" else ""])
    c = fz["composed"]; g = fz["general"]
    ub = fz["units"]["fuzzy_ub"]["entry"]
    t2.append(["5. Fuzzy, full step + outer", "general", fmt(g["qubits"]), fmt(g["cx"]), fmt(g["n_rot"]), "-",
               "-", "-", "-", ""])
    t2.append(["", "headline composed", fmt(c["qubits"]), fmt(c["cx"]), fmt(c["n_rot"]), "-",
               fmt(fz["verification"]["err"]), "-", f"U_B {ub}; link {fz['units']['fuzzy_link']['entry']}",
               "headline units (prompts/010)"])

    differ = [r for r in loops if r["archive_best"] != r["headline_id"]]
    notes = [
        "CX = CNOT count. Rotations = arbitrary-angle rotations. Fixed T = T gates already in the circuit (Toffoli-type parts).",
        "T(1e-6) = fixed T + T gates of all rotations synthesised to accuracy 1e-6 each (pygridsynth). Error = largest operator-norm",
        "  difference from the exact target over all Gauss-law states (433 states; rishon on its inner codes).",
        "Table 1 counts the data register plus helper qubits; Table 2 uses each loop's own register (outer links included), so qubit",
        "  totals differ between the tables. Compare rows within one encoding; the circuits differ (U_B only vs full step) across encodings.",
        "Table 2 'headline' = the circuit chosen by the robust-key rule (smallest CX, then sum of T(1e-6) over 20 angle pairs; prompts/104,",
        "  203, 008, 010), read from results/compress/<enc>/summary.json; it is not always the nominal-angle archive best:",
    ] + [f"  {r['loop']}: headline {r['headline_id']} (T mean over the angle set {r['t_mean_robust']}); archive best {r['archive_best']} "
         f"(CX, T(1e-6), depth_CT, qubits) = {tuple(r['archive_best_key'])}." for r in differ] + [
        "Lean: certified = native Lean checker accepted that exact circuit; n_a = checker cannot handle it yet (rishon general: 3",
        "  angles; fuzzy: no exact exporter); not_run = not attempted. Fuzzy general results were made on a dirty tree (8e71c38).",
        "Fuzzy composed step: units are the headline U_B and link U_E (results/fuzzy/compressed_step_headline.json, prompts/010).",
        f"Generated by `python scripts/summary_table.py` at commit {commit}" + (" (results dirty)" if dirty else "") + ".",
    ]
    md = ["# Gate counts of the five encodings", "", f"Commit {commit}. Command: `python scripts/summary_table.py`.", "",
          "## Table 1. General (uncompressed) circuits", "", "| " + " | ".join(t1_head) + " |",
          "|" + "---|" * len(t1_head)] + ["| " + " | ".join(r) + " |" for r in t1] + [
          "", "## Table 2. Compression loops: general vs headline", "", "| " + " | ".join(t2_head) + " |",
          "|" + "---|" * len(t2_head)] + ["| " + " | ".join(r) + " |" for r in t2] + ["", "## Notes", ""] + \
         ["- " + n.strip() if not n.startswith("  ") else "  " + n.strip() for n in notes]
    (out / "encodings-gate-counts.md").write_text("\n".join(md) + "\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    def page(pdf, title, head, rows, widths, foot):
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.text(0.03, 0.95, title, fontsize=14, weight="bold")
        ax = fig.add_axes([0.03, 0.16, 0.94, 0.76]); ax.axis("off")
        tb = ax.table(cellText=rows, colLabels=head, colWidths=widths, loc="upper left", cellLoc="left")
        tb.auto_set_font_size(False); tb.set_fontsize(7.5); tb.scale(1, 1.35)
        for (i, j), cell in tb.get_celld().items():
            cell.set_linewidth(0.3)
            if i == 0:
                cell.set_text_props(weight="bold"); cell.set_facecolor("#e8e8e8")
        fig.text(0.03, 0.02, "\n".join(foot), fontsize=7, va="bottom", family="monospace")
        pdf.savefig(fig); plt.close(fig)

    with PdfPages(out / "encodings-gate-counts.pdf") as pdf:
        page(pdf, f"Table 1. General (uncompressed) circuits, all five encodings  (commit {commit})", t1_head, t1,
             [0.14, 0.13, 0.05, 0.06, 0.07, 0.06, 0.06, 0.07, 0.30], notes)
        page(pdf, f"Table 2. Compression loops: general vs headline circuit  (commit {commit})", t2_head, t2,
             [0.15, 0.06, 0.05, 0.05, 0.06, 0.06, 0.06, 0.06, 0.16, 0.23], notes)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "summary"))
    print(build(pathlib.Path(ap.parse_args().out)))
