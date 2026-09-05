# LogParser-Dataset

SecOps-2k is 2,000 synthetic security log lines (sshd, sudo, firewall,
auditd) with template labels in LogHub format. Parser papers all evaluate
on LogHub infra logs. Nothing comparable exists for security telemetry,
so we made one.

- 25 tight templates and 10 loose groups. Grouping strictness is a
  variable here, not a given.
- Seeded generator. The same seed gives byte-identical files.
- Drain baseline scored with GA, PA, FGA, FTA (the LogHub-2.0 metrics).
- Nothing real inside. Only documentation and private address ranges,
  no real hosts, users, or IPs.

Keywords: log parsing, log dataset, intrusion detection, sshd, benchmark,
grouping accuracy, parsing accuracy, FGA, FTA, synthetic data,
reproducibility.

GitHub topics: `log-parsing` `log-dataset` `intrusion-detection`
`benchmark` `synthetic-data` `loghub` `reproducibility` `drain`

## Project pipeline

- **Tier A — [LogParser-Harness](https://github.com/TMFNK/LogParser-Harness):**
  the reproducible Drain evaluation harness for LogHub-2k and SecOps-2k.
- **Tier B — this repository:** the synthetic SecOps-2k dataset, grouping
  rules, and pinned Drain baseline.
- **Tier C — [LogParser-Trail](https://github.com/TMFNK/LogParser-Trail):**
  the deterministic-first parser, audit trail, SecOps-2k results, and
  optional local-model review.

## One-command run

```bash
./reproduce.sh
```

Needs Python 3.12+ and [uv](https://docs.astral.sh/uv/). Regenerates the
dataset from the yaml seed, validates it, runs Drain, checks
`expected/drain_secops_2k.json`, lints and tests the code, and writes
`results/baseline.md`. CI also rejects drift in the committed dataset or
baseline after regeneration.

## What is pinned

| Item | Where |
|---|---|
| Generator seed and length | `configs/templates.yaml` (`seed: 42`, `n_lines: 2000`) |
| Template registry | `configs/templates.yaml` |
| Tight → loose map | `configs/grouping.yaml` + `docs/GROUPING-RULES.md` |
| File sha256 | `expected/drain_secops_2k.json` |
| Drain `log_format`, `depth`, `st`, `regex` | `configs/drain.yaml` |
| Metric formulas | `seclog/metrics.py` (Jiang et al., ISSTA'24 §4.2) |
| Expected Drain scores | `expected/drain_secops_2k.json` |
| Python deps | `uv.lock` |
| CI | `.github/workflows/reproduce.yml` |

Datasheet: `docs/DATASHEET.md`.

## Layout

```text
LogParser-Dataset/
├── README.md CITATION.cff LICENSE NOTICE CONTRIBUTING.md
├── configs/
│   ├── templates.yaml   # 25-template registry (annotation source of truth)
│   ├── grouping.yaml    # tight -> loose map (10 groups)
│   └── drain.yaml       # pinned Drain baseline settings
├── dataset/             # COMMITTED on purpose, the data is the artifact
│   ├── SecOps_2k.log
│   ├── SecOps_2k.log_structured.csv        # tight ground truth
│   └── SecOps_2k.log_structured_loose.csv  # loose grouping variant
├── docs/GROUPING-RULES.md
├── docs/DATASHEET.md
├── expected/drain_secops_2k.json
├── scripts/
│   ├── generate.py
│   ├── validate.py
│   ├── score_baseline.py
│   └── verify_golden.py
├── seclog/metrics.py
├── results/baseline.md
└── tests/
```

## Ground-truth columns

`LineId, Month, Day, Time, Host, Process, Pid, Content, EventId,
EventTemplate, ParameterList`. That is the LogHub `*_structured.csv`
shape (Content, EventId, EventTemplate, ParameterList), so any LogHub
eval code reads these files unchanged. The loose file differs in
`EventId` only. Grouping merges, templates stay identical.

## Grouping variants

Tight (25 templates) keeps outcome, `invalid user`, process, UFW
action and protocol, and auditd event type all constant. Full rules in
`docs/GROUPING-RULES.md`.

Loose (10 groups) merges lines that describe the same security event
from different daemons. `Failed password` plus the pam failure line
both become L_AUTH_FAIL, for example.

## Metrics

Independent Apache-2.0 code (`seclog/metrics.py`, shared with
TMFNK/LogParser-Harness). We do not copy Loghub-2.0
`benchmark/evaluation/` (GPL-3). PA and FTA come out identical for both
variants by construction: the loose file differs in `EventId` only, and
both scores are computed over template strings. GA and FGA show the
grouping effect.

- **GA** — share of messages whose parsed group equals the ground-truth group
- **PA** — share of messages whose template tokens match exactly
- **FGA** — F1 of grouping accuracy at template level
- **FTA** — F1 of template accuracy (messages share one ground-truth
  template and tokens match)

## Manual steps

```bash
uv sync --frozen --extra dev
uv run python scripts/generate.py
uv run python scripts/validate.py
uv run python scripts/score_baseline.py
uv run python scripts/verify_golden.py
uv run ruff check .
uv run pytest -q
```

## License

Apache-2.0, copyright 2026 MbitAI. See LICENSE and NOTICE.

Need this applied to your own log pipelines? https://www.mbitai.com

## Must-cite

If you publish numbers on SecOps-2k, cite this dataset (see
CITATION.cff) and the LogHub papers that defined its format and metrics:

- Zhihan Jiang et al., "A Large-scale Evaluation for Log Parsing
  Techniques: How Far are We?" ISSTA, 2024.
  https://arxiv.org/abs/2308.10828
- Jieming Zhu et al., "LogHub: A Large Collection of System Log Datasets
  for AI-driven Log Analytics." ISSRE, 2023.
  https://arxiv.org/abs/2008.06448

## Limitations

- Synthetic by design. Template shapes mirror real sshd, sudo, UFW, and
  auditd lines, but there is no organic noise, no clock skew, and no
  interleaving from unrelated daemons. Good for comparing parsers, not
  for training detectors.
- 2k scale only. Same tradeoff as LogHub-2k: it runs anywhere, and rare
  templates get few lines (see the imbalance note in GROUPING-RULES.md).
