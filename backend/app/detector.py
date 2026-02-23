"""
Anomaly detection engine.

Four detectors are implemented:
  1. BruteForceDetector  — repeated failed auth from the same source IP
  2. PortScanDetector    — many unique destination ports from one source IP
  3. TrafficSpikeDetector— traffic volume exceeding N std-devs from rolling mean
  4. OffHoursDetector    — successful logins outside configured business hours

Each detector returns a list of dicts matching the Anomaly model schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from app.config import settings


# ── severity helpers ──────────────────────────────────────────────────────────

def _auth_severity(count: int) -> str:
    if count >= 50:
        return "critical"
    if count >= 20:
        return "high"
    return "medium"


def _scan_severity(count: int) -> str:
    if count >= 100:
        return "critical"
    if count >= 50:
        return "high"
    return "medium"


def _spike_severity(z: float) -> str:
    if z >= 6:
        return "critical"
    if z >= 5:
        return "high"
    return "medium"


def _risk_score(severity: str, event_count: int) -> float:
    base = {"low": 20, "medium": 45, "high": 70, "critical": 90}.get(severity, 10)
    bonus = min(10, np.log1p(event_count) * 2)
    return round(min(100.0, base + bonus), 1)


# ── 1. Brute Force ────────────────────────────────────────────────────────────

def detect_brute_force(
    df: pd.DataFrame,
    threshold: int = settings.brute_force_threshold,
    window_minutes: int = settings.brute_force_window_minutes,
) -> list[dict[str, Any]]:
    """Flag source IPs with >= threshold failed auths in a rolling window."""
    failed = df[
        (df["status"] == "failed") & (df["event_type"] == "auth")
    ].copy()

    if failed.empty:
        return []

    failed = failed.sort_values("timestamp").dropna(subset=["timestamp", "source_ip"])
    window = pd.Timedelta(minutes=window_minutes)
    anomalies: list[dict] = []
    seen_windows: set[tuple] = set()

    for ip, group in failed.groupby("source_ip"):
        times = group["timestamp"].values
        n = len(times)
        i = 0
        while i < n:
            t_start = times[i]
            t_end = t_start + np.timedelta64(int(window.total_seconds()), "s")
            mask = (times >= t_start) & (times <= t_end)
            count = int(mask.sum())
            if count >= threshold:
                key = (ip, pd.Timestamp(t_start).floor("min"))
                if key not in seen_windows:
                    seen_windows.add(key)
                    window_rows = group.iloc[mask]
                    users = window_rows["username"].dropna()
                    top_user = users.mode()[0] if not users.empty else None
                    sev = _auth_severity(count)
                    anomalies.append(
                        {
                            "anomaly_type": "brute_force",
                            "severity": sev,
                            "source_ip": str(ip),
                            "username": top_user,
                            "description": (
                                f"Brute-force attack: {count} failed login attempts "
                                f"from {ip} within {window_minutes} min"
                                + (f" targeting user '{top_user}'" if top_user else "")
                            ),
                            "event_count": count,
                            "start_time": pd.Timestamp(t_start).to_pydatetime(),
                            "end_time": pd.Timestamp(times[mask][-1]).to_pydatetime(),
                            "score": _risk_score(sev, count),
                        }
                    )
                # advance past end of this window
                i += int(mask.sum())
            else:
                i += 1

    return anomalies


# ── 2. Port Scan ──────────────────────────────────────────────────────────────

def detect_port_scan(
    df: pd.DataFrame,
    threshold: int = settings.port_scan_threshold,
    window_minutes: int = settings.port_scan_window_minutes,
) -> list[dict[str, Any]]:
    """Flag source IPs probing many unique ports in a short time window."""
    net = df[df["event_type"] == "network"].copy()
    if net.empty:
        # Fallback: any event with a port column filled
        net = df[df["port"].notna()].copy()
    if net.empty:
        return []

    net = net.sort_values("timestamp").dropna(subset=["timestamp", "source_ip", "port"])
    window = pd.Timedelta(minutes=window_minutes)
    anomalies: list[dict] = []
    seen_windows: set[tuple] = set()

    for ip, group in net.groupby("source_ip"):
        times = group["timestamp"].values
        ports = group["port"].values
        n = len(times)
        i = 0
        while i < n:
            t_start = times[i]
            t_end = t_start + np.timedelta64(int(window.total_seconds()), "s")
            mask = (times >= t_start) & (times <= t_end)
            unique_ports = len(set(ports[mask]))
            if unique_ports >= threshold:
                key = (ip, pd.Timestamp(t_start).floor("min"))
                if key not in seen_windows:
                    seen_windows.add(key)
                    sev = _scan_severity(unique_ports)
                    anomalies.append(
                        {
                            "anomaly_type": "port_scan",
                            "severity": sev,
                            "source_ip": str(ip),
                            "username": None,
                            "description": (
                                f"Port scan detected: {ip} probed {unique_ports} unique ports "
                                f"in {window_minutes} min"
                            ),
                            "event_count": int(mask.sum()),
                            "start_time": pd.Timestamp(t_start).to_pydatetime(),
                            "end_time": pd.Timestamp(times[mask][-1]).to_pydatetime(),
                            "score": _risk_score(sev, unique_ports),
                        }
                    )
                i += int(mask.sum())
            else:
                i += 1

    return anomalies


# ── 3. Traffic Spike ──────────────────────────────────────────────────────────

def detect_traffic_spike(
    df: pd.DataFrame,
    z_threshold: float = settings.traffic_spike_threshold,
) -> list[dict[str, Any]]:
    """Flag hourly traffic volumes > z_threshold standard deviations above mean."""
    ts_df = df[df["timestamp"].notna()].copy()
    if ts_df.empty:
        return []

    bytes_col: str | None = None
    for col in ("bytes_sent", "bytes_received"):
        if ts_df[col].notna().sum() > 0:
            bytes_col = col
            break

    if bytes_col is None:
        # Count events per hour as proxy for traffic volume
        ts_df["_vol"] = 1
    else:
        ts_df["_vol"] = ts_df[bytes_col].fillna(0)

    ts_df = ts_df.set_index("timestamp").sort_index()
    hourly = ts_df["_vol"].resample("1h").sum()

    if len(hourly) < 3:
        return []

    mean = hourly.mean()
    std = hourly.std()
    if std == 0 or np.isnan(std):
        return []

    anomalies: list[dict] = []
    for ts, vol in hourly.items():
        z = (vol - mean) / std
        if z >= z_threshold:
            sev = _spike_severity(z)
            label = bytes_col or "events"
            anomalies.append(
                {
                    "anomaly_type": "traffic_spike",
                    "severity": sev,
                    "source_ip": None,
                    "username": None,
                    "description": (
                        f"Traffic spike at {ts.strftime('%Y-%m-%d %H:%M')}: "
                        f"{vol:,.0f} {label} ({z:.1f}σ above normal)"
                    ),
                    "event_count": int(ts_df.loc[ts : ts + pd.Timedelta(hours=1)].shape[0]),
                    "start_time": ts.to_pydatetime(),
                    "end_time": (ts + pd.Timedelta(hours=1)).to_pydatetime(),
                    "score": _risk_score(sev, int(vol)),
                }
            )

    return anomalies


# ── 4. Off-Hours Login ────────────────────────────────────────────────────────

def detect_off_hours(
    df: pd.DataFrame,
    biz_start: int = settings.business_hours_start,
    biz_end: int = settings.business_hours_end,
) -> list[dict[str, Any]]:
    """Flag successful auth logins outside business hours."""
    logins = df[
        (df["status"] == "success") & (df["event_type"] == "auth")
    ].dropna(subset=["timestamp"])

    if logins.empty:
        return []

    off_hours = logins[
        ~logins["timestamp"].dt.hour.between(biz_start, biz_end - 1)
    ]

    if off_hours.empty:
        return []

    anomalies: list[dict] = []
    for _, row in off_hours.iterrows():
        hour = row["timestamp"].hour
        user = row["username"] if pd.notna(row["username"]) else "unknown"
        ip = row["source_ip"] if pd.notna(row["source_ip"]) else "unknown"
        anomalies.append(
            {
                "anomaly_type": "off_hours",
                "severity": "low",
                "source_ip": str(ip),
                "username": str(user),
                "description": (
                    f"Off-hours login: user '{user}' authenticated from {ip} "
                    f"at {row['timestamp'].strftime('%H:%M')} "
                    f"(outside {biz_start:02d}:00–{biz_end:02d}:00)"
                ),
                "event_count": 1,
                "start_time": row["timestamp"].to_pydatetime(),
                "end_time": row["timestamp"].to_pydatetime(),
                "score": 25.0,
            }
        )

    # Deduplicate: one anomaly per user per hour block
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for a in anomalies:
        key = (a["username"], a["source_ip"], a["start_time"].replace(minute=0, second=0) if a["start_time"] else None)
        if key not in seen:
            seen.add(key)
            deduped.append(a)

    return deduped


# ── Engine ─────────────────────────────────────────────────────────────────────

class AnomalyEngine:
    """Runs all detectors and returns a combined list of anomaly dicts."""

    def run(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        all_anomalies: list[dict] = []
        all_anomalies.extend(detect_brute_force(df))
        all_anomalies.extend(detect_port_scan(df))
        all_anomalies.extend(detect_traffic_spike(df))
        all_anomalies.extend(detect_off_hours(df))

        # Attach detection_time
        now = datetime.utcnow()
        for a in all_anomalies:
            a.setdefault("detection_time", now)
            a.setdefault("false_positive", False)

        return all_anomalies
