"""Results files and tables of the cross-encoding report (prompts/009 §5.4, §8; docs/METHODS.md §13).

`spectra_results` -> results/crosscheck/spectra.json (schema "crosscheck-spectra-1")
`gate_table`      -> results/crosscheck/gate-table.json (schema "crosscheck-gate-table-1")
`render`          -> Markdown of Tables 1-3 from those two files
`tradeoff_figure` -> results/crosscheck/tradeoff.pdf (CX against T_avg per archive)

Every number is read from a source file (results/*.json, the archives through `compress.robust.headline(..., compute=False)`) or
computed here from production functions; nothing is typed in.  A headline that is not cached (never computed, or stale for the current
code hash) is recorded as such with the reason, never replaced by a guess.  `T_avg` = mean over the 20 locked angle pairs of the T count at
eps = 1e-6 (METHODS §12.4).  Not in any hash list; decides no verdict.
"""
from __future__ import annotations

import itertools
import json
import pathlib
import time

import numpy as np

G2S = (0.5, 1.0, 2.0)
CLOSED_L = (16, 32, 64, 128, 256, 512, 1024)
FULL_L = (64, 128)
ANGLES = ((0.37, 0.61), (0.91, 0.23))
ROWS = (("twelve", "A", "Kogut-Susskind, j_max = 1/2", 433), ("spinnet", "A", "Kogut-Susskind, j_max = 1/2", 433),
        ("lsh", "A", "Kogut-Susskind, j_max = 1/2", 433), ("rishon", "B", "SU(2) quantum link model + det term", 38432),
        ("fuzzy", "C", "fuzzy gauge theory, K1 + r K2, r = 1", 101197218))
GENERAL_FILE = {"twelve": "results/twelve/step.json", "spinnet": "results/spinnet/step.json", "lsh": "results/lsh/step.json",
                "rishon": "results/rishon/step3.json", "fuzzy": "results/fuzzy/step.json"}
LOOPS = {"twelve": (("twelve", "step"),), "spinnet": (("spinnet", "step"),), "lsh": (("lsh", "step"),),
         "rishon": (("rishon", "step"),), "fuzzy": (("fuzzy_ub", "UB"), ("fuzzy_link", "UE"))}
LOOP_UNIT = {"twelve": "step", "spinnet": "step", "lsh": "step", "rishon": "loop unit U_B U_E (no det layer)",
             "fuzzy_ub": "U_B", "fuzzy_link": "U_E (one link)"}
WAITS_FOR = {"twelve": "prompts/008 Phase C replay (M2c gate)", "spinnet": "prompts/008 Phase C replay (M2c gate)",
             "lsh": "the LSH loop (M8 phases 1-2, prompts/401)", "rishon": "prompts/008 Phase C replay and Report 6 (prompts/204-205)",
             "fuzzy_ub": "prompts/008 Phase C replay (M2c gate) and prompts/010 step H.2",
             "fuzzy_link": "prompts/008 Phase C replay (M2c gate) and prompts/010 step H.2"}
SPECTRA_COMMAND = "python scripts/m11_results.py"


def _root(root):
    from su2plaq.compress.spec import ROOT

    return pathlib.Path(root) if root is not None else pathlib.Path(ROOT)


def git_snapshot(root=None):
    """{"git_commit","git_dirty"} as of now.  A script that writes several tracked files takes this ONCE, before the first write, and
    passes it to every writer (`git=`): otherwise the second file sees the first one as an uncommitted change (git_dirty always true).
    `root` given: the state of the git repository holding `root` (`git -C <root>`), the repository whose files are being written;
    `root=None`: the checkout this package lives in (unchanged behaviour).  Same conventions as `provenance()` ("unknown" /
    None outside a repository; dirty = uncommitted tracked changes)."""
    from su2plaq.metrics import provenance as P

    kw = {} if root is None else {"cwd": pathlib.Path(root)}
    commit = P._git("rev-parse", "--short", "HEAD", **kw)
    status = P._git("status", "--porcelain", "--untracked-files=no", **kw)
    return {"git_commit": commit if commit else "unknown", "git_dirty": bool(status) if status is not None else None}


