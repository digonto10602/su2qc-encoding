import json, glob
from su2plaq.compress import provenance as P
from su2plaq.spinnet import loop
rj=json.load(open('results/compress/spinnet/round-001.json'))
print("evaluator_sha256 equal:", rj['evaluator_sha256']==P.code_hash(), P.code_hash()[:12])
print("spinnet.code_sha256 equal:", rj['spinnet']['code_sha256']==loop.code_hash(), loop.code_hash()[:12], rj['spinnet']['shim'])
print("n feedback files:", len(glob.glob('results/compress/spinnet/feedback/*.json')))
