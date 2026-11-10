import sys, json, pathlib, copy, hashlib
from su2plaq.spinnet import loop
root=pathlib.Path(sys.argv[1]); cf=root/"results/compress/spinnet/robust.json"
real=loop.robust_metrics; calls=[]
orig_cache=json.loads(cf.read_text())
def stub(path, sp=None, root=None):      # counting stub returning the cached record (cheap); marks recomputation
    calls.append(pathlib.Path(path).name)
    sha=hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    rec=[r for r in orig_cache["entries"].values() if r["program_sha256"]==sha][0]
    return copy.deepcopy(rec)
loop.robust_metrics=stub
def run(label, refresh=False):
    calls.clear(); h=loop.headline(root, refresh=refresh); print(f"{label}: recomputed={len(calls)} headline={h['id']} n_rank={len(h['ranking'])}"); return len(calls)
res={}
res["warm"]=run("1 warm cache")
c=json.loads(cf.read_text()); c["entries"]["r02-F1-002"]["program_sha256"]="0"*64; cf.write_text(json.dumps(c))
res["entry_sha_changed"]=run("2 cached program_sha256 of r02-F1-002 altered")
c=json.loads(cf.read_text()); c["angle_set"]["sha256"]="1"*64; cf.write_text(json.dumps(c))
res["angle_set_sha_changed"]=run("3 cached angle-set sha altered")
c=json.loads(cf.read_text()); c["evaluator_sha256"]="2"*64; cf.write_text(json.dumps(c))
res["evaluator_sha_changed"]=run("4 cached evaluator sha altered")
res["refresh"]=run("5 refresh=True", refresh=True)
res["warm_again"]=run("6 warm again")
idx=root/"compress/archive/spinnet/entries/r02-F1-002.json"
e=json.loads(idx.read_text()); e["program_sha256"]="3"*64; idx.write_text(json.dumps(e))
loop.robust_metrics=real
try:
    h=loop.headline(root); print("7 archive sha altered: NO ERROR, headline",h["id"]); res["archive_sha_changed"]="no error"
except Exception as ex:
    print("7 archive sha altered ->",type(ex).__name__, str(ex)[:160]); res["archive_sha_changed"]=type(ex).__name__
print(json.dumps(res))
json.dump(res,open(sys.argv[2],"w"))
