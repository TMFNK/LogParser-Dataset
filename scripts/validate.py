# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 MbitAI — see NOTICE for attribution.
"""Validate SecOps-2k: format, alignment, grouping map, privacy guard.

Checks:
  1. 2000 log lines, 2000 rows per CSV, LineId 1..2000, log<->CSV alignment
  2. EventIds cover exactly the 25 tight templates; every template >= 3 lines
  3. tight->loose mapping matches configs/grouping.yaml
  4. ParameterList parses and its length matches the <*> count in EventTemplate
  5. privacy: every IPv4 literal is in RFC 5737 doc or RFC 1918 private ranges
"""

from __future__ import annotations

import ast
import csv
import ipaddress
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "dataset" / "SecOps_2k.log"
TIGHT = ROOT / "dataset" / "SecOps_2k.log_structured.csv"
LOOSE = ROOT / "dataset" / "SecOps_2k.log_structured_loose.csv"

ALLOWED_NETS = [
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1 (RFC 5737)
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2 (RFC 5737)
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3 (RFC 5737)
    ipaddress.ip_network("10.0.0.0/8"),  # private (RFC 1918)
]
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def main() -> None:
    templates_cfg = yaml.safe_load((ROOT / "configs" / "templates.yaml").read_text())
    grouping_cfg = yaml.safe_load((ROOT / "configs" / "grouping.yaml").read_text())
    tight_by_id = {t["id"]: t for t in templates_cfg["templates"]}

    lines = LOG.read_text().splitlines()
    if len(lines) != 2000:
        fail(f"log has {len(lines)} lines, want 2000")

    tight_rows = list(csv.DictReader(TIGHT.open()))
    loose_rows = list(csv.DictReader(LOOSE.open()))
    if len(tight_rows) != 2000:
        fail(f"tight csv has {len(tight_rows)} rows, want 2000")
    if len(loose_rows) != 2000:
        fail(f"loose csv has {len(loose_rows)} rows, want 2000")

    # 1. alignment: "<Mon> <Day> <Time> <Host> <proc>[pid]: <Content>"
    for r in tight_rows:
        i = int(r["LineId"])
        if i < 1 or i > 2000:
            fail(f"LineId out of range: {i}")
            continue
        suffix = (
            f"{r['Host']} "
            + (
                "kernel:"
                if r["Process"] == "kernel"
                else f"{r['Process']}[{r['Pid']}]:"
            )
            + f" {r['Content']}"
        )
        if not lines[i - 1].endswith(suffix):
            fail(f"line {i} misaligned with tight csv")
            break

    # 2. template coverage
    from collections import Counter

    counts = Counter(r["EventId"] for r in tight_rows)
    if set(counts) != set(tight_by_id):
        fail(f"tight ids {sorted(counts)} != registry {sorted(tight_by_id)}")
    for tid, n in sorted(counts.items()):
        if n < 3:
            fail(f"template {tid} has only {n} lines (< 3)")

    # 3. loose mapping
    tight_to_loose: dict[str, str] = {}
    loose_ids: set[str] = set()
    for loose_id, g in grouping_cfg["loose_groups"].items():
        loose_ids.add(loose_id)
        for tid in g["tight"]:
            if tid in tight_to_loose:
                fail(f"tight {tid} in two loose groups")
            tight_to_loose[tid] = loose_id
    if set(tight_to_loose) != set(tight_by_id):
        fail("grouping.yaml does not cover exactly the 25 tight templates")
    for t_row, l_row in zip(tight_rows, loose_rows):
        want = tight_to_loose.get(t_row["EventId"])
        if l_row["EventId"] != want:
            fail(f"line {t_row['LineId']}: loose {l_row['EventId']} != {want}")
            break
        if l_row["Content"] != t_row["Content"] or l_row["LineId"] != t_row["LineId"]:
            fail(f"line {t_row['LineId']}: loose row differs beyond EventId")
            break
        if l_row["EventTemplate"] != t_row["EventTemplate"]:
            fail(f"line {t_row['LineId']}: loose template changed (grouping-only rule)")
            break
    if {r["EventId"] for r in loose_rows} != loose_ids:
        fail("loose csv ids != grouping.yaml groups")

    # 4. ParameterList shape
    for r in tight_rows:
        try:
            params = ast.literal_eval(r["ParameterList"])
        except (SyntaxError, ValueError):
            fail(f"line {r['LineId']}: ParameterList not a literal")
            break
        stars = r["EventTemplate"].count("<*>")
        if not isinstance(params, list) or len(params) != stars:
            fail(f"line {r['LineId']}: {len(params)} params vs {stars} <*>")
            break
        for p in params:
            if not isinstance(p, str):
                fail(f"line {r['LineId']}: non-string param {p!r}")
                break

    # 5. privacy guard: only doc + private IPv4 literals
    blob = LOG.read_text() + TIGHT.read_text()
    bad: set[str] = set()
    for ip in set(IP_RE.findall(blob)):
        addr = ipaddress.ip_address(ip)
        if not any(addr in net for net in ALLOWED_NETS):
            bad.add(ip)
    if bad:
        fail(f"non-doc/private IPs found: {sorted(bad)[:10]}")

    if errors:
        print(f"VALIDATION FAILED ({len(errors)}):")
        for e in errors[:20]:
            print(f"  - {e}")
        sys.exit(1)
    print(
        f"ok: 2000 lines, {len(counts)} tight templates, "
        f"{len(loose_ids)} loose groups, params + privacy guards pass"
    )


if __name__ == "__main__":
    main()