def _prov(command, git=None, root=None):
    """Provenance dict; `git` = a `git_snapshot()` taken earlier (default: take one now, in `root` if given).  `root` = the project
    root the files are read from / written to (default: this checkout); its resolved path is recorded as `root`.  Everything else is
    read per file."""
    from su2plaq.metrics.provenance import provenance

    p = provenance({})
    if git is None and root is not None:
        git = git_snapshot(root)
    if git is not None:
        p["git_commit"], p["git_dirty"] = git["git_commit"], git["git_dirty"]
    p["root"] = str(_root(root).resolve())
    p["command"] = command
    return p


def _write_json(d, path):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, indent=1) + "\n")


def _ks_block(g2):
    return np.array([[0.0, -2.0 / g2], [-2.0 / g2, 1.5 * g2]])


def _cached_headline(enc, kind, root):
    """(headline dict, None) when the archive's headline is cached and valid, else (None, reason)."""
    from su2plaq.compress import robust as RB

    h = RB.headline(enc, kind, root=root, compute=False)
    cache = root / "results" / "compress" / enc / "robust.json"
    if h is None:
        why = (f"results/compress/{enc}/robust.json is present but stale for the current code hash" if cache.exists()
               else f"no cache file results/compress/{enc}/robust.json")
        return None, f"{why}; waits for {WAITS_FOR[enc]}"
    if h.get("id") is None or not h.get("ranking"):
        return None, f"the {enc} archive has no ranked valid entry; waits for {WAITS_FOR[enc]}"
    return h, None


# ------------------------------------------------------------------------------------------------ spectra.json
def _embedding_record(model) -> dict:
    """The `embedding[model]` entry of spectra.json: residuals as max-entry norms, the leaks stored squared (exact values 1/2, 1; 15, 33/8, 4)."""
    from su2plaq.crosscheck import embed as EM

    r = EM.link_compression(model)
    rec = {k: float(r[k]) for k in ("isometry", "U", "L", "R", "HE", "P_commutes_generators", "plaquette")}
    rec.update({"phase": [complex(r["phase"]).real, complex(r["phase"]).imag], "leak_U_sq": float(r["leak_U"] ** 2),
                "leak_plaquette_sq": float(r["leak_plaquette"] ** 2)})
    return rec


