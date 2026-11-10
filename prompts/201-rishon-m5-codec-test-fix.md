# 201 — M5 codec acceptance test: fix the unsatisfiable "weight 3" input

Date: 2026-11-06
Track: desktop R, branch `m5-rishon`
Scope: one locked test file, two tokens. The plan in force stays `prompts/200-rishon-m5-plan.md` for everything else.

## Trigger
- Builder report on step 5.4 (`reports/fixes/`, latest for M5): `tests/acceptance/m5/test_rishon_codec.py::test_M5_C1_encoding_codec_and_vectors` cannot pass against a correct codec.
- Coordinator check confirmed the assertion is contradictory (see Defect).
- Digonto approved the change to the locked test in chat on 2026-11-06 ("yes go ahead").

## Defect
`tests/acceptance/m5/_ref.py` defines `CODE_A = 3 = 0b0011` and `vac_codes()` puts link b (nibble 0, bits 0-3) of `va` at type A. So in the test

- line 33 asserts `enc.decode(va | outer)` is valid (link b = `0011`, weight 2);
- line 35 asserted `enc.decode(va | outer | (1 << 0)) is None  # link b weight 3`.

But bit 0 of link b is already set in `va`, so `va | outer | (1 << 0) == va | outer`: the same integer is required to decode both as valid and as `None`. The same input (`va | outer | 1`) was used on line 49 for the `pytest.raises(ValueError)` check of `decode_state`, which therefore also could not raise for a correct codec.

Verified numerically: `(va | 1) & 0xF = 0b0011`, popcount 2; `(va | (1 << 2)) & 0xF = 0b0111`, popcount 3.

## Change (the only edits)
File: `tests/acceptance/m5/test_rishon_codec.py`

| line | before | after |
|---|---|---|
| 35 | `enc.decode(va \| outer \| (1 << 0)) is None  # link b weight 3` | `enc.decode(va \| outer \| (1 << 2)) is None  # link b 0011 -> 0111, weight 3` |
| 49 | `enc.decode_state(np.array([va \| outer \| 1], ...), ...)` | `enc.decode_state(np.array([va \| outer \| (1 << 2)], ...), ...)  # link b weight 3` |

`tests/acceptance/LOCK.json`: the sha256 entry for that one file is updated (computed with `tools.check_lock.sha`, written with `json.dumps(lock, indent=1, sort_keys=True) + "\n"` exactly as `tools/lock.py` does). No other entry is touched. `python tools/check_lock.py` must print `LOCK OK`.

`docs/METHODS-rishon.md` does not contain the typo; unchanged.

## Justification
- It is a typo: the comment on line 35 states the intent ("link b weight 3"), and the only way to reach weight 3 from the type-A nibble `0011` with a single OR is to set bit 2 or bit 3. Bit 2 is chosen (`0111`).
- The change does not weaken the test. Before, the "invalid weight" assertion and the `decode_state` `ValueError` check were exercising a valid code and so could never pass; after, they exercise a genuinely invalid code (weight 3, which is not a one-rishon-per-end code under METHODS-rishon R2), which is the check the test was written to make. The weight-1 check on line 36 and the far-colour checks on lines 38-45 are unchanged.
- No tolerance is involved.

## Done-check
1. `python tools/check_lock.py` prints `LOCK OK`.
2. `taskset -c 10-19 pytest -n 10 tests/acceptance/m5/test_rishon_codec.py` passes.
3. `pytest --collect-only -q tests/acceptance` collects 136 tests with no errors.
