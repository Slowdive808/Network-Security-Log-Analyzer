"""
Report generator — produces PDF (multi-page) or PNG (single-chart) reports
using Matplotlib.  No external PDF libraries needed.
"""

from __future__ import annotations

import uuid
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Anomaly, LogEvent, LogFile

# ── colour palette ────────────────────────────────────────────────────────────
BG = "#0f172a"
CARD = "#1e293b"
ACCENT = "#3b82f6"
GREEN = "#22c55e"
AMBER = "#f59e0b"
RED = "#ef4444"
PURPLE = "#a855f7"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"

SEV_COLORS = {"critical": RED, "high": "#f97316", "medium": AMBER, "low": GREEN, "info": ACCENT}
TYPE_COLORS = {"brute_force": RED, "port_scan": PURPLE, "traffic_spike": AMBER, "off_hours": ACCENT}


def _apply_dark_theme():
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": CARD,
            "axes.edgecolor": "#334155",
            "axes.labelcolor": TEXT,
            "axes.titlecolor": TEXT,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": TEXT,
            "grid.color": "#334155",
            "grid.linewidth": 0.5,
            "legend.facecolor": CARD,
            "legend.edgecolor": "#334155",
            "legend.labelcolor": TEXT,
            "font.family": "monospace",
        }
    )


# ── individual chart helpers ──────────────────────────────────────────────────

