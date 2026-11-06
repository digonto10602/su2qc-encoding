import json, subprocess
from qiskit import qpy
out={}
commit=subprocess.check_output(['git','rev-parse','--short','HEAD'],text=True).strip()
for n in ['UB','UE','UE_outer_row','step','step_order2']:
    with open(f'results/rishon/{n}.qpy','rb') as f: qc=qpy.load(f)[0]
    ops=qc.count_ops()
    j=json.load(open(f'results/rishon/{n}.json'))
    out[n]={'qpy_cx':ops.get('cx',0)+ops.get('ccx',0)*0,'qpy_ops':dict(ops),'json_keys':[k for k in j][:12],'git_commit':j.get('provenance',{}).get('git_commit'),'dirty':j.get('provenance',{}).get('git_dirty')}
    print(n,{k:v for k,v in ops.items()}, j.get('provenance',{}).get('git_commit'))
json.dump({'commit':commit,'data':out},open('results/rishon/tester-207-qpy-counts.json','w'),indent=1,default=str)
