import xml.etree.ElementTree as ET, json, re, collections, subprocess, sys
t=ET.parse('results/rishon/tester-202-m5.xml')
out=[];
for tc in t.iter('testcase'):
    f=tc.find('failure'); name=tc.get('classname').split('.')[-1]+'::'+tc.get('name')
    if f is None: out.append((name,'PASS','')); continue
    txt=(f.get('message') or '')+(f.text or '')
    m=re.findall(r'PENDING: ([^\n]*)',txt)
    out.append((name,'PENDING' if m else 'FAIL', m[-1] if m else txt[-300:]))
c=collections.Counter(o[1] for o in out); print(c)
cause=collections.Counter(o[2] for o in out if o[1]=='PENDING')
for k,v in cause.items(): print(v,k)
for o in out:
    if o[1]!='PENDING': print(o[:2])
json.dump(dict(commit=subprocess.check_output(['git','rev-parse','--short','HEAD']).decode().strip(),results=out,counts=c),open('results/rishon/tester-202-m5-outcomes.json','w'),indent=1)
