"""Gate-count summary of all five encodings -> results/summary/encodings-gate-counts.{pdf,md,json}.

Reads only committed result files (no circuit is rebuilt):
  results/<enc>/{UE,UB,step,...}.json          general (uncompressed) circuits, data register only
  results/compress/<enc>/summary.json           compression-loop rows (general vs best; loop registers)
  results/spinnet/m4-compressed.json            spinnet headline (robust rule, prompts/104)
  results/fuzzy/compressed_step.json            fuzzy composed step

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
LOOPS = [  # (label, compress dir, loop state, how the best is chosen)
    ("1. 12-qubit, step", "twelve", "stopped after round 5", "global"),
    ("2. Spin network, step", "spinnet", "stopped after round 5", "headline"),
    ("3. Rishon, step (no det)", "rishon", "paused: replay rounds 0-4 under 10 % cap", "global"),
    ("5. Fuzzy, U_B", "fuzzy_ub", "running (round 7)", "global"),
    ("5. Fuzzy, link U_E", "fuzzy_link", "finished", "global"),
]


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


def loop_rows():
    rows = []
    for label, enc, state, how in LOOPS:
        s = load(f"results/compress/{enc}/summary.json")
        hdr = s.get("header") or ["row", "qubits", "CX", "T_fixed", "N_rot", "T(1e-6)", "T_est(1e-6)", "T(1e-10)",
                                  "depth_CT", "verdict", "Lean", "entry / commit"]
        rr = {r[0]: dict(zip(hdr, r)) for r in s["rows"]}
        g = rr["general"]
        if how == "headline":
            hd = load("results/spinnet/m4-compressed.json")
            lg = hd["metrics"].get("logical", hd["metrics"])
            hid = hd["extra"]["headline"]["id"] if isinstance(hd["extra"].get("headline"), dict) else s["headline"]["id"]
            b = {"qubits": lg["qubits"], "CX": lg["cx"], "N_rot": lg["n_rot"], "T(1e-6)": t_at(hd["metrics"]),
                 "verdict": f"valid (err {hd['verification']['op_norm_error']:.2g})", "Lean": "certified",
                 "entry / commit": f"{hid} (headline) @ {hd['provenance']['git_commit']}"}
        else:
            b = rr["GLOBAL BEST"]
        rows.append({"loop": label, "general": g, "best": b, "state": state, "rounds": s.get("n_rounds")})
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
    fz = load("results/fuzzy/compressed_step.json")
    data = {"general": gen, "loops": loops, "fuzzy_composed_step": {"general": fz["general"], "composed": fz["composed"],
            "units": fz["units"], "commit": fz["provenance"]["git_commit"]},
            "provenance": {"git_commit": commit, "results_dirty": dirty, "command": "python scripts/summary_table.py",
                           "written_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}}
    (out / "encodings-gate-counts.json").write_text(json.dumps(data, indent=1, default=str) + "\n")

    t1_head = ["Encoding", "Circuit", "Qubits", "CX", "Rotations", "Fixed T", "T(1e-6)", "Error", "Source"]
    t1 = [[r["encoding"], r["circuit"], fmt(r["qubits"]), fmt(r["cx"]), fmt(r["n_rot"]), fmt(r["t_fixed"]),
           fmt(r["t_1e6"]), fmt(r["error"]), r["source"]] for r in gen]
    t2_head = ["Loop", "Version", "Qubits", "CX", "Rotations", "T(1e-6)", "Error", "Lean", "Entry", "State"]
    t2 = []
    for r in loops:
        for tag, x in (("general", r["general"]), ("best", r["best"])):
            t2.append([r["loop"] if tag == "general" else "", tag, fmt(x.get("qubits")), fmt(x.get("CX")),
                       fmt(x.get("N_rot")), fmt(x.get("T(1e-6)")), fmt(err_of(x.get("verdict"))), x.get("Lean", "-"),
                       str(x.get("entry / commit", "-")).split(" @ ")[0], r["state"] if tag == "best" else ""])
    c = fz["composed"]; g = fz["general"]
    t2.append(["5. Fuzzy, full step + outer", "general", fmt(g["qubits"]), fmt(g["cx"]), fmt(g["n_rot"]), "-",
               "-", "-", "-", ""])
    t2.append(["", "composed", fmt(c["qubits"]), fmt(c["cx"]), fmt(c["n_rot"]), "-",
               fmt(fz["verification"]["err"]), "-", f"U_B {fz['units']['fuzzy_ub']['entry']}",
               "uses the old U_B; to rebuild"])
    t2.append(["4. Loop-string-hadron", "-", "-", "-", "-", "-", "-", "-", "-", "M8 not started"])

    notes = [
        "CX = CNOT count. Rotations = arbitrary-angle rotations. Fixed T = T gates already in the circuit (Toffoli-type parts).",
        "T(1e-6) = fixed T + T gates of all rotations synthesised to accuracy 1e-6 each (pygridsynth). Error = largest operator-norm",
        "  difference from the exact target over all Gauss-law states (433 states; rishon on its inner codes).",
        "Table 1 counts the data register plus helper qubits; Table 2 uses each loop's own register (outer links included), so qubit",
        "  totals differ between the tables. Compare rows within one encoding; the circuits differ (U_B only vs full step) across encodings.",
        "Spin-network best = headline chosen by the robust rule (average T over 20 angle pairs, prompts/104), not the nominal-angle key.",
        "Lean: certified = native Lean checker accepted that exact circuit; n_a = checker cannot handle it yet (rishon: 3 angles;",
        "  fuzzy: angle form not checked); not_run = not attempted. Fuzzy general results were made on a dirty tree (8e71c38).",
        f"Generated by `python scripts/summary_table.py` at commit {commit}" + (" (results dirty)" if dirty else "") + ".",
    ]
    md = ["# Gate counts of the five encodings", "", f"Commit {commit}. Command: `python scripts/summary_table.py`.", "",
          "## Table 1. General (uncompressed) circuits", "", "| " + " | ".join(t1_head) + " |",
          "|" + "---|" * len(t1_head)] + ["| " + " | ".join(r) + " |" for r in t1] + [
          "", "## Table 2. Compression loops: general vs best", "", "| " + " | ".join(t2_head) + " |",
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
        page(pdf, f"Table 2. Compression loops: general vs best circuit  (commit {commit})", t2_head, t2,
             [0.15, 0.06, 0.05, 0.05, 0.06, 0.06, 0.06, 0.06, 0.16, 0.23], notes)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "summary"))
    print(build(pathlib.Path(ap.parse_args().out)))
