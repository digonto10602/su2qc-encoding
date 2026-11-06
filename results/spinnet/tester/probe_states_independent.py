"""Independent enumeration of the 433 physical codes (even number of j=1/2 links at every 4-valent corner; a corner with all four
links j=1/2 carries the extra J bit (2 singlets)), compared with the codes in the certificate."""
import json, itertools
CORN = [(0, 3), (0, 1), (1, 2), (2, 3)]            # inner links at corner c (bits 0..3)
# outer links: bits 8..15 ; corner c has outer links 8+2c, 9+2c  (checked against enc below)
cert = json.load(open('results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json'))
cc = [s['terms'][0]['code'] for s in cert['states']]
from su2plaq.encodings.spinnet import label_of_code
cnt = 0; got = set()
for links in range(1 << 12):
    inner = links & 0xF; outer = links >> 4
    ok = True; full4 = []
    for c, (a, b) in enumerate(CORN):
        n = ((inner >> a) & 1) + ((inner >> b) & 1) + ((outer >> (2 * c)) & 1) + ((outer >> (2 * c + 1)) & 1)
        if n % 2: ok = False; break
        full4.append(n == 4)
    if not ok: continue
    for Js in itertools.product(*[(0, 1) if f else (0,) for f in full4]):
        code = inner | sum(J << (4 + c) for c, J in enumerate(Js)) | (outer << 8)
        got.add(code)
print('independent count', len(got), 'cert states', len(cc), 'sets equal:', got == set(cc), 'distinct', len(set(cc)))
