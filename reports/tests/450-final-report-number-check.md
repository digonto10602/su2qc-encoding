# Report 450: tester, number and claim check of `docs/report-12-final-project-report.md`

- Date: 2026-11-22.
- Git commit: `3ccce75` (`git rev-parse --short HEAD`). Report 12 is untracked (new). Several other files (Reports 2, 4, 5 addendum, 11, `CLAUDE.md`, `notes/STATUS.md`, two scripts) were being edited in the working tree by someone else while I worked; I read the working-tree versions, and say below where that matters.
- Prompt in force: `prompts/009` (final cross-encoding report) with `prompts/010`.
- Mode: step (document check; read only; no tests or evaluations were run).
- Related: `reports/tests/448` (milestone-11 gate), `449`; `docs/report-11-cross-encoding-comparison.md`; audits `309`, `308`, `305`.
- Raw data: `results/tester/450/check_table.json` (106 checks, each with the Report 12 line, claim, source value, recomputed value, status).
- Method: every number was read from the file Report 12 cites (JSON via Python, Reports 1 to 11, summary table, STATUS, reports/tests|audits|benchmarks) and compared. Percentages and standard errors were recomputed. Commands: `python3` json reads of `results/crosscheck/{gate-table,spectra}.json`, `results/compress/*/{summary,robust,stop}.json`, `results/*/step.json`, `results/compress/rishon/three-layer.json`, `results/fuzzy/compressed_step_headline.json`; `sed`/`grep` on the docs; `git tag`, `git rev-list`. Generator script: scratchpad `mk450.py` (not committed).

## Verdict: FAIL (minor): 96 of 106 checks match; 10 text edits needed

No wrong gate count, qubit count, rotation count, T value, percentage, error, tolerance, slope, state count, commit hash, tag or report number was found. All ten findings are about wording, scope of a sentence, or a citation that does not contain the quoted number. Each can be fixed as a text edit (list below, by line of `docs/report-12-final-project-report.md`).

## Required edits (exact)

1. **Line 46 and line 69, qubit explanation (the point you asked about).**
   - Written (line 46): "Qubit counts in this section follow the summary table (the register qubits the circuit acts on, outer-link qubits not included); the main table of §3.1 follows Report 11, which also counts the outer-link qubits read as controls, so the two qubit columns differ." Line 69: "Qubits = data + outer-link qubits (read as controls) + ancillas".
   - Both columns are correct (34, 15, 26, 19, 23 from `results/*/step.json` = summary Table 1; 50, 23, 58, 31, 23 from summary Table 2 / `robust.json` / Report 11 Table 1a). The differences are exactly the size of the outer-link register: $50-34=16$ (twelve), $23-15=8$ (spin network), $58-26=32$ (rishon), $31-19=12$ (LSH), $23-23=0$ (fuzzy).
   - The reason given is not accurate. The §3.1 column adds the whole outer register that sits in the evaluator register, whether or not the circuit reads it. The rishon circuits read no outer qubit (Report 6 §2 validity rule (v): "no outer qubit is read or written"; "the 32 outer qubits sit in the register and are never touched"). The spin-network general and headline circuits and the LSH general circuit also read none (`outer_bits_read 0`: Report 3 §3.1, Report 7 §3.1, `spectra.json` `cross_verdicts[5]`). Only the twelve headline (4) and the LSH headline (2) read outer qubits.
   - Fuzzy: 23 and 23 agree because the fuzzy inner step has no outer register in either column (Report 11 §3.2; the 32 outer qubits appear only with the outer rows: 55).
   - Suggested text: replace "(read as controls)" by "(the whole outer-link register of the evaluator: 16 twelve, 8 spin network, 12 LSH, 32 rishon; most circuits read none or few of them)", and add "the fuzzy inner step has no outer register, so its two columns agree (23)".
   - Related unlisted point: the fuzzy $U_B$ general unit has 15 qubits in §3.1 but 23 in `results/fuzzy/UB.json`. The unit register is 8 row qubits + 7 work qubits (Report 9 §2: $U_B$ touches no column or outer qubit), whereas `UB.json` counts the 16-qubit inner register + 7 (my reading of the two reports; not stated in one place).