def spectra_results(out=None, root=None, headline=True, command=None, git=None):
    """Compute every number of the spectra cross-check and write it (out=None: <root>/results/crosscheck/spectra.json; out=False: write
    nothing; else the given path).  Returns the dict.  `headline=False` skips the headline cross-verdicts (recorded as skipped)."""
    from su2plaq.compress.spec import get_encoding
    from su2plaq.crosscheck import embed as EM
    from su2plaq.crosscheck import ks as K
    from su2plaq.crosscheck import limits as LM
    from su2plaq.evaluate.evaluator import evaluate
    from su2plaq.fuzzy import link as fz
    from su2plaq.fuzzy import observables as fo
    from su2plaq.rishon import operators as rops

    root = _root(root)
    ENCS = K.KS_ENCODINGS
    d = {"schema": "crosscheck-spectra-1",
         "params": {"g2_list": list(G2S), "closed_L": list(CLOSED_L), "full_L": list(FULL_L), "headline_cross_verdicts": bool(headline)}}
    # ---- same model (prompts/009 §3.1)
    ks = {"max_pairwise_level_dev": {}, "levels": {}, "hb_multiplicities": {}, "cross_verdicts": [], "headline_skipped": []}
    for g2 in G2S:
        ev = {e: np.linalg.eigvalsh(K.ks_hamiltonian(e, g2, True)) for e in ENCS}
        ks["max_pairwise_level_dev"][str(g2)] = float(max(np.abs(ev[a] - ev[b]).max() for a in ENCS for b in ENCS))
        ks["levels"][str(g2)] = ev["twelve"].tolist()
    for e in ENCS:
        v, c = np.unique(np.round(np.linalg.eigvalsh(K.ks_operators(e)[2]), 9) + 0.0, return_counts=True)
        ks["hb_multiplicities"][e] = {str(float(x)): int(n) for x, n in zip(v, c)}
    worst = 0.0
    for (a, b) in ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00)):
        for o in (1, 2):
            own = {e: get_encoding(e).target("step", a, b, o) for e in ENCS}
            for s in ENCS:
                for t in ENCS:
                    if s != t:
                        worst = max(worst, float(np.linalg.norm(K.transported_target(s, t, "step", a, b, o) - own[t], 2)))
    ks["transported_target_max"] = worst

    def record(circ, targ, which, qc, info, a, b, t0):
        enc = get_encoding(circ)
        v = evaluate(qc, enc, K.transported_target(targ, circ, "step", a, b, 1))
        r = {"circuit": circ, "target": targ, "which": which, "entry": info["entry"], "alpha": a, "beta": b, "ok": bool(v.ok),
             "total_error": float(v.total_error), "certified": bool(v.certified), "outer_bits_read": int(v.outer_bits_read),
             "seconds": time.time() - t0}
        if which == "general":                               # negative control: the same circuit against the target at beta + 1e-6
            bad = evaluate(qc, enc, K.transported_target(targ, circ, "step", a, b + 1e-6, 1))
            r["mutant"] = {"beta_shift": 1e-6, "ok": bool(bad.ok), "block_error": float(bad.block_error)}
        return r

    for circ, targ in (("twelve", "lsh"), ("spinnet", "twelve"), ("lsh", "spinnet")):
        a, b = ANGLES[0]
        t0 = time.time()
        qc, info = K.step_circuit(circ, "general", a, b, 1)
        ks["cross_verdicts"].append(record(circ, targ, "general", qc, info, a, b, t0))
    for circ, targ in (("twelve", "spinnet"), ("spinnet", "lsh"), ("lsh", "twelve")):
        if not headline:
            ks["headline_skipped"].append({"circuit": circ, "target": targ, "which": "headline", "reason": "headline=False (scripts/m11_results.py --no-headline)"})
            continue
        h, why = _cached_headline(circ, "step", root)
        if h is None:
            ks["headline_skipped"].append({"circuit": circ, "target": targ, "which": "headline", "reason": why})
            continue
        for (a, b) in ANGLES:
            t0 = time.time()
            qc, info = K.step_circuit(circ, "headline", a, b, 1, root=root)
            ks["cross_verdicts"].append(record(circ, targ, "headline", qc, info, a, b, t0))
    d["ks"] = ks
    # ---- compression identity (prompts/009 §3.2); the leaks are stored squared (exact values 1/2, 1; 15, 33/8, 4)
    d["embedding"] = {m: _embedding_record(m) for m in EM.LINK_MODELS}
    # ---- rishon -> KS limit (prompts/009 §3.3)
    closed, full = [], []
    for g2 in G2S:
        ek, vk = np.linalg.eigh(_ks_block(g2))
        pred = -(13.0 / 4.0) / g2 ** 2 * vk[1, :] ** 2
        for L in CLOSED_L:
            ev = np.linalg.eigvalsh(LM.rishon_closed_block(g2 / 2 - 8 * L / 3, 1 / g2, -L)) + 8 * L
            dev = ev[:2] - ek
            closed.append({"g2": g2, "L": float(L), "dev": dev.tolist(), "L_times_dev": (L * dev).tolist(), "predicted": pred.tolist()})
        for L in FULL_L:
            r = LM.rishon_ks_limit(g2, L)
            full.append({"g2": g2, "L": float(L), "max_dev": r["max_dev"], "L_times_max_dev": L * r["max_dev"],
                         "gap_to_next_band": r["gap_to_next_band"]})
    d["rishon_ks_limit"] = {"rule": {"c_e": "g2/2 - 8 L/3", "c_b": "1/g2", "lam_d": "-L", "shift_full": "24 L", "shift_closed": "8 L"},
                            "closed": closed, "full": full, "dropped_images": LM.rishon_dropped_images(),
                            "block_sizes": {"n_blocks": int(len(LM.rishon_block_sizes())), "largest": int(LM.rishon_block_sizes().max())}}
    # ---- fuzzy (prompts/009 §3.4)
    fb = []
    for signs in itertools.product((1, -1), repeat=4):
        dist = {}
        for g2 in G2S:
            H = LM.fuzzy_flavour_block(g2, signs)
            ev, ek = np.linalg.eigvalsh(H), np.linalg.eigvalsh(_ks_block(g2))
            dist[str(g2)] = float(max(np.abs(ev - x).min() for x in ek))
        fb.append({"signs": list(signs), "dim": int(H.shape[0]), "ks_level_distance": dist})

    def gaps(a, b, g2s):
        return [float(np.diff(LM.fuzzy_isolated_levels(x, a, b)[:2])[0]) for x in g2s]

    w = (0.15, 0.2, 0.3, 0.4, 0.5, 1.0, 2.0, 16.0)
    k1 = {x: LM.fuzzy_isolated_levels(x, 1.0, 0.0) for x in G2S}
    iso = {"k1_only": {"g2": list(G2S), "ground_splitting": gaps(1.0, 0.0, G2S), "third_level": [float(k1[x][2] - k1[x][0]) for x in G2S]}}
    for name, (a, b) in (("k2_only", (0.0, 1.0)), ("r1", (1.0, 1.0))):
        g = gaps(a, b, w)
        iso[name] = {"g2": list(w), "gap": g, "slope_first_pair": float(np.log(g[1] / g[0]) / np.log(w[1] / w[0])),
                     "gap_over_2g2_at_16": g[-1] / 32.0}
    K2 = fz.K2()
    k2e = {}
    for m in ("fuzzy_one", "fuzzy_gamma5"):
        V = np.asarray(EM.link_isometry(m)[0])
        k2e[m] = [float(round(x, 12)) + 0.0 for x in np.real(np.diag(V.conj().T @ K2 @ V))]
    d["fuzzy"] = {"flavour_blocks": fb, "isolated": iso, "k2_on_embeddings": k2e}
    # ---- closed-sector levels side by side (different models: not expected to agree)
    cst = {"g2": list(G2S), "ks": {}, "rishon": {"lam_d=0": {}, "lam_d=0.2": {}, "lam_d=0.5": {}}, "fuzzy": {"r=0": {}, "r=1": {}}}
    for g2 in G2S:
        cst["ks"][str(g2)] = np.linalg.eigvalsh(_ks_block(g2)).tolist()
        for lam in (0.0, 0.2, 0.5):
            cst["rishon"][f"lam_d={lam:g}"][str(g2)] = np.linalg.eigvalsh(rops.closed_block_full(g2, lam)).tolist()
        for r in (0, 1):
            cst["fuzzy"][f"r={r}"][str(g2)] = np.linalg.eigvalsh(fo.closed_sector(g2, float(r))[0]).tolist()
    d["closed_sector_table"] = cst
    # ---- not comparable: the rishon step against the KS step (results/rishon/ks_projection.json)
    f = root / "results" / "rishon" / "ks_projection.json"
    path = "variants.plus.check3_step.circuit_rishon.vs_KS_exact_nominal.op_norm_after_gauge"
    if f.exists():
        x = json.loads(f.read_text())
        for part in path.split("."):
            x = x[part]
        d["not_comparable"] = {"rishon_step_distance_to_ks_step": float(x), "source": f"results/rishon/ks_projection.json: {path}"}
    else:
        d["not_comparable"] = {"rishon_step_distance_to_ks_step": None, "source": "results/rishon/ks_projection.json missing"}
    d["provenance"] = _prov(command or SPECTRA_COMMAND, git, root)
    if out is not False:
        _write_json(d, root / "results" / "crosscheck" / "spectra.json" if out is None else out)
    return d


