import json, subprocess
from su2plaq.compress import provenance as P
from su2plaq.spinnet import loop as SL
from su2plaq.rishon import compress as RC
got={'provenance_code_hash':P.code_hash(),
 'twelve':P.code_hash_for('twelve'),'spinnet':P.code_hash_for('spinnet'),
 'fuzzy_ub':P.code_hash_for('fuzzy_ub'),'fuzzy_link':P.code_hash_for('fuzzy_link'),
 'rishon':P.code_hash_for('rishon'),'lsh':P.code_hash_for('lsh'),
 'rishon.compress.code_hash':RC.code_hash(),'spinnet.loop.code_hash':SL.code_hash()}
fro=json.load(open('results/tester/434-hashes.json'))
eq={k:got[k]==fro[k] for k in got}
commit=subprocess.check_output(['git','rev-parse','--short','HEAD'],text=True).strip()
json.dump({'commit':commit,'frozen_from':'results/tester/434-hashes.json','got':got,'equal':eq,'all_equal':all(eq.values())},open('results/tester/446/hashes.json','w'),indent=1)
for k in got: print(k,got[k][:8],got[k][-4:],eq[k])
