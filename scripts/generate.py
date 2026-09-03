# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 MbitAI — see NOTICE for attribution.
"""Generate SecOps-2k: fully synthetic security/operations logs.

Reads configs/templates.yaml (single source of truth), emits:
  dataset/SecOps_2k.log                      — syslog-shaped lines
  dataset/SecOps_2k.log_structured.csv       — tight ground truth (LogHub format)
  dataset/SecOps_2k.log_structured_loose.csv — loose grouping variant

Deterministic for a given seed (default 42). Only documentation
(RFC 5737) and private (RFC 1918) addresses are emitted — see NOTICE.
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "templates.yaml"
OUT_LOG = ROOT / "dataset" / "SecOps_2k.log"
OUT_TIGHT = ROOT / "dataset" / "SecOps_2k.log_structured.csv"
OUT_LOOSE = ROOT / "dataset" / "SecOps_2k.log_structured_loose.csv"

HOST = "secops-01"
MONTH, DAY = "Jun", "14"

USERS = [
    "root",
    "admin",
    "ubuntu",
    "ec2-user",
    "oracle",
    "deploy",
    "git",
    "test",
    "guest",
    "nagios",
    "postgres",
    "www-data",
    "operator",
    "support",
    "backup",
]
TARGETS = ["root", "ubuntu", "deploy"]
TTYS = ["pts/0", "pts/1", "tty1"]
PATHS = ["/home/deploy", "/root", "/var/www", "/tmp", "/etc"]
CMDS = [
    "/usr/bin/systemctl restart nginx",
    "/bin/ls",
    "/usr/bin/apt update",
    "/sbin/iptables -L",
    "/bin/cat /etc/passwd",
    "/usr/bin/docker ps",
]
DPORTS = [22, 80, 443, 53, 3306, 5432, 6379, 8080, 8443]
IFACES = ["eth0", "ens3"]
SRC_NETS = [("203.0.113", 60), ("198.51.100", 25), ("192.0.2", 15)]

PID_RANGES = {"sshd": (10000, 30000), "sudo": (30000, 40000), "audit": (1000, 5000)}


def sample_src_ip(rng: random.Random) -> str:
    r = rng.uniform(0, 100)
    upto = 0.0
    net = SRC_NETS[-1][0]
    for prefix, share in SRC_NETS:
        upto += share
        if r <= upto:
            net = prefix
            break
    return f"{net}.{rng.randint(2, 250)}"


def sample_field(name: str, rng: random.Random) -> str:
    if name == "user":
        return rng.choice(USERS)
    if name == "target":
        return rng.choice(TARGETS)
    if name == "src_ip":
        return sample_src_ip(rng)
    if name == "dst_ip":
        return f"10.0.{rng.randint(0, 9)}.{rng.randint(2, 250)}"
    if name == "port":
        return str(rng.randint(1024, 65535))
    if name == "dport":
        return str(rng.choice(DPORTS))
    if name == "dns":
        suffix = rng.choice(["", "-corp", "-mail"])
        return f"host{rng.randint(1, 99)}.example{suffix}.com"
    if name == "tty":
        return rng.choice(TTYS)
    if name == "path":
        return rng.choice(PATHS)
    if name == "cmd":
        return rng.choice(CMDS)
    if name == "uid":
        return str(rng.choice([0, 1000, 1001]))
    if name == "auid":
        return str(rng.choice([1000, 1001, 4294967295]))
    if name == "pid":
        return str(rng.randint(1000, 5000))
    if name == "tries":
        return str(rng.randint(2, 6))
    if name == "iface":
        return rng.choice(IFACES)
    if name == "itype":
        return rng.choice(["8", "0", "3"])
    if name == "icode":
        return rng.choice(["0", "1"])
    if name == "result":
        return rng.choice(["success", "failed"])
    raise KeyError(f"unknown field {name!r}")


def pick_template(templates: list[dict], rng: random.Random) -> dict:
    total = sum(t["weight"] for t in templates)
    r = rng.uniform(0, total)
    upto = 0.0
    for t in templates:
        upto += t["weight"]
        if r <= upto:
            return t
    return templates[-1]


def generate(seed: int, n_lines: int) -> list[dict]:
    cfg = yaml.safe_load(CONFIG.read_text())
    templates = cfg["templates"]
    rng = random.Random(seed)
    ts = datetime(2026, 6, 14, 0, 0, 1)
    rows: list[dict] = []
    for i in range(1, n_lines + 1):
        t = pick_template(templates, rng)
        values = {f: sample_field(f, rng) for f in t["params"]}
        content = t["pattern"].format(**values)
        proc = t["process"]
        if proc == "kernel":
            pid = ""
        else:
            lo, hi = PID_RANGES[proc]
            pid = str(rng.randint(lo, hi))
        ts += timedelta(seconds=rng.randint(0, 7))
        rows.append(
            {
                "LineId": i,
                "Month": MONTH,
                "Day": int(DAY),
                "Time": ts.strftime("%H:%M:%S"),
                "Host": HOST,
                "Process": proc,
                "Pid": pid,
                "Content": content,
                "EventId": t["id"],
                "EventTemplate": t["template"],
                "ParameterList": repr([values[f] for f in t["params"]]),
                "LooseId": t["loose"],
            }
        )
    return rows


COLUMNS = [
    "LineId",
    "Month",
    "Day",
    "Time",
    "Host",
    "Process",
    "Pid",
    "Content",
    "EventId",
    "EventTemplate",
    "ParameterList",
]


def format_line(r: dict) -> str:
    if r["Process"] == "kernel":
        head = f"{r['Host']} kernel:"
    else:
        head = f"{r['Host']} {r['Process']}[{r['Pid']}]:"
    return f"{r['Month']} {r['Day']:>2} {r['Time']} {head} {r['Content']}"


def config_defaults() -> tuple[int, int]:
    cfg = yaml.safe_load(CONFIG.read_text())
    return int(cfg["seed"]), int(cfg["n_lines"])


def main() -> None:
    seed_default, n_default = config_defaults()
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=seed_default)
    ap.add_argument("--n", type=int, default=n_default)
    args = ap.parse_args()

    rows = generate(args.seed, args.n)
    OUT_LOG.write_text("\n".join(format_line(r) for r in rows) + "\n")
    with open(OUT_TIGHT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(OUT_LOOSE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            row = {k: r[k] for k in COLUMNS}
            row["EventId"] = r["LooseId"]
            w.writerow(row)
    print(f"wrote {len(rows)} lines -> {OUT_LOG.relative_to(ROOT)}")
    print(
        f"tight templates: {len({r['EventId'] for r in rows})}, "
        f"loose groups: {len({r['LooseId'] for r in rows})}"
    )


if __name__ == "__main__":
    main()
