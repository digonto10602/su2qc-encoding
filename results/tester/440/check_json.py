import json,glob,pathlib,math
R=pathlib.Path('/home/digimonk/Projects/su2qc-encoding')
d=json.load(open(R/'scratch/m8trial440/m8-compressed.json')); x=d['extra']
ok=[]
def chk(name,exp,got,tol=0):
    good = (abs(exp-got)<=tol) if isinstance(exp,(int,float)) and isinstance(got,(int,float)) and not isinstance(exp,bool) else exp==got
    ok.append(good); print(('PASS' if good else 'FAIL'),name,'exp',exp,'got',got)
ent={}
for f in glob.glob(str(R/'compress/archive/lsh/entries/*.json')):
    e=json.load(open(f)); ent[e['id']]=e
rb=json.load(open(R/'results/compress/lsh/robust.json'))['entries']
valid=[i for i,e in ent.items() if e['valid']]
print('n entries',len(ent),'valid',len(valid),'robust',len(rb), 'valid not in robust', [i for i in valid if i not in rb], 'robust not valid',[i for i in rb if i not in valid])
# headline: independent min of robust_key over valid
cands={i:tuple(rb[i]['robust_key']) for i in valid if i in rb}
h=min(cands,key=lambda i:cands[i]); chk('headline id',h,x['headline']['id']); chk('headline robust key',list(cands[h]),x['headline']['robust_key'])
chk('circuit_id',h,d['circuit_id'])
chk('t_mean',rb[h]['t_mean'],x['headline']['t_mean'],1e-12); chk('t_mean=t_sum/20',rb[h]['t_sum']/20,x['headline']['t_mean'],1e-12)
# archive best by key
b=min(valid,key=lambda i:tuple(ent[i]['key'])); chk('archive best',b,x['archive_best']); chk('archive best key',ent[b]['key'],x['archive_best_key'])
chk('n ranking',len(rb),len(x['ranking']))
# angle-set
chk('angle sha',rb[h]['angle_set_sha256'],x['angle_set']['sha256'] if 'sha256' in x['angle_set'] else None)
# before/after rows
r0=json.load(open(R/'results/compress/lsh/round-000.json'))
lab={c['label']:c for c in r0['candidates']}
rows={r['row']:r for r in x['before_after']}
print('round0 labels',list(lab)); print('externals',[ (e['source'],e.get('valid')) for e in r0['external']])
for name,r in rows.items():
    if r['entry']:
        e=ent[r['entry']]; m=e['metrics_raw']
        chk(name+' cx',m['cx'],r['cx']); chk(name+' tfix',m['t_fixed'],r['t_fixed']); chk(name+' nrot',m['n_rot'],r['n_rot'])
        chk(name+' T1e-6',m['t_measured']['1e-06'],r['t_1e-6']); chk(name+' T1e-10',m['t_measured']['1e-10'],r['t_1e-10']); chk(name+' dct',m['depth_ct'],r['depth_ct']); chk(name+' q',m['qubits'],r['qubits'])
        chk(name+' test1e-6',m['t_estimate']['1e-06'],r['t_est_1e-6'],1e-9)
        if r['entry'] in rb: chk(name+' tavg',rb[r['entry']]['t_sum']/20,r['t_avg'],1e-9)
        else: chk(name+' tavg none',None,r['t_avg'])
        chk(name+' lean',{'certified':'certified'}.get(((e.get('lean') or {}).get('status')),'x') if (e.get('lean') or {}).get('status')=='certified' else ('n_a' if (e.get('lean') or {}).get('status','').startswith('n_a') else ('failed' if (e.get('lean') or {}).get('status')=='failed' else 'not_run')),r['lean'])
for lbl in ['general','general+polish','qiskit_l3','wrap_pairs9','wrap_flags4','wrap_flags5','wrap_flags6','wrap_sn_headline','wrap_sn_r05F3','wrap_sn_r02F5']:
    chk(lbl+' id from round0',lab[lbl]['id'],rows[lbl]['entry'])
