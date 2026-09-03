# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 MbitAI — see NOTICE for attribution.
"""Committed dataset files: presence, size, LogHub-format columns."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "dataset" / "SecOps_2k.log"
TIGHT = ROOT / "dataset" / "SecOps_2k.log_structured.csv"
LOOSE = ROOT / "dataset" / "SecOps_2k.log_structured_loose.csv"

REQUIRED = {"LineId", "Content", "EventId", "EventTemplate", "ParameterList"}


def test_files_exist_and_sized():
    for p in (LOG, TIGHT, LOOSE):
        assert p.exists(), f"missing {p} — run ./reproduce.sh"
    assert len(LOG.read_text().splitlines()) == 2000


def test_loghub_columns_present():
    for p in (TIGHT, LOOSE):
        with open(p) as f:
            cols = set(next(csv.reader(f)))
        assert REQUIRED <= cols, (p, cols)


def test_row_counts_and_lineids():
    for p in (TIGHT, LOOSE):
        rows = list(csv.DictReader(p.open()))
        assert len(rows) == 2000
        assert [int(r["LineId"]) for r in rows] == list(range(1, 2001))
