#!/usr/bin/env python3
"""
Generates three realistic synthetic log datasets and saves them to
backend/data/samples/:

  auth_logs.csv   — SSH authentication events with embedded attack patterns
  network_logs.csv— Network traffic events including port-scan patterns
  mixed_logs.json — Combined JSON format with all event types

Attack patterns injected:
  - Brute-force SSH attack (192.168.100.50 → server)
  - Port scan sweep      (10.10.10.200 → internal hosts)
  - Traffic spike        (single 1-hour window with 10× normal volume)
  - Off-hours logins     (legit user logging in at 02:00–03:00)
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# ── configuration ─────────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)

OUT_DIR = Path(__file__).parent / "data" / "samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)

START = datetime(2024, 1, 1, 0, 0, 0)
END = datetime(2024, 1, 31, 23, 59, 59)
TOTAL_DAYS = (END - START).days + 1

USERS = [
    "alice", "bob", "carol", "dave", "eve", "frank",
    "grace", "henry", "iris", "jack", "karen", "leo",
]
INTERNAL_IPS = [f"10.0.{i}.{j}" for i in range(1, 5) for j in range(1, 25)]
EXTERNAL_IPS = [
    f"203.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    for _ in range(40)
]
SERVERS = ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.5"]
PROTOCOLS = ["ssh", "http", "https", "ftp", "smtp", "dns"]
COMMON_PORTS = [22, 80, 443, 21, 25, 53, 3306, 5432, 6379, 8080, 8443]

ATTACKER_IP = "192.168.100.50"    # brute-force source
SCANNER_IP = "10.10.10.200"       # port-scanner source
SPIKE_HOUR = datetime(2024, 1, 15, 14, 0, 0)  # traffic-spike hour
OFFHOURS_USER = "alice"           # off-hours login user


def rand_ts(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def business_ts() -> datetime:
    """Random timestamp during business hours (07–19) on a weekday."""
    day_offset = random.randint(0, TOTAL_DAYS - 1)
    dt = START + timedelta(days=day_offset)
    hour = random.randint(7, 18)
    minute = random.randint(0, 59)
    return dt.replace(hour=hour, minute=minute, second=random.randint(0, 59))


# ── AUTH LOG GENERATOR ────────────────────────────────────────────────────────

def make_auth_events(n_normal: int = 4000) -> list[dict]:
    events = []

    # ── Normal logins (business hours)
    for _ in range(n_normal):
        user = random.choice(USERS)
        ip = random.choice(INTERNAL_IPS + EXTERNAL_IPS[:10])
        ts = business_ts()
        success = random.random() < 0.92
        events.append(
            {
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "source_ip": ip,
                "dest_ip": random.choice(SERVERS),
                "username": user,
                "event_type": "auth",
                "action": "login",
                "status": "success" if success else "failed",
                "port": 22,
                "protocol": "ssh",
                "bytes_sent": random.randint(500, 8000) if success else 0,
                "bytes_received": random.randint(1000, 16000) if success else 0,
            }
        )

    # ── Brute-force attack: 80 failed logins from ATTACKER_IP in 4 min
    bf_start = datetime(2024, 1, 10, 22, 17, 0)
    for i in range(80):
        ts = bf_start + timedelta(seconds=i * 3 + random.randint(0, 2))
        target_user = random.choice(["admin", "root", "alice", "ubuntu"])
        events.append(
            {
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "source_ip": ATTACKER_IP,
                "dest_ip": SERVERS[0],
                "username": target_user,
                "event_type": "auth",
                "action": "login",
                "status": "failed",
                "port": 22,
                "protocol": "ssh",
                "bytes_sent": 0,
                "bytes_received": 0,
            }
        )
    # Attacker finally succeeds
    events.append(
        {
            "timestamp": (bf_start + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "source_ip": ATTACKER_IP,
            "dest_ip": SERVERS[0],
            "username": "alice",
            "event_type": "auth",
            "action": "login",
            "status": "success",
            "port": 22,
            "protocol": "ssh",
            "bytes_sent": 1200,
            "bytes_received": 3400,
        }
    )

    # ── Off-hours logins: alice logs in at 02:00 on Jan 5 and Jan 18
    for day in (5, 18):
        ts = datetime(2024, 1, day, 2, random.randint(10, 50), random.randint(0, 59))
        events.append(
            {
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "source_ip": random.choice(EXTERNAL_IPS[:5]),
                "dest_ip": SERVERS[0],
                "username": OFFHOURS_USER,
                "event_type": "auth",
                "action": "login",
                "status": "success",
                "port": 22,
                "protocol": "ssh",
                "bytes_sent": 980,
                "bytes_received": 2100,
            }
        )

    # ── Off-hours logins: bob logs in at 03:30 on Jan 20
    ts = datetime(2024, 1, 20, 3, 30, 14)
    events.append(
        {
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "source_ip": EXTERNAL_IPS[7],
            "dest_ip": SERVERS[1],
            "username": "bob",
            "event_type": "auth",
            "action": "login",
            "status": "success",
            "port": 22,
            "protocol": "ssh",
            "bytes_sent": 760,
            "bytes_received": 1800,
        }
    )

    return events


# ── NETWORK LOG GENERATOR ─────────────────────────────────────────────────────

def make_network_events(n_normal: int = 5000) -> list[dict]:
    events = []

    # ── Normal traffic
    for _ in range(n_normal):
        src = random.choice(INTERNAL_IPS)
        dst = random.choice(INTERNAL_IPS + SERVERS + EXTERNAL_IPS[:5])
        ts = rand_ts(START, END)
        port = random.choice(COMMON_PORTS + [random.randint(1024, 65535)])
        sent = random.randint(64, 1_500_000)
        events.append(
            {
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "source_ip": src,
                "dest_ip": dst,
                "username": None,
                "event_type": "network",
                "action": "connect",
                "status": "success" if random.random() < 0.88 else "failed",
                "port": port,
                "protocol": random.choice(PROTOCOLS),
                "bytes_sent": sent,
                "bytes_received": int(sent * random.uniform(0.5, 3.0)),
            }
        )

    # ── Port scan: SCANNER_IP touches 200 unique ports on 10.0.0.1 in 90 s
    scan_start = datetime(2024, 1, 22, 11, 5, 0)
    scanned_ports = random.sample(range(1, 65535), 200)
    for i, port in enumerate(scanned_ports):
        ts = scan_start + timedelta(seconds=i * 0.45 + random.uniform(0, 0.3))
        events.append(
            {
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "source_ip": SCANNER_IP,
                "dest_ip": SERVERS[0],
                "username": None,
                "event_type": "network",
                "action": "connect",
                "status": "failed",
                "port": port,
                "protocol": "tcp",
                "bytes_sent": 60,
                "bytes_received": 0,
            }
        )

    # ── Traffic spike: 10× normal volume during SPIKE_HOUR
    normal_rate = n_normal / TOTAL_DAYS / 24  # events per hour
    spike_events = int(normal_rate * 10)
    for _ in range(spike_events):
        ts = SPIKE_HOUR + timedelta(seconds=random.randint(0, 3599))
        sent = random.randint(100_000, 10_000_000)
        events.append(
            {
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "source_ip": random.choice(INTERNAL_IPS),
                "dest_ip": random.choice(EXTERNAL_IPS),
                "username": None,
                "event_type": "network",
                "action": "connect",
                "status": "success",
                "port": 443,
                "protocol": "https",
                "bytes_sent": sent,
                "bytes_received": int(sent * random.uniform(0.1, 0.5)),
            }
        )

    return events


# ── MIXED JSON GENERATOR ──────────────────────────────────────────────────────

def make_mixed_events() -> list[dict]:
    auth = make_auth_events(n_normal=1500)
    net = make_network_events(n_normal=2000)
    all_events = auth + net
    random.shuffle(all_events)
    return all_events


# ── SYSLOG GENERATOR ──────────────────────────────────────────────────────────

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def _syslog_line(ts: datetime, host: str, pid: int, msg: str) -> str:
    return f"{MONTHS[ts.month-1]} {ts.day:2d} {ts.strftime('%H:%M:%S')} {host} sshd[{pid}]: {msg}"


def make_syslog(n_normal: int = 3000) -> list[str]:
    lines = []
    host = "webserver"

    # Normal events
    for _ in range(n_normal):
        user = random.choice(USERS)
        ip = random.choice(INTERNAL_IPS + EXTERNAL_IPS[:8])
        ts = business_ts()
        pid = random.randint(10000, 99999)
        port = random.randint(40000, 65000)
        if random.random() < 0.88:
            lines.append(_syslog_line(ts, host, pid, f"Accepted password for {user} from {ip} port {port} ssh2"))
        else:
            lines.append(_syslog_line(ts, host, pid, f"Failed password for {user} from {ip} port {port} ssh2"))

    # Brute force burst (Jan 8 23:00)
    bf_start = datetime(2024, 1, 8, 23, 0, 0)
    for i in range(60):
        ts = bf_start + timedelta(seconds=i * 4)
        ip = "185.220.101.15"
        port = random.randint(40000, 65000)
        target = random.choice(["root", "admin", "ubuntu", "pi"])
        lines.append(
            _syslog_line(ts, host, random.randint(10000, 99999),
                         f"Failed password for invalid user {target} from {ip} port {port} ssh2")
        )

    return sorted(lines, key=lambda l: l[:15])


# ── write files ───────────────────────────────────────────────────────────────

def main():
    print("Generating sample log datasets …")

    # auth_logs.csv
    auth_events = make_auth_events()
    auth_df = pd.DataFrame(auth_events).sort_values("timestamp")
    auth_path = OUT_DIR / "auth_logs.csv"
    auth_df.to_csv(auth_path, index=False)
    print(f"  ✓ auth_logs.csv       ({len(auth_df):,} events)")

    # network_logs.csv
    net_events = make_network_events()
    net_df = pd.DataFrame(net_events).sort_values("timestamp")
    net_path = OUT_DIR / "network_logs.csv"
    net_df.to_csv(net_path, index=False)
    print(f"  ✓ network_logs.csv    ({len(net_df):,} events)")

    # mixed_logs.json
    mixed_events = make_mixed_events()
    mixed_path = OUT_DIR / "mixed_logs.json"
    mixed_path.write_text(json.dumps(mixed_events, indent=2))
    print(f"  ✓ mixed_logs.json     ({len(mixed_events):,} events)")

    # auth_logs.syslog
    syslog_lines = make_syslog()
    syslog_path = OUT_DIR / "auth_logs.syslog"
    syslog_path.write_text("\n".join(syslog_lines))
    print(f"  ✓ auth_logs.syslog    ({len(syslog_lines):,} lines)")

    print(f"\nAll files written to: {OUT_DIR}")
    print(
        "\nAttack patterns injected:"
        "\n  • Brute-force SSH  — 192.168.100.50  (Jan 10 22:17, 80 attempts)"
        "\n  • Port scan        — 10.10.10.200    (Jan 22 11:05, 200 ports)"
        "\n  • Traffic spike    — Jan 15 14:00–15:00 (10× normal volume)"
        "\n  • Off-hours logins — alice @ 02:xx (Jan 5 & 18), bob @ 03:30 (Jan 20)"
        "\n  • Brute-force SSH  — 185.220.101.15  (Jan 8 23:00, syslog, 60 attempts)"
    )


if __name__ == "__main__":
    main()
