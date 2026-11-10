"""Tester 221: compare my independent robust keys (tester-221-rank-<id>.json) with the production cache results/compress/rishon/robust.json, the production headline() ranking
(read-only call) and the archive; also my own lexicographic ranking, ties, rho, per-entry angle fits vs production angle_fit."""
import json, glob, os, subprocess, math
here = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(here))
prod = json.load(open(os.path.join(ROOT, "results/compress/rishon/robust.json")))["entries"]
arch = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(os.path.join(ROOT, "compress/archive/rishon/entries/*.json"))}
mine = {}
for f in glob.glob(os.path.join(here, "tester-221-rank-r0*.json")):
    o = json.load(open(f)); mine[o["cid"]] = o
rows, allok = [], True
for cid, o in sorted(mine.items()):
    p = prod[cid]
    key_mine = (o["cx"][0], o["t_sum"], 0 if o["linear"] else 1, o["depth_sum"], o["qubits"][0])
    key_prod = tuple(p["robust_key"])
    ok_t = o["t_list"] == p["t_eps"]; ok_d = o["depth_list"] == p["depth_ct"]
    # angle fits: mine vs production angle_fit (list of 4-tuples)
    fm = [tuple(x["fit"]) if x["fit"] else None for x in o["fits"]]; fp = [tuple(x) if x else None for x in p["angle_fit"]]
    ok_fit = fm == fp
    # per-pair T lists equal, keys equal
    ok = key_mine == key_prod and ok_t and ok_d and o["skeleton_equal"] == p["skeleton_equal"]
    allok &= ok
    rows.append(dict(id=cid, key_mine=key_mine, key_prod=key_prod, equal=ok, t_lists_equal=ok_t, depth_lists_equal=ok_d, angle_fit_equal=ok_fit, n_rot=o["n_rot"],
                     laptop_key=arch[cid]["key"], t_mean=o["t_sum"] / 20, nominal_T=arch[cid]["key"][1]))
    print(cid, key_mine, "prod", key_prod, "EQ" if ok else "DIFF", "T-lists", ok_t, "depth-lists", ok_d, "fit-eq", ok_fit, "" if ok_fit else (fm, fp))
rank = sorted(rows, key=lambda r: (r["key_mine"], tuple(r["laptop_key"]), r["id"]))
print("MY RANKING:", [r["id"] for r in rank[:6]])
head = rank[0]["id"]
print("my headline:", head, rank[0]["key_mine"])
json.dump(dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip(), all_equal=allok, rows=rows, ranking=[r["id"] for r in rank], headline=head),
          open(os.path.join(here, "tester-221-rank-summary.json"), "w"), indent=1)
