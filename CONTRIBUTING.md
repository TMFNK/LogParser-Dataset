# Contributing

This repo is a labeled dataset plus a pinned Drain baseline. A useful change
is usually a grouping-rule or template-registry change, not a parser tweak.

## Grouping-rule pull requests

1. Edit `docs/GROUPING-RULES.md` first. State the rule in English with one
   worked example.
2. Keep `configs/templates.yaml` and `configs/grouping.yaml` in sync: every
   tight id appears in exactly one loose group, and each template's `loose`
   field matches that map.
3. Run `./reproduce.sh`. That regenerates `dataset/`, rewrites
   `results/baseline.md`, and checks `expected/drain_secops_2k.json`.
4. If hashes or Drain scores change *because the labels changed*, update the
   golden file in the same PR and say so in the description. Do not retune
   `configs/drain.yaml` to recover an old score.

## What not to send

- Drain `st` / `depth` edits "to get a nicer table."
- Copies of Loghub-2.0 `benchmark/evaluation/` (GPL-3).
- Real hostnames, usernames, or public IPs. `scripts/validate.py` rejects
  IPv4 literals outside RFC 5737 and RFC 1918.

## Checks

```bash
uv sync --extra dev
uv run pytest -q
./reproduce.sh
```
