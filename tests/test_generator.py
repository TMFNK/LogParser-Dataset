# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 MbitAI — see NOTICE for attribution.
"""Generator properties: determinism, registry consistency, format shape."""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate import COLUMNS, config_defaults, format_line, generate  # noqa: E402


def test_deterministic_same_seed():
    a = generate(42, 200)
    b = generate(42, 200)
    assert [format_line(r) for r in a] == [format_line(r) for r in b]


def test_different_seed_differs():
    a = generate(42, 200)
    b = generate(7, 200)
    assert [format_line(r) for r in a] != [format_line(r) for r in b]


def test_weights_sum_to_100():
    cfg = yaml.safe_load((ROOT / "configs" / "templates.yaml").read_text())
    total = sum(t["weight"] for t in cfg["templates"])
    assert abs(total - 100.0) < 1e-9


def test_registry_params_match():
    cfg = yaml.safe_load((ROOT / "configs" / "templates.yaml").read_text())
    ids = [t["id"] for t in cfg["templates"]]
    assert len(ids) == len(set(ids)) == 25
    for t in cfg["templates"]:
        assert t["template"].count("<*>") == len(t["params"]), t["id"]
        # every declared param placeholder exists in the pattern
        for p in t["params"]:
            assert "{" + p + "}" in t["pattern"], (t["id"], p)


def test_rows_cover_all_templates():
    rows = generate(42, 2000)
    assert {r["EventId"] for r in rows} == {
        t["id"]
        for t in yaml.safe_load((ROOT / "configs" / "templates.yaml").read_text())[
            "templates"
        ]
    }
    assert {r["LooseId"] for r in rows} == {
        g
        for g in yaml.safe_load((ROOT / "configs" / "grouping.yaml").read_text())[
            "loose_groups"
        ]
    }


def test_lineids_sequential():
    rows = generate(42, 500)
    assert [r["LineId"] for r in rows] == list(range(1, 501))
    assert set(COLUMNS) <= set(rows[0])


def test_yaml_defaults_are_seed_42_and_2000():
    seed, n = config_defaults()
    assert seed == 42
    assert n == 2000


def test_committed_log_matches_generator():
    seed, n = config_defaults()
    rows = generate(seed, n)
    committed = (ROOT / "dataset" / "SecOps_2k.log").read_text().splitlines()
    assert [format_line(r) for r in rows] == committed
