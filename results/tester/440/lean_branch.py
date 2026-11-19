import sys, pathlib, json, time, resource
sys.path.insert(0,'/home/digimonk/Projects/su2qc-encoding/scripts')
import m8_results as M8
from su2plaq.compress import archive as A, robust as RB
from su2plaq.lsh import lean_export as LE, loop as LL
TR=pathlib.Path(sys.argv[1])
sp=LL.spec()
arch=A.Archive.load('lsh',root=TR,n_alt=len(sp.alt_angles),strict=True)
h=RB.headline('lsh','step',root=TR,compute=False)
head=next(e for e in arch.entries() if e.id==h['id'])
thm=TR/'lean'/'certs'/'lsh-best-step.lean'; thm.parent.mkdir(parents=True,exist_ok=True)
def run(label, text):
    thm.write_text(text)
    try:
        b=M8.lean_block(head,TR,theorem_check=True,ranked_head={'angle_linear':True})
        print(label,'-> OK', b['theorem_file_status'], b['axioms'], 'names_headline',b['theorem_names_headline'], 'elab_s', b.get('elaboration_seconds'))
    except RuntimeError as e:
        print(label,'-> RuntimeError:', str(e)[:300].replace('\n',' | '))
first=f'-- entry {head.id}, program sha256 {head.program_sha256}\n'
run('no axioms file', first+'theorem lsh_best : True := trivial\n#print axioms lsh_best\n')
run('sorry file', first+'theorem lsh_best : True := by sorry\n#print axioms lsh_best\n')
run('syntax error', first+'theorem lsh_best : True := by\n')
cert=TR/head.lean['cert_path']
t0=time.time()
LE.write_theorem_file(cert,'lsh_best',thm,comment=f'entry {head.id}, program sha256 {head.program_sha256}')
print('write_theorem_file s',time.time()-t0, thm.stat().st_size)
run('real theorem file', thm.read_text())
print('peak rss MB (python only)',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