# ------------------------------------------------------------------------------------------------ gate-table.json
def _general(root, rel):
    f = root / rel
    d = json.loads(f.read_text())
    m = d["metrics"]
    lg = m.get("logical", m)
    t6 = next(r["t_total"] for r in m["t_table"] if abs(float(r["eps"]) - 1e-6) < 1e-15)
    p = d["provenance"]
    return {"qubits": lg["qubits"], "cx": lg["cx"], "n_rot": lg["n_rot"], "t_fixed": lg["t_fixed"], "t_1e6": t6,
            "source": f"{rel} @ {p.get('git_commit')}" + (" (dirty)" if p.get("git_dirty") else "")}


def _pick(ranking):
    """(headline row, T-first row): smallest (robust_key, laptop_key, id); smallest with the first two robust-key components exchanged."""
    rows = [r for r in ranking if r["robust_key"] is not None]
    head = min(rows, key=lambda r: (tuple(r["robust_key"]), tuple(r["laptop_key"]), r["id"]))
    tkey = lambda r: (r["robust_key"][1], r["robust_key"][0], *r["robust_key"][2:], tuple(r["laptop_key"]), r["id"])
    return head, min(rows, key=tkey)


def _pareto(ranking):
    """Non-dominated (cx, t_mean) points of the ranked entries (no other entry with cx <=, t_mean <= and one strict), sorted by cx."""
    rows = [r for r in ranking if r["robust_key"] is not None]
    pts = []
    for r in rows:
        if not any((o["cx"] <= r["cx"] and o["t_mean"] <= r["t_mean"]) and (o["cx"] < r["cx"] or o["t_mean"] < r["t_mean"]) for o in rows):
            pts.append({"entry": r["id"], "cx": r["cx"], "t_mean": r["t_mean"]})
    return sorted(pts, key=lambda p: (p["cx"], p["t_mean"], p["entry"]))


