"""Tester 219: static import / forbidden-name scan of the four round-1 programs (own ast walk), sha256 file vs archive vs round JSON."""
import sys, json, hashlib, importlib.util, os
sp = importlib.util.spec_from_file_location("c", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tester-219-common.py"))
C = importlib.util.module_from_spec(sp); sp.loader.exec_module(C)
rnd = json.load(open(os.path.join(C.ROOT, "results/compress/rishon/round-002.json")))
out = {}
for cid, fam in C.CANDS:
    p = C.program_path(cid)
    mods, bad = C.imports_of(p)
    ok = []
    for m in mods:
        if m.startswith("."):
            ok.append((m, False)); continue
        ok.append((m, m in C.ALLOWED_PROJECT or m.split(".")[0] in C.ALLOWED or m == "su2plaq.compress.spec.get_encoding" or m == "su2plaq.compress.builder.Builder"))
    sha = hashlib.sha256(open(p, "rb").read()).hexdigest()
    e = C.entry(cid)
    rc = [c for c in rnd["candidates"] if c["id"] == cid][0]
    out[cid] = dict(path=e["program_path"], sha_file=sha, sha_archive=e["program_sha256"], sha_round=rc["program_sha256"], sha_equal=sha == e["program_sha256"] == rc["program_sha256"],
                    imports=ok, all_whitelisted=all(x[1] for x in ok), forbidden_names=bad)
    print(cid, out[cid]["sha_equal"], out[cid]["all_whitelisted"], [m for m, k in ok], bad)
json.dump(out, open(os.path.join(C.ROOT, "results/rishon/tester-219-static.json"), "w"), indent=1)