for e0 in [e for e in r0['external'] if e.get('metrics')]:
    r=rows[e0['source']]; m=e0['metrics']
    chk(e0['source']+' cx',m['cx'],r['cx']); chk(e0['source']+' tfixed',m['t_fixed'],r['t_fixed']); chk(e0['source']+' T1e-6',(m.get('t_measured') or {}).get('1e-06'),r['t_1e-6']);chk(e0['source']+' depth',m.get('depth_ct') if m.get('measured',True) else None,r['depth_ct'])
# families
fam={}
for i in sorted(valid,key=lambda i:cands.get(i,(10**9,)) ):
    if i in cands and ent[i]['family']!='seed': fam.setdefault(ent[i]['family'],i)
for f_,i in fam.items(): chk('best_family_'+f_,i,rows['best_family_'+f_]['entry'])
chk('families rows',sorted(fam),sorted(k[12:] for k in rows if k.startswith('best_family_')))
chk('global_best entry',b,rows['global_best']['entry']); chk('headline row entry',h,rows['headline']['entry']); chk('headline row cx',rb[h]['cx'],rows['headline']['cx'])
# vs_spinnet
m4=json.load(open(R/'results/spinnet/m4-compressed.json'))['extra']['headline']
vs=x['vs_spinnet']
chk('sn id',m4['id'],vs['spinnet_headline']['id']); chk('sn cx',m4['robust_key'][0],vs['spinnet_headline']['cx']); chk('sn tavg',m4['t_mean'],vs['spinnet_headline']['t_avg'])
chk('sn cx value 31',31,vs['spinnet_headline']['cx'])
wr=rb[lab['wrap_sn_headline']['id']]
chk('wrapped cx',wr['cx'],vs['wrapped']['cx']); chk('wrapped cx=31+40',31+40,vs['wrapped']['cx']); chk('wrapped tavg',wr['t_sum']/20,vs['wrapped']['t_avg'],1e-9)
chk('lsh cx',rb[h]['cx'],vs['lsh_headline']['cx']); chk('native_gain',wr['cx']-rb[h]['cx'],vs['native_gain_cx']); chk('overhead',rb[h]['cx']-31,vs['overhead_cx'])
chk('native_gain_t',wr['t_sum']/20-rb[h]['t_sum']/20,vs['native_gain_t_avg'],1e-9); chk('overhead_t',rb[h]['t_sum']/20-m4['t_mean'],vs['overhead_t_avg'],1e-9)
chk('transcoder',{'cx':40,'t_fixed':32},vs['transcoder'])
# pareto
rk=[(i,v) for i,v in cands.items()]
srt=sorted(rk,key=lambda p:(p[1][0],p[1][1],p[0])); fr=[];best=1e99
for i,v in srt:
    if v[1]<best: fr.append(i); best=v[1]
chk('front ids',fr,[p['id'] for p in x['pareto_cx_tavg']])
# stop / rounds
st=json.load(open(R/'results/compress/lsh/stop.json')); print('stop.json keys',list(st.keys()))
print('x.stop',{k:v for k,v in x['stop'].items() if k not in('rounds',)}.keys(), x['stop'].get('stop'),x['stop'].get('streak'),x['stop'].get('sessions'),x['stop'].get('reason'))
# lineage
rnds=[json.load(open(f)) for f in sorted(glob.glob(str(R/'results/compress/lsh/round-*.json')))]
chk('n rounds',len(rnds),x['n_rounds'])
lin=[(c['id'],c.get('parent')) for r in rnds for c in r['candidates'] if c.get('valid') and c.get('key') and c['id'] in r['entries']]
chk('lineage',lin,[(l['id'],l['parent']) for l in x['lineage']])
chk('lineage n',len(lin),len(x['lineage']))
# params/verification
chk('v n_inputs',433,d['verification']['n_inputs']); chk('err<1e-10',True,d['verification']['total_error']<1e-10)
chk('prov dirty reported',True,d['provenance']['git_dirty'])
print('ALL OK',all(ok), sum(ok),'/',len(ok))