def _cell(r, enc):
    return {"entry": r["id"], "loop_unit": LOOP_UNIT[enc], "qubits": r["qubits"], "cx": r["cx"], "t_nominal": r["t_nominal"],
            "t_mean": r["t_mean"], "depth_mean": r["depth_mean"], "angle_linear": r["angle_linear"],
            "offset_class": r.get("offset_class"), "lean": r.get("lean"), "source": f"results/compress/{enc}/robust.json"}


def _headlines(root):
    """{enc: (headline dict | None, reason | None)} for the six archives."""
    return {enc: _cached_headline(enc, kind, root) for loops in LOOPS.values() for enc, kind in loops}


def gate_table(out=None, root=None, command=None, git=None):
    """One row per encoding in three model blocks (prompts/009 §5.4).  out=None: <root>/results/crosscheck/gate-table.json; out=False:
    write nothing.  A row is "final" only if every source file and headline cache it quotes exists; otherwise "pending: <reasons>"."""
    root = _root(root)
    heads = _headlines(root)
    rows = []
    for enc, block, model, n in ROWS:
        row = {"encoding": enc, "block": block, "model": model, "n_physical_states": n,
               "comparable_with": [e for e, b, _m, _n in ROWS if b == block and e != enc], "general": _general(root, GENERAL_FILE[enc]),
               "headline": None, "t_first": None}
        pending = []
        for e, _k in LOOPS[enc]:
            if heads[e][0] is None:
                pending.append(f"no cached headline for {e}: {heads[e][1]}")
        if enc != "fuzzy":
            if not pending:
                h = heads[enc][0]
                head, tfirst = _pick(h["ranking"])
                row["headline"] = _cell(head, enc)
                row["t_first"] = {"entry": tfirst["id"], "cx": tfirst["cx"], "t_mean": tfirst["t_mean"]}
                row["pareto"] = _pareto(h["ranking"])
        else:
            row["units"] = {e: None for e, _k in LOOPS[enc]}
            row["units_pareto"] = {e: None for e, _k in LOOPS[enc]}
            if not pending:
                picks = {e: _pick(heads[e][0]["ranking"]) for e, _k in LOOPS[enc]}
                row["units"] = {e: _cell(picks[e][0], e) for e in picks}
                row["units_pareto"] = {e: _pareto(heads[e][0]["ranking"]) for e in picks}
                src = "results/fuzzy/compressed_step_headline.json"
                for key, i in (("headline", 0), ("t_first", 1)):
                    ub, lk = picks["fuzzy_ub"][i], picks["fuzzy_link"][i]
                    row[key] = {"entry": f"fuzzy_ub:{ub['id']} + 4 x fuzzy_link:{lk['id']}", "cx": ub["cx"] + 4 * lk["cx"],
                                "t_mean": ub["t_mean"] + 4 * lk["t_mean"], "t_nominal": ub["t_nominal"] + 4 * lk["t_nominal"], "source": src}
                if not (root / src).exists():
                    pending.append(f"{src} missing (prompts/010 step H.3)")
        if enc == "rishon":
            row["general_two_layer"] = _general(root, "results/rishon/step.json")
            row["headline_with_det"] = None
            f = root / "results" / "compress" / "rishon" / "three-layer.json"
            if f.exists() and row["headline"] is not None:
                t = json.loads(f.read_text())["three_layer_key"]
                row["headline_with_det"] = {"cx": int(t[0]), "t_nominal": int(t[1]), "source": "results/compress/rishon/three-layer.json"}
            elif not f.exists():
                pending.append("results/compress/rishon/three-layer.json missing (prompts/204 step C5; Report 6)")
        row["status"] = "final" if not pending else "pending: " + "; ".join(pending)
        rows.append(row)
    d = {"schema": "crosscheck-gate-table-1",
         "unit": "first-order step on the inner links; outer rows separate; T at eps = 1e-6 per rotation (pygridsynth); "
                 "T_avg = mean over the 20 locked angle pairs; headline = smallest robust key (CX first), T-first = same with the first "
                 "two key components exchanged",
         "rows": rows, "provenance": _prov(command or SPECTRA_COMMAND, git, root)}
    if out is not False:
        _write_json(d, root / "results" / "crosscheck" / "gate-table.json" if out is None else out)
    return d