def _chart_events_over_time(ax, events: list[LogEvent]):
    from collections import defaultdict

    day_counts: dict = defaultdict(int)
    for e in events:
        if e.timestamp:
            day_counts[e.timestamp.strftime("%m-%d")] += 1

    if not day_counts:
        ax.text(0.5, 0.5, "No timestamp data", ha="center", va="center", color=MUTED)
        return

    days = sorted(day_counts.keys())
    counts = [day_counts[d] for d in days]

    ax.fill_between(range(len(days)), counts, alpha=0.3, color=ACCENT)
    ax.plot(range(len(days)), counts, color=ACCENT, linewidth=2)
    ax.set_xticks(range(0, len(days), max(1, len(days) // 10)))
    ax.set_xticklabels([days[i] for i in range(0, len(days), max(1, len(days) // 10))], rotation=45, ha="right", fontsize=7)
    ax.set_title("Events Over Time", fontsize=11, pad=8)
    ax.set_ylabel("Event Count")
    ax.grid(True, axis="y", alpha=0.4)


def _chart_events_by_hour(ax, events: list[LogEvent]):
    hour_counts = Counter(e.timestamp.hour for e in events if e.timestamp)
    hours = list(range(24))
    counts = [hour_counts.get(h, 0) for h in hours]
    colors = [RED if h < 7 or h >= 19 else ACCENT for h in hours]
    ax.bar(hours, counts, color=colors, width=0.8)
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}" for h in hours], fontsize=6)
    ax.set_title("Events by Hour of Day", fontsize=11, pad=8)
    ax.set_ylabel("Count")
    # legend
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=ACCENT, label="Business hours"), Patch(color=RED, label="Off-hours")], fontsize=7)


def _chart_anomalies_by_type(ax, anomalies: list[Anomaly]):
    counts = Counter(a.anomaly_type for a in anomalies if not a.false_positive)
    if not counts:
        ax.text(0.5, 0.5, "No anomalies", ha="center", va="center", color=MUTED)
        ax.set_title("Anomalies by Type", fontsize=11, pad=8)
        return

    labels = list(counts.keys())
    vals = list(counts.values())
    colors = [TYPE_COLORS.get(l, MUTED) for l in labels]
    clean_labels = [l.replace("_", " ").title() for l in labels]
    wedges, texts, autotexts = ax.pie(vals, labels=clean_labels, colors=colors, autopct="%1.0f%%", startangle=90)
    for at in autotexts:
        at.set_color(BG)
        at.set_fontsize(8)
    ax.set_title("Anomalies by Type", fontsize=11, pad=8)


def _chart_anomalies_by_severity(ax, anomalies: list[Anomaly]):
    order = ["critical", "high", "medium", "low"]
    counts = Counter(a.severity for a in anomalies if not a.false_positive)
    vals = [counts.get(s, 0) for s in order]
    colors = [SEV_COLORS[s] for s in order]
    bars = ax.barh(order, vals, color=colors)
    for bar, v in zip(bars, vals):
        if v:
            ax.text(v + 0.3, bar.get_y() + bar.get_height() / 2, str(v), va="center", fontsize=9)
    ax.set_title("Anomalies by Severity", fontsize=11, pad=8)
    ax.set_xlabel("Count")
    ax.invert_yaxis()


def _chart_top_ips(ax, events: list[LogEvent], n: int = 10):
    ip_counts = Counter(e.source_ip for e in events if e.source_ip)
    top = ip_counts.most_common(n)
    if not top:
        ax.text(0.5, 0.5, "No IP data", ha="center", va="center", color=MUTED)
        return
    ips, counts = zip(*top)
    y = np.arange(len(ips))
    ax.barh(y, counts, color=ACCENT)
    ax.set_yticks(y)
    ax.set_yticklabels(ips, fontsize=8)
    ax.set_title(f"Top {n} Source IPs", fontsize=11, pad=8)
    ax.set_xlabel("Event Count")
    ax.invert_yaxis()


# ── summary page ──────────────────────────────────────────────────────────────

def _page_summary(pdf, log_file: LogFile, events: list[LogEvent], anomalies: list[Anomaly]):
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor(BG)

    # Title banner
    fig.text(0.5, 0.96, "NetSec Log Analyzer — Security Report", ha="center", fontsize=16, color=TEXT, weight="bold")
    fig.text(0.5, 0.93, f"File: {log_file.original_name}  |  Format: {log_file.file_format or 'auto'}",
             ha="center", fontsize=9, color=MUTED)
    fig.text(0.5, 0.91, f"Generated: {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
             ha="center", fontsize=8, color=MUTED)

    # Stat cards (row of 4)
    card_data = [
        ("Total Events", f"{log_file.event_count:,}", ACCENT),
        ("Anomalies", f"{log_file.anomaly_count:,}", RED if log_file.anomaly_count else GREEN),
        ("High/Critical", str(sum(1 for a in anomalies if a.severity in ("high", "critical") and not a.false_positive)), RED),
        ("False Positives", str(sum(1 for a in anomalies if a.false_positive)), MUTED),
    ]
    for i, (label, value, color) in enumerate(card_data):
        x = 0.1 + i * 0.22
        rect = plt.Rectangle((x, 0.76), 0.18, 0.1, transform=fig.transFigure, figure=fig,
                              facecolor=CARD, edgecolor=color, linewidth=1.5)
        fig.add_artist(rect)
        fig.text(x + 0.09, 0.84, value, ha="center", fontsize=18, color=color, weight="bold")
        fig.text(x + 0.09, 0.78, label, ha="center", fontsize=8, color=MUTED)

    # Charts grid
    gs = gridspec.GridSpec(2, 2, left=0.07, right=0.97, top=0.73, bottom=0.06, hspace=0.42, wspace=0.3)
    axes = [fig.add_subplot(gs[r, c]) for r in range(2) for c in range(2)]

    _chart_events_over_time(axes[0], events)
    _chart_events_by_hour(axes[1], events)
    _chart_anomalies_by_type(axes[2], anomalies)
    _chart_anomalies_by_severity(axes[3], anomalies)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _page_top_ips(pdf, events: list[LogEvent]):
    fig, ax = plt.subplots(figsize=(11, 8.5))
    fig.patch.set_facecolor(BG)
    _chart_top_ips(ax, events, n=15)
    fig.text(0.5, 0.97, "Top Source IPs by Event Volume", ha="center", fontsize=13, color=TEXT, weight="bold")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _page_anomaly_list(pdf, anomalies: list[Anomaly]):
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor(BG)
    fig.text(0.5, 0.97, "Anomaly Detail List", ha="center", fontsize=13, color=TEXT, weight="bold")

    cols = ["#", "Type", "Severity", "Source IP", "Count", "Start Time", "Description"]
    col_widths = [0.04, 0.11, 0.09, 0.13, 0.06, 0.14, 0.4]
    x_positions = []
    x = 0.02
    for w in col_widths:
        x_positions.append(x)
        x += w

    y_start = 0.91
    row_height = 0.052
    fig.text(x_positions[0], y_start, cols[0], fontsize=7, color=MUTED, weight="bold")
    for i, col in enumerate(cols[1:], 1):
        fig.text(x_positions[i], y_start, col, fontsize=7, color=MUTED, weight="bold")

    display_anomalies = [a for a in anomalies if not a.false_positive][:14]
    for row_idx, a in enumerate(display_anomalies):
        y = y_start - (row_idx + 1) * row_height
        if y < 0.05:
            break
        bg_color = CARD if row_idx % 2 == 0 else "#243044"
        rect = plt.Rectangle((0.01, y - 0.01), 0.98, row_height - 0.005,
                              transform=fig.transFigure, figure=fig,
                              facecolor=bg_color, edgecolor="none")
        fig.add_artist(rect)

        sev_color = SEV_COLORS.get(a.severity, MUTED)
        vals = [
            str(a.id),
            a.anomaly_type.replace("_", " ").title()[:12],
            a.severity.upper(),
            (a.source_ip or "—")[:15],
            str(a.event_count or "—"),
            a.start_time.strftime("%m-%d %H:%M") if a.start_time else "—",
            a.description[:58] + ("…" if a.description and len(a.description) > 58 else ""),
        ]
        for i, val in enumerate(vals):
            color = sev_color if i == 2 else TEXT
            fig.text(x_positions[i], y + 0.01, val, fontsize=6.5, color=color)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ── public API ────────────────────────────────────────────────────────────────

def generate_report(
    log_file: LogFile,
    db: Session,
    report_type: str = "summary",
    fmt: str = "pdf",
) -> Path:
    _apply_dark_theme()

    events = db.query(LogEvent).filter(LogEvent.file_id == log_file.id).all()
    anomalies = db.query(Anomaly).filter(Anomaly.file_id == log_file.id).all()

    stem = f"report_{log_file.id}_{uuid.uuid4().hex[:6]}"

    if fmt == "png":
        out_path = settings.reports_dir / f"{stem}.png"
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.patch.set_facecolor(BG)
        fig.suptitle(f"NetSec Report — {log_file.original_name}", color=TEXT, fontsize=14, weight="bold")
        _chart_events_over_time(axes[0][0], events)
        _chart_events_by_hour(axes[0][1], events)
        _chart_anomalies_by_type(axes[1][0], anomalies)
        _chart_anomalies_by_severity(axes[1][1], anomalies)
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG)
        plt.close(fig)
        return out_path

    # PDF
    out_path = settings.reports_dir / f"{stem}.pdf"
    with PdfPages(out_path) as pdf:
        _page_summary(pdf, log_file, events, anomalies)
        if report_type == "detailed":
            _page_top_ips(pdf, events)
            _page_anomaly_list(pdf, anomalies)

    return out_path