2. **Line 84, "Every headline is exact on all physical states of its encoding with error between 5e-15 and 1.4e-13 (audit 309 §4.2)".** Audit 309 §4.2 says the own-archive verdict errors of the six headlines (the unit rows) run from $5.1\times10^{-15}$ (spin network) to $1.39\times10^{-13}$ (rishon). Two table rows are not covered: the fuzzy composed step is checked on 40 seeded inputs only, and the rishon three-layer step (error $1.54\times10^{-13}$, outside the range) is certified by composition. Replace "Every headline" by "Every archive headline (the six unit rows)". (Source note: audit 309 quotes $1.39\times10^{-13}$ for rishon while `summary.json` and Report 6 give $1.348\times10^{-13}$; the range holds either way.)
3. **Line 84, citation "fuzzy $U_B$ qubits and general $\bar T$ from Report 11 Table 2 and summary Table 2".** Report 11 Table 2 has no qubit column. The qubits 15 (general) and 10 (headline) are in summary Table 2 and `results/compress/fuzzy_ub/robust.json` (Report 11 Table 1b gives 10 only). Suggested: "fuzzy $U_B$ qubits from summary Table 2 and `robust.json`; general $\bar T$ from Report 11 Table 2".
4. **Line 119, "Every milestone passed a full test run, an audit and (except M10) a benchmark".** `reports/benchmarks/` holds 001 (M0), 002 (M1), 003 (M2), 100 (M3), 200 (M5), 300 (M9), 301 (M4), 302 (M7), 303 (M5d), 304 (M2c), 305 (M6), 306 (M8), 307 (M11). I found no benchmark for M5x or for M10. Suggested: "(except M5x and M10)", or "Each milestone listed here passed ...". Also: the M10 gate tester report is `reports/tests/303` (PASS; 302 for rounds 1 and 2), while 428 and 429 verify the later headline-rule update; add 303 to the fuzzy M10 entry.
5. **Line 133, "checked at 23–25 pairs, not proved (Reports 2 §6, 6 §3.8)".** Neither cited section contains "23" or "25". Report 6 §3.0 (line 37) says 25 pairs; `docs/METHODS-rishon.md` R12 (line 117, audit 307 N2/N3) says 23 pairs; Report 6 §3.8 says "the angle fit confirmed at the 20 pairs"; Report 2 §6 gives no number (numerical skeleton and alternate-pair checks). The two sources disagree with each other (25 against 23). Suggested: "(rishon: confirmed at 23 to 25 angle pairs, Report 6 §3.0 and METHODS-rishon R12; twelve and spin network: only the three evaluator pairs plus the 20-pair linearity check, Reports 2 §6, 4 §3.8)", or say "confirmed numerically at many angle pairs".
6. **Line 134 (and any same wording elsewhere), "reproduced byte for byte by tester 301".** Tester 301 reports identical numbers in all seven JSON files with floats compared at relative $10^{-9}$ and timings, provenance and hashes excluded, plus 10 of 10 recomputed counts equal. Suggested: "reproduced to identical numbers by tester 301".
7. **Line 126, "order-2 steps and outer rows were not compressed".** The fuzzy composed step with outer rows ($2150\to227$ CX, line 84 of Report 12 itself) uses the compressed link unit on the 8 outer links (96 CX). Rishon outer rows (24 and 96 CX) and the KS outer phase rows are uncompressed. Suggested: "order-2 steps and the KS and rishon outer rows were not compressed (the fuzzy outer links reuse the compressed link unit)".
8. **Lines 6 to 14, "copied from the table in `notes/STATUS.md`".** The STATUS table lists the twelve row as "milestone-0, -1, -2, -2-gate, -11" and the rishon row as "-5, -5x, -5d"; Report 12 adds "-2c" and "-6". Both tags exist, so the content is right; change "copied from" to "from ... updated with `milestone-2c` and `milestone-6`". Plan numbers, locked test folders and `acceptance-v23` all match.
9. **Line 139, "`prompts/008` §15 D1–D10".** `prompts/008` §15 lists D1 to D16; the STATUS decision of 2026-11-16 item 4 says "D1-D10". Write "D1–D16 (STATUS records the decision as D1–D10)" or keep D1–D10 and add "as recorded in STATUS".
10. **Line 51, "per-site transcoder (`cx, cx, rccx` per site, 20 CX and 16 T)".** 20 CX and 16 T is one transcoder over 4 sites (5 CX, 4 T per site), used twice in the step (+40 CX, +32 T; Report 7 §3.4). Suggested: "a transcoder (`cx, cx, rccx` per site on 4 sites: 20 CX and 16 T, used before and after the walk)".

