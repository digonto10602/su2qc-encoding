import json
r=json.load(open("results/compress/spinnet/robust.json"))["entries"]
for e in ["r02-F1-002","r03-F1-003","r02-F2-002"]:
    m=json.load(open(f"results/spinnet/tester/4_3b/sensb_{e}.json"))["entries"][e]
    own=[x["T"] for x in m]; cx={x["cx"] for x in m}
    lap=r[e]["t_eps"]
    d=[a-b for a,b in zip(own,lap)]
    print(e,"own sum",sum(own),"cache sum",r[e]["t_sum"],"per-pair diffs max|d|",max(map(abs,d)),"CX own",cx,"cache cx",r[e]["cx"])
    print("  diffs",d)
