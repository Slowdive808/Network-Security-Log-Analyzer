"""
Log parser — normalises CSV, JSON, and syslog (SSH/auth) files into a
standard Pandas DataFrame ready for anomaly detection and DB storage.

Normalised column set
---------------------
timestamp       datetime64[ns]
source_ip       str
dest_ip         str  (may be NaN)
username        str  (may be NaN)
event_type      str  auth | network | system
action          str  login | logout | connect | disconnect | scan | other
status          str  success | failed | error | unknown
port            Int64 (nullable)
protocol        str
bytes_sent      Int64 (nullable)
bytes_received  Int64 (nullable)
raw_line        str
"""

from __future__ import annotations

import json
import re
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd
from dateutil import parser as dateutil_parser


# ── helpers ───────────────────────────────────────────────────────────────────

_SYSLOG_AUTH_RE = re.compile(
    r"(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})"
    r"\s+(?P<host>\S+)\s+\S+:\s+(?P<msg>.+)"
)

_ACCEPTED_RE = re.compile(
    r"Accepted (?:password|publickey) for (?P<user>\S+) from (?P<ip>[\d.]+) port (?P<port>\d+)"
)
_FAILED_RE = re.compile(
    r"Failed (?:password|publickey) for (?:invalid user )?(?P<user>\S+) from (?P<ip>[\d.]+) port (?P<port>\d+)"
)
_DISCONNECT_RE = re.compile(
    r"Disconnected from (?:authenticating user )?(?P<user>\S+)? ?(?P<ip>[\d.]+) port (?P<port>\d+)"
)
_INVALID_USER_RE = re.compile(
    r"Invalid user (?P<user>\S+) from (?P<ip>[\d.]+) port (?P<port>\d+)"
)


def _coerce_timestamp(series: pd.Series) -> pd.Series:
    """Best-effort timestamp parse; returns NaT on failure."""
    return pd.to_datetime(series, errors="coerce", utc=False)


def _normalize_status(val: str) -> str:
    if not isinstance(val, str):
        return "unknown"
    v = val.lower().strip()
    if v in ("success", "accepted", "ok", "200", "true", "1"):
        return "success"
    if v in ("fail", "failed", "failure", "error", "denied", "reject", "false", "0"):
        return "failed"
    return v


def _normalize_event_type(val: str) -> str:
    if not isinstance(val, str):
        return "system"
    v = val.lower()
    if any(k in v for k in ("auth", "login", "ssh", "password", "key")):
        return "auth"
    if any(k in v for k in ("net", "tcp", "udp", "icmp", "connect", "port", "scan", "traffic")):
        return "network"
    return "system"


def _normalize_action(val: str) -> str:
    if not isinstance(val, str):
        return "other"
    v = val.lower()
    if "login" in v or "accept" in v:
        return "login"
    if "logout" in v or "disconnect" in v:
        return "logout"
    if "connect" in v:
        return "connect"
    if "scan" in v:
        return "scan"
    return v


_EMPTY_ROW: dict = {
    "timestamp": pd.NaT,
    "source_ip": None,
    "dest_ip": None,
    "username": None,
    "event_type": "system",
    "action": "other",
    "status": "unknown",
    "port": pd.NA,
    "protocol": None,
    "bytes_sent": pd.NA,
    "bytes_received": pd.NA,
    "raw_line": "",
}

DTYPES = {
    "source_ip": "string",
    "dest_ip": "string",
    "username": "string",
    "event_type": "string",
    "action": "string",
    "status": "string",
    "protocol": "string",
    "raw_line": "string",
}

INT_NULLABLE = {"port", "bytes_sent", "bytes_received"}


def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    """Enforce column schema, types, and order."""
    for col, default in _EMPTY_ROW.items():
        if col not in df.columns:
            df[col] = default

    df["timestamp"] = _coerce_timestamp(df["timestamp"])
    df["status"] = df["status"].apply(_normalize_status)
    df["event_type"] = df["event_type"].apply(_normalize_event_type)
    df["action"] = df["action"].apply(_normalize_action)

    for col, dtype in DTYPES.items():
        df[col] = df[col].astype(dtype)

    for col in INT_NULLABLE:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    return df[list(_EMPTY_ROW.keys())].reset_index(drop=True)


# ── CSV ───────────────────────────────────────────────────────────────────────

# Columns we recognise (case-insensitive aliases → normalised name)
_CSV_COL_MAP = {
    "ts": "timestamp", "time": "timestamp", "datetime": "timestamp",
    "src": "source_ip", "src_ip": "source_ip", "source": "source_ip",
    "dst": "dest_ip", "dst_ip": "dest_ip", "destination": "dest_ip",
    "user": "username", "usr": "username",
    "type": "event_type", "category": "event_type",
    "act": "action", "operation": "action",
    "result": "status", "state": "status",
    "dport": "port", "dest_port": "port",
    "proto": "protocol",
    "sent": "bytes_sent", "bytes_out": "bytes_sent",
    "recv": "bytes_received", "received": "bytes_received", "bytes_in": "bytes_received",
}