## Notes that need no edit (wording or inherited from sources)

- Line 105, "to $1.8\times10^{-15}$" (fuzzy flavour sectors that match): `spectra.json` stores distances $\le8.9\times10^{-16}$ for those two sectors; $1.8\times10^{-15}$ is tester 422 check F1. Both are far below the $10^{-10}$ tolerance.
- Line 69: `results/crosscheck/gate-table.json` holds the general qubit counts 34, 15, 19, 26, 23 (from `step.json`), not 50, 23, 31, 58; the §3.1 numbers are those of Report 11 Table 1a (= summary Table 2 / `robust.json`).
- Line 88: LSH $\bar T$ rises by $+139.2\%$ (factor 2.39), "roughly doubled" is loose. Line 89: the rishon headline has 6 Walsh rotations on one flip qubit (10 rotations in all); "81 pairs reduced to one rotation on one qubit" would read better as "all 81 pairs share one flip qubit".
- Line 148 (list of source inconsistencies): the working tree now holds uncommitted edits that resolve several of them: Report 11 §4 (iii) now says rule stops, Report 11 §3.3 now explains the 21 and 28 ranked entries, Report 2 N11 now says Digonto accepted the stop (Report 2 §4.3 still says "awaiting", so that bullet stays true), Report 4 now records `5bbaf0f`, the Report 5 addendum §3.6 is marked superseded, and `CLAUDE.md` no longer says every test peaks at 2.2 GB. After those edits are committed, the corresponding bullets of Report 12 §4 (line 146 and 148) become stale and should be removed or reworded.
- Line 148, one more source inconsistency not listed in Report 12: summary Table 2 shows the rishon general circuit as Lean `n_a`, while Reports 6 §3.8 and 11 give native-certified (Report 12 follows Report 11).
- Fuzzy link headline error: `summary.json` gives $5.50\times10^{-15}$ (Report 12 uses $5.5\times10^{-15}$); Report 10 §3.2 still prints $5.6\times10^{-15}$ (pre-replay). No Report 12 edit.

## Check table (condensed; all 106 rows in `results/tester/450/check_table.json`)

