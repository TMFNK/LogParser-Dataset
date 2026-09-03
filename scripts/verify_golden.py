# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 MbitAI — see NOTICE for attribution.
"""Fail if dataset hashes or Drain scores drift from expected/drain_secops_2k.json."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = ("GA", "PA", "FGA", "FTA")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--expected",
        default=str(ROOT / "expected" / "drain_secops_2k.json"),
    )
    ap.add_argument(
        "--actual",
        default=str(ROOT / "results" / "raw" / "drain_secop_scores.json"),
    )
    ap.add_argument("--atol", type=float, default=1e-4)
    args = ap.parse_args()

    expected = json.loads(Path(args.expected).read_text())
    actual_path = Path(args.actual)
    if not actual_path.exists():
        msg = f"missing scores {actual_path} — run scripts/score_baseline.py"
        raise SystemExit(msg)
    actual = json.loads(actual_path.read_text())

    failed: list[str] = []
    for rel, digest in expected["files"].items():
        got = sha256_file(ROOT / rel)
        if got != digest:
            failed.append(f"{rel}: expected {digest}, got {got}")

    for split in ("tight", "loose"):
        for key in KEYS:
            exp = float(expected[split][key])
            got = float(actual[split][key])
            if abs(exp - got) > args.atol:
                failed.append(f"{split}.{key}: expected {exp}, got {got}")

    if actual.get("n_parsed_templates") != expected.get("n_parsed_templates"):
        failed.append(
            "n_parsed_templates: expected "
            f"{expected.get('n_parsed_templates')}, got "
            f"{actual.get('n_parsed_templates')}"
        )

    if failed:
        raise SystemExit("golden mismatch:\n  " + "\n  ".join(failed))
    print(f"ok: files + scores match {args.expected}")


if __name__ == "__main__":
    main()
