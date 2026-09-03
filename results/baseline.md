# SecOps-2k Drain baseline

Parser: Drain (logparser3), st=0.5 depth=4.
Wall time: 0.2s. Parsed templates: 70 (truth: 25 tight / 10 loose).

| Ground truth | GA | PA | FGA | FTA |
|---|---|---|---|---|
| tight (25) | 0.7720 | 0.6945 | 0.2947 | 0.2526 |
| loose (10) | 0.0475 | 0.6945 | 0.0500 | 0.0250 |

PA is identical for both rows by construction: loose merges grouping
only (see docs/GROUPING-RULES.md). Scores recomputed by
`./reproduce.sh`; raw JSON in `results/raw/drain_secop_scores.json`.