| check | expected (source) | got | tolerance | result |
|---|---|---|---|---|
| CX percentages: twelve, spin network, LSH, rishon unit, rishon 3 layers, fuzzy inner, fuzzy with outer | $-62.2,-42.6,-27.7,-97.9,-97.6,-93.0,-89.4\,\%$ | $-62.24,-42.59,-27.66,-97.86,-97.55,-92.96,-89.44$ | 0.05 percentage points | PASS |
| $\bar T$ percentages (six rows) | $-1.7,+94.8,+139.2,-96.0,-93.7,-41.0\,\%$ | $-1.68,+94.79,+139.18,-95.98,-93.70,-40.98$ | 0.05 | PASS |
| $\bar T\pm$ s.e. (10 entries), $s/\sqrt{20}$ from `robust.json` `t_eps` | $943.2\pm2.3$, $927.4\pm2.7$, $560.6\pm1.6$, $1092.0\pm3.1$, $592.6\pm1.6$, $1417.4\pm8.0$, $20620.2\pm58.8$, $829.8\pm2.2$, $634.4\pm3.2$, $628.8\pm3.8$ | all equal (e.g. 2.28, 2.67, 1.62, 3.13, 1.62, 7.99, 58.76, 2.20, 3.25, 3.79) | rounding to 0.1 | PASS |
| fuzzy composed $\bar T$ and quadrature errors | $5336.2\pm17$; $3149.6\pm16$ | 5336.2, 16.68; 3149.6, 15.51 | rounding | PASS |
| §3.1 qubits, both ends (50→31, 23→17, 31→24, 58→52, 23→18, 15→10, 4→4) | Report 11 Tables 1a/1b | equal (`robust.json`, `compressed_step_headline.json`) | exact | PASS |
| §2.2 qubits (34, 15, 26, 19, 23) and CX, rotations, T, errors of the six general steps | summary Table 1 / `step.json` | equal | exact (errors to 2 digits) | PASS |
| explanatory sentence on qubit columns | rule "outer qubits read as controls" | true rule: whole outer register (16, 8, 12, 32; 0 for fuzzy inner) | n/a | FAIL (edit 1) |
| headline rows: CX, rotations, $T$ nominal, errors (8 rows) | summary Table 2, `three-layer.json` ($1.535\times10^{-13}$), `m6-compressed.json` ($1.35\times10^{-13}$), `compressed_step_headline.json` ($1.2047\times10^{-14}$) | equal | exact / 2 digits | PASS |
| fuzzy link general 36 CX, 10 rotations, $T=644$ | summary row | equal | exact | PASS |
| fuzzy $U_B$ qubit citation | Report 11 Table 2 | no qubit column there | n/a | FAIL (edit 3) |
| "every headline exact on all physical states ... 5e-15 to 1.4e-13" | audit 309 §4.2 (six headlines) | composed rows differ | n/a | FAIL (edit 2) |
| §2.3 table: rounds, candidates, valid, programs, headline ids (6 loops) | `summary.json` `n_rounds`, `n_candidates`, `n_valid`; Reports 2, 4, 6, 8 | (0–5, 22, 22), (0–5, 23, 23), (0–6, 24, 23), (0–6, 29, 29), (0–13, 42, 41), (0–2, 5, 4); programs 17, 16, 19, 19 | exact | PASS |
| LSH stop reason | `max_sessions` | `max_sessions` (sessions 20, streak 2) | exact | PASS |
| spectra §3.3: level differences | $2.8,1.2,2.7\times10^{-14}$ (tol $10^{-10}$) | $2.75,1.20,2.66\times10^{-14}$ | $10^{-10}$ | PASS |
| nine cross-verdicts, errors | all ok, $\le2.7\times10^{-13}$ | 9 ok, max $2.72\times10^{-13}$ | $10^{-10}$ | PASS |
| negative control | $2.0\times10^{-6}$, window $[1.9,2.1]\times10^{-6}$ | $2.0000000012$, $2.0000000018$, $2.0000000034\times10^{-6}$ | window | PASS |
| embedding residual and leaks | $\le4.7\times10^{-16}$ (tol $10^{-12}$); 15, 33/8, 4 | $4.72\times10^{-16}$; 15.0, 4.125, 4.0 | $10^{-12}$ | PASS |
| step distance rishon to KS | 1.990 | 1.9904 | 3 digits | PASS |
| rishon limit slopes | $-0.9973,-1.0010,-1.0043$ (tol 0.02) | same | 0.02 | PASS |
| rishon limit coefficient | 0.17, 0.08, 0.30 % (tol 1 %) | 0.17, 0.08, 0.30 | 1 % | PASS |
| fuzzy flavour sectors | 2 of 16; others $\ge0.608$ (locked 0.5) | 2; 0.608 | 0.5 | PASS |
| fuzzy gap exponent | 7.0286 (tol $7\pm0.06$) | 7.0286 | 0.06 | PASS |
| T-first picks (6 archives) | `gate-table.json` | equal; `r01-F5-001`, `r13-F3-013` not angle-linear | exact | PASS |
| tags, acceptance-v23, `milestone-11` at `9b83d10` | `git tag`, `git rev-list` | all 16 tags exist; 9b83d10 | exact | PASS |
| plan table | STATUS table | -2c, -6 added | n/a | FAIL (edit 8) |
| milestone gate numbers: M2 (tester 039–042, audit 004, benchmark 003), M4 (404, 302, 301), M6 (435, 307, 305), M8 (446, 308, 306), M11 (448, 309, 307) | files and verdicts | all exist, testers PASS, audits PASS WITH NOTES, benchmarks PASS or no regression | exact | PASS |
| M11 numbers: 407 of 407 acceptance, 1235 unit | tester 448 | 407 passed, 1235 passed | exact | PASS |
| "every milestone ... (except M10) a benchmark" | `reports/benchmarks/` | no M5x benchmark | n/a | FAIL (edit 4) |
| "all audits PASS WITH NOTES, none blocking" | audits 004, 302, 307, 308, 301, 306, 309 | all PASS WITH NOTES, no blocking | n/a | PASS |
| §4: Report 8 §4 item 6 (no 67-CX circuit, one 64-point walk space) | Report 8 | match, "not a CX lower bound" | n/a | PASS |
| §4: Lean "23–25 pairs" with Reports 2 §6, 6 §3.8 | those sections | numbers absent there; 25 (Report 6 §3.0) vs 23 (METHODS-rishon) | n/a | FAIL (edit 5) |
| §4: audit 301 A1/A2 open; audit 309 N10; audit 308 N2, N4, N5; STATUS item 4 (7.4 GiB, 5.2 GiB); Report 11 21 and 28 ranked; addendum §3.6 228/260; Report 2 §4.3; Report 4 `5bbaf0f` | sources | all verified | n/a | PASS |
| "byte for byte" (tester 301) | tester 301 | identical at relative $10^{-9}$ | n/a | FAIL (edit 6) |
| "outer rows were not compressed" | Report 11 Table 1c | fuzzy outer links use compressed link | n/a | FAIL (edit 7) |
| prompts/008 §15 "D1–D10" | prompts/008 | D1–D16 | n/a | FAIL (edit 9) |
| LSH transcoder wording | Report 7 §3.4 | 20 CX/16 T per transcoder | n/a | FAIL (edit 10) |
| script names in §5 (12 scripts) | `ls scripts` | all exist | n/a | PASS |
| §5 wall times: 76.9 s [76.3, 78.6], n=6, 1.08 GB; 2243 values; 4131 s; 55 531 s | benchmark 307; tester 448; Report 5; addendum | 76.9, 1082 MB, 2243, 4131, 55 531 | exact | PASS |
| LSH Lean "433 proved twice by different rules" | Report 7 §3.6 | match | n/a | PASS |

## Section references checked

Report 1 §3.4 (662 against 1162 T), Report 2 §4.3 and §6, Report 3 §3.1 and §3.2, Report 4 §2 and §3.8, Report 5 addendum §3.6 and §5, Report 6 §2, §3.2, §3.5, §3.7, §3.8, Report 7 §3.4, §3.6, §4, Report 8 §2, §3.2, §4 item 6, Report 9 §2, §3.1, §5, Report 10 §3.2, §3.3, §3.5, §4, §5, Report 11 §3.2 to §3.6 and §4, audit 309 §4.2: each contains the claim it is cited for, except the two citations in edits 3 and 5.

## Counts

Checks: 106; matched 96; text edits needed 10; PENDING 0; new failures against a previous report: not applicable (first check of this document). Cause of each edit (a guess where marked): edits 1, 2, 5, 6, 7 are paraphrases that drifted from Report 11 or the cited report (guess); edits 3, 4, 8, 9, 10 are short-hand citations or counts (guess).
