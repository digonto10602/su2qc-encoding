"""Tester 208: rebuild UE and UB with the working tree and compare with the committed .qpy (circuit equality + sha256)."""
import json, sys, hashlib
sys.path.insert(0, 'src')
from qiskit import qpy
from su2plaq.circuits.rishon import build_UE, build_UB
out = {}
for cid, build in (('UE', lambda p: build_UE(p['alpha'])), ('UB', lambda p: build_UB(p['beta']))):
    j = json.load(open(f'results/rishon/{cid}.json')); p = j['params']
    old = qpy.load(open(f'results/rishon/{cid}.qpy', 'rb'))[0]
    new = build(p)
    sha = hashlib.sha256(open(f'results/rishon/{cid}.qpy', 'rb').read()).hexdigest()
    out[cid] = {'params': p, 'equal_to_committed_qpy': bool(new == old), 'n_ops_new': len(new.data), 'n_ops_old': len(old.data),
                'sha256_stored_matches_file': sha == j['files']['sha256']}
print(json.dumps(out, indent=1)); json.dump(out, open('results/rishon/tester-208-rebuild-circuits.json', 'w'), indent=1)
