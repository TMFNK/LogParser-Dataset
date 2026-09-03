# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 MbitAI — see NOTICE for attribution.
"""Drain baseline on SecOps-2k: parse, score vs tight + loose truth.

Writes results/raw/drain_secop_scores.json and results/baseline.md.
Settings are pinned in configs/drain.yaml — do not retune per run.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from seclog.metrics import score_frames  # noqa: E402

DATASET = "SecOps"
LOG = ROOT / "dataset" / "SecOps_2k.log"
RAW = ROOT / "results" / "raw"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    cfg = yaml.safe_load((ROOT / "configs" / "drain.yaml").read_text())
    settings = cfg["datasets"][DATASET]

    from logparser.Drain import LogParser

    RAW.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    parser = LogParser(
        log_format=settings["log_format"],
        indir=str(LOG.parent),
        outdir=str(RAW),
        depth=int(settings["depth"]),
        st=float(settings["st"]),
        maxChild=int(settings.get("max_children", 100)),
        rex=list(settings.get("regex") or []),
    )
    parser.parse(LOG.name)
    elapsed = time.time() - t0

    parsed = pd.read_csv(RAW / f"{LOG.name}_structured.csv")
    gt_tight = pd.read_csv(ROOT / "dataset" / "SecOps_2k.log_structured.csv")
    gt_loose = pd.read_csv(ROOT / "dataset" / "SecOps_2k.log_structured_loose.csv")
    assert len(parsed) == len(gt_tight) == 2000, (len(parsed), len(gt_tight))

    tight = score_frames(gt_tight, parsed)
    loose = score_frames(gt_loose, parsed)

    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        git_sha = "uncommitted"

    scores = {
        "parser": "drain",
        "parser_impl": "logparser3 / logpai.Drain",
        "dataset": "SecOps_2k",
        "synthetic": True,
        "files": {
            "dataset/SecOps_2k.log": sha256_file(LOG),
            "dataset/SecOps_2k.log_structured.csv": sha256_file(
                ROOT / "dataset" / "SecOps_2k.log_structured.csv"
            ),
            "dataset/SecOps_2k.log_structured_loose.csv": sha256_file(
                ROOT / "dataset" / "SecOps_2k.log_structured_loose.csv"
            ),
        },
        "log_sha256": sha256_file(LOG),
        "settings": settings,
        "wall_time_s": round(elapsed, 3),
        "git_sha": git_sha,
        "tight": {k: round(v, 4) for k, v in tight.items()},
        "loose": {k: round(v, 4) for k, v in loose.items()},
        "n_messages": 2000,
        "n_tight_templates": int(gt_tight["EventId"].nunique()),
        "n_loose_groups": int(gt_loose["EventId"].nunique()),
        "n_parsed_templates": int(parsed["EventId"].nunique()),
    }
    (RAW / "drain_secop_scores.json").write_text(json.dumps(scores, indent=2))

    def row(label: str, s: dict[str, float], n: int) -> str:
        return (
            f"| {label} ({n}) | {s['GA']:.4f} | {s['PA']:.4f} "
            f"| {s['FGA']:.4f} | {s['FTA']:.4f} |"
        )

    md = [
        "# SecOps-2k Drain baseline",
        "",
        f"Parser: Drain (logparser3), st={settings['st']} depth={settings['depth']}.",
        f"Parsed templates: {scores['n_parsed_templates']} "
        "(truth: 25 tight / 10 loose).",
        "",
        "| Ground truth | GA | PA | FGA | FTA |",
        "|---|---|---|---|---|",
        row("tight", tight, 25),
        row("loose", loose, 10),
        "",
        "PA is identical for both rows by construction: loose merges grouping",
        "only (see docs/GROUPING-RULES.md). Scores recomputed by",
        "`./reproduce.sh`; raw JSON in `results/raw/drain_secop_scores.json`.",
        "",
    ]
    (ROOT / "results" / "baseline.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