def parse_csv(content: str) -> pd.DataFrame:
    df = pd.read_csv(StringIO(content), low_memory=False)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={k: v for k, v in _CSV_COL_MAP.items() if k in df.columns})
    df["raw_line"] = df.apply(lambda r: r.to_json(), axis=1)
    return _finalize(df)


# ── JSON ──────────────────────────────────────────────────────────────────────

def parse_json(content: str) -> pd.DataFrame:
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            # might be {events: [...]} or similar wrapper
            for key in ("events", "logs", "records", "data", "items"):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
        if not isinstance(data, list):
            data = [data]
    except json.JSONDecodeError:
        # Try newline-delimited JSON
        data = [json.loads(line) for line in content.splitlines() if line.strip()]

    df = pd.json_normalize(data)
    df.columns = [c.strip().lower().replace(".", "_") for c in df.columns]
    df = df.rename(columns={k: v for k, v in _CSV_COL_MAP.items() if k in df.columns})
    df["raw_line"] = df.apply(lambda r: r.to_json(), axis=1)
    return _finalize(df)


# ── Syslog (SSH/auth) ─────────────────────────────────────────────────────────

def _parse_syslog_line(line: str, year: int) -> Optional[dict]:
    m = _SYSLOG_AUTH_RE.match(line.strip())
    if not m:
        return None

    row = dict(_EMPTY_ROW)
    row["raw_line"] = line.strip()

    try:
        ts_str = f"{m.group('month')} {m.group('day')} {year} {m.group('time')}"
        row["timestamp"] = dateutil_parser.parse(ts_str)
    except Exception:
        row["timestamp"] = pd.NaT

    msg = m.group("msg")
    row["event_type"] = "auth"

    if ma := _ACCEPTED_RE.search(msg):
        row["username"] = ma.group("user")
        row["source_ip"] = ma.group("ip")
        row["port"] = int(ma.group("port"))
        row["action"] = "login"
        row["status"] = "success"
        row["protocol"] = "ssh"
    elif mf := _FAILED_RE.search(msg):
        row["username"] = mf.group("user")
        row["source_ip"] = mf.group("ip")
        row["port"] = int(mf.group("port"))
        row["action"] = "login"
        row["status"] = "failed"
        row["protocol"] = "ssh"
    elif md := _DISCONNECT_RE.search(msg):
        row["username"] = md.group("user")
        row["source_ip"] = md.group("ip")
        row["port"] = int(md.group("port"))
        row["action"] = "logout"
        row["status"] = "success"
        row["protocol"] = "ssh"
    elif mi := _INVALID_USER_RE.search(msg):
        row["username"] = mi.group("user")
        row["source_ip"] = mi.group("ip")
        row["port"] = int(mi.group("port"))
        row["action"] = "login"
        row["status"] = "failed"
        row["protocol"] = "ssh"
    else:
        return None  # skip unrecognised lines

    return row


def parse_syslog(content: str, year: int = 2024) -> pd.DataFrame:
    rows = []
    for line in content.splitlines():
        row = _parse_syslog_line(line, year)
        if row:
            rows.append(row)

    if not rows:
        return _finalize(pd.DataFrame(columns=list(_EMPTY_ROW.keys())))

    df = pd.DataFrame(rows)
    return _finalize(df)


# ── Auto-detect + dispatch ────────────────────────────────────────────────────

def detect_format(content: str, filename: str = "") -> str:
    fname = filename.lower()
    if fname.endswith(".json"):
        return "json"
    if fname.endswith(".csv"):
        return "csv"
    if fname.endswith((".log", ".syslog", ".auth")):
        return "syslog"

    stripped = content.lstrip()
    if stripped.startswith(("{", "[")):
        return "json"
    # Syslog: lines start with month abbreviation
    first = stripped.splitlines()[0] if stripped else ""
    if re.match(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+", first):
        return "syslog"
    return "csv"


def parse_log_file(path: Path) -> tuple[pd.DataFrame, str]:
    """Return (dataframe, detected_format). Raises ValueError on failure."""
    content = path.read_text(encoding="utf-8", errors="replace")
    fmt = detect_format(content, path.name)

    if fmt == "csv":
        df = parse_csv(content)
    elif fmt == "json":
        df = parse_json(content)
    elif fmt == "syslog":
        df = parse_syslog(content)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    if df.empty:
        raise ValueError("No parseable events found in the log file.")

    return df, fmt
