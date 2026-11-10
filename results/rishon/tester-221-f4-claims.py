"""Tester 221: combinatorial sanity of two F4-004 DISCOVERY claims on 4-bit labels (a,b,c,w) (16 reachable labels):
(i) weight of predicate (a^b)&(c|w) is 6; (ii) a single rccx test  R ^ (l1 & l2)  with R any affine function of the 4 bits (or constant) and l1,l2 literals of distinct
bits has weight in {4,8,12} only (so 6 is unreachable)."""
import itertools, json, os
labs = list(itertools.product((0, 1), repeat=4))
w_pred = sum(((a ^ b) & (c | w)) for a, b, c, w in labs)
affine = []
for mask in range(16):
    for c0 in (0, 1):
        affine.append(tuple((sum(l[i] for i in range(4) if mask >> i & 1) + c0) & 1 for l in labs))
weights = set()
for i, j in itertools.combinations(range(4), 2):
    for si, sj in itertools.product((0, 1), repeat=2):
        A = tuple(((l[i] ^ si) & (l[j] ^ sj)) for l in labs)
        for R in affine:
            weights.add(sum(r ^ x for r, x in zip(R, A)))
print('weight of (a^b)(c|w):', w_pred, '; weights reachable by R^(l1&l2), R affine:', sorted(weights))
json.dump(dict(pred_weight=w_pred, reachable_weights=sorted(weights)), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tester-221-f4-claims.json'), 'w'))
