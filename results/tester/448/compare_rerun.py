import json, math, sys
A='results/crosscheck/'; B='scratch/tester/448/headcopy/results/crosscheck/'
IGN_KEYS={'seconds','timestamp_utc','provenance','wall_seconds','peak_rss_mb','git_commit','git_dirty'}
diffs=[]; nnum=0; maxrel=0.0
def walk(a,b,path):
    global nnum,maxrel
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):
            if k in IGN_KEYS: continue
            if k not in a or k not in b: diffs.append((path+'/'+k,'missing', k in a, k in b)); continue
            walk(a[k],b[k],path+'/'+k)
    elif isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b): diffs.append((path,'len',len(a),len(b))); return
        for i,(x,y) in enumerate(zip(a,b)): walk(x,y,f'{path}[{i}]')
    else:
        if isinstance(a,(int,float)) and isinstance(b,(int,float)) and not isinstance(a,bool):
            nnum+=1
            if a!=b:
                rel=abs(a-b)/max(abs(a),abs(b),1e-300); maxrel=max(maxrel,rel); diffs.append((path,'num',a,b,rel))
        elif a!=b: diffs.append((path,'val',a,b))
out={}
for f in ['spectra.json','gate-table.json']:
    diffs.clear(); nnum=0; maxrel=0.0
    a=json.load(open(A+f)); b=json.load(open(B+f)); walk(a,b,'')
    print(f,'numbers compared',nnum,'differences',len(diffs),'max rel diff',maxrel)
    for d in diffs[:30]: print('  ',d)
    out[f]={'numbers_compared':nnum,'n_diff':len(diffs),'max_rel':maxrel,'diffs':[list(map(str,d)) for d in diffs[:100]]}
    pa=a['provenance']; pb=b['provenance']; print('  provenance committed:',pa['git_commit'],pa['git_dirty'],pa['command'],'| rerun:',pb['git_commit'],pb['git_dirty'],pb['command'])
ta=open(A+'tables.md').read(); tb=open(B+'tables.md').read(); print('tables.md identical:',ta==tb)
out['tables_md_identical']=ta==tb
import hashlib
print('pdf sha256 committed/rerun',hashlib.sha256(open(A+'tradeoff.pdf','rb').read()).hexdigest()[:16],hashlib.sha256(open(B+'tradeoff.pdf','rb').read()).hexdigest()[:16])
json.dump(out,open('results/tester/448/compare_rerun.json','w'),indent=1)
