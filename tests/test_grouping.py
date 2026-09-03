# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 MbitAI — see NOTICE for attribution.
"""Grouping map: tight registry <-> grouping.yaml <-> committed CSVs."""

import csv
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TIGHT_CSV = ROOT / "dataset" / "SecOps_2k.log_structured.csv"
LOOSE_CSV = ROOT / "dataset" / "SecOps_2k.log_structured_loose.csv"


def load_templates() -> list[dict]:
    return yaml.safe_load((ROOT / "configs" / "templates.yaml").read_text())[
        "templates"
    ]


def load_groups() -> dict:
    return yaml.safe_load((ROOT / "configs" / "grouping.yaml").read_text())[
        "loose_groups"
    ]


def test_grouping_covers_registry_once():
    templates = load_templates()
    grouping = load_groups()
    seen: dict[str, str] = {}
    for loose_id, g in grouping.items():
        for tid in g["tight"]:
            assert tid not in seen, f"{tid} in two loose groups"
            seen[tid] = loose_id
    assert set(seen) == {t["id"] for t in templates}
    assert len(grouping) == 10


def test_loose_field_matches_map():
    templates = load_templates()
    grouping = load_groups()
    for t in templates:
        assert t["id"] in grouping[t["loose"]]["tight"], t["id"]


def test_loose_csv_follows_map():
    grouping = load_groups()
    tight_to_loose = {t: lg for lg, g in grouping.items() for t in g["tight"]}
    tight_rows = list(csv.DictReader(TIGHT_CSV.open()))
    loose_rows = list(csv.DictReader(LOOSE_CSV.open()))
    assert len(tight_rows) == len(loose_rows) == 2000
    for tr, lr in zip(tight_rows, loose_rows):
        assert lr["EventId"] == tight_to_loose[tr["EventId"]]
        assert lr["Content"] == tr["Content"]
        assert lr["EventTemplate"] == tr["EventTemplate"]
    assert len(Counter(r["EventId"] for r in tight_rows)) == 25
    assert len(Counter(r["EventId"] for r in loose_rows)) == 10