# ------------------------------------------------------------------------------------------------ Markdown
def _fmt(x, nd=1):
    return "-" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def render(root=None):
    """Markdown of Tables 1-3 (prompts/009 §8) from results/crosscheck/{gate-table,spectra}.json."""
    root = _root(root)
    t = json.loads((root / "results" / "crosscheck" / "gate-table.json").read_text())
    s = json.loads((root / "results" / "crosscheck" / "spectra.json").read_text())
    L = ["## Table 1. Gate counts of the first-order inner step (source: gate-table.json)", "",
         "Blocks: A = Kogut-Susskind j_max = 1/2 (same 433 states, like for like); B = SU(2) quantum link model + det term; "
         "C = fuzzy gauge theory. Rows of blocks B and C are a different model: compare within the row only.", "",
         "| block | encoding | model | qubits | general CX | general rot | general fixed T | general T(1e-6) | headline entry | headline qubits | "
         "headline CX | headline T nominal | headline T_avg | angle-linear | Lean | CX general/headline | T general/T_avg | status |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in t["rows"]:
        g, h = r["general"], r["headline"]
        mark = "" if r["block"] == "A" else " (different model)"
        if h:
            ratio = f"{g['cx'] / h['cx']:.2f}" if h["cx"] else "-"
            ratio_t = f"{g['t_1e6'] / h['t_mean']:.2f}" if h.get("t_mean") else "-"
            hc = (f"{h['entry']} | {h.get('qubits', '-')} | {h['cx']} | {_fmt(h.get('t_nominal'))} | {_fmt(h['t_mean'])} | "
                  f"{h.get('angle_linear', '-')} | {h.get('lean', '-')} | {ratio} | {ratio_t}")
        else:
            hc = "pending | - | - | - | - | - | - | - | -"
        L.append(f"| {r['block']} | {r['encoding']} | {r['model']}{mark} | {g['qubits']} | {g['cx']} | {g['n_rot']} | {g['t_fixed']} | "
                 f"{g['t_1e6']} | {hc} | {r['status']} |")
    L += ["", "Ratios between blocks are not efficiency statements: the rows describe different theories on the same lattice.", ""]
    for r in t["rows"]:
        if r["encoding"] == "rishon":
            hd = r.get("headline_with_det")
            L.append(f"Rishon three-layer step with det layer: {('CX ' + str(hd['cx']) + ', T nominal ' + str(hd['t_nominal']) + ' (' + hd['source'] + ')') if hd else 'pending'}; "
                     f"general two-layer step (results/rishon/step.json): CX {r['general_two_layer']['cx']}.")
        if r["encoding"] == "fuzzy":
            for e, u in r["units"].items():
                L.append(f"Fuzzy unit {e}: " + (f"{u['entry']}, CX {u['cx']}, T_avg {_fmt(u['t_mean'])}" if u else "pending"))
    L += ["", "## Table 2. CX first against T first (source: gate-table.json; figure results/crosscheck/tradeoff.pdf)", "",
          "| encoding | headline (CX, T_avg) | T-first pick (entry, CX, T_avg) | general (CX, T(1e-6)) | Pareto points (CX, T_avg) |", "|---|---|---|---|---|"]
    for r in t["rows"]:
        h, f, g = r["headline"], r["t_first"], r["general"]
        par = r.get("pareto")
        if r["encoding"] == "fuzzy" and r.get("units_pareto"):
            par = None
        L.append(f"| {r['encoding']} | " + (f"{h['cx']}, {_fmt(h['t_mean'])}" if h else "pending") + " | "
                 + (f"{f['entry']}, {f['cx']}, {_fmt(f['t_mean'])}" if f else "pending") + f" | {g['cx']}, {g['t_1e6']} | "
                 + ("; ".join(f"({p['cx']}, {p['t_mean']:.1f})" for p in par) if par else "pending") + " |")
    L += ["", "The project ranks CX first (prompts/001 §1).", "", "## Table 3. Spectra cross-check (source: spectra.json)", "",
          "### 3a. Same model (twelve, spinnet, LSH)", ""]
    ks = s["ks"]
    L.append("Largest level difference between the three Kogut-Susskind encodings: "
             + ", ".join(f"g^2 = {k}: {v:.1e}" for k, v in ks["max_pairwise_level_dev"].items()) + f"; largest transported-target difference {ks['transported_target_max']:.1e}.")
    L += ["", "| circuit | target | kind | entry | alpha, beta | ok | certified | total error | rejected mutant (beta + 1e-6) block error |", "|---|---|---|---|---|---|---|---|---|"]
    for r in ks["cross_verdicts"]:
        mu = r.get("mutant")
        L.append(f"| {r['circuit']} | {r['target']} | {r['which']} | {r['entry']} | {r['alpha']}, {r['beta']} | {r['ok']} | {r['certified']} | "
                 f"{r['total_error']:.1e} | " + (f"{mu['block_error']:.4e} (ok={mu['ok']})" if mu else "-") + " |")
    for r in ks["headline_skipped"]:
        L.append(f"| {r['circuit']} | {r['target']} | headline | pending | - | - | - | - | {r['reason']} |")
    L += ["", "### 3b. The KS link is a compression of the model link", "",
          "| model | largest residual (isometry, U, L, R, H_E, plaquette) | squared leak U | squared leak plaquette |", "|---|---|---|---|"]
    for m, e in s["embedding"].items():
        res = max(e[k] for k in ("isometry", "U", "L", "R", "HE", "P_commutes_generators", "plaquette"))
        L.append(f"| {m} | {res:.1e} | {e['leak_U_sq']:.6g} | {e['leak_plaquette_sq']:.6g} |")
    lim = s["rishon_ks_limit"]
    L += ["", "### 3c. Limits", "", "Rishon model -> Kogut-Susskind limit (c_E = g^2/2 - 8L/3, c_B = 1/g^2, lam_D = -L; our derivation, error ~ 1/L):", "",
          "| g^2 | L | L x max level deviation (433 lowest levels) | gap to the next band |", "|---|---|---|---|"]
    for r in lim["full"]:
        L.append(f"| {r['g2']} | {r['L']:g} | {r['L_times_max_dev']:.4f} | {r['gap_to_next_band']:.2f} |")
    dr = lim["dropped_images"]
    L.append("")
    L.append(f"Physical-state projection: {lim['block_sizes']['n_blocks']} blocks, largest {lim['block_sizes']['largest']}; dropped code images H_B/H_D: "
             f"{dr['HB']['images_outside_code']}/{dr['HD']['images_outside_code']} (weight {dr['HB']['outside_weight_max']:.1e}/{dr['HD']['outside_weight_max']:.1e}).")
    fz = s["fuzzy"]
    n_exact = sum(1 for b in fz["flavour_blocks"] if all(v <= 1e-10 for v in b["ks_level_distance"].values()))
    L += ["", f"Fuzzy model, K1 only: {n_exact} of 16 flavour sectors reproduce the KS 2 x 2 closed block; isolated-plaquette gap exponent "
          f"{fz['isolated']['k2_only']['slope_first_pair']:.4f} (K2 only), {fz['isolated']['r1']['slope_first_pair']:.4f} (r = 1); "
          f"strong-coupling gap / 2g^2 = {fz['isolated']['r1']['gap_over_2g2_at_16']:.7f} at g^2 = 16.", "",
          "### 3d. Closed-sector levels side by side -- different models: these numbers are not expected to agree", ""]
    cst = s["closed_sector_table"]
    for k in cst["ks"]:
        L.append(f"- g^2 = {k}: KS {len(cst['ks'][k])} levels, lowest {cst['ks'][k][0]:.4f}; rishon {len(cst['rishon']['lam_d=0'][k])} levels, lowest "
                 f"{cst['rishon']['lam_d=0'][k][0]:.4f} (lam_D = 0); fuzzy {len(cst['fuzzy']['r=0'][k])} (r = 0) / {len(cst['fuzzy']['r=1'][k])} (r = 1) levels, "
                 f"lowest {cst['fuzzy']['r=0'][k][0]:.4f} / {cst['fuzzy']['r=1'][k][0]:.4f}.")
    nc = s["not_comparable"]
    n_states = {r["encoding"]: r["n_physical_states"] for r in t["rows"]}
    L += ["", "### 3e. Not comparable (different models)", "",
          f"- State counts: {n_states['twelve']} (Kogut-Susskind) / {n_states['rishon']} (rishon) / {n_states['fuzzy']} (fuzzy, fixed far ends).",
          "- Spectra at equal g^2 outside the limits of 3b-3c; one-step unitaries and the shared observables of Reports 5 and 9; gate counts across blocks; any continuum-limit claim.",
          f"- Rishon step at operator-norm distance {_fmt(nc['rishon_step_distance_to_ks_step'], 3)} from the KS step ({nc['source']}).", ""]
    L.append("Sources: results/crosscheck/gate-table.json, results/crosscheck/spectra.json.")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------------------------------ figure
def tradeoff_figure(out=None, root=None):
    """CX against T_avg of every ranked entry, one panel per archive; headline, T-first pick and Pareto front marked.  Archives without a
    cached headline get an empty panel labelled pending.  Returns the path (default <root>/results/crosscheck/tradeoff.pdf)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = _root(root)
    out = pathlib.Path(out) if out is not None else root / "results" / "crosscheck" / "tradeoff.pdf"
    heads = _headlines(root)
    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    for ax, (enc, (h, why)) in zip(axes.ravel(), heads.items()):
        ax.set_title(enc)
        ax.set_xlabel("CX")
        ax.set_ylabel("T_avg (eps = 1e-6, 20 angle pairs)")
        if h is None:
            ax.text(0.5, 0.5, "pending:\nno cached headline", ha="center", va="center", transform=ax.transAxes)
            continue
        rows = [r for r in h["ranking"] if r["robust_key"] is not None]
        ax.scatter([r["cx"] for r in rows], [r["t_mean"] for r in rows], s=14, c="0.6", label="ranked entries")
        par = _pareto(h["ranking"])
        ax.step([p["cx"] for p in par], [p["t_mean"] for p in par], where="post", c="tab:blue", label="Pareto front")
        head, tfirst = _pick(h["ranking"])
        ax.scatter([head["cx"]], [head["t_mean"]], marker="*", s=120, c="tab:red", label="headline (CX first)")
        ax.scatter([tfirst["cx"]], [tfirst["t_mean"]], marker="D", s=40, c="tab:green", label="T-first pick")
        ax.legend(fontsize=7)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, metadata={"CreationDate": None, "Producer": None})
    plt.close(fig)
    return out
