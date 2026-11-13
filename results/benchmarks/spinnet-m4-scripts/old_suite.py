import subprocess, sys, json, time, os, resource
R="/home/digimonk/Projects/su2qc-encoding"; O=R+"/scratch/old-9c0aee6"
env=dict(os.environ,OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1",PYTHONHASHSEED="20261104")
out=[]
for i in range(3):
    ld=open("/proc/loadavg").read().split()[:3]
    t=time.perf_counter()
    p=subprocess.run(["taskset","-c","14-19",R+"/tools/run-capped",sys.executable,"-m","pytest","-n","6","-q","-p","no:cacheprovider","tests/acceptance/m0","tests/acceptance/m1"],cwd=O,env=env,capture_output=True,text=True)
    w=time.perf_counter()-t
    out.append({"wall":w,"rc":p.returncode,"load_before":ld,"tail":p.stdout[-200:]})
    print(i,w,p.returncode,p.stdout[-120:].replace("\n"," | "),flush=True)
json.dump(out,open(R+"/scratch/bench-m4m7/old_suite.json","w"))
